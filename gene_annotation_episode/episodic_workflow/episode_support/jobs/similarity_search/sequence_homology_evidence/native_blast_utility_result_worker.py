"""Bounded original utility reading and separate saved-result selection.

``parse_original`` plans contain capture, exact qualified context, bundle_file
and occurrence-associated files. ``project_saved`` plans contain source_ref,
context, selector, saved_data and nullable result/prepared_database/
prepared_manifest files. Both also contain version, task and directory.
Manifests contain version, task, plan_sha256, completed, outputs and failures;
output descriptors contain filename, sha256 and size_bytes. Completion describes
technical processing, including a qualified unavailable result, not native success.

The sealed original bundle is also an output preparation_receipt occurrence
(root's additive reuse correction to 010). Its FileIdentity uses original
attempt/bundle.json; bundle_file.path is only its retained read location. Thus a
later reuse can explicitly request these actual bytes without a source granting
auxiliary files. This receipt is outside the native output-family enumeration.
Binary family members are streamed for custody only. This module has no Store,
native invocation, model, retry, acquisition or episode loop.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_utility_contracts import blast_utility_result_version_for_operation, validate_blast_utility_record as core
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_utility_capture_contracts import _key, _selected_files, validate_native_blast_utility_capture
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.native_blast_utility_contracts import finite_json_copy, native_blast_digest
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_acquisition import (
    _confined_reader, _decode, _directory, _read_record,
)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_result_worker import _read_bytes, _write
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.native_worker_files import _encoded
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_homology_evidence.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.native_blast_utility_worker_context import MANIFEST_VERSION, MANIFEST_VERSION_V2, OUTPUT_FILES, PLAN_VERSION_V2, PREFIX, _can_read_result, _error, _file_descriptor, diagnostic, failure, unique_failures, validate_worker_manifest, validate_worker_plan
























def _verify_file(value):
    """Authenticate a binary occurrence in bounded blocks, without parsing it."""
    value = _file_descriptor(value)
    path, digest, size = Path(value["path"]), hashlib.sha256(), 0
    with _confined_reader(path.parent, path.name) as retained:
        with retained.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(block); digest.update(block)
    if size != value["size_bytes"] or digest.hexdigest() != value["sha256"]:
        _error("worker_retained_bytes_mismatch")






def _parse_original(plan, directory, manifest):
    from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.blast_database_extraction import _check, _check_bytes, parse_blastdbcmd_sequences
    from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.blast_database_inspection import _metadata_fields, parse_blast_database_inspection, parse_blastdbcheck_diagnostics
    from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.blast_database_preparation import populate_database_artifact_set, project_prepared_blast_database
    context = plan["context"]
    bundle = plan["capture"]["original_bundle"]
    if _decode(_read_bytes(plan["bundle_file"])) != bundle:
        _error("worker_original_bundle_bytes_conflict")
    content = {}
    vdb = context["operation"]["version"] == "blast_utility_operation_v3"
    authentication_ids = set()
    if vdb:
        from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.native_blast_vdb_utility_context import vdb_utility_authentication_occurrence_ids
        authentication_ids = vdb_utility_authentication_occurrence_ids(plan["capture"])
    for row, occurrence in zip(plan["files"], context["occurrences"]):
        descriptor = {k: row[k] for k in ("path", "sha256", "size_bytes")}
        if (occurrence["occurrence_id"] in authentication_ids or
                (occurrence["direction"] == "output" and occurrence["role"] in {"stdout", "stderr", "database_metadata"})
                or context["operation"]["version"] == "blast_utility_operation_v2" and (
                    occurrence["role"] in {"database_list", "profile_list", "materialized_list", "alias_file"}
                    or occurrence["native_format"] == "blast_profile_aux_text")):
            content[occurrence["occurrence_id"]] = _read_bytes(descriptor)
        else:
            _verify_file(descriptor)
    operation, outcome, rows = context["operation"], context["native_outcome"], context["occurrences"]
    if not _can_read_result(context):
        manifest["failures"].append(failure("input" if operation["mode"] == "create_sequence_database" else "capture",
            "input_population_unavailable" if operation["mode"] == "create_sequence_database" else "output_missing"))
        return
    streams = {row["role"]: row for row in rows if row["direction"] == "output" and row["role"] in {"stdout", "stderr"}}
    if vdb:
        from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.native_blast_vdb_utility_context import authenticate_vdb_utility_context
        from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_vdb_utility_inputs import parse_blast_vdb_extraction, parse_blast_vdb_inspection
        manifest["context_authentication"] = authenticate_vdb_utility_context(
            plan["capture"], context=context, contents_by_occurrence=content)
        parser = parse_blast_vdb_extraction if operation["mode"] == "extract_sequences" else parse_blast_vdb_inspection
        result = parser(content[streams["stdout"]["occurrence_id"]], occurrence=streams["stdout"],
            operation=operation, database_binding=context["database_binding"], outcome=outcome,
            operation_input_occurrences=context["operation_input_occurrences"], vdb_context=context["vdb_context"],
            stderr_contents=content[streams["stderr"]["occurrence_id"]], stderr_occurrence=streams["stderr"])
        manifest["outputs"]["result"] = _write(directory, OUTPUT_FILES["result"], result)
        manifest["failures"].extend(result["failures"])
        return
    if operation["version"] == "blast_utility_operation_v2":
        from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.blast_preparation_result_assembly import assemble_blast_preparation_result
        result, prepared = assemble_blast_preparation_result(
            context=context, capture=plan["capture"], contents=content)
        manifest["outputs"]["result"] = _write(directory, OUTPUT_FILES["result"], result)
        manifest["failures"].extend(result["failures"])
        if prepared is not None:
            manifest["outputs"]["prepared_database"] = _write(directory, OUTPUT_FILES["prepared_database"], prepared)
            if prepared["status"] == "available":
                manifest["outputs"]["prepared_manifest"] = _write(directory, OUTPUT_FILES["prepared_manifest"], prepared["manifest"])
        return
    common = {"operation": operation, "database_binding": context["database_binding"], "outcome": outcome}
    mode = operation["mode"]
    if mode == "extract_sequences":
        result = parse_blastdbcmd_sequences(content[streams["stdout"]["occurrence_id"]], occurrence=streams["stdout"], **common)
    elif mode in {"info", "metadata"}:
        result = parse_blast_database_inspection(content[streams["stdout"]["occurrence_id"]], occurrence=streams["stdout"], **common)
    elif mode == "integrity":
        result = parse_blastdbcheck_diagnostics(content[streams["stdout"]["occurrence_id"]],
            content[streams["stderr"]["occurrence_id"]], stdout_occurrence=streams["stdout"], stderr_occurrence=streams["stderr"], **common)
    else:
        metadata, checks, problems = [], [], []
        database_key = PREFIX + native_blast_digest(bundle["identity"])
        for row in rows:
            if row["direction"] != "output" or row["role"] != "database_metadata":
                continue
            raw, oid = content[row["occurrence_id"]], row["occurrence_id"]
            checks.append(_check_bytes(raw, row))
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            fields, parsing, units = _metadata_fields(text, oid)
            metadata.extend(fields); problems.extend(parsing)
            if units and units != {"nt" if operation["molecule"] == "dna" else "aa"}:
                problems.append(failure("validation", "database_kind_conflict", oid))
            if not raw:
                problems.append(failure("capture", "output_missing", oid))
            checks.append(_check("syntax", "fail" if parsing else "pass", [oid], "native_format_parser", [oid],
                "native_document_invalid" if parsing else None))
        identity = {"namespace": "episode_native_execution", "value": bundle["identity"]["execution_id"],
            "version": None, "release": None, "scope": None, "preparation_type": "sequence_database",
            "source": {"source_ref": plan["capture"]["source_ref"], "pointer": ""}}
        result = populate_database_artifact_set(operation=operation,
            inputs=[r for r in rows if r["direction"] == "input"], outputs=[r for r in rows if r["direction"] == "output"],
            database_key=database_key, identity=identity,
            software={"name": operation["program"], "version": bundle["software"]["declared_engine_version"],
                "executable_sha256": bundle["software"]["actual_sha256"]}, argv=bundle["realized_argv"],
            native_paths=[str(PurePosixPath(plan["capture"]["plan"]["attempt_directory"]) / operation["parameters"]["output_prefix"])],
            dependency_bindings=[{"role": r["role"], "occurrence_id": r["occurrence_id"]} for r in rows
                                 if r["direction"] == "input" and r["role"] in {"taxid_map", "mask_input"}],
            native_metadata=metadata, outcome=outcome)
        result["checks"].extend(check for check in checks if check not in result["checks"])
        result["failures"] = unique_failures([*result["failures"], *problems, *context["failures"]])
        result = core("DatabaseArtifactSet", result)
        receipt_occurrence = next(r for r in rows if r["direction"] == "output" and r["role"] == "preparation_receipt")
        receipt = {"path": receipt_occurrence["native_path"],
            **{k: receipt_occurrence[k] for k in ("artifact_ref", "sha256", "size_bytes")}}
        metadata_files = [{"path": r["native_path"], **{k: r[k] for k in ("sha256", "size_bytes", "artifact_ref")}}
                          for r in rows if r["direction"] == "output" and r["role"] == "database_metadata"]
        prepared = project_prepared_blast_database(result, contract="standard", preparation_receipt=receipt,
            input_manifest=None, metadata_manifests=metadata_files)
        manifest["outputs"]["prepared_database"] = _write(directory, OUTPUT_FILES["prepared_database"], prepared)
        manifest["failures"].extend(prepared["failures"])
        if prepared["status"] == "available":
            manifest["outputs"]["prepared_manifest"] = _write(directory, OUTPUT_FILES["prepared_manifest"], prepared["manifest"])
    manifest["outputs"]["result"] = _write(directory, OUTPUT_FILES["result"], result)
    manifest["failures"].extend(result["failures"])


def _project_saved(plan, directory, manifest):
    from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_utility_result_views import project_blast_utility_result
    saved = {role: _decode(_read_bytes(row)) if row is not None else None for role, row in plan["files"].items()}
    prepared = saved["prepared_database"]
    if ((prepared is not None and prepared.get("status") == "available") != (saved["prepared_manifest"] is not None)
            or saved["prepared_manifest"] is not None and prepared["manifest"] != saved["prepared_manifest"]):
        _error("worker_saved_manifest_conflict")
    context = plan["context"]
    selected = project_blast_utility_result(source_ref=plan["source_ref"], operation=context["operation"],
        native_outcome=context["native_outcome"], result=saved["result"], prepared_database=prepared,
        occurrences=context["occurrences"], selector=plan["selector"], failures=context["failures"], saved_data=plan["saved_data"],
        **({"context": context} if plan["version"] == PLAN_VERSION_V2 else {}))
    manifest["outputs"]["projection"] = _write(directory, OUTPUT_FILES["projection"], selected)
    if plan["version"] == PLAN_VERSION_V2:
        manifest["context_authentication"] = deepcopy(plan["context_authentication"])




def run(plan: dict) -> dict:
    plan = validate_worker_plan(plan)
    directory = _directory(plan["directory"])
    if not directory.is_dir():
        _error("worker_directory_required")
    intent = {"plan_sha256": native_blast_digest(plan)}
    if (directory / "worker-intent.json").exists():
        if _read_record(directory, "worker-intent.json") != intent:
            _error("worker_identity_conflict")
        if not (directory / "worker-result.json").is_file():
            _error("worker_original_work_incomplete")
        saved = validate_worker_manifest(_read_record(directory, "worker-result.json"), plan)
        for row in saved["outputs"].values():
            _verify_file({"path": str(directory / row["filename"]), **{k: row[k] for k in ("sha256", "size_bytes")}})
        return saved
    _immutable(directory / "worker-intent.json", intent)
    vdb = plan["version"] == PLAN_VERSION_V2
    manifest = {"version": MANIFEST_VERSION_V2 if vdb else MANIFEST_VERSION, "task": plan["task"], "plan_sha256": native_blast_digest(plan),
        "completed": False, "outputs": {}, "failures": deepcopy(plan["context"]["failures"])}
    if vdb:
        manifest["context_authentication"] = None
    try:
        (_parse_original if plan["task"] == "parse_original" else _project_saved)(plan, directory, manifest)
        manifest["completed"] = not (vdb and plan["task"] == "parse_original" and "result" not in manifest["outputs"])
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(canonical(diagnostic(error)), file=sys.stderr)
        code = str(error).removeprefix(PREFIX)
        if vdb and str(error).endswith("_worker_retained_bytes_mismatch"):
            code = "input_identity_mismatch"
        code = code if vdb and code in {"supplied_binding_conflict", "input_identity_mismatch", "input_population_unavailable"} else "semantic_validation_unavailable"
        manifest["failures"].append(failure("parse" if plan["task"] == "parse_original" else "projection", code))
    manifest["failures"] = unique_failures(manifest["failures"])
    manifest = validate_worker_manifest(manifest, plan)
    _immutable(directory / "worker-result.json", manifest)
    return manifest


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        _error("one_worker_plan_required")
    result = run(_decode(Path(args[0]).read_bytes()))
    print(canonical(result))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
