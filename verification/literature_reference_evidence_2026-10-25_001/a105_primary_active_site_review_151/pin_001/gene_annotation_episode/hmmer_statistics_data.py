"""Populate hmmstat's numerical sheet from supplied native bytes.

Native printed statistics are retained separately from model probabilities and
independent calculations. A label is not a model identity: native idx joins the
ordered source occurrences, with label/count/length checks. No execution or
acquisition occurs here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re

from .hmmer_model_data import OCCURRENCE_FIELDS, extract_hmmer_models


SCHEMA = "hmmer_statistics_sheet_v1"
EXTRACTION_SCHEMA = "hmmer_statistics_summary_v1"
FIELDS = ("idx", "name", "accession", "nseq", "eff_nseq", "M", "relent", "info", "p_relE", "compKL")
NUMERIC_FIELDS = frozenset(FIELDS) - {"name", "accession"}
ISSUE_CODES = frozenset({"operation_invalid", "payload_invalid", "occurrence_invalid",
    "occurrence_size_mismatch", "occurrence_digest_mismatch", "capture_incomplete",
    "summary_columns_invalid", "summary_token_invalid", "summary_nonfinite",
    "text_encoding_invalid", "summary_index_order", "models_missing_or_repeated",
    "model_extraction_mismatch", "summary_missing_or_repeated", "summary_stdout_conflict",
    "model_population_mismatch", "association_conflict", "association_unresolved"})
_INTEGER = re.compile(r"[+-]?\d+\Z")
_REAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def _issue(code, *, field=None, record_key=None, stage="extraction", **details):
    assert code in ISSUE_CODES
    return {"code": code, "stage": stage, "record_key": record_key,
            "field": field, "details": details}


def valid_operation(operation):
    return (type(operation) is dict and set(operation) == {"program", "mode", "engine_version", "settings"}
            and operation["program"] == "hmmstat" and operation["mode"] == "summary"
            and (operation["engine_version"] is None or type(operation["engine_version"]) is str)
            and operation["settings"] == {})


def _occurrence_valid(occurrence):
    return (type(occurrence) is dict and set(occurrence) == OCCURRENCE_FIELDS
            and all(type(occurrence[key]) is str and occurrence[key]
                    for key in ("occurrence_id", "role", "artifact_ref"))
            and occurrence["direction"] in ("input", "output")
            and occurrence["completeness"] in ("complete", "partial", "unknown")
            and type(occurrence["ordinal"]) is int and occurrence["ordinal"] >= 0
            and type(occurrence["size_bytes"]) is int and occurrence["size_bytes"] >= 0
            and type(occurrence["sha256"]) is str
            and re.fullmatch(r"[0-9a-fA-F]{64}", occurrence["sha256"]) is not None)


def _payload_issues(content, occurrence):
    issues = []
    if not isinstance(content, bytes):
        issues.append(_issue("payload_invalid", field="content"))
    if not _occurrence_valid(occurrence):
        issues.append(_issue("occurrence_invalid", field="occurrence"))
    if issues:
        return issues
    if len(content) != occurrence["size_bytes"]:
        issues.append(_issue("occurrence_size_mismatch", field="occurrence.size_bytes"))
    if hashlib.sha256(content).hexdigest() != occurrence["sha256"].lower():
        issues.append(_issue("occurrence_digest_mismatch", field="occurrence.sha256"))
    if occurrence["completeness"] != "complete":
        issues.append(_issue("capture_incomplete", field="occurrence.completeness"))
    return issues


def _number(token, field):
    integer = field in {"idx", "nseq", "M"}
    if token.lower().lstrip("+-") in {"nan", "inf", "infinity"}:
        return None, "nonfinite"
    if not (_INTEGER if integer else _REAL).fullmatch(token):
        return None, "invalid"
    try:
        value = int(token) if integer else float(token)
        if not math.isfinite(value):
            return None, "nonfinite"
    except (ValueError, OverflowError):
        return None, "invalid"
    if field in {"nseq", "eff_nseq"} and value == -1:
        return None, "native_missing_sentinel"
    if ((field in {"idx", "M"} and value < 1)
            or (field in {"nseq", "eff_nseq"} and value < 0)):
        return None, "invalid"
    return value, "present"


def parse_hmmstat_summary(content: bytes, *, occurrence, operation):
    """Parse every native ten-column row; malformed rows stay explicit."""
    result = {"schema": EXTRACTION_SCHEMA, "occurrence": deepcopy(occurrence),
              "rows": [], "population": {"decoded_count": None, "complete": False, "state": "invalid"},
              "issues": _payload_issues(content, occurrence)}
    if not valid_operation(operation):
        result["issues"].append(_issue("operation_invalid", field="operation"))
    if not isinstance(content, bytes) or not _occurrence_valid(occurrence):
        return result
    offset = 0
    for line_number, raw in enumerate(content.splitlines(keepends=True), 1):
        start, offset = offset, offset + len(raw)
        try:
            text = raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            result["issues"].append(_issue("text_encoding_invalid", field="summary", line=line_number))
            continue
        if not text or text.startswith("#"):
            continue
        ordinal = len(result["rows"])
        key = occurrence["occurrence_id"] + "#summary/" + str(ordinal)
        tokens = text.split()
        values, states = dict.fromkeys(FIELDS), dict.fromkeys(FIELDS, "invalid")
        row = {"record_key": key, "locator": {"artifact_ref": occurrence["artifact_ref"],
            "record_ordinal": ordinal, "byte_start": start, "byte_end": offset,
            "line_start": line_number, "line_end": line_number},
            "tokens": tokens, "values": values, "states": states}
        result["rows"].append(row)
        if len(tokens) != len(FIELDS):
            result["issues"].append(_issue("summary_columns_invalid", record_key=key,
                                          field="tokens", count=len(tokens)))
            continue
        for field, token in zip(FIELDS, tokens):
            if field in NUMERIC_FIELDS:
                values[field], states[field] = _number(token, field)
            else:
                values[field] = None if field == "accession" and token == "-" else token
                states[field] = "missing" if values[field] is None else "present"
            if states[field] in {"invalid", "nonfinite"}:
                result["issues"].append(_issue("summary_nonfinite" if states[field] == "nonfinite"
                    else "summary_token_invalid", record_key=key, field=field, token=token))
        if states["idx"] == "present" and values["idx"] != ordinal + 1:
            result["issues"].append(_issue("summary_index_order", record_key=key, field="idx"))
    # A nonfinite numerical statistic does not make the captured row population unknown.
    framing_errors = [x for x in result["issues"] if x["code"] != "summary_nonfinite"]
    result["population"] = {"decoded_count": len(result["rows"]), "complete": not framing_errors,
        "state": "partial" if framing_errors and result["rows"] else "invalid" if framing_errors else "decoded"}
    return result


def _header(record, tag):
    values = [row.get("value") for row in record.get("headers", [])
              if isinstance(row, dict) and row.get("tag") == tag]
    return values[0] if len(values) == 1 else None


def _map_payloads(mapping, direction, issues, occurrences):
    result = {}
    if type(mapping) is not dict:
        issues.append(_issue("payload_invalid", field=direction))
        return result
    for role, payloads in mapping.items():
        if type(payloads) is not list:
            issues.append(_issue("payload_invalid", field=role))
            continue
        result[role] = []
        for ordinal, payload in enumerate(payloads):
            if type(payload) is not dict or set(payload) != {"occurrence", "content"}:
                issues.append(_issue("payload_invalid", field=role))
                continue
            occurrence = payload["occurrence"]
            problems = _payload_issues(payload["content"], occurrence)
            issues.extend(problems)
            if not _occurrence_valid(occurrence) or not isinstance(payload["content"], bytes):
                continue
            if occurrence["role"] != role or occurrence["direction"] != direction or occurrence["ordinal"] != ordinal:
                issues.append(_issue("occurrence_invalid", field=role))
                continue
            if any(old["occurrence_id"] == occurrence["occurrence_id"] for old in occurrences):
                issues.append(_issue("occurrence_invalid", field="occurrence_id", duplicate=occurrence["occurrence_id"]))
                continue
            occurrences.append(deepcopy(occurrence))
            result[role].append(payload)
    return result


def populate_hmmstat_sheet(*, operation, inputs, outputs, model_extraction):
    """Bind a supplied M1 extraction and native summary to actual occurrences."""
    sheet = {"schema": SCHEMA, "operation": deepcopy(operation), "artifact_occurrences": [],
             "model_extraction": deepcopy(model_extraction), "summary": None,
             "native_rows": [], "associations": [], "issues": []}
    issues = sheet["issues"]
    if not valid_operation(operation):
        issues.append(_issue("operation_invalid", field="operation"))
    inputs = _map_payloads(inputs, "input", issues, sheet["artifact_occurrences"])
    outputs = _map_payloads(outputs, "output", issues, sheet["artifact_occurrences"])
    models = inputs.get("models", [])
    bound = False
    if len(models) != 1:
        issues.append(_issue("models_missing_or_repeated", field="models", count=len(models)))
    elif type(model_extraction) is dict:
        actual = extract_hmmer_models(models[0]["content"], occurrence=models[0]["occurrence"],
                                     format=model_extraction.get("format"))
        bound = actual == model_extraction and actual["population"]["state"] != "invalid"
        if not bound:
            issues.append(_issue("model_extraction_mismatch", field="model_extraction"))
    else:
        issues.append(_issue("model_extraction_mismatch", field="model_extraction"))
    summaries = outputs.get("summary", outputs.get("stdout", []))
    if len(summaries) != 1:
        issues.append(_issue("summary_missing_or_repeated", field="summary", count=len(summaries)))
        return sheet
    if "summary" in outputs and "stdout" in outputs and any(
            row["content"] != summaries[0]["content"] for row in outputs["stdout"]):
        issues.append(_issue("summary_stdout_conflict", field="summary"))
    summary = parse_hmmstat_summary(**summaries[0], operation=operation)
    sheet["summary"] = {key: deepcopy(summary[key]) for key in ("schema", "occurrence", "population")}
    sheet["native_rows"] = summary["rows"]
    issues.extend(summary["issues"])
    if any(item["code"] in {"occurrence_invalid", "occurrence_size_mismatch", "occurrence_digest_mismatch"}
           for item in summary["issues"]):
        bound = False
    records = model_extraction.get("records", []) if bound else []
    complete = bound and model_extraction["population"]["complete"]
    if complete and summary["population"]["complete"] and len(records) != len(summary["rows"]):
        issues.append(_issue("model_population_mismatch", field="native_rows", expected=len(records), actual=len(summary["rows"])))
    indices = [row["values"]["idx"] for row in summary["rows"]]
    for ordinal, row in enumerate(summary["rows"]):
        idx = row["values"]["idx"]
        candidates = [records[idx - 1]] if type(idx) is int and 1 <= idx <= len(records) else []
        problems = []
        if candidates:
            model = candidates[0]
            for field, expected in (("name", _header(model, "NAME")), ("accession", _header(model, "ACC")),
                                    ("M", model.get("length"))):
                if row["values"][field] != expected or (field != "accession" and expected is None):
                    problems.append(field)
            for field, expected in (("nseq", model.get("sequence_count")),
                                    ("eff_nseq", model.get("effective_sequence_count"))):
                value = row["values"][field]
                if value is not None and expected is not None and abs(value - expected) > (0.0051 if field == "eff_nseq" else 0):
                    problems.append(field)
            if indices.count(idx) != 1 or idx != ordinal + 1:
                problems.append("idx")
        else:
            problems.append("model_unavailable")
        state = "validated" if not problems else "conflicting" if candidates else "unresolved"
        association = {"native_record_key": row["record_key"],
            "model_record_keys": [model["record_key"] for model in candidates],
            "state": state, "fields": problems}
        sheet["associations"].append(association)
        if problems:
            issues.append(_issue("association_conflict" if candidates else "association_unresolved",
                stage="association", record_key=row["record_key"], field="model_record_keys", fields=problems))
    return sheet
