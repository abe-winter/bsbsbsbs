#!/usr/bin/env python
"decode pdf417 from a perfect clipped PNG. won't work on photos"

import png, argparse, logging, collections

class AllWhiteError(Exception): "content not found in image"

Region = collections.namedtuple('Region', 'a b')

def cluster_number(bars):
    "takes array of bar lengths (in x-units standardized from start pattern). returns which cluster this belongs to, used for decoding or error checking maybe"
    assert len(bars) == 4
    return (bars[0] - bars[1] + bars[2] - bars[3]) % 9

class Clip:
    def __init__(self):
        self.firstrow = None
        self.lastrow = None
        self.lineslices = None
        self.raw_words = None
        self.est_x = None

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

    def parse_raw_words(self, rows):
        assert self.lineslices is not None
        raw = [
            self.row_words(rows[slice_][0])
            for slice_ in self.lineslices
        ]
        self.raw_words, raw_x = zip(*raw)
        self.est_x = sum(raw_x) / len(raw_x)
        logging.info('raw words %s', [len(row) for row in self.raw_words])
        logging.info('est_x %.2f', self.est_x)

    @staticmethod
    def row_words(row):
        # note: checking red only (of RGBA) on the assumption this is nice grayscale
        levels = [redpix for redpix in row[::4]]
        assert levels[0] == 255 and levels[-1] == 255 # logic slightly depends on white borders
        runs = [
            (i, b)
            for i, (a, b) in enumerate(zip([None] + levels, levels + [None]))
            if a != b
        ]
        run_lengths = [(ib - ia, leva) for (ia, leva), (ib, levb) in zip(runs[:-1], runs[1:])]
        # warning: this isn't checking for like 0, 1, 2, 4, which is a long gray region that indicates troubling scan
        assert all(length == 1 or level in (0, 255) for length, level in run_lengths) # crappy anti-aliasing if this fails; todo: config flag to allow this
        # note: this is now doing super-resolution logic for the imperfect pixels. This is slightly more accurate than just thresholding at 128
        chunks = []
        assert run_lengths[0][1] == 255 # or else the loop crashes because it doesn't append an initial chunk
        for length, level in run_lengths:
            if level == 255:
                chunks.append([])
            else:
                chunks[-1].append((length, level))
        # note: at this point space lengths are discarded. That's fine; we don't need them
        # note: if any space is gray rather than white, this breaks
        # todo: factor out this logic
        bar_lengths = []
        for chunk in chunks:
            if not chunk:
                continue
            if len(chunk) == 1:
                assert chunk[0][1] == 0
            elif len(chunk) == 2:
                assert sum(item[1] == 0 for item in chunk) == 1
            elif len(chunk) == 3:
                assert chunk[0][1] != 0 and chunk[2][1] != 0 and chunk[1][1] == 0
            else:
                raise NotImplementedError('chunks must be 1/2/3')
            bar_lengths.append(sum(length * (1 - level / 255) for length, level in chunk))
        print('bar_lengths', bar_lengths)
        raise NotImplementedError
        # True means black
        assert threshed[0] is False and threshed[-1] is False 
        edges = [i for i, (a, b) in enumerate(zip(threshed[:-1], threshed[1:])) if a != b]
        blacks = [Region(*tup) for tup in zip(edges[::2], edges[1::2])]

        # https://en.wikipedia.org/wiki/PDF417#Format
        start = blacks[:4] # start pattern
        stop = blacks[-5:] # stop pattern
        center = blacks[4:-5] # left row, codewords, right row
        singles = start[1:] + stop[1:]
        approxlen = sum(tup.b - tup.a for tup in singles) / len(singles)
        limit = approxlen * 16 * 1.1 # pdf417 word starts with black bar, ends with white space, len 17, last unit is always space so 16. 1.1 slippage because idk.
        # logging.debug('approxlen %s', approxlen)
        assert len(center) % 4 == 0

        words = [center[4 * i:4 * (i+1)] for i in range(len(center) // 4)]
        assert all(word[-1].b - word[0].a <= limit for word in words)

        return words, approxlen

    def parse_words(self):
        "raw_words (list of chunks of regions) to pdf417 encoding"
        # decoding rule is https://www.expresscorp.com/uploads/specifications/44/USS-PDF-417.pdf pg 3-4
        for row in self.raw_words:
            for chunk in row:
                print('chunk', chunk)
                x_unit_bars = [round((reg.b - reg.a) / self.est_x) for reg in chunk]
                cluster = cluster_number(x_unit_bars)
                print('cluster', cluster)
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
    clip.parse_raw_words(rows)
    clip.parse_words()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', help="path to png file")
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    decode_417(args.path)

if __name__ == '__main__': main()
