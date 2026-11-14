"""Closed original selectors and plans for the two pure phylogeny adapters.

This module imports no parser or calculator. Metric names select fixed stored
Quantity cells; neither selectors nor references are an expression language.
References are scoped by the receiving publication and the encoded analysis.
"""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import quote, unquote

from .bvbrc_appservice_contracts import (
    ContractValidationError, _finite_json, _same, _Validator, contract_schema,
    validate_contract,
)

PARAMETERS_VERSION = "bvbrc_phylogeny_bundle_parameters_v1"
SUPPLIED_VERSION = "bvbrc_phylogeny_supplied_inputs_v1"
POPULATION_KEYS = ("alignments", "leaves", "composition", "taxonomy", "genomes", "families", "bootstraps", "native")
BRANCH_UNITS = ("expected_substitutions_per_model_site", "joint_mixed_partition_model_site", "native_unknown")
SUPPORT_METHODS = ("rapid_bootstrap", "rell_bootstrap", "phyml_abayes", "phyml_alrt_statistic", "phyml_chi2", "phyml_sh_like", "fasttree_sh_like", "native_unknown")
SUPPORT_SCALES = ("percent", "fraction", "statistic", "native_unknown")
COMPLETENESS = ("complete", "partial", "truncated", "unknown")
COMMON_CALCULATION_FIELDS = ("alignment_requests", "original_coverage_population_ids", "tree_requests", "bootstrap_requests", "composition_population_ids", "taxon_requests", "comparisons")
JOIN_KEYS = ("input_rows", "tip_rows", "feature_genomes", "functions", "function_equivalences", "taxa", "display_tips", "transformations", "residues", "organismal_tips")
GENE_DOCUMENT_FIELDS = ("aligned_document_id",)
CODON_DOCUMENT_FIELDS = ("final_alignment_id", "partition_document_id", "membership_document_id", "family_stats_document_id", "genome_counts_document_id", "analysis_stats_document_id", "bootstrap_tree_document_id")
GENE_TREE_FIELDS = ("raw_tree_id", "phyloxml_tree_id")
CODON_TREE_FIELDS = ("raw_tree_id", "supported_tree_id", "rooted_derivative_tree_id", "display_tree_id", "phyloxml_tree_id")
REFERENCE_KINDS = ("tree", "split", "alignment", "family", "feature", "genome", "population", "function", "comparison", "requirement", "role", "reason")


def require(condition, code="phylogeny_bundle_contract_invalid", path=""):
    if not condition:
        raise ContractValidationError(code, path)


def shape(value, keys, code="phylogeny_bundle_contract_invalid"):
    require(type(value) is dict and set(value) == set(keys), code)


def string(value, *, nullable=False):
    require(nullable and value is None or type(value) is str and bool(value))


def indices(value):
    require(type(value) is list and all(type(v) is int and v >= 0 for v in value) and len(value) == len(set(value)))


def strings(value):
    require(type(value) is list and all(type(v) is str and v for v in value) and len(value) == len(set(value)))


def evidences(value):
    require(type(value) is list)
    for row in value:
        validate_contract("SourceEvidence", row)


def slot_ref(value, *, tree=False, analysis_id=None, nullable=False):
    if nullable and value is None:
        return
    shape(value, ("analysis_id", "slot_id", "tree_index") if tree else ("analysis_id", "slot_id"), "phylogeny_slot_reference_invalid")
    string(value["analysis_id"]); string(value["slot_id"])
    require(analysis_id is None or value["analysis_id"] == analysis_id, "phylogeny_cross_analysis_reference")
    if tree:
        require(type(value["tree_index"]) is int and value["tree_index"] >= 0, "phylogeny_slot_reference_invalid")


def encode_reference(kind: str, analysis_id: str, identifier: str) -> str:
    """Encode a finite namespace and two exact UTF-8 identities.

    The outer returned row's source_ref supplies publication scope. A reference
    alone grants no right to read that publication or another analysis.
    """
    require(kind in REFERENCE_KINDS, "phylogeny_reference_kind_invalid")
    string(analysis_id); string(identifier)
    return "bvbrc_phylogeny_" + kind + ":" + quote(analysis_id, safe="-._~") + "/" + quote(identifier, safe="-._~")


def decode_reference(reference: str, *, expected_kind: str | None = None) -> tuple[str, str, str]:
    string(reference)
    prefix, separator, suffix = reference.partition(":")
    kind = prefix.removeprefix("bvbrc_phylogeny_")
    require(separator and prefix == "bvbrc_phylogeny_" + kind and kind in REFERENCE_KINDS,
            "phylogeny_reference_invalid")
    require(expected_kind is None or kind == expected_kind, "phylogeny_reference_kind_invalid")
    parts = suffix.split("/")
    require(len(parts) == 2, "phylogeny_reference_invalid")
    try:
        analysis, identifier = (unquote(part, encoding="utf-8", errors="strict") for part in parts)
    except UnicodeError as error:
        raise ContractValidationError("phylogeny_reference_invalid") from error
    require(encode_reference(kind, analysis, identifier) == reference, "phylogeny_reference_invalid")
    return kind, analysis, identifier


def validate_reader_spec(value, *, planned=True, analysis_id=None):
    require(type(value) is dict and type(value.get("reader")) is str, "phylogeny_reader_invalid")
    variants = {
        "newick": {"dialect": ("newick", "raxml_branch_labels", "bvbrc_double_quoted_names"), "allow_multiple": bool},
        "aligned_fasta": {"id_rule": ("first_whitespace_token",), "encoding": ("ascii", "utf-8")},
        "relaxed_phylip": {"layout": ("sequential", "interleaved"), "continuation_ids": ("absent", "repeated")},
        "raxml_partitions": {"alignment" if planned else "alignment_column_count": None},
        "phyloxml": {}, "raxml_run_log": {"dialect": ("raxml_8",)},
        "codon_membership": {"dialect": ("pgfams_legacy", "homologs_current")},
        "codon_family_statistics": {"dialect": ("current_missing_header_tab",)},
        "codon_genome_counts": {}, "codon_analysis_statistics": {"dialect": ("retained_current_source",)},
    }
    require(value["reader"] in variants, "phylogeny_reader_invalid")
    fields = variants[value["reader"]]
    shape(value, {"reader", *fields}, "phylogeny_reader_invalid")
    for name, allowed in fields.items():
        if name == "alignment":
            slot_ref(value[name], analysis_id=analysis_id)
        elif name == "alignment_column_count":
            require(type(value[name]) is int and value[name] >= 0, "phylogeny_reader_invalid")
        else:
            require(type(value[name]) is bool if allowed is bool else value[name] in allowed, "phylogeny_reader_invalid")
    return deepcopy(value)


def _population_plan(value, analysis_id):
    require(type(value) is dict and type(value.get("kind")) is str)
    kind = value["kind"]
    keys = {"whole_alignment": ("population_id", "alignment"),
        "alignment_subset": ("population_id", "alignment", "row_indices", "columns_0based", "completeness", "evidence"),
        "whole_tree": ("population_id", "tree"), "explicit": ("population", "population_type"),
        "bootstrap_forest": ("population_id", "forest", "expected_replicates", "expected_count_evidence")}
    require(kind in keys); shape(value, {"kind", *keys[kind]})
    if kind == "explicit":
        require(value["population_type"] in ("composition", "taxonomy", "genomes", "families"))
        require(type(value["population"]) is dict); string(value["population"].get("population_id"))
    else:
        string(value["population_id"])
        field = "tree" if kind == "whole_tree" else "forest" if kind == "bootstrap_forest" else "alignment"
        slot_ref(value[field], tree=kind == "whole_tree", analysis_id=analysis_id)
    if kind == "alignment_subset":
        indices(value["row_indices"]); indices(value["columns_0based"])
        require(value["completeness"] in COMPLETENESS); evidences(value["evidence"])
    if kind == "bootstrap_forest":
        require(value["expected_replicates"] is None or type(value["expected_replicates"]) is int and value["expected_replicates"] >= 0)
        evidences(value["expected_count_evidence"])


def _pairs(rows):
    require(type(rows) is list)
    for pair in rows:
        require(type(pair) is list and len(pair) == 2 and all(type(i) is int and i >= 0 for i in pair))
    require(len({tuple(pair) for pair in rows}) == len(rows))


def validate_calculation_parameters(value, *, provider, analysis_id):
    extra = ("literal_statistic_population_ids", "family_population_requests", "worst_sequence_population_id") if provider == "codon_tree" else ()
    shape(value, {"version", *COMMON_CALCULATION_FIELDS, *extra}, "phylogeny_calculation_plan_invalid")
    require(value["version"] == provider + "_components_v1", "phylogeny_calculation_plan_invalid")
    for key in COMMON_CALCULATION_FIELDS:
        require(type(value[key]) is list)
    for key in ("original_coverage_population_ids", "composition_population_ids"):
        strings(value[key])
    for row in value["alignment_requests"]:
        shape(row, ("population_id", "alphabet", "case_policy", "pairs")); string(row["population_id"])
        require(row["alphabet"] in ("dna", "rna", "protein", "unknown") and row["case_policy"] in ("uppercase", "literal")); _pairs(row["pairs"])
    for row in value["tree_requests"]:
        shape(row, ("population_id", "branch_unit", "pairs")); string(row["population_id"])
        require(row["branch_unit"] in BRANCH_UNITS); _pairs(row["pairs"])
    for row in value["taxon_requests"]:
        shape(row, ("population_id", "rank")); string(row["population_id"]); string(row["rank"])
    for row in value["comparisons"]:
        shape(row, ("comparison_id", "gene_tree_id", "organismal_tree_id", "tip_pairs")); string(row["comparison_id"])
        for key in ("gene_tree_id", "organismal_tree_id"):
            slot_ref(row[key], tree=True, analysis_id=analysis_id)
        require(type(row["tip_pairs"]) is list)
        for pair in row["tip_pairs"]:
            shape(pair, ("gene_tree_id", "gene_node_index", "organismal_tree_id", "organismal_node_index", "subject", "evidence"))
            for key in ("gene_tree_id", "organismal_tree_id"):
                slot_ref(pair[key], tree=True, analysis_id=analysis_id)
    for row in value["bootstrap_requests"]:
        shape(row, ("reference_tree_id", "replicate_population_id", "tip_join", "method"))
        slot_ref(row["reference_tree_id"], tree=True, analysis_id=analysis_id); string(row["replicate_population_id"])
        require(row["method"] in ("rapid_bootstrap", "rell_bootstrap"))
        shape(row["tip_join"], ("reference_tree_id", "mappings")); slot_ref(row["tip_join"]["reference_tree_id"], tree=True, analysis_id=analysis_id)
        require(type(row["tip_join"]["mappings"]) is list)
        for mapping in row["tip_join"]["mappings"]:
            shape(mapping, ("replicate_tree_id", "pairs")); slot_ref(mapping["replicate_tree_id"], tree=True, analysis_id=analysis_id)
            require(type(mapping["pairs"]) is list)
            for pair in mapping["pairs"]:
                shape(pair, ("reference_node_index", "replicate_node_index")); require(all(type(n) is int and n >= 0 for n in pair.values()))
    for field, key in (("alignment_requests", "population_id"), ("tree_requests", "population_id"), ("comparisons", "comparison_id")):
        strings([row[key] for row in value[field]])
    if provider == "codon_tree":
        strings(value["literal_statistic_population_ids"]); string(value["worst_sequence_population_id"], nullable=True)
        require(type(value["family_population_requests"]) is list)
        for row in value["family_population_requests"]:
            shape(row, ("family_population_id", "genome_population_id")); string(row["family_population_id"]); string(row["genome_population_id"])
    return deepcopy(value)


def validate_parameters(parameters, *, provider=None):
    _finite_json(parameters)
    shape(parameters, ("version", "artifact_selection", "analyses"), "phylogeny_parameters_invalid")
    require(parameters["version"] == PARAMETERS_VERSION and type(parameters["analyses"]) is list and bool(parameters["analyses"]), "phylogeny_parameters_invalid")
    ids = []
    for row in parameters["analyses"]:
        shape(row, ("analysis", "population_plans", "scientific_inputs", "read_parameters", "calculation_parameters"))
        analysis = row["analysis"]; require(type(analysis) is dict)
        inferred = "codon_tree" if analysis.get("mode") == "core_genome_codon_protein" else "gene_tree"
        require(provider is None or provider == inferred, "phylogeny_provider_mode_conflict")
        provider = inferred
        fields = (CODON_DOCUMENT_FIELDS + CODON_TREE_FIELDS + ("per_family_final_alignment_ids", "explicit_family_matrix_id")) if provider == "codon_tree" else (GENE_DOCUMENT_FIELDS + GENE_TREE_FIELDS + ("locus_ids",))
        shape(analysis, {"analysis_id", "mode", "native_engine_slots", "output_role_evidence", *fields}, "phylogeny_analysis_plan_invalid")
        aid = analysis["analysis_id"]; string(aid); ids.append(aid)
        require(analysis["mode"] in (("core_genome_codon_protein",) if provider == "codon_tree" else ("gene_tree", "concatenated_sequence_loci")))
        for field in CODON_DOCUMENT_FIELDS if provider == "codon_tree" else GENE_DOCUMENT_FIELDS:
            slot_ref(analysis[field], nullable=True, analysis_id=aid)
        for field in CODON_TREE_FIELDS if provider == "codon_tree" else GENE_TREE_FIELDS:
            slot_ref(analysis[field], tree=True, nullable=True, analysis_id=aid)
        if provider == "gene_tree":
            strings(analysis["locus_ids"])
            shape(row["read_parameters"], ("source_dialect", "raw_tree_required_for_branch_facts"))
            require(row["read_parameters"]["source_dialect"] == "retained_bvbrc_gene_tree" and type(row["read_parameters"]["raw_tree_required_for_branch_facts"]) is bool)
        else:
            string(analysis["explicit_family_matrix_id"], nullable=True)
            require(type(analysis["per_family_final_alignment_ids"]) is list)
            for ref in analysis["per_family_final_alignment_ids"]:
                slot_ref(ref, analysis_id=aid)
            shape(row["read_parameters"], ("source_dialect", "membership_dialect", "family_stats_dialect"))
            require(row["read_parameters"]["source_dialect"] == "retained_codon_trees" and row["read_parameters"]["membership_dialect"] in ("pgfams_legacy", "homologs_current") and row["read_parameters"]["family_stats_dialect"] in (None, "current_missing_header_tab"))
        require(type(analysis["native_engine_slots"]) is list)
        for ref in analysis["native_engine_slots"]:
            slot_ref(ref, analysis_id=aid)
        evidences(analysis["output_role_evidence"])
        if row["scientific_inputs"] is not None:
            validate_contract("SourceEvidence", row["scientific_inputs"])
        require(type(row["population_plans"]) is list)
        for plan in row["population_plans"]:
            _population_plan(plan, aid)
        plan_ids = [p["population"]["population_id"] if p["kind"] == "explicit" else p["population_id"] for p in row["population_plans"]]
        strings(plan_ids)
        validate_calculation_parameters(row["calculation_parameters"], provider=provider, analysis_id=aid)
    strings(ids)
    require(type(parameters["artifact_selection"]) is list)
    seen, roles = set(), set()
    for row in parameters["artifact_selection"]:
        shape(row, ("analysis_id", "slot_id", "role", "reader"))
        for key in ("analysis_id", "slot_id", "role"):
            string(row[key])
        key = (row["analysis_id"], row["slot_id"])
        require(row["analysis_id"] in ids and key not in seen and row["role"] not in roles, "phylogeny_slot_identity_conflict")
        seen.add(key); roles.add(row["role"])
        validate_reader_spec(row["reader"], analysis_id=row["analysis_id"])
        require(provider == "codon_tree" or not row["reader"]["reader"].startswith("codon_"), "phylogeny_reader_provider_conflict")
    error = next(_Validator(parameters_schema(provider=provider)).iter_errors(parameters), None)
    require(error is None, "phylogeny_parameters_invalid")
    return deepcopy(parameters)


# Every catalog row binds a fixed component collection/subcollection/Quantity.
# Selector keys are literal identity operands, never runtime paths or formulas.
SCALAR_CATALOG = {}


def _catalog(prefix, collection, fields, keys, *, nested=None, integers=()):
    for field in fields.split():
        SCALAR_CATALOG[prefix + field] = {"collection": collection, "nested": nested, "field": field,
            "kind": "integer" if field in integers else "number", "selector_keys": ("metric", "analysis_id", *keys)}


_catalog("alignment_", "alignments", "member_count site_count cell_count gap_cells gap_fraction canonical_cells canonical_fraction ambiguity_cells ambiguity_fraction stop_cells stop_fraction other_nongap_cells other_nongap_fraction", ("population_id",), integers=("member_count", "site_count", "cell_count", "gap_cells", "canonical_cells", "ambiguity_cells", "stop_cells", "other_nongap_cells"))
_catalog("site_", "alignments", "gap_count canonical_count ambiguity_count stop_count other_nongap_count gap_fraction canonical_fraction canonical_majority_fraction canonical_entropy_bits", ("population_id", "column_0based"), nested="sites", integers=("gap_count", "canonical_count", "ambiguity_count", "stop_count", "other_nongap_count"))
_catalog("row_", "alignments", "nongap_count matrix_occupancy", ("population_id", "row_index"), nested="rows", integers=("nongap_count",))
_catalog("pair_", "alignments", "identical_positions substitutions both_gap_positions a_gap_only_positions b_gap_only_positions unpaired_nongap_ambiguous_positions identity_fraction", ("population_id", "row_a", "row_b"), nested="pairs", integers=("identical_positions", "substitutions", "both_gap_positions", "a_gap_only_positions", "b_gap_only_positions", "unpaired_nongap_ambiguous_positions"))
_catalog("coverage_", "original_coverage", "original_length original_covered_positions original_member_coverage", ("population_id", "row_index", "input_binding_id", "member_id"), nested="rows", integers=("original_length", "original_covered_positions"))
_catalog("tree_", "trees", "tip_count internal_node_count rooted_representation_polytomies unrooted_degree_polytomies branch_length_sum known_branch_length_sum missing_branch_length_count", ("population_id", "tree"), integers=("tip_count", "internal_node_count", "rooted_representation_polytomies", "unrooted_degree_polytomies", "missing_branch_length_count"))
_catalog("branch_", "trees", "length support_rescaled", ("population_id", "tree", "node_index"), nested="branches")
SCALAR_CATALOG["tree_distance"] = {"collection": "trees", "nested": "distances", "field": "value", "kind": "number", "selector_keys": ("metric", "analysis_id", "population_id", "tree", "node_a", "node_b")}
_catalog("bootstrap_", "bootstrap", "supplied_replicates expected_replicates usable_replicates", ("population_id", "tree"), integers=("supplied_replicates", "expected_replicates", "usable_replicates"))
_catalog("bootstrap_split_", "bootstrap", "matches denominator frequency", ("population_id", "tree", "node_index"), nested="rows", integers=("matches", "denominator"))
_catalog("composition_", "composition", "total_members members_with_recorded_assignment members_without_recorded_assignment", ("population_id",), integers=("total_members", "members_with_recorded_assignment", "members_without_recorded_assignment"))
_catalog("function_", "composition", "assigned_members fraction_all fraction_recorded", ("population_id", "function_key"), nested="rows", integers=("assigned_members",))
_catalog("taxon_", "taxonomy", "known_members unknown_members distinct_known_taxa same_taxon_pairs known_taxon_pairs same_taxon_pair_fraction", ("population_id", "rank"), integers=("known_members", "unknown_members", "distinct_known_taxa", "same_taxon_pairs", "known_taxon_pairs"))
_catalog("taxon_", "taxonomy", "member_count", ("population_id", "rank", "taxon_id"), nested="rows", integers=("member_count",))
_catalog("comparison_", "comparisons", "matched_tips gene_splits organismal_splits shared_splits rf rf_fraction", ("comparison_id",), integers=("matched_tips", "gene_splits", "organismal_splits", "shared_splits", "rf"))
_catalog("literal_", "literal_statistics", "n_rows n_columns gaps gap_fraction literal_nongap_sum_squared_frequency literal_nongap_mean_squared_frequency native_family_ranking_score", ("population_id",), integers=("n_rows", "n_columns", "gaps"))
SCALAR_CATALOG["literal_sum_squared_frequency"] = SCALAR_CATALOG.pop("literal_literal_nongap_sum_squared_frequency")
SCALAR_CATALOG["literal_mean_squared_frequency"] = SCALAR_CATALOG.pop("literal_literal_nongap_mean_squared_frequency")
_catalog("literal_site_", "literal_statistics", "sum_squared_frequency", ("population_id", "column_0based"), nested="sites")
_catalog("literal_row_", "literal_statistics", "mean_log2_literal_frequency", ("population_id", "row_index"), nested="rows")
_catalog("family_", "family_populations", "population_genomes population_families", ("family_population_id", "genome_population_id"), integers=("population_genomes", "population_families"))
_catalog("family_", "family_populations", "present_genomes missing_genomes extra_copies presence_fraction native_initial_family_rank", ("family_population_id", "genome_population_id", "family_id"), nested="rows", integers=("present_genomes", "missing_genomes", "extra_copies", "native_initial_family_rank"))
_catalog("worst_sequence_", "worst_sequence_ratios", "mean", ("family_population_id", "genome_id"), nested="genome_means")
_catalog("worst_sequence_", "worst_sequence_ratios", "ratio", ("family_population_id", "family_id", "feature_id", "genome_id"), nested="rows")
_catalog("worst_sequence_family_", "worst_sequence_ratios", "maximum", ("family_population_id", "family_id"), nested="family_maxima")

ARRAY_CATALOG = {
    "branch_rows": ("branches", ("metric", "analysis_id", "population_id", "tree", "node_indices")),
    "site_rows": ("sites", ("metric", "analysis_id", "population_id", "columns_0based")),
    "family_membership_rows": ("family_membership", ("metric", "analysis_id", "family_ids")),
    "function_composition_rows": ("function_composition", ("metric", "analysis_id", "population_id")),
    "relationship_comparison": ("relationship_comparisons", ("metric", "analysis_id", "comparison_id")),
    "missing_requirements": ("requirements", ("metric",)),
    "qualifications": ("qualifications", ("metric", "analysis_id", "slot_id")),
}


def selector_kind(selection):
    _finite_json(selection)
    require(type(selection) is dict and type(selection.get("metric")) is str, "phylogeny_fact_selector_invalid")
    metric = selection["metric"]
    require(metric in SCALAR_CATALOG or metric in ARRAY_CATALOG, "phylogeny_fact_metric_unknown")
    spec = SCALAR_CATALOG.get(metric)
    kind, keys = (spec["kind"], spec["selector_keys"]) if spec else ARRAY_CATALOG[metric]
    shape(selection, keys, "phylogeny_fact_selector_invalid")
    for key in keys:
        item = selection[key]
        if key == "tree":
            slot_ref(item, tree=True, analysis_id=selection["analysis_id"])
        elif key in ("column_0based", "row_index", "row_a", "row_b", "node_index", "node_a", "node_b"):
            require(type(item) is int and item >= 0, "phylogeny_fact_selector_invalid")
        elif key in ("node_indices", "columns_0based"):
            indices(item)
        elif key == "family_ids":
            strings(item)
        else:
            string(item, nullable=key == "slot_id")
    return kind


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def parameters_schema(*, provider):
    """The closed original commissioning shape, without future artifact IDs.

    Shape is JSON Schema; cross-field identity/association checks remain in
    validate_parameters and the publication resolver. No defaults are inserted.
    """
    require(provider in ("gene_tree", "codon_tree"), "phylogeny_provider_invalid")
    text = {"type": "string", "minLength": 1}
    index = {"type": "integer", "minimum": 0}
    integer_array = {"type": "array", "items": index, "uniqueItems": True}
    string_array = {"type": "array", "items": text, "uniqueItems": True}
    evidence = {"$ref": "#/$defs/SourceEvidence"}
    evidence_array = {"type": "array", "items": evidence}
    completeness = {"enum": list(COMPLETENESS)}
    def nullable(schema):
        return {"anyOf": [schema, {"type": "null"}]}
    def array(schema, **kwargs):
        return {"type": "array", "items": schema, **kwargs}
    slot = _object({"analysis_id": text, "slot_id": text})
    tree = _object({"analysis_id": text, "slot_id": text, "tree_index": index})
    subject = _object({"kind": {"enum": ["input_member", "feature", "genome"]}, "id": text, "source_record_id": text})
    pair = {"type": "array", "prefixItems": [index, index], "minItems": 2, "maxItems": 2, "items": False}
    pairs = array(pair, uniqueItems=True)
    reader_variants = [
        _object({"reader": {"const": "newick"}, "dialect": {"enum": ["newick", "raxml_branch_labels", "bvbrc_double_quoted_names"]}, "allow_multiple": {"type": "boolean"}}),
        _object({"reader": {"const": "aligned_fasta"}, "id_rule": {"const": "first_whitespace_token"}, "encoding": {"enum": ["ascii", "utf-8"]}}),
        _object({"reader": {"const": "relaxed_phylip"}, "layout": {"enum": ["sequential", "interleaved"]}, "continuation_ids": {"enum": ["absent", "repeated"]}}),
        _object({"reader": {"const": "raxml_partitions"}, "alignment": slot}),
        _object({"reader": {"const": "phyloxml"}}),
        _object({"reader": {"const": "raxml_run_log"}, "dialect": {"const": "raxml_8"}}),
    ]
    if provider == "codon_tree":
        reader_variants += [
            _object({"reader": {"const": "codon_membership"}, "dialect": {"enum": ["pgfams_legacy", "homologs_current"]}}),
            _object({"reader": {"const": "codon_family_statistics"}, "dialect": {"const": "current_missing_header_tab"}}),
            _object({"reader": {"const": "codon_genome_counts"}}),
            _object({"reader": {"const": "codon_analysis_statistics"}, "dialect": {"const": "retained_current_source"}}),
        ]
    composition = {"population_id": text, "unit": {"enum": ["sequence_member", "feature"]},
        "member_subjects": array(subject), "assignment_completeness": completeness,
        "membership_completeness": completeness, "evidence": evidence_array}
    taxonomy = {**composition, "unit": {"enum": ["sequence_member", "feature", "genome"]}}
    genomes = {"population_id": text, "genome_ids": string_array,
        "stage": {"enum": ["requested_main", "requested_optional", "actually_forwarded_optional", "returned_family_records", "used_final_alignment", "used_final_tree"]},
        "completeness": completeness, "evidence": evidence_array}
    families = {"population_id": text, "family_ids": string_array, "stage": {"enum": ["returned", "eligible", "evaluated_pretrim", "selected"]},
        "completeness": completeness, "evidence": evidence_array}
    population_plans = [
        _object({"kind": {"const": "whole_alignment"}, "population_id": text, "alignment": slot}),
        _object({"kind": {"const": "alignment_subset"}, "population_id": text, "alignment": slot, "row_indices": integer_array,
                 "columns_0based": integer_array, "completeness": completeness, "evidence": evidence_array}),
        _object({"kind": {"const": "whole_tree"}, "population_id": text, "tree": tree}),
        _object({"kind": {"const": "bootstrap_forest"}, "population_id": text, "forest": slot,
                 "expected_replicates": nullable(index), "expected_count_evidence": evidence_array}),
    ]
    for kind, fields in (("composition", composition), ("taxonomy", taxonomy), ("genomes", genomes), ("families", families)):
        population_plans.append(_object({"kind": {"const": "explicit"}, "population_type": {"const": kind}, "population": _object(fields)}))
    tip_pair = _object({"gene_tree_id": tree, "gene_node_index": index, "organismal_tree_id": tree,
        "organismal_node_index": index, "subject": subject, "evidence": evidence_array})
    replicate_pairs = array(_object({"reference_node_index": index, "replicate_node_index": index}))
    bootstrap_join = _object({"reference_tree_id": tree, "mappings": array(_object({"replicate_tree_id": tree, "pairs": replicate_pairs}))})
    calculation = {"version": {"const": provider + "_components_v1"},
        "alignment_requests": array(_object({"population_id": text, "alphabet": {"enum": ["dna", "rna", "protein", "unknown"]},
                                             "case_policy": {"enum": ["uppercase", "literal"]}, "pairs": pairs})),
        "tree_requests": array(_object({"population_id": text, "branch_unit": {"enum": list(BRANCH_UNITS)}, "pairs": pairs})),
        "original_coverage_population_ids": string_array, "composition_population_ids": string_array,
        "taxon_requests": array(_object({"population_id": text, "rank": text})),
        "bootstrap_requests": array(_object({"reference_tree_id": tree, "replicate_population_id": text,
            "tip_join": bootstrap_join, "method": {"enum": ["rapid_bootstrap", "rell_bootstrap"]}})),
        "comparisons": array(_object({"comparison_id": text, "gene_tree_id": tree, "organismal_tree_id": tree, "tip_pairs": array(tip_pair)}))}
    if provider == "codon_tree":
        calculation.update(literal_statistic_population_ids=string_array,
            family_population_requests=array(_object({"family_population_id": text, "genome_population_id": text})),
            worst_sequence_population_id=nullable(text))
    analysis = {"analysis_id": text, "mode": {"enum": ["core_genome_codon_protein"] if provider == "codon_tree" else ["gene_tree", "concatenated_sequence_loci"]},
        "native_engine_slots": array(slot), "output_role_evidence": evidence_array}
    analysis.update({field: nullable(slot) for field in CODON_DOCUMENT_FIELDS if provider == "codon_tree"})
    if provider == "gene_tree":
        analysis.update(aligned_document_id=nullable(slot), locus_ids=string_array)
        reads = _object({"source_dialect": {"const": "retained_bvbrc_gene_tree"}, "raw_tree_required_for_branch_facts": {"type": "boolean"}})
    else:
        analysis.update(per_family_final_alignment_ids=array(slot), explicit_family_matrix_id=nullable(text))
        reads = _object({"source_dialect": {"const": "retained_codon_trees"}, "membership_dialect": {"enum": ["pgfams_legacy", "homologs_current"]},
                         "family_stats_dialect": {"enum": [None, "current_missing_header_tab"]}})
    analysis.update({field: nullable(tree) for field in (CODON_TREE_FIELDS if provider == "codon_tree" else GENE_TREE_FIELDS)})
    schema = _object({"version": {"const": PARAMETERS_VERSION}, "artifact_selection": array(_object({
        "analysis_id": text, "slot_id": text, "role": text, "reader": {"oneOf": reader_variants}})),
        "analyses": array(_object({"analysis": _object(analysis), "population_plans": array({"oneOf": population_plans}),
            "scientific_inputs": nullable(evidence), "read_parameters": reads, "calculation_parameters": _object(calculation)}), minItems=1)})
    schema["$defs"] = contract_schema("SourceEvidence")["$defs"]
    return deepcopy(schema)


_STR = {"type": "string", "minLength": 1}
_INT = {"type": "integer"}
_NI = {"type": ["integer", "null"]}
_NN = {"type": ["number", "null"]}
_NS = {"type": ["string", "null"]}
_ARRAY_ITEMS = {
    "branches": _object({"tree_ref": _STR, "node_index": _INT, "split_ref": _NS, "length": _NN, "length_unit": {"enum": list(BRANCH_UNITS)}, "support_value": _NN, "support_method": {"enum": list(SUPPORT_METHODS)}, "support_scale": {"enum": list(SUPPORT_SCALES)}, "bootstrap_matches": _NI, "bootstrap_replicates": _NI}),
    "sites": _object({"alignment_ref": _STR, "column_0based": _INT, "n_rows": _INT, "gap_count": _INT, "canonical_count": _NI, "ambiguity_count": _NI, "canonical_majority_fraction": _NN, "canonical_entropy_bits": _NN}),
    "family_membership": _object({"family_ref": _STR, "representation": {"enum": ["protein", "coding_nucleotide"]}, "feature_ref": _STR, "genome_ref": _NS, "alignment_row_index": _NI, "inclusion_stage": {"enum": ["requested", "returned", "eligible", "evaluated_pretrim", "selected", "final_protein", "final_coding_nucleotide", "final_matrix", "final_tree"]}}),
    "function_composition": _object({"population_ref": _STR, "function_ref": _STR, "assigned_members": _INT, "total_members": _INT, "members_with_recorded_assignment": _INT, "fraction_all": _NN, "fraction_recorded": _NN}),
    "relationship_comparisons": _object({"comparison_ref": _STR, "matched_tips": _INT, "gene_splits": _INT, "organismal_splits": _INT, "shared_splits": _INT, "rf": _INT, "rf_fraction": _NN}),
    "qualifications": _object({"code": _STR, "phase": {"enum": ["custody", "prepare", "transport", "native_decode", "association", "publication", "recovery", "return"]}, "severity": {"enum": ["error", "qualification"]}, "role_ref": _NS, "requirement_refs": {"type": "array", "items": _STR}}),
}


# Actual declared/emitted diagnostics only. Unknown retained diagnostics use
# the finite fallback during projection; their exact saved originals survive.
QUALIFICATION_CODES = frozenset(('bvbrc_phylogeny_bootstrap_method_conflict',
 'bvbrc_phylogeny_bootstrap_method_unresolved',
 'bvbrc_phylogeny_branch_unit_conflict',
 'bvbrc_phylogeny_branch_unit_unresolved',
 'bvbrc_phylogeny_extraction_operand_invalid',
 'bvbrc_phylogeny_negative_branch_length',
 'bvbrc_phylogeny_observed_alphabet_conflict',
 'bvbrc_phylogeny_observed_settings_conflict',
 'bvbrc_phylogeny_original_coordinate_metadata_incomplete',
 'bvbrc_phylogeny_original_member_associations_incomplete',
 'bvbrc_phylogeny_requested_alphabet_unverified',
 'bvbrc_phylogeny_requested_observed_setting_conflict',
 'bvbrc_phylogeny_xml_converter_zero_and_support_loss',
 'bvbrc_phylogeny_xml_raw_tree_unavailable',
 'codon_analysis_expected_field_missing',
 'codon_artifact_invalid',
 'codon_bad_sequence_duplicate_key',
 'codon_bad_sequence_map_invalid',
 'codon_boolean_invalid',
 'codon_boolean_missing',
 'codon_command_tokenization_failed',
 'codon_conflicting_analysis_field',
 'codon_conflicting_family_record',
 'codon_conflicting_genome_record',
 'codon_conflicting_membership_record',
 'codon_conflicting_missing_family',
 'codon_conflicting_qualifier',
 'codon_count_stage_order_conflict',
 'codon_data_type_invalid',
 'codon_dialect_unsupported',
 'codon_duplicate_analysis_field',
 'codon_duplicate_family_record',
 'codon_duplicate_feature_id',
 'codon_duplicate_genome_record',
 'codon_duplicate_membership_record',
 'codon_duplicate_missing_family',
 'codon_duplicate_qualifier',
 'codon_empty_input',
 'codon_hash_mismatch',
 'codon_header_incompatible',
 'codon_header_missing_tab',
 'codon_malformed_row',
 'codon_membership_feature_overlap',
 'codon_membership_marker_family_mismatch',
 'codon_missing_family_mismatch',
 'codon_native_count_invalid',
 'codon_native_number_invalid',
 'codon_native_number_missing',
 'codon_no_complete_records',
 'codon_orphan_missing_family',
 'codon_orphan_qualifier',
 'codon_provider_family_namespace_required',
 'codon_provider_feature_genome_association_required',
 'codon_provider_final_family_coordinates_required',
 'codon_provider_genome_row_association_required',
 'codon_provider_genome_tip_association_required',
 'codon_provider_member_genome_association_required',
 'codon_provider_model_record_conflict',
 'codon_provider_model_sample_correspondence_required',
 'codon_provider_native_membership_conflict',
 'codon_provider_native_membership_unique_projection',
 'codon_provider_native_stage_conflict',
 'codon_provider_operand_invalid',
 'codon_provider_optional_forwarding_required',
 'codon_provider_partition_model_association_required',
 'codon_provider_requested_genome_membership_required',
 'codon_reported_cds_uses_protein_count',
 'codon_reported_command_role_unknown',
 'codon_truncated_line',
 'codon_uninterpreted_report_row',
 'codon_unknown_disqualification',
 'codon_unknown_membership_marker',
 'codon_unpaired_family_line',
 'codon_unrecognized_row',
 'codon_utf8_invalid',
 'duplicate_artifact_representation',
 'gene_tree_analysis_loci_invalid',
 'gene_tree_analysis_mode_invalid',
 'gene_tree_header_conflict',
 'gene_tree_locus_binding_conflict',
 'gene_tree_locus_binding_invalid',
 'gene_tree_locus_inclusion_conflict',
 'gene_tree_locus_join_conflict',
 'gene_tree_locus_member_unknown',
 'gene_tree_locus_membership_unknown',
 'gene_tree_locus_order_conflict',
 'gene_tree_locus_table_invalid',
 'gene_tree_primary_analysis_required',
 'output_association_unproven',
 'output_version_unproven',
 'phylogeny_adapter_operands_invalid',
 'phylogeny_alignment_label_missing',
 'phylogeny_alignment_lengths_unequal',
 'phylogeny_alignment_row_association_required',
 'phylogeny_alignment_symbol_invalid',
 'phylogeny_alignment_whitespace_ignored',
 'phylogeny_analysis_output_association_required',
 'phylogeny_artifact_ambiguous',
 'phylogeny_artifact_bytes_conflict',
 'phylogeny_artifact_bytes_missing',
 'phylogeny_artifact_invalid',
 'phylogeny_artifact_missing',
 'phylogeny_artifact_sha256_mismatch',
 'phylogeny_bootstrap_counts_unavailable',
 'phylogeny_bootstrap_population_incomplete',
 'phylogeny_branch_unit_unresolved',
 'phylogeny_bytes_required',
 'phylogeny_calculation_dependency_unavailable',
 'phylogeny_complete_object_required',
 'phylogeny_declared_format_conflict',
 'phylogeny_empty_input',
 'phylogeny_encoding_invalid',
 'phylogeny_family_membership_incomplete',
 'phylogeny_fasta_header_missing',
 'phylogeny_join_dependency_unavailable',
 'phylogeny_native_number_invalid',
 'phylogeny_native_support_conflict',
 'phylogeny_native_support_unavailable',
 'phylogeny_negative_branch_length',
 'phylogeny_newick_double_quote_dialect_required',
 'phylogeny_newick_multiple_disallowed',
 'phylogeny_newick_rooted_marker_conflict',
 'phylogeny_newick_syntax_invalid',
 'phylogeny_newick_truncated',
 'phylogeny_original_input_conflict',
 'phylogeny_original_map_incomplete',
 'phylogeny_original_task_conflict',
 'phylogeny_parser_declaration_conflict',
 'phylogeny_partition_alignment_required',
 'phylogeny_partition_holes',
 'phylogeny_partition_out_of_bounds',
 'phylogeny_partition_overlap',
 'phylogeny_partition_range_invalid',
 'phylogeny_partition_syntax_invalid',
 'phylogeny_phylip_block_width_mismatch',
 'phylogeny_phylip_column_count_mismatch',
 'phylogeny_phylip_continuation_id_mismatch',
 'phylogeny_phylip_header_invalid',
 'phylogeny_phylip_row_count_mismatch',
 'phylogeny_phylip_trailing_data',
 'phylogeny_phylip_truncated',
 'phylogeny_phyloxml_branch_length_multiple',
 'phylogeny_phyloxml_dtd_forbidden',
 'phylogeny_phyloxml_element_uninterpreted',
 'phylogeny_phyloxml_namespace_unsupported',
 'phylogeny_phyloxml_nested_scalar',
 'phylogeny_phyloxml_root_clade_invalid',
 'phylogeny_phyloxml_root_invalid',
 'phylogeny_phyloxml_rooted_attribute_invalid',
 'phylogeny_phyloxml_syntax_invalid',
 'phylogeny_phyloxml_trees_missing',
 'phylogeny_phyloxml_truncated',
 'phylogeny_population_unavailable',
 'phylogeny_provider_calculation_invalid',
 'phylogeny_provider_extraction_invalid',
 'phylogeny_quantity_denominator_empty',
 'phylogeny_quantity_failed',
 'phylogeny_quantity_incompatible',
 'phylogeny_quantity_missing',
 'phylogeny_quantity_not_measured',
 'phylogeny_quantity_truncated',
 'phylogeny_reader_parameter_invalid',
 'phylogeny_requested_component_unavailable',
 'phylogeny_requested_member_unavailable',
 'phylogeny_scientific_inputs_required',
 'phylogeny_selected_document_unavailable',
 'phylogeny_selected_tree_unavailable',
 'phylogeny_supplied_document_invalid',
 'phylogeny_supplied_inputs_invalid',
 'phylogeny_unregistered_diagnostic',
 'raxml_artifact_hash_conflict',
 'raxml_artifact_invalid',
 'raxml_branch_optimization_conflict',
 'raxml_command_missing',
 'raxml_command_tokens_invalid',
 'raxml_dialect_unsupported',
 'raxml_encoding_invalid',
 'raxml_log_completion_unproven',
 'raxml_measurement_syntax_invalid',
 'raxml_multiple_invocations_unassociated',
 'raxml_numeric_range_invalid',
 'raxml_numeric_token_invalid',
 'raxml_parameter_partition_missing',
 'raxml_parameter_repeated',
 'raxml_parameter_syntax_invalid',
 'raxml_partition_association_conflict',
 'raxml_partition_datatype_unknown',
 'raxml_partition_header_unassociated',
 'raxml_partition_repeated',
 'raxml_partition_syntax_invalid',
 'raxml_version_conflict',
 'raxml_version_missing',
 'raxml_version_unsupported',
 'supplemental_native_content_conflict',
 'supplemental_native_content_required',
 'supplemental_parsed_claim_conflict'))
_ARRAY_ITEMS["qualifications"]["properties"]["code"] = {"enum": sorted(QUALIFICATION_CODES)}


def requested_form_schema(fields):
    _finite_json(fields)
    require(type(fields) is dict and fields and all(type(k) is str and k for k in fields), "phylogeny_requested_form_invalid")
    properties = {}
    for name, selection in fields.items():
        kind = selector_kind(selection)
        if kind == "requirements":
            node = {"type": "array", "items": contract_schema("AcquisitionRequirement")["$defs"]["AcquisitionRequirement"]}
        elif kind in ("integer", "number"):
            node = {"type": [kind, "null"]}
        else:
            node = {"type": "array" if kind == "qualifications" else ["array", "null"], "items": deepcopy(_ARRAY_ITEMS[kind])}
        properties[name] = {**node, "x-phylogeny-fact": deepcopy(selection)}
    return _object(properties)


def validate_requested_form(requested_form):
    _finite_json(requested_form)
    shape(requested_form, ("type", "properties", "required", "additionalProperties"), "phylogeny_requested_form_invalid")
    require(type(requested_form["properties"]) is dict, "phylogeny_requested_form_invalid")
    selections = {}
    for name, node in requested_form["properties"].items():
        require(type(node) is dict and "x-phylogeny-fact" in node, "phylogeny_fact_selector_required")
        selections[name] = node["x-phylogeny-fact"]
    expected = requested_form_schema(selections)
    strings(requested_form["required"])
    require(set(requested_form["required"]) == set(selections), "phylogeny_requested_form_invalid")
    expected["required"] = requested_form["required"]
    require(_same(expected, requested_form), "phylogeny_requested_form_invalid")
    return deepcopy(requested_form)


__all__ = ["SCALAR_CATALOG", "ARRAY_CATALOG", "QUALIFICATION_CODES", "selector_kind", "requested_form_schema", "validate_requested_form", "parameters_schema", "validate_parameters", "encode_reference", "decode_reference"]
