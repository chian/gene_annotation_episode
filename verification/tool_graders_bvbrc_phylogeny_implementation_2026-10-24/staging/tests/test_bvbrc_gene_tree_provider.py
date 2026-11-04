"""Actual shared/provider path: synthetic hand cases and retained native XML.

No test invokes BV-BRC or claims Store custody. Synthetic evidence names below
identify explicitly constructed fixture values. Native XML is the retained
official repository example, not a newly executed AppService result.
"""
from __future__ import annotations

import ast
import builtins
from copy import deepcopy
import hashlib
import inspect
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import urllib.request
from urllib.parse import quote

import pytest

from gene_annotation_episode import bvbrc_gene_tree_inputs as provider
from gene_annotation_episode import bvbrc_gene_tree_grader as grader
from gene_annotation_episode import bvbrc_phylogeny_common_inputs as common_inputs
from gene_annotation_episode import bvbrc_phylogeny_common_contracts as common_contracts
from gene_annotation_episode import bvbrc_phylogeny_common_grader as common_grader
from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import phylogeny_calculators as calculators
from gene_annotation_episode import phylogeny_calculation_contracts as calculation_contracts


STAGING = Path(__file__).resolve().parents[1]
BOUNDARIES = STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
NATIVE = BOUNDARIES / "additional_sources" / "bvbrc_gene_tree" / "tests"
XML_NAMES = ("Buchnera_acpS_fg_dna_raxml_hky85.xml",
             "Buchnera_acpS_fg_dna_raxml_hky85_RAxML_tree_rell.xml")
POPULATIONS = ("alignments", "leaves", "composition", "taxonomy", "genomes",
               "families", "bootstraps", "native")
JOINS = ("input_rows", "tip_rows", "feature_genomes", "functions",
         "function_equivalences", "taxa", "display_tips", "transformations", "residues", "organismal_tips")
SHEET_KEYS = {"schema_version", "tool", "mode", "inputs", "artifact_refs", "observed_run",
    "documents", "joins", "populations", "loci", "native_measurements", "support_observations",
    "dependence_groups", "qualifications", "missing_requirements", "assembly", "read_outcomes"}
COMPONENT_KEYS = {"schema_version", "parameters", "alignments", "trees", "bootstrap", "coordinate_maps",
    "original_coverage", "composition", "taxonomy", "comparisons", "missing_requirements", "diagnostics"}


def artifact(data, name):
    source = ("retained-official-repository-example/" + name.removeprefix("retained-official-example/")
              if name.startswith("retained-official-example/") else "synthetic-source/" + name)
    return {"raw_artifact_ref": name, "source_ref": source,
            "sha256": hashlib.sha256(data).hexdigest()}


def evidence(value, name, pointer=""):
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return {"content": {"source_ref": "synthetic-source/" + name,
                       "artifact_field": "artifact_ref", "artifact_ref": name,
                       "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)},
            "pointer": pointer}


def empty_run():
    return {"original_task_id": None, "source_revision": None, "settings": [],
            "commands": [], "engines": [], "conflicts": [], "completeness": "unknown"}


def empty_assembly(analysis_id="primary"):
    return {"version": "bvbrc_phylogeny_assembly_v1", "analysis_id": analysis_id,
            "caller_populations": {name: [] for name in POPULATIONS}, "locus_bindings": [],
            "genome_request_sets": [], "family_matrices": [], "historical_frequencies": [],
            "model_associations": []}


def empty_store():
    return {name: [] for name in ("alignments", "tree_documents", "partitions", "phyloxml",
                                 "source_records", "native_tables")}


def parameters():
    return {"version": "gene_tree_components_v1", "alignment_requests": [],
            "original_coverage_population_ids": [], "tree_requests": [], "bootstrap_requests": [],
            "composition_population_ids": [], "taxon_requests": [], "comparisons": []}


def whole_id(analysis_id, kind, document_id):
    return "analysis/" + quote(analysis_id, safe="-._~") + "/" + kind + "/" + quote(document_id, safe="-._~") + "/whole"


def read(data, name, reader):
    ref = artifact(data, name)
    if reader == "aligned_fasta":
        spec = {"reader": reader, "id_rule": "first_whitespace_token", "encoding": "ascii"}
        result = formats.parse_aligned_fasta(data, artifact=ref,
                   id_rule="first_whitespace_token", encoding="ascii")
    elif reader == "phyloxml":
        spec = {"reader": reader}
        result = formats.parse_phyloxml(data, artifact=ref)
    else:
        spec = {"reader": "newick", "dialect": "newick", "allow_multiple": True}
        result = formats.parse_newick(data, artifact=ref, dialect="newick", allow_multiple=True)
    return {"read_id": "read/" + name, "artifact": ref, "reader": spec, "result": result}


def tree_args(data=b"((q:0,q:0.2)75:0.3,(c:-0.1,d:0.4):0.2);", *, xml=False, name="synthetic/tree"):
    observed = read(data, name, "phyloxml" if xml else "newick")
    doc = observed["result"]["value"]
    assert doc is not None
    tree = doc["trees"][0]["tree"] if xml else doc["trees"][0]
    store = empty_store()
    store["phyloxml" if xml else "tree_documents"].append(doc)
    analysis = {"analysis_id": "primary", "mode": "gene_tree", "locus_ids": [],
                "aligned_document_id": None, "raw_tree_id": None if xml else tree["tree_id"],
                "phyloxml_tree_id": tree["tree_id"] if xml else None,
                "native_engine_observation_ids": [], "output_role_evidence": []}
    return {"documents": {"parsed": {"store": store, "analyses": [analysis]},
                          "raxml_runs": [], "reads": [observed]},
            "inputs": (), "observed_run": empty_run(), "joins": {key: [] for key in JOINS},
            "assembly": empty_assembly(), "parameters": {"source_dialect": "retained_bvbrc_gene_tree",
                "raw_tree_required_for_branch_facts": False}}


def ordinary_args(sequences=("A-CX", "ATCX", "ATGX", "AT-X")):
    args = tree_args()
    labels = ["q", "q", "c", "d"]
    data = "".join(">" + label + " retained header\n" + seq + "\n"
                   for label, seq in zip(labels, sequences)).encode()
    observed = read(data, "synthetic/alignment", "aligned_fasta")
    document = observed["result"]["value"]
    args["documents"]["reads"].append(observed)
    args["documents"]["parsed"]["store"]["alignments"].append(document)
    analysis = args["documents"]["parsed"]["analyses"][0]
    analysis.update(aligned_document_id=document["alignment_id"], locus_ids=["locus-a"])
    members, bindings = [], []
    for index, sequence in enumerate(sequences):
        original = {"sequence": sequence.replace("-", "")}
        ev = evidence(original, "synthetic/input/" + str(index), "/sequence")
        binding_id = "file/" + str(index)
        member = {"input_binding_id": binding_id, "member_id": "q"}
        members.append(member)
        bindings.append({"binding_id": binding_id, "parameter_pointer": "/sequences/" + str(index),
            "kind": "inline_parameter", "content": None, "workspace_path": None,
            "inline_value": original, "link_evidence": None,
            "members": [{"member_id": "q", "member_pointer": "/sequence",
                "length": len(original["sequence"]), "molecule": "protein",
                "sequence_sha256": hashlib.sha256(original["sequence"].encode()).hexdigest(), "evidence": ev}]})
        args["joins"]["input_rows"].append({"alignment_id": document["alignment_id"], "row_index": index,
            **member, "locus_id": "locus-a", "transformation_id": None, "evidence": [ev]})
        args["joins"]["tip_rows"].append({"tree_id": analysis["raw_tree_id"], "node_index": (2, 3, 5, 6)[index],
            "alignment_id": document["alignment_id"], "row_index": index, "evidence": [ev]})
    args["inputs"] = tuple(bindings)
    args["assembly"]["locus_bindings"] = [{"locus_id": "locus-a", "input_members": members,
        "completeness": "complete", "evidence": [evidence(members, "synthetic/locus-a")]}]
    args["observed_run"]["settings"] = [
        {"name": "recipe", "value": "raxml", "origin": "requested", "evidence": [], "location": None},
        {"name": "alphabet", "value": "protein", "origin": "observed",
         "evidence": [evidence({"alphabet": "protein"}, "synthetic/alphabet", "/alphabet")], "location": None}]
    return args


def extract(args):
    result = provider.extract_gene_tree_sheet(**args)
    assert result["value"] is not None, result
    return result, result["value"]


def alignment_parameters(sheet):
    params = parameters()
    analysis = sheet["documents"]["analyses"][0]
    params["alignment_requests"] = [{"population_id": whole_id("primary", "alignment", analysis["aligned_document_id"]),
                                     "alphabet": "protein", "case_policy": "uppercase", "pairs": [[0, 1]]}]
    return params


def tree_parameters(sheet):
    params = parameters()
    analysis = sheet["documents"]["analyses"][0]
    tree_id = analysis["raw_tree_id"] or analysis["phyloxml_tree_id"]
    params["tree_requests"] = [{"population_id": whole_id("primary", "tree", tree_id),
                               "branch_unit": "native_unknown", "pairs": []}]
    return params


def stage(locus, stage_name, member_index=0):
    ref = locus["input_members"][member_index]
    subject = common_inputs.input_member_subject_id(ref["input_binding_id"], ref["member_id"])
    return next(row for row in locus["inclusion"]
                if row["subject_id"] == subject and row["stage"] == stage_name)


def transformation(kind, name, member, alignment_id, row_index=0, **changes):
    value = {"transformation_id": name, "kind": kind, "input_members": [deepcopy(member)],
             "output_rows": [{"alignment_id": alignment_id, "row_index": row_index}],
             "before_header": None, "after_label": None, "segment_id": None, "locus_order": [],
             "removed_alignment_columns_0based": None, "before_sequence_sha256": None,
             "after_sequence_sha256": None, "evidence": []}
    value.update(changes)
    value["evidence"] = [evidence(value, "synthetic/transformation/" + name)]
    return value


def test_origins_signatures_and_no_external_operations():
    for module in (provider, grader, common_inputs, common_contracts, common_grader,
                   formats, calculators, calculation_contracts):
        assert Path(module.__file__).resolve().parent == STAGING / "gene_annotation_episode"
    signature = inspect.signature(provider.extract_gene_tree_sheet)
    assert list(signature.parameters) == ["documents", "inputs", "observed_run", "joins", "assembly", "parameters"]
    assert all(item.kind == inspect.Parameter.KEYWORD_ONLY for item in signature.parameters.values())
    assert list(inspect.signature(provider.validate_gene_tree_sheet).parameters) == ["sheet"]
    assert list(inspect.signature(grader.calculate_gene_tree).parameters) == ["sheet", "parameters"]
    for module in (provider, grader):
        syntax = ast.parse(Path(module.__file__).read_text())
        imports = {node.module for node in ast.walk(syntax) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(syntax) if isinstance(node, ast.Import) for alias in node.names)
        assert imports <= {"__future__", "copy", "urllib.parse", "bvbrc_phylogeny_common_inputs",
                           "bvbrc_phylogeny_common_contracts", "bvbrc_phylogeny_common_grader", "bvbrc_gene_tree_inputs"}


def test_ordinary_mode_exact_shapes_and_hand_arithmetic():
    args = ordinary_args()
    before = deepcopy(args)
    result, sheet = extract(args)
    assert args == before
    assert set(result) == {"status", "value", "diagnostics"}
    assert set(sheet) == SHEET_KEYS
    assert sheet["mode"] == "gene_tree"
    assert sheet["documents"] == args["documents"]["parsed"]
    assert sheet["assembly"] == args["assembly"]
    assert len(sheet["loci"]) == 1
    assert stage(sheet["loci"][0], "supplied")["state"] == "included"
    assert stage(sheet["loci"][0], "final_matrix")["state"] == "included"
    assert stage(sheet["loci"][0], "final_tree")["state"] == "included"
    for name in ("post_align", "post_trim", "post_gap_filter"):
        assert stage(sheet["loci"][0], name)["state"] == "unknown"
    params = alignment_parameters(sheet)
    components = grader.calculate_gene_tree(sheet, params)
    assert set(components) == COMPONENT_KEYS
    assert components["parameters"] == params
    alignment = components["alignments"][0]
    assert alignment["cell_count"]["value"] == 16
    assert alignment["gap_cells"]["value"] == 2
    assert alignment["gap_fraction"]["value"] == 2 / 16
    assert alignment["canonical_cells"]["value"] == 10
    assert alignment["ambiguity_cells"]["value"] == 4
    assert alignment["sites"][2]["canonical_entropy_bits"]["value"] == pytest.approx(0.9182958340544896)
    assert alignment["pairs"][0]["identity_fraction"]["value"] == 1
    assert alignment["pairs"][0]["identical_positions"]["value"] == 2
    assert math.isclose(grader.calculate_gene_tree(sheet, tree_parameters(sheet))["trees"][0]["branch_length_sum"]["value"], 1)


def test_same_member_labels_in_distinct_original_bindings_remain_distinct():
    _, sheet = extract(ordinary_args())
    assert [row["member_label"] for row in sheet["documents"]["store"]["alignments"][0]["rows"]][:2] == ["q", "q"]
    subjects = [row["subject_id"] for row in sheet["loci"][0]["inclusion"] if row["stage"] == "supplied"]
    assert len(set(subjects)) == 4
    assert subjects[:2] == ["member/file%2F0/q", "member/file%2F1/q"]


def test_requested_recipe_does_not_supply_observed_support_or_units():
    _, sheet = extract(ordinary_args())
    assert not sheet["observed_run"]["engines"]
    assert not any(row["name"] == "recipe" and row["origin"] == "observed" for row in sheet["observed_run"]["settings"])
    native = [row for row in sheet["native_measurements"] if row["field"] == "branch_support_native"]
    assert [row["value"] for row in native] == [75]
    assert all(row["method"] == "native_unknown" for row in native)
    components = grader.calculate_gene_tree(sheet, tree_parameters(sheet))
    branches = components["trees"][0]["branches"]
    assert all(row["support_rescaled"]["value"] is None for row in branches)
    assert any(row["length"]["value"] == -0.1 for row in branches)
    assert any(row["length"]["value"] == 0 for row in branches)


@pytest.mark.parametrize("case", ["missing", "requested_only", "conflicting", "unevidenced"])
def test_alphabet_request_cannot_supply_missing_or_conflicting_scientific_metadata(case):
    args = ordinary_args()
    # Remove the independent original-member evidence too: these cases test
    # unavailable scientific context, not merely an absent observed setting.
    for binding in args["inputs"]:
        binding["members"][0]["evidence"] = None
    settings = args["observed_run"]["settings"]
    if case == "missing":
        settings[:] = [row for row in settings if row["name"] != "alphabet"]
    elif case == "requested_only":
        settings[1]["origin"] = "requested"
    elif case == "conflicting":
        extra = deepcopy(settings[1])
        extra["value"] = "dna"
        extra["evidence"] = [evidence({"alphabet": "dna"}, "synthetic/conflicting-alphabet", "/alphabet")]
        settings.append(extra)
    else:
        settings[1]["evidence"] = []
    _, sheet = extract(args)
    p = alignment_parameters(sheet)
    components = grader.calculate_gene_tree(sheet, p)
    assert components["parameters"] == p
    alignment = components["alignments"][0]
    assert alignment["canonical_cells"]["value"] is None
    assert alignment["ambiguity_cells"]["value"] is None
    assert alignment["gap_cells"]["value"] == 2
    assert alignment["cell_count"]["value"] == 16
    assert alignment["sites"][3]["symbol_counts"] == [{"symbol": "X", "count": 4}]
    assert components["diagnostics"]
    assert components["missing_requirements"]


def test_complete_member_evidence_supplies_alphabet_but_partial_coverage_cannot():
    args = ordinary_args()
    args["observed_run"]["settings"][:] = [row for row in args["observed_run"]["settings"]
                                               if row["name"] != "alphabet"]
    _, sheet = extract(args)
    parameters = alignment_parameters(sheet)
    complete = grader.calculate_gene_tree(sheet, parameters)
    assert complete["alignments"][0]["canonical_cells"]["value"] == 10
    assert complete["alignments"][0]["ambiguity_cells"]["value"] == 4
    args["inputs"][-1]["members"][0]["evidence"] = None
    _, partial_sheet = extract(args)
    partial = grader.calculate_gene_tree(partial_sheet, parameters)
    assert partial["parameters"] == parameters
    assert partial["alignments"][0]["canonical_cells"]["value"] is None
    assert partial["alignments"][0]["cell_count"]["value"] == 16
    assert partial["alignments"][0]["gap_cells"]["value"] == 2


def concatenated_args():
    args = ordinary_args(("AC--", "ATGC", "ATGC", "ATGC"))
    analysis = args["documents"]["parsed"]["analyses"][0]
    analysis.update(mode="concatenated_sequence_loci", locus_ids=["locus-a", "segment-b"])
    first = args["assembly"]["locus_bindings"][0]
    second = {"locus_id": "segment-b", "input_members": deepcopy(first["input_members"]),
              "completeness": "complete", "evidence": deepcopy(first["evidence"])}
    args["assembly"]["locus_bindings"].append(second)
    for row in deepcopy(args["joins"]["input_rows"]):
        row["locus_id"] = "segment-b"
        if row["row_index"] == 0:
            row["transformation_id"] = "gap-fill"
        args["joins"]["input_rows"].append(row)
    member = first["input_members"][0]
    aid = analysis["aligned_document_id"]
    gap = transformation("missing_locus_gap_fill", "gap-fill", member, aid, locus_order=["segment-b"])
    concat = transformation("concatenate", "concat", member, aid, locus_order=["locus-a", "segment-b"])
    trim = transformation("end_trim", "trim-a-only", member, aid, locus_order=["locus-a"],
                          removed_alignment_columns_0based=[0])
    args["joins"]["input_rows"][0]["transformation_id"] = "trim-a-only"
    args["joins"]["transformations"] = [gap, concat, trim]
    return args


def test_concatenation_preserves_original_loci_and_gap_fill_without_filter_inference():
    args = concatenated_args()
    gap, concat, trim = args["joins"]["transformations"]
    _, sheet = extract(args)
    assert sheet["mode"] == "concatenated_sequence_loci"
    assert [row["locus_id"] for row in sheet["loci"]] == ["locus-a", "segment-b"]
    assert sheet["joins"]["transformations"] == [gap, concat, trim]
    assert stage(sheet["loci"][0], "post_trim")["state"] == "included"
    assert stage(sheet["loci"][1], "post_trim")["state"] == "unknown"
    assert stage(sheet["loci"][1], "final_matrix")["reason"] == "missing_locus_gap_fill"
    assert stage(sheet["loci"][1], "post_gap_filter")["state"] == "unknown"
    assert not any(item["state"] == "excluded" for row in sheet["loci"] for item in row["inclusion"])
    c = grader.calculate_gene_tree(sheet, alignment_parameters(sheet))["alignments"][0]
    assert c["member_count"]["value"] == 4
    assert c["gap_fraction"]["value"] == 2 / 16
    args["joins"]["transformations"][0]["locus_order"] = ["locus-a"]
    invalid = provider.extract_gene_tree_sheet(**args)
    assert invalid["status"] == "invalid"
    assert invalid["diagnostics"][-1]["code"] == "gene_tree_locus_order_conflict"


@pytest.mark.parametrize("kind,changes", [
    ("selected_segment", {"segment_id": "supplied-segment-2"}),
    ("amino_acid_J_to_X", {}),
    ("end_trim", {"removed_alignment_columns_0based": [0, 5]}),
    ("header_tokenization", {"before_header": "q full original header", "after_label": "q"}),
    ("duplicate_suffix", {"before_header": "q", "after_label": "q_2"}),
])
def test_supplied_transformations_are_retained_without_inventing_original_maps(kind, changes):
    args = ordinary_args()
    if kind == "amino_acid_J_to_X":
        original = args["inputs"][0]
        original["inline_value"]["sequence"] = "ACJ"
        original["members"][0]["sequence_sha256"] = hashlib.sha256(b"ACJ").hexdigest()
        original["members"][0]["evidence"] = evidence(original["inline_value"], "synthetic/before-j-to-x", "/sequence")
    if kind == "duplicate_suffix":
        observed = args["documents"]["reads"][1]
        data = b">q_2 retained header\nA-CX\n>q retained header\nATCX\n>c retained header\nATGX\n>d retained header\nAT-X\n"
        changed = read(data, "synthetic/alignment", "aligned_fasta")
        args["documents"]["reads"][1] = changed
        args["documents"]["parsed"]["store"]["alignments"][0] = changed["result"]["value"]
    join = args["joins"]["input_rows"][0]
    transform = transformation(kind, "transform", {"input_binding_id": join["input_binding_id"],
                                                  "member_id": join["member_id"]}, join["alignment_id"], **changes)
    args["joins"]["transformations"] = [transform]
    join["transformation_id"] = "transform"
    _, sheet = extract(args)
    assert sheet["joins"]["transformations"] == [transform]
    assert stage(sheet["loci"][0], "post_trim")["state"] == ("included" if kind == "end_trim" else "unknown")
    params = alignment_parameters(sheet)
    params["original_coverage_population_ids"] = [params["alignment_requests"][0]["population_id"]]
    components = grader.calculate_gene_tree(sheet, params)
    assert components["original_coverage"][0]["rows"][0]["original_member_coverage"]["value"] is None
    assert components["original_coverage"][0]["missing_requirements"]


def test_auxiliary_comparison_tree_and_unselected_locus_remain_saved():
    args = ordinary_args()
    auxiliary = read(b"((a:1,c:1):1,(b:1,d:1):1);", "synthetic/organismal", "newick")
    args["documents"]["reads"].append(auxiliary)
    args["documents"]["parsed"]["store"]["tree_documents"].append(auxiliary["result"]["value"])
    binding = deepcopy(args["assembly"]["locus_bindings"][0])
    binding["locus_id"] = "supplied-unused-locus"
    args["assembly"]["locus_bindings"].append(binding)
    _, sheet = extract(args)
    assert len(sheet["documents"]["analyses"]) == 1
    assert len(sheet["documents"]["store"]["tree_documents"]) == 2
    assert sheet["documents"]["store"]["tree_documents"][1] == auxiliary["result"]["value"]
    unused = sheet["loci"][1]
    assert unused["analysis_ids"] == [] and len(unused["input_members"]) == 4
    assert stage(unused, "supplied")["state"] == "included"
    assert stage(unused, "final_matrix")["state"] == "unknown"


def transformed_args():
    args = ordinary_args()
    original = args["inputs"][0]
    original["inline_value"]["sequence"] = "ACJ"
    original["members"][0]["sequence_sha256"] = hashlib.sha256(b"ACJ").hexdigest()
    original["members"][0]["evidence"] = evidence(original["inline_value"], "synthetic/before-j-to-x", "/sequence")
    join = args["joins"]["input_rows"][0]
    join["transformation_id"] = "J-to-X"
    tr = transformation("amino_acid_J_to_X", "J-to-X",
        {"input_binding_id": join["input_binding_id"], "member_id": join["member_id"]}, join["alignment_id"],
        before_sequence_sha256=hashlib.sha256(b"ACJ").hexdigest(),
        after_sequence_sha256=hashlib.sha256(b"A-CX").hexdigest())
    args["joins"]["transformations"] = [tr]
    return args


def test_exact_transformation_digests_preserve_symbols_and_do_not_replace_coordinate_maps():
    _, sheet = extract(transformed_args())
    tr = sheet["joins"]["transformations"][0]
    assert tr["before_sequence_sha256"] == hashlib.sha256(b"ACJ").hexdigest()
    assert tr["after_sequence_sha256"] == hashlib.sha256(b"A-CX").hexdigest()
    p = alignment_parameters(sheet)
    p["original_coverage_population_ids"] = [p["alignment_requests"][0]["population_id"]]
    components = grader.calculate_gene_tree(sheet, p)
    assert components["original_coverage"][0]["rows"][0]["original_member_coverage"]["value"] is None


@pytest.mark.parametrize("change", ["ungapped_after", "lowercase_after", "wrong_before", "unknown_before",
                                   "multiple_inputs", "multiple_outputs"])
def test_contradictory_scalar_transformation_digests_are_rejected(change):
    args = transformed_args()
    tr = args["joins"]["transformations"][0]
    if change == "ungapped_after":
        tr["after_sequence_sha256"] = hashlib.sha256(b"ACX").hexdigest()
    elif change == "lowercase_after":
        tr["after_sequence_sha256"] = hashlib.sha256(b"a-cx").hexdigest()
    elif change == "wrong_before":
        tr["before_sequence_sha256"] = hashlib.sha256(b"ACX").hexdigest()
    elif change == "unknown_before":
        args["inputs"][0]["members"][0]["sequence_sha256"] = None
    elif change == "multiple_inputs":
        tr["input_members"].append(deepcopy(args["assembly"]["locus_bindings"][0]["input_members"][1]))
    else:
        tr["output_rows"].append({"alignment_id": tr["output_rows"][0]["alignment_id"], "row_index": 1})
    result = provider.extract_gene_tree_sheet(**args)
    assert result["status"] == "invalid" and result["value"] is None


def test_multiple_transformation_operands_preserve_null_scalars_and_individual_original_facts():
    args = transformed_args()
    tr = args["joins"]["transformations"][0]
    tr["input_members"].append(deepcopy(args["assembly"]["locus_bindings"][0]["input_members"][1]))
    tr["output_rows"].append({"alignment_id": tr["output_rows"][0]["alignment_id"], "row_index": 1})
    tr["before_sequence_sha256"] = tr["after_sequence_sha256"] = None
    _, sheet = extract(args)
    assert sheet["joins"]["transformations"] == [tr]
    assert [b["members"][0]["sequence_sha256"] for b in sheet["inputs"]] == [
        b["members"][0]["sequence_sha256"] for b in args["inputs"]]


def test_explicit_trimmed_original_coordinates_use_original_denominator():
    args = ordinary_args()
    original = args["inputs"][0]
    original["inline_value"]["sequence"] = "QACXW"
    original["members"][0].update(length=5, sequence_sha256=hashlib.sha256(b"QACXW").hexdigest(),
        evidence=evidence(original["inline_value"], "synthetic/before-trim", "/sequence"))
    join = args["joins"]["input_rows"][0]
    tr = transformation("end_trim", "trim", {"input_binding_id": join["input_binding_id"],
         "member_id": join["member_id"]}, join["alignment_id"],
         removed_alignment_columns_0based=[0, 5], before_sequence_sha256=hashlib.sha256(b"QACXW").hexdigest(),
         after_sequence_sha256=hashlib.sha256(b"A-CX").hexdigest())
    args["joins"]["transformations"] = [tr]
    join["transformation_id"] = "trim"
    for row in args["documents"]["parsed"]["store"]["alignments"][0]["rows"]:
        member = args["assembly"]["locus_bindings"][0]["input_members"][row["row_index"]]
        pos = 0
        for column, symbol in enumerate(row["sequence"]):
            gap = symbol == "-"
            start = pos + (1 if row["row_index"] == 0 else 0)
            args["joins"]["residues"].append({"alignment_id": join["alignment_id"], "row_index": row["row_index"],
                "column_0based": column, "staged_ungapped_position_0based": None if gap else pos,
                "original_member": None if gap else deepcopy(member),
                "original_interval_0based_half_open": None if gap else [start, start + 1],
                "strand": "+", "translation_table": None,
                "transformation_id": "trim" if row["row_index"] == 0 else None, "evidence": deepcopy(tr["evidence"])})
            pos += not gap
    _, sheet = extract(args)
    p = alignment_parameters(sheet)
    p["original_coverage_population_ids"] = [p["alignment_requests"][0]["population_id"]]
    c = grader.calculate_gene_tree(sheet, p)
    rows = c["original_coverage"][0]["rows"]
    assert rows[0]["original_length"]["value"] == 5
    assert rows[0]["original_covered_positions"]["value"] == 3
    assert rows[0]["original_member_coverage"]["value"] == 3 / 5
    assert c["alignments"][0]["rows"][0]["matrix_occupancy"]["value"] == 3 / 4


def test_all_gap_row_is_retained_with_unknown_filter_history():
    _, sheet = extract(ordinary_args(("----", "ATCX", "ATGX", "AT-X")))
    assert stage(sheet["loci"][0], "final_matrix")["state"] == "included"
    assert stage(sheet["loci"][0], "final_matrix")["reason"] is None
    assert stage(sheet["loci"][0], "post_gap_filter")["state"] == "unknown"
    component = grader.calculate_gene_tree(sheet, alignment_parameters(sheet))["alignments"][0]
    assert component["member_count"]["value"] == 4
    assert component["rows"][0]["nongap_count"]["value"] == 0


def test_null_alignment_preserves_independent_tree():
    _, sheet = extract(tree_args())
    assert sheet["documents"]["analyses"][0]["aligned_document_id"] is None
    components = grader.calculate_gene_tree(sheet, tree_parameters(sheet))
    assert components["trees"][0]["tip_count"]["value"] == 4
    assert components["alignments"] == []


def test_malformed_independent_alignment_retains_reader_failure_and_usable_tree():
    args = tree_args()
    bad = read(b">a\nAAA\n>b\nAA\n", "synthetic/bad-alignment", "aligned_fasta")
    assert bad["result"]["status"] != "ok"
    args["documents"]["reads"].append(bad)
    if bad["result"]["value"] is not None:
        args["documents"]["parsed"]["store"]["alignments"].append(bad["result"]["value"])
    result, sheet = extract(args)
    assert result["status"] == "partial"
    saved = next(row for row in sheet["read_outcomes"] if row["read_id"] == bad["read_id"])
    assert saved["status"] == bad["result"]["status"]
    assert saved["diagnostics"] == bad["result"]["diagnostics"]
    assert grader.calculate_gene_tree(sheet, tree_parameters(sheet))["trees"][0]["tip_count"]["value"] == 4


@pytest.mark.parametrize("name", XML_NAMES)
def test_retained_native_xml_examples_preserve_full_properties_unknown_support_and_zero_limits(name):
    data = (NATIVE / name).read_bytes()
    args = tree_args(data, xml=True, name="retained-official-example/" + name)
    result, sheet = extract(args)
    native = args["documents"]["parsed"]["store"]["phyloxml"][0]
    assert sheet["documents"]["store"]["phyloxml"] == [native]
    assert len(native["trees"][0]["annotations"]) == 32
    support = [row for row in sheet["native_measurements"] if row["field"] == "branch_support_native"]
    assert len(support) == 14
    assert all(row["method"] == "native_unknown" for row in support)
    assert sheet["qualifications"], "Converter limitations remain even when native XML parsing succeeds"
    params = tree_parameters(sheet)
    components = grader.calculate_gene_tree(sheet, params)
    assert components["trees"][0]["tip_count"]["value"] == 17
    assert components["trees"][0]["internal_node_count"]["value"] == 15
    assert all(row["support_rescaled"]["value"] is None for row in components["trees"][0]["branches"])
    assert sheet["observed_run"]["original_task_id"] is None


def test_xml_explicit_zero_survives_and_missing_raw_is_qualified():
    data = b'<phyloxml xmlns="http://www.phyloxml.org"><phylogeny rooted="true"><clade><branch_length>0</branch_length><confidence type="support">0</confidence><clade><name>A</name><branch_length>0</branch_length></clade><clade><name>B</name></clade></clade></phylogeny></phyloxml>'
    _, sheet = extract(tree_args(data, xml=True))
    support = [row for row in sheet["native_measurements"] if row["field"] == "branch_support_native"]
    assert len(support) == 1 and support[0]["value"] == 0
    assert support[0]["raw_token"] == "0"
    tree = sheet["documents"]["store"]["phyloxml"][0]["trees"][0]["tree"]
    assert tree["nodes"][1]["branch_length"] == 0
    assert tree["nodes"][2]["branch_length"] is None
    c = grader.calculate_gene_tree(sheet, tree_parameters(sheet))["trees"][0]
    assert c["known_branch_length_sum"]["value"] == 0
    assert c["branch_length_sum"]["value"] is None
    assert c["missing_branch_length_count"]["value"] == 1


def test_required_raw_tree_leaves_xml_topology_and_observations_usable():
    data = b'<phyloxml xmlns="http://www.phyloxml.org"><phylogeny><clade><clade><name>A</name><branch_length>0</branch_length></clade><clade><name>B</name><branch_length>0.5</branch_length></clade></clade></phylogeny></phyloxml>'
    args = tree_args(data, xml=True)
    args["parameters"]["raw_tree_required_for_branch_facts"] = True
    result, sheet = extract(args)
    native = [row for row in sheet["native_measurements"] if row["field"] == "branch_length"]
    assert [row["value"] for row in native] == [0, 0.5]
    assert any(row["reason_code"] == "raw_tree_required_for_branch_facts" for row in sheet["missing_requirements"])
    params = tree_parameters(sheet)
    params["tree_requests"][0]["pairs"] = [[1, 2]]
    component = grader.calculate_gene_tree(sheet, params)["trees"][0]
    assert component["tip_count"]["value"] == 2
    assert component["branch_length_sum"]["value"] is None
    assert component["known_branch_length_sum"]["value"] is None
    assert all(row["length"]["value"] is None for row in component["branches"])
    assert component["distances"][0]["value"]["value"] is None


def test_missing_locus_binding_is_unknown_not_known_empty():
    args = tree_args()
    args["documents"]["parsed"]["analyses"][0]["locus_ids"] = ["unmapped-locus"]
    result, sheet = extract(args)
    assert result["status"] == "partial"
    assert sheet["loci"] == [{"locus_id": "unmapped-locus", "input_members": [],
        "analysis_ids": ["primary"], "inclusion": [], "completeness": "unknown"}]
    assert any(row["reason_code"] == "gene_tree_locus_membership_unknown" for row in sheet["missing_requirements"])
    assert grader.calculate_gene_tree(sheet, tree_parameters(sheet))["trees"][0]["tip_count"]["value"] == 4


@pytest.mark.parametrize("change", ["second_primary", "wrong_alignment", "wrong_member", "complete_locus_omits_member",
                                   "wrong_assembly", "codon_only_assembly", "extra_parameter"])
def test_wrong_references_and_shapes_do_not_get_repaired(change):
    args = ordinary_args()
    if change == "second_primary":
        other = deepcopy(args["documents"]["parsed"]["analyses"][0])
        other["analysis_id"] = "other"
        args["documents"]["parsed"]["analyses"].append(other)
    elif change == "wrong_alignment":
        args["documents"]["parsed"]["analyses"][0]["aligned_document_id"] = "missing"
    elif change == "wrong_member":
        args["assembly"]["locus_bindings"][0]["input_members"][0]["member_id"] = "missing"
    elif change == "complete_locus_omits_member":
        args["assembly"]["locus_bindings"][0]["input_members"].pop()
    elif change == "wrong_assembly":
        args["assembly"]["analysis_id"] = "another"
    elif change == "codon_only_assembly":
        args["assembly"]["historical_frequencies"] = [{}]
    else:
        args["parameters"]["extra"] = True
    result = provider.extract_gene_tree_sheet(**args)
    assert result["status"] == "invalid"
    assert result["value"] is None
    assert result["diagnostics"]


@pytest.mark.parametrize("change", ["stage", "state", "subject", "reason", "analyses", "completeness", "extra", "mode"])
def test_saved_locus_tampering_is_rejected(change):
    _, sheet = extract(ordinary_args())
    if change == "extra":
        sheet["loci"][0]["invented_score"] = 1
    elif change == "mode":
        sheet["mode"] = "concatenated_sequence_loci"
    elif change == "analyses":
        sheet["loci"][0]["analysis_ids"] = ["unrelated"]
    elif change == "completeness":
        sheet["loci"][0]["completeness"] = "unknown"
    else:
        field = "subject_id" if change == "subject" else change
        sheet["loci"][0]["inclusion"][0][field] = {"stage": "selected", "state": "excluded",
            "subject": "member/file%2F4/q", "reason": "native_gap_filter"}[change]
    with pytest.raises(ValueError):
        provider.validate_gene_tree_sheet(sheet)
    with pytest.raises(ValueError):
        grader.calculate_gene_tree(sheet, parameters())


def test_calculation_closed_parameters_are_not_silently_shortened():
    _, sheet = extract(ordinary_args())
    for name in ("version", "tree_requests"):
        p = parameters()
        del p[name]
        with pytest.raises(ValueError, match="gene_tree_calculation_parameters_invalid"):
            grader.calculate_gene_tree(sheet, p)
    p = parameters()
    p["weights"] = {"arbitrary": 1}
    with pytest.raises(ValueError, match="gene_tree_calculation_parameters_invalid"):
        grader.calculate_gene_tree(sheet, p)


def test_saved_sheet_recalculation_no_io_and_no_caller_mutation(monkeypatch):
    args = ordinary_args()
    initial, sheet = extract(args)
    p = alignment_parameters(sheet)
    p["tree_requests"] = tree_parameters(sheet)["tree_requests"]
    saved_sheet, saved_parameters = json.dumps(sheet), json.dumps(p)
    decoded, params = json.loads(saved_sheet), json.loads(saved_parameters)
    expected = grader.calculate_gene_tree(decoded, params)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved provider calculation attempted I/O or acquisition")
    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(io, "open", forbidden)
        guard.setattr(os, "open", forbidden)
        guard.setattr(Path, "read_bytes", forbidden)
        guard.setattr(Path, "read_text", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(urllib.request, "urlopen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        assert provider.extract_gene_tree_sheet(**args) == initial
        assert grader.calculate_gene_tree(decoded, params) == expected
        validated = provider.validate_gene_tree_sheet(decoded)
        assert validated == decoded and validated is not decoded
    assert json.dumps(decoded) == saved_sheet
    assert json.dumps(params) == saved_parameters
    assert "function_confidence" not in json.dumps(expected)
