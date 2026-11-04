"""Codon provider verification; retained native and synthetic cases stay separate."""
from __future__ import annotations

import builtins
from copy import deepcopy
from contextlib import contextmanager, ExitStack
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch
from urllib.parse import quote

import pytest

from gene_annotation_episode import bvbrc_codon_tree_inputs as provider
from gene_annotation_episode import bvbrc_codon_tree_grader as grader
from gene_annotation_episode import bvbrc_codon_tree_native as native
from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import phylogeny_raxml_inputs as raxml
from gene_annotation_episode import phylogeny_calculation_contracts as cells
from gene_annotation_episode import bvbrc_phylogeny_common_inputs as common


STAGING = Path(__file__).resolve().parents[1]
NATIVE = STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24" / "official_example"
BASE = "test9_genome_8taxa_10cds_10proteins_codonAndProteins"
POP_KEYS = ("alignments", "leaves", "composition", "taxonomy", "genomes", "families", "bootstraps", "native")
JOIN_KEYS = ("input_rows", "tip_rows", "feature_genomes", "functions", "function_equivalences", "taxa",
             "display_tips", "transformations", "residues", "organismal_tips", "family_blocks")


def evidence(label="synthetic", pointer=""):
    return {"content": {"source_ref": "source/" + label, "artifact_field": "artifact_ref", "artifact_ref": "raw/" + label,
        "sha256": hashlib.sha256(label.encode()).hexdigest(), "byte_count": len(label.encode())}, "pointer": pointer}


def read(name, data, reader, **kwargs):
    artifact = {"raw_artifact_ref": "raw/" + name, "source_ref": "source/" + name, "sha256": hashlib.sha256(data).hexdigest()}
    functions = {"aligned_fasta": formats.parse_aligned_fasta, "relaxed_phylip": formats.parse_relaxed_phylip,
        "newick": formats.parse_newick, "raxml_partitions": formats.parse_raxml_partitions,
        "raxml_run_log": raxml.parse_raxml_run_log, "codon_membership": native.parse_codon_membership,
        "codon_family_statistics": native.parse_codon_family_statistics, "codon_genome_counts": native.parse_codon_genome_counts,
        "codon_analysis_statistics": native.parse_codon_analysis_statistics}
    result = functions[reader](data, artifact=artifact, **kwargs)
    return {"read_id": "read/" + name, "artifact": artifact, "reader": {"reader": reader, **kwargs}, "result": result}


def envelope(reads, analysis):
    store = {k: [] for k in ("alignments", "tree_documents", "partitions", "phyloxml", "source_records", "native_tables")}
    result = {"parsed": {"store": store, "analyses": [analysis]}, "reads": reads,
              **{k: [] for k in ("raxml_runs", "membership", "family_statistics", "genome_counts", "analysis_statistics")}}
    tables = {"codon_membership": "membership", "codon_family_statistics": "family_statistics",
              "codon_genome_counts": "genome_counts", "codon_analysis_statistics": "analysis_statistics"}
    for item in reads:
        value, reader = item["result"]["value"], item["reader"]["reader"]
        if value is None:
            continue
        if reader in tables:
            result[tables[reader]].append(value)
            store["native_tables"].append(value["table"])
        elif reader == "raxml_run_log":
            result["raxml_runs"].append(value)
        else:
            key = {"newick": "tree_documents", "phyloxml": "phyloxml", "raxml_partitions": "partitions"}.get(reader, "alignments")
            store[key].append(value)
    return result


def analysis():
    return {"analysis_id": "a1", "mode": "core_genome_codon_protein", "final_alignment_id": None,
        "partition_document_id": None, "raw_tree_id": None, "supported_tree_id": None, "rooted_derivative_tree_id": None,
        "display_tree_id": None, "phyloxml_tree_id": None, "membership_document_id": None, "family_stats_document_id": None,
        "genome_counts_document_id": None, "analysis_stats_document_id": None, "native_engine_observation_ids": [],
        "bootstrap_tree_document_id": None, "per_family_final_alignment_ids": [], "explicit_family_matrix_id": None,
        "output_role_evidence": []}


def gp(ids, pid="main", stage="requested_main", complete="complete"):
    return {"population_id": pid, "genome_ids": list(ids), "stage": stage, "completeness": complete, "evidence": []}


def fp(ids, pid="families", stage="returned", complete="complete"):
    return {"population_id": pid, "family_ids": list(ids), "stage": stage, "completeness": complete, "evidence": []}


def binding(ids, bid="main-input", pointer="/genome_ids"):
    return {"binding_id": bid, "parameter_pointer": pointer, "kind": "inline_parameter", "content": None,
        "workspace_path": None, "inline_value": list(ids), "link_evidence": None,
        "members": [{"member_id": g, "member_pointer": "/" + str(i), "length": None, "molecule": None,
                     "sequence_sha256": None, "evidence": None} for i, g in enumerate(ids)]}


def request_set(pop, bid="main-input", kind="main_ids", sid="main-set"):
    return {"set_id": sid, "kind": kind, "input_binding_ids": [bid], "group_id": None,
            "derived_from_set_ids": [], "population": deepcopy(pop)}


def fixture(*, include_alignment=True, membership_bytes=None):
    """Source-derived table syntax; all supplied measurements are synthetic."""
    reads = []
    a = analysis()
    if include_alignment:
        aligned = read("synthetic-alignment", b">G1\nA-CX\n>G2\nATCX\n>G3\nATGX\n>G4\nAT-X\n", "aligned_fasta",
                       id_rule="first_whitespace_token", encoding="ascii")
        reads.append(aligned)
        a["final_alignment_id"] = aligned["result"]["value"]["alignment_id"]
    tree = read("synthetic-tree", b"((G1:0,G2:1)0:-0.1,(G3:2,G4:3):0.5);", "newick", dialect="newick", allow_multiple=False)
    reads.append(tree)
    a["raw_tree_id"] = tree["result"]["value"]["trees"][0]["tree_id"]
    if membership_bytes is None:
        membership_bytes = (b"F1\tProteins\t\ta\tc\td\tdeletedParalogs: \tb\n"
            b"F1\tCodons\t\ta\tc\tlacking CodonAlignment for F1: \td\n"
            b"F2\tProteins\t\te\tf\tg\th\nF2\tCodons\t\te\tf\tg\th\n")
    membership = read("synthetic-membership", membership_bytes, "codon_membership", dialect="homologs_current")
    reads.append(membership)
    a["membership_document_id"] = membership["result"]["value"]["table"]["table_id"] if membership["result"]["value"] else None
    stats = read("synthetic-stats", b"PGFam\tgaps\tsum_squared_freq\tmean_squared_freq\tnum_pos\tnum_seqs\tworstSeqScoreused_in_tree\nF1\t2\t3.25\t0.8125\t4\t2\t2\tTrue\nF2\t0\t0\t0\t0\t2\tna\tFalse\ndisqualification: low alignment score\n",
                 "codon_family_statistics", dialect="current_missing_header_tab")
    reads.append(stats)
    a["family_stats_document_id"] = stats["result"]["value"]["table"]["table_id"]
    counts = read("synthetic-counts", b"Genome\tAllGenes\tSingleCopy\tFiltered_SingleCopy\nG1\t12\t8\t3\nG0\t0\t0\t0\n", "codon_genome_counts")
    reads.append(counts)
    a["genome_counts_document_id"] = counts["result"]["value"]["table"]["table_id"]
    reported = read("synthetic-report", b"Statistics for CodonTree Analysis\nNum_genomes\t4\nNum_protein_alignments\t2\nNum_aligned_amino_acids\t4\nNum_CDS_alignments\t2\nNum_aligned_nucleotides\t12\nPGFams\tF1,F2\ncommand_line\tra xml -f I\nTotal job duration 17 seconds\n",
                    "codon_analysis_statistics", dialect="retained_current_source")
    reads.append(reported)
    a["analysis_stats_document_id"] = reported["result"]["value"]["table"]["table_id"]
    a["explicit_family_matrix_id"] = "matrix"
    joins = {k: [] for k in JOIN_KEYS}
    mapping = {"F1": {"G1": ["a", "b"], "G2": ["c"], "G3": ["d"], "G4": []},
               "F2": {"G1": ["e"], "G2": ["f"], "G3": ["g"], "G4": ["h"]}}
    rows = []
    for fid, genomes in mapping.items():
        for gid, features in genomes.items():
            rows.append({"family_id": fid, "genome_id": gid, "feature_ids": features, "evidence": []})
            joins["feature_genomes"].extend({"feature_id": f, "genome_id": gid, "family_id": fid,
                "family_namespace": "PGFam", "evidence": []} for f in features)
    population = gp(["G1", "G2", "G3", "G4"])
    pops = {k: [] for k in POP_KEYS}
    pops["genomes"] = [population]
    pops["families"] = [fp(["F1", "F2"])]
    assembly = {"version": "bvbrc_phylogeny_assembly_v1", "analysis_id": "a1", "caller_populations": pops,
        "locus_bindings": [], "genome_request_sets": [request_set(population)],
        "family_matrices": [{"matrix_id": "matrix", "namespace": "PGFam", "family_population_id": "families",
            "genome_population_id": "main", "rows": rows, "completeness": "complete", "evidence": []}],
        "historical_frequencies": [], "model_associations": []}
    if include_alignment:
        aid = a["final_alignment_id"]
        joins["input_rows"] = [{"alignment_id": aid, "row_index": i, "input_binding_id": "main-input", "member_id": g,
            "locus_id": "genome", "transformation_id": None, "evidence": []} for i, g in enumerate(population["genome_ids"])]
        joins["tip_rows"] = [{"tree_id": a["raw_tree_id"], "node_index": n["node_index"], "alignment_id": aid,
            "row_index": population["genome_ids"].index(n["decoded_label"]), "evidence": []}
            for n in tree["result"]["value"]["trees"][0]["nodes"] if not n["child_indices"]]
    return {"documents": envelope(reads, a), "inputs": (binding(population["genome_ids"]),),
            "observed_run": {"original_task_id": None, "source_revision": None, "settings": [], "commands": [],
                "engines": [], "conflicts": [], "completeness": "unknown"}, "joins": joins, "assembly": assembly,
            "parameters": {"source_dialect": "retained_codon_trees", "membership_dialect": "homologs_current",
                           "family_stats_dialect": "current_missing_header_tab"}}


def extract(args=None):
    result = provider.extract_codon_tree_sheet(**(fixture() if args is None else args))
    assert result["value"] is not None, result
    return result


def params(sheet, *, numerical=True):
    result = {"version": "codon_tree_components_v1", "alignment_requests": [], "original_coverage_population_ids": [],
        "tree_requests": [], "bootstrap_requests": [], "composition_population_ids": [], "taxon_requests": [],
        "comparisons": [], "literal_statistic_population_ids": [], "family_population_requests": [],
        "worst_sequence_population_id": None}
    if numerical:
        for p in sheet["populations"]["alignments"]:
            result["alignment_requests"].append({"population_id": p["population_id"], "alphabet": "unknown", "case_policy": "literal", "pairs": []})
            result["literal_statistic_population_ids"].append(p["population_id"])
        result["tree_requests"] = [{"population_id": p["population_id"], "branch_unit": "native_unknown", "pairs": []}
                                   for p in sheet["populations"]["leaves"]]
        result["family_population_requests"] = [{"family_population_id": "families", "genome_population_id": "main"}]
    return result


def historical(args, *, complete="complete", empty=False):
    population = fp([] if empty else ["F1", "F2"], pid="historical", stage="evaluated_pretrim", complete=complete)
    args["assembly"]["caller_populations"]["families"].append(population)
    table = args["documents"]["family_statistics"][0]["table"]["table_id"]
    data = [] if empty else [("F1", "a", "G1", -.5), ("F1", "c", "G2", -1.), ("F2", "e", "G1", -1.5), ("F2", "f", "G2", -3.)]
    args["assembly"]["historical_frequencies"] = [{"evaluated_family_population": {"population": population,
        "expected_sequence_memberships": [] if empty else [{"family_id": "F1", "feature_ids": ["a", "c"]},
            {"family_id": "F2", "feature_ids": ["e", "f"]}], "completeness": complete},
        "pretrim_sequence_rows": [{"family_id": fid, "feature_id": feature, "genome_id": genome,
            "value": cells.quantity(value, population=table + "/population/family/" + fid, unit="bits_per_column",
                method="row_mean_log2_literal_frequency")} for fid, feature, genome, value in data]}]


def native_fixture():
    """Complete retained historical artifacts, with explicit source-backed joins.

    The supplied main IDs come from the retained original ID file, not features
    or final leaves. Matrix completeness is deliberately unknown: a selected
    membership list does not establish all preselection absence cells.
    """
    directory = NATIVE / "test9_genome_dir"
    alignment = read("retained-final", (directory / (BASE + ".phy")).read_bytes(), "relaxed_phylip", layout="interleaved", continuation_ids="absent")
    membership = read("retained-membership", (directory / "test9_genome_8taxa_10cds_10proteins.pgfamsAndGenesIncludedInAlignment.txt").read_bytes(), "codon_membership", dialect="pgfams_legacy")
    tree = read("retained-tree", (directory / ("RAxML_bipartitions." + BASE)).read_bytes(), "newick", dialect="newick", allow_multiple=False)
    partitions = read("retained-partitions", (directory / (BASE + ".partitions")).read_bytes(), "raxml_partitions", alignment_column_count=15300)
    log = read("retained-log", (directory / ("RAxML_info." + BASE)).read_bytes(), "raxml_run_log", dialect="raxml_8")
    reads = [alignment, membership, tree, partitions, log]
    a = analysis()
    a.update(final_alignment_id=alignment["result"]["value"]["alignment_id"], membership_document_id=membership["result"]["value"]["table"]["table_id"],
        raw_tree_id=tree["result"]["value"]["trees"][0]["tree_id"], partition_document_id=partitions["result"]["value"]["document_id"],
        native_engine_observation_ids=[o["observation_id"] for o in log["result"]["value"]["observations"]])
    ids = (NATIVE / "test9_genome.ids").read_text().splitlines()[1:]
    inputs = binding(ids)
    joins = {k: [] for k in JOIN_KEYS}
    membership_features = {f for r in membership["result"]["value"]["rows"] for f in r["included_feature_ids"]}
    triples = [line.split("\t") for line in (directory / "test9_genome.genomeGenePgfams.txt").read_text().splitlines()]
    for gid, feature, fid in triples:
        if feature in membership_features:
            joins["feature_genomes"].append({"feature_id": feature, "genome_id": gid, "family_id": fid, "family_namespace": "PGFam", "evidence": []})
    # Exact explicit joins are fixture operands drawn from actual retained IDs.
    rows = alignment["result"]["value"]["rows"]
    for row in rows:
        assert row["member_label"] in ids
        joins["input_rows"].append({"alignment_id": a["final_alignment_id"], "row_index": row["row_index"],
            "input_binding_id": inputs["binding_id"], "member_id": row["member_label"], "locus_id": "retained-genome",
            "transformation_id": None, "evidence": []})
    for node in tree["result"]["value"]["trees"][0]["nodes"]:
        if not node["child_indices"]:
            matched = [r for r in rows if r["member_label"] == node["decoded_label"]]
            assert len(matched) == 1
            joins["tip_rows"].append({"tree_id": a["raw_tree_id"], "node_index": node["node_index"],
                "alignment_id": a["final_alignment_id"], "row_index": matched[0]["row_index"], "evidence": []})
    populations = {k: [] for k in POP_KEYS}
    populations["genomes"] = [gp(ids)]
    populations["families"] = [fp(list(dict.fromkeys(r["family_id"] for r in membership["result"]["value"]["rows"])), stage="selected")]
    model_associations = [{"read_id": log["read_id"], "log_model_index": i, "partition_document_id": a["partition_document_id"],
        "partition_index": m["partition_index"], "model_selection_command_id": None, "sample_alignment_id": None,
        "sample_column_map": None, "evidence": []} for i, m in enumerate(log["result"]["value"]["models"])]
    return {"documents": envelope(reads, a), "inputs": (inputs,),
        "observed_run": {"original_task_id": None, "source_revision": None, "settings": [], "commands": [], "engines": [], "conflicts": [], "completeness": "unknown"},
        "joins": joins, "assembly": {"version": "bvbrc_phylogeny_assembly_v1", "analysis_id": "a1", "caller_populations": populations,
            "locus_bindings": [], "genome_request_sets": [request_set(populations["genomes"][0])], "family_matrices": [],
            "historical_frequencies": [], "model_associations": model_associations},
        "parameters": {"source_dialect": "retained_codon_trees", "membership_dialect": "pgfams_legacy", "family_stats_dialect": None}}


def test_imports_and_exact_public_signatures():
    for module in (provider, grader, native, common):
        assert Path(module.__file__).resolve().parent == STAGING / "gene_annotation_episode"
    assert list(inspect.signature(provider.extract_codon_tree_sheet).parameters) == ["documents", "inputs", "observed_run", "joins", "assembly", "parameters"]
    assert list(inspect.signature(grader.calculate_codon_tree).parameters) == ["sheet", "parameters"]


def test_source_derived_tables_and_hand_numerical_components():
    value = extract()["value"]
    assert len(value["read_outcomes"]) == 6
    assert len(value["families"]) == 2
    family = value["families"][0]
    assert family["memberships"][0]["deleted_feature_ids"] == ["b"]
    assert family["memberships"][1]["missing_codon_feature_ids"] == ["d"]
    assert family["matrix"][3]["feature_ids"] == []
    assert any(d["code"] == "codon_reported_cds_uses_protein_count" for d in value["qualifications"])
    assert [x for x in value["observed_run"]["commands"] if "report" in x["command_id"]][0]["role"] == "unknown"
    output = grader.calculate_codon_tree(value, params(value))
    literal = output["literal_statistics"][0]
    assert literal["gaps"]["value"] == 2
    assert literal["literal_nongap_sum_squared_frequency"]["value"] == 2.875
    assert literal["literal_nongap_mean_squared_frequency"]["value"] == .71875
    assert literal["native_family_ranking_score"]["value"] == 1.4375
    row = output["family_populations"][0]["rows"][0]
    assert [row[k]["value"] for k in ("present_genomes", "missing_genomes", "extra_copies", "presence_fraction", "native_initial_family_rank")] == [3, 1, 1, .75, 2]
    assert output["trees"][0]["branch_length_sum"]["value"] == 6.4
    assert output["trees"][0]["branch_length_sum"]["unit"] == "native_unknown"
    assert len([g for g in value["dependence_groups"] if g["kind"] == "protein_and_coding_nucleotide"]) == 2


def test_retained_native_complete_membership_and_nine_row_final_matrix():
    value = extract(native_fixture())["value"]
    assert len(value["families"]) == 10
    assert sum(len(f["memberships"]) for f in value["families"]) == 20
    assert all(len(m["feature_ids"]) == 8 for f in value["families"] for m in f["memberships"])
    assert all(f["matrix_completeness"] == "unknown" and f["matrix"] == [] for f in value["families"])
    assert len(value["genomes"]) == 9
    assert len(value["models"]) == 4
    assert all(m["branch_optimization"] == "joint" for m in value["models"])
    assert all(m["sample_column_map"] is None for m in value["models"])
    output = grader.calculate_codon_tree(value, params(value))
    matrix = output["literal_statistics"][0]
    assert matrix["n_rows"]["value"] == 9
    assert matrix["n_columns"]["value"] == 15300
    assert matrix["gaps"]["value"] == 17308
    assert matrix["gap_fraction"]["value"] == 17308 / 137700
    assert matrix["literal_nongap_sum_squared_frequency"]["value"] == 10056.41975308642
    assert output["trees"][0]["tip_count"]["value"] == 9
    assert output["family_populations"][0]["rows"][0]["presence_fraction"]["value"] is None
    assert any(o["value"] == -56958.397755 and o["field"] == "log_likelihood" for o in value["native_measurements"])


def test_null_alignment_preserves_membership_and_independent_tree():
    value = extract(fixture(include_alignment=False))["value"]
    assert value["documents"]["analyses"][0]["final_alignment_id"] is None
    assert len(value["families"]) == 2
    output = grader.calculate_codon_tree(value, params(value))
    assert output["alignments"] == []
    assert output["trees"][0]["tip_count"]["value"] == 4


def test_partial_matrix_does_not_create_absence_or_requested_population():
    args = fixture()
    args["assembly"]["family_matrices"][0]["rows"].pop(3)
    args["assembly"]["family_matrices"][0]["completeness"] = "partial"
    value = extract(args)["value"]
    output = grader.calculate_codon_tree(value, params(value))
    assert output["family_populations"][0]["population_genomes"]["value"] == 4
    assert output["family_populations"][0]["rows"][0]["missing_genomes"]["value"] is None


@pytest.mark.parametrize("mutation,code", [
    (lambda a: a["assembly"]["family_matrices"][0]["rows"].pop(3), "matrix_incomplete_cartesian_population"),
    (lambda a: a["assembly"]["family_matrices"][0]["rows"].append(deepcopy(a["assembly"]["family_matrices"][0]["rows"][0])), "duplicate_matrix_cell"),
    (lambda a: a["assembly"]["family_matrices"][0]["rows"][1]["feature_ids"].append("a"), "duplicate_matrix_feature"),
    (lambda a: a["joins"]["feature_genomes"][0].update(genome_id="G2"), "matrix_feature_join_conflict"),
    (lambda a: a["inputs"][0]["inline_value"].pop(), "request_membership_conflict"),
    (lambda a: a["documents"]["parsed"]["analyses"].append(deepcopy(a["documents"]["parsed"]["analyses"][0])), "one_primary_analysis_required"),
])
def test_structural_extraction_conflicts_are_specific(mutation, code):
    args = fixture()
    mutation(args)
    result = provider.extract_codon_tree_sheet(**args)
    assert result["status"] == "invalid" and result["value"] is None
    assert any(d["code"].endswith(code) for d in result["diagnostics"]), result


def test_missing_namespace_preserves_raw_table_without_inventing_family():
    args = fixture()
    args["assembly"]["family_matrices"] = []
    args["documents"]["parsed"]["analyses"][0]["explicit_family_matrix_id"] = None
    args["joins"]["feature_genomes"] = []
    value = extract(args)["value"]
    assert value["families"] == []
    assert len(value["documents"]["store"]["native_tables"]) == 4
    assert any(r["reason_code"] == "family_namespace_required" for r in value["missing_requirements"])


def test_duplicate_native_feature_retains_original_row_and_explicit_unique_projection():
    result = extract(fixture(membership_bytes=b"F1\tProteins\t\ta\ta\nF2\tProteins\t\te\nF2\tCodons\t\te\n"))
    value = result["value"]
    native_row = value["documents"]["store"]["native_tables"][0]["rows"][0]
    assert native_row["fields"][-2:] == ["a", "a"]
    assert value["families"][0]["memberships"][0]["feature_ids"] == ["a"]
    assert any(d["code"] == "codon_duplicate_feature_id" for d in value["read_outcomes"][2]["diagnostics"])
    assert any(d["code"] == "codon_provider_native_membership_unique_projection" for d in value["qualifications"])
    assert grader.calculate_codon_tree(value, params(value))["family_populations"][0]["rows"][0]["present_genomes"]["value"] == 3


@pytest.mark.parametrize("complete", ["complete", "unknown", "partial", "truncated"])
def test_historical_empty_population_semantics(complete):
    args = fixture()
    historical(args, complete=complete, empty=True)
    value = extract(args)["value"]
    selected = params(value, numerical=False)
    selected["worst_sequence_population_id"] = "historical"
    output = grader.calculate_codon_tree(value, selected)
    history = output["worst_sequence_ratios"]
    assert history["rows"] == history["genome_means"] == history["family_maxima"] == []
    assert bool(history["missing_requirements"]) == (complete != "complete")
    assert all(r in output["missing_requirements"] for r in history["missing_requirements"])


def test_historical_full_population_hand_means_ratios_and_native_stage_separation():
    args = fixture()
    historical(args)
    value = extract(args)["value"]
    selected = params(value, numerical=False)
    selected["worst_sequence_population_id"] = "historical"
    history = grader.calculate_codon_tree(value, selected)["worst_sequence_ratios"]
    assert [r["mean"]["value"] for r in history["genome_means"]] == [-1., -2.]
    assert [r["ratio"]["denominator"] for r in history["rows"]] == [-1.00001, -2.00001, -1.00001, -2.00001]
    assert history["rows"][0]["ratio"]["value"] == -.5 / -1.00001
    assert next(o for o in value["native_measurements"] if o["field"] == "family_native_length")["value"] == 4


def test_final_alignment_cannot_supply_historical_population():
    args = fixture()
    historical(args)
    aid = args["documents"]["parsed"]["analyses"][0]["final_alignment_id"]
    ap = {"population_id": "fake-history", "alignment_id": aid, "row_indices": [0, 1], "columns_0based": [0, 1], "completeness": "complete", "evidence": []}
    args["assembly"]["caller_populations"]["alignments"].append(ap)
    for row in args["assembly"]["historical_frequencies"][0]["pretrim_sequence_rows"]:
        row["value"]["population_ref"] = "fake-history"
        row["value"]["evidence"] = [evidence()]
    result = provider.extract_codon_tree_sheet(**args)
    assert result["status"] == "invalid"
    assert result["diagnostics"][-1]["code"] == "codon_provider_history_original_population_required"


@pytest.mark.parametrize("mutation,code", [
    (lambda s: s["families"][0]["matrix"][0]["feature_ids"].append("invented"), "family_matrix_source_conflict"),
    (lambda s: s["families"][0]["memberships"][0].update(source_row_index=1), "membership_native_fields_conflict"),
    (lambda s: s["families"][0]["memberships"][0].update(genome_ids=["G4"]), "membership_genome_conflict"),
    (lambda s: s["families"][0].update(matrix_completeness="unknown"), "family_matrix_completeness_conflict"),
    (lambda s: s["genomes"][0]["final_alignment_rows"][0].update(row_index=1), "genome_row_conflict"),
    (lambda s: s["families"][0]["native_statistic_observation_ids"].append("absent"), "family_statistic_reference_conflict"),
    (lambda s: s["families"][0].update(final_block_indices=[0]), "family_block_reference_conflict"),
])
def test_saved_sheet_rejects_changed_relationships(mutation, code):
    value = extract()["value"]
    mutation(value)
    with pytest.raises(ValueError, match=code):
        provider.validate_codon_tree_sheet(value)


def test_original_coverage_unavailable_keeps_final_arithmetic():
    value = extract()["value"]
    selected = params(value)
    selected["original_coverage_population_ids"] = [value["populations"]["alignments"][0]["population_id"]]
    output = grader.calculate_codon_tree(value, selected)
    assert output["literal_statistics"][0]["gap_fraction"]["value"] == .125
    assert all(row["original_member_coverage"]["value"] is None for row in output["original_coverage"][0]["rows"])


def test_saved_json_recalculation_no_io_network_execution_or_parsing():
    args = fixture()
    historical(args)
    value = extract(args)["value"]
    selected = params(value)
    selected["worst_sequence_population_id"] = "historical"
    saved = json.loads(json.dumps({"sheet": value, "parameters": selected}, allow_nan=False))
    before = deepcopy(saved)
    expected = grader.calculate_codon_tree(saved["sheet"], saved["parameters"])
    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden acquisition/parsing during saved recalculation")
    from contextlib import ExitStack
    with ExitStack() as stack:
        for target in ((builtins, "open"), (io, "open"), (socket, "socket"), (socket, "create_connection"),
                       (subprocess, "Popen"), (subprocess, "run"), (os, "system"), (formats, "parse_newick"),
                       (formats, "parse_aligned_fasta"), (formats, "parse_relaxed_phylip"), (formats, "parse_raxml_partitions"),
                       (native, "parse_codon_membership"), (native, "parse_codon_family_statistics"),
                       (native, "parse_codon_genome_counts"), (native, "parse_codon_analysis_statistics"), (raxml, "parse_raxml_run_log")):
            stack.enter_context(patch.object(*target, side_effect=forbidden))
        actual = grader.calculate_codon_tree(saved["sheet"], saved["parameters"])
    assert actual == expected
    assert saved == before


def test_extraction_does_not_mutate_inputs_and_returns_detached_values():
    args = fixture()
    before = deepcopy(args)
    result = extract(args)
    assert args == before
    result["value"]["families"][0]["matrix"][0]["feature_ids"].append("modified")
    assert args == before


def with_requested_sets(args):
    optional = binding(["Goptional", "G1"], "optional-input", "/optional_genome_ids")
    optional_pop = gp(optional["inline_value"], "optional", "requested_optional")
    group = binding(["G2", "Ggroup"], "group-input", "/genome_groups/0")
    group.update(kind="workspace_object", workspace_path="/workspace/group", inline_value=None)
    group_evidence = evidence("synthetic-group-response")
    for i, member in enumerate(group["members"]):
        member["evidence"] = {**group_evidence, "pointer": "/genome_ids/" + str(i)}
    group_pop = gp(["G2", "Ggroup"], "group")
    group_pop["evidence"] = [group_evidence]
    group_set = request_set(group_pop, "group-input", "group_members", "group-set")
    group_set["group_id"] = "/workspace/group"
    union_pop = gp(["G1", "G2", "G3", "G4", "Ggroup"], "main-union")
    union_set = request_set(union_pop, kind="main_union", sid="main-union-set")
    union_set.update(input_binding_ids=[], derived_from_set_ids=["main-set", "group-set"])
    args["inputs"] += (optional, group)
    args["assembly"]["caller_populations"]["genomes"] += [optional_pop, group_pop, union_pop]
    args["assembly"]["genome_request_sets"] += [request_set(optional_pop, "optional-input", "optional_ids", "optional-set"), group_set, union_set]
    return args


def test_main_optional_group_and_explicit_union_remain_distinct():
    value = extract(with_requested_sets(fixture()))["value"]
    sets = {r["kind"]: r for r in value["assembly"]["genome_request_sets"]}
    assert sets["main_ids"]["population"]["genome_ids"] == ["G1", "G2", "G3", "G4"]
    assert sets["optional_ids"]["population"]["genome_ids"] == ["Goptional", "G1"]
    assert sets["group_members"]["population"]["genome_ids"] == ["G2", "Ggroup"]
    assert sets["main_union"]["population"]["genome_ids"] == ["G1", "G2", "G3", "G4", "Ggroup"]
    assert not any(p["stage"] == "actually_forwarded_optional" for p in value["populations"]["genomes"])
    assert any(r["reason_code"] == "optional_forwarding_required" for r in value["missing_requirements"])
    group = next(g for g in value["genomes"] if g["genome_id"] == "Ggroup")
    assert group["input_members"] == [{"input_binding_id": "group-input", "member_id": "Ggroup"}]
    assert group["final_alignment_rows"] == group["final_tree_tips"] == []
    assert all(i["state"] == "included" and i["stage"] == "requested" for i in group["inclusion"])
    selected = params(value, numerical=False)
    selected["family_population_requests"] = [{"family_population_id": "families", "genome_population_id": "main-union"}]
    out = grader.calculate_codon_tree(value, selected)["family_populations"][0]
    assert out["population_genomes"]["value"] == 5
    assert out["rows"][0]["presence_fraction"]["value"] is None


@pytest.mark.parametrize("change,code", [
    (lambda a: a["assembly"]["genome_request_sets"][-1]["derived_from_set_ids"].append("optional-set"), "request_union_invalid"),
    (lambda a: a["inputs"][-1]["members"][0].update(evidence=None), "group_membership_evidence_missing"),
    (lambda a: a["inputs"][-1].update(workspace_path="/wrong/group"), "request_group_binding_conflict"),
])
def test_requested_set_relationships_are_checked(change, code):
    args = with_requested_sets(fixture())
    change(args)
    result = provider.extract_codon_tree_sheet(**args)
    assert result["value"] is None
    assert result["diagnostics"][-1]["code"].endswith(code)


def forwarded_optional(args, *, observed=True, option=True):
    source = evidence("forwarded-optional-file")
    operand = binding(["Goptional"], "forwarded-input", "/actual_optional_input")
    operand.update(kind="retained_bytes", inline_value=None, content=source["content"], workspace_path="/job/opt_genomes.in")
    operand["members"][0]["evidence"] = source
    args["inputs"] += (operand,)
    witness = evidence("actual-command", "/argv/2")
    pop = gp(["Goptional"], "forwarded", "actually_forwarded_optional")
    pop["evidence"] = [witness]
    args["assembly"]["caller_populations"]["genomes"].append(pop)
    args["assembly"]["genome_request_sets"].append(request_set(pop, "forwarded-input", "actually_forwarded_optional", "forwarded-set"))
    args["observed_run"]["commands"].append({"command_id": "actual-launch", "role": "unknown",
        "argv": ["p3x-build-codon-tree.py", "--optionalGenomeIdsFile" if option else "--genomeIdsFile", "/job/opt_genomes.in"],
        "raw_text": None, "origin": "observed" if observed else "source_expected", "evidence": [witness], "location": None})
    return args


def test_forwarded_optional_requires_observed_invocation_and_actual_operand():
    value = extract(forwarded_optional(fixture()))["value"]
    actual = next(g for g in value["genomes"] if g["genome_id"] == "Goptional")
    assert actual["input_members"] == [{"input_binding_id": "forwarded-input", "member_id": "Goptional"}]
    assert next(p for p in value["populations"]["genomes"] if p["population_id"] == "forwarded")["stage"] == "actually_forwarded_optional"
    for observed, option in ((False, True), (True, False)):
        result = provider.extract_codon_tree_sheet(**forwarded_optional(fixture(), observed=observed, option=option))
        assert result["value"] is None
        assert result["diagnostics"][-1]["code"] == "codon_provider_forwarded_optional_actual_input_required"


@pytest.mark.parametrize("complete", ["complete", "unknown"])
def test_empty_main_population_is_distinct_from_unknown_main_population(complete):
    args = fixture(membership_bytes=b"")
    args["inputs"] = (binding([]),)
    if complete == "unknown":
        args["inputs"][0]["inline_value"] = None
    main = gp([], complete=complete)
    args["assembly"]["caller_populations"]["genomes"][0] = main
    args["assembly"]["genome_request_sets"][0]["population"] = deepcopy(main)
    args["assembly"]["family_matrices"][0].update(rows=[], completeness=complete)
    args["joins"]["input_rows"] = args["joins"]["tip_rows"] = []
    value = extract(args)["value"]
    output = grader.calculate_codon_tree(value, params(value))["family_populations"][0]
    assert output["population_genomes"]["value"] == (0 if complete == "complete" else None)
    assert output["rows"][0]["presence_fraction"]["value"] is None
    assert any(r["reason_code"] == "requested_genome_membership_required" for r in value["missing_requirements"]) == (complete == "unknown")


def test_missing_feature_join_preserves_membership_and_independent_matrix():
    args = fixture()
    args["assembly"]["family_matrices"] = []
    args["documents"]["parsed"]["analyses"][0]["explicit_family_matrix_id"] = None
    args["joins"]["feature_genomes"] = [j for j in args["joins"]["feature_genomes"] if j["feature_id"] != "a"]
    value = extract(args)["value"]
    membership = value["families"][0]["memberships"][0]
    assert membership["feature_ids"] == ["a", "c", "d"]
    assert membership["genome_ids"] == ["G2", "G3"]
    assert any(r["reason_code"] == "feature_genome_association_required" for r in value["missing_requirements"])
    assert grader.calculate_codon_tree(value, params(value))["literal_statistics"][0]["gaps"]["value"] == 2


def test_native_contradictory_membership_omits_only_typed_record():
    result = extract(fixture(membership_bytes=b"F1\tProteins\t\ta\tdeletedParalogs: \ta\nF1\tCodons\t\tc\nF2\tProteins\t\te\n"))
    value = result["value"]
    assert result["status"] == "partial"
    assert value["documents"]["store"]["native_tables"][0]["rows"][0]["fields"] == ["F1", "Proteins", "", "a", "deletedParalogs: ", "a"]
    assert [m["representation"] for m in value["families"][0]["memberships"]] == ["coding_nucleotide"]
    assert any(r["reason_code"] == "native_membership_conflict" for r in value["missing_requirements"])
    assert grader.calculate_codon_tree(value, params(value))["trees"][0]["tip_count"]["value"] == 4


def test_duplicate_native_missing_family_messages_keep_original_occurrences():
    value = extract(fixture(membership_bytes=b"F1\nNo codon alignment F1\nF1\nNo codon alignment F1\n"))["value"]
    rows = value["documents"]["store"]["native_tables"][0]["rows"]
    assert len(rows) == 4
    assert [p for p in value["populations"]["families"] if p["stage"] == "selected"][0]["family_ids"] == ["F1"]
    assert any(i["reason"] == "missing_codon_alignment" for i in value["families"][0]["inclusion"])


def test_explicit_final_family_blocks_do_not_use_pretrim_lengths():
    args = fixture()
    aid = args["documents"]["parsed"]["analyses"][0]["final_alignment_id"]
    args["joins"]["family_blocks"] = [
        {"alignment_id": aid, "family_id": "F1", "representation": "protein", "columns_0based": [0, 1],
         "member_row_indices": [0, 1, 2], "evidence": [evidence("final-blocks", "/F1/protein")]},
        {"alignment_id": aid, "family_id": "F1", "representation": "coding_nucleotide", "columns_0based": [2, 3],
         "member_row_indices": [0, 1], "evidence": [evidence("final-blocks", "/F1/cds")]},
    ]
    value = extract(args)["value"]
    assert value["families"][0]["final_block_indices"] == [0, 1]
    native_length = next(o for o in value["native_measurements"] if o["subject_id"] == "F1" and o["field"] == "family_native_length")
    assert native_length["value"] == 4
    assert len(value["joins"]["family_blocks"][0]["columns_0based"]) == 2
    value["joins"]["family_blocks"][1]["columns_0based"] = [1, 2]
    with pytest.raises(ValueError, match="family_blocks_overlap"):
        provider.validate_codon_tree_sheet(value)


@pytest.mark.parametrize("change,code", [
    (lambda s: s["families"].pop(), "family_records_incomplete"),
    (lambda s: s["genomes"].pop(), "genome_records_incomplete"),
    (lambda s: s["families"][0]["memberships"].pop(), "membership_records_incomplete"),
    (lambda s: s["families"][0]["inclusion"][0].update(state="excluded"), "family_inclusion_source_conflict"),
    (lambda s: s["genomes"][0]["inclusion"][0].update(reason="zero_family_records"), "genome_inclusion_source_conflict"),
    (lambda s: s["populations"]["genomes"][-1]["genome_ids"].pop(), "biological_population_source_conflict"),
    (lambda s: s["genomes"][0]["input_members"].clear(), "genome_input_members_incomplete"),
    (lambda s: s["families"][0]["native_statistic_observation_ids"].clear(), "family_statistic_source_conflict"),
])
def test_saved_sheet_rejects_omission_and_invented_stage(change, code):
    value = extract()["value"]
    change(value)
    with pytest.raises(ValueError, match=code):
        provider.validate_codon_tree_sheet(value)


def test_invalid_alignment_read_preserves_every_original_outcome_and_valid_tree():
    args = fixture(include_alignment=False)
    bad = read("malformed-alignment", b"\xff\n", "aligned_fasta",
               id_rule="first_whitespace_token", encoding="ascii")
    assert bad["result"]["value"] is None
    args["documents"]["reads"].append(bad)
    expected_reads = deepcopy(args["documents"]["reads"])
    value = extract(args)["value"]
    for original, outcome in zip(expected_reads, value["read_outcomes"], strict=True):
        assert outcome["status"] == original["result"]["status"]
        assert outcome["diagnostics"] == original["result"]["diagnostics"]
        assert outcome["value_present"] == (original["result"]["value"] is not None)
    assert bad["artifact"] in value["artifact_refs"]
    result = grader.calculate_codon_tree(value, params(value))
    assert result["trees"][0]["tip_count"]["value"] == 4
    assert result["alignments"] == []


@pytest.mark.parametrize("change,code", [
    (lambda a: a["assembly"]["model_associations"][0].update(log_model_index=500), "model_index_outside_read"),
    (lambda a: a["assembly"]["model_associations"][0].update(read_id="absent"), "model_read_missing"),
    (lambda a: a["assembly"]["model_associations"][0].update(partition_index=1), "model_partition_identity_conflict"),
    (lambda a: a["assembly"]["model_associations"][0].update(partition_document_id=None), "model_partition_pair_invalid"),
    (lambda a: a["assembly"]["model_associations"].append(deepcopy(a["assembly"]["model_associations"][0])), "duplicate_model_association"),
])
def test_model_associations_check_actual_log_indices_and_partitions(change, code):
    args = native_fixture()
    change(args)
    result = provider.extract_codon_tree_sheet(**args)
    assert result["value"] is None
    assert result["diagnostics"][-1]["code"].endswith(code), result["diagnostics"][-1]


def model_sample_fixture():
    args = native_fixture()
    sample = read("supplied-model-sample", b">sample1\nAC\n>sample2\nAX\n", "aligned_fasta",
                  id_rule="first_whitespace_token", encoding="ascii")
    args["documents"]["reads"].append(sample)
    args["documents"]["parsed"]["store"]["alignments"].append(sample["result"]["value"])
    ev = evidence("model-selection", "/sample/columns")
    args["observed_run"]["commands"].append({"command_id": "model-selection", "role": "model_selection",
        "argv": ["raxmlHPC", "-m", "PROTCATAUTO"], "raw_text": None, "origin": "observed", "evidence": [ev], "location": None})
    args["assembly"]["model_associations"][-1].update(model_selection_command_id="model-selection",
        sample_alignment_id=sample["result"]["value"]["alignment_id"], sample_column_map=[11475, 11476], evidence=[ev])
    return args


def test_exact_observed_model_sample_mapping_and_empirical_frequency_partition():
    value = extract(model_sample_fixture())["value"]
    assert value["models"][-1]["model_token"] == "LGF"
    assert value["models"][-1]["datatype"] == "protein"
    assert value["models"][-1]["sample_column_map"] == [11475, 11476]
    assert value["models"][-1]["model_selection_command_id"] == "model-selection"
    assert all(f["final_block_indices"] == [] for f in value["families"])
    assert sum(p["name"].startswith("freq pi(") for p in value["models"][-1]["parameters"]) == 20
    selected = params(value, numerical=False)
    assert grader.calculate_codon_tree(value, selected)["parameters"] == selected


@pytest.mark.parametrize("change,code", [
    (lambda a: a["assembly"]["model_associations"][-1].update(sample_column_map=[11475]), "model_sample_map_conflict"),
    (lambda a: a["assembly"]["model_associations"][-1].update(sample_column_map=[11475, 15300]), "model_sample_map_conflict"),
    (lambda a: a["assembly"]["model_associations"][-1].update(sample_column_map=[11475, 11475]), "duplicate_index"),
    (lambda a: a["assembly"]["model_associations"][-1].update(evidence=[]), "model_sample_map_conflict"),
    (lambda a: a["observed_run"]["commands"][0].update(origin="requested"), "model_selection_command_conflict"),
    (lambda a: a["assembly"]["model_associations"][-1].update(sample_alignment_id=None), "model_sample_map_without_sample"),
])
def test_model_sampling_does_not_guess_correspondence(change, code):
    args = model_sample_fixture()
    change(args)
    result = provider.extract_codon_tree_sheet(**args)
    assert result["value"] is None
    assert result["diagnostics"][-1]["code"].endswith(code), result["diagnostics"][-1]


def test_model_sample_without_map_is_null_with_specific_requirement():
    args = model_sample_fixture()
    args["assembly"]["model_associations"][-1]["sample_column_map"] = None
    value = extract(args)["value"]
    assert value["models"][-1]["sample_column_map"] is None
    assert any(r["reason_code"] == "model_sample_correspondence_required" for r in value["missing_requirements"])


def test_missing_model_log_associations_preserve_unknown_partition_models():
    args = native_fixture()
    args["assembly"]["model_associations"] = []
    value = extract(args)["value"]
    assert len(value["models"]) == 4
    assert all(m["branch_optimization"] == "unknown" and m["parameters"] == [] for m in value["models"])
    assert all(f["final_block_indices"] == [] for f in value["families"])
    assert sum(r["reason_code"] == "partition_model_association_required" for r in value["missing_requirements"]) == 4


def test_saved_model_validation_checks_sources_without_reconstructing_input_only_array():
    value = extract(native_fixture())["value"]
    # The frozen saved shape does not contain the original RAxML model array.
    # Its extraction-time index range cannot be authenticated during replay.
    value["assembly"]["model_associations"][0]["log_model_index"] = 999
    assert provider.validate_codon_tree_sheet(value) == value
    value["models"][0]["parameters"][0]["native_location"]["artifact"] = value["documents"]["store"]["alignments"][0]["artifact"]
    with pytest.raises(ValueError, match="model_parameter_source_conflict"):
        provider.validate_codon_tree_sheet(value)


@pytest.mark.parametrize("change", [
    lambda s: s.update(unexpected=True),
    lambda s: s["families"][0].update(unexpected=True),
    lambda s: s["families"].__setitem__(0, None),
    lambda s: s["genomes"][0].update(input_members=None),
    lambda s: s["assembly"]["family_matrices"][0].pop("rows"),
    lambda s: s["families"][0]["memberships"][0].update(feature_ids="a"),
])
def test_saved_validation_uses_stable_valueerrors_for_malformed_shapes(change):
    value = extract()["value"]
    change(value)
    with pytest.raises(ValueError, match="^(codon_provider_|phylogeny_|bvbrc_phylogeny_)"):
        provider.validate_codon_tree_sheet(value)


def test_closed_component_and_sheet_shapes_and_unknown_methods():
    value = extract()["value"]
    assert set(value) == {"schema_version", "tool", "mode", "inputs", "artifact_refs", "observed_run", "documents", "joins",
        "populations", "native_measurements", "support_observations", "dependence_groups", "qualifications", "missing_requirements",
        "assembly", "read_outcomes", "genomes", "families", "models"}
    result = grader.calculate_codon_tree(value, params(value))
    assert set(result) == {"schema_version", "parameters", "alignments", "trees", "bootstrap", "coordinate_maps", "original_coverage",
        "composition", "taxonomy", "comparisons", "literal_statistics", "family_populations", "worst_sequence_ratios",
        "missing_requirements", "diagnostics"}
    assert all(o["method"] == "native_unknown" for o in value["support_observations"])
    zero = [o for o in value["native_measurements"] if o["field"] == "branch_support_native" and o["raw_token"] == "0"]
    assert zero and zero[0]["value"] == 0


def scoped_outside_membership_fixture(*, empty=False):
    args = fixture(membership_bytes=(b"F1\tProteins\t\ta\tc\td\toutside\tdeletedParalogs: \tb\n"
        b"F1\tCodons\t\ta\tc\toutside\tlacking CodonAlignment for F1: \td\n"
        b"F2\tProteins\t\te\tf\tg\th\nF2\tCodons\t\te\tf\tg\th\n"))
    args["joins"]["feature_genomes"].append({"feature_id": "outside", "genome_id": "Goptional",
        "family_id": "F1", "family_namespace": "PGFam", "evidence": []})
    optional = binding(["Goptional"], "optional-input", "/optional_genome_ids")
    pop = gp(["Goptional"], "optional", "requested_optional")
    args["inputs"] += (optional,)
    args["assembly"]["caller_populations"]["genomes"].append(pop)
    args["assembly"]["genome_request_sets"].append(request_set(pop, "optional-input", "optional_ids", "optional-set"))
    if empty:
        args["inputs"] = (binding([]), optional)
        pop = gp([])
        args["assembly"]["caller_populations"]["genomes"][0] = pop
        args["assembly"]["genome_request_sets"][0]["population"] = deepcopy(pop)
        args["assembly"]["family_matrices"][0]["rows"] = []
        args["joins"]["input_rows"] = args["joins"]["tip_rows"] = []
    return args


@pytest.mark.parametrize("empty", [False, True])
def test_complete_main_matrix_retains_independent_outside_optional_memberships(empty):
    value = extract(scoped_outside_membership_fixture(empty=empty))["value"]
    assert "outside" in value["families"][0]["memberships"][0]["feature_ids"]
    assert all(r["genome_id"] != "Goptional" for r in value["families"][0]["matrix"])
    output = grader.calculate_codon_tree(value, params(value))["family_populations"][0]
    assert output["population_genomes"]["value"] == (0 if empty else 4)
    assert output["rows"][0]["present_genomes"]["value"] == (0 if empty else 3)
    assert output["rows"][0]["missing_genomes"]["value"] == (0 if empty else 1)
    assert output["rows"][0]["extra_copies"]["value"] == (0 if empty else 1)
    assert output["rows"][0]["presence_fraction"]["value"] == (None if empty else .75)


@contextmanager
def offline_guard():
    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden I/O, acquisition, execution or parsing")
    with ExitStack() as stack:
        for module, name in ((builtins, "open"), (io, "open"), (socket, "socket"), (socket, "create_connection"),
                       (subprocess, "Popen"), (subprocess, "run"), (os, "system"), (formats, "parse_newick"),
                       (formats, "parse_aligned_fasta"), (formats, "parse_relaxed_phylip"), (formats, "parse_raxml_partitions"),
                       (formats, "parse_phyloxml"), (native, "parse_codon_membership"), (native, "parse_codon_family_statistics"),
                       (native, "parse_codon_genome_counts"), (native, "parse_codon_analysis_statistics"), (raxml, "parse_raxml_run_log")):
            stack.enter_context(patch.object(module, name, side_effect=forbidden))
        yield


@pytest.mark.parametrize("case", ["native", "null_alignment", "duplicate_membership", "historical", "missing_namespace"])
def test_full_examples_recalculate_with_io_and_all_readers_disabled(case):
    if case == "native":
        args = native_fixture()
    elif case == "null_alignment":
        args = fixture(include_alignment=False)
    elif case == "duplicate_membership":
        args = fixture(membership_bytes=b"F1\tProteins\t\ta\ta\nF2\tProteins\t\te\nF2\tCodons\t\te\n")
    else:
        args = fixture()
        if case == "historical":
            historical(args)
        else:
            args["assembly"]["family_matrices"] = []
            args["documents"]["parsed"]["analyses"][0]["explicit_family_matrix_id"] = None
            args["joins"]["feature_genomes"] = []
    value = extract(args)["value"]
    selected = params(value)
    if case == "historical":
        selected["worst_sequence_population_id"] = "historical"
    saved = json.loads(json.dumps({"sheet": value, "parameters": selected}, allow_nan=False))
    before = deepcopy(saved)
    expected = grader.calculate_codon_tree(saved["sheet"], saved["parameters"])
    with offline_guard():
        actual = grader.calculate_codon_tree(saved["sheet"], saved["parameters"])
    assert actual == expected
    assert saved == before


def test_extraction_itself_operates_only_on_supplied_parsed_objects():
    args = fixture()
    expected = extract(args)
    with offline_guard():
        actual = provider.extract_codon_tree_sheet(**args)
    assert actual == expected


def test_saved_sheet_cannot_remove_protein_cds_dependence():
    value = extract()["value"]
    value["dependence_groups"] = [g for g in value["dependence_groups"] if g["kind"] != "protein_and_coding_nucleotide"]
    with pytest.raises(ValueError, match="protein_codon_dependence_missing"):
        provider.validate_codon_tree_sheet(value)


def test_complete_matrix_cannot_omit_known_inside_scope_native_features():
    args = fixture()
    args["assembly"]["family_matrices"][0]["rows"][0]["feature_ids"] = []
    result = provider.extract_codon_tree_sheet(**args)
    assert result["value"] is None
    assert result["diagnostics"][-1]["code"] == "codon_provider_membership_feature_missing_from_complete_matrix"


def test_conflicting_native_disqualification_remains_unknown_and_raw():
    args = fixture()
    source = (b"PGFam\tgaps\tsum_squared_freq\tmean_squared_freq\tnum_pos\tnum_seqs\tworstSeqScoreused_in_tree\n"
        b"F1\t0\t0\t0\t0\t0\tna\tFalse\ndisqualification: bad seqs\ndisqualification: low alignment score\n")
    replacement = read("synthetic-stats", source, "codon_family_statistics", dialect="current_missing_header_tab")
    reads = [replacement if r["read_id"] == replacement["read_id"] else r for r in args["documents"]["reads"]]
    args["documents"] = envelope(reads, args["documents"]["parsed"]["analyses"][0])
    result = extract(args)
    assert result["status"] == "partial"
    inclusion = [i for i in result["value"]["families"][0]["inclusion"] if i["stage"] == "selected"]
    assert inclusion[0]["state"] == "excluded" and inclusion[0]["reason"] is None
    assert any(d["code"] == "codon_conflicting_qualifier" for d in result["value"]["qualifications"])
    assert grader.calculate_codon_tree(result["value"], params(result["value"]))["literal_statistics"][0]["gaps"]["value"] == 2


def test_invalid_with_value_matrix_read_survives_beside_independent_tree():
    args = fixture(include_alignment=False)
    invalid = read("invalid-with-value", b"no FASTA header\n", "aligned_fasta", id_rule="first_whitespace_token", encoding="ascii")
    assert invalid["result"]["status"] == "invalid" and invalid["result"]["value"] is not None
    args["documents"]["reads"].append(invalid)
    args["documents"]["parsed"]["store"]["alignments"].append(invalid["result"]["value"])
    value = extract(args)["value"]
    assert value["read_outcomes"][-1]["status"] == "invalid"
    assert value["read_outcomes"][-1]["value_present"] is True
    assert invalid["result"]["value"] in value["documents"]["store"]["alignments"]
    selected = params(value, numerical=False)
    selected["tree_requests"] = [{"population_id": value["populations"]["leaves"][0]["population_id"],
                                  "branch_unit": "native_unknown", "pairs": []}]
    assert grader.calculate_codon_tree(value, selected)["trees"][0]["tip_count"]["value"] == 4


def test_conflicting_fitted_models_remain_separate_with_explicit_error():
    args = native_fixture()
    parameter = args["documents"]["raxml_runs"][0]["models"][0]["parameters"][0]
    lines = (NATIVE / "test9_genome_dir" / ("RAxML_info." + BASE)).read_bytes().splitlines(keepends=True)
    # This is explicitly a new synthetic conflicting log, with its own digest;
    # it does not claim the altered value came from the retained native file.
    lines[parameter["native_location"]["line_start_1based"] - 1] = (
        parameter["name"] + ": " + str(parameter["value"] + 1) + "\n").encode("ascii")
    changed = read("synthetic-conflicting-log", b"".join(lines), "raxml_run_log", dialect="raxml_8")
    args["documents"]["reads"].append(changed)
    args["documents"]["raxml_runs"].append(changed["result"]["value"])
    for association in deepcopy(args["assembly"]["model_associations"]):
        association["read_id"] = changed["read_id"]
        args["assembly"]["model_associations"].append(association)
    result = extract(args)
    value = result["value"]
    assert result["status"] == "partial" and len(value["models"]) == 8
    assert value["models"][0]["parameters"][0]["value"] + 1 == value["models"][4]["parameters"][0]["value"]
    assert any(d["code"] == "codon_provider_model_record_conflict" and d["severity"] == "error" for d in value["qualifications"])
    value["qualifications"] = [d for d in value["qualifications"] if d["code"] != "codon_provider_model_record_conflict"]
    with pytest.raises(ValueError, match="model_conflict_qualification_missing"):
        provider.validate_codon_tree_sheet(value)


def sequence_member_fixture(*, exact=False, conflict=False):
    args = fixture()
    source = evidence("synthetic-original-sequence-object", "")
    original = binding(["sequence-0", "sequence-1"], "sequence-input", "/sequence_file")
    original.update(kind="retained_bytes", content=source["content"], workspace_path="/input/sequences.json", inline_value=None)
    records = []
    for i, member in enumerate(original["members"]):
        pointer = "/records/" + str(i)
        member.update(member_pointer=pointer, evidence={**source, "pointer": pointer if exact else ""})
        gid = "G" + str(i + 1)
        records.append({"source_record_id": "genome-source-" + gid,
            "subject": {"kind": "genome", "id": gid, "source_record_id": "genome-source-" + gid},
            "artifact": None, "evidence": [deepcopy(member["evidence"])], "pointer": pointer,
            "source_database": None, "source_version": None})
    if conflict:
        records[1]["pointer"] = records[0]["pointer"]
        records[1]["evidence"] = deepcopy(records[0]["evidence"])
    args["inputs"] += (original,)
    args["documents"]["parsed"]["store"]["source_records"] = records
    return args


def test_aggregate_context_cannot_contradict_exact_inline_genome_input():
    args = fixture()
    shared = evidence("synthetic-shared-container", "")
    args["inputs"][0]["members"][0]["evidence"] = shared
    args["documents"]["parsed"]["store"]["source_records"] = [
        {"source_record_id": "genome-source-" + gid, "subject": {"kind": "genome", "id": gid,
            "source_record_id": "genome-source-" + gid}, "artifact": None, "evidence": [shared],
            "pointer": "/genomes/" + str(i), "source_database": None, "source_version": None}
        for i, gid in enumerate(("G1", "G2"))]
    value = extract(args)["value"]
    assert next(g for g in value["genomes"] if g["genome_id"] == "G1")["input_members"] == [
        {"input_binding_id": "main-input", "member_id": "G1"}]
    assert grader.calculate_codon_tree(value, params(value))["literal_statistics"][0]["gaps"]["value"] == 2


def test_shared_original_container_does_not_equate_distinct_member_pointers():
    value = extract(sequence_member_fixture())["value"]
    assert all(m["input_binding_id"] != "sequence-input" for g in value["genomes"] for m in g["input_members"])
    assert sum(r["reason_code"] == "member_genome_association_required" for r in value["missing_requirements"]) == 2
    assert grader.calculate_codon_tree(value, params(value))["trees"][0]["tip_count"]["value"] == 4


def test_exact_original_content_and_pointer_support_member_identity():
    value = extract(sequence_member_fixture(exact=True))["value"]
    genome = next(g for g in value["genomes"] if g["genome_id"] == "G1")
    assert {"input_binding_id": "sequence-input", "member_id": "sequence-0"} in genome["input_members"]
    assert not any(r["reason_code"] == "member_genome_association_required" for r in value["missing_requirements"])


def test_two_conflicting_exact_original_identities_remain_structural_error():
    result = provider.extract_codon_tree_sheet(**sequence_member_fixture(exact=True, conflict=True))
    assert result["value"] is None
    assert result["diagnostics"][-1]["code"] == "codon_provider_member_genome_conflict"


def test_matching_feature_label_and_shared_evidence_are_not_an_original_identity_join():
    args = sequence_member_fixture()
    args["documents"]["parsed"]["store"]["source_records"] = []
    member = args["inputs"][-1]["members"][0]
    member["member_id"] = "a"
    args["joins"]["feature_genomes"][0]["evidence"] = [member["evidence"]]
    value = extract(args)["value"]
    assert all(m["input_binding_id"] != "sequence-input" for g in value["genomes"] for m in g["input_members"])
    assert sum(r["reason_code"] == "member_genome_association_required" for r in value["missing_requirements"]) == 2
