"""Pure cmconvert/cmfetch/cmpress extraction and saved-sheet validation.

Counts describe retained artifacts and decoded model/request populations. None
of these quantities measures biological function confidence. Capture and native
return code are separate facts owned by the original execution receipt.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import re

from .infernal_preparation_models import (
    ISSUE_CODES as MODEL_ISSUE_CODES, MODEL_FORMATS, OPAQUE_SIGNATURES,
    extract_infernal_models,
)
from .infernal_preparation_schema import (
    check, field_input, issue, locator, new_calculations, new_sheet, record_key,
    validate_common_sheet, validate_operation, value,
)

ISSUE_CODES = frozenset({"artifact_payload_digest_mismatch", "artifact_payload_size_mismatch",
    "artifact_text_decode_failed", "artifact_summary_missing", "artifact_summary_duplicate",
    "artifact_summary_malformed", "artifact_input_population_incomplete",
    "artifact_output_population_incomplete", "artifact_required_output_missing",
    "artifact_output_role_duplicate", "artifact_output_format_mismatch",
    "artifact_model_association_conflicting", "artifact_key_provenance_missing",
    "artifact_key_request_missing", "artifact_key_request_duplicate", "artifact_key_request_ambiguous",
    "artifact_key_request_unsatisfied", "artifact_key_population_unknown", "artifact_key_population_incomplete",
    "artifact_binding_missing", "artifact_binding_source_mismatch", "artifact_binding_digest_mismatch",
    "artifact_binding_attempt_mismatch", "artifact_binding_stem_mismatch", "artifact_not_regular_file",
    "artifact_quartet_binding_mismatch", "artifact_native_count_mismatch"}) | MODEL_ISSUE_CODES
CHECK_NAMES = frozenset({"input_population_complete", "output_population_complete",
    "output_set_complete", "output_format", "model_identity_preserved", "conversion_semantics",
    "requested_keys_satisfied", "requested_keys_unique", "model_names_unique", "model_accessions_unique",
    "native_model_count", "native_indexed_name_count", "native_indexed_accession_count",
    "artifact_capture_complete", "artifact_payload_identity", "artifact_signature", "source_binding",
    "companion_stem", "attempt_binding", "regular_file", "quartet_binding", "model_calibration_present",
    "model_filter_present", "index_content_decoded"})
COMPONENT_NAMES = frozenset({"input_model_count", "output_model_count", "requested_key_count",
    "satisfied_key_count", "missing_key_count", "ambiguous_key_count", "output_artifact_count", "output_byte_count"})
ROW_FIELDS = {
    "key_request": frozenset({"kind", "record_key", "locator", "requested_key", "request_ordinal",
        "matched_input_model_keys", "output_model_keys", "match_kind", "outcome"}),
    "artifact_operation": frozenset({"kind", "record_key", "locator", "operation", "artifact_refs", "values", "content_validation"}),
}
ARTIFACT_VALUE_NAMES = frozenset({"model_count", "indexed_name_count", "indexed_accession_count", "byte_count"})
PARAMETER_NAMES = frozenset({"artifact_bindings"})
BINDING_FIELDS = frozenset({"artifact_ref", "artifact_sha256", "source_artifact_ref", "source_sha256",
    "expected_attempt_id", "actual_attempt_id", "staged_source_stem", "actual_relative_path", "regular_file"})
_SUFFIXES = {"ssi": ".ssi", "i1m": ".i1m", "i1i": ".i1i", "i1f": ".i1f", "i1p": ".i1p"}
_CONVERSIONS = {"ascii": ("converted_models", "infernal_cm_ascii"),
    "binary": ("converted_models", "infernal_cm_binary"),
    "legacy_ascii": ("converted_models", "infernal_cm_legacy_ascii"),
    "maximum_likelihood_hmm": ("converted_hmms", "hmmer_hmm_ascii"),
    "filter_hmm": ("converted_hmms", "hmmer_hmm_ascii")}
_PRESS = {"i1m": "infernal_cm_binary", "i1i": "infernal_ssi", "i1f": "infernal_i1f", "i1p": "infernal_i1p"}


def _operation(operation):
    validate_operation(operation)
    if operation["program"] not in {"cmconvert", "cmfetch", "cmpress"}:
        raise ValueError("artifact operation must be cmconvert, cmfetch or cmpress")


def _bytes(content):
    if type(content) is bytes:
        return content
    if type(content) is str:
        return content.encode("utf-8")
    try:
        chunks = list(content)
    except TypeError as exc:
        raise TypeError("content must be bytes, text or iterable text") from exc
    if any(type(chunk) is not str for chunk in chunks):
        raise TypeError("content iterable must contain text")
    return "".join(chunks).encode("utf-8")


def _artifact_row(artifact, operation, ordinal=0, *, location=None, validation="parsed"):
    return {"kind": "artifact_operation", "record_key": record_key(artifact["artifact_ref"], "artifact_operation", ordinal),
        "locator": location or locator(artifact["artifact_ref"], ordinal), "operation": deepcopy(operation),
        "artifact_refs": [artifact["artifact_ref"]], "values": {
            key: value(unit="byte" if key == "byte_count" else "count") for key in ARTIFACT_VALUE_NAMES},
        "content_validation": validation}


def parse_infernal_artifact_operation(stdout, *, operation, artifact):
    """Read actual reported index/fetch counts, preserving absent cells."""
    _operation(operation)
    new_sheet(operation, [artifact])
    if artifact["format"] != "infernal_stdout":
        raise ValueError("stdout format must be infernal_stdout")
    data = _bytes(stdout)
    row = _artifact_row(artifact, operation, validation="parsed" if artifact["completeness"] == "complete" else "partial")
    issues = []
    def problem(code, field=None):
        issues.append(issue(code, stage="extraction", artifact_ref=artifact["artifact_ref"], record_key=row["record_key"], field=field))
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        problem("artifact_payload_digest_mismatch")
    if len(data) != artifact["size_bytes"]:
        problem("artifact_payload_size_mismatch")
    try:
        lines = data.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        problem("artifact_text_decode_failed")
        row["content_validation"] = "invalid"
        return {"rows": [row], "issues": issues}
    if lines:
        row["locator"] = locator(artifact["artifact_ref"], 0, line_start=1, line_end=len(lines), byte_start=0, byte_end=len(data))
    program, mode = operation["program"], operation["mode"]
    patterns = []
    if program == "cmpress":
        patterns = [re.compile(r"Pressed and indexed (\d+) CMs and p7 HMM filters \((\d+) names(?: and (\d+) accessions)?\)\.")]
    elif program == "cmfetch" and mode == "index":
        patterns = [re.compile(r"Indexed (\d+) CMs \((\d+) names(?: and (\d+) accessions)?\)\.")]
    elif program == "cmfetch" and mode == "key_file":
        patterns = [re.compile(r"Retrieved (\d+) CMs\.")]
    count, offset = 0, 0
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        matched = next((p.fullmatch(line) for p in patterns if p.fullmatch(line)), None)
        if matched:
            count += 1
            loc = locator(artifact["artifact_ref"], 0, line_start=number, line_end=number,
                          byte_start=offset, byte_end=offset+len(raw.encode("utf-8")))
            for key, token in zip(("model_count", "indexed_name_count", "indexed_accession_count"), matched.groups()):
                if token is not None:
                    row["values"][key] = value(int(token), inputs=[field_input(loc, key)], native_token=token)
        elif patterns and line.startswith(("Indexed ", "Pressed and indexed ", "Retrieved ")):
            problem("artifact_summary_malformed")
        offset += len(raw.encode("utf-8"))
    if count > 1:
        problem("artifact_summary_duplicate")
        for key in ("model_count", "indexed_name_count", "indexed_accession_count"):
            row["values"][key] = value(state="invalid")
    if not count and (program == "cmpress" or (program == "cmfetch" and mode == "index")):
        problem("artifact_summary_missing")
    if issues:
        row["content_validation"] = "invalid" if artifact["completeness"] == "complete" else "partial"
    return {"rows": [row], "issues": issues}


def _expected_outputs(operation):
    if operation["program"] == "cmconvert":
        role, fmt = _CONVERSIONS[operation["mode"]]
        return {role: fmt}
    if operation["program"] == "cmpress":
        return dict(_PRESS)
    return {"ssi": "infernal_ssi"} if operation["mode"] == "index" else {"fetched_models": "infernal_cm_ascii"}


def _normalized_alphabet(row):
    return {"1": "RNA", "2": "DNA"}.get(row["alphabet"], row["alphabet"])


def _length(row):
    return row["filter_hmm"]["fields"]["LENG"]["value"] if row["model_type"] == "hmm" else row["fields"]["CLEN"]["value"]


def _empty_fetch_refs(sheet):
    """An explicitly reported zero-row fetch and captured empty CM are coherent.

    This does not make an empty file a valid input model library, or reinterpret
    an empty failed/partial output as a successful zero-row extraction.
    """
    op = sheet["operation"]
    if op["program"] != "cmfetch" or op["mode"] != "key_file":
        return set()
    report = [r for r in sheet["native_rows"] if r["kind"] == "artifact_operation"
              and r["content_validation"] == "parsed" and r["values"]["model_count"]["state"] == "present"]
    if len(report) != 1 or report[0]["values"]["model_count"]["value"] != 0:
        return set()
    return {a["artifact_ref"] for a in sheet["artifacts"] if a["role"] == "fetched_models"
            and a["size_bytes"] == 0 and a["completeness"] == "complete"
            and not any(i["artifact_ref"] == a["artifact_ref"] and i["code"] in {
                "artifact_payload_digest_mismatch", "artifact_payload_size_mismatch"} for i in sheet["issues"])}


def _same_context(left, right, *, conversion=False):
    if any(row["content_validation"] != "parsed_headers_and_boundaries" for row in (left, right)):
        return False
    if any(left[tag] != right[tag] for tag in ("name", "accession")):
        return False
    if _normalized_alphabet(left) != _normalized_alphabet(right) or _length(left) != _length(right):
        return False
    if left["model_type"] == right["model_type"] == "cm":
        for tag in ("NSEQ", "STATES", "NODES", "CKSUM"):
            a, b = left["fields"][tag], right["fields"][tag]
            if a["state"] == b["state"] == "present" and a["value"] != b["value"]:
                return False
        if not conversion:
            for tag in left["calibration"]:
                a, b = left["calibration"][tag], right["calibration"][tag]
                if (a is None) != (b is None):
                    return False
                if a is not None and any(a[f]["value"] != b[f]["value"] for f in (
                        "lambda", "mu_extrap", "mu_orig", "calibration_dbsize_nt", "random_hit_count", "tail_probability_mass")):
                    return False
    return True


def _payload_map(mapping, artifacts, allowed):
    if type(mapping) is not dict or set(mapping) - allowed:
        raise ValueError("unsupported input/output artifact roles")
    refs = {a["artifact_ref"]: a for a in artifacts}
    result = {}
    for role, payloads in mapping.items():
        if type(payloads) is not list:
            raise TypeError("every role must map to a list of Payloads")
        result[role] = []
        for payload in payloads:
            if type(payload) is not dict or set(payload) != {"artifact", "content"}:
                raise ValueError("invalid Payload fields")
            art = payload["artifact"]
            if art["role"] != role or refs.get(art["artifact_ref"]) != art:
                raise ValueError("Payload artifact must match declared role and retained descriptor")
            result[role].append({"artifact": art, "content": _bytes(payload["content"])})
    return result


def _key_rows(sheet, inputs, outputs):
    operation = sheet["operation"]
    if operation["program"] != "cmfetch" or operation["mode"] == "index":
        return
    requests = []
    def problem(code, ref=None, key=None):
        sheet["issues"].append(issue(code, stage="association", artifact_ref=ref, record_key=key))
    if operation["mode"] == "single_key":
        selected = operation["settings"].get("key")
        if not isinstance(selected, str) or not selected or any(c.isspace() for c in selected):
            raise ValueError("single_key needs an exact nonempty settings.key token")
        provenance = inputs.get("request", [])
        if len(provenance) != 1:
            problem("artifact_key_provenance_missing")
            return
        art = provenance[0]["artifact"]
        if art["format"] != "infernal_request_json":
            raise ValueError("single key provenance must be retained original request")
        requests.append((selected, locator(art["artifact_ref"], 0)))
    else:
        if not inputs.get("keys"):
            problem("artifact_key_request_missing")
        for payload in inputs.get("keys", []):
            art = payload["artifact"]
            if art["format"] != "key_file":
                raise ValueError("keys artifact must have key_file format")
            try:
                lines = payload["content"].decode("utf-8").splitlines(keepends=True)
            except UnicodeDecodeError:
                problem("artifact_text_decode_failed", art["artifact_ref"])
                continue
            offset, ordinal = 0, 0
            for number, raw in enumerate(lines, 1):
                tokens = raw.split("#", 1)[0].split()
                if tokens:
                    requests.append((tokens[0], locator(art["artifact_ref"], ordinal,
                        line_start=number, line_end=number, byte_start=offset, byte_end=offset+len(raw.encode("utf-8")))))
                    ordinal += 1
                offset += len(raw.encode("utf-8"))
    counts = Counter(key for key, _ in requests)
    request_artifacts = [p["artifact"] for role in ("request",) if operation["mode"] == "single_key" for p in inputs.get(role, [])]
    if operation["mode"] == "key_file":
        request_artifacts = [p["artifact"] for p in inputs.get("keys", [])]
    request_refs = {a["artifact_ref"] for a in request_artifacts}
    request_incomplete = any(a["completeness"] != "complete" for a in request_artifacts) or any(
        i["artifact_ref"] in request_refs and i["code"] in {"artifact_payload_digest_mismatch", "artifact_payload_size_mismatch", "artifact_text_decode_failed"}
        for i in sheet["issues"])
    if request_incomplete:
        problem("artifact_key_population_incomplete")
    inrows = [r for r in sheet["input_records"] if r["kind"] == "model"]
    outrows = [r for r in sheet["output_records"] if r["kind"] == "model"]
    incomplete = any(i["code"] == "artifact_input_population_incomplete" for i in sheet["issues"])
    for ordinal, (key, loc) in enumerate(requests):
        name = [r for r in inrows if r["name"] == key]
        acc = [r for r in inrows if r["accession"] == key]
        matches = [r for r in inrows if r in name or r in acc]
        matching_output = [r for r in outrows if any(_same_context(m, r) for m in matches)]
        kind = "both" if name and acc else "name" if name else "accession" if acc else "unresolved"
        outcome = "satisfied" if len(matches) == 1 and matching_output else "missing"
        if len(matches) > 1:
            outcome = "ambiguous"
        if counts[key] > 1 or incomplete or request_incomplete or (len(matches) == 1 and matches[0]["content_validation"] != "parsed_headers_and_boundaries"):
            outcome = "invalid"
        row = {"kind": "key_request", "record_key": record_key(loc["artifact_ref"], "key_request", loc["record_ordinal"]),
            "locator": loc, "requested_key": key, "request_ordinal": ordinal,
            "matched_input_model_keys": [r["record_key"] for r in matches],
            "output_model_keys": [r["record_key"] for r in matching_output], "match_kind": kind, "outcome": outcome}
        sheet["native_rows"].append(row)
        if counts[key] > 1:
            problem("artifact_key_request_duplicate", loc["artifact_ref"], row["record_key"])
        if incomplete:
            problem("artifact_key_population_unknown", loc["artifact_ref"], row["record_key"])
        if outcome in {"missing", "ambiguous"}:
            problem("artifact_key_request_ambiguous" if outcome == "ambiguous" else "artifact_key_request_unsatisfied",
                    loc["artifact_ref"], row["record_key"])
    for row in outrows:
        matches = [r for r in inrows if _same_context(r, row)
                   and any(k == r["name"] or k == r["accession"] for k, _ in requests)]
        status = "validated" if len(matches) == 1 and not incomplete else "conflicting" if len(matches) > 1 else "unresolved"
        sheet["associations"].append({"relation": "fetched_from", "input_keys": [r["record_key"] for r in matches],
            "output_keys": [row["record_key"]], "status": status})
        if status != "validated":
            problem("artifact_model_association_conflicting", row["locator"]["artifact_ref"], row["record_key"])


def populate_infernal_artifact_sheet(*, operation, artifacts, inputs, outputs):
    """Populate supporting-operation sheets from explicit role→list[Payload]."""
    _operation(operation)
    sheet = new_sheet(operation, artifacts)
    validate_common_sheet(sheet)
    expected = _expected_outputs(operation)
    inputs = _payload_map(inputs, artifacts, {"models", "keys", "ssi", "request"})
    outputs = _payload_map(outputs, artifacts, set(expected) | {"stdout", "stderr"})
    supplied_refs = [p["artifact"]["artifact_ref"] for mapping in (inputs, outputs) for payloads in mapping.values() for p in payloads]
    if len(supplied_refs) != len(set(supplied_refs)) or set(supplied_refs) != {a["artifact_ref"] for a in artifacts}:
        raise ValueError("each retained artifact needs exactly one supplied payload")
    for direction, mapping, collection in (("input", inputs, "input_records"), ("output", outputs, "output_records")):
        for role, payloads in mapping.items():
            for payload in payloads:
                art, data = payload["artifact"], payload["content"]
                ref = art["artifact_ref"]
                if hashlib.sha256(data).hexdigest() != art["sha256"]:
                    sheet["issues"].append(issue("artifact_payload_digest_mismatch", stage="validation", artifact_ref=ref))
                if len(data) != art["size_bytes"]:
                    sheet["issues"].append(issue("artifact_payload_size_mismatch", stage="validation", artifact_ref=ref))
                extraction = None
                if art["format"] in MODEL_FORMATS:
                    extraction = extract_infernal_models(data, artifact=art, format=art["format"], engine_version=operation["engine_version"])
                    sheet[collection].extend(extraction["records"])
                    sheet["issues"].extend(extraction["issues"])
                    if role in {"models", "converted_models", "converted_hmms", "fetched_models"} and not extraction["population_complete"]:
                        sheet["issues"].append(issue("artifact_"+direction+"_population_incomplete", stage="validation", artifact_ref=ref))
                elif role == "models" or (role in expected and art["format"] != expected[role]):
                    sheet["issues"].append(issue("artifact_output_format_mismatch", stage="format", artifact_ref=ref))
                if direction == "output":
                    if role == "stdout":
                        parsed = parse_infernal_artifact_operation(data, operation=operation, artifact=art)
                        sheet["native_rows"].extend(parsed["rows"])
                        sheet["issues"].extend(parsed["issues"])
                    else:
                        validation = "parsed"
                        if extraction is not None and art["format"] in OPAQUE_SIGNATURES:
                            validation = "opaque_header_only"
                        if art["completeness"] != "complete":
                            validation = "partial"
                        if extraction and any(i["severity"] == "error" for i in extraction["issues"]):
                            validation = "invalid"
                        row = _artifact_row(art, operation, validation=validation)
                        row["values"]["byte_count"] = value(len(data), basis="derived", unit="byte",
                            inputs=[field_input(locator(ref), "supplied_content_bytes")])
                        sheet["output_records"].append(row)
    for role, fmt in expected.items():
        payloads = outputs.get(role, [])
        if not payloads:
            sheet["issues"].append(issue("artifact_required_output_missing", stage="validation", field=role))
        if len(payloads) > 1:
            sheet["issues"].append(issue("artifact_output_role_duplicate", stage="validation", field=role))
        for payload in payloads:
            if payload["artifact"]["format"] != fmt:
                sheet["issues"].append(issue("artifact_output_format_mismatch", stage="validation", artifact_ref=payload["artifact"]["artifact_ref"], field=role))
    if not inputs.get("models"):
        sheet["issues"].append(issue("artifact_input_population_incomplete", stage="validation", field="models"))
    if operation["program"] == "cmconvert":
        inrows = [r for r in sheet["input_records"] if r["kind"] == "model"]
        outrows = [r for r in sheet["output_records"] if r["kind"] == "model"]
        complete = not any(i["code"] in {"artifact_input_population_incomplete", "artifact_output_population_incomplete"} for i in sheet["issues"])
        for ordinal, row in enumerate(outrows):
            parent = inrows[ordinal] if ordinal < len(inrows) else None
            valid = complete and len(inrows) == len(outrows) and parent is not None and _same_context(parent, row, conversion=True)
            sheet["associations"].append({"relation": "converted_from", "input_keys": [parent["record_key"]] if parent else [],
                "output_keys": [row["record_key"]], "status": "validated" if valid else "conflicting" if parent and complete else "unresolved"})
            if not valid:
                sheet["issues"].append(issue("artifact_model_association_conflicting", stage="association", record_key=row["record_key"], artifact_ref=row["locator"]["artifact_ref"]))
    _key_rows(sheet, inputs, outputs)
    empty_refs = _empty_fetch_refs(sheet)
    if empty_refs:
        sheet["issues"] = [i for i in sheet["issues"] if not (i["artifact_ref"] in empty_refs
            and i["code"] in {"model_empty_population", "artifact_output_population_incomplete"})]
        for row in sheet["output_records"]:
            if row["locator"]["artifact_ref"] in empty_refs and row["kind"] == "artifact_operation":
                row["content_validation"] = "parsed"
    if operation["program"] == "cmpress" or operation["mode"] == "index":
        artifact_roles = {a["artifact_ref"]: a["role"] for a in artifacts}
        sheet["associations"].append({"relation": "indexed_from",
            "input_keys": [r["record_key"] for r in sheet["input_records"] if r["kind"] == "model"],
            "output_keys": [r["record_key"] for r in sheet["output_records"] if r["kind"] == "artifact_operation"
                            and artifact_roles[r["locator"]["artifact_ref"]] in expected],
            "status": "unresolved"})
    validate_common_sheet(sheet)
    return sheet


def _parameters(parameters):
    if type(parameters) is not dict or set(parameters) - PARAMETER_NAMES:
        raise ValueError("unsupported artifact validation parameters")
    bindings = parameters.get("artifact_bindings", [])
    if type(bindings) is not list:
        raise ValueError("artifact_bindings must be a list")
    refs = set()
    for binding in bindings:
        if type(binding) is not dict or set(binding) != BINDING_FIELDS:
            raise ValueError("invalid artifact binding fields")
        for key, item in binding.items():
            if key == "regular_file":
                if type(item) is not bool:
                    raise ValueError("regular_file must be boolean")
            elif type(item) is not str or not item or "\x00" in item:
                raise ValueError("artifact binding values must be nonempty strings")
        if any(re.fullmatch(r"[a-f0-9]{64}", binding[key]) is None for key in ("artifact_sha256", "source_sha256")):
            raise ValueError("invalid artifact binding digest")
        if binding["artifact_ref"] in refs:
            raise ValueError("duplicate artifact binding")
        refs.add(binding["artifact_ref"])
    return {b["artifact_ref"]: b for b in bindings}


def _population(sheet, direction):
    records = [r for r in sheet[direction+"_records"] if r["kind"] == "model"]
    if direction == "output" and not records and _empty_fetch_refs(sheet):
        return records, True
    complete = bool(records) and all(r["content_validation"] == "parsed_headers_and_boundaries" for r in records)
    complete = complete and not any(i["code"] == "artifact_"+direction+"_population_incomplete" for i in sheet["issues"])
    return records, complete


def _derived(number=None, unit="count", inputs=(), state=None):
    return value(number, basis="derived", unit=unit, inputs=inputs, state=state)


def validate_infernal_artifact_sheet(sheet, *, parameters):
    """Recalculate counts and validation using only saved sheet and explicit bindings.

    Artifact counts/bytes cover retained output roles, including captured stdout
    and stderr. Model counts require a complete decoded population; opaque
    press/index outputs have no invented output model population. Request outcome
    counts are counts of distinct keys, so aliases and duplicate keys do not
    manufacture extra distinct model populations.
    """
    validate_common_sheet(sheet)
    _operation(sheet["operation"])
    bindings = _parameters(parameters)
    result = new_calculations(sheet["operation"], parameters)
    operation = sheet["operation"]
    expected = _expected_outputs(operation)
    artifacts = {a["artifact_ref"]: a for a in sheet["artifacts"]}
    if set(bindings) - set(artifacts):
        raise ValueError("binding references unknown artifact")
    allrows = sheet["input_records"] + sheet["output_records"] + sheet["native_rows"]
    for row in allrows:
        if row["kind"] in ROW_FIELDS and set(row) != ROW_FIELDS[row["kind"]]:
            raise ValueError("invalid supporting row fields")
        if row["kind"] == "artifact_operation" and (row["operation"] != operation or set(row["values"]) != ARTIFACT_VALUE_NAMES):
            raise ValueError("artifact operation row mismatch")
    inrows, input_complete = _population(sheet, "input")
    outrows, output_complete = _population(sheet, "output")
    output_artifacts = [a for a in artifacts.values() if a["role"] in set(expected) | {"stdout", "stderr"}]
    keyrows = [r for r in sheet["native_rows"] if r["kind"] == "key_request"]
    keycounts = Counter(r["requested_key"] for r in keyrows)
    for row in keyrows:
        key = row["requested_key"]
        if type(key) is not str or not key:
            raise ValueError("key_request must retain a nonempty requested key")
        name = [r for r in inrows if r["name"] == key]
        acc = [r for r in inrows if r["accession"] == key]
        matching_input = [r for r in inrows if r in name or r in acc]
        matching_output = [r for r in outrows if any(_same_context(m, r) for m in matching_input)]
        match_kind = "both" if name and acc else "name" if name else "accession" if acc else "unresolved"
        outcome = "satisfied" if len(matching_input) == 1 and matching_output else "missing"
        if len(matching_input) > 1:
            outcome = "ambiguous"
        if keycounts[key] > 1 or not input_complete or any(i["code"] == "artifact_key_population_incomplete" for i in sheet["issues"]):
            outcome = "invalid"
        if (row["matched_input_model_keys"] != [r["record_key"] for r in matching_input]
                or row["output_model_keys"] != [r["record_key"] for r in matching_output]
                or row["match_kind"] != match_kind or row["outcome"] != outcome):
            raise ValueError("key_request relationship mismatch")
    aggregate = [r for r in sheet["native_rows"] if r["kind"] == "artifact_operation"]
    if not aggregate:
        aggregate = [r for r in sheet["output_records"] if r["kind"] == "artifact_operation"][:1]
    components = {name: _derived(unit="byte" if name == "output_byte_count" else "count") for name in COMPONENT_NAMES}
    source = [field_input(r["locator"], "model_record") for r in inrows]
    target = [field_input(r["locator"], "model_record") for r in outrows]
    if input_complete:
        components["input_model_count"] = _derived(len(inrows), inputs=source)
    if output_complete:
        components["output_model_count"] = _derived(len(outrows), inputs=target)
    elif operation["program"] == "cmpress" or operation["mode"] == "index":
        components["output_model_count"] = _derived(state="not_measured")
    components["output_artifact_count"] = _derived(len(output_artifacts), inputs=[field_input(locator(a["artifact_ref"]), "retained_output_artifact") for a in output_artifacts])
    components["output_byte_count"] = _derived(sum(a["size_bytes"] for a in output_artifacts), "byte",
        [field_input(locator(a["artifact_ref"]), "size_bytes") for a in output_artifacts])
    if any(i["code"] in {"artifact_payload_size_mismatch", "model_artifact_size_mismatch"}
           and i["artifact_ref"] in {a["artifact_ref"] for a in output_artifacts} for i in sheet["issues"]):
        components["output_byte_count"] = _derived(unit="byte", state="invalid")
    fetch = operation["program"] == "cmfetch" and operation["mode"] != "index"
    if fetch and keyrows and not any(i["code"] == "artifact_key_population_incomplete" for i in sheet["issues"]):
        components["requested_key_count"] = _derived(len({r["requested_key"] for r in keyrows}), inputs=[field_input(r["locator"], "requested_key") for r in keyrows])
        for outcome, name in (("satisfied", "satisfied_key_count"), ("missing", "missing_key_count"), ("ambiguous", "ambiguous_key_count")):
            components[name] = _derived(len({r["requested_key"] for r in keyrows if r["outcome"] == outcome}), inputs=[field_input(r["locator"], "outcome") for r in keyrows])
    checks = []
    def add(name, outcome, inputs=()):
        checks.append(check(name, outcome, inputs))
    def problem(code, ref=None, field=None):
        result["issues"].append(issue(code, stage="validation", artifact_ref=ref, field=field))
    add("input_population_complete", "pass" if input_complete else "unknown", source)
    add("output_population_complete", "pass" if output_complete else "unknown", target)
    output_set = all(sum(a["role"] == role and a["completeness"] == "complete" for a in output_artifacts) == 1
                     and sum(a["role"] == role for a in output_artifacts) == 1 for role in expected)
    add("output_set_complete", "pass" if output_set else "fail")
    formats = all(a["format"] == expected[a["role"]] for a in output_artifacts if a["role"] in expected)
    formats = formats and not any(i["artifact_ref"] in {a["artifact_ref"] for a in output_artifacts}
        and i["code"] in {"model_signature_invalid", "model_version_unsupported", "model_binary_signature_invalid",
                          "model_binary_header_truncated", "model_text_decode_failed"} for i in sheet["issues"])
    add("output_format", "pass" if formats and output_set else "fail")
    for attr, name in (("name", "model_names_unique"), ("accession", "model_accessions_unique")):
        entries = [r[attr] for r in inrows if r[attr] is not None]
        add(name, "fail" if len(entries) != len(set(entries)) else "pass" if input_complete else "unknown", source)
    if fetch:
        add("requested_keys_unique", "pass" if keyrows and len(keyrows) == len({r["requested_key"] for r in keyrows}) else "fail" if keyrows else "unknown")
        satisfied = bool(keyrows) and all(r["outcome"] == "satisfied" for r in keyrows)
        add("requested_keys_satisfied", "pass" if satisfied else "fail" if keyrows else "unknown")
    if operation["program"] == "cmconvert" or fetch:
        associations = [r for r in sheet["associations"] if r["relation"] in {"converted_from", "fetched_from"}]
        add("model_identity_preserved", "pass" if associations and all(r["status"] == "validated" for r in associations)
            else "fail" if any(r["status"] == "conflicting" for r in associations) else "unknown")
    if operation["program"] == "cmconvert":
        mode = operation["mode"]
        semantic = None
        if output_complete:
            if mode == "legacy_ascii":
                semantic = all(r["filter_hmm"] is None and all(f is None for f in r["calibration"].values()) for r in outrows)
            elif mode in {"maximum_likelihood_hmm", "filter_hmm"}:
                semantic = all(r["model_type"] == "hmm" for r in outrows)
            elif mode == "ascii":
                semantic = all(r["model_type"] == "cm" and r["filter_hmm"] is not None for r in outrows)
        add("conversion_semantics", "unknown" if semantic is None else "pass" if semantic else "fail")
    if operation["program"] == "cmpress":
        add("model_calibration_present", "pass" if input_complete and all(all(f is not None for f in r["calibration"].values()) for r in inrows)
            else "fail" if input_complete else "unknown", source)
        add("model_filter_present", "pass" if input_complete and all(r["filter_hmm"] is not None for r in inrows) else "unknown", source)
    for row in sheet["native_rows"]:
        if row["kind"] != "artifact_operation":
            continue
        comparison = outrows if fetch else inrows
        known = output_complete if fetch else input_complete
        for field, expected_count in (("model_count", len(comparison)),
                ("indexed_name_count", len({r["name"] for r in inrows if r["name"] is not None})),
                ("indexed_accession_count", len({r["accession"] for r in inrows if r["accession"] is not None}))):
            cell = row["values"][field]
            outcome = "unknown" if not known or cell["state"] != "present" else "pass" if cell["value"] == expected_count else "fail"
            add("native_"+field, outcome, cell["inputs"])
            if outcome == "fail":
                problem("artifact_native_count_mismatch", row["locator"]["artifact_ref"], field)
    binary_checks = []
    for art in artifacts.values():
        if art["format"] not in OPAQUE_SIGNATURES:
            continue
        ref = art["artifact_ref"]
        local_checks = []
        facts = [field_input(locator(ref), "artifact")]
        codes = {i["code"] for i in sheet["issues"] if i["artifact_ref"] == ref}
        local_checks.append(check("artifact_signature", "fail" if codes & {"model_binary_signature_invalid", "model_binary_header_truncated"} else
            "pass" if "model_opaque_content" in codes else "unknown", facts))
        local_checks.append(check("artifact_capture_complete", "pass" if art["completeness"] == "complete" else "unknown", facts))
        local_checks.append(check("artifact_payload_identity", "fail" if codes & {"artifact_payload_digest_mismatch", "artifact_payload_size_mismatch",
            "model_artifact_digest_mismatch", "model_artifact_size_mismatch"} else "pass", facts))
        local_checks.append(check("index_content_decoded", "unknown", facts))
        if art["role"] not in _SUFFIXES:
            binary_checks.extend(local_checks)
            continue
        binding = bindings.get(ref)
        if binding is None:
            for name in ("source_binding", "companion_stem", "attempt_binding", "regular_file"):
                local_checks.append(check(name, "unknown", facts))
            result["issues"].append(issue("artifact_binding_missing", stage="validation", severity="information", artifact_ref=ref))
        else:
            original = artifacts.get(binding["source_artifact_ref"])
            source_ok = original is not None and original["role"] == "models" and original["sha256"] == binding["source_sha256"]
            digest_ok = art["sha256"] == binding["artifact_sha256"]
            attempt_ok = binding["expected_attempt_id"] == binding["actual_attempt_id"]
            stem_ok = binding["actual_relative_path"] == binding["staged_source_stem"] + _SUFFIXES[art["role"]]
            for name, passed, code in (("source_binding", source_ok, "artifact_binding_source_mismatch"),
                    ("artifact_payload_identity", digest_ok, "artifact_binding_digest_mismatch"),
                    ("attempt_binding", attempt_ok, "artifact_binding_attempt_mismatch"),
                    ("companion_stem", stem_ok, "artifact_binding_stem_mismatch"),
                    ("regular_file", binding["regular_file"], "artifact_not_regular_file")):
                local_checks.append(check(name, "pass" if passed else "fail", facts))
                if not passed:
                    problem(code, ref)
        binary_checks.extend(local_checks)
    checks.extend(binary_checks)
    if operation["program"] == "cmpress":
        quartet = [bindings.get(a["artifact_ref"]) for a in output_artifacts if a["role"] in _PRESS]
        coherent = len(quartet) == 4 and all(b is not None for b in quartet)
        if coherent:
            coherent = len({(b["source_artifact_ref"], b["source_sha256"], b["actual_attempt_id"], b["staged_source_stem"]) for b in quartet}) == 1
            if not coherent:
                problem("artifact_quartet_binding_mismatch")
        add("quartet_binding", "pass" if coherent else "unknown" if any(b is None for b in quartet) else "fail")
    if aggregate:
        result["rows"].append({"record_key": aggregate[0]["record_key"], "components": components, "checks": checks})
    for row in sheet["output_records"]:
        if row["kind"] != "artifact_operation" or (aggregate and row["record_key"] == aggregate[0]["record_key"]):
            continue
        ref = row["locator"]["artifact_ref"]
        result["rows"].append({"record_key": row["record_key"], "components": {
            "output_byte_count": deepcopy(row["values"]["byte_count"]), "output_artifact_count": _derived(1, inputs=[field_input(row["locator"], "artifact_refs")])},
            "checks": [c for c in binary_checks if any(x["locator"]["artifact_ref"] == ref for x in c["inputs"])]})
    return result
