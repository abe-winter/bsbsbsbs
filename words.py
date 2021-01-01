"words.py -- split raw-ish PNG run lengths into run-lengths and codewords"

import collections

class NotBarOrSpace(Exception): "trouble classifying region of barcode"

RunLength = collections.namedtuple('RunLength', 'length level')
Region = collections.namedtuple('Region', 'isbar length')

def chunk_run_lengths(run_lengths):
    "separate bars from spaces, group intermediate grays with *both* so they can get fractional lengths later"
    chunks = [[]]
    assert run_lengths[0].level == 255 # or else the loop crashes because it doesn't append an initial chunk. yes this is repeating levels[0] levels[-1] assert above
    # note: we're assuming that bars + spaces hit 0 / 255, i.e. no 'just grays'. I think the (0, 255), (255, 0) assert checks this case but hmm.
    for i, tup in enumerate(run_lengths):
        # ugh these cases are messy and correctness depends on ordering
        if tup.level == 255:
            if chunks[-1] and chunks[-1][-1].level == 0:
                chunks.append([])
            chunks[-1].append(tup)
        elif tup.level == 0:
            if chunks[-1] and chunks[-1][-1].level == 255:
                chunks.append([])
            chunks[-1].append(tup)
        else:
            # note: i + 1 is safe because we know 0 and -1 indexes aren't gray
            assert (run_lengths[i - 1].level, run_lengths[i + 1].level) in ((0, 255), (255, 0))
            chunks[-1].append(tup)
            chunks.append([tup])
    return chunks

BAR = 0, 1
SPACE = 1, 0

def chunks_to_regions(chunks):
    "do super-resolution logic for the imperfect pixels. This is slightly more accurate than just thresholding at 128"
    regions = []
    for chunk in chunks:
        assert chunk
        case = sum(tup.level == 255 for tup in chunk), sum(tup.level == 0 for tup in chunk)
        assert case in (BAR, SPACE)
        assert len(chunk) > 0 and len(chunk) <= 3
        if case == BAR:
            regions.append(Region(True, sum(tup.length * (1 - tup.level / 255) for tup in chunk)))
        elif case == SPACE:
            regions.append(Region(False, sum(tup.length * tup.level / 255 for tup in chunk)))
        else:
            raise NotBarOrSpace(chunk)

    return regions

def row_words(row):
    # note: checking red only (of RGBA) on the assumption this is nice grayscale
    levels = [redpix for redpix in row[::4]]
    assert levels[0] == 255 and levels[-1] == 255 # logic slightly depends on white borders
    runs = [
        (i, b)
        for i, (a, b) in enumerate(zip([None] + levels, levels + [None]))
        if a != b
    ]
    run_lengths = [RunLength(ib - ia, leva) for (ia, leva), (ib, levb) in zip(runs[:-1], runs[1:])]
    # warning: this isn't checking for like 0, 1, 2, 4, which is a long gray region that indicates troubling scan
    assert all(tup.length == 1 or tup.level in (0, 255) for tup in run_lengths) # crappy anti-aliasing if this fails; todo: config flag to allow this
    chunks = chunk_run_lengths(run_lengths)
    regions = chunks_to_regions(chunks)
    assert round(sum(reg.length for reg in regions)) == sum(tup.length for tup in run_lengths) # make sure the de-antialiasing didn't change the total length

    # https://en.wikipedia.org/wiki/PDF417#Format
    bars = [reg for reg in regions if reg.isbar]
    start = bars[:4] # start pattern
    stop = bars[-5:] # stop pattern
    singles = start[1:] + stop[1:]
    approxlen = sum(reg.length for reg in singles) / len(singles)
    len17 = approxlen * 17 # pdf417 word starts with black bar, ends with white space, len 17
    # logging.debug('approxlen %s len17 %s regions %d', approxlen, len17, len(regions))

    center = regions[9:-10] # 4 bars * 2 (for space) + 1 (for quiet) at start, 5 * 2 at end (no + 1 because the extra space belongs to a word)
    assert len(center) % 8 == 0 # 8 because each word has 4 bar + 4 space

    words = [center[8 * i:8 * (i+1)] for i in range(len(center) // 8)]
    assert all(round(10 * sum(reg.length for reg in word) / len17) == 10 for word in words) # i.e. test to 2 sigfigs

    return words, approxlen
