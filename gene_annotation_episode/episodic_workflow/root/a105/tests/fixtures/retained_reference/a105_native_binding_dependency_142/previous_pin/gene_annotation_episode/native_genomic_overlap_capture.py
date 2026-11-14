"""Capture the fixed files of an already qualified native overlap attempt.

The caller owns selected-action authority and terminal/quiescent writer evidence.
This finite custody operation neither observes lifecycle nor executes scientific
work. Returned identities come only from native_file_capture; the caller freezes
this detached record in its existing action receipt and owns retained-only replay.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath

from .execution_contracts import digest
from .genomic_overlap_contracts import _finite_json_copy, validate_genomic_overlap_record
from . import native_file_capture
from .native_genomic_overlap_contracts import (
    genomic_overlap_output_files, validate_genomic_overlap_batch,
    validate_genomic_overlap_independent_pair_manifest, validate_genomic_overlap_run_plan,
)


_VERSION = "genomic_overlap_native_capture_v1"
_FIELDS = {"version", "original_plan_sha256", "source_action_receipt_ref",
    "writer_closure_receipt_ref", "driver_started", "driver_state", "batch_file",
    "batch", "files", "failures"}
_FILE_FIELDS = {"specification", "declaration_source", "capture", "retained"}
_EMPTY_SHA = hashlib.sha256(b"").hexdigest()


def _require(condition, code="genomic_overlap_invalid_native_capture"):
    if not condition:
        raise ValueError(code)


def _path(value):
    _require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"))
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts
        and value != "/" and not value.startswith("//"))
    return path


def _identity(value, format_name):
    value = validate_genomic_overlap_record("NativeFileIdentity", value)
    _require(value["format"] == format_name and value["artifact_ref"] == "artifact_" + value["sha256"])
    _require(value["size_bytes"] != 0 or value["sha256"] == _EMPTY_SHA)
    return value


def _retained(value, format_name):
    _require(type(value) is dict and set(value) == {"file", "path"})
    _identity(value["file"], format_name)
    _path(value["path"])


def _capture(value, specification):
    value = validate_genomic_overlap_record("NativeFileCapture", value)
    declaration, observed = value["declared"], value["observed"]
    _require(all(declaration[k] == specification[k] for k in ("relative_path", "format")))
    present = declaration["state"] == "present"
    _require((declaration["sha256"] is not None and declaration["size_bytes"] is not None) if present
        else declaration["sha256"] is None and declaration["size_bytes"] is None)
    _require(declaration["size_bytes"] != 0 or declaration["sha256"] == _EMPTY_SHA)
    if observed is not None:
        _identity(observed, specification["format"])
    same = observed is not None and all(observed[k] == declaration[k] for k in ("sha256", "size_bytes", "format"))
    outcome, failure = value["outcome"], value["failure"]
    if outcome == "declared_absent":
        _require(not present and observed is None and failure is None)
    elif outcome == "verified":
        _require(present and same and failure is None)
    elif outcome == "digest_mismatch":
        _require(present and observed is not None and not same and failure == "capture_file_digest_mismatch")
    else:
        _require(present and observed is None and failure == "capture_file_unavailable")


def _arguments(original_plan, source_action_receipt_ref, writer_closure_receipt_ref, driver_started):
    plan = validate_genomic_overlap_run_plan(original_plan)
    _require(type(source_action_receipt_ref) is str and bool(source_action_receipt_ref))
    _require(type(writer_closure_receipt_ref) is str and bool(writer_closure_receipt_ref))
    _require(driver_started is None or type(driver_started) is bool)
    return plan


def validate_genomic_overlap_native_capture(value: object, *, original_plan: dict) -> dict:
    """Validate detached fixed-order transport data without reading any path.

    Declaration authentication occurs during capture and again in the retained
    worker. This pure record check cannot establish receipt authority or examine
    the manifest bodies, which are deliberately not duplicated in this record.
    """
    value = _finite_json_copy(value)
    _require(type(value) is dict and set(value) == _FIELDS)
    plan = _arguments(original_plan, value["source_action_receipt_ref"],
        value["writer_closure_receipt_ref"], value["driver_started"])
    _require(value["version"] == _VERSION and value["original_plan_sha256"] == digest(plan))
    state = value["driver_state"]
    _require(type(state) is str and state in ("sealed_batch", "unsealed_attempt", "not_started"))
    _require((value["driver_started"] is False) == (state == "not_started"))
    job = plan["requested_job"]["native_genomic_overlap"]
    expected = genomic_overlap_output_files(job["request"])
    retained = []
    if value["batch_file"] is not None:
        _identity(value["batch_file"], expected[-1]["format"])
    if value["batch"] is not None:
        _retained(value["batch"], expected[-1]["format"])
        _require(value["batch"]["file"] == value["batch_file"])
        retained.append(value["batch"])
    _require((value["batch"] is not None) == (state == "sealed_batch"))
    _require(type(value["files"]) is list and len(value["files"]) == len(expected) - 1)
    for row, specification in zip(value["files"], expected[:-1]):
        _require(type(row) is dict and set(row) == _FILE_FIELDS and row["specification"] == specification)
        source, captured = row["declaration_source"], row["capture"]
        _require(type(source) is str and source in ("batch", "pair", "none"))
        _require((source == "batch") == (state == "sealed_batch"))
        if source == "none":
            _require(captured is None)
        else:
            _capture(captured, specification)
            if source == "pair":
                _require(specification["role"] in ("canonical_set", "overlap_stdout", "overlap_stderr"))
        if row["retained"] is not None:
            _retained(row["retained"], specification["format"])
            _require(captured is None or row["retained"]["file"] == captured["observed"])
            retained.append(row["retained"])
    if state == "not_started":
        _require(value["batch_file"] is None and all(row["capture"] is None and row["retained"] is None
            for row in value["files"]))
    # Store deduplicates bytes independently of each output's format label.
    paths = {}
    for row in retained:
        path = _path(row["path"])
        identity = {key: row["file"][key] for key in ("artifact_ref", "sha256", "size_bytes")}
        for previous, prior in paths.items():
            _require(path not in previous.parents and previous not in path.parents
                and (path != previous or identity == prior))
        paths[path] = identity
    _require(type(value["failures"]) is list)
    set_keys = {spec["set_key"] for spec in job["request"]["region_sets"]}
    comparisons = {pair["comparison_key"]: pair for pair in job["request"]["comparisons"]}
    for failure in value["failures"]:
        validate_genomic_overlap_record("Failure", failure)
        sk, pk = failure["set_key"], failure["comparison_key"]
        _require(sk is None or sk in set_keys)
        _require(pk is None or pk in comparisons)
        _require(sk is None or pk is None or sk in (comparisons[pk]["a_set_key"], comparisons[pk]["b_set_key"]))
    return value


def _failure(specification, field_path, *, code, stage="capture", identity=None,
        expected=None, observed=None, requirement=None, comparison_key=None, refs=()):
    if requirement is None:
        requirement = "complete_input" if specification["role"] in ("original_input", "parsed_set") else "original_native_output"
    return validate_genomic_overlap_record("Failure", {"code": code, "stage": stage,
        "set_key": specification["set_key"],
        "comparison_key": comparison_key if comparison_key is not None else specification["comparison_key"],
        "artifact_ref": identity["artifact_ref"] if identity is not None else None,
        "locator": None, "field_path": field_path, "expected_value": expected, "observed_value": observed,
        "partial_artifact_refs": list(refs), "requirement": requirement})


def _missing_code(specification):
    return "input_unavailable" if specification["role"] == "original_input" else "native_output_unavailable"


def _mismatch_code(specification):
    return "input_digest_mismatch" if specification["role"] == "original_input" else "artifact_digest_mismatch"


def _retain(store, identity, specification, field_path, failures):
    try:
        path = native_file_capture.retained_native_file(store, identity)
    except native_file_capture.NativeFileCaptureError as error:
        if error.code not in ("retained_artifact_unavailable", "retained_artifact_mismatch"):
            raise
        mismatch = error.code == "retained_artifact_mismatch"
        failures.append(_failure(specification, field_path, identity=identity,
            code=_mismatch_code(specification) if mismatch else _missing_code(specification),
            requirement="matching_file_identity" if mismatch else None, expected=identity))
        return None
    return {"file": deepcopy(identity), "path": str(path)}


def _undeclared(store, plan, specification, field_path, failures):
    try:
        identity = native_file_capture.capture_native_file(store, directory=plan["attempt_directory"],
            relative_path=specification["relative_path"], format=specification["format"])
    except native_file_capture.NativeFileCaptureError as error:
        # A storage failure before a helper returns an identity is not producer
        # absence. Propagate it, preserving the helper's typed failure boundary.
        if error.code != "capture_file_unavailable":
            raise
        failures.append(_failure(specification, field_path, code=_missing_code(specification)))
        return None, None
    retained = _retain(store, identity, specification, field_path, failures)
    if specification["role"] == "original_input":
        source = next(row["source"]["file"] for row in plan["requested_job"]["native_genomic_overlap"]["request"]["region_sets"]
            if row["set_key"] == specification["set_key"])
        fields = ("sha256", "size_bytes", "format")
        if any(identity[k] != source[k] for k in fields):
            failures.append(_failure(specification, field_path, code="input_digest_mismatch", identity=identity,
                requirement="matching_file_identity", expected={k: source[k] for k in fields},
                observed={k: identity[k] for k in fields}))
    return identity, retained


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "genomic_overlap_duplicate_control_key")
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError("genomic_overlap_nonfinite_control_json")
    value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite))
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8") + b"\n"
    _require(raw == canonical, "genomic_overlap_noncanonical_control_json")
    return value


def _seal(retained, specification, field_path, failures, validate):
    if retained is None:
        return None
    identity = retained["file"]
    try:
        raw = Path(retained["path"]).read_bytes()
    except OSError:
        failures.append(_failure(specification, field_path, code="native_output_unavailable", identity=identity))
        return None
    # _retain used the shared complete-byte verifier. Its caller-held stable
    # Store requirement applies while reading the control body as well; this
    # component adds canonical/semantic checks, not another retention verifier.
    try:
        value = _decode(raw)
    except (ValueError, UnicodeError):
        failures.append(_failure(specification, field_path, code="native_output_malformed", stage="parse", identity=identity))
        return None
    try:
        return validate(value)
    except ValueError:
        failures.append(_failure(specification, field_path, code="original_attempt_mismatch", stage="parse", identity=identity,
            requirement="matching_file_identity"))
        return None


def _declared_rows(store, plan, selected, source, failures):
    """Copy each unique declaration once and preserve every helper outcome."""
    captures = native_file_capture.capture_declared_native_files(store, directory=plan["attempt_directory"],
        declarations=[declaration for _, _, declaration in selected])
    rows = {}
    for (index, specification, _), captured in zip(selected, captures):
        observed = captured["observed"]
        field_path = f"/files/{index}"
        retained = _retain(store, observed, specification, field_path + "/retained", failures) if observed is not None else None
        if captured["outcome"] == "unavailable":
            failures.append(_failure(specification, field_path + "/capture", code=_missing_code(specification)))
        elif captured["outcome"] == "digest_mismatch":
            failures.append(_failure(specification, field_path + "/capture", code=_mismatch_code(specification),
                identity=observed, requirement="matching_file_identity",
                expected={k: captured["declared"][k] for k in ("sha256", "size_bytes")},
                observed={k: observed[k] for k in ("sha256", "size_bytes")}))
        rows[index] = {"specification": specification, "declaration_source": source,
            "capture": captured, "retained": retained}
    return rows


def capture_genomic_overlap_native_files(store, *, original_plan: dict,
        source_action_receipt_ref: str, writer_closure_receipt_ref: str,
        driver_started: bool | None) -> dict:
    """Retain exactly this qualified original attempt's fixed output paths.

    ``False`` requires caller-held evidence that the driver never started.
    Missing files cannot establish that fact. No original input binding path,
    software path, network service or lifecycle endpoint is accessed here.
    """
    plan = _arguments(original_plan, source_action_receipt_ref, writer_closure_receipt_ref, driver_started)
    request = plan["requested_job"]["native_genomic_overlap"]["request"]
    specifications = genomic_overlap_output_files(request)
    rows = [{"specification": spec, "declaration_source": "none", "capture": None, "retained": None}
        for spec in specifications[:-1]]
    failures = []
    result = {"version": _VERSION, "original_plan_sha256": digest(plan),
        "source_action_receipt_ref": source_action_receipt_ref,
        "writer_closure_receipt_ref": writer_closure_receipt_ref, "driver_started": driver_started,
        "driver_state": "not_started" if driver_started is False else "unsealed_attempt",
        "batch_file": None, "batch": None, "files": rows, "failures": failures}
    if driver_started is False:
        for index, spec in enumerate(specifications):
            failures.append(_failure(spec, "/batch" if index == len(rows) else f"/files/{index}",
                code="native_output_unavailable", stage="native", requirement="original_native_output",
                observed=driver_started, refs=[writer_closure_receipt_ref]))
        return validate_genomic_overlap_native_capture(result, original_plan=plan)
    batch_spec = specifications[-1]
    result["batch_file"], retained_batch = _undeclared(store, plan, batch_spec, "/batch", failures)
    batch = _seal(retained_batch, batch_spec, "/batch", failures,
        lambda value: validate_genomic_overlap_batch(value, plan=plan))
    if batch is not None:
        result.update(driver_state="sealed_batch", batch=retained_batch)
        captured = _declared_rows(store, plan, [(i, row["specification"], row["declaration"])
            for i, row in enumerate(batch["files"])], "batch", failures)
        result["files"] = [captured[i] for i in range(len(rows))]
        return validate_genomic_overlap_native_capture(result, original_plan=plan)
    # A batch cannot qualify. Retain independent seals first, then combine
    # their declarations by fixed path, without selecting among contradictions.
    declarations = {}
    for index, row in enumerate(rows):
        spec = row["specification"]
        if spec["role"] != "pair_manifest":
            continue
        _, row["retained"] = _undeclared(store, plan, spec, f"/files/{index}", failures)
        comparison = next(pair for pair in request["comparisons"] if pair["comparison_key"] == spec["comparison_key"])
        manifest = _seal(row["retained"], spec, f"/files/{index}", failures,
            lambda value: validate_genomic_overlap_independent_pair_manifest(value, plan=plan, comparison=comparison))
        if manifest is None:
            failures.append(_failure(spec, f"/files/{index}", code="native_output_partial",
                requirement="complete_native_output"))
            continue
        for file in manifest["files"]:
            declaration = file["declaration"]
            declarations.setdefault(declaration["relative_path"], []).append(
                {"comparison_key": comparison["comparison_key"], "declaration": declaration})
    selected = []
    for index, row in enumerate(rows):
        spec = row["specification"]
        if spec["role"] == "pair_manifest":
            continue
        candidates = declarations.get(spec["relative_path"], [])
        if candidates and all(item["declaration"] == candidates[0]["declaration"] for item in candidates):
            selected.append((index, spec, candidates[0]["declaration"]))
            continue
        if candidates:
            for candidate in candidates:
                failures.append(_failure(spec, f"/files/{index}/capture", code="original_attempt_mismatch", stage="parse",
                    comparison_key=candidate["comparison_key"], requirement="matching_file_identity", observed=candidates))
        _, row["retained"] = _undeclared(store, plan, spec, f"/files/{index}", failures)
    for index, row in _declared_rows(store, plan, selected, "pair", failures).items():
        rows[index] = row
    return validate_genomic_overlap_native_capture(result, original_plan=plan)


__all__ = ["capture_genomic_overlap_native_files", "validate_genomic_overlap_native_capture"]
