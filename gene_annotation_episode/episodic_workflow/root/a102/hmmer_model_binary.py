"""Bounded decoding of original HMMER3 binary model bytes, revisions a--f.

The supported interpretation is i32/u32/IEEE754 binary32 in either byte order,
from p7_hmmfile_WriteBinary/read_bin30hmm. This does not establish a producer's
ABI, convert a model, synthesize consensus, expand legacy calibration, or load
a native HMM. Scientific calculations belong to the existing shared calculator.
"""
from __future__ import annotations

import math
import struct

from .hmmer_model_data import ALPHABETS, TRANSITIONS, _issue
from .hmmer_model_source_cells import binary_probability_cell


_MAGICS = {0xE8EDEDB6: "a", 0xE8EDEDB7: "b", 0xE8EDEDB8: "c",
           0xE8EDEDB9: "d", 0xE8EDEDB0: "e", 0xE8EDEDBA: "f"}
_OLD_MAGICS = {0xE8EDEDB1: "HMMER1.0", 0xE8EDEDB2: "HMMER1.1",
               0xE8EDEDB3: "HMMER1.7", 0xE8EDEDB4: "HMMER1.9",
               0xE8EDEDB5: "HMMER2.0"}
_ALPHABET_TYPES = {1: "RNA", 2: "DNA", 3: "amino"}
_ANNOTATIONS = (("RF", 2), ("MM", 17), ("CONS", 16), ("CS", 3), ("CA", 13))
_KNOWN_FLAGS = (1 << 18) - 1  # Includes obsolete bits 0, 4, 5 and 6, with no payload.


class _FramingLost(Exception):
    """Stop this stream at its first unestablished boundary."""


def _record(occurrence, ordinal, start, revision, byte_order):
    return {
        "record_key": occurrence["occurrence_id"] + "#model/" + str(ordinal),
        "locator": {"artifact_ref": occurrence["artifact_ref"], "record_ordinal": ordinal,
                    "byte_start": start, "byte_end": start,
                    "line_start": None, "line_end": None},
        "format_tag": "HMMER3/" + revision, "engine_text": None,
        "headers": [], "alphabet": {"kind": None, "symbols": []},
        "length": None, "sequence_count": None, "effective_sequence_count": None,
        "maximum_length": None, "checksum": None, "flags": {}, "cutoffs": {},
        "calibration": [], "composition": None,
        "initial": {"insert": None, "transitions": None}, "positions": [],
        "terminated": False, "issues": [],
        "representation": {
            "schema": "hmmer_model_representation_v1",
            "encoding": "hmmer3_binary_probability", "topology": "hmmer3_core",
            "byte_order": byte_order, "binary_layout": "i32_u32_ieee754_binary32",
            "header_semantics": "binary_field_projection", "native_fields": [],
            "legacy": None,
        },
    }


class _BinaryReader:
    def __init__(self, content, record, start):
        self.content, self.record, self.offset = content, record, start
        self.order = record["representation"]["byte_order"]
        self.prefix = "<" if self.order == "little" else ">"
        self.framing_lost = False

    def problem(self, code, field, *, position=None, **details):
        self.record["issues"].append(_issue(code, record_key=self.record["record_key"],
            field=field, position=position, details=details))

    def take(self, size):
        start = self.offset
        self.offset = min(len(self.content), start + size)
        return start, self.content[start:self.offset]

    def native(self, field, start, raw, value, state="present"):
        entry = {"field": field, "byte_start": start, "byte_end": start + len(raw),
                 "raw_hex": raw.hex(), "value": value, "state": state}
        self.record["representation"]["native_fields"].append(entry)
        return entry

    def truncated(self, field, start, expected, actual, *, position=None):
        self.framing_lost = True
        self.problem("binary_field_truncated", field, position=position,
                     byte_start=start, byte_end=start + actual,
                     expected_bytes=expected, actual_bytes=actual)

    def scalar(self, field, kind="i", *, used=True, sentinel=None, minimum=None,
               positive=False):
        start, raw = self.take(4)
        if len(raw) != 4:
            self.native(field, start, raw, None, "truncated")
            self.truncated(field, start, 4, len(raw))
            raise _FramingLost
        value = struct.unpack(self.prefix + kind, raw)[0]
        finite = not isinstance(value, float) or math.isfinite(value)
        entry = self.native(field, start, raw, value if finite else None,
                            "present" if used else "unused")
        if not used:
            return None
        if sentinel is not None and value == sentinel:
            entry["state"] = "native_missing_sentinel"
            return None
        if not finite or (minimum is not None and value < minimum) or (positive and value <= 0):
            entry["state"] = "invalid"
            self.problem("binary_native_value_invalid", field,
                         byte_start=start, byte_end=self.offset, raw_hex=raw.hex())
            return None
        return value

    def header(self, tag, value, tokens=None):
        if value is not None:
            value = str(value)
            self.record["headers"].append({"tag": tag, "value": value,
                "tokens": value.split() if tokens is None else tokens, "line": None})

    def text(self, raw, field, start):
        value = raw.decode("utf-8", errors="surrogateescape")
        if any(0xDC80 <= ord(char) <= 0xDCFF for char in value):
            self.problem("text_encoding_invalid", field, byte_start=start,
                         byte_end=start + len(raw))
        return value

    def string(self, field):
        size = self.scalar(field + ".length")
        if size < 0:
            self.record["representation"]["native_fields"][-1]["state"] = "invalid"
            self.problem("binary_length_invalid", field + ".length", value=size)
            raise _FramingLost
        start, raw = self.take(size)
        if len(raw) != size:
            self.native(field, start, raw, self.text(raw, field, start), "truncated")
            self.truncated(field, start, size, len(raw))
            raise _FramingLost
        if size == 0:
            self.native(field, start, raw, None, "native_missing_sentinel")
            return None
        valid = raw[-1:] == b"\0" and b"\0" not in raw[:-1]
        value = self.text(raw[:-1] if raw[-1:] == b"\0" else raw, field, start)
        self.native(field, start, raw, value, "present" if valid else "invalid")
        if not valid:
            self.problem("binary_string_invalid", field, byte_start=start, byte_end=self.offset)
            return None
        return value

    def distribution(self, field, symbols, position=None):
        cells = []
        for index in range(len(symbols)):
            start, raw = self.take(4)
            if raw:
                cell = binary_probability_cell(raw, byte_start=start, byte_order=self.order)
                cells.append(cell)
            if len(raw) != 4:
                self.truncated(field, start, 4, len(raw), position=position)
                break
            if cell["state"] == "invalid":
                self.problem("binary_probability_invalid", field, position=position,
                             cell=index, byte_start=start, byte_end=self.offset,
                             raw_hex=raw.hex())
        return {"symbols": symbols[:], "cells": cells, "line": None} if cells else None

    def require_framing(self):
        if self.framing_lost:
            raise _FramingLost

    def annotation(self, name, length):
        start, raw = self.take(length + 2)
        complete = len(raw) == length + 2
        valid = complete and raw[:1] == b" " and raw[-1:] == b"\0" and b"\0" not in raw[1:-1]
        self.native(name, start, raw, self.text(raw, name, start),
                    "present" if valid else "invalid" if complete else "truncated")
        # Each position is exactly one native byte; index zero and the terminal
        # NUL stay in native_fields and are never mistaken for model positions.
        for position, byte in enumerate(raw[1:min(length + 1, len(raw))], 1):
            value = self.text(bytes([byte]), name, start + position)
            self.record["positions"][position - 1]["annotations"][name] = {
                "token": value, "value": value if byte else None}
        if not complete:
            self.truncated(name, start, length + 2, len(raw))
            raise _FramingLost
        if not valid:
            self.problem("annotation_value_invalid", name, byte_start=start, byte_end=self.offset)

    def calibration(self, revision, used):
        groups = ([("LAMBDA", (("LAMBDA", "lambda"),)),
                   ("MU", (("MU", "mu"),)), ("TAU", (("TAU", "tau"),))]
                  if revision == "a" else
                  [("MSV", (("MMU", "mu"), ("MLAMBDA", "lambda"))),
                   ("VITERBI", (("VMU", "mu"), ("VLAMBDA", "lambda"))),
                   ("FORWARD", (("FTAU", "tau"), ("FLAMBDA", "lambda")))])
        for statistic, slots in groups:
            entry = {"mode": "LOCAL", "statistic": statistic,
                     "tokens": ["LOCAL", statistic], "parameters": [], "line": None}
            if used:
                self.record["calibration"].append(entry)
            for slot, name in slots:
                value = self.scalar("STATS." + slot, "f", used=used, positive=name == "lambda")
                if used:
                    token = str(value) if value is not None else None
                    entry["parameters"].append({"name": name, "token": token, "value": value,
                        "unit": "inverse_bit" if name == "lambda" else "bit"})
                    entry["tokens"].append(token)
            if used and all(token is not None for token in entry["tokens"]):
                self.header("STATS", " ".join(entry["tokens"]), tokens=entry["tokens"][:])

    def parse(self, revision):
        record = self.record
        try:
            self.scalar("magic", "I")
            flags = self.scalar("flags")
            if flags < 0 or flags & ~_KNOWN_FLAGS:
                record["representation"]["native_fields"][-1]["state"] = "invalid"
                self.problem("binary_flags_unknown", "flags", value=flags,
                             unknown_bits=(flags & 0xFFFFFFFF) & ~_KNOWN_FLAGS)
                raise _FramingLost
            for name, bit in (*_ANNOTATIONS, ("MAP", 8)):
                if name != "CA" or flags & (1 << bit):
                    record["flags"][name] = bool(flags & (1 << bit))
                    self.header(name, "yes" if record["flags"][name] else "no")
            length = self.scalar("M")
            if length <= 0:
                record["representation"]["native_fields"][-1]["state"] = "invalid"
                self.problem("binary_length_invalid", "M", value=length)
                raise _FramingLost
            record["length"] = length
            self.header("LENG", length)
            alphabet_type = self.scalar("alphabet_type")
            kind = _ALPHABET_TYPES.get(alphabet_type)
            if kind is None:
                record["representation"]["native_fields"][-1]["state"] = "invalid"
                self.problem("alphabet_invalid", "alphabet_type", value=alphabet_type)
                raise _FramingLost
            symbols = ALPHABETS[kind]
            record["alphabet"] = {"kind": kind, "symbols": symbols[:]}
            self.header("ALPH", kind)
            # Never allocate from M. Only encountered bytes create rows/cells.
            for position in range(1, length + 1):
                distribution = self.distribution("match", symbols, position)
                if distribution is not None:
                    record["positions"].append({"position": position, "position_token": None,
                        "line": None, "match": distribution, "insert": None,
                        "transitions": None, "annotations": {}, "extra_tokens": []})
                self.require_framing()
            for field, names in (("insert", symbols), ("transitions", TRANSITIONS)):
                for position in range(length + 1):
                    target = record["positions"][position - 1] if position else record["initial"]
                    target[field] = self.distribution(field if position else "initial." + field,
                                                      names, position)
                    self.require_framing()
            name = self.string("NAME")
            self.header("NAME", name)
            if name is None or not name or len(name.split()) != 1:
                self.problem("header_value_invalid", "NAME")
            for name, bit in (("ACC", 9), ("DESC", 1)):
                if flags & (1 << bit):
                    self.header(name, self.string(name))
            for name, bit in _ANNOTATIONS:
                if flags & (1 << bit):
                    self.annotation(name, length)
            self.header("COM", self.string("COM"))
            counts = [("sequence_count", "NSEQ", "i"),
                      ("effective_sequence_count", "EFFN", "f")]
            if revision >= "c":
                counts.append(("maximum_length", "MAXL", "i"))
            for field, tag, scalar_kind in counts:
                record[field] = self.scalar(tag, scalar_kind, sentinel=-1, minimum=0)
                self.header(tag, record[field])
            self.header("DATE", self.string("DATE"))
            if flags & (1 << 8):
                for position in range(length + 1):
                    value = self.scalar("MAP[" + str(position) + "]", minimum=0)
                    if position:
                        entry = record["representation"]["native_fields"][-1]
                        record["positions"][position - 1]["annotations"]["MAP"] = {
                            "token": str(entry["value"]) if entry["value"] is not None else None,
                            "value": value}
                    elif value != 0:
                        self.problem("annotation_value_invalid", "MAP[0]", value=value)
            record["checksum"] = self.scalar("CKSUM", "I", used=bool(flags & (1 << 15)))
            self.header("CKSUM", record["checksum"])
            self.calibration(revision, bool(flags & (1 << 7)))
            for tag, bit in (("GA", 10), ("TC", 11), ("NC", 12)):
                used = bool(flags & (1 << bit))
                entry = {"tokens": [], "values": [], "sequence": None, "domain": None,
                         "domain_supplied": False, "line": None, "unit": "bit"}
                if used:
                    record["cutoffs"][tag] = entry
                for index, field in enumerate(("sequence", "domain"), 1):
                    value = self.scalar(tag + str(index), "f", used=used)
                    if used:
                        entry["tokens"].append(str(value) if value is not None else None)
                        entry["values"].append(value)
                        entry[field] = value
                        if field == "domain":
                            entry["domain_supplied"] = True
                if used and all(token is not None for token in entry["tokens"]):
                    self.header(tag, " ".join(entry["tokens"]), tokens=entry["tokens"][:])
            if flags & (1 << 14):
                record["composition"] = self.distribution("composition", symbols)
                self.require_framing()
            record["terminated"] = True
        except _FramingLost:
            self.problem("record_unterminated", "terminated", byte_end=self.offset)
            if self.offset < len(self.content):
                # The boundary is unknown: these bytes cannot be assigned to a
                # fabricated next model. Preserve them with the stopping issue.
                record["issues"][-1]["details"].update(
                    remaining_byte_start=self.offset, remaining_byte_end=len(self.content),
                    remaining_raw_hex=self.content[self.offset:].hex())
        record["locator"]["byte_end"] = self.offset
        return record


def decode_hmmer3_binary(content: bytes, *, occurrence: dict) -> dict:
    """Decode validated supplied bytes; argument/capture validation is public.

    Framing follows a single recognized revision/order. The next magic is read
    only at an established record end, never searched for in damaged data.
    """
    records, issues = [], []
    offset, layout, unsupported = 0, None, False
    while offset < len(content):
        raw = content[offset:offset + 4]
        recognized = None
        old_format = None
        for order in ("little", "big"):
            if len(raw) == 4:
                magic = int.from_bytes(raw, order)
                if magic in _MAGICS:
                    recognized = (_MAGICS[magic], order)
                if magic in _OLD_MAGICS:
                    old_format = _OLD_MAGICS[magic]
        if recognized is None:
            details = {"byte_start": offset, "byte_end": len(content),
                       "raw_hex": content[offset:].hex()}
            if len(raw) < 4:
                code = "binary_field_truncated"
                details.update(expected_bytes=4, actual_bytes=len(raw))
            elif old_format:
                code, unsupported = "decoder_unavailable", True
                details["format"] = old_format + " binary"
            else:
                code, unsupported = "binary_layout_unsupported", True
            issues.append(_issue(code, field="magic", details=details))
            break
        if layout is not None and recognized != layout:
            issues.append(_issue("binary_stream_layout_changed", field="magic",
                details={"byte_start": offset, "byte_end": len(content),
                         "raw_hex": content[offset:].hex(),
                         "expected_revision": layout[0], "expected_byte_order": layout[1],
                         "actual_revision": recognized[0], "actual_byte_order": recognized[1]}))
            break
        layout = recognized
        record = _record(occurrence, len(records), offset, *layout)
        reader = _BinaryReader(content, record, offset)
        reader.parse(layout[0])
        records.append(record)
        issues.extend(record["issues"])
        offset = reader.offset
        if not record["terminated"]:
            break
    if len({r["alphabet"]["kind"] for r in records} - {None}) > 1:
        issues.append(_issue("mixed_alphabets", field="alphabet.kind"))
    state = ("partial" if records and issues else "unsupported" if unsupported
             else "invalid" if issues else "decoded")
    return {"records": records, "issues": issues,
            "population": {"decoded_count": len(records) if records or not content else None,
                           "complete": not issues, "state": state}}
