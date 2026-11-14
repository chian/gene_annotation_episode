"""Strict, declared Easel digital PHYLIP/PHYLIPS byte decoding.

Reference: Infernal 1.1.5's esl_msafile_phylip.c, with ten-byte names.
This supplies source rows and coordinates only. Alphabet inference, numerical
sheets, weighting, checksums and model maps belong to their existing owners.
"""

from .hmmer_alignment_input_types import (
    NativeAlignmentLine,
    alignment_input_diagnostic,
    iter_native_alignment_lines,
)


# esl_memspn/esl_memtok call strchr: the delimiter string's NUL also matches.
_DELIMITERS = b" \t\x00"
_C_SPACE = b" \t\n\v\f\r"
_IGNORED = b" \t012345678"
_NUCLEIC_LETTERS = b"ACGTURYMKSWHBVDNXI"


def _text(value: bytes) -> str:
    return value.decode("utf-8", "surrogateescape")


def _blank(line: NativeAlignmentLine) -> bool:
    return all(value in _DELIMITERS for value in line.data)


def _tokens(data: bytes):
    """Yield exact esl_memtok space/tab/NUL tokens and their byte columns."""
    position = 0
    while position < len(data):
        while position < len(data) and data[position] in _DELIMITERS:
            position += 1
        start = position
        while position < len(data) and data[position] not in _DELIMITERS:
            position += 1
        if start != position:
            yield start, data[start:position]


def _integer(token: bytes):
    """esl_mem_strtoi32(base=0), including prefix acceptance and overflow.

    Return (value, failure, inspected_position, overflowing_value). A high byte
    is unavailable only if the native conversion actually reaches its ctype
    tests; an ignored suffix beyond an earlier ASCII terminator is not tested.
    """
    position = 0
    while position < len(token) and token[position] in _C_SPACE:
        position += 1
    if position < len(token) and token[position] >= 128:
        return None, "ctype", position, None
    negative = position < len(token) and token[position] == 45
    if negative:
        position += 1
    digits = 0
    if token[position:position + 2] == b"0x":
        position += 2
        base = 16
    elif position < len(token) and token[position] == 48:
        position += 1
        base = 8
        digits = 1
    else:
        base = 10
    value = 0
    limit = 2147483648 if negative else 2147483647
    while position < len(token):
        symbol = token[position]
        if symbol >= 128:
            return None, "ctype", position, None
        if 48 <= symbol <= 57:
            digit = symbol - 48
        elif 65 <= symbol <= 90:
            digit = symbol - 65 + 10
        elif 97 <= symbol <= 122:
            digit = symbol - 97 + 10
        else:
            break
        if digit >= base:
            break
        candidate = value * base + digit
        if candidate > limit:
            return None, "overflow", position, -candidate if negative else candidate
        value = candidate
        position += 1
        digits += 1
    if not digits:
        return None, "syntax", position, None
    return -value if negative else value, None, None, None


def _new_record(ordinal: int, line: NativeAlignmentLine, sequential: bool) -> dict:
    return {
        "record_ordinal": ordinal,
        "reader_state": "partial",
        "native_status_equivalent": None,
        "byte_start": line.byte_start,
        "byte_end": line.byte_start,
        "line_start": line.number,
        "line_end": line.number,
        "header_valid": False,
        "column_count": None,
        "declared_row_count": None,
        "declared_column_count": None,
        "block_count": None if sequential else 0,
        "rows": [],
        "column_annotations": {},
        "events": [],
        "diagnostics": [],
    }


def _new_row(ordinal: int, name: bytes) -> dict:
    return {
        "row_ordinal": ordinal,
        "name": _text(name),
        "name_bytes_hex": name.hex(),
        "description": None,
        "aligned_sequence": "",
        "segments": [],
        "annotation_fragments": [],
        "column_annotations": {},
        "geometry_valid": False,
        "symbols_valid": True,
        "identity_unambiguous": True,
        "diagnostics": [],
    }


class _PhylipDecoder:
    def __init__(self, content: bytes, declared_format: str, alphabet: str):
        self.content = content
        self.format = declared_format
        self.alphabet = alphabet
        self.sequential = declared_format == "phylips"
        self.lines = iter_native_alignment_lines(content)
        self.pending = None
        self.cursor = 0
        self.records = []
        self.record = None
        self.lengths = []
        self.end_state = "eof"

    def read(self):
        if self.pending is not None:
            line = self.pending
            self.pending = None
        else:
            line = next(self.lines, None)
        self.cursor = len(self.content) if line is None else line.byte_end
        return line

    def put_back(self, line: NativeAlignmentLine) -> None:
        self.pending = line
        self.cursor = line.byte_start

    def event(self, line: NativeAlignmentLine, kind: str, *, row=None,
              block=None, value=None) -> dict:
        event = {
            "event_ordinal": len(self.record["events"]),
            "kind": kind,
            "block_index": block,
            "row_ordinal": row,
            "tag": None,
            "raw": _text(self.content[line.byte_start:line.byte_end]),
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

    def diagnostic(self, code: str, *, event=None, row=None, start=None,
                   end=None, expected=None, actual=None, token=None) -> dict:
        diagnostic = alignment_input_diagnostic(
            code,
            record_ordinal=self.record["record_ordinal"],
            row_ordinal=row["row_ordinal"] if row is not None else None,
            event_ordinal=event["event_ordinal"] if event is not None else None,
            byte_start=(event["locator"]["byte_start"] if event is not None else self.cursor)
            if start is None else start,
            byte_end=(event["locator"]["byte_end"] if event is not None else self.cursor)
            if end is None else end,
            expected=expected,
            actual=actual,
            token_hex=None if token is None else token.hex(),
        )
        self.record["diagnostics"].append(diagnostic)
        if row is not None:
            row["diagnostics"].append(diagnostic)
        return diagnostic

    def fail(self, code: str, *, unestablished=False, **details) -> bool:
        self.diagnostic(code, **details)
        if unestablished:
            self.record["reader_state"] = "source_semantics_unestablished"
            self.record["native_status_equivalent"] = None
            self.end_state = "source_semantics_unestablished"
        else:
            self.record["reader_state"] = "partial" if self.record["rows"] else "invalid"
            self.record["native_status_equivalent"] = 7
            self.end_state = "parse_error"
        return False

    def header(self, line: NativeAlignmentLine) -> bool:
        event = self.event(line, "dimensions")
        tokens = _tokens(line.data)
        for key in ("declared_row_count", "declared_column_count"):
            item = next(tokens, None)
            if item is None:
                return self.fail("invalid_header", event=event)
            start, token = item
            value, error, position, overflow = _integer(token)
            if error == "ctype":
                return self.fail(
                    "native_source_semantics_unestablished", event=event,
                    start=line.byte_start + start + position,
                    end=line.byte_start + start + position + 1,
                    actual="nonascii_ctype", token=token[position:position + 1],
                    unestablished=True,
                )
            if error is not None:
                return self.fail(
                    "phylip_dimension_invalid", event=event,
                    start=line.byte_start + start, end=line.byte_start + start + len(token),
                    expected=(-2147483648 if overflow is not None and overflow < 0 else 2147483647)
                    if error == "overflow" else None,
                    actual=overflow, token=token,
                )
            self.record[key] = value
        self.record["header_valid"] = True
        if self.record["declared_row_count"] <= 0 or self.record["declared_column_count"] <= 0:
            for key in ("declared_row_count", "declared_column_count"):
                if self.record[key] <= 0:
                    self.diagnostic("phylip_dimension_invalid", event=event,
                                    expected=1, actual=self.record[key])
            return self.fail(
                "native_source_semantics_unestablished", event=event,
                actual="phylip_nonpositive_dimensions", unestablished=True,
            )
        return True

    def named_row(self, line: NativeAlignmentLine, event: dict, ordinal: int):
        existing = self.record["rows"][ordinal] if ordinal < len(self.record["rows"]) else None
        if existing is not None:
            event["row_ordinal"] = ordinal
        if len(line.data) < 10:
            self.fail("missing_name", event=event, row=existing, expected=10, actual=len(line.data))
            return None
        name = line.data[:10].strip(b" ")
        name_start = 0
        while name_start < 10 and line.data[name_start] == 32:
            name_start += 1
        for position, symbol in enumerate(name, name_start):
            if symbol >= 128:
                self.fail(
                    "native_source_semantics_unestablished", event=event, row=existing,
                    start=line.byte_start + position, end=line.byte_start + position + 1,
                    actual="nonascii_ctype", token=line.data[position:position + 1],
                    unestablished=True,
                )
                return None
            if not 32 <= symbol <= 126:
                self.fail(
                    "invalid_name_byte", event=event, row=existing,
                    start=line.byte_start + position, end=line.byte_start + position + 1,
                    token=line.data[position:position + 1],
                )
                return None
        name = name.replace(b" ", b"_")
        if ordinal == len(self.record["rows"]):
            row = _new_row(ordinal, name)
            self.record["rows"].append(row)
            self.lengths.append(0)
        else:
            # PHYLIPS tests alen==0, so a second zero-length named line replaces
            # the previous name. Original name bytes remain in both Events.
            row = self.record["rows"][ordinal]
            row["name"] = _text(name)
            row["name_bytes_hex"] = name.hex()
        event["row_ordinal"] = ordinal
        return row

    def segment(self, line: NativeAlignmentLine, event: dict, row: dict,
                position: int, operation: str) -> None:
        ordinal = row["row_ordinal"]
        aligned_start = self.lengths[ordinal]
        aligned_end = aligned_start + (operation != "ignore")
        segments = row["segments"]
        byte_start = line.byte_start + position
        if (segments and segments[-1]["event_ordinal"] == event["event_ordinal"]
                and segments[-1]["operation"] == operation
                and segments[-1]["byte_end"] == byte_start):
            segments[-1]["byte_end"] = byte_start + 1
            segments[-1]["column_end"] = position + 1
            segments[-1]["aligned_end"] = aligned_end
        else:
            segments.append({
                "event_ordinal": event["event_ordinal"],
                "byte_start": byte_start,
                "byte_end": byte_start + 1,
                "column_start": position,
                "column_end": position + 1,
                "aligned_start": aligned_start,
                "aligned_end": aligned_end,
                "operation": operation,
                "basis": "input_ignored" if operation == "ignore" else "input_symbol",
                "source_text": "",
                "decoded_text": "",
            })
        self.lengths[ordinal] = aligned_end

    def sequence(self, line: NativeAlignmentLine, event: dict, row: dict, start: int) -> bool:
        event["value"] = _text(line.data[start:])
        for position in range(start, len(line.data)):
            symbol = line.data[position]
            upper = symbol - 32 if 97 <= symbol <= 122 else symbol
            if symbol in _IGNORED:
                operation = "ignore"
            elif symbol in (0, 63) or (self.alphabet != "amino" and symbol == 79):
                operation = "symbol_alias"
            elif symbol in b"-.*" or (
                65 <= upper <= 90 if self.alphabet == "amino" else upper in _NUCLEIC_LETTERS
            ):
                operation = "copy"
            else:
                row["symbols_valid"] = False
                return self.fail(
                    "invalid_sequence_byte", event=event, row=row,
                    start=line.byte_start + position, end=line.byte_start + position + 1,
                    token=line.data[position:position + 1],
                )
            self.segment(line, event, row, position, operation)
        return True

    def skip_blanks(self, line):
        while line is not None and _blank(line):
            self.event(line, "blank")
            line = self.read()
        return line

    def interleaved(self, line: NativeAlignmentLine) -> bool:
        nseq = self.record["declared_row_count"]
        declared = self.record["declared_column_count"]
        width = 0
        blocks = 0
        while True:
            index = 0
            block_width = None
            while True:
                event = self.event(line, "sequence", block=blocks,
                                   row=index if blocks else None)
                if blocks == 0:
                    row = self.named_row(line, event, index)
                    if row is None:
                        return False
                else:
                    row = self.record["rows"][index]
                previous = self.lengths[index]
                if not self.sequence(line, event, row, 10 if blocks == 0 else 0):
                    return False
                added = self.lengths[index] - previous
                if block_width is None:
                    block_width = added
                elif added != block_width:
                    return self.fail("block_geometry_mismatch", event=event, row=row,
                                     expected=block_width, actual=added)
                index += 1
                line = self.read()
                if line is None or index == nseq or _blank(line):
                    break
            if index != nseq:
                # This blank was already consumed by native GetLine before the
                # count test; it is not an unread suffix.
                event = self.event(line, "blank") if line is not None else None
                return self.fail("row_count_mismatch", event=event, expected=nseq, actual=index)
            blocks += 1
            width += block_width
            self.record["block_count"] = blocks
            self.record["column_count"] = width
            line = self.skip_blanks(line)
            if line is None:
                if width != declared:
                    return self.fail("column_count_mismatch", expected=declared, actual=width)
                return self.complete(width)
            if width >= declared:
                # Source puts the nonblank lookahead back, bypassing its EOF-only
                # final width check. Width disagreement still invalidates geometry.
                self.put_back(line)
                return self.complete(width)

    def sequential_read(self, line: NativeAlignmentLine) -> bool:
        nseq = self.record["declared_row_count"]
        declared = self.record["declared_column_count"]
        for index in range(nseq):
            length = 0
            while line is not None and length < declared:
                event = self.event(line, "sequence", row=index if length else None)
                if length == 0:
                    row = self.named_row(line, event, index)
                    if row is None:
                        return False
                else:
                    row = self.record["rows"][index]
                if not self.sequence(line, event, row, 10 if length == 0 else 0):
                    return False
                length = self.lengths[index]
                line = self.read()
            line = self.skip_blanks(line)
            if line is None:
                if index < nseq - 1:
                    return self.fail("row_count_mismatch", expected=nseq, actual=index + 1)
            elif length != declared:
                # On this error native has consumed, and does not put back, the
                # next nonblank line. Retain it without mislabelling it a row.
                event = self.event(line, "invalid")
                return self.fail("column_count_mismatch", event=event,
                                 row=self.record["rows"][index], expected=declared, actual=length)
        if line is not None:
            self.put_back(line)
        return self.complete(length)

    def complete(self, width: int) -> bool:
        self.record["column_count"] = width
        self.record["native_status_equivalent"] = 0
        declared = self.record["declared_column_count"]
        usable = width == declared and all(length == width for length in self.lengths)
        self.record["reader_state"] = "complete" if usable else "invalid"
        if not usable:
            self.diagnostic("column_count_mismatch", expected=declared, actual=width)
        return True

    def finish_rows(self) -> None:
        for row, length in zip(self.record["rows"], self.lengths):
            for segment in row["segments"]:
                raw = self.content[segment["byte_start"]:segment["byte_end"]]
                segment["source_text"] = _text(raw)
                if segment["operation"] == "copy":
                    segment["decoded_text"] = segment["source_text"]
                elif segment["operation"] == "symbol_alias":
                    segment["decoded_text"] = "".join(
                        "~" if symbol == 63 else "-" if symbol == 79 else
                        "X" if self.alphabet == "amino" else "N" for symbol in raw
                    )
            row["aligned_sequence"] = "".join(segment["decoded_text"] for segment in row["segments"])
            row["geometry_valid"] = (
                row["symbols_valid"] and length == self.record["declared_column_count"]
                and (self.record["column_count"] is None or length == self.record["column_count"])
            )

    def batch(self) -> dict:
        return {
            "version": "hmmer_native_alignment_decoding_v1",
            "format": self.format,
            "alphabet": self.alphabet,
            "records": self.records,
            "diagnostics": [],
            "end_state": self.end_state,
            "next_byte_offset": self.cursor,
            "trailing_range": {"byte_start": self.cursor, "byte_end": len(self.content)}
            if self.cursor < len(self.content) else None,
        }

    def decode(self) -> dict:
        while True:
            line = self.read()
            if line is None:
                break
            self.record = _new_record(len(self.records), line, self.sequential)
            self.lengths = []
            line = self.skip_blanks(line)
            if line is None:
                break  # Initial blank-only input has no native MSA occurrence.
            self.records.append(self.record)
            if not self.header(line):
                self.finish_rows()
                return self.batch()
            line = self.skip_blanks(self.read())
            if line is None:
                self.fail("row_count_mismatch", expected=self.record["declared_row_count"], actual=0)
                return self.batch()
            ok = self.sequential_read(line) if self.sequential else self.interleaved(line)
            self.finish_rows()
            if not ok:
                return self.batch()
        result = self.batch()
        if not self.records:
            result["diagnostics"].append(alignment_input_diagnostic(
                "empty_alignment", byte_start=0, byte_end=len(self.content), actual=0
            ))
        return result


def decode_native_phylip_alignment(
    content: bytes, *, declared_format: str, alphabet: str
) -> dict:
    """Decode all strict PHYLIP records without choosing a format or alphabet.

    Errors retain consumed Events and validated partial symbol spans. Source
    corners with unknown C-ctype or unsafe nonpositive dimensions remain
    unavailable. Native OK width anomalies retain invalid geometry without
    padding; later records cannot erase an earlier complete occurrence.
    """
    if not isinstance(content, bytes):
        raise ValueError("hmmer_alignment_content_invalid")
    if not isinstance(declared_format, str) or declared_format not in ("phylip", "phylips"):
        raise ValueError("hmmer_alignment_format_invalid")
    if not isinstance(alphabet, str) or alphabet not in ("amino", "DNA", "RNA"):
        raise ValueError("hmmer_alignment_alphabet_invalid")
    return _PhylipDecoder(content, declared_format, alphabet).decode()
