"""Real A/B1/B2/B3/B4 composition over explicitly synthetic supplied bytes.

This is the pure data path, not API custody or complete episode integration.
"""
from copy import deepcopy
from fractions import Fraction
import io
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_proteome_calculators as calculators
from gene_annotation_episode import bvbrc_proteome_inputs as inputs
from gene_annotation_episode import bvbrc_proteome_joins as joins
from gene_annotation_episode import bvbrc_proteome_native as native
from gene_annotation_episode import bvbrc_proteome_sheet as sheets
from test_bvbrc_proteome_joins import case, fasta, metadata_case, native_result


def parameters(**changes):
    return {"version": "bvbrc_proteome_native_parameters_proposal_v1", "track_keys": ["comp_genome_2"],
            "minimum_identity_fraction": .6, "minimum_subject_endpoint_difference_fraction": .7,
            "allowed_hit_categories": None, **changes}


def constructed(data):
    original = deepcopy(data)
    links = joins.build_native_joins(**data)
    assert links["value"] is not None
    result = native_result()
    assert result["value"] == data["native"]
    sheet = sheets.build_native_sheet([result], primary_source_ref=result["value"]["source"]["content"]["source_ref"],
        **{name: data[name] for name in ("input_index", "inventories", "feature_snapshots", "genome_snapshots", "sequence_snapshots")},
        joins=links["value"], representation_links=[])
    assert sheet["value"] is not None, sheet["diagnostics"]
    assert data == original
    return links, sheet


def test_parsed_bytes_reach_numerical_sheet_and_replaceable_calculator():
    data = metadata_case()
    links, envelope = constructed(data)
    sheet = envelope["value"]
    before = deepcopy(sheet)
    first = calculators.calculate_native_components(sheet, parameters=parameters())
    assert first["value"] is not None, first["diagnostics"]
    track = first["value"]["tracks"][0]
    assert track["first_hsp_identity_summary"]["mean"]["value"] == float(Fraction(7, 16))
    assert track["subject_endpoint_difference_summary"]["mean"]["value"] == float(Fraction(5, 8))
    assert [a["first_hsp_alignment_identity_percent"]["value"] for a in first["value"]["associations"]] == [87.5, 0]
    assert track["observed_bound_reference_count"]["value"] == track["observed_bound_subject_count"]["value"] == 2
    assert track["demonstrated_subject_sequence_group_count"]["value"] == 2
    assert track["selection_counts"]["pass"]["value"] == track["selection_counts"]["fail"]["value"] == 1
    assert track["reference_input_record_count"]["value"] is None
    assert track["complete_published_reference_fraction"]["fraction"]["value"] is None
    assert sheet["reference_rows"][0]["metadata_links"] == [0]
    assert sheet["reference_rows"][1]["metadata_links"] == []
    assert sheet["joins"] == links["value"]
    changed = calculators.calculate_native_components(sheet, parameters=parameters(minimum_identity_fraction=.9))
    assert changed["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
    assert changed["value"]["tracks"][0]["selection_counts"]["fail"]["value"] == 2
    assert changed["value"]["sheet_sha256"] == first["value"]["sheet_sha256"]
    assert first["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 1
    assert sheet == before


@pytest.mark.parametrize("raw,complete,count", [(b">r1\nAA-?1\n", True, 5), (b">r1\n", True, 0), (b">r1\nAC", False, None)])
def test_identified_invalid_or_partial_input_never_turns_into_execution_denominator(raw, complete, count):
    data = case()
    data["inventories"][0] = fasta("ref", raw, complete=complete)
    _, envelope = constructed(data)
    sheet = envelope["value"]
    assert sheet["reference_rows"][0]["join_state"] == "joined"
    cell = sheet["reference_rows"][0]["inventory_sequence_symbol_count"]
    assert cell["value"] == count
    assert (cell["state"] == "value") is (count is not None)
    result = calculators.calculate_native_components(sheet, parameters=parameters())
    assert result["value"] is not None, result["diagnostics"]
    assert result["value"]["tracks"][0]["reference_input_record_count"]["value"] is None
    assert result["value"]["tracks"][0]["unresolved_reference_association_count"]["value"] == 1


def test_rejected_wrong_digest_does_not_erase_neighboring_numeric_information():
    data = case()
    data["native_links"][0]["native"]["sha256"] = "0" * 64
    _, envelope = constructed(data)
    sheet = envelope["value"]
    assert sheet["reference_rows"][0]["join_state"] == "conflicting"
    assert sheet["reference_rows"][1]["join_state"] == "joined"
    result = calculators.calculate_native_components(sheet, parameters=parameters())
    assert result["value"] is not None, result["diagnostics"]
    track = result["value"]["tracks"][0]
    assert track["first_hsp_identity_summary"]["mean"]["value"] == .4375
    assert track["observed_bound_reference_count"]["value"] == 1
    assert track["unresolved_reference_association_count"]["value"] == 1
    assert sheet["joins"]["requested_native_links"][0]["native"]["sha256"] == "0" * 64


def test_saved_sheet_recalculation_forbids_reconstruction_parsing_acquisition_and_execution(monkeypatch):
    _, envelope = constructed(metadata_case())
    sheet = envelope["value"]
    expected = calculators.calculate_native_components(sheet, parameters=parameters())
    before = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved calculation attempted fresh construction or external work")
    with monkeypatch.context() as patch:
        for owner, name in ((Path, "read_text"), (Path, "read_bytes"), (io, "open"), (socket, "socket"),
                            (subprocess, "run"), (subprocess, "Popen"), (native, "parse_genome_comparison"),
                            (joins, "build_native_joins"), (sheets, "build_native_sheet")):
            patch.setattr(owner, name, forbidden)
        patch.setattr("builtins.open", forbidden)
        for name in ("read_protein_fasta", "read_feature_metadata", "read_genome_metadata", "read_feature_sequences", "index_original_inputs"):
            patch.setattr(inputs, name, forbidden)
        assert calculators.calculate_native_components(sheet, parameters=parameters()) == expected
        changed = calculators.calculate_native_components(sheet, parameters=parameters(minimum_identity_fraction=.9))
    assert changed["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
    assert sheet == before
