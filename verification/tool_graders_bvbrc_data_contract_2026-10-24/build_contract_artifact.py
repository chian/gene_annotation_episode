"""Build planning schemas/examples only; this is not a production query or parser.

All output stays in this verification directory. No network and no Store access.
The schemas freeze module interfaces so independent coding workloads can agree.
"""
from pathlib import Path
import copy
import json

HERE = Path(__file__).parent
EVIDENCE = json.loads((HERE / "field_contract_evidence.json").read_text())
COLLECTIONS = list(EVIDENCE["collections"])
FIELDS = sorted({f["name"] for c in EVIDENCE["collections"].values() for f in c["fields"]})
MEASUREMENTS = ["counts", "fpkm", "tpm", "log2_fc", "p_value", "z_score", "other_value"]

def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}

def arr(items, **kw):
    return {"type": "array", "items": items, **kw}

def enum(*values):
    return {"type": "string", "enum": list(values)}

def nullable(schema):
    return {"anyOf": [copy.deepcopy(schema), {"type": "null"}]}

def ref(name):
    return {"$ref": "#/$defs/" + name}

def constant(value):
    return {"const": value}

S = {"type": "string"}
N = {"type": "number"}
I = {"type": "integer"}
U = {"type": "integer", "minimum": 0}
B = {"type": "boolean"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
FIELD = enum(*FIELDS)
COLLECTION = enum(*COLLECTIONS)
SCALAR = {"type": ["string", "number", "boolean"]}
REASONS = ["not_selected", "native_field_absent", "native_null", "source_reports_not_measured",
    "missing_input_page", "missing_join_key", "missing_sequence_record", "missing_feature_record",
    "ambiguous_join", "sequence_type_mismatch", "sequence_text_unavailable", "native_value_invalid",
    "unrepresentable_numeric_value", "unknown_units", "unknown_denominator", "inexact_population",
    "population_conflict", "empty_population", "native_format_unverified", "native_partial_results",
    "transport_incomplete", "requested_row_absent", "conflicting_metadata", "incompatible_input"]
ISSUES = ["bvbrc_response_service_mismatch", "bvbrc_response_request_mismatch",
    "bvbrc_response_body_incomplete", "bvbrc_unsupported_media_type", "bvbrc_invalid_json_response",
    "bvbrc_expected_native_row_array", "bvbrc_expected_solr_response", "bvbrc_native_error",
    "bvbrc_native_partial_results", "bvbrc_population_metadata_conflict", "bvbrc_invalid_facet_pairs",
    "bvbrc_invalid_native_field", "bvbrc_join_conflict", "bvbrc_missing_native_identity",
    "bvbrc_schema_observed_variant", "bvbrc_unrepresentable_numeric_value", "bvbrc_input_unavailable",
    "bvbrc_native_md5_mismatch", "bvbrc_native_length_mismatch", "bvbrc_provider_http_error"]
D = {}
D["Issue"] = obj({"code": enum(*ISSUES),
    "phase": enum("transport", "format", "field", "population", "join", "projection"),
    "row_index": nullable(U), "field": nullable(FIELD), "native_path": nullable(S),
    "http_status": nullable(I)})
D["Sort"] = obj({"field": FIELD, "direction": enum("asc", "desc")})
D["Predicate"] = {"oneOf": [
    obj({"field": FIELD, "operator": constant("eq"), "value": SCALAR}),
    obj({"field": FIELD, "operator": constant("in"),
         "value": arr(SCALAR, minItems=1)}),
    obj({"field": FIELD, "operator": constant("range"),
         "lower": nullable(N), "lower_inclusive": B,
         "upper": nullable(N), "upper_inclusive": B}),
    obj({"field": FIELD, "operator": constant("exists"), "present": B})]}
D["FacetRequest"] = obj({"field": FIELD, "offset": U,
    "limit": {"type": "integer", "minimum": 1}, "min_count": U,
    "sort": enum("count", "index"), "include_missing": B})
D["DataQuery"] = obj({"version": constant("bvbrc_data_request_v2"),
    "collection": COLLECTION, "mode": enum("page", "count", "facet"),
    "filters": arr(ref("Predicate")),
    "fields": arr(FIELD, minItems=1, uniqueItems=True),
    "sort": arr(ref("Sort")), "offset": U,
    "limit": {"type": "integer", "minimum": 1, "maximum": 25000},
    "facet": ref("FacetRequest")}, required=["version", "collection", "mode", "filters"])
D["EffectiveQuery"] = obj({"version": constant("bvbrc_data_effective_query_v2"),
    "collection": COLLECTION, "mode": enum("page", "count", "facet"),
    "filters": arr(ref("Predicate")), "fields": arr(FIELD, uniqueItems=True),
    "sort": arr(ref("Sort")), "offset": U,
    "limit": {"type": "integer", "minimum": 0, "maximum": 25000},
    "facet": nullable(ref("FacetRequest"))})
D["QueryPopulation"] = obj({"version": constant("bvbrc_data_population_v1"),
    "base_url": S, "collection": COLLECTION, "filters": arr(ref("Predicate")),
    "visibility": constant("public_unauthenticated"),
    "compiler_version": constant("bvbrc_solr_compiler_v1"),
    "field_contract_version": constant("bvbrc_data_fields_2026_10_24_v1"),
    "population_key": SHA})
D["Header"] = obj({"name": S, "value": S})
D["PageSelector"] = obj({"offset": U,
    "limit": {"type": "integer", "minimum": 1, "maximum": 25000}})
D["PreparedQuery"] = obj({"version": constant("bvbrc_data_prepared_v2"),
    "service": constant("bvbrc_data"), "original_request": ref("DataQuery"),
    "page_selector": nullable(ref("PageSelector")),
    "effective_request": ref("EffectiveQuery"), "query_population": ref("QueryPopulation"),
    "field_selection": obj({"requested_fields": nullable(arr(FIELD, minItems=1, uniqueItems=True)),
        "defaulted_fields": arr(FIELD, uniqueItems=True), "custody_added_fields": arr(FIELD, uniqueItems=True)}),
    "sort_selection": obj({"requested_sort": nullable(arr(ref("Sort"))),
        "defaulted_sort": arr(ref("Sort")), "tie_breaker_added": nullable(ref("Sort"))}),
    "request_profile": constant("solr_query_solr_json_v1"),
    "native_request": obj({"method": constant("GET"), "url": S,
        "headers": arr(ref("Header")), "body": {"type": "null"},
        "query_parameters": arr(obj({"name": S, "value": S}))})})

# Native atoms retain exact number spelling independently of finite projections.
D["NativeAtom"] = obj({"kind": enum("string", "number", "boolean", "null"),
    "string_value": nullable(S), "number_value": nullable(N), "boolean_value": nullable(B),
    "number_lexeme": nullable(S)})
D["NativeCell"] = obj({"cell_key": S, "field": FIELD, "native_path": S,
    "presence": enum("present", "absent", "null", "unselected"),
    "native_shape": enum("scalar", "array", "object", "absent", "null"),
    "atoms": arr(ref("NativeAtom")),
    "status": enum("valid", "invalid", "unrepresentable", "missing", "unselected"),
    "field_schema_status": enum("match", "observed_exception", "mismatch", "not_evaluated"),
    "issue_codes": arr(enum(*ISSUES), uniqueItems=True)})
D["NumericCell"] = obj({"cell_key": S, "field": FIELD, "native_path": S,
    "value": nullable(N),
    "status": enum("reported", "parsed_numeric_text", "missing", "unselected", "invalid", "incompatible", "not_measured"),
    "reason": nullable(enum(*REASONS)), "quantity_kind": S,
    "unit_code": nullable(enum("nucleotide", "amino_acid", "document", "fraction")),
    "unit_basis": enum("field_definition", "supplied", "unknown"),
    "unit_cell_keys": arr(S),
    "denominator_value": nullable(N), "denominator_basis": enum("native", "supplied", "unknown"),
    "origin": enum("native_reported", "derived_from_native_text", "unavailable"),
    "uncertainty_cell_keys": arr(S), "issue_codes": arr(enum(*ISSUES), uniqueItems=True)})
D["NativeRow"] = obj({"row_key": S, "row_index": U, "native_path": S,
    "native_id": nullable(S), "status": enum("valid", "partial", "invalid"),
    "cells": arr(ref("NativeCell")), "numerical_cells": arr(ref("NumericCell")),
    "issues": arr(ref("Issue"))})
D["CollectionRowsExtraction"] = obj({"version": constant("bvbrc_collection_rows_v1"),
    "collection": COLLECTION, "native_sha256": SHA, "requested_fields": arr(FIELD, uniqueItems=True),
    "rows": arr(ref("NativeRow")), "issues": arr(ref("Issue"))})
D["Qualification"] = obj({"service_matches": B, "request_matches": B,
    "transport_complete": B, "http_success": B, "format_valid": B,
    "population_metadata_valid": B, "native_partial_results": nullable(B),
    "requested_fields_valid": B,
    "status": enum("complete", "partial", "failed")})
D["NativePopulation"] = obj({"population_key": SHA,
    "compiled_query": nullable(S), "echoed_query": nullable(S),
    "echoed_filter_queries": arr(S), "reported_total": nullable(U),
    "native_num_found_exact": nullable(B),
    "exactness": enum("exact", "provider_reported", "inexact", "unknown"),
    "native_location": nullable(S)})
D["Page"] = obj({"mode": enum("page", "count", "facet"),
    "requested_offset": nullable(U), "requested_limit": nullable(U),
    "response_start": nullable(U), "native_content_range": nullable(S),
    "returned_row_count": U, "valid_row_count": U, "invalid_row_count": U,
    "reported_total": nullable(U), "count_exactness": enum("exact", "provider_reported", "inexact", "unknown"),
    "response_complete": B, "population_coverage": enum("complete", "subset", "unknown"),
    "next_offset": nullable(U), "next_offset_basis": nullable(enum("reported_more", "total_unknown"))})
D["Count"] = obj({"population_key": SHA, "reported_value": nullable(U),
    "exactness": enum("exact", "provider_reported", "inexact", "unknown"),
    "availability": enum("available", "unavailable"), "reason": nullable(enum(*REASONS)),
    "native_location": nullable(S)})
D["FacetBucket"] = obj({"bucket_key": S, "term_cell_key": S, "native_path": S,
    "term": nullable(ref("NativeAtom")), "is_missing_bucket": nullable(B),
    "count": nullable(U), "status": enum("valid", "invalid"), "issues": arr(ref("Issue"))})
D["Facet"] = obj({"population_key": SHA, "request": ref("FacetRequest"),
    "native_location": S, "buckets": arr(ref("FacetBucket")),
    "returned_nonmissing_bucket_count": U,
    "bucket_window_status": enum("exhausted_window", "more_unknown", "invalid"),
    "all_categories_complete": B, "issues": arr(ref("Issue"))})
D["DataSheet"] = obj({"version": constant("bvbrc_data_sheet_v1"),
    "collection": COLLECTION, "mode": enum("page", "count", "facet"),
    "custody": obj({"native_sha256": SHA, "retrieved_at": S,
        "requested_url": S, "effective_url": S, "media_type": S,
        "native_profile": enum("json_array_with_headers_v1", "solr_json_envelope_v1"),
        "prepared_sha256": SHA, "field_contract_version": constant("bvbrc_data_fields_2026_10_24_v1")}),
    "transport": obj({"http_status": nullable(I), "body_complete": B,
        "headers": arr(ref("Header")), "failure_code": nullable(S),
        "automatic_redirects": constant(False), "native_query_time_ms": nullable(N)}),
    "qualification": ref("Qualification"), "population": ref("NativePopulation"),
    "selected_fields": arr(FIELD, uniqueItems=True), "page": ref("Page"),
    "count": ref("Count"), "rows": arr(ref("NativeRow")), "facets": arr(ref("Facet")),
    "issues": arr(ref("Issue"))})
D["ParseResult"] = obj({"version": constant("bvbrc_data_parse_result_v1"),
    "status": enum("complete", "partial", "failed"), "sheet": nullable(ref("DataSheet")),
    "failures": arr(ref("Issue")), "retained_native_sha256": SHA})
D["PageComponents"] = obj({"version": constant("bvbrc_data_page_components_v1"),
    "native_row_count": U, "valid_row_count": U, "invalid_row_count": U,
    "reported_population_count": nullable(U),
    "population_exactness": enum("exact", "provider_reported", "inexact", "unknown")})
D["FacetFraction"] = obj({"bucket_key": S, "numerator": nullable(U),
    "denominator": nullable(U), "fraction": nullable(N), "reason": nullable(enum(*REASONS))})
D["FacetComponents"] = obj({"version": constant("bvbrc_data_facet_components_v1"),
    "denominator_policy": constant("same_response_exact_document_count"),
    "population_key": SHA, "fractions": arr(ref("FacetFraction"))})
D["RowLocation"] = obj({"native_sha256": SHA, "collection": COLLECTION, "row_key": S})
D["CellLocation"] = obj({"native_sha256": SHA, "collection": COLLECTION,
    "row_key": nullable(S), "cell_key": S, "field": S,
    "source_level": enum("row", "feature", "sequence", "result", "bioset", "experiment", "supplied", "facet")})
D["AcquisitionRequirement"] = obj({"collection": COLLECTION, "field": FIELD,
    "values": arr(S), "sequence_kind": nullable(enum("AA", "NA")), "reason": enum(*REASONS)})
D["FeatureSequenceEdge"] = obj({"edge_key": S, "feature_id": S,
    "feature_rows": arr(ref("RowLocation")), "sequence_kind": enum("AA", "NA"),
    "native_md5": nullable(S), "sequence_rows": arr(ref("RowLocation")),
    "sequence_cells": arr(ref("CellLocation")), "feature_metadata_cells": arr(ref("CellLocation")),
    "sequence_length": nullable(U), "feature_length": nullable(U),
    "raw_md5_match": nullable(B), "length_match": nullable(B),
    "join_status": enum("joined", "repeated_identical", "missing_feature", "missing_key", "missing_record", "missing_sequence", "type_mismatch", "conflict"),
    "reason": nullable(enum(*REASONS)), "issues": arr(ref("Issue"))})
D["FeatureSequenceSheet"] = obj({"version": constant("bvbrc_feature_sequence_sheet_v1"),
    "selection": obj({"feature_ids": arr(S, minItems=1, uniqueItems=True), "sequence_kind": enum("AA", "NA", "both")}),
    "input_native_sha256s": arr(SHA, uniqueItems=True),
    "input_page_counts": arr(obj({"native_sha256": SHA, "collection": COLLECTION,
        "retained_row_count": U, "valid_row_count": U})), "edges": arr(ref("FeatureSequenceEdge")),
    "requirements": arr(ref("AcquisitionRequirement")), "issues": arr(ref("Issue"))})
D["FeatureSequenceComponents"] = obj({"version": constant("bvbrc_feature_sequence_components_v1"),
    **{name: U for name in ["selected_feature_count", "retained_feature_row_count", "native_sequence_record_count",
        "distinct_joined_aa_sequence_count", "distinct_joined_na_sequence_count", "relation_count",
        "missing_key_count", "missing_record_count", "conflicting_relation_count", "length_agreement_count"]}})
D["SuppliedMetadata"] = obj({"result_id": nullable(S), "bioset_id": S,
    "provenance": obj({"source_ref": S, "record_path": S}),
    "sample_ids": nullable(arr(S)), "biological_replicate_ids": nullable(arr(S)),
    "technical_replicate_ids": nullable(arr(S)),
    "measurement_units": arr(obj({"field": enum(*MEASUREMENTS), "unit": S})),
    "normalization_method": nullable(S), "pvalue_correction_method": nullable(S),
    "contrast": nullable(obj({"numerator_condition": S, "denominator_condition": S}))})
D["MolecularLink"] = obj({"expected_id": nullable(S), "rows": arr(ref("RowLocation")),
    "status": enum("matched", "missing_key", "missing_input", "missing_record", "conflict"),
    "reason": nullable(enum(*REASONS))})
D["MolecularMetadata"] = obj({"field": S, "source_level": enum("result", "bioset", "experiment", "supplied"),
    "cells": arr(ref("CellLocation")),
    "status": enum("reported", "supplied", "missing", "conflict"), "reason": nullable(enum(*REASONS))})
D["MolecularRow"] = obj({"row_key": S, "result_id": S, "result_rows": arr(ref("RowLocation")),
    "exp_id": nullable(S), "bioset_id": nullable(S), "feature_id": nullable(S), "entity_id": nullable(S),
    "experiment": ref("MolecularLink"), "bioset": ref("MolecularLink"), "feature": ref("MolecularLink"),
    "measurements": arr(ref("NumericCell")), "metadata": arr(ref("MolecularMetadata")),
    "relationship_status": enum("matched", "partial", "conflict"), "issues": arr(ref("Issue"))})
D["MolecularSheet"] = obj({"version": constant("bvbrc_molecular_sheet_v1"),
    "selected_result_ids": arr(S, minItems=1, uniqueItems=True), "input_native_sha256s": arr(SHA, uniqueItems=True),
    "supplied_metadata": arr(ref("SuppliedMetadata")), "rows": arr(ref("MolecularRow")),
    "missing_result_ids": arr(S), "requirements": arr(ref("AcquisitionRequirement")), "issues": arr(ref("Issue"))})

projection_common = {"numeric_fields": arr(FIELD, uniqueItems=True), "metadata_fields": arr(FIELD, uniqueItems=True)}
D["Projection"] = {"oneOf": [
    obj({"family": constant("query_metadata")}),
    obj({"family": constant("collection_rows"), "row_indices": arr(U, minItems=1, uniqueItems=True), **projection_common}),
    obj({"family": constant("feature_sequence"), "feature_ids": arr(S, minItems=1, uniqueItems=True),
         "sequence_kind": enum("AA", "NA", "both"),
         "feature_metadata_fields": arr(FIELD, uniqueItems=True), "include_sequence_values": B}),
    obj({"family": constant("molecular_experiment"), "result_ids": arr(S, minItems=1, uniqueItems=True),
         "measurement_fields": arr(enum(*MEASUREMENTS), uniqueItems=True),
         "metadata_fields": arr(obj({"source_level": enum("result", "bioset", "experiment", "supplied"),
              "field": S}), uniqueItems=True)})]}
D["ResultSelector"] = obj({"version": constant("bvbrc_data_result_selector_v2"),
    "page": nullable(ref("PageSelector")), "projection": ref("Projection"),
    "inputs": arr(obj({"collection": COLLECTION, "source_ref": S}), uniqueItems=True),
    "supplied_metadata": arr(ref("SuppliedMetadata"))})
D["ResultBinding"] = obj({"source_ref": S, "native_artifact_ref": S, "native_sha256": SHA,
    "grading_artifact_ref": S, "collection": COLLECTION,
    "acquisition_assignment_sha256": SHA, "selector_sha256": SHA})
D["MetadataBinding"] = obj({"source_ref": S, "native_artifact_ref": S,
    "native_sha256": SHA, "record_path": S, "metadata_sha256": SHA})
D["PublicationInputs"] = obj({"version": constant("bvbrc_data_publication_inputs_v1"),
    "prepared": ref("PreparedQuery"),
    "input_results": arr(obj({"binding": ref("ResultBinding"), "sheet": ref("DataSheet")})),
    "supplied_metadata": arr(ref("SuppliedMetadata")), "metadata_bindings": arr(ref("MetadataBinding"))})
D["PublishedGrading"] = obj({"version": constant("bvbrc_data_grading_v1"),
    "prepared": ref("PreparedQuery"), "selector": ref("ResultSelector"), "parse_result": ref("ParseResult"),
    "page_components": nullable(ref("PageComponents")), "facet_components": nullable(ref("FacetComponents")),
    "feature_sequence_sheet": nullable(ref("FeatureSequenceSheet")),
    "feature_sequence_components": nullable(ref("FeatureSequenceComponents")),
    "molecular_sheet": nullable(ref("MolecularSheet")),
    "input_bindings": arr(ref("ResultBinding")), "metadata_bindings": arr(ref("MetadataBinding"))})
D["QualifiedResult"] = obj({"version": constant("bvbrc_data_qualified_result_v1"),
    "service": constant("bvbrc_data"), "binding": ref("ResultBinding"),
    "host_qualification": obj({"run_id": S, "source_episode_id": S, "receiver_episode_id": S,
        "scope_sha256": SHA, "receipt_verified": constant(True), "native_bytes_verified": constant(True),
        "grading_custody_verified": constant(True), "original_selection_verified": constant(True),
        "input_bindings_verified": constant(True), "receiver_possession_verified": constant(True),
        "possession_basis": enum("own_completed_action", "admitted_return", "parent_assignment", "current_child_return")}),
    "grading": ref("PublishedGrading"),
    "input_results": arr(obj({"binding": ref("ResultBinding"), "sheet": ref("DataSheet")}))})

# Closed report schemas do not use $ref/oneOf/anyOf or unrestricted strings.
def identifier(namespace, null=False):
    return {"type": ["string", "null"] if null else "string", "format": "identifier",
            "x-reference-namespace": namespace}

def model_nullable(kind):
    return {"type": [kind, "null"]}

def model_enum(values, null=False):
    return {"type": ["string", "null"] if null else "string", "enum": list(values) + ([None] if null else [])}

REASON = model_enum(REASONS, True)
common = {"source_ref": identifier("execution_result"), "collection": COLLECTION,
    "input_source_refs": arr(identifier("execution_result")),
    "metadata_source_refs": arr(identifier("source")),
    "status": enum("complete", "partial", "unavailable")}
row_common = {**common, "row_ref": identifier("bvbrc_data_row", True),
    "requested_row_index": model_nullable("integer"),
    "native_id": identifier("bvbrc_data_identifier", True)}
model_measurement = obj({"field": FIELD, "cell_ref": identifier("bvbrc_data_cell"), "value": N,
    "unit_code": model_enum(["nucleotide", "amino_acid", "document", "fraction"], True),
    "unit_basis": enum("field_definition", "supplied", "unknown"),
    "unit_value_refs": arr(identifier("bvbrc_data_cell")),
    "denominator_value": model_nullable("number"), "denominator_basis": enum("native", "supplied", "unknown"),
    "uncertainty_cell_refs": arr(identifier("bvbrc_data_cell")),
    "origin": enum("native_reported", "derived_from_native_text")})
model_unavailable = obj({"field": FIELD, "reason": enum(*REASONS)})
model_metadata = obj({"field": FIELD, "value_ref": identifier("bvbrc_data_cell"),
    "source_level": enum("row", "feature", "sequence", "result", "bioset", "experiment", "supplied")})
model_metadata_unavailable = obj({"field": FIELD,
    "source_level": enum("row", "feature", "sequence", "result", "bioset", "experiment", "supplied"),
    "reason": enum(*REASONS)})
R = {}
R["execution_bvbrc_pages"] = obj({**common,
    "mode": enum("page", "count", "facet"), "requested_offset": model_nullable("integer"),
    "requested_limit": model_nullable("integer"), "returned_row_count": U,
    "valid_row_count": U, "invalid_row_count": U, "reported_total": model_nullable("integer"),
    "count_exactness": enum("exact", "provider_reported", "inexact", "unknown"),
    "response_complete": B, "population_coverage": enum("complete", "subset", "unknown"),
    "next_offset": model_nullable("integer"), "population_ref": identifier("bvbrc_data_population")})
R["execution_bvbrc_counts"] = obj({**common, "population_ref": identifier("bvbrc_data_population"),
    "reported_value": model_nullable("integer"), "exactness": enum("exact", "provider_reported", "inexact", "unknown"),
    "availability": enum("available", "unavailable"), "reason": REASON})
R["execution_bvbrc_facets"] = obj({**common, "population_ref": identifier("bvbrc_data_population"),
    "field": FIELD, "bucket_ref": identifier("bvbrc_data_bucket"), "is_missing_bucket": model_nullable("boolean"),
    "term_ref": identifier("bvbrc_data_cell", True), "count": model_nullable("integer"),
    "denominator": model_nullable("integer"), "fraction": model_nullable("number"),
    "fraction_unavailable_reason": REASON, "requested_offset": U, "requested_limit": U,
    "requested_min_count": U, "bucket_window_status": enum("exhausted_window", "more_unknown", "invalid")})
R["execution_bvbrc_numeric_rows"] = obj({**row_common,
    "measurements": arr(model_measurement), "unavailable": arr(model_unavailable),
    "metadata_cells": arr(model_metadata), "metadata_unavailable": arr(model_metadata_unavailable)})
R["execution_bvbrc_feature_sequence_rows"] = obj({**common,
    "feature_id": identifier("bvbrc_data_identifier"), "feature_row_refs": arr(identifier("bvbrc_data_row")),
    "sequence_kind": enum("AA", "NA"), "native_md5": identifier("bvbrc_data_identifier", True),
    "sequence_row_refs": arr(identifier("bvbrc_data_row")), "sequence_value_refs": arr(identifier("bvbrc_data_cell")),
    "metadata_cells": arr(model_metadata), "metadata_unavailable": arr(model_metadata_unavailable),
    "sequence_length": model_nullable("integer"),
    "feature_length": model_nullable("integer"), "raw_md5_match": model_nullable("boolean"),
    "length_match": model_nullable("boolean"),
    "join_status": enum("joined", "repeated_identical", "missing_feature", "missing_key", "missing_record", "missing_sequence", "type_mismatch", "conflict"),
    "unavailable_reason": REASON})
# Supplied metadata keys are separate reviewed semantic names, not arbitrary text.
SUPPLIED_FIELDS = ["sample_ids", "biological_replicate_ids", "technical_replicate_ids", "measurement_units",
    "normalization_method", "pvalue_correction_method", "contrast"]
molecular_metadata = copy.deepcopy(model_metadata)
molecular_metadata["properties"]["field"] = enum(*sorted(set(FIELDS + SUPPLIED_FIELDS)))
molecular_metadata_unavailable = copy.deepcopy(model_metadata_unavailable)
molecular_metadata_unavailable["properties"]["field"] = enum(*sorted(set(FIELDS + SUPPLIED_FIELDS)))
R["execution_bvbrc_expression_rows"] = obj({**row_common,
    **{key: identifier("bvbrc_data_identifier", key != "result_id") for key in
        ["result_id", "exp_id", "bioset_id", "feature_id", "entity_id"]},
    "experiment_row_refs": arr(identifier("bvbrc_data_row")),
    "bioset_row_refs": arr(identifier("bvbrc_data_row")), "feature_row_refs": arr(identifier("bvbrc_data_row")),
    "measurements": arr(model_measurement), "unavailable": arr(model_unavailable),
    "metadata_cells": arr(molecular_metadata), "metadata_unavailable": arr(molecular_metadata_unavailable),
    "relationship_status": enum("matched", "partial", "conflict")})
FACT_SCHEMAS = {name: {**arr(row), "x-source": name} for name, row in R.items()}

D["MaterializedCell"] = obj({"source_ref": S, "row_ref": nullable(S), "cell_ref": S,
    "collection": nullable(COLLECTION), "native_id": nullable(S), "field": S,
    "source_level": enum("row", "feature", "sequence", "result", "bioset", "experiment", "supplied", "facet"),
    "presence": enum("present", "absent", "null", "unselected"),
    "native_shape": enum("scalar", "array", "object", "absent", "null"),
    "atoms": arr(ref("NativeAtom")), "status": enum("valid", "invalid", "unrepresentable", "missing", "unselected"),
    "issue_codes": arr(enum(*ISSUES), uniqueItems=True)})
D["ReceiverMaterialization"] = obj({"version": constant("bvbrc_received_values_v1"),
    "admission_key": S, "form_field": S, "fact_source": enum(*R),
    "facts": arr({"oneOf": list(R.values())}), "cells": arr(ref("MaterializedCell")),
    "unavailable": arr(obj({"collection": COLLECTION, "native_id": nullable(S),
        "field": S, "source_level": S, "reason": enum(*REASONS)}))})

REGISTRY = {}
ID_NUMBERS = {"taxon_id", "taxon_id_i", "taxon_id_a", "taxon_id_b", "gene_id", "parent_id", "genetic_code", "version"}
TEXT_NUMBERS = {("protein_feature", "e_value"): "finite_nonnegative_decimal_scientific",
    ("bioset", "entity_count"): "nonnegative_decimal_integer",
    ("sequence_feature_vt", "sfvt_genome_count"): "nonnegative_decimal_integer"}
UNITS = {("genome", "genome_length"): "nucleotide", ("genome", "contig_n50"): "nucleotide",
    ("genome_sequence", "length"): "nucleotide", ("genome_feature", "aa_length"): "amino_acid",
    ("genome_feature", "na_length"): "nucleotide"}
for collection, evidence in EVIDENCE["collections"].items():
    entries = {}
    for observed in evidence["fields"]:
        field = observed["name"]
        native_numeric = observed["solr_type"] in {"int", "long", "float", "double"}
        scalar_numeric = native_numeric and not observed["multi_valued"] and field not in ID_NUMBERS
        text_grammar = TEXT_NUMBERS.get((collection, field))
        numeric = scalar_numeric or text_grammar is not None or (collection, field) == ("ppi", "score")
        entries[field] = {**observed,
            "exact_filter_supported": observed["indexed"] and observed["solr_type"] in {"string", "int", "long", "float", "double", "boolean"},
            "range_filter_supported": observed["indexed"] and native_numeric,
            "existence_filter_supported": observed["indexed"],
            "sort_supported": observed["indexed"] and not observed["multi_valued"],
            "facet_supported": observed["indexed"] and observed["solr_type"] == "string",
            "numeric_projection": numeric,
            "numeric_text_grammar": text_grammar,
            "quantity_kind": collection + "." + field if numeric else None,
            "unit_code": UNITS.get((collection, field)),
            "unit_basis": "field_definition" if (collection, field) in UNITS else "unknown",
            "coordinate_convention": "one_based_inclusive" if collection == "genome_feature" and field in {"start", "end"} else None,
            "observed_variants": ["finite_json_number"] if (collection, field) == ("ppi", "score") else []}
    REGISTRY[collection] = {"unique_key": evidence["unique_key"], "schema_sha256": evidence["schema_sha256"],
        "fields": entries, "selectable_fields": list(entries),
        "numerical_fields": [name for name, value in entries.items() if value["numeric_projection"]],
        "metadata_fields": [name for name, value in entries.items() if not value["numeric_projection"]]}

EXPORTS = {
    "bvbrc_data_fields.py": {"FIELD_CONTRACT_VERSION": "bvbrc_data_fields_2026_10_24_v1",
        "COLLECTIONS": "tuple(field_registry keys in document order)", "FIELD_REGISTRY": "field_registry",
        "SELECTABLE_FIELDS": "collection -> tuple(selectable_fields)",
        "NUMERICAL_FIELDS": "collection -> tuple(numerical_fields)",
        "METADATA_FIELDS": "collection -> tuple(metadata_fields)",
        "MOLECULAR_MEASUREMENT_FIELDS": MEASUREMENTS,
        "SUPPLIED_METADATA_FIELDS": SUPPLIED_FIELDS,
        "UNAVAILABLE_REASONS": REASONS, "ISSUE_CODES": ISSUES},
    "bvbrc_data_query.py": {"DATA_QUERY_SCHEMA": "DataQuery", "PREPARED_DATA_QUERY_SCHEMA": "PreparedQuery",
        "COMPILER_VERSION": "bvbrc_solr_compiler_v1"},
    "bvbrc_data_readers.py": {"DATA_SHEET_SCHEMA": "DataSheet", "DATA_PARSE_RESULT_SCHEMA": "ParseResult",
        "COLLECTION_ROWS_SCHEMA": "CollectionRowsExtraction", "NUMERIC_TEXT_GRAMMARS": "numeric_text_grammars"},
    "bvbrc_data_calculators.py": {"PAGE_COMPONENTS_SCHEMA": "PageComponents", "FACET_COMPONENTS_SCHEMA": "FacetComponents"},
    "bvbrc_data_feature_sequences.py": {"FEATURE_SEQUENCE_SHEET_SCHEMA": "FeatureSequenceSheet",
        "FEATURE_SEQUENCE_COMPONENTS_SCHEMA": "FeatureSequenceComponents"},
    "bvbrc_data_molecular.py": {"MOLECULAR_SHEET_SCHEMA": "MolecularSheet", "SUPPLIED_METADATA_SCHEMA": "SuppliedMetadata"},
    "bvbrc_data_views.py": {"RESULT_SELECTOR_SCHEMA": "ResultSelector", "PUBLISHED_GRADING_SCHEMA": "PublishedGrading",
        "QUALIFIED_RESULT_SCHEMA": "QualifiedResult", "PUBLICATION_INPUTS_SCHEMA": "PublicationInputs", "FACT_SCHEMAS": "fact_schemas",
        "RECEIVER_MATERIALIZATION_SCHEMA": "ReceiverMaterialization",
        "FACT_SOURCES": list(R), "IDENTIFIER_NAMESPACES": ["bvbrc_data_row", "bvbrc_data_cell", "bvbrc_data_identifier",
            "bvbrc_data_population", "bvbrc_data_bucket"]}}

OUTPUT = {"purpose": "Proposed implementation interfaces, not installed production schemas or completion evidence",
    "version": "bvbrc_data_contract_shapes_2026_10_24_v1", "field_registry": REGISTRY,
    "export_map": EXPORTS, "schemas": {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": D},
    "fact_schemas": FACT_SCHEMAS,
    "numeric_text_grammars": {
        "nonnegative_decimal_integer": {"pattern": "^[0-9]+$", "numeric_type": "integer", "minimum": 0},
        "finite_nonnegative_decimal_scientific": {"pattern": "^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?$", "numeric_type": "number", "minimum": 0}},
    "function_contracts": {
        "parse_data_snapshot(snapshot: SourceSnapshot, *, prepared: dict) -> dict": "ParseResult; v2 PreparedQuery exact request/profile check, then actual native payload decoding. No Store/network.",
        "extract_collection_rows(page_sheet: dict, *, fields: tuple[str, ...]) -> dict": "CollectionRowsExtraction; every retained row in original order, cells/numerical_cells restricted to requested registered fields; absent selected fields preserve missing, fields outside selected_fields create explicit unselected slots. No new acquisition.",
        "calculate_page_counts(sheet: dict) -> dict": "PageComponents",
        "calculate_facet_fractions(sheet: dict, *, denominator_policy: str) -> dict": "FacetComponents; policy must equal same_response_exact_document_count",
        "calculate_feature_sequence_counts(join_sheet: dict) -> dict": "FeatureSequenceComponents",
        "extract_feature_sequence_join(feature_pages: list[dict], sequence_pages: list[dict], *, feature_ids: list[str], sequence_kind: str) -> dict": "FeatureSequenceSheet; AA, NA or both; supplied DataSheet objects only",
        "extract_molecular_experiment_rows(result_pages: list[dict], *, bioset_pages: list[dict], experiment_pages: list[dict], feature_pages: list[dict], result_ids: list[str], supplied_metadata: list[dict]) -> dict": "MolecularSheet; host-qualified supplied metadata; no source lookup",
        "bvbrc_data_fact_sources() -> dict": "Mapping exact six source names to {type: array, meaning: fixed description, report_schema: corresponding fact_schemas entry}; report_schema has top-level x-source and a closed item object, matching ExecutionEpisodes.fact_sources conventions",
        "validate_data_result_selector(selector: dict, *, request: dict) -> dict": "Finite deep copy preserving selector values; validates exact ResultSelector shape and request mode/collection/field/source-level relationships. It performs no source/Store lookup; host separately qualifies every named input",
        "project_bvbrc_data_facts(qualified_results: list[dict], *, selector: dict, requested_sources: tuple[str, ...]) -> dict": "Mapping exactly requested source names to arrays conforming to corresponding FACT_SCHEMAS; selector must equal each qualified result original selector, not change a frozen request; no silent omitted requested row",
        "resolve_bvbrc_data_identifier(qualified_results: list[dict], *, reference: str, namespace: str) -> bool": "Pure exact membership in registries built from each qualified result original selector and selected recorded rows/cells/IDs/population/buckets. Does not access Store or accept arbitrary provider-associated values; full return validation still checks relationships",
        "validate_bvbrc_data_return(form: dict, *, original_schema: dict, recorded_facts: dict) -> None": "Validate existing closed schema and whole projected relationships; recorded x-source arrays must exactly equal the requested recorded arrays, not merely resolve each string",
        "materialize_bvbrc_received_values(qualified_results: list[dict], *, admitted_form: dict, original_schema: dict) -> list[dict]": "ReceiverMaterialization list in original top-level field order; only requested BV-BRC x-sources and admitted selected rows/cells. Host inputs already custody-qualified. Missing metadata and exact native strings become visible data; no lookup or model",
        "render_bvbrc_received_values(materializations: list[dict]) -> str": "Deterministic source-value text/tables only. Preserve every requested value and distinction; escape delimiters/control characters; no truncation, task prose generation or action selection"
    },
    "semantic_constraints": [
        "All JSON objects are closed; all keys required unless DataQuery.required explicitly says otherwise. All numbers finite, booleans never numeric.",
        "Field enums are global syntax only; validate actual collection membership and registry flags for every field, sort, facet, predicate and projection.",
        "No registered date fields in this v1 registry: date ranges are incomplete and rejected rather than guessed.",
        "Only page permits fields/sort/offset/limit; count/facet emit zero rows/start zero and no selected fields/sort. Facet mode requires exactly one facet request; other modes reject it.",
        "Omitted page fields default to unique key only; empty fields rejected. Append unique key for custody if absent. Omitted or empty sort defaults to unique key ascending; append ascending unique-key tie breaker if absent.",
        "Predicate types follow native field type. In is homogeneous and nonempty. Range has a bound, null bound inclusivity false, lower <= upper. Equality is not analyzed text matching.",
        "Population key is SHA256 of canonical population record excluding population_key. It includes compiler and field version, endpoint, collection, filters, visibility, not row/facet windows, fields or sort.",
        "Prepared native request must be reproducible byte for byte. Request headers include Accept application/solr+json and Content-Type application/solrquery+x-www-form-urlencoded. No credentials or arbitrary headers.",
        "PreparedQuery is the new v2 contract only. Legacy requests, defaults, selectors, receipts and identities remain unchanged. Low-level native payload decoding can verify retained array fixtures without claiming a v2 acquisition.",
        "Cells enumerate selected_fields in order, one per selected registered field including absent keys. A requested extractor field absent from selected_fields is unselected, not a native missing value.",
        "NativeRow.status valid means all selected cells and native identity are well-formed; partial/invalid rows count in invalid_row_count, so valid_row_count + invalid_row_count equals returned_row_count. Missing selected values are valid missing facts; malformed values/identity are partial. Valid components survive other cell failures.",
        "NativeAtom has exactly its kind's value populated; null atom has all values null. Number atom always retains exact number_lexeme; null number_value denotes unrepresentable finite value with an explicit issue, never measured zero.",
        "Cell absent/null/unselected has zero atoms. Scalar has one atom; array preserves order and cardinality including empty arrays. Unexpected object is invalid and preserved by native_path into complete raw bytes.",
        "Numerical cells reference the corresponding selected raw cell key. Only reviewed numeric fields parse; numeric text grammars and PPI scalar-number exception are explicit. Their values never overwrite native atoms.",
        "Numeric unit_code and unit_basis report field-defined units only where registry declares them. Molecular measurement units remain unknown unless explicitly supplied; field name is not evidence for actual experimental normalization.",
        "Explicitly supplied unit strings attach unit_cell_keys to the numeric cell and unit_value_refs to its typed measurement. Materialization always includes those referenced unit values with the selected number; it does not require a separate metadata-field selection or silently map arbitrary unit strings into a standard code.",
        "Row keys are native SHA256 plus '/row/' plus zero-based ordinal; cell keys append '/field/' plus JSON Pointer escaped field. Bucket keys append '/facet/' plus escaped field plus '/bucket/' plus native ordinal; term keys append '/term'.",
        "Query population completeness and complete response bytes are distinct. Array/header totals are provider_reported, not exact. No response => no fabricated counts or rows. Count/facet docs empty is expected.",
        "For count/facet the page population_coverage is unknown (document rows intentionally not requested), next_offset null; count/facet aggregate completeness has its own exactness and qualification. Malformed facet term yields term null and is_missing_bucket null, not a fabricated native missing bucket.",
        "Facet terms permit only the registered exact string field (or null missing bucket). Counts are nonnegative integers. Fraction denominator is same successful exact response numFound; zero/inexact/partial/conflicting denominator produces unavailable, not 0/0.",
        "Facet all_categories_complete requires offset=0, min_count<=1, include_missing true, valid response, fewer nonmissing buckets than limit, and no truncation/partial evidence. Exactly limit buckets gives more_unknown. This concerns categories observed in this query, not a database snapshot.",
        "Selectors are entirely closed with all keys explicit. Page null reuses original page; non-null changes only offset/limit. Query_metadata is required for count/facet. Collection_rows row_indices address current response ordinal; a registered requested field absent from acquisition selected_fields is unavailable not_selected, never silently acquired.",
        "A requested row ordinal or result ID absent from the retained response yields an unavailable projected row with null row_ref and the requested ordinal/ID; it does not vanish. Native identifiers absent from a present row remain null. Unavailable requested metadata has an explicit metadata_unavailable entry, including unknown supplied units/replication/correction.",
        "Feature_sequence uses feature/sequence sheets only, explicit feature IDs and kind. Molecular uses bioset_result/bioset/experiment/genome_feature sheets only, explicit result IDs. Input references bind exact collection and current receiver possession. No implicit fetch.",
        "query_metadata and collection_rows require inputs=[] and supplied_metadata=[]. Join projections require page mode and the current collection to belong to their declared input collection set. feature_sequence requires supplied_metadata=[]. Molecular accepts only its four declared collections plus separately qualified supplied metadata sources. Repeated input source_ref with conflicting collection is invalid.",
        "Molecular metadata selector field must belong to its source-level collection or SUPPLIED_METADATA_FIELDS. Required seven measurement slots remain in the retained molecular sheet; only explicitly selected measurement fields cross the report.",
        "Supplied metadata provenance must be an actually received source whose exact record_path content equals supplied values; the host resolves and verifies it. Extractor accepts only already qualified supplied values.",
        "For supplied metadata, source_ref must identify an already received source with a retained JSON artifact; record_path is a JSON Pointer into that artifact. The pointed object equals the supplied metadata record without provenance. Other formats remain incompatible rather than triggering acquisition or an LLM. MetadataBinding preserves source/artifact/raw-byte and selected-content hashes.",
        "Supplied nested metadata is materialized as atomic cells at exact JSON Pointer paths, retaining array indexes and object field names. Its CellLocation.collection is bioset_result (the consuming relation); MaterializedCell.collection is null for the supplied source and source_level supplied. metadata_source_refs use existing source namespace, separately from BV-BRC input_source_refs.",
        "Feature sequence selection yields one edge per selected feature occurrence and requested kind; never collapse distinct feature IDs sharing MD5. Conflicting copies remain separate candidates and no arbitrary first candidate wins.",
        "FeatureSequenceEdge.feature_rows contains exactly one feature occurrence. Missing selected features have empty feature_rows. relation_count counts only joined or repeated_identical edges; missing/conflicting edges remain in the sheet and separate counts. native_sequence_record_count counts all retained rows in explicitly supplied sequence pages.",
        "input_page_counts is one entry per distinct (native_sha256,collection) supplied page; duplicate identical bytes remain repeated representations in host input bindings, never independent evidence. Counts and all joins use only explicit supplied pages. Input counts allow the separate calculator to count unjoined supplied sequence records without rereading any source.",
        "Molecular result ID duplicates with conflicting measurements remain separate retained occurrences and are conflict-qualified; exact repeated representations are explicit. Parent links use recorded IDs and agreement, never array order.",
        "QualifiedResult is constructed only by host read_bvbrc_result after original read_result and artifact/selector/input/receipt/possession checks. A JSON flag or provider name does not confer trust. Pure views receive this already qualified structure.",
        "Incoming child-return admission is not circular: current_child_return possession requires the exact successful runtime_report_attempt row for the host operation key, matching parent, child, original report contract and full form. Validate the producer child's owned/received result and recorded projection before adding parent receipts. A free-standing same-scope form is insufficient.",
        "QualifiedResult.grading input_bindings match input_results exactly, including native bytes and grading refs. No self source_ref inside PublishedGrading: attach root binding after source publication, avoiding source/grading identity cycles.",
        "Reference IDs derive from qualified result source and selected row/cell/bucket/population keys. Identifier namespace accepts only validated native ID values linked to the selected rows or explicitly requested missing join operands; namespace membership alone does not validate a whole returned row.",
        "FACT_SCHEMAS use only supported closed schema features. Internal oneOf/anyOf/$ref is expanded or dispatch-validated outside communication; never relax communication.py to admit arbitrary model strings.",
        "Parent numeric-row views also support vocabulary-only rows with zero measurements and requested metadata cells. Such rows are acquisition facts, not a scientific scoring sheet.",
        "ReceiverMaterialization is host-generated, not model-generated. Resolve only refs actually present in the admitted form against its qualified selected projection; retain every requested value, source level, missingness and order. No extra lookup action or summarizing model.",
        "Exact receiver text quotes string/array values, distinguishes empty string/null/absent/unselected, displays numbers and units as requested and marks data as source values. Tracking hashes/run IDs stay outside prompt text. No silent top-N or character truncation.",
        "Acquisition identity excludes only local projection/calculator variants; changed effective native request or response bytes remains distinct. Historical legacy receipt identities are immutable. Re-rendering, recalculation and replay add no completed action or acquired-record credit."
    ]}
(HERE / "CONTRACT_SHAPES.json").write_text(json.dumps(OUTPUT, indent=2, allow_nan=False) + "\n")
print("Wrote CONTRACT_SHAPES.json:", len(D), "internal definitions,", len(R), "closed report row types,",
      len(REGISTRY), "collections,", sum(len(c["fields"]) for c in REGISTRY.values()), "fields")
