"""Saved phylogeny values and real immediate-child typed-return records.

Publication and saved-sheet values are controlled fixtures. Store, Journal,
EpisodeReceipts, original commissions and TypedReportContract are real. These
tests prove return/custody boundaries, not native science or a full Workflow.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from gene_annotation_episode.bvbrc_phylogeny_bundle_contracts import (
    SCALAR_CATALOG, encode_reference, requested_form_schema,
)
from gene_annotation_episode.bvbrc_phylogeny_returns import (
    BVBRCPhylogenyReturns, FACT_SOURCES, IDENTIFIER_NAMESPACES,
    phylogeny_fact_sources, project_phylogeny_facts, requested_sources,
)
from gene_annotation_episode.communication import form_with_facts, plain, validate_closed_schema, validate_form
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_custody import SavedRecords, selector


MEASUREMENTS, BRANCHES, SITES, MEMBERS, FUNCTIONS, COMPARISONS, REQUIREMENTS, QUALIFICATIONS = FACT_SOURCES
AID = "selected analysis / α"
TREE = "artifact_" + "a" * 64 + "#tree_document/tree/0"
ALIGNMENT = "artifact_" + "b" * 64 + "#alignment"


def ref(kind, identifier, aid=AID):
    return encode_reference(kind, aid, identifier)


def slot(name, *, tree=False):
    return {"analysis_id": AID, "slot_id": name, **({"tree_index": 0} if tree else {})}


SELECTIONS = {
    "tips": {"metric": "tree_tip_count", "analysis_id": AID, "population_id": "leaves", "tree": slot("tree", tree=True)},
    "negative": {"metric": "literal_row_mean_log2_literal_frequency", "analysis_id": AID, "population_id": "alignment", "row_index": 0},
    "zero": {"metric": "site_gap_count", "analysis_id": AID, "population_id": "alignment", "column_0based": 0},
    "missing": {"metric": "coverage_original_member_coverage", "analysis_id": AID, "population_id": "alignment", "row_index": 0, "input_binding_id": "input", "member_id": "member"},
    "edges": {"metric": "branch_rows", "analysis_id": AID, "population_id": "leaves", "tree": slot("tree", tree=True), "node_indices": [1, 2]},
    "columns": {"metric": "site_rows", "analysis_id": AID, "population_id": "alignment", "columns_0based": [0, 1]},
    "members": {"metric": "family_membership_rows", "analysis_id": AID, "family_ids": ["PGF_1"]},
    "functions": {"metric": "function_composition_rows", "analysis_id": AID, "population_id": "function_population"},
    "comparison": {"metric": "relationship_comparison", "analysis_id": AID, "comparison_id": "organismal"},
    "needs": {"metric": "missing_requirements"},
    "limitations": {"metric": "qualifications", "analysis_id": AID, "slot_id": "tree"},
}


def fact_form(*sources):
    properties = {"requested_" + str(i): phylogeny_fact_sources()[source]["report_schema"]
                  for i, source in enumerate(sources)}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def content(value, name="supplied"):
    raw = canonical(value).encode()
    sha = hashlib.sha256(raw).hexdigest()
    return {"source_ref": "source_" + digest([name, sha])[:24], "artifact_field": "artifact_ref",
        "artifact_ref": "artifact_" + sha, "sha256": sha, "byte_count": len(raw)}


def parameters():
    analysis = {"analysis_id": AID, "mode": "core_genome_codon_protein", "final_alignment_id": slot("alignment"),
        "raw_tree_id": slot("tree", tree=True), "native_engine_slots": [], "output_role_evidence": [],
        "per_family_final_alignment_ids": [], "explicit_family_matrix_id": None}
    analysis.update({key: None for key in ("partition_document_id", "supported_tree_id", "rooted_derivative_tree_id",
        "display_tree_id", "phyloxml_tree_id", "membership_document_id", "family_stats_document_id",
        "genome_counts_document_id", "analysis_stats_document_id", "bootstrap_tree_document_id")})
    calc = {"version": "codon_tree_components_v1", "alignment_requests": [{"population_id": "alignment", "alphabet": "dna", "case_policy": "literal", "pairs": [[0, 1]]}],
        "tree_requests": [{"population_id": "leaves", "branch_unit": "native_unknown", "pairs": [[1, 2]]}],
        "original_coverage_population_ids": ["alignment"], "composition_population_ids": ["function_population"],
        "taxon_requests": [{"population_id": "taxonomy", "rank": "species"}], "comparisons": [{"comparison_id": "organismal",
            "gene_tree_id": slot("tree", tree=True), "organismal_tree_id": slot("tree", tree=True), "tip_pairs": []}],
        "bootstrap_requests": [{"reference_tree_id": slot("tree", tree=True), "replicate_population_id": "bootstrap",
            "tip_join": {"reference_tree_id": slot("tree", tree=True), "mappings": []}, "method": "rapid_bootstrap"}],
        "literal_statistic_population_ids": ["alignment"], "family_population_requests": [{"family_population_id": "families", "genome_population_id": "genomes"}],
        "worst_sequence_population_id": "families"}
    populations = [{"kind": "whole_alignment", "population_id": "alignment", "alignment": slot("alignment")},
        {"kind": "whole_tree", "population_id": "leaves", "tree": slot("tree", tree=True)}]
    for kind, pid in (("composition", "function_population"), ("taxonomy", "taxonomy"), ("families", "families"), ("genomes", "genomes")):
        population = {"population_id": pid, "evidence": []}
        if kind in {"composition", "taxonomy"}:
            population.update(unit="feature", member_subjects=[{"kind": "feature", "id": "feature1", "source_record_id": "source1"},
                {"kind": "feature", "id": "feature2", "source_record_id": "source2"}], assignment_completeness="unknown", membership_completeness="complete")
        elif kind == "families":
            population.update(family_ids=["PGF_1"], stage="selected", completeness="complete")
        else:
            population.update(genome_ids=["genome1"], stage="requested_main", completeness="complete")
        populations.append({"kind": "explicit", "population_type": kind, "population": population})
    populations.append({"kind": "bootstrap_forest", "population_id": "bootstrap", "forest": slot("tree"), "expected_replicates": None, "expected_count_evidence": []})
    return {"version": "bvbrc_phylogeny_bundle_parameters_v1", "artifact_selection": [
        {"analysis_id": AID, "slot_id": "tree", "role": "raw_tree", "reader": {"reader": "newick", "dialect": "newick", "allow_multiple": False}},
        {"analysis_id": AID, "slot_id": "alignment", "role": "final_alignment", "reader": {"reader": "aligned_fasta", "id_rule": "first_whitespace_token", "encoding": "ascii"}}],
        "analyses": [{"analysis": analysis, "population_plans": populations, "scientific_inputs": None,
            "read_parameters": {"source_dialect": "retained_codon_trees", "membership_dialect": "homologs_current", "family_stats_dialect": None},
            "calculation_parameters": calc}]}


def saved_sheet():
    tree_artifact = {"raw_artifact_ref": TREE.split("#")[0], "source_ref": "source_" + "c" * 24, "sha256": "a" * 64}
    alignment_artifact = {"raw_artifact_ref": ALIGNMENT.split("#")[0], "source_ref": "source_" + "d" * 24, "sha256": "b" * 64}
    tree = {"tree_id": TREE, "document_id": TREE.rsplit("/tree/", 1)[0], "tree_index": 0,
        "nodes": [{"node_index": i, "parent_index": parent, "child_indices": children, "branch_length": length}
            for i, parent, children, length in ((0, None, [1, 4], None), (1, 0, [2, 3], -.125),
                (2, 1, [], 0.0), (3, 1, [], .2), (4, 0, [5, 6], .1), (5, 4, [], .3), (6, 4, [], .4))]}
    alignment = {"alignment_id": ALIGNMENT, "artifact": alignment_artifact, "observed_column_count": 2, "rows": [
        {"row_index": 0, "sequence": "A-"}, {"row_index": 1, "sequence": "AT"}]}
    sheet = {"tool": "C-L193-CodonTree", "schema_version": "bvbrc_codon_tree_sheet_v1", "mode": "core_genome_codon_protein",
        "documents": {"analyses": [{"analysis_id": AID}], "store": {
        "tree_documents": [{"document_id": tree["document_id"], "artifact": tree_artifact, "trees": [tree]}],
        "phyloxml": [], "alignments": [alignment], "native_tables": []}},
        "populations": {"leaves": [{"population_id": "leaves", "tree_id": TREE, "node_indices": [2, 3, 5, 6]}],
            "alignments": [{"population_id": "alignment", "alignment_id": ALIGNMENT, "row_indices": [0, 1], "columns_0based": [0, 1]}],
            "composition": [{"population_id": "function_population", "member_subjects": [{"id": "feature1"}, {"id": "feature2"}]}]},
        "families": [{"family_id": "PGF_1", "final_block_indices": [0, 1], "memberships": [
            {"representation": "protein", "feature_ids": ["feature1"]}, {"representation": "coding_nucleotide", "feature_ids": ["feature1"]}]}],
        "genomes": [{"genome_id": "genome1", "final_alignment_rows": [{"alignment_id": ALIGNMENT, "row_index": 0}]}],
        "joins": {"functions": [{"function_key": "enzyme / original label"}], "function_equivalences": [], "input_rows": [],
            "feature_genomes": [{"feature_id": "feature1", "genome_id": "genome1", "family_id": "PGF_1"}],
            "family_blocks": [{"family_id": "PGF_1", "alignment_id": ALIGNMENT, "representation": rep, "member_row_indices": [0]}
                for rep in ("protein", "coding_nucleotide")]}, "missing_requirements": []}
    selections = [{"analysis_id": AID, "slot_id": sid, "role": role, "state": "resolved",
        "artifact_refs": [tree_artifact if sid == "tree" else alignment_artifact],
        "acquisition_receipt_refs": [], "read_id": sid, "document_id": doc, "tree_ids": trees, "requirement_ids": []}
        for sid, role, doc, trees in (("tree", "raw_tree", tree["document_id"], [TREE]), ("alignment", "final_alignment", ALIGNMENT, []))]
    return {"schema_version": "bvbrc_phylogeny_sheet_set_v1", "tool": "C-L193-CodonTree", "selections": selections,
        "analyses": [{"analysis_id": AID, "status": "ok", "sheet": sheet, "diagnostics": [], "missing_requirements": []}]}


def projection(*, selections=None, values=None):
    selections = deepcopy(SELECTIONS if selections is None else selections)
    facts = {"tips": 4, "negative": -.5, "zero": 0, "missing": None,
        "edges": [{"tree_ref": ref("tree", TREE), "node_index": i,
            "split_ref": ref("split", TREE + "/split/2,3") if i == 1 else None,
            "length": length, "length_unit": "native_unknown", "support_value": support,
            "support_method": "native_unknown", "support_scale": "native_unknown",
            "bootstrap_matches": None, "bootstrap_replicates": None} for i, length, support in ((1, -.125, 0.0), (2, 0.0, None))],
        "columns": [{"alignment_ref": ref("alignment", ALIGNMENT), "column_0based": i, "n_rows": 2,
            "gap_count": gap, "canonical_count": 2 - gap, "ambiguity_count": 0,
            "canonical_majority_fraction": 1.0, "canonical_entropy_bits": 0.0} for i, gap in ((0, 0), (1, 1))],
        "members": [{"family_ref": ref("family", "PGF_1"), "representation": rep, "feature_ref": ref("feature", "feature1"),
            "genome_ref": ref("genome", "genome1"), "alignment_row_index": 0, "inclusion_stage": "final_" + rep}
            for rep in ("protein", "coding_nucleotide")],
        "functions": [{"population_ref": ref("population", "function_population"), "function_ref": ref("function", "enzyme / original label"),
            "assigned_members": 1, "total_members": 2, "members_with_recorded_assignment": 1, "fraction_all": .5, "fraction_recorded": 1.0}],
        "comparison": [{"comparison_ref": ref("comparison", "organismal"), "matched_tips": 4, "gene_splits": 1,
            "organismal_splits": 1, "shared_splits": 1, "rf": 0, "rf_fraction": 0.0}], "needs": [],
        "limitations": [{"code": "bvbrc_phylogeny_negative_branch_length", "phase": "native_decode", "severity": "qualification",
            "role_ref": ref("role", "raw_tree"), "requirement_refs": []}]}
    facts = {name: deepcopy((values or facts)[name]) for name in selections}
    selected = selector()
    selected.update(endpoint="requested_projection", adapter={"adapter_id": "bvbrc_codon_tree", "adapter_version": "1", "parameters": parameters()},
        requested_schema=requested_form_schema(selections))
    sheet = saved_sheet()
    bundle = content({"fixture": "retained controlled publication"}, "bundle")
    saved = {"adapter_id": "bvbrc_codon_tree", "adapter_version": "1", "status": "ok", "facts": facts,
        "sheet_content": content(sheet, "sheet"), "components_content": None, "missing_requirements": [], "diagnostics": []}
    return {"version": RESULT_VERSION, "reference": bundle["source_ref"], "source_ref": bundle["source_ref"],
        "record_refs": [bundle["source_ref"]], "publication": {"bundle_content": bundle,
            "result_record_refs": [bundle["source_ref"]], "adapter_result": saved},
        "publication_inputs": {"selector": selected, "adapter": deepcopy(selected["adapter"])}}, sheet


def all_facts(body, sheet):
    return project_phylogeny_facts(body, requested_sources=FACT_SOURCES, sheet_set=sheet)


def numbers(facts):
    return {row["field"]: row["value"] for row in facts[MEASUREMENTS]}


def forbid_acquisition_or_scientific_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved return attempted acquisition, parsing, calculation or execution")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    import importlib
    targets = {
        "phylogeny_formats": ["parse_newick", "parse_aligned_fasta", "parse_relaxed_phylip", "parse_phyloxml"],
        "phylogeny_calculators": ["alignment_components", "tree_components", "function_composition", "compare_unrooted_relationships"],
        "bvbrc_gene_tree_inputs": ["extract_gene_tree_sheet"], "bvbrc_codon_tree_inputs": ["extract_codon_tree_sheet"],
        "bvbrc_gene_tree_grader": ["calculate_gene_tree"], "bvbrc_codon_tree_grader": ["calculate_codon_tree"],
        "bvbrc_gene_tree_bundle_adapter": ["consume_bundle"], "bvbrc_codon_tree_bundle_adapter": ["consume_bundle"],
        "bvbrc_phylogeny_bundle_resolution": ["parse_reader"], "bvbrc_phylogeny_bundle_projection": ["consume_bundle"],
    }
    # Import every target before replacing functions: imported aliases must
    # not retain a temporary forbidden function after pytest restores patches.
    loaded = {name: importlib.import_module("gene_annotation_episode." + name) for name in targets}
    for module_name, names in targets.items():
        module = loaded[module_name]
        for name in names:
            monkeypatch.setattr(module, name, forbidden)


@pytest.fixture(autouse=True)
def no_acquisition_or_scientific_work(monkeypatch, request):
    # These two cases first produce genuine parser/calculator output from
    # synthetic supplied bytes, then disable all scientific work before reads.
    if not request.node.name.startswith("test_real_provider_output_is_forwarded"):
        forbid_acquisition_or_scientific_work(monkeypatch)


def test_all_eight_closed_families_preserve_saved_numbers_and_references():
    body, sheet = projection()
    original = deepcopy((body, sheet))
    facts = all_facts(body, sheet)
    assert numbers(facts) == {"tips": 4, "negative": -.5, "zero": 0, "missing": None}
    assert type(numbers(facts)["tips"]) is int
    assert facts[BRANCHES][0]["branches"][0]["length"] == -.125
    assert facts[SITES][0]["sites"][1]["gap_count"] == 1
    assert facts[MEMBERS][0]["members"][1]["representation"] == "coding_nucleotide"
    assert facts[FUNCTIONS][0]["functions"][0]["fraction_all"] == .5
    assert facts[COMPARISONS][0]["comparisons"][0]["rf"] == 0
    assert facts[REQUIREMENTS][0]["requirements"] == []
    assert facts[QUALIFICATIONS][0]["qualifications"][0]["role_ref"] == ref("role", "raw_tree")
    schema = validate_closed_schema(fact_form(*FACT_SOURCES))
    form = form_with_facts({}, schema, facts)
    assert validate_form(form, schema, lambda *_: True) == form
    assert (body, sheet) == original
    assert "documents" not in canonical(facts) and "sheet_content" not in canonical(facts)


def scalar_selection(metric, spec):
    defaults = {"analysis_id": AID, "population_id": "alignment", "tree": slot("tree", tree=True),
        "column_0based": 0, "row_index": 0, "row_a": 0, "row_b": 1, "node_index": 1, "node_a": 1, "node_b": 2,
        "input_binding_id": "input", "member_id": "member", "function_key": "enzyme / original label",
        "rank": "species", "taxon_id": "taxon1", "comparison_id": "organismal", "family_population_id": "families",
        "genome_population_id": "genomes", "family_id": "PGF_1", "feature_id": "feature1", "genome_id": "genome1"}
    defaults["population_id"] = {"trees": "leaves", "bootstrap": "bootstrap", "composition": "function_population",
        "taxonomy": "taxonomy"}.get(spec["collection"], "alignment")
    return {key: metric if key == "metric" else deepcopy(defaults[key]) for key in spec["selector_keys"]}


@pytest.mark.parametrize("metric", sorted(SCALAR_CATALOG))
def test_every_finite_scalar_selector_is_read_without_calculation(metric):
    spec = SCALAR_CATALOG[metric]
    selection = scalar_selection(metric, spec)
    value = 0 if spec["kind"] == "integer" else -.5
    body, sheet = projection(selections={"selected": selection}, values={"selected": value})
    assert numbers(all_facts(body, sheet)) == {"selected": value}
    body["publication"]["adapter_result"]["facts"]["selected"] = None
    assert numbers(all_facts(body, sheet)) == {"selected": None}


@pytest.mark.parametrize("field,source,key", [("edges", BRANCHES, "branches"), ("columns", SITES, "sites"),
    ("members", MEMBERS, "members"), ("functions", FUNCTIONS, "functions"), ("comparison", COMPARISONS, "comparisons")])
def test_missing_arrays_and_available_empty_arrays_differ(field, source, key):
    selections = {field: deepcopy(SELECTIONS[field])}
    for coordinate in ("node_indices", "columns_0based", "family_ids"):
        if coordinate in selections[field]:
            selections[field][coordinate] = []
    for value in (None, []):
        body, sheet = projection(selections=selections, values={field: value})
        facts = all_facts(body, sheet)
        assert facts[source] == [{"source_ref": body["source_ref"], "field": field, key: value}]


def test_failed_absent_facts_are_not_fabricated_nulls_and_unrequested_groups_do_not_expand():
    body, sheet = projection()
    assert project_phylogeny_facts(body, requested_sources=(), sheet_set=sheet) == {}
    values = project_phylogeny_facts(body, requested_sources=[MEASUREMENTS], sheet_set=sheet)
    assert set(values) == {MEASUREMENTS}
    body["publication"]["adapter_result"].update(status="failed", facts={})
    assert all_facts(body, sheet) == {source: [] for source in FACT_SOURCES}
    assert requested_sources(fact_form(SITES, BRANCHES, SITES)) == (SITES, BRANCHES)


@pytest.mark.parametrize("alter", [
    lambda b, s: b.update(source_ref="source_" + "f" * 24),
    lambda b, s: b["publication"]["bundle_content"].update(source_ref="source_" + "f" * 24),
    lambda b, s: b["publication"]["adapter_result"].update(adapter_id="bvbrc_homology"),
    lambda b, s: b["publication"]["adapter_result"].update(adapter_version="2"),
    lambda b, s: b["publication_inputs"]["selector"]["adapter"].update(adapter_id="bvbrc_gene_tree"),
    lambda b, s: b["publication"]["adapter_result"]["facts"].update(extra=42),
    lambda b, s: b["publication"]["adapter_result"]["facts"].pop("tips"),
    lambda b, s: b["publication_inputs"]["selector"]["requested_schema"]["properties"]["tips"].pop("x-phylogeny-fact"),
    lambda b, s: b["publication_inputs"]["selector"]["requested_schema"]["properties"]["tips"]["x-phylogeny-fact"].update(metric="arbitrary_expression"),
    lambda b, s: b["publication_inputs"]["selector"]["requested_schema"]["properties"]["tips"]["x-phylogeny-fact"].update(analysis_id="not_selected"),
    lambda b, s: b["publication_inputs"]["selector"]["requested_schema"]["properties"]["tips"].update(type=["number", "null"]),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["edges"][0].update(node_index=4),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["columns"][0].update(column_0based=1),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["columns"][0].update(n_rows=3),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["edges"][0].update(tree_ref=ref("tree", TREE, "foreign")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["edges"][0].update(tree_ref=ref("tree", "wrong tree")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["edges"][0].update(split_ref=ref("split", TREE + "/split/2,5")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["columns"][0].update(alignment_ref=ref("alignment", "wrong matrix")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["members"][0].update(family_ref=ref("family", "other_family")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["members"][0].update(feature_ref=ref("feature", "other_feature")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["members"][0].update(genome_ref=ref("genome", "other_genome")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["members"][0].update(alignment_row_index=9),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["functions"][0].update(population_ref=ref("population", "other_population")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["comparison"][0].update(comparison_ref=ref("comparison", "other_comparison")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["limitations"][0].update(role_ref=ref("role", "not_selected_role")),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["limitations"][0].update(code="unregistered_diagnostic_text"),
    lambda b, s: b["publication"]["adapter_result"]["facts"]["needs"].append({"requirement_id": "extra", "kind": "scientific_metadata", "role": None, "source_refs": [], "reason_code": "extra"}),
    lambda b, s: s["selections"][0].update(document_id="unbound_document"),
])
def test_source_schema_selector_and_scoped_relationship_tampering_is_rejected(alter):
    body, sheet = projection()
    alter(body, sheet)
    with pytest.raises(ValueError):
        all_facts(body, sheet)


@pytest.mark.parametrize("bad", [True, 4.0, "4", float("nan")])
def test_saved_integer_types_are_not_coerced(bad):
    body, sheet = projection()
    body["publication"]["adapter_result"]["facts"]["tips"] = bad
    with pytest.raises(ValueError):
        all_facts(body, sheet)


@pytest.mark.parametrize("bad", ["bvbrc_phylogeny_tree:a/b/c", "bvbrc_phylogeny_tree:%61/b", "bvbrc_phylogeny_tree:a/%ff",
    "bvbrc_phylogeny_tree:a/b%2fc", "bvbrc_phylogeny_tree:/b", "bvbrc_phylogeny_unknown:a/b"])
def test_noncanonical_or_unknown_reference_namespace_is_rejected(bad):
    body, sheet = projection()
    body["publication"]["adapter_result"]["facts"]["edges"][0]["tree_ref"] = bad
    with pytest.raises(ValueError):
        all_facts(body, sheet)


@pytest.mark.parametrize("selection_change,fact_change", [
    ({"tree": {"analysis_id": AID, "slot_id": "tree", "tree_index": 1}}, {}),
    ({"node_indices": [7, 2]}, {"node_index": 7}),
    ({"tree": {"analysis_id": AID, "slot_id": "alignment", "tree_index": 0}}, {}),
])
def test_branch_indices_must_resolve_in_the_original_selected_tree(selection_change, fact_change):
    body, sheet = projection()
    selected = body["publication_inputs"]["selector"]["requested_schema"]["properties"]["edges"]["x-phylogeny-fact"]
    selected.update(selection_change)
    body["publication"]["adapter_result"]["facts"]["edges"][0].update(fact_change)
    with pytest.raises(ValueError):
        all_facts(body, sheet)


def test_column_outside_selected_saved_population_is_rejected_even_if_schema_and_fact_agree():
    body, sheet = projection()
    body["publication_inputs"]["selector"]["requested_schema"]["properties"]["columns"]["x-phylogeny-fact"]["columns_0based"] = [9, 1]
    body["publication"]["adapter_result"]["facts"]["columns"][0]["column_0based"] = 9
    with pytest.raises(ValueError, match="column_outside_population"):
        all_facts(body, sheet)


def test_saved_tree_source_index_is_not_successful_array_position():
    body, sheet = projection()
    tree = sheet["analyses"][0]["sheet"]["documents"]["store"]["tree_documents"][0]["trees"][0]
    tree["tree_index"] = 2
    body["publication"]["adapter_result"]["sheet_content"] = content(sheet, "sparse-original-index")
    with pytest.raises(ValueError, match="saved_identity_required"):
        all_facts(body, sheet)


@pytest.mark.parametrize("alter", [
    lambda s: s["selections"][0].update(role="other_original_role"),
    lambda s: s["selections"][0].update(artifact_refs=[]),
    lambda s: s["selections"][1].update(artifact_refs=[]),
    lambda s: s["selections"][1].update(document_id="different_alignment"),
])
def test_authenticated_sheet_identity_must_still_match_original_slots(alter):
    body, sheet = projection()
    alter(sheet)
    body["publication"]["adapter_result"]["sheet_content"] = content(sheet, "inconsistent-saved-identities")
    with pytest.raises(ValueError):
        all_facts(body, sheet)


def test_family_row_integer_cannot_hide_two_distinct_alignment_rows():
    body, sheet = projection(selections={"members": SELECTIONS["members"]})
    provider = sheet["analyses"][0]["sheet"]
    block = {**provider["joins"]["family_blocks"][0], "alignment_id": "another_saved_alignment"}
    provider["joins"]["family_blocks"].append(block)
    provider["families"][0]["final_block_indices"].append(2)
    provider["genomes"][0]["final_alignment_rows"].append({"alignment_id": "another_saved_alignment", "row_index": 0})
    body["publication"]["adapter_result"]["sheet_content"] = content(sheet, "ambiguous-family-row")
    with pytest.raises(ValueError, match="saved_family_row_conflict"):
        all_facts(body, sheet)


def test_family_row_never_joins_an_input_member_to_feature_by_shared_label():
    body, sheet = projection(selections={"members": SELECTIONS["members"]})
    provider = sheet["analyses"][0]["sheet"]
    provider["genomes"][0]["final_alignment_rows"] = []
    provider["joins"]["input_rows"] = [{"input_binding_id": "unrelated-original-input", "member_id": "feature1",
        "alignment_id": ALIGNMENT, "row_index": 0}]
    body["publication"]["adapter_result"]["sheet_content"] = content(sheet, "same-label-no-association")
    with pytest.raises(ValueError, match="saved_family_row_conflict"):
        all_facts(body, sheet)


def test_qualification_keeps_canonical_requirement_scope_without_exposing_sheet():
    body, sheet = projection(selections={"limitations": SELECTIONS["limitations"]})
    row = body["publication"]["adapter_result"]["facts"]["limitations"][0]
    row["requirement_refs"] = [ref("requirement", "source requirement / 1")]
    assert all_facts(body, sheet)[QUALIFICATIONS][0]["qualifications"][0] == row
    row["requirement_refs"] = [ref("requirement", "source requirement / 1", "other analysis")]
    with pytest.raises(ValueError, match="reference_analysis_conflict"):
        all_facts(body, sheet)


def test_unavailable_analysis_can_return_qualifications_and_null_measurements():
    body, sheet = projection(selections={"tips": SELECTIONS["tips"], "limitations": SELECTIONS["limitations"]})
    body["publication"]["adapter_result"]["facts"]["tips"] = None
    body["publication"]["adapter_result"]["status"] = "partial"
    sheet["analyses"][0].update(status="invalid", sheet=None)
    body["publication"]["adapter_result"]["sheet_content"] = content(sheet, "unavailable-analysis")
    result = all_facts(body, sheet)
    assert numbers(result) == {"tips": None}
    assert result[QUALIFICATIONS][0]["qualifications"]


@pytest.mark.parametrize("field,value", [("schema_version", "wrong_sheet_v1"), ("mode", "gene_tree"), ("tool", "C-L194-GeneTree")])
def test_nonnull_scalar_needs_matching_saved_provider_sheet(field, value):
    body, sheet = projection(selections={"negative": SELECTIONS["negative"]})
    sheet["analyses"][0]["sheet"][field] = value
    body["publication"]["adapter_result"]["sheet_content"] = content(sheet, "wrong-inner-sheet")
    with pytest.raises(ValueError):
        all_facts(body, sheet)


class ControlledPublications:
    """Saved Store bytes with controlled publication envelope, never native proof."""
    def __init__(self, saved):
        self.saved, self.bodies, self.sheets = saved, {}, {}

    def add(self, context, body, sheet, *, index=0):
        body = deepcopy(body)
        binding = self.saved.source(canonical(sheet).encode(), provider=DATA_PROVIDER)
        body["publication"]["adapter_result"]["sheet_content"] = binding
        self.sheets[binding["source_ref"]] = binding
        bundle = self.saved.source(canonical({"body": body, "episode_id": context.episode_id, "action_index": index}).encode(), provider=DATA_PROVIDER)
        reference = bundle["source_ref"]
        body.update(reference=reference, source_ref=reference, record_refs=[reference], run_id=context.run_id,
            episode_id=context.episode_id, scope=plain(context.scope), assignment=plain(context.assignment))
        body["publication"].update(bundle_content=bundle, result_record_refs=[reference])
        self.bodies[reference] = body
        self.saved.own(context, reference, index, tool="api.bvbrc_appservice.download")
        return body

    def own_results(self, context):
        self.saved.custody.authenticate(context, allow_unsaved=True)
        rows = self.saved.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND result IS NOT NULL ORDER BY decision_index", (context.run_id, context.episode_id))
        return [ref for row in rows if (result := json.loads(row["result"]))["status"] in {"completed", "partial"}
            for ref in result["record_refs"] if ref in self.bodies]

    def read(self, reference, scope, *, episode_id=None):
        body = deepcopy(self.bodies[reference])
        context = self.saved.custody.context(body["episode_id"])
        assert episode_id is None or episode_id == context.episode_id
        self.saved.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        self.saved.custody.possession(context, reference)
        assert reference in self.own_results(context)
        return body

    def read_content_source(self, reference, scope):
        binding = self.sheets[reference]
        raw = self.saved.store.get_artifact(binding["artifact_ref"])
        assert hashlib.sha256(raw).hexdigest() == binding["sha256"]
        return json.loads(raw)


class ReturnFixture:
    def __init__(self, store):
        self.saved, self.store = SavedRecords(store), store
        self.publications = ControlledPublications(self.saved)
        self.api = SimpleNamespace(store=store, run_id=self.saved.run_id)
        self.api.appservice = SimpleNamespace(publications=self.publications, custody=self.saved.custody, resolve=self.resolve_source)
        self.host = BVBRCPhylogenyReturns(self.api)

    def resolve_source(self, context, reference, namespace):
        if namespace not in {None, "source", "execution_result"}:
            return None
        try:
            self.saved.custody.possession(context, reference)
            if namespace == "execution_result":
                self.publications.read(reference, context.scope)
            return True
        except (KeyError, ValueError):
            return False

    def child(self, parent, role, body, *, index=0, sources=FACT_SOURCES, schema=None):
        assignment = {} if role != "results" else {"version": "execution_results_assignment_v1",
            "handoff_ref": "source_" + "a" * 24, "selector": body["publication_inputs"]["selector"]}
        return self.saved.child(parent, role, assignment, index, schema=fact_form(*sources) if schema is None else schema)

    def candidate(self, child, *, extra_facts=None):
        schema = plain(child.request)["report_contract"]["measurements"]["schema"]
        facts = self.host.facts(child, schema) if child.role == "results" else self.host.received_facts(child, schema)
        facts.update(extra_facts or {})
        form = form_with_facts({}, schema, facts)
        self.saved.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        return form, schema

    def admit(self, parent, child, *, extra_facts=None, receive=True):
        form, schema = self.candidate(child, extra_facts=extra_facts)
        original = plain(child.request)["report_contract"]
        resolve = self.host.resolve_own if child.role == "results" else self.host.resolve_received
        def resolver(reference, namespace):
            value = resolve(child, reference, namespace)
            return self.resolve_source(child, reference, namespace) if value is None else value
        typed = TypedReportContract(original["decision"], schema, resolver,
            lambda value: self.host.validate_received_report(child, value, schema))
        admitted = plain(typed.admit(form, audit_identifiers=(child.episode_id,)).as_record())
        index = int(child.path[-1][1].removeprefix("child_"))
        self.saved.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24], "child_episode_id": child.episode_id,
            "contract": canonical(original), "form": canonical(admitted), "failure": None})
        key = f"{parent.run_id}:{parent.episode_id}:{index}:typed_form"
        references = self.host.record_admission(parent, admitted, schema, key)
        if receive:
            self.saved.receipts.receive(parent.episode_id, references, kind="child_form", source_index=index)
        return admitted, schema, key, references


@pytest.fixture
def run(tmp_path):
    with Store(tmp_path / "state") as store:
        yield ReturnFixture(store)


def test_real_typed_admission_and_recursive_forwarding_keep_all_eight_families(run):
    body, sheet = projection()
    root = run.saved.root
    parent = run.child(root, "scientific_process", body)
    producer = run.child(parent, "results", body)
    publication = run.publications.add(producer, body, sheet)
    schema = fact_form(*FACT_SOURCES)
    expected = run.host.facts(producer, schema)
    count = run.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
    assert run.host.received_context(root) == run.host.received_context(parent) == []
    _, _, _, references = run.admit(parent, producer, receive=False)
    assert references == [publication["source_ref"]]
    assert run.host.received_facts(parent, schema) == expected
    assert run.host.received_context(root) == []
    run.saved.receipts.receive(parent.episode_id, references, kind="child_form", source_index=0)
    run.admit(root, parent)
    assert run.host.received_facts(root, schema) == expected
    assert run.host.resolve_received(root, ref("function", "enzyme / original label"), "bvbrc_phylogeny_function")
    assert not run.host.resolve_received(root, ref("function", "not_received"), "bvbrc_phylogeny_function")
    assert run.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == count
    assert run.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_latest_publication_uses_numerical_completed_action_order(run):
    body, sheet = projection()
    early = deepcopy(body)
    early["publication"]["adapter_result"].update(status="partial")
    early["publication"]["adapter_result"]["facts"]["functions"] = None
    producer = run.child(run.saved.root, "results", body)
    first = run.publications.add(producer, early, sheet, index=2)
    before = run.host.facts(producer, fact_form(*FACT_SOURCES))
    last = run.publications.add(producer, body, sheet, index=10)
    after = run.host.facts(producer, fact_form(*FACT_SOURCES))
    assert before[FUNCTIONS][0]["functions"] is None
    assert {row["source_ref"] for rows in after.values() for row in rows} == {last["source_ref"]}
    assert first["source_ref"] != last["source_ref"]
    run.publications.add(producer, early, sheet, index=11)
    run.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE episode_id=? AND decision_index=11", (producer.episode_id,))
    assert run.host.facts(producer, fact_form(*FACT_SOURCES)) == after


@pytest.mark.parametrize("alter", [
    lambda f: f["requested_0"][0].update(value=4.0),
    lambda f: f["requested_0"][0].update(field="negative"),
    lambda f: f["requested_1"][0]["branches"][0].update(node_index=2),
    lambda f: f["requested_2"][0]["sites"][0].update(column_0based=1),
    lambda f: f["requested_4"][0]["functions"][0].update(fraction_all=.75),
    lambda f: f["requested_0"].reverse(),
])
def test_individually_valid_identifiers_cannot_substitute_saved_values(run, alter):
    body, sheet = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body, sheet)
    form, schema = run.candidate(producer)
    alter(form)
    with pytest.raises(ValueError):
        run.host.validate_received_report(producer, form, schema)


def test_frozen_form_and_original_admitted_schema_cannot_be_replaced(run):
    body, sheet = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body, sheet)
    form, schema, key, _ = run.admit(run.saved.root, producer)
    altered = deepcopy(schema)
    altered["properties"]["requested_0"]["items"]["properties"]["value"]["type"] = ["integer", "null"]
    with pytest.raises(ValueError, match="admitted_form_conflict"):
        run.host.record_admission(run.saved.root, form, altered, key)
    row = run.saved.journal.row("runtime_forms", producer.episode_id)
    form["requested_0"][0]["value"] = 3
    run.saved.journal.save("runtime_forms", {**row, "form": canonical(form)})
    with pytest.raises(ValueError, match="frozen_form_conflict"):
        run.host.received_context(run.saved.root)


def test_unrequested_groups_and_opaque_sources_never_grant_saved_values(run):
    body, sheet = projection()
    parent = run.child(run.saved.root, "scientific_process", body)
    producer = run.child(parent, "results", body, sources=(MEASUREMENTS,))
    run.publications.add(producer, body, sheet)
    run.admit(parent, producer)
    assert run.host.received_facts(parent, fact_form(FUNCTIONS)) == {FUNCTIONS: []}
    assert not run.host.resolve_received(parent, ref("function", "enzyme / original label"), "bvbrc_phylogeny_function")
    opaque = {"type": "object", "properties": {"refs": {"type": "array", "items": {
        "type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        "x-source": "execution_result_refs"}}, "required": ["refs"], "additionalProperties": False}
    ref_only = run.child(parent, "results", body, index=1, schema=opaque)
    published = run.publications.add(ref_only, body, sheet)
    run.admit(parent, ref_only, extra_facts={"execution_result_refs": [published["source_ref"]]})
    assert run.host.resolve_received(parent, published["source_ref"], "execution_result")
    assert run.host.received_facts(parent, fact_form(FUNCTIONS)) == {FUNCTIONS: []}
    run.admit(run.saved.root, parent)
    assert run.host.received_facts(run.saved.root, fact_form(FUNCTIONS)) == {FUNCTIONS: []}


def test_deleted_child_report_invalidates_forwarded_facts(run):
    body, sheet = projection()
    parent = run.child(run.saved.root, "scientific_process", body)
    producer = run.child(parent, "results", body)
    run.publications.add(producer, body, sheet)
    run.admit(parent, producer)
    run.admit(run.saved.root, parent)
    run.store.db.execute("DELETE FROM runtime_report_attempts WHERE parent_episode_id=?", (parent.episode_id,))
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        run.host.received_context(run.saved.root)


def test_unsuccessful_return_and_missing_frozen_form_cannot_deliver_facts(run):
    body, sheet = projection()
    producer = run.child(run.saved.root, "results", body, sources=(MEASUREMENTS,))
    published = run.publications.add(producer, body, sheet)
    form, schema = run.candidate(producer)
    attempt = {"parent_episode_id": run.saved.root.episode_id, "decision_index": 0, "delivery_ref": "delivery_failed",
        "child_episode_id": producer.episode_id, "contract": canonical(plain(producer.request)["report_contract"]),
        "form": canonical(form), "failure": canonical({"code": "controlled_failure"})}
    run.saved.journal.save("runtime_report_attempts", attempt)
    assert run.host.received_facts(run.saved.root, schema) == {MEASUREMENTS: []}
    assert not run.host.resolve_received(run.saved.root, published["source_ref"], "execution_result")
    run.saved.journal.save("runtime_report_attempts", {**attempt, "failure": None})
    run.store.db.execute("DELETE FROM runtime_forms WHERE episode_id=?", (producer.episode_id,))
    with pytest.raises(ValueError, match="closed_child_facts_required"):
        run.host.received_context(run.saved.root)


def test_later_publication_cannot_reprice_original_frozen_child_form(run):
    body, sheet = projection()
    producer = run.child(run.saved.root, "results", body, sources=(MEASUREMENTS,))
    run.publications.add(producer, body, sheet)
    run.admit(run.saved.root, producer)
    later = deepcopy(body)
    later["publication"]["adapter_result"]["facts"]["tips"] = 5
    run.publications.add(producer, later, sheet, index=1)
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        run.host.received_context(run.saved.root)


def test_repeated_reads_and_redelivery_create_no_new_records_or_observations(run):
    body, sheet = projection()
    parent = run.saved.root
    producer = run.child(parent, "results", body)
    publication = run.publications.add(producer, body, sheet)
    form, _, _, _ = run.admit(parent, producer)
    before = run.host.received_context(parent)
    records = list(run.store.db.iterdump())
    fresh = BVBRCPhylogenyReturns(run.api)
    assert fresh.received_context(parent) == fresh.received_context(parent) == before
    assert list(run.store.db.iterdump()) == records
    prior = run.store.db.execute("SELECT delivery_ref FROM runtime_report_attempts WHERE parent_episode_id=?", (parent.episode_id,)).fetchone()
    schema = fact_form(MEASUREMENTS)
    returned = {"requested_0": form["requested_0"]}
    contract = {"decision": "Return selected numerical cells", "measurements": {"schema": schema}, "information": {"requested_0": "requested_0"}}
    selected = {"kind": "redeliver_report", "delivery_ref": prior["delivery_ref"], "schema_json": canonical(schema), "purpose": contract["decision"]}
    run.saved.journal.save("runtime_model_calls", {"episode_id": parent.episode_id, "call_index": 1, "purpose": "decision", "request": "{}", "response": canonical({"selection": selected})})
    run.saved.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": 1,
        "delivery_ref": prior["delivery_ref"], "child_episode_id": producer.episode_id, "contract": canonical(contract), "form": canonical(returned), "failure": None})
    assert fresh.record_admission(parent, returned, schema, f"{parent.run_id}:{parent.episode_id}:1:typed_form") == [publication["source_ref"]]
    assert fresh.received_context(parent) == before
    assert run.saved.journal.row("runtime_actions", parent.episode_id, 1) is None
    assert run.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_requirement_dependencies_keep_original_custody_and_are_only_receipts(run):
    body, sheet = projection()
    producer = run.child(run.saved.root, "results", body)
    dependency = run.saved.source(b"original dependency")["source_ref"]
    run.saved.own(producer, dependency)
    needs = [{"requirement_id": "original map", "kind": "scientific_metadata", "role": "residue_map", "source_refs": [dependency], "reason_code": "original_map_required"}]
    body["publication"]["adapter_result"].update(status="partial", missing_requirements=needs)
    body["publication"]["adapter_result"]["facts"]["needs"] = deepcopy(needs)
    publication = run.publications.add(producer, body, sheet, index=1)
    form, _, _, references = run.admit(run.saved.root, producer)
    assert references == [publication["source_ref"], dependency]
    assert form["requested_6"][0]["requirements"] == needs
    assert run.host.resolve_received(run.saved.root, "original map", "bvbrc_phylogeny_requirement")
    assert run.host.resolve_received(run.saved.root, dependency, "source")
    assert not any(ref.startswith("bvbrc_phylogeny_") for ref in run.saved.receipts.known(run.saved.root.episode_id))


def test_unpossessed_requirement_source_cannot_be_returned(run):
    body, sheet = projection()
    producer = run.child(run.saved.root, "results", body)
    dependency = run.saved.source(b"unreceived dependency")["source_ref"]
    needs = [{"requirement_id": "missing", "kind": "scientific_metadata", "role": None, "source_refs": [dependency], "reason_code": "unavailable"}]
    body["publication"]["adapter_result"].update(status="partial", missing_requirements=needs)
    body["publication"]["adapter_result"]["facts"]["needs"] = deepcopy(needs)
    run.publications.add(producer, body, sheet)
    with pytest.raises(ValueError, match="input_not_possessed"):
        run.host.facts(producer, fact_form(REQUIREMENTS))


@pytest.mark.parametrize("field", ["run_id", "episode_id", "assignment", "scope"])
def test_foreign_or_modified_results_context_is_rejected(run, field):
    body, sheet = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body, sheet)
    with pytest.raises(ValueError):
        run.host.facts(replace(producer, **{field: "other" if field in {"run_id", "episode_id"} else {}}), fact_form(*FACT_SOURCES))


def test_unknown_namespaces_and_unsaved_results_are_not_scientific_facts(run):
    body, _ = projection()
    producer = run.child(run.saved.root, "results", body)
    assert run.host.facts(producer, fact_form(*FACT_SOURCES)) == {source: [] for source in FACT_SOURCES}
    assert run.host.resolve_own(producer, "other", "not_phylogeny") is None
    assert run.host.resolve_received(run.saved.root, "other", "not_phylogeny") is None
    assert len(IDENTIFIER_NAMESPACES) == 13


@pytest.mark.parametrize("provider", ["gene_tree", "codon_tree"])
def test_real_provider_output_is_forwarded_without_reparsing_or_recalculation(run, monkeypatch, provider):
    from test_bvbrc_phylogeny_bundle_resolution import fixture, slot as selected_slot
    from test_bvbrc_phylogeny_bundle_adapter import consume, numerical_fields
    f = fixture(provider)
    fields = numerical_fields()
    fields.update(branches={"metric": "branch_rows", "analysis_id": "a", "population_id": "leaves",
        "tree": selected_slot("tree", tree=True), "node_indices": [1, 5]},
        sites={"metric": "site_rows", "analysis_id": "a", "population_id": "matrix", "columns_0based": [0, 2, 3]},
        qualifications={"metric": "qualifications", "analysis_id": "a", "slot_id": None})
    result = consume(f, fields, provider)
    assert result["status"] in {"ok", "partial"}, result
    body, _ = projection()
    original_selector = body["publication_inputs"]["selector"]
    original_selector.update(adapter={"adapter_id": result["adapter_id"], "adapter_version": "1", "parameters": f[3]},
        requested_schema=requested_form_schema(fields))
    body["publication_inputs"]["adapter"] = deepcopy(original_selector["adapter"])
    saved = {key: deepcopy(value) for key, value in result.items() if key not in {"sheet", "components"}}
    saved.update(sheet_content=content(result["sheet"], "actual-sheet"), components_content=content(result["components"], "actual-components"))
    body["publication"]["adapter_result"] = saved
    forbid_acquisition_or_scientific_work(monkeypatch)
    producer = run.child(run.saved.root, "results", body, sources=(MEASUREMENTS, BRANCHES, SITES, QUALIFICATIONS))
    run.publications.add(producer, body, result["sheet"])
    run.admit(run.saved.root, producer)
    facts = run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS, BRANCHES, SITES, QUALIFICATIONS))
    assert numbers(facts) == {"tips": 4, "cells": 16, "gaps": .125, "ambiguity": .25, "canonical": .625, "distance": .2}
    assert facts[BRANCHES][0]["branches"][0]["support_value"] == 75
    assert facts[BRANCHES][0]["branches"][1]["length"] == -.1
    assert facts[SITES][0]["sites"][1]["canonical_majority_fraction"] == pytest.approx(2 / 3)
    assert facts[SITES][0]["sites"][2]["canonical_entropy_bits"] is None
    assert facts[QUALIFICATIONS][0]["qualifications"]
    original = list(run.store.db.iterdump())
    assert BVBRCPhylogenyReturns(run.api).received_facts(run.saved.root,
        fact_form(MEASUREMENTS, BRANCHES, SITES, QUALIFICATIONS)) == facts
    assert list(run.store.db.iterdump()) == original


def test_real_provider_output_is_forwarded_with_codon_family_memberships(run, monkeypatch):
    from test_bvbrc_phylogeny_bundle_adapter import consume, codon_hand_fixture, codon_fields
    f, fields = codon_hand_fixture(), codon_fields()
    result = consume(f, fields, "codon_tree")
    assert result["status"] == "ok", result
    body, _ = projection()
    original_selector = body["publication_inputs"]["selector"]
    original_selector.update(adapter={"adapter_id": result["adapter_id"], "adapter_version": "1", "parameters": f[3]},
        requested_schema=requested_form_schema(fields))
    body["publication_inputs"]["adapter"] = deepcopy(original_selector["adapter"])
    saved = {key: deepcopy(value) for key, value in result.items() if key not in {"sheet", "components"}}
    saved.update(sheet_content=content(result["sheet"], "actual-sheet"), components_content=content(result["components"], "actual-components"))
    body["publication"]["adapter_result"] = saved
    forbid_acquisition_or_scientific_work(monkeypatch)
    producer = run.child(run.saved.root, "results", body, sources=(MEASUREMENTS, MEMBERS))
    run.publications.add(producer, body, result["sheet"])
    run.admit(run.saved.root, producer)
    facts = run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS, MEMBERS))
    assert numbers(facts)["family_present_genomes"] == 3
    assert numbers(facts)["family_missing_genomes"] == 1
    assert numbers(facts)["family_extra_copies"] == 1
    assert numbers(facts)["family_presence_fraction"] == .75
    assert numbers(facts)["logfreq"] < 0
    members = facts[MEMBERS][0]["members"]
    assert members == result["facts"]["members"]
    assert len(members) == 5 and all(type(row["alignment_row_index"]) is int for row in members)
