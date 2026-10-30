"""Check the planning artifacts and construct labeled expected fixtures.

This does not implement or invoke a production BV-BRC parser, compiler, service,
grader or episode. It reads only this task's retained evidence and proposed
schemas. Hypothetical Store/episode bindings are explicitly labeled synthetic.
"""
from pathlib import Path
import copy
import hashlib
import json
from urllib.parse import parse_qsl, urlsplit

from jsonschema import Draft202012Validator
from gene_annotation_episode.communication import validate_closed_schema, validate_form

HERE = Path(__file__).parent
SHAPES = json.loads((HERE / "CONTRACT_SHAPES.json").read_text())
FROZEN = json.loads((HERE / "D1_QUERY_CONTRACT_FROZEN.json").read_text())
DEFS = SHAPES["schemas"]["$defs"]
CHECKS = []

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()

def check(name, condition):
    assert condition, name
    CHECKS.append(name)

def validate(name, value):
    schema = {"$ref": "#/$defs/" + name, "$defs": DEFS}
    Draft202012Validator(schema).validate(value)
    CHECKS.append("example conforms to " + name)

def body(name):
    return json.loads((HERE / (name + ".body")).read_bytes())

def meta(name):
    return json.loads((HERE / (name + ".meta.json")).read_text())

def atom(value):
    # Expected fixture values only, not a native lexer: original numeric spelling
    # is checked explicitly for each fixture number retained in these examples.
    kind = "null" if value is None else "boolean" if type(value) is bool else "number" if type(value) in (int, float) else "string"
    return {"kind": kind, "string_value": value if kind == "string" else None,
        "number_value": value if kind == "number" else None,
        "boolean_value": value if kind == "boolean" else None,
        "number_lexeme": json.dumps(value) if kind == "number" else None}

def rowkey(native_sha, index):
    return native_sha + "/row/" + str(index)

def rowloc(name, collection, index):
    native_sha = meta(name)["sha256"]
    return {"native_sha256": native_sha, "collection": collection, "row_key": rowkey(native_sha, index)}

def cellloc(name, collection, index, field, level):
    location = rowloc(name, collection, index)
    return {**location, "cell_key": location["row_key"] + "/field/" + field,
        "field": field, "source_level": level}

Draft202012Validator.check_schema(SHAPES["schemas"])
for name, schema in SHAPES["fact_schemas"].items():
    validate_closed_schema({"type": "object", "properties": {"values": schema},
        "required": ["values"], "additionalProperties": False})
    CHECKS.append("existing closed report validator accepts " + name)
check("D1 frozen field registry unchanged", FROZEN["field_registry"] == SHAPES["field_registry"])
for name, schema in FROZEN["schemas"]["$defs"].items():
    check("D1 frozen schema unchanged: " + name, schema == DEFS[name])
check("22 fixed collections", len(SHAPES["field_registry"]) == 22)
check("318 reviewed fields", sum(len(c["fields"]) for c in SHAPES["field_registry"].values()) == 318)
for path in sorted(HERE.glob("*.meta.json")):
    record = json.loads(path.read_text())
    native = path.with_name(path.name.replace(".meta.json", ".body"))
    if native.exists() and "sha256" in record:
        check("raw byte digest " + native.name, sha(native.read_bytes()) == record["sha256"])
        check("raw byte length " + native.name, len(native.read_bytes()) == record["byte_count"])

feature_rows = body("feature_page")
sequences = body("feature_sequences")
check("two separate feature IDs", len(feature_rows) == 2 and len({r["feature_id"] for r in feature_rows}) == 2)
check("shared AA and NA hashes", all(feature_rows[0][key] == feature_rows[1][key] for key in ("aa_sequence_md5", "na_sequence_md5")))
sequence_sheet = {"version": "bvbrc_feature_sequence_sheet_v1",
    "selection": {"feature_ids": [r["feature_id"] for r in feature_rows], "sequence_kind": "both"},
    "input_native_sha256s": [meta(n)["sha256"] for n in ("feature_page", "feature_sequences")],
    "input_page_counts": [{"native_sha256": meta(n)["sha256"], "collection": c,
        "retained_row_count": 2, "valid_row_count": 2} for n, c in
        (("feature_page", "genome_feature"), ("feature_sequences", "feature_sequence"))],
    "edges": [], "requirements": [], "issues": []}
for feature_index, feature in enumerate(feature_rows):
    for kind, prefix in (("AA", "aa"), ("NA", "na")):
        candidates = [(i, r) for i, r in enumerate(sequences) if r["md5"] == feature[prefix + "_sequence_md5"]]
        check("one retained sequence for " + str(feature_index) + kind, len(candidates) == 1)
        sequence_index, sequence = candidates[0]
        raw_match = hashlib.md5(sequence["sequence"].encode("ascii")).hexdigest() == sequence["md5"]
        length_match = len(sequence["sequence"]) == feature[prefix + "_length"]
        check("exact raw MD5 " + str(feature_index) + kind, raw_match)
        check("native feature length " + str(feature_index) + kind, length_match)
        sequence_sheet["edges"].append({"edge_key": rowkey(meta("feature_page")["sha256"], feature_index) + "/" + kind,
            "feature_id": feature["feature_id"], "feature_rows": [rowloc("feature_page", "genome_feature", feature_index)],
            "sequence_kind": kind, "native_md5": sequence["md5"],
            "sequence_rows": [rowloc("feature_sequences", "feature_sequence", sequence_index)],
            "sequence_cells": [cellloc("feature_sequences", "feature_sequence", sequence_index, "sequence", "sequence")],
            "feature_metadata_cells": [cellloc("feature_page", "genome_feature", feature_index, field, "feature")
                for field in ("genome_id", "sequence_id", "patric_id", "annotation", "start", "end", "strand") if field in feature],
            "sequence_length": len(sequence["sequence"]), "feature_length": feature[prefix + "_length"],
            "raw_md5_match": raw_match, "length_match": length_match, "join_status": "joined", "reason": None, "issues": []})
sequence_components = {"version": "bvbrc_feature_sequence_components_v1", "selected_feature_count": 2,
    "retained_feature_row_count": 2, "native_sequence_record_count": 2, "distinct_joined_aa_sequence_count": 1,
    "distinct_joined_na_sequence_count": 1, "relation_count": 4, "missing_key_count": 0,
    "missing_record_count": 0, "conflicting_relation_count": 0, "length_agreement_count": 4}
validate("FeatureSequenceSheet", sequence_sheet)
validate("FeatureSequenceComponents", sequence_components)
na = next(r for r in sequences if r["sequence_type"] == "NA")
check("NA uppercase would change its MD5", hashlib.md5(na["sequence"].upper().encode("ascii")).hexdigest() != na["md5"])

# Full count/facet sheet fixture, with an explicitly hypothetical v2 preparation.
facet_native, facet_meta = body("feature_facet_solr_zero"), meta("feature_facet_solr_zero")
ids = [r["feature_id"] for r in feature_rows]
facet_request = {"field": "annotation", "offset": 0, "limit": 2, "min_count": 1, "sort": "index", "include_missing": True}
query = {"version": "bvbrc_data_request_v2", "collection": "genome_feature", "mode": "facet",
    "filters": [{"field": "feature_id", "operator": "in", "value": ids}], "facet": facet_request}
population = {"version": "bvbrc_data_population_v1", "base_url": "https://www.bv-brc.org/api",
    "collection": "genome_feature", "filters": query["filters"], "visibility": "public_unauthenticated",
    "compiler_version": "bvbrc_solr_compiler_v1", "field_contract_version": "bvbrc_data_fields_2026_10_24_v1"}
population["population_key"] = sha(population)
prepared = {"version": "bvbrc_data_prepared_v2", "service": "bvbrc_data", "original_request": query,
    "page_selector": None, "effective_request": {"version": "bvbrc_data_effective_query_v2",
        "collection": "genome_feature", "mode": "facet", "filters": query["filters"], "fields": [], "sort": [],
        "offset": 0, "limit": 0, "facet": facet_request}, "query_population": population,
    "field_selection": {"requested_fields": None, "defaulted_fields": [], "custody_added_fields": []},
    "sort_selection": {"requested_sort": None, "defaulted_sort": [], "tie_breaker_added": None},
    "request_profile": "solr_query_solr_json_v1", "native_request": {"method": "GET", "url": facet_meta["url"],
        "headers": FROZEN["encoding"]["headers"], "body": None,
        "query_parameters": [{"name": k, "value": v} for k, v in parse_qsl(urlsplit(facet_meta["url"]).query)]}}
validate("PreparedQuery", prepared)
facets = facet_native["facet_counts"]["facet_fields"]["annotation"]
bucket_rows, fractions = [], []
for index in range(0, len(facets), 2):
    term, count = facets[index:index + 2]
    key = facet_meta["sha256"] + "/facet/annotation/bucket/" + str(index // 2)
    bucket_rows.append({"bucket_key": key, "term_cell_key": key + "/term",
        "native_path": "/facet_counts/facet_fields/annotation/" + str(index), "term": atom(term),
        "is_missing_bucket": term is None, "count": count, "status": "valid", "issues": []})
    fractions.append({"bucket_key": key, "numerator": count, "denominator": 2, "fraction": count / 2, "reason": None})
check("facet two real terms and explicit missing bucket", facets == ["PATRIC", 1, "RefSeq", 1, None, 0])
check("same-response exact denominator 2", facet_native["response"]["numFound"] == 2 and facet_native["response"]["numFoundExact"] is True)
check("facet count response has no docs", facet_native["response"]["docs"] == [])
sheet = {"version": "bvbrc_data_sheet_v1", "collection": "genome_feature", "mode": "facet",
    "custody": {"native_sha256": facet_meta["sha256"], "retrieved_at": facet_meta["retrieved_at"],
        "requested_url": facet_meta["url"], "effective_url": facet_meta["effective_url"],
        "media_type": "application/solr+json; charset=utf-8", "native_profile": "solr_json_envelope_v1",
        "prepared_sha256": sha(prepared), "field_contract_version": "bvbrc_data_fields_2026_10_24_v1"},
    "transport": {"http_status": facet_meta["status"], "body_complete": True,
        "headers": [{"name": k, "value": v} for k, v in facet_meta["headers"]], "failure_code": None,
        "automatic_redirects": False, "native_query_time_ms": facet_native["responseHeader"]["QTime"]},
    "qualification": {"service_matches": True, "request_matches": True, "transport_complete": True,
        "http_success": True, "format_valid": True, "population_metadata_valid": True,
        "native_partial_results": None, "requested_fields_valid": True, "status": "complete"},
    "population": {"population_key": population["population_key"],
        "compiled_query": facet_native["responseHeader"]["params"]["q"],
        "echoed_query": facet_native["responseHeader"]["params"]["q"],
        "echoed_filter_queries": [facet_native["responseHeader"]["params"]["fq"]],
        "reported_total": 2, "native_num_found_exact": True, "exactness": "exact", "native_location": "/response/numFound"},
    "selected_fields": [], "page": {"mode": "facet", "requested_offset": None, "requested_limit": None,
        "response_start": 0, "native_content_range": "items 0-0/2", "returned_row_count": 0,
        "valid_row_count": 0, "invalid_row_count": 0, "reported_total": 2, "count_exactness": "exact",
        "response_complete": True, "population_coverage": "unknown", "next_offset": None, "next_offset_basis": None},
    "count": {"population_key": population["population_key"], "reported_value": 2, "exactness": "exact",
        "availability": "available", "reason": None, "native_location": "/response/numFound"},
    "rows": [], "facets": [{"population_key": population["population_key"], "request": facet_request,
        "native_location": "/facet_counts/facet_fields/annotation", "buckets": bucket_rows,
        "returned_nonmissing_bucket_count": 2, "bucket_window_status": "more_unknown", "all_categories_complete": False,
        "issues": []}], "issues": []}
validate("DataSheet", sheet)
facet_components = {"version": "bvbrc_data_facet_components_v1", "denominator_policy": "same_response_exact_document_count",
    "population_key": population["population_key"], "fractions": fractions}
validate("FacetComponents", facet_components)
selector = {"version": "bvbrc_data_result_selector_v2", "page": None,
    "projection": {"family": "query_metadata"}, "inputs": [], "supplied_metadata": []}
validate("ResultSelector", selector)
parse_result = {"version": "bvbrc_data_parse_result_v1", "status": "complete", "sheet": sheet,
    "failures": [], "retained_native_sha256": facet_meta["sha256"]}
grading = {"version": "bvbrc_data_grading_v1", "prepared": prepared, "selector": selector,
    "parse_result": parse_result, "page_components": {"version": "bvbrc_data_page_components_v1",
        "native_row_count": 0, "valid_row_count": 0, "invalid_row_count": 0, "reported_population_count": 2,
        "population_exactness": "exact"}, "facet_components": facet_components, "feature_sequence_sheet": None,
    "feature_sequence_components": None, "molecular_sheet": None, "input_bindings": [], "metadata_bindings": []}
qualified = {"version": "bvbrc_data_qualified_result_v1", "service": "bvbrc_data",
    "binding": {"source_ref": "source_fixture_facet", "native_artifact_ref": "artifact_fixture_native",
        "native_sha256": facet_meta["sha256"], "grading_artifact_ref": "artifact_fixture_grading",
        "collection": "genome_feature", "acquisition_assignment_sha256": sha("fixture_assignment"), "selector_sha256": sha(selector)},
    "host_qualification": {"run_id": "fixture_run", "source_episode_id": "fixture_results", "receiver_episode_id": "fixture_parent",
        "scope_sha256": sha("fixture_scope"), "receipt_verified": True, "native_bytes_verified": True,
        "grading_custody_verified": True, "original_selection_verified": True, "input_bindings_verified": True,
        "receiver_possession_verified": True, "possession_basis": "admitted_return"}, "grading": grading, "input_results": []}
validate("QualifiedResult", qualified)

# Molecular values from distinct retained feature measurements and their exact parents.
expressions, biosets, experiments = body("expression_page"), body("bioset_page"), body("experiment_page")
measurement_fields = ["counts", "fpkm", "tpm", "log2_fc", "p_value", "z_score", "other_value"]
molecular = {"version": "bvbrc_molecular_sheet_v1", "selected_result_ids": [r["id"] for r in expressions],
    "input_native_sha256s": [meta(n)["sha256"] for n in ("expression_page", "bioset_page", "experiment_page")],
    "supplied_metadata": [], "rows": [], "missing_result_ids": [], "requirements": [], "issues": []}
for index, result in enumerate(expressions):
    bioset_index = next(i for i, r in enumerate(biosets) if r["bioset_id"] == result["bioset_id"])
    experiment_index = next(i for i, r in enumerate(experiments) if r["exp_id"] == result["exp_id"])
    check("molecular experiment agrees " + str(index), biosets[bioset_index]["exp_id"] == result["exp_id"])
    numeric = []
    for field in measurement_fields:
        present = field in result
        numeric.append({"cell_key": cellloc("expression_page", "bioset_result", index, field, "result")["cell_key"],
            "field": field, "native_path": "/" + str(index) + "/" + field, "value": result.get(field),
            "status": "reported" if present else "missing", "reason": None if present else "native_field_absent",
            "quantity_kind": "bioset_result." + field, "unit_code": None, "unit_basis": "unknown",
            "unit_cell_keys": [],
            "denominator_value": None, "denominator_basis": "unknown", "origin": "native_reported" if present else "unavailable",
            "uncertainty_cell_keys": [], "issue_codes": []})
    metadata = []
    for name, collection, ordinal, record, level, fields in [
        ("expression_page", "bioset_result", index, result, "result", ["result_type", "treatment_name", "treatment_type", "treatment_amount", "treatment_duration"]),
        ("bioset_page", "bioset", bioset_index, biosets[bioset_index], "bioset", ["analysis_group_1", "analysis_group_2", "analysis_method", "treatment_duration"]),
        ("experiment_page", "experiment", experiment_index, experiments[experiment_index], "experiment", ["measurement_technique", "samples", "biosets", "treatment_duration"])]:
        for field in fields:
            present = field in record
            metadata.append({"field": field, "source_level": level,
                "cells": [cellloc(name, collection, ordinal, field, level)] if present else [],
                "status": "reported" if present else "missing", "reason": None if present else "native_field_absent"})
    for field in ["measurement_units", "biological_replicate_ids", "technical_replicate_ids", "normalization_method", "pvalue_correction_method", "contrast"]:
        metadata.append({"field": field, "source_level": "supplied", "cells": [], "status": "missing", "reason": "missing_input_page"})
    molecular["rows"].append({"row_key": rowkey(meta("expression_page")["sha256"], index), "result_id": result["id"],
        "result_rows": [rowloc("expression_page", "bioset_result", index)], "exp_id": result["exp_id"],
        "bioset_id": result["bioset_id"], "feature_id": result["feature_id"], "entity_id": result["entity_id"],
        "experiment": {"expected_id": result["exp_id"], "rows": [rowloc("experiment_page", "experiment", experiment_index)], "status": "matched", "reason": None},
        "bioset": {"expected_id": result["bioset_id"], "rows": [rowloc("bioset_page", "bioset", bioset_index)], "status": "matched", "reason": None},
        "feature": {"expected_id": result["feature_id"], "rows": [], "status": "missing_input", "reason": "missing_input_page"},
        "measurements": numeric, "metadata": metadata, "relationship_status": "partial", "issues": []})
molecular["requirements"] = [{"collection": "genome_feature", "field": "feature_id",
    "values": [r["feature_id"] for r in expressions], "sequence_kind": None, "reason": "missing_input_page"}]
validate("MolecularSheet", molecular)
check("actual expression negatives retained", [r["log2_fc"] for r in expressions] == [-0.132, -0.129])
check("actual z scores retained", [r["z_score"] for r in expressions] == [-0.544, -0.556])
check("unreported measurements are absent not zero", all(all(f not in r for f in ["counts", "fpkm", "tpm", "p_value", "other_value"]) for r in expressions))
check("bioset empty duration is a native empty string", next(r for r in biosets if r["bioset_id"] == "57692532")["treatment_duration"] == "")
check("native empty TPM query", body("expression_tpm_page") == [] and any(k.lower() == "content-range" and v == "items 0-0/0" for k, v in meta("expression_tpm_page")["headers"]))
check("counts is a native float field", SHAPES["field_registry"]["bioset_result"]["fields"]["counts"]["solr_type"] == "float")
check("native protein feature e-value text", body("protein_feature_page")[0]["e_value"] == "1.25E-9")
check("native PPI scalar score contradicts declared string array", type(body("ppi_page")[0]["score"]) is float and SHAPES["field_registry"]["ppi"]["fields"]["score"]["multi_valued"] is True)
for name, length in [("range_gt", 1), ("range_lt", 1), ("range_ge", 0), ("range_le", 0)]:
    check("deployed equality-boundary " + name, len(body(name)) == length)
check("explicit Solr inclusive boundary", body("solr_range_inclusive")["response"]["numFound"] == 1)
check("explicit Solr exclusive boundary", body("solr_range_exclusive")["response"]["numFound"] == 0)
check("literal failed native request retained", meta("feature_count")["status"] == 400)

# A populated page-row extraction fixture, including an actually reported zero.
genome = body("genome_page")[0]
genome_fields = ["genome_id", "genome_length", "gc_content", "plasmids"]
genome_cells, genome_numbers = [], []
for field in genome_fields:
    location = cellloc("genome_page", "genome", 0, field, "row")
    genome_cells.append({"cell_key": location["cell_key"], "field": field,
        "native_path": "/0/" + field, "presence": "present", "native_shape": "scalar",
        "atoms": [atom(genome[field])], "status": "valid", "field_schema_status": "match", "issue_codes": []})
    if field != "genome_id":
        genome_numbers.append({"cell_key": location["cell_key"], "field": field,
            "native_path": "/0/" + field, "value": genome[field], "status": "reported", "reason": None,
            "quantity_kind": "genome." + field, "unit_code": "nucleotide" if field == "genome_length" else None,
            "unit_basis": "field_definition" if field == "genome_length" else "unknown", "unit_cell_keys": [],
            "denominator_value": None, "denominator_basis": "unknown", "origin": "native_reported",
            "uncertainty_cell_keys": [], "issue_codes": []})
genome_extraction = {"version": "bvbrc_collection_rows_v1", "collection": "genome",
    "native_sha256": meta("genome_page")["sha256"], "requested_fields": genome_fields,
    "rows": [{"row_key": rowkey(meta("genome_page")["sha256"], 0), "row_index": 0,
        "native_path": "/0", "native_id": genome["genome_id"], "status": "valid", "cells": genome_cells,
        "numerical_cells": genome_numbers, "issues": []}], "issues": []}
validate("CollectionRowsExtraction", genome_extraction)
check("actual reported zero remains present numeric zero", genome_numbers[-1]["value"] == 0 and genome_numbers[-1]["status"] == "reported")

# Filled typed return fixture: actual values, hypothetical host references.
row = molecular["rows"][1]
result = expressions[1]
selected_metadata = [{"field": "treatment_name", "value_ref": "cell_fixture_result_treatment", "source_level": "result"},
    {"field": "treatment_duration", "value_ref": "cell_fixture_bioset_duration", "source_level": "bioset"},
    {"field": "measurement_technique", "value_ref": "cell_fixture_experiment_technique", "source_level": "experiment"}]
typed_row = {"source_ref": "source_fixture_expression", "collection": "bioset_result",
    "input_source_refs": ["source_fixture_bioset", "source_fixture_experiment"], "metadata_source_refs": [],
    "status": "partial", "row_ref": "row_fixture_expression_1", "requested_row_index": None,
    "native_id": result["id"], **{k: result[k] for k in ("exp_id", "bioset_id", "feature_id", "entity_id")},
    "result_id": result["id"], "experiment_row_refs": ["row_fixture_experiment"], "bioset_row_refs": ["row_fixture_bioset"],
    "feature_row_refs": [], "measurements": [{"field": c["field"], "cell_ref": "cell_fixture_" + c["field"],
        "value": c["value"], "unit_code": None, "unit_basis": "unknown", "unit_value_refs": [], "denominator_value": None,
        "denominator_basis": "unknown", "uncertainty_cell_refs": [], "origin": "native_reported"}
        for c in row["measurements"] if c["value"] is not None],
    "unavailable": [{"field": c["field"], "reason": c["reason"]} for c in row["measurements"] if c["value"] is None],
    "metadata_cells": selected_metadata, "metadata_unavailable": [{"field": f, "source_level": "supplied", "reason": "missing_input_page"}
        for f in ("measurement_units", "biological_replicate_ids", "pvalue_correction_method")],
    "relationship_status": "partial"}
report_schema = {"type": "object", "properties": {"expression": SHAPES["fact_schemas"]["execution_bvbrc_expression_rows"]},
    "required": ["expression"], "additionalProperties": False}
validate_form({"expression": [typed_row]}, report_schema, lambda reference, namespace: True)
CHECKS.append("filled expression form accepted structurally; resolver intentionally fixture-only, not host admission")
materialized_cells = []
for source, row_ref, cell_ref, collection, native_id, field, level, value in [
    ("source_fixture_expression", "row_fixture_expression_1", "cell_fixture_result_treatment", "bioset_result", result["id"], "treatment_name", "result", result["treatment_name"]),
    ("source_fixture_bioset", "row_fixture_bioset", "cell_fixture_bioset_duration", "bioset", result["bioset_id"], "treatment_duration", "bioset", ""),
    ("source_fixture_experiment", "row_fixture_experiment", "cell_fixture_experiment_technique", "experiment", result["exp_id"], "measurement_technique", "experiment", "Microarray")]:
    materialized_cells.append({"source_ref": source, "row_ref": row_ref, "cell_ref": cell_ref,
        "collection": collection, "native_id": native_id, "field": field, "source_level": level,
        "presence": "present", "native_shape": "scalar", "atoms": [atom(value)], "status": "valid", "issue_codes": []})
for measurement in typed_row["measurements"]:
    materialized_cells.append({"source_ref": "source_fixture_expression", "row_ref": "row_fixture_expression_1",
        "cell_ref": measurement["cell_ref"], "collection": "bioset_result", "native_id": result["id"],
        "field": measurement["field"], "source_level": "result", "presence": "present", "native_shape": "scalar",
        "atoms": [atom(measurement["value"])], "status": "valid", "issue_codes": []})
materialization = {"version": "bvbrc_received_values_v1", "admission_key": "fixture_admission", "form_field": "expression",
    "fact_source": "execution_bvbrc_expression_rows", "facts": [typed_row], "cells": materialized_cells,
    "unavailable": [{"collection": "bioset_result", "native_id": result["id"], "field": u["field"],
        "source_level": "result", "reason": u["reason"]} for u in typed_row["unavailable"]] +
        [{"collection": "bioset_result", "native_id": result["id"], **u} for u in typed_row["metadata_unavailable"]]}
validate("ReceiverMaterialization", materialization)

examples = {"version": "bvbrc_planning_examples_v1", "interpretation":
    "Native numerical values are copied from retained responses; prepared v2 records, sheets, source refs, admission flags and report forms are expected fixtures only. No production parser or episode produced them.",
    "feature_sequence_expected_sheet": sequence_sheet, "feature_sequence_expected_components": sequence_components,
    "genome_page_expected_extraction": genome_extraction,
    "facet_expected_sheet": sheet, "facet_expected_components": facet_components,
    "qualified_result_fixture": qualified, "molecular_expected_sheet": molecular,
    "expression_report_fixture": {"schema": report_schema, "form": {"expression": [typed_row]}},
    "receiver_materialization_fixture": materialization,
    "empty_population_fraction_fixture": {"native_count": 0, "numerator": 0, "denominator": 0,
        "fraction": None, "reason": "empty_population", "evidence_kind": "synthetic_calculator_edge_case"},
    "no_data_native_evidence": {"artifact": "expression_tpm_page.body", "body": [], "content_range": "items 0-0/0",
        "meaning": "Zero matching rows for this exact queried population; no per-feature TPM measurement is reported."}}
(HERE / "FILLED_EXAMPLES.json").write_text(json.dumps(examples, indent=2, allow_nan=False) + "\n")
(HERE / "RECEIVER_TEXT_EXAMPLE.txt").write_text('''STEERING excerpt — admitted native values, not instructions

Result 00000317-5d60-4e06-9c35-c42e53fd5ae3
Experiment 30087; bioset 57692532
Feature PATRIC.511145.12.NC_000913.CDS.1741481.1742854.fwd

Field | Source level | Exact value | Qualification
log2_fc | result | -0.129 | native reported; experimental units unknown
z_score | result | -0.556 | native reported; experimental units unknown
treatment_name | result | "glucose" | native reported
treatment_duration | bioset | "" | present empty string
measurement_technique | experiment | "Microarray" | native reported
counts, fpkm, tpm, p_value, other_value | result | unavailable | native fields absent
measurement_units, biological_replicate_ids, pvalue_correction_method | supplied | unavailable | no supplied metadata
feature relationship | feature | unavailable | no feature page supplied

This is a filled planning example. Its host admission is synthetic; no episode
received this text during this study. Native values come from the retained rows.
''')
report = {"version": "bvbrc_planning_verification_v1", "status": "passed",
    "check_count": len(CHECKS), "checks": CHECKS,
    "executed": ["offline schema validation", "existing closed report schema validator", "raw byte/hash/length checks",
        "explicit native expected numerical and association checks", "labeled expected-fixture shape validation"],
    "not_executed": ["production v2 query compiler", "production native sheet parser", "production calculator functions",
        "source/receipt host admission", "provider prompt delivery", "model episode", "HMMER or BLAST work"],
    "D1_frozen_sha256": sha((HERE / "D1_QUERY_CONTRACT_FROZEN.json").read_bytes()),
    "contract_shapes_sha256": sha((HERE / "CONTRACT_SHAPES.json").read_bytes())}
(HERE / "REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
print("Planning verification passed:", len(CHECKS), "checks; no production capability claimed")
