"""Declared Codon matrix populations and independent native memberships.

Synthetic sheets exercise only the production numerical calculator. The native
case retains actual legacy membership and exact supplied gene-table joins; its
one-genome scope is an explicit test selection, not a claimed native main set.
Provider assembly, service acquisition and episode returns remain separate.
"""
from __future__ import annotations

import builtins
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

from gene_annotation_episode import bvbrc_codon_tree_calculators as calc
from gene_annotation_episode import bvbrc_codon_tree_native as native
from gene_annotation_episode import phylogeny_formats as formats


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24/official_example/test9_genome_dir"
POP_KEYS = ("alignments", "leaves", "composition", "taxonomy", "genomes", "families", "bootstraps", "native")


def membership(features=("a", "outside"), genomes=("Goptional", "G1"), *, index=0,
               representation="protein", deleted=(), missing=()):
    return {"representation": representation, "feature_ids": list(features), "genome_ids": list(genomes),
            "deleted_feature_ids": list(deleted), "missing_codon_feature_ids": list(missing),
            "source_table_id": "synthetic#codon_membership", "source_row_index": index}


def scoped_sheet(*, empty=False):
    """Two main genomes, one extra copy, plus an unrelated native member."""
    main = {"population_id": "main", "genome_ids": [] if empty else ["G1", "G2"],
            "stage": "requested_main", "completeness": "complete", "evidence": []}
    families = {"population_id": "returned", "family_ids": ["F1"], "stage": "returned",
                "completeness": "complete", "evidence": []}
    optional = {"population_id": "optional", "genome_ids": ["Goptional"],
                "stage": "requested_optional", "completeness": "complete", "evidence": []}
    pops = {key: [] for key in POP_KEYS}
    pops["genomes"] = [main, optional]
    pops["families"] = [families]
    rows = [] if empty else [{"genome_id": "G1", "feature_ids": ["a", "b"]},
                            {"genome_id": "G2", "feature_ids": []}]
    members = [membership(deleted=("b", "deleted-outside")),
               membership(index=1, representation="coding_nucleotide", missing=("missing-outside",))]
    family = {"family_id": "F1", "namespace": "PGFam", "matrix": rows,
              "matrix_completeness": "complete", "memberships": members,
              "inclusion": [], "native_statistic_observation_ids": [], "final_block_indices": []}
    analysis = {"analysis_id": "synthetic", "mode": "core_genome_codon_protein",
        "final_alignment_id": None, "partition_document_id": None, "raw_tree_id": None,
        "supported_tree_id": None, "rooted_derivative_tree_id": None, "display_tree_id": None,
        "phyloxml_tree_id": None, "membership_document_id": None, "family_stats_document_id": None,
        "genome_counts_document_id": None, "analysis_stats_document_id": None,
        "native_engine_observation_ids": [], "bootstrap_tree_document_id": None,
        "per_family_final_alignment_ids": [], "explicit_family_matrix_id": "main-matrix", "output_role_evidence": []}
    return {"schema_version": "bvbrc_codon_tree_sheet_v1", "tool": "C-L193-CodonTree",
        "mode": "core_genome_codon_protein", "inputs": [], "artifact_refs": [],
        "observed_run": {"original_task_id": None, "source_revision": None, "settings": [], "commands": [],
            "engines": [], "conflicts": [], "completeness": "unknown"},
        "documents": {"analyses": [analysis], "store": {key: [] for key in
            ("alignments", "tree_documents", "partitions", "phyloxml", "source_records", "native_tables")}},
        "joins": {key: [] for key in ("input_rows", "tip_rows", "feature_genomes", "functions", "function_equivalences",
            "taxa", "display_tips", "transformations", "residues", "organismal_tips", "family_blocks")},
        "populations": pops, "genomes": [], "families": [family], "models": [], "native_measurements": [],
        "support_observations": [], "dependence_groups": [], "qualifications": [], "missing_requirements": [],
        "assembly": {"version": "bvbrc_phylogeny_assembly_v1", "analysis_id": "synthetic",
            "caller_populations": deepcopy(pops), "locus_bindings": [], "genome_request_sets": [],
            "family_matrices": [{"matrix_id": "main-matrix", "namespace": "PGFam",
                "family_population_id": "returned", "genome_population_id": "main",
                "rows": [{"family_id": "F1", **deepcopy(row), "evidence": []} for row in rows],
                "completeness": "complete", "evidence": []}],
            "historical_frequencies": [], "model_associations": []}, "read_outcomes": []}


def calculate(sheet, genome="main"):
    return calc.codon_family_population_components(sheet, family_population_id="returned", genome_population_id=genome)


def values(component):
    return {key: quantity["value"] for key, quantity in component["rows"][0].items() if key != "family_id"}


def test_complete_main_subset_retains_external_memberships_and_exact_denominator():
    sheet = scoped_sheet()
    before = deepcopy(sheet)
    got = calculate(sheet)
    assert values(got) == {"present_genomes": 1, "missing_genomes": 1, "extra_copies": 1,
                           "presence_fraction": .5, "native_initial_family_rank": 0}
    assert got["population_genomes"]["value"] == 2
    assert got["population_families"]["value"] == 1
    fraction = got["rows"][0]["presence_fraction"]
    assert (fraction["numerator"], fraction["denominator"], fraction["population_ref"]) == (1, 2, "main")
    assert calc.codon_calculation_requirements(got) == []
    assert sheet == before


def test_complete_empty_main_retains_unrelated_native_memberships():
    sheet = scoped_sheet(empty=True)
    before = deepcopy(sheet)
    got = calculate(sheet)
    assert values(got) == {"present_genomes": 0, "missing_genomes": 0, "extra_copies": 0,
                           "presence_fraction": None, "native_initial_family_rank": 0}
    fraction = got["rows"][0]["presence_fraction"]
    assert (fraction["numerator"], fraction["denominator"]) == (0, 0)
    assert got["population_genomes"]["value"] == 0
    assert calc.codon_calculation_requirements(got) == []
    assert sheet == before


def test_external_requested_population_is_unknown_without_its_matrix_rows():
    got = calculate(scoped_sheet(), genome="optional")
    assert got["population_genomes"]["value"] == 1
    assert all(value is None for value in values(got).values())
    assert got["rows"][0]["presence_fraction"]["denominator"] == 1
    assert {row["reason_code"] for row in calc.codon_calculation_requirements(got)} == {"family_membership_required"}


@pytest.mark.parametrize("state", ["unknown", "partial", "truncated"])
def test_empty_unknown_main_does_not_become_measured_zero(state):
    sheet = scoped_sheet(empty=True)
    sheet["populations"]["genomes"][0]["completeness"] = state
    got = calculate(sheet)
    assert got["population_genomes"]["value"] is None
    assert all(value is None for value in values(got).values())
    assert "genome_population_required" in {r["reason_code"] for r in calc.codon_calculation_requirements(got)}


@pytest.mark.parametrize("state", ["complete", "partial", "truncated", "unknown"])
def test_explicit_feature_genome_conflict_rejected_for_every_matrix_state(state):
    sheet = scoped_sheet()
    sheet["families"][0]["matrix_completeness"] = state
    sheet["families"][0]["memberships"] = [membership(features=("a",), genomes=("G2",))]
    with pytest.raises(ValueError, match="^phylogeny_codon_representation_genome_membership_conflict$"):
        calculate(sheet)


def test_explicit_unselected_matrix_mapping_conflict_is_still_rejected():
    sheet = scoped_sheet()
    sheet["families"][0]["matrix"].append({"genome_id": "Goptional", "feature_ids": ["outside"]})
    sheet["families"][0]["memberships"] = [membership(features=("outside",), genomes=("G1",))]
    with pytest.raises(ValueError, match="^phylogeny_codon_representation_genome_membership_conflict$"):
        calculate(sheet)


@pytest.mark.parametrize("mutation,code", [
    (lambda f: f["matrix"].append({"genome_id": "Goptional", "feature_ids": ["a"]}), "codon_feature_genome_membership_conflict"),
    (lambda f: f["matrix"].append({"genome_id": "G1", "feature_ids": []}), "codon_duplicate_matrix_genome"),
    (lambda f: f["matrix"][0]["feature_ids"].append("a"), "duplicate_identifier"),
    (lambda f: f["memberships"].append(deepcopy(f["memberships"][0])), "codon_duplicate_representation_record"),
    (lambda f: f["memberships"][0]["deleted_feature_ids"].append("a"), "codon_included_deleted_feature_conflict"),
])
def test_structural_and_membership_conflicts_remain_invalid(mutation, code):
    sheet = scoped_sheet()
    mutation(sheet["families"][0])
    with pytest.raises(ValueError, match="^phylogeny_" + code + "$"):
        calculate(sheet)


def test_independent_lists_are_not_zipped_and_absent_mappings_are_not_inferred():
    sheet = scoped_sheet()
    sheet["families"][0]["matrix"][1]["feature_ids"] = ["c"]
    sheet["families"][0]["memberships"] = [membership(
        features=("c", "a", "b", "unmapped"), genomes=("G1", "Goptional", "G2"))]
    before = deepcopy(sheet)
    assert values(calculate(sheet)) == {"present_genomes": 2, "missing_genomes": 0, "extra_copies": 1,
                                       "presence_fraction": 1, "native_initial_family_rank": 1}
    assert sheet == before


def test_unknown_membership_genomes_do_not_invalidate_explicit_matrix():
    sheet = scoped_sheet()
    sheet["families"][0]["memberships"] = [membership(features=("a", "unmapped"), genomes=())]
    assert values(calculate(sheet))["presence_fraction"] == .5


def test_missing_selected_matrix_row_is_not_zero_or_repaired_from_membership():
    sheet = scoped_sheet()
    sheet["families"][0]["matrix"].pop()
    got = calculate(sheet)
    assert all(value is None for value in values(got).values())
    assert {row["reason_code"] for row in calc.codon_calculation_requirements(got)} == {"family_membership_required"}


def retained_subset_sheet():
    """Use exact rows in two retained artifacts, never feature-name parsing."""
    path = NATIVE / "test9_genome_8taxa_10cds_10proteins.pgfamsAndGenesIncludedInAlignment.txt"
    data = path.read_bytes()
    artifact = {"raw_artifact_ref": "retained/membership", "source_ref": "source/retained/membership",
                "sha256": hashlib.sha256(data).hexdigest()}
    result = native.parse_codon_membership(data, artifact=artifact, dialect="pgfams_legacy")
    assert result["status"] == "ok"
    table = result["value"]["table"]
    fid, genome = "PGF_00017063", "1075089.3"
    triples = [line.split("\t") for line in (NATIVE / "test9_genome.genomeGenePgfams.txt").read_text().splitlines()]
    mapping = {feature: gid for gid, feature, family_id in triples if family_id == fid}
    assert len(mapping) == 8
    sheet = scoped_sheet()
    family = sheet["families"][0]
    family["family_id"] = fid
    family["matrix"] = [{"genome_id": genome, "feature_ids": [feature for feature, gid in mapping.items() if gid == genome]}]
    assert family["matrix"][0]["feature_ids"] == ["fig|1075089.3.peg.399"]
    family["memberships"] = []
    for row in result["value"]["rows"]:
        if row["family_id"] == fid:
            family["memberships"].append({"representation": row["representation"],
                "feature_ids": deepcopy(row["included_feature_ids"]),
                "genome_ids": list(dict.fromkeys(mapping[f] for f in row["included_feature_ids"])),
                "deleted_feature_ids": deepcopy(row["deleted_feature_ids"]),
                "missing_codon_feature_ids": deepcopy(row["missing_codon_feature_ids"]),
                "source_table_id": table["table_id"], "source_row_index": row["source_row_index"]})
    sheet["populations"]["families"][0]["family_ids"] = [fid]
    sheet["populations"]["genomes"][0]["genome_ids"] = [genome]
    sheet["populations"]["genomes"] = sheet["populations"]["genomes"][:1]
    sheet["documents"]["store"]["native_tables"] = [table]
    sheet["documents"]["analyses"][0]["membership_document_id"] = table["table_id"]
    sheet["artifact_refs"] = [artifact]
    sheet["joins"]["feature_genomes"] = [{"feature_id": feature, "genome_id": gid,
        "family_id": fid, "family_namespace": "PGFam", "evidence": []} for feature, gid in mapping.items()]
    sheet["assembly"]["caller_populations"] = deepcopy(sheet["populations"])
    sheet["assembly"]["family_matrices"][0]["rows"] = [{"family_id": fid, **deepcopy(row), "evidence": []} for row in family["matrix"]]
    return sheet


def test_retained_native_membership_with_explicit_single_genome_scope():
    sheet = retained_subset_sheet()
    before = deepcopy(sheet)
    got = calculate(sheet)
    assert got["population_genomes"]["value"] == got["population_families"]["value"] == 1
    assert values(got) == {"present_genomes": 1, "missing_genomes": 0, "extra_copies": 0,
                           "presence_fraction": 1, "native_initial_family_rank": 1}
    assert [len(row["feature_ids"]) for row in sheet["families"][0]["memberships"]] == [8, 8]
    assert sheet == before


def test_saved_json_recalculation_uses_production_calculator_without_external_access(monkeypatch):
    assert Path(calc.__file__).resolve() == ROOT / "gene_annotation_episode/bvbrc_codon_tree_calculators.py"
    originals = [scoped_sheet(), scoped_sheet(empty=True), retained_subset_sheet()]
    saved = json.loads(json.dumps(originals))
    expected = [calculate(sheet) for sheet in originals]
    before = deepcopy(saved)
    attempted = []

    def denied(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("Recalculation must use only saved numerical operands")

    with monkeypatch.context() as guard:
        for module, name in [(builtins, "open"), (io, "open"), (os, "open"), (os, "system"),
                             (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"),
                             (socket, "create_connection"), (urllib.request, "urlopen")]:
            guard.setattr(module, name, denied)
        for module in (native, formats):
            for name in dir(module):
                if name.startswith("parse_"):
                    guard.setattr(module, name, denied)
        guard.setattr(builtins, "__import__", denied)
        actual = [calculate(sheet) for sheet in saved]
        requirements = [calc.codon_calculation_requirements(component) for component in actual]
    assert attempted == []
    assert actual == expected
    assert requirements == [[], [], []]
    assert saved == before
