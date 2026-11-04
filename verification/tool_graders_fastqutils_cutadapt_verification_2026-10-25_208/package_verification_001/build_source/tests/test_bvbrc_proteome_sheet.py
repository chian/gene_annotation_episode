"""Synthetic A/B1 -> B3 -> B4 checks, with explicit synthetic B2 handoffs.

No fixture is retained native service output. Expected numerical answers are
literal independent values, and every calculator call uses the real shared
saved-sheet validator. No scientific execution or episode integration is claimed.
"""
import builtins
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_proteome_inputs as inputs
from gene_annotation_episode import bvbrc_proteome_native as parser
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components
from gene_annotation_episode.bvbrc_proteome_sheet import build_native_sheet
from gene_annotation_episode.bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data


IDENTITY = "native_first_hsp_alignment_identity_fraction"
ENDPOINT = "native_subject_endpoint_difference_fraction"
CONTRACT = {"id": "GenomeComparison_inspected_source_v1",
            "application_tree": "5c365e1dca2b3a8c311d7d352e862ff1442eefc9",
            "application_sha256": "4267b35bdd5ad858b833fa2b84eb794c91e95b7f5abc0628b90ec4d6a0a33c14",
            "dependency_tree": "18196fe0df123702457e4af2e0b1e0707d5f5281",
            "deployment_match": "unobserved", "deployment_evidence": []}
REF_FIELDS = "contig gene aa_length patric_id locus_tag gene_name plfam_id pgfam_id function start end strand".split()
SUB_FIELDS = "hit contig gene aa_length patric_id locus_tag gene_name function percent_identity seq_coverage".split()


def source(raw, key, *, complete="yes", body=True):
    return {"content": {"source_ref": key, "artifact_field": "artifact_ref", "artifact_ref": key + "-bytes",
                         "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)},
            "body_complete": body, "object_complete": complete}


def field(src, pointer="", ordinal=None, name=None):
    return {"source_ref": src["content"]["source_ref"], "sha256": src["content"]["sha256"],
            "pointer": pointer, "row_ordinal": ordinal, "field_name": name}


def scope(**values):
    return {k: values.get(k) for k in ("track_key", "reference_row_ordinal", "association_key", "protein_key",
                                      "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")}


def diagnostic(code, **where):
    return {"code": code, "severity": "qualification", "path": "", "scope": scope(**where), "source_fields": []}


def missing(reason="execution_witness_interface_unavailable"):
    return {"state": "missing_input", "value": None, "reason_codes": [reason], "source_fields": []}


def native_rows():
    result = []
    for i in range(4):
        ref = ["ctg", str(i), "4", f"R{i}", f"r{i}", "", "", "", "native reference assignment", str(1+15*i), str(12+15*i), "+"]
        row = dict(zip(["ref_genome_" + n for n in REF_FIELDS], ref))
        if i < 3:
            sub = ["bi (<->)" if i != 1 else "uni (->)", "ctgS", str(i), "4", "S0" if i < 2 else "S1",
                   "", "", "native subject assignment", ["0.875", "0.000", "0.625"][i], ["0.990", "0.500", "0.750"][i]]
            row.update(zip(["comp_genome_2_" + n for n in SUB_FIELDS], sub))
        result.append(row)
    return result


def native(rows=None, *, key="synthetic-primary", complete="yes", body=True, fmt="json", extra_tracks=True):
    rows = native_rows() if rows is None else rows
    names = {"ref_genome": "same label", "comp_genome_2": "same label"}
    if extra_tracks:
        names["comp_genome_4"] = "name only"
    if fmt == "json":
        raw = json.dumps({"genome_names": names, "feature_matches": rows}, ensure_ascii=False).encode()
    else:
        headers = ["ref_genome_" + n for n in REF_FIELDS] + ["comp_genome_2_" + n for n in SUB_FIELDS]
        labels = ["same label"] + [""] * 11 + ["same label"] + [""] * 9
        lines = ["\t".join(labels), "\t".join(headers)]
        lines += ["\t".join(str(row.get(k, "")) for k in headers) for row in rows]
        raw = ("\n".join(lines) + "\n").encode()
    result = parser.parse_genome_comparison(raw, source=source(raw, key, complete=complete, body=body),
        declared_format=f"genome_comparison_{fmt}_v1", source_contract=deepcopy(CONTRACT))
    assert result["value"] is not None
    return result


def arguments(result=None):
    result = native() if result is None else result
    return {"native_results": [result], "primary_source_ref": result["value"]["source"]["content"]["source_ref"],
            "input_index": None, "inventories": [], "feature_snapshots": [], "genome_snapshots": [],
            "sequence_snapshots": [], "joins": None, "representation_links": []}


def index(kind="user_genome"):
    values = [f"/selected-{i}.faa" for i in range(5)]
    parameters = {"genome_ids": values if kind == "genome_id" else [], "user_genomes": values if kind == "user_genome" else [],
                  "user_feature_groups": [], "reference_genome_index": 1, "min_ident": 0,
                  "min_seq_cov": None, "max_e_val": 1e-5}
    src = source(json.dumps({"parameters": parameters}).encode(), "synthetic-parameters")
    task = {"resource_id": "synthetic-api", "task_id": "synthetic-task",
            "required_application_id": "GenomeComparison", "native_application_id": "GenomeComparison",
            "submitted_parameters": parameters, "submitted_start_parameters": {}, "scheduler_returned_parameters": None,
            "effective_parameters": None, "submission_receipt_ref": "synthetic-submission",
            "submission_operation_key": "synthetic-op", "submission_source_ref": src["content"]["source_ref"]}
    result = inputs.index_original_inputs(task, parameter_source={"kind": "submitted", "source_field": field(src, "/parameters")},
                                         source_contract=deepcopy(CONTRACT))
    assert result["value"] is not None
    return result["value"]


def inventory(key, raw, *, complete="yes"):
    result = inputs.read_protein_fasta(raw, source=source(raw, key + "-source", complete=complete),
                                      declared_format="protein_fasta_utf8_v1", inventory_key=key)
    assert result["value"] is not None
    return result["value"]


def linked_arguments(*, ref_raw=b">R0\nAAAA\n>R1\nCCCC\n>R2\nDDDD\n>R3\nEEEE\n",
                     sub_raw=b">S0\nFFFF\n>S1\nFFFF\n", ref_complete="yes", sub_complete="yes", result=None):
    """Explicit test handoff, not a replacement B2 implementation or ID matcher."""
    args = arguments(result)
    args["input_index"] = index()
    ref = inventory("reference-input", ref_raw, complete=ref_complete)
    sub = inventory("subject-input", sub_raw, complete=sub_complete)
    args["inventories"] = [ref, sub]
    joins = {"version": "bvbrc_proteome_joins_proposal_v1", "primary_source_ref": args["primary_source_ref"],
             "execution_links": [], "requested_native_links": [], "requested_metadata_links": [],
             "track_bindings": [], "reference_joins": [], "subject_joins": [], "metadata_joins": [],
             "sequence_groups": deepcopy(ref["sequence_groups"] + sub["sequence_groups"]), "diagnostics": []}
    for entry in args["input_index"]["inputs"]:
        inv = ref if entry["expected_track_key"] == "ref_genome" else sub if entry["expected_track_key"] == "comp_genome_2" else None
        joins["track_bindings"].append({"track_key": entry["expected_track_key"], "input_key": entry["input_key"],
            "inventory_key": inv["inventory_key"] if inv else None, "execution_relation": "original_supplied_fasta" if inv else "unknown",
            "input_record_count": missing(), "membership_complete": "unknown", "identifier_collisions": [], "diagnostics": []})
        if inv:
            joins["execution_links"].append({"input_key": entry["input_key"], "inventory_key": inv["inventory_key"],
                "relation": "original_supplied_fasta", "executed_fasta": None, "membership_complete": "unknown",
                "staged_path": None, "witness_source_fields": []})
    projection = args["native_results"][0]["value"]
    binding = projection["source"]["content"]
    for kind, rows, inv, ordinals, dest in (
        ("reference", projection["reference_rows"], ref, [0, 1, 2, 3], "reference_joins"),
        ("association_subject", projection["associations"], sub, [0, 0, 1], "subject_joins"),
    ):
        for row, ordinal in zip(rows, ordinals):
            selector = {"source_ref": binding["source_ref"], "sha256": binding["sha256"], "kind": kind,
                        "reference_row_ordinal": row.get("row_ordinal", row.get("reference_row_ordinal")),
                        "track_key": "ref_genome" if kind == "reference" else row["track_key"],
                        "association_key": None if kind == "reference" else row["association_key"]}
            protein = {"inventory_key": inv["inventory_key"], "record_ordinal": ordinal}
            link = {"native": deepcopy(selector), "protein": deepcopy(protein), "basis": "unique_exact_identifier",
                    "native_identifier": row["patric_id"]["value"], "mapping_source_fields": []}
            joins[dest].append({"native": selector, "state": "joined", "protein": protein, "candidates": [deepcopy(protein)],
                "accepted_link_indices": [len(joins["requested_native_links"])], "diagnostics": []})
            joins["requested_native_links"].append(link)
    args["joins"] = joins
    return args


def parameters(identity=.6, endpoint=.7):
    return {"version": "bvbrc_proteome_native_parameters_proposal_v1", "track_keys": ["comp_genome_2"],
            "minimum_identity_fraction": identity, "minimum_subject_endpoint_difference_fraction": endpoint,
            "allowed_hit_categories": None}


def build(args):
    result = build_native_sheet(**args)
    assert result["status"] == "partial", result
    assert validate_proteome_sheet_data("NativeSheetResult", result) == result
    return result["value"]


def representation(left, right, permutation=None):
    l, r = left["value"], right["value"]
    mapping = dict(enumerate(range(len(l["reference_rows"])) if permutation is None else permutation))
    return {"left_source_ref": l["source"]["content"]["source_ref"], "right_source_ref": r["source"]["content"]["source_ref"],
            "relation": "alternate_full_projection",
            "reference_pairs": [{"left_row_ordinal": a, "right_row_ordinal": b} for a, b in mapping.items()],
            "association_pairs": [{"left_association_key": a["association_key"],
                "right_association_key": f'{a["track_key"]}/row/{mapping[a["reference_row_ordinal"]]}'} for a in l["associations"]],
            "source_fields": []}


def test_real_parser_cells_copy_exactly_and_b4_recalculates_without_sheet_mutation():
    args = linked_arguments()
    before = deepcopy(args)
    sheet = build(args)
    assert args == before
    assert sheet["native_results"] == before["native_results"]
    assert sheet["joins"] == before["joins"]
    for row, original in zip(sheet["association_rows"], args["native_results"][0]["value"]["associations"]):
        assert row[IDENTITY] == original["percent_identity"]
        assert row[ENDPOINT] == original["seq_coverage"]
        assert row["native_subject_length_aa"] == original["aa_length"]
        assert row["native_hit_category"] == original["hit"]
    snapshot = deepcopy(sheet)
    first = calculate_native_components(sheet, parameters=parameters())
    second = calculate_native_components(sheet, parameters=parameters(.9))
    assert first["status"] == second["status"] == "partial"
    track = first["value"]["tracks"][0]
    assert track["first_hsp_identity_summary"]["mean"]["value"] == .5
    assert track["subject_endpoint_difference_summary"]["mean"]["value"] == pytest.approx(56/75)
    assert [r["first_hsp_alignment_identity_percent"]["value"] for r in first["value"]["associations"]] == [87.5, 0, 62.5]
    assert track["observed_bound_reference_count"]["value"] == 3
    assert track["observed_bound_subject_count"]["value"] == 2
    assert track["multiple_reference_subject_count"]["value"] == track["excess_bound_pair_count"]["value"] == 1
    assert track["demonstrated_subject_sequence_group_count"]["value"] == 1
    assert [track["selection_counts"][k]["value"] for k in ("pass", "fail", "unknown")] == [2, 1, 0]
    assert second["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
    assert track["reference_input_record_count"]["value"] is None
    assert track["observed_reference_fraction"]["fraction"]["value"] is None
    assert track["no_published_reference_count"]["value"] is None
    assert first["value"]["sheet_sha256"] == second["value"]["sheet_sha256"]
    assert sheet == snapshot
    sheet["native_results"][0]["value"]["reference_rows"][0]["aa_length"]["value"] = 99
    assert args == before


def test_missing_joins_preserve_numbers_and_missing_expected_tracks_keep_original_keys():
    args = arguments()
    args["input_index"] = index()
    sheet = build(args)
    tracks = {t["track_key"]: t for t in sheet["tracks"]}
    assert set(tracks) == {"ref_genome", "comp_genome_1", "comp_genome_2", "comp_genome_3", "comp_genome_4"}
    assert tracks["comp_genome_2"]["original_input_key"] == "/user_genomes/2"
    assert tracks["comp_genome_1"]["native_materialization"] == tracks["comp_genome_3"]["native_materialization"] == "not_in_projection"
    assert tracks["comp_genome_4"]["native_materialization"] == "unknown"
    assert all(t["complete_reference_row_membership"] == t["complete_published_association_membership"] == "unknown" for t in tracks.values())
    assert [r[IDENTITY]["value"] for r in sheet["association_rows"]] == [.875, 0, .625]
    assert all(r["join_state"] == "not_supplied" and r["coordinate_kind"] == "unknown" for r in sheet["reference_rows"])
    for key in ("comp_genome_1", "comp_genome_4"):
        options = parameters(); options["track_keys"] = [key]
        result = calculate_native_components(sheet, parameters=options)
        assert result["value"]["tracks"][0]["source_association_record_count"]["value"] == 0
        assert result["value"]["tracks"][0]["complete_published_reference_fraction"]["fraction"]["value"] is None


@pytest.mark.parametrize("complete,body", [("no", True), ("unknown", True), ("yes", False)])
def test_partial_source_stays_partial_without_replacing_finite_values(complete, body):
    result = native(complete=complete, body=body)
    sheet = build(arguments(result))
    assert sheet["native_results"] == [result]
    assert sheet["association_rows"][0][IDENTITY]["value"] == .875
    assert all(t["input_record_count"]["value"] is None for t in sheet["tracks"])


def test_invalid_nonprimary_envelope_retained_and_exact_primary_required():
    args = arguments()
    raw = b"{bad JSON"
    invalid = parser.parse_genome_comparison(raw, source=source(raw, "synthetic-invalid"),
        declared_format="genome_comparison_json_v1", source_contract=deepcopy(CONTRACT))
    assert invalid["status"] == "invalid"
    args["native_results"].insert(0, invalid)
    sheet = build(args)
    assert sheet["native_results"][0] == invalid
    assert not any(r["required_input"] == "complete_bytes" for r in sheet["requirements"])
    assert any(r["code"] == "projection_incomplete" and r["required_input"] == "producer_execution_facts" for r in sheet["requirements"])
    args["primary_source_ref"] = "synthetic-invalid"
    result = build_native_sheet(**args)
    assert result["status"] == "invalid" and result["value"] is None
    assert result["diagnostics"][0]["path"] == "/primary_source_ref"


@pytest.mark.parametrize("mutation", [
    lambda a: a.update(native_results=None),
    lambda a: a.update(primary_source_ref=""),
    lambda a: a.update(primary_source_ref="missing"),
    lambda a: a["native_results"].append(deepcopy(a["native_results"][0])),
    lambda a: a["native_results"][0].update(status="invalid"),
    lambda a: a["native_results"][0]["value"]["associations"][0]["percent_identity"].update(value=.9),
    lambda a: a["native_results"][0]["value"]["associations"][0]["percent_identity"]["source_field"].update(sha256="0"*64),
    lambda a: a.update(representation_links={}),
    lambda a: a.update(inventories=()),
    lambda a: a.update(joins={}),
])
def test_malformed_saved_contracts_return_fixed_failure(mutation):
    args = arguments(); mutation(args)
    result = build_native_sheet(**args)
    assert result["status"] == "invalid" and result["value"] is None
    assert result["diagnostics"][0]["code"] == "supplied_contract_invalid"
    assert validate_proteome_sheet_data("NativeSheetResult", result) == result


@pytest.mark.parametrize("text,count", [("AA-?1", 5), ("", 0), ("aa*", 3), ("Aéß", 3)])
def test_complete_invalid_empty_and_stop_containing_sequences_keep_actual_counts(text, count):
    rows = native_rows(); rows[0]["ref_genome_aa_length"] = "77"
    args = linked_arguments(result=native(rows), ref_raw=(">R0\n" + text + "\n>R1\nCCCC\n>R2\nDDDD\n>R3\nEEEE\n").encode())
    sheet = build(args)
    row = sheet["reference_rows"][0]
    assert row["join_state"] == "joined"
    assert row["inventory_sequence_symbol_count"]["state"] == "value"
    assert row["inventory_sequence_symbol_count"]["value"] == count
    assert row["native_aa_length"]["value"] == 77
    assert row["coordinate_kind"] == "artificial_layout"
    assert sheet["tracks"][0]["input_record_count"]["value"] is None


def test_incomplete_identified_sequence_keeps_join_but_no_full_symbol_count():
    args = linked_arguments(ref_complete="unknown", sub_complete="unknown")
    sheet = build(args)
    assert sheet["reference_rows"][3]["join_state"] == "joined"
    assert sheet["reference_rows"][3]["inventory_sequence_symbol_count"]["state"] == "truncated"
    assert sheet["association_rows"][2]["subject_join_state"] == "joined"
    assert sheet["association_rows"][2]["inventory_subject_sequence_symbol_count"]["value"] is None
    assert sheet["reference_rows"][0]["inventory_sequence_symbol_count"]["value"] == 4
    assert any(r["code"] == "fasta_record_incomplete" and r["required_input"] == "complete_bytes" and
               r["scope"]["reference_row_ordinal"] == 3 for r in sheet["requirements"])


@pytest.mark.parametrize("text,count", [("AA-?1", 5), ("", 0)])
def test_complete_invalid_subject_count_is_not_its_published_protein_length(text, count):
    args = linked_arguments(sub_raw=(">S0\n" + text + "\n>S1\nFFFF\n").encode())
    sheet = build(args)
    for row in sheet["association_rows"][:2]:
        assert row["subject_join_state"] == "joined"
        assert row["inventory_subject_sequence_symbol_count"]["value"] == count
        assert row["native_subject_length_aa"]["value"] == 4


def test_duplicate_input_identifiers_keep_unresolved_occurrences_and_native_measurements():
    args = linked_arguments(ref_raw=b">R0\nAAAA\n>R0\nCCCC\n>R2\nDDDD\n>R3\nEEEE\n")
    joins = args["joins"]["reference_joins"]
    joins[0].update(state="ambiguous", protein=None, accepted_link_indices=[],
                    candidates=[{"inventory_key": "reference-input", "record_ordinal": i} for i in (0, 1)])
    joins[1].update(state="unmatched", protein=None, accepted_link_indices=[])
    sheet = build(args)
    assert sheet["inventories"][0]["observed_header_count"] == 4
    assert sheet["joins"]["reference_joins"][0]["candidates"] == joins[0]["candidates"]
    assert [r[IDENTITY]["value"] for r in sheet["association_rows"]] == [.875, 0, .625]
    track = calculate_native_components(sheet, parameters=parameters())["value"]["tracks"][0]
    assert track["observed_bound_reference_count"]["value"] == 1
    assert track["unresolved_reference_association_count"]["value"] == 2


def test_repeated_accepted_request_does_not_create_an_extra_occurrence_or_observation():
    args = linked_arguments()
    joins = args["joins"]
    joins["reference_joins"][0]["accepted_link_indices"].append(len(joins["requested_native_links"]))
    joins["requested_native_links"].append(deepcopy(joins["requested_native_links"][0]))
    sheet = build(args)
    assert sheet["joins"]["requested_native_links"] == joins["requested_native_links"]
    track = calculate_native_components(sheet, parameters=parameters())["value"]["tracks"][0]
    assert track["source_association_record_count"]["value"] == track["observed_bound_reference_count"]["value"] == 3


def test_rejected_wrong_source_digest_stays_a_raw_claim_and_preserves_other_joins():
    args = linked_arguments(); joins = args["joins"]
    bad = deepcopy(joins["requested_native_links"][0])
    bad["native"]["sha256"] = "0"*64
    joins["requested_native_links"].append(bad)
    joins["diagnostics"].append(diagnostic("identifier_mapping_conflict", track_key="ref_genome", reference_row_ordinal=0))
    joins["diagnostics"][-1]["path"] = f'/requested_native_links/{len(joins["requested_native_links"])-1}'
    sheet = build(args)
    assert sheet["joins"]["requested_native_links"][-1] == bad
    assert sheet["reference_rows"][0]["join_state"] == "joined"


@pytest.mark.parametrize("state", ["not_supplied", "unmatched", "ambiguous", "conflicting"])
def test_supplied_unresolved_join_outcomes_are_not_repaired(state):
    args = linked_arguments(); join = args["joins"]["subject_joins"][0]
    join.update(state=state, protein=None, accepted_link_indices=[])
    sheet = build(args)
    assert sheet["joins"] == args["joins"]
    row = sheet["association_rows"][0]
    assert row["subject_join_state"] == state and row["subject_protein"] is None
    assert row["inventory_subject_sequence_symbol_count"]["value"] is None
    assert row[IDENTITY]["value"] == .875


@pytest.mark.parametrize("mutation", [
    lambda a: a["joins"].update(primary_source_ref="wrong-source"),
    lambda a: a["joins"]["reference_joins"][0]["native"].update(sha256="0"*64),
    lambda a: a["joins"]["reference_joins"].append(deepcopy(a["joins"]["reference_joins"][0])),
    lambda a: a["joins"]["reference_joins"][0]["protein"].update(record_ordinal=99),
    lambda a: a["joins"]["track_bindings"][0]["input_record_count"].update(state="value", value=4),
    lambda a: a["joins"]["track_bindings"][0].update(execution_relation="exact_executed_fasta"),
    lambda a: a["joins"]["requested_native_links"][0].update(basis="producer_occurrence_mapping"),
    lambda a: a["inventories"][0]["records"][0].update(sequence_symbol_count=99),
])
def test_inconsistent_admitted_joins_and_forged_denominators_are_rejected(mutation):
    args = linked_arguments(); mutation(args)
    result = build_native_sheet(**args)
    assert result["status"] == "invalid" and result["value"] is None
    assert result["diagnostics"][0]["code"] in {"supplied_contract_invalid", "sheet_relationship_invalid"}


def test_locator_only_execution_claim_is_retained_without_an_executed_denominator():
    args = linked_arguments()
    link = args["joins"]["execution_links"][0]
    link.update(relation="exact_executed_fasta", membership_complete="yes",
                executed_fasta=deepcopy(args["inventories"][0]["source"]["content"]),
                witness_source_fields=[field(source(b"synthetic-locator", "witness-locator"))])
    args["joins"]["track_bindings"][0]["execution_relation"] = "unknown"
    sheet = build(args)
    assert sheet["joins"]["execution_links"][0] == link
    assert sheet["tracks"][0]["input_record_count"]["value"] is None


@pytest.mark.parametrize("bad", ["bad", None, "", True])
def test_bad_json_neighbor_does_not_erase_other_native_cells(bad):
    rows = native_rows(); rows[0]["comp_genome_2_aa_length"] = bad
    sheet = build(arguments(native(rows)))
    row = sheet["association_rows"][0]
    assert row[IDENTITY]["value"] == .875 and row[ENDPOINT]["value"] == .99
    assert row["layout_state"] == "source_field_located"
    assert not any(r["required_input"] == "complete_bytes" for r in sheet["requirements"])
    if bad in ("bad", True):
        assert any(d["code"] == "native_invalid_cell" for d in sheet["diagnostics"])
    result = calculate_native_components(sheet, parameters=parameters())
    assert result["value"]["tracks"][0]["first_hsp_identity_summary"]["mean"]["value"] == .5


def test_bad_fraction_does_not_erase_neighbor_and_zero_stays_a_value():
    rows = native_rows(); rows[0]["comp_genome_2_percent_identity"] = "bad"
    sheet = build(arguments(native(rows)))
    assert sheet["association_rows"][0][IDENTITY]["presence"] == "invalid"
    assert sheet["association_rows"][0][ENDPOINT]["value"] == .99
    assert sheet["association_rows"][1][IDENTITY]["lexeme"] == "0.000"
    result = calculate_native_components(sheet, parameters=parameters())["value"]
    assert result["tracks"][0]["first_hsp_identity_summary"]["mean"]["value"] == .3125
    assert result["tracks"][0]["first_hsp_identity_summary"]["invalid_count"]["value"] == 1


def test_missing_ids_limit_published_membership_without_erasing_located_json_fraction():
    rows = native_rows()
    rows[0].pop("ref_genome_patric_id"); rows[1].pop("comp_genome_2_patric_id")
    sheet = build(arguments(native(rows)))
    result = calculate_native_components(sheet, parameters=parameters())["value"]["tracks"][0]
    assert result["source_association_record_count"]["value"] == 3
    assert result["published_association_record_count"]["value"] == 1
    assert result["first_hsp_identity_summary"]["value_count"]["value"] == 3
    assert result["first_hsp_identity_summary"]["mean"]["value"] == .5


def test_wrong_width_tsv_retains_native_cells_but_excludes_semantic_numeric_use():
    headers = ["ref_genome_" + k for k in REF_FIELDS] + ["comp_genome_2_" + k for k in SUB_FIELDS]
    rows = native_rows()
    lines = ["\t".join(["ref"] + [""]*11 + ["comparison"] + [""]*9), "\t".join(headers)]
    lines += ["\t".join(row.get(k, "") for k in headers) + ("\textra" if i == 0 else "") for i, row in enumerate(rows)]
    raw = ("\n".join(lines) + "\n").encode()
    result = parser.parse_genome_comparison(raw, source=source(raw, "synthetic-malformed-table"),
        declared_format="genome_comparison_tsv_v1", source_contract=deepcopy(CONTRACT))
    sheet = build(arguments(result))
    assert sheet["association_rows"][0][IDENTITY]["value"] == .875
    assert sheet["association_rows"][0]["layout_state"] == "uncertain_table_layout"
    calculated = calculate_native_components(sheet, parameters=parameters())["value"]
    assert calculated["associations"][0]["first_hsp_alignment_identity_percent"]["value"] is None
    summary = calculated["tracks"][0]["first_hsp_identity_summary"]
    assert summary["layout_uncertain_count"]["value"] == 1
    assert summary["mean"]["value"] == .3125


def test_explicit_reordered_json_tsv_correspondence_equal_values_different_lexemes():
    left = native(extra_tracks=False)
    rows = native_rows()
    rows[0]["comp_genome_2_percent_identity"] = "8.750E-1"
    right = native([rows[2], rows[3], rows[0], rows[1]], key="synthetic-alt", fmt="tsv", extra_tracks=False)
    args = arguments(left); args["native_results"].append(right)
    args["representation_links"] = [representation(left, right, [2, 3, 0, 1])]
    sheet = build(args)
    assert sheet["representation_comparisons"][0]["state"] == "equal_observed_cells"
    assert sheet["association_rows"][0][IDENTITY]["lexeme"] == "0.875"
    assert sheet["native_results"][1]["value"]["associations"][1]["percent_identity"]["lexeme"] == "8.750E-1"
    result = calculate_native_components(sheet, parameters=parameters())
    assert result["value"]["tracks"][0]["source_association_record_count"]["value"] == 3


@pytest.mark.parametrize("case", ["conflict", "missing-value", "no-correspondence", "partial-source", "bad-row", "bad-association", "wrong-track", "wrong-reference", "mixed", "unknown-source"])
def test_representation_conflicts_and_unbound_mappings_preserve_primary(case):
    left = native(extra_tracks=False); rows = native_rows()
    if case in {"conflict", "mixed"}: rows[0]["comp_genome_2_percent_identity"] = ".900"
    if case == "missing-value": rows[0]["comp_genome_2_percent_identity"] = None
    if case == "wrong-track":
        rows[0].update({k.replace("comp_genome_2_", "comp_genome_9_"): v for k, v in list(rows[0].items()) if k.startswith("comp_genome_2_")})
    right = native(rows, key="synthetic-alt", complete="unknown" if case == "partial-source" else "yes", extra_tracks=False)
    link = representation(left, right)
    if case == "no-correspondence": link.update(reference_pairs=[], association_pairs=[])
    if case in {"bad-row", "mixed"}: link["reference_pairs"][3]["right_row_ordinal"] = 999
    if case == "bad-association": link["association_pairs"][0]["right_association_key"] = "comp_genome_2/row/999"
    if case == "wrong-track": link["association_pairs"][0]["right_association_key"] = "comp_genome_9/row/0"
    if case == "wrong-reference":
        link["association_pairs"][0]["right_association_key"], link["association_pairs"][1]["right_association_key"] = (
            link["association_pairs"][1]["right_association_key"], link["association_pairs"][0]["right_association_key"])
    if case == "unknown-source": link["right_source_ref"] = "not-supplied"
    args = arguments(left); args["native_results"].append(right); args["representation_links"] = [link]
    sheet = build(args)
    comparison = sheet["representation_comparisons"][0]
    expected = "conflicting" if case in {"conflict", "mixed"} else "incomplete_comparison" if case in {"missing-value", "no-correspondence", "partial-source"} else "unbound"
    assert comparison["state"] == expected
    assert comparison["link"] == link
    assert bool(comparison["conflict_source_fields"]) == (expected == "conflicting")
    assert sheet["association_rows"][0][IDENTITY]["value"] == .875
    assert sheet["native_results"] == args["native_results"]
    if case == "mixed":
        assert {d["code"] for d in comparison["diagnostics"]} >= {"representation_correspondence_missing", "representation_conflict"}


@pytest.mark.parametrize("case", ["self", "duplicate-link", "reverse-duplicate", "duplicate-ref", "duplicate-association", "extra-field", "boolean-ordinal"])
def test_malformed_representation_links_return_invalid(case):
    left = native(); right = native(key="synthetic-alt")
    args = arguments(left); args["native_results"].append(right)
    link = representation(left, right); args["representation_links"] = [link]
    if case == "self": link["right_source_ref"] = link["left_source_ref"]
    if case == "duplicate-link": args["representation_links"].append(deepcopy(link))
    if case == "reverse-duplicate":
        second = representation(right, left); args["representation_links"].append(second)
    if case == "duplicate-ref": link["reference_pairs"].append(deepcopy(link["reference_pairs"][0]))
    if case == "duplicate-association": link["association_pairs"].append(deepcopy(link["association_pairs"][0]))
    if case == "extra-field": link["guessed"] = True
    if case == "boolean-ordinal": link["reference_pairs"][0]["left_row_ordinal"] = False
    assert build_native_sheet(**args)["status"] == "invalid"


def test_empty_source_only_correspondence_does_not_claim_numeric_equality():
    left, right = native([], extra_tracks=False), native([], key="synthetic-empty-alt", extra_tracks=False)
    args = arguments(left); args["native_results"].append(right)
    args["representation_links"] = [representation(left, right)]
    sheet = build(args)
    assert sheet["representation_comparisons"][0]["state"] == "incomplete_comparison"
    assert sheet["reference_rows"] == sheet["association_rows"] == []


def test_primary_selection_uses_exact_caller_source_not_first_or_more_complete_file():
    rows = native_rows(); rows[0]["comp_genome_2_percent_identity"] = ".900"
    alternate = native(rows, key="synthetic-alternate")
    primary = native(complete="unknown")
    args = arguments(primary); args["native_results"].insert(0, alternate)
    sheet = build(args)
    assert sheet["association_rows"][0][IDENTITY]["value"] == .875
    assert sheet["native_results"][0] == alternate
    assert sheet["representation_comparisons"] == []
    assert any(r["code"] == "representation_correspondence_missing" for r in sheet["requirements"])


def metadata_args():
    args = linked_arguments()
    population = {"origin": "supplied_snapshot", "selected_fields": [], "query_source": None,
                  "offset": None, "requested_limit": None, "reported_total_count": None,
                  "population_complete": "unknown", "completeness_evidence": []}
    ref, sub = args["inventories"][0]["records"][0], args["inventories"][1]["records"][0]
    feature_values = [{"feature_id": "S0", "genome_id": "G", "product": "subject function",
                       "aa_sequence_md5": sub["sequence_md5"], "aa_length": "invalid neighbor"},
                      {"patric_id": "R0", "genome_id": "G", "product": "reference function",
                       "aa_sequence_md5": ref["sequence_md5"], "start": 1, "end": 12, "strand": "+"}]
    for kind, values, reader, fmt in (
        ("feature", feature_values, inputs.read_feature_metadata, "bvbrc_genome_feature_json_array_v1"),
        ("genome", [{"genome_id": "G", "taxon_id": 7}], inputs.read_genome_metadata, "bvbrc_genome_json_array_v1"),
        ("sequence", [{"md5": sub["sequence_md5"], "sequence": "FFFF"}, {"md5": ref["sequence_md5"], "sequence": "AAAA"}],
         inputs.read_feature_sequences, "bvbrc_feature_sequence_json_array_v1"),
    ):
        raw = json.dumps(values).encode(); src = source(raw, "synthetic-" + kind)
        options = {"coordinate_convention": {"value": "one_based_closed", "source_fields": [field(source(b"one based closed", "convention-source"))]}} if kind == "feature" else {}
        result = reader(raw, source=src, declared_format=fmt, snapshot_key=kind + "-snapshot", population=population, **options)
        args[kind + "_snapshots"] = [result["value"]]
    links = []
    for i, inv in enumerate(("subject-input", "reference-input")):
        links.append({"protein": {"inventory_key": inv, "record_ordinal": 0},
                      "feature": {"snapshot_key": "feature-snapshot", "row_ordinal": i},
                      "genome": {"snapshot_key": "genome-snapshot", "row_ordinal": 0},
                      "feature_sequence": {"snapshot_key": "sequence-snapshot", "row_ordinal": i},
                      "basis": "exact_feature_identifier", "mapping_source_fields": []})
    args["joins"]["requested_metadata_links"] = deepcopy(links)
    # Reverse joined-result array order independently of raw link_index.
    args["joins"]["metadata_joins"] = [{k: deepcopy(v) for k, v in links[i].items() if k not in {"basis", "mapping_source_fields"}} |
                                      {"state": "joined", "link_index": i, "diagnostics": []} for i in (1, 0)]
    return args


def test_metadata_indices_address_join_array_positions_and_all_snapshots_survive():
    args = metadata_args(); sheet = build(args)
    assert sheet["reference_rows"][0]["metadata_links"] == [0]
    assert sheet["association_rows"][0]["metadata_links"] == sheet["association_rows"][1]["metadata_links"] == [1]
    assert sheet["joins"]["metadata_joins"][0]["link_index"] == 1
    assert args["feature_snapshots"][0]["records"][0]["valid"] is False
    for key in ("input_index", "inventories", "feature_snapshots", "genome_snapshots", "sequence_snapshots", "joins"):
        assert sheet[key] == args[key]


def test_separate_source_assignments_keep_separate_metadata_array_positions():
    args = metadata_args()
    original = args["feature_snapshots"][0]
    raw = b'[{"feature_id":"S0","product":"another supplied assignment"}]'
    snapshot = inputs.read_feature_metadata(raw, source=source(raw, "synthetic-other-feature"),
        declared_format="bvbrc_genome_feature_json_array_v1", snapshot_key="other-feature-snapshot",
        population=original["population"], coordinate_convention={"value": "unknown", "source_fields": []})["value"]
    args["feature_snapshots"].append(snapshot)
    link = deepcopy(args["joins"]["requested_metadata_links"][0])
    link.update(feature={"snapshot_key": "other-feature-snapshot", "row_ordinal": 0}, genome=None, feature_sequence=None)
    args["joins"]["requested_metadata_links"].append(link)
    args["joins"]["metadata_joins"].append({k: deepcopy(v) for k, v in link.items() if k not in {"basis", "mapping_source_fields"}} |
                                          {"link_index": 2, "state": "joined", "diagnostics": []})
    sheet = build(args)
    assert sheet["association_rows"][0]["metadata_links"] == [1, 2]
    assert [s["records"][0]["product"]["value"] for s in sheet["feature_snapshots"]] == ["subject function", "another supplied assignment"]


def test_unresolved_metadata_link_is_retained_but_not_indexed_as_joined():
    args = metadata_args()
    join = args["joins"]["metadata_joins"][1]
    join.update(state="conflicting", feature=None, genome=None, feature_sequence=None)
    sheet = build(args)
    assert sheet["joins"] == args["joins"]
    assert sheet["association_rows"][0]["metadata_links"] == []
    assert sheet["reference_rows"][0]["metadata_links"] == [0]


def test_coordinate_kind_requires_explicit_input_and_relevant_bound_metadata():
    args = metadata_args()
    args["input_index"] = index(kind="genome_id")
    for binding in args["joins"]["track_bindings"]:
        binding["input_key"] = binding["input_key"].replace("user_genomes", "genome_ids")
    for link in args["joins"]["execution_links"]:
        link["input_key"] = link["input_key"].replace("user_genomes", "genome_ids")
    sheet = build(args)
    assert sheet["reference_rows"][0]["coordinate_kind"] == "genomic_metadata"
    assert sheet["reference_rows"][1]["coordinate_kind"] == "unknown"
    args["feature_snapshots"][0]["coordinate_convention"] = {"value": "unknown", "source_fields": []}
    assert build(args)["reference_rows"][0]["coordinate_kind"] == "unknown"


def test_empty_complete_projection_and_unavailable_directional_attachment_are_distinct():
    args = arguments(native([], extra_tracks=False))
    args["directional_attachment"] = {"version": "bvbrc_proteome_directional_attachment_proposal_v1", "state": "unavailable",
        "expected_scopes": [{"comparison_track_key": "comp_genome_2", "direction": "reference_to_comparison"}],
        "reports": [], "operand_links": [],
        "requirements": [{"code": "directional_report_missing", "required_input": "directional_report", "scope": scope(track_key="comp_genome_2"), "source_fields": []}],
        "diagnostics": []}
    sheet = build(args)
    assert sheet["reference_rows"] == sheet["association_rows"] == []
    assert sheet["directional_attachment"] == args["directional_attachment"]
    assert sheet["tracks"][0]["input_record_count"]["value"] is None
    calculated = calculate_native_components(sheet, parameters=parameters())["value"]["tracks"][0]
    assert calculated["source_association_record_count"]["value"] == 0
    assert calculated["first_hsp_identity_summary"]["sum"]["value"] == 0
    assert calculated["first_hsp_identity_summary"]["mean"]["state"] == "not_applicable"
    args["directional_attachment"]["state"] = "complete_emitted_reports"
    assert build_native_sheet(**args)["status"] == "invalid"


def test_sheet_construction_and_recalculation_make_no_io_parser_or_join_calls(monkeypatch):
    from gene_annotation_episode import bvbrc_proteome_joins as joins
    args = metadata_args(); expected = build(args)
    calculate_native_components(expected, parameters=parameters())  # warm packaged schemas

    def forbidden(*a, **kw):
        raise AssertionError("pure construction attempted acquisition, parsing or execution")

    with monkeypatch.context() as patch:
        for name in ("read_protein_fasta", "read_feature_metadata", "read_feature_sequences", "read_genome_metadata", "index_original_inputs"):
            patch.setattr(inputs, name, forbidden)
        patch.setattr(parser, "parse_genome_comparison", forbidden)
        patch.setattr(joins, "build_native_joins", forbidden)
        patch.setattr(builtins, "open", forbidden)
        for name in ("open", "read_text", "read_bytes", "write_text", "write_bytes"):
            patch.setattr(Path, name, forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        result = build_native_sheet(**args)
        assert result["value"] == expected
        calculated = calculate_native_components(result["value"], parameters=parameters(.9))
        assert calculated["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0

