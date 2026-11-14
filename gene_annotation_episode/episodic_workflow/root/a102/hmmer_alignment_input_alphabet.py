"""Retain native Easel alphabet-open facts from original alignment bytes.

The retained Infernal 1.1.5 Easel guessers inspect format-specific byte regions
before any digital row parser runs.  This module mirrors that pre-read pass;
it does not choose an alphabet flag, decode rows, or calculate scientific
components.  Non-ASCII C ctype behavior and native integer domains that the
source does not establish remain explicitly unavailable.
"""

from .hmmer_alignment_input_types import (
    alignment_input_diagnostic,
    iter_native_alignment_lines,
)


_FORMATS = frozenset({
    "stockholm", "pfam", "afa", "a2m", "psiblast", "selex",
    "clustal", "clustallike", "phylip", "phylips",
})
_HEADER_FORMATS = frozenset({"clustal", "clustallike", "phylip", "phylips"})
_PHYLIP_FORMATS = frozenset({"phylip", "phylips"})
_FASTA_FORMATS = frozenset({"afa", "a2m"})
_COMMENT_FORMATS = frozenset({"stockholm", "pfam", "selex"})
_C_WHITESPACE = frozenset({9, 10, 11, 12, 13, 32})
# esl_memtok/esl_memspn use strchr(" \t", byte): NUL matches its terminator.
_TOKEN_DELIMITERS = frozenset({0, 9, 32})
_THRESHOLDS = (500, 5000, 50000)
_AA_ONLY = "EFIJLOPQZ"
_BOTH_CANONICAL = "ACG"
_AA_CANONICAL_NUCLEIC_AMBIGUOUS = "DHKMRSVWY"
_NARROWED_LETTERS = _AA_ONLY + _BOTH_CANONICAL + _AA_CANONICAL_NUCLEIC_AMBIGUOUS
_INT_MAX = 2147483647
_INT64_MAX = 9223372036854775807


def classify_easel_alphabet_counts(counts: list[int]) -> dict:
    """Apply esl_abc_GuessAlphabet's ordered rules to an A--Z histogram.

    Counts are exact integers, including zero.  The native function accumulates
    a signed int64 total and narrows three groups of input counts to C int.
    Outside those established domains no implementation-defined narrowing is
    invented.  The rule name records the first native branch that succeeds;
    neither an undetermined result nor unavailable arithmetic defaults to DNA.
    """
    if (
        not isinstance(counts, list)
        or len(counts) != 26
        or any(type(count) is not int or count < 0 for count in counts)
    ):
        raise ValueError("hmmer_alignment_counts_invalid")

    total = sum(counts)
    if total > _INT64_MAX or any(
        counts[ord(letter) - 65] > _INT_MAX for letter in _NARROWED_LETTERS
    ):
        return {
            "alphabet": None,
            "status": "source_semantics_unestablished",
            "rule": "native_count_range_unestablished",
        }

    n1 = sum(counts[ord(letter) - 65] for letter in _AA_ONLY)
    n2 = sum(counts[ord(letter) - 65] for letter in _BOTH_CANONICAL)
    n3 = sum(counts[ord(letter) - 65] for letter in _AA_CANONICAL_NUCLEIC_AMBIGUOUS)
    x1 = sum(counts[ord(letter) - 65] > 0 for letter in _AA_ONLY)
    x2 = sum(counts[ord(letter) - 65] > 0 for letter in _BOTH_CANONICAL)
    x3 = sum(counts[ord(letter) - 65] > 0 for letter in _AA_CANONICAL_NUCLEIC_AMBIGUOUS)
    nn, nt, nu, nx = (counts[ord(letter) - 65] for letter in "NTUX")
    xn, xt, xu = (int(count > 0) for count in (nn, nt, nu))

    alphabet = None
    rule = "undetermined"
    if total <= 10:
        rule = "short_sample"
    elif total > 2000 and nn == total:
        alphabet, rule = "DNA", "all_n_dna"
    elif n1 > 0:
        alphabet, rule = "amino", "aa_only_letter"
    elif total - (n2 + nt + nn) <= 0.02 * total and x2 + xt == 4:
        alphabet, rule = "DNA", "dna_canonical_fraction"
    elif total - (n2 + nu + nn) <= 0.02 * total and x2 + xu == 4:
        alphabet, rule = "RNA", "rna_canonical_fraction"
    elif (
        total - (n1 + n2 + n3 + nn + nt + nx) <= 0.02 * total
        and n3 > n2
        and x1 + x2 + x3 + xn + xt >= 15
    ):
        # Preserve the literal native branch.  With established nonnegative
        # counts it is unreachable: n1 == 0 leaves at most 14 distinct letters.
        alphabet, rule = "amino", "amino_diversity"
    return {
        "alphabet": alphabet,
        "status": "determined" if alphabet is not None else "undetermined",
        "rule": rule,
    }


def _token_tail(data: bytes) -> tuple[int, int] | None:
    """Return the first token start and native post-token pointer."""
    start = 0
    while start < len(data) and data[start] in _TOKEN_DELIMITERS:
        start += 1
    if start == len(data):
        return None
    tail = start
    while tail < len(data) and data[tail] not in _TOKEN_DELIMITERS:
        tail += 1
    while tail < len(data) and data[tail] in _TOKEN_DELIMITERS:
        tail += 1
    return start, tail


def _unestablished_byte(probe: dict, *, byte_start: int, byte: int) -> dict:
    probe["state"] = "source_semantics_unestablished"
    probe["alphabet"] = None
    probe["stopped_at"] = "unestablished_byte_semantics"
    probe["diagnostics"].append(alignment_input_diagnostic(
        "native_source_semantics_unestablished",
        byte_start=byte_start,
        byte_end=byte_start + 1,
        expected="ascii_ctype",
        actual=byte,
        token_hex=bytes((byte,)).hex(),
    ))
    return probe


def _checkpoint(probe: dict, *, threshold: int | None, line: int | None) -> dict:
    classification = classify_easel_alphabet_counts(probe["counts_az"])
    probe["checkpoints"].append({
        "threshold": threshold,
        "at_eof": threshold is None,
        "line": line,
        "byte_end": probe["scan_end_byte"],
        "counts_az": probe["counts_az"].copy(),
        "state": classification["status"],
        "alphabet": classification["alphabet"],
        "rule": classification["rule"],
    })
    probe["state"] = classification["status"]
    probe["alphabet"] = classification["alphabet"]
    if classification["status"] == "source_semantics_unestablished":
        total = probe["counted_letters"]
        expected, actual, token_hex = _INT64_MAX, total, None
        if total <= _INT64_MAX:
            for letter in _NARROWED_LETTERS:
                count = probe["counts_az"][ord(letter) - 65]
                if count > _INT_MAX:
                    expected, actual, token_hex = _INT_MAX, count, letter.encode("ascii").hex()
                    break
        probe["stopped_at"] = "unestablished_count_semantics"
        probe["diagnostics"].append(alignment_input_diagnostic(
            "native_source_semantics_unestablished",
            expected=expected,
            actual=actual,
            token_hex=token_hex,
        ))
    return classification


def infer_hmmer_alignment_alphabet(content: bytes, *, declared_format: str) -> dict:
    """Probe the original byte source using its declared native format.

    Counts and byte positions describe this pre-read scan, independently of
    subsequent row parsing.  A checkpoint examines the entire eligible line,
    only once, at a strictly exceeded threshold.  Unresolved scans continue to
    EOF with no sample cap.  EOF checkpoints name the last physical line read
    (or None for empty input); scan_end_byte includes fetched line terminators.
    """
    if not isinstance(content, bytes):
        raise ValueError("hmmer_alignment_content_invalid")
    if not isinstance(declared_format, str) or declared_format not in _FORMATS:
        raise ValueError("hmmer_alignment_format_invalid")

    probe = {
        "version": "hmmer_native_alignment_alphabet_probe_v1",
        "format": declared_format,
        "state": "undetermined",
        "alphabet": None,
        "counts_az": [0] * 26,
        "counted_letters": 0,
        "checkpoints": [],
        "scan_end_byte": 0,
        "stopped_at": "eof",
        "diagnostics": [],
    }
    awaiting_header = declared_format in _HEADER_FORMATS
    step = 0
    last_line = None
    for line in iter_native_alignment_lines(content):
        data = line.data
        last_line = line.number
        # GetLine consumes the whole physical line before the native scanner
        # examines bytes, even if a subsequent ctype call is unestablished.
        probe["scan_end_byte"] = line.byte_end

        if awaiting_header:
            if not all(byte in _TOKEN_DELIMITERS for byte in data):
                awaiting_header = False
            continue

        if declared_format in _FASTA_FORMATS:
            start = 0
            while start < len(data):
                byte = data[start]
                if byte >= 128:
                    return _unestablished_byte(
                        probe, byte_start=line.byte_start + start, byte=byte,
                    )
                if byte not in _C_WHITESPACE:
                    break
                start += 1
            if start == len(data) or data[start] == 62:  # '>'
                continue
        elif declared_format in _PHYLIP_FORMATS:
            if len(data) < 10 or all(byte in _TOKEN_DELIMITERS for byte in data):
                continue
            start = 10  # applies even to unnamed continuation lines
        else:
            token = _token_tail(data)
            if token is None:
                continue
            token_start, start = token
            if declared_format in _COMMENT_FORMATS and data[token_start] == 35:
                continue

        for offset in range(start, len(data)):
            byte = data[offset]
            if byte >= 128:
                return _unestablished_byte(
                    probe, byte_start=line.byte_start + offset, byte=byte,
                )
            if 65 <= byte <= 90:
                probe["counts_az"][byte - 65] += 1
                probe["counted_letters"] += 1
            elif 97 <= byte <= 122:
                probe["counts_az"][byte - 97] += 1
                probe["counted_letters"] += 1

        # nres is int in six scanners, int64_t in the shared PHYLIP scanner.
        # Keep the complete line's observed histogram; do not emulate overflow
        # or call the classifier as if the native counter remained defined.
        count_bound = _INT64_MAX if declared_format in _PHYLIP_FORMATS else _INT_MAX
        if probe["counted_letters"] > count_bound:
            probe["state"] = "source_semantics_unestablished"
            probe["alphabet"] = None
            probe["stopped_at"] = "unestablished_count_semantics"
            probe["diagnostics"].append(alignment_input_diagnostic(
                "native_source_semantics_unestablished",
                byte_start=line.byte_start,
                byte_end=line.byte_end,
                expected=count_bound,
                actual=probe["counted_letters"],
            ))
            return probe

        if step < len(_THRESHOLDS) and probe["counted_letters"] > _THRESHOLDS[step]:
            classification = _checkpoint(probe, threshold=_THRESHOLDS[step], line=line.number)
            if classification["status"] == "determined":
                probe["stopped_at"] = "checkpoint"
                return probe
            if classification["status"] == "source_semantics_unestablished":
                return probe
            step += 1

    # Unlike the other guessers, Clustal/PHYLIP return before the classifier
    # when no nonblank header was found.  Do not invent an attempted call.
    if not awaiting_header:
        _checkpoint(probe, threshold=None, line=last_line)
    return probe
