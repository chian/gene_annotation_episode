"""Captured-input interpretation and deterministic additional-BLAST sheet population.

The five closed wire schemas below describe supplied data, not grading rules.
Validation is pure. Preparation reads only authenticated catalog paths. Population
uses the public 303/305/306/311/312 ports and never calculates scientific scores.
Raw payloads, source identities and unresolved relations remain inspectable.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator

from . import blast_iteration_inputs as _iteration
from . import blast_profile_inputs as _profile
from . import blast_pssm_inputs as _pssm
from . import blast_sequence_database as _sequence
from . import blast_vdb_inputs as _vdb
from . import native_blast_database_contracts as _contracts
from .domain import parse_sequences


__all__ = ["metadata_schema_registry", "validate_native_blast_database_metadata_payload",
           "prepare_native_blast_database_inputs", "populate_native_blast_database_sheets"]


def _object(**fields):
    return {"type": "object", "properties": fields, "required": list(fields),
            "additionalProperties": False}


def _array(item):
    return {"type": "array", "items": item}


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def _enum(*values):
    return {"enum": list(values)}


def _slot(schema, kind):
    return dict(schema, **{"x-wire": kind})


_STRING = {"type": "string"}
_TOKEN = {"type": "string", "minLength": 1, "maxLength": 512,
          "pattern": r"^[^\x00\r\n]+$"}
_I0 = {"type": "integer", "minimum": 0}
_I1 = {"type": "integer", "minimum": 1}
_NUMBER = {"type": "number"}
_BOOL = {"type": "boolean"}
_SHA = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
_POINTER = {"type": "string", "pattern": r"^(?:/(?:[^~]|~[01])*)?$"}
_NATIVE = {}  # finite JSON is checked before schema validation
_NATIVE_OBJECT = {"type": "object"}
_INTERVAL = {"type": "array", "prefixItems": [_I0, _I1], "minItems": 2, "maxItems": 2,
             "x-wire": "interval"}
_IDENTIFIER = _object(namespace=_TOKEN, value=_TOKEN, version=_nullable(_TOKEN))
_FUNCTION = _object(namespace=_TOKEN, value=_TOKEN)
_PROV = _slot(_object(source_ref=_TOKEN, pointer=_POINTER), "provenance")
_SOURCE = _slot(_TOKEN, "source")
_SEARCH = _slot(_object(output_key=_TOKEN, member_ordinal=_nullable(_I0), report_index=_I0,
                        search_pointer=_POINTER), "search")
_PSSM = _slot(_object(document_key=_TOKEN, record_ordinal=_I0), "pssm")
_LINEAGE = _array(_object(taxid=_I1, rank=_TOKEN, name=_nullable(_STRING)))
_DESCRIPTION = _object(id=_nullable(_STRING), accession=_nullable(_STRING),
                       title=_nullable(_STRING), taxid=_nullable(_I1))
_DATABASE = _slot(_object(namespace=_TOKEN, value=_TOKEN, version=_nullable(_TOKEN),
    release=_nullable(_TOKEN), scope=_nullable(_TOKEN),
    preparation_type=_enum("sequence_database", "rps", "delta", "unknown"), source=_PROV), "database")
_OPERAND = _object(role=_enum("query", "subject", "database", "profile", "msa", "checkpoint"),
    artifact_key=_nullable(_TOKEN), record_ordinal=_nullable(_I0), native_id=_nullable(_STRING),
    native_title=_nullable(_STRING), subject_ref=_nullable(_TOKEN),
    molecule=_enum("dna", "rna", "protein", "unknown"), length=_nullable(_I1),
    selected_interval=_nullable(_INTERVAL), identity=_nullable(_IDENTIFIER))
_ADDRESS = {"oneOf": [
    _object(kind=_enum("input"), input_key=_TOKEN),
    _object(kind=_enum("output"), output_key=_TOKEN, relative_path=_TOKEN),
    _object(kind=_enum("database_manifest"), database_key=_TOKEN),
    _object(kind=_enum("database_metadata_manifest"), database_key=_TOKEN, manifest_index=_I0),
    _object(kind=_enum("database_sidecar"), database_key=_TOKEN,
            role=_enum("preparation_input_manifest", "offline_configuration")),
    _object(kind=_enum("received"), source_ref=_TOKEN, artifact_ref=_TOKEN, sha256=_SHA, size_bytes=_I0)]}
_DOCUMENT = _object(document_key=_TOKEN, artifact=_ADDRESS, format=_enum("json", "text", "fasta",
    "clustal", "scoremat_asn_text", "runinfo_csv", "blast_vdb_cmd_table", "ncbi_gbseq_xml"))
_SEQUENCE_BINDING = _object(report_index=_I0, hit_index=_I0, kind=_enum("full_sequence_digest"),
    sequence_group=_TOKEN, algorithm=_enum("sha256"), digest=_SHA, molecule=_enum("aa", "nt"),
    sequence_length=_I1, source_ref=_SOURCE, pointer=_POINTER,
    linkage_source_ref=_SOURCE, linkage_pointer=_POINTER)
_SEQUENCE_PROOF = _slot(_object(binding_index=_I0, document_key=_TOKEN,
    representation=_enum("fasta_record", "json_sequence"), record_ordinal=_nullable(_I0),
    sequence_pointer=_nullable(_POINTER), molecule=_enum("aa", "nt"), sha256=_SHA, length=_I1), "proof")
_BOUND_SEQUENCE = _object(search_key=_SEARCH, binding=_SEQUENCE_BINDING)
_DESCRIPTION_BINDING = _object(report_index=_I0, hit_index=_I0, description_index=_I0,
    metadata_index=_I0, native_description=_DESCRIPTION,
    metadata_identifier=_object(namespace=_TOKEN, value=_TOKEN), metadata_source_ref=_SOURCE,
    metadata_pointer=_POINTER, linkage_source_ref=_SOURCE, linkage_pointer=_POINTER)
_ASSEMBLY = _object(accession=_nullable(_TOKEN),
    completeness_fraction=_nullable({"type": "number", "minimum": 0, "maximum": 1}),
    contamination_fraction=_nullable({"type": "number", "minimum": 0}),
    contig_count=_nullable(_I0), contig_n50=_nullable(_I0), total_sequence_length=_nullable(_I0),
    quality_method=_nullable(_TOKEN), quality_version=_nullable(_TOKEN),
    measurement_methods=_object(**{k: _nullable(_TOKEN) for k in (
        "completeness_fraction", "contamination_fraction", "contig_count", "contig_n50", "total_sequence_length")}),
    source=_SOURCE, linkage_source=_SOURCE)
_SEQUENCE_RECORD = _object(identifier_namespace=_TOKEN, accession=_TOKEN, source=_SOURCE,
    native_pointer=_POINTER, taxid=_nullable(_I1), lineage=_LINEAGE,
    functions=_array(_object(function=_TOKEN, evidence=_array(_NATIVE), source=_SOURCE)),
    origin={"type": "object", "propertyNames": _TOKEN,
            "additionalProperties": {"type": ["string", "number", "boolean", "null"]}},
    assembly=_nullable(_ASSEMBLY), sequence_group=_nullable(_TOKEN), study_groups=_array(_TOKEN), native_record=_NATIVE)
_SEQUENCE_POPULATION = _object(database=_TOKEN, release=_nullable(_TOKEN), scope=_TOKEN,
    count_unit=_enum("unique_sequences", "sequence_groups"), total_count=_I1,
    function_counts={"type": "object", "propertyNames": _TOKEN, "additionalProperties": _I0}, source=_SOURCE)
_PROFILE_RECORD = _object(profile_key=_TOKEN, database_identity=_DATABASE, model_identifier=_IDENTIFIER,
    pssm_key=_nullable(_PSSM), num_columns=_nullable(_I1), master_sequence_ref=_nullable(_PROV),
    specific_bits_threshold=_nullable(_NUMBER), reporting_bits_threshold=_nullable(_NUMBER),
    source=_PROV, native_record=_NATIVE_OBJECT)
_PROFILE_BINDING = _object(search_key=_SEARCH, hit_ordinal=_I0, description_ordinal=_I0,
    profile_key=_TOKEN, native_description=_DESCRIPTION, provenance=_PROV)
_PROFILE_FUNCTION = _object(profile_key=_TOKEN, function=_FUNCTION, evidence_refs=_array(_PROV), provenance=_PROV)
_MODEL_RELATION = _object(left_profile_key=_TOKEN, right_profile_key=_TOKEN,
    relation=_enum("identical_model", "same_family", "same_superfamily", "overlapping_training_set"), provenance=_PROV)
_EVIDENCE = _object(origin=_enum("supplied_source_record"), source=_PROV, source_format=_TOKEN,
    original_record={"type": ["object", "array", "string"]}, extractor={"type": "null"})
_SNAPSHOT = _object(release=_nullable(_TOKEN), snapshot_id=_nullable(_TOKEN), manifest_sha256=_nullable(_SHA))
_SELECTED = _object(kind=_enum("accession", "path", "alias"), value=_TOKEN)
_DATASET = _object(dataset_key=_TOKEN, identifier=_nullable(_IDENTIFIER),
    dataset_type=_enum("sra", "csra", "wgs", "unknown"), selected_input=_SELECTED, snapshot=_SNAPSHOT,
    search_context=_object(search_key=_SEARCH, sra_mode=_enum(0, 1, 2, None),
        include_filtered_reads=_nullable(_BOOL), subject_genetic_code=_nullable(_I1), input_pssm_key=_nullable(_PSSM),
        source=_PROV, query_extent=_object(mode=_enum("full", "interval", "unknown"),
            interval=_nullable(_INTERVAL), source=_nullable(_PROV))),
    run_identifiers=_array(_IDENTIFIER), sample_links=_array(_object(sample_key=_TOKEN,
        sample_identifier=_IDENTIFIER, biosample_identifier=_nullable(_IDENTIFIER), source=_PROV)),
    assembly_links=_array(_object(assembly_identifier=_IDENTIFIER, source=_PROV)),
    metadata_keys=_array(_TOKEN), source=_PROV)
_MEMBER_KIND = _enum("read", "reference", "wgs_sequence", "unknown")
_MEMBER_KEY = _object(dataset_key=_TOKEN, member_kind=_MEMBER_KIND, member_identifier=_IDENTIFIER)
_MEMBER_BINDING = _object(search_key=_SEARCH, hit_ordinal=_I0, description_ordinal=_I0,
    native_description=_DESCRIPTION, dataset_key=_TOKEN, member_kind=_MEMBER_KIND, member_identifier=_IDENTIFIER,
    relationship=_enum("reported_origin", "catalog_membership"),
    read_identity=_nullable(_object(native_read_name=_TOKEN, spot_id=_nullable(_TOKEN), read_index=_nullable(_I0), source=_PROV)),
    reference_identity=_nullable(_object(identifier=_IDENTIFIER, full_length=_nullable(_I1), sequence_sha256=_nullable(_SHA), source=_PROV)),
    sample_key=_nullable(_TOKEN), provenance=_PROV)
_ENTITY = _slot(_object(kind=_enum("dataset", "sample", "member", "feature", "query_master"),
    dataset_key=_nullable(_TOKEN), member_identifier=_nullable(_IDENTIFIER), sample_key=_nullable(_TOKEN),
    feature_identifier=_nullable(_IDENTIFIER), pssm_key=_nullable(_PSSM)), "entity")
_VDB_ISSUE = _object(code=_TOKEN, search_key=_nullable(_SEARCH), hit_ordinal=_nullable(_I0),
    hsp_ordinal=_nullable(_I0), source_pointer=_nullable(_POINTER), details=_NATIVE_OBJECT)
_VDB_RECORD = _object(metadata_key=_TOKEN, entity=_ENTITY, linkage_source=_nullable(_PROV),
    source_format=_enum("supplied_explicit"), source_version=_nullable(_TOKEN),
    native_record={"type": ["object", "string"]}, source=_PROV, identifiers=_array(_IDENTIFIER),
    sequence=_nullable(_object(symbols=_STRING, molecule=_enum("nt", "aa"), length=_I1, sha256=_SHA)),
    functions=_array(_object(function=_FUNCTION, evidence=_array(_NATIVE_OBJECT), source=_PROV)),
    taxid=_nullable(_I1), taxid_scope=_enum("entity_organism", "sample_context", "reported_subject", "unknown"), lineage=_LINEAGE,
    assembly=_nullable(_object(identifier=_IDENTIFIER, completeness_percent=_nullable(_NUMBER),
        contamination_percent=_nullable(_NUMBER), contig_count=_nullable(_I0), contig_n50=_nullable(_I0),
        total_sequence_length=_nullable(_I0), method=_nullable(_TOKEN), method_version=_nullable(_TOKEN),
        source=_PROV, linkage_source=_PROV)),
    feature=_nullable(_object(feature_identifier=_IDENTIFIER, key=_TOKEN, location=_STRING,
        segments=_array(_INTERVAL), strand=_enum(-1, 1, None), partial5=_nullable(_BOOL), partial3=_nullable(_BOOL),
        codon_start=_enum(1, 2, 3, None), genetic_code=_nullable(_I1), translation=_nullable(_STRING),
        qualifiers=_array(_object(name=_TOKEN, value=_nullable(_STRING))), member_sequence_metadata_key=_nullable(_TOKEN))),
    master_mapping=_nullable(_object(pssm_key=_PSSM, num_columns=_I1,
        columns=_array(_object(column=_I0, master_position=_nullable(_I0), symbol=_STRING)))),
    extraction_method=_enum("supplied_explicit"), issues=_array(_VDB_ISSUE))
_FEATURE_BINDING = _object(search_key=_SEARCH, hit_ordinal=_I0, member_binding_index=_I0,
    member_identifier=_IDENTIFIER, feature_identifier=_IDENTIFIER, feature_kind=_TOKEN,
    member_interval=_INTERVAL, segments=_array(_INTERVAL), location_status=_enum("exact", "partial", "unsupported"),
    strand=_enum(-1, 1, None), genetic_code=_nullable(_I1), codon_start=_enum(1, 2, 3, None),
    function=_nullable(_FUNCTION), feature_sequence_sha256=_nullable(_SHA),
    translation_metadata_key=_nullable(_TOKEN), provenance=_PROV)
_POP_ENTITY = _slot(_object(kind=_enum("read", "reference", "wgs_sequence", "unique_sequence", "feature", "sample"),
    member_key=_nullable(_MEMBER_KEY), sequence_group_key=_nullable(_TOKEN),
    feature_identifier=_nullable(_IDENTIFIER), sample_key=_nullable(_TOKEN)), "population_entity")
_POPULATION = _object(population_key=_TOKEN, datasets=_array(_object(dataset_key=_TOKEN,
    identifier=_nullable(_IDENTIFIER), snapshot=_SNAPSHOT, sra_mode=_enum(0, 1, 2, None), include_filtered_reads=_nullable(_BOOL))),
    count_unit=_enum("reads", "references", "wgs_sequences", "unique_sequences", "features", "samples"),
    scope=_enum("searched_population", "dataset_census", "supplied_subset"), total_count=_nullable(_I0), complete=_BOOL,
    members=_nullable(_array(_POP_ENTITY)), function_counts=_nullable(_array(_object(function=_FUNCTION,
        count=_I0, assignment_scope=_enum("whole_sequence", "feature", "sample"), source=_PROV))),
    function_members=_nullable(_array(_object(function=_FUNCTION, entities=_array(_POP_ENTITY)))),
    source=_PROV, native_record=_NATIVE_OBJECT)
_EXTRACTION = _object(dataset_key=_TOKEN, selected_input=_SELECTED, snapshot=_SNAPSHOT,
    entry_identifiers=_array(_IDENTIFIER), native_returncode=_nullable({"type": "integer"}), producer_complete=_nullable(_BOOL),
    include_filtered_reads=_nullable(_BOOL), reference_selection=_nullable(_BOOL),
    outfmt=_enum("%i\t%a\t%l\t%s"), source=_PROV)
_PARSED_SOURCE = _slot(_object(document_key=_TOKEN,
    parser=_enum("runinfo_csv", "blast_vdb_cmd_table", "ncbi_gbseq_xml"), source_version=_nullable(_TOKEN),
    extraction_context=_nullable(_EXTRACTION)), "parsed_source")
_METADATA_BINDING = _object(binding_key=_TOKEN,
    record_key=_object(source_ref=_SOURCE, record_ordinal=_I0), metadata_key=_TOKEN, entity=_ENTITY,
    parent_metadata_key=_nullable(_TOKEN), member_binding_index=_nullable(_I0),
    identifier_links=_array(_object(source_identifier=_IDENTIFIER, target_identifier=_IDENTIFIER,
        representation=_enum("literal", "sra_general_tag"), source=_PROV)), source=_PROV)


def _payload(consumer, **fields):
    schema_id = "native_blast_database_" + consumer + "_metadata_v1"
    return _object(schema=_enum(schema_id), documents=_array(_DOCUMENT), **fields)


_SCHEMAS = {
    "query_identity": _payload("query", sequence_records=_array(_object(input_key=_TOKEN, record_ordinal=_I0,
        subject_ref=_nullable(_TOKEN), identity=_nullable(_IDENTIFIER), source=_PROV)),
        effective_msa_masters=_array(_object(input_key=_TOKEN, record_ordinal=_I0, source=_PROV)),
        master_subjects=_array(_object(kind=_enum("msa", "pssm"), input_key=_TOKEN, record_ordinal=_I0,
            subject_ref=_TOKEN, sequence_sha256=_SHA, source=_PROV)),
        search_bindings=_array(_slot(_object(search_key=_SEARCH, stage=_enum("sequence_database", "domain_database", None),
            biological_round=_nullable(_I1), database_key=_nullable(_TOKEN), input_pssm_key=_nullable(_PSSM),
            provenance=_nullable(_PROV)), "search_binding")),
        target_contexts=_array(_object(search_key=_SEARCH, taxid=_nullable(_I1), lineage=_LINEAGE,
            independent_of_search=_nullable(_BOOL), source=_PROV))),
    "sequence_database": _payload("sequence", searches=_array(_object(search_key=_SEARCH,
        reference_metadata=_array(_SEQUENCE_RECORD),
        description_bindings=_array(_object(search_key=_SEARCH, binding=_DESCRIPTION_BINDING)),
        sequence_identity_bindings=_array(_BOUND_SEQUENCE), sequence_proofs=_array(_SEQUENCE_PROOF),
        database_profile=_nullable(_SEQUENCE_POPULATION)))),
    "profile": _payload("profile", searches=_array(_object(search_key=_SEARCH,
        profile_records=_array(_PROFILE_RECORD), profile_bindings=_array(_PROFILE_BINDING),
        function_bindings=_array(_PROFILE_FUNCTION), model_relations=_array(_MODEL_RELATION)))),
    "iteration": _payload("iteration", checkpoint_bindings=_array(_object(pssm_key=_PSSM,
        role=_enum("input", "after_search", "output"), search_key=_nullable(_SEARCH),
        biological_round=_nullable(_I1), provenance=_PROV)), comparison_pairs=_array(_object(comparison_key=_TOKEN,
        earlier_search_key=_SEARCH, later_search_key=_SEARCH,
        identity_basis=_enum("full_sequence_digest", "profile_model_identifier"), relation_source=_PROV)),
        inclusion_records=_array(_object(record_key=_TOKEN, pssm_key=_PSSM, search_key=_nullable(_SEARCH),
            membership_kind=_enum("checkpoint_sequence_members"), query_membership=_enum("included", "excluded", "unknown"),
            complete=_BOOL, members=_array(_object(identity=_IDENTIFIER, provenance=_PROV)), evidence=_EVIDENCE)),
        convergence_records=_array(_object(record_key=_TOKEN, search_key=_nullable(_SEARCH),
            query_operand=_nullable(_OPERAND), native_converged=_BOOL, evidence=_EVIDENCE))),
    "vdb": _payload("vdb", searches=_array(_object(search_key=_SEARCH, dataset_records=_array(_DATASET),
        member_bindings=_array(_MEMBER_BINDING), sequence_identity_bindings=_array(_BOUND_SEQUENCE),
        sequence_proofs=_array(_SEQUENCE_PROOF), feature_bindings=_array(_FEATURE_BINDING),
        reference_metadata=_array(_VDB_RECORD), population_records=_array(_POPULATION),
        parsed_sources=_array(_PARSED_SOURCE), metadata_bindings=_array(_METADATA_BINDING))))}


def metadata_schema_registry():
    """Return the five literal supported tuples, detached from module state."""
    module = __name__
    return [dict(consumer=consumer, schema_id=schema["properties"]["schema"]["enum"][0],
        validator_module=module, validator_function="_validate_" + validator + "_metadata",
        populator_module=pop_module, populator_function=pop_function)
        for consumer, validator, pop_module, pop_function in (
            ("query_identity", "query", module, "prepare_native_blast_database_inputs"),
            ("sequence_database", "sequence", "gene_annotation_episode.blast_sequence_database", "populate_blast_sequence_database_sheet"),
            ("profile", "profile", "gene_annotation_episode.blast_profile_inputs", "populate_blast_profile_sheet"),
            ("iteration", "iteration", "gene_annotation_episode.blast_iteration_inputs", "populate_blast_iteration_sheet"),
            ("vdb", "vdb", "gene_annotation_episode.blast_vdb_inputs", "populate_blast_vdb_sheet"))
        for schema in [_SCHEMAS[consumer]]]


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _copy(v) for k, v in value.items()}
    raise ValueError("native_blast_metadata_finite_json_required")


def _token(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(contents):
    return hashlib.sha256(contents).hexdigest()


def _escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _pointer_get(value, pointer):
    if not Draft202012Validator(_POINTER).is_valid(pointer):
        raise ValueError("pointer_invalid")
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            if re.fullmatch(r"0|[1-9][0-9]*", part) is None:
                raise ValueError("pointer_index_invalid")
            value = value[int(part)]
        elif type(value) is dict:
            value = value[part]
        else:
            raise ValueError("pointer_unresolved")
    return value


def _decode(contents):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError("nonfinite_json")
    return _copy(json.loads(contents, object_pairs_hook=pairs, parse_constant=bad_constant))


def _issue(descriptor, code, pointer, detail, *, document=None, search=None):
    return dict(code="native_blast_metadata_" + code, input_key=descriptor["input_key"],
        consumer=descriptor["consumer"], schema_id=descriptor["schema_id"], pointer=pointer,
        document_key=document, search_address=deepcopy(search), detail_code=detail)


class _Invalid(ValueError):
    def __init__(self, pointer, detail, code="payload_invalid", document=None, search=None):
        self.pointer, self.detail, self.code = pointer, detail, code
        self.document, self.search = document, search


def _validate_shape(payload, consumer):
    errors = list(Draft202012Validator(_SCHEMAS[consumer]).iter_errors(payload))
    if errors:
        error = errors[0]
        pointer = "".join("/" + _escape(p) for p in error.absolute_path)
        raise _Invalid(pointer, "closed_payload_shape_invalid")
    return payload


def _validate_query_metadata(payload):
    return _validate_shape(payload, "query_identity")


def _validate_sequence_metadata(payload):
    return _validate_shape(payload, "sequence_database")


def _validate_profile_metadata(payload):
    return _validate_shape(payload, "profile")


def _validate_iteration_metadata(payload):
    for field in ("inclusion_records", "convergence_records"):
        rows = payload.get(field, []) if type(payload) is dict else []
        for index, row in enumerate(rows if type(rows) is list else []):
            evidence = row.get("evidence") if type(row) is dict else None
            if type(evidence) is dict and (evidence.get("origin") == "native_extractor_output"
                                          or evidence.get("extractor") is not None):
                raise _Invalid(f"/{field}/{index}/evidence", "extractor_not_registered", "extractor_unbound")
    return _validate_shape(payload, "iteration")


def _validate_vdb_metadata(payload):
    _validate_shape(payload, "vdb")
    for i, unit in enumerate(payload["searches"]):
        for j, binding in enumerate(unit["sequence_identity_bindings"]):
            if binding["binding"]["molecule"] != "nt":
                raise _Invalid(f"/searches/{i}/sequence_identity_bindings/{j}/binding/molecule", "vdb_member_molecule_invalid")
        for j, dataset in enumerate(unit["dataset_records"]):
            extent = dataset["search_context"]["query_extent"]
            if ((extent["mode"] == "interval") != (extent["interval"] is not None)
                    or (extent["mode"] == "unknown") != (extent["source"] is None)):
                raise _Invalid(f"/searches/{i}/dataset_records/{j}/search_context/query_extent", "query_extent_shape_invalid")
        for j, member in enumerate(unit["member_bindings"]):
            if (member["read_identity"] is not None and member["member_kind"] != "read"
                    or member["reference_identity"] is not None and member["member_kind"] not in {"reference", "wgs_sequence"}):
                raise _Invalid(f"/searches/{i}/member_bindings/{j}", "member_identity_kind_conflict")
        for j, record in enumerate(unit["reference_metadata"]):
            kind = record["entity"]["kind"]
            if (record["sequence"] is not None and kind not in {"member", "query_master"}
                    or record["feature"] is not None and kind != "feature"
                    or record["master_mapping"] is not None and kind != "query_master"):
                raise _Invalid(f"/searches/{i}/reference_metadata/{j}", "metadata_entity_payload_conflict")
    return payload


class _Unresolved(_Invalid):
    pass


def _document_view(document):
    return {k: deepcopy(v) for k, v in document.items() if k not in ("contents", "path")}


def _schema_branch(schema, value):
    if "anyOf" in schema:
        return next((s for s in schema["anyOf"] if Draft202012Validator(s).is_valid(value)), schema)
    if "oneOf" in schema:
        return next((s for s in schema["oneOf"] if Draft202012Validator(s).is_valid(value)), schema)
    return schema


def _lower_payload(payload, descriptor, catalog, job, issues, normalization_map):
    declared, documents, decoded_documents = {}, {}, {}
    for index, row in enumerate(payload["documents"]):
        key = row["document_key"]
        if key in declared:
            raise _Invalid(f"/documents/{index}/document_key", "document_key_duplicate", document=key)
        declared[key] = row
    for row in catalog["documents"]:
        key = row["document_key"]
        if key in documents or key not in declared:
            raise _Invalid("/documents", "document_catalog_key_conflict", document=key)
        if any(row.get(k) != declared[key][k] for k in ("artifact", "format")):
            raise _Invalid("/documents", "document_catalog_address_conflict", document=key)
        address = row["artifact"]
        expected = None
        if address["kind"] == "received":
            if any(row[k] != address[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")):
                raise _Invalid("/documents", "received_document_identity_conflict", document=key)
        elif address["kind"] == "input":
            matches = [r for r in job["inputs"] if r["input_key"] == address["input_key"]]
            expected = matches[0] if len(matches) == 1 else None
            if expected is None:
                raise _Invalid("/documents", "input_document_not_selected", document=key)
        elif address["kind"].startswith("database_"):
            matches = [r for r in job["databases"] if r["database_key"] == address["database_key"]]
            if len(matches) != 1:
                raise _Invalid("/documents", "database_document_not_selected", document=key)
            selected = matches[0]
            if address["kind"] == "database_manifest":
                expected = selected["manifest_file"]
            elif address["kind"] == "database_metadata_manifest":
                originals = selected["manifest"]["metadata_manifests"]
                if address["manifest_index"] >= len(originals):
                    raise _Invalid("/documents", "original_manifest_index_invalid", document=key)
                expected = originals[address["manifest_index"]]
                if row["artifact_key"] != _metadata_capture_key(selected["database_key"], "metadata", expected):
                    raise _Invalid("/documents", "original_manifest_capture_key_conflict", document=key)
            else:
                expected = (selected["manifest"]["preparation"]["input_manifest"] if address["role"] == "preparation_input_manifest"
                            else selected["manifest"]["access"]["offline_configuration"])
                if expected is None or row["artifact_key"] != _metadata_capture_key(selected["database_key"], address["role"], expected):
                    raise _Invalid("/documents", "sidecar_capture_key_conflict", document=key)
        elif not any(r["output_key"] == address["output_key"] for r in job["outputs"]):
            raise _Invalid("/documents", "output_document_not_selected", document=key)
        if expected is not None and any(row[k] != expected[k] for k in ("sha256", "size_bytes")):
            issues.append(_issue(descriptor, "source_unavailable", "/documents", "selected_document_digest_conflict", document=key))
            continue
        raw = row["contents"]
        if type(raw) is not bytes or _sha(raw) != row["sha256"] or len(raw) != row["size_bytes"]:
            issues.append(_issue(descriptor, "source_unavailable", "/documents", "document_bytes_conflict", document=key))
            continue
        documents[key] = row
    reports = catalog["primary_reports"]
    if type(reports) is not list or len({r["output_key"] for r in reports}) != len(reports) or len({r["artifact_key"] for r in reports}) != len(reports):
        raise _Invalid("", "primary_report_catalog_duplicate")
    for report in reports:
        selected = [r for r in job["outputs"] if r["output_key"] == report["output_key"]
                    and r["role"] == "primary_report" and r["path_kind"] == "file" and r["format"] == report["format"]]
        if len(selected) != 1:
            raise _Invalid("", "primary_report_catalog_descriptor_conflict")

    def document(key, pointer):
        if key not in declared:
            raise _Invalid(pointer, "document_key_undeclared", document=key)
        if key not in documents:
            raise _Unresolved(pointer, "document_bytes_unavailable", "source_unavailable", document=key)
        return documents[key]

    def provenance(key, pointer, path):
        doc = document(key, path)
        if doc["format"] == "json":
            try:
                if key not in decoded_documents:
                    decoded_documents[key] = _decode(doc["contents"])
                _pointer_get(decoded_documents[key], pointer)
            except (ValueError, KeyError, IndexError, UnicodeError):
                raise _Invalid(path, "literal_json_pointer_unresolved", document=key) from None
        elif pointer:
            # A parser address is checked against its saved parse after preparation;
            # it is never represented as a pointer into XML/ASN/plain text bytes.
            parser_formats = {r["document_key"]: r["parser"]
                for search in payload.get("searches", []) for r in search.get("parsed_sources", [])}
            if parser_formats.get(key) != doc["format"] or not re.match(r"^/records/(0|[1-9][0-9]*)(/|$)", pointer):
                raise _Invalid(path, "source_locator_not_supported", document=key)
        return {"source_ref": doc["source_ref"], "pointer": pointer}

    def walk(value, schema, path):
        schema = _schema_branch(schema, value)
        if value is None:
            return None
        kind = schema.get("x-wire")
        if kind == "source":
            return document(value, path)["source_ref"]
        if kind == "provenance":
            return provenance(value["source_ref"], value["pointer"], path)
        if kind == "search":
            reports = [r for r in catalog.get("primary_reports", []) if r["output_key"] == value["output_key"]]
            if len(reports) != 1 or value["member_ordinal"] is not None:
                raise _Unresolved(path, "primary_report_address_unresolved", "relation_unresolved", search=value)
            return {"artifact_key": reports[0]["artifact_key"],
                    **{k: value[k] for k in ("member_ordinal", "report_index", "search_pointer")}}
        if kind == "pssm":
            doc = document(value["document_key"], path)
            if doc["format"] != "scoremat_asn_text" or doc["artifact_key"] is None:
                raise _Unresolved(path, "pssm_artifact_unresolved", "relation_unresolved", document=value["document_key"])
            return json.dumps([doc["artifact_key"], value["record_ordinal"]], separators=(",", ":"))
        if kind == "interval" and value[0] >= value[1]:
            raise _Invalid(path, "interval_order_invalid")
        if kind == "proof":
            document(value["document_key"], path + "/document_key")
            fasta = value["representation"] == "fasta_record"
            if (value["record_ordinal"] is not None) != fasta or (value["sequence_pointer"] is None) != fasta:
                raise _Invalid(path, "sequence_proof_selector_invalid")
        if kind in ("entity", "population_entity"):
            slots = ({"dataset": {"dataset_key"}, "sample": {"dataset_key", "sample_key"},
                "member": {"dataset_key", "member_identifier"}, "feature": {"dataset_key", "member_identifier", "feature_identifier"},
                "query_master": {"pssm_key"}} if kind == "entity" else {
                "read": {"member_key"}, "reference": {"member_key"}, "wgs_sequence": {"member_key"},
                "unique_sequence": {"sequence_group_key"}, "feature": {"member_key", "feature_identifier"}, "sample": {"sample_key"}})
            if {k for k, v in value.items() if k != "kind" and v is not None} != slots[value["kind"]]:
                raise _Invalid(path, "entity_slots_invalid")
        if kind == "parsed_source":
            doc = document(value["document_key"], path)
            table = value["parser"] == "blast_vdb_cmd_table"
            if doc["format"] != value["parser"] or table != (value["extraction_context"] is not None):
                raise _Invalid(path, "native_metadata_parser_context_invalid")
            if table and (value["source_version"] is None or not value["extraction_context"]["entry_identifiers"]
                          or any(i["value"] == "all" for i in value["extraction_context"]["entry_identifiers"])):
                raise _Invalid(path, "specific_entry_extraction_required")
        if type(value) is list:
            return [walk(v, schema.get("items", {}), path + "/" + str(i)) for i, v in enumerate(value)]
        if type(value) is dict:
            properties = schema.get("properties", {})
            result = {k: walk(v, properties.get(k, {}), path + "/" + _escape(k)) for k, v in value.items()}
            # String provenance slots have paired pointers in these exact shapes.
            for source_field, pointer_field in (("source", "native_pointer"), ("source_ref", "pointer"),
                    ("metadata_source_ref", "metadata_pointer"), ("linkage_source_ref", "linkage_pointer")):
                if source_field in properties and properties[source_field].get("x-wire") == "source" and pointer_field in properties:
                    provenance(value[source_field], value[pointer_field], path + "/" + pointer_field)
            if kind == "search_binding":
                key = value["database_key"]
                matches = [d for d in job["databases"] if d["database_key"] == key] if key is not None else []
                if key is not None and len(matches) != 1:
                    issues.append(_issue(descriptor, "relation_unresolved", path + "/database_key", "selected_database_unresolved"))
                result.pop("database_key")
                result["database_identity"] = deepcopy(matches[0]["identity"]) if len(matches) == 1 else None
            if kind == "database":
                fields = set(result) - {"source"}
                if not any(all(result[k] == d["identity"][k] for k in fields) for d in job["databases"]):
                    issues.append(_issue(descriptor, "relation_conflict", path, "selected_database_identity_conflict"))
            return result
        return value

    result = {"schema": payload["schema"], "documents": []}
    for index, row in enumerate(payload["documents"]):
        if row["document_key"] in documents:
            normalization_map.append(dict(normalized_pointer=f"/documents/{len(result['documents'])}", payload_pointer=f"/documents/{index}"))
            result["documents"].append(_document_view(documents[row["document_key"]]))
        else:
            issues.append(_issue(descriptor, "source_unavailable", f"/documents/{index}", "document_bytes_unavailable", document=row["document_key"]))
    properties = _SCHEMAS[descriptor["consumer"]]["properties"]
    for field in payload.keys() - {"schema", "documents"}:
        result[field] = []
        for index, row in enumerate(payload[field]):
            pointer = f"/{field}/{index}"
            try:
                lowered = walk(row, properties[field]["items"], pointer)
            except _Unresolved as error:
                issues.append(_issue(descriptor, error.code, error.pointer, error.detail, document=error.document, search=error.search))
            else:
                normalization_map.append(dict(normalized_pointer=f"/{field}/{len(result[field])}", payload_pointer=pointer))
                result[field].append(lowered)
    return result


def _validate_catalog(catalog):
    if type(catalog) is not dict or set(catalog) != {"descriptor", "documents", "primary_reports", "bundle_source_ref", "bundle_artifact_ref"}:
        raise _Invalid("", "document_catalog_fields_invalid")
    descriptor_schema = _object(input_key=_TOKEN, consumer=_enum(*_SCHEMAS), schema_id=_TOKEN,
        artifact_ref=_TOKEN, sha256=_SHA, size_bytes=_I0, origin=_enum("original_job_input", "selected_results_input"))
    if not Draft202012Validator(descriptor_schema).is_valid(catalog["descriptor"]):
        raise _Invalid("", "metadata_descriptor_shape_invalid")
    if not all(Draft202012Validator(_TOKEN).is_valid(catalog[k]) for k in ("bundle_source_ref", "bundle_artifact_ref")):
        raise _Invalid("", "bundle_source_reference_invalid")
    document_schema = _object(**_DOCUMENT["properties"], artifact_key=_nullable(_TOKEN), artifact_ref=_TOKEN,
        source_ref=_TOKEN, sha256=_SHA, size_bytes=_I0)
    if type(catalog["documents"]) is not list:
        raise _Invalid("", "document_catalog_array_required")
    for row in catalog["documents"]:
        if type(row) is not dict or "contents" not in row or not Draft202012Validator(document_schema).is_valid({k: v for k, v in row.items() if k != "contents"}):
            raise _Invalid("", "resolved_document_shape_invalid")
    report_schema = _object(output_key=_TOKEN, artifact_key=_TOKEN, artifact_ref=_TOKEN, source_ref=_TOKEN,
        sha256=_SHA, size_bytes=_I0, format=_enum("json15", "tabular6", "tabular7"))
    if not Draft202012Validator(_array(report_schema)).is_valid(catalog["primary_reports"]):
        raise _Invalid("", "primary_report_catalog_shape_invalid")


def validate_native_blast_database_metadata_payload(payload, *, descriptor, document_catalog, job):
    """Validate supplied finite JSON without filesystem, network or calculation.

    The caller authenticates descriptor bytes; prepare additionally checks their
    exact decoded equality. The catalog carries only already authenticated bytes.
    """
    value = _copy(payload)
    result = {k: descriptor[k] for k in ("consumer", "schema_id", "input_key", "artifact_ref", "sha256")}
    result.update(status="valid", payload=value, normalized=None, normalization_map=[], issues=[])
    registry = {(r["consumer"], r["schema_id"]): r for r in metadata_schema_registry()}
    entry = registry.get((descriptor["consumer"], descriptor["schema_id"]))
    if entry is None:
        result["status"] = "unsupported"
        result["issues"].append(_issue(descriptor, "schema_unsupported", "", "metadata_tuple_unregistered"))
        return result
    try:
        _validate_catalog(document_catalog)
        if document_catalog["descriptor"] != descriptor:
            raise _Invalid("", "descriptor_catalog_conflict")
        globals()[entry["validator_function"]](value)
        result["normalized"] = _lower_payload(value, descriptor, document_catalog, job, result["issues"], result["normalization_map"])
    except _Invalid as error:
        result["status"] = "valid" if isinstance(error, _Unresolved) else "invalid"
        result["normalization_map"] = []
        result["issues"].append(_issue(descriptor, error.code, error.pointer, error.detail,
            document=error.document, search=error.search))
    return result


class _Catalog:
    """A per-call byte cache restricted to the supplied authenticated catalog."""
    def __init__(self, catalog, bundle=None):
        self.catalog, self.cache, self.entries, self.decoded = catalog, {}, {}, {}
        for row in catalog["entries"]:
            key = row["artifact_key"]
            if key in self.entries:
                raise ValueError("native_blast_metadata_artifact_key_duplicate")
            if not Path(row["path"]).is_absolute():
                raise ValueError("native_blast_metadata_catalog_path_not_absolute")
            self.entries[key] = row
        if bundle is not None:
            originals = {a["artifact_key"]: a for a in bundle["artifacts"]}
            for key, row in self.entries.items():
                original = originals.get(key)
                if original is None or any(row.get(k) != original[k] for k in original if k != "content_assessment"):
                    raise ValueError("native_blast_metadata_catalog_bundle_conflict")

    def read(self, row):
        signature = (row["path"], row["sha256"], row["size_bytes"])
        if signature not in self.cache:
            try:
                raw = Path(row["path"]).read_bytes()
            except OSError:
                raise _Unresolved("", "artifact_bytes_unavailable", "source_unavailable") from None
            if len(raw) != row["size_bytes"] or _sha(raw) != row["sha256"]:
                raise _Unresolved("", "artifact_digest_conflict", "source_unavailable")
            self.cache[signature] = raw
        return self.cache[signature]

    def json(self, row):
        signature = (row["path"], row["sha256"], row["size_bytes"])
        if signature not in self.decoded:
            self.decoded[signature] = _decode(self.read(row))
        return self.decoded[signature]

    def reference(self, artifact_ref):
        rows = [r for r in self.catalog["entries"] + self.catalog["retained_sources"] if r["artifact_ref"] == artifact_ref]
        identities = {(r["path"], r["sha256"], r["size_bytes"]) for r in rows}
        if len(identities) != 1:
            raise _Unresolved("", "artifact_reference_unresolved", "source_unavailable")
        return rows[0]


def _one(rows, detail):
    if len(rows) != 1:
        raise _Unresolved("", detail, "source_unavailable")
    return rows[0]


def _metadata_capture_key(database_key, role, identity):
    return "database-metadata-" + _sha(_token(dict(database_key=database_key, role=role, identity=identity)).encode())


def _resolve_document(declaration, *, job, bundle, files):
    address = declaration["artifact"]
    kind = address["kind"]
    expected = None
    if kind == "received":
        row = _one([r for r in files.catalog["retained_sources"] if all(r[k] == address[k]
            for k in ("source_ref", "artifact_ref", "sha256", "size_bytes"))], "received_source_not_selected")
    elif kind == "input":
        source = _one([r for r in job["inputs"] if r["input_key"] == address["input_key"]], "input_not_selected")
        capture = _one([r for r in bundle["input_manifest"] if r["input_key"] == address["input_key"]], "input_capture_missing")
        if capture["original_path"] != source["path"]:
            raise _Unresolved("", "input_original_identity_conflict", "source_unavailable")
        row = files.entries.get(capture["artifact_key"])
        expected = source
    elif kind == "output":
        selected = _one([r for r in job["outputs"] if r["output_key"] == address["output_key"]], "output_not_selected")
        capture = _one([r for r in bundle["output_manifest"] if r["output_key"] == address["output_key"]], "output_capture_missing")
        row = _one([files.entries[k] for k in capture["artifact_keys"] if k in files.entries
            and files.entries[k]["relative_path"] == address["relative_path"]], "output_member_unresolved")
        if row["role"] != selected["role"] or row["format"] != selected["format"]:
            raise _Unresolved("", "output_descriptor_conflict", "source_unavailable")
    else:
        selected = _one([r for r in job["databases"] if r["database_key"] == address["database_key"]], "database_not_selected")
        capture = _one([r for r in bundle["database_manifest"] if r["database_key"] == address["database_key"]], "database_capture_missing")
        if kind == "database_manifest":
            expected, key = selected["manifest_file"], capture["manifest_artifact_key"]
        else:
            if kind == "database_metadata_manifest":
                index = address["manifest_index"]
                original = selected["manifest"]["metadata_manifests"]
                if index >= len(original):
                    raise _Unresolved("", "original_manifest_index_unresolved", "source_unavailable")
                expected = original[index]
                slots = capture["metadata_manifest_artifacts"]
                if len(slots) != len(original) or slots[index]["identity"] != expected:
                    raise _Unresolved("", "original_manifest_identity_conflict", "source_unavailable")
                key = slots[index]["artifact_key"]
                role = "metadata"
            else:
                role = address["role"]
                expected = (selected["manifest"]["preparation"]["input_manifest"] if role == "preparation_input_manifest"
                            else selected["manifest"]["access"]["offline_configuration"])
                slot = _one([r for r in capture["sidecar_artifacts"] if r["role"] == role], "sidecar_role_unresolved")
                if expected is None or slot["identity"] != expected:
                    raise _Unresolved("", "sidecar_identity_conflict", "source_unavailable")
                key = slot["artifact_key"]
            if key is not None and key != _metadata_capture_key(selected["database_key"], role, expected):
                raise _Unresolved("", "metadata_capture_key_conflict", "source_unavailable")
        row = files.entries.get(key)
    if row is None:
        raise _Unresolved("", "artifact_bytes_unavailable", "source_unavailable")
    if expected is not None and any(row[k] != expected[k] for k in ("sha256", "size_bytes")):
        raise _Unresolved("", "selected_identity_digest_conflict", "source_unavailable")
    return dict(declaration, artifact_key=row.get("artifact_key"),
        **{k: row[k] for k in ("artifact_ref", "source_ref", "sha256", "size_bytes")}, contents=files.read(row))


def _options(job):
    # The public job validator has already checked N's exact token grammar.
    no_argument = {"-lcase_masking", "-parse_deflines", "-show_gis", "-use_sw_tback", "-subject_besthit",
        "-save_each_pssm", "-save_pssm_after_last_round", "-show_domain_hits", "-ungapped", "-include_filtered_reads", "-no_greedy"}
    selected, i = {}, 0
    while i < len(job["options"]):
        flag = job["options"][i]
        selected[flag] = None if flag in no_argument else job["options"][i + 1]
        i += 1 if flag in no_argument else 2
    selected.update(requested_hit_limit=int(selected["-max_target_seqs"]) if "-max_target_seqs" in selected else None,
                    requested_hsp_limit=int(selected["-max_hsps"]) if "-max_hsps" in selected else None)
    for key in ("inclusion_ethresh", "domain_inclusion_ethresh"):
        if "-" + key in selected:
            selected[key] = float(selected["-" + key])
    return selected


def _input_issue_descriptor(job):
    return dict(input_key=job["query"]["input_key"], consumer="query_identity",
                schema_id="native_blast_database_query_metadata_v1")


def _valid_payloads(prepared, consumer):
    return [r for r in prepared["metadata"] if r["consumer"] == consumer
            and r["status"] == "valid" and r["normalized"] is not None]


def _native_pssm_names(record):
    """Read literal Seq-id/title fields; no alias inference or master decoding."""
    query = record["native_pssm"].get("query")
    fields = query.get("seq") if type(query) is dict else None
    if type(fields) is not list:
        return None, None
    ids, titles = [], []
    for field in fields:
        if type(field) is not dict:
            continue
        for identifier in field.get("id", []) if type(field.get("id")) is list else []:
            if type(identifier) is dict and type(identifier.get("local")) is dict:
                value = identifier["local"].get("str")
                if type(value) is str:
                    ids.append(value)
        for desc in field.get("descr", []) if type(field.get("descr")) is list else []:
            if type(desc) is dict and type(desc.get("title")) is str:
                titles.append(desc["title"])
    return (ids[0] if len(ids) == 1 else None, titles[0] if len(titles) == 1 else None)


def prepare_native_blast_database_inputs(*, job, bundle, artifact_catalog, metadata_payloads, subject_snapshots):
    """Read captured inputs once, prove complete subjects, and prepare collector operands."""
    job = _contracts.validate_native_blast_database_job(job)
    request = _contracts.requested_job_from_native_blast_database(job)
    if bundle["requested_job"] != request:
        raise ValueError("native_blast_metadata_requested_job_conflict")
    files = _Catalog(artifact_catalog, bundle)
    options = _options(job)
    selected = job["query"]["msa_master_record_ordinal"]
    prepared = dict(schema="native_blast_database_prepared_inputs_v1", invocation=dict(
        execution_program=job["program"], scientific_mode="database", resource_kind="hpc",
        query_kind=job["query"]["kind"], reference_kind=("profile" if job["program"] in {"rpsblast", "rpstblastn"}
            else "vdb_mixed" if job["program"].endswith("_vdb") else "sequence"),
        request=request, effective_options=options, operands=[],
        completion={"native_returncode": bundle["process"]["returncode"],
            "producer_complete": bool(bundle.get("sealed_at") and bundle["process"]["started"]
                                      and bundle["process"]["returncode"] == 0 and not bundle["failures"])}),
        query_records=[], selected_master_record_ordinal=selected, effective_master_record_ordinal=selected,
        effective_master_source=None, pssm_sheets=[], msa_sheets=[], metadata=[], resolved_documents=[],
        source_relations=[], issues=[])
    reports = []
    for row in artifact_catalog["entries"]:
        if row["role"] == "primary_report":
            try:
                files.read(row)
            except _Unresolved:
                continue
            reports.append({k: row[k] for k in ("output_key", "artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes", "format")})
    tuple_counts, input_identities = {}, {}
    for raw in metadata_payloads:
        d = raw["descriptor"]
        identity = (d["input_key"], d["consumer"], d["schema_id"])
        tuple_counts[identity] = tuple_counts.get(identity, 0) + 1
        input_identities.setdefault(d["input_key"], set()).add((d["artifact_ref"], d["sha256"], d["size_bytes"]))
    for raw in metadata_payloads:
        descriptor, payload = raw["descriptor"], raw["payload"]
        documents, early = [], []
        try:
            identity = (descriptor["input_key"], descriptor["consumer"], descriptor["schema_id"])
            if tuple_counts[identity] != 1:
                raise _Invalid("", "metadata_descriptor_tuple_duplicate")
            if len(input_identities[descriptor["input_key"]]) != 1:
                raise _Invalid("", "metadata_input_identity_conflict")
            if descriptor["origin"] == "selected_results_input" and any(r["input_key"] == descriptor["input_key"] and r["role"] != "metadata" for r in job["inputs"]):
                raise _Invalid("", "selected_metadata_aliases_nonmetadata_input")
            entry = files.reference(descriptor["artifact_ref"])
            if any(entry[k] != descriptor[k] for k in ("sha256", "size_bytes")):
                raise _Unresolved("", "metadata_descriptor_digest_conflict", "source_unavailable")
            if descriptor["origin"] == "original_job_input":
                matches = [r for r in job["metadata_inputs"] if all(r[k] == descriptor[k] for k in ("input_key", "consumer", "schema_id"))]
                if len(matches) != 1 or entry.get("input_key") != descriptor["input_key"]:
                    raise _Invalid("", "original_metadata_descriptor_conflict")
            try:
                decoded = files.json(entry)
            except (ValueError, UnicodeError):
                payload = None
                raise _Invalid("", "metadata_json_invalid") from None
            if _copy(payload) != decoded:
                raise _Invalid("", "metadata_payload_bytes_conflict")
            declarations = payload.get("documents", []) if type(payload) is dict else []
            if type(declarations) is list:
                for i, declaration in enumerate(declarations):
                    if not Draft202012Validator(_DOCUMENT).is_valid(declaration):
                        continue
                    try:
                        doc = _resolve_document(declaration, job=job, bundle=bundle, files=files)
                    except _Unresolved as error:
                        early.append(_issue(descriptor, error.code, f"/documents/{i}", error.detail,
                                            document=declaration["document_key"]))
                    else:
                        documents.append(doc)
                        prepared["resolved_documents"].append(dict(input_key=descriptor["input_key"], **{
                            k: doc[k] for k in ("document_key", "artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes", "format")}))
            catalog = dict(descriptor=descriptor, documents=documents, primary_reports=reports,
                bundle_source_ref=artifact_catalog["bundle_source_ref"], bundle_artifact_ref=artifact_catalog["bundle_artifact_ref"])
            validation = validate_native_blast_database_metadata_payload(payload,
                descriptor=descriptor, document_catalog=catalog, job=job)
            validation["issues"] = early + validation["issues"]
        except _Invalid as error:
            validation = {k: descriptor[k] for k in ("consumer", "schema_id", "input_key", "artifact_ref", "sha256")}
            validation.update(status="invalid", payload=_copy(payload), normalized=None, normalization_map=[],
                issues=[_issue(descriptor, error.code, error.pointer, error.detail)])
        prepared["metadata"].append(validation)
        prepared["issues"].extend(validation["issues"])
        for issue in validation["issues"]:
            prepared["source_relations"].append({**{k: descriptor[k] for k in ("consumer", "schema_id", "input_key")},
                "pointer": issue["pointer"], "status": "incompatible" if issue["code"].endswith(("conflict", "invalid")) else "unavailable"})

    descriptor = _input_issue_descriptor(job)
    query_key = job["query"]["input_key"]
    query_payloads = [r["normalized"] for r in _valid_payloads(prepared, "query_identity")]
    if job["query"]["kind"] == "msa":
        effective = [r for p in query_payloads for r in p["effective_msa_masters"] if r["input_key"] == query_key]
        if selected is None and len(effective) == 1:
            prepared["effective_master_record_ordinal"] = effective[0]["record_ordinal"]
            prepared["effective_master_source"] = effective[0]["source"]
        elif len(effective) > 1 or selected is not None and any(r["record_ordinal"] != selected for r in effective):
            prepared["issues"].append(_issue(descriptor, "relation_conflict", "/query/msa_master_record_ordinal", "effective_master_conflict"))
            if selected is None:
                prepared["effective_master_record_ordinal"] = None

    snapshots = {}
    for snapshot in subject_snapshots:
        try:
            entry = files.reference(snapshot["sequence_artifact_ref"])
            if entry["path"] != snapshot["sequence_path"]:
                raise _Unresolved("", "subject_path_not_cataloged", "source_unavailable")
            symbols = files.read(entry).decode("ascii")
            alphabet = {"dna": "ACGTRYSWKMBDHVN", "rna": "ACGURYSWKMBDHVN", "protein": "ABCDEFGHIKLMNPQRSTVWXYZJUO*"}.get(snapshot["molecule"], "")
            if (len(symbols) != snapshot["length"] or _sha(symbols.encode("ascii")) != snapshot["sequence_sha256"]
                    or not symbols or symbols != symbols.upper() or not set(symbols) <= set(alphabet)):
                raise _Unresolved("", "subject_full_sequence_conflict", "relation_conflict")
            snapshots.setdefault(snapshot["subject_ref"], []).append((snapshot, symbols))
        except (ValueError, UnicodeError, _Invalid):
            prepared["issues"].append(_issue(descriptor, "relation_conflict", "/subject_snapshots", "subject_full_sequence_unverified"))

    def add_record(entry, ordinal, symbols, native_id, native_title, molecule, *, compatible=True, identity=None):
        digest, subject, status = _sha(symbols.encode("ascii")), None, "unavailable" if compatible else "incompatible"
        kind = job["query"]["kind"]
        relations = [r for p in query_payloads for r in p["sequence_records" if kind == "sequence" else "master_subjects"]
            if r["input_key"] == query_key and r["record_ordinal"] == ordinal and (kind == "sequence" or r["kind"] == kind)]
        if len(relations) == 1:
            relation = relations[0]
            if kind == "sequence":
                identity = relation["identity"]
            candidates = snapshots.get(relation["subject_ref"], [])
            if compatible and len(candidates) == 1:
                snap, actual = candidates[0]
                if actual == symbols and snap["molecule"] == molecule and snap["length"] == len(symbols) and snap["sequence_sha256"] == digest and (
                        kind == "sequence" or relation["sequence_sha256"] == digest):
                    subject, status = relation["subject_ref"], "available"
                else:
                    status = "incompatible"
        elif len(relations) > 1:
            status = "incompatible"
        interval = None
        if "-query_loc" in options:
            start, end = map(int, options["-query_loc"].split("-"))
            if end > len(symbols):
                compatible, status = False, "incompatible"
                prepared["issues"].append(_issue(descriptor, "relation_conflict", "/options", "query_interval_exceeds_full_length"))
            else:
                interval = [start - 1, end]
        row = dict(input_key=query_key, artifact_key=entry["artifact_key"], artifact_ref=entry["artifact_ref"],
            record_ordinal=ordinal, native_id=native_id, native_title=native_title, sequence=symbols, molecule=molecule,
            length=len(symbols), sequence_sha256=digest, selected_interval=interval, subject_ref=subject, binding_status=status)
        prepared["query_records"].append(row)
        if compatible:
            prepared["invocation"]["operands"].append(dict(role="query", artifact_key=entry["artifact_key"],
                record_ordinal=ordinal, native_id=native_id, native_title=native_title, subject_ref=subject,
                molecule=molecule, length=len(symbols), selected_interval=interval, identity=identity))

    for entry in artifact_catalog["entries"]:
        if entry["role"] not in {"query_sequence", "query_pssm", "query_msa", "checkpoint_asn"}:
            continue
        try:
            raw = files.read(entry)
            if entry["role"] == "query_sequence":
                molecule = "dna" if job["program"] in {"rpstblastn", "blastn_vdb"} else "protein"
                records = parse_sequences(raw, format="fasta", molecule=molecule)
                for ordinal, record in enumerate(records):
                    actual_molecule = molecule
                    if molecule == "dna":
                        relations = [r for p in query_payloads for r in p["sequence_records"] if r["input_key"] == query_key and r["record_ordinal"] == ordinal]
                        if len(relations) == 1:
                            candidates = snapshots.get(relations[0]["subject_ref"], [])
                            if len(candidates) == 1 and candidates[0][0]["molecule"] == "rna" and candidates[0][1] == record.sequence:
                                actual_molecule = "rna"
                    alphabet = "ABCDEFGHIKLMNPQRSTVWXYZJUO*" if actual_molecule == "protein" else (
                        "ACGURYSWKMBDHVN" if actual_molecule == "rna" else "ACGTRYSWKMBDHVN")
                    compatible = set(record.sequence) <= set(alphabet)
                    add_record(entry, ordinal, record.sequence, record.name,
                        record.name + (" " + record.description if record.description else ""), actual_molecule, compatible=compatible)
                    for code in record.issues:
                        if code == "unexpected_symbol_for_declared_molecule" and compatible:
                            continue
                        prepared["issues"].append(_issue(descriptor, "relation_unresolved", f"/query_records/{ordinal}", code))
            elif entry["role"] in {"query_pssm", "checkpoint_asn"}:
                sheet = _pssm.read_blast_pssm(raw, format="scoremat_asn_text", artifact_key=entry["artifact_key"], source_ref=entry["source_ref"])
                prepared["pssm_sheets"].append(sheet)
                if entry["role"] == "query_pssm":
                    from .blast_pssm_master_inputs import extract_blast_pssm_master_metadata
                    masters = extract_blast_pssm_master_metadata(sheet)
                    by_ordinal = {r["record_ordinal"]: r for r in sheet["pssms"]}
                    for record in masters["records"]:
                        master = record["master"]
                        if master["sequence"]:
                            names = _native_pssm_names(by_ordinal[record["record_ordinal"]])
                            add_record(entry, record["record_ordinal"], master["sequence"], *names, "protein",
                                compatible=master["status"] == "complete")
            elif prepared["effective_master_record_ordinal"] is not None:
                sheet = _pssm.read_blast_msa_master(raw, format="clustal", artifact_key=entry["artifact_key"],
                    source_ref=entry["source_ref"], master_record_ordinal=prepared["effective_master_record_ordinal"],
                    ignore_master_for_profile=job["query"]["ignore_msa_master"] is True)
                prepared["msa_sheets"].append(sheet)
                masters = [r for r in sheet["records"] if r["record_ordinal"] == prepared["effective_master_record_ordinal"]]
                if len(masters) == 1 and masters[0]["ungapped_sequence"]:
                    record = masters[0]
                    add_record(entry, record["record_ordinal"], record["ungapped_sequence"], record["identifier"],
                        record["identifier"], "protein", compatible=sheet["status"] == "complete")
        except (_Invalid, ValueError, UnicodeError, ImportError) as error:
            prepared["issues"].append(_issue(descriptor, "source_unavailable", "/inputs", "input_parser_unavailable" if isinstance(error, ImportError) else "input_bytes_or_syntax_unavailable"))
    # Record the independently checked database custody needed for narrow derivation.
    for index, database in enumerate(job["databases"]):
        status = "unavailable"
        try:
            doc = _resolve_document(dict(document_key="manifest", artifact=dict(kind="database_manifest", database_key=database["database_key"]), format="json"),
                                    job=job, bundle=bundle, files=files)
            capture = _one([r for r in bundle["database_manifest"] if r["database_key"] == database["database_key"]], "database_capture_missing")
            if (_decode(doc["contents"]) == database["manifest"] and capture["native_paths"] == database["native_paths"]
                    and len(capture["checks"]) == len(database["manifest"]["files"])
                    and all(r["status"] == "verified" and r["observed_sha256"] == r["expected_sha256"] for r in capture["checks"])):
                status = "available"
            else:
                status = "incompatible"
        except (_Invalid, ValueError):
            pass
        prepared["source_relations"].append({**descriptor,
            "pointer": f"/requested_job/native_blast_database/databases/{index}", "status": status})
    for validation in _valid_payloads(prepared, "query_identity"):
        for field in ("sequence_records", "master_subjects"):
            for index, relation in enumerate(validation["normalized"][field]):
                if (relation["input_key"] != query_key or not any(r["record_ordinal"] == relation["record_ordinal"] for r in prepared["query_records"])
                        or field == "master_subjects" and relation["kind"] != job["query"]["kind"]
                        or field == "sequence_records" and job["query"]["kind"] != "sequence"):
                    pointer = _original_pointer(validation, f"/{field}/{index}")
                    prepared["issues"].append(_issue(validation, "relation_unresolved", pointer, "query_record_address_unresolved"))
    return _copy(prepared)


def _original_pointer(validation, pointer):
    candidates = [r for r in validation["normalization_map"]
                  if pointer == r["normalized_pointer"] or pointer.startswith(r["normalized_pointer"] + "/")]
    if not candidates:
        return pointer
    row = max(candidates, key=lambda r: len(r["normalized_pointer"]))
    return row["payload_pointer"] + pointer[len(row["normalized_pointer"]):]


def _population_issue(result, validation, pointer, detail, *, conflict=False):
    original = _original_pointer(validation, pointer)
    issue = _issue(validation, "relation_conflict" if conflict else "relation_unresolved", original, detail)
    result["issues"].append(issue)
    result["prepared_inputs"]["source_relations"].append({**{k: validation[k] for k in ("consumer", "schema_id", "input_key")},
        "pointer": original, "status": "incompatible" if conflict else "unavailable"})


def _qualified_addresses(value, schema, pointer=""):
    if value is None:
        return
    if "anyOf" in schema:
        schema = next(s for s in schema["anyOf"] if s.get("type") != "null")
    kind = schema.get("x-wire")
    if kind in {"search", "pssm"}:
        yield kind, value, pointer
        return
    if type(value) is list:
        for index, row in enumerate(value):
            yield from _qualified_addresses(row, schema.get("items", {}), f"{pointer}/{index}")
    elif type(value) is dict:
        for field, row in value.items():
            yield from _qualified_addresses(row, schema.get("properties", {}).get(field, {}), pointer + "/" + _escape(field))


def _proof_bindings(unit, validation, pointer, *, search, prepared, files, result, fasta_cache):
    documents = {d["document_key"]: d for d in validation["normalized"]["documents"]}
    accepted = []
    for index, row in enumerate(unit["sequence_identity_bindings"]):
        binding = row["binding"]
        proofs = [p for p in unit["sequence_proofs"] if p["binding_index"] == index]
        valid = len(proofs) == 1 and row["search_key"] == search["search_key"]
        if valid:
            proof = proofs[0]
            doc = documents.get(proof["document_key"])
            valid = (doc is not None and doc["source_ref"] == binding["source_ref"]
                and proof["sha256"] == binding["digest"] and proof["length"] == binding["sequence_length"]
                and proof["molecule"] == binding["molecule"] and binding["report_index"] == search["search_key"]["report_index"])
            symbols = None
            try:
                if valid and proof["representation"] == "json_sequence" and doc["format"] == "json":
                    symbols = _pointer_get(files.json(files.reference(doc["artifact_ref"])), proof["sequence_pointer"])
                    valid = proof["sequence_pointer"] == binding["pointer"] or proof["sequence_pointer"].startswith(binding["pointer"] + "/")
                elif valid and proof["representation"] == "fasta_record" and doc["format"] == "fasta":
                    key = (doc["artifact_ref"], proof["molecule"])
                    if key not in fasta_cache:
                        existing = [r for r in prepared["query_records"] if r["artifact_ref"] == doc["artifact_ref"]
                                    and prepared["invocation"]["query_kind"] == "sequence"]
                        fasta_cache[key] = ([r["sequence"] for r in existing] if existing else
                            [r.sequence for r in parse_sequences(files.read(files.reference(doc["artifact_ref"])), format="fasta",
                                molecule="protein" if proof["molecule"] == "aa" else "unspecified")])
                    symbols = fasta_cache[key][proof["record_ordinal"]]
                    valid = binding["pointer"] == ""
                else:
                    valid = False
            except (ValueError, KeyError, IndexError, UnicodeError, _Invalid):
                valid = False
            alphabet = r"[A-Z*]+" if binding["molecule"] == "aa" else r"[ACGTURYSWKMBDHVN]+"
            valid = (valid and type(symbols) is str and symbols.isascii() and re.fullmatch(alphabet, symbols) is not None
                     and len(symbols) == proof["length"] and _sha(symbols.encode("ascii")) == proof["sha256"])
            hits = [h for h in search["normalized"]["hits"] if h["hit_index"] == binding["hit_index"]]
            valid = valid and len(hits) == 1 and (hits[0].get("length") is None or hits[0]["length"] == proof["length"])
        if valid:
            accepted.append(deepcopy(row))
        else:
            _population_issue(result, validation, f"{pointer}/sequence_identity_bindings/{index}", "full_sequence_identity_unverified", conflict=bool(proofs))
    return accepted


def _query_binding(search, prepared):
    operand = search["operand_binding"]
    if operand is None:
        return None
    rows = [r for r in prepared["query_records"] if r["artifact_key"] == operand["artifact_key"] and r["record_ordinal"] == operand["record_ordinal"]]
    if len(rows) != 1:
        return None
    row, kind = rows[0], prepared["invocation"]["query_kind"]
    mapping, pssm_key = None, None
    if kind == "pssm":
        matches = [(s, i, r) for s in prepared["pssm_sheets"] for i, r in enumerate(s["pssms"])
                   if s["artifact_key"] == operand["artifact_key"] and r["record_ordinal"] == operand["record_ordinal"]]
        if len(matches) != 1:
            return None
        sheet, index, record = matches[0]
        pssm_key = record["pssm_key"]
        mapping = dict(source_ref=sheet["source_ref"], pointer=f"/pssms/{index}/native_pssm/query")
    elif kind == "msa":
        sheets = [s for s in prepared["msa_sheets"] if s["artifact_key"] == operand["artifact_key"]]
        if len(sheets) != 1:
            return None
        mapping = dict(source_ref=sheets[0]["source_ref"], pointer="/master_column_map")
    return dict(operand=deepcopy(operand), axis_kind={"sequence": "sequence", "msa": "msa_master", "pssm": "pssm_master"}[kind],
        full_length=row["length"], coordinate_unit="aa" if row["molecule"] == "protein" else "nt",
        sequence_sha256=row["sequence_sha256"], pssm_key=pssm_key, master_mapping_ref=mapping)


def _empty_binding(key):
    return dict(search_key=deepcopy(key), stage=None, biological_round=None, database_identity=None, input_pssm_key=None, provenance=None)


def _derive_binding(search, prepared, files):
    invocation = prepared["invocation"]
    job = invocation["request"]["native_blast_database"]
    program = job["program"]
    expected = {"psiblast": ("blast_protein_sequence", "sequence_database"),
                "rpsblast": ("rps_profile", "domain_database"), "rpstblastn": ("rps_profile", "domain_database")}
    if program not in expected or len(job["databases"]) != 1:
        return None
    database = job["databases"][0]
    kind, stage = expected[program]
    context = search["program_context"]
    if (database["kind"] != kind or database["role"] != "target"
            or context["reported_program"] is None or context["reported_program"].lower() != program
            or not context["native_version"] or context["geometry_program"] is None
            or search["normalized"]["search"]["database"] not in (database["identity"]["value"], " ".join(database["native_paths"]))):
        return None
    pointer = "/requested_job/native_blast_database/databases/0"
    if not any(r["pointer"] == pointer and r["status"] == "available" for r in prepared["source_relations"]):
        return None
    manifests = [r for r in files.catalog["entries"] if r["role"] == "database_manifest" and r["database_key"] == database["database_key"]]
    if len(manifests) != 1:
        return None
    try:
        if files.json(manifests[0]) != database["manifest"]:
            return None
    except (_Invalid, ValueError):
        return None
    provenance = dict(source_ref=files.catalog["bundle_source_ref"], pointer="/requested_job/native_blast_database")
    binding = dict(search_key=deepcopy(search["search_key"]), stage=stage, biological_round=None,
                   database_identity=deepcopy(database["identity"]), input_pssm_key=None, provenance=provenance)
    report = files.entries.get(search["search_key"]["artifact_key"])
    if report is None:
        return None
    report_pointer = search["search_key"]["search_pointer"].split("/results/")[0]
    pointers = [provenance, dict(source_ref=files.catalog["bundle_source_ref"], pointer="/database_manifest/0"),
        dict(source_ref=manifests[0]["source_ref"], pointer="/identity"),
        dict(source_ref=report["source_ref"], pointer=report_pointer + "/program"),
        dict(source_ref=report["source_ref"], pointer=report_pointer + "/version"),
        dict(source_ref=report["source_ref"], pointer=report_pointer + "/search_target/db" if report["format"] == "json15" else search["search_key"]["search_pointer"])]
    return dict(binding=binding, origin="derived", input_pointers=pointers)


def _namespace_profile(unit, input_key):
    row = deepcopy(unit)
    keys = {}
    for record in row["profile_records"]:
        old = record["profile_key"]
        if old in keys:
            raise ValueError("profile_key_duplicate")
        keys[old] = "profile-" + _sha(_token([input_key, record["database_identity"], record["model_identifier"], old]).encode())
        record["profile_key"] = keys[old]
    for name, fields in (("profile_bindings", ("profile_key",)), ("function_bindings", ("profile_key",)),
                        ("model_relations", ("left_profile_key", "right_profile_key"))):
        for record in row[name]:
            for field in fields:
                record[field] = keys.get(record[field], "unresolved-profile-" + _sha(_token([input_key, record[field]]).encode()))
    return row


def _sequence_units(search, prepared, files, result, fasta_cache):
    rows = []
    for validation in _valid_payloads(prepared, "sequence_database"):
        for index, unit in enumerate(validation["normalized"]["searches"]):
            if unit["search_key"] != search["search_key"]:
                continue
            row = {k: deepcopy(v) for k, v in unit.items() if k != "sequence_proofs"}
            row["sequence_identity_bindings"] = _proof_bindings(unit, validation, f"/searches/{index}", search=search,
                prepared=prepared, files=files, result=result, fasta_cache=fasta_cache)
            rows.append(row)
    merged = dict(search_key=search["search_key"], reference_metadata=[], description_bindings=[], sequence_identity_bindings=[], database_profile=None)
    populations = []
    for row in rows:
        offset = len(merged["reference_metadata"])
        merged["reference_metadata"].extend(row["reference_metadata"])
        for binding in row["description_bindings"]:
            binding["binding"]["metadata_index"] += offset
            merged["description_bindings"].append(binding)
        merged["sequence_identity_bindings"].extend(row["sequence_identity_bindings"])
        if row["database_profile"] is not None:
            populations.append(row["database_profile"])
    unique = {_token(p): p for p in populations}
    if len(unique) == 1:
        merged["database_profile"] = next(iter(unique.values()))
    elif len(unique) > 1:
        result["issues"].append(_issue(_input_issue_descriptor(prepared["invocation"]["request"]["native_blast_database"]),
            "relation_conflict", "/searches", "database_population_conflict"))
    for field in ("description_bindings", "sequence_identity_bindings"):
        merged[field] = list({_token(r): r for r in merged[field]}.values())
    return merged


def _profile_units(search, prepared, result):
    merged = dict(search_key=search["search_key"], profile_records=[], profile_bindings=[], function_bindings=[], model_relations=[])
    for validation in _valid_payloads(prepared, "profile"):
        for index, unit in enumerate(validation["normalized"]["searches"]):
            if unit["search_key"] != search["search_key"]:
                continue
            try:
                row = _namespace_profile(unit, validation["input_key"])
            except ValueError:
                _population_issue(result, validation, f"/searches/{index}", "profile_local_key_conflict", conflict=True)
                continue
            for field in merged.keys() - {"search_key"}:
                merged[field].extend(row[field])
    records = {}
    for record in merged["profile_records"]:
        records.setdefault(record["profile_key"], []).append(record)
    conflicting = {k for k, rows in records.items() if len({_token(r) for r in rows}) > 1}
    merged["profile_records"] = [rows[0] for k, rows in records.items() if k not in conflicting]
    bindings = {}
    for binding in merged["profile_bindings"]:
        identity = _token([binding["search_key"], binding["hit_ordinal"], binding["description_ordinal"], binding["profile_key"]])
        bindings.setdefault(identity, []).append(binding)
    merged["profile_bindings"] = [rows[0] for rows in bindings.values()
        if len({_token(r) for r in rows}) == 1 and rows[0]["profile_key"] not in conflicting]
    if conflicting or any(len({_token(r) for r in rows}) > 1 for rows in bindings.values()):
        result["issues"].append(_issue(_input_issue_descriptor(prepared["invocation"]["request"]["native_blast_database"]),
            "relation_conflict", "/searches", "profile_source_association_conflict"))
    return merged


def _vdb_dataset_matches(dataset, job, options, query):
    candidates = []
    for database in job["databases"]:
        if database["kind"] != "vdb":
            continue
        selected = dataset["selected_input"]
        allowed = database["native_paths"] if selected["kind"] == "path" else [database["identity"]["value"]]
        if selected["value"] not in allowed:
            continue
        snapshot = dataset["snapshot"]
        # An otherwise unmatched snapshot label cannot establish the searched
        # dataset. A captured manifest digest supplies the exact snapshot link.
        if snapshot["snapshot_id"] is not None and snapshot["manifest_sha256"] is None:
            continue
        if snapshot["manifest_sha256"] is not None and snapshot["manifest_sha256"] != database["manifest_file"]["sha256"]:
            continue
        if snapshot["release"] is not None and snapshot["release"] != database["identity"]["release"]:
            continue
        candidates.append(database)
    if len(candidates) != 1:
        return False
    context = dataset["search_context"]
    for flag, field in (("-sra_mode", "sra_mode"), ("-db_gencode", "subject_genetic_code")):
        if flag in options and context[field] is not None and context[field] != int(options[flag]):
            return False
    if "-include_filtered_reads" in options and context["include_filtered_reads"] is False:
        return False
    extent = context["query_extent"]
    if "-query_loc" in options:
        start, end = map(int, options["-query_loc"].split("-"))
        if extent["mode"] == "full" or extent["mode"] == "interval" and extent["interval"] != [start - 1, end]:
            return False
    elif extent["mode"] == "interval":
        return False
    return context["input_pssm_key"] is None or query is not None and context["input_pssm_key"] == query["pssm_key"]


def _vdb_units(search, prepared, files, result, fasta_cache, query, report_source):
    fields = ("dataset_records", "member_bindings", "sequence_identity_bindings", "feature_bindings", "reference_metadata", "population_records")
    merged = {field: [] for field in fields}
    units = []
    for validation in _valid_payloads(prepared, "vdb"):
        for index, original in enumerate(validation["normalized"]["searches"]):
            if original["search_key"] != search["search_key"]:
                continue
            pointer, unit = f"/searches/{index}", deepcopy(original)
            if not all(_vdb_dataset_matches(d, prepared["invocation"]["request"]["native_blast_database"], prepared["invocation"]["effective_options"], query)
                       for d in unit["dataset_records"]):
                _population_issue(result, validation, pointer + "/dataset_records", "selected_vdb_dataset_context_conflict", conflict=True)
                continue
            unit["sequence_identity_bindings"] = _proof_bindings(unit, validation, pointer, search=search,
                prepared=prepared, files=files, result=result, fasta_cache=fasta_cache)
            parsed, docs = [], {d["document_key"]: d for d in validation["normalized"]["documents"]}
            try:
                for source in unit["parsed_sources"]:
                    doc = docs[source["document_key"]]
                    contents = files.read(files.reference(doc["artifact_ref"]))
                    kwargs = dict(source_ref=doc["source_ref"], source_version=source["source_version"])
                    if source["parser"] == "runinfo_csv":
                        item = _vdb.parse_ncbi_sra_runinfo(contents, **kwargs)
                    elif source["parser"] == "ncbi_gbseq_xml":
                        item = _vdb.parse_ncbi_gbseq_vdb_metadata(contents, **kwargs)
                    else:
                        context = source["extraction_context"]
                        selected = [d for d in unit["dataset_records"] if d["dataset_key"] == context["dataset_key"]]
                        if (len(selected) != 1 or context["selected_input"] != selected[0]["selected_input"]
                                or context["snapshot"] != selected[0]["snapshot"]
                                or context["include_filtered_reads"] is not None and selected[0]["search_context"]["include_filtered_reads"] is not None
                                and context["include_filtered_reads"] != selected[0]["search_context"]["include_filtered_reads"]):
                            raise ValueError("vdb_extraction_selected_context_conflict")
                        item = _vdb.parse_blast_vdb_member_sequences(contents, extraction_context=source["extraction_context"], **kwargs)
                    parsed.append(item)
                    result["metadata_parse_results"].append(item)
                parsed = list({_token(p): p for p in parsed}.values())
                bound = _vdb.bind_blast_vdb_metadata(parsed, dataset_records=unit["dataset_records"],
                    member_bindings=unit["member_bindings"], query_binding=query, bindings=unit["metadata_bindings"])
                result["metadata_binding_results"].append(bound)
                unit["reference_metadata"].extend(bound["reference_metadata"])
            except (ValueError, KeyError, _Invalid) as error:
                context_conflict = str(error) == "vdb_extraction_selected_context_conflict"
                _population_issue(result, validation, pointer,
                    "vdb_extraction_selected_context_conflict" if context_conflict else "vdb_native_metadata_binding_unavailable", conflict=context_conflict)
                continue
            present = {r["metadata_key"] for r in unit["reference_metadata"]}
            for i, dataset in enumerate(unit["dataset_records"]):
                absent = [k for k in dataset["metadata_keys"] if k not in present]
                if absent:
                    _population_issue(result, validation, f"{pointer}/dataset_records/{i}/metadata_keys", "vdb_metadata_relation_unresolved")
                    dataset["metadata_keys"] = [k for k in dataset["metadata_keys"] if k in present]
            for i, feature in enumerate(unit["feature_bindings"]):
                if feature["translation_metadata_key"] is not None and feature["translation_metadata_key"] not in present:
                    _population_issue(result, validation, f"{pointer}/feature_bindings/{i}/translation_metadata_key", "vdb_translation_metadata_unresolved")
                    feature["translation_metadata_key"] = None
            try:
                checked = _vdb.populate_blast_vdb_sheet(search, report_source=report_source, query_binding=query,
                    **{field: unit[field] for field in fields})
            except ValueError:
                _population_issue(result, validation, pointer, "vdb_consumer_relationship_invalid", conflict=True)
                continue
            unit.update({field: checked[field] for field in fields})
            units.append((validation, pointer, unit))
    # A collision is unresolved on both sides; input order cannot choose a dataset.
    conflicts = set()
    for field, key in (("dataset_records", "dataset_key"), ("reference_metadata", "metadata_key"), ("population_records", "population_key")):
        owners = {}
        for i, (_, _, unit) in enumerate(units):
            for row in unit[field]:
                owners.setdefault(row[key], []).append(i)
        for indices in owners.values():
            if len(indices) > 1:
                conflicts.update(indices)
    for i, (validation, pointer, unit) in enumerate(units):
        if i in conflicts:
            _population_issue(result, validation, pointer, "vdb_local_key_conflict", conflict=True)
            continue
        offset = len(merged["member_bindings"])
        for feature in unit["feature_bindings"]:
            feature["member_binding_index"] += offset
        for field in fields:
            merged[field].extend(unit[field])
    return merged


def populate_native_blast_database_sheets(collection, *, prepared_inputs, artifact_catalog):
    """Populate the actual public sheets; retain native rows and qualified absences."""
    prepared = _copy(prepared_inputs)
    if collection["invocation"] != prepared["invocation"]:
        raise ValueError("native_blast_metadata_collection_invocation_conflict")
    files = _Catalog(artifact_catalog)
    result = dict(schema="native_blast_database_sheet_set_v1", collection=_copy(collection), prepared_inputs=prepared,
        derived_search_bindings=[], sequence=[], profile=[], vdb=[], pssm=deepcopy(prepared["pssm_sheets"]),
        msa=deepcopy(prepared["msa_sheets"]), iteration=None, metadata_parse_results=[], metadata_binding_results=[], issues=deepcopy(prepared["issues"]))
    program = prepared["invocation"]["execution_program"]
    report_sources, query_bindings, search_bindings, targets = [], [], [], []
    sequence_metadata, profile_metadata, fasta_cache = [], [], {}
    known_keys = {_token(s["search_key"]) for s in collection["searches"]}
    query_payloads = _valid_payloads(prepared, "query_identity")
    pssm_keys = {r["pssm_key"] for s in prepared["pssm_sheets"] for r in s["pssms"]}
    for validation in prepared["metadata"]:
        if validation["status"] != "valid" or validation["normalized"] is None:
            continue
        for kind, value, pointer in _qualified_addresses(validation["normalized"], _SCHEMAS[validation["consumer"]]):
            if kind == "search" and _token(value) not in known_keys:
                _population_issue(result, validation, pointer, "collection_search_address_unresolved")
            if kind == "pssm" and value not in pssm_keys:
                _population_issue(result, validation, pointer, "pssm_record_address_unresolved")
    for search in collection["searches"]:
        key = search["search_key"]
        report = files.entries.get(key["artifact_key"])
        if report is None:
            raise ValueError("native_blast_metadata_report_catalog_unresolved")
        source = dict(artifact_key=key["artifact_key"], artifact_ref=report["artifact_ref"], member_ordinal=key["member_ordinal"], member_sha256=None)
        report_sources.append(dict(search_key=key, report_source=source))
        query = _query_binding(search, prepared)
        query_bindings.append(dict(search_key=key, query_binding=query))
        supplied = [deepcopy(r) for v in query_payloads for r in v["normalized"]["search_bindings"] if r["search_key"] == key]
        derived = _derive_binding(search, prepared, files)
        bindings = supplied[:]
        if derived is not None:
            result["derived_search_bindings"].append(derived)
            if not supplied:
                bindings.append(derived["binding"])
            elif any(r["stage"] != derived["binding"]["stage"] or r["database_identity"] != derived["binding"]["database_identity"] for r in supplied):
                bindings.append(derived["binding"])
                result["issues"].append(_issue(_input_issue_descriptor(prepared["invocation"]["request"]["native_blast_database"]),
                    "relation_conflict", "/search_bindings", "supplied_derived_stage_conflict"))
        if not bindings:
            bindings = [_empty_binding(key)]
        search_bindings.extend(bindings)
        binding = bindings[0] if len(bindings) == 1 else _empty_binding(key)
        target_rows = []
        for validation in query_payloads:
            for i, row in enumerate(validation["normalized"]["target_contexts"]):
                if row["search_key"] != key:
                    continue
                context = None if query is None else dict(query_operand=query["operand"], **{k: row[k] for k in ("taxid", "lineage", "independent_of_search", "source")})
                target_rows.append(dict(search_key=key, target_context=context))
                if query is None:
                    _population_issue(result, validation, f"/target_contexts/{i}", "target_query_operand_unresolved")
        targets.extend(target_rows)
        target = target_rows[0]["target_context"] if len(target_rows) == 1 else None
        if program in {"psiblast", "deltablast"}:
            seq = _sequence_units(search, prepared, files, result, fasta_cache)
            prof = _profile_units(search, prepared, result)
            sequence_metadata.append(seq)
            profile_metadata.append(prof)
            if binding["stage"] == "sequence_database":
                sheet = _sequence.populate_blast_sequence_database_sheet(search, report_source=source, search_binding=binding,
                    query_binding=query, target_context=target, **{k: v for k, v in seq.items() if k != "search_key"})
                result["sequence"].append(dict(search_key=key, sheet=sheet))
            if program == "deltablast" and binding["stage"] == "domain_database":
                sheet = _profile.populate_blast_profile_sheet(search, report_source=source, search_binding=binding,
                    query_binding=query, target_context=target, **{k: v for k, v in prof.items() if k != "search_key"})
                result["profile"].append(dict(search_key=key, sheet=sheet))
        elif program in {"rpsblast", "rpstblastn"}:
            prof = _profile_units(search, prepared, result)
            sheet = _profile.populate_blast_profile_sheet(search, report_source=source, search_binding=binding,
                query_binding=query, target_context=target, **{k: v for k, v in prof.items() if k != "search_key"})
            result["profile"].append(dict(search_key=key, sheet=sheet))
        else:
            metadata = _vdb_units(search, prepared, files, result, fasta_cache, query, source)
            sheet = _vdb.populate_blast_vdb_sheet(search, report_source=source, query_binding=query, target_context=target, **metadata)
            result["vdb"].append(dict(search_key=key, sheet=sheet))
    if program in {"psiblast", "deltablast"}:
        iteration_data = {k: [] for k in ("checkpoint_bindings", "comparison_pairs", "inclusion_records", "convergence_records")}
        for validation in _valid_payloads(prepared, "iteration"):
            for field in iteration_data:
                for index, row in enumerate(validation["normalized"][field]):
                    value = deepcopy(row)
                    key_field = "comparison_key" if field == "comparison_pairs" else "record_key" if field.endswith("records") else None
                    if key_field:
                        value[key_field] = "metadata-" + _sha(_token([validation["input_key"],
                            _original_pointer(validation, f"/{field}/{index}"), value[key_field]]).encode())
                    iteration_data[field].append(value)
        # Keep orphan context rows in v2 so its qualifier reports their exact scope.
        for validation in query_payloads:
            search_bindings.extend(deepcopy(r) for r in validation["normalized"]["search_bindings"] if _token(r["search_key"]) not in known_keys)
            for row in validation["normalized"]["target_contexts"]:
                if _token(row["search_key"]) not in known_keys:
                    targets.append(dict(search_key=row["search_key"], target_context=dict(query_operand=None,
                        **{k: row[k] for k in ("taxid", "lineage", "independent_of_search", "source")})))
        result["iteration"] = _iteration.populate_blast_iteration_sheet(collection, report_sources=report_sources,
            query_bindings=query_bindings, search_bindings=search_bindings, pssm_sheets=prepared["pssm_sheets"],
            sequence_metadata=sequence_metadata, profile_metadata=profile_metadata, **iteration_data,
            invocation_source=dict(source_ref=artifact_catalog["bundle_source_ref"], pointer="/requested_job/native_blast_database"),
            target_contexts=targets)
    return _copy(result)
