"""Actual pure bundle→reader→provider→calculator→projection integration.

Synthetic C4 records do not attest Store custody, a live API result, a selected
episode tool or parent return admission. Retained official output is labeled
separately from synthetic hand arithmetic in these tests and saved examples.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_gene_tree_bundle_adapter as gene
from gene_annotation_episode import bvbrc_codon_tree_bundle_adapter as codon
from gene_annotation_episode import bvbrc_phylogeny_bundle_contracts as c
from gene_annotation_episode import bvbrc_phylogeny_bundle_resolution as r
from gene_annotation_episode.bvbrc_gene_tree_grader import calculate_gene_tree
from gene_annotation_episode.bvbrc_codon_tree_grader import calculate_codon_tree
from gene_annotation_episode.phylogeny_calculation_contracts import quantity
from test_bvbrc_phylogeny_bundle_resolution import fixture, slot, add_artifact, supply, supplemental, evidence


BOUNDARY = Path(__file__).resolve().parents[1] / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
EXAMPLE = BOUNDARY / "official_example/test9_genome_dir"
NATIVE_PREFIX = "test9_genome_8taxa_10cds_10proteins_codonAndProteins"


def genome_binding(genomes):
    return {"binding_id": "original-genomes", "parameter_pointer": "/genome_ids", "kind": "inline_parameter",
        "content": None, "workspace_path": None, "inline_value": genomes, "link_evidence": None,
        "members": [{"member_id": g, "member_pointer": "/" + str(i), "length": None, "molecule": None,
            "sequence_sha256": None, "evidence": None} for i, g in enumerate(genomes)]}


def codon_hand_fixture():
    """Synthetic hand operands; current table syntax is source-derived."""
    f = fixture("codon_tree"); plan = f[3]["analyses"][0]; scientific = deepcopy(f[2][0]["value"])
    readers = [
        ("membership", b"F1\tProteins\t\ta\tc\td\tdeletedParalogs: \tb\nF1\tCodons\t\ta\tc\tlacking CodonAlignment for F1: \td\nF2\tProteins\t\te\tf\tg\th\nF2\tCodons\t\te\tf\tg\th\n", {"reader": "codon_membership", "dialect": "homologs_current"}),
        ("statistics", b"PGFam\tgaps\tsum_squared_freq\tmean_squared_freq\tnum_pos\tnum_seqs\tworstSeqScoreused_in_tree\nF1\t2\t3.25\t0.8125\t4\t2\t2\tTrue\nF2\t0\t0\t0\t0\t2\tna\tFalse\ndisqualification: low alignment score\n", {"reader": "codon_family_statistics", "dialect": "current_missing_header_tab"}),
        ("counts", b"Genome\tAllGenes\tSingleCopy\tFiltered_SingleCopy\nG1\t12\t8\t3\nG0\t0\t0\t0\n", {"reader": "codon_genome_counts"}),
        ("report", b"Statistics for CodonTree Analysis\nNum_genomes\t4\nNum_protein_alignments\t2\nNum_aligned_amino_acids\t4\nNum_CDS_alignments\t2\nNum_aligned_nucleotides\t12\nPGFams\tF1,F2\ncommand_line\tra xml -f I\nTotal job duration 17 seconds\n", {"reader": "codon_analysis_statistics", "dialect": "retained_current_source"})]
    for sid, data, reader in readers:
        add_artifact(f, sid, data, reader)
    plan["analysis"].update(membership_document_id=slot("membership"), family_stats_document_id=slot("statistics"),
        genome_counts_document_id=slot("counts"), analysis_stats_document_id=slot("report"), explicit_family_matrix_id="family-matrix")
    plan["read_parameters"].update(membership_dialect="homologs_current", family_stats_dialect="current_missing_header_tab")
    genomes = ["G1", "G2", "G3", "G4"]
    genome_pop = {"population_id": "genomes", "genome_ids": genomes, "stage": "requested_main", "completeness": "complete", "evidence": []}
    family_pop = {"population_id": "families", "family_ids": ["F1", "F2"], "stage": "returned", "completeness": "complete", "evidence": []}
    assembly = scientific["assembly"]
    assembly["caller_populations"]["genomes"] = [genome_pop]
    assembly["caller_populations"]["families"] = [family_pop]
    assembly["genome_request_sets"] = [{"set_id": "main-set", "kind": "main_ids", "input_binding_ids": ["original-genomes"],
        "group_id": None, "derived_from_set_ids": [], "population": deepcopy(genome_pop)}]
    f[0]["input_bindings"] = [genome_binding(genomes)]
    f[0]["original_task"]["submitted_parameters"] = {"genome_ids": genomes}
    mapping = {"F1": {"G1": ["a", "b"], "G2": ["c"], "G3": ["d"], "G4": []},
               "F2": {"G1": ["e"], "G2": ["f"], "G3": ["g"], "G4": ["h"]}}
    rows = []
    for fid, by_genome in mapping.items():
        for gid, features in by_genome.items():
            rows.append({"family_id": fid, "genome_id": gid, "feature_ids": features, "evidence": []})
            scientific["joins"]["feature_genomes"].extend({"feature_id": feature, "genome_id": gid,
                "family_id": fid, "family_namespace": "PGFam", "evidence": []} for feature in features)
    assembly["family_matrices"] = [{"matrix_id": "family-matrix", "namespace": "PGFam", "family_population_id": "families",
        "genome_population_id": "genomes", "rows": rows, "completeness": "complete", "evidence": []}]
    scientific["joins"]["input_rows"] = [{"alignment_id": slot("alignment"), "row_index": i, "input_binding_id": "original-genomes",
        "member_id": gid, "locus_id": "genome", "transformation_id": None, "evidence": []} for i, gid in enumerate(genomes)]
    scientific["joins"]["tip_rows"] = [{"tree_id": slot("tree", tree=True), "node_index": n, "alignment_id": slot("alignment"),
        "row_index": i, "evidence": []} for i, n in enumerate((2, 3, 5, 6))]
    # These small synthetic final blocks are explicitly selected fixture data;
    # they are not reconstructed from the source-derived pre-trim statistics.
    scientific["joins"]["family_blocks"] = [
        {"family_id": "F1", "representation": "protein", "alignment_id": slot("alignment"), "columns_0based": [0, 1],
         "member_row_indices": [0, 1, 2], "evidence": []},
        {"family_id": "F1", "representation": "coding_nucleotide", "alignment_id": slot("alignment"), "columns_0based": [2, 3],
         "member_row_indices": [0, 1], "evidence": []}]
    plan["calculation_parameters"]["family_population_requests"] = [{"family_population_id": "families", "genome_population_id": "genomes"}]
    supply(f, scientific)
    return f


def codon_fields():
    fields = {name: {"metric": name, "analysis_id": "a", "population_id": "matrix"} for name in (
        "literal_n_rows", "literal_n_columns", "literal_gaps", "literal_gap_fraction", "literal_sum_squared_frequency",
        "literal_mean_squared_frequency", "literal_native_family_ranking_score")}
    fields["logfreq"] = {"metric": "literal_row_mean_log2_literal_frequency", "analysis_id": "a", "population_id": "matrix", "row_index": 0}
    fields.update({name: {"metric": name, "analysis_id": "a", "family_population_id": "families", "genome_population_id": "genomes", "family_id": "F1"}
        for name in ("family_present_genomes", "family_missing_genomes", "family_extra_copies", "family_presence_fraction", "family_native_initial_family_rank")})
    fields["members"] = {"metric": "family_membership_rows", "analysis_id": "a", "family_ids": ["F1"]}
    return fields


def native_codon_fixture():
    """Retained native outputs, carried by synthetic C4 association receipts.

    No final family block boundaries or complete preselection matrix are
    inferred. The native membership file does not supply either denominator.
    """
    f = fixture("codon_tree"); f[0]["artifacts"] = []; f[0]["acquisition_receipt_refs"] = []; f[1].clear(); f[3]["artifact_selection"] = []
    files = [
        ("alignment", NATIVE_PREFIX + ".phy", {"reader": "relaxed_phylip", "layout": "interleaved", "continuation_ids": "absent"}),
        ("tree", "RAxML_bestTree." + NATIVE_PREFIX, {"reader": "newick", "dialect": "newick", "allow_multiple": True}),
        ("supported", "RAxML_bipartitions." + NATIVE_PREFIX, {"reader": "newick", "dialect": "newick", "allow_multiple": True}),
        ("bootstrap", "RAxML_bootstrap." + NATIVE_PREFIX, {"reader": "newick", "dialect": "newick", "allow_multiple": True}),
        ("partitions", NATIVE_PREFIX + ".partitions", {"reader": "raxml_partitions", "alignment": slot("alignment")}),
        ("log", "RAxML_info." + NATIVE_PREFIX, {"reader": "raxml_run_log", "dialect": "raxml_8"}),
        ("membership", "test9_genome_8taxa_10cds_10proteins.pgfamsAndGenesIncludedInAlignment.txt", {"reader": "codon_membership", "dialect": "pgfams_legacy"})]
    for sid, name, reader in files:
        add_artifact(f, sid, (EXAMPLE / name).read_bytes(), reader)
    plan = f[3]["analyses"][0]
    plan["analysis"].update(partition_document_id=slot("partitions"), supported_tree_id=slot("supported", tree=True),
        bootstrap_tree_document_id=slot("bootstrap"), membership_document_id=slot("membership"), native_engine_slots=[slot("log")])
    plan["calculation_parameters"]["alignment_requests"] = [{"population_id": "matrix", "alphabet": "unknown", "case_policy": "literal", "pairs": []}]
    plan["calculation_parameters"]["tree_requests"][0]["pairs"] = []
    scientific = deepcopy(f[2][0]["value"]); scientific["observed_run"]["settings"] = []
    # The original native request ID list is a distinct retained source from
    # the feature table and final matrix. It remains explicit fixture input.
    genomes = (EXAMPLE.parent / "test9_genome.ids").read_text().splitlines()[1:]
    f[0]["input_bindings"] = [genome_binding(genomes)]
    f[0]["original_task"]["submitted_parameters"] = {"genome_ids": genomes}
    population = {"population_id": "genomes", "genome_ids": genomes, "stage": "requested_main", "completeness": "complete", "evidence": []}
    scientific["assembly"]["caller_populations"]["genomes"] = [population]
    scientific["assembly"]["genome_request_sets"] = [{"set_id": "main-set", "kind": "main_ids", "input_binding_ids": ["original-genomes"],
        "group_id": None, "derived_from_set_ids": [], "population": deepcopy(population)}]
    # Explicit retained source table supplies these namespace/genome/feature
    # relationships; the adapter never decodes genome IDs from feature names.
    included_features = {feature for line in f[1]["SYNTHETIC-native/a/membership"].decode().splitlines() if line
                         for feature in line.split("\t")[3:]}
    for gid, feature, fid in (line.split("\t") for line in (EXAMPLE / "test9_genome.genomeGenePgfams.txt").read_text().splitlines()):
        if feature in included_features:
            scientific["joins"]["feature_genomes"].append({"feature_id": feature, "genome_id": gid, "family_id": fid, "family_namespace": "PGFam", "evidence": []})
    scientific["assembly"]["model_associations"] = [{"read_id": slot("log"), "log_model_index": i,
        "partition_document_id": slot("partitions"), "partition_index": i, "model_selection_command_id": None,
        "sample_alignment_id": None, "sample_column_map": None, "evidence": []} for i in range(4)]
    supply(f, scientific)
    return f


def relationship_fixture():
    """Explicit synthetic feature/function/taxon and cross-tree associations."""
    f = fixture(); supplemental(f, data=b"((A:1,C:1):1,(B:1,D:1):1);")
    plan = f[3]["analyses"][0]; scientific = deepcopy(f[2][0]["value"])
    subjects = [{"kind": "feature", "id": "SYNTHETIC-feature/" + label, "source_record_id": "anchor-" + label} for label in "ABCD"]
    for subject in subjects:
        scientific["source_records"].append({"source_record_id": subject["source_record_id"], "subject": subject,
            "artifact": None, "evidence": [], "pointer": "", "source_database": "synthetic", "source_version": "1"})
    for i, key in enumerate(("function/A", "function/A", "function/B")):
        scientific["joins"]["functions"].append({"assignment_id": "assignment-" + str(i), "subject": subjects[i],
            "function_key": key, "function_label": key, "source_record_id": subjects[i]["source_record_id"], "evidence": []})
        scientific["joins"]["taxa"].append({"subject": subjects[i], "taxon_id": ("taxon/X", "taxon/X", "taxon/Y")[i],
            "rank": "species", "lineage": [], "source_record_id": subjects[i]["source_record_id"], "evidence": []})
    population = {"population_id": "features", "unit": "feature", "member_subjects": subjects,
        "assignment_completeness": "complete", "membership_completeness": "complete", "evidence": []}
    scientific["assembly"]["caller_populations"]["composition"] = [population]
    scientific["assembly"]["caller_populations"]["taxonomy"] = [{**population, "population_id": "taxa"}]
    pairs = [{"gene_tree_id": slot("tree", tree=True), "gene_node_index": a,
        "organismal_tree_id": slot("reference", tree=True), "organismal_node_index": b, "subject": subject, "evidence": []}
        for a, b, subject in zip((2, 3, 5, 6), (2, 5, 3, 6), subjects)]
    scientific["joins"]["organismal_tips"] = pairs
    plan["calculation_parameters"].update(composition_population_ids=["features"], taxon_requests=[{"population_id": "taxa", "rank": "species"}],
        comparisons=[{"comparison_id": "gene-v-reference", "gene_tree_id": slot("tree", tree=True),
            "organismal_tree_id": slot("reference", tree=True), "tip_pairs": deepcopy(pairs)}])
    supply(f, scientific)
    return f


def relationship_fields():
    return {"functions": {"metric": "function_composition_rows", "analysis_id": "a", "population_id": "features"},
        "comparison": {"metric": "relationship_comparison", "analysis_id": "a", "comparison_id": "gene-v-reference"},
        "unknown": {"metric": "taxon_unknown_members", "analysis_id": "a", "population_id": "taxa", "rank": "species"},
        "same_taxon": {"metric": "taxon_same_taxon_pair_fraction", "analysis_id": "a", "population_id": "taxa", "rank": "species"}}


def historical_codon_fixture():
    f = codon_hand_fixture(); scientific = deepcopy(f[2][0]["value"])
    population = {"population_id": "historical", "family_ids": ["F1", "F2"], "stage": "evaluated_pretrim", "completeness": "complete", "evidence": []}
    scientific["assembly"]["caller_populations"]["families"].append(population)
    # The native historical population IDs identify exact saved native table
    # observations, distinct from this evaluated-family set and final matrix.
    table_id = "SYNTHETIC-native/a/statistics#codon_family_statistics"
    rows = [("F1", "a", "G1", -.5), ("F1", "c", "G2", -1.), ("F2", "e", "G1", -1.5), ("F2", "f", "G2", -3.)]
    scientific["assembly"]["historical_frequencies"] = [{"evaluated_family_population": {"population": population,
        "expected_sequence_memberships": [{"family_id": "F1", "feature_ids": ["a", "c"]}, {"family_id": "F2", "feature_ids": ["e", "f"]}],
        "completeness": "complete"}, "pretrim_sequence_rows": [{"family_id": fid, "feature_id": feature, "genome_id": gid,
            "value": quantity(value, population=table_id + "/population/family/" + fid, unit="bits_per_column", method="row_mean_log2_literal_frequency")}
            for fid, feature, gid, value in rows]}]
    f[3]["analyses"][0]["calculation_parameters"]["worst_sequence_population_id"] = "historical"
    supply(f, scientific)
    return f


def bootstrap_fixture(*, include_log=True, partial=False):
    f = fixture(); plan = f[3]["analyses"][0]
    forest = b"((A,B),(C,D));((A,B),(C,D));((A,C),(B,D));(A,B,C,D);"
    if partial:
        forest += b"BROKEN("
    add_artifact(f, "replicates", forest, {"reader": "newick", "dialect": "newick", "allow_multiple": True})
    plan["population_plans"].append({"kind": "bootstrap_forest", "population_id": "replicates", "forest": slot("replicates"),
        "expected_replicates": 5 if partial else 4, "expected_count_evidence": [evidence(5 if partial else 4, "replicate-count")]})
    plan["calculation_parameters"]["bootstrap_requests"] = [{"reference_tree_id": slot("tree", tree=True),
        "replicate_population_id": "replicates", "method": "rapid_bootstrap", "tip_join": {"reference_tree_id": slot("tree", tree=True),
            "mappings": [{"replicate_tree_id": slot("replicates", tree=True, index=i),
                "pairs": [{"reference_node_index": a, "replicate_node_index": b} for a, b in zip((2, 3, 5, 6), nodes)]}
                for i, nodes in enumerate(((2, 3, 5, 6), (2, 3, 5, 6), (2, 5, 3, 6), (1, 2, 3, 4)))]}}]
    if include_log:
        data = (b"This is RAxML version 8.2.9 released by source.\nRAxML was called as follows:\n\n"
            b"raxml -s input.fa -n run -f a -m PROTGAMMALG -N 4 -T 2\n"
            b"Alignment has 7 distinct alignment patterns\nFinal ML Optimization Likelihood: -3.25\n"
            b"Overall execution time for full ML analysis: 1.0 secs\n")
        add_artifact(f, "log", data, {"reader": "raxml_run_log", "dialect": "raxml_8"})
        plan["analysis"]["native_engine_slots"] = [slot("log")]
        plan["analysis"]["output_role_evidence"] = [evidence({"analysis": "a", "tree": "a:tree", "log": "a:log"}, "synthetic-analysis-association")]
        plan["calculation_parameters"]["tree_requests"][0]["branch_unit"] = "expected_substitutions_per_model_site"
    return f


def bootstrap_fields():
    result = {name: {"metric": name, "analysis_id": "a", "population_id": "replicates", "tree": slot("tree", tree=True)}
        for name in ("bootstrap_supplied_replicates", "bootstrap_expected_replicates", "bootstrap_usable_replicates")}
    result.update({name: {"metric": name, "analysis_id": "a", "population_id": "replicates", "tree": slot("tree", tree=True), "node_index": 1}
        for name in ("bootstrap_split_matches", "bootstrap_split_denominator", "bootstrap_split_frequency")})
    result["support"] = {"metric": "branch_support_rescaled", "analysis_id": "a", "population_id": "leaves", "tree": slot("tree", tree=True), "node_index": 1}
    return result


def consume(f, fields=None, provider="gene_tree"):
    adapter = gene if provider == "gene_tree" else codon
    b, content, values, params = f
    fields = fields or {"tips": {"metric": "tree_tip_count", "analysis_id": "a", "population_id": "leaves", "tree": slot("tree", tree=True)}}
    return adapter.consume_bundle(b, artifact_bytes=content, supplied_values=values,
        parameters=params, requested_form=adapter.requested_form_schema(fields))


def numerical_fields(aid="a"):
    return {"tips": {"metric": "tree_tip_count", "analysis_id": aid, "population_id": "leaves", "tree": slot("tree", aid, True)},
        "cells": {"metric": "alignment_cell_count", "analysis_id": aid, "population_id": "matrix"},
        "gaps": {"metric": "alignment_gap_fraction", "analysis_id": aid, "population_id": "matrix"},
        "ambiguity": {"metric": "alignment_ambiguity_fraction", "analysis_id": aid, "population_id": "matrix"},
        "canonical": {"metric": "alignment_canonical_fraction", "analysis_id": aid, "population_id": "matrix"},
        "distance": {"metric": "tree_distance", "analysis_id": aid, "population_id": "leaves", "tree": slot("tree", aid, True), "node_a": 2, "node_b": 3},
        "missing": {"metric": "missing_requirements"}}


@pytest.mark.parametrize("mode", ["gene_tree", "concatenated_sequence_loci"])
def test_hand_numbers_complete_saved_sets_and_original_inputs_unchanged(mode):
    f = fixture(); f[3]["analyses"][0]["analysis"]["mode"] = mode
    for artifact in f[0]["artifacts"]:
        artifact["declared_format"]["mode"] = mode
    before = deepcopy(f); fields = numerical_fields(); form = gene.requested_form_schema(fields)
    saved_form = deepcopy(form)
    result = gene.consume_bundle(f[0], artifact_bytes=f[1], supplied_values=f[2], parameters=f[3], requested_form=form)
    assert result["status"] == "ok", result
    assert result["facts"] == {"tips": 4, "cells": 16, "gaps": 0.125, "ambiguity": 0.25, "canonical": 0.625, "distance": 0.2, "missing": []}
    assert set(result) == {"adapter_id", "adapter_version", "status", "sheet", "components", "facts", "missing_requirements", "diagnostics"}
    assert result["sheet"]["schema_version"] == "bvbrc_phylogeny_sheet_set_v1"
    sheet = result["sheet"]["analyses"][0]["sheet"]
    assert sheet["documents"]["store"]["alignments"][0]["rows"][0]["sequence"] == "A-CX"
    assert result["components"]["analyses"][0]["components"]["alignments"][0]["cell_count"]["unit"] == "characters"
    assert form == saved_form and f == before


def test_codon_hand_statistics_family_memberships_and_all_native_tables():
    f = codon_hand_fixture(); original = deepcopy(f)
    result = consume(f, codon_fields(), provider="codon_tree")
    assert result["status"] == "ok", result["diagnostics"]
    values = result["facts"]
    assert {k: values[k] for k in codon_fields() if k != "members"} == {
        "literal_n_rows": 4, "literal_n_columns": 4, "literal_gaps": 2, "literal_gap_fraction": .125,
        "literal_sum_squared_frequency": 2.875, "literal_mean_squared_frequency": .71875,
        "literal_native_family_ranking_score": 1.4375, "logfreq": -.75,
        "family_present_genomes": 3, "family_missing_genomes": 1, "family_extra_copies": 1,
        "family_presence_fraction": .75, "family_native_initial_family_rank": 2}
    assert len(values["members"]) == 5
    assert [m["alignment_row_index"] for m in values["members"]] == [0, 1, 2, 0, 1]
    assert {c.decode_reference(m["feature_ref"])[2] for m in values["members"]} == {"a", "c", "d"}
    sheet = result["sheet"]["analyses"][0]["sheet"]
    assert len(sheet["read_outcomes"]) == 6 and len(sheet["documents"]["store"]["native_tables"]) == 4
    assert sheet["families"][0]["memberships"][0]["deleted_feature_ids"] == ["b"]
    assert sheet["families"][0]["memberships"][1]["missing_codon_feature_ids"] == ["d"]
    assert f == original


def test_codon_partial_family_matrix_never_treats_absent_row_as_zero():
    f = codon_hand_fixture(); scientific = deepcopy(f[2][0]["value"])
    matrix = scientific["assembly"]["family_matrices"][0]
    matrix["rows"] = [row for row in matrix["rows"] if (row["family_id"], row["genome_id"]) != ("F1", "G4")]
    matrix["completeness"] = "partial"; supply(f, scientific)
    fields = codon_fields()
    result = consume(f, {"missing": fields["family_missing_genomes"], "gaps": fields["literal_gaps"]}, provider="codon_tree")
    assert result["facts"] == {"missing": None, "gaps": 2} and result["status"] == "partial", result["diagnostics"]
    assert any(req["reason_code"] == "family_membership_required" for req in result["missing_requirements"])
    assert consume(f, {"gaps": fields["literal_gaps"]}, provider="codon_tree")["status"] == "ok"


def test_family_auxiliary_rows_do_not_override_checked_primary_genome_mapping():
    f = codon_hand_fixture(); scientific = deepcopy(f[2][0]["value"])
    add_artifact(f, "other-alignment", f[1]["SYNTHETIC-native/a/alignment"],
        {"reader": "aligned_fasta", "id_rule": "first_whitespace_token", "encoding": "ascii"})
    f[3]["analyses"][0]["analysis"]["per_family_final_alignment_ids"] = [slot("other-alignment")]
    scientific["joins"]["input_rows"] += [{**row, "alignment_id": slot("other-alignment")} for row in list(scientific["joins"]["input_rows"])]
    scientific["joins"]["family_blocks"].append({**scientific["joins"]["family_blocks"][0], "alignment_id": slot("other-alignment")})
    supply(f, scientific)
    result = consume(f, {"members": codon_fields()["members"]}, provider="codon_tree")
    assert result["status"] == "ok", result["diagnostics"]
    protein = [row for row in result["facts"]["members"] if row["representation"] == "protein"]
    assert [row["alignment_row_index"] for row in protein] == [0, 1, 2]
    saved = result["sheet"]["analyses"][0]["sheet"]
    assert all("other-alignment" not in row["alignment_id"] for genome in saved["genomes"] for row in genome["final_alignment_rows"])


def test_original_member_coverage_is_separate_from_final_row_occupancy():
    f = fixture(); scientific = deepcopy(f[2][0]["value"])
    original = {"sequence": "ACX"}; ev = evidence(original, "original-sequence", "/sequence")
    member = {"input_binding_id": "original-sequence", "member_id": "A"}
    f[0]["original_task"]["submitted_parameters"] = {"sequence": original}
    f[0]["input_bindings"] = [{"binding_id": "original-sequence", "parameter_pointer": "/sequence", "kind": "inline_parameter",
        "content": None, "workspace_path": None, "inline_value": original, "link_evidence": None,
        "members": [{"member_id": "A", "member_pointer": "/sequence", "length": 3, "molecule": "protein",
            "sequence_sha256": hashlib.sha256(b"ACX").hexdigest(), "evidence": ev}]}]
    scientific["assembly"]["locus_bindings"] = [{"locus_id": "locus", "input_members": [member], "completeness": "complete", "evidence": [ev]}]
    scientific["joins"]["input_rows"] = [{"alignment_id": slot("alignment"), "row_index": 0, **member,
        "locus_id": "locus", "transformation_id": None, "evidence": [ev]}]
    scientific["joins"]["residues"] = [{"alignment_id": slot("alignment"), "row_index": 0, "column_0based": col,
        "staged_ungapped_position_0based": pos, "original_member": None if pos is None else member,
        "original_interval_0based_half_open": None if pos is None else [pos, pos + 1], "strand": "+", "translation_table": None,
        "transformation_id": None, "evidence": [ev]} for col, pos in enumerate((0, None, 1, 2))]
    f[3]["analyses"][0]["analysis"]["locus_ids"] = ["locus"]
    f[3]["analyses"][0]["population_plans"].append({"kind": "alignment_subset", "population_id": "one-member", "alignment": slot("alignment"),
        "row_indices": [0], "columns_0based": [0, 1, 2, 3], "completeness": "complete", "evidence": [ev]})
    f[3]["analyses"][0]["calculation_parameters"]["original_coverage_population_ids"] = ["one-member"]
    supply(f, scientific)
    fields = {"coverage": {"metric": "coverage_original_member_coverage", "analysis_id": "a", "population_id": "one-member", "row_index": 0, **member},
        "occupancy": {"metric": "row_matrix_occupancy", "analysis_id": "a", "population_id": "matrix", "row_index": 0}}
    result = consume(f, fields)
    assert result["status"] == "ok" and result["facts"] == {"coverage": 1., "occupancy": .75}, result["diagnostics"]
    scientific["joins"]["residues"].pop(); supply(f, scientific)
    partial = consume(f, fields)
    assert partial["facts"] == {"coverage": None, "occupancy": .75} and partial["status"] == "partial"


def test_actual_failed_bundle_without_usable_requested_science_retains_failure():
    f = fixture(); f[0]["status"] = "failed"
    assert consume(f)["facts"] == {"tips": 4}
    f[0]["artifacts"] = []; f[0]["acquisition_receipt_refs"] = []; f[1].clear()
    result = consume(f)
    assert result["facts"] == {"tips": None} and result["status"] == "failed"
    assert result["missing_requirements"]


def test_retained_nine_row_codon_adapter_full_matrix_partitions_trees_log_and_membership():
    f = native_codon_fixture()
    fields = {name: selector for name, selector in codon_fields().items() if name.startswith("literal_")}
    fields["tips"] = numerical_fields()["tips"]
    result = consume(f, fields, provider="codon_tree")
    assert result["status"] == "ok", result["diagnostics"]
    values = result["facts"]
    assert (values["literal_n_rows"], values["literal_n_columns"], values["literal_gaps"], values["tips"]) == (9, 15300, 17308, 9)
    assert values["literal_gap_fraction"] == pytest.approx(17308 / 137700)
    assert values["literal_sum_squared_frequency"] == pytest.approx(10056.41975308642)
    sheet = result["sheet"]["analyses"][0]["sheet"]
    assert len(sheet["read_outcomes"]) == 7
    assert len(sheet["models"]) == 4 and len(sheet["families"]) == 10
    assert [len(p["columns_0based"]) for p in sheet["documents"]["store"]["partitions"][0]["partitions"]] == [3825] * 4
    bootstrap = next(d for d in sheet["documents"]["store"]["tree_documents"] if "bootstrap" in d["document_id"])
    assert len(bootstrap["trees"]) == 100 and bootstrap["completeness"] == "complete"
    assert sum(len(row["feature_ids"]) for fam in sheet["families"] for row in fam["memberships"]) == 160
    assert sheet["assembly"]["family_matrices"] == []


def test_function_taxonomy_and_reference_comparison_use_exact_saved_associations():
    result = consume(relationship_fixture(), relationship_fields())
    assert result["status"] == "ok", result["diagnostics"]
    functions = result["facts"]["functions"]
    assert len(functions) == 2
    row = next(r for r in functions if c.decode_reference(r["function_ref"])[2] == "function/A")
    assert (row["assigned_members"], row["total_members"], row["members_with_recorded_assignment"]) == (2, 4, 3)
    assert row["fraction_all"] == .5 and row["fraction_recorded"] == pytest.approx(2/3)
    assert result["facts"]["unknown"] == 1 and result["facts"]["same_taxon"] == pytest.approx(1/3)
    comparison = result["facts"]["comparison"][0]
    assert {k: v for k, v in comparison.items() if k != "comparison_ref"} == {
        "matched_tips": 4, "gene_splits": 1, "organismal_splits": 1, "shared_splits": 0, "rf": 2, "rf_fraction": 1.0}


def test_forged_reference_claim_blocks_only_requested_comparison():
    f = relationship_fixture(); scientific = deepcopy(f[2][0]["value"])
    scientific["supplemental_documents"][0]["read"]["result"]["value"]["trees"][0]["nodes"][2]["decoded_label"] = "FORGED"
    supply(f, scientific)
    fields = {"comparison": relationship_fields()["comparison"], "tips": numerical_fields()["tips"]}
    result = consume(f, fields)
    assert result["facts"] == {"comparison": None, "tips": 4} and result["status"] == "partial"
    assert any(req["reason_code"] == "supplemental_parsed_claim_conflict" for req in result["missing_requirements"])


def test_codon_historical_ratios_copy_saved_pretrim_cells():
    fields = {"mean": {"metric": "worst_sequence_mean", "analysis_id": "a", "family_population_id": "historical", "genome_id": "G1"},
        "ratio": {"metric": "worst_sequence_ratio", "analysis_id": "a", "family_population_id": "historical", "family_id": "F1", "feature_id": "a", "genome_id": "G1"},
        "maximum": {"metric": "worst_sequence_family_maximum", "analysis_id": "a", "family_population_id": "historical", "family_id": "F1"}}
    result = consume(historical_codon_fixture(), fields, provider="codon_tree")
    assert result["status"] == "ok", result["diagnostics"]
    assert result["facts"]["mean"] == -1.
    assert result["facts"]["ratio"] == pytest.approx(-.5 / -1.00001)
    assert result["facts"]["maximum"] == pytest.approx(-1. / -2.00001)


@pytest.mark.parametrize("partial", [False, True])
def test_bootstrap_forest_counts_and_conditional_split_frequency(partial):
    result = consume(bootstrap_fixture(partial=partial), bootstrap_fields())
    assert result["status"] == ("partial" if partial else "ok"), result["diagnostics"]
    assert result["facts"] == {"bootstrap_supplied_replicates": 4, "bootstrap_expected_replicates": 5 if partial else 4,
        "bootstrap_usable_replicates": 4, "bootstrap_split_matches": 2, "bootstrap_split_denominator": 4,
        "bootstrap_split_frequency": .5, "support": .75}
    if partial:
        component = result["components"]["analyses"][0]["components"]["bootstrap"][0]
        assert component["rows"][0]["frequency"]["method"] == "conditional_rapid_bootstrap_frequency"


def test_unknown_bootstrap_method_keeps_exact_requested_requirement_and_independent_tree():
    f = bootstrap_fixture(include_log=False)
    result = consume(f, {"frequency": bootstrap_fields()["bootstrap_split_frequency"], "tips": numerical_fields()["tips"]})
    assert result["facts"] == {"frequency": None, "tips": 4} and result["status"] == "partial"
    assert any(req["reason_code"] == "bootstrap_method_unresolved" for req in result["missing_requirements"])
    assert consume(f)["status"] == "ok"


def test_complete_four_member_bootstrap_population_ignores_unrelated_malformed_tree():
    f = bootstrap_fixture()
    add_artifact(f, "unrelated-tree", b"BROKEN(", {"reader": "newick", "dialect": "newick", "allow_multiple": True})
    result = consume(f, bootstrap_fields())
    assert result["status"] == "ok" and result["facts"]["bootstrap_split_frequency"] == .5
    counts = {k: v for k, v in bootstrap_fields().items() if k.startswith("bootstrap_") and "split" not in k}
    partial = consume(bootstrap_fixture(partial=True), counts)
    assert partial["status"] == "ok" and partial["missing_requirements"] == []
    assert partial["facts"]["bootstrap_expected_replicates"] == 5 and partial["facts"]["bootstrap_usable_replicates"] == 4


@pytest.mark.parametrize("data", [b"", b">A\nAA\n>B\nA\n", b"not an alignment"])
def test_malformed_alignment_keeps_valid_tree_and_requested_requirements_local(data):
    f = fixture(alignment=data)
    tree_only = consume(f)
    assert tree_only["facts"] == {"tips": 4} and tree_only["status"] == "ok", tree_only
    both = consume(f, {"tips": numerical_fields()["tips"], "cells": numerical_fields()["cells"], "needs": {"metric": "missing_requirements"}})
    assert both["facts"]["tips"] == 4 and both["facts"]["cells"] is None
    assert both["status"] == "partial" and both["facts"]["needs"]


def test_missing_alignment_and_independently_missing_supplement_keep_current_tree():
    f = fixture(); f[0]["artifacts"] = [a for a in f[0]["artifacts"] if a["role"] != "a:alignment"]
    f[1].pop("SYNTHETIC-native/a/alignment")
    read = supplemental(f); del f[1][read["artifact"]["raw_artifact_ref"]]
    result = consume(f)
    assert result["status"] == "ok" and result["facts"] == {"tips": 4}, result
    assert result["sheet"]["analyses"][0]["sheet"]["documents"]["analyses"][0]["aligned_document_id"] is None
    assert any(q["reason_code"] == "supplemental_native_content_required" for q in result["sheet"]["analyses"][0]["missing_requirements"])


def test_known_unit_scalar_cannot_copy_unknown_native_signed_length():
    f = fixture(); f[3]["analyses"][0]["calculation_parameters"]["tree_requests"][0]["branch_unit"] = "expected_substitutions_per_model_site"
    result = consume(f, {"tips": numerical_fields()["tips"], "length": {"metric": "branch_length", "analysis_id": "a", "population_id": "leaves", "tree": slot("tree", tree=True), "node_index": 5}})
    assert result["facts"] == {"tips": 4, "length": None} and result["status"] == "partial", result
    branch = next(b for b in result["components"]["analyses"][0]["components"]["trees"][0]["branches"] if b["node_index"] == 5)
    assert branch["length"]["value"] == -0.1 and branch["length"]["unit"] == "native_unknown"


def test_branch_site_qualification_arrays_have_scoped_references_and_native_values():
    f = fixture()
    result = consume(f, {"branches": {"metric": "branch_rows", "analysis_id": "a", "population_id": "leaves", "tree": slot("tree", tree=True), "node_indices": [1, 5]},
        "sites": {"metric": "site_rows", "analysis_id": "a", "population_id": "matrix", "columns_0based": [0, 2, 3]},
        "q": {"metric": "qualifications", "analysis_id": "a", "slot_id": None}})
    assert result["facts"]["branches"][0]["support_value"] == 75
    assert result["facts"]["branches"][1]["length"] == -0.1
    assert result["facts"]["sites"][1]["canonical_majority_fraction"] == pytest.approx(2/3)
    assert result["facts"]["sites"][2]["canonical_entropy_bits"] is None
    assert c.decode_reference(result["facts"]["branches"][0]["tree_ref"])[1:] == ("a", "SYNTHETIC-native/a/tree#tree_document/tree/0")
    assert result["facts"]["q"] and all(row["code"] in c.QUALIFICATION_CODES for row in result["facts"]["q"])


def test_explicit_empty_subpopulation_and_all_gap_matrix_are_not_missing_input():
    f = fixture(alignment=b">A\n----\n>B\n----\n>C\n----\n>D\n----\n")
    fields = {"gaps": numerical_fields()["gaps"], "canonical": numerical_fields()["canonical"]}
    result = consume(f, fields)
    assert result["facts"] == {"gaps": 1.0, "canonical": 0.0} and result["status"] == "ok"
    f[3]["analyses"][0]["population_plans"][0] = {"kind": "alignment_subset", "population_id": "matrix", "alignment": slot("alignment"), "row_indices": [], "columns_0based": [], "completeness": "complete", "evidence": []}
    f[3]["analyses"][0]["calculation_parameters"]["alignment_requests"][0]["pairs"] = []
    result = consume(f, {"count": {"metric": "alignment_cell_count", "analysis_id": "a", "population_id": "matrix"},
        "sites": {"metric": "site_rows", "analysis_id": "a", "population_id": "matrix", "columns_0based": []}, "fraction": fields["gaps"]})
    assert result["facts"] == {"count": 0, "sites": [], "fraction": None}
    assert any(req["reason_code"] == "phylogeny_quantity_denominator_empty" for req in result["missing_requirements"])


def test_unknown_alphabet_preserves_gap_counts_and_blocks_canonical_values_only():
    f = fixture(); scientific = deepcopy(f[2][0]["value"]); scientific["observed_run"]["settings"] = []; supply(f, scientific)
    result = consume(f, {"gaps": numerical_fields()["gaps"], "canonical": numerical_fields()["canonical"]})
    assert result["facts"] == {"gaps": 0.125, "canonical": None}
    assert any(req["reason_code"] == "alphabet_required" for req in result["missing_requirements"])
    assert consume(f, {"gaps": numerical_fields()["gaps"]})["status"] == "ok"


@pytest.mark.parametrize("failure", ["wrong_task", "malformed_envelope"])
def test_all_original_analyses_survive_independent_invalid_member(failure):
    f, second = fixture(), fixture(aid="second")
    f[0]["artifacts"] += second[0]["artifacts"]
    f[0]["acquisition_receipt_refs"] += second[0]["acquisition_receipt_refs"]
    f[0]["supplied_scientific_metadata"] += second[0]["supplied_scientific_metadata"]
    f[1].update(second[1]); f[2].extend(second[2]); f[3]["artifact_selection"] += second[3]["artifact_selection"]; f[3]["analyses"] += second[3]["analyses"]
    # A structurally wrong original-task association is local supplied metadata.
    if failure == "wrong_task":
        f[2][1]["value"]["observed_run"]["original_task_id"] = "DIFFERENT-task"
    else:
        del f[2][1]["value"]["joins"]
    supply(f, f[2][1]["value"], aid="second")
    result = consume(f, {"first": numerical_fields()["tips"], "second": numerical_fields("second")["tips"]})
    assert result["facts"] == {"first": 4, "second": None}, result
    assert [a["analysis_id"] for a in result["sheet"]["analyses"]] == ["a", "second"]
    assert [a["analysis_id"] for a in result["components"]["analyses"]] == ["a", "second"]
    assert result["sheet"]["analyses"][1]["status"] == "invalid"


def test_malformed_optional_supplemental_shape_keeps_independent_tree():
    f = fixture(); scientific = deepcopy(f[2][0]["value"])
    scientific["supplemental_documents"].append({"slot_id": "reference", "role": "reference", "evidence": []})
    supply(f, scientific)
    result = consume(f)
    assert result["facts"] == {"tips": 4} and result["status"] == "ok", result["diagnostics"]
    assert any(s["slot_id"] == "reference" and s["state"] == "invalid" for s in result["sheet"]["selections"])


@pytest.mark.parametrize("provider,factory,fields", [("gene_tree", fixture, numerical_fields), ("codon_tree", codon_hand_fixture, codon_fields)])
def test_pure_consume_and_saved_recalculation_have_no_hidden_io(monkeypatch, provider, factory, fields):
    f = factory(); result = consume(f, fields(), provider=provider)
    saved = json.loads(json.dumps(result)); sheet = saved["sheet"]["analyses"][0]["sheet"]
    component = saved["components"]["analyses"][0]["components"]
    def forbidden(*args, **kwargs):
        raise AssertionError("I/O forbidden in scientific calls")
    with monkeypatch.context() as m:
        for owner, name in ((builtins, "open"), (io, "open"), (socket, "socket"), (socket, "create_connection"),
                (subprocess, "run"), (subprocess, "Popen"), (Path, "read_bytes"), (Path, "read_text")):
            m.setattr(owner, name, forbidden)
        assert consume(f, fields(), provider=provider) == result
        m.setattr(r, "parse_reader", forbidden)
        calculate = calculate_gene_tree if provider == "gene_tree" else calculate_codon_tree
        assert calculate(sheet, component["parameters"]) == component


@pytest.mark.parametrize("filename", ["Buchnera_acpS_fg_dna_raxml_hky85.xml", "Buchnera_acpS_fg_dna_raxml_hky85_RAxML_tree_rell.xml"])
def test_retained_official_gene_tree_xml_qualified_topology(filename):
    f = gene_xml_fixture(filename)
    result = consume(f, {"tips": {"metric": "tree_tip_count", "analysis_id": "a", "population_id": "leaves", "tree": slot("xml", tree=True)}})
    assert result["status"] == "ok", result
    assert result["facts"]["tips"] == 17
    assert any(d["code"] == "bvbrc_phylogeny_xml_converter_zero_and_support_loss" for d in result["diagnostics"])


def gene_xml_fixture(filename):
    data = (BOUNDARY / "additional_sources/bvbrc_gene_tree/tests" / filename).read_bytes()
    f = fixture(); f[0]["artifacts"] = []; f[0]["acquisition_receipt_refs"] = []; f[1].clear(); f[3]["artifact_selection"] = []
    p = f[3]["analyses"][0]; p["analysis"].update(aligned_document_id=None, raw_tree_id=None, phyloxml_tree_id=slot("xml", tree=True))
    p["population_plans"] = [{"kind": "whole_tree", "population_id": "leaves", "tree": slot("xml", tree=True)}]
    p["calculation_parameters"]["alignment_requests"] = []; p["calculation_parameters"]["tree_requests"][0]["pairs"] = []
    add_artifact(f, "xml", data, {"reader": "phyloxml"})
    return f
