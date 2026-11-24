"""The grader and the sheet of the parts-discovery tool ``describe_piece``: what the bare DNA of the piece is, as facts. It proposes
no part. Everything is counted from the sequence alone.

THE FACTS. ``length`` (nt); the counts of A, C, G, T and of every other letter (``ambiguous_nt``); ``gc_fraction`` = (G + C) over
the unambiguous bases (A + C + G + T); ``gc_skew`` = (G - C) / (G + C) over the whole piece; the GC fraction of each consecutive
non-overlapping window of ``WINDOW_NT`` nt (the full windows only: a tail shorter than a window is not a window; a piece shorter
than one window has ``window_count`` 0 and no minimum or maximum), kept as a list, with its minimum and maximum; the frequencies of
the 256 overlapping words of four unambiguous bases (``tetranucleotide_frequency``, each count over ``tetranucleotide_total``, the
words with an ambiguous base left out). The frequencies stay in this sheet; what the head returns are the numbers named above.

The sheet is controlled data: numbers and the letters of the bases."""
from itertools import product

import numpy as np

SCHEMA = 'parts_piece_description_sheet'
PROVIDER = 'piece_description'
WINDOW_NT = 5000
WORD_LENGTH = 4
BASES = 'ACGT'
WORDS = [''.join(word) for word in product(BASES, repeat=WORD_LENGTH)]
_CODE = np.full(256, 4, dtype=np.int64)
for _index, _letter in enumerate(BASES):
    _CODE[ord(_letter)] = _index


def grade_piece_description(sequence, *, piece_ref):
    """The sheet of the piece ``piece_ref`` whose upper-case ``sequence`` is given."""
    coded = _CODE[np.frombuffer(sequence.encode('ascii'), dtype=np.uint8)]
    counts = np.bincount(coded, minlength=5)
    a, c, g, t, other = (int(count) for count in counts)
    windows = coded[:len(coded) // WINDOW_NT * WINDOW_NT].reshape(-1, WINDOW_NT)
    window_gc = [float(value) for value in ((windows == 1) | (windows == 2)).sum(axis=1) / (windows < 4).sum(axis=1)]
    valid = np.ones(len(coded) - WORD_LENGTH + 1, dtype=bool)
    index = np.zeros(len(coded) - WORD_LENGTH + 1, dtype=np.int64)
    for offset in range(WORD_LENGTH):
        letters = coded[offset:len(coded) - WORD_LENGTH + 1 + offset]
        valid &= letters < 4
        index = index * 4 + letters
    word_counts = np.bincount(index[valid], minlength=len(WORDS))
    total = int(word_counts.sum())
    return {'schema': SCHEMA, 'provider': PROVIDER, 'piece_ref': piece_ref, 'length': len(sequence),
            'base_counts': {'A': a, 'C': c, 'G': g, 'T': t}, 'ambiguous_nt': other,
            'gc_fraction': (g + c) / (a + c + g + t), 'gc_skew': (g - c) / (g + c),
            'window_nt': WINDOW_NT, 'window_count': len(window_gc),
            'window_gc_min': min(window_gc) if window_gc else None, 'window_gc_max': max(window_gc) if window_gc else None,
            'window_gc': window_gc, 'tetranucleotide_total': total,
            'tetranucleotide_frequency': {word: int(count) / total for word, count in zip(WORDS, word_counts)}}


__all__ = ['PROVIDER', 'SCHEMA', 'WINDOW_NT', 'grade_piece_description']
