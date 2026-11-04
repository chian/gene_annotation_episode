"""Selected HOMER native entry and a separate retained-data calculation entry.

The native entry stages the selected closure inside the original bounded job,
runs one wrapper, and seals its completion before inspecting native outputs.
The two-file entry uses only the existing shared HOMER readers/calculator.
Neither entry imports a Store or creates a Source, receipt, episode or grant.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


WORKER_REQUEST_VERSION = "homer_motif_worker_request_v1"
WORKER_RESULT_VERSION = "homer_motif_worker_result_v1"
_PURE_FIELDS = ("version", "mode", "files", "invocation", "execution", "saved", "selection", "projection_source_ref")


def _require(condition, code):
    if not condition:
        raise ValueError("homer_worker_" + code)


def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _copy_selected(row, target, *, mode):
    from .native_flux_balance_storage import file_pin, retain_input
    observed = retain_input(row["path"], target, max_bytes=row["size_bytes"])
    _require(observed == {key: row[key] for key in ("sha256", "size_bytes")}, "selected_copy_identity_conflict")
    os.chmod(target, mode)
    return file_pin(target)


def _stage_native(plan):
    """Copy only the selected bytes; caches and all mutable paths stay owned."""
    from . import native_homer_execution as e
    from .native_flux_balance_storage import directory, file_pin, immutable_bytes, read_bytes
    root = Path(plan["attempt_directory"])
    deployment = plan["request"]["deployment"]
    for name in ("inputs", "runtime_control", "native", "work", "preparsed", "tmp", "cache", "home", "perl_trace"):
        directory(root / name, create=True)
    copies, patches, inputs = [], [], []
    for row in deployment["files"]:
        original = dict(path=str(Path(deployment["root"]) / row["relative_path"]),
            sha256=row["sha256"], size_bytes=row["size_bytes"])
        target = root / row["relative_path"]
        directory(target.parent, create=True)
        copied = _copy_selected(original, target, mode=row["mode"])
        copies.append(dict(relative_path=row["relative_path"], original=original, copied=copied, mode=row["mode"]))
    # These are the only per-attempt source changes, recorded byte-for-byte.
    for name in e.PATCH_NAMES:
        target = root / "deployment/bin" / name
        raw = read_bytes(target)
        lines = raw.splitlines(keepends=True)
        original_root = Path(deployment["root"])
        _require(len(lines) >= 4 and lines[2] == ('use lib "' + str(original_root / "deployment/bin") + '";\n').encode()
            and lines[3] == ('my $homeDir = "' + str(original_root / "deployment") + '/";\n').encode(),
            "selected_perl_header_conflict")
        lines[2] = ('use lib "' + str(root / "deployment/bin") + '";\n').encode()
        lines[3] = ('my $homeDir = "' + str(root / "deployment") + '/";\n').encode()
        # Mutation is confined to this new owned copy, never the selected asset.
        os.chmod(target, 0o600)
        with target.open("wb") as output:
            output.write(b"".join(lines)); output.flush(); os.fsync(output.fileno())
        selected_mode = next(row["mode"] for row in deployment["files"]
            if row["relative_path"] == "deployment/bin/" + name)
        os.chmod(target, selected_mode)
        patches.append(dict(relative_path="deployment/bin/" + name, before=e._raw_pin(target, raw),
            after=file_pin(target), changed_lines_1based=[3, 4]))
    for row, name in zip(plan["request"]["frozen_inputs"]["inputs"], ("target.bed", "reference.fa", "background.bed")):
        source = dict(path=row["path"], sha256=row["file"]["sha256"], size_bytes=row["file"]["size_bytes"])
        inputs.append(dict(role=row["role"], selected_file=row["file"], original=source,
            staged=_copy_selected(source, root / "inputs" / name, mode=0o444)))
    module_paths = [str(root / "deployment/bin"), *(str(root / "selected_runtime/perl/modules" / label)
        for label in ("base", "arch", "pure"))]
    # @INC is replaced rather than extending the interpreter's compiled home.
    module = ("package HomerSelectedRuntime;\nBEGIN { @INC = (" + ",".join("'" + p + "'" for p in module_paths)
        + "); }\n1;\n").encode("ascii")
    module_path = root / "runtime_control/HomerSelectedRuntime.pm"
    immutable_bytes(module_path, module)
    realization = dict(version="homer_native_realization_v1", identity=plan["identity"],
        selected_payload_sha256=plan["selected_payload_sha256"], copies=copies, header_rebases=patches,
        inputs=inputs, runtime_module=file_pin(module_path), corrections=deployment["corrections"],
        cache_directory=str(root / "preparsed"), runtime_and_input_bytes=sum(row["size_bytes"] for row in deployment["files"])
            + sum(row["file"]["size_bytes"] for row in plan["request"]["frozen_inputs"]["inputs"]))
    immutable_bytes(root / e.REALIZATION_FILENAME, _json_bytes(realization))
    # Account for actual private controls and every copied file before release of
    # the one wrapper. The same lifecycle enforces the full evolving scratch cap.
    from .local_jobs import allocated_bytes
    _require(allocated_bytes(Path(plan["operation_directory"])) <= plan["policy"]["scratch_bytes"],
        "staged_allocation_exceeds_scratch")
    return file_pin(root / e.REALIZATION_FILENAME)


def _observed_output(root, specification):
    from . import native_homer_execution as e
    from .native_flux_balance_storage import confined_file, file_pin
    row = dict(specification, observed_state="absent", sha256=None, size_bytes=None, failure=None)
    try:
        path = confined_file(root, specification["native_relative_path"])
        pin = file_pin(path)
        row.update(observed_state="present", sha256=pin["sha256"], size_bytes=pin["size_bytes"])
    except FileNotFoundError:
        # A missing parent is genuine absent output too; no path is fabricated.
        pass
    except (OSError, ValueError) as error:
        row.update(observed_state="unavailable", failure=e.failure_record("homer_output_unavailable", "native_inventory", error))
    return row


def _inventory_native(plan, completion, completion_pin):
    """Seal each surviving output independently, including empty native files."""
    from . import native_homer_execution as e
    from .native_flux_balance_storage import file_pin
    root = Path(plan["attempt_directory"])
    files = [_observed_output(root, row) for row in e.homer_output_specifications(plan)]
    failures = []
    for folder, expression, role in (("native/knownResults", r"known([1-9][0-9]*)\.motif", "known_pwm"),
            ("native/homerResults", r"motif([1-9][0-9]*)\.motif", "denovo_nonredundant_pwm")):
        known = root / folder
        if not known.exists(): continue
        try:
            _require(stat.S_ISDIR(known.lstat().st_mode), "known_output_directory_invalid")
            paths = [path for path in known.iterdir() if re.fullmatch(expression, path.name)]
            paths.sort(key=lambda p: int(re.fullmatch(expression, p.name)[1]))
            for path in paths:
                files.append(_observed_output(root, dict(role=role,
                    native_relative_path=folder + "/" + path.name, format="homer_native_pwm")))
        except (OSError, ValueError) as error:
            failures.append(e.failure_record("homer_known_pwm_inventory_unavailable", "native_inventory", error))
    selected = {row["native_relative_path"] for row in files}
    other = []
    # Native byproducts are retained without implying public File admission.
    def walk(directory):
        try:
            for entry in sorted(directory.iterdir(), key=lambda p: p.name):
                mode = entry.lstat().st_mode
                if stat.S_ISDIR(mode): walk(entry)
                elif stat.S_ISREG(mode):
                    relative = str(entry.relative_to(root))
                    if relative not in selected:
                        pin = file_pin(entry)
                        other.append(dict(native_relative_path=relative, sha256=pin["sha256"], size_bytes=pin["size_bytes"]))
                else:
                    failures.append(e.failure_record("homer_non_regular_output", "native_inventory",
                        ValueError(str(entry.relative_to(root)))))
        except (OSError, ValueError) as error:
            failures.append(e.failure_record("homer_output_inventory_incomplete", "native_inventory", error))
    for name in ("native", "work", "preparsed"):
        path = root / name
        if path.exists():
            if stat.S_ISDIR(path.lstat().st_mode): walk(path)
            else: failures.append(e.failure_record("homer_output_directory_invalid", "native_inventory", ValueError(name)))
    wrapper = completion["wrapper"]
    wrapper_outcome = "succeeded" if wrapper["outcome"] == "returned" and wrapper["returncode"] == 0 else \
        "failed" if wrapper["outcome"] == "returned" else "not_run" if wrapper["outcome"] == "not_started" else "unknown"
    # No file-size, fixture expectation or rc0 assertion proves successful
    # scientific branches. Preserve unknown until an affirmative native branch
    # protocol is selected. Literal failures are independently retained in logs.
    execution = dict(wrapper_returncode=wrapper["returncode"], wrapper_outcome=wrapper_outcome,
        known_outcome="not_run" if wrapper["outcome"] == "not_started" else "unknown",
        denovo_outcome="not_run" if wrapper["outcome"] == "not_started" else "unknown")
    value = dict(version=e.MANIFEST_VERSION, identity=plan["identity"],
        selected_payload_sha256=plan["selected_payload_sha256"], completion_file=completion_pin,
        files=files, other_files=other, failures=failures, execution=execution)
    return e.validate_homer_output_manifest(value, plan=plan, completion=completion)


def run_native_homer(plan_path, expected_payload_sha256):
    """Execute one immutable selected wrapper; never retry or replace it."""
    from . import native_homer_execution as e
    from .native_flux_balance_storage import confined_file, decode_json, directory, file_pin, immutable_bytes, read_bytes
    plan_path = Path(plan_path)
    _require(plan_path.name == e.PLAN_FILENAME and plan_path.parent == Path.cwd(), "selected_plan_path_conflict")
    plan = e.validate_homer_plan(decode_json(read_bytes(plan_path)))
    _require(plan["selected_payload_sha256"] == expected_payload_sha256 and plan["operation_directory"] == str(Path.cwd()),
        "selected_plan_payload_conflict")
    _require(Path(sys.executable).absolute() == Path(plan["software"]["python"]["path"])
        and os.environ.get("PYTHONHOME") == plan["software"]["python_home"]
        and os.environ.get("PYTHONPATH") == ":".join(plan["software"]["import_roots"])
        and sys.dont_write_bytecode and sys.flags.no_site and sys.flags.no_user_site,
        "selected_python_startup_conflict")
    _require(file_pin(plan["request_file"]["path"]) == plan["request_file"]
        and read_bytes(plan["request_file"]["path"]) == _json_bytes(plan["request"]), "selected_request_identity_conflict")
    root = Path(plan["attempt_directory"])
    # A second entry never overwrites evidence or invokes a second wrapper.
    _require(not root.exists() and not root.is_symlink(), "original_attempt_already_exists")
    directory(root, create=True)
    invocation = e.homer_native_invocation(plan)
    wrapper = dict(**invocation, started_at=None, finished_at=None, returncode=None, outcome="not_started")
    realization_pin, started_pin, completion, completion_pin = None, None, None, None
    failure, original_error = None, None
    try:
        e.verify_homer_start_inputs(plan, verify_loaded=True)
        realization_pin = _stage_native(plan)
        wrapper["started_at"] = _now()
        started = dict(version="homer_native_wrapper_started_v1", identity=plan["identity"],
            selected_payload_sha256=expected_payload_sha256, request_file=plan["request_file"],
            realization_file=realization_pin, **invocation, started_at=wrapper["started_at"])
        immutable_bytes(root / e.STARTED_FILENAME, _json_bytes(started))
        started_pin = file_pin(root / e.STARTED_FILENAME)
        # The start marker precedes the sole subprocess site. An interruption
        # between these events is unconfirmed, never a proven zero native calls.
        wrapper["outcome"] = "unconfirmed"
        with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
            completed = subprocess.run(invocation["argv"], cwd=invocation["cwd"], env=invocation["environment"],
                stdout=stdout, stderr=stderr, check=False)
            wrapper.update(returncode=completed.returncode, finished_at=_now(), outcome="returned")
            stdout.flush(); stderr.flush(); os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
    except BaseException as error:
        original_error = error
        failure = e.failure_record("homer_native_driver_failed", "native_driver", error)
        wrapper["finished_at"] = _now()
    finally:
        # Completion is independent of semantic parsing and output inventory.
        # Its own publication failure must not trigger a second wrapper call.
        completion = dict(version=e.COMPLETION_VERSION, identity=plan["identity"], request_file=plan["request_file"],
            selected_payload_sha256=expected_payload_sha256, wrapper_started_file=started_pin,
            realization_file=realization_pin, wrapper=wrapper, stdout=None, stderr=None, failure=failure)
        for role in ("stdout", "stderr"):
            path = root / (role + ".log")
            try: completion[role] = file_pin(confined_file(root, role + ".log"))
            except (OSError, ValueError): pass
        completion = e.validate_homer_completion(completion, plan=plan)
        immutable_bytes(root / e.COMPLETION_FILENAME, _json_bytes(completion))
        completion_pin = file_pin(root / e.COMPLETION_FILENAME)
        # An output's failed read does not discard its independently valid siblings.
        manifest = _inventory_native(plan, completion, completion_pin)
        immutable_bytes(root / e.OUTPUT_MANIFEST_FILENAME, _json_bytes(manifest))
    if original_error is not None:
        return 2
    return 0


def _read_worker_file(identity, path):
    from .native_file_capture import _identity
    from .native_flux_balance_storage import read_bytes
    identity = _identity(identity)
    _require(type(path) is str and Path(path).is_absolute(), "input_path_invalid")
    raw = read_bytes(path)
    _require(hashlib.sha256(raw).hexdigest() == identity["sha256"] and len(raw) == identity["size_bytes"],
        "input_identity_conflict")
    return raw


def _initial_selector(sheet, selection):
    from . import homer_motif_contracts as c
    if type(selection) is dict and set(selection) == {"series_ids", "offset", "limit"}:
        return c.validate_homer_selector(selection)
    _closed(selection, ("series", "offset", "limit"), "initial_selection_fields_invalid")
    _require(type(selection["series"]) is list, "initial_series_required")
    files = {f["file_id"]: f for f in sheet["files"]}
    selected, logical = [], []
    for row in selection["series"]:
        _require(type(row) is dict and row.get("role") in ("known_results", "denovo_pwm", "denovo_combined_pwm",
            "denovo_nonredundant_pwm"), "initial_series_role_invalid")
        if row["role"] == "denovo_pwm":
            _closed(row, ("role", "motif_length"), "initial_series_fields_invalid")
            _require(type(row["motif_length"]) is int and row["motif_length"] > 0, "initial_motif_length_invalid")
            native_path = "native/homerMotifs.motifs" + str(row["motif_length"])
        else:
            _closed(row, ("role",), "initial_series_fields_invalid")
            native_path = None
        logical.append(_json_bytes(row))
        candidates = [s["series_id"] for s in sheet["series"] if s["role"] == row["role"]
            and (native_path is None or files[s["file_id"]]["native_relative_path"] == native_path)]
        _require(len(candidates) <= 1 or row["role"] == "denovo_nonredundant_pwm", "initial_series_ambiguous")
        if not candidates:
            issue = "selected_native_role_unavailable:" + row["role"]
            if row["role"] == "denovo_pwm": issue += ":" + str(row["motif_length"])
            if issue not in sheet["issues"]: sheet["issues"].append(issue)
        selected.extend(candidates)
    _require(len(set(logical)) == len(logical), "initial_series_duplicate")
    return c.validate_homer_selector(dict(series_ids=selected, offset=selection["offset"], limit=selection["limit"]))


def run_homer_motif_job(*, request, output_directory):
    """Pure retained-data adapter around the existing sheet and calculator."""
    from . import homer_motif_contracts as c
    from .homer_motif_measurements import parse_homer_motif_sheet, calculate_homer_components, project_homer_return
    from .homer_motif_result_contracts import validate_homer_motif_value
    from .native_flux_balance_storage import decode_json, directory, file_pin, immutable_bytes
    _closed(request, _PURE_FIELDS, "request_fields_invalid")
    _require(request["version"] == WORKER_REQUEST_VERSION and request["mode"] in ("parse", "calculate_saved")
        and type(request["projection_source_ref"]) is str and request["projection_source_ref"].startswith("source_"),
        "request_invalid")
    root = directory(Path(output_directory))
    sheet_declaration = None
    if request["mode"] == "parse":
        _require(request["saved"] is None and type(request["files"]) is list
            and request["invocation"] is not None and request["execution"] is not None, "parse_request_invalid")
        files, qualifications = [], []
        for row in request["files"]:
            _closed(row, ("role", "native_relative_path", "file", "path", "source_ref", "capture", "motif_length", "qualification"),
                "file_row_fields_invalid")
            _require(type(row["source_ref"]) is str and row["source_ref"].startswith("source_")
                and (row["qualification"] is None or type(row["qualification"]) is str)
                and (row["motif_length"] is None or type(row["motif_length"]) is int and row["motif_length"] > 0),
                "file_row_invalid")
            if row["file"] is None:
                _require(row["path"] is None, "missing_file_path_conflict")
                raw, artifact = None, None
            else:
                raw = _read_worker_file(row["file"], row["path"])
                artifact = dict(raw_artifact_ref=row["file"]["artifact_ref"], source_ref=row["source_ref"],
                    sha256=row["file"]["sha256"], size_bytes=row["file"]["size_bytes"])
            files.append(dict(role=row["role"], native_relative_path=row["native_relative_path"], content=raw,
                artifact=artifact, capture=row["capture"]))
            if row["qualification"] is not None:
                qualifications.append(row["qualification"])
        sheet = parse_homer_motif_sheet(files, invocation=request["invocation"], execution=request["execution"])
        # Literal capture qualifications are retained, not inferred native failures.
        sheet["issues"].extend(qualifications)
        sheet = c.validate_homer_sheet(sheet)
    else:
        _require(request["files"] is None and request["invocation"] is None and request["execution"] is None,
            "saved_request_invalid")
        _closed(request["saved"], ("file", "path"), "saved_sheet_fields_invalid")
        _require(request["saved"]["file"]["format"] == c.SHEET_VERSION, "saved_sheet_format_invalid")
        sheet = c.validate_homer_sheet(decode_json(_read_worker_file(request["saved"]["file"], request["saved"]["path"])))
    selector = _initial_selector(sheet, request["selection"])
    if request["mode"] == "parse":
        sheet = c.validate_homer_sheet(sheet)
        immutable_bytes(root / "sheet.json", _json_bytes(sheet))
        pin = file_pin(root / "sheet.json")
        sheet_declaration = dict(relative_path="sheet.json", format=c.SHEET_VERSION,
            sha256=pin["sha256"], size_bytes=pin["size_bytes"])
    components = calculate_homer_components(sheet, selector=selector)
    immutable_bytes(root / "components.json", _json_bytes(components))
    pin = file_pin(root / "components.json")
    value = project_homer_return(components, source_ref=request["projection_source_ref"])
    del value["version"]; del value["source_ref"]
    value = validate_homer_motif_value(value)
    return dict(version=WORKER_RESULT_VERSION, value=value, selector=selector, sheet=sheet_declaration,
        components=dict(relative_path="components.json", format=c.COMPONENTS_VERSION,
            sha256=pin["sha256"], size_bytes=pin["size_bytes"]))


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "--native-plan" and sys.argv[3] == "--selected-payload-sha256":
        return run_native_homer(Path(sys.argv[2]).absolute(), sys.argv[4])
    _require(len(sys.argv) == 3, "two_file_arguments_required")
    from .native_flux_balance_storage import decode_json
    request_path, output_path = map(Path, sys.argv[1:])
    payload = decode_json(request_path.read_bytes())
    _closed(payload, ("operation", "arguments"), "payload_fields_invalid")
    _require(payload["operation"] == "homer_motif_result", "operation_unsupported")
    _closed(payload["arguments"], ("request",), "payload_arguments_invalid")
    try:
        result = run_homer_motif_job(**payload["arguments"], output_directory=output_path.parent)
    except ValueError as error:
        output_path.write_bytes(_json_bytes(dict(code=str(error), exception_type="ValueError")))
        return 2
    except MemoryError:
        output_path.write_bytes(_json_bytes(dict(code="native_memory_allocation_failed", exception_type="MemoryError")))
        return 3
    output_path.write_bytes(_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
