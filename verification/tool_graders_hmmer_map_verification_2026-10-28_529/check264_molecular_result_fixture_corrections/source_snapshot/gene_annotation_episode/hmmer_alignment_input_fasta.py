"""Pure Easel digital AFA/A2M input decoding into the shared input contract.

The reference is Infernal 1.1.5's retained Easel source, not a generic FASTA
parser.  This module expands only format-defined A2M insert slots.  It does not
infer an alphabet, calculate a checksum, weight rows, or construct a model map.
"""

from .hmmer_alignment_input_types import (
    NativeAlignmentLine,
    alignment_input_diagnostic,
    iter_native_alignment_lines,
)


_C_SPACE = b" \t\n\v\f\r"
# esl_memtok/esl_memspn use strchr; the delimiter C string's NUL also matches.
_TOKEN_DELIMITERS = b" \t\x00"
_NUCLEIC_LETTERS = b"ACGTURYMKSWHBVDNXI"
_AMINO_LETTERS = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_A2M_IGNORED = b" \t.Oo"


def _text(data: bytes) -> str:
    return data.decode("utf-8", "surrogateescape")


def _leading_space(data: bytes) -> int:
    offset = 0
    while offset < len(data) and data[offset] in _C_SPACE:
        offset += 1
    return offset


def _new_record() -> dict:
    return {
        "record_ordinal": 0,
        "reader_state": "partial",
        "native_status_equivalent": None,
        "byte_start": 0,
        "byte_end": 0,
        "line_start": 1,
        "line_end": 1,
        "header_valid": False,
        "column_count": None,
        "declared_row_count": None,
        "declared_column_count": None,
        "block_count": None,
        "rows": [],
        "column_annotations": {},
        "events": [],
        "diagnostics": [],
    }


def _new_row(ordinal: int, name: bytes, description: bytes | None) -> dict:
    return {
        "row_ordinal": ordinal,
        "name": _text(name),
        "name_bytes_hex": name.hex(),
        "description": _text(description) if description is not None else None,
        "aligned_sequence": None,
        "segments": [],
        "annotation_fragments": [],
        "column_annotations": {},
        "geometry_valid": False,
        "symbols_valid": True,
        "identity_unambiguous": True,
        "diagnostics": [],
    }


def _append_source_segment(
    segments: list[dict],
    line: NativeAlignmentLine,
    event: dict,
    start: int,
    end: int,
    aligned_start: int,
    operation: str,
) -> None:
    """Collect byte/column spans; materialize text once to avoid quadratic joins."""
    if start == end:
        return
    basis = "input_ignored" if operation == "ignore" else "input_symbol"
    aligned_end = aligned_start if operation == "ignore" else aligned_start + end - start
    byte_start = line.byte_start + start
    byte_end = line.byte_start + end
    if segments:
        previous = segments[-1]
        if (
            previous["event_ordinal"] == event["event_ordinal"]
            and previous["operation"] == operation
            and previous["basis"] == basis
            and previous["byte_end"] == byte_start
            and previous["aligned_end"] == aligned_start
        ):
            previous["byte_end"] = byte_end
            previous["column_end"] = end
            previous["aligned_end"] = aligned_end
            return
    segments.append(
        {
            "event_ordinal": event["event_ordinal"],
            "byte_start": byte_start,
            "byte_end": byte_end,
            "column_start": start,
            "column_end": end,
            "aligned_start": aligned_start,
            "aligned_end": aligned_end,
            "operation": operation,
            "basis": basis,
            "source_text": "",
            "decoded_text": "",
        }
    )


def _append_native_gap(segments: list[dict], aligned_start: int, count: int) -> None:
    if count:
        segments.append(
            {
                "event_ordinal": None,
                "byte_start": None,
                "byte_end": None,
                "column_start": None,
                "column_end": None,
                "aligned_start": aligned_start,
                "aligned_end": aligned_start + count,
                "operation": "native_gap",
                "basis": "a2m_insert_slot",
                "source_text": "",
                "decoded_text": "-" * count,
            }
        )


def _finish_segments(content: bytes, segments: list[dict], alphabet: str) -> str:
    for segment in segments:
        if segment["byte_start"] is None:
            continue
        raw = content[segment["byte_start"] : segment["byte_end"]]
        segment["source_text"] = _text(raw)
        if segment["operation"] == "copy":
            segment["decoded_text"] = segment["source_text"]
        elif segment["operation"] == "symbol_alias":
            # AFA's inmap[0] is a valid unknown code, unlike an illegal byte.
            segment["decoded_text"] = ("X" if alphabet == "amino" else "N") * len(raw)
    return "".join(segment["decoded_text"] for segment in segments)


class _FastaDecoder:
    def __init__(self, content: bytes, declared_format: str, alphabet: str):
        self.content = content
        self.format = declared_format
        self.alphabet = alphabet
        self.letters = _AMINO_LETTERS if alphabet == "amino" else _NUCLEIC_LETTERS
        self.record = _new_record()
        self.states = []
        self.current = None
        self.expected_consensus = None
        self.first_insert_capacity = 1
        self.end_state = "eof"

    def event(self, line: NativeAlignmentLine, kind: str, *, row=None, value=None) -> dict:
        event = {
            "event_ordinal": len(self.record["events"]),
            "kind": kind,
            "block_index": None,
            "row_ordinal": row,
            "tag": None,
            "raw": _text(self.content[line.byte_start : line.byte_end]),
            "value": value,
            "locator": {
                "line": line.number,
                "byte_start": line.byte_start,
                "byte_end": line.byte_end,
            },
        }
        self.record["events"].append(event)
        self.record["byte_end"] = line.byte_end
        self.record["line_end"] = line.number
        return event

    def stop(
        self,
        code: str,
        event: dict,
        *,
        state=None,
        start=None,
        end=None,
        expected=None,
        actual=None,
        token_hex=None,
        unestablished=False,
    ) -> bool:
        row = state["row"] if state is not None else None
        diagnostic = alignment_input_diagnostic(
            code,
            record_ordinal=0,
            row_ordinal=row["row_ordinal"] if row is not None else None,
            event_ordinal=event["event_ordinal"],
            byte_start=event["locator"]["byte_start"] if start is None else start,
            byte_end=event["locator"]["byte_end"] if end is None else end,
            expected=expected,
            actual=actual,
            token_hex=token_hex,
        )
        self.record["diagnostics"].append(diagnostic)
        if row is not None:
            row["diagnostics"].append(diagnostic)
            row["geometry_valid"] = False
        if unestablished:
            self.end_state = "source_semantics_unestablished"
            self.record["reader_state"] = "source_semantics_unestablished"
            self.record["native_status_equivalent"] = None
        else:
            self.end_state = "parse_error"
            self.record["reader_state"] = "partial" if self.states else "invalid"
            self.record["native_status_equivalent"] = 7
        return False

    def header(self, line: NativeAlignmentLine, start: int, event: dict) -> bool:
        position = start + 1
        while position < len(line.data) and line.data[position] in _TOKEN_DELIMITERS:
            position += 1
        name_start = position
        while position < len(line.data) and line.data[position] not in _TOKEN_DELIMITERS:
            position += 1
        name = line.data[name_start:position]
        if not name:
            self.record["header_valid"] = False
            # AFA checks n <= 1 before esl_memtok; A2M goes directly to memtok.
            code = "invalid_header" if self.format == "afa" and len(line.data) - start <= 1 else "missing_name"
            return self.stop(code, event)
        while position < len(line.data) and line.data[position] in _TOKEN_DELIMITERS:
            position += 1
        description = line.data[position:] if position < len(line.data) else None
        row = _new_row(len(self.states), name, description)
        self.current = {
            "row": row,
            "length": 0,
            "ncons": 0,
            "insert_lengths": [0],
            "source_lines": [],
        }
        self.states.append(self.current)
        self.record["rows"].append(row)
        self.record["header_valid"] = True
        event["row_ordinal"] = row["row_ordinal"]
        event["value"] = row["name"]
        return True

    def valid_letter(self, value: int) -> bool:
        upper = value - 32 if 97 <= value <= 122 else value
        return upper in self.letters

    def afa_sequence(self, line: NativeAlignmentLine, start: int, event: dict) -> bool:
        state = self.current
        row = state["row"]
        segments = row["segments"]
        _append_source_segment(segments, line, event, 0, start, state["length"], "ignore")
        for position in range(start, len(line.data)):
            value = line.data[position]
            if value == 32:
                operation = "ignore"
            elif value == 0:
                operation = "symbol_alias"
            elif self.valid_letter(value) or value in b"-._*~":
                operation = "copy"
            else:
                row["symbols_valid"] = False
                return self.stop(
                    "invalid_sequence_byte",
                    event,
                    state=state,
                    start=line.byte_start + position,
                    end=line.byte_start + position + 1,
                    token_hex=line.data[position : position + 1].hex(),
                )
            _append_source_segment(
                segments, line, event, position, position + 1, state["length"], operation
            )
            if operation != "ignore":
                state["length"] += 1
        return True

    def a2m_sequence(self, line: NativeAlignmentLine, start: int, event: dict) -> bool:
        state = self.current
        if state["row"]["row_ordinal"] == 0:
            # Exact last allocation in Read: old this_ncons + physical tail n + 1.
            self.first_insert_capacity = state["ncons"] + len(line.data) - start + 1

        # Native performs the entire structural pass before digital validation.
        for position in range(start, len(line.data)):
            value = line.data[position]
            if value >= 128:
                state["row"]["symbols_valid"] = False
                return self.stop(
                    "native_source_semantics_unestablished",
                    event,
                    state=state,
                    start=line.byte_start + position,
                    end=line.byte_start + position + 1,
                    actual="nonascii_ctype",
                    token_hex=line.data[position : position + 1].hex(),
                    unestablished=True,
                )
            if value == 79:  # uppercase O is a free insertion module marker
                continue
            if 65 <= value <= 90 or value == 45:
                state["ncons"] += 1
                state["insert_lengths"].append(0)
            elif 97 <= value <= 122:
                if (
                    self.expected_consensus == 0
                    and state["row"]["row_ordinal"] > 0
                    and state["ncons"] >= self.first_insert_capacity
                ):
                    return self.stop(
                        "native_source_semantics_unestablished",
                        event,
                        state=state,
                        start=line.byte_start + position,
                        end=line.byte_start + position + 1,
                        actual="a2m_zero_consensus_insert_slot",
                        token_hex=line.data[position : position + 1].hex(),
                        unestablished=True,
                    )
                state["insert_lengths"][state["ncons"]] += 1
            if self.expected_consensus and state["ncons"] > self.expected_consensus:
                return self.stop(
                    "a2m_consensus_count_mismatch",
                    event,
                    state=state,
                    start=line.byte_start + position,
                    end=line.byte_start + position + 1,
                    expected=self.expected_consensus,
                    actual=state["ncons"],
                )

        corner = None
        for position in range(start, len(line.data)):
            value = line.data[position]
            if value in (0, 111) and corner is None:
                corner = position
            if value in _A2M_IGNORED:
                continue
            if value == 0 or value == 45 or self.valid_letter(value):
                state["length"] += 1
                continue
            state["row"]["symbols_valid"] = False
            return self.stop(
                "invalid_sequence_byte",
                event,
                state=state,
                start=line.byte_start + position,
                end=line.byte_start + position + 1,
                token_hex=line.data[position : position + 1].hex(),
            )
        if corner is not None:
            value = line.data[corner]
            return self.stop(
                "native_source_semantics_unestablished",
                event,
                state=state,
                start=line.byte_start + corner,
                end=line.byte_start + corner + 1,
                actual="a2m_nul" if value == 0 else "a2m_lowercase_o",
                token_hex=line.data[corner : corner + 1].hex(),
                unestablished=True,
            )
        return True

    def finish_row(self, event: dict) -> bool:
        state = self.current
        if self.format == "afa":
            if state["length"] == 0:
                return self.stop("empty_sequence", event, state=state, expected=1, actual=0)
            expected = self.states[0]["length"]
            if state["length"] != expected:
                return self.stop(
                    "column_count_mismatch",
                    event,
                    state=state,
                    expected=expected,
                    actual=state["length"],
                )
            state["row"]["geometry_valid"] = True
        elif self.expected_consensus is None:
            self.expected_consensus = state["ncons"]
        elif state["ncons"] != self.expected_consensus:
            return self.stop(
                "a2m_consensus_count_mismatch",
                event,
                state=state,
                expected=self.expected_consensus,
                actual=state["ncons"],
            )
        return True

    def expand_a2m(self) -> None:
        ncons = self.expected_consensus
        widths = [
            max(state["insert_lengths"][slot] for state in self.states)
            for slot in range(ncons + 1)
        ]
        rf = "".join("." * width + ("x" if slot < ncons else "") for slot, width in enumerate(widths))
        self.record["column_count"] = len(rf)
        self.record["column_annotations"]["RF"] = {
            "text": rf,
            "valid": True,
            "basis": "native_format_derivation",
            "fragments": [],
        }
        for state in self.states:
            row = state["row"]
            segments = row["segments"]
            aligned = slot = inserted = 0
            for line, start, event in state["source_lines"]:
                _append_source_segment(segments, line, event, 0, start, aligned, "ignore")
                for position in range(start, len(line.data)):
                    value = line.data[position]
                    if value in _A2M_IGNORED:
                        _append_source_segment(segments, line, event, position, position + 1, aligned, "ignore")
                        continue
                    if 65 <= value <= 90 or value == 45:
                        count = widths[slot] - inserted
                        _append_native_gap(segments, aligned, count)
                        aligned += count
                        slot += 1
                        inserted = 0
                    else:
                        inserted += 1
                    _append_source_segment(segments, line, event, position, position + 1, aligned, "copy")
                    aligned += 1
            _append_native_gap(segments, aligned, widths[slot] - inserted)
            row["aligned_sequence"] = _finish_segments(self.content, segments, self.alphabet)
            row["geometry_valid"] = bool(rf)

    def batch(self) -> dict:
        if self.format == "afa":
            for state in self.states:
                row = state["row"]
                row["aligned_sequence"] = _finish_segments(self.content, row["segments"], self.alphabet)
        next_offset = self.record["byte_end"]
        return {
            "version": "hmmer_native_alignment_decoding_v1",
            "format": self.format,
            "alphabet": self.alphabet,
            "records": [self.record],
            "diagnostics": list(self.record["diagnostics"]),
            "end_state": self.end_state,
            "next_byte_offset": next_offset,
            "trailing_range": (
                {"byte_start": next_offset, "byte_end": len(self.content)}
                if next_offset < len(self.content)
                else None
            ),
        }

    def decode(self) -> dict:
        for line in iter_native_alignment_lines(self.content):
            if self.current is None and all(value in _TOKEN_DELIMITERS for value in line.data):
                self.event(line, "blank")
                continue
            start = _leading_space(line.data)
            if start < len(line.data) and line.data[start] >= 128:
                # Native isspace(*p) sees this signed/non-ASCII char before
                # framing or digitization; locale-dependent behavior is unknown.
                event = self.event(
                    line,
                    "invalid" if self.current is None else "sequence",
                    row=self.current["row"]["row_ordinal"] if self.current is not None else None,
                    value=_text(line.data[start:]),
                )
                if self.current is not None:
                    self.current["row"]["symbols_valid"] = False
                    if self.format == "afa":
                        _append_source_segment(
                            self.current["row"]["segments"],
                            line, event, 0, start, self.current["length"], "ignore"
                        )
                self.stop(
                    "native_source_semantics_unestablished",
                    event,
                    state=self.current,
                    start=line.byte_start + start,
                    end=line.byte_start + start + 1,
                    actual="nonascii_ctype",
                    token_hex=line.data[start : start + 1].hex(),
                    unestablished=True,
                )
                return self.batch()
            if self.current is None:
                if start == len(line.data) or line.data[start] != 62:
                    event = self.event(line, "invalid")
                    self.stop("invalid_header", event)
                    return self.batch()
                event = self.event(line, "header")
                if not self.header(line, start, event):
                    return self.batch()
            elif start < len(line.data) and line.data[start] == 62:
                # GetLine has already consumed this header when prior-row checks run.
                event = self.event(line, "header")
                if not self.finish_row(event) or not self.header(line, start, event):
                    return self.batch()
            else:
                event = self.event(
                    line,
                    "blank" if start == len(line.data) else "sequence",
                    row=self.current["row"]["row_ordinal"],
                    value=None if start == len(line.data) else _text(line.data[start:]),
                )
                self.current["source_lines"].append((line, start, event))
                if self.format == "afa":
                    if not self.afa_sequence(line, start, event):
                        return self.batch()
                elif start < len(line.data) and not self.a2m_sequence(line, start, event):
                    return self.batch()

        if self.current is None:
            # EOF without an MSA is not an alignment occurrence.
            return {
                "version": "hmmer_native_alignment_decoding_v1",
                "format": self.format,
                "alphabet": self.alphabet,
                "records": [],
                "diagnostics": [
                    alignment_input_diagnostic(
                        "empty_alignment", byte_start=0, byte_end=len(self.content), actual=0
                    )
                ],
                "end_state": "eof",
                "next_byte_offset": len(self.content),
                "trailing_range": None,
            }
        if not self.finish_row(self.record["events"][-1]):
            return self.batch()
        self.record["reader_state"] = "complete"
        self.record["native_status_equivalent"] = 0
        if self.format == "afa":
            self.record["column_count"] = self.states[0]["length"]
        else:
            self.expand_a2m()
            if self.record["column_count"] == 0:
                # Native accepts this empty geometry; numerical consumers cannot.
                self.record["reader_state"] = "invalid"
                diagnostic = alignment_input_diagnostic(
                    "empty_alignment",
                    record_ordinal=0,
                    byte_start=0,
                    byte_end=len(self.content),
                    expected=1,
                    actual=0,
                )
                self.record["diagnostics"].append(diagnostic)
        return self.batch()


def decode_native_fasta_alignment(
    content: bytes, *, declared_format: str, alphabet: str
) -> dict:
    """Decode one whole-file AFA/A2M MSA with an explicit actual alphabet.

    Malformed scientific bytes return the consumed events, usable partial AFA
    spans, diagnostics, and the unconsumed range.  Failed A2M expansion has no
    aligned row or segment coordinates.  Only argument misuse raises ValueError.
    """
    if not isinstance(content, bytes):
        raise ValueError("hmmer_alignment_content_invalid")
    if not isinstance(declared_format, str) or declared_format not in ("afa", "a2m"):
        raise ValueError("hmmer_alignment_format_invalid")
    if not isinstance(alphabet, str) or alphabet not in ("amino", "DNA", "RNA"):
        raise ValueError("hmmer_alignment_alphabet_invalid")
    return _FastaDecoder(content, declared_format, alphabet).decode()
