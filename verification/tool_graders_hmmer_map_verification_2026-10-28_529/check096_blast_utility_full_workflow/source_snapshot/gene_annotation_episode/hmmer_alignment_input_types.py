"""Byte locations and closed diagnostics shared by native alignment readers.

These primitives deliberately have no dependency on a row decoder, an alphabet
probe, or a numerical sheet.  Text conversion belongs to the calling reader;
locations here always address the retained bytes.
"""

from collections.abc import Iterator
from typing import NamedTuple


class NativeAlignmentLine(NamedTuple):
    number: int
    byte_start: int
    content_end: int
    byte_end: int
    data: bytes


_DIAGNOSTIC_CODES = frozenset(
    {
        "invalid_header",
        "missing_name",
        "invalid_name_byte",
        "invalid_sequence_byte",
        "row_count_mismatch",
        "row_order_mismatch",
        "column_count_mismatch",
        "block_geometry_mismatch",
        "annotation_order_mismatch",
        "annotation_cardinality_mismatch",
        "missing_consensus_line",
        "a2m_consensus_count_mismatch",
        "psiblast_case_conflict",
        "phylip_dimension_invalid",
        "native_source_semantics_unestablished",
        "empty_alignment",
        "empty_sequence",
    }
)


def iter_native_alignment_lines(content: bytes) -> Iterator[NativeAlignmentLine]:
    """Yield LF/CRLF-delimited physical lines without decoding their contents.

    A bare CR, VT or FF remains a payload byte.  Line terminators are represented
    by the difference between ``content_end`` and ``byte_end``.  A final
    terminator does not produce an extra line.
    """
    if not isinstance(content, bytes):
        raise ValueError("hmmer_alignment_content_invalid")

    def lines() -> Iterator[NativeAlignmentLine]:
        start = 0
        number = 1
        while start < len(content):
            newline = content.find(b"\n", start)
            if newline == -1:
                end = len(content)
                yield NativeAlignmentLine(number, start, end, end, content[start:end])
                return
            end = newline - 1 if newline > start and content[newline - 1] == 13 else newline
            yield NativeAlignmentLine(number, start, end, newline + 1, content[start:end])
            start = newline + 1
            number += 1

    return lines()


def alignment_input_diagnostic(
    code: str,
    *,
    record_ordinal=None,
    row_ordinal=None,
    event_ordinal=None,
    byte_start=None,
    byte_end=None,
    expected=None,
    actual=None,
    token_hex=None,
) -> dict:
    """Construct the frozen seven-field diagnostic, rejecting API misuse."""
    error = "hmmer_alignment_diagnostic_invalid"
    if not isinstance(code, str) or code not in _DIAGNOSTIC_CODES:
        raise ValueError(error)
    for value in (record_ordinal, row_ordinal, event_ordinal, byte_start, byte_end):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(error)
    if byte_start is not None and byte_end is not None and byte_end < byte_start:
        raise ValueError(error)
    for value in (expected, actual):
        if value is not None and type(value) not in (int, str):
            raise ValueError(error)
    if token_hex is not None and (
        not isinstance(token_hex, str)
        or len(token_hex) % 2
        or any(character not in "0123456789abcdef" for character in token_hex)
    ):
        raise ValueError(error)
    return {
        "code": code,
        "record_ordinal": record_ordinal,
        "row_ordinal": row_ordinal,
        "event_ordinal": event_ordinal,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "details": {"expected": expected, "actual": actual, "token_hex": token_hex},
    }
