"""Join retained preparation facts through the common utility result contracts.

This pure helper belongs to the existing result worker. It selects parsers for
already retained bytes, calls the shared population/projection functions and
does no acquisition, native execution, episode iteration or numerical scoring.
"""
from __future__ import annotations

from pathlib import PurePosixPath

from .blast_database_extraction import _outcome_observations
from .blast_database_preparation import project_prepared_blast_database
from .blast_preparation_inputs import (
    parse_blast_alias_document, parse_blast_aliastool_diagnostics,
    parse_blast_preparation_list, parse_blast_seqid_list_info,
    parse_makembindex_diagnostics, parse_makeprofiledb_aux,
    parse_makeprofiledb_diagnostics,
)
from .blast_preparation_population import populate_blast_preparation_artifact_set
from .blast_utility_contracts import (
    blast_utility_result_version_for_operation,
    validate_blast_utility_record as core,
)
from .native_blast_contracts import native_blast_digest


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(row)
    return result


def _file_identity(occurrence):
    return {"path": occurrence["native_path"],
            **{k: occurrence[k] for k in ("artifact_ref", "sha256", "size_bytes")}}


def _inspection(context, contents):
    operation, outcome = context["operation"], context["native_outcome"]
    output = next(r for r in context["occurrences"] if r["direction"] == "output" and r["role"] == "stdout")
    selected = (operation["program"], operation["mode"])
    subject_failures = []
    if selected == ("blastdb_aliastool", "inspect_seqid_list"):
        document = parse_blast_seqid_list_info(contents[output["occurrence_id"]], occurrence=output)
        subject = {"kind": "identifier_list", "occurrence_id": operation["parameters"]["input_occurrence_id"]}
        subject_key = subject["occurrence_id"]
        if not any(r["direction"] == "input" and r["occurrence_id"] == subject_key
                   for r in context["occurrences"]):
            # Preserve the actual native inspection and its selected subject.
            # Missing original input bytes prevent granting that artifact.
            subject_failures.append(core("UtilityFailure", {
                "stage": "input", "code": "input_population_unavailable",
                "occurrence_id": None, "record_key": None, "line_number": None,
                "native_returncode": None,
            }))
    else:
        # Empty native filter output is an observed empty document, not a zero
        # filter count. Nonempty unrecognized lines remain explicitly qualified.
        document = parse_makembindex_diagnostics(contents[output["occurrence_id"]], occurrence=output)
        subject = {"kind": "database", "database_key": operation["database_key"]}
        subject_key = subject["database_key"]
    checks, failures = _outcome_observations(outcome, [output], subject_key)
    complete = output["completeness"] == "complete" and outcome["writer_closed"] and outcome["inventory_complete"]
    return core("DatabaseInspection", {
        "version": "blast_database_inspection_v2", "operation": operation,
        "original_outcome": outcome, "subject": subject,
        "database_bindings": context["database_bindings"], "output_occurrence": output,
        "native_fields": document["native_fields"],
        "completeness": "partial" if document["failures"] or subject_failures else "complete" if complete else "unknown",
        "checks": _unique([*document["checks"], *checks]),
        "failures": _unique([*document["failures"], *failures, *subject_failures, *context["failures"]]),
    })


def _documents(context, contents):
    operation, documents = context["operation"], []
    parser = {"blastdb_aliastool": parse_blast_aliastool_diagnostics,
              "makembindex": parse_makembindex_diagnostics,
              "makeprofiledb": parse_makeprofiledb_diagnostics}[operation["program"]]
    for row in context["occurrences"]:
        oid = row["occurrence_id"]
        if oid not in contents:
            continue
        if row["direction"] == "output":
            if row["role"] in {"stdout", "stderr"}:
                documents.append(parser(contents[oid], occurrence=row))
            elif row["role"] == "alias_file":
                documents.append(parse_blast_alias_document(contents[oid], occurrence=row))
            elif row["native_format"] == "blast_profile_aux_text":
                documents.append(parse_makeprofiledb_aux(contents[oid], occurrence=row))
        elif row["role"] in {"database_list", "profile_list", "materialized_list"} and (
                oid in operation["input_occurrence_ids"] or row["role"] == "materialized_list"):
            grammar = "profile_whitespace_tokens" if operation["program"] == "makeprofiledb" else "blast_database_lines"
            documents.append(parse_blast_preparation_list(contents[oid], grammar=grammar, occurrence=row))
    return documents


def assemble_blast_preparation_result(*, context: dict, capture: dict, contents: dict) -> tuple[dict, dict | None]:
    """Assemble the exact v2 record from the worker's authenticated context.

    The existing worker authenticates the capture, file population, original
    bundle and retained bytes before calling this helper. Parsers independently
    compare each supplied text blob to its occurrence identity.
    """
    operation = context["operation"]
    if blast_utility_result_version_for_operation(operation) == "blast_database_inspection_v2":
        return _inspection(context, contents), None
    bundle, plan = capture["original_bundle"], capture["plan"]
    job = plan["requested_job"]["native_blast_utility"]
    rows = context["occurrences"]
    selected = (operation["program"], operation["mode"])
    preparation_type = "unknown"
    if selected == ("makeprofiledb", "create_profile_database"):
        if operation["parameters"]["profile_type"] in {"rps", "delta"}:
            preparation_type = operation["parameters"]["profile_type"]
    elif selected[0] == "blastdb_aliastool" and selected[1] in {
            "create_subset_alias", "aggregate_databases", "aggregate_volumes"}:
        if not any(b["kind"] == "vdb" for b in context["database_bindings"]):
            preparation_type = "sequence_database"
    execution_id = bundle["identity"]["execution_id"]
    identity = {
        "namespace": "episode_native_execution" if execution_id is not None else "episode_native_attempt",
        "value": execution_id if execution_id is not None else bundle["identity"]["attempt_id"],
        "version": None, "release": None, "scope": None, "preparation_type": preparation_type,
        "source": {"source_ref": capture["source_ref"], "pointer": ""},
    }
    native_paths = [str(PurePosixPath(plan["attempt_directory"]) / r["relative_path"])
                    for r in job["outputs"] if r["role"] in {"identifier_list", "database_family", "index_family"}]
    result = populate_blast_preparation_artifact_set(
        operation=operation,
        inputs=[r for r in rows if r["direction"] == "input"],
        outputs=[r for r in rows if r["direction"] == "output"],
        database_bindings=context["database_bindings"], materializations=context["materializations"],
        database_key="native_blast_utility_" + native_blast_digest(bundle["identity"]),
        identity=identity,
        software={"name": operation["program"], "version": bundle["software"]["declared_engine_version"],
                  "executable_sha256": bundle["software"]["actual_sha256"]},
        argv=bundle["realized_argv"], native_paths=native_paths,
        documents=_documents(context, contents), outcome=context["native_outcome"],
    )
    result["failures"] = _unique([*result["failures"], *context["failures"]])
    result = core("DatabaseArtifactSet", result)
    receipt = next(r for r in rows if r["direction"] == "output" and r["role"] == "preparation_receipt")
    metadata = [_file_identity(r) for r in rows if r["direction"] == "output" and r["role"] == "database_metadata"]
    prepared = project_prepared_blast_database(
        result, contract="additional" if preparation_type in {"rps", "delta"} else "standard",
        preparation_receipt=_file_identity(receipt), input_manifest=None, metadata_manifests=metadata,
    )
    # Unavailable prepared-search projections for list/index artifacts are
    # reported only when requested; they do not invalidate their actual outputs.
    return result, prepared
