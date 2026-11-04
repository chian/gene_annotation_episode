"""Fixed Codon arithmetic, invalid associations and retained-final-matrix tests.

Synthetic pre-trim rows are explicitly constructed tests, not measured biology.
The official repository's final matrix cannot reconstruct historical pre-trim
means. No test here establishes provider assembly, custody or episode return.
"""
from __future__ import annotations

import ast
import builtins
from collections import Counter
from copy import deepcopy
from fractions import Fraction
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

from gene_annotation_episode import bvbrc_codon_tree_calculators as calc
from gene_annotation_episode import phylogeny_calculation_contracts as checks
from gene_annotation_episode import phylogeny_calculators as shared
from gene_annotation_episode import phylogeny_format_contracts as format_checks
from gene_annotation_episode import phylogeny_formats as formats


STAGING = Path(__file__).resolve().parents[1]
BOUNDARIES = STAGING / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
NATIVE = BOUNDARIES / "official_example" / "test9_genome_dir"
BASE = "test9_genome_8taxa_10cds_10proteins_codonAndProteins"
Q_KEYS = {"value", "state", "unit", "origin", "numerator", "denominator", "population_ref", "method", "evidence", "requirement_ids"}


def artifact(name="synthetic", data=b"synthetic"):
    return {"raw_artifact_ref": name, "source_ref": "source/" + name, "sha256": hashlib.sha256(data).hexdigest()}


def alignment(sequences=("A-CX", "ATCX", "ATGX", "AT-X"), complete="complete"):
    ref = artifact()
    location = {"artifact": ref, "byte_start_0based": 0, "byte_end_0based_exclusive": 100,
                "line_start_1based": None, "line_end_1based_inclusive": None, "xml_path": None}
    return {"alignment_id": "synthetic#alignment", "artifact": ref, "format": "aligned_fasta", "layout": "fasta",
            "id_rule": "first_whitespace_token", "encoding": "ascii", "declared_row_count": None,
            "declared_column_count": None, "observed_row_count": len(sequences),
            "observed_column_count": len(sequences[0]) if sequences and complete == "complete" else 0 if not sequences and complete == "complete" else None,
            "completeness": complete, "rows": [{"row_index": i, "raw_header": "member" + str(i),
                "member_label": "member" + str(i), "sequence": sequence, "source_location": deepcopy(location)}
                for i, sequence in enumerate(sequences)]}


def apop(doc, rows=None, columns=None, completeness="complete"):
    return {"population_id": "literal/population", "alignment_id": doc["alignment_id"],
        "row_indices": list(range(len(doc["rows"]))) if rows is None else list(rows),
        "columns_0based": list(range(max((len(r["sequence"]) for r in doc["rows"]), default=0))) if columns is None else list(columns),
        "completeness": completeness, "evidence": []}


def family(fid, matrix):
    return {"family_id": fid, "namespace": "PGFam", "matrix": [
        {"genome_id": genome, "feature_ids": list(features)} for genome, features in matrix.items()],
        "matrix_completeness": "complete", "memberships": [], "inclusion": [],
        "native_statistic_observation_ids": [], "final_block_indices": []}


def family_population(families=("F1", "F2"), stage="evaluated_pretrim", complete="complete", pid="families/evaluated"):
    return {"population_id": pid, "family_ids": list(families), "stage": stage, "completeness": complete, "evidence": []}


def genome_population(genomes=("G1", "G2", "G3", "G4"), stage="requested_main", complete="complete", pid="genomes/main"):
    return {"population_id": pid, "genome_ids": list(genomes), "stage": stage, "completeness": complete, "evidence": []}


def sheet():
    result = {"schema_version": "bvbrc_codon_tree_sheet_v1", "tool": "C-L193-CodonTree", "mode": "core_genome_codon_protein",
        "inputs": [], "artifact_refs": [],
        "observed_run": {"original_task_id": None, "source_revision": None, "settings": [], "commands": [], "engines": [], "conflicts": [], "completeness": "unknown"},
        "documents": {"store": {"alignments": [], "tree_documents": [], "partitions": [], "phyloxml": [], "source_records": [], "native_tables": []}, "analyses": []},
        "joins": {key: [] for key in ("input_rows", "tip_rows", "feature_genomes", "functions", "function_equivalences", "taxa", "display_tips", "transformations", "residues", "organismal_tips", "family_blocks")},
        "populations": {key: [] for key in ("alignments", "leaves", "composition", "taxonomy", "genomes", "families", "bootstraps", "native")},
        "genomes": [], "families": [], "models": [], "native_measurements": [], "support_observations": [],
        "dependence_groups": [], "qualifications": [], "missing_requirements": []}
    result["populations"]["families"] = [family_population(stage="returned")]
    result["populations"]["genomes"] = [genome_population()]
    result["families"] = [family("F1", {"G1": ["F1_G1a", "F1_G1b"], "G2": ["F1_G2"], "G3": ["F1_G3"], "G4": []}),
                           family("F2", {genome: ["F2_" + genome] for genome in ("G1", "G2", "G3", "G4")})]
    result["assembly"] = {"version": "bvbrc_phylogeny_assembly_v1", "analysis_id": "synthetic-analysis",
        "caller_populations": deepcopy(result["populations"]), "locus_bindings": [], "genome_request_sets": [],
        "family_matrices": [{"matrix_id": "synthetic/matrix", "namespace": "PGFam",
            "family_population_id": "families/evaluated", "genome_population_id": "genomes/main",
            "rows": [{"family_id": f["family_id"], "genome_id": row["genome_id"],
                      "feature_ids": list(row["feature_ids"]), "evidence": []} for f in result["families"] for row in f["matrix"]],
            "completeness": "complete", "evidence": []}], "historical_frequencies": [], "model_associations": []}
    result["read_outcomes"] = []
    result["documents"]["analyses"] = [{"analysis_id": "synthetic-analysis", "mode": "core_genome_codon_protein",
        "final_alignment_id": None, "partition_document_id": None, "raw_tree_id": None,
        "supported_tree_id": None, "rooted_derivative_tree_id": None, "display_tree_id": None,
        "phyloxml_tree_id": None, "membership_document_id": None, "family_stats_document_id": None,
        "genome_counts_document_id": None, "analysis_stats_document_id": None,
        "native_engine_observation_ids": [], "bootstrap_tree_document_id": None,
        "per_family_final_alignment_ids": [], "explicit_family_matrix_id": "synthetic/matrix", "output_role_evidence": []}]
    return result


def familycalc(value, fpid="families/evaluated", gpid="genomes/main"):
    return calc.codon_family_population_components(value, family_population_id=fpid, genome_population_id=gpid)


def mean_row(fid, feature, genome, value, state="missing"):
    return {"family_id": fid, "feature_id": feature, "genome_id": genome,
            "value": checks.quantity(value, population="pretrim/alignment/" + fid, unit="bits_per_column",
                method="row_mean_log2_literal_frequency", state=state)}


def historical():
    return {"pretrim_sequence_rows": [mean_row("F1", "a1", "G1", -0.5), mean_row("F1", "a2", "G2", -1.0),
                                      mean_row("F2", "b1", "G1", -1.5), mean_row("F2", "b2", "G2", -3.0)],
            "evaluated_family_population": {"population": family_population(),
                "expected_sequence_memberships": [{"family_id": "F1", "feature_ids": ["a1", "a2"]},
                                                   {"family_id": "F2", "feature_ids": ["b1", "b2"]}], "completeness": "complete"}}


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


def assert_quantities(value):
    for cell in quantities(value):
        assert set(cell) == Q_KEYS
        assert (cell["value"] is not None) == (cell["state"] == "available")
        assert cell["origin"] == "derived"
        assert cell["population_ref"]
        for key in ("value", "numerator", "denominator"):
            assert cell[key] is None or isinstance(cell[key], (int, float)) and math.isfinite(cell[key])


def reasons(component):
    return {row["reason_code"] for row in calc.codon_calculation_requirements(component)}


def test_import_origins_and_closed_exports():
    for module in (calc, checks, shared, formats, format_checks):
        assert Path(module.__file__).resolve().parent == STAGING / "gene_annotation_episode"
    assert calc.__all__ == ["native_codon_literal_statistics", "codon_family_population_components",
                            "native_codon_worst_sequence_ratios", "codon_calculation_requirements"]


@pytest.mark.parametrize("field", ["assembly", "read_outcomes"])
def test_provider_sheet_additions_are_required_top_level_keys(field):
    value = sheet()
    del value[field]
    with pytest.raises(ValueError, match="^phylogeny_codon_sheet_shape_invalid$"):
        familycalc(value)


def test_provider_sheet_rejects_unapproved_extra_top_level_keys():
    value = sheet()
    value["other_provider_data"] = {}
    with pytest.raises(ValueError, match="^phylogeny_codon_sheet_shape_invalid$"):
        familycalc(value)


def enriched_sheet():
    """Correctly shaped caller assembly and an actual synthetic reader result."""
    value = sheet()
    data = b">member1\nAC\n"
    ref = artifact("synthetic/provider-alignment", data)
    read = formats.parse_aligned_fasta(data, artifact=ref, id_rule="first_whitespace_token", encoding="ascii")
    assert read["status"] == "ok"
    doc = read["value"]
    value["documents"]["store"]["alignments"].append(doc)
    value["documents"]["analyses"][0]["final_alignment_id"] = doc["alignment_id"]
    value["artifact_refs"].append(ref)
    value["read_outcomes"].append({"read_id": "synthetic/read", "artifact": ref,
        "reader": {"reader": "aligned_fasta", "id_rule": "first_whitespace_token", "encoding": "ascii"},
        "status": read["status"], "value_present": True, "document_ids": [doc["alignment_id"]],
        "observation_ids": [], "diagnostics": deepcopy(read["diagnostics"])})
    return value


def test_provider_enrichment_is_preserved_and_does_not_replace_numerical_operands():
    value = enriched_sheet()
    before = deepcopy(value)
    assembly = value["assembly"]
    assert set(assembly) == {"version", "analysis_id", "caller_populations", "locus_bindings",
        "genome_request_sets", "family_matrices", "historical_frequencies", "model_associations"}
    assert assembly["version"] == "bvbrc_phylogeny_assembly_v1"
    assert assembly["analysis_id"] == value["documents"]["analyses"][0]["analysis_id"]
    assert set(value["read_outcomes"][0]) == {"read_id", "artifact", "reader", "status", "value_present",
                                           "document_ids", "observation_ids", "diagnostics"}
    assert familycalc(value) == familycalc(sheet())
    assert value == before


def test_four_row_fixed_arithmetic_and_canonical_separation():
    doc = alignment()
    before = deepcopy(doc)
    got = calc.native_codon_literal_statistics(doc, population=apop(doc))
    assert got["n_rows"]["value"] == got["n_columns"]["value"] == 4
    assert got["gaps"]["value"] == 2
    assert got["gap_fraction"]["value"] == 2 / 16
    assert [r["sum_squared_frequency"]["value"] for r in got["sites"]] == [1, .5625, .3125, 1]
    assert got["literal_nongap_sum_squared_frequency"]["value"] == 2.875
    assert got["literal_nongap_mean_squared_frequency"]["value"] == .71875
    assert got["native_family_ranking_score"]["value"] == 1.4375
    assert [r["mean_log2_literal_frequency"]["value"] for r in got["rows"]] == pytest.approx([
        -.75, -.35375937481971094, -.603759374819711, -.603759374819711])
    canonical = shared.alignment_components(doc, population=apop(doc), alphabet="protein", case_policy="literal")
    assert canonical["sites"][2]["canonical_entropy_bits"]["value"] == pytest.approx(.9182958340544896)
    assert canonical["sites"][3]["canonical_entropy_bits"]["value"] is None
    assert got["sites"][3]["sum_squared_frequency"]["value"] == 1
    assert not reasons(got)
    assert doc == before
    assert_quantities(got)


def test_literal_lowercase_ambiguities_dot_stop_and_gap_are_unmodified():
    doc = alignment(("X-a.*", "X-A.*"))
    got = calc.native_codon_literal_statistics(doc, population=apop(doc))
    assert [r["sum_squared_frequency"]["value"] for r in got["sites"]] == [1, 0, .5, 1, 1]
    assert got["literal_nongap_sum_squared_frequency"]["value"] == 3.5
    assert got["gaps"]["value"] == 2
    assert [r["mean_log2_literal_frequency"]["value"] for r in got["rows"]] == [-.2, -.2]


def test_explicit_subset_is_not_hidden_filter_or_document_order_join():
    doc = alignment()
    pop = apop(doc, rows=[3, 1], columns=[3, 2])
    got = calc.native_codon_literal_statistics(doc, population=pop)
    assert [r["row_index"] for r in got["rows"]] == [3, 1]
    assert [r["column_0based"] for r in got["sites"]] == [3, 2]
    assert got["literal_nongap_sum_squared_frequency"]["value"] == 1.25
    assert got["gap_fraction"]["value"] == .25


@pytest.mark.parametrize("seqs,rows,columns", [((), None, None), (("", ""), None, None), (("AX", "AT"), [], [0, 1]), (("AX", "AT"), [0, 1], [])])
def test_empty_populations_keep_counts_and_null_statistics_without_requirements(seqs, rows, columns):
    doc = alignment(seqs)
    got = calc.native_codon_literal_statistics(doc, population=apop(doc, rows, columns))
    assert got["gaps"]["value"] == 0
    for field in ("gap_fraction", "literal_nongap_sum_squared_frequency", "literal_nongap_mean_squared_frequency", "native_family_ranking_score"):
        assert got[field]["value"] is None
        assert got[field]["requirement_ids"] == []
    assert all(r["mean_log2_literal_frequency"]["value"] is None for r in got["rows"])
    assert not reasons(got)


@pytest.mark.parametrize("seqs,expected", [(("--", "--"), 0), (("XX", "XX"), 2)])
def test_all_gap_and_x_only_literal_columns(seqs, expected):
    doc = alignment(seqs)
    got = calc.native_codon_literal_statistics(doc, population=apop(doc))
    assert got["literal_nongap_sum_squared_frequency"]["value"] == expected
    assert [r["mean_log2_literal_frequency"]["value"] for r in got["rows"]] == [0, 0]


@pytest.mark.parametrize("doc_state,pop_state", [("truncated", "complete"), ("partial", "complete"), ("complete", "unknown"), ("complete", "partial")])
def test_incomplete_alignment_cannot_supply_denominator(doc_state, pop_state):
    doc = alignment(("AC", "A"), complete=doc_state) if doc_state != "complete" else alignment()
    got = calc.native_codon_literal_statistics(doc, population=apop(doc, completeness=pop_state))
    assert all(q["value"] is None for q in quantities(got))
    assert reasons(got) == {"codon_alignment_population_incomplete"}
    assert len(doc["rows"][1]["sequence"]) == (1 if doc_state != "complete" else 4)


@pytest.mark.parametrize("field,value,code", [("row_indices", [0, 0], "duplicate_index"), ("row_indices", [4], "population_row_outside_alignment"), ("columns_0based", [4], "population_column_outside_alignment"), ("alignment_id", "wrong", "alignment_population_identity_conflict")])
def test_invalid_alignment_population(field, value, code):
    doc = alignment()
    pop = apop(doc)
    pop[field] = value
    with pytest.raises(ValueError, match="^phylogeny_" + code + "$"):
        calc.native_codon_literal_statistics(doc, population=pop)


def test_four_genome_copy_counts_and_no_representation_double_counting():
    value = sheet()
    fam = value["families"][0]
    feats = [f for r in fam["matrix"] for f in r["feature_ids"]]
    for i, representation in enumerate(("protein", "coding_nucleotide")):
        fam["memberships"].append({"representation": representation, "feature_ids": feats[:], "genome_ids": ["G1", "G2", "G3"],
            "deleted_feature_ids": [], "missing_codon_feature_ids": [], "source_table_id": "synthetic/memberships", "source_row_index": i})
    got = familycalc(value)
    f1, f2 = got["rows"]
    assert {k: f1[k]["value"] for k in f1 if k != "family_id"} == {
        "present_genomes": 3, "missing_genomes": 1, "extra_copies": 1, "presence_fraction": .75, "native_initial_family_rank": 2}
    assert f2["native_initial_family_rank"]["value"] == 4
    assert got["population_families"]["value"] == 2
    assert got["population_genomes"]["value"] == 4
    assert f1["presence_fraction"]["denominator"] == 4
    assert f1["presence_fraction"]["population_ref"] == "genomes/main"
    assert not reasons(got)
    assert_quantities(got)


def test_explicit_other_genomes_and_input_order_do_not_change_requested_population():
    value = sheet()
    value["families"][0]["matrix"].insert(0, {"genome_id": "optional", "feature_ids": ["extra1", "extra2", "extra3"]})
    value["families"].reverse()
    value["populations"]["genomes"][0]["genome_ids"].reverse()
    value["families"][1]["matrix"].reverse()
    got = familycalc(value)
    assert got["rows"][0]["family_id"] == "F1"
    assert got["rows"][0]["present_genomes"]["value"] == 3
    assert got["rows"][0]["extra_copies"]["value"] == 1
    value["populations"]["genomes"].append(genome_population(["optional"], stage="requested_optional", pid="optional/population"))
    optional = familycalc(value, gpid="optional/population")
    assert optional["rows"][0]["presence_fraction"]["value"] == 1
    assert optional["rows"][0]["native_initial_family_rank"]["value"] == -1


@pytest.mark.parametrize("mutation,code", [
    (lambda s: s["families"][0]["matrix"][0]["feature_ids"].append("F1_G1a"), "duplicate_identifier"),
    (lambda s: s["families"][0]["matrix"].append({"genome_id": "unselected", "feature_ids": ["F1_G1a"]}), "codon_feature_genome_membership_conflict"),
    (lambda s: s["families"][0]["matrix"].append({"genome_id": "G1", "feature_ids": []}), "codon_duplicate_matrix_genome"),
    (lambda s: s["families"].append(deepcopy(s["families"][0])), "codon_duplicate_family_id"),
    (lambda s: s["populations"]["genomes"].append(deepcopy(s["populations"]["genomes"][0])), "codon_duplicate_population_id"),
    (lambda s: s["populations"]["families"][0]["family_ids"].append("F1"), "duplicate_identifier"),
    (lambda s: s["populations"]["genomes"][0].update(stage="guessed_main"), "codon_population_stage_invalid"),
])
def test_family_identity_and_structure_failures(mutation, code):
    value = sheet()
    mutation(value)
    with pytest.raises(ValueError, match="^phylogeny_" + code + "$"):
        familycalc(value)


@pytest.mark.parametrize("mutation,reason", [
    (lambda s: s["populations"]["genomes"].clear(), "genome_population_required"),
    (lambda s: s["populations"]["genomes"][0].update(completeness="unknown"), "genome_population_required"),
    (lambda s: s["families"][0].update(matrix_completeness="partial"), "family_membership_required"),
    (lambda s: s["families"][0]["matrix"].pop(), "family_membership_required"),
    (lambda s: s["families"].pop(0), "family_membership_required"),
])
def test_missing_family_denominators_are_not_absence(mutation, reason):
    value = sheet()
    mutation(value)
    got = familycalc(value)
    assert got["rows"][0]["present_genomes"]["value"] is None
    assert got["rows"][0]["presence_fraction"]["numerator"] is None
    assert reason in reasons(got)


def test_unknown_family_population_count_retains_individually_known_family_measurements():
    value = sheet()
    value["populations"]["families"][0]["completeness"] = "partial"
    got = familycalc(value)
    assert got["population_families"]["value"] is None
    assert got["rows"][0]["present_genomes"]["value"] == 3
    assert reasons(got) == {"family_population_required"}
    value["populations"]["families"].clear()
    got = familycalc(value)
    assert got["rows"] == []
    assert got["population_families"]["value"] is None
    assert reasons(got) == {"family_population_required"}


def test_zero_population_and_negative_native_initial_rank():
    value = sheet()
    value["populations"]["genomes"][0]["genome_ids"] = []
    got = familycalc(value)
    assert got["population_genomes"]["value"] == 0
    assert got["rows"][0]["present_genomes"]["value"] == got["rows"][0]["extra_copies"]["value"] == 0
    assert got["rows"][0]["presence_fraction"]["value"] is None
    assert not reasons(got)
    value["populations"]["families"][0]["family_ids"] = []
    assert familycalc(value)["population_families"]["value"] == 0


def test_complete_historical_genome_means_ratios_and_maxima():
    operands = historical()
    got = calc.native_codon_worst_sequence_ratios(**operands)
    assert [r["mean"]["value"] for r in got["genome_means"]] == [-1, -2]
    assert [r["mean"]["numerator"] for r in got["genome_means"]] == [-2, -4]
    assert [r["mean"]["denominator"] for r in got["genome_means"]] == [2, 2]
    assert [r["ratio"]["value"] for r in got["rows"]] == pytest.approx([.5 / 1.00001, 1 / 2.00001, 1.5 / 1.00001, 3 / 2.00001])
    assert [r["ratio"]["denominator"] for r in got["rows"]] == [-1.00001, -2.00001, -1.00001, -2.00001]
    assert [r["maximum"]["value"] for r in got["family_maxima"]] == pytest.approx([1 / 2.00001, 3 / 2.00001])
    assert got["denominator_adjustment"] == .00001
    assert not reasons(got)
    assert_quantities(got)


def test_same_genome_mean_uses_exact_rows_including_multiple_copies():
    op = historical()
    op["pretrim_sequence_rows"].append(mean_row("F1", "a3", "G1", -4))
    op["evaluated_family_population"]["expected_sequence_memberships"][0]["feature_ids"].append("a3")
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert got["genome_means"][0]["mean"]["value"] == -2
    assert got["genome_means"][0]["sequence_observations"] == 3
    assert got["rows"][-1]["ratio"]["value"] == 4 / 2.00001


def test_missing_expected_feature_identity_invalidates_all_potential_genome_means():
    op = historical()
    op["pretrim_sequence_rows"].pop()
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert all(r["mean"]["value"] is None for r in got["genome_means"])
    assert all(r["ratio"]["value"] is None for r in got["rows"])
    assert all(r["maximum"]["value"] is None for r in got["family_maxima"])
    assert reasons(got) == {"pretrim_sequence_population_required"}
    assert len(got["rows"]) == 3


@pytest.mark.parametrize("state", ["missing", "not_measured", "truncated", "failed", "incompatible"])
def test_missing_known_genome_measurement_invalidates_only_that_genome(state):
    op = historical()
    op["pretrim_sequence_rows"][-1]["value"].update(value=None, state=state)
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert got["genome_means"][0]["mean"]["value"] == -1
    assert got["genome_means"][1]["mean"]["value"] is None
    assert got["genome_means"][1]["mean"]["denominator"] == 2
    assert got["genome_means"][1]["sequence_observations"] == 1
    assert got["genome_means"][1]["mean"]["state"] == state
    assert got["rows"][0]["ratio"]["value"] == .5 / 1.00001
    assert all(r["maximum"]["value"] is None for r in got["family_maxima"])
    assert reasons(got) == (set() if state == "incompatible" else {"pretrim_sequence_measurement_required"})


@pytest.mark.parametrize("field,state,reason", [("population", "partial", "evaluated_family_population_required"), ("population", "truncated", "evaluated_family_population_required"), ("expected", "unknown", "pretrim_sequence_population_required")])
def test_incomplete_historical_populations_cannot_use_retained_subset(field, state, reason):
    op = historical()
    if field == "population":
        op["evaluated_family_population"]["population"]["completeness"] = state
    else:
        op["evaluated_family_population"]["completeness"] = state
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert all(r["mean"]["value"] is None for r in got["genome_means"])
    assert reasons(got) == {reason}


def test_missing_expected_family_membership_is_explicit_requirement():
    op = historical()
    op["evaluated_family_population"]["expected_sequence_memberships"].pop()
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert all(r["mean"]["value"] is None for r in got["genome_means"])
    assert reasons(got) == {"pretrim_sequence_population_required"}


@pytest.mark.parametrize("mutation,code", [
    (lambda o: o["evaluated_family_population"]["population"].update(stage="selected"), "historical_pretrim_stage_required"),
    (lambda o: o["pretrim_sequence_rows"].append(deepcopy(o["pretrim_sequence_rows"][0])), "duplicate_pretrim_feature"),
    (lambda o: o["pretrim_sequence_rows"][0].update(feature_id="wrong"), "pretrim_feature_outside_population"),
    (lambda o: o["pretrim_sequence_rows"][0].update(family_id="wrong"), "pretrim_family_outside_population"),
    (lambda o: o["pretrim_sequence_rows"][0]["value"].update(unit="ratio"), "pretrim_quantity_unit_conflict"),
    (lambda o: o["pretrim_sequence_rows"][0]["value"].update(origin="native_fitted"), "pretrim_quantity_origin_conflict"),
    (lambda o: o["pretrim_sequence_rows"][0]["value"].update(state="missing"), "pretrim_quantity_value_state_conflict"),
    (lambda o: o["evaluated_family_population"]["expected_sequence_memberships"][1]["feature_ids"].append("a1"), "feature_family_membership_conflict"),
    (lambda o: o["evaluated_family_population"]["expected_sequence_memberships"].append(deepcopy(o["evaluated_family_population"]["expected_sequence_memberships"][0])), "duplicate_expected_family"),
])
def test_historical_identity_units_and_stage_errors(mutation, code):
    op = historical()
    mutation(op)
    with pytest.raises(ValueError, match="^phylogeny_codon_" + code + "$"):
        calc.native_codon_worst_sequence_ratios(**op)


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf"), True])
def test_nonfinite_and_boolean_measurements_fail(number):
    op = historical()
    op["pretrim_sequence_rows"][0]["value"]["value"] = number
    with pytest.raises(ValueError, match="^phylogeny_number_invalid$"):
        calc.native_codon_worst_sequence_ratios(**op)


def test_zero_log_frequency_is_valid_and_positive_value_is_incompatible():
    op = historical()
    for row in op["pretrim_sequence_rows"]:
        row["value"]["value"] = 0
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert all(r["ratio"]["value"] == 0 for r in got["rows"])
    assert all(r["ratio"]["denominator"] == -.00001 for r in got["rows"])
    assert not reasons(got)
    op["pretrim_sequence_rows"][0]["value"]["value"] = .2
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert got["genome_means"][0]["mean"]["state"] == "incompatible"
    assert got["rows"][0]["ratio"]["numerator"] == .2
    assert got["rows"][0]["ratio"]["value"] is None
    assert got["rows"][1]["ratio"]["value"] == 0
    assert all(r["maximum"]["state"] == "incompatible" for r in got["family_maxima"])
    assert not reasons(got)


def test_ratio_above_eight_is_returned_without_eligibility_rule():
    op = {"pretrim_sequence_rows": [mean_row("F" + str(i), "f" + str(i), "G", -10 if i == 0 else 0) for i in range(10)],
          "evaluated_family_population": {"population": family_population(["F" + str(i) for i in range(10)]),
              "expected_sequence_memberships": [{"family_id": "F" + str(i), "feature_ids": ["f" + str(i)]} for i in range(10)], "completeness": "complete"}}
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert got["rows"][0]["ratio"]["value"] == 10 / 1.00001
    assert len(got["rows"]) == len(got["family_maxima"]) == 10
    assert set(got) == {"family_population_id", "genome_means", "rows", "family_maxima", "denominator_adjustment", "missing_requirements"}


def test_empty_historical_populations_do_not_manufacture_maximum_or_requirements():
    op = historical()
    op["pretrim_sequence_rows"] = []
    for row in op["evaluated_family_population"]["expected_sequence_memberships"]:
        row["feature_ids"] = []
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert got["genome_means"] == got["rows"] == []
    assert all(r["maximum"]["value"] is None for r in got["family_maxima"])
    assert not reasons(got)


@pytest.mark.parametrize("family_state,membership_state", [
    ("complete", "complete"), ("unknown", "complete"), ("partial", "complete"), ("truncated", "complete"),
    ("complete", "unknown"), ("complete", "partial"), ("complete", "truncated"),
    ("unknown", "unknown"), ("partial", "partial"), ("truncated", "truncated"),
])
def test_empty_historical_missing_requirements_survive_json_without_dummy_values(family_state, membership_state):
    op = {"pretrim_sequence_rows": [], "evaluated_family_population": {
        "population": family_population([], complete=family_state), "expected_sequence_memberships": [],
        "completeness": membership_state}}
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert got["rows"] == got["genome_means"] == got["family_maxima"] == []
    expected = set()
    if family_state != "complete":
        expected.add("evaluated_family_population_required")
    if membership_state != "complete":
        expected.add("pretrim_sequence_population_required")
    assert reasons(got) == expected
    assert {r["reason_code"] for r in got["missing_requirements"]} == expected
    saved = json.loads(json.dumps(got))
    assert calc.codon_calculation_requirements(saved) == got["missing_requirements"]
    assert not list(quantities(saved))


def test_known_families_without_supplied_rows_keep_each_missing_identity():
    op = historical()
    op["pretrim_sequence_rows"] = []
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert got["rows"] == got["genome_means"] == []
    assert len(got["family_maxima"]) == 2
    assert all(row["maximum"]["value"] is None for row in got["family_maxima"])
    assert len(got["missing_requirements"]) == 4
    assert calc.codon_calculation_requirements(got) == got["missing_requirements"]


def test_input_missing_measurement_requirements_are_retained_and_deduplicated():
    op = historical()
    rid = "phylogeny/original%2Fpretrim/pretrim_sequence_measurement_required"
    op["pretrim_sequence_rows"][0]["value"].update(value=None, state="missing", requirement_ids=[rid])
    got = calc.native_codon_worst_sequence_ratios(**op)
    assert rid in got["genome_means"][0]["mean"]["requirement_ids"]
    assert rid in {r["requirement_id"] for r in got["missing_requirements"]}
    assert calc.codon_calculation_requirements(got) == got["missing_requirements"]


@pytest.mark.parametrize("matrix_state", ["partial", "truncated", "unknown", "absent"])
def test_empty_genome_population_does_not_need_unused_family_memberships(matrix_state):
    value = sheet()
    value["populations"]["genomes"][0]["genome_ids"] = []
    if matrix_state == "absent":
        value["families"] = []
    else:
        for row in value["families"]:
            row["matrix_completeness"] = matrix_state
    got = familycalc(value)
    assert got["population_genomes"]["value"] == 0
    for row in got["rows"]:
        assert row["present_genomes"]["value"] == row["missing_genomes"]["value"] == row["extra_copies"]["value"] == 0
        assert row["presence_fraction"]["value"] is None
        assert row["presence_fraction"]["denominator"] == 0
    assert not reasons(got)


def test_requirements_helper_never_recalculates(monkeypatch):
    op = historical()
    op["pretrim_sequence_rows"] = []
    got = calc.native_codon_worst_sequence_ratios(**op)
    expected = deepcopy(got["missing_requirements"])
    def denied(*args, **kwargs):
        raise AssertionError("Requirement resolution is not numeric recalculation")
    for name in calc.__all__[:-1]:
        monkeypatch.setattr(calc, name, denied)
    assert calc.codon_calculation_requirements(got) == expected


def test_requirement_scope_encoding_and_conflicts():
    doc = alignment()
    pop = apop(doc, completeness="partial")
    pop["population_id"] = "A/B%2F"
    got = calc.native_codon_literal_statistics(doc, population=pop)
    reqs = calc.codon_calculation_requirements(got)
    assert reqs == [{"requirement_id": "phylogeny/A%2FB%252F/codon_alignment_population_incomplete",
        "kind": "output_bytes", "role": "alignment", "source_refs": [], "reason_code": "codon_alignment_population_incomplete"}]
    explicit = deepcopy(reqs)
    explicit[0]["source_refs"] = ["actual/source"]
    merged = calc.codon_calculation_requirements({"component": got, "missing_requirements": explicit})
    assert merged == explicit
    merged[0]["source_refs"].append("detached")
    assert explicit[0]["source_refs"] == ["actual/source"]
    with pytest.raises(ValueError, match="requirement_meaning_conflict"):
        calc.codon_calculation_requirements({"missing_requirements": explicit + reqs})


@pytest.mark.parametrize("rid", ["phylogeny/x/unknown", "x/genome_population_required", "phylogeny//genome_population_required", "phylogeny/A%2fB/genome_population_required"])
def test_unknown_or_malformed_requirement_ids_fail(rid):
    with pytest.raises(ValueError, match="requirement_(reason_unknown|scope_invalid)"):
        calc.codon_calculation_requirements({"requirement_ids": [rid]})


@pytest.fixture(scope="module")
def native_alignment():
    data = (NATIVE / (BASE + ".phy")).read_bytes()
    result = formats.parse_relaxed_phylip(data, artifact=artifact("native/retained-final.phy", data),
                                        layout="interleaved", continuation_ids="absent")
    assert result["status"] == "ok"
    return result["value"]


def test_retained_native_final_alignment_arithmetic_is_not_pretrim_history(native_alignment):
    doc = native_alignment
    got = calc.native_codon_literal_statistics(doc, population=apop(doc))
    assert got["n_rows"]["value"] == 9
    assert got["n_columns"]["value"] == 15300
    assert got["gaps"]["value"] == 17308
    assert got["gap_fraction"]["value"] == 17308 / 137700
    # Independent exact rational oracle; no historical family assignment is
    # inferred from final concatenation or the four global partition blocks.
    numerator = sum(count * count for j in range(15300) for symbol, count in
        Counter(r["sequence"][j] for r in doc["rows"]).items() if symbol != "-")
    exact_sum = Fraction(numerator, 9 * 9)
    assert got["literal_nongap_sum_squared_frequency"]["value"] == pytest.approx(float(exact_sum), rel=1e-15)
    assert got["native_family_ranking_score"]["value"] == pytest.approx(float(exact_sum) / math.sqrt(15300), rel=1e-15)
    assert len(got["rows"]) == 9 and len(got["sites"]) == 15300


def test_no_io_process_network_model_or_parser_calls_and_inputs_unchanged(monkeypatch, native_alignment):
    doc, pop, data, historic = deepcopy(native_alignment), apop(native_alignment), sheet(), historical()
    before = deepcopy((doc, pop, data, historic))
    attempted = []
    def denied(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("Forbidden external access or parsing during calculation")
    with monkeypatch.context() as guard:
        for module, name in [(builtins, "open"), (io, "open"), (os, "open"), (os, "system"), (subprocess, "run"),
                (subprocess, "Popen"), (socket, "socket"), (socket, "create_connection"), (urllib.request, "urlopen")]:
            guard.setattr(module, name, denied)
        for name in dir(formats):
            if name.startswith("parse_"):
                guard.setattr(formats, name, denied)
        # Imports are forbidden inside calls, including lazy model/client loads.
        guard.setattr(builtins, "__import__", denied)
        outputs = [calc.native_codon_literal_statistics(doc, population=pop), familycalc(data),
                   calc.native_codon_worst_sequence_ratios(**historic)]
        for output in outputs:
            calc.codon_calculation_requirements(output)
    assert not attempted
    assert (doc, pop, data, historic) == before


def test_module_uses_only_pure_dependencies_and_no_dynamic_invocation():
    tree = ast.parse(Path(calc.__file__).read_text())
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    roots = {node.module for node in imports if isinstance(node, ast.ImportFrom)} | {
        alias.name for node in imports if isinstance(node, ast.Import) for alias in node.names}
    assert roots <= {"__future__", "collections", "copy", "math", "re", None, "phylogeny_format_contracts"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in ("eval", "exec", "open", "__import__")
