"""Pure numerical-body extraction for supplied HMMER model representations.

The grammar is p7_hmmfile.c:WriteASCII/read_asc30hmm (HMMER 3.4), revisions
a--f. The separate HMMER3 binary and HMMER2 ASCII readers retain their native
representations in this same envelope. No conversion, acquisition, execution,
file access, confidence assignment or credit occurs.

Record identity is the caller's artifact occurrence plus its zero-based model
ordinal. Names and identical bytes never collapse occurrences. ``decoded_count``
counts returned records, including explicitly partial records; ``complete`` is
false if decoding, framing or supplied acquisition completeness is incomplete.
Raw ordered headers, every available body cell and annotations survive errors.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re


SCHEMA = "hmmer_model_extraction_v1"
FORMATS = frozenset({"hmmer3_ascii", "hmmer2_ascii", "hmmer_binary"})
OCCURRENCE_FIELDS = frozenset({"occurrence_id", "direction", "role", "ordinal",
                             "artifact_ref", "sha256", "size_bytes", "completeness"})
ALPHABETS = {"amino": list("ACDEFGHIKLMNPQRSTVWY"), "DNA": list("ACGT"),
             "RNA": list("ACGU")}
TRANSITIONS = ["m->m", "m->i", "m->d", "i->m", "i->i", "d->m", "d->d"]
ISSUE_CODES = frozenset({
    "content_type_invalid", "occurrence_invalid", "occurrence_size_mismatch",
    "occurrence_digest_mismatch", "capture_incomplete", "format_invalid",
    "decoder_unavailable", "text_encoding_invalid", "signature_invalid",
    "revision_unsupported", "record_unterminated", "header_missing",
    "header_duplicate", "header_width_invalid", "header_number_invalid",
    "header_value_invalid", "header_revision_incompatible", "alphabet_invalid",
    "alphabet_symbols_invalid", "calibration_invalid", "calibration_incomplete",
    "body_missing", "transition_labels_invalid", "distribution_missing",
    "distribution_width_invalid", "probability_token_invalid", "probability_underflow",
    "position_invalid", "position_order_invalid", "length_mismatch",
    "annotation_width_invalid", "annotation_value_invalid", "mixed_alphabets",
    "mixed_revisions",
    "binary_layout_unsupported", "binary_stream_layout_changed",
    "binary_flags_unknown", "binary_field_truncated", "binary_length_invalid",
    "binary_string_invalid", "binary_native_value_invalid",
    "binary_probability_invalid",
})
_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_REAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_TAGS = {f"HMMER3/{revision}" for revision in "abcdef"}


def _issue(code, *, record_key=None, position=None, field=None, line=None,
           details=None):
    assert code in ISSUE_CODES
    return {"code": code, "stage": "extraction", "record_key": record_key,
            "position": position, "field": field, "line": line,
            "details": details or {}}


def _numeric(token, *, integer=False, minimum=None, positive=False, maximum=None):
    if not isinstance(token, str) or not (_INTEGER if integer else _REAL).fullmatch(token):
        return None
    try:
        value = int(token) if integer else float(token)
        if not math.isfinite(value) or (minimum is not None and value < minimum):
            return None
        if (positive and value <= 0) or (maximum is not None and value > maximum):
            return None
        return value
    except (ValueError, OverflowError):
        return None


def _occurrence_valid(occurrence):
    if not isinstance(occurrence, dict) or occurrence.keys() != OCCURRENCE_FIELDS:
        return False
    if any(type(occurrence[key]) is not str or not occurrence[key]
           for key in ("occurrence_id", "role", "artifact_ref")):
        return False
    return (isinstance(occurrence["direction"], str) and occurrence["direction"] in {"input", "output"}
            and isinstance(occurrence["completeness"], str)
            and occurrence["completeness"] in {"complete", "partial", "unknown"}
            and type(occurrence["ordinal"]) is int and occurrence["ordinal"] >= 0
            and type(occurrence["size_bytes"]) is int and occurrence["size_bytes"] >= 0
            and isinstance(occurrence["sha256"], str)
            and re.fullmatch(r"[0-9a-fA-F]{64}", occurrence["sha256"]) is not None)


class _Reader:
    def __init__(self, content, occurrence):
        raw_lines = content.splitlines(keepends=True)
        self.lines = [line.decode("utf-8", errors="surrogateescape").rstrip("\r\n")
                      for line in raw_lines]
        self.offsets = [0]
        for line in raw_lines:
            self.offsets.append(self.offsets[-1] + len(line))
        self.occurrence = occurrence

    def record(self, start, end, terminated, ordinal):
        parts = self.lines[start].strip().split(None, 1)
        tag = parts[0]
        key = self.occurrence["occurrence_id"] + "#model/" + str(ordinal)
        record = {
            "record_key": key,
            "locator": {"artifact_ref": self.occurrence["artifact_ref"],
                        "record_ordinal": ordinal, "byte_start": self.offsets[start],
                        "byte_end": self.offsets[end], "line_start": start + 1,
                        "line_end": end},
            "format_tag": tag, "engine_text": parts[1] if len(parts) == 2 else None,
            "headers": [], "alphabet": {"kind": None, "symbols": []},
            "length": None, "sequence_count": None, "effective_sequence_count": None,
            "maximum_length": None, "checksum": None, "flags": {}, "cutoffs": {},
            "calibration": [], "composition": None,
            "initial": {"insert": None, "transitions": None}, "positions": [],
            "terminated": terminated, "issues": [],
        }
        def problem(code, field=None, *, position=None, line=None, **details):
            record["issues"].append(_issue(code, record_key=key, field=field,
                position=position, line=line, details=details))

        for i in range(start, end):
            if any(0xDC80 <= ord(char) <= 0xDCFF for char in self.lines[i]):
                problem("text_encoding_invalid", "text", line=i+1)
        if not terminated:
            problem("record_unterminated", "terminated", line=end)
        stop = end - int(terminated)
        by_tag, body = {}, None
        for i in range(start + 1, stop):
            text = self.lines[i].strip()
            if not text or text.startswith("#"):
                continue
            header_parts = text.split(None, 1)
            name = header_parts[0]
            value = header_parts[1] if len(header_parts) == 2 else ""
            header = {"tag": name, "value": value, "tokens": value.split(), "line": i+1}
            record["headers"].append(header)
            by_tag.setdefault(name, []).append(header)
            if name == "HMM":
                body = i
                record["alphabet"]["symbols"] = header["tokens"][:]
                break

        def single(name, *, required=False):
            entries = by_tag.get(name, [])
            if not entries:
                if required:
                    problem("header_missing", name)
                return None
            if len(entries) > 1:
                problem("header_duplicate", name, line=entries[0]["line"], count=len(entries))
                return None
            return entries[0]

        def scalar(name, **kwargs):
            header = single(name, required=name == "LENG")
            if header is None:
                return None
            if len(header["tokens"]) != 1:
                problem("header_width_invalid", name, line=header["line"])
                return None
            number = _numeric(header["tokens"][0], **kwargs)
            if number is None:
                problem("header_number_invalid", name, line=header["line"], token=header["tokens"][0])
            return number

        for name in ("NAME", "ACC", "DESC"):
            header = single(name, required=name == "NAME")
            if header is not None and (not header["tokens"] or
                    (name != "DESC" and len(header["tokens"]) != 1)):
                problem("header_value_invalid", name, line=header["line"])
        record["length"] = scalar("LENG", integer=True, positive=True)
        record["sequence_count"] = scalar("NSEQ", integer=True, positive=True)
        record["effective_sequence_count"] = scalar("EFFN", minimum=0)
        record["checksum"] = scalar("CKSUM", integer=True, minimum=0, maximum=2**32-1)
        if tag >= "HMMER3/c":
            record["maximum_length"] = scalar("MAXL", integer=True, positive=True)
        elif "MAXL" in by_tag:
            problem("header_revision_incompatible", "MAXL")
        alph = single("ALPH", required=True)
        if alph is not None:
            if len(alph["tokens"]) == 1:
                record["alphabet"]["kind"] = alph["tokens"][0]
            if record["alphabet"]["kind"] not in ALPHABETS:
                problem("alphabet_invalid", "ALPH", line=alph["line"])
        kind, symbols = record["alphabet"]["kind"], record["alphabet"]["symbols"]
        if kind in ALPHABETS and symbols != ALPHABETS[kind]:
            problem("alphabet_symbols_invalid", "alphabet.symbols",
                    line=body+1 if body is not None else None, expected=ALPHABETS[kind], actual=symbols)
        for name in ("RF", "MM", "CONS", "CS", "MAP"):
            if name not in by_tag:
                continue
            header = single(name)
            flag = None
            if header and len(header["tokens"]) == 1 and header["tokens"][0].lower() in {"yes", "no"}:
                flag = header["tokens"][0].lower() == "yes"
            else:
                problem("header_value_invalid", name)
            record["flags"][name] = flag
            if (name == "MM" and tag < "HMMER3/f") or (name == "CONS" and tag < "HMMER3/e"):
                problem("header_revision_incompatible", name)
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
            if len(tokens) not in (1, 2) or (kind == "amino" and len(tokens) != 2):
                problem("header_width_invalid", name, line=header["line"])
            if any(value is None for value in values):
                problem("header_number_invalid", name, line=header["line"])

        expected_stats = ({"VLAMBDA", "VMU", "FTAU"} if tag == "HMMER3/a"
                          else {"MSV", "VITERBI", "FORWARD"})
        seen_stats = []
        for header in by_tag.get("STATS", []):
            tokens = header["tokens"]
            mode = tokens[0] if tokens else None
            statistic = tokens[1] if len(tokens) > 1 else None
            seen_stats.append(statistic.upper() if isinstance(statistic, str) else None)
            names = (["lambda"] if statistic and statistic.upper() == "VLAMBDA" else
                     ["mu"] if statistic and statistic.upper() == "VMU" else
                     ["tau"] if statistic and statistic.upper() == "FTAU" else
                     ["tau", "lambda"] if statistic and statistic.upper() == "FORWARD" else
                     ["mu", "lambda"] if statistic and statistic.upper() in {"MSV", "VITERBI"} else [])
            parameters = []
            for j, token in enumerate(tokens[2:]):
                name = names[j] if j < len(names) else None
                number = _numeric(token, positive=name == "lambda")
                parameters.append({"name": name, "token": token, "value": number,
                    "unit": "inverse_bit" if name == "lambda" else "bit" if name else None})
                if number is None:
                    problem("header_number_invalid", "STATS." + str(statistic), line=header["line"])
            record["calibration"].append({"mode": mode, "statistic": statistic,
                "tokens": tokens[:], "parameters": parameters, "line": header["line"]})
            if (not isinstance(mode, str) or mode.upper() != "LOCAL"
                    or seen_stats[-1] not in expected_stats
                    or len(tokens) != (3 if tag == "HMMER3/a" else 4)):
                problem("calibration_invalid", "STATS", line=header["line"])
        if seen_stats and (set(seen_stats) != expected_stats or len(seen_stats) != 3):
            problem("calibration_incomplete", "STATS")

        if body is None:
            problem("body_missing", "HMM")
            return record
        rows = [(i+1, self.lines[i].split()) for i in range(body+1, stop)
                if self.lines[i].strip() and not self.lines[i].lstrip().startswith("#")]
        cursor = 0
        transition_symbols = []
        if rows:
            transition_symbols = rows[0][1]
            if transition_symbols == TRANSITIONS:
                cursor = 1
            elif any("->" in token for token in transition_symbols):
                cursor = 1
            else:
                transition_symbols = []
        if transition_symbols != TRANSITIONS:
            problem("transition_labels_invalid", "transitions.symbols", line=body+2)
        width = len(ALPHABETS[kind]) if kind in ALPHABETS else len(symbols)
        if not width:
            problem("body_missing", "alphabet.symbols")
            return record

        def distribution(tokens, names, expected, field, position, line):
            cells = []
            if len(tokens) != expected:
                problem("distribution_width_invalid", field, position=position, line=line,
                        expected=expected, actual=len(tokens))
            for j, token in enumerate(tokens):
                cell = {"token": token, "negative_log_probability": None,
                        "probability": None, "state": "invalid"}
                if token == "*":
                    cell.update(probability=0.0, state="structural_zero")
                else:
                    number = _numeric(token, minimum=0)
                    if number is None:
                        problem("probability_token_invalid", field, position=position, line=line,
                                cell=j, token=token)
                    else:
                        probability = math.exp(-number)
                        cell.update(negative_log_probability=number,
                                    probability=probability if probability else None,
                                    state="finite" if probability else "underflow")
                        if not probability:
                            problem("probability_underflow", field, position=position, line=line, cell=j)
                cells.append(cell)
            return {"symbols": names[:], "cells": cells, "line": line}

        annotations = ["MAP"] + (["CONS"] if tag >= "HMMER3/e" else []) + ["RF"]
        annotations += (["MM"] if tag >= "HMMER3/f" else []) + ["CS"]
        def match_like(tokens):
            return bool(tokens and _INTEGER.fullmatch(tokens[0])
                        and len(tokens) >= 1 + width + len(annotations))

        def take(field, position, names, expected):
            nonlocal cursor
            if cursor >= len(rows) or match_like(rows[cursor][1]):
                problem("distribution_missing", field, position=position)
                return None
            line, tokens = rows[cursor]
            cursor += 1
            return distribution(tokens, names, expected, field, position, line)

        if cursor < len(rows) and rows[cursor][1][0] == "COMPO":
            line, tokens = rows[cursor]
            record["composition"] = distribution(tokens[1:], symbols, width, "composition", None, line)
            cursor += 1
        record["initial"]["insert"] = take("initial.insert", 0, symbols, width)
        record["initial"]["transitions"] = take("initial.transitions", 0, transition_symbols, 7)
        while cursor < len(rows):
            line, tokens = rows[cursor]
            cursor += 1
            position = _numeric(tokens[0], integer=True, positive=True)
            ordinal_position = len(record["positions"])
            if position is None:
                problem("position_invalid", "position", line=line, token=tokens[0])
            elif position != ordinal_position + 1:
                problem("position_order_invalid", "position", position=position, line=line,
                        expected=ordinal_position+1)
            entry = {"position": position, "position_token": tokens[0], "line": line,
                     "match": distribution(tokens[1:1+width], symbols, width, "match", position, line),
                     "insert": None, "transitions": None, "annotations": {}, "extra_tokens": []}
            annotation_tokens = tokens[1+width:]
            if len(annotation_tokens) != len(annotations):
                problem("annotation_width_invalid", "annotations", position=position, line=line,
                        expected=len(annotations), actual=len(annotation_tokens))
            for name, token in zip(annotations, annotation_tokens):
                number = _numeric(token, integer=True, minimum=0) if name == "MAP" else token
                if (name == "MAP" and number is None and token != "-") or (name != "MAP" and len(token) != 1):
                    problem("annotation_value_invalid", "annotations."+name, position=position,
                            line=line, token=token)
                if name == "MAP" and token == "-" and record["flags"].get("MAP") is True:
                    problem("annotation_value_invalid", "annotations.MAP", position=position, line=line, token=token)
                entry["annotations"][name] = {"token": token, "value": number}
            entry["extra_tokens"] = annotation_tokens[len(annotations):]
            entry["insert"] = take("insert", position, symbols, width)
            entry["transitions"] = take("transitions", position, transition_symbols, 7)
            record["positions"].append(entry)
        if record["length"] != len(record["positions"]):
            problem("length_mismatch", "positions", expected=record["length"], actual=len(record["positions"]))
        return record


def extract_hmmer_models(content: bytes, *, occurrence: dict, format: str) -> dict:
    """Extract retained model data and explicit partial/unsupported states.

    The eight-field occurrence is copied unchanged. Digest/size mismatches do
    not discard decoded records, but invalidate their artifact association.
    Invalid argument shapes return structured issues, without invented identity.
    UTF-8 metadata is preserved; invalid UTF-8 bytes use reversible surrogate
    escapes and explicit issues, leaving earlier valid records available.
    """
    result = {"schema": SCHEMA, "occurrence": deepcopy(occurrence), "format": format,
              "records": [], "population": {"decoded_count": None, "complete": False,
                                            "state": "invalid"}, "issues": []}
    if not isinstance(content, bytes):
        result["issues"].append(_issue("content_type_invalid", field="content"))
    if not _occurrence_valid(occurrence):
        result["issues"].append(_issue("occurrence_invalid", field="occurrence"))
    if not isinstance(format, str) or format not in FORMATS:
        result["issues"].append(_issue("format_invalid", field="format"))
    if result["issues"]:
        return result
    if len(content) != occurrence["size_bytes"]:
        result["issues"].append(_issue("occurrence_size_mismatch", field="occurrence.size_bytes",
            details={"supplied": occurrence["size_bytes"], "actual": len(content)}))
    digest = hashlib.sha256(content).hexdigest()
    if digest != occurrence["sha256"].lower():
        result["issues"].append(_issue("occurrence_digest_mismatch", field="occurrence.sha256",
            details={"supplied": occurrence["sha256"], "actual": digest}))
    if occurrence["completeness"] != "complete":
        result["issues"].append(_issue("capture_incomplete", field="occurrence.completeness",
                                      details={"supplied": occurrence["completeness"]}))
    if format != "hmmer3_ascii":
        if format == "hmmer_binary":
            from .hmmer_model_binary import decode_hmmer3_binary
            decoded = decode_hmmer3_binary(content, occurrence=occurrence)
        else:
            from .hmmer_model_legacy import decode_hmmer2_ascii
            decoded = decode_hmmer2_ascii(content, occurrence=occurrence)
        result["records"] = decoded["records"]
        result["issues"].extend(decoded["issues"])
        result["population"] = decoded["population"]
        if any(item["code"].startswith("occurrence_") for item in result["issues"]):
            result["population"].update(complete=False, state="invalid")
        elif occurrence["completeness"] != "complete":
            result["population"]["complete"] = False
            if result["population"]["state"] == "decoded":
                result["population"]["state"] = "partial"
        return result
    reader, index = _Reader(content, occurrence), 0
    while index < len(reader.lines):
        text = reader.lines[index].strip()
        if not text or text.startswith("#"):
            index += 1
            continue
        tag = text.split()[0]
        if tag not in _TAGS:
            code = "revision_unsupported" if tag.startswith("HMMER3/") else "signature_invalid"
            result["issues"].append(_issue(code, field="format_tag", line=index+1, details={"token": tag}))
            index += 1
            continue
        end, terminated = index + 1, False
        while end < len(reader.lines):
            value = reader.lines[end].strip()
            if value == "//":
                end, terminated = end + 1, True
                break
            if value.startswith("HMMER"):
                break
            end += 1
        record = reader.record(index, end, terminated, len(result["records"]))
        result["records"].append(record)
        result["issues"].extend(record["issues"])
        index = end
    for field, values, code in (
        ("alphabet.kind", {r["alphabet"]["kind"] for r in result["records"]}, "mixed_alphabets"),
        ("format_tag", {r["format_tag"] for r in result["records"]}, "mixed_revisions"),
    ):
        if len(values - {None}) > 1:
            result["issues"].append(_issue(code, field=field))
    errors = [item for item in result["issues"] if item["code"] != "probability_underflow"]
    association_error = any(item["code"].startswith("occurrence_") for item in errors)
    unsupported = (not result["records"] and any(item["code"] == "revision_unsupported" for item in errors))
    state = ("invalid" if association_error else "unsupported" if unsupported
             else "invalid" if errors and not result["records"]
             else "partial" if errors else "decoded")
    result["population"] = {"decoded_count": None if unsupported else len(result["records"]), "complete": not errors,
                            "state": state}
    return result
