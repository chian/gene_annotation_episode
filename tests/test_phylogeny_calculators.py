"""Hand arithmetic, constructed counterexamples and retained-native tests.

Native fixtures are official repository examples, not a new service execution.
These tests exercise only format-to-calculation boundaries, not episode return.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.episodic_workflow.root.library import phylogeny_calculators as calc
from gene_annotation_episode import phylogeny_calculation_contracts as checks
def artifact(name="synthetic", data=b"synthetic"):
    return {"raw_artifact_ref": name, "source_ref": "source/" + name, "sha256": hashlib.sha256(data).hexdigest()}


def location(ref):
    return {"artifact": deepcopy(ref), "byte_start_0based": 0, "byte_end_0based_exclusive": 100,
            "line_start_1based": None, "line_end_1based_inclusive": None, "xml_path": None}


def alignment(sequences=("A-CX", "ATCX", "ATGX", "AT-X"), name="synthetic/alignment", complete=True):
    ref = artifact(name)
    lengths = {len(s) for s in sequences}
    return {"alignment_id": name + "#alignment", "artifact": ref, "format": "aligned_fasta", "layout": "fasta",
            "id_rule": "first_whitespace_token", "encoding": "ascii", "declared_row_count": None,
            "declared_column_count": None, "observed_row_count": len(sequences),
            "observed_column_count": next(iter(lengths), 0) if len(lengths) <= 1 and complete else None,
            "completeness": "complete" if complete else "truncated",
            "rows": [{"row_index": i, "raw_header": "member" + str(i), "member_label": "member" + str(i),
                      "sequence": s, "source_location": location(ref)} for i, s in enumerate(sequences)]}


def apop(document, rows=None, columns=None, complete="complete"):
    return {"population_id": "population/" + document["alignment_id"], "alignment_id": document["alignment_id"],
            "row_indices": list(range(len(document["rows"]))) if rows is None else list(rows),
            "columns_0based": list(range(max((len(r["sequence"]) for r in document["rows"]), default=0))) if columns is None else list(columns),
            "completeness": complete, "evidence": []}


def hand_tree(topology=(("A", "B"), ("C", "D")), name="synthetic/tree", lengths=None):
    """Build a closed document from explicit topology, without parsing bytes."""
    ref = artifact(name)
    document_id = name + "#tree_document"
    nodes = []
    def add(item, parent):
        index = len(nodes)
        leaf = type(item) is str
        node = {"node_index": index, "parent_index": parent, "child_indices": [],
                "raw_label": item if leaf else None, "decoded_label": item if leaf else None,
                "label_token": item if leaf else None, "branch_length": None, "branch_length_token": None,
                "comments": [], "source_location": location(ref)}
        nodes.append(node)
        if not leaf:
            node["child_indices"] = [add(child, index) for child in item]
        if lengths is not None and index in lengths:
            node["branch_length"] = lengths[index]
            node["branch_length_token"] = str(lengths[index]) if lengths[index] is not None else None
        return index
    add(topology, None)
    return {"tree_id": document_id + "/tree/0", "document_id": document_id, "tree_index": 0,
            "source_format": "newick", "root_node_index": 0, "native_rooted_marker": "unspecified",
            "nodes": nodes, "source_location": location(ref)}


def tips(tree):
    return {n["node_index"]: n["decoded_label"] for n in tree["nodes"] if not n["child_indices"]}


def lpop(tree):
    return {"population_id": "leaves/" + tree["tree_id"], "tree_id": tree["tree_id"],
            "node_indices": list(tips(tree)), "completeness": "complete", "evidence": []}


def treecalc(tree, *, support=(), native=(), unit="native_unknown", pairs=()):
    return calc.tree_components(tree, leaf_population=lpop(tree), support_observations=support,
                                native_measurements=native, branch_unit=unit, pairs=pairs)


def native_observation(tree, index, value, *, ident="obs", field="branch_support_native", unit="percent", method="rapid_bootstrap"):
    return {"observation_id": ident, "field": field, "value": value,
            "raw_token": str(value) if value is not None else None, "state": "available" if value is not None else "missing",
            "unit": unit, "population_id": "native/" + tree["tree_id"],
            "subject_id": tree["tree_id"] + "/node/" + str(index), "method": method,
            "location": deepcopy(tree["nodes"][index]["source_location"]), "evidence": [], "uncertainty": None,
            "requirement_ids": []}


def support(tree, index, *, ident="obs", method="rapid_bootstrap", scale="percent", source="internal_label"):
    return {"tree_id": tree["tree_id"], "node_index": index, "native_observation_id": ident,
            "source_kind": source, "method": method, "scale": scale,
            "command_id": None, "bootstrap_population_id": None, "evidence": []}


def member(i, kind="input_member"):
    return {"kind": kind, "id": "m" + str(i), "source_record_id": "member-source-" + str(i)}


def comparison_join(gene, org, labels=None):
    left, right = {v: k for k, v in tips(gene).items()}, {v: k for k, v in tips(org).items()}
    labels = sorted(left.keys() & right.keys()) if labels is None else labels
    return tuple({"gene_tree_id": gene["tree_id"], "gene_node_index": left[label],
                  "organismal_tree_id": org["tree_id"], "organismal_node_index": right[label],
                  "subject": member(label, "genome"), "evidence": []} for label in labels)


def compare(gene, org, labels=None):
    return calc.compare_unrooted_relationships(gene, comparison_id="explicit-comparison",
                organismal_tree=org, injective_tip_join=comparison_join(gene, org, labels))


def test_tree_root_length_excluded_signed_sums_zero_and_paths():
    tree = hand_tree(lengths={0: 99, 1: 1, 2: 0, 3: -0.5, 4: 2, 5: 3, 6: 4})
    result = treecalc(tree, pairs=((2, 3), (2, 5), (2, 2), (0, 5)))
    assert result["tip_count"]["value"] == 4
    assert result["internal_node_count"]["value"] == 3
    assert result["branch_length_sum"]["value"] == 9.5
    assert result["branch_length_sum"]["unit"] == "native_unknown"
    assert [r["value"]["value"] for r in result["distances"]] == [-0.5, 6, 0, 5]
    assert len(result["branches"]) == 6
    assert result["branches"][1]["length"]["value"] == 0
    assert tree["nodes"][0]["branch_length"] == 99


def test_known_units_require_per_edge_native_measurements_and_cannot_override_conflict():
    tree = hand_tree(lengths={i: 1 for i in range(7)})
    unit = "expected_substitutions_per_model_site"
    requested_only = treecalc(tree, unit=unit)
    assert requested_only["branch_length_sum"]["unit"] == "native_unknown"
    native = tuple(native_observation(tree, i, 1, field="branch_length", ident="length" + str(i), unit=unit, method="raxml") for i in range(1, 7))
    evidenced = treecalc(tree, unit=unit, native=native)
    assert evidenced["branch_length_sum"]["unit"] == unit
    assert treecalc(tree, unit=unit, native=native[:-1])["branch_length_sum"]["unit"] == "native_unknown"
    with pytest.raises(ValueError, match="branch_unit_conflict"):
        treecalc(tree, unit="joint_mixed_partition_model_site", native=native)
    native[0]["value"] = 3
    with pytest.raises(ValueError, match="length_native_value_conflict"):
        treecalc(tree, native=native)


def test_known_partial_sum_preserves_units_of_its_actual_contributing_edges():
    tree = hand_tree(lengths={i: 1 for i in range(1, 6)})
    unit = "expected_substitutions_per_model_site"
    native = tuple(native_observation(tree, i, 1, field="branch_length", ident="length" + str(i), unit=unit, method="raxml") for i in range(1, 6))
    result = treecalc(tree, native=native, unit=unit)
    assert result["branch_length_sum"]["value"] is None
    assert result["known_branch_length_sum"]["value"] == 5
    assert result["known_branch_length_sum"]["unit"] == unit


def test_finite_native_lengths_cannot_create_nonfinite_aggregate_cells():
    tree = hand_tree(lengths={i: 1e308 for i in range(1, 7)})
    with pytest.raises(ValueError, match="^phylogeny_arithmetic_nonfinite$"):
        treecalc(tree)


def test_root_representation_split_deduplication_and_polytomy_conventions():
    balanced = treecalc(hand_tree())
    assert len(balanced["splits"]) == 1
    assert balanced["splits"][0]["side_node_indices"] == [2, 3]
    assert balanced["splits"][0]["edge_node_indices"] == [1, 4]
    assert balanced["splits"][0]["split_id"].endswith("/split/2,3")
    degree_three = treecalc(hand_tree(("A", "B", ("C", "D"))))
    assert degree_three["rooted_representation_polytomies"]["value"] == 1
    assert degree_three["unrooted_degree_polytomies"]["value"] == 0
    star = treecalc(hand_tree(("A", "B", "C", "D")))
    assert star["rooted_representation_polytomies"]["value"] == 1
    assert star["unrooted_degree_polytomies"]["value"] == 1
    assert star["splits"] == []


def test_duplicate_display_labels_are_distinct_tip_identities():
    tree = hand_tree((("same", "same"), ("same", "same")))
    result = treecalc(tree)
    assert result["tip_count"]["value"] == 4
    assert result["splits"][0]["side_node_indices"] == [2, 3]
    assert result["splits"][0]["complement_node_indices"] == [5, 6]


@pytest.mark.parametrize("change", ["value", "scale", "method"])
def test_conflicting_support_observations_are_not_selected_or_averaged(change):
    tree = hand_tree()
    a, b = native_observation(tree, 1, 75, ident="a"), native_observation(tree, 1, 75, ident="b")
    sa, sb = support(tree, 1, ident="a"), support(tree, 1, ident="b", source="phyloxml_confidence")
    if change == "value":
        b["value"], b["raw_token"] = 80, "80"
    elif change == "scale":
        b["value"], b["raw_token"], b["unit"], sb["scale"] = .75, ".75", "fraction", "fraction"
    else:
        b["method"] = sb["method"] = "rell_bootstrap"
    row = treecalc(tree, support=(sa, sb), native=(a, b))["branches"][0]
    assert row["support_rescaled"]["value"] is None
    assert row["support_rescaled"]["state"] == "incompatible"
    assert row["native_support_observation_ids"] == ["a", "b"]


@pytest.mark.parametrize("edit,code", [
    (lambda s, n: n.update(subject_id="wrong/node/1"), "support_native_relationship_conflict"),
    (lambda s, n: n.update(field="branch_length", unit="native_unknown"), "support_native_relationship_conflict"),
    (lambda s, n: s.update(native_observation_id="absent"), "support_native_observation_missing"),
    (lambda s, n: n.update(unit="fraction"), "support_native_scale_conflict"),
    (lambda s, n: n.update(value=101), "support_value_outside_scale"),
])
def test_support_wrong_associations_fail(edit, code):
    tree = hand_tree()
    s, n = support(tree, 1), native_observation(tree, 1, 75)
    edit(s, n)
    with pytest.raises(ValueError, match="^phylogeny_" + code + "$"):
        treecalc(tree, support=(s,), native=(n,))


def test_unrooted_relationship_rf_examples_and_root_representation():
    gene = hand_tree()
    conflict = hand_tree((("A", "C"), ("B", "D")), name="organismal")
    result = compare(gene, conflict)
    assert [result[k]["value"] for k in ("matched_tips", "gene_splits", "organismal_splits", "shared_splits", "rf")] == [4, 1, 1, 0, 2]
    assert result["rf_fraction"]["value"] == 1
    star = compare(gene, hand_tree(("A", "B", "C", "D"), name="star"))
    assert star["rf"]["value"] == 1
    assert star["rf_fraction"]["value"] == 1
    root_shift = compare(gene, hand_tree(("A", "B", ("C", "D")), name="shift"))
    assert root_shift["rf"]["value"] == 0
    assert len(root_shift["shared_split_pairs"]) == 1
    assert root_shift["comparison_id"] == "explicit-comparison"


def test_relationship_restriction_reports_omitted_tips_and_no_small_set_evidence():
    gene, org = hand_tree(), hand_tree(("A", "B", ("C", "D")), name="org")
    result = compare(gene, org, labels=["A", "B", "C"])
    assert result["matched_tips"]["value"] == 3
    assert result["gene_splits"]["value"] == result["organismal_splits"]["value"] == 0
    assert result["rf_fraction"]["value"] is None
    assert len(result["omitted_gene_tips"]) == len(result["omitted_organismal_tips"]) == 1


def test_pruning_retains_all_original_edges_collapsing_to_one_restricted_split():
    gene = hand_tree(((("A", "B"), "E"), ("C", "D")))
    organismal = hand_tree((("A", "B"), ("C", "D")), name="organismal")
    result = compare(gene, organismal)
    assert len(result["restricted_gene_splits"]) == 1
    assert result["restricted_gene_splits"][0]["edge_node_indices"] == [1, 2, 6]
    assert result["gene_splits"]["value"] == result["organismal_splits"]["value"] == 1
    assert result["shared_splits"]["value"] == 1


@pytest.mark.parametrize("change", ["extra", "long_symbol", "long_modal", "boolean_count", "nonfinite",
                                    "wrong_unit", "boolean_source_index", "boolean_threshold"])
def test_literal_conservation_closed_shape_rejects_unbounded_symbols_and_invalid_cells(change):
    doc = alignment(("C", "A", "C", "A"))
    population = apop(doc)
    value = calc.literal_site_conservation(doc, population=population)
    row = value["sites"][0]
    if change == "extra": value["unexpected"] = 0
    elif change == "long_symbol": row["symbol_counts"][0]["symbol"] = "arbitrary prose"
    elif change == "long_modal": row["modal_symbol"] = "arbitrary prose"
    elif change == "boolean_count": row["symbol_counts"][0]["count"] = True
    elif change == "nonfinite": row["majority_fraction"]["value"] = float("nan")
    elif change == "wrong_unit": row["majority_fraction"]["unit"] = "annotation_probability"
    elif change == "boolean_source_index": value["ordered_source_row_indices"][0] = False
    elif change == "boolean_threshold": row["strict_gt_0_8"] = 0
    with pytest.raises(ValueError, match="^phylogeny_"):
        checks.validate_literal_site_conservation_components(value, alignment=doc, population=population)


