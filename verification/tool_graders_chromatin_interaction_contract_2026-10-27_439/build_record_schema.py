"""Build planning-only data definitions; no native reader or scientific calculator.

The emitted schema is the reviewable interface proposal. Production must not
import this verification script. Formula meanings remain in CONTRACT.md.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
D = {}
def ref(name): return {"$ref": "#/$defs/" + name}
def enum(*values): return {"enum": list(values)}
def const(value): return {"const": value}
def nullable(schema): return {"anyOf": [schema, {"type": "null"}]}
def arr(schema, minimum=0, unique=False):
    return {"type": "array", "items": schema, "minItems": minimum, **({"uniqueItems": True} if unique else {})}
def obj(fields, required=None):
    return {"type": "object", "properties": fields, "required": list(fields) if required is None else required,
            "additionalProperties": False}
def put(name, fields): D[name] = obj(fields); return ref(name)
S = {"type": "string", "minLength": 1}
KEY = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"}
TEXT = {"type": "string"}
N = {"type": "number", "minimum": -1.7976931348623157e308, "maximum": 1.7976931348623157e308}
I = {"type": "integer", "minimum": 0}
P = {"type": "integer", "minimum": 1}
B = {"type": "boolean"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
ABS = {"type": "string", "pattern": "^/[^\\\\\\u0000\\r\\n]+$"}
REL = {"type": "string", "pattern": "^[^/\\\\\\u0000\\r\\n][^\\\\\\u0000\\r\\n]*$"}
EX = enum("complete", "partial", "unavailable", "incompatible")
FORMAT = enum("cooler_hdf5_v3", "hic_binary_v9")
MODES = enum("cis_anchor_contact_enrichment", "cross_window_insulation_heuristic")
ROLES = enum("bins", "contacts", "weights", "cell_states", "dense_values")
STORAGE = enum("symmetric-upper", "square", "hic-symmetric")
RELATION = enum("consistent_assertions", "conflicting_assertions", "unknown")
STATES = enum("observed", "derived", "normalized", "missing", "not_measured", "failed", "truncated", "incompatible", "undefined")
CODES = "input_unavailable input_digest_mismatch unsupported_native_format unsupported_native_version malformed_native_header malformed_native_index native_chunk_unavailable native_output_partial native_value_nonfinite native_value_negative numerical_overflow duplicate_native_pixel invalid_coordinate population_boundary_not_bin_aligned population_unavailable external_native_dependency_unbound element_assignment_missing anchor_outside_element anchor_bin_unavailable reference_conflict incompatible_variable_bins incompatible_matrix_symmetry normalization_missing normalization_weight_invalid normalization_masked_bin same_bin_not_evaluated below_minimum_separation no_valid_distance_pairs zero_denominator incomplete_comparison_population incomplete_window no_full_windows zero_variance boundary_neighbor_unavailable native_dependency_unavailable native_nonzero_exit resource_limit original_attempt_mismatch artifact_digest_mismatch requested_field_unavailable".split()
REQUIREMENTS = "supplied_contact_file matching_file_identity complete_population explicit_element_assignment compatible_reference fixed_bin_grid selected_weight_vector positive_denominator complete_window original_native_outcome requested_selected_field supported_native_format valid_native_structure finite_nonnegative_contact_values finite_positive_weights bound_dependencies caller_resource_fit matching_original_attempt finite_numerical_result".split()
put("NativeFileIdentity", {"artifact_ref": {"type":"string", "pattern":"^artifact_[0-9a-f]{64}$"}, "sha256": SHA, "size_bytes": I, "format": S})
put("NativeFileDeclaration", {"relative_path": REL, "format": S, "state": enum("present", "absent"), "sha256": nullable(SHA), "size_bytes": nullable(I)})
D["NativeFileDeclaration"]["allOf"] = [{"if":{"properties":{"state":const("absent")}}, "then":{"properties":{"sha256":{"type":"null"},"size_bytes":{"type":"null"}}}, "else":{"properties":{"sha256":SHA,"size_bytes":I}}}]
put("NativeFileCapture", {"declared":ref("NativeFileDeclaration"), "observed":nullable(ref("NativeFileIdentity")), "outcome":enum("verified","declared_absent","digest_mismatch","unavailable"), "failure":nullable(enum("capture_file_unavailable","capture_file_digest_mismatch"))})
D["Locator"] = {"oneOf":[
 obj({"kind":const("native_row"),"value":obj({"table_path":S,"row_index":I})}),
 obj({"kind":const("hdf5_path"),"value":{"type":"string","pattern":"^/"}}),
 obj({"kind":const("hic_block"),"value":obj({"chromosome1_index":I,"chromosome2_index":I,"resolution_bp":P,"block_id":I,"record_ordinal":nullable(I)})}),
 obj({"kind":const("bed_line"),"value":P}),
 obj({"kind":const("json_pointer"),"value":{"type":"string","pattern":"^(/|$)"}})]}
put("Failure", {"code":enum(*CODES), "stage":enum("input","native_parse","metadata","execution","capture","calculation","projection","return_validation"),
 "input_key":nullable(KEY),"population_key":nullable(KEY),"element_key":nullable(KEY),"pair_key":nullable(KEY),
 "artifact_ref":nullable(S),"locator":nullable(ref("Locator")),"field_path":nullable({"type":"string","pattern":"^/"}),
 "partial_artifact_refs":arr(S,unique=True),"requirement":enum(*REQUIREMENTS)})
put("ContigSpec", {"chromosome":S,"length_bp":P})
put("ReferenceSpec", {"assembly_accession":nullable(S),"assembly_label":nullable(S),"contigs":nullable(arr(ref("ContigSpec"))),"source_ref":nullable(S)})
put("SampleSpec", {"sample_key":KEY,"condition_key":nullable(KEY),"replicate_key":nullable(KEY),"assay":nullable(S),"source_ref":S})
put("ContactSampleLink", {"contact_input_key":KEY,"sample_key":KEY,"fraction":nullable({"type":"number","minimum":0,"maximum":1}),"source_ref":S})
put("DependenceGroup", {"group_key":KEY,"member_sample_keys":arr(KEY,1,True),"relationship":enum("same_sample","shared_library","technical_replicate","biological_replicate","pooled_input"),"source_ref":S})
put("AttributeBinding", {"native_attribute_path":S,"meaning":enum("sample_key","condition_key","replicate_key","assembly_label"),"supplied_target_key":KEY})
put("Unit", {"kind":enum("bp","kb","bins","count","contact_pairs","source_contact","source_contact_squared","normalized_contact","normalized_contact_squared","source_contact_per_pair","normalized_contact_per_pair","dimensionless"),"source_unit":nullable(S)})
D["Unit"]["allOf"]=[{"if":{"properties":{"kind":enum("source_contact","source_contact_squared","normalized_contact","normalized_contact_squared","source_contact_per_pair","normalized_contact_per_pair")}},"then":{"properties":{"source_unit":S}},"else":{"properties":{"source_unit":{"type":"null"}}}}]
put("SuppliedUncertainty", {"input_key":KEY,"population_key":nullable(KEY),"field":enum("raw_contact","normalized_contact","source_assay_measurement"),"native_attribute_path":nullable(S),"kind":enum("standard_error","standard_deviation","interval"),"value":nullable(N),"lower":nullable(N),"upper":nullable(N),"unit":ref("Unit"),"source_ref":S})
put("MetadataSpec", {"reference":ref("ReferenceSpec"),"samples":arr(ref("SampleSpec")),"contact_sample_links":arr(ref("ContactSampleLink")),"dependence_groups":arr(ref("DependenceGroup")),"native_attribute_bindings":arr(ref("AttributeBinding")),"supplied_uncertainty":arr(ref("SuppliedUncertainty"))})
put("ContactSpec", {"input_key":KEY,"file":ref("NativeFileIdentity"),"source_ref":S,"format":FORMAT,"group_path":nullable({"type":"string","pattern":"^/"}),"resolution_bp":nullable(P),"value_field":const("count"),"value_kind":enum("contact_count","supplied_contact_weight"),"value_unit":S,"specimen_key":nullable(KEY)})
D["ContactSpec"]["allOf"]=[{"if":{"properties":{"format":const("hic_binary_v9")}},"then":{"properties":{"group_path":{"type":"null"},"resolution_bp":P}},"else":{"properties":{"group_path":{"type":"string","pattern":"^/"}}}}, {"if":{"properties":{"value_kind":const("contact_count")}},"then":{"properties":{"value_unit":const("contacts")}}}]
put("PopulationSpec", {"population_key":KEY,"chromosome":S,"start_bp":I,"end_bp":P})
put("GeneLink", {"gene_key":KEY,"relationship":enum("promoter_of","enhancer_associated_with","overlaps_gene","supplied_association"),"source_ref":S})
D["AnchorSpec"]={"oneOf":[obj({"policy":const("interval_start")}),obj({"policy":const("supplied_position"),"position_bp":I})]}
put("ElementAssignment", {"element_key":KEY,"source_data_row":I,"class":enum("enhancer","promoter","other"),"gene_links":arr(ref("GeneLink")),"anchor":ref("AnchorSpec")})
put("ElementSpec", {"input_key":KEY,"file":ref("NativeFileIdentity"),"source_ref":S,"format":const("bed_outer_span_v1"),"reference":ref("ReferenceSpec"),"assignments":arr(ref("ElementAssignment"))})
D["NormalizationSpec"]={"oneOf":[obj({"kind":const("raw"),"weight_column":{"type":"null"},"convention":{"type":"null"}}),obj({"kind":const("precomputed_weighted"),"weight_column":S,"convention":enum("multiplicative","divisive")})]}
put("ChromatinRequest", {"version":const("chromatin_interaction_request_v1"),"operation":const("analyze_chromatin_interactions"),"analysis_modes":arr(MODES,1,True),"contact":ref("ContactSpec"),"populations":arr(ref("PopulationSpec"),1),"elements":nullable(ref("ElementSpec")),"normalization":ref("NormalizationSpec"),"supplied_metadata":ref("MetadataSpec"),"output_prefix":REL})
D["ChromatinRequest"]["allOf"]=[{"if":{"properties":{"analysis_modes":{"contains":const("cis_anchor_contact_enrichment")}}},"then":{"properties":{"elements":ref("ElementSpec")}}}]
put("Chromosome", {"chromosome_index":I,"chromosome":S,"length_bp":P})
put("NativeAttribute", {"path":S,"dtype":S,"shape":arr(I),"value_state":enum("decoded","retained_only"),"value":{"anyOf":[{"type":["string","boolean","null"]},N,arr({"anyOf":[{"type":["string","boolean","null"]},N]})]}})
put("NativeVectorDescriptor", {"name":S,"native_path":S,"chromosome_index":nullable(I),"resolution_bp":nullable(P),"dtype":S,"length":nullable(I),"extent":EX,"meaning":enum("normalization_weight","native_expected_not_used")})
put("NativeMetadata", {"source_file":ref("NativeFileIdentity"),"source_ref":S,"format":FORMAT,"format_version":enum(3,9),"group_path":nullable(S),"coordinate_system":const("zero_based_half_open"),"bin_type":enum("fixed","variable"),"bin_size_bp":nullable(P),"storage_mode":STORAGE,"value_field":const("count"),"value_dtype":enum("<i8","<u8","<f4","<f8"),"native_value_dtype":S,"value_kind":enum("contact_count","supplied_contact_weight"),"value_unit":S,"attributes":arr(ref("NativeAttribute")),"vectors":arr(ref("NativeVectorDescriptor")),"reference_assertion":ref("ReferenceSpec")})
put("NativeSheetHeader", {"metadata":nullable(ref("NativeMetadata")),"chromosomes":arr(ref("Chromosome"))})
put("RawCellPopulation", {k:nullable(I) for k in ["directed_cells","unique_unordered_cells","stored_rows","explicit_zero_rows","implicit_zero_directed_cells","native_nonfinite_directed_cells","unavailable_directed_cells"]}|{"validated_observed_row_count":I})
put("NativeRowRange", {"table_path":S,"start_row":I,"end_row":I})
put("PopulationReadEvidence", {"axes_extent":EX,"index_extent":EX,"selected_records_extent":EX,"required_native_row_ranges":arr(ref("NativeRowRange")),"expected_block_count":nullable(I),"read_block_count":nullable(I),"failed_block_ids":arr(I,unique=True),"implicit_zero_semantics":enum("validated_sparse_absence","not_established"),"symmetry":enum("native_symmetric_upper","native_hic_symmetric","square_reciprocal_verified","not_established")})
put("NormalizationSummary", {"specification":ref("NormalizationSpec"),"availability":enum("available","partial","missing","not_requested"),"vector_table_key":nullable(KEY),"native_weight_dtype":nullable(S),"valid_bin_count":nullable(I),"masked_bin_count":nullable(I),"invalid_bin_count":nullable(I)})
put("DtypeField", {"name":enum("bin1_id","bin2_id","value","source_block","source_row","state"),"dtype":enum("<i8","<u8","<f4","<f8","|u1")})
D["DtypeDescriptor"]={"oneOf":[obj({"kind":const("scalar"),"dtype":enum("<i8","<u8","<f4","<f8","utf8_tsv_int64")}),obj({"kind":const("structured"),"fields":arr(ref("DtypeField"),1)})]}
TABLE = {"table_key":KEY,"population_key":KEY,"role":ROLES,"availability":enum("present","not_requested","not_native_representation","unavailable"),"absence_reason":nullable(enum(*CODES)),"encoding":nullable(enum("tsv","npy")),"shape":nullable(arr(I,1)),"dtype_descriptor":nullable(ref("DtypeDescriptor")),"row_count":nullable(I),"native_source_locator":nullable(ref("Locator")),"extent":EX}
put("TableDraft", TABLE)
put("TableDescriptor", TABLE|{"file":nullable(ref("NativeFileIdentity"))})
for name in ['TableDraft','TableDescriptor']:
    present={"encoding":enum("tsv","npy"),"shape":arr(I,1),"dtype_descriptor":ref("DtypeDescriptor"),"row_count":I,"absence_reason":{"type":"null"}}
    absent={k:{"type":"null"} for k in ['encoding','shape','dtype_descriptor','row_count']}
    absent['extent']=const('unavailable')
    if name=='TableDescriptor': present['file']=ref('NativeFileIdentity');absent['file']={"type":"null"}
    D[name]['allOf']=[{"if":{"properties":{"availability":const('present')}},"then":{"properties":present},"else":{"properties":absent}},{"if":{"properties":{"availability":const('unavailable')}},"then":{"properties":{"absence_reason":enum(*CODES)}},"else":{"properties":{"absence_reason":{"type":"null"}}}}]
POPEX={"population_key":KEY,"selected_region":ref("PopulationSpec"),"extent":EX,"bin_count":nullable(I),"fixed_bin_size_bp":nullable(P),"native_storage_mode":nullable(STORAGE),"data_table_keys":arr(KEY,unique=True),"raw_cell_population":ref("RawCellPopulation"),"normalization":ref("NormalizationSummary"),"read_evidence":ref("PopulationReadEvidence"),"failures":arr(ref("Failure"))}
put("PopulationExtraction", POPEX)
put("ContactExtraction", {"format":FORMAT,"format_version":nullable(enum(3,9)),"native_metadata":nullable(ref("NativeMetadata")),"chromosomes":arr(ref("Chromosome")),"populations":arr(ref("PopulationExtraction")),"table_drafts":arr(ref("TableDraft")),"failures":arr(ref("Failure"))})
put("ElementRow", {"source_data_row":I,"source_line":P,"columns":arr(TEXT,3),"chromosome":S,"start_bp":I,"end_bp":P,"name":nullable(TEXT),"element_key":nullable(KEY),"class":nullable(enum("enhancer","promoter","other")),"gene_links":arr(ref("GeneLink")),"anchor":nullable(ref("AnchorSpec")),"anchor_position_bp":nullable(I)})
put("RetainedTextLine", {"source_line":P,"kind":enum("comment","track","browser","blank"),"raw_line_base64":{"type":"string","contentEncoding":"base64"}})
put("RejectedElementRow", {"source_data_row":I,"source_line":P,"raw_line_base64":{"type":"string","contentEncoding":"base64"},"failures":arr(ref("Failure"),1)})
put("ParsedElements", {"source_file":ref("NativeFileIdentity"),"input_data_row_count":I,"rows":arr(ref("ElementRow")),"rejected_rows":arr(ref("RejectedElementRow")),"other_lines":arr(ref("RetainedTextLine")),"extent":EX,"failures":arr(ref("Failure"))})
put("ReferenceAssertion", {"assertion_key":KEY,"input_key":KEY,"origin":enum("native","supplied"),"reference":ref("ReferenceSpec")})
put("ReferenceRelation", {"contact_input_key":KEY,"element_input_key":nullable(KEY),"population_key":KEY,"relation":RELATION,"basis":enum("accession_agreement","label_agreement","supplied_same_reference","contig_only","conflict","unknown"),"assertion_keys":arr(KEY,unique=True),"chromosome":S,"native_length_bp":nullable(P),"supplied_length_bp":nullable(P)})
put("ReferenceRelations", {"assertions":arr(ref("ReferenceAssertion")),"relations":arr(ref("ReferenceRelation"))})
put("SampleRelations", {"samples":arr(ref("SampleSpec")),"contact_sample_links":arr(ref("ContactSampleLink")),"dependence_groups":arr(ref("DependenceGroup")),"supplied_uncertainty":arr(ref("SuppliedUncertainty"))})
put("MetadataRelations", {"reference_assertions":arr(ref("ReferenceAssertion")),"reference_relations":arr(ref("ReferenceRelation")),"samples":arr(ref("SampleSpec")),"contact_sample_links":arr(ref("ContactSampleLink")),"dependence_groups":arr(ref("DependenceGroup")),"supplied_uncertainty":arr(ref("SuppliedUncertainty")),"failures":arr(ref("Failure"))})
put("UncertaintyNotMeasured", {"kind":const("not_measured"),"value":{"type":"null"},"unit":{"type":"null"}})
MEAS={"value":nullable(N),"state":STATES,"unit":ref("Unit"),"reason":nullable(enum(*CODES)),"population_key":KEY,"numerator":nullable(N),"denominator":nullable(N),"uncertainty":ref("UncertaintyNotMeasured")}
put("Measurement", MEAS)
D["Measurement"]["allOf"]=[{"if":{"properties":{"state":enum("observed","derived","normalized")}},"then":{"properties":{"value":N,"reason":{"type":"null"}}},"else":{"properties":{"value":{"type":"null"}}}}]
put("BooleanComponent", {"value":nullable(B),"state":enum("derived","missing","failed","truncated","incompatible","undefined"),"reason":nullable(enum(*CODES)),"population_key":KEY})
put("ElementAnchorRow", {"element_key":KEY,"source_data_row":I,"class":enum("enhancer","promoter","other"),"chromosome":S,"anchor_position_bp":I,"bin_id":nullable(I),"bin_ordinal":nullable(I),"membership":enum("inside","outside","unresolved"),"reference_relation":RELATION,"reason":nullable(enum(*CODES))})
put("PairBasis", {"pair_key":KEY,"population_key":KEY,"enhancer_element_key":KEY,"promoter_element_key":KEY,"enhancer_bin_id":nullable(I),"promoter_bin_id":nullable(I),"enhancer_bin_ordinal":nullable(I),"promoter_bin_ordinal":nullable(I),"enhancer_anchor_bp":I,"promoter_anchor_bp":I,"raw_contact":ref("Measurement"),"cell_origin":enum("explicit_native","validated_implicit_zero","unavailable"),"source_locators":arr(ref("Locator")),"reference_relation":RELATION,"reason":nullable(enum(*CODES))})
put("SheetPopulation", POPEX|{"element_anchor_rows":arr(ref("ElementAnchorRow")),"pair_rows":arr(ref("PairBasis"))})
put("ContactSheet", {"version":const("chromatin_interaction_sheet_v1"),"request":ref("ChromatinRequest"),"native":ref("NativeSheetHeader"),"references":ref("ReferenceRelations"),"samples":ref("SampleRelations"),"elements":nullable(ref("ParsedElements")),"populations":arr(ref("SheetPopulation")),"data_tables":arr(ref("TableDescriptor")),"failures":arr(ref("Failure"))})
put("NativeScalar", {"value":nullable(N),"state":enum("finite","native_nan","native_posinf","native_neginf","native_no_value")})
D["NativeScalar"]["allOf"]=[{"if":{"properties":{"state":const("finite")}},"then":{"properties":{"value":N}},"else":{"properties":{"value":{"type":"null"}}}}]
put("BinRow", {"bin_id":I,"chromosome_index":I,"start_bp":I,"end_bp":P})
put("ContactRow", {"bin1_id":I,"bin2_id":I,"value":ref("NativeScalar"),"source_block":{"type":"integer","minimum":-1},"source_row":I})
put("WeightRow", {"bin_id":I,"value":ref("NativeScalar")})
put("CellStateRow", {"bin1_id":I,"bin2_id":I,"state":enum(1,2,3,4,5)})
put("DenseTable", {"table_key":KEY,"row_bin_ids":arr(I),"column_bin_ids":arr(I),"values":arr(arr(ref("NativeScalar")))})
put("PopulationTableFixture", {"population_key":KEY,"bins":nullable(arr(ref("BinRow"))),"contacts":nullable(arr(ref("ContactRow"))),"weights":nullable(arr(ref("WeightRow"))),"cell_states":nullable(arr(ref("CellStateRow"))),"dense_values":nullable(ref("DenseTable"))})
put("ContactTableFixture", {"version":const("chromatin_contact_table_fixture_v1"),"populations":arr(ref("PopulationTableFixture"))})
put("ContactParameters", {"minimum_separation_bins":P,"fold_threshold":{"type":"number","minimum":0,"maximum":1.7976931348623157e308},"threshold_comparison":const("strict_gt"),"expectation":const("same_population_distance_mean"),"missing_policy":const("exclude_declared_masked_bins_require_complete_population")})
put("InsulationParameters", {"window_bins":P,"z_threshold":N,"threshold_comparison":const("strict_lt"),"zscore_ddof":const(0),"boundary_rule":const("strict_two_neighbor_minimum"),"window_end_rule":const("all_full_windows"),"missing_policy":const("complete_window")})
put("CalculationParameters", {"normalization":ref("NormalizationSpec"),"contact":nullable(ref("ContactParameters")),"insulation":nullable(ref("InsulationParameters"))})
put("RowQualifications", {"data_extent":EX,"reference_relation":RELATION,"normalization_kind":enum("raw","precomputed_weighted"),"normalization_state":enum("available","partial","missing","not_requested"),"eligibility":enum("eligible","below_minimum_separation","reference_unresolved","cell_unavailable","masked_bin","invalid_weight","incomplete_population","incompatible","ineligible_edge","undefined_statistic","not_applicable"),"interpretation":enum("complete_population","known_subset","heuristic_prediction"),"reasons":arr(enum(*CODES),unique=True)})
CONTACT_NUM="raw_contact normalized_contact anchor_distance_bp bin_separation expected_contact fold_enrichment occurrence_multiplicity".split()
DIST_NUM="nominal_distance_pair_count masked_distance_pair_count valid_distance_pair_count raw_distance_sum raw_distance_sum_squares distance_sum distance_sum_squares expected_contact distance_population_variance".split()
CONTACT_COUNTS="requested_pair_count eligible_pair_count fold_defined_pair_count above_threshold_pair_count distinct_bin_pair_count".split()
WINDOW_NUM="boundary_position_bp nominal_window_cell_count valid_window_cell_count known_cross_contact_sum cross_contact_sum cross_contact_mean insulation_z boundary_strength".split()
Z_NUM="nominal_window_count complete_window_count omitted_window_count z_population_count z_population_mean z_population_variance selected_boundary_count domain_count".split()
DOMAIN_NUM="domain_start_bp domain_end_bp domain_length_bp domain_size_kb".split()
POP_NUM="bin_count directed_cell_count unique_unordered_cell_count stored_row_count explicit_zero_row_count implicit_zero_directed_cell_count native_nonfinite_directed_cell_count unavailable_directed_cell_count requested_pair_count eligible_pair_count fold_defined_pair_count above_threshold_pair_count distinct_bin_pair_count nominal_window_count complete_window_count omitted_window_count selected_boundary_count domain_count".split()
put("PairMeasurements", {k:ref("Measurement") for k in CONTACT_NUM}|{"above_fold_threshold":ref("BooleanComponent")})
put("DistanceMeasurements", {k:ref("Measurement") for k in DIST_NUM})
put("ContactCountMeasurements", {k:ref("Measurement") for k in CONTACT_COUNTS})
put("WindowMeasurements", {k:ref("Measurement") for k in WINDOW_NUM}|{"is_boundary":ref("BooleanComponent")})
put("ZMeasurements", {k:ref("Measurement") for k in Z_NUM})
put("DomainMeasurements", {k:ref("Measurement") for k in DOMAIN_NUM})
def typed_measure(kinds, integer=False):
    return {"allOf":[ref("Measurement"),{"properties":{"unit":{"properties":{"kind":enum(*kinds)}},**({"value":nullable(I)} if integer else {})}}]}
for name in ["ContactCountMeasurements","ZMeasurements"]:
    for key in D[name]['properties']:
        if key not in {"z_population_mean","z_population_variance"}: D[name]['properties'][key]=typed_measure(["count","contact_pairs"],True)
for key in ["anchor_distance_bp","bin_separation","occurrence_multiplicity"]:
    D['PairMeasurements']['properties'][key]=typed_measure([{"anchor_distance_bp":"bp","bin_separation":"bins","occurrence_multiplicity":"count"}[key]],True)
for key in ["nominal_distance_pair_count","masked_distance_pair_count","valid_distance_pair_count"]:
    D['DistanceMeasurements']['properties'][key]=typed_measure(["contact_pairs"],True)
for key in ["boundary_position_bp","nominal_window_cell_count","valid_window_cell_count"]:
    D['WindowMeasurements']['properties'][key]=typed_measure(["bp" if key=='boundary_position_bp' else "contact_pairs"],True)
for key in DOMAIN_NUM:
    D['DomainMeasurements']['properties'][key]=typed_measure(["kb" if key=='domain_size_kb' else "bp"],key!='domain_size_kb')
UNIT_FIELDS={
 'PairMeasurements':{'raw_contact':['source_contact'],'normalized_contact':['normalized_contact'],'expected_contact':['source_contact','normalized_contact'],'fold_enrichment':['dimensionless']},
 'DistanceMeasurements':{'raw_distance_sum':['source_contact'],'raw_distance_sum_squares':['source_contact_squared'],'distance_sum':['source_contact','normalized_contact'],'distance_sum_squares':['source_contact_squared','normalized_contact_squared'],'expected_contact':['source_contact','normalized_contact'],'distance_population_variance':['source_contact_squared','normalized_contact_squared']},
 'WindowMeasurements':{'known_cross_contact_sum':['source_contact','normalized_contact'],'cross_contact_sum':['source_contact','normalized_contact'],'cross_contact_mean':['source_contact_per_pair','normalized_contact_per_pair'],'insulation_z':['dimensionless'],'boundary_strength':['dimensionless']},
 'ZMeasurements':{'z_population_mean':['source_contact','normalized_contact'],'z_population_variance':['source_contact_squared','normalized_contact_squared']}}
for name,fields in UNIT_FIELDS.items():
    for key,kinds in fields.items(): D[name]['properties'][key]=typed_measure(kinds)
PAIRKEYS={"pair_key":KEY,"population_key":KEY,"enhancer_element_key":KEY,"promoter_element_key":KEY,"enhancer_bin_id":nullable(I),"promoter_bin_id":nullable(I)}
DISTKEYS={"population_key":KEY,"separation_bins":P}
WINDOWKEYS={"population_key":KEY,"boundary_bin_id":I,"boundary_ordinal":I}
DOMAINKEYS={"domain_key":KEY,"population_key":KEY,"left_boundary_bin_id":I,"right_boundary_bin_id":I}
put("ContactPairComponent", PAIRKEYS|{"measurements":ref("PairMeasurements"),"qualifications":ref("RowQualifications")})
put("DistanceComponent", DISTKEYS|{"measurements":ref("DistanceMeasurements"),"qualifications":ref("RowQualifications")})
put("InsulationWindowComponent", WINDOWKEYS|{"measurements":ref("WindowMeasurements"),"qualifications":ref("RowQualifications")})
put("DomainComponent", DOMAINKEYS|{"measurements":ref("DomainMeasurements"),"qualifications":ref("RowQualifications")})
put("ContactPopulationComponents", {"population_key":KEY,"source_table_keys":arr(KEY,unique=True),"pairs":arr(ref("ContactPairComponent")),"distance_expectations":arr(ref("DistanceComponent")),"counts":ref("ContactCountMeasurements"),"qualifications":ref("RowQualifications"),"failures":arr(ref("Failure"))})
put("InsulationPopulationComponents", {"population_key":KEY,"source_table_keys":arr(KEY,unique=True),"windows":arr(ref("InsulationWindowComponent")),"statistics":ref("ZMeasurements"),"domains":arr(ref("DomainComponent")),"qualifications":ref("RowQualifications"),"failures":arr(ref("Failure"))})
BASIS={"source_sheet_sha256":SHA,"table_identities":arr(ref("NativeFileIdentity")),"normalization":ref("NormalizationSpec")}
put("ContactComponents", {"version":const("chromatin_contact_components_v1"),**BASIS,"mode":const("cis_anchor_contact_enrichment"),"parameters":ref("ContactParameters"),"populations":arr(ref("ContactPopulationComponents")),"failures":arr(ref("Failure"))})
put("InsulationComponents", {"version":const("chromatin_insulation_components_v1"),**BASIS,"mode":const("cross_window_insulation_heuristic"),"parameters":ref("InsulationParameters"),"populations":arr(ref("InsulationPopulationComponents")),"failures":arr(ref("Failure"))})
put("ChromatinComponents", {"version":const("chromatin_interaction_components_v1"),"source_sheet_sha256":SHA,"table_identities":arr(ref("NativeFileIdentity")),"parameters":ref("CalculationParameters"),"contact":nullable(ref("ContactComponents")),"insulation":nullable(ref("InsulationComponents")),"failures":arr(ref("Failure"))})
put("SavedSheetBundle", {"sheet":ref("NativeFileIdentity"),"tables":arr(ref("NativeFileIdentity"))})
put("PageSelection", {"offset":I,"limit":P})
KEY_SELECTIONS={"contact_pairs":("pair_keys",KEY,PAIRKEYS,CONTACT_NUM+["above_fold_threshold"]),"distance_expectations":("separations",P,DISTKEYS,DIST_NUM),"insulation_windows":("boundary_bin_ids",I,WINDOWKEYS,WINDOW_NUM+["is_boundary"]),"domains":("domain_keys",KEY,DOMAINKEYS,DOMAIN_NUM)}
SELECTORS=[]; PROJROWS={}
for kind,(keyname,keytype,rowkeys,fields) in KEY_SELECTIONS.items():
    selected={"oneOf":[obj({"by":const("keys"),keyname:arr(keytype,1,True)}),obj({"by":const("page"),"page":ref("PageSelection")})]}
    SELECTORS.append(obj({"kind":const(kind),"selection":selected,"fields":arr(enum(*fields),1,True)}))
    source={'contact_pairs':'PairMeasurements','distance_expectations':'DistanceMeasurements','insulation_windows':'WindowMeasurements','domains':'DomainMeasurements'}[kind]
    field_schemas={k:D[source]['properties'][k] for k in fields}
    name="Projection"+"".join(p.title() for p in kind.split("_"))+"Row"
    put(name,rowkeys|{"fields":obj(field_schemas,[]),"qualifications":ref("RowQualifications")})
    D[name]["properties"]["fields"]["minProperties"]=1
    PROJROWS[kind]=name
SELECTORS.append(obj({"kind":const("population_metrics"),"fields":arr(enum(*POP_NUM),1,True)}))
put("ProjectionPopulationMetricsRow", {"population_key":KEY,"fields":obj({k:typed_measure(['count','contact_pairs'],True) for k in POP_NUM},[]),"qualifications":ref("RowQualifications")})
D["ProjectionPopulationMetricsRow"]["properties"]["fields"]["minProperties"]=1
PROJROWS["population_metrics"]="ProjectionPopulationMetricsRow"
D["ProjectionSelection"]={"oneOf":SELECTORS}
put("ResultSelector", {"version":const("chromatin_interaction_result_selector_v1"),"mode":enum("native_result","saved_sheet_recalculation"),"saved_sheet_bundle":nullable(ref("SavedSheetBundle")),"population_keys":arr(KEY,1,True),"parameters":ref("CalculationParameters"),"projection":ref("ProjectionSelection")})
D["ResultSelector"]["allOf"]=[{"if":{"properties":{"mode":const("native_result")}},"then":{"properties":{"saved_sheet_bundle":{"type":"null"}}},"else":{"properties":{"saved_sheet_bundle":ref("SavedSheetBundle")}}}]
put("PageResult", {"offset":I,"returned_count":I,"total_row_count":nullable(I),"has_more":B})
D["RequestedProjection"]={"oneOf":[obj({"version":const("chromatin_interaction_projection_v1"),"source_sheet_sha256":SHA,"parameters":ref("CalculationParameters"),"kind":const(kind),"population_keys":arr(KEY,1,True),"requested_fields":arr(enum(*(POP_NUM if kind=="population_metrics" else KEY_SELECTIONS[kind][3])),1,True),"rows":arr(ref(rowname)),"page":nullable(ref("PageResult")),"qualifications":arr(ref("RowQualifications")),"failures":arr(ref("Failure"))}) for kind,rowname in PROJROWS.items()]}
put("Policy", {"memory_bytes":const(21474836480),"scratch_bytes":const(4294967296),"wall_seconds":{"type":"null"}})
put("ImplementationFile", {"module":S,"sha256":SHA})
put("DependencyFile", {"path":ABS,"sha256":SHA,"size_bytes":I})
put("DependencyBinding", {"distribution":S,"version":S,"package_root":ABS,"files":arr(ref("DependencyFile"),1)})
put("SoftwareBinding", {"python_executable":ABS,"python_sha256":SHA,"python_version":S,"module_root":ABS,"driver_module":const("gene_annotation_episode.native_chromatin_interaction_driver"),"implementation_files":arr(ref("ImplementationFile"),1),"dependencies":arr(ref("DependencyBinding"),1)})
put("Binding", {"operation":const("analyze_chromatin_interactions"),"resource_kind":const("local"),"analysis_modes":arr(MODES,1,True),"supported_formats":arr(FORMAT,1,True),"software":ref("SoftwareBinding")})
put("InputBinding", {"input_key":KEY,"file":ref("NativeFileIdentity"),"path":ABS})
ENV_KEYS="PYTHONPATH PYTHONHOME PYTHONNOUSERSITE PYTHONSAFEPATH PYTHONDONTWRITEBYTECODE TMPDIR TMP TEMP XDG_CACHE_HOME PIP_CACHE_DIR OPENBLAS_NUM_THREADS OMP_NUM_THREADS".split()
put("Environment", {k:S for k in ENV_KEYS},)  # Exact declared caller environment keys; values remain supplied.
put("NativeJob", {"request":ref("ChromatinRequest"),"software":ref("SoftwareBinding"),"input_bindings":arr(ref("InputBinding"),1)})
put("RequestedJob", {"argv":arr(S,5),"environment":ref("Environment"),"native_chromatin_interactions":ref("NativeJob")})
put("AttemptIdentity", {"run_id":S,"episode_id":S,"resource_id":S,"execution_id":S,"operation_key":S,"attempt_id":SHA,"requested_job_sha256":SHA,"assignment_sha256":SHA})
OUTPUT_ROLES="original_contact original_elements original_metadata bins contacts weights cell_states dense_values population_manifest bundle stdout stderr".split()
put("OutputSpec", {"file_key":KEY,"population_key":nullable(KEY),"role":enum(*OUTPUT_ROLES),"relative_path":REL,"format":S})
put("RunPlan", {"version":const("chromatin_interaction_run_plan_v1"),"identity":ref("AttemptIdentity"),"requested_job":ref("RequestedJob"),"attempt_directory":ABS,"policy":ref("Policy"),"outputs":arr(ref("OutputSpec"),1)})
put("DeclaredTable", {"draft":ref("TableDraft"),"declaration":ref("NativeFileDeclaration")})
put("PopulationSeal", {"version":const("chromatin_interaction_population_seal_v1"),"identity":ref("AttemptIdentity"),"request_sha256":SHA,"population":ref("PopulationExtraction"),"tables":arr(ref("DeclaredTable")),"input_files":arr(ref("NativeFileIdentity"),1),"failures":arr(ref("Failure"))})
put("DeclaredOutput", {"specification":ref("OutputSpec"),"declaration":ref("NativeFileDeclaration")})
put("NativeBundle", {"version":const("chromatin_interaction_native_bundle_v1"),"identity":ref("AttemptIdentity"),"request":ref("ChromatinRequest"),"software":ref("SoftwareBinding"),"extraction":nullable(ref("ContactExtraction")),"elements":nullable(ref("ParsedElements")),"metadata":nullable(ref("MetadataRelations")),"population_seals":arr(ref("NativeFileDeclaration")),"outputs":arr(ref("DeclaredOutput")),"failures":arr(ref("Failure"))})
put("RetainedFile", {"file":ref("NativeFileIdentity"),"path":ABS})
put("RetainedSheetBundle", {"sheet":ref("RetainedFile"),"tables":arr(ref("RetainedFile"))})
put("CapturedInputFile", {"specification":ref("OutputSpec"),"declaration_source":enum("bundle","population","none"),"capture":nullable(ref("NativeFileCapture")),"retained":nullable(ref("RetainedFile"))})
DRIVERSTATE=enum("sealed_bundle","unsealed_attempt","not_started")
CAPTURE={"original_plan":ref("RunPlan"),"source_action_receipt_ref":S,"writer_closure_receipt_ref":S,"driver_state":DRIVERSTATE,"bundle":nullable(ref("RetainedFile")),"files":arr(ref("CapturedInputFile")),"failures":arr(ref("Failure"))}
put("NativeCapture", CAPTURE)
put("NativeWorkerPlan", {"version":const("chromatin_interaction_result_worker_plan_v1"),"mode":const("native_result"),"directory":ABS,**CAPTURE,"selector":ref("ResultSelector")})
put("SavedWorkerPlan", {"version":const("chromatin_interaction_result_worker_plan_v1"),"mode":const("saved_sheet_recalculation"),"directory":ABS,"sheet_bundle":ref("RetainedSheetBundle"),"selector":ref("ResultSelector")})
D["WorkerPlan"]={"oneOf":[ref("NativeWorkerPlan"),ref("SavedWorkerPlan")]}
put("WorkerOutput", {"role":enum("sheet","table","components","projection","diagnostics"),"table_key":nullable(KEY),"declaration":ref("NativeFileDeclaration")})
put("WorkerResult", {"version":const("chromatin_interaction_result_worker_result_v1"),"mode":enum("native_result","saved_sheet_recalculation"),"state":enum("produced","partial","unavailable"),"source_sheet_sha256":nullable(SHA),"parameters":ref("CalculationParameters"),"outputs":arr(ref("WorkerOutput")),"failures":arr(ref("Failure"))})
put("CapturedWorkerOutput", {"role":enum("sheet","table","components","projection","diagnostics"),"table_key":nullable(KEY),"capture":ref("NativeFileCapture")})
put("WorkerCapture", {"version":const("chromatin_interaction_worker_capture_v1"),"plan_file":ref("NativeFileIdentity"),"execution_receipt_file":ref("NativeFileIdentity"),"worker_result_file":nullable(ref("NativeFileIdentity")),"result":nullable(ref("WorkerResult")),"outputs":arr(ref("CapturedWorkerOutput")),"failures":arr(ref("Failure"))})
put("DiagnosticPopulation", {"population_key":KEY,"manifest_origin":enum("bundle","population","none"),"manifest_file":nullable(ref("NativeFileIdentity")),"result_extent":EX,"failures":arr(ref("Failure"))})
put("Diagnostics", {"version":const("chromatin_interaction_result_diagnostics_v1"),"mode":enum("native_result","saved_sheet_recalculation"),"populations":arr(ref("DiagnosticPopulation")),"failures":arr(ref("Failure"))})

schema={"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:planning:chromatin-interaction:439:records:v1","title":"Planning-only complete chromatin interface records, packet 439","$defs":D}
(ROOT/"RECORD_SCHEMA.json").write_text(json.dumps(schema,indent=2,allow_nan=False)+"\n")
(ROOT/"SCHEMA_COLUMN_INVENTORY.json").write_text(json.dumps({"record_type":"data_field_inventory_not_formula_rules","contact_pair":CONTACT_NUM+["above_fold_threshold"],"distance":DIST_NUM,"contact_counts":CONTACT_COUNTS,"window":WINDOW_NUM+["is_boundary"],"z_statistics":Z_NUM,"domain":DOMAIN_NUM,"population":POP_NUM},indent=2)+"\n")
print(json.dumps({"schema_definitions":len(D),"output":"RECORD_SCHEMA.json"}))
