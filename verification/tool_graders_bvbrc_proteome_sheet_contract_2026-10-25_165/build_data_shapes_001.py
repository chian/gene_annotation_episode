"""Build a review-only data-shape proposal. No production implementation.

This script writes only in its own verification directory. Formula definitions
belong to CONTRACT_PROPOSAL_001.md, as ordinary proposed Python functions.
"""
from copy import deepcopy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
NATIVE = json.loads((ROOT / "gene_annotation_episode/bvbrc_proteome_native_schemas.json").read_text())
D = deepcopy(NATIVE["$defs"])

def ref(name): return {"$ref": "#/$defs/" + name}
def obj(fields): return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}
def arr(item): return {"type": "array", "items": item}
def nullable(item): return {"anyOf": [item, {"type": "null"}]}
def enum(*values): return {"enum": list(values)}
def const(value): return {"const": value}
S = {"type": "string", "minLength": 1}
TEXT = {"type": "string"}
N = {"type": "integer", "minimum": 0}
POS = {"type": "integer", "minimum": 1}
NUM = {"type": "number"}
BOOL = {"type": "boolean"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
MD5 = {"type": "string", "pattern": "^[0-9a-f]{32}$"}
TRI = enum("yes", "no", "unknown")
PTR = {"type": "string", "pattern": "^(|/.*)$"}
F = ref("SourceField")
FS = arr(F)
REASONS = [
    "source_bytes_incomplete", "source_object_incomplete", "content_binding_mismatch",
    "encoding_invalid", "format_incompatible", "json_invalid", "duplicate_json_member",
    "fasta_header_invalid", "fasta_record_incomplete", "fasta_sequence_invalid", "fasta_empty_sequence",
    "input_empty", "input_arrays_unavailable", "input_reference_index_invalid", "parameter_source_conflict",
    "input_order_is_not_execution_proof", "exact_executed_input_missing", "input_membership_incomplete",
    "input_membership_unknown", "inventory_record_invalid", "input_binding_conflict", "staging_collision",
    "duplicate_identifier", "cross_input_identifier_collision", "identifier_mapping_missing",
    "identifier_mapping_conflict", "row_join_missing", "row_join_ambiguous", "row_join_conflict",
    "sequence_digest_conflict", "sequence_length_conflict", "metadata_record_invalid", "metadata_join_missing",
    "metadata_join_ambiguous", "metadata_join_conflict", "metadata_population_incomplete",
    "metadata_population_unknown", "coordinate_convention_unknown", "later_snapshot_not_original_input",
    "unknown_metadata_fields_retained", "native_invalid_cell", "native_missing_cell", "native_table_layout_uncertain",
    "native_identifier_unavailable", "native_category_invalid", "track_missing_from_projection",
    "track_materialization_unknown", "projection_incomplete", "reference_membership_unresolved",
    "representation_correspondence_missing", "representation_conflict", "alternate_representation_not_independent",
    "duplicate_native_representation", "reported_rows_not_input_population", "legacy_first_hsp_only",
    "legacy_rounded_fraction", "legacy_subject_endpoint_difference", "legacy_zero_fallback_possible",
    "native_category_not_orthology_probability", "observed_subset_not_total", "no_eligible_values",
    "postfilter_cannot_recover_filtered_associations", "native_min_positives_not_enforced_in_projection", "native_zero_default_divergence",
    "denominator_unavailable", "denominator_zero", "selection_unknown", "published_absence_not_biological_absence",
    "sequence_equivalence_not_feature_identity", "dependence_not_independence", "full_reports_not_retained",
    "directional_report_missing", "directional_report_partial", "report_operand_unbound", "report_query_missing",
    "report_counts_conflict", "report_geometry_conflict", "report_mapping_conflict", "native_hit_limit_censoring",
    "producer_exit_unknown", "producer_failed", "producer_format_unverified", "calculation_parameters_invalid",
    "sheet_relationship_invalid", "supplied_contract_invalid",
]
D["PReason"] = enum(*REASONS)
D["PDiagnostic"] = obj({"code": ref("PReason"), "severity": enum("error", "qualification"),
    "path": PTR, "scope": ref("Scope"), "source_fields": FS})
D["PRequirement"] = obj({"code": ref("PReason"), "scope": ref("Scope"),
    "required_input": enum("complete_bytes", "original_parameters", "exact_executed_fasta", "execution_input_witness",
        "complete_membership", "occurrence_mapping", "feature_metadata", "genome_metadata", "feature_sequence",
        "coordinate_convention", "representation_correspondence", "directional_report", "producer_execution_facts",
        "valid_parameters", "valid_saved_sheet"), "source_fields": FS})
DIAGS = arr(ref("PDiagnostic"))
REQS = arr(ref("PRequirement"))

def cell(name, value_schema):
    node = obj({"state": enum("value", "missing_input", "not_retained", "truncated", "ambiguous", "conflicting",
        "invalid", "not_applicable", "zero_denominator"), "value": nullable(value_schema),
        "reason_codes": arr(ref("PReason")), "source_fields": FS})
    node["allOf"] = [{"if": {"properties": {"state": {"const": "value"}}},
        "then": {"properties": {"value": value_schema}}, "else": {"properties": {"value": {"type": "null"}}}}]
    D[name] = node

cell("CountCell", N)
cell("ScalarCell", NUM)
cell("FractionCell", {"type": "number", "minimum": 0, "maximum": 1})
cell("PercentageCell", {"type": "number", "minimum": 0, "maximum": 100})
D["Ratio"] = obj({"numerator": ref("CountCell"), "denominator": ref("CountCell"), "fraction": ref("FractionCell")})
D["ProteinRef"] = obj({"inventory_key": S, "record_ordinal": N})
PROTEIN = ref("ProteinRef")
D["MetadataRef"] = obj({"snapshot_key": S, "row_ordinal": N})
META = ref("MetadataRef")
D["DuplicateIdentifierGroup"] = obj({"identifier": S, "record_ordinals": arr(N)})
D["SequenceGroup"] = obj({"molecule": const("aa"), "normalization": const("ascii_whitespace_removed_uppercase_no_symbol_substitution_v1"),
    "sequence_sha256": SHA, "sequence_symbol_count": N, "members": arr(PROTEIN)})
D["FastaRecord"] = obj({"record_ordinal": N, "byte_start": N, "byte_end_exclusive": N,
    "header": TEXT, "identifier": nullable(S), "description": nullable(TEXT),
    "sequence": nullable(TEXT), "sequence_symbol_count": nullable(N), "sequence_sha256": nullable(SHA),
    "sequence_md5": nullable(MD5), "record_complete": BOOL, "valid_sequence": BOOL,
    "source_field": F, "diagnostics": DIAGS})
D["ProteinInventory"] = obj({"version": const("bvbrc_proteome_inventory_proposal_v1"), "inventory_key": S,
    "format": const("protein_fasta_utf8_v1"), "source": ref("NativeSource"), "molecule": const("aa"),
    "normalization": const("ascii_whitespace_removed_uppercase_no_symbol_substitution_v1"),
    "records": arr(ref("FastaRecord")), "observed_header_count": N, "complete_record_count": N,
    "valid_complete_record_count": N, "duplicate_identifier_groups": arr(ref("DuplicateIdentifierGroup")),
    "sequence_groups": arr(ref("SequenceGroup")), "diagnostics": DIAGS})
D["PopulationDescriptor"] = obj({"origin": enum("execution_time_snapshot", "supplied_snapshot", "later_database_snapshot", "unknown"),
    "query_source": nullable(F), "selected_fields": arr(S), "offset": nullable(N), "requested_limit": nullable(N),
    "reported_total_count": nullable(ref("NativeNumber")), "population_complete": TRI,
    "completeness_evidence": FS})
D["CoordinateConvention"] = obj({"value": enum("one_based_closed", "zero_based_half_open", "unknown"), "source_fields": FS})
feature = {"row_ordinal": N, "source_field": F, "valid": BOOL,
    **{name: ref("NativeString") for name in ("feature_id", "patric_id", "genome_id", "accession", "annotation", "feature_type",
        "aa_sequence_md5", "product", "refseq_locus_tag", "gene", "plfam_id", "pgfam_id", "strand")},
    **{name: ref("NativeNumber") for name in ("start", "end", "aa_length")}, "diagnostics": DIAGS}
D["FeatureRecord"] = obj(feature)
D["GenomeRecord"] = obj({"row_ordinal": N, "source_field": F, "valid": BOOL,
    "genome_id": ref("NativeString"), "genome_name": ref("NativeString"), "taxon_id": ref("NativeNumber"),
    "diagnostics": DIAGS})
D["FeatureSequenceRecord"] = obj({"row_ordinal": N, "source_field": F, "valid": BOOL,
    "md5": ref("NativeString"), "sequence": ref("NativeString"), "molecule": const("aa"),
    "sequence_symbol_count": nullable(N), "computed_md5": nullable(MD5), "computed_sha256": nullable(SHA), "diagnostics": DIAGS})
for label, record, fmt in (("FeatureSnapshot", "FeatureRecord", "bvbrc_genome_feature_json_array_v1"),
        ("GenomeSnapshot", "GenomeRecord", "bvbrc_genome_json_array_v1"),
        ("FeatureSequenceSnapshot", "FeatureSequenceRecord", "bvbrc_feature_sequence_json_array_v1")):
    fields = {"version": const("bvbrc_proteome_metadata_proposal_v1"), "snapshot_key": S, "format": const(fmt),
        "source": ref("NativeSource"), "population": ref("PopulationDescriptor"), "records": arr(ref(record)),
        "unsupported_field_paths": arr(PTR), "diagnostics": DIAGS}
    if label == "FeatureSnapshot": fields["coordinate_convention"] = ref("CoordinateConvention")
    D[label] = obj(fields)

D["ParameterSource"] = obj({"kind": enum("submitted", "effective"), "source_field": F})
D["RecordedParameterNumber"] = obj({"value": nullable(NUM),
    "presence": enum("value", "omitted", "explicit_null", "invalid"), "source_field": F})
D["RecordedParameterNumber"]["allOf"] = [{"if": {"properties": {"presence": {"const": "value"}}},
    "then": {"properties": {"value": NUM}}, "else": {"properties": {"value": {"type": "null"}}}}]
D["RunParameterSnapshot"] = obj({"kind": enum("submitted", "effective"), "source_field": F,
    **{name: ref("RecordedParameterNumber") for name in ("min_ident", "min_seq_cov", "min_positives", "max_e_val")}})
D["OriginalInputEntry"] = obj({"input_key": S, "parameter_pointer": PTR,
    "original_index": POS, "kind": enum("genome_id", "user_genome", "user_feature_group"),
    "value": S, "expected_track_key": S, "source_field": F})
D["InputIndex"] = obj({"version": const("bvbrc_proteome_input_index_proposal_v1"),
    "parameter_source": ref("ParameterSource"), "reference_original_index": POS,
    "inputs": arr(ref("OriginalInputEntry")), "source_contract": ref("SourceContract"),
    "run_parameter_snapshots": arr(ref("RunParameterSnapshot")), "diagnostics": DIAGS})
D["ExecutionInputLink"] = obj({"input_key": S, "inventory_key": S,
    "relation": enum("exact_executed_fasta", "original_supplied_fasta", "later_snapshot", "unknown"),
    "executed_fasta": nullable(ref("ContentBinding")), "membership_complete": TRI,
    "staged_path": nullable(S), "witness_source_fields": FS})
D["NativeOperandSelector"] = obj({"source_ref": S, "sha256": SHA, "kind": enum("reference", "association_subject"),
    "reference_row_ordinal": N, "track_key": S, "association_key": nullable(S)})
D["NativeProteinLink"] = obj({"native": ref("NativeOperandSelector"), "protein": PROTEIN,
    "basis": enum("unique_exact_identifier", "producer_occurrence_mapping"),
    "native_identifier": S, "mapping_source_fields": FS})
D["ProteinMetadataLink"] = obj({"protein": PROTEIN, "feature": META,
    "genome": nullable(META), "feature_sequence": nullable(META),
    "basis": enum("exact_feature_identifier", "producer_occurrence_mapping"), "mapping_source_fields": FS})
D["OperandJoin"] = obj({"native": ref("NativeOperandSelector"),
    "state": enum("joined", "not_supplied", "unmatched", "ambiguous", "conflicting"),
    "protein": nullable(PROTEIN), "candidates": arr(PROTEIN), "accepted_link_indices": arr(N), "diagnostics": DIAGS})
D["TrackInputBinding"] = obj({"track_key": S, "input_key": S, "inventory_key": nullable(S),
    "execution_relation": enum("exact_executed_fasta", "original_supplied_fasta", "later_snapshot", "unknown"),
    "input_record_count": ref("CountCell"), "membership_complete": TRI,
    "identifier_collisions": arr(S), "diagnostics": DIAGS})
D["MetadataJoin"] = obj({"link_index": N, "state": enum("joined", "unmatched", "ambiguous", "conflicting"),
    "protein": PROTEIN, "feature": nullable(META), "genome": nullable(META),
    "feature_sequence": nullable(META), "diagnostics": DIAGS})
D["NativeJoins"] = obj({"version": const("bvbrc_proteome_joins_proposal_v1"), "primary_source_ref": S,
    "execution_links": arr(ref("ExecutionInputLink")), "requested_native_links": arr(ref("NativeProteinLink")),
    "requested_metadata_links": arr(ref("ProteinMetadataLink")), "track_bindings": arr(ref("TrackInputBinding")),
    "reference_joins": arr(ref("OperandJoin")), "subject_joins": arr(ref("OperandJoin")),
    "metadata_joins": arr(ref("MetadataJoin")), "sequence_groups": arr(ref("SequenceGroup")), "diagnostics": DIAGS})
D["ReferenceRowPair"] = obj({"left_row_ordinal": N, "right_row_ordinal": N})
D["AssociationRowPair"] = obj({"left_association_key": S, "right_association_key": S})
D["RepresentationLink"] = obj({"left_source_ref": S, "right_source_ref": S,
    "relation": enum("alternate_full_projection", "alternate_partial_projection"),
    "reference_pairs": arr(ref("ReferenceRowPair")), "association_pairs": arr(ref("AssociationRowPair")),
    "source_fields": FS})
D["RepresentationComparison"] = obj({"link": ref("RepresentationLink"),
    "state": enum("equal_observed_cells", "conflicting", "incomplete_comparison", "unbound"),
    "conflict_source_fields": FS, "diagnostics": DIAGS})

D["SheetTrack"] = obj({"track_key": S, "comparison_ordinal": nullable(POS), "original_input_key": nullable(S),
    "native_materialization": enum("reference_rows", "table_field_block", "published_association", "unknown", "not_in_projection"),
    "native_source_fields": FS, "inventory_key": nullable(S), "input_record_count": ref("CountCell"),
    "complete_reference_row_membership": TRI, "complete_published_association_membership": TRI, "diagnostics": DIAGS})
D["SheetReference"] = obj({"reference_row_ordinal": N, "reference_row_key": S,
    "protein": nullable(PROTEIN), "join_state": enum("joined", "not_supplied", "unmatched", "ambiguous", "conflicting"),
    "native_aa_length": ref("NativeNumber"), "inventory_sequence_symbol_count": ref("CountCell"),
    "native_start": ref("NativeNumber"), "native_end": ref("NativeNumber"), "native_strand": ref("NativeString"),
    "coordinate_kind": enum("artificial_layout", "genomic_metadata", "unknown"),
    "metadata_links": arr(N), "diagnostics": DIAGS})
D["SheetAssociation"] = obj({"association_key": S, "reference_row_ordinal": N, "track_key": S,
    "reference_protein": nullable(PROTEIN), "subject_protein": nullable(PROTEIN),
    "reference_join_state": enum("joined", "not_supplied", "unmatched", "ambiguous", "conflicting"),
    "subject_join_state": enum("joined", "not_supplied", "unmatched", "ambiguous", "conflicting"),
    "native_hit_category": ref("NativeString"), "native_subject_length_aa": ref("NativeNumber"),
    "inventory_subject_sequence_symbol_count": ref("CountCell"),
    "native_first_hsp_alignment_identity_fraction": ref("NativeNumber"),
    "native_subject_endpoint_difference_fraction": ref("NativeNumber"),
    "layout_state": enum("source_field_located", "uncertain_table_layout"),
    "native_subject_identifier_present": BOOL, "metadata_links": arr(N), "diagnostics": DIAGS})

# Future retained-report data. These are attachment shapes, not an installed
# native format reader, an invented report, or a claim of full scientific output.
D["ReportExecution"] = obj({"argv": nullable(arr(TEXT)), "program": const("blastp"),
    "executable_version": ref("NativeString"), "exit_code": ref("NativeNumber"),
    "requested_alignment_limit": ref("NativeNumber"), "requested_description_limit": ref("NativeNumber"),
    "stdout": ref("NativeSource"), "stderr": nullable(ref("NativeSource")), "source_fields": FS})
D["RetainedHSP"] = obj({"hsp_ordinal": N, "source_field": F,
    **{name: ref("NativeNumber") for name in ("bit_score", "raw_score", "evalue", "alignment_columns", "identical_columns",
        "positive_columns", "gap_columns", "query_from", "query_to", "subject_from", "subject_to")},
    "query_aligned": ref("NativeString"), "subject_aligned": ref("NativeString"),
    "coordinate_unit": const("aa"), "coordinate_convention": const("one_based_closed"), "diagnostics": DIAGS})
D["RetainedSubject"] = obj({"hit_ordinal": N, "source_field": F, "identifier": ref("NativeString"),
    "description": ref("NativeString"), "length_aa": ref("NativeNumber"),
    "hsp_array_state": enum("present", "missing", "malformed"), "hsps": arr(ref("RetainedHSP")), "diagnostics": DIAGS})
D["RetainedQuery"] = obj({"query_ordinal": N, "source_field": F, "identifier": ref("NativeString"),
    "description": ref("NativeString"), "length_aa": ref("NativeNumber"),
    "query_state": enum("complete", "partial", "malformed"),
    "reported_outcome": enum("hits_reported", "explicit_no_hits", "not_established"),
    "outcome_source_fields": FS, "subjects": arr(ref("RetainedSubject")), "diagnostics": DIAGS})
D["DirectionalReport"] = obj({"report_key": S, "source": ref("NativeSource"),
    "native_format": const("legacy_blast_pairwise_text"), "native_format_version": S,
    "direction": enum("reference_to_comparison", "comparison_to_reference"), "comparison_track_key": S,
    "query_inventory_key": S, "subject_inventory_key": S, "execution": ref("ReportExecution"),
    "all_emitted_queries_retained": TRI, "queries": arr(ref("RetainedQuery")),
    "unsupported_source_fields": FS, "diagnostics": DIAGS})
D["ReportOperandLink"] = obj({"report_key": S, "query_ordinal": N, "hit_ordinal": nullable(N),
    "protein": PROTEIN, "basis": enum("unique_exact_identifier", "producer_occurrence_mapping"),
    "mapping_source_fields": FS})
D["DirectionalScope"] = obj({"comparison_track_key": S, "direction": enum("reference_to_comparison", "comparison_to_reference")})
D["DirectionalAttachment"] = obj({"version": const("bvbrc_proteome_directional_attachment_proposal_v1"),
    "state": enum("unavailable", "partial", "complete_emitted_reports"), "expected_scopes": arr(ref("DirectionalScope")),
    "reports": arr(ref("DirectionalReport")), "operand_links": arr(ref("ReportOperandLink")),
    "requirements": REQS, "diagnostics": DIAGS})
D["NativeSheet"] = obj({"version": const("bvbrc_proteome_native_sheet_proposal_v1"),
    "scientific_mode": const("proteome_comparison"), "primary_source_ref": S,
    "native_results": arr(ref("NativeProjectionResult")), "input_index": nullable(ref("InputIndex")),
    "inventories": arr(ref("ProteinInventory")), "feature_snapshots": arr(ref("FeatureSnapshot")),
    "genome_snapshots": arr(ref("GenomeSnapshot")), "sequence_snapshots": arr(ref("FeatureSequenceSnapshot")),
    "joins": nullable(ref("NativeJoins")), "representation_comparisons": arr(ref("RepresentationComparison")),
    "tracks": arr(ref("SheetTrack")), "reference_rows": arr(ref("SheetReference")),
    "association_rows": arr(ref("SheetAssociation")), "directional_attachment": nullable(ref("DirectionalAttachment")),
    "requirements": REQS, "diagnostics": DIAGS})
D["NativeCalculationParameters"] = obj({"version": const("bvbrc_proteome_native_parameters_proposal_v1"),
    "track_keys": arr(S), "minimum_identity_fraction": nullable({"type": "number", "minimum": 0, "maximum": 1}),
    "minimum_subject_endpoint_difference_fraction": nullable({"type": "number", "minimum": 0, "maximum": 1}),
    "allowed_hit_categories": nullable(arr(enum("bi (<->)", "uni (->)")))})
D["AssociationComponents"] = obj({"association_key": S, "track_key": S,
    "first_hsp_alignment_identity_percent": ref("PercentageCell"),
    "subject_endpoint_difference_percent": ref("PercentageCell"),
    "selection": enum("pass", "fail", "unknown"), "failed_conditions": arr(enum("identity", "subject_endpoint_difference", "category")),
    "unknown_conditions": arr(enum("identity", "subject_endpoint_difference", "category")), "diagnostics": DIAGS})
D["NativeFractionSummary"] = obj({"used_association_keys": arr(S), "value_count": ref("CountCell"),
    "omitted_count": ref("CountCell"), "null_count": ref("CountCell"), "blank_count": ref("CountCell"),
    "invalid_count": ref("CountCell"), "layout_uncertain_count": ref("CountCell"),
    "sum": ref("ScalarCell"), "mean": ref("FractionCell"), "minimum": ref("FractionCell"), "maximum": ref("FractionCell"),
    "unit": const("fraction"), "native_rounding_quantum": const(0.001)})
D["SelectionCounts"] = obj({"pass": ref("CountCell"), "fail": ref("CountCell"), "unknown": ref("CountCell")})
D["NativeTrackComponents"] = obj({"track_key": S,
    "materialization": enum("table_field_block", "published_association", "unknown", "not_in_projection"),
    "source_scope": enum("complete_document", "complete_prefix_only", "partial_or_unknown_artifact"),
    **{name: ref("CountCell") for name in ("source_association_record_count", "published_association_record_count", "native_bi_count",
        "native_uni_count", "native_other_category_count", "native_missing_category_count", "observed_bound_reference_count",
        "observed_bound_subject_count", "unresolved_reference_association_count", "unresolved_subject_association_count",
        "reference_input_record_count", "comparison_input_record_count", "no_published_reference_count",
        "multiple_reference_subject_count", "excess_bound_pair_count", "observed_selected_reference_count",
        "demonstrated_subject_sequence_group_count", "unresolved_subject_sequence_count")},
    "first_hsp_identity_summary": ref("NativeFractionSummary"),
    "subject_endpoint_difference_summary": ref("NativeFractionSummary"),
    "observed_reference_fraction": ref("Ratio"), "complete_published_reference_fraction": ref("Ratio"),
    "selection_counts": ref("SelectionCounts"), "observed_selected_reference_fraction": ref("Ratio"),
    "complete_selected_reference_fraction": ref("Ratio"), "qualifications": arr(ref("PReason"))})
D["NativeComponents"] = obj({"version": const("bvbrc_proteome_native_components_proposal_v1"),
    "formula_version": const("native_descriptive_components_v1"), "sheet_sha256": SHA,
    "parameters": ref("NativeCalculationParameters"), "associations": arr(ref("AssociationComponents")),
    "tracks": arr(ref("NativeTrackComponents")),
    "used_component_families": const(["legacy_identity", "legacy_subject_endpoint_difference", "native_category",
        "explicit_occurrence_membership", "full_sequence_identity"]),
    "retained_unused_component_families": const(["feature_function_assignments", "feature_taxonomy", "feature_families",
        "genomic_or_layout_coordinates", "directional_hsps"]),
    "requirements": REQS, "diagnostics": DIAGS})

for name in ("ProteinInventory", "FeatureSnapshot", "GenomeSnapshot", "FeatureSequenceSnapshot", "InputIndex", "NativeJoins",
        "NativeSheet", "NativeComponents", "DirectionalAttachment"):
    shape = obj({"status": enum("ok", "partial", "invalid"), "value": nullable(ref(name)), "requirements": REQS, "diagnostics": DIAGS})
    shape["allOf"] = [{"if": {"properties": {"status": {"const": "invalid"}}},
        "then": {"properties": {"value": {"type": "null"}}}, "else": {"properties": {"value": ref(name)}}}]
    D[name + "Result"] = shape

DOCUMENT = {"$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:gene-annotation:genome-comparison:sheet-contract:proposal-001-165",
    "title": "GenomeComparison modular data-shape proposal 001; not an installed contract",
    "$comment": "Data shapes only. Formulas are ordinary proposed Python functions in CONTRACT_PROPOSAL_001.md. Native definitions are copied unchanged from accepted native schema c84fecffe0170b7c77948f411593a55ae63e902f976e8a42463a0053c1a1f01d. Finite-number and cross-record semantic validation is additionally required.",
    "$defs": D}
(HERE / "DATA_SHAPES_PROPOSAL_001.json").write_text(json.dumps(DOCUMENT, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"definitions": len(D), "native_definitions_unchanged": all(D[k] == v for k, v in NATIVE["$defs"].items())}))
