"""Finite retained-fluorescence calculation inside an already selected worker.

Only this layer reads full scientific artifacts. It consumes attributable saved
parse batches or a supplied common sheet, invokes the shared calculator once,
and copies requested cells. It never parses native events or launches work.
"""
from copy import deepcopy
import errno
import os
from pathlib import Path
import sys

from . import fluorescence_event_contracts as core
from .fluorescence_context_views import project_fluorescence_context
from .fluorescence_event_calculations import calculate_fluorescence_sheet
from .fluorescence_event_sheet import populate_fluorescence_sheet, validate_fluorescence_sheet
from .fluorescence_execution_common import canonical, digest, identity, require, same, unique
from .fluorescence_result_contracts import (OUTPUTS, RESULT_VERSION, failure,
    validate_fluorescence_projection, validate_fluorescence_worker_plan, validate_fluorescence_worker_result)
from .fluorescence_result_views import project_fluorescence_result
from .fluorescence_prepared_results import admit_preparations, admit_reports
from .native_fluorescence_contracts import (unavailable_fluorescence_input,
    validate_fluorescence_manifest, validate_fluorescence_parsed_batch)
from .native_fluorescence_storage import directory, file_pin, regular, decode_json, immutable_bytes, immutable_json, read_json

_UNAVAILABLE_ERRNOS = {errno.ENOENT, errno.EACCES, errno.EPERM, errno.ENOTDIR, errno.ELOOP}
_STORAGE_ERRORS = {"fluorescence_non_directory_or_symlink", "fluorescence_non_regular_file",
                   "fluorescence_file_changed_during_read"}


def _operand(retained, *, read=False):
    """Return exact bytes or a verified pin, and a restricted input failure.

    Resource and process failures propagate. An unreadable/changed operand is
    information about that operand, never a numerical zero.
    """
    if retained is None:
        return None, "capture_file_unavailable"
    expected = retained["file"]
    try:
        if read:
            with regular(retained["path"]) as stream:
                before = os.fstat(stream.fileno())
                raw = stream.read(expected["size_bytes"] + 1)
                after = os.fstat(stream.fileno())
            stable = (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino) == (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino)
            if not stable or not same(identity(raw, format=expected["format"]), expected):
                return None, "capture_file_digest_mismatch"
            return raw, None
        pin = file_pin(retained["path"])
        if any(pin[key] != expected[key] for key in ("sha256", "size_bytes")):
            return None, "capture_file_digest_mismatch"
        return pin, None
    except OSError as error:
        if error.errno not in _UNAVAILABLE_ERRNOS:
            raise
        return None, "capture_file_unavailable"
    except ValueError as error:
        if str(error) not in _STORAGE_ERRORS:
            raise
        return None, "capture_file_digest_mismatch" if str(error) == "fluorescence_file_changed_during_read" else "capture_file_unavailable"


def _native(plan):
    original, capture = plan["original_plan"], plan["capture"]
    job = original["requested_job"]["native_fluorescence"]
    failures = deepcopy(capture["failures"])
    captured = {row["role"]: row for row in capture["files"]}
    verified, raw_values, operand_problems = {}, {}, {}
    for role, row in captured.items():
        read = role == "manifest" or role.startswith(("event_batch:", "support_input:",
            "report_input:", "preparation_parameters:", "prepared_data:", "prepared_batch:", "report_batch:"))
        value, problem = _operand(row["retained"], read=read)
        verified[role] = problem is None
        if problem is not None:
            operand_problems[role] = problem
            index = int(role.split(":")[1]) if ":" in role else None
            failures.append(failure(problem, "capture", input_index=index, role=role))
        elif read:
            raw_values[role] = value
    # A retained original must also be the selected original, independently of
    # a self-consistent batch envelope or manifest.
    for prefix, items in (("event_input", job["inputs"]), ("support_input", job["support_inputs"]),
                          ("report_input", job.get("report_inputs", []))):
        for index, item in enumerate(items):
            role = f"{prefix}:{index}"
            expected = item["source"]["file"] if prefix == "event_input" else item["file"]
            row = captured[role]
            if verified[role] and not same(row["retained"]["file"], expected):
                verified[role] = False
                raw_values.pop(role, None)
                operand_problems[role] = "input_identity_mismatch"
                failures.append(failure("input_identity_mismatch", "authority", input_index=index, role=role))
    manifest = None
    manifest_whole = False
    if "manifest" not in raw_values:
        failures.append(failure("manifest_missing_or_malformed", "capture", role="manifest"))
    else:
        try:
            document = decode_json(raw_values["manifest"])
        except (ValueError, UnicodeError):
            failures.append(failure("manifest_missing_or_malformed", "capture", role="manifest"))
        else:
            try:
                manifest = validate_fluorescence_manifest(document, original_plan=original)
            except ValueError:
                failures.append(failure("native_manifest_conflict", "authority", role="manifest"))
    if manifest is not None:
        manifest_whole = not manifest["failures"]
        failures.extend(manifest["failures"])
        for row in manifest["outputs"]:
            role, declaration = row["role"], row["declaration"]
            retained = captured[role]["retained"]
            equal = retained is not None and verified[role] and all(
                retained["file"][key] == declaration[key] for key in ("sha256", "size_bytes", "format"))
            if declaration["state"] != "present" or not equal:
                manifest_whole = False
            if (declaration["state"] == "present" and not equal or
                    declaration["state"] == "absent" and retained is not None):
                index = int(role.split(":")[1]) if ":" in role else None
                failures.append(failure("native_manifest_conflict", "authority", input_index=index, role=role))
    started = capture["driver_started"] is True
    if not started:
        failures.append(failure("original_execution_mismatch", "authority"))
    parsed, admitted, original_batch_files = [], [], []
    for index, binding in enumerate(job["inputs"]):
        role = f"event_batch:{index}"
        batch = None
        rejected = None
        if role not in raw_values:
            rejected = "parsed_batch_unavailable"
        else:
            try:
                batch = validate_fluorescence_parsed_batch(decode_json(raw_values[role]),
                    original_plan=original, input_index=index)
            except (ValueError, UnicodeError):
                rejected = "parsed_batch_invalid"
        if rejected is not None:
            failures.append(failure(rejected, "capture", input_index=index, role=role))
        accepted = batch is not None and rejected is None and started and verified[f"event_input:{index}"]
        if accepted:
            value = batch["parse"]
            admitted.append(value)
            original_batch_files.append(captured[role]["retained"]["file"])
            if manifest is not None and (manifest["inputs"][index]["extent"] != value["source"]["extent"]
                    or not same(manifest["inputs"][index]["batch_file"], captured[role]["retained"]["file"])):
                manifest_whole = False
                failures.append(failure("native_manifest_conflict", "authority", input_index=index, role=role))
        else:
            original_batch_files.append(None)
            # Keep every originally declared identity and definition. A missing
            # batch becomes an unavailable parser result, never an empty source.
            mismatch = rejected == "parsed_batch_invalid" or any(row["role"] in (f"event_input:{index}", role) and
                row["code"] in ("input_identity_mismatch", "capture_file_digest_mismatch") for row in failures)
            value = unavailable_fluorescence_input(binding,
                code="retained_artifact_mismatch" if mismatch else "source_unavailable")
        parsed.append(value)
    acquired = any(row["source"]["extent"] in ("complete", "partial") for row in admitted)
    prepared, prepared_files, statuses, preparation_failures = admit_preparations(
        original_plan=original, captured=captured, verified=verified, raw_values=raw_values,
        originals=parsed, original_batch_files=original_batch_files, started=started,
        operand_problems=operand_problems)
    sources, reports, report_issues, report_files, report_extents, report_failures = admit_reports(
        original_plan=original, captured=captured, verified=verified, raw_values=raw_values, started=started,
        operand_problems=operand_problems)
    failures.extend(preparation_failures)
    failures.extend(report_failures)
    if manifest is not None:
        for index, file in enumerate(prepared_files):
            if file is None:
                continue
            request = job["preparations"][index]
            parents = original_batch_files if request["input"]["kind"] == "event_input" else prepared_files
            expected = dict(preparation_index=index, parent_batch_file=parents[request["input"]["index"]],
                parameters_file=captured[f"preparation_parameters:{index}"]["retained"]["file"],
                prepared_file=prepared[index]["source"]["file"], batch_file=file, status=statuses[index])
            if not same(manifest["preparations"][index], expected):
                manifest_whole = False
                failures.append(failure("native_manifest_conflict", "authority", input_index=index,
                    role=f"prepared_batch:{index}"))
        for index, file in enumerate(report_files):
            if file is not None and not same(manifest["reports"][index], dict(report_index=index,
                    source_file=job["report_inputs"][index]["file"], batch_file=file, extent=report_extents[index])):
                manifest_whole = False
                failures.append(failure("native_manifest_conflict", "authority", input_index=index,
                    role=f"report_batch:{index}"))
    whole = started and manifest_whole and all(verified.values()) and not failures
    outcome = ("complete" if whole and len(admitted) == len(parsed)
        and all(row["source"]["extent"] == "complete" for row in parsed)
        and all(status == "complete" for status in statuses) and all(extent == "complete" for extent in report_extents)
        else "partial" if acquired else "unavailable")
    definitions = job["definitions"]
    sheet = populate_fluorescence_sheet([*parsed, *prepared], populations=definitions["populations"], gates=definitions["gates"],
        control_pairs=definitions["control_pairs"], native_reports=definitions["native_reports"])
    sheet["input_sources"].extend(sources)
    sheet["native_reports"].extend(reports)
    sheet["issues"] = unique([*sheet["issues"], *report_issues])
    validate_fluorescence_sheet(sheet)
    # A declared comparison basis remains recorded, but its unverified original
    # bytes cannot authorize a numerical control difference. The shared core
    # owns the dependency fields and the resulting calculation qualification.
    unverified_support = {core.canonical(item["file"]): (
        "retained_artifact_mismatch" if operand_problems[f"support_input:{index}"] in
        ("capture_file_digest_mismatch", "input_identity_mismatch") else "source_unavailable")
        for index, item in enumerate(job["support_inputs"]) if not verified[f"support_input:{index}"]}
    for pair in sheet["control_pairs"]:
        for dependency in core.control_comparison_files(sheet, control_key=pair["key"]):
            code = unverified_support.get(core.canonical(dependency["file"]))
            if code is not None:
                sheet["issues"].append(core.issue(code, "input", control_key=pair["key"]))
        sheet["issues"] = unique(sheet["issues"])
    return sheet, bool(started and admitted), acquired, outcome, unique(failures)


def execute_fluorescence_worker(plan):
    """Perform this selected calculation; subprocess ownership stays outside."""
    plan = validate_fluorescence_worker_plan(plan)
    root = directory(plan["directory"])
    root.mkdir(parents=True, exist_ok=True)
    # A persisted result is the completed original finite operation. Validate
    # and return it without recalculating or reacquiring an operand.
    if (root / "worker-result.json").exists():
        saved = validate_fluorescence_worker_result(read_json(root / "worker-result.json"))
        require(saved["plan_sha256"] == digest(plan) and same(saved["selector"], plan["selector"]),
                "worker_execution_mismatch")
        return saved
    values = {name: None for name, _, _ in OUTPUTS}
    failures, bound, acquired, complete = [], False, False, False
    outcome = "unavailable" if plan["mode"] == "native_result" else "not_applicable"
    parameters = (plan["original_plan"]["requested_job"]["native_fluorescence"]["parameters"]
        if plan["mode"] == "native_result" else plan["selector"]["parameters"])
    if plan["mode"] == "native_result":
        input_identities = [row["source"]["file"] for row in plan["original_plan"]["requested_job"]["native_fluorescence"]["inputs"]]
        try:
            values["sheet"], bound, acquired, outcome, failures = _native(plan)
        except core.FluorescenceContractError:
            failures.append(failure("worker_output_malformed", "worker", role="sheet"))
    else:
        input_identities = [plan["sheet"]["file"]]
        raw, problem = _operand(plan["sheet"], read=True)
        if problem is not None:
            failures.append(failure(problem, "input", role="sheet"))
        else:
            try:
                values["sheet"] = deepcopy(validate_fluorescence_sheet(decode_json(raw)))
            except (ValueError, UnicodeError):
                failures.append(failure("saved_sheet_incompatible", "worker", role="sheet"))
    if values["sheet"] is not None:
        try:
            values["calculations"] = calculate_fluorescence_sheet(values["sheet"], parameters=parameters)
        except core.FluorescenceContractError:
            failures.append(failure("saved_sheet_incompatible" if plan["mode"] == "saved_sheet_recalculation"
                else "worker_output_malformed", "worker", role="calculations"))
    if values["calculations"] is not None:
        try:
            values["projection"] = validate_fluorescence_projection(project_fluorescence_result(
                values["sheet"], values["calculations"], selection=plan["selector"]["selection"]))
            if plan["selector"]["context_fields"]:
                values["context"] = project_fluorescence_context(values["sheet"], values["calculations"],
                    selection=plan["selector"]["selection"], context_fields=plan["selector"]["context_fields"])
        except ValueError:
            failures.append(failure("projection_contract_invalid", "projection", role=(
                "context" if values["projection"] is not None else "projection")))
    failures = unique(failures)
    complete = not failures and values["projection"] is not None and (
        not plan["selector"]["context_fields"] or values["context"] is not None)
    values["diagnostics"] = failures
    outputs = []
    for role, name, format_ in OUTPUTS:
        value = values[role]
        file = None
        if value is not None:
            raw = (canonical(value) if role == "diagnostics" else core.canonical(value)) + b"\n"
            target = root / name
            if target.exists():
                with regular(target) as stream:
                    require(stream.read() == raw, "worker_execution_mismatch")
            else:
                immutable_bytes(target, raw)
            file = identity(raw, format=format_)
        outputs.append({"role": role, "declaration": {"relative_path": name, "format": format_,
            "state": "present" if file is not None else "absent", "sha256": None if file is None else file["sha256"],
            "size_bytes": None if file is None else file["size_bytes"]}})
    result = validate_fluorescence_worker_result(dict(version=RESULT_VERSION, mode=plan["mode"], plan_sha256=digest(plan),
        selector=plan["selector"], outputs=outputs, failures=failures, input_identities=input_identities,
        native_binding=bound, native_outcome=outcome, original_events_acquired=acquired, analysis_complete=bool(complete)))
    immutable_json(root / "worker-result.json", result)
    return result


def main():
    require(len(sys.argv) == 2, "one_fluorescence_worker_plan_required")
    execute_fluorescence_worker(read_json(Path(sys.argv[1]).absolute()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
