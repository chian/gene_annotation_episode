"""One private selected molecular driver invocation and immutable byte replay.

This adapter neither launches episodes nor publishes scientific facts. Its
identity is a recorded assertion until an existing result owner authenticates
the actual original practical request, handle and terminal resource evidence.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from .execution_contracts import canonical, digest
from . import molecular_sequence_driver as private
from . import molecular_sequence_native as native
from .molecular_sequence_execution_contracts import (
    BUNDLE_FILENAME, BUNDLE_VERSION, MANIFEST_RELATIVE, OWNER_FILENAME,
    OUTPUT_DIRECTORY, REQUEST_RELATIVE, STARTED_FILENAME, MolecularSequenceExecutionError,
    expected_output_roles, failure, molecular_sequence_adapter_argv,
    molecular_sequence_private_driver_argv, output_comparison, output_specifications as _specifications,
    require, validate_molecular_sequence_attempt_bundle,
    validate_molecular_sequence_selected_plan,
)
from .native_flux_balance_storage import (
    directory, file_pin, immutable_bytes, read_bytes, retain_input,
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(raw):
    # Reuse the existing private duplicate-key/finite-JSON decoder.
    return private._json(raw)


def _exact_pin(pin):
    observed = file_pin(pin["path"])
    require(observed == pin, "replay_artifact_conflict", pin["path"])
    return observed


def _realize(pin, *, root, relative, use, max_bytes):
    target = root / relative
    directory(target.parent, create=True)
    if not target.exists():
        retain_input(pin["path"], target, max_bytes=max_bytes)
    observed = file_pin(target)
    return {"selected": deepcopy(pin), "retained_relative_path": relative,
        "observed": observed, "byte_identity_matches_selected": all(
            observed[k] == pin[k] for k in ("sha256", "size_bytes")),
        "content_changed": False, "use": use}


def _software(plan, manifest):
    software = plan["software"]
    require(str(Path(sys.executable).resolve()) == str(Path(software["python"]["path"]).resolve())
        and str(Path(sys.prefix).resolve()) == software["python_home"] and sys.version == software["python_version"],
        "software_identity_conflict")
    require(all(os.environ.get(key) == value for key, value in plan["selected_environment"].items()),
        "software_identity_conflict", "/selected_environment")
    # This technical record has the exact existing software_files_file /
    # FilePin[] manifest contract; no native deployment envelope is invented.
    actual = {**software, "software_files_file": manifest["observed"]}
    index, _ = native._manifest(actual)
    require(software["python"]["path"] in index and index[software["python"]["path"]] == software["python"],
        "software_identity_conflict", "/software/python")
    for pin in index.values():
        require(file_pin(pin["path"]) == pin, "software_identity_conflict", pin["path"])
    roots = [Path(software["python_home"]), *map(Path, software["import_roots"])]
    imported = native._imports(index, roots, Path(__file__).resolve())
    return [{"module": row["module_name"], "file": row["file"]} for row in imported]


def _declaration(plan, request, root, failures):
    path = root / OUTPUT_DIRECTORY / "declaration.json"
    try:
        raw = read_bytes(path)
    except FileNotFoundError as error:
        failures.append(failure("declaration_missing", "declaration_validation", role="declaration", error=error))
        return None
    except (OSError, ValueError) as error:
        failures.append(failure("declaration_malformed", "declaration_validation", role="declaration", error=error))
        return None
    try:
        value = _json(raw)
        wanted = plan["selection"]["driver_request"]
        v2 = wanted["version"] == private.REQUEST_VERSION_V2
        fields = {"version", "mode", "operation", "request_file", "request_file_pin_verified", "attempt_identity",
            "native_call_state", "native_failure", "driver_failure", "files", "qualification"}
        if v2:
            fields |= {"native_outcome", "observer_state", "observer_failures", "verification_failures", "native_output_completion"}
        require(type(value) is dict and set(value) == fields and value["version"] == (
            private.DECLARATION_VERSION_V2 if v2 else private.DECLARATION_VERSION), "declaration_malformed")
        require(value["request_file"] == request["observed"] and value["request_file_pin_verified"] is True
            and value["attempt_identity"] == wanted["attempt_identity"] and value["mode"] == wanted["mode"]
            and value["operation"] == wanted["selection"]["operation"], "declaration_input_conflict")
        roles = {"capture", "sheet", "components"}
        if "native_results" in expected_output_roles(plan):
            roles |= {"native_results", "native_plot"}
        require(type(value["files"]) is dict and set(value["files"]) == roles, "declaration_malformed")
        for role, row in value["files"].items():
            require(type(row) is dict and set(row) == {"relative_path", "format", "state", "sha256", "size_bytes"}
                and row["state"] in ("present", "absent"), "declaration_malformed")
            expected_relative, expected_format = _specifications(plan)[role]
            require(str(Path(OUTPUT_DIRECTORY) / row["relative_path"]) == expected_relative
                and row["format"] == expected_format, "declaration_input_conflict")
            if row["state"] == "present":
                private._file_pin({"path": str(root / expected_relative), "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
            else:
                require(row["sha256"] is None and row["size_bytes"] is None, "declaration_malformed")
        return value
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError) as error:
        code = getattr(error, "code", "declaration_malformed")
        if code not in ("declaration_malformed", "declaration_input_conflict"):
            code = "declaration_malformed"
        failures.append(failure(code, "declaration_validation", role="declaration", error=error))
        return None


def _observe_outputs(plan, request, failures):
    root = Path(plan["attempt_directory"])
    declaration = _declaration(plan, request, root, failures) if request is not None else None
    specifications = _specifications(plan)
    rows = []
    for role in expected_output_roles(plan):
        relative, format_ = specifications[role]
        path = root / relative
        row = {"role": role, "relative_path": relative, "format": format_, "observed_state": "absent",
            "observed": None, "declared": None, "comparison": "not_declared", "failure": None}
        try:
            observed = file_pin(path)
            row.update(observed_state="present", observed=observed)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            row.update(observed_state="unavailable", failure=failure("output_not_regular", "output_observation", role=role, error=error))
        declared = None if declaration is None else declaration["files"].get(role)
        if declared is not None:
            row["declared"] = deepcopy(declared)
            row["comparison"] = output_comparison(row["observed_state"], row["observed"], declared)
            if row["comparison"] != "matches" and row["failure"] is None:
                row["failure"] = failure("output_identity_conflict" if row["comparison"] == "mismatch" else
                    "output_unavailable", "output_observation", role=role)
        if row["failure"] is not None:
            failures.append(row["failure"])
        rows.append(row)
    return rows


def read_molecular_sequence_selected_replay(plan, *, expected_payload_sha256):
    """Read original retained controls/bytes; inspect no historical software."""
    plan = validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=expected_payload_sha256)
    root = Path(plan["attempt_directory"])
    value = validate_molecular_sequence_attempt_bundle(_json(read_bytes(root / BUNDLE_FILENAME)), plan=plan)
    owner = value["retained_inputs"]["plan_file"]
    _exact_pin(owner)
    require(canonical(_json(read_bytes(owner["path"]))) == canonical(plan), "original_owner_conflict")
    for key in ("request", "software_manifest"):
        realization = value["retained_inputs"][key]
        if realization is not None:
            _exact_pin(realization["observed"])
    for row in value["files"]:
        if row["observed"] is not None:
            _exact_pin(row["observed"])
        elif row["observed_state"] == "absent":
            path = root / row["relative_path"]
            require(not path.exists() and not path.is_symlink(), "replay_artifact_conflict", row["relative_path"])
    return deepcopy(value)


def execute_molecular_sequence_selected_plan(plan, *, expected_payload_sha256, plan_bytes=None):
    """Attempt the unchanged private CLI once; retain its independent outputs.

    Software verification means selected-file pin stability and actual outer
    adapter imports. The separate private CLI's full import roster is not
    observed here. Its native helper retains its own distinct observations.
    """
    plan = validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=expected_payload_sha256)
    raw = (canonical(plan) + "\n").encode() if plan_bytes is None else plan_bytes
    require(type(raw) is bytes and canonical(_json(raw)) == canonical(plan), "invalid_plan")
    root = directory(plan["attempt_directory"], create=True)
    require(Path.cwd().resolve() == root.parent.resolve(), "invalid_plan", "/cwd")
    if (root / BUNDLE_FILENAME).exists():
        return read_molecular_sequence_selected_replay(plan, expected_payload_sha256=expected_payload_sha256)
    owner = root / OWNER_FILENAME
    if owner.exists():
        require(read_bytes(owner) == raw, "original_owner_conflict")
        raise MolecularSequenceExecutionError("original_invocation_uncertain")
    require(not any(root.iterdir()), "original_owner_conflict")
    try:
        immutable_bytes(owner, raw)
    except FileExistsError as error:
        # Another adapter acquired the same exclusive owner after our check.
        # It alone may retain controls, invoke, observe and seal this attempt.
        require(read_bytes(owner) == raw, "original_owner_conflict")
        raise MolecularSequenceExecutionError("original_invocation_uncertain") from error
    require(not (root / STARTED_FILENAME).exists(), "original_invocation_uncertain")
    value = {"version": BUNDLE_VERSION, "plan_sha256": digest(plan), "identity": deepcopy(plan["identity"]),
        "selected_payload_sha256": expected_payload_sha256,
        "retained_inputs": {"plan_file": file_pin(owner), "request": None, "software_manifest": None},
        "selected_request_file": deepcopy(plan["selection"]["request_file"]), "observed_request_file": None,
        "private_asserted_attempt_identity": deepcopy(plan["selection"]["driver_request"]["attempt_identity"]),
        "adapter_argv": molecular_sequence_adapter_argv(plan), "private_driver_argv": None,
        "cwd": str(root.parent), "selected_environment": deepcopy(plan["selected_environment"]),
        "realized_environment": deepcopy(plan["selected_environment"]),
        "software_verification": {"before": "not_checked", "after": "not_checked", "adapter_imported_files": [],
            "inner_complete_import_closure_observed": False, "failures": []},
        "invocation": {"launch_attempt_count": 0, "invocation_count": 0, "pid": None, "returncode": None,
            "started_at": None, "finished_at": None, "process_exit_observed": False},
        "files": [], "failures": [], "sealed": True}
    phase = "request"
    try:
        request = _realize(plan["selection"]["request_file"], root=root, relative=REQUEST_RELATIVE,
            use="private_cli_request", max_bytes=plan["policy"]["scratch_bytes"])
        value["retained_inputs"]["request"] = request
        value["observed_request_file"] = {**request["observed"], "path": request["selected"]["path"]}
        require(request["byte_identity_matches_selected"], "request_identity_conflict")
        require(canonical(_json(read_bytes(request["observed"]["path"]))) == canonical(plan["selection"]["driver_request"]),
            "request_document_conflict")
        phase = "software_before"
        manifest = _realize(plan["software"]["software_files_file"], root=root, relative=MANIFEST_RELATIVE,
            use="software_manifest_evidence", max_bytes=plan["policy"]["scratch_bytes"])
        value["retained_inputs"]["software_manifest"] = manifest
        require(manifest["byte_identity_matches_selected"], "software_identity_conflict")
        value["software_verification"]["adapter_imported_files"] = _software(plan, manifest)
        value["software_verification"]["before"] = "verified"
        phase = "launch"
        command = molecular_sequence_private_driver_argv(plan, retained_request_file=request["observed"])
        require(not (root / OUTPUT_DIRECTORY).exists() and not (root / OUTPUT_DIRECTORY).is_symlink(), "original_owner_conflict")
        value["private_driver_argv"] = command
        value["invocation"].update(launch_attempt_count=1, started_at=_now())
        try:
            immutable_bytes(root / STARTED_FILENAME, (canonical({"version": "molecular_sequence_started_v1",
                "plan_sha256": digest(plan), "selected_payload_sha256": expected_payload_sha256,
                "private_driver_argv": command, "started_at": value["invocation"]["started_at"]}) + "\n").encode())
        except FileExistsError as error:
            raise MolecularSequenceExecutionError("original_invocation_uncertain") from error
        with (root / "private.stdout").open("xb") as stdout, (root / "private.stderr").open("xb") as stderr:
            process = subprocess.Popen(command, cwd=root.parent, env=plan["selected_environment"],
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            value["invocation"].update(invocation_count=1, pid=process.pid)
            phase = "process"
            try:
                returncode = process.wait()
            except BaseException as error:
                # A live/uncertain writer cannot be sealed or started again.
                raise MolecularSequenceExecutionError("original_invocation_uncertain") from error
            value["invocation"].update(returncode=returncode, finished_at=_now(), process_exit_observed=True)
            stdout.flush(); stderr.flush()
            os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
        if returncode:
            value["failures"].append(failure("inner_nonzero_exit", "process"))
        phase = "software_after"
        value["software_verification"]["adapter_imported_files"] = _software(plan, manifest)
        value["software_verification"]["after"] = "verified"
    except MolecularSequenceExecutionError as error:
        if error.code == "original_invocation_uncertain":
            raise
        code = error.code
        if code not in ("request_identity_conflict", "request_document_conflict", "software_identity_conflict", "original_owner_conflict"):
            code = "adapter_io_failure"
        item = failure(code, phase, error=error)
        value["failures"].append(item)
        if phase.startswith("software_"):
            value["software_verification"]["before" if phase == "software_before" else "after"] = "conflict"
            value["software_verification"]["failures"].append(item)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        code = ("request_unavailable" if phase == "request" else "inner_launch_failed" if phase == "launch" else
            "software_identity_conflict" if phase.startswith("software_") else "adapter_io_failure")
        item = failure(code, phase, error=error)
        value["failures"].append(item)
        if phase.startswith("software_"):
            value["software_verification"]["before" if phase == "software_before" else "after"] = "conflict"
            value["software_verification"]["failures"].append(item)
    value["files"] = _observe_outputs(plan, value["retained_inputs"]["request"], value["failures"])
    value = validate_molecular_sequence_attempt_bundle(value, plan=plan)
    immutable_bytes(root / BUNDLE_FILENAME, (canonical(value) + "\n").encode())
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--selected-payload-sha256", required=True)
    arguments = parser.parse_args(argv)
    try:
        path = Path(arguments.plan)
        raw = read_bytes(str(path.absolute()))
        plan = _json(raw)
        plan = validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=arguments.selected_payload_sha256)
        require(path.absolute() == Path(plan["identity"]["execution_id"]).parent / "molecular-sequence-plan.json", "invalid_plan", "/plan")
        value = execute_molecular_sequence_selected_plan(plan,
            expected_payload_sha256=arguments.selected_payload_sha256, plan_bytes=raw)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        sys.stderr.write(json.dumps({"version": "molecular_sequence_adapter_error_v1", "code": getattr(error, "code", "invalid_plan"),
            "message": str(error)}, allow_nan=False) + "\n")
        return 1
    sys.stdout.write(json.dumps(value, allow_nan=False) + "\n")
    return int(bool(value["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
