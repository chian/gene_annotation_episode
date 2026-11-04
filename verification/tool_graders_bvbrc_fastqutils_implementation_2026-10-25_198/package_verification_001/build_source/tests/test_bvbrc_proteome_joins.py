"""Explicit synthetic supplied inputs, parsed with the real A/B1 functions.

These examples do not assert live BV-BRC output or proof of executed FASTAs.
"""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_proteome_inputs as inputs
from gene_annotation_episode import bvbrc_proteome_native as native_parser
from gene_annotation_episode.bvbrc_proteome_joins import build_native_joins
from gene_annotation_episode.bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data


CONTRACT = {
    "id": "GenomeComparison_inspected_source_v1",
    "application_tree": "5c365e1dca2b3a8c311d7d352e862ff1442eefc9",
    "application_sha256": "4267b35bdd5ad858b833fa2b84eb794c91e95b7f5abc0628b90ec4d6a0a33c14",
    "dependency_tree": "18196fe0df123702457e4af2e0b1e0707d5f5281",
    "deployment_match": "unobserved", "deployment_evidence": [],
}


def source(raw, name, *, complete=True):
    return {"content": {"source_ref": name, "artifact_field": "artifact_ref", "artifact_ref": name,
            "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)},
            "body_complete": complete, "object_complete": "yes" if complete else "unknown"}


def fasta(key, raw, *, complete=True):
    result = inputs.read_protein_fasta(raw, source=source(raw, "synthetic-" + key, complete=complete),
                                     declared_format="protein_fasta_utf8_v1", inventory_key=key)
    assert result["value"] is not None
    return result["value"]


def native_result(rows=None):
    if rows is None:
        rows = [{"ref_genome_patric_id": "r1", "ref_genome_aa_length": 4,
                 "comp_genome_2_patric_id": "s1", "comp_genome_2_aa_length": 4,
                 "comp_genome_2_hit": "bi (<->)", "comp_genome_2_percent_identity": "0.875", "comp_genome_2_seq_coverage": "0.750"},
                {"ref_genome_patric_id": "r2", "ref_genome_aa_length": 4,
                 "comp_genome_2_patric_id": "s2", "comp_genome_2_aa_length": 3,
                 "comp_genome_2_hit": "uni (->)", "comp_genome_2_percent_identity": "0.000", "comp_genome_2_seq_coverage": "0.500"}]
    raw = json.dumps({"genome_names": {"ref_genome": "same label", "comp_genome_2": "same label"},
                      "feature_matches": rows}).encode()
    result = native_parser.parse_genome_comparison(raw, source=source(raw, "synthetic-native"),
                        declared_format="genome_comparison_json_v1", source_contract=deepcopy(CONTRACT))
    assert result["value"] is not None
    return result


def input_index():
    params = {"genome_ids": [], "user_genomes": ["/unused.faa", "/ref.faa", "/subject.faa"],
              "user_feature_groups": [], "reference_genome_index": 2}
    raw = json.dumps({"parameters": params}).encode()
    task = {"resource_id": "synthetic-api", "task_id": "synthetic-task", "required_application_id": "GenomeComparison",
            "native_application_id": "GenomeComparison", "submitted_parameters": params, "submitted_start_parameters": {},
            "scheduler_returned_parameters": None, "effective_parameters": None, "submission_receipt_ref": "synthetic-receipt",
            "submission_operation_key": "synthetic-operation", "submission_source_ref": "synthetic-original-parameters"}
    parameter = {"kind": "submitted", "source_field": {"source_ref": task["submission_source_ref"],
                 "sha256": hashlib.sha256(raw).hexdigest(), "pointer": "/parameters", "row_ordinal": None, "field_name": None}}
    result = inputs.index_original_inputs(task, parameter_source=parameter, source_contract=deepcopy(CONTRACT))
    assert result["value"] is not None
    return result["value"]


def native_link(native, kind, ordinal, inventory, record, identifier):
    binding = native["source"]["content"]
    return {"native": {"source_ref": binding["source_ref"], "sha256": binding["sha256"], "kind": kind,
                       "reference_row_ordinal": ordinal, "track_key": "ref_genome" if kind == "reference" else "comp_genome_2",
                       "association_key": None if kind == "reference" else f"comp_genome_2/row/{ordinal}"},
            "protein": {"inventory_key": inventory, "record_ordinal": record}, "basis": "unique_exact_identifier",
            "native_identifier": identifier, "mapping_source_fields": []}


def case():
    native = native_result()["value"]
    links = [native_link(native, "reference", 0, "ref", 0, "r1"),
             native_link(native, "reference", 1, "ref", 1, "r2"),
             native_link(native, "association_subject", 0, "subject", 0, "s1"),
             native_link(native, "association_subject", 1, "subject", 1, "s2")]
    execution = [{"input_key": f"/user_genomes/{i}", "inventory_key": key, "relation": "original_supplied_fasta",
                  "executed_fasta": None, "membership_complete": "unknown", "staged_path": None, "witness_source_fields": []}
                 for i, key in ((1, "ref"), (2, "subject"))]
    return {"native": native, "input_index": input_index(),
            "inventories": [fasta("ref", b">r1\nACDE\n>r2\nCCCC\n"), fasta("subject", b">s1\nACDE\n>s2\nAGG\n")],
            "feature_snapshots": [], "genome_snapshots": [], "sequence_snapshots": [],
            "execution_links": execution, "native_links": links, "metadata_links": []}


def codes(result):
    return {item["code"] for item in result["diagnostics"]}


def build(data):
    before = deepcopy(data)
    result = build_native_joins(**data)
    assert data == before
    assert validate_proteome_sheet_data("NativeJoinsResult", result) == result
    return result


def test_actual_parsed_inputs_keep_original_track_mapping_and_sequence_occurrences():
    result = build(case())
    value = result["value"]
    assert result["status"] == "partial"
    assert [(b["input_key"], b["track_key"], b["inventory_key"]) for b in value["track_bindings"]] == [
        ("/user_genomes/1", "ref_genome", "ref"), ("/user_genomes/0", "comp_genome_1", None),
        ("/user_genomes/2", "comp_genome_2", "subject")]
    assert [j["state"] for j in value["reference_joins"] + value["subject_joins"]] == ["joined"] * 4
    assert all(b["input_record_count"]["value"] is None and b["membership_complete"] == "unknown" for b in value["track_bindings"])
    assert [[(m["inventory_key"], m["record_ordinal"]) for m in g["members"]] for g in value["sequence_groups"]] == [
        [("ref", 0), ("subject", 0)], [("ref", 1)], [("subject", 1)]]
    assert "exact_executed_input_missing" in codes(result)


def test_no_explicit_links_means_no_automatic_identifier_join():
    data = case()
    data["native_links"] = []
    result = build(data)["value"]
    assert all(j["state"] == "not_supplied" and j["protein"] is None for j in result["reference_joins"] + result["subject_joins"])


def test_identical_link_requests_do_not_duplicate_protein_occurrences():
    data = case()
    data["native_links"].append(deepcopy(data["native_links"][0]))
    value = build(data)["value"]
    assert value["reference_joins"][0]["accepted_link_indices"] == [0, 4]
    assert len(value["reference_joins"][0]["candidates"]) == 1
    assert sum(len(group["members"]) for group in value["sequence_groups"]) == 4


@pytest.mark.parametrize("field,value", [("source_ref", "wrong-source"), ("sha256", "0" * 64)])
def test_wrong_native_source_request_is_retained_as_local_conflict(field, value):
    data = case()
    data["native_links"][0]["native"][field] = value
    result = build(data)
    assert result["status"] == "partial"
    assert result["value"]["requested_native_links"] == data["native_links"]
    assert result["value"]["reference_joins"][0]["state"] == "conflicting"
    assert result["value"]["reference_joins"][1]["state"] == "joined"


@pytest.mark.parametrize("replacement", [{"inventory_key": "subject", "record_ordinal": 0},
                                        {"inventory_key": "ref", "record_ordinal": 99},
                                        {"inventory_key": "missing", "record_ordinal": 0}])
def test_wrong_occurrence_link_fails_locally(replacement):
    data = case()
    data["native_links"][0]["protein"] = replacement
    value = build(data)["value"]
    assert value["reference_joins"][0]["state"] == "conflicting"
    assert value["subject_joins"][0]["state"] == "joined"


def test_requested_nonexistent_native_row_is_not_fabricated():
    data = case()
    link = deepcopy(data["native_links"][0])
    link["native"]["reference_row_ordinal"] = 99
    data["native_links"].append(link)
    result = build(data)
    assert len(result["value"]["reference_joins"]) == 2
    assert result["diagnostics"][-1]["path"] == "/requested_native_links/4"


def test_contradictory_explicit_links_do_not_select_first():
    data = case()
    wrong = deepcopy(data["native_links"][0])
    wrong["protein"]["record_ordinal"] = 1
    data["native_links"].append(wrong)
    assert build(data)["value"]["reference_joins"][0]["state"] == "conflicting"


@pytest.mark.parametrize("sequence", [b"ACDE", b"CCCC"])
def test_duplicate_header_occurrences_remain_ambiguous_even_if_sequences_match(sequence):
    data = case()
    data["inventories"][0] = fasta("ref", b">r1\nACDE\n>r1\n" + sequence + b"\n")
    result = build(data)
    join = result["value"]["reference_joins"][0]
    assert join["state"] == "ambiguous" and join["protein"] is None
    assert [p["record_ordinal"] for p in join["candidates"]] == [0, 1]
    assert "duplicate_identifier" in codes(result)


def test_cross_input_id_collision_includes_invalid_sequence_occurrences():
    data = case()
    data["inventories"][1] = fasta("subject", b">r1\nAA-?\n>s2\nAGG\n")
    result = build(data)
    assert result["value"]["reference_joins"][0]["state"] == "ambiguous"
    assert "cross_input_identifier_collision" in codes(result)
    assert all(b["identifier_collisions"] == ["r1"] for b in result["value"]["track_bindings"] if b["inventory_key"])


@pytest.mark.parametrize("raw,complete", [(b">r1\nAA-?1\n", True), (b">r1\n", True), (b">r1\nAC", False), (b">r1\nACDE*\n", True)])
def test_identifier_correspondence_does_not_assert_complete_valid_sequence_or_stop_convention(raw, complete):
    data = case()
    data["inventories"][0] = fasta("ref", raw, complete=complete)
    result = build(data)
    assert result["value"]["reference_joins"][0]["state"] == "joined"
    if raw != b">r1\nACDE*\n":
        assert not any(m["inventory_key"] == "ref" for g in result["value"]["sequence_groups"] for m in g["members"])


def test_comparable_native_length_conflict_is_not_ignored():
    data = case()
    data["inventories"][0] = fasta("ref", b">r1\nACDEF\n>r2\nCCCC\n")
    result = build(data)
    assert result["value"]["reference_joins"][0]["state"] == "conflicting"
    assert "sequence_length_conflict" in codes(result)


def test_exact_execution_locator_does_not_supply_denominator():
    data = case()
    link = data["execution_links"][0]
    link.update(relation="exact_executed_fasta", membership_complete="yes",
                executed_fasta=deepcopy(data["inventories"][0]["source"]["content"]),
                witness_source_fields=[data["inventories"][0]["records"][0]["source_field"]])
    result = build(data)
    binding = next(b for b in result["value"]["track_bindings"] if b["track_key"] == "ref_genome")
    assert binding["execution_relation"] == binding["membership_complete"] == "unknown"
    assert binding["input_record_count"]["value"] is None
    assert binding["input_record_count"]["reason_codes"] == ["execution_witness_interface_unavailable"]
    assert result["value"]["reference_joins"][0]["state"] == "joined"
    assert result["value"]["execution_links"][0] == link


def test_producer_occurrence_locator_is_not_a_qualified_mapping():
    data = case()
    data["native_links"][0].update(basis="producer_occurrence_mapping",
                mapping_source_fields=[data["inventories"][0]["records"][0]["source_field"]])
    result = build(data)
    assert result["value"]["reference_joins"][0]["protein"] is None
    assert "occurrence_witness_interface_unavailable" in codes(result)


@pytest.mark.parametrize("change", ["other_inventory", "other_relation", "wrong_bytes"])
def test_conflicting_execution_links_do_not_admit_a_track_inventory(change):
    data = case()
    if change == "wrong_bytes":
        data["execution_links"][0]["executed_fasta"] = deepcopy(data["inventories"][1]["source"]["content"])
    else:
        extra = deepcopy(data["execution_links"][0])
        extra["inventory_key" if change == "other_inventory" else "relation"] = "subject" if change == "other_inventory" else "later_snapshot"
        data["execution_links"].append(extra)
    result = build(data)
    binding = next(b for b in result["value"]["track_bindings"] if b["track_key"] == "ref_genome")
    assert binding["inventory_key"] is None
    assert result["value"]["reference_joins"][0]["protein"] is None
    assert result["value"]["subject_joins"][0]["state"] == "joined"


def test_absent_original_input_index_preserves_requests_without_inferred_track_mapping():
    data = case()
    data["input_index"] = None
    result = build(data)
    assert result["value"]["track_bindings"] == []
    assert all(j["protein"] is None for j in result["value"]["reference_joins"])
    assert "input_arrays_unavailable" in codes(result)


def replace_native(data, replacements):
    rows = []
    for ordinal, reference in enumerate(data["native"]["reference_rows"]):
        row = {"ref_genome_" + k: cell["value"] for k, cell in reference.items()
               if type(cell) is dict and cell.get("presence") == "value"}
        for association in data["native"]["associations"]:
            if association["reference_row_ordinal"] == ordinal:
                row.update({association["track_key"] + "_" + k: cell["value"] for k, cell in association.items()
                            if type(cell) is dict and cell.get("presence") == "value"})
        row.update(replacements.get(ordinal, {}))
        rows.append(row)
    data["native"] = native_result(rows)["value"]
    for link in data["native_links"]:
        link["native"]["sha256"] = data["native"]["source"]["content"]["sha256"]


def test_invalid_json_length_preserves_identity_and_neighboring_native_fraction():
    data = case()
    replace_native(data, {0: {"ref_genome_aa_length": "bad length", "comp_genome_2_aa_length": "bad length"}})
    result = build(data)
    assert result["value"]["reference_joins"][0]["state"] == result["value"]["subject_joins"][0]["state"] == "joined"
    assert data["native"]["associations"][0]["percent_identity"]["value"] == .875


def test_missing_native_identity_is_not_repaired_from_explicit_request_or_label():
    data = case()
    replace_native(data, {0: {"ref_genome_patric_id": None}})
    result = build(data)
    assert result["value"]["reference_joins"][0]["state"] == "unmatched"
    assert result["value"]["subject_joins"][0]["state"] == "joined"
    assert "native_identifier_unavailable" in codes(result)


def test_unknown_table_width_excludes_positional_identity_but_preserves_valid_neighbor():
    data = case()
    header = ["ref_genome_" + name for name in ("contig", "gene", "aa_length", "patric_id", "locus_tag", "gene_name", "plfam_id", "pgfam_id", "function", "start", "end", "strand")]
    header += ["comp_genome_2_" + name for name in ("hit", "contig", "gene", "aa_length", "patric_id", "locus_tag", "gene_name", "function", "percent_identity", "seq_coverage")]
    names = ["reference"] + [""] * 11 + ["subject"] + [""] * 9
    first = ["c", "0", "4", "r1", "", "", "", "", "", "", "", "", "bi (<->)", "s", "0", "4", "s1", "", "", "", ".875"]
    second = ["c", "1", "4", "r2", "", "", "", "", "", "", "", "", "uni (->)", "s", "1", "3", "s2", "", "", "", "0", ".5"]
    raw = ("\n".join("\t".join(row) for row in (names, header, first, second)) + "\n").encode()
    value = native_parser.parse_genome_comparison(raw, source=source(raw, "synthetic-native"),
                declared_format="genome_comparison_tsv_v1", source_contract=CONTRACT)["value"]
    assert value is not None
    data["native"] = value
    for link in data["native_links"]:
        link["native"]["sha256"] = value["source"]["content"]["sha256"]
    result = build(data)
    assert [j["state"] for j in result["value"]["reference_joins"]] == ["unmatched", "joined"]
    assert [j["state"] for j in result["value"]["subject_joins"]] == ["unmatched", "joined"]
    assert "native_table_layout_uncertain" in codes(result)


def test_reusing_inventory_for_two_original_input_slots_preserves_collision():
    data = case()
    data["execution_links"].append({**data["execution_links"][0], "input_key": "/user_genomes/0"})
    result = build(data)
    assert result["value"]["reference_joins"][0]["state"] == "ambiguous"
    assert len(result["value"]["reference_joins"][0]["candidates"]) == 1
    assert "cross_input_identifier_collision" in codes(result)


def test_later_snapshot_does_not_become_original_execution():
    data = case()
    data["execution_links"][0]["relation"] = "later_snapshot"
    result = build(data)
    assert result["value"]["track_bindings"][0]["execution_relation"] == "later_snapshot"
    assert result["value"]["track_bindings"][0]["input_record_count"]["value"] is None
    assert "later_snapshot_not_original_input" in codes(result)


def metadata(kind, rows, key):
    raw = json.dumps(rows).encode()
    population = {"origin": "later_database_snapshot", "query_source": None, "selected_fields": [], "offset": None,
                  "requested_limit": None, "reported_total_count": None, "population_complete": "unknown", "completeness_evidence": []}
    readers = {"feature": (inputs.read_feature_metadata, "bvbrc_genome_feature_json_array_v1"),
               "genome": (inputs.read_genome_metadata, "bvbrc_genome_json_array_v1"),
               "sequence": (inputs.read_feature_sequences, "bvbrc_feature_sequence_json_array_v1")}
    reader, fmt = readers[kind]
    kwargs = {"coordinate_convention": {"value": "unknown", "source_fields": []}} if kind == "feature" else {}
    result = reader(raw, source=source(raw, "synthetic-" + key), declared_format=fmt,
                    snapshot_key=key, population=population, **kwargs)
    assert result["value"] is not None
    return result["value"]


def metadata_case(*, feature=None, genome=None, sequence=None):
    data = case()
    md5 = hashlib.md5(b"ACDE").hexdigest()
    feature = {"feature_id": "r1", "genome_id": "g1", "aa_sequence_md5": md5.upper(), "product": "explicit supplied assignment", **(feature or {})}
    genome = {"genome_id": "g1", "taxon_id": 7, **(genome or {})}
    sequence = {"md5": md5, "sequence": "ac de\n", **(sequence or {})}
    data.update(feature_snapshots=[metadata("feature", [feature], "features")],
                genome_snapshots=[metadata("genome", [genome], "genomes")],
                sequence_snapshots=[metadata("sequence", [sequence], "sequences")])
    data["metadata_links"] = [{"protein": {"inventory_key": "ref", "record_ordinal": 0},
        "feature": {"snapshot_key": "features", "row_ordinal": 0}, "genome": {"snapshot_key": "genomes", "row_ordinal": 0},
        "feature_sequence": {"snapshot_key": "sequences", "row_ordinal": 0}, "basis": "exact_feature_identifier", "mapping_source_fields": []}]
    return data


def test_metadata_feature_genome_md5_and_actual_sequence_relationships():
    data = metadata_case()
    join = build(data)["value"]["metadata_joins"][0]
    assert join["state"] == "joined"
    assert all(join[k] == data["metadata_links"][0][k] for k in ("protein", "feature", "genome", "feature_sequence"))


def test_invalid_unrelated_metadata_numbers_do_not_erase_exact_identity():
    data = metadata_case(feature={"aa_length": "bad-value"}, genome={"taxon_id": -1})
    assert not data["feature_snapshots"][0]["records"][0]["valid"]
    assert not data["genome_snapshots"][0]["records"][0]["valid"]
    assert build(data)["value"]["metadata_joins"][0]["state"] == "joined"


@pytest.mark.parametrize("override", [{"feature": {"feature_id": "not-r1"}}, {"genome": {"genome_id": "g2"}},
                                     {"feature": {"aa_sequence_md5": "0" * 32}}, {"feature": {"aa_sequence_md5": "not-a-digest"}}])
def test_conflicting_metadata_relationship_fails_locally(override):
    result = build(metadata_case(**override))
    join = result["value"]["metadata_joins"][0]
    assert join["state"] == "conflicting"
    assert all(join[k] is None for k in ("feature", "genome", "feature_sequence"))
    assert result["value"]["reference_joins"][0]["state"] == "joined"


@pytest.mark.parametrize("field", ["feature", "genome", "feature_sequence"])
def test_missing_requested_metadata_row_stays_unmatched(field):
    data = metadata_case()
    data["metadata_links"][0][field]["row_ordinal"] = 9
    join = build(data)["value"]["metadata_joins"][0]
    assert join["state"] == "unmatched"
    assert all(join[k] is None for k in ("feature", "genome", "feature_sequence"))


def test_multiple_explicit_source_assignments_remain_separate():
    data = metadata_case()
    data["feature_snapshots"].append(metadata("feature", [{"patric_id": "r1", "product": "another assignment"}], "second-features"))
    link = deepcopy(data["metadata_links"][0])
    link.update(feature={"snapshot_key": "second-features", "row_ordinal": 0}, genome=None, feature_sequence=None)
    data["metadata_links"].append(link)
    joins = build(data)["value"]["metadata_joins"]
    assert [(j["link_index"], j["state"]) for j in joins] == [(0, "joined"), (1, "joined")]


def test_metadata_claim_of_producer_mapping_stays_unqualified():
    data = metadata_case()
    data["metadata_links"][0]["basis"] = "producer_occurrence_mapping"
    result = build(data)
    assert result["value"]["metadata_joins"][0]["state"] == "unmatched"
    assert "occurrence_witness_interface_unavailable" in codes(result)


def test_feature_sequence_digest_conflict_is_preserved_as_conflict():
    result = build(metadata_case(sequence={"sequence": "CCCC"}))
    assert result["value"]["metadata_joins"][0]["state"] == "conflicting"
    assert "sequence_digest_conflict" in codes(result)


def test_duplicate_feature_identity_in_one_snapshot_is_not_arbitrarily_resolved():
    data = metadata_case()
    data["feature_snapshots"] = [metadata("feature", [{"feature_id": "r1", "product": "one"},
                                                     {"patric_id": "r1", "product": "two"}], "features")]
    result = build(data)
    assert result["value"]["metadata_joins"][0]["state"] == "ambiguous"
    assert "metadata_join_ambiguous" in codes(result)


def test_actual_source_identity_conflict_is_global_and_distinct_from_rejected_raw_link():
    data = case()
    data["inventories"][0] = fasta("ref", b">r1\nACDE\n")
    # These are separately well-formed saved inputs, but they claim the same
    # source identity for different byte objects. No join can repair that.
    data["inventories"][1] = inputs.read_protein_fasta(b">s1\nACDE\n", source=source(b">s1\nACDE\n", "synthetic-ref"),
                declared_format="protein_fasta_utf8_v1", inventory_key="subject")["value"]
    result = build(data)
    assert result["status"] == "invalid"
    assert codes(result) == {"supplied_contract_invalid"}


@pytest.mark.parametrize("change", ["link_extra", "boolean_ordinal", "duplicate_inventory", "duplicate_snapshot", "bad_native_copy", "wrong_array_type"])
def test_malformed_global_contract_is_invalid(change):
    data = metadata_case()
    if change == "link_extra":
        data["native_links"][0]["invented"] = True
    elif change == "boolean_ordinal":
        data["native_links"][0]["protein"]["record_ordinal"] = True
    elif change == "duplicate_inventory":
        data["inventories"].append(deepcopy(data["inventories"][0]))
    elif change == "duplicate_snapshot":
        data["genome_snapshots"][0]["snapshot_key"] = "features"
    elif change == "bad_native_copy":
        data["native"]["associations"][0]["percent_identity"]["value"] = .3
    else:
        data["native_links"] = {}
    result = build(data)
    assert result["status"] == "invalid" and result["value"] is None
    assert codes(result) == {"supplied_contract_invalid"}


def test_detached_result_and_pure_repeated_construction(monkeypatch):
    data = metadata_case()
    expected = build(data)
    def forbidden(*args, **kwargs):
        raise AssertionError("Join construction attempted IO, parsing or execution")
    with monkeypatch.context() as patch:
        for owner, attr in ((Path, "read_text"), (Path, "read_bytes"), (io, "open"), (socket, "socket"),
                            (subprocess, "run"), (subprocess, "Popen"), (native_parser, "parse_genome_comparison")):
            patch.setattr(owner, attr, forbidden)
        patch.setattr("builtins.open", forbidden)
        for name in ("read_protein_fasta", "read_feature_metadata", "read_genome_metadata", "read_feature_sequences", "index_original_inputs"):
            patch.setattr(inputs, name, forbidden)
        assert build(data) == expected
    data["native_links"][0]["native_identifier"] = "mutated"
    data["inventories"][0]["records"][0]["sequence"] = "mutated"
    assert expected["value"]["requested_native_links"][0]["native_identifier"] == "r1"
