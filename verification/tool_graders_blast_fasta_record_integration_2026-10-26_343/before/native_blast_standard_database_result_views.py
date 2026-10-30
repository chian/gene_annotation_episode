"""Closed standard database BLAST numerical fields and frozen projections.

This module does no acquisition, parsing, calculation or publication. Complete
scientific components remain in the saved calculation; the receiver selects
only named numerical cells from those immutable rows.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from .domain import ContractError, validate_schema


PROGRAMS = ("blastn", "blastp", "blastx", "tblastn", "tblastx")
UNITS = {"blastn": ("nt", "nt", "nt"), "blastp": ("aa", "aa", "aa"),
         "blastx": ("nt", "aa", "aa"), "tblastn": ("aa", "nt", "aa"),
         "tblastx": ("nt", "nt", "aa")}
PREFIX = "native_blast_standard_database_"
BOOLEANS = {"search": ("limit_reached",), "hsp": ("qualified_geometry_available",),
            "sequence_hit": ("geometry_complete",),
            "sequence_function": ("calibrated_annotation_probability",),
            "sequence_taxonomy": ("target_independent_of_search",)}
REASONS = ("missing_input", "not_measured", "incompatible_input", "invalid_native_row",
           "partial_output", "unsupported_schema")
ORIGINS = ("native_report", "native_traceback", "derived", "supplied_source_record",
           "native_extractor_output", "supplied_effective_option", "mixed")
STATUSES = ("available", "unavailable", "incompatible")
NATIVE_STATUSES = ("complete", "partial", "no_reported_hits", "available", "unavailable",
                   "incompatible", "ambiguous", "invalid")
FAILURE_CODES = tuple(PREFIX + code for code in "capture_incomplete artifact_missing artifact_identity_mismatch metadata_schema_unsupported metadata_payload_invalid metadata_source_unavailable metadata_relation_unresolved metadata_relation_conflict metadata_extractor_unbound query_unbound report_unreadable sheet_invalid calculation_failed row_unavailable selector_unavailable worker_resource_limit worker_failed frozen_artifact_changed publication_invalid return_unauthorized".split())
DETAIL_CODES = tuple("artifact_bytes_unavailable artifact_digest_conflict attempt_identity_conflict metadata_tuple_unregistered metadata_shape_invalid metadata_address_unresolved metadata_relation_conflict extractor_not_registered query_identity_unresolved native_syntax_invalid native_row_invalid calculator_contract_invalid resource_limit implementation_failure explicit_row_missing frozen_value_changed scope_or_receipt_conflict".split())


def _copy(value, active=None):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or type(value) is dict and all(type(k) is str for k in value):
        active = set() if active is None else active
        if id(value) in active:
            raise ContractError(PREFIX + "finite_json_required")
        active.add(id(value))
        try:
            return [_copy(v, active) for v in value] if type(value) is list else {k: _copy(v, active) for k, v in value.items()}
        finally:
            active.remove(id(value))
    raise ContractError(PREFIX + "finite_json_required")


def _hash(value):
    return hashlib.sha256(json.dumps(_copy(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _array(items, **kw):
    return dict(type="array", items=items, **kw)


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


TOKEN = {"type": "string", "minLength": 1, "pattern": r"^[^\n\r\u0000]+$"}
POINTER = {"type": "string", "pattern": r"^(?:/(?:[^~]|~[01])*)?$"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
I0 = {"type": "integer", "minimum": 0}
REF = {**TOKEN, "format": "reference", "x-reference-namespace": "execution_result"}
ARTIFACT = {**TOKEN, "format": "identifier", "x-reference-namespace": PREFIX + "artifact_key"}
ENTITY = {**TOKEN, "format": "identifier", "x-reference-namespace": PREFIX + "entity_key"}
ROW_ID = {**TOKEN, "format": "identifier", "x-reference-namespace": PREFIX + "row"}
SEARCH_KEY_SCHEMA = _object(dict(artifact_key=ARTIFACT, member_ordinal=_nullable(I0), report_index=I0,
    search_pointer={**POINTER, "format": "identifier", "x-reference-namespace": PREFIX + "search_pointer"}))
ROW_KEY_SCHEMA = _object(dict(search_key=SEARCH_KEY_SCHEMA, hit_ordinal=_nullable(I0),
    hsp_ordinal=_nullable(I0), description_ordinal=_nullable(I0)))
PROVENANCE_SCHEMA = _object(dict(source_ref=REF, pointer=POINTER))


def _definition(inputs, formula, units, population, denominator=None, *, origin="derived"):
    return dict(inputs=inputs, formula=formula, units=units, population=population,
        denominator=denominator, origin=origin,
        coordinates="Original zero-based half-open nt/aa intervals; translated nongap nt spans have width 3. PSSM indices are zero-based model positions.",
        uncertainty="No uncertainty fitted; retain original native statistical context and qualifications.",
        missingness="Null is qualified as missing_input, not_measured, incompatible_input, invalid_native_row, partial_output or unsupported_schema; measured zero remains available.")


def _catalog():
    out = {}
    def add(family, fields, units, path, population, *, origin="derived"):
        names, units = fields.split(), units.split()
        assert len(names) == len(units)
        out[family] = {name: _definition(path + "." + name, "Copy the exact saved component without rounding.", unit, population, origin=origin)
                       for name, unit in zip(names, units)}
    add("search", "reported_hit_count reported_hsp_count observed_hsp_count parsed_hit_count parsed_hsp_count declared_alignment_row_count",
        "hit hsp hsp hit hsp alignment_row", "search_facts.counts", "One original source-qualified search")
    add("search_statistic", "native_database_sequences native_database_letters native_hsp_length_adjustment native_effective_search_space native_lambda native_kappa native_entropy",
        "sequence native_database_letter native_length_adjustment native_effective_search_space inverse_native_score native_statistic native_statistic",
        "native_search_statistics.measurements", "Original native search statistical model, not a function census", origin="native_report")
    add("hsp", "native_score_bits native_raw_score native_evalue native_reported_alignment_columns native_reported_identity_count native_reported_positive_count native_reported_gap_count native_reported_identity_percent native_reported_query_coverage_percent native_reported_query_subject_coverage_percent native_reported_query_unique_subject_coverage_percent alignment_columns paired_columns identical_pairs query_gap_columns reference_gap_columns paired_query_units paired_reference_units paired_identity alignment_identity reported_query_length reported_reference_length reported_query_coverage reported_reference_coverage qualified_paired_query_units qualified_paired_reference_units full_query_paired_coverage full_reference_paired_coverage",
        "bits native_score expected_count alignment_column alignment_column alignment_column alignment_column percent percent percent percent alignment_column paired_column paired_column alignment_column alignment_column query_unit reference_unit fraction fraction query_unit reference_unit fraction fraction query_unit reference_unit fraction fraction",
        "native_hsp_components.component", "One original HSP slot; alternative HSPs are not independent references")
    add("sequence_hit", "maximum_bit_score minimum_evalue hsp_count observed_paired_query_positions observed_paired_reference_positions unique_pair_count identical_unique_pair_count overlap_pair_representations query_paired_coverage reference_paired_coverage selected_query_coverage",
        "bits expected_count hsp query_unit reference_unit paired_column paired_column paired_column fraction fraction fraction",
        "sequence.components.components.database_sheet.hits.measurements", "One original hit, using unions of qualified original coordinates")
    add("sequence_group", "maximum_bit_score hit_representation_count explicit_function_count", "bits hit count",
        "sequence.components.components.database_sheet.sequence_groups", "Demonstrated full-sequence group or explicitly unresolved native-hit group")
    add("sequence_function", "sequence_group_count native_hit_count maximum_bit_score mean_bit_score scored_group_count function_mass function_prior unadjusted_probability representation_adjusted_probability",
        "sequence_group hit bits bits sequence_group function_mass fraction fraction fraction",
        "sequence.components.components", "Explicitly assigned functions among returned scored sequence groups")
    add("sequence_population", "database_sequence_count database_total_sequence_count database_fraction observed_sequence_group_count",
        "census_unit census_unit fraction sequence_group", "sequence.components.components.database_sheet.database_representation.function_representation",
        "Actual supplied census of the selected database/release/scope and exact function")
    add("sequence_taxonomy", "unambiguous_group_count ambiguous_group_count unknown_group_count same_taxon_pair_count comparable_pair_count same_taxon_pair_fraction target_matching_groups target_conflicting_groups target_ambiguous_groups target_matching_fraction",
        "sequence_group sequence_group sequence_group taxon_pair taxon_pair fraction sequence_group sequence_group sequence_group fraction",
        "sequence.components.components.database_sheet.taxonomy.ranks", "Whole result or exact function-specific groups at one supplied rank")
    add("sequence_quality", "completeness_fraction contamination_fraction contig_count contig_n50 total_sequence_length",
        "fraction fraction count nt nt", "sequence.components.components.database_sheet.source_quality.assembly_measurements.measurements",
        "Exact linked source and assembly measurement method", origin="supplied_source_record")
    add("pssm_matrix", "residue_rows positions master_reported_length master_decoded_length lambda kappa h scalingFactor lambdaUngapped kappaUngapped hUngapped wordScoreThreshold",
        "residue_row pssm_position aa aa inverse_native_score native_statistic native_statistic native_weight inverse_native_score native_statistic native_statistic native_score",
        "pssm.components.matrices", "One actual supplied tblastn PSSM record", origin="native_report")
    add("pssm_position", "informationContent gaplessColumnWeights sigma intervalSizes numMatchingSeqs numIndeptObsr",
        "native_information_content native_weight native_statistic count sequence native_statistic",
        "pssm.components.matrices.position_diagnostics", "One model position in the original PSSM", origin="native_report")
    add("pssm_cell", "scores resFreqsPerPos weightedResFreqsPerPos freqRatios",
        "native_score native_frequency native_weight native_frequency_ratio", "pssm.components.matrices.matrix_values",
        "One native residue row and model position, not an annotation probability", origin="native_report")
    def define(family, name, inputs, formula, denominator=None, origin=None):
        out[family][name].update(inputs=inputs, formula=formula, denominator=denominator)
        if origin is not None:
            out[family][name]["origin"] = origin
    for name, source in zip(out["search_statistic"], ("db_num", "db_len", "hsp_len", "eff_space", "lambda", "kappa", "entropy")):
        define("search_statistic", name, "original search.stat." + source, "Copy finite native statistic; nonnegative integer required for the four count/space fields. Absent in tables is not_measured.", origin="native_report")
    for name in ("reported_hit_count", "reported_hsp_count", "observed_hsp_count"):
        define("search", name, "original search.hits[].hsps[] or table section rows", "Count original containers, including malformed slots. Observed HSP count retains known arrays when other arrays are unavailable.", origin="native_report")
    for name in ("parsed_hit_count", "parsed_hsp_count"):
        define("search", name, "source-qualified normalized hits and HSP arrays", "Count retained parsed rows separately from original slots.")
    define("search", "declared_alignment_row_count", "original table7 '# N hits found' control line", "Copy declared alignment-row count; never relabel it as distinct subjects.", origin="native_report")
    hsp_paths = {"native_score_bits": "native_scores.bit_score", "native_raw_score": "native_scores.score", "native_evalue": "native_scores.evalue",
        **{"native_reported_" + n: "reported_counts." + f for n, f in (("alignment_columns", "align_len"), ("identity_count", "identity"), ("positive_count", "positive"), ("gap_count", "gaps"))},
        **{"native_reported_" + n: "reported_percentages." + n for n in ("identity_percent", "query_coverage_percent", "query_subject_coverage_percent", "query_unique_subject_coverage_percent")},
        "reported_query_length": "denominators.query_length", "reported_reference_length": "denominators.reference_length"}
    for name, path in hsp_paths.items():
        define("hsp", name, "native_hsp_components.component." + path, "Copy raw reported-axis field; qcovs/qcovus are query coverage and never reference coverage.", origin="native_report")
    for name, formula in (("alignment_columns", "len(qseq)"), ("paired_columns", "count(qseq[i] != '-' and hseq[i] != '-')"),
            ("identical_pairs", "count(equal nongap symbol pairs)"), ("query_gap_columns", "qseq.count('-')"), ("reference_gap_columns", "hseq.count('-')")):
        define("hsp", name, "original qseq,hseq; qualified reported counts when traceback absent", formula + "; existing qualified reported-count fallback remains separately sourced", origin="mixed")
    for prefix, axis in (("query", "query"), ("reference", "reference")):
        define("hsp", "paired_" + prefix + "_units", "raw component.pairs and counts.paired_" + axis + "_positions", "Sum widths of valid paired original-coordinate intervals; invalid reported-axis geometry is unavailable.")
        define("hsp", "qualified_paired_" + prefix + "_units", "qualified_hsp_components.component_pointer -> saved303 HSP.counts.paired_" + axis + "_positions", "Copy existing full-axis count resolved by original row_key and component_index. No second calculation.")
        define("hsp", "reported_" + prefix + "_coverage", "raw HSP fractions." + axis + "_paired_coverage", "Copy raw paired units / raw reported length; invalid geometry remains unavailable.", "reported " + axis + " length")
        define("hsp", "full_" + prefix + "_paired_coverage", "qualified pointer -> saved303 HSP fractions." + axis + "_paired_coverage", "Copy saved qualified fraction with its exact count and denominator. Unknown full length stays unavailable.", "qualified full " + axis + " length")
    define("hsp", "paired_identity", "counts.identical_pairs,denominators.paired_columns", "identical pairs / paired columns", "paired_columns")
    define("hsp", "alignment_identity", "counts.identical_pairs,denominators.alignment_columns,reported_percentages.identity_percent", "identical pairs / alignment columns, or qualified native percent/100 with unknown count denominator", "alignment_columns; null for percentage-only fallback")
    for name in ("query_paired_coverage", "reference_paired_coverage"):
        define("sequence_hit", name, "saved hit observed paired union and full coordinate_context", "Union width / full length only when all original HSP geometry is complete", "qualified full axis length")
    define("sequence_hit", "selected_query_coverage", "saved selected_query_coverage numerator,denominator,value", "Copy paired union intersected with explicit selection / selection width. No selected interval means unavailable.", "explicit selected interval width")
    for name, source, formula in (("maximum_bit_score", "HSP bit scores", "maximum native bit score"), ("minimum_evalue", "HSP E-values", "minimum native E-value"), ("hsp_count", "retained HSP components", "number of retained HSP representations"),
            ("observed_paired_query_positions", "qualified HSP pairs", "length of union of query intervals"), ("observed_paired_reference_positions", "qualified HSP pairs", "length of union of reference intervals"),
            ("unique_pair_count", "qualified HSP pairs", "count distinct(query_start,query_end,reference_start,reference_end,identical)"),
            ("identical_unique_pair_count", "distinct qualified HSP pair keys", "count identical keys"), ("overlap_pair_representations", "qualified HSP pairs and distinct keys", "number of pairs minus number of distinct keys")):
        define("sequence_hit", name, source, formula)
    define("sequence_group", "maximum_bit_score", "group native hit maximum scores", "maximum once per demonstrated or unresolved sequence group")
    define("sequence_group", "hit_representation_count", "group.hit_indices", "len(hit_indices)")
    define("sequence_group", "explicit_function_count", "group.functions", "len(distinct exact functions)")
    define("sequence_function", "function_mass", "group maximum bits b_g, function sets F_g, temperature T", "M_f=sum(2**((b_g-b*)/T)/len(F_g)); b* is maximum scored annotated-group bits")
    define("sequence_function", "function_prior", "function_weights.parameters.function_priors", "Copy normalized selected exact prior population")
    define("sequence_function", "unadjusted_probability", "function_weights.unadjusted_probabilities,priors,masses", "pi_f*M_f / sum_j(pi_j*M_j)", "sum(pi*M) for scored explicit functions")
    define("sequence_function", "representation_adjusted_probability", "qualified census N_f,priors,masses", "(pi_f*M_f/N_f) / sum_j(pi_j*M_j/N_j)", "sum(pi*M/N), actual matching census required")
    for name, formula in (("sequence_group_count", "count exact function-associated groups"), ("native_hit_count", "count hit representations in those groups"),
            ("maximum_bit_score", "maximum measured group bit score"), ("mean_bit_score", "arithmetic mean of measured group bit scores"), ("scored_group_count", "count groups with measured bit scores")):
        define("sequence_function", name, "saved303 function summary and exact group associations", formula)
    for name in ("database_sequence_count", "database_total_sequence_count"):
        define("sequence_population", name, "actual supplied database_profile function_counts,total_count", "Copy supplied census count; preserve count_unit, release, scope and qualification.", origin="supplied_source_record")
    define("sequence_population", "database_fraction", "database_sequence_count,database_total_sequence_count", "N_f/N_total", "actual supplied total_count")
    define("sequence_population", "observed_sequence_group_count", "returned exact function-associated groups", "count returned function groups; not database prevalence")
    for name, formula in (("same_taxon_pair_count", "sum_t n_t*(n_t-1)/2"), ("comparable_pair_count", "k*(k-1)/2 for k unambiguous groups"),
            ("same_taxon_pair_fraction", "same_taxon_pair_count/comparable_pair_count"), ("target_matching_fraction", "matching/(matching+conflicting)")):
        define("sequence_taxonomy", name, "saved per-rank exact group memberships and explicit target lineage", formula,
            "comparable_pair_count" if name == "same_taxon_pair_fraction" else "matching+conflicting" if name == "target_matching_fraction" else None)
    for name in out["sequence_taxonomy"]:
        if name.endswith("group_count") or name.startswith("target_") and name.endswith("groups"):
            define("sequence_taxonomy", name, "saved303 rank-qualified group memberships and target lineage", "Copy exact membership count; unknown and ambiguous groups remain separate, absent target stays null")
    for name in ("completeness_fraction", "contamination_fraction"):
        define("sequence_quality", name, "source reader's linked assembly " + name.replace("fraction", "percent"), "supplied percentage / 100 once at extraction; contamination may exceed 1", origin="supplied_source_record")
    for name in out["pssm_cell"]:
        define("pssm_cell", name, "native PSSM array with M rows,N positions,byRow", "raw[r*N+p] if byRow else raw[p*M+r]; require M*N; copy saved normalized array, never divide scores by scalingFactor", origin="native_report")
    for name in out["pssm_position"]:
        define("pssm_position", name, "native PSSM intermediateData." + name, "Copy existing N-vector decoding at original position; effective observations are not biological replicates", origin="native_report")
    return out


METRICS = _catalog()
FAMILIES = tuple(METRICS)


def standard_blast_database_metric_definitions() -> dict:
    return deepcopy(METRICS)


def _eligible(family, program):
    return program in PROGRAMS and (not family.startswith("pssm_") or program == "tblastn")


def _identity_schema(family):
    fields = dict(search_key=SEARCH_KEY_SCHEMA)
    if family in ("hsp", "sequence_hit"):
        fields = dict(row_key=deepcopy(ROW_KEY_SCHEMA))
        props = fields["row_key"]["properties"]
        props["description_ordinal"] = {"type": "null"}
        if family == "hsp": props["hsp_ordinal"] = I0
        else:
            props["hit_ordinal"], props["hsp_ordinal"] = I0, {"type": "null"}
    elif family == "sequence_group":
        fields["hit_ordinals"] = _array(I0, minItems=1, uniqueItems=True)
    elif family in ("sequence_function", "sequence_population"):
        fields["function"] = ENTITY
        if family == "sequence_population":
            fields["count_unit"] = {"enum": ["unique_sequences", "sequence_groups"]}
    elif family in ("sequence_taxonomy", "sequence_quality"):
        fields["function"] = _nullable(ENTITY)
        fields["rank" if family == "sequence_taxonomy" else "assembly_source"] = TOKEN if family == "sequence_taxonomy" else PROVENANCE_SCHEMA
    elif family.startswith("pssm_"):
        fields = dict(artifact_key=ARTIFACT, record_ordinal=I0)
        if family != "pssm_matrix": fields["position"] = I0
        if family == "pssm_cell": fields["residue_row"] = I0
    return _object(fields)


def _cell_schema(family, boolean=False):
    names = BOOLEANS.get(family, ()) if boolean else METRICS[family]
    fields = dict(name={"enum": list(names)} if names else {"not": {}},
        value={"type": ["boolean" if boolean else "number", "null"]}, status={"enum": list(STATUSES)},
        reason={"enum": [None, *REASONS]}, origin={"enum": list(ORIGINS)}, component_pointer=POINTER)
    if not boolean:
        units = sorted({v["units"] for m in METRICS.values() for v in m.values()} - {"query_unit", "reference_unit", "census_unit"} | {"aa", "nt", "sequence", "sequence_group"})
        fields.update(numerator={"type": ["number", "null"]}, denominator={"type": ["number", "null"]},
            unit={"enum": units}, complete={"type": ["boolean", "null"]})
    schema = _object(fields)
    schema["allOf"] = [{"if": {"properties": {"value": {"type": "null"}}},
        "then": {"properties": {"status": {"enum": ["unavailable", "incompatible"]}, "reason": {"enum": list(REASONS)}}},
        "else": {"properties": {"status": {"const": "available"}, "reason": {"type": "null"}}}}]
    if not boolean:
        dynamic = {"query_unit": ["aa", "nt"], "reference_unit": ["aa", "nt"], "census_unit": ["sequence", "sequence_group"]}
        schema["allOf"].extend({"if": {"properties": {"name": {"const": name}}}, "then": {"properties": {
            "unit": {"enum": dynamic.get(definition["units"], [definition["units"]])}}}} for name, definition in METRICS[family].items())
    return schema


def standard_blast_database_row_schema(family: str) -> dict:
    if family not in METRICS:
        raise ContractError(PREFIX + "family_invalid")
    context = dict(query_axis_kind={"enum": ["sequence", "pssm_master", None]}, reference_axis_kind={"const": "sequence"},
        stage={"enum": ["sequence_database", None]}, query_unit={"enum": ["aa", "nt"]}, reference_unit={"enum": ["aa", "nt"]}, alignment_unit={"enum": ["aa", "nt"]})
    if family == "sequence_population": context["count_unit"] = {"enum": ["unique_sequences", "sequence_groups"]}
    schema = _object(dict(schema={"const": PREFIX + "numeric_row_v1"}, family={"const": family},
        record_key=ROW_ID, calculation_id=SHA, identity=_identity_schema(family), program={"enum": [p for p in PROGRAMS if _eligible(family, p)]},
        context=_object(context), component_refs=_array(_object(dict(artifact_role={"enum": ["collection", "sheets", "calculations"]}, pointer=POINTER))),
        native_status={"enum": list(NATIVE_STATUSES)}, measurements=_array(_cell_schema(family)), booleans=_array(_cell_schema(family, True))))
    schema["allOf"] = []
    for program in PROGRAMS:
        units = dict(zip(("query_unit", "reference_unit", "alignment_unit"), UNITS[program]))
        cells = [{"if": {"properties": {"name": {"const": name}}}, "then": {"properties": {"unit": {"const": units[definition["units"]]}}}}
            for name, definition in METRICS[family].items() if definition["units"] in units]
        schema["allOf"].append({"if": {"properties": {"program": {"const": program}}}, "then": {"properties": {
            "context": {"properties": {k: {"const": unit} for k, unit in units.items()}}, "measurements": {"items": {"allOf": cells} if cells else {}}}}})
    if family.startswith("pssm_"):
        schema["properties"]["context"]["properties"].update(query_axis_kind={"const": "pssm_master"}, stage={"type": "null"})
    if family == "sequence_population":
        for kind, unit in (("unique_sequences", "sequence"), ("sequence_groups", "sequence_group")):
            schema["allOf"].append({"if": {"properties": {"identity": {"properties": {"count_unit": {"const": kind}}}}},
                "then": {"properties": {"context": {"properties": {"count_unit": {"const": kind}}}, "measurements": {"items": {
                    "if": {"properties": {"name": {"enum": ["database_sequence_count", "database_total_sequence_count"]}}},
                    "then": {"properties": {"unit": {"const": unit}}}}}}}})
    return deepcopy(schema)


FAILURE_SCHEMA = _object(dict(stage={"enum": "capture metadata inputs collection population calculation rows projection publication authority worker".split()},
    code={"enum": list(FAILURE_CODES)}, artifact_key=_nullable(TOKEN), input_key=_nullable(TOKEN),
    search_key=_nullable(_object(dict(artifact_key=TOKEN, member_ordinal=_nullable(I0), report_index=I0, search_pointer=POINTER))),
    record_key=_nullable(TOKEN), pointer=POINTER, detail_code={"enum": list(DETAIL_CODES)}))


def standard_blast_database_fact_sources() -> dict:
    result = {}
    for family in FAMILIES:
        name = "execution_blast_standard_database_" + family + "_rows"
        schema = standard_blast_database_row_schema(family)
        extra = dict(source_ref=REF, observation_ref=_nullable(REF), subject_ref=_nullable({**REF, "x-reference-namespace": "subject"}),
            reference_refs=_array(REF, uniqueItems=True), publication_status={"enum": ["published", "source_only", "invalid"]})
        schema["properties"].update(extra); schema["required"].extend(extra)
        result[name] = dict(type="array", meaning="Requested frozen " + family + " measurements with original identities, units and qualified missingness.",
            report_schema={**_array(schema, uniqueItems=True), "x-source": name, "x-unique-by": ["calculation_id", "record_key"]})
    for suffix, schema in (("result_refs", _array(REF, uniqueItems=True)), ("failures", _array(FAILURE_SCHEMA)),
            ("acquisition", _object({k: {"type": "boolean"} for k in ("acquisition_complete", "projection_complete", "native_execution_successful", "complete")}))):
        name = "execution_blast_standard_database_" + suffix
        result[name] = dict(type=schema["type"], meaning="Frozen standard database result " + suffix + ".", report_schema={**schema, "x-source": name})
    return deepcopy(result)


def _selector_schema(program):
    identity = dict(artifact_ref=REF, sha256=SHA, size_bytes=I0)
    return _object(dict(version={"const": PREFIX + "selector_v1"}, acquisition={"const": "complete_bound_bundle"},
        metadata_inputs=_array(_object(dict(input_key=TOKEN, consumer={"enum": ["query_identity", "sequence_database"]},
            schema_id={"enum": ["native_blast_database_query_metadata_v1", "native_blast_database_sequence_metadata_v1"]}, **identity))),
        retained_sources=_array(_object(dict(source_ref=REF, **identity))),
        projections=_array({"oneOf": [_object(dict(family={"const": family},
            rows={"oneOf": [_object(dict(offset=I0, limit={"type": "integer", "minimum": 1})), _object(dict(record_keys=_array(ROW_ID, minItems=1, uniqueItems=True)))]},
            metrics=_array({"enum": list(METRICS[family])}, uniqueItems=True),
            booleans=_array({"enum": list(BOOLEANS[family])} if BOOLEANS.get(family) else {"not": {}}, uniqueItems=True)))
            for family in FAMILIES if _eligible(family, program)]}, minItems=1)))


def validate_standard_blast_database_selector(selector: dict, *, program: str) -> dict:
    selector = _copy(selector)
    if program not in PROGRAMS:
        raise ContractError(PREFIX + "program_unsupported")
    try:
        validate_schema(selector, _selector_schema(program))
        projections = selector["projections"]
        if len({p["family"] for p in projections}) != len(projections): raise ValueError("duplicate_family")
        for p in projections:
            if not p["metrics"] and not p["booleans"]: raise ValueError("empty_metrics")
            if "offset" in p["rows"] and any(type(v) is not int for v in p["rows"].values()): raise ValueError("integer_required")
        seen, identities = set(), {}
        for row in selector["metadata_inputs"]:
            key = row["input_key"], row["consumer"], row["schema_id"]
            expected = "native_blast_database_" + ("query" if row["consumer"] == "query_identity" else "sequence") + "_metadata_v1"
            if key in seen or row["schema_id"] != expected: raise ValueError("metadata_tuple_invalid")
            seen.add(key)
            value = tuple(row[k] for k in ("artifact_ref", "sha256", "size_bytes"))
            if row["input_key"] in identities and identities[row["input_key"]] != value: raise ValueError("metadata_identity_conflict")
            identities[row["input_key"]] = value
        sources = selector["retained_sources"]
        if len({r["source_ref"] for r in sources}) != len(sources): raise ValueError("duplicate_source")
        if any(type(r["size_bytes"]) is not int for r in sources + selector["metadata_inputs"]): raise ValueError("integer_required")
    except (ValueError, TypeError, KeyError) as error:
        raise ContractError(PREFIX + "selector_invalid") from error
    return selector


def _validate_row(row, calculation_id, *, full=True):
    family = row.get("family") if type(row) is dict else None
    validate_schema(row, standard_blast_database_row_schema(family))
    if row["calculation_id"] != calculation_id: raise ContractError(PREFIX + "calculation_identity_conflict")
    if tuple(row["context"][k] for k in ("query_unit", "reference_unit", "alignment_unit")) != UNITS[row["program"]]:
        raise ContractError(PREFIX + "coordinate_unit_conflict")
    for field, names in (("measurements", METRICS[family]), ("booleans", BOOLEANS.get(family, ()))):
        actual = [c["name"] for c in row[field]]
        if len(set(actual)) != len(actual) or full and set(actual) != set(names): raise ContractError(PREFIX + "row_cells_invalid")
    integer_keys = {"report_index", "member_ordinal", "hit_ordinal", "hsp_ordinal", "description_ordinal", "record_ordinal", "position", "residue_row"}
    def check(value):
        if type(value) is dict:
            for key, child in value.items():
                if key in integer_keys and child is not None and type(child) is not int: raise ContractError(PREFIX + "integer_required")
                if key == "hit_ordinals" and (any(type(i) is not int for i in child) or child != sorted(set(child))): raise ContractError(PREFIX + "row_identity_invalid")
                check(child)
        elif type(value) is list:
            for child in value: check(child)
    check(row["identity"])
    if family == "sequence_population" and row["identity"]["count_unit"] != row["context"]["count_unit"]: raise ContractError(PREFIX + "population_unit_conflict")
    for cell in row["measurements"]:
        unit = METRICS[family][cell["name"]]["units"]
        expected = row["context"].get(unit) if unit in ("query_unit", "reference_unit") else (
            "sequence" if row["context"].get("count_unit") == "unique_sequences" else "sequence_group") if unit == "census_unit" else unit
        if cell["unit"] != expected: raise ContractError(PREFIX + "cell_unit_conflict")
    return row


def project_standard_blast_database_rows(full_rows: list, *, selector: dict, calculation_id: str) -> dict:
    rows = _copy(full_rows)
    validate_schema(calculation_id, SHA)
    if type(rows) is not list: raise ContractError(PREFIX + "rows_required")
    programs = {r.get("program") for r in rows if type(r) is dict}
    if len(programs) > 1: raise ContractError(PREFIX + "row_program_conflict")
    if programs:
        selector = validate_standard_blast_database_selector(selector, program=next(iter(programs)))
    else:
        # The owning preparation separately binds the exact program, including
        # for a valid empty population. Validate the closed union here.
        selector = validate_standard_blast_database_selector(selector, program="tblastn")
    families, seen = {f: [] for f in FAMILIES}, set()
    for row in rows:
        _validate_row(row, calculation_id)
        if row["record_key"] in seen: raise ContractError(PREFIX + "row_identity_duplicate")
        seen.add(row["record_key"]); families[row["family"]].append(row)
    output, failures = [], []
    for pi, selection in enumerate(selector["projections"]):
        family, address = selection["family"], selection["rows"]
        population, next_offset = families[family], None
        if "record_keys" in address:
            lookup, selected = {r["record_key"]: r for r in population}, []
            for ri, key in enumerate(address["record_keys"]):
                if key in lookup: selected.append(lookup[key])
                else: failures.append(dict(stage="projection", code=PREFIX + "selector_unavailable", artifact_key=None,
                    input_key=None, search_key=None, record_key=key, pointer=f"/projections/{pi}/rows/record_keys/{ri}", detail_code="explicit_row_missing"))
        else:
            start, limit = address["offset"], address["limit"]
            selected = population[start:start + limit]
            if start + len(selected) < len(population): next_offset = start + len(selected)
        projected = []
        for row in selected:
            saved = deepcopy(row)
            for field, names in (("measurements", selection["metrics"]), ("booleans", selection["booleans"])):
                cells = {c["name"]: c for c in row[field]}
                saved[field] = [deepcopy(cells[name]) for name in names]
            projected.append(saved)
        output.append(dict(family=family, total_rows=len(population), selected_record_keys=[r["record_key"] for r in projected], next_offset=next_offset, rows=projected))
    return dict(schema=PREFIX + "projection_v1", calculation_id=calculation_id, families=output, failures=failures)


__all__ = ["standard_blast_database_metric_definitions", "standard_blast_database_row_schema",
    "standard_blast_database_fact_sources", "validate_standard_blast_database_selector", "project_standard_blast_database_rows", "FAILURE_SCHEMA"]
