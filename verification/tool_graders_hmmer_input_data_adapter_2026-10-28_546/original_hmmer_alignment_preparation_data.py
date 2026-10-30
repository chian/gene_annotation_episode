"""Pure occurrence-preserving hmmbuild/alimask result readers (B1).

The public sheet has the contract's nine fields. ``artifact_occurrences`` are
the exact eight-field M1 identities. ``input_records``/``output_records`` hold
Stockholm records (kind=alignment) and output model references (kind=model).
Every alignment keeps all original events, interleaved fragments, annotations,
row occurrences and exact case. ``native_rows`` contains typed population,
build_summary, requested_interval and mapping records; unsupported populations
have decoded_count=None, never zero. Summary and mapping rows retain raw lines,
tokens and byte/line locators. Associations join occurrence keys, never hashes.

Only Stockholm/Pfam framing is decoded here. A declared different grammar is
retained by its occurrence and an explicit unavailable population. Complete
native bytes remain the caller's retained artifacts, not a serialized preview.
No filesystem, process, network, Store, model call, observation or credit occurs.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import math
import re

from .hmmalign_inputs import iter_hmmalign_stockholm_records
from .hmmer_model_data import _occurrence_valid, extract_hmmer_models

SCHEMA = "hmmer_alignment_preparation_sheet_v1"
MODES = {"hmmbuild": frozenset({"build_alignment", "build_single_sequence_matrix"}),
         "alimask": frozenset({"mask_alignment", "mask_model", "model_to_alignment", "alignment_to_model"})}
RANGE_FLAGS = {"mask_alignment": "--alirange", "mask_model": "--modelrange",
               "model_to_alignment": "--model2ali", "alignment_to_model": "--ali2model"}
ISSUE_CODES = frozenset({
    "operation_invalid", "payload_invalid", "occurrence_invalid", "occurrence_duplicate",
    "occurrence_role_mismatch", "occurrence_size_mismatch", "occurrence_digest_mismatch",
    "capture_incomplete", "text_encoding_invalid", "alignment_format_unsupported",
    "alignment_invalid", "alignment_incomplete", "alignment_empty", "row_geometry_invalid",
    "row_symbols_invalid", "annotation_geometry_invalid", "annotation_join_ambiguous",
    "duplicate_sequence_name", "weight_invalid", "role_missing", "role_cardinality_invalid",
    "summary_header_missing", "summary_header_invalid", "summary_row_invalid",
    "summary_index_invalid", "summary_unparsed_line", "mapping_header_missing",
    "mapping_header_invalid", "mapping_row_invalid", "mapping_row_count_mismatch",
    "range_invalid", "range_capacity_exceeded", "model_extraction_missing",
    "model_extraction_mismatch", "model_extraction_issue", "association_incomplete",
    "association_conflict", "model_map_invalid", "first_record_only",
    "unexpected_output", "resaved_alignment_empty", "mm_symbol_invalid",
    "map_context_unavailable", "map_context_invalid",
})
ROW_FIELDS = {
    "population": frozenset({"record_key", "kind", "occurrence_id", "format", "decoded_count", "complete", "state"}),
    "build_summary": frozenset({"record_key", "kind", "occurrence_id", "locator", "raw", "tokens", "valid",
        "idx", "name", "nseq", "alen", "mlen", "W", "eff_nseq", "re_per_position", "description", "native_tokens"}),
    "requested_interval": frozenset({"record_key", "kind", "request_ordinal", "flag", "raw", "start", "end", "coordinate_system", "valid"}),
    "mapping": frozenset({"record_key", "kind", "occurrence_id", "locator", "raw", "tokens", "valid", "request_ordinal",
        "requested_start", "requested_end", "returned_source_start", "returned_source_end", "target_start", "target_end",
        "source_coordinate_system", "target_coordinate_system", "native_state"}),
}
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
_INTEGER = re.compile(r"[0-9]+\Z")
_MAPPING = re.compile(r"\s*(\d+)\.\.(\d+)\s+->\s+(?:(\d+)\.\.(\d+)|-\.\.-\s+\(no map\))\s*\Z")

# A retained implementation association, not a guess from a version banner or
# the installation on the machine reading a saved sheet. No file is opened.
ALIMASK_PROFILE_EXECUTABLE_SHA256 = "4cf273b7b4b52363468b758a39bedf8f00540b01983bf6641ffd36140afad547"
ALIMASK_PROFILE = {"name": "infernal_1_1_5_hmmer_3_4_alimask", "source_sha256s": {
    "hmmer/src/alimask.c": "504e52c49a249facca5887d96f5efeaaf8012820b47bbe75e782aa14af7034ab",
    "easel/esl_msaweight.c": "0195e7c2a4428f02a84e3c239922090e72a5a72a5cc5de8a3a5551f06b6efe68",
    "easel/esl_msaweight.h": "caf345d5c9053af80e899b697a648430306f2db6240f8724b017490b94ffb106",
    "easel/esl_rand64.c": "abd4b05b7bf619f196b1ca99c0de452e0fe38b3ffa0f7e2f5991d88d763e5359",
    "easel/esl_vectorops.c": "6226cb25818a1319811f7fdec2aa590df0b60f40aa01521a806cf484ea117463",
}}
MAP_CONTEXT_FIELDS = frozenset({"version", "source_occurrence_id", "source_sha256", "producer", "profile",
    "binding", "requested_cli_seed", "resolved_cli_seed", "effective_pb_config"})
_PB_CONFIG = {"fragthresh": .5, "symfrac": .5, "ignore_rf": True, "allow_samp": True,
    "sampthresh": 50000, "nsamp": 10000, "maxfrag": 5000, "seed": 42,
    "rng": "easel_mt19937_64", "sampler": "esl_rand64_Deal_vitter_D_A"}


def alimask_map_context_shape(context):
    """Closed JSON operand shape, separate from its semantic association."""
    digest = lambda value: type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    integer = lambda value: type(value) is int and 0 <= value <= 2147483647
    if (type(context) is not dict or set(context) != MAP_CONTEXT_FIELDS
            or context["version"] != "hmmer_alignment_map_context_v1"
            or type(context["source_occurrence_id"]) is not str or not context["source_occurrence_id"]
            or not digest(context["source_sha256"])
            or type(context["binding"]) is not str or context["binding"] not in {"retained_executable_profile", "unavailable"}
            or context["requested_cli_seed"] is not None and not integer(context["requested_cli_seed"])
            or not integer(context["resolved_cli_seed"])):
        return False
    producer = context["producer"]
    if (type(producer) is not dict or set(producer) != {"program", "engine_version", "executable_sha256"}
            or producer["program"] != "alimask" or producer["engine_version"] != "3.4"
            or producer["executable_sha256"] is not None and not digest(producer["executable_sha256"])):
        return False
    profile, config = context["profile"], context["effective_pb_config"]
    if profile is not None and (type(profile) is not dict or set(profile) != {"name", "source_sha256s"}
            or type(profile["name"]) is not str or not profile["name"]
            or type(profile["source_sha256s"]) is not dict
            or set(profile["source_sha256s"]) != set(ALIMASK_PROFILE["source_sha256s"])
            or any(not digest(value) for value in profile["source_sha256s"].values())):
        return False
    if config is not None and (type(config) is not dict or set(config) != set(_PB_CONFIG)
            or any(type(config[k]) is not bool for k in ("ignore_rf", "allow_samp"))
            or any(not integer(config[k]) for k in ("sampthresh", "nsamp", "maxfrag", "seed"))
            or any(not finite(config[k]) or not 0 <= config[k] <= 1 for k in ("fragthresh", "symfrac"))
            or any(type(config[k]) is not str for k in ("rng", "sampler"))):
        return False
    return True


def alimask_map_context_valid(context, *, settings, source_occurrence=None, operation=None, alignment=None):
    """Validate retained identities/settings; never resolve a source or profile."""
    if not alimask_map_context_shape(context) or type(settings) is not dict:
        return False
    if operation is not None and (operation.get("program") != "alimask" or operation.get("engine_version") != "3.4"):
        return False
    if source_occurrence is not None and (not _occurrence_valid(source_occurrence)
            or source_occurrence["direction"] != "input" or source_occurrence["role"] != "alignment"
            or source_occurrence["ordinal"] != 0
            or context["source_occurrence_id"] != source_occurrence["occurrence_id"]
            or context["source_sha256"] != source_occurrence["sha256"]):
        return False
    if alignment is not None and (context["source_occurrence_id"] != alignment.get("occurrence_id")
            or alignment.get("record_key") != context["source_occurrence_id"] + "#alignment/0"
            or alignment.get("engine_version") != "3.4"):
        return False
    resolved = settings.get("--seed", 42)
    if (type(resolved) is not int or context["resolved_cli_seed"] != resolved
            or context["requested_cli_seed"] is not None and context["requested_cli_seed"] != resolved
            or context["requested_cli_seed"] is None and resolved != 42):
        return False
    if context["binding"] == "unavailable":
        return context["profile"] is None and context["effective_pb_config"] is None
    return (context["producer"]["executable_sha256"] == ALIMASK_PROFILE_EXECUTABLE_SHA256
        and context["profile"] == ALIMASK_PROFILE
        and context["effective_pb_config"] == {**_PB_CONFIG, "ignore_rf": not bool(settings.get("--hand"))})


def issue(code, *, record_key=None, occurrence_id=None, field=None, stage="extraction", **details):
    assert code in ISSUE_CODES
    return {"code": code, "stage": stage, "record_key": record_key,
            "occurrence_id": occurrence_id, "field": field, "details": details}


def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _number(token, integer=False):
    if not isinstance(token, str) or not (_INTEGER if integer else _NUMBER).fullmatch(token):
        return None
    try:
        value = int(token) if integer else float(token)
        return value if finite(value) else None
    except (ValueError, OverflowError):
        return None


def selected_alphabet(settings):
    values = [name for flag, name in (("--amino", "amino"), ("--dna", "DNA"), ("--rna", "RNA")) if settings.get(flag)]
    return values[0] if len(values) == 1 else None


def annotation(record, tag):
    value = record.get("column_annotations", {}).get(tag)
    return value["text"] if value and value.get("valid") is True else None


def gf_value(record, tag):
    values = [event["value"] for event in record.get("original_events", []) if event["kind"] == "GF" and event["tag"] == tag]
    return values[0] if len(values) == 1 else None


def model_header(record, tag):
    values = [header["value"] for header in record.get("headers", []) if header["tag"] == tag]
    return values[0] if len(values) == 1 else None


def valid_alignment(record):
    return (isinstance(record, dict) and record.get("kind") == "alignment" and record.get("header_valid") is True
        and record.get("complete") is True and type(record.get("column_count")) is int
        and record["column_count"] > 0 and bool(record.get("rows"))
        and all(r.get("geometry_valid") and r.get("symbols_valid") and r.get("identity_unambiguous") for r in record["rows"]))


def _locator(occurrence, ordinal, lines, byte_start, byte_end):
    return {"artifact_ref": occurrence["artifact_ref"], "record_ordinal": ordinal,
            "byte_start": byte_start, "byte_end": byte_end, "line_start": lines[0], "line_end": lines[-1]}


def _lines(content, occurrence, issues):
    offset = 0
    for ordinal, raw in enumerate(content.splitlines(keepends=True)):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            issues.append(issue("text_encoding_invalid", occurrence_id=occurrence["occurrence_id"], line=ordinal + 1))
            text = raw.decode("utf-8", errors="surrogateescape")
        yield text, _locator(occurrence, ordinal, [ordinal + 1], offset, offset + len(raw))
        offset += len(raw)


def _population(occurrence, fmt, count=None, complete=False, state="unsupported"):
    return {"record_key": occurrence["occurrence_id"] + "#population/0", "kind": "population",
            "occurrence_id": occurrence["occurrence_id"], "format": fmt, "decoded_count": count,
            "complete": complete, "state": state}


def _alignment_records(payload, fmt, operation, sheet):
    occurrence, content = payload["occurrence"], payload["content"]
    oid = occurrence["occurrence_id"]
    # Autodetection here is a framing test, never an extension-based guess.
    if fmt is None and content.lstrip().startswith(b"# STOCKHOLM 1.0"):
        fmt = "stockholm"
    if fmt is not None:
        fmt = fmt.lower()
    if fmt not in {"stockholm", "pfam"}:
        sheet["issues"].append(issue("alignment_format_unsupported", occurrence_id=oid, format=fmt))
        sheet["native_rows"].append(_population(occurrence, fmt))
        return []
    encoding_complete = True
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        sheet["issues"].append(issue("text_encoding_invalid", occurrence_id=oid))
        # A malformed suffix cannot erase complete preceding MSA occurrences.
        # No offsets after the bad byte are guessed; that population is partial.
        text = content[:error.start].decode("utf-8")
        encoding_complete = False
    records = list(iter_hmmalign_stockholm_records(text, artifact_ref=occurrence["artifact_ref"],
                                                 engine_version=operation["engine_version"]))
    for index, record in enumerate(records):
        key = oid + "#alignment/" + str(index)
        record.update(record_key=key, kind="alignment", occurrence_id=oid, format=fmt)
        events = record["original_events"]
        record["locator"] = _locator(occurrence, index, [e["locator"]["line"] for e in events],
                                    events[0]["locator"]["byte_start"], events[-1]["locator"]["byte_end"])
        record["native_issues"] = record.pop("issues")
        local = []
        if not record["header_valid"] or record["native_issues"]:
            local.append(issue("alignment_invalid", record_key=key, occurrence_id=oid, native_issues=record["native_issues"]))
        if not record["complete"]:
            local.append(issue("alignment_incomplete", record_key=key, occurrence_id=oid))
        if not record["rows"]:
            local.append(issue("alignment_empty", record_key=key, occurrence_id=oid))
        for tag, item in record["column_annotations"].items():
            if not item["valid"]:
                local.append(issue("annotation_geometry_invalid", record_key=key, occurrence_id=oid, field=tag))
        mask = annotation(record, "MM")
        if mask is not None and any(symbol not in "m." for symbol in mask):
            local.append(issue("mm_symbol_invalid", record_key=key, occurrence_id=oid, field="MM"))
        names = Counter(row["name"] for row in record["rows"])
        for row_index, row in enumerate(record["rows"]):
            row["record_key"] = key + "/sequence/" + str(row_index)
            row["native_issues"] = row.pop("issues")
            fragments = row["fragments"]
            row["locator"] = _locator(occurrence, row_index, [e["locator"]["line"] for e in fragments],
                fragments[0]["locator"]["byte_start"], fragments[-1]["locator"]["byte_end"])
            for flag, code in (("geometry_valid", "row_geometry_invalid"), ("symbols_valid", "row_symbols_invalid"),
                               ("identity_unambiguous", "annotation_join_ambiguous")):
                if not row[flag]:
                    local.append(issue(code, record_key=row["record_key"], occurrence_id=oid))
            if names[row["name"]] > 1:
                local.append(issue("duplicate_sequence_name", record_key=row["record_key"], occurrence_id=oid, name=row["name"]))
            weight_events = [event for event in row["sequence_annotations"] if event["tag"] == "WT"]
            weights = [_number(event["value"]) for event in weight_events]
            valid = (row["sequence_annotations_joined"] and len(weights) == 1 and weights[0] is not None and weights[0] >= 0)
            row["weight"] = {"value": weights[0] if valid else None, "state": "present" if valid else "missing" if not weights else "incompatible",
                             "events": deepcopy(weight_events)}
            if weights and not valid:
                local.append(issue("weight_invalid", record_key=row["record_key"], occurrence_id=oid))
        weight_events = [event for event in events if event["kind"] == "GS" and event["tag"] == "WT"]
        malformed_weight = any(event["kind"] == "malformed_annotation" and
            re.match(r"#=GS\s+\S+\s+WT(?:\s|$)", event["raw"]) for event in events)
        if malformed_weight or weight_events and (len(weight_events) != len(record["rows"])
                or any(row["weight"]["state"] != "present" for row in record["rows"])):
            local.append(issue("weight_invalid", record_key=key, occurrence_id=oid))
        record["issues"] = local
        sheet["issues"].extend(local)
    complete = encoding_complete and occurrence["completeness"] == "complete" and all(valid_alignment(r) and not r["issues"] for r in records)
    sheet["native_rows"].append(_population(occurrence, fmt, len(records), complete, "decoded" if complete else "partial"))
    return records


def _summary(payload, sheet):
    occurrence, content = payload["occurrence"], payload["content"]
    header = None
    rows = []
    for raw, locator in _lines(content, occurrence, sheet["issues"]):
        text = raw.strip()
        if text.startswith("#"):
            fields = text.lstrip("#").split()
            if fields[:2] == ["idx", "name"]:
                if fields not in (["idx", "name", "nseq", "alen", "mlen", "eff_nseq", "re/pos", "description"],
                                  ["idx", "name", "nseq", "alen", "mlen", "W", "eff_nseq", "re/pos", "description"]):
                    sheet["issues"].append(issue("summary_header_invalid", occurrence_id=occurrence["occurrence_id"], tokens=fields))
                    header = None
                else:
                    header = fields
            continue
        if not text:
            continue
        if header is None or not re.match(r"\d", text):
            sheet["issues"].append(issue("summary_unparsed_line", occurrence_id=occurrence["occurrence_id"], raw=raw, locator=locator))
            continue
        fields = text.split(None, len(header) - 1)
        if len(fields) == len(header) - 1:
            fields.append("")
        values = dict(zip(header, fields))
        key = occurrence["occurrence_id"] + "#build_summary/" + str(len(rows))
        locator["record_ordinal"] = len(rows)
        row = {"record_key": key, "kind": "build_summary", "occurrence_id": occurrence["occurrence_id"],
               "locator": locator, "raw": raw, "tokens": text.split(), "native_tokens": values,
               "valid": len(fields) == len(header), "name": values.get("name"), "description": values.get("description")}
        for field in ("idx", "nseq", "alen", "mlen", "W", "eff_nseq", "re_per_position"):
            source = "re/pos" if field == "re_per_position" else field
            row[field] = _number(values.get(source), integer=field not in {"eff_nseq", "re_per_position"})
            if source in header and (row[field] is None or row[field] < 0 or field in {"idx", "nseq", "alen", "mlen", "W"} and row[field] == 0):
                row["valid"] = False
        if not row["valid"]:
            sheet["issues"].append(issue("summary_row_invalid", record_key=key, occurrence_id=occurrence["occurrence_id"]))
        if row["idx"] != len(rows) + 1:
            sheet["issues"].append(issue("summary_index_invalid", record_key=key, occurrence_id=occurrence["occurrence_id"], actual=row["idx"], expected=len(rows) + 1))
        rows.append(row)
    if header is None:
        sheet["issues"].append(issue("summary_header_missing", occurrence_id=occurrence["occurrence_id"]))
    sheet["native_rows"].extend(rows)
    return rows


def _requests(operation, sheet):
    mode, settings = operation["mode"], operation["settings"]
    flag = RANGE_FLAGS[mode]
    value = settings.get(flag)
    rows = []
    for index, raw in enumerate(value.split(",") if isinstance(value, str) else []):
        match = re.fullmatch(r"\s*(\d+)\s*(?:-|\.\.)\s*(\d+)\s*", raw)
        start, end = (int(match[1]), int(match[2])) if match else (None, None)
        valid = start is not None and 1 <= start <= end <= 2**32 - 1
        row = {"record_key": "request#interval/" + str(index), "kind": "requested_interval", "request_ordinal": index,
               "flag": flag, "raw": raw, "start": start, "end": end, "valid": valid,
               "coordinate_system": "alignment" if mode in {"mask_alignment", "alignment_to_model"} else "model"}
        rows.append(row)
        if not valid:
            sheet["issues"].append(issue("range_invalid", record_key=row["record_key"], field=flag, raw=raw))
    if not rows:
        sheet["issues"].append(issue("range_invalid", field=flag, supplied=value))
    if len(rows) > 100:
        sheet["issues"].append(issue("range_capacity_exceeded", field=flag, count=len(rows), capacity=100))
    sheet["native_rows"].extend(rows)
    return rows


def _mapping(payload, operation, requests, sheet):
    occurrence, content = payload["occurrence"], payload["content"]
    source = "model" if operation["mode"] == "model_to_alignment" else "alignment"
    target = "alignment" if source == "model" else "model"
    expected_header = f"{source} coordinates {target} coordinates"
    header = False
    rows = []
    for raw, locator in _lines(content, occurrence, sheet["issues"]):
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        if "coordinates" in text:
            header = " ".join(text.split()) == expected_header
            if not header:
                sheet["issues"].append(issue("mapping_header_invalid", occurrence_id=occurrence["occurrence_id"], raw=raw))
            continue
        matched = _MAPPING.fullmatch(raw.rstrip("\r\n"))
        request = requests[len(rows)] if len(rows) < len(requests) else {}
        key = occurrence["occurrence_id"] + "#mapping/" + str(len(rows))
        locator["record_ordinal"] = len(rows)
        row = {"record_key": key, "kind": "mapping", "occurrence_id": occurrence["occurrence_id"],
               "locator": locator, "raw": raw, "tokens": text.split(), "valid": bool(header and matched),
               "request_ordinal": len(rows), "requested_start": request.get("start"), "requested_end": request.get("end"),
               "returned_source_start": int(matched[1]) if matched else None,
               "returned_source_end": int(matched[2]) if matched else None,
               "target_start": int(matched[3]) if matched and matched[3] else None,
               "target_end": int(matched[4]) if matched and matched[4] else None,
               "source_coordinate_system": source, "target_coordinate_system": target,
               "native_state": "mapped" if matched and matched[3] else "no_map" if matched else "malformed"}
        if row["native_state"] == "no_map" and source != "alignment":
            row["valid"] = False
        if matched and (row["returned_source_start"] < 1 or row["returned_source_end"] < row["returned_source_start"]
                        or row["target_start"] is not None and not 1 <= row["target_start"] <= row["target_end"]):
            row["valid"] = False
        if not row["valid"]:
            sheet["issues"].append(issue("mapping_row_invalid", record_key=key, occurrence_id=occurrence["occurrence_id"]))
        rows.append(row)
    if not header:
        sheet["issues"].append(issue("mapping_header_missing", occurrence_id=occurrence["occurrence_id"]))
    if len(rows) != len(requests):
        sheet["issues"].append(issue("mapping_row_count_mismatch", occurrence_id=occurrence["occurrence_id"], actual=len(rows), requested=len(requests)))
    sheet["native_rows"].extend(rows)


def _model_map(model, width):
    if model.get("flags", {}).get("MAP") is not True:
        return None
    values = [position.get("annotations", {}).get("MAP", {}).get("value") for position in model.get("positions", [])]
    if (len(values) != model.get("length") or any(type(v) is not int or not 1 <= v <= width for v in values)
            or any(a >= b for a, b in zip(values, values[1:]))):
        return None
    return values


def _build_associations(sheet, summaries, usable_inputs, settings):
    inputs = [r for r in sheet["input_records"] if r["kind"] == "alignment"] if usable_inputs else []
    models = (sheet["model_extraction"] or {}).get("records", [])
    resaved = [r for r in sheet["output_records"] if r["kind"] == "alignment"]
    summary_by_idx = {}
    for row in summaries:
        summary_by_idx.setdefault(row["idx"], []).append(row)
    resaved_index = 0
    for index in range(max(len(inputs), len(models))):
        source = inputs[index] if index < len(inputs) else None
        model = models[index] if index < len(models) else None
        candidates = summary_by_idx.get(index + 1, [])
        summary = candidates[0] if len(candidates) == 1 else None
        singlemx = bool(settings.get("--singlemx")) and source is not None and len(source["rows"]) == 1
        transformed = resaved[resaved_index] if resaved_index < len(resaved) and not singlemx else None
        if not singlemx:
            resaved_index += 1
        qualification = {}
        key = source["record_key"] if source else model["record_key"]
        if source and model:
            qualification["source_complete"] = valid_alignment(source)
            qualification["nseq"] = len(source["rows"]) == model["sequence_count"]
            alph = selected_alphabet(settings)
            qualification["alphabet"] = model["alphabet"]["kind"] == alph if alph else None
            expected_name = source["rows"][0]["name"] if singlemx else settings.get("-n") or gf_value(source, "ID")
            qualification["model_name"] = model_header(model, "NAME") == expected_name if expected_name else None
            source_acc = gf_value(source, "AC")
            qualification["accession"] = (model_header(model, "ACC") == source_acc if source_acc and not singlemx else None)
            if model["flags"].get("MAP") is True:
                qualification["model_map"] = _model_map(model, source["column_count"] or 0) is not None
                if not qualification["model_map"]:
                    sheet["issues"].append(issue("model_map_invalid", record_key=model["record_key"]))
            if summary:
                expected_summary_name = settings.get("-n") or gf_value(source, "ID")
                qualification["summary_name"] = summary["name"] == expected_summary_name if expected_summary_name else None
                qualification["summary_nseq"] = summary["nseq"] == len(source["rows"]) == model["sequence_count"]
                qualification["summary_alen"] = summary["alen"] == source["column_count"]
                qualification["summary_mlen"] = summary["mlen"] == model["length"]
                qualification["summary_valid"] = summary["valid"]
                qualification["summary_window"] = summary["W"] == model["maximum_length"] if summary["W"] is not None else None
            involved = {source["occurrence_id"], sheet["model_extraction"]["occurrence"]["occurrence_id"]}
            qualification["artifact_binding"] = not any(i["occurrence_id"] in involved and i["code"] in
                {"occurrence_digest_mismatch", "occurrence_size_mismatch", "occurrence_role_mismatch"} for i in sheet["issues"])
        status = ("conflicting" if False in qualification.values() else "validated" if source and model and summary else "unresolved")
        association = {"record_key": key, "relation": "build", "source_record_key": source["record_key"] if source else None,
            "summary_record_key": summary["record_key"] if summary else None, "model_record_key": model["record_key"] if model else None,
            "resaved_record_key": transformed["record_key"] if transformed else None,
            "native_single_sequence_matrix": singlemx, "status": status, "qualifications": qualification}
        sheet["associations"].append(association)
        if status != "validated":
            sheet["issues"].append(issue("association_conflict" if status == "conflicting" else "association_incomplete", record_key=key, qualification=qualification))
    for summary in summaries:
        if not any(a["summary_record_key"] == summary["record_key"] for a in sheet["associations"]):
            sheet["issues"].append(issue("association_incomplete", record_key=summary["record_key"], field="summary"))


def populate_hmmer_alignment_preparation_sheet(*, operation, inputs, outputs, model_extraction=None,
                                               map_reconstruction_context=None):
    """Read supplied bytes only; failures preserve complete prefix records.

    Operation settings use native flag spellings. The selected summary artifact
    is authoritative; stdout is used only when no -o/summary was selected.
    Mapping rows always come from stdout, independently of a -o header artifact.
    """
    sheet = {"schema": SCHEMA, "operation": deepcopy(operation), "artifact_occurrences": [],
             "input_records": [], "output_records": [], "model_extraction": None, "native_rows": [],
             "associations": [], "issues": []}
    if (not isinstance(operation, dict) or set(operation) != {"program", "mode", "engine_version", "settings"}
            or not isinstance(operation.get("program"), str) or operation.get("program") not in MODES
            or not isinstance(operation.get("mode"), str) or operation.get("mode") not in MODES.get(operation.get("program"), ())
            or not isinstance(operation.get("engine_version"), str) or not operation["engine_version"]
            or not isinstance(operation.get("settings"), dict)):
        sheet["issues"].append(issue("operation_invalid"))
        return sheet
    settings, payloads, ids = operation["settings"], {"input": {}, "output": {}}, set()
    for direction, supplied in (("input", inputs), ("output", outputs)):
        if not isinstance(supplied, dict):
            sheet["issues"].append(issue("payload_invalid", field=direction))
            continue
        for role, values in supplied.items():
            if not isinstance(role, str) or not isinstance(values, list):
                sheet["issues"].append(issue("payload_invalid", field=direction))
                continue
            payloads[direction].setdefault(role, [])
            for payload in values:
                if not isinstance(payload, dict) or set(payload) != {"occurrence", "content"} or not isinstance(payload.get("content"), bytes):
                    sheet["issues"].append(issue("payload_invalid", field=role))
                    continue
                occurrence, content = payload["occurrence"], payload["content"]
                if not _occurrence_valid(occurrence):
                    sheet["issues"].append(issue("occurrence_invalid", field=role))
                    continue
                oid = occurrence["occurrence_id"]
                if oid in ids:
                    sheet["issues"].append(issue("occurrence_duplicate", occurrence_id=oid))
                    continue
                ids.add(oid)
                sheet["artifact_occurrences"].append(deepcopy(occurrence))
                if occurrence["direction"] != direction or occurrence["role"] != role:
                    sheet["issues"].append(issue("occurrence_role_mismatch", occurrence_id=oid, field=role))
                if occurrence["size_bytes"] != len(content):
                    sheet["issues"].append(issue("occurrence_size_mismatch", occurrence_id=oid, actual=len(content)))
                if occurrence["sha256"].lower() != hashlib.sha256(content).hexdigest():
                    sheet["issues"].append(issue("occurrence_digest_mismatch", occurrence_id=oid))
                if occurrence["completeness"] != "complete":
                    sheet["issues"].append(issue("capture_incomplete", occurrence_id=oid))
                payloads[direction].setdefault(role, []).append(payload)
    for direction in payloads:
        for role in payloads[direction]:
            payloads[direction][role].sort(key=lambda p: p["occurrence"]["ordinal"])
    source_payloads = payloads["input"].get("alignment", [])
    if len(source_payloads) != 1:
        sheet["issues"].append(issue("role_missing" if not source_payloads else "role_cardinality_invalid", field="input.alignment", count=len(source_payloads)))
    for payload in source_payloads:
        sheet["input_records"].extend(_alignment_records(payload, settings.get("--informat"), operation, sheet))
    if map_reconstruction_context is not None:
        first = next((r for r in sheet["input_records"] if len(source_payloads) == 1 and
            r["record_key"] == source_payloads[0]["occurrence"]["occurrence_id"] + "#alignment/0"), None)
        occurrence = source_payloads[0]["occurrence"] if len(source_payloads) == 1 else None
        if first is not None and operation["program"] == "alimask":
            first["map_reconstruction_context"] = deepcopy(map_reconstruction_context)
        if not alimask_map_context_valid(map_reconstruction_context, settings=settings,
                source_occurrence=occurrence, operation=operation, alignment=first):
            problem = issue("map_context_invalid", record_key=first["record_key"] if first else None,
                            occurrence_id=occurrence["occurrence_id"] if occurrence else None)
            sheet["issues"].append(problem)
            if first is not None:
                first["issues"].append(problem)
    output_role = "resaved_alignment" if operation["program"] == "hmmbuild" else "masked_alignment"
    transformed = payloads["output"].get(output_role, [])
    if len(transformed) > 1:
        sheet["issues"].append(issue("role_cardinality_invalid", field="output." + output_role, count=len(transformed)))
    for payload in transformed:
        fmt = "stockholm" if operation["program"] == "hmmbuild" else settings.get("--outformat", "stockholm")
        sheet["output_records"].extend(_alignment_records(payload, fmt, operation, sheet))
        if output_role == "resaved_alignment" and not payload["content"]:
            sheet["issues"].append(issue("resaved_alignment_empty", occurrence_id=payload["occurrence"]["occurrence_id"]))
    if operation["program"] == "hmmbuild":
        if settings.get("--mxfile") and not payloads["input"].get("matrix"):
            sheet["issues"].append(issue("role_missing", field="input.matrix"))
        models = payloads["output"].get("models", [])
        if len(models) != 1:
            sheet["issues"].append(issue("role_missing" if not models else "role_cardinality_invalid", field="output.models", count=len(models)))
        if model_extraction is None:
            sheet["issues"].append(issue("model_extraction_missing"))
        elif len(models) == 1:
            # Identity metadata alone cannot prove that supplied arrays match bytes.
            expected = extract_hmmer_models(models[0]["content"], occurrence=models[0]["occurrence"], format="hmmer3_ascii")
            if model_extraction != expected:
                sheet["issues"].append(issue("model_extraction_mismatch", occurrence_id=models[0]["occurrence"]["occurrence_id"]))
            else:
                sheet["model_extraction"] = deepcopy(model_extraction)
                for problem in model_extraction["issues"]:
                    sheet["issues"].append(issue("model_extraction_issue", record_key=problem["record_key"], cause=problem))
                for model in model_extraction["records"]:
                    sheet["output_records"].append({"record_key": model["record_key"], "kind": "model", "occurrence_id": models[0]["occurrence"]["occurrence_id"], "locator": deepcopy(model["locator"])})
        summary_role = "summary" if settings.get("-o") or "summary" in payloads["output"] else "stdout"
        summary_payloads = payloads["output"].get(summary_role, [])
        summaries = []
        if len(summary_payloads) != 1:
            sheet["issues"].append(issue("role_missing" if not summary_payloads else "role_cardinality_invalid", field="output." + summary_role, count=len(summary_payloads)))
        else:
            summaries = _summary(summary_payloads[0], sheet)
        if (settings.get("-O") or "resaved_alignment" in payloads["output"]) and not transformed:
            sheet["issues"].append(issue("role_missing", field="output.resaved_alignment"))
        _build_associations(sheet, summaries, len(source_payloads) == 1, settings)
    else:
        requests = _requests(operation, sheet)
        sources = sheet["input_records"] if len(source_payloads) == 1 else []
        results = [r for r in sheet["output_records"] if r["kind"] == "alignment"]
        for index, record in enumerate(sources):
            sheet["associations"].append({"record_key": record["record_key"], "relation": "mask" if index == 0 else "unprocessed",
                "source_record_key": record["record_key"], "output_record_key": results[0]["record_key"] if index == 0 and len(results) == 1 else None,
                "status": "selected_first_record" if index == 0 else "unprocessed"})
        if len(sources) > 1:
            sheet["issues"].append(issue("first_record_only", processed=sources[0]["record_key"], unprocessed=[r["record_key"] for r in sources[1:]]))
        if operation["mode"] in {"model_to_alignment", "alignment_to_model"}:
            streams = payloads["output"].get("stdout", [])
            if len(streams) != 1:
                sheet["issues"].append(issue("role_missing" if not streams else "role_cardinality_invalid", field="output.stdout", count=len(streams)))
            else:
                _mapping(streams[0], operation, requests, sheet)
            if transformed:
                sheet["issues"].append(issue("unexpected_output", field="masked_alignment"))
        elif not transformed:
            sheet["issues"].append(issue("role_missing", field="output.masked_alignment"))
        elif len(results) != 1:
            sheet["issues"].append(issue("role_cardinality_invalid", field="output.masked_alignment.records", count=len(results)))
    return sheet


__all__ = ["populate_hmmer_alignment_preparation_sheet", "SCHEMA", "MODES", "ROW_FIELDS", "ISSUE_CODES"]
