"""Immutable I/O boundary for the five standard database BLAST result parsers.

The calling episode selects and authenticates inputs, parameters and resources.
This worker reads those exact bytes once, calls the pure population/calculation
ports, and seals complete artifacts. It never launches BLAST or acquires data.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile

from jsonschema import Draft202012Validator, validators

from . import native_blast_standard_database_calculators as calculators
from . import native_blast_standard_database_contracts as contracts
from . import native_blast_standard_database_metadata as metadata
from . import native_blast_standard_database_result_views as views
from .blast_report_collection import parse_blast_report_collection
from .domain import validate_schema


PREFIX = views.PREFIX
_ABS = {"type": "string", "pattern": r"^/[^\x00]*$", "minLength": 1}
_FILE_ID = dict(artifact_ref=views.REF, sha256=views.SHA, size_bytes=views.I0)
_ATTEMPT = views._object(dict(identity=contracts.IDENTITY_SCHEMA, attempt_directory=_ABS, plan_sha256=views.SHA))
_MODEL = {"anyOf": [{"type": "null"}, {"type": "object", "properties": {
    "temperature_bits": {"type": "number", "exclusiveMinimum": 0},
    "function_priors": {"anyOf": [{"type": "null"}, {"type": "object", "additionalProperties": {"type": "number", "minimum": 0}}]}},
    "additionalProperties": False}]}
_DESCRIPTOR = views._object(dict(input_key=views.TOKEN, consumer={"enum": ["query_identity", "sequence_database"]},
    schema_id={"enum": ["native_blast_database_query_metadata_v1", "native_blast_database_sequence_metadata_v1"]},
    **_FILE_ID, origin={"enum": ["original_job_input", "selected_results_input"]}))
_SNAPSHOT = dict(subject_ref=views.REF, record_type={"enum": ["input", "feature", "product", "read_subject"]},
    molecule={"enum": ["dna", "rna", "protein"]}, length={"type": "integer", "minimum": 1},
    sequence_sha256=views.SHA, sequence_artifact_ref=views.REF)
_ROLES = {"inputs": ("inputs.json", metadata.PREPARED_INPUTS_SCHEMA),
    "collection": ("collection.json", "blast_report_collection_v1"), "sheets": ("sheets.json", metadata.SHEET_SET_SCHEMA),
    "calculations": ("calculations.json", calculators.CALCULATION_SCHEMA),
    "rows": ("rows.ndjson", PREFIX + "numeric_row_v1"), "row_index": ("row-index.json", PREFIX + "row_index_v1"),
    "metric_definitions": ("metric-definitions.json", PREFIX + "metric_definitions_v1"),
    "diagnostics": ("diagnostics.json", PREFIX + "diagnostics_v1")}

STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA = views._object(dict(
    version={"const": PREFIX + "result_worker_request_v1"}, calculation_id=views.SHA,
    bundle=contracts.NATIVE_BLAST_STANDARD_DATABASE_BUNDLE_SCHEMA, bundle_artifact_ref=views.REF,
    bundle_capture=views._object(dict(path=_ABS, sha256=views.SHA, size_bytes=views.I0)),
    authenticated_attempt=_ATTEMPT,
    artifacts=views._array(views._object(dict(artifact_key=views.TOKEN, path=_ABS, **_FILE_ID))),
    metadata_descriptors=views._array(_DESCRIPTOR), retained_sources=views._array(views._object(dict(source_ref=views.REF, path=_ABS, **_FILE_ID))),
    subject_snapshots=views._array(views._object(dict(**_SNAPSHOT, sequence_path=_ABS))),
    implementation=views._object(dict(manifest_sha256=views.SHA, files=views._array(views._object(dict(module=views.TOKEN, path=_ABS, sha256=views.SHA)), minItems=1))),
    sequence_model=_MODEL, output_directory=_ABS, reuse=views._nullable(views._object(dict(
        manifest_path=_ABS, manifest_sha256=views.SHA, manifest_size_bytes=views.I0, collection_path=_ABS, sheets_path=_ABS)))))
STANDARD_BLAST_DATABASE_WORKER_MANIFEST_SCHEMA = views._object(dict(
    version={"const": PREFIX + "result_worker_manifest_v1"}, calculation_id=views.SHA, request_sha256=views.SHA,
    status={"enum": ["complete", "partial", "failed"]}, input_identity=views.SHA, input_interpretation_id=views.SHA,
    input_implementation_sha256=views.SHA, implementation_manifest_sha256=views.SHA, sequence_model=_MODEL,
    artifacts=views._array(views._object(dict(role={"enum": list(_ROLES)}, relative_path=views.TOKEN,
        sha256=views.SHA, size_bytes=views.I0, schema=views.TOKEN))),
    counts=views._object(dict(searches=views.I0, native_hsp_slots=views.I0, numerical_rows=views.I0)),
    failures=views._array(views.FAILURE_SCHEMA)))
_StrictValidator = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda checker, value: type(value) is int))


def _shape(value, schema):
    validate_schema(value, schema)
    _StrictValidator(schema).validate(value)
    return value


def _absolute_path(value):
    if type(value) is not str or not value.startswith("/") or "\x00" in value or ".." in value.split("/"):
        raise ValueError(PREFIX + "absolute_path_required")
    return value


def standard_blast_database_implementation_identity(files: list[dict]) -> str:
    """Hash actual named implementation identities, independent of local paths."""
    files = views._copy(files)
    if type(files) is not list or not files:
        raise ValueError(PREFIX + "implementation_files_required")
    projected = []
    for row in files:
        if type(row) is not dict or set(row) not in ({"module", "sha256"}, {"module", "path", "sha256"}):
            raise ValueError(PREFIX + "implementation_file_invalid")
        projected.append(_shape({k: row[k] for k in ("module", "sha256")}, views._object(dict(module=views.TOKEN, sha256=views.SHA))))
        if "path" in row: _absolute_path(row["path"])
    if len({r["module"] for r in projected}) != len(projected):
        raise ValueError(PREFIX + "implementation_module_duplicate")
    return views._hash(dict(version=PREFIX + "implementation_identity_v1", files=sorted(projected, key=lambda r: r["module"])))


def standard_blast_database_input_identity(request: dict) -> str:
    """Hash selected inputs and original attempt, without local capture paths."""
    request = views._copy(request)
    value = dict(version=PREFIX + "input_identity_v1",
        bundle=dict(artifact_ref=request["bundle_artifact_ref"], **{k: request["bundle_capture"][k] for k in ("sha256", "size_bytes")}),
        authenticated_attempt=request["authenticated_attempt"],
        artifacts=[{k: r[k] for k in ("artifact_key", *_FILE_ID)} for r in request["artifacts"]],
        metadata_descriptors=request["metadata_descriptors"],
        retained_sources=[{k: r[k] for k in ("source_ref", *_FILE_ID)} for r in request["retained_sources"]],
        subject_snapshots=[{k: r[k] for k in _SNAPSHOT} for r in request["subject_snapshots"]])
    _shape(value, views._object(dict(version={"const": PREFIX + "input_identity_v1"}, bundle=views._object(_FILE_ID),
        authenticated_attempt=_ATTEMPT, artifacts=views._array(views._object(dict(artifact_key=views.TOKEN, **_FILE_ID))),
        metadata_descriptors=views._array(_DESCRIPTOR), retained_sources=views._array(views._object(dict(source_ref=views.REF, **_FILE_ID))),
        subject_snapshots=views._array(views._object(_SNAPSHOT)))))
    _absolute_path(value["authenticated_attempt"]["attempt_directory"])
    return views._hash(value)


def standard_blast_database_calculation_identity(*, input_identity: str, input_implementation_sha256: str,
        sequence_model: dict | None, implementation_manifest_sha256: str) -> dict:
    for digest in (input_identity, input_implementation_sha256, implementation_manifest_sha256): _shape(digest, views.SHA)
    model = calculators.validate_sequence_model(sequence_model)
    interpretation = views._hash(dict(version=PREFIX + "interpretation_identity_v1",
        input_identity=input_identity, input_implementation_sha256=input_implementation_sha256))
    return dict(input_interpretation_id=interpretation, calculation_id=views._hash(dict(version=PREFIX + "calculation_identity_v1",
        input_interpretation_id=interpretation, sequence_model=model, implementation_manifest_sha256=implementation_manifest_sha256)))


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError(PREFIX + "duplicate_json_key")
            result[key] = value
        return result
    def nonfinite(value): raise ValueError(PREFIX + "finite_json_required")
    return views._copy(json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite))


def _json_bytes(value):
    return (json.dumps(views._copy(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode()


class _WorkerFailure(Exception):
    def __init__(self, stage, code, detail, *, pointer="", artifact_key=None, input_key=None, search_key=None):
        self.failure = dict(stage=stage, code=PREFIX + code, detail_code=detail, pointer=pointer,
            artifact_key=artifact_key, input_key=input_key, search_key=search_key, record_key=None)
        super().__init__(self.failure["code"])


def _verified_bytes(path, sha256, size_bytes, *, frozen=False, pointer="", artifact_key=None):
    try: raw = Path(_absolute_path(path)).read_bytes()
    except OSError as error:
        raise _WorkerFailure("capture", "artifact_missing", "artifact_bytes_unavailable", pointer=pointer, artifact_key=artifact_key) from error
    if len(raw) != size_bytes or hashlib.sha256(raw).hexdigest() != sha256:
        raise _WorkerFailure("capture", "frozen_artifact_changed" if frozen else "artifact_identity_mismatch",
            "frozen_value_changed" if frozen else "artifact_digest_conflict", pointer=pointer, artifact_key=artifact_key)
    return raw


_DEPENDENCY_ROOTS = {"Bio", "numpy", "jsonschema", "jsonschema_specifications", "referencing", "rpds", "attr", "attrs"}
_PROJECT_MODULES = tuple("native_blast_standard_database_result_worker native_blast_standard_database_result_views native_blast_standard_database_calculators native_blast_standard_database_metadata native_blast_standard_database_contracts native_blast_database_result_worker native_blast_database_result_views native_blast_database_metadata native_blast_database_contracts blast_report_collection blast_grading_inputs blast_program_context blast_sequence_database blast_database_grader blast_pairwise_grader blast_profile_inputs blast_profile_calculators blast_pssm_inputs blast_pssm_calculators blast_pssm_master_inputs blast_iteration_inputs blast_iteration_calculators blast_vdb_inputs blast_vdb_calculators blast_search domain".split())


def _implementation_modules():
    """Actual imported parser/calculator closure for caller-created inventories."""
    names = ["gene_annotation_episode." + name for name in _PROJECT_MODULES]
    for name in names: importlib.import_module(name)
    names += [name for name, module in tuple(sys.modules.items()) if name.split(".")[0] in _DEPENDENCY_ROOTS and getattr(module, "__file__", None)]
    return {name: sys.modules[name] for name in sorted(set(names + ["gene_annotation_episode"]))}


def _verify_implementation(implementation):
    if standard_blast_database_implementation_identity(implementation["files"]) != implementation["manifest_sha256"]:
        raise _WorkerFailure("worker", "artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/manifest_sha256")
    files = {r["module"]: r for r in implementation["files"]}
    for name in files:
        if name not in sys.modules and name.split(".")[0] in _DEPENDENCY_ROOTS: importlib.import_module(name)
    modules = _implementation_modules()
    if not set(modules) <= set(files):
        raise _WorkerFailure("worker", "artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
    for name, row in files.items():
        path = getattr(sys.modules.get(name), "__file__", None)
        if path is None or Path(path).resolve() != Path(row["path"]).resolve():
            raise _WorkerFailure("worker", "artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
        _verified_bytes(row["path"], row["sha256"], Path(row["path"]).stat().st_size, pointer="/implementation/files")


def _atomic_bytes(directory, filename, raw):
    destination = directory / filename
    if destination.exists(): raise FileExistsError(PREFIX + "generation_immutable")
    descriptor, temporary = tempfile.mkstemp(prefix="." + filename + ".", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally: Path(temporary).unlink(missing_ok=True)
    return dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _catalog(request, failures):
    originals = {r["artifact_key"]: r for r in request["bundle"]["artifacts"]}
    entries, contents, collector_contents = [], {}, {}
    if len({r["artifact_key"] for r in request["artifacts"]}) != len(request["artifacts"]):
        raise _WorkerFailure("capture", "artifact_identity_mismatch", "artifact_digest_conflict", pointer="/artifacts")
    identities = {}
    for group, records in (("artifacts", request["artifacts"]), ("retained_sources", request["retained_sources"])):
        for index, row in enumerate(records):
            pointer = f"/{group}/{index}"
            key = row.get("artifact_key")
            if group == "artifacts":
                original = originals.get(key)
                if original is None or any(row[k] != original[k] for k in ("sha256", "size_bytes")):
                    raise _WorkerFailure("capture", "artifact_identity_mismatch", "artifact_digest_conflict", pointer=pointer, artifact_key=key)
                entries.append(dict(original, **row, source_ref=row["artifact_ref"]))
            signature = row["sha256"], row["size_bytes"]
            if row["artifact_ref"] in identities and identities[row["artifact_ref"]] != signature:
                raise _WorkerFailure("capture", "artifact_identity_mismatch", "artifact_digest_conflict", pointer=pointer, artifact_key=key)
            identities[row["artifact_ref"]] = signature
            try:
                raw = _verified_bytes(row["path"], *signature, pointer=pointer, artifact_key=key, frozen=request["reuse"] is not None)
                contents[row["artifact_ref"]] = raw
                if key is not None: collector_contents[key] = raw
            except _WorkerFailure as error: failures.append(error.failure)
    for key in originals.keys() - {r["artifact_key"] for r in entries}:
        failures.append(_WorkerFailure("capture", "artifact_missing", "artifact_bytes_unavailable", artifact_key=key, pointer="/artifacts").failure)
    if len({r["source_ref"] for r in request["retained_sources"]}) != len(request["retained_sources"]):
        raise _WorkerFailure("capture", "artifact_identity_mismatch", "artifact_digest_conflict", pointer="/retained_sources")
    return dict(bundle_source_ref=request["bundle_artifact_ref"], bundle_artifact_ref=request["bundle_artifact_ref"],
        bundle_sha256=request["bundle_capture"]["sha256"], entries=entries, retained_sources=deepcopy(request["retained_sources"])), contents, collector_contents


def _metadata_payloads(request, catalog, contents, failures):
    job = request["bundle"]["requested_job"]["native_blast_standard_database"]
    descriptors = request["metadata_descriptors"]
    if len({(r["input_key"], r["consumer"], r["schema_id"]) for r in descriptors}) != len(descriptors):
        raise _WorkerFailure("metadata", "metadata_payload_invalid", "metadata_shape_invalid", pointer="/metadata_descriptors")
    original = [r for r in descriptors if r["origin"] == "original_job_input"]
    if descriptors[:len(original)] != original or [{k: r[k] for k in ("input_key", "consumer", "schema_id")} for r in original] != job["metadata_inputs"]:
        raise _WorkerFailure("metadata", "metadata_payload_invalid", "metadata_shape_invalid", pointer="/metadata_descriptors")
    identities, payloads = {}, []
    for index, descriptor in enumerate(descriptors):
        pointer = f"/metadata_descriptors/{index}"
        signature = tuple(descriptor[k] for k in _FILE_ID)
        if descriptor["input_key"] in identities and identities[descriptor["input_key"]] != signature:
            raise _WorkerFailure("metadata", "artifact_identity_mismatch", "artifact_digest_conflict", pointer=pointer, input_key=descriptor["input_key"])
        identities[descriptor["input_key"]] = signature
        selected = [r for r in job["inputs"] if r["input_key"] == descriptor["input_key"]]
        candidates = [r for r in catalog["entries"] + catalog["retained_sources"] if r["artifact_ref"] == descriptor["artifact_ref"]]
        if any(tuple(r[k] for k in _FILE_ID) != signature for r in candidates) or selected and (selected[0]["role"] != "metadata" or
                not any(r.get("input_key") == descriptor["input_key"] for r in candidates)):
            raise _WorkerFailure("metadata", "artifact_identity_mismatch", "artifact_digest_conflict", pointer=pointer, input_key=descriptor["input_key"])
        payload = None
        if not candidates or descriptor["artifact_ref"] not in contents:
            failures.append(_WorkerFailure("metadata", "metadata_source_unavailable", "metadata_address_unresolved", pointer=pointer, input_key=descriptor["input_key"]).failure)
        else:
            try: payload = _decode(contents[descriptor["artifact_ref"]])
            except (ValueError, UnicodeError):
                failures.append(_WorkerFailure("metadata", "metadata_payload_invalid", "metadata_shape_invalid", pointer=pointer, input_key=descriptor["input_key"]).failure)
        payloads.append(dict(descriptor=deepcopy(descriptor), payload=payload))
    return payloads


def _subjects(request, failures):
    contents, identities = {}, {}
    for index, row in enumerate(request["subject_snapshots"]):
        key = row["sequence_artifact_ref"]
        signature = row["sequence_sha256"], row["length"]
        if key in identities and identities[key] != signature:
            raise _WorkerFailure("inputs", "artifact_identity_mismatch", "artifact_digest_conflict", pointer=f"/subject_snapshots/{index}")
        identities[key] = signature
        try: contents[key] = _verified_bytes(row["sequence_path"], *signature, frozen=request["reuse"] is not None, pointer=f"/subject_snapshots/{index}")
        except _WorkerFailure as error: failures.append(error.failure)
    return contents


def _reuse(request, input_identity, catalog, contents, subject_contents):
    reused = request["reuse"]
    manifest = _decode(_verified_bytes(reused["manifest_path"], reused["manifest_sha256"], reused["manifest_size_bytes"], frozen=True, pointer="/reuse/manifest_path"))
    _shape(manifest, STANDARD_BLAST_DATABASE_WORKER_MANIFEST_SCHEMA)
    ids = standard_blast_database_calculation_identity(input_identity=manifest["input_identity"],
        input_implementation_sha256=manifest["input_implementation_sha256"], sequence_model=manifest["sequence_model"],
        implementation_manifest_sha256=manifest["implementation_manifest_sha256"])
    if manifest["status"] == "failed" or manifest["input_identity"] != input_identity or any(manifest[k] != v for k, v in ids.items()):
        raise _WorkerFailure("inputs", "frozen_artifact_changed", "frozen_value_changed", pointer="/reuse")
    artifacts = {r["role"]: r for r in manifest["artifacts"]}
    if set(artifacts) != set(_ROLES) or len(artifacts) != len(manifest["artifacts"]):
        raise _WorkerFailure("inputs", "sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
    values = {}
    for role, artifact in artifacts.items():
        if (artifact["relative_path"], artifact["schema"]) != _ROLES[role]:
            raise _WorkerFailure("inputs", "sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
        path = reused[role + "_path"] if role in {"collection", "sheets"} else str(Path(reused["manifest_path"]).parent / artifact["relative_path"])
        raw = _verified_bytes(path, artifact["sha256"], artifact["size_bytes"], frozen=True, pointer="/reuse/" + role)
        if role in {"inputs", "collection", "sheets"}: values[role] = _decode(raw)
    sheets = metadata.validate_standard_blast_database_sheet_set(values["sheets"])
    prepared = sheets["prepared_inputs"]
    if sheets["collection"] != values["collection"] or prepared != values["inputs"]:
        raise _WorkerFailure("inputs", "sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
    attempts = [r["value"] for r in prepared["source_relations"] if r["kind"] == "attempt"]
    expected = dict(bundle=request["bundle"], attempt_identity=request["authenticated_attempt"],
        **{k: catalog[k] for k in ("bundle_source_ref", "bundle_artifact_ref", "bundle_sha256")})
    if attempts != [expected]: raise _WorkerFailure("inputs", "frozen_artifact_changed", "frozen_value_changed", pointer="/reuse/attempt")
    documents = prepared["resolved_documents"]
    if [(r["kind"], {k: v for k, v in r["catalog"].items() if k != "path"}) for r in documents] != [
            (kind, {k: v for k, v in r.items() if k != "path"}) for kind, rows in (("captured", catalog["entries"]), ("received", catalog["retained_sources"])) for r in rows]:
        raise _WorkerFailure("inputs", "frozen_artifact_changed", "frozen_value_changed", pointer="/reuse/inputs")
    for row in documents:
        raw = contents.get(row["catalog"]["artifact_ref"])
        if row["status"] == "available" and (raw is None or raw.hex() != row["contents_hex"]):
            raise _WorkerFailure("inputs", "frozen_artifact_changed", "frozen_value_changed", pointer="/reuse/inputs")
    for relation in prepared["source_relations"]:
        if relation["kind"] == "subject" and relation["status"] == "available":
            value, snapshot = relation["value"], relation["value"]["snapshot"]
            candidates = [r for r in request["subject_snapshots"] if r["subject_ref"] == snapshot["subject_ref"]]
            if len(candidates) != 1 or any(candidates[0][k] != snapshot[k] for k in _SNAPSHOT) or subject_contents.get(snapshot["sequence_artifact_ref"]) != value["sequence"].encode():
                raise _WorkerFailure("inputs", "frozen_artifact_changed", "frozen_value_changed", pointer="/reuse/subjects")
    return values["collection"], sheets, manifest["input_implementation_sha256"]


def _metadata_failures(issues):
    details = {"schema_unsupported": "metadata_tuple_unregistered", "payload_invalid": "metadata_shape_invalid",
        "source_unavailable": "metadata_address_unresolved", "relation_unresolved": "metadata_address_unresolved",
        "relation_conflict": "metadata_relation_conflict", "extractor_unbound": "extractor_not_registered"}
    result = []
    for index, issue in enumerate(issues):
        raw = issue["code"]
        code = "metadata_" + raw.removeprefix("native_blast_metadata_") if raw.startswith("native_blast_metadata_") else raw.removeprefix(PREFIX)
        if PREFIX + code not in views.FAILURE_CODES:
            code = "metadata_relation_unresolved"
        detail = details.get(code.removeprefix("metadata_"), {"artifact_missing": "artifact_bytes_unavailable",
            "artifact_identity_mismatch": "artifact_digest_conflict", "query_unbound": "query_identity_unresolved"}.get(code, "metadata_address_unresolved"))
        descriptor = issue.get("descriptor") or {}
        result.append(_WorkerFailure("metadata", code, detail, pointer=f"/sheets/issues/{index}",
            input_key=issue.get("input_key", descriptor.get("input_key")), search_key=issue.get("search_key")).failure)
    return result


_NATIVE_ROW_ERRORS = frozenset("""blast_hit_array_invalid blast_hit_array_not_reported blast_hit_object_required
    blast_hsp_object_required blast_hsp_array_invalid blast_hsp_field_invalid blast_description_object_required
    blast_description_field_invalid blast_query_id_invalid blast_query_length_invalid blast_query_title_invalid
    blast_reference_length_invalid blast_database_text_invalid blast_search_target_object_invalid
    blast_pairwise_database_mode_conflict blast_tabular_column_count_invalid blast_tabular_declared_fields_conflict
    blast_tabular_empty_without_zero_hit_report blast_tabular_fields_required blast_tabular_fields_unavailable_or_conflicting
    blast_tabular_frames_invalid blast_tabular_hit_count_conflict blast_tabular_number_invalid
    blast_tabular_query_identifier_required blast_tabular_query_identity_conflict blast_tabular_query_length_conflict
    blast_tabular_reference_length_conflict blast_tabular_reported_row_count_mismatch""".split())


def _collection_failures(collection):
    failures = [_WorkerFailure("collection", "report_unreadable", "native_syntax_invalid", artifact_key=issue.get("artifact_key"),
        pointer=f"/collection/issues/{i}").failure for i, issue in enumerate(collection["issues"])]
    for si, search in enumerate(collection["searches"]):
        for ii, issue in enumerate(search["issues"]):
            if issue["code"] in _NATIVE_ROW_ERRORS:
                failures.append(_WorkerFailure("collection", "report_unreadable", "native_row_invalid", search_key=search["search_key"],
                    artifact_key=search["search_key"]["artifact_key"], pointer=f"/collection/searches/{si}/issues/{ii}").failure)
    return failures


def run_standard_blast_database_result_worker(request_path: str) -> dict:
    """Run one caller-resourced interpretation/calculation, without private retries."""
    request_bytes = Path(_absolute_path(str(request_path))).read_bytes()
    request = _decode(request_bytes)
    calculators.validate_sequence_model(request.get("sequence_model"))
    _shape(request, STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA)
    directory = Path(_absolute_path(request["output_directory"]))
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()): raise FileExistsError(PREFIX + "generation_directory_not_empty")
    input_id = standard_blast_database_input_identity(request)
    input_impl = request["implementation"]["manifest_sha256"]
    initial = standard_blast_database_calculation_identity(input_identity=input_id, input_implementation_sha256=input_impl,
        sequence_model=request["sequence_model"], implementation_manifest_sha256=input_impl)
    manifest = dict(version=PREFIX + "result_worker_manifest_v1", calculation_id=request["calculation_id"],
        request_sha256=hashlib.sha256(request_bytes).hexdigest(), status="failed", input_identity=input_id,
        input_interpretation_id=initial["input_interpretation_id"], input_implementation_sha256=input_impl,
        implementation_manifest_sha256=input_impl, sequence_model=deepcopy(request["sequence_model"]), artifacts=[],
        counts=dict(searches=0, native_hsp_slots=0, numerical_rows=0), failures=[])
    failures, errors, metadata_issues = manifest["failures"], [], []
    stage = "capture"
    def save(role, value):
        filename, schema = _ROLES[role]
        record = _atomic_bytes(directory, filename, _json_bytes(value))
        manifest["artifacts"].append(dict(role=role, relative_path=filename, schema=schema, **record))
    try:
        if _decode(_verified_bytes(**request["bundle_capture"], pointer="/bundle_capture", frozen=request["reuse"] is not None)) != request["bundle"]:
            raise _WorkerFailure("capture", "artifact_identity_mismatch", "artifact_digest_conflict", pointer="/bundle_capture")
        try:
            bundle = contracts.validate_standard_blast_database_bundle(request["bundle"],
                original_job=request["bundle"]["requested_job"]["native_blast_standard_database"], attempt_identity=request["authenticated_attempt"])
        except ValueError as error:
            raise _WorkerFailure("capture", "artifact_identity_mismatch", "attempt_identity_conflict", pointer="/authenticated_attempt") from error
        _verify_implementation(request["implementation"])
        catalog, contents, collector_contents = _catalog(request, failures)
        subject_contents = _subjects(request, failures)
        for i, issue in enumerate(bundle["failures"]):
            failures.append(_WorkerFailure("capture", "capture_incomplete", "artifact_bytes_unavailable",
                artifact_key=issue["artifact_key"], input_key=issue["input_key"], pointer=f"/bundle/failures/{i}").failure)
        stage = "inputs"
        if request["reuse"] is not None:
            if any(f["stage"] == "capture" for f in failures):
                raise _WorkerFailure("inputs", "frozen_artifact_changed", "frozen_value_changed", pointer="/reuse/original_inputs")
            collection, sheets, input_impl = _reuse(request, input_id, catalog, contents, subject_contents)
            prepared = sheets["prepared_inputs"]
        else:
            payloads = _metadata_payloads(request, catalog, contents, failures)
            prepared = metadata.prepare_standard_blast_database_inputs(job=bundle["requested_job"]["native_blast_standard_database"],
                bundle=bundle, attempt_identity=request["authenticated_attempt"], artifact_catalog=catalog, contents=contents,
                metadata_payloads=payloads, subject_snapshots=request["subject_snapshots"], subject_contents=subject_contents)
            metadata.validate_standard_blast_database_prepared_inputs(prepared)
            save("inputs", prepared)
            stage = "collection"
            roles = {"primary_report": "primary_report", "stdout": "native_log", "stderr": "native_log", "query_pssm": "query_pssm"}
            records = [r for r in catalog["entries"] if r["role"] in roles and r["artifact_key"] in collector_contents]
            descriptors = [dict(artifact_key=r["artifact_key"], role=roles[r["role"]], format=r["format"],
                fields=None if r["format"] == "json15" else r["fields"], delimiter=r["delimiter"]) for r in records]
            collection = parse_blast_report_collection({r["artifact_key"]: collector_contents[r["artifact_key"]] for r in records},
                artifacts=descriptors, invocation=prepared["invocation"])
            save("collection", collection)
            stage = "population"
            sheets = metadata.populate_standard_blast_database_sheets(collection, prepared_inputs=prepared)
            metadata.validate_standard_blast_database_sheet_set(sheets)
            save("sheets", sheets)
        ids = standard_blast_database_calculation_identity(input_identity=input_id, input_implementation_sha256=input_impl,
            sequence_model=request["sequence_model"], implementation_manifest_sha256=request["implementation"]["manifest_sha256"])
        manifest.update(input_implementation_sha256=input_impl, input_interpretation_id=ids["input_interpretation_id"])
        if ids["calculation_id"] != request["calculation_id"]:
            raise _WorkerFailure("inputs", "artifact_identity_mismatch", "artifact_digest_conflict", pointer="/calculation_id")
        if request["reuse"] is not None:
            save("inputs", prepared); save("collection", collection); save("sheets", sheets)
        metadata_issues.extend(sheets["issues"])
        failures.extend(_metadata_failures(metadata_issues))
        failures.extend(_collection_failures(collection))
        manifest["counts"]["searches"] = len(collection["searches"])
        stage = "calculation"
        calculation_errors = []
        calculations = calculators._calculate(sheets, sequence_model=request["sequence_model"], diagnostics=calculation_errors)
        save("calculations", calculations)
        offset = len(failures)
        failures.extend(calculations["issues"])
        errors.extend(dict(failure_index=offset + row["issue_index"], exception_type=row["exception_type"], message=row["message"]) for row in calculation_errors)
        manifest["counts"]["native_hsp_slots"] = len(calculations["native_hsp_components"])
        stage = "rows"
        rows = calculators.build_standard_blast_database_rows(bundle_identity=bundle["identity"], calculation_id=request["calculation_id"], sheet_set=sheets, calculations=calculations)
        chunks, index, position = [], [], 0
        for ordinal, row in enumerate(rows):
            raw = _json_bytes(row)
            chunks.append(raw)
            index.append(dict(family=row["family"], record_key=row["record_key"], ordinal=ordinal, byte_start=position, byte_end=position + len(raw)))
            position += len(raw)
        record = _atomic_bytes(directory, "rows.ndjson", b"".join(chunks))
        manifest["artifacts"].append(dict(role="rows", relative_path="rows.ndjson", schema=_ROLES["rows"][1], **record))
        save("row_index", dict(schema=PREFIX + "row_index_v1", calculation_id=request["calculation_id"], rows=index))
        manifest["counts"]["numerical_rows"] = len(rows)
        save("metric_definitions", views.standard_blast_database_metric_definitions())
        _verify_implementation(request["implementation"])
        manifest["status"] = "partial" if failures else "complete"
    except _WorkerFailure as error:
        failures.append(error.failure)
        if error.__cause__ is not None:
            cause = error.__cause__
            errors.append(dict(failure_index=len(failures) - 1, exception_type=type(cause).__module__ + "." + type(cause).__qualname__, message=str(cause)))
    except Exception as error:
        resource = isinstance(error, MemoryError) or isinstance(error, OSError) and error.errno in (12, 27, 28, 122)
        code = "worker_resource_limit" if resource else "sheet_invalid" if stage in {"inputs", "population"} else "calculation_failed" if stage == "calculation" else "worker_failed"
        detail = "resource_limit" if resource else "calculator_contract_invalid" if stage in {"inputs", "population", "calculation"} else "implementation_failure"
        failures.append(_WorkerFailure("worker" if resource else stage, code, detail).failure)
        errors.append(dict(failure_index=len(failures) - 1, exception_type=type(error).__module__ + "." + type(error).__qualname__, message=str(error)))
    save("diagnostics", dict(schema=PREFIX + "diagnostics_v1", failures=failures, metadata_issues=metadata_issues, exceptions=errors))
    _shape(manifest, STANDARD_BLAST_DATABASE_WORKER_MANIFEST_SCHEMA)
    _atomic_bytes(directory, "worker-manifest.json", _json_bytes(manifest))
    return views._copy(manifest)


if __name__ == "__main__":
    result = run_standard_blast_database_result_worker(sys.argv[1])
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


__all__ = ["standard_blast_database_implementation_identity", "standard_blast_database_input_identity",
    "standard_blast_database_calculation_identity", "run_standard_blast_database_result_worker",
    "STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA", "STANDARD_BLAST_DATABASE_WORKER_MANIFEST_SCHEMA"]
