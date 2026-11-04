"""Iteration composition oracles; synthetic searches, retained native PSSMs.

No supplied membership/convergence fixture here verifies a native extractor.
"""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import blast_sequence_database as sequence
from gene_annotation_episode import blast_profile_calculators as profile
from gene_annotation_episode.blast_profile_inputs import populate_blast_profile_sheet
from gene_annotation_episode.blast_pssm_calculators import calculate_blast_pssm_components
from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm, read_blast_msa_master
from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components as calculate
from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet as populate
from tests.test_blast_iteration_inputs import (make_inputs, from_collection, add_pair, add_pssm, add_members,
    add_convergence, evidence, provenance, digest, operand, hsp)
from tests.test_blast_sequence_database import collect, invocation

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "verification/tool_graders_blast_pssm_2026-10-26_306/sources"


def run(args):
    return calculate(populate(**args))


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def values(result):
    return {k: v["value"] for k, v in result["counts"].items()}


def test_delivered_sequence_math_is_exact_per_search_and_recalculable_without_sum():
    args = make_inputs()
    sheet = populate(**args)
    result = calculate(sheet)
    assert len(result["searches"]) == 2 and not result["round_comparisons"]
    assert not any(k in result for k in ("final", "selected", "total_weight", "converged"))
    for row, search, source, query, binding, metadata in zip(result["searches"], args["collection"]["searches"],
            args["report_sources"], args["query_bindings"], args["search_bindings"], args["sequence_metadata"]):
        supplied = dict(search=search, report_source=source["report_source"], query_binding=query["query_binding"],
            search_binding=binding, target_context=None, **{k: v for k, v in metadata.items() if k != "search_key"})
        direct = sequence.calculate_blast_sequence_database_components(sequence.populate_blast_sequence_database_sheet(**supplied))
        assert row["sequence_components"] == direct
        assert row["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
        assert row["profile_components"] is None
    warmer = calculate(sheet, sequence_model={"temperature_bits": 2})
    for row in warmer["searches"]:
        assert row["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"] == pytest.approx({"F": .585786437626905, "G": .414213562373095})
    assert sheet == populate(**args)


def test_delivered_domain_math_is_deeply_equal_and_has_no_sequence_weights():
    args = make_inputs([["P1"]], program="deltablast", stages=["domain_database"],
                       query=operand(length=100, selected_interval=None))
    row = run(args)["searches"][0]
    metadata = args["profile_metadata"][0]
    direct = profile.calculate_blast_profile_components(populate_blast_profile_sheet(args["collection"]["searches"][0],
        report_source=args["report_sources"][0]["report_source"], search_binding=args["search_bindings"][0],
        query_binding=args["query_bindings"][0]["query_binding"], **{k: v for k, v in metadata.items() if k != "search_key"}))
    assert row["profile_components"] == direct
    assert direct["hsps"][0]["model_matches"][0]["specific_bits_margin"] == 2
    assert direct["models"][0]["query_coverage"]["value"] == .5
    assert direct["models"][0]["model_coverage"]["value"] == .5
    assert row["sequence_components"] is None
    assert row["native_search"]["program_context"]["reference_kind"] == "sequence"


def test_labels_do_not_assign_stages_rounds_comparisons_or_final_results():
    args = make_inputs([["A"], ["A"], ["A"]], labels=[7, 7, 11])
    args["search_bindings"] = []
    for i in range(3):
        add_pssm(args, key=f"checkpoint{i}", role=None)
    out = run(args)
    assert len(out["searches"]) == len(out["pssms"]) == 3
    assert [s["native_iteration"]["value"] for s in out["searches"]] == [7, 7, 11]
    assert all(s["stage"] is None and s["biological_round"]["value"] is None for s in out["searches"])
    assert all(s["sequence_components"] is None and s["profile_components"] is None for s in out["searches"])
    assert out["round_comparisons"] == []
    assert any(v["details"].get("original_issue", {}).get("code") == "blast_iteration_number_duplicate" for v in out["issues"])


def test_raw_counts_keep_malformed_original_ordinals_and_valid_siblings():
    args = make_inputs([["A"]], raw_searches=[dict(query_id="q", query_title="q", query_len=8,
        hits=[False, dict(len=10, description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[None, hsp(40)])])])
    row = run(args)["searches"][0]
    assert values(row) == dict(reported_hit_count=2, reported_hsp_count=None, observed_hsp_count=2,
        parsed_hit_count=1, parsed_hsp_count=1, declared_alignment_row_count=None)
    h = row["sequence_components"]["components"]["row_keys"]["hits"][0]
    assert h["row_key"]["hit_ordinal"] == 1 and h["hsps"][0]["row_key"]["hsp_ordinal"] == 1


def table_inputs(*, malformed=False, zero=False, empty=False, delimiter="\t"):
    fields = ["qseqid", "sseqid", "qlen", "slen", "qstart", "qend", "sstart", "send", "qseq", "sseq", "bitscore"]
    rows = [] if zero or empty else [delimiter.join(["q", name, "8", "10", "3", "6", "2", "5", "ACDE", "ACDE", "40"]) for name in ("A", "A", "B")]
    if malformed:
        rows.append("unassignable")
    text = "" if empty else "# PSIBLAST 2.17.0+\n# Query: q\n# Database: synthetic_db\n# " + str(0 if zero else 3) + " hits found\n" + "\n".join(rows) + "\n"
    data = collect(raw=text.encode(), format_name="tabular6" if empty else "tabular7", fields=fields, delimiter=delimiter,
                   inv=invocation())
    return from_collection(data)


@pytest.mark.parametrize("delimiter", ["\t", "@"])
def test_table_counts_use_original_grouping_rows_and_explicit_layout(delimiter):
    row = run(table_inputs(delimiter=delimiter))["searches"][0]
    assert values(row) == dict(reported_hit_count=2, reported_hsp_count=3, observed_hsp_count=3,
        parsed_hit_count=2, parsed_hsp_count=3, declared_alignment_row_count=3)
    bad = run(table_inputs(malformed=True, delimiter=delimiter))["searches"][0]
    assert values(bad) == dict(reported_hit_count=None, reported_hsp_count=4, observed_hsp_count=4,
        parsed_hit_count=2, parsed_hsp_count=3, declared_alignment_row_count=3)
    assert "blast_iteration_native_count_conflict" in codes(bad)


@pytest.mark.parametrize("returncode,complete", [(0, True), (2, True), (0, False), (None, None)])
def test_explicit_empty_search_and_failed_or_incomplete_are_distinct(returncode, complete):
    args = make_inputs([[]], completion={"native_returncode": returncode, "producer_complete": complete})
    row = run(args)["searches"][0]
    assert row["counts"]["reported_hit_count"]["value"] == row["counts"]["reported_hsp_count"]["value"] == 0
    assert (row["status"] == "no_reported_hits") is (returncode == 0 and complete is True)


def test_empty_table6_missing_array_and_zero_byte_do_not_become_no_hits():
    result = run(table_inputs(empty=True))
    assert result["searches"][0]["counts"]["reported_hit_count"]["value"] is None
    assert result["status"] != "no_reported_hits"
    args = make_inputs([[]], raw_searches=[dict(query_id="q", query_title="q", query_len=8)])
    row = run(args)["searches"][0]
    assert row["counts"]["reported_hit_count"]["value"] is None and row["status"] != "no_reported_hits"


def test_threshold_candidates_conflicts_missing_sources_and_domain_semantics():
    args = make_inputs()
    row = run(args)["searches"][0]
    assert row["thresholds"]["native_inclusion_threshold"]["value"] == .002
    assert row["thresholds"]["native_inclusion_threshold"]["origin"] == "mixed"
    args["collection"]["invocation"]["effective_options"]["inclusion_ethresh"] = .003
    row = run(args)["searches"][0]
    assert [c["value"] for c in row["threshold_candidates"] if c["kind"] != "domain_inclusion"] == [.002, .003]
    assert row["thresholds"]["native_inclusion_threshold"]["status"] == "incompatible"
    args = make_inputs([["P1"]], program="deltablast", stages=["domain_database"], query=operand(length=100, selected_interval=None))
    row = run(args)["searches"][0]
    assert row["thresholds"]["domain_inclusion_threshold"]["value"] == .05
    assert row["thresholds"]["reported_include"]["value"] == .002
    assert row["thresholds"]["native_inclusion_threshold"]["value"] is None
    args["invocation_source"] = None
    row = run(args)["searches"][0]
    assert row["thresholds"]["domain_inclusion_threshold"]["value"] is None
    assert row["threshold_candidates"][-1]["value"] == .05
    assert row["threshold_candidates"][-1]["status"] == "unavailable"
    args = make_inputs(params={})
    args["collection"]["invocation"]["effective_options"] = {"num_iterations": 0}
    row = run(args)["searches"][0]
    assert row["threshold_candidates"] == []
    assert all(c["value"] is None for c in row["thresholds"].values())


@pytest.mark.parametrize("value", [-1, "0.002", True, None])
def test_present_invalid_threshold_disables_application_without_dropping_raw(value):
    args = make_inputs(params={"include": value})
    row = run(args)["searches"][0]
    assert row["native_search"]["native"]["report"]["params"]["include"] == value
    assert row["thresholds"]["native_inclusion_threshold"]["value"] is None
    assert row["thresholds"]["reported_include"]["status"] == "incompatible"


def test_unknown_delta_stage_keeps_bits_and_native_counts_without_guessing():
    args = make_inputs([["A"]], program="deltablast", stages=[None])
    args["collection"]["invocation"]["effective_options"]["show_domain_hits"] = True
    row = run(args)["searches"][0]
    assert row["native_search"]["native"]["search"]["hits"][0]["hsps"][0]["bit_score"] == 40
    assert row["counts"]["reported_hsp_count"]["value"] == 1
    assert row["sequence_components"] is row["profile_components"] is None
    assert row["stage"] is None


def test_sequence_returned_set_differences_use_delivered_groups_and_keep_raw_hits():
    args = make_inputs([["A", "B", "B"], ["B", "C"]])
    add_pair(args)
    out = run(args)
    pair = out["round_comparisons"][0]
    assert pair["status"] == "available"
    assert [s["counts"]["reported_hit_count"]["value"] for s in out["searches"]] == [3, 2]
    assert [pair[k]["value"] for k in ("earlier_target_count", "later_target_count", "added_count", "removed_count", "retained_count")] == [2, 2, 1, 1, 1]
    for kind, name in (("added", "C"), ("removed", "A"), ("retained", "B")):
        assert pair["returned_hit_set_"+kind][0]["identity"]["digest"] == digest(name)
    assert len(pair["returned_hit_set_retained"][0]["row_keys"]) == 3
    assert all(r["profile_keys"] == [] for r in pair["earlier_targets"])
    args["sequence_metadata"][0]["sequence_identity_bindings"].pop()
    pair = run(args)["round_comparisons"][0]
    assert pair["earlier_targets"] and not pair["earlier_set_complete"]
    assert pair["returned_hit_set_added"] is None and pair["added_count"]["value"] is None
    assert pair["earlier_target_count"]["value"] is None


def test_missing_hsp_geometry_does_not_hide_a_qualified_sequence_identity():
    native = [dict(query_id="q", query_title="q", query_len=8, hits=[dict(len=10,
        description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[{"bit_score": 40}])])] * 2
    args = make_inputs([["A"], ["A"]], raw_searches=native)
    add_pair(args)
    pair = run(args)["round_comparisons"][0]
    assert pair["retained_count"]["value"] == 1


def test_profile_differences_keep_models_distinct_and_merge_source_rows():
    args = make_inputs([["P1", "P2"], ["P2", "P3"]], program="deltablast", stages=["domain_database"]*2,
                       query=operand(length=100, selected_interval=None))
    for metadata in args["profile_metadata"]:
        metadata["model_relations"] = [dict(left_profile_key="profile_1", right_profile_key="profile_3",
            relation="same_family", provenance=provenance())]
    add_pair(args, basis="profile_model_identifier")
    pair = run(args)["round_comparisons"][0]
    assert pair["status"] == "available"
    assert [pair[k+"_count"]["value"] for k in ("added", "removed", "retained")] == [1, 1, 1]
    assert pair["returned_hit_set_retained"][0]["identity"]["model_identifier"]["value"] == "cd00002"
    assert len(pair["returned_hit_set_retained"][0]["row_keys"]) == 2
    args["profile_metadata"][1]["profile_records"][0]["model_identifier"]["value"] = "unestablished_alias"
    pair = run(args)["round_comparisons"][0]
    assert pair["returned_hit_set_added"] is None


@pytest.mark.parametrize("change", ["missing_query", "interval", "digest", "length", "round", "missing_search", "self", "release", "scope"])
def test_unqualified_comparisons_preserve_each_native_search(change):
    args = make_inputs()
    add_pair(args)
    if change == "missing_query":
        args["query_bindings"].pop()
    elif change == "interval":
        args["query_bindings"][1]["query_binding"]["operand"]["selected_interval"] = [3, 10]
    elif change == "digest":
        args["query_bindings"][1]["query_binding"]["sequence_sha256"] = "b"*64
    elif change == "length":
        args["query_bindings"][1]["query_binding"]["full_length"] = 13
    elif change == "round":
        args["search_bindings"][1]["biological_round"] = 1
    elif change == "missing_search":
        args["comparison_pairs"][0]["later_search_key"]["artifact_key"] = "missing"
    elif change == "self":
        args["comparison_pairs"][0]["later_search_key"] = deepcopy(args["comparison_pairs"][0]["earlier_search_key"])
    elif change == "release":
        args["search_bindings"][1]["database_identity"]["release"] = "different"
    else:
        args["search_bindings"][1]["database_identity"]["scope"] = None
    out = run(args)
    assert len(out["searches"]) == 2
    assert all(s["native_search"] == orig for s, orig in zip(out["searches"], args["collection"]["searches"]))
    assert out["round_comparisons"][0]["added_count"]["value"] is None


@pytest.mark.parametrize("filename,rows", [("pssm_freq_ratios.asn", 26), ("pssm_zero_fratios.asn", 28)])
def test_actual_retained_upstream_pssm_is_deeply_equal_to_direct_dependency(filename, rows):
    args = make_inputs()
    saved = read_blast_pssm((SOURCES / filename).read_bytes(), format="scoremat_asn_text", artifact_key=filename,
                          source_ref="retained:upstream-306/"+filename)
    args["pssm_sheets"] = [saved]
    out = run(args)
    assert out["pssms"][0]["components"] == calculate_blast_pssm_components(saved)
    matrix = out["pssms"][0]["components"]["matrices"][0]
    assert matrix["dimensions"] == {"positions": 232, "residue_rows": rows}
    assert len(matrix["matrix_values"]["freqRatios"]) == 232
    assert all(len(row) == rows for row in matrix["matrix_values"]["freqRatios"])
    assert out["checkpoint_associations"] == []


def test_pssm_gap_map_preserves_native_columns_and_differs_from_clustal():
    args = make_inputs()
    add_pssm(args, length=3, sequence="A-C", role=None)
    result = run(args)
    matrix = result["pssms"][0]["components"]["matrices"][0]
    assert [v["master_position"] for v in matrix["master"]["column_to_residue"]] == [0, None, 2]
    msa = read_blast_msa_master(b"CLUSTAL W\n\nq A-C\ns ABC\n", format="clustal", artifact_key="msa", source_ref="synthetic:msa",
                               master_record_ordinal=0, ignore_master_for_profile=False)
    assert [v["master_position"] for v in msa["master_column_map"]] == [0, None, 1]


def test_selected_full_query_units_preserve_native_endpoints():
    query = operand(length=200, selected_interval=[50, 150])
    native = dict(query_id="q", query_title="q", query_len=100, hits=[dict(len=10,
        description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[hsp(40, query_from=51, query_to=54)])])
    args = make_inputs([["A"]], query=query, raw_searches=[native])
    row = run(args)["searches"][0]
    axis = row["sequence_components"]["components"]["coordinate_context"]["query"]
    assert axis["full_length"] == 200 and axis["reported_length"] == 100 and axis["selected_interval"] == [50, 150]
    assert row["native_search"]["native"]["search"]["hits"][0]["hsps"][0]["query_from"] == 51


def test_checkpoint_after_search_and_input_are_separate_relations_with_duplicates_once():
    args = make_inputs()
    pkey = add_pssm(args)
    args["search_bindings"][1]["input_pssm_key"] = pkey
    args["checkpoint_bindings"].append(dict(pssm_key=pkey, role="input", search_key=deepcopy(args["search_bindings"][1]["search_key"]),
        biological_round=2, provenance=provenance("/actual_consumption")))
    args["checkpoint_bindings"].append(deepcopy(args["checkpoint_bindings"][0]))
    out = run(args)
    assert len(out["pssms"]) == 1 and len(out["checkpoint_associations"]) == 2
    assert out["checkpoint_associations"][0]["binding_indices"] == [0, 2]
    assert all(r["status"] == "available" for r in out["checkpoint_associations"])
    args["checkpoint_bindings"][1]["pssm_key"] = "wrong"
    assert run(args)["checkpoint_associations"][1]["status"] == "incompatible"


@pytest.mark.parametrize("change", ["round", "master_length", "duplicate_key", "conflicting_source", "output_scope"])
def test_checkpoint_conflicts_preserve_matrices_and_localize_relations(change):
    args = make_inputs(query_kind="pssm" if change == "master_length" else "sequence")
    pkey = add_pssm(args, length=11 if change == "master_length" else 12)
    if change == "master_length":
        args["query_bindings"][0]["query_binding"]["pssm_key"] = pkey
        args["search_bindings"][0]["input_pssm_key"] = pkey
    if change == "round":
        args["checkpoint_bindings"][0]["biological_round"] = 7
    elif change == "duplicate_key":
        args["pssm_sheets"].append(deepcopy(args["pssm_sheets"][0]))
    elif change == "conflicting_source":
        other = deepcopy(args["checkpoint_bindings"][0])
        other["provenance"]["source_ref"] = "different:assertion"
        args["checkpoint_bindings"].append(other)
    elif change == "output_scope":
        args["checkpoint_bindings"][0]["role"] = "output"
    out = run(args)
    assert out["pssms"][0]["components"]["matrices"][0]["matrix_values"]["scores"]
    assert out["checkpoint_associations"][0]["status"] != "available"


def test_supplied_membership_counts_complete_incomplete_empty_and_missing_are_distinct():
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey)
    row = run(args)["inclusion_observations"][0]
    assert [row[n]["value"] for n in ("member_record_count", "observed_unique_member_count", "duplicate_member_count", "included_sequence_count")] == [3, 2, 1, 2]
    assert row["included_sequence_count"]["origin"] == "supplied_source_record"
    args["inclusion_records"][0]["complete"] = False
    row = run(args)["inclusion_observations"][0]
    assert row["observed_unique_member_count"]["value"] == 2 and row["included_sequence_count"]["value"] is None
    args["inclusion_records"] = []
    assert run(args)["inclusion_observations"] == []
    add_members(args, pkey, names=())
    args["inclusion_records"][0]["evidence"]["original_record"] = []
    assert run(args)["inclusion_observations"][0]["included_sequence_count"]["value"] == 0


@pytest.mark.parametrize("change", ["key", "round", "association_missing", "set", "convention", "wrong_role"])
def test_supplied_membership_qualifications_do_not_erase_observed_rows_or_matrices(change):
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey)
    if change == "key":
        args["inclusion_records"][0]["pssm_key"] = "missing"
    elif change == "round":
        args["checkpoint_bindings"][0]["biological_round"] = 100
    elif change == "association_missing":
        args["checkpoint_bindings"] = []
    elif change in ("set", "convention"):
        add_members(args, pkey, ("C",) if change == "set" else ("A", "B"), record_key="second")
        if change == "convention":
            args["inclusion_records"][1]["query_membership"] = "included"
    else:
        args["checkpoint_bindings"][0]["role"] = "input"
    out = run(args)
    row = out["inclusion_observations"][0]
    assert row["included_sequence_count"]["value"] is None
    assert row["observed_unique_member_count"]["value"] == 2 and row["member_rows"] == args["inclusion_records"][0]["members"]
    assert out["pssms"][0]["components"]["matrices"][0]["matrix_values"]["scores"]


def test_equal_membership_observations_stay_separate_without_cross_record_sum():
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey)
    add_members(args, pkey, ("B", "A"), record_key="second")
    out = run(args)
    assert [r["included_sequence_count"]["value"] for r in out["inclusion_observations"]] == [2, 2]
    assert all("blast_iteration_membership_duplicate" in codes(r) for r in out["inclusion_observations"])


def test_convergence_explicit_scope_duplicates_conflicts_and_query_only():
    args = make_inputs()
    add_pair(args)
    out = run(args)
    assert all(r["native_converged"]["value"] is None for r in out["searches"])
    add_convergence(args)
    add_convergence(args, key="again")
    out = run(args)
    assert out["searches"][0]["native_converged"]["value"] is True
    assert out["searches"][1]["native_converged"]["value"] is None
    add_convergence(args, False, key="conflict")
    out = run(args)
    assert out["searches"][0]["native_converged"]["status"] == "incompatible"
    assert all(r["native_converged"]["value"] is None for r in out["convergence_observations"])
    args["convergence_records"] = []
    add_convergence(args, query_only=True)
    out = run(args)
    assert out["convergence_observations"][0]["native_converged"]["value"] is True
    assert all(r["native_converged"]["value"] is None for r in out["searches"])


def test_different_search_scopes_can_have_different_native_convergence_states():
    args = make_inputs()
    add_convergence(args, False)
    add_convergence(args, True, key="later", search_index=1)
    assert [r["native_converged"]["value"] for r in run(args)["searches"]] == [False, True]


@pytest.mark.parametrize("role", ["report_sources", "query_bindings", "sequence_metadata", "search_bindings"])
def test_duplicate_role_disables_only_its_search_and_returns_all_indices(role):
    args = make_inputs()
    args[role].append(deepcopy(args[role][0]))
    out = run(args)
    assert out["searches"][0]["association_indices"][role] == [0, 2]
    assert out["searches"][0]["sequence_components"] is None
    assert out["searches"][1]["sequence_components"] is not None
    assert "blast_iteration_duplicate_search_association" in codes(out)


def test_full_archive_and_iteration_keys_prevent_inner_cross_links():
    args = make_inputs(archive=True)
    assert len(args["collection"]["searches"]) == 4
    args["sequence_metadata"][2]["description_bindings"] = deepcopy(args["sequence_metadata"][0]["description_bindings"])
    args["sequence_metadata"][2]["sequence_identity_bindings"] = deepcopy(args["sequence_metadata"][0]["sequence_identity_bindings"])
    out = run(args)
    assert out["searches"][0]["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
    assert out["searches"][2]["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"] is None
    assert len({_key(r["search_key"]) for r in out["searches"]}) == 4


def _key(value):
    return json.dumps(value, sort_keys=True)


@pytest.mark.parametrize("change", ["member", "container", "pointer", "row_map", "layout"])
def test_source_conflicts_keep_raw_counts_and_original_inputs(change):
    args = table_inputs() if change == "layout" else make_inputs(archive=change in ("member", "container"))
    if change in ("member", "container"):
        args["report_sources"][0]["report_source"]["member_sha256"] = "0"*64 if change == "member" else args["collection"]["artifacts"][0]["sha256"]
    elif change == "pointer":
        args["collection"]["searches"][0]["native"]["search"] = deepcopy(args["collection"]["searches"][1]["native"]["search"])
        args["collection"]["searches"][0]["native"]["search"]["query_len"] = 99
    elif change == "row_map":
        args["collection"]["searches"][0]["row_map"][0]["hsp_ordinals"] = [9]
    else:
        args["collection"]["searches"][0]["normalized"]["native"].pop("table_layout")
    row = run(args)["searches"][0]
    assert row["source_status"] != "available" and row["sequence_components"] is None
    assert row["native_search"] == args["collection"]["searches"][0]
    assert row["counts"]["reported_hsp_count"]["value"] is not None
    if change in ("pointer", "row_map"):
        assert row["counts"]["parsed_hit_count"]["status"] == "incompatible"


def test_dependency_contract_rejection_is_local_and_preserves_exact_error_code():
    args = make_inputs()
    args["sequence_metadata"][0]["description_bindings"][0]["binding"]["extra"] = 3
    out = run(args)
    assert out["searches"][0]["sequence_components"] is None and out["searches"][1]["sequence_components"] is not None
    issue = next(v for v in out["issues"] if v["code"] == "blast_iteration_dependency_contract_rejected")
    assert issue["details"]["metadata_indices"] == [0]
    assert issue["details"]["error_code"] == "blast_sequence_database_inner_binding_fields_invalid"


def test_actual_source_helper_is_reused_without_scoring_unknown_stage(monkeypatch):
    args = make_inputs(stages=[None, None])
    calls = []
    original = profile._source_rows
    def checked(sheet, issues):
        calls.append(deepcopy(sheet))
        assert set(sheet) == {"search", "report_source"}
        return original(sheet, issues)
    def forbidden(*args, **kwargs):
        raise AssertionError("scoring/admission is forbidden for an unknown stage")
    monkeypatch.setattr(profile, "_source_rows", checked)
    monkeypatch.setattr(profile, "calculate_blast_profile_components", forbidden)
    monkeypatch.setattr(sequence, "calculate_blast_sequence_database_components", forbidden)
    monkeypatch.setattr(sequence, "_admit", forbidden)
    out = run(args)
    assert len(calls) == 2
    assert all(s["counts"]["parsed_hit_count"]["value"] == 2 for s in out["searches"])


def test_saved_sheet_offline_recalculation_changes_only_explicit_sequence_model(monkeypatch):
    from gene_annotation_episode.state import Store
    args = make_inputs([["A", "B", "B"], ["B", "C"]])
    add_pair(args)
    add_pssm(args)
    sheet = json.loads(json.dumps(populate(**args)))
    before = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("I/O, acquisition, subprocess or Store/model access")
    for target, name in ((builtins, "open"), (Path, "open"), (socket, "socket"), (socket, "create_connection"),
                         (subprocess, "Popen"), (subprocess, "run")):
        monkeypatch.setattr(target, name, forbidden)
    monkeypatch.setattr(Store, "__init__", forbidden)
    a, b = calculate(sheet), calculate(sheet, sequence_model={"temperature_bits": 2})
    assert sheet == before
    assert a["round_comparisons"] == b["round_comparisons"] and a["pssms"] == b["pssms"]
    for left, right in zip(a["searches"], b["searches"]):
        assert left["counts"] == right["counts"] and left["native_search"] == right["native_search"]
        assert left["sequence_components"]["components"]["coordinate_context"] == right["sequence_components"]["components"]["coordinate_context"]


@pytest.mark.parametrize("model", [{"temperature_bits": 0}, {"temperature_bits": True}, {"temperature_bits": float("nan")},
                                 {"function_priors": {}}, {"function_priors": {"F": -1}}, {"extra": 1}])
def test_model_parameters_are_validated_even_without_an_admissible_search(model):
    args = make_inputs(stages=[None, None])
    with pytest.raises(ValueError, match="blast_iteration_model_parameters_invalid"):
        calculate(populate(**args), sequence_model=model)


def test_tampered_projection_label_is_not_available_as_a_native_iteration():
    args = make_inputs(labels=[7, 11])
    args["collection"]["searches"][0]["iteration"] = 123
    row = run(args)["searches"][0]
    assert row["native_iteration"]["value"] is None and row["native_iteration"]["status"] == "incompatible"
    assert row["native_search"]["normalized"]["native"]["document"]["BlastOutput2"][0]["report"]["results"]["iterations"][0]["iter_num"] == 7
    assert row["counts"]["reported_hit_count"]["value"] == 2


def test_checkpoint_construction_without_exact_axis_relation_does_not_compare_lengths():
    args = make_inputs(query=operand(length=200, selected_interval=[50, 150]))
    add_pssm(args, length=100)
    out = run(args)
    assert out["checkpoint_associations"][0]["status"] == "available"
    assert out["pssms"][0]["components"]["matrices"][0]["dimensions"]["positions"] == 100
    assert "blast_iteration_master_axis_conflict" not in codes(out)


def test_supplied_biological_round_is_independent_of_missing_stage():
    args = make_inputs(stages=[None, None], labels=[7, 7])
    out = run(args)
    assert [s["biological_round"]["value"] for s in out["searches"]] == [1, 2]
    assert all(s["stage"] is None for s in out["searches"])


def test_collection_completion_cannot_be_replaced_with_tampered_per_search_success():
    args = make_inputs([[]], completion={"native_returncode": 2, "producer_complete": False})
    args["collection"]["searches"][0]["reporting"].update(native_returncode=0, producer_complete=True)
    row = run(args)["searches"][0]
    assert row["source_status"] == "incompatible" and row["status"] != "no_reported_hits"


def test_empty_native_data_still_needs_a_source_in_the_supplied_record_contract():
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey, ())
    args["inclusion_records"][0]["evidence"]["original_record"] = []
    assert run(args)["inclusion_observations"][0]["included_sequence_count"]["value"] == 0
    args["inclusion_records"][0]["evidence"]["source"] = None
    with pytest.raises(ValueError, match="blast_iteration_input_fields_invalid"):
        populate(**args)


def test_successful_zero_with_missing_thresholds_is_not_a_failed_output():
    args = make_inputs([[]], params={})
    args["collection"]["invocation"]["effective_options"].pop("inclusion_ethresh")
    out = run(args)
    assert out["searches"][0]["status"] == "no_reported_hits"
    assert out["searches"][0]["thresholds"]["native_inclusion_threshold"]["value"] is None


def test_absent_source_wrapper_does_not_fabricate_a_ref_or_discard_validated_native_counts():
    args = make_inputs()
    args["report_sources"] = []
    row = run(args)["searches"][0]
    assert row["report_source"] is None and row["source_status"] == "unavailable"
    assert row["counts"]["parsed_hit_count"]["value"] == 2
    assert row["sequence_components"] is None


def test_orphan_wrappers_remain_local_issues_without_making_a_complete_result():
    args = make_inputs()
    orphan = deepcopy(args["query_bindings"][0])
    orphan["search_key"]["artifact_key"] = "absent"
    args["query_bindings"].append(orphan)
    result = run(args)
    assert result["status"] == "partial" and "blast_iteration_orphan_search_key" in codes(result)
    assert all(s["sequence_components"] is not None for s in result["searches"])


def test_checkpoint_relation_does_not_require_a_separate_stage_assertion():
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey)
    args["search_bindings"] = []
    out = run(args)
    assert out["searches"][0]["stage"] is None
    assert out["checkpoint_associations"][0]["status"] == "available"
    assert out["inclusion_observations"][0]["included_sequence_count"]["value"] == 2


def test_exact_search_scoped_convergence_does_not_invent_a_biological_operand():
    collection = collect(inv=invocation(operands=[]))
    args = from_collection(collection)
    args["convergence_records"] = [dict(record_key="source-only", search_key=deepcopy(collection["searches"][0]["search_key"]),
        query_operand=None, native_converged=False, evidence=evidence([]))]
    out = run(args)
    assert out["searches"][0]["query_binding"] is None
    assert out["searches"][0]["native_converged"]["value"] is False


def test_real_empty_returned_sets_have_measured_zero_differences():
    args = make_inputs([[], []])
    add_pair(args)
    pair = run(args)["round_comparisons"][0]
    assert pair["status"] == "available"
    assert pair["earlier_targets"] == pair["later_targets"] == pair["returned_hit_set_added"] == []
    assert [pair[n]["value"] for n in ("added_count", "removed_count", "retained_count", "earlier_target_count", "later_target_count")] == [0]*5


def test_profile_comparison_retains_original_order_even_if_metadata_records_are_reversed():
    args = make_inputs([["P1", "P2"], ["P2", "P3"]], program="deltablast", stages=["domain_database"]*2,
                       query=operand(length=100, selected_interval=None))
    for m in args["profile_metadata"]:
        m["profile_records"].reverse()
    add_pair(args, basis="profile_model_identifier")
    pair = run(args)["round_comparisons"][0]
    assert [r["identity"]["model_identifier"]["value"] for r in pair["earlier_targets"]] == ["cd00001", "cd00002"]


def test_pssm_calculator_called_once_per_artifact_even_with_repeated_associations(monkeypatch):
    from gene_annotation_episode import blast_pssm_calculators as module
    args = make_inputs()
    add_pssm(args)
    args["checkpoint_bindings"] += [deepcopy(args["checkpoint_bindings"][0])]*3
    calls, original = [], module.calculate_blast_pssm_components
    def observed(sheet):
        calls.append(sheet["artifact_key"])
        return original(sheet)
    monkeypatch.setattr(module, "calculate_blast_pssm_components", observed)
    run(args)
    assert calls == ["checkpoint"]


def test_phi_alias_is_retained_but_not_admitted_by_the_iteration_composer():
    raw = dict(query_id="q", query_title="q", query_len=8, hits=[dict(len=10,
        description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[hsp(40)])])
    doc = {"BlastOutput2": [{"report": dict(program="phiblastp", version="PHIBLASTP 2.17.0+", search_target={"db": "synthetic_db"},
        params={"pattern": "A-X-C"}, results={"search": raw})}]}
    args = from_collection(collect(doc))
    row = run(args)["searches"][0]
    assert row["native_search"]["program_context"]["reported_program"] == "phiblastp"
    assert row["sequence_components"] is None and "blast_iteration_phase_semantics_unavailable" in codes(row)


def test_closed_output_shapes_and_cell_pointers_are_checkable_against_saved_sheet():
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey)
    add_convergence(args)
    add_pair(args)
    sheet = populate(**args)
    out = calculate(sheet)
    assert set(out) == {"schema", "status", "searches", "pssms", "checkpoint_associations", "inclusion_observations",
                        "convergence_observations", "round_comparisons", "issues", "definitions"}
    assert set(out["definitions"]) == {"version", "coordinates", "count_populations", "threshold_sources", "membership_population",
        "comparison_population", "convergence_meaning", "child_component_definitions", "missingness", "uncertainty",
        "no_cross_round_combination", "unused_inputs"}
    assert set(out["searches"][0]) == {"search_key", "status", "source_status", "native_search", "report_source", "query_binding", "search_binding",
        "association_indices", "native_iteration", "stage", "biological_round", "reporting", "counts", "thresholds", "threshold_candidates",
        "sequence_components", "profile_components", "component_availability", "checkpoint_association_indices", "native_converged",
        "convergence_observation_indices", "issues"}
    def check(value):
        if type(value) is dict:
            if "input_pointers" in value:
                assert set(value) == {"value", "status", "unavailable_reason", "unit", "origin", "input_pointers"}
                assert (value["value"] is not None) == (value["status"] == "available")
                assert (value["unavailable_reason"] is None) == (value["status"] == "available")
                for pointer in value["input_pointers"]:
                    sequence._at(sheet, pointer)
            for child in value.values():
                check(child)
        elif type(value) is list:
            for child in value:
                check(child)
    check(out)
    assert json.loads(json.dumps(out, allow_nan=False)) == out
