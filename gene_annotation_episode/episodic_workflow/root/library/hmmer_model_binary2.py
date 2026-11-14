"""Original HMMER2.0 binary probability records, with no model conversion.

Layout authority: HMMER 2.3.2 src/hmmio.c WriteBinHMM/read_bin20hmm,
src/structs.h plan7_s and src/alphabet.c SetAlphabet, retained by Debian at
https://sources.debian.org/src/hmmer/2.3.2-5/src/ . The supported interpretation
is four-byte integers and IEEE754 binary32 in either byte order. The format
magic does not establish a producer version or its ABI. Source index-zero
entry/exit/map slots are unused bytes, not observations or fabricated zeros.
"""
from __future__ import annotations

import math
import struct

from gene_annotation_episode.episodic_workflow.root.library.hmmer_model_data import ALPHABETS, TRANSITIONS, _issue
from gene_annotation_episode.episodic_workflow.root.library.hmmer_model_binary import _BinaryReader, _FramingLost
from gene_annotation_episode.episodic_workflow.root.library.hmmer_model_source_cells import binary_probability_cell, hmmer2_evd_calibration
from gene_annotation_episode.episodic_workflow.root.library.hmmer_model_binary2_saved_fields import (
    MAGIC, _KNOWN_FLAGS, binary2_header, binary2_probability_start,
)


ENCODING = "hmmer2_binary_probability"
_SPECIAL = ["NB", "NN", "EC", "EJ", "CT", "CC", "JB", "JJ"]


def _record(occurrence, ordinal, start, order):
    return {"record_key": occurrence["occurrence_id"] + "#model/" + str(ordinal),
        "locator": {"artifact_ref": occurrence["artifact_ref"], "record_ordinal": ordinal,
            "byte_start": start, "byte_end": start, "line_start": None, "line_end": None},
        "format_tag": "HMMER2.0", "engine_text": None, "headers": [],
        "alphabet": {"kind": None, "symbols": []}, "length": None,
        "sequence_count": None, "effective_sequence_count": None, "maximum_length": None,
        "checksum": None, "flags": {}, "cutoffs": {}, "calibration": [], "composition": None,
        "initial": {"insert": None, "transitions": None}, "positions": [],
        "terminated": False, "issues": [], "representation": {
            "schema": "hmmer_model_representation_v1", "encoding": ENCODING,
            "topology": "hmmer2_configured", "byte_order": order,
            "binary_layout": "i32_u32_ieee754_binary32", "header_semantics": "binary_field_projection",
            "native_fields": [], "legacy": {"null_emissions": None, "special_transitions": None,
                "null_transitions": None, "begin_transitions": None, "entry_exit": [],
                "checksum": None, "evd": []}}}


class _Binary2Reader(_BinaryReader):
    def probability(self, field, *, used=True):
        start, raw = self.take(4)
        if len(raw) != 4:
            self.native(field, start, raw, None, "truncated")
            self.truncated(field, start, 4, len(raw))
            raise _FramingLost
        value = struct.unpack(self.prefix + "f", raw)[0]
        cell = binary_probability_cell(raw, byte_start=start, byte_order=self.order)
        self.native(field, start, raw, value if math.isfinite(value) else None,
            "unused" if not used else "present" if cell["state"] != "invalid" else "invalid")
        if used and cell["state"] == "invalid":
            self.problem("binary_probability_invalid", field, byte_start=start,
                byte_end=self.offset, raw_hex=raw.hex())
        return cell

    def annotation2(self, field, length):
        start, raw = self.take(length + 1)
        complete = len(raw) == length + 1
        # Index zero has no annotation meaning in this source layout. Preserve
        # its arbitrary byte without diagnosing it as a biological character.
        self.native(field, start, raw, raw.decode("utf-8", "surrogateescape"), "present" if complete else "truncated")
        if not complete:
            self.truncated(field, start, length + 1, len(raw))
            raise _FramingLost
        if b"\0" in raw[1:]:
            self.problem("annotation_value_invalid", field, byte_start=start, byte_end=self.offset)
        return [{"token": self.text(bytes([byte]), field, start + index),
                 "value": self.text(bytes([byte]), field, start + index) if byte else None}
            for index, byte in enumerate(raw[1:], 1)]

    def parse2(self):
        record, pending = self.record, {}
        legacy = record["representation"]["legacy"]
        try:
            self.scalar("magic", "I")
            flags = self.scalar("flags")
            if flags < 0 or flags & ~_KNOWN_FLAGS:
                self.problem("binary_flags_unknown", "flags", value=flags,
                    unknown_bits=(flags & 0xFFFFFFFF) & ~_KNOWN_FLAGS)
                raise _FramingLost
            name = self.string("NAME")
            self.header("NAME", name)
            if name is None or not name or len(name.split()) != 1:
                self.problem("header_value_invalid", "NAME")
            for field, bit in (("ACC", 9), ("DESC", 1)):
                if flags & (1 << bit):
                    self.header(field, self.string(field))
            length = self.scalar("M")
            if length <= 0:
                self.problem("binary_length_invalid", "M", value=length)
                raise _FramingLost
            record["length"] = length
            self.header("LENG", length)
            alphabet = self.scalar("alphabet_type")
            # Native hmmNUCLEIC is 2 and its represented symbols are ACGT.
            # This is not a claim about biological RNA/DNA source provenance.
            kind = {2: "DNA", 3: "amino"}.get(alphabet)
            if kind is None:
                self.problem("alphabet_invalid", "alphabet_type", value=alphabet)
                raise _FramingLost
            symbols = ALPHABETS[kind]
            record["alphabet"] = {"kind": kind, "symbols": symbols[:]}
            self.header("ALPH", "Nucleic" if alphabet == 2 else "Amino")
            for field, bit in (("RF", 2), ("CS", 3), ("MAP", 8)):
                record["flags"][field] = bool(flags & (1 << bit))
                self.header(field, "yes" if record["flags"][field] else "no")
                if field != "MAP" and record["flags"][field]:
                    pending[field] = self.annotation2(field, length)
            if flags & (1 << 8):
                pending["MAP"] = []
                self.scalar("MAP[0]", used=False)
                for position in range(1, length + 1):
                    value = self.scalar("MAP[" + str(position) + "]", minimum=0)
                    native = record["representation"]["native_fields"][-1]
                    pending["MAP"].append({"token": str(native["value"]), "value": value})
            self.header("COM", self.string("COM"))
            record["sequence_count"] = self.scalar("NSEQ", minimum=0)
            self.header("NSEQ", record["sequence_count"])
            self.header("DATE", self.string("DATE"))
            checksum = self.scalar("CKSUM", minimum=-(2 ** 31))
            legacy["checksum"] = {"token": str(checksum), "value": checksum,
                "line": None, "meaning": "hmmer2_legacy_checksum"}
            self.header("CKSUM", checksum)
            for field, bit in (("GA", 10), ("TC", 11), ("NC", 12)):
                if flags & (1 << bit):
                    values = [self.scalar(field + str(index), "f", minimum=-math.inf) for index in (1, 2)]
                    tokens = [None if value is None else str(value) for value in values]
                    record["cutoffs"][field] = {"tokens": tokens, "values": values,
                        "sequence": values[0], "domain": values[1], "domain_supplied": True,
                        "line": None, "unit": "bit"}
                    if all(token is not None for token in tokens):
                        self.header(field, " ".join(tokens), tokens=tokens[:])
            legacy["special_transitions"] = {"symbols": _SPECIAL[:], "cells": [
                self.probability("XT[" + str(index) + "]") for index in range(8)], "line": None}
            legacy["null_transitions"] = {"symbols": ["slot_0"],
                "cells": [self.probability("NULT.p1")], "line": None}
            legacy["null_emissions"] = {"symbols": symbols[:], "cells": [
                self.probability("NULE[" + str(index) + "]") for index in range(len(symbols))], "line": None}
            if flags & (1 << 7):
                mu = self.scalar("EVD.mu", "f", minimum=-math.inf)
                scale = self.scalar("EVD.lambda", "f", positive=True)
                values = [mu, scale]
                tokens = [None if value is None else str(value) for value in values]
                legacy["evd"].append({"tokens": tokens[:], "values": values[:], "line": None, "unit": None})
                if all(value is not None for value in values):
                    record["calibration"].append(hmmer2_evd_calibration(tokens, values))
                    self.header("EVD", " ".join(tokens), tokens=tokens[:])
                else:
                    self.problem("calibration_invalid", "EVD")
            legacy["begin_transitions"] = {"symbols": ["B->D1"],
                "cells": [self.probability("TBD1")], "line": None}
            entries, exits = [], []
            for field, target in (("begin", entries), ("end", exits)):
                self.probability(field + "[0]", used=False)
                for position in range(1, length + 1):
                    target.append(self.probability(field + "[" + str(position) + "]"))
            legacy["entry_exit"] = [{"position": position, "cells": [entry, exit], "line": None}
                for position, (entry, exit) in enumerate(zip(entries, exits), 1)]
            for position in range(1, length + 1):
                distribution = self.distribution("match", symbols, position)
                if distribution is not None:
                    record["positions"].append({"position": position, "position_token": None, "line": None,
                        "match": distribution, "insert": None, "transitions": None,
                        "annotations": {name: values[position - 1] for name, values in pending.items()}, "extra_tokens": []})
                self.require_framing()
            for field, names in (("insert", symbols), ("transitions", TRANSITIONS)):
                for position in range(1, length):
                    record["positions"][position - 1][field] = self.distribution(field, names, position)
                    self.require_framing()
            record["terminated"] = True
        except _FramingLost:
            self.problem("record_unterminated", "terminated", byte_end=self.offset,
                remaining_byte_start=self.offset, remaining_byte_end=len(self.content),
                remaining_raw_hex=self.content[self.offset:].hex())
        record["locator"]["byte_end"] = self.offset
        return record


def decode_hmmer2_binary(content, *, occurrence):
    records, issues, offset, order = [], [], 0, None
    while offset < len(content):
        raw = content[offset:offset + 4]
        observed = next((kind for kind in ("little", "big") if len(raw) == 4
            and int.from_bytes(raw, kind) == MAGIC), None)
        if observed is None or order is not None and observed != order:
            code = "binary_field_truncated" if len(raw) < 4 else (
                "binary_stream_layout_changed" if records else "binary_layout_unsupported")
            issues.append(_issue(code, field="magic", details={"byte_start": offset,
                "byte_end": len(content), "raw_hex": content[offset:].hex()}))
            break
        order = observed
        record = _record(occurrence, len(records), offset, order)
        reader = _Binary2Reader(content, record, offset)
        reader.parse2()
        records.append(record)
        issues.extend(record["issues"])
        offset = reader.offset
        if not record["terminated"]:
            break
    if len({row["alphabet"]["kind"] for row in records} - {None}) > 1:
        issues.append(_issue("mixed_alphabets", field="alphabet.kind"))
    return {"records": records, "issues": issues, "population": {
        "decoded_count": len(records) if records or not content else None,
        "complete": not issues, "state": "partial" if records and issues else "invalid" if issues else "decoded"}}


__all__ = ["MAGIC", "ENCODING", "decode_hmmer2_binary", "binary2_header", "binary2_probability_start"]
