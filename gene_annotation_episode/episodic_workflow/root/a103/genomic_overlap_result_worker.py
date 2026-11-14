"""Bounded, retained-byte genomic overlap conversion and saved recalculation.

The caller owns source/action authority and the local-job reservation. This
finite worker opens only explicit retained paths, preserves original native
facts, and calls the existing G1 readers/calculator and G3a projector. It writes
byte declarations, never Store identities. The fixed records are packet428's
contract; production does not read verification files.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import PurePosixPath
import stat
import sys
from typing import Any, Literal, TypeAlias, TypedDict

from .genomic_overlap_contracts import (
    Failure, NativeFileCapture, NativeFileDeclaration, NativeFileIdentity,
    Parameters, Selector, _finite_json_copy, canonical_genomic_overlap_sheet_sha256,
    validate_genomic_overlap_record,
)
from .genomic_overlap_inputs import (
    _failure, _unique_issues, _validate_set, _validate_sheet,
    build_genomic_overlap_sheet, extract_overlap_reference_metadata,
    parse_bedtools_intersect_wo, parse_region_set,
)
from .genomic_overlap_calculations import calculate_genomic_overlap_components
from .genomic_overlap_result_views import project_genomic_overlap_result
from .native_genomic_overlap_contracts import (
    genomic_overlap_output_files, validate_genomic_overlap_batch,
    validate_genomic_overlap_independent_pair_manifest,
    validate_genomic_overlap_run_plan,
)


class RetainedFile(TypedDict):
    file: NativeFileIdentity
    path: str


class CapturedInputFile(TypedDict):
    specification: dict[str, Any]
    declaration_source: Literal["batch", "pair", "none"]
    capture: NativeFileCapture | None
    retained: RetainedFile | None


class NativeWorkerPlan(TypedDict):
    version: Literal["genomic_overlap_result_worker_plan_v1"]
    mode: Literal["native_result"]
    directory: str
    original_plan: dict[str, Any]
    batch: RetainedFile | None
    files: list[CapturedInputFile]
    selector: Selector
    source_action_receipt_ref: str
    writer_closure_receipt_ref: str
    driver_state: Literal["sealed_batch", "unsealed_attempt", "not_started"]
    failures: list[Failure]


class SavedWorkerPlan(TypedDict):
    version: Literal["genomic_overlap_result_worker_plan_v1"]
    mode: Literal["saved_sheet_recalculation"]
    directory: str
    sheet: RetainedFile
    selector: Selector


WorkerPlan: TypeAlias = NativeWorkerPlan | SavedWorkerPlan


class SetConversion(TypedDict):
    set_key: str
    set_position: int
    basis: Literal["retained_parsed_set", "reparsed_retained_original", "unavailable"]
    original_file: NativeFileIdentity | None
    parsed_file: NativeFileIdentity | None
    result_extent: Literal["complete", "partial", "unavailable"]
    failures: list[Failure]


class PairConversion(TypedDict):
    comparison_key: str
    manifest_origin: Literal["batch", "pair", "none"]
    manifest_file: NativeFileIdentity | None
    batch_pair_index: int | None
    result_extent: Literal["complete", "partial", "unavailable"]
    failures: list[Failure]


class Diagnostics(TypedDict):
    version: Literal["genomic_overlap_result_diagnostics_v1"]
    mode: Literal["native_result", "saved_sheet_recalculation"]
    sets: list[SetConversion]
    pairs: list[PairConversion]
    failures: list[Failure]


class WorkerOutput(TypedDict):
    role: Literal["sheet", "components", "projection", "diagnostics"]
    declaration: NativeFileDeclaration


class WorkerResult(TypedDict):
    version: Literal["genomic_overlap_result_worker_result_v1"]
    mode: Literal["native_result", "saved_sheet_recalculation"]
    state: Literal["produced", "partial", "unavailable"]
    source_sheet_sha256: str | None
    parameters: Parameters
    outputs: list[WorkerOutput]
    failures: list[Failure]


_PLAN_VERSION = "genomic_overlap_result_worker_plan_v1"
_RESULT_VERSION = "genomic_overlap_result_worker_result_v1"
_MODES = ("native_result", "saved_sheet_recalculation")
_OUTPUTS = (
    ("sheet", "sheet.json", "genomic_region_overlap_sheet_v1"),
    ("components", "components.json", "genomic_region_overlap_components_v1"),
    ("projection", "projection.json", "genomic_overlap_projection_v1"),
    ("diagnostics", "diagnostics.json", "genomic_overlap_result_diagnostics_v1"),
)
_RESULT_NAME = "worker-result.json"
_EMPTY_SHA = hashlib.sha256(b"").hexdigest()


def _require(condition, code="genomic_overlap_worker_invalid_record"):
    if not condition:
        raise ValueError(code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields))


def _path(value):
    # Pure lexical validation: validators never stat producer or retained paths.
    _require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"),
             "genomic_overlap_worker_invalid_path")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts
             and value != "/" and not value.startswith("//"), "genomic_overlap_worker_invalid_path")
    return path


def _identity(value, expected_format=None):
    value = validate_genomic_overlap_record("NativeFileIdentity", value)
    _require(value["size_bytes"] != 0 or value["sha256"] == _EMPTY_SHA)
    _require(expected_format is None or value["format"] == expected_format,
             "genomic_overlap_worker_format_binding")
    return value


def _content_identity(value):
    # Store deduplicates byte content independently of each consuming role's
    # format label. Each label is validated separately before this alias join.
    return tuple(value[key] for key in ("artifact_ref", "sha256", "size_bytes"))


def _retained(value, expected_format):
    _closed(value, RetainedFile.__annotations__)
    _identity(value["file"], expected_format)
    return _path(value["path"])


def _declaration(value):
    value = validate_genomic_overlap_record("NativeFileDeclaration", value)
    path = PurePosixPath(value["relative_path"])
    _require(not path.is_absolute() and str(path) == value["relative_path"] and
        ".." not in path.parts and str(path) != "." and not any(c in str(path) for c in "\0\r\n\\"))
    present = value["state"] == "present"
    _require((value["sha256"] is not None and value["size_bytes"] is not None) if present
             else value["sha256"] is None and value["size_bytes"] is None)
    _require(value["size_bytes"] != 0 or value["sha256"] == _EMPTY_SHA)
    return value


def _capture(value):
    value = validate_genomic_overlap_record("NativeFileCapture", value)
    declaration = _declaration(value["declared"])
    observed = value["observed"]
    if observed is not None:
        _identity(observed, declaration["format"])
    same = observed is not None and all(observed[k] == declaration[k] for k in ("format", "sha256", "size_bytes"))
    outcome, failure = value["outcome"], value["failure"]
    if outcome == "declared_absent":
        _require(declaration["state"] == "absent" and observed is None and failure is None)
    else:
        _require(declaration["state"] == "present")
        if outcome == "verified":
            _require(same and failure is None)
        elif outcome == "digest_mismatch":
            _require(observed is not None and not same and failure == "capture_file_digest_mismatch")
        else:
            _require(observed is None and failure == "capture_file_unavailable")
    return value


def _failures(values):
    _require(type(values) is list)
    return [validate_genomic_overlap_record("Failure", value) for value in values]


def _selector(value, *, mode, request=None):
    value = validate_genomic_overlap_record("Selector", value)
    _require(value["mode"] == mode and len(set(value["comparison_keys"])) == len(value["comparison_keys"]))
    for name in ("minimum_a_fraction", "minimum_b_fraction"):
        fraction = value["parameters"][name]
        _require(fraction["numerator"] <= fraction["denominator"])
    projection = value["projection"]
    occurrences = [(r["set_key"], r["occurrence_key"]) for r in projection["occurrence_keys"]]
    _require(len(set(occurrences)) == len(occurrences))
    _require(projection["kind"] == "occurrence_rows" or not occurrences)
    if request is not None:
        keys = [row["comparison_key"] for row in request["comparisons"]]
        _require([key for key in keys if key in value["comparison_keys"]] == value["comparison_keys"],
                 "genomic_overlap_worker_selector_binding")
        selected_sets = {pair[side] for pair in request["comparisons"]
            if pair["comparison_key"] in value["comparison_keys"] for side in ("a_set_key", "b_set_key")}
        _require(all(key in selected_sets for key, _ in occurrences))
    return value


def validate_genomic_overlap_result_worker_plan(value: object) -> WorkerPlan:
    """Validate the closed transport plan and joins; return detached data, no I/O."""
    value = _finite_json_copy(value)
    _require(type(value) is dict and value.get("mode") in _MODES)
    native = value["mode"] == "native_result"
    _closed(value, (NativeWorkerPlan if native else SavedWorkerPlan).__annotations__)
    _require(value["version"] == _PLAN_VERSION)
    directory = _path(value["directory"])
    retained = []
    if native:
        original = validate_genomic_overlap_run_plan(value["original_plan"])
        request = original["requested_job"]["native_genomic_overlap"]["request"]
        selector = _selector(value["selector"], mode=value["mode"], request=request)
        _require(selector["saved_sheet_file"] is None)
        _require(value["driver_state"] in ("sealed_batch", "unsealed_attempt", "not_started"))
        for key in ("source_action_receipt_ref", "writer_closure_receipt_ref"):
            _require(type(value[key]) is str and bool(value[key]))
        failures = _failures(value["failures"])
        set_keys = {row["set_key"] for row in request["region_sets"]}
        comparisons = {row["comparison_key"]: row for row in request["comparisons"]}
        for failure in failures:
            sk, pk = failure["set_key"], failure["comparison_key"]
            _require(sk is None or sk in set_keys)
            _require(pk is None or pk in comparisons)
            _require(sk is None or pk is None or sk in (comparisons[pk]["a_set_key"], comparisons[pk]["b_set_key"]))
        if value["batch"] is not None:
            _retained(value["batch"], "genomic_overlap_native_batch_v1")
            retained.append(value["batch"])
            _require(value["driver_state"] == "sealed_batch")
        _require(type(value["files"]) is list)
        expected = genomic_overlap_output_files(request)[:-1]
        _require(len(value["files"]) == len(expected), "genomic_overlap_worker_file_order")
        for row, specification in zip(value["files"], expected):
            _closed(row, CapturedInputFile.__annotations__)
            _require(row["specification"] == specification, "genomic_overlap_worker_file_order")
            source, capture = row["declaration_source"], row["capture"]
            _require(source in ("batch", "pair", "none"))
            if source == "none":
                _require(capture is None)
            else:
                capture = _capture(capture)
                _require(all(capture["declared"][k] == specification[k] for k in ("relative_path", "format")))
                if source == "pair":
                    _require(specification["role"] in ("canonical_set", "overlap_stdout", "overlap_stderr"))
                else:
                    _require(value["driver_state"] == "sealed_batch")
            if row["retained"] is not None:
                _retained(row["retained"], specification["format"])
                retained.append(row["retained"])
                _require(capture is None or row["retained"]["file"] == capture["observed"])
        if value["driver_state"] == "not_started":
            _require(value["batch"] is None and all(row["capture"] is None and row["retained"] is None
                for row in value["files"]), "genomic_overlap_worker_not_started_observations")
    else:
        _retained(value["sheet"], _OUTPUTS[0][2])
        retained.append(value["sheet"])
        selector = _selector(value["selector"], mode=value["mode"])
        _require(selector["saved_sheet_file"] == value["sheet"]["file"],
                 "genomic_overlap_worker_saved_sheet_binding")
    paths = {}
    for row in retained:
        path = _path(row["path"])
        _require(path != directory and directory not in path.parents and path not in directory.parents,
                 "genomic_overlap_worker_invalid_path")
        for previous, identity in paths.items():
            _require(not (path in previous.parents or previous in path.parents)
                and (path != previous or identity == _content_identity(row["file"])), "genomic_overlap_worker_path_alias")
        paths[path] = _content_identity(row["file"])
    return value


def validate_genomic_overlap_result_worker_result(value: object) -> WorkerResult:
    """Validate declarations and production state without opening output files."""
    value = _finite_json_copy(value)
    _closed(value, WorkerResult.__annotations__)
    _require(value["version"] == _RESULT_VERSION and value["mode"] in _MODES)
    parameters = validate_genomic_overlap_record("Parameters", value["parameters"])
    for key in ("minimum_a_fraction", "minimum_b_fraction"):
        _require(parameters[key]["numerator"] <= parameters[key]["denominator"])
    _failures(value["failures"])
    _require(type(value["outputs"]) is list and len(value["outputs"]) == 4)
    present = []
    for row, (role, filename, format_name) in zip(value["outputs"], _OUTPUTS):
        _closed(row, WorkerOutput.__annotations__)
        declaration = _declaration(row["declaration"])
        _require(row["role"] == role and declaration["relative_path"] == filename
                 and declaration["format"] == format_name)
        if declaration["state"] == "present":
            _require(declaration["size_bytes"] > 0)
        present.append(declaration["state"] == "present")
    _require(present[3] and (not present[1] or present[0]) and (not present[2] or all(present[:2])))
    _require(value["state"] == ("produced" if all(present[:3]) else "partial" if any(present[:3]) else "unavailable"))
    _require(value["source_sheet_sha256"] == (value["outputs"][0]["declaration"]["sha256"] if present[0] else None))
    return value


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _decode(raw, *, newline=False):
    def pairs(rows):
        result = {}
        for key, item in rows:
            _require(key not in result, "genomic_overlap_worker_duplicate_json_key")
            result[key] = item
        return result
    def nonfinite(_):
        raise ValueError("genomic_overlap_worker_nonfinite_json")
    try:
        value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                                           parse_constant=nonfinite))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("genomic_overlap_worker_invalid_json") from error
    _require(raw == _canonical(value) + (b"\n" if newline else b""),
             "genomic_overlap_worker_noncanonical_json")
    return value


@contextmanager
def _directory(value, *, create=False):
    """Pin every path component; never follow a directory symlink."""
    path = PurePosixPath("/") if value == "/" else _path(value)
    with ExitStack() as stack:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open("/", flags)
        stack.callback(os.close, descriptor)
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            descriptor = os.open(part, flags, dir_fd=descriptor)
            stack.callback(os.close, descriptor)
        yield descriptor


def _read(value):
    path = _path(value)
    with _directory(str(path.parent)) as parent:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
        try:
            observed = os.fstat(descriptor)
            _require(stat.S_ISREG(observed.st_mode), "genomic_overlap_worker_nonregular_input")
            with os.fdopen(os.dup(descriptor), "rb") as stream:
                raw = stream.read()
            after = os.fstat(descriptor)
            _require((observed.st_dev, observed.st_ino, observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                "genomic_overlap_worker_input_changed")
            return raw, (observed.st_dev, observed.st_ino)
        finally:
            os.close(descriptor)


class _SourceFailure(Exception):
    def __init__(self, failure):
        self.failure = failure
        super().__init__(failure["code"])


def _load(retained, *, location, missing_code, requirement, original=False, inodes):
    identity = retained["file"] if retained is not None else None
    common = {**location, "artifact_ref": identity["artifact_ref"] if identity else location.get("artifact_ref")}
    if retained is None:
        raise _SourceFailure(_failure(missing_code, "capture", requirement=requirement, **common))
    try:
        raw, inode = _read(retained["path"])
    except (OSError, ValueError) as error:
        observed = error.errno if isinstance(error, OSError) else None
        raise _SourceFailure(_failure(missing_code, "capture", requirement=requirement,
                                     observed_value=observed, **common)) from error
    prior = inodes.setdefault(inode, _content_identity(identity))
    _require(prior == _content_identity(identity), "genomic_overlap_worker_path_alias")
    actual = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    expected = {k: identity[k] for k in actual}
    if actual != expected:
        raise _SourceFailure(_failure("input_digest_mismatch" if original else "artifact_digest_mismatch",
            "capture", requirement="matching_file_identity", expected_value=expected, observed_value=actual, **common))
    return raw


class _NativeInputs:
    """Current retained representations; no producer lookup or acquisition."""
    def __init__(self, plan, diagnostics, inodes):
        self.plan, self.diagnostics, self.inodes = plan, diagnostics, inodes
        self.rows = {row["specification"]["file_key"]: (i, row) for i, row in enumerate(plan["files"])}
        self.cache = {}
        self.join_failures = {}

    def failure(self, key, code, *, stage="capture", expected=None, observed=None, requirement="matching_file_identity"):
        index, row = self.rows[key]
        spec = row["specification"]
        retained = row["retained"]
        return _failure(code, stage, set_key=spec["set_key"], comparison_key=spec["comparison_key"],
            artifact_ref=retained["file"]["artifact_ref"] if retained else
                row["capture"]["observed"]["artifact_ref"] if row["capture"] and row["capture"]["observed"] else None,
            field_path=f"/files/{index}", expected_value=expected, observed_value=observed, requirement=requirement)

    def join(self, key, declaration, source):
        _, row = self.rows[key]
        if row["declaration_source"] != source or row["capture"] is None or row["capture"]["declared"] != declaration:
            failure = self.failure(key, "original_attempt_mismatch", stage="parse", expected=declaration,
                observed=row["capture"]["declared"] if row["capture"] else None)
            self.join_failures.setdefault(key, []).append(failure)
            self.cache.pop(key, None)

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        index, row = self.rows[key]
        spec, capture = row["specification"], row["capture"]
        original = spec["role"] == "original_input"
        missing = "input_unavailable" if original else "native_output_unavailable"
        requirement = "complete_input" if spec["role"] in ("original_input", "parsed_set") else "original_native_output"
        failures = list(self.join_failures.get(key, []))
        raw = None
        if capture is not None and capture["outcome"] == "digest_mismatch":
            failures.append(self.failure(key, "input_digest_mismatch" if original else "artifact_digest_mismatch",
                expected={k: capture["declared"][k] for k in ("sha256", "size_bytes")},
                observed={k: capture["observed"][k] for k in ("sha256", "size_bytes")}))
        elif capture is not None and capture["outcome"] in ("declared_absent", "unavailable"):
            failures.append(self.failure(key, missing, requirement=requirement))
        elif not failures:
            try:
                raw = _load(row["retained"], location={"set_key": spec["set_key"],
                    "comparison_key": spec["comparison_key"], "field_path": f"/files/{index}/retained",
                    "artifact_ref": capture["observed"]["artifact_ref"] if capture and capture["observed"] else None},
                    missing_code=missing, requirement=requirement, original=original, inodes=self.inodes)
            except _SourceFailure as error:
                failures.append(error.failure)
        result = (raw, row["retained"]["file"] if raw is not None else None, failures)
        self.cache[key] = result
        return result


def _json_source(raw, identity, *, record, location, validate):
    try:
        value = _decode(raw, newline=True)
        return validate(value), None
    except ValueError:
        return None, _failure("native_output_malformed", "parse", artifact_ref=identity["artifact_ref"],
            requirement="complete_input" if record == "ParsedRegionSet" else "original_native_output", **location)


def _batch(plan, inputs):
    retained = plan["batch"]
    try:
        raw = _load(retained, location={"field_path": "/batch"}, missing_code="native_output_unavailable",
            requirement="original_native_output", inodes=inputs.inodes)
    except _SourceFailure as error:
        inputs.diagnostics["failures"].append(error.failure)
        return None
    try:
        decoded = _decode(raw, newline=True)
    except ValueError:
        inputs.diagnostics["failures"].append(_failure("native_output_malformed", "parse",
            artifact_ref=retained["file"]["artifact_ref"], field_path="/batch", requirement="original_native_output"))
        return None
    try:
        batch = validate_genomic_overlap_batch(decoded, plan=plan["original_plan"])
    except ValueError:
        inputs.diagnostics["failures"].append(_failure("original_attempt_mismatch", "parse",
            artifact_ref=retained["file"]["artifact_ref"], field_path="/batch", requirement="matching_file_identity"))
        return None
    for row in batch["files"]:
        inputs.join(row["specification"]["file_key"], row["declaration"], "batch")
    return batch


def _resolve_sets(plan, inputs, batch):
    request = plan["original_plan"]["requested_job"]["native_genomic_overlap"]["request"]
    results = []
    for position, spec in enumerate(request["region_sets"]):
        original_key, parsed_key = f"s{position}:original", f"s{position}:parsed"
        raw, original_file, original_failures = inputs.get(original_key)
        failures = list(original_failures)
        reparsed = None
        if raw is not None:
            expected = {k: spec["source"]["file"][k] for k in ("sha256", "size_bytes", "format")}
            actual = {k: original_file[k] for k in expected}
            if actual != expected:
                failures.append(inputs.failure(original_key, "input_digest_mismatch", expected=expected, observed=actual))
                original_file = None
            else:
                reparsed = parse_region_set(raw, specification=spec, set_position=position)
        parsed_raw, parsed_file, parsed_failures = inputs.get(parsed_key)
        failures.extend(parsed_failures)
        parsed = None
        if parsed_raw is not None:
            parsed, failure = _json_source(parsed_raw, parsed_file, record="ParsedRegionSet",
                location={"set_key": spec["set_key"], "field_path": f"/files/{inputs.rows[parsed_key][0]}"},
                validate=lambda value: _validate_set(value, specification=spec, set_position=position))
            if failure is not None:
                failures.append(failure)
            if parsed is not None and batch is not None and parsed["result_extent"] != batch["sets"][position]["parse_extent"]:
                failures.append(inputs.failure(parsed_key, "original_attempt_mismatch", stage="parse",
                    expected=batch["sets"][position]["parse_extent"], observed=parsed["result_extent"]))
                parsed = None
            if parsed is not None and reparsed is not None and parsed != reparsed:
                failures.append(inputs.failure(parsed_key, "original_attempt_mismatch", stage="parse",
                    expected=reparsed, observed=parsed))
                parsed = None
            if parsed is not None and batch is None and reparsed is None:
                failures.append(inputs.failure(parsed_key, "native_output_unavailable", stage="parse",
                    requirement="complete_input"))
                parsed = None
        if parsed is not None:
            result, basis = parsed, "retained_parsed_set"
        elif reparsed is not None:
            result, basis = reparsed, "reparsed_retained_original"
            parsed_file = None
        else:
            result = parse_region_set(None, specification=spec, set_position=position)
            basis, parsed_file = "unavailable", None
        # Current capture failures stay outside an originally parsed record.
        inputs.diagnostics["sets"].append({"set_key": spec["set_key"], "set_position": position,
            "basis": basis, "original_file": original_file, "parsed_file": parsed_file,
            "result_extent": result["result_extent"], "failures": _unique_issues(failures, result["issues"])})
        results.append(result)
    return results


def _driver_failure(row, *, inputs):
    code = row["code"]
    if code == "invalid_input":
        return None  # Actual G1 malformed rows remain in the original parsed map.
    mapping = {
        "input_unavailable": ("input_unavailable", "input", "complete_input"),
        "input_digest_mismatch": ("input_digest_mismatch", "capture", "matching_file_identity"),
        "native_dependency_unavailable": ("native_dependency_unavailable", "native", "bound_bedtools"),
        "native_version_unverified": ("native_version_unverified", "native", "native_version_evidence"),
        "software_identity_mismatch": ("original_attempt_mismatch", "native", "matching_file_identity"),
        "native_spawn_failed": ("native_output_unavailable", "native", "original_native_output"),
        "native_nonzero_exit": ("native_nonzero_exit", "native", "complete_native_output"),
        "resource_limit": ("resource_limit", "native", "complete_native_output"),
        "output_unavailable": ("native_output_unavailable", "capture", "complete_native_output"),
        "seal_failed": ("native_output_partial", "capture", "complete_native_output"),
    }
    mapped, stage, requirement = mapping[code]
    retained = inputs.rows[row["file_key"]][1]["retained"] if row["file_key"] in inputs.rows else None
    return _failure(mapped, stage, set_key=row["set_key"], comparison_key=row["comparison_key"],
        artifact_ref=retained["file"]["artifact_ref"] if retained else None, field_path=row["field_path"],
        expected_value=row["expected_value"], observed_value=row["observed_value"], requirement=requirement)


def _pair_keys(pair, positions):
    return [f"s{positions[pair[side + '_set_key']]}:canonical" for side in ("a", "b")] + [
        f"p{pair['ordinal']}:{role}" for role in ("stdout", "stderr")]


def _manifests(plan, inputs, batch, request):
    """Qualify independent seals first, so shared declarations cannot be chosen."""
    manifests, origins, identities, failures = [], [], [], []
    positions = {spec["set_key"]: i for i, spec in enumerate(request["region_sets"])}
    declarations = {}
    for pair in request["comparisons"]:
        index = pair["ordinal"]
        key = f"p{index}:manifest"
        raw, identity, problems = inputs.get(key)
        problems = list(problems)
        standalone = None
        if raw is not None:
            try:
                decoded = _decode(raw, newline=True)
            except ValueError:
                problems.append(inputs.failure(key, "native_output_malformed", stage="parse", requirement="original_native_output"))
            else:
                try:
                    standalone = validate_genomic_overlap_independent_pair_manifest(decoded,
                        plan=plan["original_plan"], comparison=pair)
                except ValueError:
                    problems.append(inputs.failure(key, "original_attempt_mismatch", stage="parse"))
        embedded = batch["pairs"][index]["manifest"] if batch else None
        origin, manifest_file = "none", None
        manifest = embedded if embedded is not None else standalone
        if embedded is not None:
            origin, manifest_file = "batch", plan["batch"]["file"]
        elif standalone is not None:
            origin, manifest_file = "pair", identity
        if embedded is not None and standalone is not None and embedded != standalone:
            problems.append(inputs.failure(key, "original_attempt_mismatch", stage="parse", expected=embedded, observed=standalone))
            manifest, origin, manifest_file = None, "none", None
        if batch is not None and embedded is None and standalone is not None:
            problems.append(inputs.failure(key, "original_attempt_mismatch", stage="parse", expected=None, observed=standalone))
            manifest, origin, manifest_file = None, "none", None
        if manifest is not None and manifest["files"]:
            for file_key, row in zip(_pair_keys(pair, positions), manifest["files"]):
                declaration = row["declaration"]
                if file_key in declarations and declarations[file_key] != declaration:
                    issue = inputs.failure(file_key, "original_attempt_mismatch", stage="parse",
                        expected=declarations[file_key], observed=declaration)
                    inputs.join_failures.setdefault(file_key, []).append(issue)
                declarations.setdefault(file_key, declaration)
                if batch is None:
                    # Previously batch-authenticated capture rows remain their
                    # original source label after later batch byte loss.
                    source = inputs.rows[file_key][1]["declaration_source"]
                    inputs.join(file_key, declaration, "batch" if source == "batch" else "pair")
        manifests.append(manifest); origins.append(origin); identities.append(manifest_file); failures.append(problems)
    return manifests, origins, identities, failures


def _native_identity(plan):
    original = plan["original_plan"]["identity"]
    return {**{k: original[k] for k in ("run_id", "resource_id", "execution_id", "attempt_id", "operation_key")},
            "origin_episode_id": original["episode_id"]}


def _relevant(failures, pair):
    return [failure for failure in failures if
        failure["comparison_key"] == pair["comparison_key"] or failure["comparison_key"] is None and
        failure["set_key"] in (pair["a_set_key"], pair["b_set_key"])]


def _current_pair_failures(plan, pair, sets, inputs):
    """Recovered maps do not inherit a failed alternative representation."""
    result = []
    for failure in _relevant(plan["failures"], pair):
        path = failure["field_path"] or ""
        located = [(index, row) for index, row in inputs.rows.values()
            if path == f"/files/{index}" or path.startswith(f"/files/{index}/")]
        if located and located[0][1]["specification"]["role"] in ("rejected_input", "pair_manifest") \
                and failure["stage"] in ("capture", "parse"):
            # These files supply diagnostics or redundant original metadata.
            # Current qualified maps/seals/role bytes determine scientific use.
            continue
        sk = failure["set_key"]
        if sk is not None and sets[sk]["result_extent"] == "complete" and failure["stage"] in ("input", "capture", "parse"):
            applicable = [index for index, row in inputs.rows.values()
                if row["specification"]["set_key"] == sk and row["specification"]["role"] in ("original_input", "parsed_set")]
            artifacts = {sets[sk]["source_file"]["artifact_ref"]}
            for index, row in inputs.rows.values():
                if index in applicable and row["retained"]:
                    artifacts.add(row["retained"]["file"]["artifact_ref"])
            if (located and located[0][0] in applicable) or not located and failure["artifact_ref"] in artifacts:
                continue
        result.append(failure)
    return result


def _receipt(plan, pair, sets, inputs, *, manifest, manifest_file, batch, pair_failures):
    specs = plan["original_plan"]["requested_job"]["native_genomic_overlap"]["request"]["region_sets"]
    positions = {spec["set_key"]: i for i, spec in enumerate(specs)}
    keys = _pair_keys(pair, positions)
    # Original uninvoked derivations have no native streams. An absent output
    # declaration is an original fact, not a current lost-file failure.
    noninvoked = batch is not None and batch["pairs"][pair["ordinal"]]["disposition"] in (
        "input_unavailable", "native_unavailable") or plan["driver_state"] == "not_started"
    uninvoked = noninvoked or manifest is not None and manifest["derivation"] != "bedtools_intersect"
    roles = []
    for position, key in enumerate(keys):
        row = inputs.rows[key][1]
        expected = row["retained"] is not None or row["capture"] is not None and row["capture"]["declared"]["state"] == "present"
        roles.append((None, None, []) if uninvoked and (position >= 2 or not expected) else inputs.get(key))
    operands = [sets[pair[side + "_set_key"]] for side in ("a", "b")]
    current_failures = []
    for role in roles:
        current_failures.extend(role[2])
    current_failures.extend(_current_pair_failures(plan, pair, sets, inputs))
    native = {"version": "genomic_overlap_native_pair_receipt_v1", "comparison_key": pair["comparison_key"],
        "identity": _native_identity(plan), "derivation": "bedtools_intersect",
        "outcome": "not_executed" if noninvoked else "unknown", "software": None,
        "realized_argv": [], "environment": {}, "returncode": None, "started_at": None,
        "finished_at": None, "writer_closed": None, "stdout": None, "stderr": None,
        "capture_extent": "unavailable", "native_result_extent": "unavailable",
        "completeness_basis": "unavailable", "completeness_source_refs": list(dict.fromkeys([
            plan["source_action_receipt_ref"], plan["writer_closure_receipt_ref"],
            *([manifest_file["artifact_ref"]] if manifest_file else [])])), "issues": []}
    for side, operand, role in zip(("a", "b"), operands, roles):
        native[side] = {"set_key": operand["set_key"], "original_file": operand["source_file"],
                        "canonical_file": role[1]}
    content = None
    if manifest is not None:
        for field in ("identity", "derivation", "outcome", "software", "realized_argv", "environment",
                      "returncode", "started_at", "finished_at", "writer_closed"):
            native[field] = deepcopy(manifest[field])
        if manifest["derivation"] == "validated_empty_input":
            native.update(native_result_extent="complete", completeness_basis="validated_empty_input",
                capture_extent="complete" if all(row["result_extent"] == "complete" for row in operands) else "unavailable")
            # No native output exists for this analytic derivation. Missing
            # canonical captures do not invalidate complete original row maps.
            pair_failures.extend(failure for role in roles for failure in role[2])
            current_failures = _current_pair_failures(plan, pair, sets, inputs)
            for operand in operands:
                if operand["result_extent"] == "unavailable":
                    current_failures.extend(operand["issues"])
        elif manifest["derivation"] == "not_executed_invalid_input":
            pair_failures.extend(failure for role in roles for failure in role[2])
            current_failures = _current_pair_failures(plan, pair, sets, inputs)
        else:
            content, native["stdout"], _ = roles[2]
            native["stderr"] = roles[3][1]
            native.update(native_result_extent="complete" if manifest["outcome"] == "succeeded" else "partial",
                completeness_basis="closed_successful_native_attempt" if manifest["outcome"] == "succeeded" else "partial_native_result",
                capture_extent="unavailable" if content is None else
                    "complete" if all(row[0] is not None for row in roles) and all(row["result_extent"] == "complete" for row in operands)
                    else "partial")
    elif not noninvoked:
        content, native["stdout"], _ = roles[2]
        native["stderr"] = roles[3][1]
        if content is not None:
            native.update(writer_closed=True, capture_extent="partial", native_result_extent="partial",
                          completeness_basis="partial_native_result")
        current_failures.append(_failure("native_output_partial", "capture", comparison_key=pair["comparison_key"],
            field_path=f"/pairs/{pair['ordinal']}", requirement="complete_native_output"))
    if batch is not None:
        for index in batch["pairs"][pair["ordinal"]]["failure_indices"]:
            failure = _driver_failure(batch["failures"][index], inputs=inputs)
            if failure is not None:
                # Shared software/native failures affect this pair because the
                # original PairOutput explicitly references their indices.
                if failure["comparison_key"] is None and failure["set_key"] is None:
                    failure["comparison_key"] = pair["comparison_key"]
                current_failures.append(failure)
    # A missing redundant seal is diagnostic when usable embedded facts exist.
    scientifically_relevant = [f for f in pair_failures if manifest is None and f["code"] == "original_attempt_mismatch"]
    native["issues"] = _unique_issues(current_failures, scientifically_relevant)
    return native, content


def _native(plan, diagnostics, inodes):
    inputs = _NativeInputs(plan, diagnostics, inodes)
    request = plan["original_plan"]["requested_job"]["native_genomic_overlap"]["request"]
    batch = _batch(plan, inputs) if plan["driver_state"] != "not_started" else None
    manifests, origins, identities, failures = _manifests(plan, inputs, batch, request)
    sets = _resolve_sets(plan, inputs, batch)
    by_key = {row["set_key"]: row for row in sets}
    if batch is not None:
        diagnostics["failures"].extend(failure for row in batch["failures"]
            if (failure := _driver_failure(row, inputs=inputs)) is not None)
    pairs = []
    for pair, manifest, origin, identity, problems in zip(request["comparisons"], manifests, origins, identities, failures):
        native, content = _receipt(plan, pair, by_key, inputs, manifest=manifest, manifest_file=identity,
                                   batch=batch, pair_failures=problems)
        try:
            parsed = parse_bedtools_intersect_wo(content, pair=pair, sets=by_key, native=native)
        except ValueError as error:
            # Only a source contradiction at the known manifest/map boundary
            # is recoverable. Programming errors are not converted to no data.
            if str(error) not in {"genomic_overlap_invalid_analytic_empty", "genomic_overlap_invalid_unexecuted_pair",
                                 "genomic_overlap_analytic_capture_unavailable", "genomic_overlap_analytic_extent"}:
                raise
            failure = _failure("original_attempt_mismatch", "parse", comparison_key=pair["comparison_key"],
                artifact_ref=identity["artifact_ref"] if identity else None,
                field_path=f"/pairs/{pair['ordinal']}/manifest", requirement="matching_file_identity")
            problems.append(failure)
            native, content = _receipt(plan, pair, by_key, inputs, manifest=None, manifest_file=None,
                                       batch=None, pair_failures=problems)
            parsed = parse_bedtools_intersect_wo(content, pair=pair, sets=by_key, native=native)
            origin, identity = "none", None
        diagnostics["pairs"].append({"comparison_key": pair["comparison_key"], "manifest_origin": origin,
            "manifest_file": identity, "batch_pair_index": pair["ordinal"] if origin == "batch" else None,
            "result_extent": parsed["result_extent"],
            "failures": _unique_issues(problems, native["issues"], parsed["issues"])})
        pairs.append(parsed)
    references = extract_overlap_reference_metadata(specifications=request["region_sets"],
        sets=by_key, comparisons=request["comparisons"])
    return build_genomic_overlap_sheet(request=request, sets=sets, native_pairs=pairs, reference_relations=references)


def _saved(plan, diagnostics, inodes):
    try:
        raw = _load(plan["sheet"], location={"field_path": "/sheet"}, missing_code="input_unavailable",
                    requirement="complete_input", inodes=inodes)
    except _SourceFailure as error:
        diagnostics["failures"].append(error.failure)
        return None, None
    try:
        sheet = _validate_sheet(_decode(raw))
    except ValueError:
        diagnostics["failures"].append(_failure("native_output_malformed", "parse",
            artifact_ref=plan["sheet"]["file"]["artifact_ref"], field_path="/sheet", requirement="complete_input"))
        return None, None
    return sheet, raw


def _publish(directory, outputs, inodes):
    """Publish closed immutable bytes without replacement; result comes last."""
    with _directory(directory, create=True) as parent:
        for filename in [row[1] for row in _OUTPUTS] + [_RESULT_NAME]:
            try:
                descriptor = os.open(filename, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
            except FileNotFoundError:
                continue
            try:
                info = os.fstat(descriptor)
                _require(stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) not in inodes,
                         "genomic_overlap_worker_invalid_output")
                with os.fdopen(os.dup(descriptor), "rb") as stream:
                    _require(filename in outputs and stream.read() == outputs[filename], "genomic_overlap_worker_output_conflict")
            finally:
                os.close(descriptor)
        for filename, raw in outputs.items():
            try:
                os.stat(filename, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                continue
            temporary = "." + filename + ".writing"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            try:
                with os.fdopen(os.dup(descriptor), "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                os.fchmod(descriptor, 0o444)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.link(temporary, filename, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.fsync(parent)
            os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)


def run_genomic_overlap_result_worker(plan: WorkerPlan) -> WorkerResult:
    """Convert exactly supplied retained data and emit four fixed declarations."""
    plan = validate_genomic_overlap_result_worker_plan(plan)
    diagnostics = {"version": "genomic_overlap_result_diagnostics_v1", "mode": plan["mode"],
        "sets": [], "pairs": [], "failures": deepcopy(plan.get("failures", []))}
    outputs, inodes = {}, {}
    if plan["mode"] == "native_result":
        sheet = _native(plan, diagnostics, inodes)
        sheet_raw = _canonical(sheet)
    else:
        sheet, sheet_raw = _saved(plan, diagnostics, inodes)
    source_sha = None
    if sheet is not None:
        source_sha = canonical_genomic_overlap_sheet_sha256(sheet)
        _require(hashlib.sha256(sheet_raw).hexdigest() == source_sha, "genomic_overlap_worker_sheet_hash")
        outputs["sheet.json"] = sheet_raw
        # Invalid API parameters were rejected before I/O. Only scientific
        # validation errors have a typed failure; unexpected errors propagate.
        try:
            components = calculate_genomic_overlap_components(sheet, parameters=plan["selector"]["parameters"])
        except ValueError as error:
            if not str(error).startswith("genomic_overlap_"):
                raise
            diagnostics["failures"].append(_failure("requested_field_unavailable", "calculate",
                field_path="/components", requirement="requested_selected_field"))
        else:
            _require(components["source_sheet_sha256"] == source_sha and
                components["parameters"] == plan["selector"]["parameters"], "genomic_overlap_worker_component_join")
            outputs["components.json"] = _canonical(components)
            try:
                projection = project_genomic_overlap_result(sheet, components, selector=plan["selector"])
            except ValueError as error:
                if not str(error).startswith(("genomic_overlap_", "genomic_overlap_projection:")):
                    raise
                diagnostics["failures"].append(_failure("requested_field_unavailable", "project",
                    field_path="/projection", requirement="requested_selected_field"))
            else:
                _require(projection["source_sheet_sha256"] == source_sha and
                    projection["parameters"] == plan["selector"]["parameters"], "genomic_overlap_worker_projection_join")
                outputs["projection.json"] = _canonical(projection)
    diagnostics["failures"] = _unique_issues(diagnostics["failures"],
        *(row["failures"] for row in diagnostics["sets"]), *(row["failures"] for row in diagnostics["pairs"]))
    outputs["diagnostics.json"] = _canonical(diagnostics)
    declarations = []
    for role, filename, format_name in _OUTPUTS:
        raw = outputs.get(filename)
        declarations.append({"role": role, "declaration": {"relative_path": filename, "format": format_name,
            "state": "absent" if raw is None else "present", "sha256": None if raw is None else hashlib.sha256(raw).hexdigest(),
            "size_bytes": None if raw is None else len(raw)}})
    count = sum(name in outputs for name in ("sheet.json", "components.json", "projection.json"))
    result = validate_genomic_overlap_result_worker_result({"version": _RESULT_VERSION, "mode": plan["mode"],
        "state": "produced" if count == 3 else "partial" if count else "unavailable", "source_sheet_sha256": source_sha,
        "parameters": plan["selector"]["parameters"], "outputs": declarations, "failures": diagnostics["failures"]})
    outputs[_RESULT_NAME] = _canonical(result)
    _publish(plan["directory"], outputs, inodes)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    _require(type(arguments) is list and len(arguments) == 1, "genomic_overlap_worker_plan_argument")
    raw, _ = _read(arguments[0])
    run_genomic_overlap_result_worker(validate_genomic_overlap_result_worker_plan(_decode(raw)))
    return 0


__all__ = ["RetainedFile", "CapturedInputFile", "NativeWorkerPlan", "SavedWorkerPlan", "WorkerPlan",
    "SetConversion", "PairConversion", "Diagnostics", "WorkerOutput", "WorkerResult",
    "validate_genomic_overlap_result_worker_plan", "validate_genomic_overlap_result_worker_result",
    "run_genomic_overlap_result_worker", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
