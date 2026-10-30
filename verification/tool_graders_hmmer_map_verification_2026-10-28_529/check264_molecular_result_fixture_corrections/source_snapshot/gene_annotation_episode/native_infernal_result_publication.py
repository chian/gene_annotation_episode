"""Retain bounded Infernal grading and publish receiver-selected measurements.

Only captured bytes reach the deterministic worker. This adapter copies saved
quantities into Store observations after original subject and scope validation;
it performs no scientific calculation, acquisition, retry, or credit assignment.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

from .acquisition import AcquisitionError
from .domain import ContractError, identity, validate_schema
from .infernal_native_result_views import (NATIVE_INFERNAL_METRICS, row_schema,
    validate_native_infernal_result_selector)
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job
from .materials import artifact_file, artifact_path
from .native_infernal_contracts import (finite_json_copy, native_infernal_digest,
    validate_native_infernal_requested_job)
from .practical_execution_state import _immutable, _read
from .tool_grading_artifacts import retain_tool_grading


_PREPARED_VERSION = "native_infernal_prepared_grading_v1"
_SCHEMA_VERSION = "native_infernal_retained_grading_v1"
_PREPARED_FIELDS = {"version", "bundle_artifact_ref", "source_grading_artifact_ref",
    "grading_artifact_ref", "sheet_artifact_ref", "scores_artifact_ref",
    "selected_rows_artifact_ref", "failures", "numerical_complete"}
_STABLE_FIELDS = {"schema", "sheet_artifact_ref", "sheet_schema", "sheet_format",
    "scores_artifact_ref", "scores_schema", "scores_format", "captured_artifacts"}
_SELECTED_FIELDS = {"version", "family", "native_ordinal", "record_key", "locator",
    "sequence_name", "model_name", "strand", "origin", "population", "column_index",
    "pair_columns", "invalid", "measurements", "unavailable", "observation_measurements",
    "subject_operand", "subject_intervals", "related_operands"}
_OPERAND_FIELDS = {"operand_role", "record_ordinal", "artifact_ref", "name", "accession",
    "kind", "alphabet", "length", "sequence_sha256", "locator", "binding"}


def _failure(stage, code, record_key=None):
    return {"stage": stage, "code": code, "record_key": record_key}


def _failures(rows):
    if type(rows) is not list or any(type(row) is not dict or set(row) != {
            "stage", "code", "record_key"} or any(type(row[k]) is not str or not row[k]
            for k in ("stage", "code")) or row["record_key"] is not None and
            (type(row["record_key"]) is not str or not row["record_key"]) for row in rows):
        raise ContractError("native_infernal_grading_failures_invalid")
    return rows


def _decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError("native_infernal_grading_duplicate_json_key")
            result[key] = value
        return result
    try:
        return finite_json_copy(json.loads(raw, object_pairs_hook=unique))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ContractError("native_infernal_grading_json_invalid") from error


def _retained(store, reference):
    row = store._require(reference, {"artifact"})
    path = artifact_path(store, reference)
    if (reference != "artifact_" + row["sha256"] or type(row["size"]) is not int
            or path.stat().st_size != row["size"]):
        raise ContractError("native_infernal_retained_artifact_identity_mismatch")
    return row, path


def _bundle(store, bundle, reference):
    bundle = finite_json_copy(bundle)
    if type(bundle) is not dict or bundle.get("version") != "native_infernal_bundle_v1":
        raise ContractError("native_infernal_original_bundle_required")
    _retained(store, reference)
    if native_infernal_digest(_decode(store.get_artifact(reference))) != native_infernal_digest(bundle):
        raise ContractError("native_infernal_bundle_artifact_identity_mismatch")
    request = validate_native_infernal_requested_job(bundle["requested_job"])
    job = request["native_infernal"]
    if any(bundle[key] != job[key] for key in ("program", "table_format", "operand_bindings")):
        raise ContractError("native_infernal_bundle_request_identity_mismatch")
    return bundle


def _captured_paths(store, bundle, artifacts):
    """Verify each supplied artifact; retain unusable descriptors and siblings."""
    declared, job = {}, bundle["requested_job"]["native_infernal"]
    for kind, rows in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        selected = {r["role"]: r for r in job["operands" if kind == "input" else "outputs"]}
        for row in rows:
            key = (row["role"], row["format"], row["relative_path"])
            path = PurePosixPath(row["relative_path"])
            original = selected.get(row["role"])
            if (key in declared or original is None or original["format"] != row["format"]
                    or path.is_absolute() or ".." in path.parts or str(path) != row["relative_path"]
                    or kind == "output" and original["relative_path"] != row["relative_path"]):
                raise ContractError("native_infernal_bundle_artifact_binding_invalid")
            declared[key] = kind, row, original
    paths, custody, failures, seen = [], [], [], set()
    for item in artifacts:
        if (type(item) is not dict or set(item) != {"role", "format", "relative_path", "artifact_ref"}
                or any(type(v) is not str or not v for v in item.values())):
            raise ContractError("native_infernal_captured_artifact_shape_invalid")
        key = (item["role"], item["format"], item["relative_path"])
        if key not in declared or key in seen:
            raise ContractError("native_infernal_captured_artifact_binding_invalid")
        seen.add(key)
        kind, native, original = declared[key]
        custody.append({**item, "kind": kind})
        expected = native["actual_sha256"] if kind == "input" else native["sha256"]
        try:
            stored, path = _retained(store, item["artifact_ref"])
            if stored["sha256"] != expected or stored["size"] != native["size_bytes"]:
                raise ContractError("native_infernal_captured_artifact_digest_mismatch")
            if kind == "input" and (expected != native["expected_sha256"]
                    or native["size_bytes"] != native["expected_size_bytes"]
                    or expected != original["sha256"] or native["size_bytes"] != original["size_bytes"]
                    or native["original_path"] != original["path"]):
                raise ContractError("native_infernal_input_not_original_selected_bytes")
            paths.append({**item, "kind": kind, "path": str(path)})
        except (ValueError, OSError) as error:
            code = str(error) if isinstance(error, ValueError) else "native_infernal_captured_artifact_unreadable"
            failures.append(_failure("custody", code + ":" + item["role"]))
    for key in declared:
        if key not in seen:
            failures.append(_failure("custody", "native_infernal_captured_artifact_missing:" + key[0]))
    return paths, custody, failures


def _grading(store, prepared, bundle, selector, *, verify_files=False):
    """Validate small retained envelopes without hydrating sheets or datasets."""
    prepared = finite_json_copy(prepared)
    if (type(prepared) is not dict or set(prepared) != _PREPARED_FIELDS
            or prepared["version"] != _PREPARED_VERSION or type(prepared["numerical_complete"]) is not bool):
        raise ContractError("native_infernal_prepared_grading_invalid")
    _failures(prepared["failures"])
    for field, reference in prepared.items():
        if field.endswith("artifact_ref") and reference is not None:
            if verify_files or field in {"source_grading_artifact_ref", "grading_artifact_ref"}:
                _retained(store, reference)
            else:
                store._require(reference, {"artifact"})
    envelopes = []
    for field in ("source_grading_artifact_ref", "grading_artifact_ref"):
        if prepared[field] is None:
            raise ContractError("native_infernal_retained_grading_required")
        envelope = _decode(store.get_artifact(prepared[field]))
        if (type(envelope) is not dict or set(envelope) != {
                "schema", "provider", "native_artifact_ref", "grading"}
                or envelope["schema"] != "tool_grading_artifact_v1"
                or envelope["provider"] != "episode.execution_result"
                or envelope["native_artifact_ref"] != prepared["bundle_artifact_ref"]
                or type(envelope["grading"]) is not dict):
            raise ContractError("native_infernal_prepared_grading_identity_mismatch")
        envelopes.append(envelope["grading"])
    stable, selected = envelopes
    if (set(stable) != _STABLE_FIELDS or stable["schema"] != _SCHEMA_VERSION
            or stable["sheet_format"] != "json" or stable["scores_format"] != "json"
            or {key: selected.get(key) for key in _STABLE_FIELDS} != stable
            or selected.get("bundle_sha256") != native_infernal_digest(bundle)
            or selected.get("selector") != selector
            or selected.get("selected_rows_schema") != "native_infernal_selected_row_v1"
            or selected.get("selected_rows_format") != "ndjson"
            or any(selected.get(field) != prepared[field] for field in (
                "sheet_artifact_ref", "scores_artifact_ref", "selected_rows_artifact_ref",
                "source_grading_artifact_ref", "failures", "numerical_complete"))):
        raise ContractError("native_infernal_prepared_grading_identity_mismatch")
    if verify_files:
        for descriptor in selected.get("diagnostic_artifacts", []):
            _retained(store, descriptor["artifact_ref"])
    return selected


def prepare_native_infernal_grading(store, *, bundle, bundle_artifact_ref, artifacts,
                                    directory, policy, selector):
    """Run the supplied bounded worker once; sealed replay verifies and reuses."""
    bundle = _bundle(store, bundle, bundle_artifact_ref)
    if not isinstance(policy, LocalJobPolicy):
        raise ContractError("native_infernal_local_job_policy_required")
    selector = validate_native_infernal_result_selector(selector, program=bundle["program"])
    artifacts = finite_json_copy(artifacts)
    paths, custody, failures = _captured_paths(store, bundle, artifacts)
    failures += [_failure(row["stage"], row["code"]) for row in bundle.get("failures", [])]
    if bundle.get("returncode") != 0:
        failures.append(_failure("native", "native_infernal_native_execution_unsuccessful"))
    directory = Path(directory).resolve() / "native-infernal-grading"
    fingerprint = native_infernal_digest({"bundle": bundle, "bundle_artifact_ref": bundle_artifact_ref,
        "artifacts": artifacts, "policy": policy.to_dict(), "selector": selector})
    if directory.exists():
        intent, saved = directory / "intent.json", directory / "prepared.json"
        if not intent.is_file() or _read(intent) != {"request_sha256": fingerprint}:
            raise ContractError("native_infernal_grading_directory_identity_conflict")
        if not saved.is_file():
            raise ContractError("native_infernal_grading_original_preparation_incomplete")
        prepared = finite_json_copy(_read(saved))
        grading = _grading(store, prepared, bundle, selector, verify_files=True)
        if (prepared["bundle_artifact_ref"] != bundle_artifact_ref
                or grading["captured_artifacts"] != custody
                or any(failure not in prepared["failures"] for failure in failures)):
            raise ContractError("native_infernal_prepared_grading_identity_mismatch")
        return prepared
    directory.mkdir(parents=True)
    _immutable(directory / "intent.json", {"request_sha256": fingerprint})
    plan = {"version": "native_infernal_grading_plan_v1", "bundle": bundle,
        "artifacts": paths, "directory": str(directory), "selector": selector, "failures": failures}
    _immutable(directory / "plan.json", plan)
    prepared = {"version": _PREPARED_VERSION, "bundle_artifact_ref": bundle_artifact_ref,
        "source_grading_artifact_ref": None, "grading_artifact_ref": None, "sheet_artifact_ref": None,
        "scores_artifact_ref": None, "selected_rows_artifact_ref": None,
        "failures": failures, "numerical_complete": False}
    receipt, successful_worker = None, False
    try:
        for name in ("tmp", "cache"):
            (directory / name).mkdir()
        check_scratch_budget(directory, policy)
        result = run_local_job([sys.executable, "-m", "gene_annotation_episode.native_infernal_result_worker",
            str(directory / "plan.json")], cwd=directory, policy=policy,
            stdout_path=directory / "worker.stdout", stderr_path=directory / "worker.stderr",
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]),
                **{key: str(directory / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
                "XDG_CACHE_HOME": str(directory / "cache")})
        receipt, successful_worker = result.metadata, result.returncode == 0
        if not successful_worker:
            failures.append(_failure("worker", "native_infernal_grading_worker_nonzero"))
    except (AcquisitionError, OSError, ValueError) as error:
        failures.append(_failure("worker", getattr(error, "code", "native_infernal_grading_worker_failed")))
        receipt = {"exception_type": type(error).__name__, "detail": str(error),
            "operational": getattr(error, "operational", None)}
    manifest_path, manifest = directory / "worker-result.json", {}
    try:
        if manifest_path.is_file():
            manifest = _decode(manifest_path.read_bytes())
        if (type(manifest) is not dict or set(manifest) != {
                "version", "sheet_schema", "scores_schema", "numerical_complete", "failures"}
                or manifest["version"] != "native_infernal_worker_result_v1"
                or type(manifest["numerical_complete"]) is not bool
                or any(manifest[k] is not None and type(manifest[k]) is not str
                    for k in ("sheet_schema", "scores_schema"))):
            raise ContractError("native_infernal_grading_worker_manifest_invalid")
        _failures(manifest["failures"])
    except (ValueError, OSError):
        manifest = {}
        failures.append(_failure("worker", "native_infernal_grading_worker_manifest_invalid"))
    failures = list({(r["stage"], r["code"], r["record_key"]): r
        for r in [*failures, *manifest.get("failures", [])]}.values())
    retained = []
    for field, name, schema, media_type in (
            ("sheet_artifact_ref", "sheet.json", "sheet_schema", "application/json"),
            ("scores_artifact_ref", "scores.json", "scores_schema", "application/json"),
            ("selected_rows_artifact_ref", "selected-rows.ndjson", None, "application/x-ndjson")):
        path = directory / name
        if path.is_file() and (schema is None or manifest.get(schema) is not None):
            prepared[field] = artifact_file(store, path, media_type)
        elif schema is not None and manifest.get(schema) is not None:
            failures.append(_failure("worker", "native_infernal_grading_output_missing:" + name))
    if successful_worker and prepared["selected_rows_artifact_ref"] is None:
        failures.append(_failure("worker", "native_infernal_grading_output_missing:selected-rows.ndjson"))
    for name in ("diagnostics.json", "worker.stdout", "worker.stderr", "worker-result.json"):
        path = directory / name
        if path.is_file():
            retained.append({"role": name, "artifact_ref": artifact_file(store, path)})
    prepared.update(failures=failures, numerical_complete=successful_worker
        and manifest.get("numerical_complete") is True and not failures)
    stable = {"schema": _SCHEMA_VERSION, "sheet_artifact_ref": prepared["sheet_artifact_ref"],
        "sheet_schema": manifest.get("sheet_schema"), "sheet_format": "json",
        "scores_artifact_ref": prepared["scores_artifact_ref"], "scores_schema": manifest.get("scores_schema"),
        "scores_format": "json", "captured_artifacts": custody}
    prepared["source_grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=bundle_artifact_ref, grading=stable)
    selected = {**stable, "source_grading_artifact_ref": prepared["source_grading_artifact_ref"],
        "selected_rows_artifact_ref": prepared["selected_rows_artifact_ref"],
        "selected_rows_schema": "native_infernal_selected_row_v1", "selected_rows_format": "ndjson",
        "bundle_sha256": native_infernal_digest(bundle), "selector": selector,
        "failures": failures, "numerical_complete": prepared["numerical_complete"],
        "diagnostic_artifacts": retained, "worker_receipt": receipt}
    prepared["grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=bundle_artifact_ref, grading=selected)
    _immutable(directory / "prepared.json", prepared)
    return prepared


def _subject_chunks(store, reference, start=0, end=None, reverse=False):
    """Read complete original Store symbols in bounded windows, including features."""
    row, length = store.get(reference), store.subject_length(reference)
    end = length if end is None else end
    if not 0 <= start <= end <= length:
        raise ContractError("native_infernal_subject_window_invalid")
    if row["record_type"] == "feature":
        if row["strand"] == "-":
            start, end, reverse = length - end, length - start, not reverse
        segments, cursor = [], 0
        for segment in row["segments"]:
            n = segment["end"] - segment["start"]
            a, b = max(start, cursor), min(end, cursor + n)
            if a < b:
                segments.append((segment["start"] + a - cursor, segment["start"] + b - cursor))
            cursor += n
        for a, b in reversed(segments) if reverse else segments:
            yield from _subject_chunks(store, row["subject_ref"], a, b, reverse)
        return
    path = artifact_path(store, row["sequence_ref"]) if row.get("sequence_ref") else None
    if path is None and row["record_type"] != "read_subject":
        raise ContractError("native_infernal_subject_sequence_unavailable")
    from . import materials_packing
    molecule = store.subject_molecule(reference)
    def read(a, b):
        if path is not None:
            with path.open("rb") as handle:
                handle.seek(a)
                return handle.read(b - a)
        return materials_packing.component_window(store, store.get(row["member_ref"]), "sequence", a, b - a)
    cursor = end if reverse else start
    while cursor > start if reverse else cursor < end:
        a, b = (max(start, cursor - 65536), cursor) if reverse else (cursor, min(end, cursor + 65536))
        chunk = read(a, b).decode("ascii").upper()
        if len(chunk) != b - a:
            raise ContractError("native_infernal_subject_sequence_truncated")
        if reverse:
            chunk = chunk.translate(str.maketrans("ACGTRYSWKMBDHVNU", "TGCAYRSWMKVHDBNA"))[::-1]
            if molecule == "rna":
                chunk = chunk.replace("T", "U")
        yield chunk.encode("ascii")
        cursor = a if reverse else b


def _operand(operand, *, bundle, custody):
    if (type(operand) is not dict or set(operand) != _OPERAND_FIELDS
            or operand["kind"] not in {"nucleotide_sequence", "covariance_model"}
            or type(operand["record_ordinal"]) is not int or operand["record_ordinal"] < 0
            or type(operand["length"]) is not int or operand["length"] < 1
            or type(operand["name"]) is not str or not operand["name"]
            or operand["accession"] is not None and type(operand["accession"]) is not str
            or not any(r["kind"] == "input" and r["role"] == operand["operand_role"]
                and r["artifact_ref"] == operand["artifact_ref"] for r in custody)):
        raise ContractError("native_infernal_selected_operand_identity_invalid")
    if ((operand["kind"] == "covariance_model") != (operand["operand_role"] == "models")
            or operand["operand_role"] not in {"models", "sequences", "mapali"}
            or operand["kind"] == "covariance_model" and operand["sequence_sha256"] is not None
            or operand["alphabet"] not in {"dna", "rna"}):
        raise ContractError("native_infernal_selected_operand_kind_invalid")
    matches = [b for b in bundle["operand_bindings"] if (b["operand_role"], b["record_ordinal"]) ==
        (operand["operand_role"], operand["record_ordinal"])]
    binding = operand["binding"]
    if matches:
        if (len(matches) != 1 or binding != matches[0]
                or binding["native_name"] is None and binding["native_accession"] is None
                or any(binding[b] is not None and binding[b] != operand[k]
                    for b, k in (("native_name", "name"), ("native_accession", "accession")))):
            raise ContractError("native_infernal_operand_binding_identity_mismatch")
    elif binding is not None:
        raise ContractError("native_infernal_operand_binding_not_original")
    return binding or {}


def _validate_subject(store, operand, reference, intervals, scope):
    if (operand["kind"] != "nucleotide_sequence" or type(operand["sequence_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", operand["sequence_sha256"]) is None):
        raise ContractError("native_infernal_original_sequence_operand_required")
    if store.subject_length(reference) != operand["length"]:
        raise ContractError("native_infernal_subject_length_mismatch")
    if store.subject_unit(reference) != "nt":
        raise ContractError("native_infernal_subject_unit_mismatch")
    digest = hashlib.sha256()
    for chunk in _subject_chunks(store, reference):
        digest.update(chunk)
    if digest.hexdigest() != operand["sequence_sha256"]:
        raise ContractError("native_infernal_subject_sequence_mismatch")
    if reference not in store.reference_subset([reference], scope):
        raise ContractError("native_infernal_subject_outside_scope")
    if not intervals:
        raise ContractError("native_infernal_subject_intervals_unavailable")
    seen = set()
    for interval in intervals:
        if (type(interval) is not list or len(interval) != 2 or any(type(n) is not int for n in interval)
                or not 0 <= interval[0] < interval[1] <= operand["length"] or tuple(interval) in seen):
            raise ContractError("native_infernal_subject_interval_invalid")
        seen.add(tuple(interval))
        footprint = store.map_segments(reference, [{"start": interval[0], "end": interval[1]}])
        if not footprint or not store.scope_covers(footprint, scope):
            raise ContractError("native_infernal_subject_interval_outside_scope")


def _reference(store, operand, source_ref, scope, bundle, custody):
    binding = _operand(operand, bundle=bundle, custody=custody)
    if operand["kind"] != "covariance_model":
        raise ContractError("native_infernal_covariance_model_reference_required")
    supplied = binding.get("reference_ref")
    if supplied is not None:
        row = store.get(supplied)
        if (row.get("record_type") != "reference" or row["reference_type"] != "family"
                or row["accession"] not in {operand["name"], operand["accession"]}):
            raise ContractError("native_infernal_reference_binding_identity_mismatch")
        return supplied
    accession = operand["accession"] or operand["name"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]{0,199}", accession):
        accession = identity("native_operand", {key: operand[key]
            for key in ("artifact_ref", "operand_role", "record_ordinal")})
    return store.put("reference", {"reference_type": "family", "source_ref": source_ref,
        "accession": accession, "label": operand["name"][:512], "sequence_ref": None,
        "molecule": None, "length": None, "term_refs": [], "context_refs": []},
        origin="tool", scope=scope)["id"]


def _selected(native, family, requested):
    if (type(native) is not dict or set(native) != _SELECTED_FIELDS
            or native["version"] != "native_infernal_selected_row_v1" or native["family"] != family
            or type(native["record_key"]) is not str or not native["record_key"]
            or type(native["native_ordinal"]) is not int or native["native_ordinal"] < 0
            or type(native["invalid"]) is not bool or type(native["subject_intervals"]) is not list
            or type(native["related_operands"]) is not list or native["strand"] not in {"+", "-", None}):
        raise ContractError("native_infernal_selected_row_schema_mismatch")
    names = [r["name"] for r in native["measurements"] + native["unavailable"]]
    if len(names) != len(set(names)) or set(names) != set(requested):
        raise ContractError("native_infernal_selected_metrics_mismatch")
    values = native["observation_measurements"]
    if (type(values) is not list or any(type(v) is not dict or set(v) != {"name", "value"}
            or v["name"] not in NATIVE_INFERNAL_METRICS[family] or type(v["value"]) not in (int, float)
            or not math.isfinite(v["value"]) for v in values)
            or len({v["name"] for v in values}) != len(values)):
        raise ContractError("native_infernal_observation_metrics_invalid")
    available = {v["name"]: v["value"] for v in values}
    if (any(v["name"] not in available or available[v["name"]] != v["value"] for v in native["measurements"])
            or any(v["name"] in available for v in native["unavailable"])):
        raise ContractError("native_infernal_selected_observation_values_mismatch")


def publish_selected_native_infernal_rows(store, *, source_ref, bundle, prepared, scope, selector):
    """Copy only requested retained rows; publish valid explicit physical bindings."""
    bundle = _bundle(store, bundle, prepared.get("bundle_artifact_ref"))
    selector = validate_native_infernal_result_selector(selector, program=bundle["program"])
    scope, source = store.validate_scope(scope), store.get(source_ref)
    if (source.get("record_type") != "source" or source.get("provider") != "episode.execution_result"
            or source.get("origin") != "tool" or source.get("version") != "native_infernal_bundle_v1"
            or source.get("artifact_ref") != prepared.get("bundle_artifact_ref")
            or prepared.get("source_grading_artifact_ref") not in source.get("auxiliary_artifact_refs", [])):
        raise ContractError("native_infernal_publication_source_custody_mismatch")
    grading = _grading(store, prepared, bundle, selector)
    result = {"record_refs": [source_ref], "rows": [], "failures": deepcopy(prepared["failures"])}
    if prepared["selected_rows_artifact_ref"] is None:
        return result
    projection = selector["projection"]
    family, requested, choice = projection["family"], projection["metrics"], projection["rows"]
    seen, previous = set(), -1
    with artifact_path(store, prepared["selected_rows_artifact_ref"]).open(encoding="utf-8") as stream:
        for line in stream:
            native = _decode(line)
            _selected(native, family, requested)
            key, ordinal = native["record_key"], native["native_ordinal"]
            if key in seen or ordinal <= previous:
                raise ContractError("native_infernal_selected_row_duplicate_or_reordered")
            if ("record_keys" in choice and key not in choice["record_keys"] or "offset" in choice
                    and not choice["offset"] <= ordinal < choice["offset"] + choice["limit"]):
                raise ContractError("native_infernal_selected_row_outside_selector")
            seen.add(key)
            previous = ordinal
            projected = {"record_key": key, "source_ref": source_ref, "observation_ref": None,
                "subject_ref": None, "reference_refs": [], **{field: native[field] for field in (
                    "sequence_name", "model_name", "origin", "population", "column_index", "pair_columns")},
                "strand": {"+": "plus", "-": "minus", None: None}[native["strand"]],
                "status": "invalid" if native["invalid"] else "unbound",
                "measurements": native["measurements"], "unavailable": native["unavailable"]}
            validate_schema(projected, row_schema(family))
            try:
                if native["invalid"]:
                    raise ContractError("native_infernal_invalid_native_row")
                # Models are known source entities even when a population row
                # has no physical subject. Validate explicit model bindings in
                # this case too; only observations need a target association.
                with store.transaction():
                    references = list(dict.fromkeys(_reference(store, other, source_ref, scope,
                        bundle, grading["captured_artifacts"]) for other in native["related_operands"]))
                projected["reference_refs"] = references
                result["record_refs"].extend(references)
                operand = native["subject_operand"]
                if operand is None:
                    if native["subject_intervals"]:
                        raise ContractError("native_infernal_intervals_without_subject")
                    continue_unbound = True
                else:
                    binding = _operand(operand, bundle=bundle, custody=grading["captured_artifacts"])
                    continue_unbound = binding.get("subject_ref") is None
                if not continue_unbound:
                    subject = binding["subject_ref"]
                    _validate_subject(store, operand, subject, native["subject_intervals"], scope)
                    if family in {"alignment_column", "alignment_pair"}:
                        raise ContractError("native_infernal_population_has_no_single_subject")
                    with store.transaction():
                        observation = store.put("observation", {"subject_refs": [subject],
                            "source_subject_refs": references,
                            "kind": "alignment" if family == "alignment_sequence" else "profile_match",
                            "source_ref": source_ref, "measurements": [{"name": v["name"],
                                "value": {"type": "number", "value": v["value"], "unit_ref": None}}
                                for v in native["observation_measurements"]],
                            "dependencies": list(dict.fromkeys([source_ref, subject, *references])), "anchor": None,
                            "operand_intervals": [{"role": "query", "subject_ref": subject,
                                "start": interval[0], "end": interval[1], "unit": "nt", "model_unit": "nt"}
                                for interval in native["subject_intervals"]],
                            "native_infernal": {"version": "native_infernal_observation_v1", "program": bundle["program"],
                                "family": family, "record_key": key, "bundle_artifact_ref": source["artifact_ref"]}},
                            origin="tool", scope=scope)
                    projected.update(observation_ref=observation["id"], subject_ref=subject,
                        reference_refs=references, status="published")
                    result["record_refs"].extend([*references, observation["id"]])
            except (ValueError, KeyError, TypeError, OSError) as error:
                code = str(error) if isinstance(error, ValueError) else "native_infernal_row_publication_failed"
                # Unknown physical correspondence preserves a valid unbound row.
                if code != "native_infernal_subject_intervals_unavailable":
                    projected["status"] = "invalid"
                result["failures"].append(_failure("publication", code, key))
            result["rows"].append(projected)
    if "record_keys" in choice:
        for key in choice["record_keys"]:
            if key not in seen and not any(r["stage"] == "selection" and r["record_key"] == key
                    for r in result["failures"]):
                raise ContractError("native_infernal_selected_record_missing_without_failure")
    result["record_refs"] = list(dict.fromkeys(result["record_refs"]))
    return result


__all__ = ["prepare_native_infernal_grading", "publish_selected_native_infernal_rows"]
