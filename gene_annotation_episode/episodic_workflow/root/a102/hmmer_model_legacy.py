"""Decode original HMMER2.0 ASCII source without constructing an HMMER3 model.

The grammar follows the retained HMMER 3.4 h2_io.c writer and the source fields
read by p7_hmmfile.c:read_asc20hmm. The latter's model conversion is deliberately
not performed: configured transitions, NULE, integer scores and terminal
placeholders remain source data. Scalar reconstruction belongs to the shared
source-cell helper; scientific calculations belong to the common calculators.
"""
from __future__ import annotations

import re

from .hmmer_model_data import ALPHABETS, TRANSITIONS, _issue, _numeric
from .hmmer_model_source_cells import hmmer2_evd_calibration, hmmer2_probability_cell


_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_SIGNATURE = re.compile(r"HMMER(?:[12]\.[0-9]+|3/[a-z])\Z")
_TRANSITIONS = TRANSITIONS + ["b->m", "m->e"]
_SPECIAL = ["NB", "NN", "EC", "EJ", "CT", "CC", "JB", "JJ"]
# The source contains no NULT labels. Do not infer a producer from its bytes.
_NULL_TRANSITIONS = ["slot_0", "slot_1"]
_BEGIN = ["B->M1", "unused", "B->D1"]


class _LegacyReader:
    def __init__(self, content, occurrence):
        raw_lines = content.splitlines(keepends=True)
        self.lines = [line.decode("utf-8", errors="surrogateescape").rstrip("\r\n")
                      for line in raw_lines]
        self.offsets = [0]
        for line in raw_lines:
            self.offsets.append(self.offsets[-1] + len(line))
        self.occurrence = occurrence

    def header(self, index):
        parts = self.lines[index].strip().split(None, 1)
        value = parts[1] if len(parts) == 2 else ""
        return {"tag": parts[0], "value": value, "tokens": value.split(), "line": index + 1}

    def record(self, start, end, terminated, ordinal):
        signature = self.lines[start].strip().split(None, 1)
        key = self.occurrence["occurrence_id"] + "#model/" + str(ordinal)
        legacy = {"null_emissions": None, "special_transitions": None,
                  "null_transitions": None, "begin_transitions": None,
                  "entry_exit": [], "checksum": None, "evd": []}
        record = {
            "record_key": key,
            "locator": {"artifact_ref": self.occurrence["artifact_ref"],
                        "record_ordinal": ordinal, "byte_start": self.offsets[start],
                        "byte_end": self.offsets[end], "line_start": start + 1,
                        "line_end": end},
            "format_tag": signature[0],
            "engine_text": signature[1] if len(signature) == 2 else None,
            "headers": [], "alphabet": {"kind": None, "symbols": []},
            "length": None, "sequence_count": None, "effective_sequence_count": None,
            "maximum_length": None, "checksum": None, "flags": {}, "cutoffs": {},
            "calibration": [], "composition": None,
            "initial": {"insert": None, "transitions": None}, "positions": [],
            "terminated": terminated, "issues": [],
            "representation": {"schema": "hmmer_model_representation_v1",
                "encoding": "hmmer2_ascii_millibit_log_odds", "topology": "hmmer2_configured",
                "byte_order": None, "binary_layout": None,
                "header_semantics": "original_ascii_headers", "native_fields": [],
                "legacy": legacy},
        }

        def problem(code, field=None, *, position=None, line=None, **details):
            record["issues"].append(_issue(code, record_key=key, field=field,
                position=position, line=line, details=details))

        for i in range(start, end):
            if any(0xDC80 <= ord(char) <= 0xDCFF for char in self.lines[i]):
                problem("text_encoding_invalid", "text", line=i + 1)
        if not terminated:
            problem("record_unterminated", "terminated", line=end)
        stop = end - int(terminated)
        by_tag, body = {}, None
        for i in range(start + 1, stop):
            text = self.lines[i].strip()
            if not text or text.startswith("#"):
                continue
            header = self.header(i)
            record["headers"].append(header)
            by_tag.setdefault(header["tag"], []).append(header)
            if header["tag"] == "HMM":
                body = i
                record["alphabet"]["symbols"] = header["tokens"][:]
                break
        for name, entries in by_tag.items():
            if len(entries) > 1 and name != "COM":
                problem("header_duplicate", name, line=entries[0]["line"], count=len(entries))

        def single(name, *, required=False):
            entries = by_tag.get(name, [])
            if not entries:
                if required:
                    problem("header_missing", name)
                return None
            return entries[0] if len(entries) == 1 else None

        def scalar(name, **kwargs):
            header = single(name, required=name == "LENG")
            if header is None:
                return None
            if len(header["tokens"]) != 1:
                problem("header_width_invalid", name, line=header["line"])
                return None
            value = _numeric(header["tokens"][0], **kwargs)
            if value is None:
                problem("header_number_invalid", name, line=header["line"], token=header["tokens"][0])
            return value

        for name in ("NAME", "ACC", "DESC", "DATE"):
            header = single(name, required=name == "NAME")
            # Bare DESC is explicitly accepted by the retained reader (#h106).
            if header and name != "DESC" and (not header["tokens"] or
                    name != "DATE" and len(header["tokens"]) != 1):
                problem("header_value_invalid", name, line=header["line"])
        for header in by_tag.get("COM", []):
            if not header["tokens"]:
                problem("header_value_invalid", "COM", line=header["line"])
        record["length"] = scalar("LENG", integer=True, positive=True)
        record["sequence_count"] = scalar("NSEQ", integer=True, minimum=0)
        alph = single("ALPH", required=True)
        label = (alph["tokens"][0].lower() if alph and len(alph["tokens"]) == 1 else None)
        symbols = record["alphabet"]["symbols"]
        width = 20 if label == "amino" else 4 if label == "nucleic" else len(symbols)
        if label == "amino":
            record["alphabet"]["kind"] = "amino"
            valid_symbols = symbols == ALPHABETS["amino"]
        elif label == "nucleic":
            # This identifies the represented body symbols, not a biological
            # RNA/DNA provenance that the Nucleic header never supplied.
            kind = next((kind for kind in ("DNA", "RNA") if symbols == ALPHABETS[kind]), None)
            record["alphabet"]["kind"] = kind
            valid_symbols = kind is not None
        else:
            valid_symbols = False
            if alph is not None:
                problem("alphabet_invalid", "ALPH", line=alph["line"])
        if body is not None and not valid_symbols:
            problem("alphabet_symbols_invalid", "alphabet.symbols", line=body + 1, actual=symbols)
        for name in ("RF", "CS", "MAP"):
            if name not in by_tag:
                continue
            header = single(name)
            flag = None
            if header and len(header["tokens"]) == 1 and header["tokens"][0].lower() in {"yes", "no"}:
                flag = header["tokens"][0].lower() == "yes"
            else:
                problem("header_value_invalid", name, line=header["line"] if header else None)
            record["flags"][name] = flag
        for name in ("GA", "TC", "NC"):
            header = single(name)
            if header is None:
                continue
            tokens = header["tokens"]
            values = [_numeric(token) for token in tokens]
            record["cutoffs"][name] = {"tokens": tokens[:], "values": values,
                "sequence": values[0] if values else None,
                "domain": values[1] if len(values) > 1 else None,
                "domain_supplied": len(tokens) > 1, "line": header["line"], "unit": "bit"}
            if len(tokens) != 2:
                problem("header_width_invalid", name, line=header["line"], expected=2, actual=len(tokens))
            if any(value is None for value in values):
                problem("header_number_invalid", name, line=header["line"])
        checksum = single("CKSUM")
        if checksum is not None:
            value = scalar("CKSUM", integer=True)
            legacy["checksum"] = {"token": checksum["tokens"][0] if len(checksum["tokens"]) == 1 else None,
                "value": value, "line": checksum["line"], "meaning": "hmmer2_legacy_checksum"}
        for header in by_tag.get("EVD", []):
            values = [_numeric(token) for token in header["tokens"]]
            legacy["evd"].append({"tokens": header["tokens"][:], "values": values,
                                  "line": header["line"], "unit": None})
            if len(values) != 2:
                problem("header_width_invalid", "EVD", line=header["line"], expected=2, actual=len(values))
            if any(value is None for value in values):
                problem("header_number_invalid", "EVD", line=header["line"])
        if len(legacy["evd"]) == 1:
            observed = legacy["evd"][0]
            calibrated = hmmer2_evd_calibration(observed["tokens"], observed["values"], line=observed["line"])
            if calibrated is not None:
                record["calibration"].append(calibrated)
            else:
                problem("calibration_invalid", "EVD", line=observed["line"])

        def distribution(tokens, names, expected, field, position, line, reference_kind):
            if len(tokens) != expected:
                problem("distribution_width_invalid", field, position=position, line=line,
                        expected=expected, actual=len(tokens))
            cells = []
            for j, token in enumerate(tokens):
                reference_cell = None
                if reference_kind == "nule":
                    reference = {"kind": "nule", "cell_index": j}
                    nulls = legacy["null_emissions"]
                    if nulls is not None and j < len(nulls["cells"]):
                        reference_cell = nulls["cells"][j]
                elif reference_kind == "uniform_alphabet":
                    reference = {"kind": "uniform_alphabet", "denominator": width}
                else:
                    reference = {"kind": "unit"}
                cell = hmmer2_probability_cell(token, reference=reference, reference_cell=reference_cell)
                if token != "*" and (not _INTEGER.fullmatch(token) or cell["source"]["score"] is None):
                    problem("probability_token_invalid", field, position=position, line=line,
                            cell=j, token=token)
                elif cell["state"] == "underflow":
                    problem("probability_underflow", field, position=position, line=line, cell=j)
                # Valid integer encodings with unusable nominal arithmetic are
                # retained. Their numerical qualification is a calculator task.
                cells.append(cell)
            return {"symbols": names[:], "cells": cells, "line": line}

        for tag, field, names, count, reference_kind in (
            ("NULE", "null_emissions", symbols, width, "uniform_alphabet"),
            ("XT", "special_transitions", _SPECIAL, 8, "unit"),
            ("NULT", "null_transitions", _NULL_TRANSITIONS, 2, "unit"),
        ):
            header = single(tag, required=True)
            if header is not None:
                if tag == "NULE" and alph is not None and header["line"] < alph["line"]:
                    problem("header_value_invalid", "NULE", line=header["line"],
                            required_preceding_header="ALPH")
                legacy[field] = distribution(header["tokens"], names, count, "legacy." + field,
                                             None, header["line"], reference_kind)
        if body is None:
            problem("body_missing", "HMM")
            return record
        if not width:
            problem("body_missing", "alphabet.symbols")
            return record

        rows = [(i + 1, self.lines[i].split()) for i in range(body + 1, stop)
                if self.lines[i].strip() and not self.lines[i].lstrip().startswith("#")]
        cursor, labels = 0, []
        if rows and (any("->" in token for token in rows[0][1]) or
                     len(rows[0][1]) >= 7 and any(token != "*" and not _INTEGER.fullmatch(token)
                                                for token in rows[0][1])):
            line, labels = rows[0]
            # The transition-column line is a native body header. Keep its
            # actual nine labels, even if corrupt, in the original accessor.
            record["headers"].append(self.header(line - 1))
            cursor = 1
        if labels != _TRANSITIONS:
            problem("transition_labels_invalid", "transitions.symbols", line=body + 2,
                    expected=_TRANSITIONS, actual=labels)

        has_map = record["flags"].get("MAP") is True

        def match_like(index):
            if index >= len(rows):
                return False
            tokens = rows[index][1]
            if (_numeric(tokens[0], integer=True, positive=True) is None or
                    len(tokens) != 1 + width + int(has_map)):
                return False
            if has_map:
                return True
            # A numeric RF character is legal. Its following transition row
            # distinguishes it from the next position's match row when present.
            return not (index + 1 < len(rows) and len(rows[index + 1][1]) == 10
                        and len(rows[index + 1][1][0]) == 1)

        if cursor < len(rows) and not match_like(cursor):
            line, tokens = rows[cursor]
            legacy["begin_transitions"] = distribution(tokens, _BEGIN, 3,
                "legacy.begin_transitions", None, line, "unit")
            cursor += 1
        else:
            problem("distribution_missing", "legacy.begin_transitions")

        def annotation(entry, name, token, line):
            value = _numeric(token, integer=True, minimum=0) if name == "MAP" else token
            if (name == "MAP" and value is None) or (name != "MAP" and len(token) != 1):
                problem("annotation_value_invalid", "annotations." + name,
                        position=entry["position"], line=line, token=token)
            entry["annotations"][name] = {"token": token, "value": value}

        def take(entry, field, names, expected, annotation_name, reference_kind):
            nonlocal cursor
            position = entry["position"]
            if cursor >= len(rows) or match_like(cursor):
                problem("distribution_missing", field, position=position)
                return None
            line, tokens = rows[cursor]
            cursor += 1
            annotation(entry, annotation_name, tokens[0], line)
            return distribution(tokens[1:], names, expected, field, position, line, reference_kind)

        while cursor < len(rows):
            line, tokens = rows[cursor]
            cursor += 1
            position = _numeric(tokens[0], integer=True, positive=True)
            expected_position = len(record["positions"]) + 1
            if position is None:
                problem("position_invalid", "position", line=line, token=tokens[0])
            elif position != expected_position:
                problem("position_order_invalid", "position", position=position, line=line,
                        expected=expected_position)
            entry = {"position": position, "position_token": tokens[0], "line": line,
                "match": distribution(tokens[1:1 + width], symbols, width, "match", position, line, "nule"),
                "insert": None, "transitions": None, "annotations": {}, "extra_tokens": []}
            extras = tokens[1 + width:]
            if len(extras) != int(has_map):
                problem("annotation_width_invalid", "annotations", position=position, line=line,
                        expected=int(has_map), actual=len(extras))
            if has_map and extras:
                annotation(entry, "MAP", extras[0], line)
            entry["extra_tokens"] = extras[int(has_map):]
            entry["insert"] = take(entry, "insert", symbols, width, "RF", "nule")
            transitions = take(entry, "transitions", labels, 9, "CS", "unit")
            if transitions is not None:
                entry["transitions"] = {"symbols": transitions["symbols"][:7],
                    "cells": transitions["cells"][:7], "line": transitions["line"]}
                legacy["entry_exit"].append({"position": position,
                    "cells": transitions["cells"][7:9], "line": transitions["line"]})
                # Invalid extra source slots stay retained as tokens; they do
                # not extend a seven-slot common distribution's population.
                entry["extra_tokens"].extend(cell["token"] for cell in transitions["cells"][9:])
            else:
                legacy["entry_exit"].append({"position": position, "cells": [], "line": None})
            record["positions"].append(entry)
        if record["length"] != len(record["positions"]):
            problem("length_mismatch", "positions", expected=record["length"], actual=len(record["positions"]))
        return record


def decode_hmmer2_ascii(content: bytes, *, occurrence: dict) -> dict:
    """Decode the declared source; the public dispatcher validates its occurrence.

    Complete records and all observed partial rows keep their original order.
    Text signatures may resynchronize an interrupted record. Numerical nominal
    range/underflow qualifications do not erase an otherwise decoded population.
    """
    reader = _LegacyReader(content, occurrence)
    result = {"records": [], "issues": [], "population": None}
    index = 0
    while index < len(reader.lines):
        text = reader.lines[index].strip()
        if not text or text.startswith("#"):
            index += 1
            continue
        tag = text.split()[0]
        if tag != "HMMER2.0":
            code = "revision_unsupported" if tag.startswith("HMMER") else "signature_invalid"
            result["issues"].append(_issue(code, field="format_tag", line=index + 1,
                                           details={"token": tag}))
            index += 1
            continue
        end, terminated = index + 1, False
        while end < len(reader.lines):
            text = reader.lines[end].strip()
            if text == "//":
                end, terminated = end + 1, True
                break
            if text and _SIGNATURE.fullmatch(text.split()[0]):
                break
            end += 1
        record = reader.record(index, end, terminated, len(result["records"]))
        result["records"].append(record)
        result["issues"].extend(record["issues"])
        index = end
    kinds = {record["alphabet"]["kind"] for record in result["records"]} - {None}
    if len(kinds) > 1:
        result["issues"].append(_issue("mixed_alphabets", field="alphabet.kind"))
    errors = [issue for issue in result["issues"] if issue["code"] != "probability_underflow"]
    no_records = not result["records"]
    unsupported = no_records and any(issue["code"] == "revision_unsupported" for issue in errors)
    state = ("unsupported" if unsupported else "invalid" if errors and no_records
             else "partial" if errors else "decoded")
    result["population"] = {"decoded_count": None if errors and no_records else len(result["records"]),
                            "complete": not errors, "state": state}
    return result
