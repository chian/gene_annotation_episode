"""Hand arithmetic, constructed counterexamples and retained-native tests.

Native fixtures are official repository examples, not a new service execution.
These tests exercise only format-to-calculation boundaries, not episode return.
"""
from __future__ import annotations

import ast
import builtins
from copy import deepcopy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

from gene_annotation_episode import phylogeny_calculators as calc
from gene_annotation_episode import phylogeny_calculation_contracts as checks
from gene_annotation_episode import phylogeny_format_contracts as format_checks


STAGING = Path(__file__).resolve().parents[1]
REPOSITORY = next(path for path in Path(__file__).resolve().parents
    if (path / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24").is_dir())
BOUNDARIES = REPOSITORY / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
NATIVE = BOUNDARIES / "official_example" / "test9_genome_dir"
BASE = "test9_genome_8taxa_10cds_10proteins_codonAndProteins"
Q_KEYS = {"value", "state", "unit", "origin", "numerator", "denominator", "population_ref", "method", "evidence", "requirement_ids"}


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


def cpop(n=4, *, kind="input_member", complete="complete"):
    return {"population_id": "composition", "unit": "sequence_member" if kind == "input_member" else "feature",
            "member_subjects": [member(i, kind) for i in range(n)], "assignment_completeness": "unknown",
            "membership_completeness": complete, "evidence": []}


def function(i, key, ident=None):
    return {"assignment_id": ident or "assignment-" + str(i) + "-" + key, "subject": member(i),
            "function_key": key, "function_label": key, "source_record_id": "annotation-" + str(i), "evidence": []}


def taxon(i, taxon_id, rank="species", lineage=()):
    return {"subject": member(i), "taxon_id": taxon_id, "rank": rank,
            "lineage": list(lineage), "source_record_id": "taxon-" + str(i), "evidence": []}


def original_member(document, row=0, *, name="input", length=8, binding="binding"):
    return {"row": {"alignment_id": document["alignment_id"], "row_index": row},
            "member": {"input_binding_id": binding, "member_id": name}, "original_length": length,
            "original_sequence_sha256": "1" * 64, "evidence": []}


def correspondence(document, column, interval, *, row=0, name="input", binding="binding"):
    sequence = document["rows"][row]["sequence"]
    is_gap = sequence[column] == "-"
    return {"alignment_id": document["alignment_id"], "row_index": row, "column_0based": column,
            "staged_ungapped_position_0based": None if is_gap else sum(s != "-" for s in sequence[:column]),
            "original_member": None if is_gap else {"input_binding_id": binding, "member_id": name},
            "original_interval_0based_half_open": interval, "strand": "+", "translation_table": None,
            "transformation_id": None, "evidence": []}


def replicate_join(reference, replicates):
    ref_labels = {label: i for i, label in tips(reference).items()}
    assert len(ref_labels) == len(tips(reference)), "Only these explicitly unique fixture labels support this fixture join"
    return {"reference_tree_id": reference["tree_id"], "mappings": [
        {"replicate_tree_id": tree["tree_id"], "pairs": [
            {"reference_node_index": ref_labels[label], "replicate_node_index": i}
            for i, label in tips(tree).items() if label in ref_labels]} for tree in replicates]}


def bootstrap_population(replicates, expected=None, complete="complete"):
    return {"population_id": "bootstraps", "tree_ids": [t["tree_id"] for t in replicates],
            "expected_replicates": len(replicates) if expected is None else expected,
            "completeness": complete, "expected_count_evidence": []}


def comparison_join(gene, org, labels=None):
    left, right = {v: k for k, v in tips(gene).items()}, {v: k for k, v in tips(org).items()}
    labels = sorted(left.keys() & right.keys()) if labels is None else labels
    return tuple({"gene_tree_id": gene["tree_id"], "gene_node_index": left[label],
                  "organismal_tree_id": org["tree_id"], "organismal_node_index": right[label],
                  "subject": member(label, "genome"), "evidence": []} for label in labels)


def compare(gene, org, labels=None):
    return calc.compare_unrooted_relationships(gene, comparison_id="explicit-comparison",
                organismal_tree=org, injective_tip_join=comparison_join(gene, org, labels))


def quantities(value):
    if isinstance(value, dict):
        if "population_ref" in value:
            yield value
        else:
            for child in value.values():
                yield from quantities(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from quantities(child)


def test_actual_module_origins_and_only_pure_imports():
    for module in (calc, checks, format_checks):
        assert Path(module.__file__).resolve().parent == STAGING / "gene_annotation_episode"
    for module in (calc, checks):
        syntax = ast.parse(Path(module.__file__).read_text())
        imports = [node.module for node in ast.walk(syntax) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(syntax) if isinstance(node, ast.Import) for alias in node.names]
        assert set(imports) <= {None, "__future__", "collections", "copy", "math", "re", "phylogeny_format_contracts"}


def test_four_row_hand_arithmetic_and_closed_cells():
    doc = alignment()
    result = calc.alignment_components(doc, population=apop(doc), alphabet="protein", case_policy="uppercase", pairs=((0, 1),))
    assert [result[k]["value"] for k in ("member_count", "site_count", "cell_count", "gap_cells", "ambiguity_cells", "canonical_cells")] == [4, 4, 16, 2, 4, 10]
    assert result["gap_fraction"]["value"] == 2 / 16
    assert result["gap_fraction"]["numerator"] == 2
    assert result["gap_fraction"]["denominator"] == 16
    assert result["ambiguity_fraction"]["value"] == 4 / 16
    assert result["canonical_fraction"]["value"] == 10 / 16
    assert [s["canonical_majority_fraction"]["value"] for s in result["sites"]] == [1, 1, 2/3, None]
    assert result["sites"][2]["canonical_entropy_bits"]["value"] == pytest.approx(0.9182958340544896)
    assert result["sites"][2]["canonical_entropy_bits"]["denominator"] == 3
    pair = result["pairs"][0]
    assert [pair[k]["value"] for k in ("identical_positions", "substitutions", "both_gap_positions", "a_gap_only_positions", "b_gap_only_positions", "unpaired_nongap_ambiguous_positions")] == [2, 0, 0, 1, 0, 1]
    assert pair["identity_fraction"]["value"] == 1
    assert pair["identity_fraction"]["denominator"] == 2
    for q in quantities(result):
        assert set(q) == Q_KEYS
        assert (q["value"] is None) != (q["state"] == "available")
        assert q["value"] is None or math.isfinite(q["value"])
    assert calc.calculation_requirements(result) == []


@pytest.mark.parametrize("alphabet,sequence,expected", [
    ("dna", "ACGTRYSWKMBDHVN.-*X", (4, 11, 0, 3)),
    ("rna", "ACGURYSWKMBDHVN.-*T", (4, 11, 0, 3)),
    ("protein", "ACDEFGHIKLMNPQRSTVWYBZJX*.-", (20, 4, 1, 1)),
])
def test_exact_symbol_alphabets(alphabet, sequence, expected):
    doc = alignment((sequence,))
    result = calc.alignment_components(doc, population=apop(doc), alphabet=alphabet, case_policy="literal")
    assert tuple(result[k]["value"] for k in ("canonical_cells", "ambiguity_cells", "stop_cells", "other_nongap_cells")) == expected
    assert result["gap_cells"]["value"] == 1
    assert sum(result[k]["value"] for k in ("canonical_cells", "ambiguity_cells", "stop_cells", "other_nongap_cells", "gap_cells")) == len(sequence)


def test_literal_case_raw_symbols_subset_and_whole_string_duplicate_groups():
    doc = alignment(("a-c", "A-C", "A-T", "---"))
    upper = calc.alignment_components(doc, population=apop(doc, columns=[0, 1]), alphabet="dna", case_policy="uppercase")
    literal = calc.alignment_components(doc, population=apop(doc), alphabet="dna", case_policy="literal")
    assert upper["cell_count"]["value"] == 8
    assert upper["gap_cells"]["value"] == 5
    assert upper["sites"][0]["symbol_counts"] == [{"symbol": "-", "count": 1}, {"symbol": "A", "count": 2}, {"symbol": "a", "count": 1}]
    assert [g["row_indices"] for g in upper["identical_sequence_groups"]] == [[0, 1]]
    assert literal["canonical_cells"]["value"] == 4
    assert literal["other_nongap_cells"]["value"] == 2
    assert literal["identical_sequence_groups"] == []
    assert upper["rows"][-1]["nongap_count"]["value"] == 0
    assert upper["rows"][-1]["matrix_occupancy"]["value"] == 0


def test_unknown_alphabet_preserves_gaps_dimensions_occupancy_and_literal_symbols():
    doc = alignment()
    result = calc.alignment_components(doc, population=apop(doc), alphabet="unknown", case_policy="uppercase", pairs=((0, 1),))
    assert result["cell_count"]["value"] == 16
    assert result["gap_fraction"]["value"] == 0.125
    assert result["rows"][0]["matrix_occupancy"]["value"] == 3/4
    assert result["canonical_cells"]["value"] is None
    assert result["ambiguity_cells"]["value"] is None
    assert result["pairs"][0]["identity_fraction"]["value"] is None
    assert result["pairs"][0]["a_gap_only_positions"]["value"] == 1
    assert [r["reason_code"] for r in calc.calculation_requirements(result)] == ["alphabet_required"]


@pytest.mark.parametrize("sequences,rows,columns", [((), [], []), (("", ""), [0, 1], []), (("A",), [], [0])])
def test_empty_populations_have_zero_counts_and_null_ratios(sequences, rows, columns):
    doc = alignment(sequences)
    result = calc.alignment_components(doc, population=apop(doc, rows, columns), alphabet="protein", case_policy="literal")
    assert result["cell_count"]["value"] == 0
    assert result["gap_cells"]["value"] == 0
    assert result["gap_fraction"]["value"] is None
    assert calc.calculation_requirements(result) == []


def test_incomplete_matrix_never_promotes_prefix_to_whole_denominator():
    doc = alignment(("AA--", "A"), complete=False)
    result = calc.alignment_components(doc, population=apop(doc), alphabet="dna", case_policy="literal")
    assert result["cell_count"]["value"] is None
    assert result["cell_count"]["state"] == "truncated"
    assert result["gap_cells"]["value"] is None
    assert result["sites"][0]["symbol_counts"] == [{"symbol": "A", "count": 2}]
    assert result["rows"][0]["nongap_count"]["value"] == 2
    assert result["rows"][1]["nongap_count"]["value"] is None
    assert calc.calculation_requirements(result)[0]["reason_code"] == "alignment_population_incomplete"


@pytest.mark.parametrize("edit,code", [
    (lambda p: p.update(alignment_id="other"), "alignment_population_identity_conflict"),
    (lambda p: p.update(row_indices=[0, 0]), "duplicate_index"),
    (lambda p: p.update(columns_0based=[4]), "population_column_outside_alignment"),
    (lambda p: p.update(row_indices=[True]), "integer_invalid"),
    (lambda p: p.update(extra=1), "alignment_population_shape_invalid"),
])
def test_alignment_population_conflicts_fail(edit, code):
    doc = alignment()
    population = apop(doc)
    edit(population)
    with pytest.raises(ValueError, match="^phylogeny_" + code + "$"):
        calc.alignment_components(doc, population=population, alphabet="protein", case_policy="literal")


def test_all_pair_categories_are_disjoint_and_directional():
    doc = alignment(("A-C-XT", "AT--XG"))
    row = calc.alignment_components(doc, population=apop(doc), alphabet="protein", case_policy="literal", pairs=((0, 1),))["pairs"][0]
    assert [row[k]["value"] for k in ("identical_positions", "substitutions", "both_gap_positions", "a_gap_only_positions", "b_gap_only_positions", "unpaired_nongap_ambiguous_positions")] == [1, 1, 1, 1, 1, 1]
    assert row["identity_fraction"]["value"] == 1/2


def test_staged_coordinate_map_is_not_original_coordinates():
    doc = alignment(("-A--BC-", "-------"))
    result = calc.ungapped_coordinate_map(doc, row_indices=(0, 1))
    assert [r["ungapped_position_0based"] for r in result[:7]] == [None, 0, None, None, 1, 2, None]
    assert all(r["ungapped_position_0based"] is None for r in result[7:])
    assert result[4]["column_0based"] == 4


def test_original_coverage_unions_overlap_and_keeps_original_denominator():
    doc = alignment(("AA-C",))
    maps = (correspondence(doc, 0, [2, 5]), correspondence(doc, 1, [4, 7]), correspondence(doc, 2, None), correspondence(doc, 3, [7, 8]))
    result = calc.original_member_coverage(doc, population=apop(doc), members=(original_member(doc),), correspondences=maps)
    row = result["rows"][0]
    assert row["original_covered_positions"]["value"] == 6
    assert row["original_member_coverage"]["value"] == 6/8
    assert row["original_member_coverage"]["denominator"] == 8
    assert calc.calculation_requirements(result) == []


def test_concatenated_members_have_separate_coverage_and_incomplete_association_affects_both():
    doc = alignment(("ACGT",))
    members = (original_member(doc, name="first", length=10), original_member(doc, name="second", length=20))
    maps = tuple(correspondence(doc, i, [i, i+1], name="first" if i < 2 else "second") for i in range(4))
    result = calc.original_member_coverage(doc, population=apop(doc), members=members, correspondences=maps)
    assert [r["original_member_coverage"]["value"] for r in result["rows"]] == [2/10, 2/20]
    partial = calc.original_member_coverage(doc, population=apop(doc), members=members, correspondences=maps[:-1])
    assert all(r["original_member_coverage"]["value"] is None for r in partial["rows"])
    assert [r["original_covered_positions"]["value"] for r in partial["rows"]] == [2, 1]
    assert len(calc.calculation_requirements(partial)) == 2


@pytest.mark.parametrize("length,expected", [(0, None), (8, 0), (None, None)])
def test_all_gap_original_coverage_and_missing_lengths(length, expected):
    doc = alignment(("---",))
    result = calc.original_member_coverage(doc, population=apop(doc), members=(original_member(doc, length=length),), correspondences=())
    assert result["rows"][0]["original_member_coverage"]["value"] == expected
    assert result["rows"][0]["original_covered_positions"]["value"] == 0
    assert bool(calc.calculation_requirements(result)) == (length is None)


@pytest.mark.parametrize("edit,code", [
    (lambda r: r.update(staged_ungapped_position_0based=1), "staged_coordinate_conflict"),
    (lambda r: r.update(original_interval_0based_half_open=[2, 1]), "original_interval_invalid"),
    (lambda r: r.update(original_interval_0based_half_open=[0, 9]), "original_interval_outside_member"),
    (lambda r: r["original_member"].update(member_id="wrong"), "correspondence_member_identity_conflict"),
    (lambda r: r.update(alignment_id="wrong"), "correspondence_identity_conflict"),
])
def test_correspondence_conflicts_fail(edit, code):
    doc = alignment(("A",))
    row = correspondence(doc, 0, [0, 1])
    edit(row)
    with pytest.raises(ValueError, match="^phylogeny_" + code + "$"):
        calc.original_member_coverage(doc, population=apop(doc), members=(original_member(doc),), correspondences=(row,))


def test_conflicting_original_digests_and_conflicting_column_maps_fail():
    doc = alignment(("A", "A"))
    members = (original_member(doc), original_member(doc, row=1))
    members[1]["original_sequence_sha256"] = "2" * 64
    with pytest.raises(ValueError, match="original_member_facts_conflict"):
        calc.original_member_coverage(doc, population=apop(doc), members=members, correspondences=())
    doc = alignment(("A",))
    with pytest.raises(ValueError, match="correspondence_conflict"):
        calc.original_member_coverage(doc, population=apop(doc), members=(original_member(doc),),
            correspondences=(correspondence(doc, 0, [0, 1]), correspondence(doc, 0, [1, 2])))


def test_absent_original_map_is_unknown_not_zero_and_gap_membership_is_allowed():
    doc = alignment(("A-",))
    absent = calc.original_member_coverage(doc, population=apop(doc), members=(original_member(doc),), correspondences=())
    assert absent["rows"][0]["original_covered_positions"]["value"] is None
    assert absent["rows"][0]["original_member_coverage"]["value"] is None
    gap = correspondence(doc, 1, None)
    gap["original_member"] = original_member(doc)["member"]
    complete = calc.original_member_coverage(doc, population=apop(doc), members=(original_member(doc),),
        correspondences=(correspondence(doc, 0, [5, 6]), gap))
    assert complete["rows"][0]["original_member_coverage"]["value"] == 1/8


def test_explicitly_unavailable_correspondence_operands_are_missing_not_invalid():
    doc = alignment(("A",))
    record = correspondence(doc, 0, None)
    record.update(staged_ungapped_position_0based=None, original_member=None, strand="unknown")
    missing = calc.original_member_coverage(doc, population=apop(doc), members=(original_member(doc),), correspondences=(record,))
    assert missing["rows"][0]["original_member_coverage"]["value"] is None
    assert missing["rows"][0]["original_covered_positions"]["value"] is None
    assert calc.calculation_requirements(missing)[0]["reason_code"] == "original_residue_map_required"


def test_missing_intermediate_digest_does_not_hide_conflicting_original_identity():
    doc = alignment(("A", "A", "A"))
    members = [original_member(doc, row=i) for i in range(3)]
    members[1]["original_sequence_sha256"] = None
    members[2]["original_sequence_sha256"] = "2" * 64
    with pytest.raises(ValueError, match="original_member_facts_conflict"):
        calc.original_member_coverage(doc, population=apop(doc), members=members, correspondences=())


def test_original_subset_unions_only_selected_columns_and_preserves_reverse_intervals():
    doc = alignment(("ACGT",))
    maps = [correspondence(doc, i, [7-i, 8-i]) for i in range(4)]
    for row in maps:
        row["strand"] = "-"
    result = calc.original_member_coverage(doc, population=apop(doc, columns=[0, 2]),
        members=(original_member(doc),), correspondences=maps)
    assert result["rows"][0]["original_covered_positions"]["value"] == 2
    assert result["rows"][0]["original_member_coverage"]["value"] == 2/8


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


def test_missing_lengths_do_not_erase_topology_or_known_partial_sum():
    tree = hand_tree(lengths={1: 1, 2: 0, 3: 2, 5: 3, 6: 4})
    result = treecalc(tree, pairs=((2, 3), (2, 5)))
    assert result["branch_length_sum"]["value"] is None
    assert result["known_branch_length_sum"]["value"] == 10
    assert result["missing_branch_length_count"]["value"] == 1
    assert [r["value"]["value"] for r in result["distances"]] == [2, None]
    assert len(result["splits"]) == 1
    assert calc.calculation_requirements(result)


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


def test_split_identity_tie_break_is_numeric_and_whole_tree_population_is_required():
    tree = hand_tree((("A", "B", "C", "D"), ("E", "F", "G", "H")))
    result = treecalc(tree)
    assert result["splits"][0]["side_node_indices"] == [2, 3, 4, 5]
    assert result["splits"][0]["complement_node_indices"] == [7, 8, 9, 10]
    subset = lpop(tree)
    subset["node_indices"].pop()
    with pytest.raises(ValueError, match="whole_tree_leaf_population_required"):
        calc.tree_components(tree, leaf_population=subset, support_observations=(), native_measurements=(), branch_unit="native_unknown", pairs=())


def test_native_zero_support_not_inferred_from_absent_support():
    tree = hand_tree(lengths={i: 0 for i in range(7)})
    result = treecalc(tree)
    assert result["branch_length_sum"]["value"] == 0
    assert result["branches"][0]["support_rescaled"]["value"] is None
    assert result["branches"][0]["support_rescaled"]["state"] == "not_measured"
    assert calc.calculation_requirements(result) == []


@pytest.mark.parametrize("value,scale,method,expected", [
    (0, "percent", "rapid_bootstrap", 0), (75, "percent", "rapid_bootstrap", .75),
    (.95, "fraction", "phyml_abayes", .95), (.4, "fraction", "fasttree_sh_like", .4),
    (5, "statistic", "phyml_alrt_statistic", None), (75, "percent", "native_unknown", None),
])
def test_support_semantics_preserve_native_method_and_zero(value, scale, method, expected):
    tree = hand_tree()
    unit = "native_statistic" if scale == "statistic" else scale
    result = treecalc(tree, support=(support(tree, 1, method=method, scale=scale),),
                      native=(native_observation(tree, 1, value, unit=unit, method=method),))
    row = result["branches"][0]
    assert row["support_rescaled"]["value"] == expected
    assert row["support_method"] == method
    assert row["native_support_observation_ids"] == ["obs"]
    if method == "native_unknown":
        assert any(r["reason_code"] == "support_method_unresolved" for r in calc.calculation_requirements(result))


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


def test_bootstrap_three_of_four_and_conditional_denominator():
    ref = hand_tree()
    reps = [hand_tree(name="rep" + str(i)) for i in range(3)] + [hand_tree((("A", "C"), ("B", "D")), name="rep3")]
    result = calc.bootstrap_split_frequencies(ref, replicates=tuple(reps), replicate_population=bootstrap_population(reps),
                tip_join=replicate_join(ref, reps), method="rapid_bootstrap")
    assert result["rows"][0]["matches"]["value"] == 3
    assert result["rows"][0]["denominator"]["value"] == 4
    assert result["rows"][0]["frequency"]["value"] == .75
    assert result["rows"][0]["frequency"]["method"] == "rapid_bootstrap_frequency"
    join = replicate_join(ref, reps)
    join["mappings"].pop()
    conditional = calc.bootstrap_split_frequencies(ref, replicates=tuple(reps), replicate_population=bootstrap_population(reps, expected=100, complete="truncated"),
                tip_join=join, method="rell_bootstrap")
    assert conditional["expected_replicates"]["value"] == 100
    assert conditional["supplied_replicates"]["value"] == 4
    assert conditional["usable_replicates"]["value"] == 3
    assert conditional["rows"][0]["frequency"]["value"] == 1
    assert conditional["rows"][0]["frequency"]["method"] == "conditional_rell_bootstrap_frequency"
    assert conditional["excluded_replicates"] == [{"tree_id": reps[-1]["tree_id"], "reason_code": "replicate_tip_mapping_missing"}]


def test_bootstrap_incompatible_leaf_set_is_excluded_not_counted_as_absent_split():
    ref = hand_tree()
    reps = [hand_tree(name="rep1"), hand_tree(("A", "B", "C"), name="rep2")]
    result = calc.bootstrap_split_frequencies(ref, replicates=tuple(reps), replicate_population=bootstrap_population(reps),
                tip_join=replicate_join(ref, reps), method="rapid_bootstrap")
    assert result["usable_replicates"]["value"] == 1
    assert result["rows"][0]["frequency"]["value"] == 1
    assert result["excluded_replicates"][0]["reason_code"] == "replicate_tip_population_incompatible"


def test_bootstrap_empty_known_population_and_unknown_expected_population_are_distinct():
    ref = hand_tree()
    population = bootstrap_population([], expected=0)
    empty = calc.bootstrap_split_frequencies(ref, replicates=(), replicate_population=population,
        tip_join=replicate_join(ref, []), method="rapid_bootstrap")
    assert empty["expected_replicates"]["value"] == empty["supplied_replicates"]["value"] == empty["usable_replicates"]["value"] == 0
    assert empty["rows"][0]["frequency"]["value"] is None
    assert calc.calculation_requirements(empty) == []
    population["expected_replicates"] = None
    population["completeness"] = "unknown"
    unknown = calc.bootstrap_split_frequencies(ref, replicates=(), replicate_population=population,
        tip_join=replicate_join(ref, []), method="rapid_bootstrap")
    assert unknown["expected_replicates"]["value"] is None
    assert unknown["rows"][0]["frequency"]["method"] == "conditional_rapid_bootstrap_frequency"
    assert {r["reason_code"] for r in calc.calculation_requirements(unknown)} == {"bootstrap_expected_count_required", "bootstrap_replicates_not_retained"}


def test_bootstrap_duplicate_labels_can_be_mapped_by_explicit_nodes():
    ref = hand_tree((("X", "X"), ("X", "X")))
    rep = hand_tree(("X", "X", ("X", "X")), name="rep")
    join = {"reference_tree_id": ref["tree_id"], "mappings": [{"replicate_tree_id": rep["tree_id"],
        "pairs": [{"reference_node_index": a, "replicate_node_index": b} for a, b in zip(tips(ref), tips(rep))]}]}
    result = calc.bootstrap_split_frequencies(ref, replicates=(rep,), replicate_population=bootstrap_population([rep]), tip_join=join, method="rapid_bootstrap")
    assert result["rows"][0]["frequency"]["value"] == 1


@pytest.mark.parametrize("edit,code", [
    (lambda j: j.update(reference_tree_id="wrong"), "replicate_reference_conflict"),
    (lambda j: j["mappings"][0]["pairs"].append(deepcopy(j["mappings"][0]["pairs"][0])), "replicate_mapping_not_injective"),
    (lambda j: j["mappings"][0].update(replicate_tree_id="absent"), "replicate_mapping_absent_tree"),
    (lambda j: j["mappings"][0]["pairs"][0].update(reference_node_index=0), "replicate_reference_tip_invalid"),
])
def test_bootstrap_wrong_reference_or_mapping_fails(edit, code):
    ref, reps = hand_tree(), [hand_tree(name="rep")]
    join = replicate_join(ref, reps)
    edit(join)
    with pytest.raises(ValueError, match="^phylogeny_" + code + "$"):
        calc.bootstrap_split_frequencies(ref, replicates=tuple(reps), replicate_population=bootstrap_population(reps), tip_join=join, method="rapid_bootstrap")


def test_function_composition_two_of_four_and_two_of_three_with_missing_metadata():
    result = calc.function_composition(population=cpop(), assignments=(function(0, "A"), function(1, "A"), function(2, "B")))
    assert result["total_members"]["value"] == 4
    assert result["members_with_recorded_assignment"]["value"] == 3
    assert result["members_without_recorded_assignment"]["value"] == 1
    a, b = result["rows"]
    assert a["assigned_members"]["value"] == 2
    assert a["fraction_all"]["value"] == 2/4
    assert a["fraction_recorded"]["value"] == 2/3
    assert b["fraction_all"]["value"] == 1/4
    assert b["fraction_recorded"]["value"] == 1/3
    empty = calc.function_composition(population=cpop(), assignments=())
    assert empty["members_without_recorded_assignment"]["value"] == 4
    assert empty["rows"] == []


def test_multivalued_functions_and_explicit_equivalence_do_not_double_count_members():
    equivalent = {"equivalence_id": "equivalence", "function_keys": ["A", "A2"], "canonical_function_key": "A", "evidence": []}
    result = calc.function_composition(population=cpop(2), assignments=(function(0, "A"), function(0, "A2"), function(0, "B"), function(1, "B")), equivalences=(equivalent,))
    assert [r["assigned_members"]["value"] for r in result["rows"]] == [1, 2]
    assert sum(r["fraction_all"]["value"] for r in result["rows"]) == 1.5
    assert result["members_with_recorded_assignment"]["value"] == 2


def test_composition_unknown_membership_keeps_quantities_unavailable():
    result = calc.function_composition(population=cpop(complete="truncated"), assignments=(function(0, "A"),))
    assert result["total_members"]["state"] == "truncated"
    assert result["rows"][0]["fraction_all"]["value"] is None
    assert calc.calculation_requirements(result)[0]["reason_code"] == "composition_population_required"


def test_taxon_known_denominators_and_explicit_lineage():
    result = calc.taxon_components(population=cpop(), rank="genus", assignments=(
        taxon(0, "s1", lineage=[{"taxon_id": "g1", "rank": "genus"}]),
        taxon(1, "g1", "genus"), taxon(2, "g2", "genus")))
    assert result["known_members"]["value"] == 3
    assert result["unknown_members"]["value"] == 1
    assert result["distinct_known_taxa"]["value"] == 2
    assert result["same_taxon_pairs"]["value"] == 1
    assert result["known_taxon_pairs"]["value"] == 3
    assert result["same_taxon_pair_fraction"]["value"] == 1/3
    assert result["same_taxon_pair_fraction"]["denominator"] == 3


def test_unknown_taxa_require_rank_specific_metadata_but_empty_populations_do_not():
    result = calc.taxon_components(population=cpop(), rank="species/a", assignments=())
    assert result["known_members"]["value"] == 0
    assert result["unknown_members"]["value"] == 4
    assert result["same_taxon_pair_fraction"]["value"] is None
    requirements = calc.calculation_requirements(result)
    assert requirements[0]["requirement_id"].endswith("/rank/species%2Fa/taxon_associations_required")
    assert calc.calculation_requirements(calc.taxon_components(population=cpop(0), rank="species", assignments=())) == []


def test_wrong_function_taxon_subjects_and_conflicting_rank_fail():
    assignment = function(0, "A")
    assignment["subject"]["source_record_id"] = "wrong"
    with pytest.raises(ValueError, match="function_assignment_subject_conflict"):
        calc.function_composition(population=cpop(), assignments=(assignment,))
    with pytest.raises(ValueError, match="taxon_assignment_conflict"):
        calc.taxon_components(population=cpop(), rank="species", assignments=(taxon(0, "a"), taxon(0, "b")))
    with pytest.raises(ValueError, match="taxon_rank_conflict"):
        calc.taxon_components(population=cpop(), rank="species", assignments=(taxon(0, "a", lineage=[{"taxon_id": "b", "rank": "species"}]),))


def test_feature_population_keeps_distinct_features_and_rejects_genome_function_votes():
    population = cpop(2, kind="feature")
    assignments = [function(0, "A"), function(1, "A")]
    for row in assignments:
        row["subject"]["kind"] = "feature"
    result = calc.function_composition(population=population, assignments=assignments)
    assert result["unit"] == "feature"
    assert result["rows"][0]["assigned_members"]["value"] == 2
    population["member_subjects"][0]["kind"] = "genome"
    with pytest.raises(ValueError, match="composition_subject_unit_conflict"):
        calc.function_composition(population=population, assignments=assignments)


def test_four_genome_taxonomy_population_and_function_rejection():
    population = cpop(4, kind="genome")
    population["unit"] = "genome"
    assignments = [taxon(0, "X"), taxon(1, "X"), taxon(2, "Y")]
    for row in assignments:
        row["subject"]["kind"] = "genome"
    result = calc.taxon_components(population=population, rank="species", assignments=assignments)
    assert [result[k]["value"] for k in ("known_members", "unknown_members", "distinct_known_taxa", "same_taxon_pairs", "known_taxon_pairs")] == [3, 1, 2, 1, 3]
    assert result["same_taxon_pair_fraction"]["value"] == 1/3
    assert [s["kind"] for row in result["rows"] for s in row["member_subjects"]] == ["genome"] * 3
    with pytest.raises(ValueError, match="composition_unit_invalid"):
        calc.function_composition(population=population, assignments=())
    population["member_subjects"][0]["kind"] = "input_member"
    with pytest.raises(ValueError, match="taxon_subject_unit_conflict"):
        calc.taxon_components(population=population, rank="species", assignments=assignments)


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


def test_restricted_split_definitions_resolve_five_to_four_canonical_side_change():
    gene = hand_tree(((("A", "E"), "B"), ("C", "D")))
    organismal = hand_tree((("A", "B"), ("C", "D")), name="organismal")
    result = compare(gene, organismal)
    assert result["rf"]["value"] == 0
    assert result["matched_tips"]["value"] == 4
    assert result["omitted_gene_tips"] == [{"tree_id": gene["tree_id"], "node_index": 4}]
    row = result["restricted_gene_splits"][0]
    assert row["side_node_indices"] == [3, 5]
    assert row["complement_node_indices"] == [7, 8]
    assert row["edge_node_indices"] == [1, 6]
    assert row["split_id"] == "explicit-comparison/gene/split/3,5"
    whole = treecalc(gene)
    assert [3, 5] not in [r["side_node_indices"] for r in whole["splits"]]
    gene_ids = {r["split_id"] for r in result["restricted_gene_splits"]}
    organismal_ids = {r["split_id"] for r in result["restricted_organismal_splits"]}
    assert all(pair["gene_split_id"] in gene_ids and pair["organismal_split_id"] in organismal_ids for pair in result["shared_split_pairs"])
    second = calc.compare_unrooted_relationships(gene, comparison_id="second-comparison", organismal_tree=organismal,
        injective_tip_join=comparison_join(gene, organismal))
    assert second["rf"] == dict(result["rf"], population_ref="second-comparison")
    assert not gene_ids & {r["split_id"] for r in second["restricted_gene_splits"]}


def test_pruning_retains_all_original_edges_collapsing_to_one_restricted_split():
    gene = hand_tree(((("A", "B"), "E"), ("C", "D")))
    organismal = hand_tree((("A", "B"), ("C", "D")), name="organismal")
    result = compare(gene, organismal)
    assert len(result["restricted_gene_splits"]) == 1
    assert result["restricted_gene_splits"][0]["edge_node_indices"] == [1, 2, 6]
    assert result["gene_splits"]["value"] == result["organismal_splits"]["value"] == 1
    assert result["shared_splits"]["value"] == 1


def test_comparison_duplicate_labels_require_and_accept_explicit_node_identity_map():
    gene, org = hand_tree((("X", "X"), ("X", "X"))), hand_tree(("X", "X", ("X", "X")), name="org")
    pairs = tuple({"gene_tree_id": gene["tree_id"], "gene_node_index": a, "organismal_tree_id": org["tree_id"],
                   "organismal_node_index": b, "subject": member(i, "genome"), "evidence": []}
                  for i, (a, b) in enumerate(zip(tips(gene), tips(org))))
    assert calc.compare_unrooted_relationships(gene, comparison_id="duplicates", organismal_tree=org, injective_tip_join=pairs)["rf"]["value"] == 0
    pairs[0]["organismal_node_index"] = pairs[1]["organismal_node_index"]
    with pytest.raises(ValueError, match="comparison_join_not_injective"):
        calc.compare_unrooted_relationships(gene, comparison_id="duplicates", organismal_tree=org, injective_tip_join=pairs)


def test_requirement_ids_escape_supplied_segments_and_conflicts_fail():
    doc = alignment(("A",))
    population = apop(doc)
    population["population_id"] = "p/a%2F"
    result = calc.original_member_coverage(doc, population=population,
        members=(original_member(doc, binding="a/b", name="c/d"),), correspondences=())
    req = calc.calculation_requirements(result)[0]
    assert req["requirement_id"].startswith("phylogeny/p%2Fa%252F/row/0/member/a%2Fb/c%2Fd/")
    conflict = deepcopy(result)
    other = deepcopy(conflict["missing_requirements"][0])
    other["source_refs"] = ["other"]
    conflict["missing_requirements"].append(other)
    with pytest.raises(ValueError, match="requirement_meaning_conflict"):
        calc.calculation_requirements(conflict)
    with pytest.raises(ValueError, match="requirement_reason_unknown"):
        calc.calculation_requirements({"x": {"requirement_ids": ["phylogeny/p/unknown_reason"]}})


@pytest.fixture(scope="module")
def native_documents():
    from gene_annotation_episode import phylogeny_formats as formats
    assert Path(formats.__file__).resolve().parent == STAGING / "gene_annotation_episode"
    result = {}
    for key, filename in (("alignment", BASE + ".phy"), ("partitions", BASE + ".partitions"),
                          ("best", "RAxML_bestTree." + BASE), ("supported", "RAxML_bipartitions." + BASE),
                          ("bootstraps", "RAxML_bootstrap." + BASE)):
        data = (NATIVE / filename).read_bytes()
        ref = artifact("native/" + filename, data)
        if key == "alignment":
            parsed = formats.parse_relaxed_phylip(data, artifact=ref, layout="interleaved", continuation_ids="absent")
        elif key == "partitions":
            parsed = formats.parse_raxml_partitions(data, artifact=ref, alignment_column_count=15300)
        else:
            parsed = formats.parse_newick(data, artifact=ref, dialect="newick", allow_multiple=(key == "bootstraps"))
        assert parsed["status"] == "ok", parsed["diagnostics"]
        result[key] = parsed["value"]
    return result


def test_retained_native_codon_alignment_partitions_and_gap_denominator(native_documents):
    doc = native_documents["alignment"]
    result = calc.alignment_components(doc, population=apop(doc), alphabet="unknown", case_policy="literal")
    assert result["member_count"]["value"] == 9
    assert result["site_count"]["value"] == 15300
    assert result["cell_count"]["value"] == 137700
    assert result["gap_cells"]["value"] == 17308
    assert result["gap_fraction"]["value"] == 17308/137700
    partitions = native_documents["partitions"]["partitions"]
    assert [len(p["columns_0based"]) for p in partitions] == [3825] * 4
    parts = [calc.alignment_components(doc, population=apop(doc, columns=p["columns_0based"]),
              alphabet="dna" if i < 3 else "protein", case_policy="literal") for i, p in enumerate(partitions)]
    assert sum(r["cell_count"]["value"] for r in parts) == 137700
    assert sum(r["gap_cells"]["value"] for r in parts) == 17308


def test_retained_native_codon_bootstraps_six_splits_and_root_independent_rf(native_documents):
    best, supported = native_documents["best"]["trees"][0], native_documents["supported"]["trees"][0]
    reps = native_documents["bootstraps"]["trees"]
    assert len(reps) == 100
    result = calc.bootstrap_split_frequencies(supported, replicates=tuple(reps), replicate_population=bootstrap_population(reps),
                tip_join=replicate_join(supported, reps), method="rapid_bootstrap")
    assert result["usable_replicates"]["value"] == 100
    assert len(result["rows"]) == 6
    assert all(row["matches"]["value"] == row["denominator"]["value"] == 100 for row in result["rows"])
    assert all(row["frequency"]["value"] == 1 for row in result["rows"])
    compared = compare(best, supported)
    assert compared["matched_tips"]["value"] == 9
    assert compared["shared_splits"]["value"] == 6
    assert compared["rf"]["value"] == 0


def test_saved_json_recalculation_for_all_functions_without_io_or_imports(monkeypatch, native_documents):
    # Fixtures and modules are loaded before disabling access. No test-local
    # temporary fixture is opened during a guarded calculator invocation.
    doc = json.loads(json.dumps(alignment(("AC",))))
    population = apop(doc)
    tree, org = hand_tree(), hand_tree(("A", "B", ("C", "D")), name="org")
    reps = (hand_tree(name="rep"),)
    native_doc = json.loads(json.dumps(native_documents["alignment"]))
    native_pop = apop(native_doc)
    actions = [
        lambda: calc.alignment_components(doc, population=population, alphabet="protein", case_policy="literal"),
        lambda: calc.ungapped_coordinate_map(doc, row_indices=(0,)),
        lambda: calc.original_member_coverage(doc, population=population, members=(original_member(doc),),
            correspondences=(correspondence(doc, 0, [2, 3]), correspondence(doc, 1, [3, 4]))),
        lambda: treecalc(tree),
        lambda: calc.bootstrap_split_frequencies(tree, replicates=reps, replicate_population=bootstrap_population(reps),
            tip_join=replicate_join(tree, reps), method="rapid_bootstrap"),
        lambda: calc.function_composition(population=cpop(), assignments=(function(0, "A"),)),
        lambda: calc.taxon_components(population=cpop(), rank="species", assignments=(taxon(0, "s"),)),
        lambda: compare(tree, org),
        lambda: calc.alignment_components(native_doc, population=native_pop, alphabet="unknown", case_policy="literal"),
    ]
    expected = [action() for action in actions]
    snapshots = deepcopy((doc, population, tree, org, reps, native_doc, native_pop))
    def deny(*args, **kwargs):
        raise AssertionError("I/O, process, network or import attempted inside calculator")
    with monkeypatch.context() as guard:
        for module, name in ((builtins, "open"), (io, "open"), (os, "open"), (os, "system"),
                             (subprocess, "Popen"), (subprocess, "run"), (socket, "socket"),
                             (socket, "create_connection"), (urllib.request, "urlopen"), (builtins, "__import__")):
            guard.setattr(module, name, deny)
        actual = [action() for action in actions]
        for result in actual:
            if type(result) is dict:
                calc.calculation_requirements(result)
    assert actual == expected
    assert (doc, population, tree, org, reps, native_doc, native_pop) == snapshots


def test_literal_conservation_reuses_shared_counts_and_preserves_historical_canonical_values():
    doc = alignment()
    population = apop(doc)
    before = deepcopy((doc, population))
    canonical = calc.alignment_components(doc, population=population, alphabet="protein", case_policy="uppercase")
    result = calc.literal_site_conservation(doc, population=population)
    assert result["member_count"] == canonical["member_count"]
    assert result["site_count"] == canonical["site_count"]
    assert [row["symbol_counts"] for row in result["sites"]] == [row["symbol_counts"] for row in canonical["sites"]]
    assert [row["modal_count"]["value"] for row in result["sites"]] == [4, 3, 2, 4]
    assert [row["majority_fraction"]["value"] for row in result["sites"]] == [1, 3/4, 1/2, 1]
    assert all(row["majority_fraction"]["denominator"] == 4 for row in result["sites"])
    assert result["sites"][2]["modal_symbol"] == "C"
    assert canonical["sites"][2]["canonical_majority_fraction"]["value"] == 2/3
    assert canonical["sites"][2]["canonical_entropy_bits"]["value"] == pytest.approx(0.9182958340544896)
    assert calc.alignment_components(doc, population=population, alphabet="protein", case_policy="uppercase") == canonical
    assert (doc, population) == before
    assert calc.calculation_requirements(result) == []
    for quantity in quantities(result):
        assert set(quantity) == Q_KEYS


def test_literal_conservation_source_tie_order_is_not_symbol_or_population_selection_order():
    doc = alignment(("C", "A", "C", "A"))
    population = apop(doc, rows=[3, 2, 1, 0])
    result = calc.literal_site_conservation(doc, population=population)
    row, = result["sites"]
    assert row["symbol_counts"] == [{"symbol": "A", "count": 2}, {"symbol": "C", "count": 2}]
    assert result["ordered_source_row_indices"] == [0, 1, 2, 3]
    assert (row["modal_symbol"], row["modal_first_source_row_index"]) == ("C", 0)
    reversed_doc = alignment(("A", "C", "A", "C"))
    reversed_row, = calc.literal_site_conservation(reversed_doc, population=apop(reversed_doc))["sites"]
    assert reversed_row["symbol_counts"] == row["symbol_counts"]
    assert reversed_row["modal_symbol"] == "A"
    subset, = calc.literal_site_conservation(doc, population=apop(doc, rows=[3, 2]))["sites"]
    assert (subset["modal_symbol"], subset["modal_first_source_row_index"]) == ("C", 2)
    assert subset["majority_fraction"]["value"] == 1/2


def test_literal_conservation_preserves_case_gap_ambiguity_and_requested_column_order():
    doc = alignment(("a-X*?", "A-X*?", "a-X*?", "A-X*?"))
    result = calc.literal_site_conservation(doc, population=apop(doc, columns=[4, 0, 1, 2, 3]))
    assert [row["column_0based"] for row in result["sites"]] == [4, 0, 1, 2, 3]
    assert [row["modal_symbol"] for row in result["sites"]] == ["?", "a", "-", "X", "*"]
    assert [row["majority_fraction"]["value"] for row in result["sites"]] == [1, 1/2, 1, 1, 1]
    assert result["sites"][2]["strict_gt_0_8"] is True  # Literal gap majority, not amino-acid conservation.
    assert calc.calculation_requirements(result) == []  # No invented canonical-alphabet dependency.
    for row in doc["rows"]:
        row["raw_header"] = row["member_label"] = "duplicate"
    assert calc.literal_site_conservation(doc, population=apop(doc, columns=[4, 0, 1, 2, 3])) == result


@pytest.mark.parametrize("modal,total,above,display", [
    (4, 5, False, .8), (401, 500, True, .8), (399, 500, False, .8),
    (2, 3, False, .67), (1, 1, True, 1),
])
def test_literal_conservation_threshold_uses_unrounded_shared_fraction(modal, total, above, display):
    doc = alignment(tuple(["A"] * modal + ["C"] * (total-modal)))
    row, = calc.literal_site_conservation(doc, population=apop(doc))["sites"]
    assert row["modal_count"]["value"] == modal
    assert row["majority_fraction"]["numerator"] == modal
    assert row["majority_fraction"]["denominator"] == total
    assert row["majority_fraction"]["value"] == modal/total
    assert row["strict_gt_0_8"] is above
    assert row["displayed_2dp_fraction"]["value"] == display


@pytest.mark.parametrize("sequences,rows,columns,members", [
    ((), [], [], 0), (("", ""), [0, 1], [], 2), (("A",), [], [0], 0),
])
def test_literal_conservation_known_empty_has_no_fabricated_modal_value(sequences, rows, columns, members):
    doc = alignment(sequences)
    result = calc.literal_site_conservation(doc, population=apop(doc, rows, columns))
    assert result["member_count"]["value"] == members
    assert result["site_count"]["value"] == len(columns)
    for row in result["sites"]:
        assert row["symbol_counts"] == []
        assert row["modal_symbol"] is row["modal_first_source_row_index"] is row["strict_gt_0_8"] is None
        assert all(row[field]["value"] is None for field in ("modal_count", "majority_fraction", "displayed_2dp_fraction"))
        assert row["majority_fraction"]["denominator"] == 0
        assert row["majority_fraction"]["state"] == "not_measured"
    assert calc.calculation_requirements(result) == []


@pytest.mark.parametrize("partial_matrix,partial_population", [(True, False), (False, True), (True, True)])
def test_literal_conservation_partial_counts_do_not_establish_a_complete_mode(partial_matrix, partial_population):
    doc = alignment(("AA--", "A") if partial_matrix else ("AA--", "AAAA"), complete=not partial_matrix)
    population = apop(doc, complete="partial" if partial_population else "complete")
    result = calc.literal_site_conservation(doc, population=population)
    assert result["sites"][0]["symbol_counts"] == [{"symbol": "A", "count": 2}]
    assert result["member_count"]["value"] is None
    assert result["member_count"]["state"] == ("truncated" if partial_matrix else "missing")
    for row in result["sites"]:
        assert row["modal_symbol"] is row["modal_first_source_row_index"] is row["strict_gt_0_8"] is None
        assert all(row[field]["value"] is None for field in ("modal_count", "majority_fraction", "displayed_2dp_fraction"))
        assert row["majority_fraction"]["denominator"] is None
    assert [row["reason_code"] for row in calc.calculation_requirements(result)] == ["alignment_population_incomplete"]


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


def test_literal_conservation_rejects_unknown_convention_and_duplicate_population():
    doc = alignment(("A",))
    with pytest.raises(ValueError, match="literal_conservation_convention_invalid"):
        calc.literal_site_conservation(doc, population=apop(doc), convention="canonical")
    with pytest.raises(ValueError, match="duplicate_index"):
        calc.literal_site_conservation(doc, population=apop(doc, rows=[0, 0]))


def test_literal_conservation_saved_json_needs_no_import_io_parser_or_execution(monkeypatch):
    doc = json.loads(json.dumps(alignment(("C-X", "A-X", "C-X", "A-X"))))
    population = json.loads(json.dumps(apop(doc, rows=[3, 2, 1, 0], columns=[2, 0, 1])))
    expected = calc.literal_site_conservation(doc, population=population)
    snapshot = deepcopy((doc, population))
    def deny(*args, **kwargs):
        raise AssertionError("saved literal conservation attempted import, I/O or execution")
    with monkeypatch.context() as guard:
        for module, name in ((builtins, "open"), (io, "open"), (os, "open"), (os, "system"),
                             (subprocess, "Popen"), (subprocess, "run"), (socket, "socket"),
                             (socket, "create_connection"), (urllib.request, "urlopen"), (builtins, "__import__")):
            guard.setattr(module, name, deny)
        actual = calc.literal_site_conservation(doc, population=population)
        assert calc.calculation_requirements(actual) == []
    assert actual == expected and (doc, population) == snapshot
