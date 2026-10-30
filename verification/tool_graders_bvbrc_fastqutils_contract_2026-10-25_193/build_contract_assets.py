"""Generate review-only finite schema/example assets; not a production grader."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def arr(items):
    return {"type": "array", "items": items}


def nullable(node):
    return {"anyOf": [node, {"type": "null"}]}


def ref(name):
    return {"$ref": "#/$defs/" + name}


TEXT = {"type": "string"}
TOKEN = {"type": "string", "minLength": 1}
ID = {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.:/%~-]*$"}
COUNT = {"type": "integer", "minimum": 0}
NUMBER = {"type": "number"}
STATES = ["available", "partial", "missing", "not_measured", "failed", "malformed", "truncated", "incompatible", "undefined"]
UNITS = ["reads", "bases", "pairs", "alignment_records", "phred", "phred_deviation", "percent", "fraction", "ratio", "expected_errors", "scaled_native_count", "native_count", "dimensionless", "ascii", "bp", "kbp", "Mbp", "Gbp"]
METRICS = [
    "fastq_read_count", "fastq_base_count", "fastq_symbol_count", "fastq_min_length", "fastq_max_length",
    "fastq_length_histogram_count", "quality_character_count", "phred_histogram_count", "verified_pair_count",
    "fastqc_total_sequences", "fastqc_flagged_sequences", "fastqc_total_bases_display", "fastqc_min_length", "fastqc_max_length", "fastqc_gc_percent",
    "fastqc_base_quality_mean", "fastqc_base_quality_median", "fastqc_base_quality_lower_quartile", "fastqc_base_quality_upper_quartile", "fastqc_base_quality_p10", "fastqc_base_quality_p90",
    "fastqc_tile_quality_deviation", "fastqc_sequence_quality_count", "fastqc_base_content_percent", "fastqc_n_percent", "fastqc_sequence_gc_smoothed_count", "fastqc_length_bin_count",
    "fastqc_total_deduplicated_percent", "fastqc_duplication_bin_percent", "fastqc_overrepresented_count", "fastqc_overrepresented_percent", "fastqc_adapter_percent",
    "fastqc_kmer_scaled_count", "fastqc_kmer_pvalue", "fastqc_kmer_obs_exp_max",
    "trim_processed_count", "trim_removed_short_count", "trim_removed_short_percent", "trim_removed_n_count", "trim_removed_n_percent", "trim_removed_long_count", "trim_removed_long_percent",
    "trim_validation_pair_count", "trim_removed_pair_count", "trim_removed_pair_percent", "trim_native_option", "trim_adapter_detection_count",
    "fastq_pair_left_paired", "fastq_pair_right_paired", "fastq_pair_left_single", "fastq_pair_right_single",
    "hostile_reads_in", "hostile_reads_out", "hostile_reads_removed", "hostile_removed_proportion",
    "bam_record_count", "bam_primary_record_count", "bam_secondary_record_count", "bam_supplementary_record_count", "bam_mapped_primary_count", "bam_mapq_histogram_count", "bam_mapq_unavailable_count",
]
COMPONENT_METRICS = ["gc_acgt_fraction", "n_fraction", "ambiguous_fraction", "mean_read_length", "mean_phred", "q_ge_threshold_fraction", "phred_implied_expected_errors", "phred_implied_error_fraction", "read_retention_fraction", "base_retention_fraction", "pair_retention_fraction", "removed_count", "removed_fraction", "native_report_retention_fraction", "distinct_mapped_read_fraction", "primary_record_fraction", "report_count_difference"]
ISSUES = ["missing_artifact", "partial_transfer", "malformed_native", "nonfinite_native", "unsupported_format", "unsupported_version", "producer_version_unproven", "compression_suffix_mismatch", "truncated_compressed_stream", "missing_bgzf_eof", "unknown_quality_encoding", "invalid_quality_score", "invalid_sequence_symbol", "ambiguous_pair_key", "missing_mate", "association_unresolved", "stage_execution_unknown", "stage_reused_report", "artifact_collision", "input_path_reused", "unknown_reference", "reference_incomplete", "missing_denominator", "zero_denominator", "incompatible_population", "count_inconsistent", "not_retained_by_service", "report_overwritten", "unsupported_report_section", "native_fallback_value", "rounded_native_value", "truncated_native_display", "native_estimator", "synthetic_identity", "missing_requested_value"]
FORMATS = ["fastq", "fastqc_html_0_12_1", "fastqc_zip_0_12_1", "fastqc_data_0_12_1", "trim_galore_report_0_6_10", "fastq_pair_stderr_0_3", "hostile_json_1_1_0", "sam_1_6", "bam_1", "bai", "samstat_html", "sra_metadata", "native_text", "native_json", "unknown"]
defs = {}
defs["Diagnostic"] = obj({"code": enum(*ISSUES), "source_refs": arr(ID), "locator": nullable(TOKEN), "affected_refs": arr(ID)})
defs["Locator"] = obj({"member": nullable(TEXT), "block": TOKEN, "block_ordinal": COUNT, "row_ordinal": nullable(COUNT), "field": TOKEN, "byte_start": nullable(COUNT), "byte_end": nullable(COUNT)})
defs["Axis"] = obj({"kind": enum("none", "base_closed_1", "length_closed", "quality_score", "quality_ascii", "symbol", "adapter", "sequence", "duplication_bin", "tile_base_closed_1", "native_label", "mapq"), "label": nullable(TEXT), "lower": nullable(NUMBER), "upper": nullable(NUMBER)})
defs["Artifact"] = obj({"id": ID, "source_ref": ID, "content_ref": ID, "task_ref": ID, "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "byte_count": COUNT, "native_name": TOKEN, "declared_format": enum(*FORMATS), "actual_format": enum(*FORMATS), "compression": enum("none", "gzip", "bgzf", "zip", "unknown"), "transfer_scope": enum("complete", "partial", "unknown"), "producer_name": nullable(TOKEN), "producer_version": nullable(TOKEN), "identity": enum("genuine_service_artifact", "supplied_native_artifact", "source_executed_synthetic", "handcrafted_synthetic", "unknown")})
defs["Cell"] = obj({"id": ID, "artifact_ref": ID, "locator": ref("Locator"), "metric": enum(*METRICS), "axis": ref("Axis"), "population_ref": nullable(ID), "association_ref": nullable(ID), "state": enum(*STATES), "value": nullable(NUMBER), "native_token": nullable(TEXT), "unit": enum(*UNITS), "meaning": enum("observed_count", "observed_native", "native_normalized", "native_estimate", "native_configuration"), "precision": enum("exact_for_retained_population", "not_reported", "native_rounded", "native_truncated_display", "native_estimator"), "diagnostic_codes": arr(enum(*ISSUES))})
defs["Cell"]["allOf"] = [{"if": {"properties": {"state": {"enum": ["available", "partial"]}}}, "then": {"properties": {"value": NUMBER}}, "else": {"properties": {"value": {"type": "null"}}}}]
defs["Category"] = obj({"id": ID, "artifact_ref": ID, "locator": ref("Locator"), "association_ref": nullable(ID), "native_label": TOKEN, "value": enum("pass", "warn", "fail", "unrecognized"), "native_token": TOKEN})
defs["RawBlock"] = obj({"artifact_ref": ID, "locator": ref("Locator"), "kind": enum("table", "header", "record", "unsupported_section", "error_report"), "native_name": TOKEN, "parse_status": enum("complete", "partial", "unsupported", "malformed"), "field_names": arr(TEXT)})
defs["SequenceRecord"] = obj({"id": ID, "artifact_ref": ID, "ordinal": COUNT, "title": TEXT, "sequence": TEXT, "quality_symbols": nullable(TEXT), "phred_values": nullable(arr({"type": "integer", "minimum": 0, "maximum": 93})), "locator": ref("Locator")})
defs["NativeTag"] = obj({"tag": TOKEN, "type": enum("A", "c", "C", "s", "S", "i", "I", "f", "Z", "H", "B", "unrecognized"), "native_value_token": TEXT, "value": nullable(NUMBER), "numeric_array": nullable(arr(nullable(NUMBER))), "array_subtype": nullable(enum("c", "C", "s", "S", "i", "I", "f"))})
defs["AlignmentRecord"] = obj({"id": ID, "artifact_ref": ID, "ordinal": COUNT, "qname": nullable(TEXT), "flag": {"type": "integer", "minimum": 0, "maximum": 65535}, "reference_token": nullable(TEXT), "position_0": nullable(COUNT), "mapq": {"type": "integer", "minimum": 0, "maximum": 255}, "native_cigar": TEXT, "resolved_cigar": nullable(TEXT), "mate_reference_token": nullable(TEXT), "mate_position_0": nullable(COUNT), "template_length": {"type": "integer"}, "sequence": nullable(TEXT), "phred_values": nullable(arr(nullable({"type": "integer", "minimum": 0, "maximum": 93}))), "tags": arr(ref("NativeTag")), "locator": ref("Locator")})
defs["NativeDocument"] = obj({"schema_version": {"const": "fastqutils_native_v1"}, "artifact": ref("Artifact"), "parse_scope": enum("complete", "partial", "unsupported", "malformed"), "cells": arr(ref("Cell")), "categories": arr(ref("Category")), "raw_blocks": arr(ref("RawBlock")), "sequence_records": arr(ref("SequenceRecord")), "alignment_records": arr(ref("AlignmentRecord")), "diagnostics": arr(ref("Diagnostic"))})
defs["Library"] = obj({"id": ID, "task_ref": ID, "input_pointer": {"type": "string", "pattern": "^/(paired_end_libs|single_end_libs|srr_libs)/[0-9]+$"}, "sample_ref": nullable(ID), "condition_ref": nullable(ID), "replicate_ref": nullable(ID), "platform": nullable(enum("infer", "illumina", "pacbio", "pacbio_hifi", "nanopore", "unrecognized")), "evidence_refs": arr(ID)})
defs["Stage"] = obj({"id": ID, "task_ref": ID, "recipe_ordinal": nullable(COUNT), "requested_token": nullable(TEXT), "mode": enum("INPUT", "TRIM", "PAIRED_FILTER", "FASTQC", "ALIGN", "SCRUB_HUMAN", "UNKNOWN"), "observed_state": enum("completed", "failed", "skipped", "unknown"), "input_population_refs": arr(ID), "output_population_refs": arr(ID), "evidence_refs": arr(ID)})
defs["Association"] = obj({"id": ID, "task_ref": ID, "library_ref": ID, "stage_ref": nullable(ID), "mate": enum("R1", "R2", "unpaired", "combined", "unknown"), "branch": enum("input", "current", "trimmed", "paired", "singleton", "clean", "aligned", "unconcordant", "unmapped", "report_only", "unknown"), "artifact_refs": arr(ID), "evidence_refs": arr(ID), "state": enum("established", "unresolved", "conflicting")})
defs["Population"] = obj({"id": ID, "association_ref": nullable(ID), "kind": enum("fastq_reads", "fastq_bases", "verified_read_pairs", "native_pair_validation", "alignment_records", "primary_alignment_reads", "native_qc_population", "native_report_population"), "scope": enum("complete", "partial", "unknown"), "representation": enum("emitted_bytes", "input_bytes", "native_report", "native_estimator"), "member_artifact_refs": arr(ID), "member_record_refs": arr(ID), "parent_population_refs": arr(ID), "disjoint_from_refs": arr(ID), "pair_key_rule": nullable(enum("exact_title", "first_token", "first_token_slash_mate", "fastq_pair_0_3")), "quality_encoding": enum("phred33", "phred64", "bam_phred", "unknown"), "encoding_evidence_refs": arr(ID)})
defs["Requirement"] = obj({"id": ID, "code": enum(*ISSUES), "affected_refs": arr(ID), "required_data": enum("complete_native_bytes", "full_fastqc_data", "earlier_hostile_report", "before_population", "after_population", "mate_identity", "pair_correspondence", "quality_encoding", "stage_input_association", "reference_identity", "reference_completeness", "native_version", "native_execution_evidence", "supported_parser", "requested_measurement"), "state": enum("missing", "unavailable", "unresolved", "incompatible"), "source_refs": arr(ID)})
defs["Metadata"] = obj({"task_ref": ID, "libraries": arr(ref("Library")), "stages": arr(ref("Stage")), "associations": arr(ref("Association")), "populations": arr(ref("Population")), "requirements": arr(ref("Requirement")), "diagnostics": arr(ref("Diagnostic"))})
defs["Sheet"] = obj({"schema_version": {"const": "fastqutils_sheet_v1"}, "task_ref": ID, "documents": arr(ref("NativeDocument")), "libraries": arr(ref("Library")), "stages": arr(ref("Stage")), "associations": arr(ref("Association")), "populations": arr(ref("Population")), "measurements": arr(ref("Cell")), "categories": arr(ref("Category")), "requirements": arr(ref("Requirement")), "diagnostics": arr(ref("Diagnostic"))})
defs["Comparison"] = obj({"id": ID, "before_population_ref": ID, "after_population_ref": ID, "before_measurement_ref": ID, "after_measurement_ref": ID, "kind": enum("read_retention", "base_retention", "pair_retention", "native_report_retention", "report_count_consistency")})
defs["CalculatorParameters"] = obj({"version": {"const": "fastqutils_calculators_v1"}, "composition_populations": arr(ID), "quality_populations": arr(ID), "quality_thresholds": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 93}, "uniqueItems": True}, "comparisons": arr(ref("Comparison")), "mapping_populations": arr(ID), "mapping_input_pairs": arr(obj({"mapping_population_ref": ID, "input_population_ref": ID}))})
defs["Component"] = obj({"id": ID, "metric": enum(*COMPONENT_METRICS), "state": enum(*STATES), "value": nullable(NUMBER), "unit": enum(*UNITS), "method": enum("composition_v1", "quality_phred_v1", "retention_v1", "mapping_v1", "report_consistency_v1"), "population_refs": arr(ID), "operand_measurement_refs": arr(ID), "numerator": nullable(NUMBER), "denominator": nullable(NUMBER), "threshold": nullable(NUMBER), "meaning": enum("derived_descriptive", "phred_model_prediction", "native_report_derived"), "uncertainty": enum("not_estimated", "phred_model_only", "native_reporting_precision"), "parameter_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "diagnostic_codes": arr(enum(*ISSUES))})
defs["Component"]["allOf"] = defs["Cell"]["allOf"]
defs["Components"] = obj({"schema_version": {"const": "fastqutils_components_v1"}, "sheet_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "parameters": ref("CalculatorParameters"), "components": arr(ref("Component")), "requirements": arr(ref("Requirement")), "diagnostics": arr(ref("Diagnostic"))})
defs["RequestedForm"] = obj({"version": {"const": "fastqutils_projection_v1"}, "fields": arr(obj({"field": ID, "family": enum("measurement", "component", "category", "population", "association", "requirements", "request_status"), "record_refs": arr(ID), "metric": nullable(enum(*(METRICS + COMPONENT_METRICS)))}))})
defs["ProviderParameters"] = obj({"version": {"const": "fastqutils_provider_v1"},
    "artifact_bindings": arr(obj({"content_ref": ID, "format": enum(*FORMATS), "producer_version": nullable(TOKEN)})),
    "metadata_source_refs": arr(ID), "calculator_parameters": ref("CalculatorParameters")})
defs["FactSelection"] = obj({"kind": enum("measurement", "component", "category", "population", "association", "requirements", "request_status"), "record_ref": nullable(ID), "metric": nullable(enum(*(METRICS + COMPONENT_METRICS))), "target_field": nullable(ID)})
defs["MeasurementFact"] = obj({"availability": enum("available", "partial", "unavailable", "invalid", "incompatible"),
    "measurement_ref": ID, "quantity": enum(*METRICS), "state": enum(*STATES), "value": nullable(NUMBER),
    "unit": enum(*UNITS), "meaning": defs["Cell"]["properties"]["meaning"], "population_ref": nullable(ID),
    "source_refs": arr(ID), "requirement_refs": arr(ID), "diagnostic_codes": arr(enum(*ISSUES))})
defs["ComponentFact"] = obj({"availability": enum("available", "partial", "unavailable", "invalid", "incompatible"),
    "component_ref": ID, "quantity": enum(*COMPONENT_METRICS), "state": enum(*STATES), "value": nullable(NUMBER),
    "unit": enum(*UNITS), "method": defs["Component"]["properties"]["method"], "population_refs": arr(ID),
    "operand_measurement_refs": arr(ID), "numerator": nullable(NUMBER), "denominator": nullable(NUMBER),
    "threshold": nullable(NUMBER), "meaning": defs["Component"]["properties"]["meaning"],
    "requirement_refs": arr(ID), "diagnostic_codes": arr(enum(*ISSUES))})
defs["CategoryFact"] = obj({"availability": enum("available", "unavailable", "invalid"), "category_ref": ID,
    "native_label_ref": ID, "value": enum("pass", "warn", "fail", "unrecognized"), "association_ref": nullable(ID), "source_refs": arr(ID)})
defs["PopulationFact"] = obj({"availability": enum("available", "unavailable", "invalid", "incompatible"),
    "population_ref": ID, "kind": defs["Population"]["properties"]["kind"], "scope": enum("complete", "partial", "unknown"),
    "representation": defs["Population"]["properties"]["representation"], "association_ref": nullable(ID), "artifact_refs": arr(ID), "parent_population_refs": arr(ID), "requirement_refs": arr(ID)})
defs["AssociationFact"] = obj({"availability": enum("available", "unavailable", "invalid", "incompatible"),
    "association_ref": ID, "library_ref": ID, "stage_ref": nullable(ID), "mate": defs["Association"]["properties"]["mate"],
    "branch": defs["Association"]["properties"]["branch"], "artifact_refs": arr(ID), "requirement_refs": arr(ID)})
defs["RequirementsFact"] = obj({"availability": {"const": "available"}, "requirements": arr(ref("Requirement"))})
defs["RequestStatusFact"] = obj({"availability": {"const": "available"}, "field": ID,
    "state": enum("available", "partial", "unavailable", "invalid", "incompatible"), "requirement_refs": arr(ID)})
schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:gene-annotation:fastqutils-contract:193:001", "$defs": defs}
(ROOT / "SCHEMAS_001.json").write_text(json.dumps(schema, indent=2, allow_nan=False) + "\n")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def locator(field):
    return {"member": None, "block": "synthetic_controlled_population", "block_ordinal": 0,
            "row_ordinal": None, "field": field, "byte_start": None, "byte_end": None}


def cell(name, metric, value, unit, population, axis=None):
    return {"id": name, "artifact_ref": "artifact_fixture", "locator": locator(metric), "metric": metric,
            "axis": axis or {"kind": "none", "label": None, "lower": None, "upper": None},
            "population_ref": population, "association_ref": None, "state": "available", "value": value,
            "native_token": str(value), "unit": unit, "meaning": "observed_count",
            "precision": "exact_for_retained_population", "diagnostic_codes": ["synthetic_identity"]}


fixture = {"identity": "handcrafted_synthetic_not_service_output", "population": {
    "before_pairs": 4, "after_pairs": 3, "before_reads": 8, "after_reads": 6,
    "before_bases": 160, "after_bases": 108, "quality_histogram": {"20": 20, "30": 20}}}
fixture_raw = canonical(fixture)
(ROOT / "synthetic/numerical_population.json").write_bytes(fixture_raw)
artifact = {"id": "artifact_fixture", "source_ref": "source_synthetic_fixture", "content_ref": "content_synthetic_fixture",
    "task_ref": "task_synthetic", "sha256": hashlib.sha256(fixture_raw).hexdigest(), "byte_count": len(fixture_raw),
    "native_name": "numerical_population.json", "declared_format": "native_json", "actual_format": "native_json",
    "compression": "none", "transfer_scope": "complete", "producer_name": "controlled_example", "producer_version": "1",
    "identity": "handcrafted_synthetic"}
measurements = [cell("m_before_reads", "fastq_read_count", 8, "reads", "p_before_reads"),
    cell("m_after_reads", "fastq_read_count", 6, "reads", "p_after_reads"),
    cell("m_before_bases", "fastq_base_count", 160, "bases", "p_before_bases"),
    cell("m_after_bases", "fastq_base_count", 108, "bases", "p_after_bases"),
    cell("m_before_pairs", "verified_pair_count", 4, "pairs", "p_before_pairs"),
    cell("m_after_pairs", "verified_pair_count", 3, "pairs", "p_after_pairs")]
for q in (20, 30):
    measurements.append(cell(f"m_q{q}", "phred_histogram_count", 20, "bases", "p_quality",
        {"kind": "quality_score", "label": str(q), "lower": q, "upper": q}))
populations = []
for name in ("before_reads", "after_reads", "before_bases", "after_bases", "before_pairs", "after_pairs", "quality"):
    kind = "verified_read_pairs" if name.endswith("pairs") else ("fastq_reads" if name.endswith("reads") else "fastq_bases")
    populations.append({"id": "p_" + name, "association_ref": None, "kind": kind, "scope": "complete",
        "representation": "input_bytes" if name.startswith("before") else "emitted_bytes",
        "member_artifact_refs": ["artifact_fixture"], "member_record_refs": [], "parent_population_refs": [],
        "disjoint_from_refs": [], "pair_key_rule": "first_token_slash_mate" if name.endswith("pairs") else None,
        "quality_encoding": "phred33" if name == "quality" else "unknown", "encoding_evidence_refs": ["source_synthetic_fixture"] if name == "quality" else []})
document = {"schema_version": "fastqutils_native_v1", "artifact": artifact, "parse_scope": "complete",
    "cells": measurements, "categories": [], "raw_blocks": [], "sequence_records": [], "alignment_records": [], "diagnostics": []}
sheet = {"schema_version": "fastqutils_sheet_v1", "task_ref": "task_synthetic", "documents": [document],
    "libraries": [], "stages": [], "associations": [], "populations": populations, "measurements": measurements,
    "categories": [], "requirements": [], "diagnostics": []}
params = {"version": "fastqutils_calculators_v1", "composition_populations": [], "quality_populations": ["p_quality"],
    "quality_thresholds": [20, 30], "comparisons": [], "mapping_populations": [], "mapping_input_pairs": []}
for unit in ("reads", "bases", "pairs"):
    params["comparisons"].append({"id": "compare_" + unit, "before_population_ref": "p_before_" + unit,
        "after_population_ref": "p_after_" + unit, "before_measurement_ref": "m_before_" + unit,
        "after_measurement_ref": "m_after_" + unit, "kind": {"reads": "read_retention", "bases": "base_retention", "pairs": "pair_retention"}[unit]})

# These are hand-worked oracle components, not outputs of a production calculator.
components = []
for unit, numerator, denominator in (("reads", 6, 8), ("bases", 108, 160), ("pairs", 3, 4)):
    components.append({"id": "c_retention_" + unit, "metric": {"reads": "read_retention_fraction", "bases": "base_retention_fraction", "pairs": "pair_retention_fraction"}[unit],
        "state": "available", "value": numerator / denominator, "unit": "fraction", "method": "retention_v1",
        "population_refs": ["p_before_" + unit, "p_after_" + unit],
        "operand_measurement_refs": ["m_before_" + unit, "m_after_" + unit], "numerator": numerator,
        "denominator": denominator, "threshold": None, "meaning": "derived_descriptive", "uncertainty": "not_estimated",
        "parameter_sha256": sha(params), "diagnostic_codes": ["synthetic_identity"]})
for name, metric, value, numerator, denominator, threshold in (
    ("q30", "q_ge_threshold_fraction", 0.5, 20, 40, 30),
    ("meanq", "mean_phred", 25, 1000, 40, None),
    ("errors", "phred_implied_expected_errors", 0.22, None, None, None),
    ("error_fraction", "phred_implied_error_fraction", 0.0055, 0.22, 40, None)):
    predicted = metric.startswith("phred_implied")
    components.append({"id": "c_" + name, "metric": metric, "state": "available", "value": value,
        "unit": "phred" if name == "meanq" else ("expected_errors" if name == "errors" else "fraction"),
        "method": "quality_phred_v1", "population_refs": ["p_quality"], "operand_measurement_refs": ["m_q20", "m_q30"],
        "numerator": numerator, "denominator": denominator, "threshold": threshold,
        "meaning": "phred_model_prediction" if predicted else "derived_descriptive",
        "uncertainty": "phred_model_only" if predicted else "not_estimated", "parameter_sha256": sha(params),
        "diagnostic_codes": ["synthetic_identity"]})
examples = {"identity": "handcrafted_numerical_oracle_not_service_output", "shape_only_sheet": sheet,
    "oracle_components": {"schema_version": "fastqutils_components_v1", "sheet_sha256": sha(sheet), "parameters": params,
        "components": components, "requirements": [], "diagnostics": []},
    "semantic_qualification": "Shape-valid numerical oracle only: counts and verified pairs are stipulated controlled inputs, not a custody/lineage integration fixture. A production provider must require established lineage before issuing retention facts.",
    "zero_case": {"native_hostile_input": 0, "native_hostile_output": 0, "native_hostile_removed_proportion": 0.0,
        "derived_retention": None, "state": "undefined", "code": "zero_denominator"},
    "nonfinite_case": {"native_fastqc_token": "NaN", "canonical_value": None, "state": "malformed", "code": "nonfinite_native"}}
(ROOT / "NUMERICAL_EXAMPLES_001.json").write_text(json.dumps(examples, indent=2, allow_nan=False) + "\n")
def expand(node):
    if isinstance(node, dict):
        if "$ref" in node:
            return expand(defs[node["$ref"].split("/")[-1]])
        return {k: expand(v) for k, v in node.items()}
    if isinstance(node, list):
        return [expand(v) for v in node]
    return node

selections = {
    "input_reads": {"kind": "measurement", "record_ref": "m_before_reads", "metric": "fastq_read_count", "target_field": None},
    "read_retention": {"kind": "component", "record_ref": "c_retention_reads", "metric": "read_retention_fraction", "target_field": None},
    "retention_status": {"kind": "request_status", "record_ref": None, "metric": None, "target_field": "read_retention"},
}
fact_type = {"measurement": "MeasurementFact", "component": "ComponentFact", "request_status": "RequestStatusFact"}
request = obj({name: {**expand(defs[fact_type[selection["kind"]]]), "x-bvbrc-fastqutils": selection}
    for name, selection in selections.items()})
(ROOT / "REQUEST_EXAMPLE_001.json").write_text(json.dumps({"identity": "synthetic_request_builder_example_not_production_selector",
    "selections": selections, "requested_schema": request}, indent=2, allow_nan=False) + "\n")
print(json.dumps({"schema_definitions": len(defs), "native_metrics": len(METRICS), "component_metrics": len(COMPONENT_METRICS), "oracle_components": len(components)}))
