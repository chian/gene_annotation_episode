"""One finite selected MACS2 pipeline, with independent command seals.

The existing native lifecycle owns process-tree limits and original execution.
No retry, native mode choice, scientific calculation or episode loop lives here.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys

from .acquisition import AcquisitionError
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_atac_differential_contracts import (
    POLICY, OWNER_FILENAME, STARTED_FILENAME, STEP_KEYS, canonical, digest, require, path_value,
    failure, unique_failures, atac_command_argv, atac_native_environment, atac_driver_argv,
    producer_ref, validate_atac_run_plan, validate_atac_command_seal, validate_atac_native_bundle,
    validate_driver_runtime,
)


def _directory(value):
    path = Path(path_value(str(value), absolute=True))
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        require(stat.S_ISDIR(mode), "invalid_output_path")
    return path


def confined_file(directory, relative_path):
    path = _directory(directory) / str(path_value(relative_path, absolute=False))
    _directory(path.parent)
    try:
        require(stat.S_ISREG(path.lstat().st_mode), "invalid_output_path")
    except FileNotFoundError:
        pass
    return path


@contextmanager
def _regular(value):
    path = Path(path_value(str(value), absolute=True))
    with ExitStack() as stack:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open("/", flags)
        stack.callback(os.close, descriptor)
        for part in path.parts[1:-1]:
            descriptor = os.open(part, flags, dir_fd=descriptor)
            stack.callback(os.close, descriptor)
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=descriptor)
        stack.callback(os.close, descriptor)
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), "input_unavailable")
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            yield stream


def stream_identity(stream):
    stream.seek(0)
    hasher, size = hashlib.sha256(), 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        hasher.update(block)
        size += len(block)
    stream.seek(0)
    return {"sha256": hasher.hexdigest(), "size_bytes": size}


def file_identity(path):
    with _regular(path) as stream:
        return stream_identity(stream)


def decode_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "invalid_native_control_json")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("invalid_native_control_json")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid_native_control_json") from error


def _read_control(path):
    with _regular(path) as stream:
        raw = stream.read()
    value = decode_json(raw)
    require(raw in (canonical(value), canonical(value) + b"\n"), "original_attempt_mismatch")
    return value


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish(temporary, destination):
    os.chmod(temporary, 0o444)
    os.link(temporary, destination)
    _sync_directory(destination.parent)
    temporary.unlink()
    _sync_directory(destination.parent)


@contextmanager
def _writing(path):
    path = confined_file(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = confined_file(path.parent, "." + path.name + ".writing")
    with temporary.open("xb") as stream:
        yield stream
        stream.flush()
        os.fsync(stream.fileno())
    _publish(temporary, path)


def _immutable(path, value):
    raw = canonical(value)
    if path.exists():
        with _regular(path) as stream:
            require(stream.read() == raw)
        return
    with _writing(path) as stream:
        stream.write(raw)


def declaration(spec, directory):
    result = {"relative_path": spec["relative_path"], "format": spec["format"],
        "state": "absent", "sha256": None, "size_bytes": None}
    path = confined_file(directory, spec["relative_path"])
    if path.exists():
        result.update(state="present", **file_identity(path))
    return result


def _stage(binding, spec, *, directory, policy):
    target = confined_file(directory, spec["relative_path"])
    temporary = confined_file(target.parent, "." + target.name + ".staging")
    with _regular(binding["path"]) as source:
        before = os.fstat(source.fileno())
        check_scratch_budget(directory.parent, policy, additional_bytes=before.st_size)
        with temporary.open("xb") as output:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        after = os.fstat(source.fileno())
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "artifact_digest_mismatch")
    require(file_identity(temporary) == {k: binding["file"][k] for k in ("sha256", "size_bytes")}, "artifact_digest_mismatch")
    _publish(temporary, target)
    return target


def verify_driver_runtime(driver):
    """Verify the selected Python, implementation and dependency file closure."""
    driver = validate_driver_runtime(driver)
    selected = Path(driver["python_executable"]).resolve(strict=True)
    require(os.path.samefile(selected, "/proc/self/exe") and
        file_identity(selected)["sha256"] == driver["python_sha256"] and
        platform.python_version() == driver["python_version"], "native_dependency_unavailable")
    for row in driver["implementation_files"]:
        path = confined_file(driver["module_root"], row["module"].replace(".", "/") + ".py")
        require(file_identity(path)["sha256"] == row["sha256"], "native_dependency_unavailable")
        loaded = sys.modules.get(row["module"])
        if loaded is not None:
            require(Path(loaded.__file__) == path, "native_dependency_unavailable")
    module_names = {"rpds-py": "rpds", "jsonschema-specifications": "jsonschema_specifications", "attrs": "attr", "python-dateutil": "dateutil", "fair-esm": "esm"}
    for dependency in driver["dependencies"]:
        name = dependency["distribution"]
        require(importlib.metadata.version(name) == dependency["version"], "native_dependency_unavailable")
        module = importlib.import_module(module_names.get(name, name.replace("-", "_")))
        require(Path(module.__file__).parent == Path(dependency["package_root"]), "native_dependency_unavailable")
        for pin in dependency["files"]:
            require(file_identity(pin["path"]) == {k: pin[k] for k in ("sha256", "size_bytes")}, "native_dependency_unavailable")
    pinned = {p["path"] for row in driver["dependencies"] for p in row["files"]}
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and "site-packages" in Path(filename).parts:
            require(str(Path(filename).resolve(strict=True)) in pinned, "native_dependency_unavailable")


def verify_software(software):
    """Verify the actual host reader and distinct native interpreter closure."""
    verify_driver_runtime(software["driver_runtime"])
    native = software["macs2_runtime"]
    require(file_identity(Path(native["python_executable"]).resolve(strict=True))["sha256"] == native["python_sha256"]
        and file_identity(native["macs2_script"])["sha256"] == native["macs2_sha256"], "native_dependency_unavailable")
    for pin in native["files"]:
        require(file_identity(pin["path"]) == {k: pin[k] for k in ("sha256", "size_bytes")}, "native_dependency_unavailable")


def _identity_from_declaration(value):
    if value["state"] != "present":
        return None
    return {"artifact_ref": "artifact_" + value["sha256"], **{k: value[k] for k in ("sha256", "size_bytes", "format")}}


def _callpeak_binding(plan, seal):
    request = plan["requested_job"]["native_atac_differential"]["request"]
    i = int(seal["step_key"][-1]) - 1
    selected = request["inputs"][i]
    roles = {r["specification"]["role"]: _identity_from_declaration(r["declaration"]) for r in seal["outputs"]}
    p = request["callpeak"]
    return dict(run_key=seal["step_key"], condition_id=selected["condition_id"], sample_ids=[selected["sample_id"]],
        reference_id=selected["reference_id"], treatment_input_refs=[selected["file"]["artifact_ref"]],
        supplied_control_sample_ids=[], supplied_control_input_refs=[], selected_format="BAM", paired_end=False,
        selected_argv=seal["argv"], selected_parameters={**p, "effective_genome_size_bp": None,
            "pvalue_cutoff": None, "small_local_window_bp": None, "large_local_window_bp": None},
        artifact_roles={key: roles[role]["artifact_ref"] if roles[role] else None for key, role in
            (("peaks_xls", "peaks_xls"), ("narrowpeak", "narrowpeak"), ("summits", "summits"),
             ("signal_track", "signal"), ("background_track", "background"))}, producer_ref=seal["producer_ref"])


def _depths(plan, seals, directory):
    from .atac_differential_inputs import parse_macs2_peaks_xls
    from .atac_differential_sheet import select_atac_depth_counts
    bindings, reports = [], []
    request = plan["requested_job"]["native_atac_differential"]["request"]
    for seal in seals:
        binding = _callpeak_binding(plan, seal)
        bindings.append(binding)
        row = next(r for r in seal["outputs"] if r["specification"]["role"] == "peaks_xls")
        identity = _identity_from_declaration(row["declaration"])
        artifact = dict(artifact_ref=identity["artifact_ref"] if identity else None, format="macs2_peaks_xls_narrow",
            expected_sha256=identity["sha256"] if identity else None, expected_size_bytes=identity["size_bytes"] if identity else None,
            supplied_extent="complete" if seal["outcome"] == "succeeded" else "partial" if identity else "unknown",
            producer_run_ref=seal["producer_ref"], producer_outcome=seal["outcome"], writer_closed=True,
            producer_name="MACS2", producer_version="2.2.9.1", producer_source_ref=None,
            origin=request["samples"][next(i for i,s in enumerate(request["samples"]) if s["sample_id"] == binding["sample_ids"][0])]["origin"])
        if identity is None:
            report = parse_macs2_peaks_xls(None, artifact=artifact, callpeak=binding)
        else:
            with _regular(confined_file(directory, row["specification"]["relative_path"])) as stream:
                report = parse_macs2_peaks_xls(stream, artifact=artifact, callpeak=binding)
        reports.append(report)
    return select_atac_depth_counts(reports, conditions=tuple(c["condition_id"] for c in request["conditions"]), callpeak_bindings=bindings)


def _execute(plan, key, *, inputs, argv, enabled, problems, directory, specs, policy):
    started = finished = returncode = None
    outcome = "not_run"
    environment = atac_native_environment(plan, key)
    if enabled:
        try:
            verify_software(plan["requested_job"]["native_atac_differential"]["software"])
            check_scratch_budget(directory.parent, policy)
        except (OSError, ValueError, ImportError, AcquisitionError) as error:
            problems.append(failure("resource_limit" if isinstance(error, AcquisitionError) else "native_dependency_unavailable",
                "execution", step_key=key, requirement="resource_allocation" if isinstance(error, AcquisitionError) else "native_runtime"))
            enabled = False
    if enabled:
        for name in (environment["TMPDIR"], str(directory / "tmp/c1"), str(directory / "tmp/c2")):
            _directory(name).mkdir(parents=True, exist_ok=True)
        started = datetime.now(timezone.utc).isoformat()
        try:
            with confined_file(directory, specs[key + ".stdout"]["relative_path"]).open("xb") as stdout, \
                    confined_file(directory, specs[key + ".stderr"]["relative_path"]).open("xb") as stderr:
                completed = subprocess.run(argv, cwd=directory, env=environment, stdout=stdout, stderr=stderr, check=False)
                returncode = completed.returncode
            outcome = "succeeded" if returncode == 0 else "failed"
            if returncode != 0:
                problems.append(failure("native_nonzero_exit", "execution", step_key=key, requirement="original_native_outcome"))
        except OSError:
            outcome = "failed"
            problems.append(failure("native_dependency_unavailable", "execution", step_key=key, requirement="native_runtime"))
        finished = datetime.now(timezone.utc).isoformat()
    outputs = [{"specification": spec, "declaration": declaration(spec, directory)}
        for spec in plan["outputs"] if spec["step_key"] == key and spec["role"] != "seal"]
    if outcome == "succeeded":
        for row in outputs:
            if row["declaration"]["state"] == "absent":
                problems.append(failure("native_output_unavailable", "execution", step_key=key,
                    file_key=row["specification"]["file_key"], requirement="complete_native_output"))
    seal = validate_atac_command_seal(dict(version="atac_native_command_seal_v1", identity=plan["identity"],
        step_key=key, producer_ref=producer_ref(plan, key), argv=argv, environment=environment, inputs=inputs,
        started_at=started, finished_at=finished, returncode=returncode, outcome=outcome,
        outputs=outputs, failures=problems), plan=plan, step_key=key)
    _immutable(confined_file(directory, specs[key + ".seal"]["relative_path"]), seal)
    return seal


def run_atac_differential_driver(plan):
    plan = validate_atac_run_plan(plan)
    directory = _directory(plan["attempt_directory"])
    specs = {r["file_key"]: r for r in plan["outputs"]}
    bundle_path = confined_file(directory, specs["bundle"]["relative_path"])
    if directory.exists() and any(directory.iterdir()):
        require(_read_control(confined_file(directory, OWNER_FILENAME)) == plan)
        require(bundle_path.exists(), "unsealed_native_attempt")
        result = validate_atac_native_bundle(_read_control(bundle_path), plan=plan)
        for row in result["outputs"]:
            require(declaration(row["specification"], directory) == row["declaration"])
        return result
    directory.mkdir(parents=True, exist_ok=True)
    _immutable(directory / OWNER_FILENAME, plan)
    _immutable(directory / STARTED_FILENAME, {"plan": plan, "started_at": datetime.now(timezone.utc).isoformat()})
    job = plan["requested_job"]["native_atac_differential"]
    request, policy = job["request"], LocalJobPolicy(**plan["policy"])
    for spec in plan["outputs"]:
        confined_file(directory, spec["relative_path"]).parent.mkdir(parents=True, exist_ok=True)
    for name in ("tmp", "cache/pip"):
        (directory / name).mkdir(parents=True, exist_ok=True)
    _immutable(confined_file(directory, specs["request_metadata"]["relative_path"]), request)
    seals, inspections, problems = [], [], []
    runtime_available = True
    try:
        # The raw-header reader is part of this same pinned driver closure.
        # Check it before staging or interpreting either selected input.
        verify_software(job["software"])
    except (OSError, ValueError, ImportError) as error:
        runtime_available = False
    from .native_atac_differential_reference import extract_atac_bam_header
    for i, binding in enumerate(job["input_bindings"], 1):
        key, own = f"callpeak{i}", []
        staged = None
        if not runtime_available:
            own.append(failure("native_dependency_unavailable", "execution", step_key=key,
                binding_key=binding["input_key"], requirement="native_runtime"))
        else:
            try:
                staged = _stage(binding, specs[f"input{i}"], directory=directory, policy=policy)
            except (OSError, ValueError, AcquisitionError) as error:
                code = "resource_limit" if isinstance(error, AcquisitionError) else "artifact_digest_mismatch" if str(error) == "artifact_digest_mismatch" else "input_unavailable"
                own.append(failure(code, "input", step_key=key, file_key=f"input{i}", binding_key=binding["input_key"],
                    artifact_ref=binding["file"]["artifact_ref"], requirement="resource_allocation" if code == "resource_limit" else "matching_file_identity"))
        header_spec = specs[f"header{i}"]
        if staged is not None:
            header = extract_atac_bam_header(input_path=staged, input_file=binding["file"], input_key=binding["input_key"],
                callpeak_run_key=key, input_ordinal=0, output_path=confined_file(directory, header_spec["relative_path"]),
                output_relative_path=header_spec["relative_path"], policy=policy)
            own.extend(header["failures"])
        else:
            header = dict(version="atac_bam_header_extraction_v1", input_key=binding["input_key"], callpeak_run_key=key,
                input_ordinal=0, input_file=binding["file"], header=declaration(header_spec, directory),
                producer_outcome="not_run", supplied_extent="unknown", failures=list(own))
        inspections.append(header)
        seals.append(_execute(plan, key, inputs=[{"file_key": f"input{i}", "role": "treatment", "file": binding["file"]}],
            argv=atac_command_argv(plan, key), enabled=staged is not None and header["producer_outcome"] == "succeeded",
            problems=own, directory=directory, specs=specs, policy=policy))
        problems.extend(seals[-1]["failures"])
    depth = _depths(plan, seals, directory)
    _immutable(confined_file(directory, specs["depth_selection"]["relative_path"]), depth)
    own, inputs = [], []
    for key in ("callpeak1.signal", "callpeak1.background", "callpeak2.signal", "callpeak2.background"):
        row = next(r for seal in seals for r in seal["outputs"] if r["specification"]["file_key"] == key)
        identity = _identity_from_declaration(row["declaration"])
        if identity is None:
            own.append(failure("native_dependency_output_unavailable", "execution", step_key="bdgdiff", file_key=key,
                requirement="complete_native_output"))
        else:
            inputs.append({"file_key": key, "role": row["specification"]["role"], "file": identity})
    argv = atac_command_argv(plan, "bdgdiff", depth_selection=depth)
    if not argv:
        own.append(failure("native_depth_unavailable", "execution", step_key="bdgdiff", requirement="matching_count_population"))
    # A failed callpeak may retain useful files; it cannot establish the full
    # selected bdgdiff operand population. Preserve those files and its status.
    if any(s["outcome"] != "succeeded" for s in seals):
        own.append(failure("native_dependency_output_unavailable", "execution", step_key="bdgdiff", requirement="complete_native_output"))
    if len(inputs) != 4:
        inputs = []
    seals.append(_execute(plan, "bdgdiff", inputs=inputs, argv=argv, enabled=not own,
        problems=own, directory=directory, specs=specs, policy=policy))
    problems = unique_failures(problems, own)
    with _writing(confined_file(directory, specs["stdout"]["relative_path"])) as stream:
        for seal in seals:
            stream.write(canonical({"step_key": seal["step_key"], "outcome": seal["outcome"], "returncode": seal["returncode"]}) + b"\n")
    with _writing(confined_file(directory, specs["stderr"]["relative_path"])) as stream:
        for item in problems:
            stream.write(canonical(item) + b"\n")
    result = validate_atac_native_bundle(dict(version="atac_differential_native_bundle_v1", identity=plan["identity"],
        request=request, software=job["software"], input_inspections=inspections, steps=seals, depth_selection=depth,
        outputs=[{"specification": spec, "declaration": declaration(spec, directory)} for spec in plan["outputs"][:-1]],
        failures=problems), plan=plan)
    _immutable(bundle_path, result)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    require(len(args) == 1)
    plan = validate_atac_run_plan(_read_control(Path(args[0])))
    require(args[0] == atac_driver_argv(plan)[-1] and Path.cwd() == Path(plan["identity"]["execution_id"]).parent)
    result = run_atac_differential_driver(plan)
    return 0 if all(s["outcome"] == "succeeded" for s in result["steps"]) and not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


