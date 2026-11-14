"""Pure retained-output reader for HMMER 3.4 ``hmmsim`` (261/S1).

No execution or I/O occurs here. Supplied M1 model occurrences establish serial
identity; native names only validate that order. Simulation scores are generated
model measurements, never biological observations or annotation probabilities.
The original bytes of binary segments are JSON-safe hexadecimal strings.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re
import struct


SCHEMA = "hmmer_simulation_sheet_v1"
OCCURRENCE_FIELDS = frozenset({"occurrence_id", "direction", "role", "ordinal",
                             "artifact_ref", "sha256", "size_bytes", "completeness"})
ROW_FIELDS = {
    "summary": frozenset({"name", "tokens", "values", "states", "raw_text"}),
    "scores": frozenset({"values", "states", "declared_population", "observed_count",
                         "original_bytes_hex", "completeness", "representation", "tokens"}),
    "alignments": frozenset({"sample_ordinal", "trace_state_count", "score",
                             "tokens", "states", "raw_text"}),
    "filter": frozenset({"name", "count", "denominator", "fraction", "tokens",
                         "states", "raw_text"}),
    "xy_series": frozenset({"series_kind", "series_ordinal", "meaning", "points",
                            "tokens", "legends", "delimiter", "raw_text", "complete"}),
}
SUMMARY_FIELDS = {
    mode: ("tailp", "mu", "lambda", "E10", "mufix", "E10fix")
          + (() if mode == "forward" else ("mufix2", "E10fix2"))
          + ("pmu", "plambda", "E10p")
    for mode in ("viterbi", "msv", "forward", "hybrid")
}
SUMMARY_UNITS = {name: ("inverse_bit" if name in {"lambda", "plambda"}
                       else "dimensionless" if name == "tailp"
                       else "sequence" if name.startswith("E10")
                       else "trace_state" if name in {"almean", "alsd"} else "bit")
                 for name in (*SUMMARY_FIELDS["viterbi"], "almean", "alsd")}
ISSUE_CODES = frozenset({
    "operation_invalid", "engine_version_unsupported", "setting_missing", "setting_invalid",
    "mode_flag_conflict", "style_flag_conflict", "setting_conflict", "fast_hybrid_unsupported",
    "fast_traceback_unverified", "traceback_requires_viterbi", "mpi_order_unverified",
    "payload_map_invalid", "payload_invalid", "occurrence_invalid", "occurrence_duplicate",
    "occurrence_order_invalid", "occurrence_size_mismatch", "occurrence_digest_mismatch",
    "capture_incomplete", "content_type_invalid", "model_extraction_invalid",
    "model_extraction_mismatch", "model_record_invalid", "model_alphabet_mismatch",
    "model_name_mismatch", "model_association_unresolved", "model_population_missing",
    "output_missing", "output_empty", "forward_filter_unavailable", "abi_missing", "abi_invalid",
    "score_segment_incomplete", "score_population_mismatch", "number_invalid", "number_nonfinite",
    "summary_width_invalid", "summary_population_mismatch", "summary_tail_mismatch",
    "hybrid_calibration_undetermined", "alignment_width_invalid", "alignment_population_mismatch",
    "filter_width_invalid", "filter_count_invalid", "filter_population_mismatch",
    "xy_point_invalid", "xy_unterminated", "xy_series_count_invalid", "xy_name_mismatch",
    "text_encoding_invalid", "tail_schedule_missing", "tail_schedule_invalid", "verbose_population_mismatch",
})
_REAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
_INT = re.compile(r"[+-]?\d+\Z")
_MODES = {"--vit": "viterbi", "--msv": "msv", "--fwd": "forward", "--hyb": "hybrid"}
_STYLES = {"--fs", "--sw", "--ls", "--s"}
_ROLES = {"summary", "scores", "alignments", "filter", "survival", "expected_counts", "stdout", "stderr"}


def _issue(code, *, record_key=None, field=None, occurrence_id=None, details=None):
    assert code in ISSUE_CODES
    return {"code": code, "stage": "parsing", "record_key": record_key,
            "field": field, "occurrence_id": occurrence_id, "details": details or {}}


def recorded_tail_masses(settings):
    """Return an explicit schedule only, never a guessed native default."""
    values = settings.get("tail_masses")
    if values is not None:
        if (not isinstance(values, list) or not values or
                any(type(x) not in (int, float) or not math.isfinite(x) or not 0 < x <= 1 for x in values)):
            return None, "tail_schedule_invalid"
        return deepcopy(values), None
    required = ("--tmin", "--tmax", "--tpoints", "--tlinear")
    if not all(key in settings for key in required):
        return None, "tail_schedule_missing"
    lo, hi, n, linear = (settings[key] for key in required)
    if (type(lo) not in (int, float) or type(hi) not in (int, float) or
            not math.isfinite(lo) or not math.isfinite(hi) or not 0 < lo <= hi <= 1 or
            type(n) is not int or n < 1 or type(linear) is not bool or (n > 1 and lo == hi)):
        return None, "tail_schedule_invalid"
    if n == 1:
        return [lo], None
    # Match the source's repeated addition/multiplication, not rounded summary values.
    schedule, value = [], lo
    step = (hi-lo)/(n-1) if linear else math.exp(math.log(hi/lo)/(n-1))
    for _ in range(n):
        schedule.append(min(value, 1.0))
        value = value + step if linear else value * step
    return schedule, None


def _settings(operation, issues):
    if (not isinstance(operation, dict) or
            set(operation) != {"program", "mode", "engine_version", "settings"} or
            operation.get("program") != "hmmsim" or not isinstance(operation.get("mode"), str) or
            operation.get("mode") not in SUMMARY_FIELDS or
            not isinstance(operation.get("settings"), dict)):
        issues.append(_issue("operation_invalid", field="operation"))
        return {}, False
    settings = operation["settings"]
    if operation["engine_version"] != "3.4":
        issues.append(_issue("engine_version_unsupported", field="engine_version"))
    for field in ("-N", "-L"):
        if field not in settings:
            issues.append(_issue("setting_missing", field=field))
        elif type(settings[field]) is not int or settings[field] <= 0:
            issues.append(_issue("setting_invalid", field=field))
    flags = [mode for flag, mode in _MODES.items() if settings.get(flag) is True]
    if len(flags) > 1 or (flags and flags != [operation["mode"]]):
        issues.append(_issue("mode_flag_conflict", field="mode"))
    styles = [s for s in _STYLES if settings.get(s) is True]
    style = settings.get("style")
    if isinstance(style, str) and not style.startswith("--"):
        style = "--" + style
    if style is None and len(styles) == 1:
        style = styles[0]
    if style is None:
        issues.append(_issue("setting_missing", field="style"))
    elif not isinstance(style, str) or style not in _STYLES:
        issues.append(_issue("setting_invalid", field="style"))
    if len(styles) > 1 or (styles and styles != [style]):
        issues.append(_issue("style_flag_conflict", field="style"))
    for flag in set(_MODES) | _STYLES | {"--fast", "-a", "-v", "--mpi", "--tlinear"}:
        if flag in settings and type(settings[flag]) is not bool:
            issues.append(_issue("setting_invalid", field=flag))
    fast = settings.get("fast", settings.get("--fast"))
    if type(fast) is not bool:
        issues.append(_issue("setting_missing" if fast is None else "setting_invalid", field="fast"))
    if "fast" in settings and "--fast" in settings and settings["fast"] != settings["--fast"]:
        issues.append(_issue("setting_conflict", field="fast"))
    seed = settings.get("seed", settings.get("--seed"))
    if type(seed) is not int or seed < 0:
        issues.append(_issue("setting_missing" if seed is None else "setting_invalid", field="seed"))
    if "seed" in settings and "--seed" in settings and settings["seed"] != settings["--seed"]:
        issues.append(_issue("setting_conflict", field="seed"))
    if fast and operation["mode"] == "hybrid":
        issues.append(_issue("fast_hybrid_unsupported", field="fast"))
    if fast and settings.get("-a"):
        issues.append(_issue("fast_traceback_unverified", field="-a"))
    if settings.get("-a") and operation["mode"] != "viterbi":
        issues.append(_issue("traceback_requires_viterbi", field="-a"))
    if settings.get("--mpi"):
        issues.append(_issue("mpi_order_unverified", field="--mpi"))
    if operation["mode"] == "forward" and "tail_masses" in settings and all(k in settings for k in ("--tmin", "--tmax", "--tpoints", "--tlinear")):
        selected, error = recorded_tail_masses(settings)
        native, native_error = recorded_tail_masses({k: v for k, v in settings.items() if k != "tail_masses"})
        if error or native_error or len(selected) != len(native) or any(abs(a-b) > 1e-12 for a, b in zip(selected, native)):
            issues.append(_issue("setting_conflict", field="tail_masses"))
    return settings, not issues


def _occurrence_valid(o):
    return (isinstance(o, dict) and set(o) == OCCURRENCE_FIELDS and
            all(isinstance(o[k], str) and o[k] for k in ("occurrence_id", "artifact_ref", "role")) and
            o["direction"] in ("input", "output") and o["completeness"] in ("complete", "partial", "unknown") and
            type(o["ordinal"]) is int and o["ordinal"] >= 0 and
            type(o["size_bytes"]) is int and o["size_bytes"] >= 0 and
            isinstance(o["sha256"], str) and re.fullmatch(r"[0-9a-fA-F]{64}", o["sha256"]) is not None)


def populate_hmmsim_sheet(*, operation, inputs, outputs, model_extraction, native_abi=None):
    """Populate S1 from supplied bytes and exact M1 envelope(s), without I/O.

    ``model_extraction`` is one M1 envelope, or an ordered list of M1 envelopes
    for multiple input occurrences. An absent output has no occurrence; a zero
    byte output keeps its occurrence and produces an explicit empty-output issue.
    Unknown ABI leaves values/count unknown while retaining the original bytes.
    Locators are zero-based half-open bytes and one-based inclusive lines.
    """
    sheet = {"schema": SCHEMA, "operation": deepcopy(operation), "artifact_occurrences": [],
             "input_records": [], "native_rows": [], "associations": [],
             "native_abi": deepcopy(native_abi), "issues": []}
    issues = sheet["issues"]
    settings, operation_valid = _settings(operation, issues)
    mode = operation.get("mode") if isinstance(operation, dict) and isinstance(operation.get("mode"), str) else None
    n = settings.get("-N")
    n = n if type(n) is int and n > 0 else None
    seen, valid_payloads, validity = set(), {"input": {}, "output": {}}, {}
    for direction, mapping, allowed in (("input", inputs, {"models"}), ("output", outputs, _ROLES)):
        if not isinstance(mapping, dict):
            issues.append(_issue("payload_map_invalid", field=direction))
            continue
        for role, payloads in mapping.items():
            if role not in allowed or not isinstance(payloads, list):
                issues.append(_issue("payload_map_invalid", field=str(role)))
                continue
            valid_payloads[direction][role] = []
            for ordinal, payload in enumerate(payloads):
                if not isinstance(payload, dict) or set(payload) != {"occurrence", "content"}:
                    issues.append(_issue("payload_invalid", field=role))
                    continue
                o, content = payload["occurrence"], payload["content"]
                if not _occurrence_valid(o):
                    issues.append(_issue("occurrence_invalid", field=role))
                    continue
                sheet["artifact_occurrences"].append(deepcopy(o))
                oid, valid = o["occurrence_id"], True
                if oid in seen:
                    issues.append(_issue("occurrence_duplicate", occurrence_id=oid))
                    validity[oid] = False
                    continue
                seen.add(oid)
                if o["direction"] != direction or o["role"] != role or o["ordinal"] != ordinal:
                    issues.append(_issue("occurrence_order_invalid", occurrence_id=oid))
                    valid = False
                if not isinstance(content, bytes):
                    issues.append(_issue("content_type_invalid", occurrence_id=oid))
                    continue
                if len(content) != o["size_bytes"]:
                    issues.append(_issue("occurrence_size_mismatch", occurrence_id=oid))
                    valid = False
                if hashlib.sha256(content).hexdigest() != o["sha256"].lower():
                    issues.append(_issue("occurrence_digest_mismatch", occurrence_id=oid))
                    valid = False
                if o["completeness"] != "complete":
                    issues.append(_issue("capture_incomplete", occurrence_id=oid))
                validity[oid] = valid
                valid_payloads[direction][role].append(payload)

    models, model_ok = [], []
    extraction_list = model_extraction if isinstance(model_extraction, list) else [model_extraction]
    supplied_models = valid_payloads["input"].get("models", [])
    if len(extraction_list) != len(supplied_models):
        issues.append(_issue("model_extraction_mismatch", field="model_extraction"))
    for ordinal, payload in enumerate(supplied_models):
        o, content = payload["occurrence"], payload["content"]
        extraction = extraction_list[ordinal] if ordinal < len(extraction_list) else None
        if (not isinstance(extraction, dict) or set(extraction) != {"schema", "occurrence", "format", "records", "population", "issues"}
                or extraction.get("schema") != "hmmer_model_extraction_v1" or
                not isinstance(extraction.get("records"), list)):
            issues.append(_issue("model_extraction_invalid", occurrence_id=o["occurrence_id"]))
            continue
        if extraction["occurrence"] != o:
            issues.append(_issue("model_extraction_mismatch", occurrence_id=o["occurrence_id"]))
            continue
        for ri, record in enumerate(extraction["records"]):
            if not isinstance(record, dict):
                issues.append(_issue("model_record_invalid", occurrence_id=o["occurrence_id"]))
                continue
            models.append(deepcopy(record))
            locator = record.get("locator", {})
            start, end = locator.get("byte_start"), locator.get("byte_end")
            valid = (validity[o["occurrence_id"]] and
                     record.get("record_key") == o["occurrence_id"] + "#model/" + str(ri) and
                     locator.get("record_ordinal") == ri and locator.get("artifact_ref") == o["artifact_ref"] and
                     type(start) is int and type(end) is int and 0 <= start < end <= len(content) and
                     record.get("terminated") is True and bool(record.get("positions")) and
                     len(record["positions"]) == record.get("length") and
                     not any(i.get("code") != "probability_underflow" for i in record.get("issues", [])))
            model_ok.append(valid)
            if not valid:
                issues.append(_issue("model_record_invalid", record_key=record.get("record_key")))
    sheet["input_records"] = models
    alphabets = [m.get("alphabet", {}).get("kind") for m in models]
    if len(set(alphabets)) > 1 or any(a not in {"amino", "DNA", "RNA"} for a in alphabets):
        issues.append(_issue("model_alphabet_mismatch", field="alphabet"))
        model_ok = [False] * len(models)
    if not models:
        issues.append(_issue("model_population_missing", field="models"))

    def name_at(i):
        if i is None or i >= len(models):
            return None
        names = [h.get("value") for h in models[i].get("headers", []) if h.get("tag") == "NAME"]
        return names[0] if len(names) == 1 else None

    def number(token, record_key, field, integer=False):
        value, state = None, "invalid"
        if isinstance(token, str) and (_INT if integer else _REAL).fullmatch(token):
            try:
                value = int(token) if integer else float(token)
                state = "present" if math.isfinite(value) else "nonfinite"
            except (ValueError, OverflowError):
                state = "nonfinite"
        elif isinstance(token, str) and token.lower().lstrip("+-") in {"inf", "infinity", "nan"}:
            state = "nonfinite"
        if state != "present":
            issues.append(_issue("number_nonfinite" if state == "nonfinite" else "number_invalid",
                                 record_key=record_key, field=field, details={"token": token}))
            value = None
        return value, state

    def row(payload, kind, ordinal, start, end, line_start, line_end, data, mi, *, named=None, method="serial_input_order"):
        o = payload["occurrence"]
        key = o["occurrence_id"] + "#" + kind + "/" + str(ordinal)
        if named is not None and mi is not None and mi < len(models) and name_at(mi) != named:
            issues.append(_issue("model_name_mismatch", record_key=key,
                                 details={"expected": name_at(mi), "actual": named}))
            model_ok[mi] = False
        resolved = (operation_valid and validity.get(o["occurrence_id"], False) and
                    mi is not None and mi < len(models) and model_ok[mi] and name_at(mi) is not None)
        keys = [models[mi]["record_key"]] if resolved else []
        result = {"kind": kind, "record_key": key,
                  "locator": {"artifact_ref": o["artifact_ref"], "occurrence_id": o["occurrence_id"],
                              "record_ordinal": ordinal, "byte_start": start, "byte_end": end,
                              "line_start": line_start, "line_end": line_end},
                  "model_keys": keys, "payload": data}
        assert set(data) == ROW_FIELDS[kind]
        sheet["native_rows"].append(result)
        sheet["associations"].append({"record_key": key, "model_keys": keys[:],
            "state": "resolved" if resolved else "unresolved", "method": method})
        if not resolved:
            issues.append(_issue("model_association_unresolved", record_key=key))
        return result

    def lines(payload):
        offset = 0
        for index, raw in enumerate(payload["content"].splitlines(keepends=True)):
            text = raw.decode("utf-8", errors="surrogateescape").rstrip("\r\n")
            if any(0xDC80 <= ord(char) <= 0xDCFF for char in text):
                issues.append(_issue("text_encoding_invalid", occurrence_id=payload["occurrence"]["occurrence_id"]))
            yield index + 1, offset, offset + len(raw), text
            offset += len(raw)

    out = valid_payloads["output"]
    for role, flag in (("scores", "--xfile"), ("alignments", "--afile"), ("filter", "--ffile"),
                       ("survival", "--pfile"), ("expected_counts", "--efile")):
        if settings.get(flag) and not out.get(role):
            issues.append(_issue("output_missing", field=role))
    for role, payloads in out.items():
        for payload in payloads:
            if not payload["content"] and role not in {"stdout", "stderr"}:
                code = "forward_filter_unavailable" if role == "filter" and mode == "forward" else "output_empty"
                issues.append(_issue(code, field=role, occurrence_id=payload["occurrence"]["occurrence_id"]))

    schedule, schedule_issue = recorded_tail_masses(settings) if mode == "forward" else ([1.0], None)
    if schedule_issue:
        issues.append(_issue(schedule_issue, field="tail_masses"))
    # If summary is stdout, parse it only when no explicit summary occurrence is supplied.
    summaries = out.get("summary") or ([] if settings.get("-o") else out.get("stdout", []))
    if not summaries:
        issues.append(_issue("output_missing", field="summary"))
    for payload in summaries:
        ordinal = 0
        for li, start, end, text in lines(payload):
            tokens = text.split()
            if not tokens or text.lstrip().startswith("#"):
                continue
            if payload["occurrence"]["role"] == "stdout" and settings.get("-v") and len(tokens) == 1:
                # Kept separately below; they cannot replace binary vectors.
                continue
            fields = SUMMARY_FIELDS.get(mode, ()) + (("almean", "alsd") if settings.get("-a") else ())
            key = payload["occurrence"]["occurrence_id"] + "#summary/" + str(ordinal)
            mi = ordinal // len(schedule) if schedule else (0 if len(models) == 1 else None)
            values, states, native_tokens = {}, {}, {}
            if len(tokens) != len(fields) + 1:
                issues.append(_issue("summary_width_invalid", record_key=key,
                                     details={"expected": len(fields)+1, "actual": len(tokens)}))
            for j, field in enumerate(fields):
                token = tokens[j+1] if j+1 < len(tokens) else None
                native_tokens[field] = token
                values[field], states[field] = number(token, key, field)
                value = values[field]
                if value is not None and ((field in {"lambda", "plambda"} and value <= 0) or
                        (field == "tailp" and not 0 < value <= 1) or
                        ((field.startswith("E10") or field in {"almean", "alsd"}) and value < 0)):
                    states[field] = "invalid"
                    issues.append(_issue("number_invalid", record_key=key, field=field,
                                         details={"token": token, "reason": "outside_native_quantity_domain"}))
            if len(tokens) != len(fields) + 1:
                states = {field: "invalid" if state == "present" else state for field, state in states.items()}
            if mode == "hybrid" and states.get("pmu") == "present":
                states["pmu"] = "undetermined"
                issues.append(_issue("hybrid_calibration_undetermined", record_key=key, field="pmu"))
            if schedule and values.get("tailp") is not None and abs(values["tailp"] - schedule[ordinal % len(schedule)]) > 5.00001e-5:
                issues.append(_issue("summary_tail_mismatch", record_key=key, field="tailp"))
                mi = None
            row(payload, "summary", ordinal, start, end, li, li,
                {"name": tokens[0], "tokens": native_tokens, "values": values, "states": states, "raw_text": text},
                mi, named=tokens[0], method="serial_input_order_and_name")
            ordinal += 1
        if schedule and ordinal != len(models) * len(schedule):
            issues.append(_issue("summary_population_mismatch", occurrence_id=payload["occurrence"]["occurrence_id"],
                                 details={"actual": ordinal, "expected": len(models)*len(schedule)}))

    abi_valid = (isinstance(native_abi, dict) and set(native_abi) == {"byte_order", "float_format", "bytes_per_float"}
                 and native_abi["byte_order"] in ("little", "big")
                 and native_abi["float_format"] == "ieee754_binary64" and type(native_abi["bytes_per_float"]) is int
                 and native_abi["bytes_per_float"] == 8)
    if out.get("scores") and not abi_valid:
        issues.append(_issue("abi_missing" if native_abi is None else "abi_invalid", field="native_abi"))
    for payload in out.get("scores", []):
        content = payload["content"]
        if not abi_valid or n is None:
            row(payload, "scores", 0, 0, len(content), None, None,
                {"values": None, "states": None, "declared_population": n, "observed_count": None,
                 "original_bytes_hex": content.hex(), "completeness": "unknown",
                 "representation": "native_binary64", "tokens": None}, None)
            continue
        expected = 8 * n * len(models)
        if len(content) != expected:
            issues.append(_issue("score_population_mismatch", occurrence_id=payload["occurrence"]["occurrence_id"],
                                 details={"expected_bytes": expected, "actual_bytes": len(content)}))
        # A final short segment remains available; absent segments are not manufactured.
        starts = range(0, len(content), 8*n) if content else [0]
        for ordinal, start in enumerate(starts):
            segment = content[start:start+8*n]
            values, states = [], []
            for value, in struct.iter_unpack(("<" if native_abi["byte_order"] == "little" else ">") + "d", segment[:len(segment)//8*8]):
                states.append("present" if math.isfinite(value) else "nonfinite")
                values.append(value if math.isfinite(value) else None)
            complete = len(segment) == 8*n
            completeness = "complete" if complete else "partial"
            if payload["occurrence"]["completeness"] == "unknown":
                completeness = "unknown"
            result = row(payload, "scores", ordinal, start, start+len(segment), None, None,
                {"values": values, "states": states, "declared_population": n,
                 "observed_count": len(values), "original_bytes_hex": segment.hex(), "completeness": completeness,
                 "representation": "native_binary64", "tokens": None}, ordinal if len(content) <= expected else None)
            if not complete:
                issues.append(_issue("score_segment_incomplete", record_key=result["record_key"]))
            if "nonfinite" in states:
                issues.append(_issue("number_nonfinite", record_key=result["record_key"], field="values"))

    if settings.get("-v"):
        for payload in out.get("stdout", []):
            # Native stdout emits each model's scores, then its summary if -o
            # is absent. Contiguous one-token groups retain the exact printed
            # precision and raw byte spans, including incomplete final groups.
            groups, group = [], []
            for item in lines(payload):
                parts = item[3].split()
                if len(parts) == 1 and not parts[0].startswith("#"):
                    group.append(item)
                    if n and len(group) == n:
                        groups.append(group)
                        group = []
                elif group:
                    groups.append(group)
                    group = []
            if group:
                groups.append(group)
            for ordinal, group in enumerate(groups):
                key = payload["occurrence"]["occurrence_id"] + "#scores/" + str(ordinal)
                tokens = [item[3].strip() for item in group]
                cells = [number(token, key, "values") for token in tokens]
                start, end = group[0][1], group[-1][2]
                row(payload, "scores", ordinal, start, end, group[0][0], group[-1][0],
                    {"values": [v for v, _ in cells], "states": [s for _, s in cells],
                     "declared_population": n, "observed_count": len(group), "original_bytes_hex": payload["content"][start:end].hex(),
                     "completeness": "complete" if len(group) == n else "partial",
                     "representation": "printed_3_decimal", "tokens": tokens}, ordinal)
            if not n or len(groups) != len(models) or any(len(g) != n for g in groups):
                issues.append(_issue("verbose_population_mismatch", occurrence_id=payload["occurrence"]["occurrence_id"]))

    for payload in out.get("alignments", []):
        ordinal = 0
        for li, start, end, text in lines(payload):
            tokens = text.split()
            if not tokens:
                continue
            key = payload["occurrence"]["occurrence_id"] + "#alignments/" + str(ordinal)
            if len(tokens) != 2:
                issues.append(_issue("alignment_width_invalid", record_key=key))
            length, ls = number(tokens[0], key, "trace_state_count", True)
            score, ss = number(tokens[1] if len(tokens) > 1 else None, key, "score")
            if len(tokens) != 2:
                ls = ss = "invalid"
            if length is not None and length < 0:
                length, ls = None, "invalid"
                issues.append(_issue("number_invalid", record_key=key, field="trace_state_count"))
            row(payload, "alignments", ordinal, start, end, li, li,
                {"sample_ordinal": ordinal % n if n else None, "trace_state_count": length, "score": score,
                 "tokens": tokens, "states": {"trace_state_count": ls, "score": ss}, "raw_text": text},
                ordinal // n if n else None)
            ordinal += 1
        if n is None or ordinal != n*len(models):
            issues.append(_issue("alignment_population_mismatch", occurrence_id=payload["occurrence"]["occurrence_id"]))

    for payload in out.get("filter", []):
        ordinal = 0
        for li, start, end, text in lines(payload):
            tokens = text.split()
            if not tokens:
                continue
            key = payload["occurrence"]["occurrence_id"] + "#filter/" + str(ordinal)
            if len(tokens) != 3:
                issues.append(_issue("filter_width_invalid", record_key=key))
            count, cs = number(tokens[1] if len(tokens) > 1 else None, key, "count", True)
            fraction, fs = number(tokens[2] if len(tokens) > 2 else None, key, "fraction")
            if len(tokens) != 3:
                cs = fs = "invalid"
            if (count is not None and (count < 0 or (n is not None and count > n))) or (fraction is not None and not 0 <= fraction <= 1):
                issues.append(_issue("filter_count_invalid", record_key=key))
                cs = fs = "invalid"
            row(payload, "filter", ordinal, start, end, li, li,
                {"name": tokens[0], "count": count, "denominator": n, "fraction": fraction,
                 "tokens": tokens, "states": {"count": cs, "fraction": fs}, "raw_text": text},
                ordinal, named=tokens[0], method="serial_input_order_and_name")
            ordinal += 1
        if ordinal != len(models) and not (mode == "forward" and ordinal == 0):
            issues.append(_issue("filter_population_mismatch", occurrence_id=payload["occurrence"]["occurrence_id"]))

    for role in ("survival", "expected_counts"):
        for payload in out.get(role, []):
            first_row = len(sheet["native_rows"])
            block, points, tokens, legends, ordinal = [], [], [], [], 0
            start, first_line, end, last_line = 0, 1, 0, 0
            def finish(delimiter):
                nonlocal ordinal, block, points, tokens, legends, start, first_line
                per_model = 3 if role == "survival" else 1
                mi = ordinal // per_model
                meaning = ("native_calibration_expected_count_by_rank" if role == "expected_counts" else
                           ("empirical_binned_survival", "last_tail_exponential_survival" if mode == "forward" else "fitted_gumbel_survival",
                            "last_tail_fixed_lambda_exponential_survival" if mode == "forward" else "fixed_lambda_gumbel_survival")[ordinal % 3])
                if mi >= len(models):
                    mi, meaning = None, "unknown"
                if role == "expected_counts":
                    names = [s[1:].strip() for s in legends if s.startswith("#")]
                    if names != [name_at(mi)]:
                        issues.append(_issue("xy_name_mismatch", occurrence_id=payload["occurrence"]["occurrence_id"]))
                        mi = None
                row(payload, "xy_series", ordinal, start, end, first_line, last_line,
                    {"series_kind": role, "series_ordinal": ordinal, "meaning": meaning, "points": points,
                     "tokens": tokens, "legends": legends, "delimiter": delimiter,
                     "raw_text": "\n".join(block), "complete": delimiter == "&"}, mi)
                ordinal += 1
                block, points, tokens, legends = [], [], [], []
                start, first_line = end, last_line + 1
            for li, line_start, line_end, text in lines(payload):
                end, last_line = line_end, li
                if not block:
                    start, first_line = line_start, li
                block.append(text)
                parts = text.split()
                if not parts:
                    continue
                if text.lstrip().startswith(("#", "@")):
                    legends.append(text)
                elif text.strip() == "&":
                    finish("&")
                else:
                    key = payload["occurrence"]["occurrence_id"] + "#xy_series/" + str(ordinal)
                    x, xs = number(parts[0], key, "points.x")
                    y, ys = number(parts[1] if len(parts) > 1 else None, key, "points.y")
                    if len(parts) != 2 or xs != "present" or ys != "present":
                        issues.append(_issue("xy_point_invalid", record_key=key))
                    points.append([x, y])
                    tokens.append(parts)
            if block and any(s.strip() for s in block):
                issues.append(_issue("xy_unterminated", occurrence_id=payload["occurrence"]["occurrence_id"]))
                finish(None)
            if ordinal != len(models)*(3 if role == "survival" else 1):
                issues.append(_issue("xy_series_count_invalid", occurrence_id=payload["occurrence"]["occurrence_id"]))
                if len(models) > 1:
                    # With missing separators the boundary between models is
                    # not recoverable. Retain all points without asserting a
                    # possibly shifted model or curve identity.
                    for r, association in zip(sheet["native_rows"][first_row:], sheet["associations"][first_row:]):
                        r["model_keys"] = []
                        r["payload"]["meaning"] = "unknown"
                        association.update(model_keys=[], state="unresolved")

    # A late conflicting named record invalidates all joins to that model, not
    # merely the last row; no independently sorted-name fallback is possible.
    bad_keys = {m.get("record_key") for m, ok in zip(models, model_ok) if not ok}
    for result, association in zip(sheet["native_rows"], sheet["associations"]):
        if bad_keys.intersection(result["model_keys"]) or not validity.get(result["locator"]["occurrence_id"], False):
            result["model_keys"] = []
            association.update(model_keys=[], state="unresolved")
    return sheet
