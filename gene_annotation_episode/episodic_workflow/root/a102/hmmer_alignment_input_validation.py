"""Closed validation of retained HMMER alignment input facts.

These checks do not decode, acquire, calculate scientific components or repair
saved records.  Initial validation can compare retained spans with supplied
bytes.  Saved validation checks internal consistency and original occurrence
joins; a histogram and a hash cannot prove unretained scanner input.  Local
checks deliberately have no invented occurrence, file size or custody claim.
"""

from functools import wraps
import re

from .hmmer_alignment_input_alphabet import classify_easel_alphabet_counts
from .hmmer_alignment_input_types import (
    alignment_input_diagnostic,
    iter_native_alignment_lines,
)


_FORMATS = frozenset({"stockholm", "pfam", "afa", "a2m", "psiblast", "selex",
                      "clustal", "clustallike", "phylip", "phylips"})
_NATIVE_FORMATS = _FORMATS - {"stockholm", "pfam"}
_PHYLIP = frozenset({"phylip", "phylips"})
_ALPHABETS = frozenset({"amino", "DNA", "RNA"})
_INT_MAX = 2147483647
_INT64_MAX = 9223372036854775807
_PROFILE = "infernal_1_1_5_easel_alignment_input_v1"
_CONTEXT = frozenset({"version", "reader_profile", "source_occurrence_id", "source_sha256",
    "format", "alphabet_basis", "explicit_alphabet", "effective_alphabet", "alphabet_probe",
    "reader_state", "first_record_end_byte", "file_end_state"})
_SOURCE = frozenset({"version", "source_occurrence_id", "source_sha256", "alphabet", "alphabet_basis"})
_PROBE = frozenset({"version", "format", "state", "alphabet", "counts_az", "counted_letters",
                   "checkpoints", "scan_end_byte", "stopped_at", "diagnostics"})
_CHECKPOINT = frozenset({"threshold", "at_eof", "line", "byte_end", "counts_az", "state", "alphabet", "rule"})
_BATCH = frozenset({"version", "format", "alphabet", "records", "diagnostics", "end_state",
                   "next_byte_offset", "trailing_range"})
_NATIVE_RECORD = frozenset({"record_ordinal", "reader_state", "native_status_equivalent",
    "byte_start", "byte_end", "line_start", "line_end", "header_valid", "column_count",
    "declared_row_count", "declared_column_count", "block_count", "rows",
    "column_annotations", "events", "diagnostics"})
_ROW = frozenset({"row_ordinal", "name", "name_bytes_hex", "description", "aligned_sequence",
    "segments", "annotation_fragments", "column_annotations", "geometry_valid", "symbols_valid",
    "identity_unambiguous", "diagnostics"})
_EVENT = frozenset({"event_ordinal", "kind", "block_index", "row_ordinal", "tag", "raw", "value", "locator"})
_SEGMENT = frozenset({"event_ordinal", "byte_start", "byte_end", "column_start", "column_end",
    "aligned_start", "aligned_end", "operation", "basis", "source_text", "decoded_text"})
_DIAGNOSTIC = frozenset({"code", "record_ordinal", "row_ordinal", "event_ordinal", "byte_start", "byte_end", "details"})
_OCCURRENCE = frozenset({"occurrence_id", "direction", "role", "ordinal", "artifact_ref", "sha256", "size_bytes", "completeness"})
_LOCATOR = frozenset({"artifact_ref", "record_ordinal", "byte_start", "byte_end", "line_start", "line_end"})
_OPTIONAL = frozenset({"input_decoding", "source_alphabet", "native_input", "native_decoding", "alphabet_probe"})


def _boolean(function):
    """Malformed JSON-like operands fail closed at every public boundary."""
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return bool(function(*args, **kwargs))
        except (TypeError, ValueError, KeyError, IndexError, AttributeError,
                OverflowError, UnicodeError, RecursionError):
            return False
    return checked


def _object(value, keys):
    return type(value) is dict and value.keys() == keys


def _integer(value, minimum=0, maximum=None):
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def _text(value):
    return type(value) is str and bool(value)


def _hex(value, *, digest=False):
    return (type(value) is str and (not digest or len(value) == 64)
            and len(value) % 2 == 0 and re.fullmatch("[0-9a-f]*", value) is not None)


def _bytes(value):
    if type(value) is not str:
        raise ValueError("text_required")
    return value.encode("utf-8", "surrogateescape")


def _span(start, end, size=None, *, minimum=0):
    return (_integer(start, minimum) and _integer(end, start)
            and (size is None or end <= size))


def _histogram(value):
    return type(value) is list and len(value) == 26 and all(_integer(x) for x in value)


def _diagnostic_shape(value):
    if not _object(value, _DIAGNOSTIC) or not _object(value["details"], {"expected", "actual", "token_hex"}):
        return False
    details = value["details"]
    return value == alignment_input_diagnostic(
        value["code"], record_ordinal=value["record_ordinal"], row_ordinal=value["row_ordinal"],
        event_ordinal=value["event_ordinal"], byte_start=value["byte_start"], byte_end=value["byte_end"],
        expected=details["expected"], actual=details["actual"], token_hex=details["token_hex"],
    )


def _diagnostic(value, *, size=None, records=None, record=None, row=None, content=None):
    if not _diagnostic_shape(value):
        return False
    start, end = value["byte_start"], value["byte_end"]
    if (start is None) != (end is None) or start is not None and not _span(start, end, size):
        return False
    ordinal = value["record_ordinal"]
    if record is None and ordinal is not None:
        if records is None or ordinal >= len(records):
            return False
        record = records[ordinal]
    if record is not None and ordinal != record["record_ordinal"]:
        return False
    ri, ei = value["row_ordinal"], value["event_ordinal"]
    if ri is not None and (record is None or ri >= len(record["rows"])):
        return False
    if row is not None and ri != row["row_ordinal"]:
        return False
    events = record["events"] if record is not None else []
    if ei is not None and (ei >= len(events) or record is None):
        return False
    raw = None
    if start is not None:
        if content is not None:
            raw = content[start:end]
        if ei is not None:
            event = events[ei]
            loc = event["locator"]
            if not loc["byte_start"] <= start <= end <= loc["byte_end"]:
                return False
            raw = _bytes(event["raw"])[start - loc["byte_start"]:end - loc["byte_start"]]
        elif raw is None:
            for event in events:
                loc = event["locator"]
                if loc["byte_start"] <= start <= end <= loc["byte_end"]:
                    raw = _bytes(event["raw"])[start - loc["byte_start"]:end - loc["byte_start"]]
                    break
    token = value["details"]["token_hex"]
    # Some native name diagnostics locate a whole line, not just the token.
    if token is not None and raw is not None and bytes.fromhex(token) not in raw:
        return False
    return True


@_boolean
def alphabet_probe_valid(probe: dict, *, declared_format: str,
                         source_size_bytes: int | None = None) -> bool:
    """Validate scanner history with the single retained Easel classifier."""
    if (declared_format not in _FORMATS or not _object(probe, _PROBE)
            or probe["version"] != "hmmer_native_alignment_alphabet_probe_v1"
            or probe["format"] != declared_format
            or source_size_bytes is not None and not _integer(source_size_bytes)
            or not _histogram(probe["counts_az"]) or not _integer(probe["counted_letters"])
            or probe["counted_letters"] != sum(probe["counts_az"])
            or not _integer(probe["scan_end_byte"], probe["counted_letters"])
            or source_size_bytes is not None and probe["scan_end_byte"] > source_size_bytes
            or type(probe["checkpoints"]) is not list or type(probe["diagnostics"]) is not list):
        return False
    checkpoints, final = probe["checkpoints"], probe["counts_az"]
    end = probe["scan_end_byte"]
    bound = _INT64_MAX if declared_format in _PHYLIP else _INT_MAX
    previous = None
    threshold_index = 0
    for index, item in enumerate(checkpoints):
        if (not _object(item, _CHECKPOINT) or type(item["at_eof"]) is not bool
                or not _histogram(item["counts_az"]) or not _integer(item["byte_end"], sum(item["counts_az"]))
                or item["byte_end"] > end or any(a > b for a, b in zip(item["counts_az"], final))
                or sum(item["counts_az"]) > bound):
            return False
        classified = classify_easel_alphabet_counts(item["counts_az"])
        if (item["state"] != classified["status"] or item["alphabet"] != classified["alphabet"]
                or item["rule"] != classified["rule"]):
            return False
        line = item["line"]
        if line is not None and not _integer(line, 1, item["byte_end"]):
            return False
        if (line is None) != (item["byte_end"] == 0):
            return False
        if item["at_eof"]:
            if (item["threshold"] is not None or index != len(checkpoints) - 1
                    or item["byte_end"] != end
                    or source_size_bytes is not None and end != source_size_bytes):
                return False
        else:
            if (threshold_index >= 3 or type(item["threshold"]) is not int
                    or item["threshold"] != (500, 5000, 50000)[threshold_index]
                    or sum(item["counts_az"]) <= item["threshold"] or line is None):
                return False
            threshold_index += 1
        if previous is not None:
            if previous["state"] != "undetermined" or previous["at_eof"]:
                return False
            if any(a > b for a, b in zip(previous["counts_az"], item["counts_az"])):
                return False
            repeat = (item["at_eof"] and line == previous["line"]
                      and item["byte_end"] == previous["byte_end"]
                      and item["counts_az"] == previous["counts_az"])
            if not repeat and (line <= previous["line"] or item["byte_end"] <= previous["byte_end"]):
                return False
        previous = item
    diagnostics = probe["diagnostics"]
    if not all(_diagnostic(d, size=source_size_bytes) and
               all(d[k] is None for k in ("record_ordinal", "row_ordinal", "event_ordinal"))
               for d in diagnostics):
        return False
    stop = probe["stopped_at"]
    if stop in {"checkpoint", "eof"}:
        if diagnostics or probe["state"] not in {"determined", "undetermined"}:
            return False
        if stop == "eof" and source_size_bytes is not None and end != source_size_bytes:
            return False
        if not checkpoints:
            return (stop == "eof" and declared_format in {"clustal", "clustallike", "phylip", "phylips"}
                    and not any(final) and probe["state"] == "undetermined" and probe["alphabet"] is None)
        last = checkpoints[-1]
        return (last["counts_az"] == final and last["byte_end"] == end
                and last["state"] == probe["state"] and last["alphabet"] == probe["alphabet"]
                and (last["at_eof"] if stop == "eof" else
                     not last["at_eof"] and last["state"] == "determined"))
    if (stop not in {"unestablished_byte_semantics", "unestablished_count_semantics"}
            or probe["state"] != "source_semantics_unestablished" or probe["alphabet"] is not None
            or len(diagnostics) != 1 or diagnostics[0]["code"] != "native_source_semantics_unestablished"):
        return False
    diagnostic = diagnostics[0]
    details = diagnostic["details"]
    if stop == "unestablished_byte_semantics":
        start = diagnostic["byte_start"]
        return (all(c["state"] == "undetermined" and not c["at_eof"] for c in checkpoints)
                and _integer(start) and diagnostic["byte_end"] == start + 1 <= end
                and (not checkpoints or start >= checkpoints[-1]["byte_end"])
                and details["expected"] == "ascii_ctype" and _integer(details["actual"], 128, 255)
                and details["token_hex"] == bytes((details["actual"],)).hex())
    if probe["counted_letters"] > bound:
        return (all(c["state"] == "undetermined" and not c["at_eof"] for c in checkpoints)
                and _span(diagnostic["byte_start"], diagnostic["byte_end"], end)
                and diagnostic["byte_start"] < diagnostic["byte_end"] == end
                and (not checkpoints or diagnostic["byte_start"] >= checkpoints[-1]["byte_end"])
                and details == {"expected": bound, "actual": probe["counted_letters"], "token_hex": None})
    if (not checkpoints or checkpoints[-1]["state"] != "source_semantics_unestablished"
            or checkpoints[-1]["counts_az"] != final or checkpoints[-1]["byte_end"] != end
            or diagnostic["byte_start"] is not None or diagnostic["byte_end"] is not None):
        return False
    # This selects the diagnostic's first exceeded native domain, not an
    # alternative alphabet classifier. N/T/U/X/B are not narrowed by Easel.
    for letter in "EFIJLOPQZACGDHKMRSVWY":
        count = final[ord(letter) - 65]
        if count > _INT_MAX:
            return details == {"expected": _INT_MAX, "actual": count, "token_hex": letter.encode("ascii").hex()}
    return False


def _envelope(value, *, size=None):
    if (not _object(value, _BATCH - {"records"})
            or value["version"] != "hmmer_native_alignment_decoding_v1"
            or value["format"] not in _NATIVE_FORMATS or value["alphabet"] not in _ALPHABETS
            or value["end_state"] not in {"eof", "parse_error", "source_semantics_unestablished"}
            or not _integer(value["next_byte_offset"]) or type(value["diagnostics"]) is not list
            or not all(_diagnostic_shape(d) for d in value["diagnostics"])):
        return False
    cursor, trailing = value["next_byte_offset"], value["trailing_range"]
    if trailing is not None and (not _object(trailing, {"byte_start", "byte_end"})
            or trailing["byte_start"] != cursor or not _integer(trailing["byte_start"])
            or not _integer(trailing["byte_end"], cursor + 1)):
        return False
    if value["end_state"] == "eof" and trailing is not None:
        return False
    if size is not None:
        return (cursor <= size and (value["end_state"] != "eof" or cursor == size)
                and trailing == ({"byte_start": cursor, "byte_end": size} if cursor < size else None))
    return True


def _events(record, fmt, *, size=None, lines=None):
    events, rows = record["events"], record["rows"]
    if type(events) is not list or not events:
        return False
    previous = None
    for index, event in enumerate(events):
        if (not _object(event, _EVENT) or not _integer(event["event_ordinal"])
                or event["event_ordinal"] != index
                or event["kind"] not in {"header", "dimensions", "sequence", "annotation", "consensus", "blank", "comment", "invalid"}
                or event["value"] is not None and type(event["value"]) is not str
                or not _object(event["locator"], {"line", "byte_start", "byte_end"})):
            return False
        loc, raw = event["locator"], _bytes(event["raw"])
        if (not _integer(loc["line"], 1) or not _span(loc["byte_start"], loc["byte_end"], size)
                or not record["byte_start"] <= loc["byte_start"] < loc["byte_end"] <= record["byte_end"]
                or len(raw) != loc["byte_end"] - loc["byte_start"]):
            return False
        payload = raw[:-2] if raw.endswith(b"\r\n") else raw[:-1] if raw.endswith(b"\n") else raw
        if b"\n" in payload or size is not None and loc["byte_end"] < size and not raw.endswith(b"\n"):
            return False
        if event["value"] is not None and _bytes(event["value"]) not in payload:
            return False
        if previous is not None and (loc["byte_start"] != previous["byte_end"] or loc["line"] != previous["line"] + 1):
            return False
        if lines is not None:
            original = lines.get(loc["byte_start"])
            if original is None or original != (loc["line"], loc["byte_end"], raw):
                return False
        previous = loc
        ri, bi = event["row_ordinal"], event["block_index"]
        if ri is not None and (not _integer(ri) or ri >= len(rows)):
            return False
        if bi is not None and (not _integer(bi) or record["block_count"] is None or bi > record["block_count"]):
            return False
        if event["tag"] is not None:
            if fmt != "selex" or event["kind"] != "annotation" or event["tag"] not in {"RF", "MM", "CS", "SS", "SA"}:
                return False
            if event["tag"] in {"RF", "MM", "CS"} and ri is not None:
                return False
        elif event["kind"] == "annotation":
            return False
    return (events[0]["locator"]["byte_start"] == record["byte_start"]
            and events[0]["locator"]["line"] == record["line_start"]
            and events[-1]["locator"]["byte_end"] == record["byte_end"]
            and events[-1]["locator"]["line"] == record["line_end"])


def _fragments(fragments, events, *, row=None, kinds=None, tag=None):
    if type(fragments) is not list:
        return False
    previous = -1
    for event in fragments:
        if type(event) is not dict or not _integer(event.get("event_ordinal")):
            return False
        index = event["event_ordinal"]
        if index <= previous or index >= len(events) or event != events[index]:
            return False
        if row is not None and event["row_ordinal"] != row:
            return False
        if kinds is not None and event["kind"] not in kinds or tag is not None and event["tag"] != tag:
            return False
        previous = index
    return True


def _annotations(annotations, record, fmt, *, row=None):
    if type(annotations) is not dict:
        return False
    allowed = {"SS", "SA"} if row is not None and fmt == "selex" else (
        {"RF", "MM", "SS_cons"} if fmt == "selex" else {"RF"} if fmt in {"a2m", "psiblast"} and row is None else set())
    if annotations.keys() - allowed:
        return False
    for tag, item in annotations.items():
        if (not _object(item, {"text", "valid", "basis", "fragments"}) or type(item["valid"]) is not bool
                or item["basis"] != ("native_input" if fmt == "selex" else "native_format_derivation")):
            return False
        raw = _bytes(item["text"])
        if item["valid"] and (any(b == 0 or b >= 128 for b in raw) or len(raw) != record["column_count"]):
            return False
        if record["reader_state"] == "complete" and len(raw) != record["column_count"]:
            return False
        if not _fragments(item["fragments"], record["events"], row=row,
                kinds={"annotation"} if fmt == "selex" else {"sequence"},
                tag="CS" if tag == "SS_cons" else tag if fmt == "selex" else None):
            return False
        if fmt == "a2m" and item["fragments"] or fmt == "selex" and not item["fragments"]:
            return False
        if fmt == "selex" and row is None and any(e["row_ordinal"] is not None for e in item["fragments"]):
            return False
        if record["reader_state"] == "complete" and not item["valid"]:
            indices = {e["event_ordinal"] for e in item["fragments"]}
            if not any(d["code"] == "native_source_semantics_unestablished"
                       and d["details"]["actual"] == "annotation_byte_interpretation"
                       and d["event_ordinal"] in indices for d in record["diagnostics"]):
                return False
    return True


def _segments(row, record, fmt, alphabet):
    if type(row["segments"]) is not list:
        return False
    sequence = row["aligned_sequence"]
    if sequence is None:
        return not row["geometry_valid"] and not row["segments"]
    if type(sequence) is not str or not sequence.isascii():
        return False
    position, previous_byte, pieces = 0, -1, []
    for segment in row["segments"]:
        if (not _object(segment, _SEGMENT) or not _integer(segment["aligned_start"])
                or segment["aligned_start"] != position or not _integer(segment["aligned_end"], position)
                or type(segment["decoded_text"]) is not str or not segment["decoded_text"].isascii()
                or segment["aligned_end"] - position != len(segment["decoded_text"])):
            return False
        decoded, operation = segment["decoded_text"], segment["operation"]
        source = _bytes(segment["source_text"])
        if operation == "native_gap":
            expected = {"a2m": "a2m_insert_slot", "selex": "selex_physical_columns"}.get(fmt)
            if (expected is None or segment["basis"] != expected or source or not decoded or set(decoded) != {"-"}
                    or any(segment[k] is not None for k in ("event_ordinal", "byte_start", "byte_end", "column_start", "column_end"))):
                return False
        else:
            ei = segment["event_ordinal"]
            if not _integer(ei) or ei >= len(record["events"]):
                return False
            event = record["events"][ei]
            loc, raw = event["locator"], _bytes(event["raw"])
            payload = raw[:-2] if raw.endswith(b"\r\n") else raw[:-1] if raw.endswith(b"\n") else raw
            start, end = segment["byte_start"], segment["byte_end"]
            if (event["row_ordinal"] != row["row_ordinal"] or event["kind"] not in {"sequence", "blank"}
                    or not _span(start, end) or start == end or start < previous_byte
                    or not loc["byte_start"] <= start < end <= loc["byte_start"] + len(payload)
                    or not _span(segment["column_start"], segment["column_end"])
                    or segment["column_start"] != start - loc["byte_start"]
                    or segment["column_end"] != end - loc["byte_start"]
                    or source != payload[start - loc["byte_start"]:end - loc["byte_start"]]):
                return False
            previous_byte = end
            if operation == "ignore":
                if segment["basis"] != "input_ignored" or decoded:
                    return False
            elif operation == "copy":
                if segment["basis"] != "input_symbol" or source != decoded.encode("ascii"):
                    return False
                letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if alphabet == "amino" else "ACGTURYMKSWHBVDNXI"
                symbols = "-" if fmt == "a2m" else "-.*" if fmt in _PHYLIP else "-._*~"
                allowed = set(letters + letters.lower() + symbols)
                if fmt in {"a2m", "psiblast"}:
                    allowed -= set("Oo")
                if fmt == "psiblast":
                    allowed -= set("._*~")
                if any(c not in allowed for c in decoded):
                    return False
            elif operation == "symbol_alias":
                aliases = {0: "X" if alphabet == "amino" else "N"}
                if fmt in _PHYLIP:
                    aliases[63] = "~"
                    if alphabet != "amino":
                        aliases[79] = "-"
                if fmt == "selex":
                    aliases[32] = "-"
                if (fmt == "a2m" or segment["basis"] != "input_symbol"
                        or any(b not in aliases for b in source)
                        or decoded != "".join(aliases[b] for b in source)):
                    return False
            else:
                return False
        pieces.append(decoded)
        position = segment["aligned_end"]
    return "".join(pieces) == sequence


def _native_record(record, fmt, alphabet, *, size=None, lines=None, content=None):
    if (not _object(record, _NATIVE_RECORD) or not _integer(record["record_ordinal"])
            or record["reader_state"] not in {"complete", "partial", "invalid", "source_semantics_unestablished"}
            or record["native_status_equivalent"] is not None and
               (type(record["native_status_equivalent"]) is not int or record["native_status_equivalent"] not in {0, 3, 7})
            or not _span(record["byte_start"], record["byte_end"], size)
            or not _span(record["line_start"], record["line_end"], minimum=1)
            or type(record["header_valid"]) is not bool or type(record["rows"]) is not list
            or type(record["diagnostics"]) is not list):
        return False
    for key in ("column_count", "declared_row_count", "declared_column_count", "block_count"):
        value = record[key]
        if value is not None and not _integer(value, -2147483648 if key.startswith("declared_") else 0,
                                             _INT_MAX if key.startswith("declared_") else None):
            return False
    if fmt not in _PHYLIP and any(record[k] is not None for k in ("declared_row_count", "declared_column_count")):
        return False
    if (fmt in {"afa", "a2m", "phylips"}) != (record["block_count"] is None):
        return False
    if not _events(record, fmt, size=size, lines=lines):
        return False
    for index, row in enumerate(record["rows"]):
        if (not _object(row, _ROW) or not _integer(row["row_ordinal"]) or row["row_ordinal"] != index
                or type(row["name"]) is not str or not _hex(row["name_bytes_hex"])
                or _bytes(row["name"]).hex() != row["name_bytes_hex"]
                or row["description"] is not None and type(row["description"]) is not str
                or any(type(row[flag]) is not bool for flag in ("geometry_valid", "symbols_valid", "identity_unambiguous"))
                or type(row["diagnostics"]) is not list
                or not _segments(row, record, fmt, alphabet)
                or not _fragments(row["annotation_fragments"], record["events"], row=index, kinds={"annotation"})
                or not _annotations(row["column_annotations"], record, fmt, row=index)):
            return False
        if row["geometry_valid"]:
            width = record["column_count"] if record["column_count"] is not None else record["declared_column_count"]
            if (row["aligned_sequence"] is None or width is not None and len(row["aligned_sequence"]) != width
                    or fmt in _PHYLIP and len(row["aligned_sequence"]) != record["declared_column_count"]):
                return False
        if any(d not in record["diagnostics"] or not _diagnostic(d, size=size, record=record, row=row, content=content)
               for d in row["diagnostics"]):
            return False
    if not _annotations(record["column_annotations"], record, fmt):
        return False
    if not all(_diagnostic(d, size=size, record=record, content=content) for d in record["diagnostics"]):
        return False
    state, status = record["reader_state"], record["native_status_equivalent"]
    if state == "complete":
        if (status != 0 or not record["header_valid"] or not _integer(record["column_count"], 1)
                or not record["rows"] or not all(r["geometry_valid"] and r["symbols_valid"] and r["identity_unambiguous"] for r in record["rows"])
                or fmt in _PHYLIP and (len(record["rows"]) != record["declared_row_count"]
                                      or record["column_count"] != record["declared_column_count"])):
            return False
        if any(d["code"] != "native_source_semantics_unestablished"
               or d["details"]["actual"] != "annotation_byte_interpretation" for d in record["diagnostics"]):
            return False
    elif state == "source_semantics_unestablished":
        if status is not None or not any(d["code"] == "native_source_semantics_unestablished"
                and d["details"]["actual"] != "annotation_byte_interpretation" for d in record["diagnostics"]):
            return False
    elif status not in {0, 7} or not record["diagnostics"] or state == "partial" and status != 7:
        return False
    return True


@_boolean
def native_alignment_batch_valid(batch: dict, *, source_size_bytes: int,
                                 content: bytes | None = None) -> bool:
    """Validate the unchanged DecoderBatch, optionally against original bytes."""
    if (not _integer(source_size_bytes) or not _object(batch, _BATCH)
            or type(batch["records"]) is not list
            or content is not None and (type(content) is not bytes or len(content) != source_size_bytes)
            or not _envelope({k: v for k, v in batch.items() if k != "records"}, size=source_size_bytes)):
        return False
    fmt, records = batch["format"], batch["records"]
    if fmt not in _PHYLIP and len(records) > 1:
        return False
    lines = None if content is None else {
        line.byte_start: (line.number, line.byte_end, content[line.byte_start:line.byte_end])
        for line in iter_native_alignment_lines(content)
    }
    previous_end = previous_line = 0
    for index, record in enumerate(records):
        if (not _native_record(record, fmt, batch["alphabet"], size=source_size_bytes, lines=lines, content=content)
                or record["record_ordinal"] != index or record["byte_start"] < previous_end
                or record["line_start"] <= previous_line):
            return False
        if index < len(records) - 1 and record["native_status_equivalent"] != 0:
            return False
        previous_end, previous_line = record["byte_end"], record["line_end"]
    if records and batch["next_byte_offset"] < previous_end and not (
            fmt == "selex" and batch["end_state"] != "eof"
            and any(batch["next_byte_offset"] == e["locator"]["byte_start"] + len(
                _bytes(e["raw"]).removesuffix(b"\n").removesuffix(b"\r")) for e in records[-1]["events"])):
        return False
    if not all(_diagnostic(d, size=source_size_bytes, records=records, content=content) for d in batch["diagnostics"]):
        return False
    if records:
        if batch["end_state"] == "eof" and any(r["native_status_equivalent"] != 0 for r in records):
            return False
        if batch["end_state"] == "parse_error" and records[-1]["native_status_equivalent"] != 7:
            return False
        if batch["end_state"] == "source_semantics_unestablished" and records[-1]["reader_state"] != "source_semantics_unestablished":
            return False
        return batch["diagnostics"] == (records[0]["diagnostics"] if fmt in {"afa", "a2m"} else [])
    return (batch["end_state"] == "eof" and len(batch["diagnostics"]) == 1
            and batch["diagnostics"][0] == alignment_input_diagnostic(
                "empty_alignment", byte_start=0, byte_end=source_size_bytes, actual=0))


def _occurrence(value, *, direction=None, roles=None):
    return (_object(value, _OCCURRENCE)
            and all(_text(value[k]) for k in ("occurrence_id", "artifact_ref", "role"))
            and value["direction"] in {"input", "output"}
            and (direction is None or value["direction"] == direction)
            and (roles is None or value["role"] in roles)
            and _integer(value["ordinal"]) and _integer(value["size_bytes"])
            and value["completeness"] in {"complete", "partial", "unknown"}
            and type(value["sha256"]) is str and _hex(value["sha256"].lower(), digest=True))


def _locator(value, *, ordinal, occurrence=None):
    return (_object(value, _LOCATOR) and _text(value["artifact_ref"])
            and _integer(value["record_ordinal"]) and value["record_ordinal"] == ordinal
            and _span(value["byte_start"], value["byte_end"], None if occurrence is None else occurrence["size_bytes"])
            and _span(value["line_start"], value["line_end"], minimum=1)
            and (occurrence is None or value["artifact_ref"] == occurrence["artifact_ref"]))


def _record_identity(record, *, oid, fmt, index=None, occurrence=None, engine_version=None):
    if type(record) is not dict or not _integer(record.get("alignment_index")):
        return False
    ordinal = record["alignment_index"]
    return (record.get("kind") == "alignment" and record.get("occurrence_id") == oid
            and record.get("format") == fmt and record.get("record_key") == oid + "#alignment/" + str(ordinal)
            and _text(record.get("engine_version")) and (engine_version is None or record["engine_version"] == engine_version)
            and (index is None or ordinal == index)
            and _locator(record.get("locator"), ordinal=ordinal, occurrence=occurrence))


def _b1_native(record, *, alphabet, size=None):
    """Check the adapter's retained copies without rebuilding the B1 adapter."""
    native, envelope = record.get("native_input"), record.get("native_decoding")
    fmt = record["format"]
    if fmt not in _NATIVE_FORMATS:
        return "native_input" not in record and "native_decoding" not in record
    if (not _native_record(native, fmt, alphabet, size=size)
            or not _envelope(envelope, size=size) or envelope["format"] != fmt
            or envelope["alphabet"] != alphabet or native["record_ordinal"] != record["alignment_index"]):
        return False
    expected = {
        "header_valid": native["header_valid"], "complete": native["reader_state"] == "complete",
        "column_count": native["column_count"], "block_count": native["block_count"],
        "column_annotations": native["column_annotations"], "original_events": native["events"],
        "native_issues": native["diagnostics"],
    }
    if any(record.get(k) != value or type(record.get(k)) is not type(value) for k, value in expected.items()):
        return False
    loc = record["locator"]
    if any(loc[k] != native[k] for k in ("byte_start", "byte_end", "line_start", "line_end")):
        return False
    if type(record.get("rows")) is not list or len(record["rows"]) != len(native["rows"]):
        return False
    seen = {}
    for index, (row, original) in enumerate(zip(record["rows"], native["rows"])):
        if type(row) is not dict:
            return False
        for key in _ROW - {"diagnostics"}:
            if key not in row or type(row[key]) is not type(original[key]) or row[key] != original[key]:
                return False
        attached = [e for e in native["events"] if e["row_ordinal"] == index]
        if not attached:
            return False
        name = original["name"]
        if (row.get("record_key") != record["record_key"] + "/sequence/" + str(index)
                or not _integer(row.get("row_index")) or row["row_index"] != index
                or not _integer(row.get("alignment_index")) or row["alignment_index"] != record["alignment_index"]
                or not _integer(row.get("occurrence")) or row["occurrence"] != seen.get(name, 0)
                or row.get("native_issues") != original["diagnostics"]
                or row.get("fragments") != [e for e in attached if e["kind"] == "sequence"]
                or row.get("sequence_annotations") != [] or row.get("sequence_annotations_joined") is not True
                or row.get("weight") != {"value": None, "state": "missing", "events": []}
                or not _locator(row.get("locator"), ordinal=index)
                or row["locator"]["artifact_ref"] != loc["artifact_ref"]):
            return False
        rowloc = row["locator"]
        if (rowloc["byte_start"] != attached[0]["locator"]["byte_start"]
                or rowloc["byte_end"] != attached[-1]["locator"]["byte_end"]
                or rowloc["line_start"] != attached[0]["locator"]["line"]
                or rowloc["line_end"] != attached[-1]["locator"]["line"]):
            return False
        seen[name] = seen.get(name, 0) + 1
    return True


def _usable(record):
    """Geometry qualification only; this adds no numerical scoring policy."""
    return (record.get("complete") is True and record.get("header_valid") is True
            and _integer(record.get("column_count"), 1) and type(record.get("rows")) is list
            and bool(record["rows"]) and all(type(row) is dict
                and type(row.get("aligned_sequence")) is str
                and len(row["aligned_sequence"]) == record["column_count"]
                and all(row.get(k) is True for k in ("geometry_valid", "symbols_valid", "identity_unambiguous"))
                for row in record["rows"]))


def _reader_state(records, end_state):
    complete = [_usable(record) for record in records]
    if end_state == "eof" and all(complete):
        return "complete"
    if any(complete):
        return "partial"
    return "unavailable" if end_state in {"alphabet_undetermined", "source_semantics_unestablished"} else "invalid"


@_boolean
def input_decoding_local_valid(value: dict, *, alignment: dict | None, settings: dict) -> bool:
    """Check represented local facts; do not synthesize source identity/size."""
    if (not _object(value, _CONTEXT) or type(settings) is not dict
            or value["version"] != "hmmer_alignment_input_decoding_v1" or value["reader_profile"] != _PROFILE
            or not _text(value["source_occurrence_id"]) or not _hex(value["source_sha256"], digest=True)
            or value["format"] not in _FORMATS
            or value["alphabet_basis"] not in {"explicit_flag", "native_source_inference"}
            or value["explicit_alphabet"] is not None and value["explicit_alphabet"] not in _ALPHABETS
            or value["effective_alphabet"] is not None and value["effective_alphabet"] not in _ALPHABETS
            or value["reader_state"] not in {"complete", "partial", "invalid", "unavailable"}
            or value["file_end_state"] not in {"eof", "parse_error", "source_semantics_unestablished", "alphabet_undetermined"}
            or value["first_record_end_byte"] is not None and not _integer(value["first_record_end_byte"])):
        return False
    flags = (("--amino", "amino"), ("--dna", "DNA"), ("--rna", "RNA"))
    if any(flag in settings and type(settings[flag]) is not bool for flag, _ in flags):
        return False
    selected = [alphabet for flag, alphabet in flags if settings.get(flag)]
    if len(selected) > 1:
        return False
    fmt = value["format"]
    if "--informat" in settings:
        if type(settings["--informat"]) is not str or settings["--informat"].lower() != fmt:
            return False
    elif fmt != "stockholm":
        return False
    probe = value["alphabet_probe"]
    if value["alphabet_basis"] == "explicit_flag":
        if (len(selected) != 1 or selected[0] != value["explicit_alphabet"]
                or value["effective_alphabet"] != selected[0] or probe is not None):
            return False
    else:
        if (selected or value["explicit_alphabet"] is not None
                or not alphabet_probe_valid(probe, declared_format=fmt)
                or value["effective_alphabet"] != probe["alphabet"]):
            return False
        if probe["state"] != "determined":
            return (alignment is None and value["reader_state"] == "unavailable"
                    and value["first_record_end_byte"] is None
                    and value["file_end_state"] == ("alphabet_undetermined" if probe["state"] == "undetermined"
                                                    else "source_semantics_unestablished"))
    if value["file_end_state"] == "alphabet_undetermined" or value["reader_state"] == "complete" and value["file_end_state"] != "eof":
        return False
    if value["reader_state"] == "unavailable" and value["file_end_state"] != "source_semantics_unestablished":
        return False
    if alignment is None:
        return True
    if (not _record_identity(alignment, oid=value["source_occurrence_id"], fmt=fmt)
            or "source_alphabet" in alignment or "alphabet_probe" in alignment
            or alignment.get("input_decoding") != value or value["first_record_end_byte"] is None
            or not _b1_native(alignment, alphabet=value["effective_alphabet"])):
        return False
    if alignment["alignment_index"] == 0:
        return value["first_record_end_byte"] == alignment["locator"]["byte_end"]
    return value["first_record_end_byte"] <= alignment["locator"]["byte_start"]


@_boolean
def input_decoding_valid(value: dict, *, source_occurrence: dict,
                         declared_format: str, settings: dict, records: list[dict]) -> bool:
    """Add actual source custody and cross-record joins to the local check."""
    if (not _occurrence(source_occurrence, direction="input", roles={"alignment"})
            or source_occurrence["ordinal"] != 0 or declared_format not in _FORMATS
            or type(records) is not list or not input_decoding_local_valid(value, alignment=None, settings=settings)
            or value["source_occurrence_id"] != source_occurrence["occurrence_id"]
            or value["source_sha256"] != source_occurrence["sha256"].lower()
            or value["format"] != declared_format):
        return False
    size = source_occurrence["size_bytes"]
    if value["alphabet_probe"] is not None and not alphabet_probe_valid(
            value["alphabet_probe"], declared_format=declared_format, source_size_bytes=size):
        return False
    if (value["first_record_end_byte"] is None) != (not records):
        return False
    previous_end, envelope = 0, None
    for index, record in enumerate(records):
        if (not input_decoding_local_valid(value, alignment=record, settings=settings)
                or not _record_identity(record, oid=source_occurrence["occurrence_id"], fmt=declared_format,
                                        index=index, occurrence=source_occurrence)
                or record["locator"]["byte_start"] < previous_end):
            return False
        previous_end = record["locator"]["byte_end"]
        if declared_format in _NATIVE_FORMATS:
            if index == 0:
                envelope = record["native_decoding"]
            elif envelope != record["native_decoding"]:
                return False
    if envelope is not None:
        if (value["file_end_state"] != envelope["end_state"]
                or not native_alignment_batch_valid({**envelope, "records": [r["native_input"] for r in records]},
                                                     source_size_bytes=size)):
            return False
    if value["effective_alphabet"] is None:
        return not records
    return value["reader_state"] == _reader_state(records, value["file_end_state"])


def _source_alphabet(value, context):
    return (_object(value, _SOURCE) and value["version"] == "hmmer_alignment_source_alphabet_v1"
            and context is not None and context["effective_alphabet"] in _ALPHABETS
            and value["source_occurrence_id"] == context["source_occurrence_id"]
            and value["source_sha256"] == context["source_sha256"]
            and value["alphabet"] == context["effective_alphabet"]
            and value["alphabet_basis"] == context["alphabet_basis"])


def _population_valid(sheet, occurrence, fmt, *, count, complete):
    rows = [r for r in sheet["native_rows"] if type(r) is dict and r.get("kind") == "population"
            and r.get("occurrence_id") == occurrence["occurrence_id"]]
    if len(rows) != 1:
        return False
    row = rows[0]
    expected = {"record_key": occurrence["occurrence_id"] + "#population/0", "kind": "population",
                "occurrence_id": occurrence["occurrence_id"], "format": fmt, "decoded_count": count,
                "complete": complete, "state": "unsupported" if count is None else "decoded" if complete else "partial"}
    return (row == expected and type(row.get("complete")) is bool
            and (row.get("decoded_count") is None or _integer(row["decoded_count"])))


def _stockholm_encoding_failed(sheet, occurrence):
    return any(problem.get("code") == "text_encoding_invalid"
               and problem.get("occurrence_id") == occurrence["occurrence_id"]
               for problem in sheet["issues"])


def _population_complete(sheet, occurrence, fmt, records, *, reader_complete):
    """Preserve the existing reader's population qualifications separately."""
    if not reader_complete or occurrence["completeness"] != "complete":
        return False
    if fmt not in {"stockholm", "pfam"}:
        return True
    # Stockholm's B1 population is qualified by WT and annotation issues even
    # when the rows decoded completely. The later map-context attachment does
    # not change that already recorded population. Native byte-annotation
    # qualifications deliberately retain their separate, geometry-only rule.
    return (not _stockholm_encoding_failed(sheet, occurrence)
            and all(type(record.get("issues")) is list
                    and not any(problem.get("code") != "map_context_invalid"
                                for problem in record["issues"])
                    for record in records))


@_boolean
def saved_alignment_decoding_valid(sheet: dict, *, formats: dict[str, str] | None = None) -> bool:
    """Validate optional new facts after ordinary B1 admission; legacy stays absent."""
    if type(sheet) is not dict or any(type(sheet.get(k)) is not list for k in (
            "artifact_occurrences", "input_records", "output_records", "native_rows", "associations", "issues")):
        return False
    records = sheet["input_records"] + sheet["output_records"]
    if any(type(r) is not dict for r in records) or any(type(i) is not dict for i in sheet["issues"]):
        return False
    extraction = sheet.get("model_extraction")
    models = [] if extraction is None else extraction.get("records", [])
    if type(models) is not list or any(type(r) is not dict or r.keys() & _OPTIONAL for r in models):
        return False
    source_issues = [i for i in sheet["issues"] if i.get("field") in {"input_decoding", "source_alphabet"}]
    if sheet.keys() & _OPTIONAL:
        return False
    if not source_issues and not any(r.keys() & _OPTIONAL for r in records):
        return True
    operation = sheet.get("operation")
    if type(operation) is not dict or type(operation.get("settings")) is not dict or not _text(operation.get("engine_version")):
        return False
    settings = operation["settings"]
    if formats is not None and (type(formats) is not dict or any(not _text(k) or not _text(v) for k, v in formats.items())):
        return False
    occurrences = {}
    for occurrence in sheet["artifact_occurrences"]:
        if not _occurrence(occurrence) or occurrence["occurrence_id"] in occurrences:
            return False
        occurrences[occurrence["occurrence_id"]] = occurrence
    grouped = {"input": {}, "output": {}}
    for direction in grouped:
        for record in sheet[direction + "_records"]:
            if (record.get("kind") != "alignment" and record.keys() & _OPTIONAL
                    or "alphabet_probe" in record
                    or direction == "input" and "source_alphabet" in record
                    or direction == "output" and "input_decoding" in record):
                return False
            if record.get("kind") == "alignment":
                oid = record.get("occurrence_id")
                if oid not in occurrences or occurrences[oid]["direction"] != direction:
                    return False
                grouped[direction].setdefault(oid, []).append(record)
    issues_by_oid = {}
    for issue in source_issues:
        oid = issue.get("occurrence_id")
        if (oid not in occurrences or issue.get("record_key") is not None
                or issue.get("code") not in {"alignment_empty", "alignment_decoding_unavailable"}
                or not _object(issue.get("details"), {"context", "native_decoding"})
                or oid in issues_by_oid):
            return False
        direction = "input" if issue["field"] == "input_decoding" else "output"
        if occurrences[oid]["direction"] != direction or oid in grouped[direction]:
            return False
        issues_by_oid[oid] = issue
    contexts = {}
    input_ids = set(grouped["input"]) | {oid for oid, i in issues_by_oid.items() if i["field"] == "input_decoding"}
    for oid in input_ids:
        occurrence, current = occurrences[oid], grouped["input"].get(oid, [])
        issue = issues_by_oid.get(oid)
        context = current[0].get("input_decoding") if current else issue["details"]["context"]
        if context is None and current and not any(r.keys() & _OPTIONAL for r in current):
            continue
        if type(context) is not dict or not input_decoding_valid(context, source_occurrence=occurrence,
                declared_format=context.get("format"), settings=settings, records=current):
            return False
        contexts[oid] = context
        fmt = context["format"]
        if formats is not None and formats.get(oid) != fmt:
            return False
        if any(r["engine_version"] != operation["engine_version"] for r in current):
            return False
        if current:
            count = len(current)
        else:
            envelope = issue["details"]["native_decoding"]
            count = 0 if context["reader_state"] == "complete" and context["file_end_state"] == "eof" else None
            expected_issue = "alignment_empty" if count == 0 else "alignment_decoding_unavailable"
            if fmt in {"stockholm", "pfam"} and context["effective_alphabet"] is not None:
                # A structural decode can fail before its first record. It
                # still attempted a known population, unlike alphabet refusal.
                encoding_failed = _stockholm_encoding_failed(sheet, occurrence)
                if context["file_end_state"] != ("parse_error" if encoding_failed else "eof"):
                    return False
                count = 0
                expected_issue = "alignment_decoding_unavailable" if encoding_failed else "alignment_empty"
            if issue["code"] != expected_issue:
                return False
            if fmt in _NATIVE_FORMATS and count == 0:
                if (not _envelope(envelope, size=occurrence["size_bytes"])
                        or envelope["format"] != fmt or envelope["alphabet"] != context["effective_alphabet"]
                        or not native_alignment_batch_valid({**envelope, "records": []}, source_size_bytes=occurrence["size_bytes"])):
                    return False
            elif envelope is not None:
                return False
        complete = _population_complete(sheet, occurrence, fmt, current,
                                        reader_complete=context["reader_state"] == "complete")
        if not _population_valid(sheet, occurrence, fmt, count=count, complete=complete):
            return False
    source_occurrences = [o for o in occurrences.values() if o["direction"] == "input" and o["role"] == "alignment"]
    source = contexts.get(source_occurrences[0]["occurrence_id"]) if len(source_occurrences) == 1 else None
    output_ids = set(grouped["output"]) | {oid for oid, i in issues_by_oid.items() if i["field"] == "source_alphabet"}
    by_key = {r.get("record_key"): r for r in records}
    for oid in output_ids:
        occurrence, current = occurrences[oid], grouped["output"].get(oid, [])
        issue = issues_by_oid.get(oid)
        binding = current[0].get("source_alphabet") if current else issue["details"]["context"]
        if current and binding is None and not any(r.keys() & _OPTIONAL for r in current):
            continue
        if not _occurrence(occurrence, direction="output", roles={"masked_alignment", "resaved_alignment"}) or occurrence["ordinal"] != 0:
            return False
        fmt = "stockholm" if occurrence["role"] == "resaved_alignment" else settings.get("--outformat", "stockholm")
        fmt = fmt.lower() if type(fmt) is str else fmt
        if fmt not in _FORMATS or formats is not None and formats.get(oid) != fmt:
            return False
        if binding is None:
            if (current or source is not None and source["effective_alphabet"] is not None
                    or issue["details"]["native_decoding"] is not None):
                return False
            # Stockholm/Pfam output parsing is structural and can establish
            # zero rows without a source alphabet. Other formats did not run.
            structural = fmt in {"stockholm", "pfam"}
            expected_issue = ("alignment_empty" if structural
                and not _stockholm_encoding_failed(sheet, occurrence) else "alignment_decoding_unavailable")
            complete = _population_complete(sheet, occurrence, fmt, [], reader_complete=structural)
            if (issue["code"] != expected_issue
                    or not _population_valid(sheet, occurrence, fmt,
                                             count=0 if structural else None, complete=complete)):
                return False
            continue
        if not _source_alphabet(binding, source):
            return False
        for index, record in enumerate(current):
            if (record.get("source_alphabet") != binding
                    or not _record_identity(record, oid=oid, fmt=fmt, index=index,
                                            occurrence=occurrence, engine_version=operation["engine_version"])
                    or not _b1_native(record, alphabet=binding["alphabet"], size=occurrence["size_bytes"])):
                return False
        envelope = current[0].get("native_decoding") if current else issue["details"]["native_decoding"]
        if fmt in _NATIVE_FORMATS:
            if (not _envelope(envelope, size=occurrence["size_bytes"])
                    or envelope["format"] != fmt or envelope["alphabet"] != binding["alphabet"]
                    or any(r["native_decoding"] != envelope for r in current)
                    or not native_alignment_batch_valid({**envelope, "records": [r["native_input"] for r in current]},
                                                         source_size_bytes=occurrence["size_bytes"])):
                return False
        elif envelope is not None:
            return False
        complete = _population_complete(sheet, occurrence, fmt, current,
            reader_complete=all(_usable(r) for r in current)
                            and (envelope is None or envelope["end_state"] == "eof"))
        expected_issue = ("alignment_decoding_unavailable" if fmt in {"stockholm", "pfam"}
                          and _stockholm_encoding_failed(sheet, occurrence) else "alignment_empty")
        if not current and issue["code"] != expected_issue:
            return False
        if not _population_valid(sheet, occurrence, fmt, count=len(current), complete=complete):
            return False
    # Output source binding does not expand which source record an association
    # can name. Existing B1 admission owns its other numerical relationships.
    for association in sheet["associations"]:
        if type(association) is not dict:
            return False
        for field in ("output_record_key", "resaved_record_key"):
            target = by_key.get(association.get(field))
            if target is not None and "source_alphabet" in target:
                origin = by_key.get(association.get("source_record_key"))
                if (origin is None or origin.get("input_decoding") is None
                        or target["source_alphabet"]["source_occurrence_id"] != origin.get("occurrence_id")
                        or not _source_alphabet(target["source_alphabet"], origin["input_decoding"])):
                    return False
    return True
