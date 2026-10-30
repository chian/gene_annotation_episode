"""Finite supplied-Cooler extraction, closing each population before the next.

The shared native lifecycle owns execution and limits. This module chooses no
new population, normalization, resource, retry, timer, or episode action.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import stat
import sys

from .acquisition import AcquisitionError
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .chromatin_interaction_contracts import validate_chromatin_record
from .native_chromatin_interaction_contracts import (
    OWNER_FILENAME, STARTED_FILENAME, TABLE_ROLES, canonical, digest, require,
    path_value, failure, unique_failures, unavailable_extraction,
    chromatin_driver_argv, chromatin_environment, validate_chromatin_bundle,
    validate_chromatin_population_seal, validate_chromatin_run_plan,
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


def verify_software(software):
    """Check actual selected interpreter, source bytes and imported dependencies."""
    selected = Path(software["python_executable"]).resolve(strict=True)
    require(os.path.samefile(selected, "/proc/self/exe") and
        file_identity(selected)["sha256"] == software["python_sha256"] and
        platform.python_version() == software["python_version"], "native_dependency_unavailable")
    for row in software["implementation_files"]:
        path = confined_file(software["module_root"], row["module"].replace(".", "/") + ".py")
        require(file_identity(path)["sha256"] == row["sha256"], "native_dependency_unavailable")
        loaded = sys.modules.get(row["module"])
        if loaded is not None:
            require(Path(loaded.__file__) == path, "native_dependency_unavailable")
    module_names = {"rpds-py": "rpds", "jsonschema-specifications": "jsonschema_specifications", "attrs": "attr", "python-dateutil": "dateutil"}
    for dependency in software["dependencies"]:
        name = dependency["distribution"]
        require(importlib.metadata.version(name) == dependency["version"], "native_dependency_unavailable")
        module = importlib.import_module(module_names.get(name, name.replace("-", "_")))
        require(Path(module.__file__).parent == Path(dependency["package_root"]), "native_dependency_unavailable")
        for pin in dependency["files"]:
            require(file_identity(pin["path"]) == {k: pin[k] for k in ("sha256", "size_bytes")},
                "native_dependency_unavailable")
    pinned = {pin["path"] for row in software["dependencies"] for pin in row["files"]}
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename is not None and "site-packages" in Path(filename).parts:
            require(str(Path(filename).resolve(strict=True)) in pinned, "native_dependency_unavailable")


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
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "input_digest_mismatch")
    require(file_identity(temporary) == {k: binding["file"][k] for k in ("sha256", "size_bytes")}, "input_digest_mismatch")
    _publish(temporary, target)
    return target


def merge_extractions(extractions, request):
    known = [e for e in extractions if e["native_metadata"] is not None]
    header = known[0] if known else extractions[0]
    require(all(all(e[k] == header[k] for k in ("format", "format_version", "native_metadata", "chromosomes"))
        for e in known), "original_attempt_mismatch")
    return validate_chromatin_record("ContactExtraction", {**{k: deepcopy(header[k]) for k in
        ("format", "format_version", "native_metadata", "chromosomes")},
        "populations": [p for e in extractions for p in e["populations"]],
        "table_drafts": [t for e in extractions for t in e["table_drafts"]],
        "failures": unique_failures(*(e["failures"] for e in extractions))})


def _extract_one(source, population, request, specs, directory, policy):
    from .chromatin_cooler_inputs import read_cooler_contacts
    temporary, streams = {}, {}
    with ExitStack() as stack:
        for role in TABLE_ROLES:
            target = confined_file(directory, specs[role]["relative_path"])
            temporary[role] = confined_file(target.parent, "." + target.name + ".writing")
            streams[(population["population_key"], role)] = stack.enter_context(temporary[role].open("x+b"))
        source.seek(0)
        extraction = read_cooler_contacts(source, spec=request["contact"], normalization=request["normalization"],
            populations=[population], table_streams=streams)
        extraction = validate_chromatin_record("ContactExtraction", extraction)
        require([p["selected_region"] for p in extraction["populations"]] == [population])
        require([d["role"] for d in extraction["table_drafts"]] == list(TABLE_ROLES))
        for stream in streams.values():
            stream.flush()
            os.fsync(stream.fileno())
        check_scratch_budget(directory.parent, policy)
    for draft in extraction["table_drafts"]:
        role = draft["role"]
        if draft["availability"] == "present":
            _publish(temporary[role], confined_file(directory, specs[role]["relative_path"]))
        elif temporary[role].stat().st_size == 0:
            temporary[role].unlink()
        # Nonempty failed encodings remain explicit .writing diagnostics and
        # never become a claimed present canonical table.
    return extraction


def run_chromatin_interaction_driver(plan):
    plan = validate_chromatin_run_plan(plan)
    directory = _directory(plan["attempt_directory"])
    specs = {row["file_key"]: row for row in plan["outputs"]}
    bundle_path = confined_file(directory, specs["bundle"]["relative_path"])
    if directory.exists() and any(directory.iterdir()):
        require(_read_control(confined_file(directory, OWNER_FILENAME)) == plan)
        if not bundle_path.exists():
            raise ValueError("unsealed_native_attempt")
        result = validate_chromatin_bundle(_read_control(bundle_path), plan=plan)
        for row in result["outputs"]:
            require(declaration(row["specification"], directory) == row["declaration"])
        return result
    directory.mkdir(parents=True, exist_ok=True)
    _immutable(directory / OWNER_FILENAME, plan)
    _immutable(directory / STARTED_FILENAME, {"plan": plan, "started_at": datetime.now(timezone.utc).isoformat()})
    job = plan["requested_job"]["native_chromatin_interactions"]
    request, policy = job["request"], LocalJobPolicy(**plan["policy"])
    for spec in plan["outputs"]:
        confined_file(directory, spec["relative_path"]).parent.mkdir(parents=True, exist_ok=True)
    for name in ("tmp", "cache", "cache/pip"):
        (directory / name).mkdir(parents=True, exist_ok=True)
    problems, staged, extractions, seals = [], {}, [], []
    try:
        verify_software(job["software"])
        software_ok = True
    except (OSError, ValueError, ImportError):
        software_ok = False
        problems.append(failure("native_dependency_unavailable", "execution", field_path="/software", requirement="bound_dependencies"))
    for binding, role in zip(job["input_bindings"], ("original_contact", "original_elements")):
        try:
            staged[role] = _stage(binding, specs[role], directory=directory, policy=policy)
        except (OSError, ValueError, AcquisitionError) as error:
            code = "resource_limit" if isinstance(error, AcquisitionError) else "input_digest_mismatch" if str(error) == "input_digest_mismatch" else "input_unavailable"
            problems.append(failure(code, "input", input_key=binding["input_key"], artifact_ref=binding["file"]["artifact_ref"],
                requirement="caller_resource_fit" if code == "resource_limit" else "matching_file_identity"))
    _immutable(confined_file(directory, specs["original_metadata"]["relative_path"]), request["supplied_metadata"])
    elements = metadata = None
    if software_ok and "original_elements" in staged:
        from .chromatin_interaction_inputs import parse_chromatin_elements
        with _regular(staged["original_elements"]) as stream:
            elements = parse_chromatin_elements(stream.read(), spec=request["elements"])
    with ExitStack() as stack:
        source = stack.enter_context(_regular(staged["original_contact"])) if "original_contact" in staged else None
        log_path = confined_file(directory, specs["stdout"]["relative_path"])
        log = stack.enter_context(log_path.open("xb"))
        for ordinal, population in enumerate(request["populations"]):
            selected = {role: specs[f"p{ordinal}.{role}"] for role in TABLE_ROLES}
            if software_ok and source is not None:
                extraction = _extract_one(source, population, request, selected, directory, policy)
            else:
                extraction = unavailable_extraction(request, code="input_unavailable" if source is None else "native_dependency_unavailable", populations=[population])
            extractions.append(extraction)
            seal = {"version": "chromatin_interaction_population_seal_v1", "identity": plan["identity"],
                "request_sha256": digest(request), "native": {"metadata": extraction["native_metadata"], "chromosomes": extraction["chromosomes"]},
                "population": extraction["populations"][0], "tables": [{"draft": draft,
                    "declaration": declaration(selected[draft["role"]], directory)} for draft in extraction["table_drafts"]],
                "input_files": [r["file"] for r in job["input_bindings"]], "failures": extraction["failures"]}
            validate_chromatin_population_seal(seal, plan=plan, population=population)
            seal_spec = specs[f"p{ordinal}.population_manifest"]
            _immutable(confined_file(directory, seal_spec["relative_path"]), seal)
            seals.append(declaration(seal_spec, directory))
            log.write(canonical({"event": "population_sealed", "population_key": population["population_key"],
                "at": datetime.now(timezone.utc).isoformat(), "ordinal": ordinal, "extent": extraction["populations"][0]["extent"],
                "stored_rows": extraction["populations"][0]["raw_cell_population"]["stored_rows"]}) + b"\n")
            log.flush()
            os.fsync(log.fileno())
    log_path.chmod(0o444)
    extraction = merge_extractions(extractions, request)
    if software_ok:
        from .chromatin_interaction_inputs import extract_chromatin_metadata
        metadata = extract_chromatin_metadata(request=request, native=extraction, supplied=request["supplied_metadata"], elements=elements)
        try:
            verify_software(job["software"])
        except (OSError, ValueError, ImportError):
            problems.append(failure("native_dependency_unavailable", "execution", field_path="/software", requirement="bound_dependencies"))
    problems = unique_failures(problems, extraction["failures"], elements["failures"] if elements else [], metadata["failures"] if metadata else [])
    with _writing(confined_file(directory, specs["stderr"]["relative_path"])) as stream:
        for problem in problems:
            stream.write(canonical(problem) + b"\n")
    result = validate_chromatin_bundle({"version": "chromatin_interaction_native_bundle_v1", "identity": plan["identity"],
        "request": request, "software": job["software"], "extraction": extraction, "elements": elements, "metadata": metadata,
        "population_seals": seals, "outputs": [{"specification": spec, "declaration": declaration(spec, directory)}
            for spec in plan["outputs"] if spec["role"] != "bundle"], "failures": problems}, plan=plan)
    _immutable(bundle_path, result)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    require(len(args) == 1)
    plan = validate_chromatin_run_plan(_read_control(Path(args[0])))
    require(args[0] == chromatin_driver_argv(plan)[-1] and Path.cwd() == Path(plan["identity"]["execution_id"]).parent)
    result = run_chromatin_interaction_driver(plan)
    return 0 if result["extraction"] is not None and all(p["extent"] == "complete" for p in result["extraction"]["populations"]) and not any(
        p["stage"] in ("execution", "input") for p in result["failures"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
