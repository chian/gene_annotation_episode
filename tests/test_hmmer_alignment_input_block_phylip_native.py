"""Six-format native conformance; execute only in root's bounded lifecycle.

Reuse packet 539's original-source observer/build fixture. Importing its fixture
and helpers does not select its completed classifier/scanner/AFA/A2M tests.
No producer rerun, alternative numerical formula, or integrated-return claim is
made here. Authored cases and unchanged retained inputs are pinned in packet 543.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_alignment_input_blocks import decode_native_block_alignment
from gene_annotation_episode.hmmer_alignment_input_phylip import decode_native_phylip_alignment
from gene_annotation_episode.hmmalign_inputs import stockholm_digital_checksum
from test_hmmer_alignment_input_native_oracle import (
    _canonical,
    _fixture_bytes,
    _hex,
    _write_json,
    native_observer,
)


_REPO = Path(__file__).resolve().parents[1]
_PACKET = _REPO / "verification/tool_graders_hmmer_input_block_phylip_native_2026-10-28_543"
_MANIFEST = json.loads((_PACKET / "CASES.json").read_text())
_FORMATS = {"psiblast", "selex", "clustal", "clustallike", "phylip", "phylips"}


@pytest.fixture(scope="module")
def pinned_case_manifest():
    cases = _MANIFEST["cases"]
    assert len(cases) == _MANIFEST["expected_native_comparison_count"]
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["format"] for case in cases} == _FORMATS
    for case in cases:
        assert case["native_oracle_eligible"] is True
        assert case["source_expected_status"] in (0, 3, 7)
        assert case["alphabet"] in ("amino", "DNA", "RNA")
        assert case["native_record_scope"] in ("single_record", "first_record_only")
        assert case["row_comparison_scope"] in ("whole_rows", "native_alen_prefixes")
        if case["row_comparison_scope"] == "native_alen_prefixes":
            assert case["source_expected_geometry"] == "invalid"
            assert case["format"] == "phylips"
            assert case["source_expected_status"] == 0
    for pin in _MANIFEST["provenance_pins"]:
        path = (_REPO / pin["path"]).resolve(strict=True)
        assert path.is_relative_to(_REPO)
        payload = path.read_bytes()
        assert len(payload) == pin["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == pin["sha256"], pin["path"]


def _annotation_text(container, tag):
    annotation = container["column_annotations"].get(tag)
    return None if annotation is None else annotation["text"]


def _compare_annotations(record, native):
    for tag in ("RF", "MM", "SS_cons", "SA_cons", "PP_cons"):
        assert _hex(_annotation_text(record, tag)) == native["annotations"][tag + "_hex"]
    for row, observed in zip(record["rows"], native["rows"]):
        for tag in ("SS", "SA", "PP"):
            assert _hex(_annotation_text(row, tag)) == observed[tag + "_hex"]
        assert observed["accession_hex"] is None
    assert all(value is None for value in native["metadata"].values())
    assert native["unparsed_gc"] == native["unparsed_gr"] == []


def _check_source_expectations(decoded, case, content):
    """Expected byte cursors/partial facts are source checks, not native outputs."""
    checks = case["python_checks"]
    for key in ("end_state", "next_byte_offset"):
        if key in checks:
            assert decoded[key] == checks[key]
    for key, field in (("record_states", "reader_state"), ("record_statuses", "native_status_equivalent")):
        if key in checks:
            assert [record[field] for record in decoded["records"]] == checks[key]
    if "record_count" in checks:
        assert len(decoded["records"]) == checks["record_count"]
    if not decoded["records"]:
        return
    first = decoded["records"][0]
    for key in ("column_count", "declared_column_count", "block_count"):
        if key in checks:
            assert first[key] == checks[key]
    if "first_record_end_byte" in checks:
        assert first["byte_end"] == checks["first_record_end_byte"]
    if "rows" in checks:
        assert [row["aligned_sequence"] for row in first["rows"]] == checks["rows"]
    if "names" in checks:
        assert [row["name"] for row in first["rows"]] == checks["names"]
    for tag, expected in checks.get("annotations", {}).items():
        assert _annotation_text(first, tag) == expected
    for tag, expected in checks.get("first_row_annotations", {}).items():
        assert _annotation_text(first["rows"][0], tag) == expected
    if "consensus_event_count" in checks:
        assert sum(event["kind"] == "consensus" for event in first["events"]) == checks["consensus_event_count"]
    if "diagnostic_code" in checks:
        assert checks["diagnostic_code"] in {entry["code"] for entry in first["diagnostics"]}
    # Even rejected native records keep the actual inspected Python events.
    # No attempt is made to compare these to a native MSA destroyed on failure.
    for record in decoded["records"]:
        for event in record["events"]:
            locator = event["locator"]
            assert event["raw"].encode("utf-8", "surrogateescape") == content[locator["byte_start"]:locator["byte_end"]]
    if decoded["trailing_range"] is not None:
        assert decoded["trailing_range"] == {
            "byte_start": decoded["next_byte_offset"], "byte_end": len(content),
        }


@pytest.mark.parametrize("case", _MANIFEST["cases"], ids=lambda case: case["id"])
def test_six_format_native_read_conformance(native_observer, pinned_case_manifest, case):
    directory = native_observer.case("block_phylip", case)
    content, input_path = _fixture_bytes(case, directory)
    native = native_observer.call(["read", case["format"], case["alphabet"], input_path], directory)
    assert native["open_status"] == 0
    assert native["status"] == native["read_status"] == case["source_expected_status"]
    assert native["selected_alphabet"] == case["alphabet"]
    assert native["classifier_calls"] == []
    for key, expected in case["native_checks"].items():
        assert native[key] == expected

    decoder = (decode_native_phylip_alignment if case["format"] in {"phylip", "phylips"}
               else decode_native_block_alignment)
    decoded = decoder(content, declared_format=case["format"], alphabet=case["alphabet"])
    _write_json(directory / "python_result.json", decoded)
    _check_source_expectations(decoded, case, content)
    comparison = {
        "status": "passed",
        "comparison": "actual_native_open_read_digital_rows_names_annotations_and_shared_checksum",
        "native_record_scope": case["native_record_scope"],
        "row_comparison_scope": case["row_comparison_scope"],
        "byte_cursor_evidence": "source_checks_only_observer_has_no_byte_cursor",
        "later_records_compared_to_native": False,
        "valid_alignment": False,
    }
    if native["read_status"] == 3:
        assert decoded["records"] == [] and decoded["end_state"] == "eof"
        assert native["rows"] == [] and native["nseq"] is native["alen"] is None
        assert native["annotations"] is native["checksum_status"] is None
        comparison["comparison"] = "actual_native_eof_without_alignment"
    elif native["read_status"] == 7:
        assert decoded["end_state"] == "parse_error"
        assert len(decoded["records"]) == 1
        assert decoded["records"][0]["native_status_equivalent"] == 7
        assert decoded["records"][0]["reader_state"] != "complete"
        assert native["rows"] == [] and native["nseq"] is native["alen"] is None
        assert native["annotations"] is native["checksum_status"] is None
        assert native["error_hex"]
        comparison["comparison"] = "actual_native_failure_no_native_partial_rows"
    else:
        assert native["read_status"] == 0
        assert decoded["records"]
        record = decoded["records"][0]  # observer performs exactly one native Read
        if case["native_record_scope"] == "single_record":
            assert len(decoded["records"]) == 1 and decoded["end_state"] == "eof"
        assert record["native_status_equivalent"] == 0
        assert record["reader_state"] == case["source_expected_geometry"]
        assert record["column_count"] == native["alen"]
        assert len(record["rows"]) == native["nseq"]
        assert [row["row_ordinal"] for row in record["rows"]] == [row["ordinal"] for row in native["rows"]]
        assert [row["name_bytes_hex"] for row in record["rows"]] == [row["name_hex"] for row in native["rows"]]
        assert [_hex(row["description"]) for row in record["rows"]] == [row["description_hex"] for row in native["rows"]]
        assert all(row["symbols_valid"] and row["identity_unambiguous"] for row in record["rows"])
        if record["reader_state"] == "complete":
            assert all(row["geometry_valid"] for row in record["rows"])
            comparison["valid_alignment"] = True
        else:
            assert not all(row["geometry_valid"] for row in record["rows"])
            assert any(entry["code"] == "column_count_mismatch" for entry in record["diagnostics"])
        _compare_annotations(record, native)

        digital = _canonical(record["rows"], case["alphabet"])
        raw_rows = [row["aligned_sequence"] for row in record["rows"]]
        checksum_scope = "whole_first_record_rows"
        if case["row_comparison_scope"] == "native_alen_prefixes":
            # This selected short-last-row case initializes every observed byte.
            # Keep the complete unequal Python rows; never pad or silently claim
            # that the observer exposed the longer row's undisplayed suffix.
            assert native["alen"] > 0
            assert len({len(row) for row in digital}) > 1
            assert all(len(row) >= native["alen"] for row in digital)
            with pytest.raises(ValueError, match="^hmmalign_checksum_row_geometry_invalid$"):
                stockholm_digital_checksum(raw_rows, alphabet=case["alphabet"])
            digital = [row[:native["alen"]] for row in digital]
            raw_rows = [row[:native["alen"]] for row in raw_rows]
            checksum_scope = "observer_visible_prefixes_only_invalid_alignment"
        assert digital == [row["digital"] for row in native["rows"]]
        assert native["checksum_status"] == 0
        checksum = stockholm_digital_checksum(raw_rows, alphabet=case["alphabet"])
        assert checksum == native["native_checksum_uint32"]
        _write_json(directory / "shared_checksum.json", {
            "shared_checksum": checksum, "scope": checksum_scope,
            "valid_alignment": comparison["valid_alignment"],
        })
    _write_json(directory / "comparison.json", comparison)
