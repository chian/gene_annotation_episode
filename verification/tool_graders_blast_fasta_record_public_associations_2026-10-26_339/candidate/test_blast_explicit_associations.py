"""Synthetic explicit-link contracts; no BLAST execution or service access."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_database_grader import (
    build_database_sheet, calculate_database_probabilities,
)


EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_explicit_associations_2026-10-24"


def synthetic_inputs():
    """Noncompact original indices and real-shaped source IDs are deliberate."""
    report = {"artifact_ref": "synthetic-native-json", "report_index": 7,
              "pointer": "/BlastOutput2/7/report"}
    hits, metadata, bindings = [], [], []
    for index, (hit_index, ordinal, score) in enumerate(((4, 2, 20), (9, 3, 18))):
        hit_locator = {**report, "hit_index": hit_index,
                       "pointer": report["pointer"] + f"/results/search/hits/{hit_index}"}
        description = {"id": f"gnl|BL_ORD_ID|{hit_index}", "accession": str(hit_index),
            "title": "Synthetic native description", "taxid": 562,
            "source_locator": {**hit_locator, "description_index": ordinal,
                "pointer": hit_locator["pointer"] + f"/description/{ordinal}"}}
        hits.append({"hit_index": hit_index, "length": 10, "source_locator": hit_locator,
            "descriptions": [description], "unpaired_metadata": {},
            "hsps": [{"bit_score": score, "score": score * 2, "evalue": 0.0,
                "query_from": 1, "query_to": 5, "hit_from": 1, "hit_to": 5,
                "align_len": 5, "identity": 5, "gaps": 0, "qseq": "ACDEF", "hseq": "ACDEF",
                "source_locator": {**hit_locator, "hsp_index": 6,
                    "pointer": hit_locator["pointer"] + "/hsps/6"}}]})
        metadata.append({"accession": f"fig|562.{index + 1}.peg.7", "identifier_namespace": "patric_id",
            "source": "synthetic-metadata", "native_pointer": f"/records/{index}", "taxid": 562,
            "functions": [{"function": "F" if index == 0 else "G", "source": "synthetic-metadata"}],
            "lineage": [{"taxid": 562, "rank": "species"}], "assembly": {}, "origin": {},
            "sequence_group": "unverified-shared-label", "study_groups": []})
        bindings.append({"report_index": 7, "hit_index": hit_index, "description_index": ordinal,
            "metadata_index": index, "native_description": {
                key: description.get(key) for key in ("id", "accession", "title", "taxid")},
            "metadata_identifier": {"namespace": "patric_id", "value": metadata[-1]["accession"]},
            "metadata_source_ref": "synthetic-metadata", "metadata_pointer": f"/records/{index}",
            "linkage_source_ref": "synthetic-record-links", "linkage_pointer": f"/links/{index}"})
    return {"result": {"schema": "blast_normalized_result_v1", "mode": "database", "resource": "api",
        "format": "json2", "source_locator": report,
        "query": {"id": "synthetic-query", "title": None, "length": 10},
        "search": {"program": "blastp", "database": "synthetic-db", "request": {},
                   "hit_array_present": True, "reported_hit_count": 10},
        "hits": hits, "native": {"synthetic": True}, "issues": []},
        "reference_metadata": metadata, "description_bindings": bindings,
        "sequence_identity_bindings": []}


def sequence_binding(hit_index, *, sequence="ACDEFGHIKL", molecule="aa", length=None):
    digest = hashlib.sha256(sequence.encode("ascii")).hexdigest()
    return {"report_index": 7, "hit_index": hit_index, "kind": "full_sequence_digest",
        "sequence_group": "sha256:" + digest, "algorithm": "sha256", "digest": digest,
        "molecule": molecule, "sequence_length": len(sequence) if length is None else length,
        "source_ref": "synthetic-full-sequences", "pointer": f"/records/{hit_index}",
        "linkage_source_ref": "synthetic-sequence-links", "linkage_pointer": f"/links/{hit_index}"}


def codes(sheet):
    return {row["code"] for row in sheet["issues"]}


@pytest.mark.parametrize("case", json.loads((EVIDENCE / "legacy_prechange.json").read_text())["cases"],
                         ids=lambda case: case["name"])
def test_exact_prechange_legacy_sheets_and_calculations(case):
    for extra in ({}, {"description_bindings": None, "sequence_identity_bindings": None}):
        sheet = build_database_sheet(**case["arguments"], **extra)
        assert sheet == case["sheet"]
        assert calculate_database_probabilities(sheet) == case["calculations"][0]
        assert calculate_database_probabilities(sheet, model={"temperature_bits": 2}) == case["calculations"][1]


def test_explicit_original_ordinals_join_actual_ids_preserve_provenance_and_numbers():
    arguments = synthetic_inputs()
    before = deepcopy(arguments)
    sheet = build_database_sheet(**arguments)
    assert arguments == before
    assert sheet["normalized_result"] == arguments["result"]
    assert sheet["reference_metadata"] == arguments["reference_metadata"]
    assert sheet["description_bindings"] == arguments["description_bindings"]
    assert sheet["sequence_identity_bindings"] == []
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    for index, hit in enumerate(sheet["hits"]):
        association, = hit["associations"]
        assert association["description_index"] == (2, 3)[index]
        assert association["native_identifier"] == str((4, 9)[index])
        assert association["accession"] == arguments["reference_metadata"][index]["accession"]
        assert association["metadata_identifier"] == arguments["description_bindings"][index]["metadata_identifier"]
        assert association["description_binding"] == arguments["description_bindings"][index]
        assert association["source_locator"] == arguments["result"]["hits"][index]["descriptions"][0]["source_locator"]
        assert hit["measurements"]["query_paired_coverage"] == .5
        assert hit["measurements"]["reference_paired_coverage"] == .5
        assert hit["measurements"]["identical_unique_pair_count"] == 5
        assert hit["measurements"]["minimum_evalue"] == 0
        assert association["reported_sequence_group"] == "unverified-shared-label"
    scored = calculate_database_probabilities(sheet, model={"temperature_bits": 2})
    assert scored["function_masses"] == {"F": 1, "G": .5}
    assert scored["unadjusted_probabilities"] == {"F": 2 / 3, "G": 1 / 3}
    assert scored["representation_adjusted_probabilities"] is None
    assert sheet["dependence"]["unknown_cross_hit_sequence_identity"] is True
    assert "Unresolved returned native-hit groups" in scored["assumptions"][-1]
    assert scored["calibrated_annotation_probability"] is False


def test_empty_bindings_never_fall_back_to_accession_or_metadata_sequence_groups():
    arguments = synthetic_inputs()
    for hit, row in zip(arguments["result"]["hits"], arguments["reference_metadata"]):
        hit["descriptions"][0]["accession"] = "identical-uploaded-label"
        row["accession"] = "identical-uploaded-label"
        row["sequence_group"] = "sha256:" + "a" * 64
    arguments["description_bindings"] = []
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["matched_metadata_row_count"] == 0
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0, 1]
    assert len(sheet["sequence_groups"]) == 2
    assert sheet["functions"] == []
    assert sheet["dependence"]["unknown_cross_hit_sequence_identity"] is True
    assert calculate_database_probabilities(sheet)["unannotated_reference_kernel_fraction"] == 1


@pytest.mark.parametrize("field", ["description_bindings", "sequence_identity_bindings"])
def test_mixed_implicit_explicit_binding_contract_is_rejected(field):
    arguments = synthetic_inputs()
    arguments[field] = None
    with pytest.raises(ValueError, match="^blast_explicit_binding_pair_required$"):
        build_database_sheet(**arguments)


@pytest.mark.parametrize("field,value", [("description_bindings", {}), ("sequence_identity_bindings", ())])
def test_nonlist_binding_contract_is_rejected(field, value):
    arguments = synthetic_inputs()
    arguments[field] = value
    with pytest.raises(ValueError, match="^blast_explicit_binding_lists_required$"):
        build_database_sheet(**arguments)


@pytest.mark.parametrize("locator", [None, {}, {"artifact_ref": "a", "report_index": True, "pointer": ""},
    {"artifact_ref": "a", "report_index": 0, "pointer": "not-a-pointer"},
    {"artifact_ref": "a", "report_index": 0, "pointer": "/invalid~2escape"}])
def test_invalid_report_locator_fails_specifically(locator):
    arguments = synthetic_inputs()
    arguments["result"]["source_locator"] = locator
    with pytest.raises(ValueError, match="^blast_explicit_report_source_locator_required$"):
        build_database_sheet(**arguments)


@pytest.mark.parametrize("changes,code", [
    ({"unexpected": 1}, "blast_description_binding_fields_invalid"),
    ({"report_index": True}, "blast_description_binding_index_invalid"),
    ({"report_index": 0}, "blast_description_binding_report_mismatch"),
    ({"hit_index": 0}, "blast_description_binding_hit_unavailable"),
    ({"description_index": 0}, "blast_description_binding_description_unavailable"),
    ({"metadata_index": 99}, "blast_description_binding_metadata_unavailable"),
    ({"metadata_source_ref": "different-source"}, "blast_description_binding_metadata_provenance_mismatch"),
    ({"metadata_pointer": "/records/1"}, "blast_description_binding_metadata_provenance_mismatch"),
    ({"linkage_pointer": "made-up-line"}, "blast_description_binding_provenance_invalid"),
    ({"linkage_source_ref": ""}, "blast_description_binding_provenance_invalid"),
    ({"metadata_identifier": {"namespace": "other", "value": "fig|562.1.peg.7"}},
      "blast_description_binding_metadata_identity_mismatch"),
    ({"metadata_identifier": {"namespace": "patric_id", "value": "4"}},
      "blast_description_binding_metadata_identity_mismatch"),
    ({"metadata_identifier": {"namespace": "patric_id", "value": "x", "extra": True}},
      "blast_description_binding_metadata_identifier_invalid"),
])
def test_invalid_description_link_is_local_preserves_other_function_and_geometry(changes, code):
    arguments = synthetic_inputs()
    arguments["description_bindings"][0].update(changes)
    sheet = build_database_sheet(**arguments)
    assert code in codes(sheet)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0]
    assert [row["function"] for row in sheet["functions"]] == ["G"]
    assert sheet["hits"][0]["measurements"]["maximum_bit_score"] == 20
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == .5
    assert sheet["description_bindings"] == arguments["description_bindings"]


@pytest.mark.parametrize("field,value", [("id", "changed"), ("accession", "4.1"),
    ("title", "changed"), ("taxid", 620)])
def test_literal_native_description_is_checked(field, value):
    arguments = synthetic_inputs()
    arguments["description_bindings"][0]["native_description"][field] = value
    sheet = build_database_sheet(**arguments)
    assert "blast_description_binding_native_identity_mismatch" in codes(sheet)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0]


@pytest.mark.parametrize("native", [{"id": 7}, {"taxid": True}, {"title": []}])
def test_native_scalar_identity_types_cannot_authorize_binding(native):
    arguments = synthetic_inputs()
    arguments["result"]["hits"][0]["descriptions"][0].update(native)
    sheet = build_database_sheet(**arguments)
    assert "blast_description_binding_native_identity_mismatch" in codes(sheet)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0]


def test_absent_native_fields_use_null_snapshot_and_invalid_snapshot_fails_locally():
    arguments = synthetic_inputs()
    del arguments["result"]["hits"][0]["descriptions"][0]["id"]
    arguments["description_bindings"][0]["native_description"]["id"] = None
    assert build_database_sheet(**arguments)["coverage"]["matched_metadata_row_count"] == 2
    arguments["description_bindings"][0]["native_description"]["taxid"] = True
    sheet = build_database_sheet(**arguments)
    assert "blast_description_binding_native_identity_invalid" in codes(sheet)
    assert sheet["coverage"]["matched_metadata_row_count"] == 1


@pytest.mark.parametrize("taxid,code", [(620, "metadata_taxon_conflicts_with_native"),
                                      (True, "metadata_taxid_invalid")])
def test_taxon_conflicts_do_not_replace_actual_native_taxon(taxid, code):
    arguments = synthetic_inputs()
    arguments["reference_metadata"][0]["taxid"] = taxid
    sheet = build_database_sheet(**arguments)
    assert code in codes(sheet)
    association, = sheet["hits"][0]["associations"]
    assert association["taxid"] == 562 and association["functions"] == []
    assert sheet["reference_metadata"][0]["taxid"] == taxid


@pytest.mark.parametrize("kind,field,value", [("hit", "report_index", 0),
    ("hit", "hit_index", 0), ("description", "artifact_ref", "other"),
    ("description", "hit_index", 0), ("description", "description_index", True)])
def test_wrong_original_locators_cannot_attach_but_alignments_survive(kind, field, value):
    arguments = synthetic_inputs()
    hit = arguments["result"]["hits"][0]
    row = hit if kind == "hit" else hit["descriptions"][0]
    row["source_locator"][field] = value
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0]
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == .5


def test_ambiguous_original_description_ordinal_is_not_first_or_last_row_wins():
    arguments = synthetic_inputs()
    descriptions = arguments["result"]["hits"][0]["descriptions"]
    descriptions.append(deepcopy(descriptions[0]))
    descriptions[-1]["title"] = "Conflicting retained description"
    sheet = build_database_sheet(**arguments)
    assert "blast_explicit_description_locator_ambiguous" in codes(sheet)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0]
    assert len(sheet["normalized_result"]["hits"][0]["descriptions"]) == 2


def test_unbound_metadata_overwrite_and_matching_ordinals_do_not_gain_associations():
    arguments = synthetic_inputs()
    overwritten = deepcopy(arguments["reference_metadata"][0])
    overwritten.update(accession="4", native_pointer="/overwritten/4", functions=[{"function": "WRONG"}])
    arguments["reference_metadata"].append(overwritten)
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [2]
    assert {row["function"] for row in sheet["functions"]} == {"F", "G"}
    assert sheet["reference_metadata"][2] == overwritten


@pytest.mark.parametrize("changed", [{"accession": "different-original-record"}, {"taxid": 620}])
def test_contradictory_identity_at_one_metadata_source_pointer_is_unavailable(changed):
    arguments = synthetic_inputs()
    conflicting = deepcopy(arguments["reference_metadata"][0])
    conflicting.update(changed)
    arguments["reference_metadata"].append(conflicting)
    sheet = build_database_sheet(**arguments)
    assert "blast_description_binding_metadata_record_conflict" in codes(sheet)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0, 2]
    assert [row["function"] for row in sheet["functions"]] == ["G"]
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == .5


def test_duplicate_bindings_add_no_association_or_kernel_mass():
    arguments = synthetic_inputs()
    arguments["sequence_identity_bindings"] = [sequence_binding(4), sequence_binding(9, sequence="ACDEFPQRST")]
    base = build_database_sheet(**arguments)
    arguments["description_bindings"] *= 3
    arguments["sequence_identity_bindings"] *= 4
    repeated = build_database_sheet(**arguments)
    assert repeated["hits"] == base["hits"]
    assert repeated["sequence_groups"] == base["sequence_groups"]
    assert calculate_database_probabilities(repeated) == calculate_database_probabilities(base)
    assert len(repeated["description_bindings"]) == 6
    assert len(repeated["sequence_identity_bindings"]) == 8


def test_only_compatible_complete_sequences_merge_hits_across_ids_and_taxa():
    arguments = synthetic_inputs()
    arguments["result"]["hits"][1]["descriptions"][0]["taxid"] = 620
    arguments["description_bindings"][1]["native_description"]["taxid"] = 620
    arguments["reference_metadata"][1]["taxid"] = 620
    arguments["sequence_identity_bindings"] = [sequence_binding(4), sequence_binding(9)]
    sheet = build_database_sheet(**arguments)
    group, = sheet["sequence_groups"]
    assert group["hit_indices"] == [4, 9] and group["maximum_bit_score"] == 20
    assert group["taxids"] == [562, 620]
    assert group["functions"] == ["F", "G"]
    assert sheet["dependence"]["duplicate_native_hit_count"] == 1
    assert sheet["dependence"]["unknown_cross_hit_sequence_identity"] is False
    scored = calculate_database_probabilities(sheet)
    assert scored["function_masses"] == {"F": .5, "G": .5}
    assert scored["unadjusted_probabilities"] == {"F": .5, "G": .5}


@pytest.mark.parametrize("changes,code", [
    ({"extra": 1}, "blast_sequence_binding_fields_invalid"),
    ({"kind": "accession"}, "blast_sequence_binding_digest_invalid"),
    ({"algorithm": "md5"}, "blast_sequence_binding_digest_invalid"),
    ({"digest": "A" * 64}, "blast_sequence_binding_digest_invalid"),
    ({"sequence_group": "sha256:" + "0" * 64}, "blast_sequence_binding_digest_invalid"),
    ({"molecule": "protein"}, "blast_sequence_binding_operand_invalid"),
    ({"sequence_length": True}, "blast_sequence_binding_operand_invalid"),
    ({"sequence_length": 0}, "blast_sequence_binding_operand_invalid"),
    ({"molecule": "nt"}, "blast_sequence_binding_reference_molecule_mismatch"),
    ({"sequence_length": 11}, "blast_sequence_binding_reference_length_mismatch"),
    ({"source_ref": ""}, "blast_sequence_binding_provenance_invalid"),
    ({"pointer": "/invalid~3escape"}, "blast_sequence_binding_provenance_invalid"),
    ({"report_index": 0}, "blast_sequence_binding_report_mismatch"),
    ({"hit_index": 0}, "blast_sequence_binding_hit_unavailable"),
])
def test_invalid_sequence_identity_never_merges_or_loses_hits(changes, code):
    arguments = synthetic_inputs()
    arguments["sequence_identity_bindings"] = [sequence_binding(4), sequence_binding(9)]
    arguments["sequence_identity_bindings"][0].update(changes)
    sheet = build_database_sheet(**arguments)
    assert code in codes(sheet)
    assert len(sheet["sequence_groups"]) == 2
    assert sheet["dependence"]["unknown_cross_hit_sequence_identity"] is True
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == .5


def test_conflicting_full_sequence_digests_for_one_hit_do_not_choose_a_record():
    arguments = synthetic_inputs()
    arguments["sequence_identity_bindings"] = [sequence_binding(4), sequence_binding(9),
                                               sequence_binding(4, sequence="ACDEFPQRST")]
    arguments["sequence_identity_bindings"][-1]["pointer"] = "/records/independent-conflicting-sequence"
    sheet = build_database_sheet(**arguments)
    assert "blast_sequence_identity_conflict" in codes(sheet)
    assert len(sheet["sequence_groups"]) == 2
    assert sheet["sequence_groups"][0]["identity_basis"] == []
    assert len(sheet["hits"][0]["sequence_identity_bindings"]) == 2


def test_same_digest_with_conflicting_record_lengths_cannot_join_unknown_length_hits():
    arguments = synthetic_inputs()
    for hit in arguments["result"]["hits"]:
        hit["length"] = None
    arguments["sequence_identity_bindings"] = [sequence_binding(4), sequence_binding(9, length=11)]
    sheet = build_database_sheet(**arguments)
    assert "blast_sequence_identity_operand_conflict" in codes(sheet)
    assert len(sheet["sequence_groups"]) == 2
    assert sheet["dependence"]["unknown_cross_hit_sequence_identity"] is True
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == .5
    assert sheet["hits"][0]["measurements"]["reference_paired_coverage"] is None


def test_one_sequence_source_record_cannot_supply_contradictory_digests():
    arguments = synthetic_inputs()
    arguments["sequence_identity_bindings"] = [sequence_binding(4),
                                               sequence_binding(9, sequence="ACDEFPQRST")]
    arguments["sequence_identity_bindings"][1]["pointer"] = "/records/4"
    sheet = build_database_sheet(**arguments)
    assert "blast_sequence_binding_source_identity_conflict" in codes(sheet)
    assert len(sheet["sequence_groups"]) == 2
    assert all(group["identity_basis"] == [] for group in sheet["sequence_groups"])
    assert sheet["dependence"]["unknown_cross_hit_sequence_identity"] is True


@pytest.mark.parametrize("field", ["description_bindings", "sequence_identity_bindings"])
def test_nonobject_independent_binding_row_remains_a_local_diagnostic(field):
    arguments = synthetic_inputs()
    arguments[field].append(None)
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert sheet[field][-1] is None
    assert any(issue["code"].endswith("binding_fields_invalid") for issue in sheet["issues"])


def test_explicit_path_never_calls_legacy_matching_or_grouping(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("An explicit path must not fall back to legacy accession/label joins")

    monkeypatch.setattr("gene_annotation_episode.blast_database_grader._attach_metadata", forbidden)
    monkeypatch.setattr("gene_annotation_episode.blast_database_grader._sequence_groups", forbidden)
    sheet = build_database_sheet(**synthetic_inputs())
    assert sheet["coverage"]["matched_metadata_row_count"] == 2


def test_invalid_independent_metadata_fields_preserve_available_function_and_native_scores():
    arguments = synthetic_inputs()
    arguments["reference_metadata"][0].update(assembly=["invalid-shape"], origin=["invalid-shape"])
    sheet = build_database_sheet(**arguments)
    assert {"assembly_object_required", "origin_object_required"} <= codes(sheet)
    assert [row["function"] for row in sheet["functions"]] == ["F", "G"]
    assert sheet["reference_metadata"][0]["assembly"] == ["invalid-shape"]
    assert sheet["hits"][0]["measurements"]["maximum_bit_score"] == 20


@pytest.mark.parametrize("program,molecule", [("blastp", "aa"), ("blastx", "aa"),
    ("blastn", "nt"), ("tblastn", "nt"), ("tblastx", "nt")])
def test_sequence_identity_molecule_uses_reference_operand_not_alignment_symbols(program, molecule):
    arguments = synthetic_inputs()
    arguments["result"]["search"]["program"] = program
    arguments["sequence_identity_bindings"] = [sequence_binding(i, molecule=molecule) for i in (4, 9)]
    sheet = build_database_sheet(**arguments)
    assert len(sheet["sequence_groups"]) == 1
    assert "blast_sequence_binding_reference_molecule_mismatch" not in codes(sheet)


def test_partial_hsp_keeps_observed_coverage_without_fabricating_complete_fraction():
    arguments = synthetic_inputs()
    native = arguments["result"]["hits"][0]
    native["hsps"] *= 2
    native["hsps"].append({"bit_score": 17, "evalue": .01})
    sheet = build_database_sheet(**arguments)
    measured = sheet["hits"][0]["measurements"]
    assert measured["observed_paired_query_positions"] == 5
    assert measured["query_paired_coverage"] is None
    assert measured["maximum_bit_score"] == 20
    assert measured["hsp_count"] == 3
    assert measured["overlap_pair_representations"] == 5
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] == {"F": .8, "G": .2}


def test_empty_hit_report_is_distinct_from_unknown_report_in_explicit_path():
    arguments = synthetic_inputs()
    arguments["result"]["hits"] = []
    arguments["result"]["search"].update(reported_hit_count=0, hit_array_present=True)
    arguments["reference_metadata"] = []
    arguments["description_bindings"] = []
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["native_hit_count"] == 0
    assert sheet["search_limits"]["hit_array_present"] is True
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] is None
    arguments["result"]["search"].update(reported_hit_count=None, hit_array_present=False)
    missing = build_database_sheet(**arguments)
    assert missing["search_limits"]["hit_array_present"] is False
    assert missing["search_limits"]["reported_hit_count"] is None


def test_saved_recalculation_changes_only_parameters_and_derived_weights(tmp_path, monkeypatch):
    arguments = synthetic_inputs()
    sheet = build_database_sheet(**arguments)
    path = tmp_path / "synthetic-sheet.json"
    path.write_text(json.dumps(sheet, allow_nan=False))
    saved = path.read_bytes()
    reopened = json.loads(saved)

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved calculations may not reacquire, rerun, or rebuild inputs")

    monkeypatch.setattr("gene_annotation_episode.blast_database_grader.build_database_sheet", forbidden)
    monkeypatch.setattr("gene_annotation_episode.blast_grading_inputs.parse_blast_json", forbidden)
    monkeypatch.setattr("gene_annotation_episode.blast_grading_inputs.parse_blast_tabular", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    t2 = calculate_database_probabilities(reopened, model={"temperature_bits": 2})
    t1 = calculate_database_probabilities(reopened, model={"temperature_bits": 1})
    assert t2["unadjusted_probabilities"] == {"F": 2 / 3, "G": 1 / 3}
    assert t1["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert t2["function_masses"] == {"F": 1, "G": .5}
    assert t1["function_masses"] == {"F": 1, "G": .25}
    assert reopened == sheet and path.read_bytes() == saved


def fasta_arguments(*, duplicate_content=False, duplicate_text=False):
    """Already-qualified scientific rows; actual byte receipt is M's boundary."""
    arguments = synthetic_inputs()
    for ordinal, row in enumerate(arguments["reference_metadata"]):
        row.update(source="original-full-fasta", native_pointer="",
                   record_locator={"kind": "fasta_record", "record_ordinal": ordinal})
        row["functions"][0]["source"] = "separately-supplied-assignment-json"
        if duplicate_text:
            row["accession"] = "same-identifier"
        binding = arguments["description_bindings"][ordinal]
        binding.update(metadata_source_ref=row["source"], metadata_pointer="",
                       metadata_record_locator=deepcopy(row["record_locator"]))
        binding["metadata_identifier"]["value"] = row["accession"]
        sequence = sequence_binding(binding["hit_index"], sequence=(
            "ACDEFGHIKL" if ordinal == 0 or duplicate_content else "ACDEPQRSTV"))
        sequence.update(source_ref=row["source"], pointer="", record_locator=deepcopy(row["record_locator"]))
        arguments["sequence_identity_bindings"].append(sequence)
    return arguments


def test_v2_original_records_keep_explicit_function_provenance_and_numerical_oracles():
    arguments = fasta_arguments()
    arguments["database_profile"] = dict(database="synthetic-db", release=None, scope="searched_database",
        source="explicit-census-json", count_unit="unique_sequences", total_count=1000, function_counts={"F":100, "G":10})
    before = deepcopy(arguments)
    sheet = build_database_sheet(**arguments)
    assert arguments == before
    assert sheet["schema"] == "blast_database_sheet_v2" and sheet["association_mode"] == "explicit_bindings_v2"
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert len(sheet["sequence_groups"]) == 2
    for index, hit in enumerate(sheet["hits"]):
        assert hit["sequence_identity_bindings"] == [arguments["sequence_identity_bindings"][index]]
        assert hit["associations"][0]["description_binding"] == arguments["description_bindings"][index]
        assert hit["associations"][0]["functions"][0]["source"] == "separately-supplied-assignment-json"
        assert hit["measurements"]["query_paired_coverage"] == .5
    scored = calculate_database_probabilities(sheet)
    assert scored["schema"] == "blast_database_probabilities_v1"
    assert scored["function_masses"] == {"F":1, "G":.25}
    assert scored["unadjusted_probabilities"] == {"F":.8, "G":.2}
    assert scored["representation_adjusted_probabilities"] == {"F":pytest.approx(2/7), "G":pytest.approx(5/7)}
    assert calculate_database_probabilities(sheet, model={"temperature_bits":2})["unadjusted_probabilities"] == {"F":2/3, "G":1/3}


def test_v2_no_functions_are_created_from_original_record_identity():
    arguments = fasta_arguments()
    for row in arguments["reference_metadata"]:
        row["functions"] = []
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert sheet["functions"] == []
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] is None
    assert [g["maximum_bit_score"] for g in sheet["sequence_groups"]] == [20, 18]


def test_v2_distinct_original_ordinals_with_same_content_contribute_one_maximum_split_mass():
    arguments = fasta_arguments(duplicate_content=True)
    sheet = build_database_sheet(**arguments)
    group, = sheet["sequence_groups"]
    assert group["maximum_bit_score"] == 20 and group["hit_indices"] == [4, 9]
    assert calculate_database_probabilities(sheet)["function_masses"] == {"F":.5, "G":.5}
    arguments["sequence_identity_bindings"] *= 3
    repeated = build_database_sheet(**arguments)
    assert repeated["hits"] == sheet["hits"]
    assert calculate_database_probabilities(repeated) == calculate_database_probabilities(sheet)


def test_v2_same_text_at_distinct_original_ordinals_does_not_group_different_symbols():
    sheet = build_database_sheet(**fasta_arguments(duplicate_text=True))
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert len(sheet["sequence_groups"]) == 2
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] == {"F":.8, "G":.2}


def test_v2_same_original_record_can_keep_multiple_native_hits_and_explicit_functions():
    arguments = fasta_arguments(duplicate_content=True, duplicate_text=True)
    for field in ("reference_metadata", "description_bindings", "sequence_identity_bindings"):
        key = "metadata_record_locator" if field == "description_bindings" else "record_locator"
        arguments[field][1][key]["record_ordinal"] = 0
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert len(sheet["hits"]) == 2 and len(sheet["sequence_groups"]) == 1
    assert calculate_database_probabilities(sheet)["function_masses"] == {"F":.5, "G":.5}


def test_v2_file_only_v1_record_and_explicit_ordinal_are_not_inferred_equal_addresses():
    arguments = fasta_arguments()
    arguments["reference_metadata"][0].pop("record_locator")
    arguments["description_bindings"][0].pop("metadata_record_locator")
    arguments["sequence_identity_bindings"][0].pop("record_locator")
    sheet = build_database_sheet(**arguments)
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert "blast_sequence_binding_source_identity_conflict" not in codes(sheet)
    assert "blast_description_binding_metadata_record_conflict" not in codes(sheet)
    assert "record_locator" not in sheet["sequence_identity_bindings"][0]
    assert len(sheet["sequence_groups"]) == 2


def test_v2_sequence_source_key_rejects_contradictory_same_record():
    arguments = fasta_arguments()
    arguments["sequence_identity_bindings"][1]["record_locator"] = {"kind":"fasta_record", "record_ordinal":0}
    sheet = build_database_sheet(**arguments)
    assert "blast_sequence_binding_source_identity_conflict" in codes(sheet)
    assert all(hit["sequence_identity_bindings"] == [] for hit in sheet["hits"])
    assert [hit["measurements"]["maximum_bit_score"] for hit in sheet["hits"]] == [20,18]
    assert "Unresolved returned native-hit groups" in calculate_database_probabilities(sheet)["assumptions"][-1]


@pytest.mark.parametrize("change", [{"accession":"different"}, {"taxid":620}])
def test_v2_metadata_source_key_rejects_contradiction_only_at_that_record(change):
    arguments = fasta_arguments()
    contradictory = deepcopy(arguments["reference_metadata"][0])
    contradictory.update(change)
    arguments["reference_metadata"].append(contradictory)
    sheet = build_database_sheet(**arguments)
    assert "blast_description_binding_metadata_record_conflict" in codes(sheet)
    assert sheet["coverage"]["unmatched_metadata_indices"] == [0,2]
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] == {"G":1.0}


def test_v2_metadata_binding_locator_equality_and_same_hit_sequence_crosscheck():
    arguments = fasta_arguments(duplicate_text=True)
    arguments["description_bindings"][0]["metadata_record_locator"]["record_ordinal"] = 1
    mismatch = build_database_sheet(**arguments)
    assert "blast_description_binding_metadata_provenance_mismatch" in codes(mismatch)
    arguments["reference_metadata"][0]["record_locator"]["record_ordinal"] = 1
    cross = build_database_sheet(**arguments)
    assert "blast_description_binding_sequence_record_mismatch" in codes(cross)
    assert "blast_description_binding_metadata_record_conflict" not in codes(cross)
    assert cross["coverage"]["matched_metadata_row_count"] == 1
    assert calculate_database_probabilities(cross)["unadjusted_probabilities"] == {"G":1.0}


def test_v2_separate_json_assignment_record_does_not_need_the_fasta_address():
    arguments = fasta_arguments()
    original = synthetic_inputs()
    arguments["reference_metadata"] = original["reference_metadata"]
    arguments["description_bindings"] = original["description_bindings"]
    sheet = build_database_sheet(**arguments)
    assert sheet["schema"] == "blast_database_sheet_v2"
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] == {"F":.8, "G":.2}
    assert "record_locator" not in sheet["reference_metadata"][0]


def test_null_and_absent_locators_use_the_same_existing_pointer_key():
    arguments = synthetic_inputs()
    arguments["sequence_identity_bindings"] = [sequence_binding(4), sequence_binding(9, sequence="ACDEPQRSTV")]
    arguments["sequence_identity_bindings"][0]["record_locator"] = None
    arguments["sequence_identity_bindings"][1]["pointer"] = arguments["sequence_identity_bindings"][0]["pointer"]
    sheet = build_database_sheet(**arguments)
    assert sheet["schema"] == "blast_database_sheet_v2"
    assert "blast_sequence_binding_source_identity_conflict" in codes(sheet)


def test_implicit_matcher_cannot_consume_a_new_locator_even_when_null():
    arguments = synthetic_inputs()
    arguments["reference_metadata"][0]["record_locator"] = None
    arguments.pop("description_bindings")
    arguments.pop("sequence_identity_bindings")
    with pytest.raises(ValueError, match="^blast_record_locator_requires_explicit_bindings$"):
        build_database_sheet(**arguments)


def test_saved_generic_v1_never_auto_upgrades_and_v2_mode_is_explicit():
    sheet = build_database_sheet(**fasta_arguments())
    sheet["schema"] = "blast_database_sheet_v1"
    sheet["association_mode"] = "explicit_bindings_v1"
    with pytest.raises(ValueError, match="^blast_record_locator_requires_v2_sheet$"):
        calculate_database_probabilities(sheet)
    sheet["schema"] = "blast_database_sheet_v2"
    with pytest.raises(ValueError, match="^blast_database_association_mode_invalid$"):
        calculate_database_probabilities(sheet)
    sheet["schema"] = "blast_database_sheet_v3"
    with pytest.raises(ValueError, match="^blast_database_sheet_required$"):
        calculate_database_probabilities(sheet)


def test_locator_words_inside_evidence_and_native_record_do_not_select_v2():
    arguments = synthetic_inputs()
    arguments["reference_metadata"][0]["native_record"] = {"record_locator":{"not":"a locator"}}
    arguments["reference_metadata"][0]["functions"][0]["evidence"] = [{"metadata_record_locator":True}]
    assert build_database_sheet(**arguments)["schema"] == "blast_database_sheet_v1"

