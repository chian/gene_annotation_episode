"""One finite retained FBA read, shared calculation and source-free projection.

No producer, scientific runtime, Store, process launcher or acquisition is in
this worker's import closure. Native controls are supplied retained bytes.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

from .execution_contracts import canonical, digest
from .flux_balance_contracts import ISSUE_CODES, validate_flux_balance_record
from .flux_balance_readers import parse_fba_capture
from .flux_balance_sheet import populate_flux_balance_sheet, validate_flux_balance_sheet
from .flux_balance_calculations import calculate_flux_balance_sheet
from .flux_balance_result_contracts import validate_fba_projection
from .flux_balance_result_views import project_fba_result
from .flux_balance_worker_contracts import (EVIDENCE_ROLES, OUTPUTS, RESULT_VERSION,
    _require, validate_flux_balance_worker_plan, validate_flux_balance_worker_result)
from .native_flux_balance_contracts import path_value
from .native_flux_balance_storage import decode_json, directory, immutable_json, read_bytes

__all__ = ["execute_flux_balance_worker"]
_OWNER = ".flux-balance-worker-plan.json"
_RESULT = "worker-result.json"


def _issue(code, field, *, stage="capture", source=None):
    return validate_flux_balance_record("Issue", {"code": code, "stage": stage, "field": field,
        "source_row_index": None, "reaction_position": None, "metabolite_position": None,
        "variable_position": None, "constraint_position": None, "detail_file": deepcopy(source)})


def _unique(issues):
    result, seen = [], set()
    for issue in issues:
        key = canonical(issue)
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result


def _record_failure(error, field, *, stage):
    code, _, pointer = str(error).partition(":")
    if code not in ISSUE_CODES:
        code, pointer = "schema_invalid", ""
    return _issue(code, field + pointer if pointer.startswith("/") else field, stage=stage)


def _json(raw):
    value = decode_json(raw)
    # decode_json rejects duplicate keys and JSON constants; canonical also
    # rejects numbers such as 1e999 that Python's JSON decoder maps to infinity.
    canonical(value)
    return value


def _pin(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _read(retained, field, issues):
    if retained is None:
        issues.append(_issue("artifact_missing", field))
        return None
    try:
        raw = read_bytes(retained["path"])
    except (OSError, ValueError):
        issues.append(_issue("artifact_missing", field))
        return None
    if _pin(raw) != {k: retained["file"][k] for k in ("sha256", "size_bytes")}:
        issues.append(_issue("artifact_identity_conflict", field))
        return None
    return raw


def _document(retained, field, issues):
    raw = _read(retained, field, issues)
    if raw is None:
        return None
    try:
        return _json(raw)
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        issues.append(_issue("schema_invalid", field, source=retained["file"]))
        return None


def _controls(original, capture, issues):
    """Join records, keeping missing evidence separate from contradictions."""
    controls = capture["controls"]
    owner = _document(controls["owner"], "/controls/owner", issues)
    start = _document(controls["started"], "/controls/started", issues)
    checks = []
    def join(value, expected, field, source):
        if value is None:
            checks.append(None)
            return False
        agrees = canonical(value) == canonical(expected)
        checks.append(agrees)
        if not agrees:
            issues.append(_issue("artifact_identity_conflict", field, source=source))
        return agrees
    owner_ok = join(owner, original, "/controls/owner", None if controls["owner"] is None else controls["owner"]["file"])
    v2 = original["version"] == "flux_balance_run_plan_v2"
    keys = {"plan_sha256", "started_at"} | ({"environment_observation_sha256"} if v2 else set())
    start_ok = False
    if start is None:
        checks.append(None)
    elif type(start) is not dict or set(start) != keys or type(start["started_at"]) is not str or not start["started_at"]:
        checks.append(None)
        issues.append(_issue("schema_invalid", "/controls/started", source=controls["started"]["file"]))
    else:
        start_ok = join(start["plan_sha256"], digest(original), "/controls/started/plan_sha256", controls["started"]["file"])
    if v2:
        observation = _document(controls["environment"], "/controls/environment", issues)
        expected = original["environment_binding"]["realized_environment"]
        if observation is None:
            checks.append(None)
        elif (type(observation) is not dict or set(observation) != {"version", "plan_sha256", "expected_environment", "observed_environment"}
                or observation["version"] != "flux_balance_environment_observation_v1"
                or type(observation["observed_environment"]) is not dict
                or set(observation["observed_environment"]) != set(expected)
                or any(v is not None and type(v) is not str for v in observation["observed_environment"].values())):
            checks.append(None)
            issues.append(_issue("schema_invalid", "/controls/environment", source=controls["environment"]["file"]))
        else:
            source = controls["environment"]["file"]
            join(observation["plan_sha256"], digest(original), "/controls/environment/plan_sha256", source)
            join(observation["expected_environment"], expected, "/controls/environment/expected_environment", source)
            join(start.get("environment_observation_sha256") if type(start) is dict else None,
                 digest(observation), "/controls/started/environment_observation_sha256",
                 None if controls["started"] is None else controls["started"]["file"])
            if observation["observed_environment"] != expected:
                # A failed original environment remains that original attempt.
                issues.append(_issue("binding_unavailable", "/controls/environment/observed_environment", source=source))
    elif controls["environment"] is not None:
        # Do not infer v2 evidence for a v1 plan.
        _read(controls["environment"], "/controls/environment", issues)
        checks.append(False)
        issues.append(_issue("artifact_identity_conflict", "/controls/environment", source=controls["environment"]["file"]))
    return checks, owner_ok and start_ok


def _manifest_transport(original, payloads, issues):
    """Only the transport envelope assigns native states; scientific parsing
    still receives the complete unmodified original manifest bytes.
    """
    payload = payloads["manifest"]
    if payload["bytes"] is None:
        return None
    source = payload["file"]
    try:
        manifest = _json(payload["bytes"])
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        issues.append(_issue("schema_invalid", "/files/manifest", source=source))
        return None
    if (type(manifest) is not dict or manifest.get("version") != "flux_balance_native_manifest_v1"
            or manifest.get("sealed") is not True):
        issues.append(_issue("schema_invalid", "/files/manifest", source=source))
        payload["state"] = "incompatible"
        return None
    job = original["requested_job"]["native_flux_balance"]
    expected = {"attempt": original["identity"], "software_sha256": digest(job["software"]),
        "source_function_sha256": job["source_function_sha256"],
        "model_identity": {k: job["model_input"]["file"][k] for k in ("sha256", "size_bytes")}}
    conflict = False
    for key, value in expected.items():
        if canonical(manifest.get(key)) != canonical(value):
            issues.append(_issue("artifact_identity_conflict", "/files/manifest/" + key, source=source))
            conflict = True
    if conflict:
        payload["state"] = "incompatible"
        return False
    rows = manifest.get("files")
    if type(rows) is not list:
        issues.append(_issue("schema_invalid", "/files/manifest/files", source=source))
        payload["state"] = "incompatible"
        return None
    expected_rows = original["outputs"][:-1]
    for expected_row in expected_rows:
        role = expected_row["role"]
        declarations = [r for r in rows if type(r) is dict and r.get("role") == role]
        actual = payloads[role]
        valid = len(declarations) == 1
        declaration = declarations[0] if valid else None
        if valid:
            try:
                validate_flux_balance_record("ManifestFile", declaration)
            except ValueError:
                valid = False
        if valid:
            valid = all(declaration[k] == expected_row[k] for k in ("role", "relative_path", "format"))
        if valid and actual["bytes"] is not None:
            valid = (declaration["state"] != "absent" and declaration["identity"] == _pin(actual["bytes"]))
        if not valid:
            if actual["bytes"] is not None:
                actual["state"] = "incompatible"
            issues.append(_issue("artifact_identity_conflict", "/files/manifest/files/" + role, source=source))
            conflict = True
        elif actual["bytes"] is not None:
            actual["state"] = declaration["state"]
        # An absent actual role stays absent, even when declared present.
    if len(rows) != len(expected_rows) or any(type(r) is not dict or r.get("role") not in payloads or r.get("role") == "manifest" for r in rows):
        issues.append(_issue("artifact_identity_conflict", "/files/manifest/files", source=source))
        conflict = True
    return not conflict


def _native(plan, issues):
    original, capture = plan["original_plan"], plan["capture"]
    issues.extend(deepcopy(capture["failures"]))
    payloads = {}
    for row in capture["files"]:
        raw = _read(row["retained"], "/files/" + row["role"], issues)
        payloads[row["role"]] = {"file": None if raw is None else row["retained"]["file"],
            "bytes": raw, "state": "absent" if raw is None else "present"}
    priors = []
    for index, retained in enumerate(capture["prior_sources"]):
        raw = _read(retained, f"/prior_sources/{index}", issues)
        if raw is not None:
            priors.append({"file": retained["file"], "bytes": raw})
    checks, own_start = _controls(original, capture, issues)
    selected = payloads["selected_request"]
    if selected["bytes"] is None:
        checks.append(None)
    else:
        try:
            value = _json(selected["bytes"])
        except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
            checks.append(None)
            issues.append(_issue("schema_invalid", "/files/selected_request", source=selected["file"]))
        else:
            same = canonical(value) == canonical({"version": "flux_balance_selected_request_v1", "attempt": original["identity"],
                "requested_job": original["requested_job"]})
            checks.append(same)
            if not same:
                selected["state"] = "incompatible"
                issues.append(_issue("artifact_identity_conflict", "/files/selected_request", source=selected["file"]))
    checks.append(_manifest_transport(original, payloads, issues))
    checks.append(True if capture["driver_started"] is True else None)
    if any(i["code"] == "artifact_identity_conflict" and
            (i["field"].startswith("/files/") or i["field"].startswith("/controls/")) for i in issues if type(i["field"]) is str):
        checks.append(False)
    association = "conflict" if False in checks else "unavailable" if None in checks else "verified"
    if association == "unavailable":
        issues.append(_issue("binding_unavailable", "/native_association"))
    bundle = parse_fba_capture(payloads, expected=original["identity"], prior_sources=priors)
    sheet = populate_flux_balance_sheet(bundle=bundle)
    usable = {"effective_model": any(bundle["models"][p] is not None for p in ("loaded_original", "effective")),
        "effective_problem": any(bundle["problems"][p] is not None for p in ("loaded_original", "effective")),
        "solution": bundle["native_solution"]["native"] is not None,
        "native_log": bundle["native"]["source_log_file"] is not None,
        "manifest": bundle["native_manifest_file"] is not None and bundle["native"]["execution_outcome"] != "unknown"}
    evidence = [r for r in EVIDENCE_ROLES if own_start and capture["driver_started"] is True
        and payloads[r]["state"] == "present" and usable[r]]
    return sheet, association, evidence


def _replay(plan, root):
    try:
        saved = validate_flux_balance_worker_result(_json(read_bytes(root / _RESULT)))
        _require(saved["plan_sha256"] == digest(plan) and saved["mode"] == plan["mode"]
            and saved["selector"] == plan["selector"], "replay_plan_mismatch")
        _require(canonical(_json(read_bytes(root / _OWNER))) == canonical(plan), "replay_plan_mismatch")
        for row in saved["outputs"]:
            declaration = row["declaration"]
            path = root / declaration["relative_path"]
            if declaration["state"] == "absent":
                _require(not path.exists() and not path.is_symlink(), "replay_output_changed", "/outputs/" + row["role"])
            else:
                raw = read_bytes(path)
                _require(_pin(raw) == {k: declaration[k] for k in ("sha256", "size_bytes")},
                    "replay_output_changed", "/outputs/" + row["role"])
                if row["role"] == "projection":
                    projection = validate_fba_projection(_json(raw))
                    _require(projection["selector"] == plan["selector"]["projection"], "replay_projection_mismatch")
        return saved
    except (OSError, ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError("fba_worker_replay_invalid") from error


def execute_flux_balance_worker(plan: dict) -> dict:
    plan = validate_flux_balance_worker_plan(plan)
    root = directory(plan["directory"], create=True)
    if (root / _RESULT).exists() or (root / _RESULT).is_symlink():
        return _replay(plan, root)
    _require(not any(root.iterdir()), "unsealed_directory", "/directory")
    # Exclusive immutable ownership prevents a second invocation from silently
    # redoing an interrupted operation, including interruption before outputs.
    immutable_json(root / _OWNER, plan)
    issues, sheet, calculations, projection = [], None, None, None
    association = "not_applicable" if plan["mode"] == "saved_sheet_recalculation" else "unavailable"
    evidence = []
    try:
        if plan["mode"] == "native_result":
            sheet, association, evidence = _native(plan, issues)
        else:
            raw = _read(plan["sheet"], "/sheet", issues)
            if raw is not None:
                try:
                    sheet = validate_flux_balance_sheet(_json(raw))
                except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
                    issues.append(_issue("schema_invalid", "/sheet", stage="parse", source=plan["sheet"]["file"]))
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, OverflowError, RecursionError) as error:
        issues.append(_record_failure(error, "/sheet", stage="parse"))
    if sheet is not None:
        try:
            calculations = calculate_flux_balance_sheet(sheet, parameters=plan["selector"]["calculation_parameters"])
        except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
            issues.append(_record_failure(error, "/selector/calculation_parameters", stage="parse"))
    if calculations is not None:
        try:
            projection = validate_fba_projection(project_fba_result(sheet, calculations,
                selector=plan["selector"]["projection"]))
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            issues.append(_issue("projection_invalid", "/selector/projection", stage="project"))
    issues = _unique(issues)
    diagnostics = {"version": "flux_balance_result_diagnostics_v1", "plan_sha256": digest(plan), "issues": issues}
    outputs = []
    for (role, name, format_), value in zip(OUTPUTS, (sheet, calculations, projection, diagnostics)):
        pin = {"sha256": None, "size_bytes": None}
        if value is not None:
            immutable_json(root / name, value)
            pin = _pin(read_bytes(root / name))
        outputs.append({"role": role, "declaration": {"relative_path": name, "format": format_,
            "state": "absent" if value is None else "present", **pin}})
    result = validate_flux_balance_worker_result({"version": RESULT_VERSION, "mode": plan["mode"],
        "plan_sha256": digest(plan), "selector": plan["selector"], "outputs": outputs, "failures": issues,
        "native_association": association, "new_attempt_evidence_roles": evidence,
        "requested_projection_valid": projection is not None})
    immutable_json(root / _RESULT, result)
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise ValueError("fba_worker_requires_one_absolute_plan_path")
    path_value(argv[0], absolute=True)
    execute_flux_balance_worker(_json(read_bytes(argv[0])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
