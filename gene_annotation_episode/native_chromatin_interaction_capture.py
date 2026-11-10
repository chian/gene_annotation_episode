"""Complete byte custody for one caller-authenticated chromatin attempt.

The result host owns original-action authority, writer closure and persistence.
This helper only retains fixed output files and authenticates their declarations.
It does not read original input bindings, run native work or calculate scores.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

from . import native_file_capture
from .terminal_native_file_capture import capture_execution_file, capture_execution_declarations
from .chromatin_interaction_contracts import decode_chromatin_json, validate_chromatin_record
from .native_chromatin_interaction_contracts import (
    TABLE_ROLES, canonical, failure, path_value,
    validate_chromatin_bundle, validate_chromatin_population_seal,
    validate_chromatin_run_plan,
)


_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _require(condition):
    if not condition:
        raise ValueError("chromatin_invalid_native_capture")


def _identity(value, format_name):
    value = validate_chromatin_record("NativeFileIdentity", value)
    _require(value["format"] == format_name and value["artifact_ref"] == "artifact_" + value["sha256"])
    _require((value["size_bytes"] == 0) == (value["sha256"] == _EMPTY_SHA256))
    return value


def _declaration(value, specification):
    value = validate_chromatin_record("NativeFileDeclaration", value)
    _require(all(value[k] == specification[k] for k in ("relative_path", "format")))
    path_value(value["relative_path"], absolute=False)
    if value["state"] == "present":
        _require((value["size_bytes"] == 0) == (value["sha256"] == _EMPTY_SHA256))
    return value


def _captured(value, specification):
    value = validate_chromatin_record("NativeFileCapture", value)
    declaration = _declaration(value["declared"], specification)
    actual = value["observed"]
    if actual is not None:
        _identity(actual, specification["format"])
    equal = actual is not None and all(actual[k] == declaration[k] for k in ("sha256", "size_bytes", "format"))
    _require(
        (value["outcome"] == "verified" and declaration["state"] == "present" and equal and value["failure"] is None)
        or (value["outcome"] == "declared_absent" and declaration["state"] == "absent" and actual is None and value["failure"] is None)
        or (value["outcome"] == "unavailable" and declaration["state"] == "present" and actual is None and value["failure"] == "capture_file_unavailable")
        or (value["outcome"] == "digest_mismatch" and declaration["state"] == "present" and actual is not None and not equal and value["failure"] == "capture_file_digest_mismatch"))


def _retained(value, format_name):
    value = validate_chromatin_record("RetainedFile", value)
    identity = _identity(value["file"], format_name)
    path = path_value(value["path"], absolute=True)
    # These are actual Store artifact paths, not producer paths or arbitrary
    # caller labels. Equality below is still a pure record check, not authority.
    _require(path.name == identity["sha256"] and path.parent.name == identity["sha256"][:2]
        and path.parent.parent.name == "artifacts")
    return path


def _input_key(specification, plan):
    request = plan["requested_job"]["native_chromatin_interactions"]["request"]
    if specification["role"] == "original_contact":
        return request["contact"]["input_key"]
    if specification["role"] == "original_elements" and request["elements"] is not None:
        return request["elements"]["input_key"]
    return None


def _located_failure(specification, plan, field_path, *, code="input_unavailable",
        stage="capture", retained=None, refs=(), requirement="original_native_outcome"):
    return failure(code, stage, input_key=_input_key(specification, plan),
        population_key=specification["population_key"], field_path=field_path,
        artifact_ref=retained["file"]["artifact_ref"] if retained is not None else None,
        partial_artifact_refs=refs, requirement=requirement)


def validate_chromatin_native_capture(value: object, *, original_plan: dict) -> dict:
    """Validate detached custody data without filesystem or lifecycle access.

    Manifest bodies are not duplicated in this transport record. Capture checks
    them against the original plan; the retained worker checks them again. This
    pure validator cannot authenticate receipt authority or retained bytes.
    """
    plan = validate_chromatin_run_plan(original_plan)
    value = validate_chromatin_record("NativeCapture", value)
    _require(value["original_plan"] == plan)
    state = value["driver_state"]
    _require((state == "sealed_bundle") == (value["bundle"] is not None))
    specifications = plan["outputs"]
    _require([row["specification"] for row in value["files"]] == specifications[:-1])
    retained = []
    if value["bundle"] is not None:
        _retained(value["bundle"], specifications[-1]["format"])
        retained.append(value["bundle"])
    for row in value["files"]:
        specification, capture = row["specification"], row["capture"]
        source = row["declaration_source"]
        _require((source == "bundle") == (state == "sealed_bundle"))
        if source == "none":
            _require(capture is None)
        else:
            _require(capture is not None)
            _captured(capture, specification)
            _require(source != "population" or specification["role"] in TABLE_ROLES)
        if row["retained"] is not None:
            _retained(row["retained"], specification["format"])
            _require(capture is None or row["retained"]["file"] == capture["observed"])
            retained.append(row["retained"])
        # A returned observation has passed the Store verifier. Storage failure
        # propagates rather than turning retained custody into producer absence.
        if capture is not None:
            _require((capture["observed"] is not None) == (row["retained"] is not None))
    if state == "not_started":
        _require(all(row["capture"] is None and row["retained"] is None for row in value["files"]))
    paths, identities = {}, {}
    for row in retained:
        path = path_value(row["path"], absolute=True)
        identity = tuple(row["file"][k] for k in ("artifact_ref", "sha256", "size_bytes"))
        _require(identity not in identities or identities[identity] == path)
        for previous, content in paths.items():
            _require(path not in previous.parents and previous not in path.parents
                and (path != previous or identity == content))
        paths[path], identities[identity] = identity, path
    request = plan["requested_job"]["native_chromatin_interactions"]["request"]
    inputs = {row["input_key"] for row in plan["requested_job"]["native_chromatin_interactions"]["input_bindings"]}
    populations = {row["population_key"] for row in request["populations"]}
    elements = {row["element_key"] for row in request["elements"]["assignments"]} if request["elements"] else set()
    for problem in value["failures"]:
        _require(problem["input_key"] is None or problem["input_key"] in inputs)
        _require(problem["population_key"] is None or problem["population_key"] in populations)
        _require(problem["element_key"] is None or problem["element_key"] in elements)
        # Capture does not construct scientific pairs or native-input locations.
        _require(problem["pair_key"] is None and problem["locator"] is None)
        field = problem["field_path"]
        _require(type(field) is str)
        parts = field.split("/")
        if len(parts) >= 2 and parts[1] == "bundle":
            specification = specifications[-1]
        else:
            _require(len(parts) >= 3 and parts[1] == "files" and parts[2].isascii() and parts[2].isdigit())
            index = int(parts[2])
            _require(str(index) == parts[2] and index < len(value["files"]))
            specification = specifications[index]
        _require(problem["population_key"] == specification["population_key"]
            and problem["input_key"] == _input_key(specification, plan))
    return value


def _retain(store, identity):
    return {"file": deepcopy(identity), "path": str(native_file_capture.retained_native_file(store, identity))}


def _undeclared(store, plan, specification, field_path, failures, command_proof=None):
    try:
        identity = capture_execution_file(store, directory=plan["attempt_directory"],
            relative_path=specification["relative_path"], format=specification["format"], command_proof=command_proof)
    except native_file_capture.NativeFileCaptureError as error:
        if error.code != "capture_file_unavailable":
            raise
        failures.append(_located_failure(specification, plan, field_path))
        return None
    retained = _retain(store, identity)
    request = plan["requested_job"]["native_chromatin_interactions"]["request"]
    expected = None
    if specification["role"] == "original_contact":
        expected = request["contact"]["file"]
    elif specification["role"] == "original_elements" and request["elements"] is not None:
        expected = request["elements"]["file"]
    elif specification["role"] == "original_metadata":
        raw = canonical(request["supplied_metadata"])
        expected = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "format": specification["format"]}
    if expected is not None and any(identity[k] != expected[k] for k in ("sha256", "size_bytes", "format")):
        failures.append(_located_failure(specification, plan, field_path, code="input_digest_mismatch",
            retained=retained, requirement="matching_file_identity"))
    return retained


def _control(retained, specification, plan, field_path, failures, validate):
    if retained is None:
        return None
    try:
        raw = Path(retained["path"]).read_bytes()
    except OSError as error:
        raise native_file_capture.NativeFileCaptureError("retained_artifact_unavailable") from error
    try:
        value = decode_chromatin_json(raw)
        # Match the actual C3 encoder and reader, including its permitted single
        # final newline. Whitespace/key-order/number-encoding rewrites reject.
        _require(raw in (canonical(value), canonical(value) + b"\n"))
    except (ValueError, UnicodeError):
        failures.append(_located_failure(specification, plan, field_path, code="malformed_native_header",
            stage="native_parse", retained=retained, requirement="valid_native_structure"))
        return None
    try:
        return validate(value)
    except ValueError:
        failures.append(_located_failure(specification, plan, field_path, code="original_attempt_mismatch",
            stage="native_parse", retained=retained, requirement="matching_original_attempt"))
        return None


def _bundle(value, plan):
    value = validate_chromatin_bundle(value, plan=plan)
    for row in value["outputs"]:
        _declaration(row["declaration"], row["specification"])
    return value


def _population(value, plan, population):
    value = validate_chromatin_population_seal(value, plan=plan, population=population)
    specs = {r["role"]: r for r in plan["outputs"]
        if r["population_key"] == population["population_key"] and r["role"] in TABLE_ROLES}
    for row in value["tables"]:
        _declaration(row["declaration"], specs[row["draft"]["role"]])
    return value


def _declared_rows(store, plan, selected, source, failures, command_proof=None):
    captures = capture_execution_declarations(store, directory=plan["attempt_directory"],
        declarations=[declaration for _, _, declaration in selected], command_proof=command_proof)
    rows = {}
    for (index, specification, _), captured in zip(selected, captures):
        retained = _retain(store, captured["observed"]) if captured["observed"] is not None else None
        if captured["outcome"] in ("unavailable", "digest_mismatch"):
            code = "input_unavailable" if captured["outcome"] == "unavailable" else (
                "input_digest_mismatch" if specification["role"] in ("original_contact", "original_elements") else "artifact_digest_mismatch")
            failures.append(_located_failure(specification, plan, f"/files/{index}/capture", code=code,
                retained=retained, requirement="matching_file_identity" if captured["outcome"] == "digest_mismatch" else "original_native_outcome"))
        rows[index] = {"specification": specification, "declaration_source": source,
            "capture": captured, "retained": retained}
    return rows


def capture_chromatin_native_files(store, *, original_plan: dict,
        source_action_receipt_ref: str, writer_closure_receipt_ref: str,
        driver_started: bool | None, command_proof=None) -> dict:
    """Retain the exact fixed outputs after the caller qualifies writer closure.

    ``False`` requires affirmative caller-held evidence that this driver never
    started. Missing files alone leave its state unknown. Storage errors retain
    their shared helper error codes and are never recoded as absent producers.
    """
    plan = validate_chromatin_run_plan(original_plan)
    _require(type(source_action_receipt_ref) is str and bool(source_action_receipt_ref)
        and type(writer_closure_receipt_ref) is str and bool(writer_closure_receipt_ref)
        and (driver_started is None or type(driver_started) is bool))
    rows = [{"specification": spec, "declaration_source": "none", "capture": None, "retained": None}
        for spec in plan["outputs"][:-1]]
    failures = []
    result = {"original_plan": plan, "source_action_receipt_ref": source_action_receipt_ref,
        "writer_closure_receipt_ref": writer_closure_receipt_ref,
        "driver_state": "not_started" if driver_started is False else "unsealed_attempt",
        "bundle": None, "files": rows, "failures": failures}
    if driver_started is False:
        for index, spec in enumerate(plan["outputs"]):
            failures.append(_located_failure(spec, plan, "/bundle" if index == len(rows) else f"/files/{index}",
                stage="execution", refs=[writer_closure_receipt_ref]))
        return validate_chromatin_native_capture(result, original_plan=plan)
    spec = plan["outputs"][-1]
    retained_bundle = _undeclared(store, plan, spec, "/bundle", failures, command_proof)
    bundle = _control(retained_bundle, spec, plan, "/bundle", failures, lambda value: _bundle(value, plan))
    if bundle is not None:
        result.update(driver_state="sealed_bundle", bundle=retained_bundle)
        captured = _declared_rows(store, plan, [(i, r["specification"], r["declaration"])
            for i, r in enumerate(bundle["outputs"])], "bundle", failures, command_proof)
        result["files"] = [captured[i] for i in range(len(rows))]
        return validate_chromatin_native_capture(result, original_plan=plan)
    populations = {p["population_key"]: p for p in plan["requested_job"]["native_chromatin_interactions"]["request"]["populations"]}
    seals = {}
    for index, row in enumerate(rows):
        spec = row["specification"]
        if spec["role"] != "population_manifest":
            continue
        row["retained"] = _undeclared(store, plan, spec, f"/files/{index}", failures, command_proof)
        seal = _control(row["retained"], spec, plan, f"/files/{index}", failures,
            lambda value: _population(value, plan, populations[spec["population_key"]]))
        if seal is not None:
            seals[spec["population_key"]] = (index, row, seal)
        else:
            failures.append(_located_failure(spec, plan, f"/files/{index}", code="native_output_partial",
                retained=row["retained"], requirement="complete_population"))
    known = [(index, row, seal) for index, row, seal in seals.values() if seal["native"]["metadata"] is not None]
    if known and any(seal["native"] != known[0][2]["native"] for _, _, seal in known):
        references = list(dict.fromkeys(row["retained"]["file"]["artifact_ref"] for _, row, _ in known))
        for index, row, _ in known:
            failures.append(_located_failure(row["specification"], plan, f"/files/{index}/native",
                code="original_attempt_mismatch", stage="native_parse", retained=row["retained"],
                refs=references, requirement="matching_original_attempt"))
    selected = []
    for index, row in enumerate(rows):
        spec = row["specification"]
        if spec["role"] == "population_manifest":
            continue
        if spec["role"] in TABLE_ROLES and spec["population_key"] in seals:
            seal = seals[spec["population_key"]][2]
            declaration = next(r["declaration"] for r in seal["tables"] if r["draft"]["role"] == spec["role"])
            selected.append((index, spec, declaration))
        else:
            row["retained"] = _undeclared(store, plan, spec, f"/files/{index}", failures, command_proof)
    for index, row in _declared_rows(store, plan, selected, "population", failures, command_proof).items():
        rows[index] = row
    return validate_chromatin_native_capture(result, original_plan=plan)


__all__ = ["capture_chromatin_native_files", "validate_chromatin_native_capture"]
