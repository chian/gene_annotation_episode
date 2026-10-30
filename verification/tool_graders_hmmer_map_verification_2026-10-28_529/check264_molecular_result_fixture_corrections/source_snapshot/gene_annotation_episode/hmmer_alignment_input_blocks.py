"""Pure digital Easel PSI-BLAST, SELEX and Clustal input decoding.

The three reader state machines follow the retained Infernal 1.1.5 Easel
sources.  SELEX physical expansion and PSI case-derived RF are input grammar;
this module supplies no alphabet inference, weights, scores or model map.
"""

from .hmmer_alignment_input_types import (
    NativeAlignmentLine,
    alignment_input_diagnostic,
    iter_native_alignment_lines,
)


_C_SPACE = b" \t\n\v\f\r"
# esl_memtok/esl_memspn call strchr, so its terminating NUL also matches.
_TOKEN_DELIMITERS = b" \t\x00"
_CONSENSUS_BYTES = b" .:*\x00"
_NUCLEIC_LETTERS = b"ACGTURYMKSWHBVDNXI"
_SELEX_TAGS = ("RF", "MM", "CS", "SS", "SA")


def _text(value: bytes) -> str:
    return value.decode("utf-8", "surrogateescape")


def _blank(data: bytes) -> bool:
    return all(value in _TOKEN_DELIMITERS for value in data)


def _token(data: bytes) -> tuple[int, int, int]:
    """The first esl_memtok token and its already delimiter-stripped tail."""
    start = 0
    while start < len(data) and data[start] in _TOKEN_DELIMITERS:
        start += 1
    end = start
    while end < len(data) and data[end] not in _TOKEN_DELIMITERS:
        end += 1
    tail = end
    while tail < len(data) and data[tail] in _TOKEN_DELIMITERS:
        tail += 1
    return start, end, tail


def _row(ordinal: int, name: bytes) -> dict:
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


class _DecodeStopped(Exception):
    """An already recorded malformed-input or unestablished-source outcome."""


class _BlockDecoder:
    def __init__(self, content: bytes, declared_format: str, alphabet: str):
        self.content = content
        self.format = declared_format
        self.alphabet = alphabet
        self.lines = iter_native_alignment_lines(content)
        self.lengths = {}
        self.pieces = {}
        self.last_item = None
        self.next_offset = 0
        self.active = False
        self.end_state = "eof"
        self.width = 0
        self.block = 0
        self.record = {
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
            "block_count": 0,
            "rows": [],
            "column_annotations": {},
            "events": [],
            "diagnostics": [],
        }

    def take(self) -> tuple[NativeAlignmentLine, dict] | None:
        line = next(self.lines, None)
        if line is None:
            self.next_offset = len(self.content)
            self.last_item = None
            return None
        event = {
            "event_ordinal": len(self.record["events"]),
            "kind": "invalid",
            "block_index": self.block,
            "row_ordinal": None,
            "tag": None,
            "raw": _text(self.content[line.byte_start : line.byte_end]),
            "value": None,
            "locator": {
                "line": line.number,
                "byte_start": line.byte_start,
                "byte_end": line.byte_end,
            },
        }
        self.record["events"].append(event)
        self.record["byte_end"] = line.byte_end
        self.record["line_end"] = line.number
        self.next_offset = line.byte_end
        self.last_item = (line, event)
        return self.last_item

    def stop(
        self, code: str, item=None, *, row=None, expected=None, actual=None,
        position=None, token_hex=None, unestablished=False, reset=False,
    ) -> None:
        line, event = item if item is not None else (None, None)
        if row is None and event is not None:
            ordinal = event["row_ordinal"]
            if ordinal is not None and ordinal < len(self.record["rows"]):
                row = self.record["rows"][ordinal]
        start = line.byte_start if line is not None else self.next_offset
        end = line.byte_end if line is not None else self.next_offset
        if position is not None:
            start = line.byte_start + position
            end = start + 1
        diagnostic = alignment_input_diagnostic(
            code, record_ordinal=0,
            row_ordinal=row["row_ordinal"] if row is not None else None,
            event_ordinal=event["event_ordinal"] if event is not None else None,
            byte_start=start, byte_end=end, expected=expected, actual=actual,
            token_hex=token_hex,
        )
        self.record["diagnostics"].append(diagnostic)
        if reset and line is not None:
            # selex_ErrorInBlock resets before the original LF/CRLF. The
            # collected Events still retain every inspected physical line.
            self.next_offset = line.content_end
        if row is not None:
            row["diagnostics"].append(diagnostic)
        self.record["native_status_equivalent"] = None if unestablished else 7
        self.record["reader_state"] = (
            "source_semantics_unestablished" if unestablished
            else "partial" if self.record["rows"] else "invalid"
        )
        self.end_state = "source_semantics_unestablished" if unestablished else "parse_error"
        raise _DecodeStopped

    def cspace(self, item, position: int) -> bool:
        line, _ = item
        value = line.data[position]
        if value >= 128:
            self.stop(
                "native_source_semantics_unestablished", item,
                actual="nonascii_ctype", position=position,
                token_hex=line.data[position : position + 1].hex(),
                unestablished=True,
            )
        return value in _C_SPACE

    def fields(self, item, *, entire_tail: bool) -> tuple[bytes, int, int]:
        """Shared literal C whitespace scans; framing stays reader-specific."""
        line, event = item
        size = len(line.data)
        position = 0
        while position < size and self.cspace(item, position):
            position += 1
        name_start = position
        if position >= size:
            self.stop("missing_name", item)
        position += 1
        while position < size and not self.cspace(item, position):
            position += 1
        name = line.data[name_start:position]
        position += 1
        while position < size and self.cspace(item, position):
            position += 1
        start = position
        if start >= size:
            self.stop("empty_sequence", item, expected=1, actual=0)
        if entire_tail:
            end = size
            while end > 1 and self.cspace(item, end - 1):
                end -= 1
        else:
            position += 1
            while position < size and not self.cspace(item, position):
                position += 1
            end = position
        event["kind"] = "sequence"
        event["value"] = _text(line.data[start:end])
        return name, start, end

    def bind_row(self, name: bytes, index: int, item) -> dict:
        _, event = item
        rows = self.record["rows"]
        if self.block == 0:
            # SetSeqName copies all bytes, but its native name is C-visible.
            # Subsequent memstrcmp still compares the whole current token.
            result = _row(index, name.partition(b"\x00")[0])
            rows.append(result)
        elif index >= len(rows):
            capacity = 16
            while capacity < len(rows):
                capacity *= 2
            if index >= capacity:
                self.stop(
                    "native_source_semantics_unestablished", item,
                    expected=capacity, actual="block_row_storage_overrun", unestablished=True,
                )
            self.stop("row_count_mismatch", item, expected=len(rows), actual=index + 1)
        else:
            result = rows[index]
            if name.hex() != result["name_bytes_hex"]:
                self.stop(
                    "row_order_mismatch", item, row=result,
                    expected=result["name"], actual=_text(name), token_hex=name.hex(),
                )
        event["row_ordinal"] = index
        self.record["header_valid"] = True
        return result

    def source_segment(self, row, item, start, end, operation, decoded=None) -> None:
        if start == end:
            return
        line, event = item
        source = line.data[start:end]
        ordinal = row["row_ordinal"]
        offset = self.lengths.get(ordinal, 0)
        if decoded is None:
            decoded = "" if operation == "ignore" else _text(source)
        segment = {
            "event_ordinal": event["event_ordinal"],
            "byte_start": line.byte_start + start,
            "byte_end": line.byte_start + end,
            "column_start": start,
            "column_end": end,
            "aligned_start": offset,
            "aligned_end": offset + len(decoded),
            "operation": operation,
            "basis": "input_ignored" if operation == "ignore" else "input_symbol",
            "source_text": _text(source),
            "decoded_text": decoded,
        }
        row["segments"].append(segment)
        self.lengths[ordinal] = offset + len(decoded)
        self.pieces.setdefault(ordinal, []).append(decoded)

    def gap(self, row, count: int) -> None:
        if count <= 0:
            return
        ordinal = row["row_ordinal"]
        offset = self.lengths.get(ordinal, 0)
        row["segments"].append({
            "event_ordinal": None,
            "byte_start": None, "byte_end": None,
            "column_start": None, "column_end": None,
            "aligned_start": offset, "aligned_end": offset + count,
            "operation": "native_gap", "basis": "selex_physical_columns",
            "source_text": "", "decoded_text": "-" * count,
        })
        self.lengths[ordinal] = offset + count
        self.pieces.setdefault(ordinal, []).append("-" * count)

    def sequence(self, row, item, start: int, end: int) -> None:
        """Append valid input spans; never substitute native error placeholders."""
        line, _ = item
        run = start
        for position in range(start, end):
            value = line.data[position]
            upper = value - 32 if 97 <= value <= 122 else value
            letter = 65 <= upper <= 90 if self.alphabet == "amino" else upper in _NUCLEIC_LETTERS
            allowed = letter or value in b"-._*~"
            if self.format == "psiblast" and value in b"._*~Oo":
                allowed = False
            alias = value == 0 or (self.format == "selex" and value == 32)
            if alias or not allowed:
                self.source_segment(row, item, run, position, "copy")
                if not alias:
                    row["symbols_valid"] = False
                    self.stop(
                        "invalid_sequence_byte", item, row=row, position=position,
                        token_hex=line.data[position : position + 1].hex(),
                        reset=self.format == "selex",
                    )
                decoded = "-" if value == 32 else "X" if self.alphabet == "amino" else "N"
                self.source_segment(row, item, position, position + 1, "symbol_alias", decoded)
                run = position + 1
        self.source_segment(row, item, run, end, "copy")

    def next_nonblank(self):
        while (item := self.take()) is not None:
            if not _blank(item[0].data):
                return item
            item[1]["kind"] = "blank"
            item[1]["block_index"] = None
        return None

    def psiblast(self) -> None:
        item = self.next_nonblank()
        if item is None:
            return
        self.active = True
        rf = {"text": "", "valid": False, "basis": "native_format_derivation", "fragments": []}
        self.record["column_annotations"]["RF"] = rf
        while item is not None:
            index = 0
            block_start = block_width = None
            block_rf = []
            while item is not None and not _blank(item[0].data):
                line, event = item
                name, start, end = self.fields(item, entire_tail=True)
                if index == 0:
                    block_start, block_width = start, end - start
                    block_rf = ["-"] * block_width
                elif start != block_start or end - start != block_width:
                    self.stop(
                        "block_geometry_mismatch", item,
                        expected=block_start if start != block_start else block_width,
                        actual=start if start != block_start else end - start,
                    )
                # Native derives RF before validating the name or digital row.
                for position in range(start, end):
                    value = line.data[position]
                    if value >= 128:
                        self.stop(
                            "native_source_semantics_unestablished", item,
                            actual="nonascii_ctype", position=position,
                            token_hex=line.data[position : position + 1].hex(), unestablished=True,
                        )
                    case = "x" if 65 <= value <= 90 else "." if 97 <= value <= 122 else None
                    if case is not None:
                        prior = block_rf[position - start]
                        if prior not in ("-", case):
                            self.stop(
                                "psiblast_case_conflict", item, position=position,
                                expected=prior, actual=case,
                                token_hex=line.data[position : position + 1].hex(),
                            )
                        block_rf[position - start] = case
                row = self.bind_row(name, index, item)
                self.source_segment(row, item, 0, start, "ignore")
                self.sequence(row, item, start, end)
                self.source_segment(row, item, end, len(line.data), "ignore")
                rf["fragments"].append(event)
                index += 1
                item = self.take()
            if item is not None:
                item[1]["kind"] = "blank"
                item[1]["block_index"] = None
            if index != len(self.record["rows"]):
                self.stop("row_count_mismatch", item, expected=len(self.record["rows"]), actual=index)
            self.width += block_width
            rf["text"] += "".join(block_rf)
            self.block += 1
            self.record["block_count"] = self.block
            item = self.next_nonblank()
        rf["valid"] = True

    def clustal(self) -> None:
        item = self.next_nonblank()
        if item is None:
            return
        self.active = True
        line, event = item
        event["kind"] = "header"
        event["block_index"] = None
        start, end, tail = _token(line.data)
        if (
            start == end
            or (self.format == "clustal" and not line.data[start:end].startswith(b"CLUSTAL"))
            or b"alignment" not in line.data[tail:]
        ):
            self.stop("invalid_header", item)
        self.record["header_valid"] = True
        item = self.next_nonblank()
        if item is None:
            self.stop("empty_alignment", expected=1, actual=0)
        while item is not None:
            index = 0
            block_start = block_width = None
            while True:
                line, event = item
                name, start, end = self.fields(item, entire_tail=False)
                if index == 0:
                    block_start, block_width = start, end - start
                elif start != block_start or end - start != block_width:
                    self.stop(
                        "block_geometry_mismatch", item,
                        expected=block_start if start != block_start else block_width,
                        actual=start if start != block_start else end - start,
                    )
                row = self.bind_row(name, index, item)
                self.source_segment(row, item, 0, start, "ignore")
                self.sequence(row, item, start, end)
                self.source_segment(row, item, end, len(line.data), "ignore")
                item = self.take()
                if item is None:
                    self.stop("missing_consensus_line", expected=1, actual=0)
                index += 1
                if all(value in _CONSENSUS_BYTES for value in item[0].data):
                    item[1]["kind"] = "consensus"
                    item[1]["value"] = _text(item[0].data)
                    break
            if index != len(self.record["rows"]):
                self.stop("row_count_mismatch", item, expected=len(self.record["rows"]), actual=index)
            self.width += block_width
            self.block += 1
            self.record["block_count"] = self.block
            item = self.next_nonblank()

    @staticmethod
    def selex_tag(data: bytes) -> str | None:
        for tag in _SELEX_TAGS:
            if data.startswith(b"#=" + tag.encode("ascii")):
                return tag
        return None

    def selex_block(self):
        retained = []
        while (item := self.take()) is not None:
            line, event = item
            if line.data.startswith(b"#") and not line.data.startswith(b"#="):
                event["kind"] = "comment"
                event["block_index"] = None
                continue
            if _blank(line.data):
                event["kind"] = "blank"
                event["block_index"] = None
                if retained:
                    break
                continue
            self.active = True
            retained.append(item)
        return retained

    def selex(self) -> None:
        template = None
        while (items := self.selex_block()):
            if template is not None and len(items) != len(template):
                # read_block detects cardinality only after reading the whole block.
                self.stop("row_count_mismatch", self.last_item, expected=len(template), actual=len(items))
            tags = [self.selex_tag(line.data) for line, _ in items]
            if template is None:
                seen_global = {"RF": 0, "CS": 0}
                seen_row = {"SS": 0, "SA": 0}
                sequence_count = 0
                for item, tag in zip(items, tags):
                    event = item[1]
                    event["kind"] = "sequence" if tag is None else "annotation"
                    event["tag"] = tag
                    if tag is None:
                        sequence_count += 1
                        seen_row = {"SS": 0, "SA": 0}
                    elif tag in seen_row:
                        seen_row[tag] += 1
                        if sequence_count == 0:
                            self.stop("annotation_order_mismatch", item, expected="sequence", actual=tag, reset=True)
                        if seen_row[tag] > 1:
                            self.stop("annotation_cardinality_mismatch", item, expected=1, actual=seen_row[tag], reset=True)
                    elif tag in seen_global:
                        seen_global[tag] += 1
                        if seen_global[tag] > 1:
                            self.stop("annotation_cardinality_mismatch", item, expected=1, actual=seen_global[tag], reset=True)
                if sequence_count == 0:
                    self.stop(
                        "native_source_semantics_unestablished", items[0],
                        actual="selex_no_sequence_rows", unestablished=True,
                    )
                template = tags
            else:
                for item, tag, expected in zip(items, tags, template):
                    item[1]["kind"] = "sequence" if tag is None else "annotation"
                    item[1]["tag"] = tag
                    if tag != expected:
                        self.stop(
                            "annotation_order_mismatch", item,
                            expected=expected or "sequence", actual=tag or "sequence", reset=True,
                        )
            entries = []
            seqi = 0
            for item, tag in zip(items, tags):
                line, event = item
                start, end, tail = _token(line.data)
                name = line.data[start:end]
                if tag is None:
                    if self.block == 0:
                        row = _row(seqi, name)
                        self.record["rows"].append(row)
                    else:
                        row = self.record["rows"][seqi]
                        if name.hex() != row["name_bytes_hex"]:
                            self.stop(
                                "row_order_mismatch", item, row=row,
                                expected=row["name"], actual=_text(name), token_hex=name.hex(), reset=True,
                            )
                    event["row_ordinal"] = seqi
                    seqi += 1
                elif tag in ("SS", "SA"):
                    event["row_ordinal"] = seqi - 1
                left = tail if tail < len(line.data) else -1
                event["value"] = _text(line.data[tail:])
                entries.append((item, tag, left))
            self.record["header_valid"] = True
            # Native computes every right edge before appending any row.
            bounds = []
            for item, tag, left in entries:
                position = len(item[0].data) - 1
                while position >= 0 and self.cspace(item, position):
                    position -= 1
                right = -1 if position < left else position
                bounds.append((item, tag, left, right))
            leftmost = bounds[0][2]
            rightmost = bounds[0][3]
            for _, _, left, right in bounds[1:]:
                if left != -1:
                    leftmost = min(leftmost, left)
                if right != -1:
                    rightmost = max(rightmost, right)
            if rightmost == -1:
                self.block += 1
                self.record["block_count"] = self.block
                continue
            if leftmost == -1:
                self.stop(
                    "native_source_semantics_unestablished", items[0],
                    expected=0, actual="selex_first_data_missing", unestablished=True,
                )
            added = rightmost - leftmost + 1
            # Repeated MM lines overwrite this same block interval natively.
            block_annotations = {}
            for item, tag, left, right in bounds:
                line, event = item
                nleft = left - leftmost if left != -1 else added
                ntext = right - left + 1 if left != -1 else 0
                if ntext < 0:
                    self.stop(
                        "native_source_semantics_unestablished", item,
                        expected=0, actual="selex_negative_data_width", unestablished=True,
                    )
                if tag is None:
                    row = self.record["rows"][event["row_ordinal"]]
                    self.source_segment(row, item, 0, left if left >= 0 else len(line.data), "ignore")
                    self.gap(row, nleft)
                    if ntext:
                        self.sequence(row, item, left, right + 1)
                    self.gap(row, added - nleft - ntext)
                    if left >= 0:
                        self.source_segment(row, item, right + 1, len(line.data), "ignore")
                else:
                    ordinal = event["row_ordinal"]
                    key = (ordinal, "SS_cons" if tag == "CS" else tag)
                    text = "." * nleft + (_text(line.data[left:right + 1]) if ntext else "")
                    text += "." * (added - nleft - ntext)
                    unsupported = next(
                        (position for position in range(left, right + 1)
                         if line.data[position] == 0 or line.data[position] >= 128),
                        None,
                    ) if ntext else None
                    limitation = (item, unsupported) if unsupported is not None else None
                    annotations = (
                        self.record["column_annotations"] if ordinal is None
                        else self.record["rows"][ordinal]["column_annotations"]
                    )
                    output_tag = key[1]
                    if output_tag not in annotations:
                        annotations[output_tag] = {
                            "text": "", "valid": True, "basis": "native_input", "fragments": [],
                        }
                    annotation = annotations[output_tag]
                    if key not in block_annotations:
                        block_annotations[key] = [annotation["text"], annotation["valid"], limitation]
                    else:
                        block_annotations[key][2] = limitation
                    prefix, prior_valid, _ = block_annotations[key]
                    # Commit in source append order so a later failed sequence
                    # does not erase an earlier parsed annotation contribution.
                    annotation["text"] = prefix + text
                    annotation["valid"] = prior_valid and limitation is None
                    annotation["fragments"].append(event)
                    if ordinal is not None:
                        self.record["rows"][ordinal]["annotation_fragments"].append(event)
            for (ordinal, tag), (_, _, limitation) in block_annotations.items():
                if limitation is not None:
                    item, position = limitation
                    line, event = item
                    diagnostic = alignment_input_diagnostic(
                        "native_source_semantics_unestablished", record_ordinal=0,
                        row_ordinal=ordinal, event_ordinal=event["event_ordinal"],
                        byte_start=line.byte_start + position,
                        byte_end=line.byte_start + position + 1,
                        actual="annotation_byte_interpretation",
                        token_hex=line.data[position:position + 1].hex(),
                    )
                    self.record["diagnostics"].append(diagnostic)
                    if ordinal is not None:
                        self.record["rows"][ordinal]["diagnostics"].append(diagnostic)
            self.width += added
            self.block += 1
            self.record["block_count"] = self.block

    def result(self) -> dict:
        diagnostics = []
        for row in self.record["rows"]:
            if self.end_state == "source_semantics_unestablished" and not row["segments"]:
                row["aligned_sequence"] = None
                row["symbols_valid"] = False
            else:
                row["aligned_sequence"] = "".join(self.pieces.get(row["row_ordinal"], []))
        if not self.active:
            records = []
            diagnostics.append(alignment_input_diagnostic(
                "empty_alignment", byte_start=0, byte_end=len(self.content), actual=0,
            ))
        else:
            records = [self.record]
            if self.end_state == "eof":
                self.record["native_status_equivalent"] = 0
                self.record["column_count"] = self.width
                if self.width > 0 and self.record["rows"]:
                    for row in self.record["rows"]:
                        row["geometry_valid"] = len(row["aligned_sequence"]) == self.width
                    self.record["reader_state"] = (
                        "complete" if all(row["geometry_valid"] for row in self.record["rows"])
                        else "invalid"
                    )
                else:
                    self.record["reader_state"] = "invalid"
                    self.record["diagnostics"].append(alignment_input_diagnostic(
                        "empty_alignment", record_ordinal=0,
                        byte_start=0, byte_end=self.next_offset, actual=0,
                    ))
            else:
                for row in self.record["rows"]:
                    row["geometry_valid"] = False
                for annotation in self.record["column_annotations"].values():
                    annotation["valid"] = False
                for row in self.record["rows"]:
                    for annotation in row["column_annotations"].values():
                        annotation["valid"] = False
        return {
            "version": "hmmer_native_alignment_decoding_v1",
            "format": self.format,
            "alphabet": self.alphabet,
            "records": records,
            "diagnostics": diagnostics,
            "end_state": self.end_state,
            "next_byte_offset": self.next_offset,
            "trailing_range": (
                {"byte_start": self.next_offset, "byte_end": len(self.content)}
                if self.next_offset < len(self.content) else None
            ),
        }


def decode_native_block_alignment(content: bytes, *, declared_format: str, alphabet: str) -> dict:
    """Decode one whole-file alignment using an explicitly supplied alphabet.

    Input/format/alphabet argument misuse raises the shared ValueError code.
    Malformed source bytes instead retain partial data and closed diagnostics.
    """
    if not isinstance(content, bytes):
        raise ValueError("hmmer_alignment_content_invalid")
    if not isinstance(declared_format, str) or declared_format not in ("psiblast", "selex", "clustal", "clustallike"):
        raise ValueError("hmmer_alignment_format_invalid")
    if not isinstance(alphabet, str) or alphabet not in ("amino", "DNA", "RNA"):
        raise ValueError("hmmer_alignment_alphabet_invalid")
    decoder = _BlockDecoder(content, declared_format, alphabet)
    try:
        if declared_format == "psiblast":
            decoder.psiblast()
        elif declared_format == "selex":
            decoder.selex()
        else:
            decoder.clustal()
    except _DecodeStopped:
        pass
    return decoder.result()
