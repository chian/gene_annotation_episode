"""Closed numerical views of frozen additional-BLAST database results.

No acquisition, parsing, calculation, publication or authority lookup occurs in
this module. The caller owns the immutable generation and receiving scope.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .domain import ContractError, validate_schema


_PROGRAMS = ("psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")
FUNCTION_SELECTOR = "native_blast_database_result_selector_vdb_function_v1"
FUNCTION_FAMILIES = ("vdb_function_summary", "vdb_function", "vdb_function_contribution", "vdb_function_census")
SAVED_INPUT_SOURCE = "execution_blast_database_vdb_function_saved_inputs"
_BOOLEANS = {
    "search": ("native_converged", "limit_reached"),
    "sequence_hit": ("geometry_complete",), "profile_model": ("geometry_complete",),
    "vdb_subject": ("geometry_complete",),
    "sequence_function": ("calibrated_annotation_probability",),
    "iteration_convergence": ("native_converged",),
    "sequence_taxonomy": ("target_independent_of_search",),
    "vdb_taxonomy": ("target_independent_of_search",),
    "vdb_membership": ("complete_for_reported_subjects", "complete_for_origin_members"),
    "vdb_population": ("population_complete",),
    "vdb_function_summary": ("report_complete", "metadata_complete", "dependency_complete", "calibrated_annotation_probability"),
    "vdb_function": ("calibrated_annotation_probability",),
    "vdb_function_census": ("census_complete",),
}


def _definition(inputs, formula, units, population, denominator=None, *, origin="derived",
                missingness="Null retains missing_input, not_measured, incompatible_input, invalid_native_row or partial_output; measured zero remains available."):
    return dict(inputs=inputs, formula=formula, units=units, population=population,
        denominator=denominator, origin=origin,
        coordinates="Zero-based half-open original query/member intervals; model/PSSM axes are positions, never biological reference residues.",
        uncertainty="No new uncertainty estimate; complete native statistics and qualifications remain in the calculation artifact.",
        missingness=missingness)


def _catalog():
    """Executable catalog construction, with no expression evaluation/dispatch."""
    out = {}
    def add(family, names, units, source, population, *, origin="derived"):
        assert len(names.split()) == len(units.split())
        rows = out.setdefault(family, {})
        for name, unit in zip(names.split(), units.split()):
            rows[name] = _definition(source + "." + name, "Copy the named saved component without rounding.",
                unit, population, origin=origin)
    add("search", "reported_hit_count reported_hsp_count observed_hsp_count parsed_hit_count parsed_hsp_count declared_alignment_row_count",
        "hit hsp hsp hit hsp hsp", "search.counts", "Original native search containers and retained valid projections")
    add("search", "native_iteration biological_round reported_include native_inclusion_threshold domain_inclusion_threshold",
        "count count expected_count expected_count expected_count", "iteration.searches", "One source-qualified search")
    add("hsp", "native_score_bits native_raw_score native_evalue alignment_columns paired_columns identical_pairs query_gap_columns reference_gap_columns paired_query_units paired_reference_units paired_identity alignment_identity reported_query_coverage reported_reference_coverage reported_query_length reported_reference_length",
        "bits native_score expected_count alignment_column paired_column paired_column alignment_column alignment_column query_unit reference_unit fraction fraction fraction fraction query_unit reference_unit",
        "native_hsp_components.component", "One original raw HSP; representative symbols for a profile", origin="native_report")
    add("sequence_hit", "maximum_bit_score minimum_evalue hsp_count observed_paired_query_positions observed_paired_reference_positions unique_pair_count identical_unique_pair_count overlap_pair_representations query_paired_coverage reference_paired_coverage selected_query_coverage",
        "bits expected_count hsp query_unit reference_unit paired_column paired_column paired_column fraction fraction fraction",
        "sequence_components.components.database_sheet.hits.measurements", "Original sequence hit; paired position unions")
    add("sequence_group", "maximum_bit_score hit_representation_count explicit_function_count", "bits hit count",
        "sequence_components.components.database_sheet.sequence_groups", "Demonstrated sequence group, or explicitly unresolved native-hit group")
    add("sequence_function", "sequence_group_count native_hit_count maximum_bit_score mean_bit_score scored_group_count function_mass function_prior unadjusted_probability representation_adjusted_probability",
        "sequence_group hit bits bits sequence_group function_mass fraction fraction fraction",
        "sequence_components.components", "Explicit function assignments among returned scored sequence groups")
    add("sequence_population", "database_sequence_count database_total_sequence_count database_fraction observed_sequence_group_count",
        "sequence sequence fraction sequence_group", "sequence_components.components.database_sheet.database_representation.function_representation",
        "Actual supplied selected database census and matching function")
    taxonomy = "unambiguous_group_count ambiguous_group_count unknown_group_count same_taxon_pair_count comparable_pair_count same_taxon_pair_fraction target_matching_groups target_conflicting_groups target_ambiguous_groups target_matching_fraction"
    tunits = "sequence_group sequence_group sequence_group taxon_pair taxon_pair fraction sequence_group sequence_group sequence_group fraction"
    add("sequence_taxonomy", taxonomy, tunits, "sequence_components.components.database_sheet.taxonomy.ranks",
        "Whole-result or exact function-specific sequence groups; independently supplied target context")
    quality = "completeness_fraction contamination_fraction contig_count contig_n50 total_sequence_length"
    qunits = "fraction fraction count nt nt"
    add("sequence_quality", quality, qunits, "sequence_components.components.database_sheet.source_quality.assembly_measurements.measurements",
        "Exact linked assembly/source/method measurement", origin="supplied_source_record")
    add("profile_model", "paired_query_units paired_model_positions query_coverage selected_query_coverage model_coverage",
        "query_unit model_position fraction fraction fraction", "profile_components.models", "One exact source-qualified model and union of its paired HSPs")
    add("profile_hsp_model", "model_columns specific_bits_threshold specific_bits_margin reporting_bits_threshold reporting_bits_margin",
        "model_position bits bits bits bits", "profile_components.hsps.model_matches", "Exact HSP/model/database-release relation")
    add("profile_overlap", "paired_query_overlap_units", "query_unit", "profile_components.dependence.query_overlaps",
        "Intersection of two model-specific query unions; not independent evidence")
    add("pssm_matrix", "residue_rows positions master_reported_length master_decoded_length lambda kappa h scalingFactor lambdaUngapped kappaUngapped hUngapped wordScoreThreshold",
        "residue_row pssm_position aa aa inverse_native_score native_statistic native_statistic native_weight inverse_native_score native_statistic native_statistic native_score",
        "pssm_components.matrices", "One original PSSM record", origin="native_report")
    add("pssm_cell", "scores resFreqsPerPos weightedResFreqsPerPos freqRatios",
        "native_score native_frequency native_weight native_frequency_ratio", "pssm_components.matrices.matrix_values",
        "One native position and residue row; no population-probability interpretation", origin="native_report")
    add("pssm_position", "informationContent gaplessColumnWeights sigma intervalSizes numMatchingSeqs numIndeptObsr",
        "native_information_content native_weight native_statistic count sequence native_statistic", "pssm_components.matrices.position_diagnostics",
        "One model position and the native model construction population", origin="native_report")
    add("iteration_inclusion", "member_record_count duplicate_member_count observed_unique_member_count included_sequence_count",
        "member member member member", "iteration.inclusion_observations", "Explicit checkpoint native member identifiers; no query subtraction", origin="supplied_source_record")
    out["iteration_convergence"] = {}
    add("iteration_comparison", "added_count removed_count retained_count earlier_target_count later_target_count", "count count count count count",
        "iteration.round_comparisons", "Explicitly related complete retained returned target sets, not a database census")
    add("vdb_subject", "observed_paired_query_units observed_paired_reference_nt maximum_bit_score minimum_evalue hsp_count full_query_coverage selected_query_coverage reported_reference_coverage full_member_coverage",
        "query_unit nt bits expected_count hsp fraction fraction fraction fraction", "vdb_components.subjects", "One original native VDB subject; distinct full/selected/reported/member axes")
    add("vdb_membership", "reported_subject_count reported_hsp_count origin_bound_subject_count origin_unbound_subject_count origin_ambiguous_subject_count catalog_read_count catalog_reference_count catalog_wgs_sequence_count catalog_unknown_count origin_read_count origin_reference_count origin_wgs_sequence_count origin_unknown_count demonstrated_group_count grouped_subject_count ungrouped_subject_count duplicate_subject_representations observed_origin_sample_count catalog_sample_count unresolved_origin_member_count",
        "hit hsp hit hit hit member member member member member member member member sequence_group hit hit hit sample sample member",
        "vdb_components.membership/sequence_groups/sample_groups", "Native subjects, exact catalogue members, qualified reported-origin members, demonstrated sequences and linked samples remain distinct")
    add("vdb_sequence_group", "subject_count member_count", "hit member", "vdb_components.sequence_groups.groups", "Demonstrated full-sequence identity group")
    add("vdb_sample", "origin_member_count catalog_member_count origin_subject_count", "member member hit", "vdb_components.sample_groups.groups",
        "Exact unique linked member/subject keys within one source-qualified sample")
    add("vdb_feature", "paired_reference_overlap_nt feature_length_nt feature_translation_length feature_paired_nt_coverage paired_subject_fraction_in_feature feature_paired_residue_coverage",
        "nt nt aa fraction fraction fraction", "vdb_components.feature_components", "Exact linked member feature; full ordered codon map retained separately")
    add("vdb_feature_hsp", "paired_reference_overlap_nt aligned_reference_overlap_nt paired_query_overlap_units complete_paired_codons partial_codon_overlap_nt corresponding_feature_residues identical_query_feature_residues substitutions_query_feature",
        "nt nt query_unit count nt aa aa aa", "vdb_components.feature_components.hsp_rows", "One original HSP and exact linked feature")
    add("vdb_taxonomy", taxonomy + " different_taxon_pair_fraction", tunits + " fraction", "vdb_components.taxonomy.sequence_group_ranks",
        "Demonstrated sequence groups, excluding sample-only taxonomy")
    add("vdb_quality", quality, qunits, "vdb_components.source_quality.records", "Exact linked assembly, metadata source and method", origin="supplied_source_record")
    add("vdb_population", "total_count observed_entity_count observed_fraction_of_supplied_population", "population_unit population_unit fraction",
        "vdb_components.population_components.records", "Exact dataset/snapshot/filter/count-unit population and complete supplied membership")
    add("vdb_population_function", "population_function_count population_function_fraction observed_function_entity_count observed_fraction_of_function_population",
        "population_unit fraction population_unit fraction", "vdb_components.population_components.records.function_components",
        "Exact function and whole_sequence/feature/sample assignment in its supplied population")

    def define(family, metric, inputs, formula, denominator=None):
        out[family][metric].update(inputs=inputs, formula=formula, denominator=denominator)
    for family in ("sequence_taxonomy", "vdb_taxonomy"):
        define(family, "same_taxon_pair_fraction", "same_taxon_pair_count, comparable_pair_count", "same / comparable", "k*(k-1)/2 for k unambiguous groups")
        define(family, "target_matching_fraction", "target_matching_groups, target_conflicting_groups", "matching / (matching + conflicting)", "matching + conflicting; ambiguous/unknown excluded")
    define("vdb_taxonomy", "different_taxon_pair_fraction", "comparable_pair_count, same_taxon_pair_count", "(comparable - same) / comparable", "comparable_pair_count")
    for name, source in {"native_score_bits":"native_scores.bit_score", "native_raw_score":"native_scores.score", "native_evalue":"native_scores.evalue", "paired_query_units":"counts.paired_query_positions", "paired_reference_units":"counts.paired_reference_positions", "reported_query_length":"denominators.query_length", "reported_reference_length":"denominators.reference_length"}.items():
        define("hsp", name, "AlignmentComponents." + source, "Copy the raw-reported-axis component; never substitute the qualified full axis.")
    for name, n, d in (("paired_identity", "identical_pairs", "paired_columns"), ("alignment_identity", "identical_pairs", "alignment_columns"),
                       ("reported_query_coverage", "paired_query_positions", "query_length"), ("reported_reference_coverage", "paired_reference_positions", "reference_length")):
        define("hsp", name, "AlignmentComponents.counts." + n + ", AlignmentComponents.denominators." + d,
            "Copy the stored fraction; numerator/denominator remain null when unreported. Percentage fallback does not invent an identity count.", d)
    for family, names in {"sequence_hit":("query_paired_coverage", "reference_paired_coverage", "selected_query_coverage"),
        "profile_model":("query_coverage", "selected_query_coverage", "model_coverage"),
        "vdb_subject":("full_query_coverage", "selected_query_coverage", "reported_reference_coverage", "full_member_coverage"),
        "vdb_feature":("feature_paired_nt_coverage", "paired_subject_fraction_in_feature", "feature_paired_residue_coverage"),
        "vdb_population":("observed_fraction_of_supplied_population",),
        "vdb_population_function":("population_function_fraction", "observed_fraction_of_function_population",)}.items():
        for name in names:
            out[family][name].update(formula="Copy the saved numerator/denominator ratio and completeness; partial unions retain observed numerator but no complete fraction.",
                                    denominator="Exact " + name.removesuffix("_coverage").removesuffix("_fraction") + " axis/population denominator in the named component")
    define("sequence_group", "hit_representation_count", "G.hit_indices", "len(G.hit_indices)")
    define("sequence_group", "explicit_function_count", "G.functions", "len(G.functions)")
    define("sequence_function", "function_mass", "W.function_masses[function]; G.maximum_bit_score, G.functions, W.parameters.temperature_bits", "M_f=sum(2**((b_g-b*)/temperature_bits)/k_g); b* is the largest scored annotated-group bit score")
    define("sequence_function", "function_prior", "W.parameters.function_priors[function]", "Copy normalized selected prior; no empirical annotation-probability claim")
    define("sequence_function", "unadjusted_probability", "W.unadjusted_probabilities[function], W.function_masses, W.parameters.function_priors", "pi_f*M_f / sum(pi*M)", "sum(pi*M) among scored explicitly assigned functions")
    define("sequence_function", "representation_adjusted_probability", "W.representation_adjusted_probabilities[function], actual qualified N_f, W.function_masses, W.parameters.function_priors", "(pi_f*M_f/N_f) / sum(pi*M/N)", "sum(pi*M/N); actual selected database census required")
    define("sequence_population", "database_fraction", "database_sequence_count, database_total_sequence_count", "count / total", "Actual supplied database total, never returned hits")
    for prefix in ("specific", "reporting"):
        define("profile_hsp_model", prefix + "_bits_margin", "native bit score and exact same-model/release " + prefix + "_bits_threshold", "bit_score - threshold; copy stored margin")
    for name in out["pssm_cell"]:
        out["pssm_cell"][name]["formula"] = "For M residue rows and N positions, raw[r*N+p] if byRow=true, otherwise raw[p*M+r]; copy normalized [p][r], require M*N. Do not divide scores by scalingFactor."
    for name in out["pssm_position"]:
        out["pssm_position"][name]["formula"] = "Copy the N-element native diagnostic at original position; retain native REAL decoding and dimension qualification."
    for name in ("completeness_fraction", "contamination_fraction"):
        define("vdb_quality", name, "Exact linked assembly " + name.replace("fraction", "percent"), "supplied percentage / 100; contamination may exceed 1")
    for name, source in (("origin_member_count", "origin_member_keys"), ("catalog_member_count", "catalog_member_keys"), ("origin_subject_count", "origin_subject_row_keys")):
        define("vdb_sample", name, "sample_groups.groups." + source, "len(distinct exact stored keys)")
    for name, formula in (("member_record_count", "len(members)"), ("duplicate_member_count", "len(members)-len(unique identifiers)"), ("observed_unique_member_count", "len(unique(namespace,value,version))"), ("included_sequence_count", "unique count only for a complete qualified checkpoint membership")):
        out["iteration_inclusion"][name]["formula"] = formula
    for name, formula in (("added_count", "|L\\E|"), ("removed_count", "|E\\L|"), ("retained_count", "|E intersection L|"), ("earlier_target_count", "|E|"), ("later_target_count", "|L|")):
        out["iteration_comparison"][name]["formula"] = formula + "; only for the calculator's complete qualified sets"
    out["sequence_record_quality"] = deepcopy(out["sequence_quality"])
    add("vdb_function_summary", "source_entity_count eligible_entity_count excluded_entity_count eligible_hsp_count target_unit_count model_group_count unknown_origin_subject_count unassigned_target_unit_count unresolved_sample_entity_count unknown_reference_kernel_fraction",
        "entity_unit entity_unit entity_unit hsp target_unit model_group_unit hit target_unit entity_unit fraction",
        "vdb_function.components.strata", "Exact search, assignment scope and literal namespace; observed eligible/excluded source entities and demonstrated targets")
    add("vdb_function", "function_mass log2_function_mass prior log2_prior conditional_function_weight log2_conditional_function_weight census_function_unit_count census_total_unit_count census_function_fraction census_partition_function_mass representation_rate representation_adjusted_function_weight log2_representation_adjusted_function_weight",
        "function_mass log2_function_mass fraction log2_fraction fraction log2_fraction model_group_unit model_group_unit fraction function_mass function_rate_unit fraction log2_fraction",
        "vdb_function.components.strata.functions", "Represented scored functions in one exact search/scope/namespace; qualified complete matching census for corrected cells")
    add("vdb_function_contribution", "best_bit_score within_group_kernel split_denominator function_baseline_mass global_baseline_mass",
        "bits kernel_weight kernel_weight function_mass kernel_weight", "vdb_function.components.strata.groups.function_contributions",
        "One demonstrated target or explicitly selected dependence block and function/unknown bucket")
    add("vdb_function_census", "base_entity_count target_unit_count model_group_count", "base_entity_unit target_unit model_group_unit",
        "vdb_function.components.census_results", "Actual retained enumeration, descriptively counted even when incomplete")
    for family in FUNCTION_FAMILIES:
        for name, definition in out[family].items():
            definition.update(missingness="Copy the saved qualification. Positive linear underflow is null with a finite log2 value; mathematical zero remains zero. No publication-time arithmetic.",
                uncertainty="Not estimated; model-conditional weights are not calibrated annotation probabilities.")
    for metric, numerator, denominator in (
            ("conditional_function_weight", "prior_weighted_mass.value", "conditional_weight_denominator.value"),
            ("representation_adjusted_function_weight", "representation_rate.value", "representation_adjusted_weight_denominator.value")):
        out["vdb_function"][metric].update(inputs="Saved FunctionComponent." + numerator + " and StratumComponents." + denominator,
            formula="Copy the saved normalized value and its saved numerator/denominator; never recompute.", denominator=denominator)
    return out


_METRICS = _catalog()
_UNITS = tuple("bits native_score expected_count alignment_column paired_column aa nt model_position native_reference_position pssm_position residue_row sequence sequence_group hit hsp metadata_record member sample feature taxon_pair count fraction kernel_weight function_mass native_frequency native_frequency_ratio native_weight native_information_content inverse_native_score native_statistic".split())
_REASONS = ("missing_input", "not_measured", "incompatible_input", "invalid_native_row", "partial_output", "unsupported_schema", None)
_ORIGINS = ("native_report", "native_traceback", "derived", "supplied_source_record", "native_extractor_output", "supplied_effective_option", "mixed")
_STATUS = ("available", "unavailable", "incompatible")
_NATIVE_STATUS = ("complete", "partial", "no_reported_hits", "available", "unavailable", "incompatible", "ambiguous", "invalid")
_FAILURE_CODES = tuple("native_blast_database_capture_incomplete native_blast_database_artifact_missing native_blast_database_artifact_identity_mismatch native_blast_metadata_schema_unsupported native_blast_metadata_payload_invalid native_blast_metadata_source_unavailable native_blast_metadata_relation_unresolved native_blast_metadata_relation_conflict native_blast_metadata_extractor_unbound native_blast_database_query_unbound native_blast_database_report_unreadable native_blast_database_sheet_invalid native_blast_database_calculation_failed native_blast_database_row_unavailable native_blast_database_selector_unavailable native_blast_database_worker_resource_limit native_blast_database_worker_failed native_blast_database_frozen_artifact_changed native_blast_database_publication_invalid native_blast_database_return_unauthorized".split())
_DETAIL_CODES = tuple("artifact_bytes_unavailable artifact_digest_conflict attempt_identity_conflict metadata_tuple_unregistered metadata_shape_invalid metadata_address_unresolved metadata_relation_conflict extractor_not_registered query_identity_unresolved native_syntax_invalid native_row_invalid calculator_contract_invalid resource_limit implementation_failure explicit_row_missing frozen_value_changed scope_or_receipt_conflict".split())


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _array(items, **kw):
    return dict(type="array", items=items, **kw)


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


_TOKEN = {"type": "string", "minLength": 1, "maxLength": 512, "pattern": r"^[^\n\r\u0000]+$"}
_POINTER = {"type": "string", "pattern": r"^(?:/(?:[^~]|~[01])*)?$"}
_SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_I0 = {"type": "integer", "minimum": 0}
_REF = {**_TOKEN, "format": "reference", "x-reference-namespace": "execution_result"}
_ENTITY = {**_TOKEN, "format": "identifier", "x-reference-namespace": "native_blast_database_entity_key"}
_ARTIFACT = {**_TOKEN, "format": "identifier", "x-reference-namespace": "native_blast_database_artifact_key"}
_ROW_ID = {**_TOKEN, "format": "identifier", "x-reference-namespace": "native_blast_database_row"}
_SEARCH = _object(dict(artifact_key=_ARTIFACT, member_ordinal=_nullable(_I0), report_index=_I0,
    search_pointer={**_POINTER, "format": "identifier", "x-reference-namespace": "native_blast_database_search_pointer"}))
_ROW = _object(dict(search_key=_SEARCH, hit_ordinal=_nullable(_I0), hsp_ordinal=_nullable(_I0), description_ordinal=_nullable(_I0)))
_PROV = _object(dict(source_ref=_REF, pointer=_POINTER))
_IDENTIFIER = _object(dict(namespace=_TOKEN, value=_ENTITY, version=_nullable(_TOKEN)))
_FUNCTION = _object(dict(namespace=_TOKEN, value=_ENTITY))
_MEMBER = _object(dict(dataset_key=_ENTITY, member_kind={"enum": ["read", "reference", "wgs_sequence", "unknown"]}, member_identifier=_IDENTIFIER))
_INTERVAL = {"type": "array", "prefixItems": [_I0, {"type": "integer", "minimum": 1}], "minItems": 2, "maxItems": 2}
_QIDENTITY = _object(dict(artifact_key=_ARTIFACT, record_ordinal=_I0,
    axis_kind={"enum": ["sequence", "msa_master", "pssm_master"]}, selected_interval=_nullable(_INTERVAL)))

_SAVED_RECEIPT = _object(dict(source_ref=_REF, run_id=_TOKEN, episode_id=_TOKEN,
    operation_key=_TOKEN, receipt_sha256=_SHA))
_SAVED_INPUT_FIELDS = dict(original_result_receipt=_SAVED_RECEIPT,
    manifest_artifact_ref=_REF, manifest_sha256=_SHA, sheets_artifact_ref=_REF, sheets_sha256=_SHA,
    collection_artifact_ref=_REF, collection_sha256=_SHA, input_interpretation_id=_SHA, original_calculation_id=_SHA)
_SAVED_INPUT_SCHEMA = _object(dict(schema={"const": "native_blast_vdb_function_saved_input_v1"}, **_SAVED_INPUT_FIELDS))
_CALCULATION_INPUT = {"oneOf": [_object(dict(mode={"const": "captured_inputs"})),
    _object(dict(mode={"const": "saved_function_sheet"}, **_SAVED_INPUT_FIELDS))]}


def saved_function_descriptor(calculation_input):
    value = _copy(calculation_input)
    validate_schema(value, _CALCULATION_INPUT)
    if value["mode"] != "saved_function_sheet":
        raise ContractError("native_blast_database_saved_function_input_required")
    return dict(schema="native_blast_vdb_function_saved_input_v1", **{k: v for k, v in value.items() if k != "mode"})


def _identities():
    search, row = dict(search_key=_SEARCH), dict(row_key=_ROW)
    identities = {"search": search, "hsp": row, "sequence_hit": row, "vdb_subject": row,
        "sequence_group": {**search, "hit_ordinals": _array(_I0, uniqueItems=True)},
        "sequence_function": {**search, "function": _ENTITY}, "sequence_population": {**search, "function": _ENTITY},
        "sequence_taxonomy": {**search, "function": _nullable(_ENTITY), "rank": _TOKEN},
        "sequence_quality": {**search, "function": _nullable(_ENTITY), "assembly_source": _PROV},
        "sequence_record_quality": {**search, "function": _nullable(_ENTITY), "assembly_source": _object(dict(
            source_ref=_REF, pointer={"const": ""}, record_locator=_object(dict(kind={"const": "fasta_record"}, record_ordinal=_I0))))},
        "profile_model": {**search, "profile_source": _PROV, "model_identifier": _IDENTIFIER},
        "profile_hsp_model": {**row, "profile_source": _PROV, "model_identifier": _IDENTIFIER},
        "profile_overlap": {**search, "left_profile_source": _PROV, "right_profile_source": _PROV},
        "iteration_inclusion": {"record_source": _PROV},
        "iteration_comparison": {"earlier_search_key": _SEARCH, "later_search_key": _SEARCH,
            "relation_source": _PROV, "identity_basis": {"enum": ["full_sequence_digest", "profile_model_identifier"]}},
        "vdb_membership": search, "vdb_sequence_group": {**search, "sequence_group_key": _ENTITY},
        "vdb_sample": {**search, "sample_key": _ENTITY, "sources": _array(_PROV, uniqueItems=True)},
        "vdb_feature": {**search, "member_key": _MEMBER, "feature_identifier": _IDENTIFIER, "sources": _array(_PROV, uniqueItems=True)},
        "vdb_feature_hsp": {**row, "member_key": _MEMBER, "feature_identifier": _IDENTIFIER, "sources": _array(_PROV, uniqueItems=True)},
        "vdb_taxonomy": {**search, "rank": _TOKEN},
        "vdb_quality": {**search, "metadata_source": _PROV, "assembly_identifier": _IDENTIFIER},
        "vdb_population": {**search, "population_source": _PROV, "population_key": _ENTITY}}
    identities["vdb_population_function"] = {**identities["vdb_population"], "function": _FUNCTION,
        "assignment_scope": {"enum": ["whole_sequence", "feature", "sample"]}}
    stratum = {**search, "assignment_scope": {"enum": ["whole_sequence", "feature"]}, "namespace": _TOKEN,
        "grouping_model": {"enum": ["target_duplicates_only", "known_source_blocks"]}}
    identities.update(vdb_function_summary=stratum,
        vdb_function={**stratum, "function": _FUNCTION, "census_key": _nullable(_ENTITY)},
        vdb_function_contribution={**stratum, "group_key": _ENTITY, "function": _nullable(_FUNCTION)},
        vdb_function_census={**stratum, "census_key": _ENTITY})
    for name in ("pssm_matrix", "pssm_position", "pssm_cell"):
        identities[name] = dict(artifact_key=_ARTIFACT, record_ordinal=_I0)
        if name != "pssm_matrix":
            identities[name]["position"] = _I0
        if name == "pssm_cell":
            identities[name]["residue_row"] = _I0
    schemas = {k: _object(v) for k, v in identities.items()}
    schemas["iteration_convergence"] = {"oneOf": [_object(dict(record_source=_PROV, scope={"const": scope},
        search_key=_SEARCH if scope == "search" else {"type": "null"},
        query_identity=_QIDENTITY if scope == "query" else {"type": "null"})) for scope in ("search", "query", "unbound")]}
    return schemas


_IDENTITIES = _identities()


def _eligible(family, program):
    if family in ("search", "hsp"):
        return program in _PROGRAMS
    return program in ({"sequence": ("psiblast", "deltablast"),
        "profile": ("deltablast", "rpsblast", "rpstblastn"), "iteration": ("psiblast", "deltablast"),
        "pssm": ("psiblast", "deltablast", "tblastn_vdb"), "vdb": ("blastn_vdb", "tblastn_vdb")}.get(family.split("_", 1)[0], ()))


def _copy(value, _active=None):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or type(value) is dict and all(type(k) is str for k in value):
        active = set() if _active is None else _active
        if id(value) in active:
            raise ContractError("native_blast_database_finite_json_required")
        active.add(id(value))
        try:
            if type(value) is list:
                return [_copy(v, active) for v in value]
            return {k: _copy(v, active) for k, v in value.items()}
        finally:
            active.remove(id(value))
    raise ContractError("native_blast_database_finite_json_required")


def _cell_schema(family, boolean=False):
    names = _BOOLEANS.get(family, ()) if boolean else tuple(_METRICS[family])
    properties = dict(name={"enum": list(names)} if names else {"not": {}},
        value={"type": ["boolean" if boolean else "number", "null"]},
        status={"enum": list(_STATUS)}, reason={"enum": [r for r in _REASONS if not boolean or r != "unsupported_schema"] +
            (["linear_underflow", "arithmetic_out_of_range"] if family in FUNCTION_FAMILIES and not boolean else [])},
        origin={"enum": list(_ORIGINS)}, component_pointer=_POINTER)
    if not boolean:
        properties.update(numerator={"type": ["number", "null"]}, denominator={"type": ["number", "null"]},
            unit={"enum": list(_UNITS) + ("target_unit dependence_block member_instance feature_instance log2_function_mass log2_fraction function_mass_per_target_unit function_mass_per_dependence_block".split() if family in FUNCTION_FAMILIES else [])}, complete={"type": ["boolean", "null"]})
    schema = _object(properties)
    schema["allOf"] = [{"if": {"properties": {"value": {"type": "null"}}},
        "then": {"properties": {"status": {"enum": ["unavailable", "incompatible"]}, "reason": {"not": {"type": "null"}}}},
        "else": {"properties": {"status": {"const": "available"}, "reason": {"type": "null"}}}}]
    if not boolean:
        dynamic = {"query_unit": ["aa", "nt"], "reference_unit": ["aa", "nt", "model_position", "native_reference_position"],
            "population_unit": ["member", "sequence_group", "feature", "sample"],
            "entity_unit": ["member", "feature"], "base_entity_unit": ["member_instance", "feature_instance"],
            "model_group_unit": ["target_unit", "dependence_block"],
            "function_rate_unit": ["function_mass_per_target_unit", "function_mass_per_dependence_block"]}
        schema["allOf"].extend({"if": {"properties": {"name": {"const": name}}},
            "then": {"properties": {"unit": {"enum": dynamic.get(definition["units"], [definition["units"]])}}}}
            for name, definition in _METRICS[family].items())
    return schema


def native_blast_database_row_schema(family):
    """Closed FullRow schema. Fact sources add the publication-only fields."""
    if family not in _METRICS:
        raise ContractError("native_blast_database_family_invalid")
    return deepcopy(_object(dict(schema={"const": "native_blast_vdb_function_numeric_row_v1" if family in FUNCTION_FAMILIES else "native_blast_database_numeric_row_v1"}, family={"const": family},
        record_key=_ROW_ID, calculation_id=_SHA, identity=_IDENTITIES[family],
        program={"enum": [p for p in _PROGRAMS if _eligible(family, p)]},
        context=_object(dict(query_axis_kind={"enum": ["sequence", "msa_master", "pssm_master", None]},
            reference_axis_kind={"enum": ["sequence", "profile_model", "vdb_member", None]},
            stage={"enum": ["sequence_database", "domain_database", None]},
            native_iteration=_nullable({"type": "integer", "minimum": 1}), biological_round=_nullable({"type": "integer", "minimum": 1}))),
        component_refs=_array(_object(dict(artifact_role={"enum": ["collection", "sheets", "calculations"]}, pointer=_POINTER))),
        native_status={"enum": list(_NATIVE_STATUS) + (["no_eligible_functions"] if family in FUNCTION_FAMILIES else [])}, measurements=_array(_cell_schema(family)), booleans=_array(_cell_schema(family, True)))))


def _failure_schema():
    # A failed requested address need not exist. It does not assert possession
    # of a row/artifact and must not use the successful row's reference types.
    failed_search = _object(dict(artifact_key=_TOKEN, member_ordinal=_nullable(_I0),
        report_index=_I0, search_pointer=_POINTER))
    return _object(dict(stage={"enum": "capture metadata inputs collection population calculation rows projection publication authority worker".split()},
        code={"enum": list(_FAILURE_CODES)}, artifact_key=_nullable(_TOKEN), input_key=_nullable(_TOKEN),
        search_key=_nullable(failed_search), record_key=_nullable(_TOKEN), pointer=_POINTER, detail_code={"enum": list(_DETAIL_CODES)}))


def native_blast_database_fact_sources():
    sources = {}
    for family in _METRICS:
        name = "execution_blast_database_" + family + "_rows"
        schema = native_blast_database_row_schema(family)
        extra = dict(source_ref=_REF, observation_ref=_nullable(_REF),
            subject_ref=_nullable({**_REF, "x-reference-namespace": "subject"}),
            reference_refs=_array(_REF, uniqueItems=True), publication_status={"enum": ["published", "source_only", "invalid"]})
        schema["properties"].update(extra); schema["required"].extend(extra)
        sources[name] = dict(type="array", meaning="Selected frozen " + family + " numerical components; null and measured zero are distinct. Full native associations remain retained.",
            report_schema={**_array(schema, uniqueItems=True), "x-source": name, "x-unique-by": ["calculation_id", "record_key"]})
    for name, schema in (("result_refs", _array(_REF, uniqueItems=True)), ("failures", _array(_failure_schema())),
            ("acquisition", _object({k: {"type": "boolean"} for k in ("acquisition_complete", "projection_complete", "native_execution_successful", "complete")}))):
        source = "execution_blast_database_" + name
        sources[source] = dict(type=schema["type"], meaning="Frozen selected native database result " + name + ".", report_schema={**schema, "x-source": source})
    sources[SAVED_INPUT_SOURCE] = dict(type="array", meaning="Exact admitted immutable VDB function generation available for a separately selected saved calculation.",
        report_schema={**_array(_SAVED_INPUT_SCHEMA, uniqueItems=True), "x-source": SAVED_INPUT_SOURCE})
    return deepcopy(sources)


def validate_native_blast_database_result_selector(selector, *, program):
    selector = _copy(selector)
    if program not in _PROGRAMS:
        raise ContractError("native_blast_database_result_program_unsupported")
    identity = dict(artifact_ref=_REF, sha256=_SHA, size_bytes=_I0)
    function_mode = selector.get("version") == FUNCTION_SELECTOR if type(selector) is dict else False
    if function_mode and program not in ("blastn_vdb", "tblastn_vdb"):
        raise ContractError("native_blast_database_result_program_unsupported")
    schema = _object(dict(version={"const": FUNCTION_SELECTOR if function_mode else "native_blast_database_result_selector_v1"}, acquisition={"const": "complete_bound_bundle"},
        metadata_inputs=_array(_object(dict(input_key=_TOKEN, consumer={"enum": ["query_identity", "sequence_database", "profile", "iteration", "vdb"] + (["vdb_function"] if function_mode else [])}, schema_id=_TOKEN, **identity))),
        retained_sources=_array(_object(dict(source_ref=_REF, **identity))), projections=_array({"oneOf": [_object(dict(family={"const": f},
            rows={"oneOf": [_object(dict(offset=_I0, limit={"type": "integer", "minimum": 1})), _object(dict(record_keys=_array(_ROW_ID, minItems=1, uniqueItems=True)))]},
            metrics=_array({"enum": list(_METRICS[f])} if _METRICS[f] else {"not": {}}, uniqueItems=True),
            booleans=_array({"enum": list(_BOOLEANS[f])} if _BOOLEANS.get(f) else {"not": {}}, uniqueItems=True)))
            for f in _METRICS if _eligible(f, program) and (function_mode or f not in FUNCTION_FAMILIES)]}, minItems=1)))
    if function_mode:
        schema["properties"].update(vdb_function_model={"type": "object"}, calculation_input=_CALCULATION_INPUT)
        schema["required"].extend(("vdb_function_model", "calculation_input"))
    try:
        validate_schema(selector, schema)
        if function_mode:
            from .blast_vdb_function_calculators import validate_blast_vdb_function_model
            validate_blast_vdb_function_model(selector["vdb_function_model"])
            if selector["calculation_input"]["mode"] == "saved_function_sheet" and (selector["metadata_inputs"] or selector["retained_sources"]):
                raise ValueError("saved_function_input_cannot_add_metadata")
        if len({p["family"] for p in selector["projections"]}) != len(selector["projections"]):
            raise ValueError("duplicate_family")
        for projection in selector["projections"]:
            if not projection["metrics"] and not projection["booleans"]:
                raise ValueError("empty_metrics")
            if "offset" in projection["rows"] and any(type(v) is not int for v in projection["rows"].values()):
                raise ValueError("integer_required")
        identities = {}
        for row in selector["metadata_inputs"]:
            value = tuple(row[k] for k in ("artifact_ref", "sha256", "size_bytes"))
            if row["input_key"] in identities and identities[row["input_key"]] != value:
                raise ValueError("metadata_identity_conflict")
            identities[row["input_key"]] = value
        tuples = [(r["input_key"], r["consumer"], r["schema_id"]) for r in selector["metadata_inputs"]]
        if len(set(tuples)) != len(tuples) or any(type(r["size_bytes"]) is not int for r in selector["metadata_inputs"]):
            raise ValueError("duplicate_metadata_tuple_or_integer_required")
        for rows, key in ((selector["retained_sources"], "source_ref"),):
            if len({r[key] for r in rows}) != len(rows) or any(type(r["size_bytes"]) is not int for r in rows):
                raise ValueError("duplicate_identity_or_integer_required")
    except (ValueError, KeyError, TypeError) as error:
        raise ContractError("native_blast_database_result_selector_invalid") from error
    return selector


def _validate_row(row, calculation_id, *, full=True):
    family = row.get("family") if type(row) is dict else None
    validate_schema(row, native_blast_database_row_schema(family))
    integer_fields = {"member_ordinal", "report_index", "hit_ordinal", "hsp_ordinal", "description_ordinal",
        "record_ordinal", "position", "residue_row", "native_iteration", "biological_round"}
    def exact_integers(value):
        if type(value) is dict:
            for key, child in value.items():
                if key in integer_fields and child is not None and type(child) is not int:
                    raise ContractError("native_blast_database_integer_required")
                if key in ("hit_ordinals", "selected_interval") and child is not None:
                    if any(type(n) is not int for n in child):
                        raise ContractError("native_blast_database_integer_required")
                    if key == "hit_ordinals" and child != sorted(set(child)) or key == "selected_interval" and child[0] >= child[1]:
                        raise ContractError("native_blast_database_identity_order_invalid")
                exact_integers(child)
        elif type(value) is list:
            for child in value:
                exact_integers(child)
    exact_integers(row["identity"]); exact_integers(row["context"])
    if row["calculation_id"] != calculation_id:
        raise ContractError("native_blast_database_calculation_identity_conflict")
    for field, catalog in (("measurements", _METRICS[family]), ("booleans", _BOOLEANS.get(family, ()))):
        names = [c["name"] for c in row[field]]
        if len(set(names)) != len(names) or full and set(names) != set(catalog):
            raise ContractError("native_blast_database_row_cells_invalid")
    return row


def project_native_blast_database_rows(full_rows, *, selector, calculation_id):
    """Select exact frozen cells in requested order. Never parse or calculate."""
    rows = _copy(full_rows)
    validate_schema(calculation_id, _SHA)
    if type(rows) is not list:
        raise ContractError("native_blast_database_rows_required")
    programs = {r.get("program") for r in rows if type(r) is dict}
    if len(programs) > 1:
        raise ContractError("native_blast_database_row_program_conflict")
    if programs:
        selector = validate_native_blast_database_result_selector(selector, program=next(iter(programs)))
    else:
        # Empty saved populations still have a checkable selector. The owning
        # E preparation has the program and performs its stricter pair check.
        valid = []
        for program in _PROGRAMS:
            try:
                valid.append(validate_native_blast_database_result_selector(selector, program=program))
            except ValueError:
                pass
        if not valid:
            raise ContractError("native_blast_database_result_selector_invalid")
        selector = valid[0]
    byfamily = {f: [] for f in _METRICS}; seen = set()
    for row in rows:
        _validate_row(row, calculation_id)
        if row["record_key"] in seen:
            raise ContractError("native_blast_database_row_identity_duplicate")
        seen.add(row["record_key"]); byfamily[row["family"]].append(row)
    output, failures = [], []
    for pi, spec in enumerate(selector["projections"]):
        family, selection = spec["family"], spec["rows"]
        population = byfamily[family]; next_offset = None
        if "record_keys" in selection:
            index = {r["record_key"]: r for r in population}; selected = []
            for ri, key in enumerate(selection["record_keys"]):
                if key in index:
                    selected.append(index[key])
                else:
                    failures.append(dict(stage="projection", code="native_blast_database_selector_unavailable", artifact_key=None,
                        input_key=None, search_key=None, record_key=key, pointer=f"/projections/{pi}/rows/record_keys/{ri}", detail_code="explicit_row_missing"))
        else:
            offset, limit = selection["offset"], selection["limit"]
            selected = population[offset:offset + limit]
            if offset + len(selected) < len(population):
                next_offset = offset + len(selected)
        projected = []
        for row in selected:
            saved = deepcopy(row)
            for field, names in (("measurements", spec["metrics"]), ("booleans", spec["booleans"])):
                cells = {c["name"]: c for c in row[field]}
                saved[field] = [deepcopy(cells[name]) for name in names]
            projected.append(saved)
        output.append(dict(family=family, total_rows=len(population), selected_record_keys=[r["record_key"] for r in projected], next_offset=next_offset, rows=projected))
    return dict(schema="native_blast_database_projection_v1", calculation_id=calculation_id, families=output, failures=failures)


def native_blast_database_metric_definitions(*, include_vdb_function=True):
    return deepcopy({k: v for k, v in _METRICS.items() if include_vdb_function or k not in FUNCTION_FAMILIES})


__all__ = ["validate_native_blast_database_result_selector", "native_blast_database_row_schema",
    "native_blast_database_fact_sources", "project_native_blast_database_rows", "native_blast_database_metric_definitions"]
