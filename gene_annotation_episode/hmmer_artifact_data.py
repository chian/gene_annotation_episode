"""Pure A1 sheets for HMMER conversion, selection and index preparation.

The caller supplies retained bytes and exact M1 extraction envelopes. This
module checks those envelopes with M1, preserves occurrence multiplicity, and
extracts native key/summary/framing facts. It never acquires, executes, opens a
file, authenticates custody, awards credit, or interprets a model as biology.
Concrete closed row shapes are exported in ROW_FIELDS and documented in 268.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from .hmmer_model_data import extract_hmmer_models, _occurrence_valid, ALPHABETS


SCHEMA = "hmmer_artifact_sheet_v1"
MODES = {"hmmconvert": frozenset({"ascii", "binary", "legacy_hmmer2"}),
         "hmmfetch": frozenset({"single_key", "key_file", "index"}),
         "hmmpress": frozenset({"index"})}
MODEL_ROLES = frozenset({"models", "converted_models", "fetched_models", "binary_models"})
BUNDLE_ROLES = ("binary_models", "ssi_index", "msv_profiles", "remaining_profiles")
BINDING_FIELDS = frozenset({"artifact_occurrence_id", "source_occurrence_id", "source_sha256",
                          "producer_attempt_id", "staged_source_stem", "actual_relative_path"})
SHEET_FIELDS = frozenset({"schema", "operation", "artifact_occurrences", "model_extractions",
                        "input_records", "output_records", "native_rows", "associations",
                        "artifact_bindings", "issues"})
ROW_FIELDS = {
    "artifact_metadata": frozenset({"kind", "row_key", "occurrence_id", "measured_size_bytes",
        "measured_sha256", "signature_hex", "trailing_signature_hex", "format", "revision",
        "byte_order", "offset_width", "framing_state", "decoded_record_count", "internal_content_state"}),
    "requested_key": frozenset({"kind", "row_key", "occurrence_id", "request_ordinal", "key",
        "tokens", "raw_line", "locator", "request_source"}),
    "index_summary": frozenset({"kind", "row_key", "occurrence_id", "locator", "text", "tokens",
        "model_count", "primary_name_count", "accession_count", "accession_clause_supplied"}),
    "reported_path": frozenset({"kind", "row_key", "occurrence_id", "locator", "text", "role", "path"}),
    "diagnostic": frozenset({"kind", "row_key", "occurrence_id", "locator", "text", "tokens", "code"}),
    "key_resolution": frozenset({"kind", "association_id", "key_row_key", "key", "source_record_keys",
        "selected_source_record_keys", "output_record_keys", "state", "lookup_state", "basis"}),
    "model_pair": frozenset({"kind", "association_id", "key_row_keys", "source_record_keys",
        "output_record_keys", "state", "basis"}),
}
ISSUE_CODES = frozenset({"operation_invalid", "payload_invalid", "occurrence_invalid",
    "occurrence_role_mismatch", "occurrence_ordinal_invalid", "occurrence_id_duplicate",
    "occurrence_size_mismatch", "occurrence_digest_mismatch", "capture_incomplete",
    "required_role_missing", "unexpected_role", "content_type_invalid", "text_encoding_invalid",
    "model_extraction_invalid", "model_extraction_mismatch", "model_extraction_duplicate",
    "model_extraction_missing", "model_extraction_issue", "key_invalid", "key_duplicate",
    "model_label_duplicate", "native_summary_invalid", "native_summary_duplicate",
    "native_diagnostic", "artifact_binding_invalid", "artifact_binding_duplicate",
    "artifact_binding_mismatch", "conversion_stdout_mismatch"})
_EXTRACTION_FIELDS = frozenset({"schema", "occurrence", "format", "records", "population", "issues"})
_MODEL_MAGIC = {0xe8ededb5: "2.0", 0xe8ededb6: "3/a", 0xe8ededb7: "3/b", 0xe8ededb8: "3/c",
                0xe8ededb9: "3/d", 0xe8ededb0: "3/e", 0xe8ededba: "3/f"}
_PROFILE_MAGIC = {0xe8b3e6f3: ("msv_profiles", "3/a"), 0xe8b3f0f3: ("remaining_profiles", "3/a")}
for _i, _revision in enumerate("bcdef", 2):
    _PROFILE_MAGIC[0xb300e6f3 + (_i + 0xe0) * 0x10000] = ("msv_profiles", "3/" + _revision)
    _PROFILE_MAGIC[0xb300f0f3 + (_i + 0xe0) * 0x10000] = ("remaining_profiles", "3/" + _revision)
_SUMMARY = re.compile(r"(?:Indexed|Pressed and indexed) ([0-9]+) HMMs \(([0-9]+) names(?: and ([0-9]+) accessions)?\)\.")
_PATH_PREFIXES = {"SSI index written to file ": "ssi",
    "Models pressed into binary file:": "binary_models", "SSI index for binary model file:": "ssi_index",
    "Profiles (MSV part) pressed into:": "msv_profiles", "Profiles (remainder) pressed into:": "remaining_profiles"}


def _issue(code, *, occurrence_id=None, row_key=None, field=None, **details):
    assert code in ISSUE_CODES
    return {"code": code, "stage": "extraction", "occurrence_id": occurrence_id,
            "row_key": row_key, "field": field, "details": details}


def _operation_valid(operation):
    return (isinstance(operation, dict) and set(operation) == {"program", "mode", "engine_version", "settings"}
            and isinstance(operation.get("program"), str) and operation["program"] in MODES
            and isinstance(operation.get("mode"), str) and operation["mode"] in MODES[operation["program"]]
            and isinstance(operation.get("engine_version"), str) and bool(operation["engine_version"])
            and isinstance(operation.get("settings"), dict))


def _roles(operation):
    program, mode = operation["program"], operation["mode"]
    incoming, required_in = {"models"}, {"models"}
    if program == "hmmfetch" and mode != "index":
        incoming.add("ssi")
        if mode == "key_file":
            incoming.add("keys")
            required_in.add("keys")
    main_out = ({"converted_models"} if program == "hmmconvert" else
                {"ssi"} if program == "hmmfetch" and mode == "index" else
                {"fetched_models"} if program == "hmmfetch" else set(BUNDLE_ROLES))
    return incoming, required_in, main_out | {"stdout", "stderr"}, main_out


def _lines(content):
    start = 0
    # esl_fgets reads LF-terminated lines. A standalone CR or vertical tab is
    # whitespace within that line, not another requested-key occurrence.
    parts = content.split(b"\n")
    for line, part in enumerate(parts, 1):
        if line == len(parts) and not part:
            break
        raw = part + (b"\n" if line < len(parts) else b"")
        yield line, start, start + len(raw), part.decode("utf-8", "surrogateescape")
        start += len(raw)


def _locator(occurrence, line, start, end):
    return {"artifact_ref": occurrence["artifact_ref"], "line": line,
            "byte_start": start, "byte_end": end}


def _artifact_metadata(content, occurrence):
    """Decode framing only; no count or full-body decoding is inferred."""
    row = {"kind": "artifact_metadata", "row_key": occurrence["occurrence_id"] + "#artifact",
        "occurrence_id": occurrence["occurrence_id"], "measured_size_bytes": len(content),
        "measured_sha256": hashlib.sha256(content).hexdigest(), "signature_hex": content[:4].hex(),
        "trailing_signature_hex": content[-4:].hex(), "format": None, "revision": None,
        "byte_order": None, "offset_width": None, "framing_state": "unknown",
        "decoded_record_count": None, "internal_content_state": "unknown"}
    first = content.splitlines()[0].split() if content else []
    if first and re.fullmatch(rb"HMMER3/[a-f]", first[0]):
        row.update(format="hmmer3_ascii", revision=first[0].decode()[5:], framing_state="prefix_recognized")
    elif first and first[0] == b"HMMER2.0":
        row.update(format="hmmer2_ascii", revision="2.0", framing_state="prefix_recognized")
    elif len(content) >= 4:
        for order in ("big", "little"):
            magic = int.from_bytes(content[:4], order)
            if magic in _MODEL_MAGIC:
                row.update(format="hmmer_binary", revision=_MODEL_MAGIC[magic], byte_order=order,
                    framing_state="prefix_recognized" if len(content) >= 16 else "truncated")
                break
            if magic == 0xd3d3c9b3:
                width = int.from_bytes(content[8:12], order) if len(content) >= 12 else None
                row.update(format="ssi", revision="3.0", byte_order=order, offset_width=width,
                    framing_state="prefix_recognized" if width in {4, 8} and len(content) >= 54 + 3*width
                    else "truncated" if len(content) < 12 or width in {4, 8} else "invalid")
                break
            if magic in _PROFILE_MAGIC:
                family, revision = _PROFILE_MAGIC[magic]
                row.update(format=family, revision=revision, byte_order=order,
                    framing_state="prefix_and_terminal_marker" if len(content) >= 20 and content[-4:] == content[:4]
                    else "truncated")
                break
    return row


def _native_rows(content, occurrence, operation):
    rows = []
    role, oid = occurrence["role"], occurrence["occurrence_id"]
    for line, start, end, text in _lines(content):
        locator, key = _locator(occurrence, line, start, end), oid + "#line/" + str(line)
        # Native GetTokenOnLine splits whitespace, and recognizes a comment
        # only when the token STARTS with '#'; embedded '#' is part of a key.
        tokens = re.findall(r"[^ \t\r\n]+", text.lstrip(" \t\r\n\v\f"))
        if role == "keys":
            if tokens and not tokens[0].startswith("#"):
                prefix = text.index(tokens[0])
                locator.update(token_byte_start=start+len(text[:prefix].encode("utf-8", "surrogateescape")),
                    token_byte_end=start+len(text[:prefix+len(tokens[0])].encode("utf-8", "surrogateescape")))
                rows.append({"kind": "requested_key", "row_key": key, "occurrence_id": oid,
                    "request_ordinal": None, "key": tokens[0], "tokens": tokens, "raw_line": text,
                    "locator": locator, "request_source": "key_file"})
        elif role == "stdout" and (operation["mode"] == "index"):
            match = _SUMMARY.fullmatch(text.strip())
            expected_prefix = "Pressed and indexed " if operation["program"] == "hmmpress" else "Indexed "
            if not text.strip().startswith(expected_prefix):
                match = None
            if match:
                rows.append({"kind": "index_summary", "row_key": key, "occurrence_id": oid,
                    "locator": locator, "text": text, "tokens": tokens, "model_count": int(match[1]),
                    "primary_name_count": int(match[2]), "accession_count": int(match[3]) if match[3] else 0,
                    "accession_clause_supplied": match[3] is not None})
            elif text.strip().startswith(("Indexed", "Pressed and indexed")):
                rows.append({"kind": "diagnostic", "row_key": key, "occurrence_id": oid,
                    "locator": locator, "text": text, "tokens": tokens, "code": "invalid_index_summary"})
            for prefix, output_role in _PATH_PREFIXES.items():
                if text.startswith(prefix):
                    rows.append({"kind": "reported_path", "row_key": key, "occurrence_id": oid,
                        "locator": locator, "text": text, "role": output_role, "path": text[len(prefix):].strip()})
        elif role == "stderr" and text.strip():
            lower = text.lower()
            code = ("duplicate_key" if "more than once" in lower or "not unique" in lower else
                    "missing_key" if "not found" in lower and ("hmm " in lower or "key" in lower) else
                    "native_error" if "error" in lower or "failed" in lower else "native_message")
            rows.append({"kind": "diagnostic", "row_key": key, "occurrence_id": oid,
                "locator": locator, "text": text, "tokens": tokens, "code": code})
    return rows


def _label(record, tag):
    headers = [h for h in record.get("headers", []) if isinstance(h, dict) and h.get("tag") == tag]
    return headers[0]["tokens"][0] if len(headers) == 1 and len(headers[0].get("tokens", [])) == 1 else None


def _pair_identity(source, output):
    if _label(source, "NAME") is None or _label(output, "NAME") is None:
        return False
    alphabet = source.get("alphabet", {})
    return (alphabet.get("kind") in ALPHABETS and alphabet.get("symbols") == ALPHABETS[alphabet["kind"]]
        and _label(source, "NAME") == _label(output, "NAME")
        and _label(source, "ACC") == _label(output, "ACC")
        and not any(i.get("code") == "header_duplicate" and i.get("field") in {"NAME", "ACC"}
                    for r in (source, output) for i in r.get("issues", []))
        and source.get("alphabet") == output.get("alphabet")
        and type(source.get("length")) is int and source["length"] == output.get("length"))


def _population_known(sheet, direction):
    occurrences = [o for o in sheet["artifact_occurrences"] if o["direction"] == direction and o["role"] in MODEL_ROLES]
    extracts = {e["occurrence"]["occurrence_id"]: e for e in sheet["model_extractions"]}
    return bool(occurrences) and all(o["occurrence_id"] in extracts and
        extracts[o["occurrence_id"]]["population"]["complete"] is True for o in occurrences)


def _build_associations(sheet):
    operation = sheet["operation"]
    sources, outputs = sheet["input_records"], sheet["output_records"]
    if operation["program"] == "hmmconvert":
        unsupported = {direction: any(e["occurrence"]["direction"] == direction and
            e["population"]["decoded_count"] is None for e in sheet["model_extractions"])
            for direction in ("input", "output")}
        return [{"kind": "model_pair", "association_id": "conversion/" + str(i), "key_row_keys": [],
            "source_record_keys": [sources[i]["record_key"]] if i < len(sources) else [],
            "output_record_keys": [outputs[i]["record_key"]] if i < len(outputs) else [],
            "state": ("matched" if _pair_identity(sources[i], outputs[i]) else "mismatch")
                     if i < min(len(sources), len(outputs)) else
                     "unavailable" if unsupported["output" if i < len(sources) else "input"] else
                     "missing_output" if i < len(sources) else "unexpected_output", "basis": "ordered_conversion"}
            for i in range(max(len(sources), len(outputs)))]
    if operation["program"] != "hmmfetch" or operation["mode"] == "index":
        return []
    keys = [r for r in sheet["native_rows"] if r["kind"] == "requested_key"]
    indexed = any(o["direction"] == "input" and o["role"] == "ssi" for o in sheet["artifact_occurrences"])
    single = operation["mode"] == "single_key"
    basis = "indexed_key_order" if indexed else "first_source_match" if single else "unindexed_source_order"
    source_complete, resolutions, expected, seen, blocked = _population_known(sheet, "input"), [], [], set(), False
    for key in keys:
        candidates = [s for s in sources if key["key"] in {_label(s, "NAME"), _label(s, "ACC")}]
        duplicate = key["key"] in seen
        seen.add(key["key"])
        selected = candidates if not single and not indexed else candidates[:1] if not indexed or len(candidates) == 1 else []
        state = ("ambiguous" if indexed and len(candidates) > 1 else "resolved" if candidates else
                 "missing" if source_complete else "unknown")
        lookup = "blocked_after_error" if blocked else "duplicate_error" if duplicate else "eligible"
        if duplicate or blocked:
            selected = []
        row = {"kind": "key_resolution", "association_id": "key/" + str(len(resolutions)),
            "key_row_key": key["row_key"], "key": key["key"],
            "source_record_keys": [s["record_key"] for s in candidates],
            "selected_source_record_keys": [s["record_key"] for s in selected],
            "output_record_keys": [], "state": state, "lookup_state": lookup, "basis": basis}
        resolutions.append(row)
        if indexed:
            if not blocked and not duplicate and len(selected) == 1:
                expected.append((selected[0], [key["row_key"]]))
            if duplicate or state != "resolved":
                blocked = True
        elif single and selected:
            expected.append((selected[0], [key["row_key"]]))
    if not indexed and not single and not any(r["lookup_state"] == "duplicate_error" for r in resolutions):
        for source in sources:
            matched_keys = [r["key_row_key"] for r in resolutions if source["record_key"] in r["selected_source_record_keys"]]
            if matched_keys:
                expected.append((source, matched_keys))
    if not indexed and not single and any(r["lookup_state"] == "duplicate_error" for r in resolutions):
        # Unindexed multifetch validates all keys before it begins the scan.
        for row in resolutions:
            row["selected_source_record_keys"] = []
    pairs = []
    for i in range(max(len(expected), len(outputs))):
        source, key_ids = expected[i] if i < len(expected) else (None, [])
        output = outputs[i] if i < len(outputs) else None
        state = ("matched" if _pair_identity(source, output) else "mismatch") if source and output else (
            "missing_output" if source else "unexpected_output" if source_complete else "unavailable")
        pair = {"kind": "model_pair", "association_id": "fetch/" + str(i), "key_row_keys": key_ids,
            "source_record_keys": [source["record_key"]] if source else [],
            "output_record_keys": [output["record_key"]] if output else [], "state": state, "basis": basis}
        pairs.append(pair)
        if state == "matched":
            for row in resolutions:
                if row["key_row_key"] in key_ids:
                    row["output_record_keys"].append(output["record_key"])
    return resolutions + pairs


def _binding_errors(binding, occurrences):
    if (not isinstance(binding, dict) or set(binding) != BINDING_FIELDS or
            any(not isinstance(value, str) or not value for value in binding.values())):
        return ["shape"]
    artifact, source = occurrences.get(binding["artifact_occurrence_id"]), occurrences.get(binding["source_occurrence_id"])
    errors = []
    if artifact is None or artifact["role"] not in {*BUNDLE_ROLES, "ssi"}:
        errors.append("artifact_occurrence_id")
    if source is None or source["role"] != "models" or source["direction"] != "input":
        errors.append("source_occurrence_id")
    elif binding["source_sha256"].lower() != source["sha256"].lower():
        errors.append("source_sha256")
    for field in ("staged_source_stem", "actual_relative_path"):
        value = binding[field]
        if value.startswith("/") or any(part in {"", ".", ".."} for part in value.split("/")) or "\x00" in value:
            errors.append(field)
    if artifact:
        suffix = {"binary_models": ".h3m", "ssi_index": ".h3i", "msv_profiles": ".h3f",
                  "remaining_profiles": ".h3p", "ssi": ".ssi"}.get(artifact["role"])
        if suffix and binding["actual_relative_path"] != binding["staged_source_stem"] + suffix:
            errors.append("source_stem_member_relationship")
    return errors


def populate_hmmer_artifact_sheet(*, operation, inputs, outputs, model_extractions,
                                  artifact_bindings=None):
    """Populate the A1 envelope solely from supplied bytes and M1 envelopes.

    Matching supplied metadata is a supplied-association check only. There is
    no authenticated custody assertion at this port. In particular, a filename,
    a magic word or a zero exit status cannot establish a binary's contents.
    """
    sheet = {"schema": SCHEMA, "operation": deepcopy(operation), "artifact_occurrences": [],
        "model_extractions": [], "input_records": [], "output_records": [], "native_rows": [],
        "associations": [], "artifact_bindings": deepcopy(artifact_bindings) if isinstance(artifact_bindings, list) else [],
        "issues": []}
    issues, payloads = sheet["issues"], {}
    if not _operation_valid(operation):
        issues.append(_issue("operation_invalid", field="operation"))
        return sheet
    incoming, required_in, outgoing, required_out = _roles(operation)
    for direction, supplied, allowed, required in (("input", inputs, incoming, required_in),
                                                   ("output", outputs, outgoing, required_out)):
        if not isinstance(supplied, dict):
            issues.append(_issue("payload_invalid", field=direction))
            continue
        for role in sorted(required):
            if not supplied.get(role):
                issues.append(_issue("required_role_missing", field=direction+"."+role))
        for role, items in supplied.items():
            if role not in allowed:
                issues.append(_issue("unexpected_role", field=direction+"."+str(role)))
                continue
            if not isinstance(items, list):
                issues.append(_issue("payload_invalid", field=direction+"."+role))
                continue
            valid = []
            for item in items:
                if not isinstance(item, dict) or set(item) != {"occurrence", "content"}:
                    issues.append(_issue("payload_invalid", field=direction+"."+role))
                    continue
                occurrence, content = item["occurrence"], item["content"]
                if not _occurrence_valid(occurrence):
                    issues.append(_issue("occurrence_invalid", field=direction+"."+role))
                    continue
                oid = occurrence["occurrence_id"]
                if occurrence["direction"] != direction or occurrence["role"] != role:
                    issues.append(_issue("occurrence_role_mismatch", occurrence_id=oid, field=direction+"."+role))
                    continue
                if not isinstance(content, bytes):
                    issues.append(_issue("content_type_invalid", occurrence_id=oid, field="content"))
                    continue
                if oid in payloads:
                    issues.append(_issue("occurrence_id_duplicate", occurrence_id=oid))
                    continue
                payloads[oid] = item
                valid.append(item)
                if len(content) != occurrence["size_bytes"]:
                    issues.append(_issue("occurrence_size_mismatch", occurrence_id=oid))
                if hashlib.sha256(content).hexdigest() != occurrence["sha256"].lower():
                    issues.append(_issue("occurrence_digest_mismatch", occurrence_id=oid))
                if occurrence["completeness"] != "complete":
                    issues.append(_issue("capture_incomplete", occurrence_id=oid))
            ordinals = [i["occurrence"]["ordinal"] for i in valid]
            if sorted(ordinals) != list(range(len(valid))):
                issues.append(_issue("occurrence_ordinal_invalid", field=direction+"."+role, supplied=ordinals))
            for item in sorted(valid, key=lambda i: i["occurrence"]["ordinal"]):
                occurrence, content = item["occurrence"], item["content"]
                sheet["artifact_occurrences"].append(deepcopy(occurrence))
                sheet["native_rows"].append(_artifact_metadata(content, occurrence))
                if role in {"keys", "stdout", "stderr"} and not (role == "stdout" and operation["program"] == "hmmconvert"):
                    rows = _native_rows(content, occurrence, operation)
                    sheet["native_rows"].extend(rows)
                    if any(0xdc80 <= ord(c) <= 0xdcff for c in content.decode("utf-8", "surrogateescape")):
                        issues.append(_issue("text_encoding_invalid", occurrence_id=occurrence["occurrence_id"]))
    if not isinstance(model_extractions, list):
        issues.append(_issue("model_extraction_invalid", field="model_extractions"))
        model_extractions = []
    accepted, seen_extractions = {}, set()
    for extraction in model_extractions:
        if (not isinstance(extraction, dict) or set(extraction) != _EXTRACTION_FIELDS or
                not _occurrence_valid(extraction.get("occurrence"))):
            issues.append(_issue("model_extraction_invalid", field="model_extractions"))
            continue
        oid = extraction["occurrence"]["occurrence_id"]
        if oid in seen_extractions:
            issues.append(_issue("model_extraction_duplicate", occurrence_id=oid))
            accepted.pop(oid, None)
            continue
        seen_extractions.add(oid)
        payload = payloads.get(oid)
        if payload is None or payload["occurrence"]["role"] not in MODEL_ROLES or payload["occurrence"] != extraction["occurrence"]:
            issues.append(_issue("model_extraction_mismatch", occurrence_id=oid, field="occurrence"))
            continue
        checked = extract_hmmer_models(payload["content"], occurrence=payload["occurrence"], format=extraction["format"])
        if checked != extraction:
            issues.append(_issue("model_extraction_mismatch", occurrence_id=oid, field="extraction"))
            continue
        accepted[oid] = deepcopy(extraction)
    for occurrence in sheet["artifact_occurrences"]:
        if occurrence["role"] not in MODEL_ROLES:
            continue
        oid = occurrence["occurrence_id"]
        if oid not in accepted:
            issues.append(_issue("model_extraction_missing", occurrence_id=oid))
            continue
        extraction = accepted[oid]
        sheet["model_extractions"].append(extraction)
        sheet[occurrence["direction"]+"_records"].extend(deepcopy(extraction["records"]))
        for issue in extraction["issues"]:
            issues.append(_issue("model_extraction_issue", occurrence_id=oid, field=issue["field"], native_issue=issue))
    if operation["program"] == "hmmfetch" and operation["mode"] == "single_key":
        key = operation["settings"].get("key")
        if not isinstance(key, str) or not key or "\x00" in key:
            issues.append(_issue("key_invalid", field="operation.settings.key"))
        else:
            sheet["native_rows"].append({"kind": "requested_key", "row_key": "operation.settings.key",
                "occurrence_id": None, "request_ordinal": 0, "key": key, "tokens": [key],
                "raw_line": None, "locator": None, "request_source": "single_key"})
    key_rows = [row for row in sheet["native_rows"] if row["kind"] == "requested_key"]
    seen = set()
    for i, row in enumerate(key_rows):
        row["request_ordinal"] = i
        if "\x00" in row["key"]:
            issues.append(_issue("key_invalid", occurrence_id=row["occurrence_id"], row_key=row["row_key"]))
        if row["key"] in seen:
            issues.append(_issue("key_duplicate", occurrence_id=row["occurrence_id"], row_key=row["row_key"], key=row["key"]))
        seen.add(row["key"])
    for direction in ("input", "output"):
        for tag in ("NAME", "ACC"):
            labels = {}
            for record in sheet[direction+"_records"]:
                label = _label(record, tag)
                if label is not None:
                    labels.setdefault(label, []).append(record["record_key"])
            for label, keys in labels.items():
                if len(keys) > 1:
                    issues.append(_issue("model_label_duplicate", field=direction+"."+tag, label=label, record_keys=keys))
    summaries = [r for r in sheet["native_rows"] if r["kind"] == "index_summary"]
    if len(summaries) > 1:
        issues.append(_issue("native_summary_duplicate", field="native_rows"))
    for row in sheet["native_rows"]:
        if row["kind"] == "diagnostic" and row["code"] != "native_message":
            issues.append(_issue("native_diagnostic", occurrence_id=row["occurrence_id"], row_key=row["row_key"], native_code=row["code"]))
            if row["code"] == "invalid_index_summary":
                issues.append(_issue("native_summary_invalid", occurrence_id=row["occurrence_id"], row_key=row["row_key"]))
    if artifact_bindings is not None and not isinstance(artifact_bindings, list):
        issues.append(_issue("artifact_binding_invalid", field="artifact_bindings"))
    occurrences = {o["occurrence_id"]: o for o in sheet["artifact_occurrences"]}
    seen = set()
    for binding in sheet["artifact_bindings"]:
        errors = _binding_errors(binding, occurrences)
        if errors:
            issues.append(_issue("artifact_binding_invalid" if errors == ["shape"] else "artifact_binding_mismatch",
                field="artifact_bindings", affected_fields=errors))
        if isinstance(binding, dict) and isinstance(binding.get("artifact_occurrence_id"), str):
            oid = binding["artifact_occurrence_id"]
            if oid in seen:
                issues.append(_issue("artifact_binding_duplicate", occurrence_id=oid))
            seen.add(oid)
    if operation["program"] == "hmmconvert":
        converted = [o for o in sheet["artifact_occurrences"] if o["role"] == "converted_models"]
        stdout = [o for o in sheet["artifact_occurrences"] if o["role"] == "stdout"]
        if stdout and (len(converted) != len(stdout) or any(payloads[a["occurrence_id"]]["content"] !=
                payloads[b["occurrence_id"]]["content"] for a, b in zip(converted, stdout))):
            issues.append(_issue("conversion_stdout_mismatch", field="outputs.stdout"))
    sheet["associations"] = _build_associations(sheet)
    return sheet
