"""Deterministic database BLAST calculations and a separate bounded I/O entry.

The pure ports consume detached supplied sheets. PSI/DELTA use the iteration
calculator once; other modes use their own scientific population. Raw reported
HSP axes are calculated independently and never substituted for full axes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

from gene_annotation_episode.episodic_workflow.root.a101.library import blast_iteration_calculators as _iteration
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_profile_calculators as _profile
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_pssm_calculators as _pssm
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_vdb_calculators as _vdb
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_grader import alignment_components
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_program_context import resolve_blast_program_context
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_fasta_record_identity import blast_record_identity
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_report_collection import parse_blast_report_collection
from .domain import ContractError, canonical, identity, validate_schema
from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_database_result_views as _views
from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_database_contracts as _contracts
from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_worker_values import _ABS, _ATTEMPT, _FILE_ID, _FUNCTION_CALCULATIONS, _FUNCTION_REQUEST, _FUNCTION_SHEETS, _SNAPSHOT_ID, _absolute_path, _at, _descriptor, _model, _shape, _sheet_binding, build_native_blast_database_rows, calculate_native_blast_database_sheets, native_blast_database_calculation_identity, native_blast_database_implementation_identity, native_blast_database_input_identity


_FUNCTION_MANIFEST = "native_blast_database_result_worker_manifest_vdb_function_v1"




















_MODEL = {"anyOf": [{"type": "null"}, {"type": "object", "properties": {
    "temperature_bits": {"type": "number", "exclusiveMinimum": 0},
    "function_priors": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0}}}, "additionalProperties": False}]}






















def _population_capture_binding(sheet_set, request, catalog):
    """Tie v3 retained JSON facts to the caller's original captured bytes.

    This is worker custody validation, separate from the pure saved metadata
    validator. JSON decoding checks original source values; no native parser,
    metadata extraction/population or scientific calculator runs here.
    """
    from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_population_metadata import SEQUENCE_POPULATION_METADATA_SCHEMA
    validations = [v for v in sheet_set["prepared_inputs"]["metadata"]
        if v["schema_id"] == SEQUENCE_POPULATION_METADATA_SCHEMA]
    selected = [d for d in request["metadata_descriptors"] if d["schema_id"] == SEQUENCE_POPULATION_METADATA_SCHEMA]
    fields = ("consumer", "schema_id", "input_key", "artifact_ref", "sha256")
    if ([{k: v[k] for k in fields} for v in validations] != [{k: d[k] for k in fields} for d in selected]
            or any("descriptor" in v and v["descriptor"] != d for v, d in zip(validations, selected))):
        raise ValueError("blast_database_population_saved_relation_conflict")
    if not validations:
        return
    # Native envelopes retain the five fields above; the sealed request retains
    # full descriptors, including byte counts and original/selected origin. The
    # existing reuse input identity authenticates those full original values.
    bundle = request["bundle"]
    if sheet_set["prepared_inputs"]["invocation"]["request"] != bundle["requested_job"]:
        raise ValueError("blast_database_population_saved_relation_conflict")
    root = dict(source_ref=catalog["bundle_source_ref"], artifact_ref=catalog["bundle_artifact_ref"],
        sha256=request["bundle_capture"]["sha256"], size_bytes=request["bundle_capture"]["size_bytes"],
        pointer="", value=bundle)
    records = {canonical(r): r for v in validations for r in v["population_source_records"]}
    if canonical(root) not in records:
        raise ValueError("blast_database_population_saved_relation_conflict")
    entries = catalog["entries"] + catalog["retained_sources"]
    checked = {}
    # A saved interpretation cannot erase an original available manifest and
    # then call the selected database unavailable. Preserve partial captures:
    # an absent or malformed original document supplies no JSON root.
    manifest_keys = {r["manifest_artifact_key"] for r in bundle["database_manifest"]
        if r.get("manifest_artifact_key") is not None}
    for entry in catalog["entries"]:
        if entry["artifact_key"] not in manifest_keys or entry["role"] != "database_manifest":
            continue
        try:
            raw = _verified_bytes(entry["path"], entry["sha256"], entry["size_bytes"],
                frozen=request["reuse"] is not None, pointer="/population_source_records")
        except _WorkerFailure:
            if request["reuse"] is not None:
                raise
            continue
        try:
            value = _decode(raw)
        except (ValueError, UnicodeError):
            continue
        original = dict(**{k: entry[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")},
            pointer="", value=value)
        if canonical(original) not in records:
            raise ValueError("blast_database_population_saved_relation_conflict")
        checked[tuple(entry[k] for k in ("artifact_ref", "sha256", "size_bytes"))] = value
    for record in records.values():
        if record["artifact_ref"] == root["artifact_ref"]:
            if canonical(record) != canonical(root):
                raise ValueError("blast_database_population_saved_relation_conflict")
            continue
        matches = [r for r in entries if all(r[k] == record[k]
            for k in ("source_ref", "artifact_ref", "sha256", "size_bytes"))]
        if not matches:
            raise ValueError("blast_database_population_saved_relation_conflict")
        key = tuple(record[k] for k in ("artifact_ref", "sha256", "size_bytes"))
        if key not in checked:
            entry = matches[0]
            checked[key] = _decode(_verified_bytes(entry["path"], entry["sha256"], entry["size_bytes"],
                frozen=request["reuse"] is not None, pointer="/population_source_records"))
        if canonical(_at(checked[key], record["pointer"])) != canonical(record["value"]):
            raise ValueError("blast_database_population_saved_relation_conflict")
    bykey = {r["artifact_key"]: r for r in catalog["entries"]}
    for row in sheet_set["sequence"]:
        scientific = row["sheet"]
        if scientific["schema"] != "blast_sequence_database_result_sheet_v3":
            continue
        report = bykey.get(row["search_key"]["artifact_key"])
        source = scientific["report_source"]
        if (report is None or source.get("source_ref") != report["source_ref"]
                or source["artifact_ref"] != report["artifact_ref"]
                or scientific["search"]["normalized"]["native"]["sha256"] != report["sha256"]):
            raise ValueError("blast_database_population_saved_relation_conflict")
































_ARTIFACT_ROLES = {"inputs": ("inputs.json", "native_blast_database_prepared_inputs_v1"),
    "collection": ("collection.json", "blast_report_collection_v1"), "sheets": ("sheets.json", "native_blast_database_sheet_set_v1"),
    "calculations": ("calculations.json", "native_blast_database_calculations_v1"),
    "rows": ("rows.ndjson", "native_blast_database_numeric_row_v1"), "row_index": ("row-index.json", "native_blast_database_row_index_v1"),
    "metric_definitions": ("metric-definitions.json", "native_blast_database_metric_definitions_v1"),
    "diagnostics": ("diagnostics.json", "native_blast_database_diagnostics_v1")}
_ARTIFACT_ROLES_V2 = {**_ARTIFACT_ROLES,
    "sheets": ("sheets.json", "native_blast_database_sheet_set_v2"),
    "native_convergence": ("native-convergence.json", "blast_native_convergence_extraction_v1")}
_ARTIFACT_ROLES_FUNCTION = {**_ARTIFACT_ROLES,
    "sheets": ("sheets.json", _FUNCTION_SHEETS), "calculations": ("calculations.json", _FUNCTION_CALCULATIONS),
    "rows": ("rows.ndjson", "native_blast_vdb_function_numeric_row_v1")}


def _artifact_roles(version):
    if version == "native_blast_database_result_worker_manifest_v1":
        return _ARTIFACT_ROLES
    if version == "native_blast_database_result_worker_manifest_v2":
        return _ARTIFACT_ROLES_V2
    if version == _FUNCTION_MANIFEST:
        return _ARTIFACT_ROLES_FUNCTION
    raise ValueError("native_blast_database_manifest_version_invalid")


def _request_schema(version="native_blast_database_result_worker_request_v1"):
    function_mode = version == _FUNCTION_REQUEST
    value = _views._object(dict(version={"const": version}, calculation_id=_views._SHA,
        bundle=_contracts.NATIVE_BLAST_DATABASE_BUNDLE_SCHEMA, bundle_artifact_ref=_views._REF,
        bundle_capture=_views._object(dict(path=_ABS, sha256=_views._SHA, size_bytes=_views._I0)),
        authenticated_attempt=_ATTEMPT, artifacts=_views._array(_views._object(dict(artifact_key=_views._TOKEN, path=_ABS, **_FILE_ID))),
        metadata_descriptors=_views._array(_descriptor(function_mode)), retained_sources=_views._array(_views._object(dict(source_ref=_views._REF, path=_ABS, **_FILE_ID))),
        subject_snapshots=_views._array(_views._object(dict(**_SNAPSHOT_ID, sequence_path=_ABS))),
        implementation=_views._object(dict(manifest_sha256=_views._SHA, files=_views._array(_views._object(dict(module=_views._TOKEN, path=_ABS, sha256=_views._SHA)), minItems=1))),
        sequence_model=_MODEL, output_directory=_ABS, reuse=_views._nullable(_views._object(dict(
            manifest_path=_ABS, manifest_sha256=_views._SHA, manifest_size_bytes=_views._I0, collection_path=_ABS, sheets_path=_ABS)))))
    if function_mode:
        value["properties"]["vdb_function_model"] = {"type": "object"}
        value["required"].append("vdb_function_model")
    elif version != "native_blast_database_result_worker_request_v1":
        raise ValueError("native_blast_database_request_version_invalid")
    return value


def _manifest_schema(version="native_blast_database_result_worker_manifest_v1"):
    roles = _artifact_roles(version)
    value = _views._object(dict(version={"const": version}, calculation_id=_views._SHA,
        request_sha256=_views._SHA, status={"enum": ["complete", "partial", "failed"]}, input_identity=_views._SHA,
        input_interpretation_id=_views._SHA, input_implementation_sha256=_views._SHA, implementation_manifest_sha256=_views._SHA,
        sequence_model=_MODEL, artifacts=_views._array(_views._object(dict(role={"enum": list(roles)},
            relative_path=_views._TOKEN, sha256=_views._SHA, size_bytes=_views._I0, schema=_views._TOKEN))),
        counts=_views._object(dict(searches=_views._I0, native_hsp_slots=_views._I0, numerical_rows=_views._I0)),
        failures=_views._array(_views._failure_schema())))
    if version == _FUNCTION_MANIFEST:
        value["properties"]["vdb_function_model"] = {"type": "object"}
        value["required"].append("vdb_function_model")
    return value


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("native_blast_database_duplicate_json_key")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("native_blast_database_finite_json_required")
    return _views._copy(json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite))


class _WorkerFailure(Exception):
    def __init__(self, stage, code, detail, *, pointer="", artifact_key=None, input_key=None, search_key=None):
        self.failure = dict(stage=stage, code=code, detail_code=detail, pointer=pointer, artifact_key=artifact_key,
            input_key=input_key, search_key=search_key, record_key=None)
        super().__init__(code)


def _verified_bytes(path, sha256, size_bytes, *, frozen=False, pointer="", artifact_key=None):
    _absolute_path(path)
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        raise _WorkerFailure("capture", "native_blast_database_artifact_missing", "artifact_bytes_unavailable",
            pointer=pointer, artifact_key=artifact_key) from error
    if len(data) != size_bytes or hashlib.sha256(data).hexdigest() != sha256:
        raise _WorkerFailure("capture", "native_blast_database_frozen_artifact_changed" if frozen else "native_blast_database_artifact_identity_mismatch",
            "frozen_value_changed" if frozen else "artifact_digest_conflict", pointer=pointer, artifact_key=artifact_key)
    return data


_DEPENDENCY_ROOTS = {"Bio", "numpy", "jsonschema", "jsonschema_specifications", "referencing", "rpds", "attr", "attrs"}


def _module_name(name):
    return 'gene_annotation_episode.episodic_workflow.root.a101.' + ('library.' if name in ('alignment_correspondence', 'blast_database_grader', 'blast_database_population_associations', 'blast_fasta_record_identity', 'blast_grading_inputs', 'blast_iteration_calculators', 'blast_iteration_inputs', 'blast_native_iteration_records', 'blast_pairwise_grader', 'blast_profile_calculators', 'blast_profile_inputs', 'blast_program_context', 'blast_pssm_calculators', 'blast_pssm_inputs', 'blast_pssm_master_inputs', 'blast_report_collection', 'blast_search', 'blast_sequence_database', 'blast_vdb_calculators', 'blast_vdb_function_calculators', 'blast_vdb_function_inputs', 'blast_vdb_inputs', 'native_blast_database_contracts', 'native_blast_database_convergence', 'native_blast_database_population_metadata', 'native_blast_database_result_views', 'native_blast_vdb_function_metadata', 'native_blast_database_worker_values', 'native_blast_database_metadata') else '') + name


def _implementation_modules(*, execution_program=None, vdb_function=False):
    """Actual loaded scientific dependency closure, excluding unrelated callers."""
    names = [_module_name(name) for name in ('native_blast_database_result_worker', 'native_blast_database_result_views', 'native_blast_database_metadata', 'native_blast_database_contracts', 'native_blast_database_population_metadata', 'blast_database_population_associations', 'blast_report_collection', 'blast_grading_inputs', 'blast_program_context', 'blast_fasta_record_identity', 'blast_sequence_database', 'blast_database_grader', 'blast_pairwise_grader', 'alignment_correspondence', 'blast_profile_inputs', 'blast_profile_calculators', 'blast_pssm_inputs', 'blast_pssm_calculators', 'blast_pssm_master_inputs', 'blast_iteration_inputs', 'blast_iteration_calculators', 'blast_vdb_inputs', 'blast_vdb_calculators', 'blast_search', 'domain', 'native_blast_database_worker_values')]
    if execution_program in ("psiblast", "deltablast"):
        names.extend(_module_name(name) for name in
            ("native_blast_database_convergence", "blast_native_iteration_records"))
    if vdb_function:
        names.extend(_module_name(name) for name in
            ("blast_vdb_function_inputs", "blast_vdb_function_calculators", "native_blast_vdb_function_metadata"))
    for name in names:
        importlib.import_module(name)
    names.extend(name for name, module in tuple(sys.modules.items()) if name.split(".")[0] in _DEPENDENCY_ROOTS and getattr(module, "__file__", None))
    names.append("gene_annotation_episode")
    return {name: sys.modules[name] for name in sorted(set(names))}


def _verify_implementation(implementation, *, execution_program=None, vdb_function=False):
    expected = native_blast_database_implementation_identity(implementation["files"])
    if implementation["manifest_sha256"] != expected:
        raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/manifest_sha256")
    files = {r["module"]: r for r in implementation["files"]}
    # The parent may previously have used another mode and retained more of the
    # same allowed dependency packages. Load exactly its declared dependencies
    # in this fresh process before verifying their actual files. This does not
    # import unrelated project operations or invoke their scientific functions.
    for name in files:
        if name not in sys.modules and name.split(".")[0] in _DEPENDENCY_ROOTS:
            importlib.import_module(name)
    modules = _implementation_modules(execution_program=execution_program, vdb_function=vdb_function)
    if not set(modules) <= set(files):
        raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
    if Path(__file__).resolve() != Path(files["gene_annotation_episode.episodic_workflow.root.a101.native_blast_database_result_worker"]["path"]).resolve():
        raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
    for name, row in files.items():
        module = sys.modules.get(name)
        path = getattr(module, "__file__", None)
        if path is None or Path(path).resolve() != Path(row["path"]).resolve():
            raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")
        raw = Path(row["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise _WorkerFailure("worker", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/implementation/files")


def _atomic_bytes(directory, filename, raw):
    path = directory / filename
    if path.exists():
        raise FileExistsError("native_blast_database_generation_immutable")
    descriptor, temporary = tempfile.mkstemp(prefix="." + filename + ".", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        # Linking is atomic and fails rather than replacing a prior artifact.
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _json_bytes(value):
    return (json.dumps(_views._copy(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _catalog(request, failures):
    originals = {r["artifact_key"]: r for r in request["bundle"]["artifacts"]}
    entries, contents = [], {}
    if len({r["artifact_key"] for r in request["artifacts"]}) != len(request["artifacts"]):
        raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/artifacts")
    for i, row in enumerate(request["artifacts"]):
        original = originals.get(row["artifact_key"])
        if original is None or any(row[k] != original[k] for k in ("sha256", "size_bytes")):
            raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer=f"/artifacts/{i}", artifact_key=row["artifact_key"])
        entry = {k: v for k, v in original.items() if k != "content_assessment"}
        entry.update(row, source_ref=row["artifact_ref"])
        entries.append(entry)
        try:
            contents[row["artifact_key"]] = _verified_bytes(row["path"], row["sha256"], row["size_bytes"], pointer=f"/artifacts/{i}", artifact_key=row["artifact_key"])
        except _WorkerFailure as error:
            failures.append(error.failure)
    captured_keys = {r["artifact_key"] for r in entries}
    for key in originals:
        if key not in captured_keys:
            failures.append(_WorkerFailure("capture", "native_blast_database_artifact_missing", "artifact_bytes_unavailable", artifact_key=key, pointer="/artifacts").failure)
    if len({r["source_ref"] for r in request["retained_sources"]}) != len(request["retained_sources"]):
        raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/retained_sources")
    for i, row in enumerate(request["retained_sources"]):
        try:
            _verified_bytes(row["path"], row["sha256"], row["size_bytes"], pointer=f"/retained_sources/{i}")
        except _WorkerFailure as error:
            failures.append(error.failure)
    catalog = dict(bundle_source_ref=request["bundle_artifact_ref"], bundle_artifact_ref=request["bundle_artifact_ref"],
        bundle_sha256=request["bundle_capture"]["sha256"], entries=entries, retained_sources=deepcopy(request["retained_sources"]))
    if any(r["schema_id"] == "native_blast_database_sequence_metadata_v3" for r in request["metadata_descriptors"]):
        catalog["bundle_size_bytes"] = request["bundle_capture"]["size_bytes"]
    return catalog, contents


def _metadata_payloads(request, catalog, failures):
    job = request["bundle"]["requested_job"]["native_blast_database"]
    descriptors = request["metadata_descriptors"]
    if len({(r["input_key"], r["consumer"], r["schema_id"]) for r in descriptors}) != len(descriptors):
        raise _WorkerFailure("metadata", "native_blast_metadata_payload_invalid", "metadata_shape_invalid", pointer="/metadata_descriptors")
    identities = {}
    for descriptor in descriptors:
        value = tuple(descriptor[k] for k in ("artifact_ref", "sha256", "size_bytes"))
        if descriptor["input_key"] in identities and identities[descriptor["input_key"]] != value:
            raise _WorkerFailure("metadata", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", input_key=descriptor["input_key"], pointer="/metadata_descriptors")
        identities[descriptor["input_key"]] = value
    original = [r for r in descriptors if r["origin"] == "original_job_input"]
    if [{k: r[k] for k in ("input_key", "consumer", "schema_id")} for r in original] != job["metadata_inputs"] or descriptors[:len(original)] != original:
        raise _WorkerFailure("metadata", "native_blast_metadata_payload_invalid", "metadata_shape_invalid", pointer="/metadata_descriptors")
    payloads = []
    selected_inputs = {r["input_key"]: r for r in job["inputs"]}
    for i, descriptor in enumerate(descriptors):
        original_input = selected_inputs.get(descriptor["input_key"])
        if original_input is not None and original_input["role"] != "metadata":
            raise _WorkerFailure("metadata", "native_blast_metadata_payload_invalid", "metadata_shape_invalid", input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}")
        candidates = [r for r in catalog["entries"] + catalog["retained_sources"] if r["artifact_ref"] == descriptor["artifact_ref"]]
        # Exact artifact identity is required, even when its JSON is malformed.
        unique = {canonical({k: r[k] for k in ("artifact_ref", "path", "sha256", "size_bytes")}): r for r in candidates}
        if not unique:
            failures.append(_WorkerFailure("metadata", "native_blast_metadata_source_unavailable", "metadata_address_unresolved",
                input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}").failure)
            payloads.append(dict(descriptor=deepcopy(descriptor), payload=None))
            continue
        if len(unique) != 1:
            raise _WorkerFailure("metadata", "native_blast_metadata_source_unavailable", "metadata_address_unresolved", input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}")
        row = next(iter(unique.values()))
        if any(row[k] != descriptor[k] for k in ("sha256", "size_bytes")) or original_input is not None and row.get("input_key") != descriptor["input_key"]:
            raise _WorkerFailure("metadata", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", input_key=descriptor["input_key"], pointer=f"/metadata_descriptors/{i}")
        try:
            raw = _verified_bytes(row["path"], row["sha256"], row["size_bytes"], pointer=f"/metadata_descriptors/{i}")
            payload = _decode(raw)
        except _WorkerFailure as error:
            failures.append(error.failure); payload = None
        except (ValueError, UnicodeError):
            payload = None
        payloads.append(dict(descriptor=deepcopy(descriptor), payload=payload))
    return payloads


def _reuse(request, input_identity):
    reused = request["reuse"]
    raw = _verified_bytes(reused["manifest_path"], reused["manifest_sha256"], reused["manifest_size_bytes"], frozen=True, pointer="/reuse/manifest_path")
    function_mode = request["version"] == _FUNCTION_REQUEST
    manifest = _decode(raw)
    if function_mode and (type(manifest) is not dict or manifest.get("version") != _FUNCTION_MANIFEST):
        raise _WorkerFailure("population", "native_blast_database_sheet_invalid", "metadata_shape_invalid", pointer="/reuse/manifest_path")
    _shape(manifest, _manifest_schema(manifest.get("version")))
    if function_mode != (manifest["version"] == _FUNCTION_MANIFEST):
        raise _WorkerFailure("population", "native_blast_database_sheet_invalid", "metadata_shape_invalid", pointer="/reuse")
    roles = _artifact_roles(manifest["version"])
    identities = native_blast_database_calculation_identity(input_identity=manifest["input_identity"],
        input_implementation_sha256=manifest["input_implementation_sha256"], sequence_model=manifest["sequence_model"],
        implementation_manifest_sha256=manifest["implementation_manifest_sha256"], vdb_function_model=manifest.get("vdb_function_model"))
    if (manifest["status"] == "failed" or manifest["input_identity"] != input_identity
            or any(manifest[k] != value for k, value in identities.items())):
        raise _WorkerFailure("inputs", "native_blast_database_frozen_artifact_changed", "frozen_value_changed", pointer="/reuse")
    artifacts = {r["role"]: r for r in manifest["artifacts"]}
    if len(artifacts) != len(manifest["artifacts"]) or not {"collection", "sheets"} <= artifacts.keys():
        raise _WorkerFailure("population" if function_mode else "inputs", "native_blast_database_sheet_invalid",
            "metadata_shape_invalid" if function_mode else "calculator_contract_invalid", pointer="/reuse")
    for role, artifact in artifacts.items():
        if (artifact["relative_path"], artifact["schema"]) != roles[role]:
            raise _WorkerFailure("population" if function_mode else "inputs", "native_blast_database_sheet_invalid",
                "metadata_shape_invalid" if function_mode else "calculator_contract_invalid", pointer="/reuse")
    values = {}
    for role in ("collection", "sheets"):
        artifact = artifacts[role]
        data = _verified_bytes(reused[role + "_path"], artifact["sha256"], artifact["size_bytes"], frozen=True, pointer="/reuse/" + role + "_path")
        values[role] = _decode(data)
        if values[role].get("schema") != artifact["schema"]:
            raise _WorkerFailure("population" if function_mode else "inputs", "native_blast_database_sheet_invalid",
                "metadata_shape_invalid" if function_mode else "calculator_contract_invalid", pointer="/reuse/" + role + "_path")
    try:
        binding = _sheet_binding(values["sheets"])
    except ValueError as error:
        if not function_mode:
            raise
        raise _WorkerFailure("population", "native_blast_database_sheet_invalid", "metadata_shape_invalid", pointer="/reuse/sheets_path") from error
    if (values["sheets"]["collection"] != values["collection"]
            or values["sheets"]["prepared_inputs"].get("schema") != "native_blast_database_prepared_inputs_v1"):
        raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
    if binding is not None:
        expected_context = dict(original_job=request["bundle"]["requested_job"]["native_blast_database"],
            bundle=request["bundle"], attempt_identity=request["authenticated_attempt"])
        if binding["source_context"] != expected_context:
            raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
        extraction = binding["extraction"]
        if (extraction is not None) != ("native_convergence" in artifacts):
            raise _WorkerFailure("inputs", "native_blast_database_sheet_invalid", "calculator_contract_invalid", pointer="/reuse")
        if extraction is not None:
            artifact = artifacts["native_convergence"]
            path = str(Path(reused["manifest_path"]).parent / artifact["relative_path"])
            data = _verified_bytes(path, artifact["sha256"], artifact["size_bytes"], frozen=True, pointer="/reuse/native_convergence")
            expected = binding["extraction_artifact"]
            if (data != _json_bytes(extraction)
                    or any(artifact[k] != expected[k] for k in ("sha256", "size_bytes"))):
                raise _WorkerFailure("inputs", "native_blast_database_frozen_artifact_changed", "frozen_value_changed", pointer="/reuse/native_convergence")
    saved_calculations = None
    if function_mode:
        artifact = artifacts.get("calculations")
        if artifact is None:
            raise _WorkerFailure("population", "native_blast_database_sheet_invalid", "metadata_shape_invalid", pointer="/reuse")
        path = str(Path(reused["manifest_path"]).parent / artifact["relative_path"])
        saved_calculations = _decode(_verified_bytes(path, artifact["sha256"], artifact["size_bytes"], frozen=True, pointer="/reuse/calculations"))
        if saved_calculations.get("schema") != _FUNCTION_CALCULATIONS:
            raise _WorkerFailure("population", "native_blast_database_sheet_invalid", "metadata_shape_invalid", pointer="/reuse/calculations")
    return values["collection"], values["sheets"], manifest["input_implementation_sha256"], manifest["version"], saved_calculations


def _metadata_failures(issues):
    details = {"schema_unsupported": "metadata_tuple_unregistered", "payload_invalid": "metadata_shape_invalid",
        "source_unavailable": "metadata_address_unresolved", "relation_unresolved": "metadata_address_unresolved",
        "relation_conflict": "metadata_relation_conflict", "extractor_unbound": "extractor_not_registered"}
    output = []
    for issue in issues:
        code = issue["code"]
        detail = details.get(code.removeprefix("native_blast_metadata_"))
        if detail is None:
            raise ValueError("native_blast_database_metadata_failure_mapping_required")
        output.append(_WorkerFailure("metadata", code, detail, pointer=issue["pointer"],
            input_key=issue.get("input_key"), search_key=issue.get("search_key")).failure)
    return output


def run_native_blast_database_result_worker(request_path):
    """I/O entry invoked within E's caller-owned local_jobs resource boundary."""
    request_bytes = Path(_absolute_path(str(request_path))).read_bytes()
    request = _decode(request_bytes)
    if type(request) is dict and "sequence_model" in request:
        _model(request["sequence_model"])
    _shape(request, _request_schema(request.get("version")))
    function_mode = request["version"] == _FUNCTION_REQUEST
    if function_mode:
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_vdb_function_calculators import validate_blast_vdb_function_model
        validate_blast_vdb_function_model(request["vdb_function_model"])
        if request["bundle"]["program"] not in ("blastn_vdb", "tblastn_vdb"):
            raise ValueError("native_blast_database_program_unsupported")
    directory = Path(_absolute_path(request["output_directory"]))
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise FileExistsError("native_blast_database_generation_directory_not_empty")
    input_identity = native_blast_database_input_identity(request)
    input_implementation = request["implementation"]["manifest_sha256"]
    initial = native_blast_database_calculation_identity(input_identity=input_identity,
        input_implementation_sha256=input_implementation, sequence_model=request["sequence_model"],
        implementation_manifest_sha256=request["implementation"]["manifest_sha256"], vdb_function_model=request.get("vdb_function_model"))
    program = request["bundle"]["requested_job"]["native_blast_database"]["program"]
    version = _FUNCTION_MANIFEST if function_mode else "native_blast_database_result_worker_manifest_v2" if program in ("psiblast", "deltablast") else "native_blast_database_result_worker_manifest_v1"
    manifest = dict(version=version, calculation_id=request["calculation_id"],
        request_sha256=hashlib.sha256(request_bytes).hexdigest(), status="failed", input_identity=input_identity,
        input_interpretation_id=initial["input_interpretation_id"], input_implementation_sha256=input_implementation,
        implementation_manifest_sha256=request["implementation"]["manifest_sha256"], sequence_model=deepcopy(request["sequence_model"]),
        artifacts=[], counts=dict(searches=0, native_hsp_slots=0, numerical_rows=0), failures=[])
    if function_mode:
        manifest["vdb_function_model"] = deepcopy(request["vdb_function_model"])
    saved_calculations = None
    failures, metadata_issues, errors = manifest["failures"], [], []
    stage = "capture"
    def save(role, value):
        filename, schema = _artifact_roles(manifest["version"])[role]
        record = _atomic_bytes(directory, filename, _json_bytes(value))
        manifest["artifacts"].append(dict(role=role, relative_path=filename, schema=schema, **record))
        return record
    def save_extraction(binding):
        if binding["extraction"] is not None:
            record = save("native_convergence", binding["extraction"])
            if record != {k: binding["extraction_artifact"][k] for k in ("sha256", "size_bytes")}:
                raise _WorkerFailure("population", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/native_convergence/extraction_artifact")
    try:
        capture = request["bundle_capture"]
        if _decode(_verified_bytes(**capture, pointer="/bundle_capture")) != request["bundle"]:
            raise _WorkerFailure("capture", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/bundle_capture")
        bundle = _contracts.validate_retained_native_blast_database_bundle(request["bundle"],
            original_job=request["bundle"]["requested_job"]["native_blast_database"], attempt_identity=request["authenticated_attempt"])
        _verify_implementation(request["implementation"], execution_program=program, vdb_function=function_mode)
        population_selected = any(r["schema_id"] == "native_blast_database_sequence_metadata_v3" for r in request["metadata_descriptors"])
        catalog, contents = _catalog(request, failures) if request["reuse"] is None or population_selected else (None, None)
        for i, native_failure in enumerate(bundle["failures"]):
            failures.append(_WorkerFailure("capture", "native_blast_database_capture_incomplete", "artifact_bytes_unavailable",
                artifact_key=native_failure["artifact_key"], input_key=native_failure["input_key"], pointer=f"/bundle/failures/{i}").failure)
        stage = "inputs"
        if request["reuse"] is not None:
            collection, sheets, input_implementation, saved_version, saved_calculations = _reuse(request, input_identity)
            manifest["version"] = saved_version
            prepared = sheets["prepared_inputs"]
        else:
            metadata_payloads = _metadata_payloads(request, catalog, failures)
            from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_metadata import prepare_native_blast_database_inputs, populate_native_blast_database_sheets
            prepared = prepare_native_blast_database_inputs(job=bundle["requested_job"]["native_blast_database"], bundle=bundle,
                artifact_catalog=catalog, metadata_payloads=metadata_payloads, subject_snapshots=request["subject_snapshots"])
            save("inputs", prepared)
            stage = "collection"
            roles = {"primary_report": "primary_report", "stdout": "native_log", "stderr": "native_log",
                "query_msa": "query_msa", "query_pssm": "query_pssm", "checkpoint_asn": "checkpoint", "checkpoint_ascii": "checkpoint"}
            collected = [r for r in catalog["entries"] if r["role"] in roles and r["artifact_key"] in contents]
            descriptors = [{**{k: r[k] for k in ("artifact_key", "format", "fields", "delimiter")}, "role": roles[r["role"]]} for r in collected]
            for descriptor in descriptors:
                if descriptor["format"] == "json15":
                    descriptor["fields"] = None
            collection = parse_blast_report_collection({r["artifact_key"]: contents[r["artifact_key"]] for r in collected},
                artifacts=descriptors, invocation=prepared["invocation"])
            save("collection", collection)
            stage = "population"
            options = {}
            if program in ("psiblast", "deltablast"):
                from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_convergence import bind_native_blast_database_convergence
                binding = bind_native_blast_database_convergence(original_job=bundle["requested_job"]["native_blast_database"],
                    bundle=bundle, attempt_identity=request["authenticated_attempt"], collection=collection,
                    artifact_catalog={k: v for k, v in catalog.items() if k != "bundle_size_bytes"}, artifact_contents=contents)
                save_extraction(binding)
                options["native_convergence"] = binding
            sheets = populate_native_blast_database_sheets(collection, prepared_inputs=prepared, artifact_catalog=catalog, **options)
            if function_mode:
                from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_vdb_function_metadata import populate_native_blast_vdb_function_sheets
                populated = populate_native_blast_vdb_function_sheets(sheets,
                    prepared_inputs=sheets["prepared_inputs"], artifact_catalog=catalog)
                sheets.update(schema=_FUNCTION_SHEETS, vdb_function=populated["sheets"])
                sheets["issues"].extend(populated["issues"])
            _population_capture_binding(sheets, request, catalog)
            save("sheets", sheets)
        identities = native_blast_database_calculation_identity(input_identity=input_identity, input_implementation_sha256=input_implementation,
            sequence_model=request["sequence_model"], implementation_manifest_sha256=request["implementation"]["manifest_sha256"],
            vdb_function_model=request.get("vdb_function_model"))
        manifest.update(input_implementation_sha256=input_implementation, input_interpretation_id=identities["input_interpretation_id"])
        if request["calculation_id"] != identities["calculation_id"]:
            raise _WorkerFailure("inputs", "native_blast_database_artifact_identity_mismatch", "artifact_digest_conflict", pointer="/calculation_id")
        if request["reuse"] is not None:
            if population_selected:
                _population_capture_binding(sheets, request, catalog)
            save("inputs", prepared); save("collection", collection)
            if sheets["schema"] == "native_blast_database_sheet_set_v2":
                save_extraction(sheets["native_convergence"])
            save("sheets", sheets)
        metadata_issues.extend(sheets["issues"])
        failures.extend(_metadata_failures(metadata_issues))
        manifest["counts"]["searches"] = len(collection["searches"])
        for i, issue in enumerate(collection["issues"]):
            failures.append(_WorkerFailure("collection", "native_blast_database_report_unreadable", "native_syntax_invalid",
                artifact_key=issue.get("artifact_key"), pointer=f"/collection/issues/{i}").failure)
        stage = "calculation"
        calculations = calculate_native_blast_database_sheets(sheets, sequence_model=request["sequence_model"],
            **(dict(vdb_function_model=request["vdb_function_model"], saved_calculations=saved_calculations) if function_mode else {}))
        save("calculations", calculations)
        manifest["counts"]["native_hsp_slots"] = len(calculations["native_hsp_components"])
        for i, issue in enumerate(calculations["issues"]):
            failures.append(_WorkerFailure("calculation", "native_blast_database_calculation_failed", "calculator_contract_invalid",
                pointer=f"/calculations/issues/{i}", artifact_key=issue["artifact_key"], search_key=issue["search_key"]).failure)
        stage = "rows"
        rows = build_native_blast_database_rows(bundle_identity=bundle["identity"], calculation_id=request["calculation_id"], sheet_set=sheets, calculations=calculations)
        index, chunks, position = [], [], 0
        for ordinal, row in enumerate(rows):
            data = _json_bytes(row)
            index.append(dict(family=row["family"], record_key=row["record_key"], ordinal=ordinal, byte_start=position, byte_end=position + len(data)))
            chunks.append(data); position += len(data)
        record = _atomic_bytes(directory, "rows.ndjson", b"".join(chunks))
        manifest["artifacts"].append(dict(role="rows", relative_path="rows.ndjson", schema=_artifact_roles(manifest["version"])["rows"][1], **record))
        save("row_index", dict(schema="native_blast_database_row_index_v1", calculation_id=request["calculation_id"], rows=index))
        manifest["counts"]["numerical_rows"] = len(rows)
        save("metric_definitions", _views.native_blast_database_metric_definitions(include_vdb_function=function_mode))
        _verify_implementation(request["implementation"], execution_program=program, vdb_function=function_mode)
        manifest["status"] = "partial" if failures else "complete"
    except _WorkerFailure as error:
        failures.append(error.failure)
        if error.__cause__ is not None:
            cause = error.__cause__
            errors.append(dict(failure_index=len(failures) - 1, exception_type=type(cause).__module__ + "." + type(cause).__qualname__, message=str(cause)))
    except MemoryError as error:
        failures.append(_WorkerFailure("worker", "native_blast_database_worker_resource_limit", "resource_limit").failure)
        errors.append(dict(failure_index=len(failures) - 1, exception_type=type(error).__module__ + "." + type(error).__qualname__, message=str(error)))
    except Exception as error:
        resource = isinstance(error, OSError) and error.errno in (12, 27, 28, 122)
        code = ("native_blast_database_worker_resource_limit" if resource else "native_blast_database_sheet_invalid" if stage in ("inputs", "population")
            else "native_blast_database_calculation_failed" if stage == "calculation" else "native_blast_database_worker_failed")
        detail = "resource_limit" if resource else "calculator_contract_invalid" if isinstance(error, ValueError) and stage in ("inputs", "population", "calculation") else "implementation_failure"
        failures.append(_WorkerFailure("worker" if resource else stage, code, detail).failure)
        errors.append(dict(failure_index=len(failures) - 1, exception_type=type(error).__module__ + "." + type(error).__qualname__, message=str(error)))
    save("diagnostics", dict(schema="native_blast_database_diagnostics_v1", failures=failures, metadata_issues=metadata_issues, errors=errors))
    _shape(manifest, _manifest_schema(manifest["version"]))
    _atomic_bytes(directory, "worker-manifest.json", _json_bytes(manifest))
    return manifest


__all__ = ["calculate_native_blast_database_sheets",
    "build_native_blast_database_rows", "run_native_blast_database_result_worker", "native_blast_database_implementation_identity",
    "native_blast_database_input_identity", "native_blast_database_calculation_identity"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("native_blast_database_result_worker requires one retained request path")
    result = run_native_blast_database_result_worker(sys.argv[1])
    raise SystemExit(1 if result["status"] == "failed" else 0)
