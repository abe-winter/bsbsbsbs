#!/usr/bin/env python
"decode pdf417 from a perfect clipped PNG. won't work on photos"

import png, argparse, logging, csv, time
from words import row_words
from modes import MainState, TextState

class AllWhiteError(Exception): "content not found in image"

def cluster_number(bars):
    "takes array of bar lengths (in x-units standardized from start pattern). returns which cluster this belongs to, used for decoding or error checking maybe"
    assert len(bars) == 4
    return (bars[0] - bars[1] + bars[2] - bars[3]) % 9

def maybe_int(raw):
    return int(raw) if raw.isdigit() else raw

class Clip:
    def __init__(self):
        self.firstrow = None
        self.lastrow = None
        self.lineslices = None
        self.raw_words = None
        self.est_x = None
        self.coderows = None

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
            row_words(rows[slice_][0])
            for slice_ in self.lineslices
        ]
        self.raw_words, raw_x = zip(*raw)
        self.est_x = sum(raw_x) / len(raw_x)
        logging.info('raw words %s', [len(row) for row in self.raw_words])
        logging.info('est_x %.2f', self.est_x)

    def parse_words(self):
        "raw_words (list of chunks of regions) to codewords, i.e. looked-up integers that have to be further processed"
        # decoding rule is https://www.expresscorp.com/uploads/specifications/44/USS-PDF-417.pdf pg 3-4
        coderows = []
        for irow, row in enumerate(self.raw_words):
            lengths = [[round(bar.length / self.est_x) for bar in chunk] for chunk in row]
            clusters = [cluster_number(chunk[::2]) for chunk in lengths]
            assert all(cluster in (0, 3, 6) for cluster in clusters)
            assert all(cluster == 3 * (irow % 3) for cluster in clusters)
            len_strs = [''.join(map(str, chunk)) for chunk in lengths]
            lookup = self.bs[clusters[0]]
            coderows.append([lookup[key] for key in len_strs])
        self.coderows = coderows

    def load_bs(self):
        "bs = bar-space pattern. I copy-pasted this from an OCRed PDF so YTMND"
        t0 = time.time()
        bs = {}
        for cluster in (0, 3, 6):
            reader = csv.reader(open(f"cluster-{cluster}-bs.csv"))
            lookup = {}
            for pattern, symbol in reader:
                lookup[pattern] = int(symbol)
            assert list(lookup.values()) == list(range(len(lookup))) # i.e. expect ordering
            assert all(len(pattern) == 8 for pattern in lookup.keys())
            bs[cluster] = lookup
        self.bs = bs

        text_codes = {
            'alpha': [],
            'lower': [],
            'mixed': [],
            'punc': [],
        }
        for i, (index, alpha, lower, mixed, punc) in enumerate(csv.reader(open('text-codes.csv'))):
            assert int(index) == i
            text_codes['alpha'].append(maybe_int(alpha))
            text_codes['lower'].append(maybe_int(lower))
            text_codes['mixed'].append(maybe_int(mixed))
            text_codes['punc'].append(maybe_int(punc))
        self.text_codes = text_codes

        logging.debug('loaded csvs in %.2fs', time.time() - t0)

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

    def decode(self):
        "partial implementation of mode switching"
        assert self.coderows is not None
        # symbol_len_descriptor = self.coderows[0][1]
        # print(sum(map(len, self.coderows)) - 2 * len(self.coderows), symbol_len_descriptor)
        # assert sum(map(len, self.coderows)) == symbol_len_descriptor
        chunks = [[]]
        state = MainState()
        text_state = TextState()
        for row in self.coderows:
            for point in row[1:-1]: # ignoring LRI / RRI for now
                if point > 899:
                    state.command(point)
                    # todo: does text_state reset here?
                    chunks.append([])
                else:
                    mode = state.state()
                    state.tick()
                    if mode == 'text':
                        hichar = point // 30
                        lowchar = point % 30
                        for char in (hichar, lowchar):
                            processed = self.text_codes[text_state.state()][char]
                            text_state.tick()
                            if isinstance(processed, int):
                                chunks[-1].append(chr(processed))
                            else:
                                text_state.command(processed)
                    elif mode == 'byte':
                        print('todo byte')
                    elif mode == 'num':
                        print('todo num')
        print(chunks)
        raise NotImplementedError

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
    clip.load_bs()
    clip.parse_words()
    clip.decode()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', help="path to png file")
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    decode_417(args.path)

if __name__ == '__main__': main()
