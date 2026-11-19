"""Original native_blast_standard_database_result_worker scientific values and explicit received-record contracts."""
from __future__ import annotations

from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.episode_support.calculations.similarity_search import native_blast_standard_database_calculators as calculators
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence import native_blast_standard_database_contracts as contracts
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import validate_schema
from jsonschema import validators
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence import native_blast_standard_database_result_views as views

PREFIX = views.PREFIX

_ABS = {"type": "string", "pattern": r"^/[^\x00]*$", "minLength": 1}

_FILE_ID = dict(artifact_ref=views.REF, sha256=views.SHA, size_bytes=views.I0)

_ATTEMPT = views._object(dict(identity=contracts.IDENTITY_SCHEMA, attempt_directory=_ABS, plan_sha256=views.SHA))

_DESCRIPTOR = {"oneOf": [views._object(dict(input_key=views.TOKEN, consumer={"const": consumer},
    schema_id={"const": schema_id}, **_FILE_ID, origin={"enum": ["original_job_input", "selected_results_input"]}))
    for consumer, schema_id in contracts._METADATA_TUPLES]}

_SNAPSHOT = dict(subject_ref=views.REF, record_type={"enum": ["input", "feature", "product", "read_subject"]},
    molecule={"enum": ["dna", "rna", "protein"]}, length={"type": "integer", "minimum": 1},
    sequence_sha256=views.SHA, sequence_artifact_ref=views.REF)

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

def standard_blast_database_calculation_identity(*, input_identity: str, sequence_model: dict | None) -> dict:
    _shape(input_identity, views.SHA)
    model = calculators.validate_sequence_model(sequence_model)
    interpretation = views._hash(dict(version=PREFIX + "interpretation_identity_v1",
        input_identity=input_identity))
    return dict(input_interpretation_id=interpretation, calculation_id=views._hash(dict(version=PREFIX + "calculation_identity_v1",
        input_interpretation_id=interpretation, sequence_model=model)))

class _WorkerFailure(Exception):
    def __init__(self, stage, code, detail, *, pointer="", artifact_key=None, input_key=None, search_key=None):
        self.failure = dict(stage=stage, code=PREFIX + code, detail_code=detail, pointer=pointer,
            artifact_key=artifact_key, input_key=input_key, search_key=search_key, record_key=None)
        super().__init__(self.failure["code"])

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

def _resolved_population_failures(issues, sheets, calculations):
    """Resolve only original binding notes answered by the calculated v3 facts.

    The original issues and binding remain intact. The returned failure objects
    retain their original issue index and complete search address; no other
    metadata, capture or calculation failure is reclassified.
    """
    resolved = []
    mapped = _metadata_failures(issues)
    for index, issue in enumerate(issues):
        if issue.get("detail_code") != "native_path_semantic_identity_population_equality_unproven":
            continue
        key = issue.get("search_key")
        selected = [r["sheet"] for r in sheets["sequence"] if r["search_key"] == key]
        calculated = [r["components"] for r in calculations["sequence"] if r["search_key"] == key]
        if len(selected) != 1 or len(calculated) != 1:
            continue
        scientific, result = selected[0], calculated[0]
        if (scientific.get("schema") != "blast_sequence_database_result_sheet_v3"
                or not scientific["database_population_associations"] or result is None
                or result.get("search_key") != key):
            continue
        database = result["components"].get("database_sheet")
        if database is None or database.get("schema") != "blast_database_sheet_v3":
            continue
        context = dict(schema="blast_database_population_context_v1", search_key=key,
            associations=scientific["database_population_associations"])
        relation = database.get("database_population_relation")
        if (database.get("database_population_context") == context and relation is not None
                and relation.get("schema") == "blast_database_population_relation_v1"
                and relation.get("search_key") == key and relation.get("status") == "available"
                and relation.get("reason_codes") == [] and relation.get("association_results")
                and all(r["status"] == "available" and r["reason_codes"] == [] for r in relation["association_results"])):
            resolved.append(mapped[index])
    return resolved

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
