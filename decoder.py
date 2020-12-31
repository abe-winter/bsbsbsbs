#!/usr/bin/env python
"decode pdf417 from a perfect clipped PNG. won't work on photos"

import png, argparse, logging, collections

class AllWhiteError(Exception): "content not found in image"

Region = collections.namedtuple('Region', 'a b')

class Clip:
    def __init__(self):
        self.firstrow = None
        self.lastrow = None
        self.lineslices = None

    def extract_lines(self, rows):
        "get identical line regions from image"
        assert self.firstrow is not None and self.lastrow is not None
        breaks = [self.firstrow]
        for i in range(self.firstrow, self.lastrow - 1):
            if rows[i] != rows[i + 1]:
                breaks.append(i + 1)
        breaks.append(self.lastrow)
        slices = []
        for a, b in zip(breaks[:-1], breaks[1:]):
            if b - a > 4: # arbitrary thresh, make it configurable
                slices.append(slice(a, b))
        self.lineslices = slices
        logging.debug('found %d lines', len(self.lineslices))

    def parse_rows(self, rows):
        assert self.lineslices is not None
        for slice_ in self.lineslices:
            yield self.parse_row(rows[slice_][0])

    def parse_row(self, row):
        # note: checking red only (of RGBA) on the assumption this is pretty grayscale
        threshed = [redpix < 128 for redpix in row[::4]]
        # True means black
        assert threshed[0] is False and threshed[-1] is False # logic slightly depends on white borders
        edges = [i for i, (a, b) in enumerate(zip(threshed[:-1], threshed[1:])) if a != b]
        blacks = [Region(*tup) for tup in zip(edges[::2], edges[1::2])]
        print('blacks', blacks)
        # https://en.wikipedia.org/wiki/PDF417#Format
        start = blacks[:4] # start pattern
        stop = blacks[-5:] # stop pattern
        center = blacks[4:-5] # left row, codewords, right row
        singles = start[1:] + stop[1:]
        approxlen = sum(tup.b - tup.a for tup in singles) / len(singles)
        limit = approxlen * 16 # pdf417 word starts with black bar, ends with white space, len 17. I'm using 16 to make room for antialiasing? prove this is robust
        logging.debug('approxlen %s', approxlen)
        words = [[]]
        for region in center:
            if words[-1] and region.b - words[-1][0].a > limit:
                words.append([])
            words[-1].append(region)
        logging.debug('parsed %d words', len(words))
        raise NotImplementedError

    def infer_height(self, rows):
        # todo perf: only scan top-left tenth maybe
        for i, row in enumerate(rows):
            if any(px != 255 for px in row):
                self.firstrow = i
                logging.debug('first row %d / %d', self.firstrow, len(rows))
                break
        else:
            raise AllWhiteError("at top")
        for i, row in enumerate(reversed(rows)):
            if any(px != 255 for px in row):
                self.lastrow = len(rows) - 1 - i
                logging.debug('last row %d / %d', self.lastrow, len(rows))
                break
        else:
            raise AllWhiteError("at bottom")

def decode_417(fname):
    "try to decode 4-bar, 1-space, 17-unit structure"
    width, height, rows_gen, info = png.Reader(filename=fname).asDirect()
    rows = list(rows_gen)
    assert len(rows) == height
    assert all(len(row) == width * 4 for row in rows)
    clip = Clip()
    clip.infer_height(rows)
    print(clip.firstrow, clip.lastrow)
    clip.extract_lines(rows)
    parsed = list(clip.parse_rows(rows))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', help="path to png file")
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    decode_417(args.path)

if __name__ == '__main__': main()
