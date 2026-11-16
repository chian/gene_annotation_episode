"""B1 parsing tests: retained native 259 data and labelled synthetic errors."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_alignment_preparation_data import ISSUE_CODES, ROW_FIELDS, populate_hmmer_alignment_preparation_sheet
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_model_data import extract_hmmer_models

ROOT = Path(__file__).resolve().parents[5]
NATIVE = ROOT / "gene_annotation_episode/episodic_workflow/root/a101/tests/fixtures/hmmer_preparation_contracts"


def payload(role, content, direction="input", ordinal=0, oid=None):
    occurrence = {"occurrence_id": oid or f"{direction}:{role}:{ordinal}", "direction": direction,
        "role": role, "ordinal": ordinal, "artifact_ref": "retained:" + role + ":" + str(ordinal),
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content), "completeness": "complete"}
    return {"occurrence": occurrence, "content": content}


def operation(program="alimask", mode="mask_alignment", **settings):
    return {"program": program, "mode": mode, "engine_version": "3.4", "settings": settings}


def mask_sheet(content, output=None, *, mode="mask_alignment", stdout=None, **settings):
    selected = operation(mode=mode, **settings)
    outputs = {}
    if output is not None:
        outputs["masked_alignment"] = [payload("masked_alignment", output, "output")]
    if stdout is not None:
        outputs["stdout"] = [payload("stdout", stdout, "output")]
    return populate_hmmer_alignment_preparation_sheet(operation=selected,
        inputs={"alignment": [payload("alignment", content)]}, outputs=outputs)


def test_native_all_four_alimask_modes():
    cases = [("alignment", "mask_alignment", "--alirange", "2-4,4-6"), ("model", "mask_model", "--modelrange", "2-4"),
             ("model2ali", "model_to_alignment", "--model2ali", "2-4"), ("ali2model", "alignment_to_model", "--ali2model", "2-4")]
    source = (NATIVE / "inputs/protein.sto").read_bytes()
    for case, mode, flag, value in cases:
        directory = NATIVE / "native" / ("alimask_" + case)
        output = (directory / "masked.sto").read_bytes() if mode.startswith("mask_") else None
        sheet = mask_sheet(source, output, mode=mode, stdout=(directory / "stdout.log").read_bytes(), **{flag: value, "--hand": True, "--amino": True})
        assert not sheet["issues"]
        assert all(set(row) == ROW_FIELDS[row["kind"]] for row in sheet["native_rows"])


def test_ali2model_preserves_adjusted_endpoints_and_no_map():
    source = b"# STOCKHOLM 1.0\na ABCDEF\n#=GC RF .x..x.\n//\n"
    stdout = b"alignment coordinates     model coordinates\n 2..5 -> 1..2\n 3..4 -> -..-  (no map)\n"
    sheet = mask_sheet(source, mode="alignment_to_model", stdout=stdout, **{"--ali2model": "1-6,3-4", "--hand": True})
    rows = [r for r in sheet["native_rows"] if r["kind"] == "mapping"]
    assert (rows[0]["requested_start"], rows[0]["requested_end"]) == (1, 6)
    assert (rows[0]["returned_source_start"], rows[0]["returned_source_end"]) == (2, 5)
    assert rows[1]["native_state"] == "no_map" and rows[1]["target_start"] is None
    assert [row["locator"]["record_ordinal"] for row in rows] == [0, 1]


# AFA keeps unknown alphabet inference; DNA selects the partial Stockholm reader.
@pytest.mark.parametrize("content,settings", [(b">a\nACGT\n", {"--informat": "afa"}), (b"# STOCKHOLM 1.0\na ACGT\n", {"--dna": True})])
def test_unsupported_and_partial_are_not_empty_success(content, settings):
    sheet = mask_sheet(content, **{"--alirange": "1-1", **settings})
    population = next(r for r in sheet["native_rows"] if r["kind"] == "population")
    assert not population["complete"]
    if settings.get("--informat") == "afa":
        assert population["decoded_count"] is None and population["state"] == "unsupported"
    else:
        assert population["decoded_count"] == 1 and population["state"] == "partial"


def test_first_record_only_and_bad_utf8_tail_preserve_valid_prefix():
    source = b"# STOCKHOLM 1.0\na AC\n//\n"
    sheet = mask_sheet(source + source + b"\xffignored", **{"--alirange": "1-1", "--dna": True})
    assert len(sheet["input_records"]) == 2
    assert [a["relation"] for a in sheet["associations"]] == ["mask", "unprocessed"]
    assert {"first_record_only", "text_encoding_invalid"} <= {i["code"] for i in sheet["issues"]}


def test_invalid_payload_and_repeated_ids_do_not_throw_or_merge():
    value = payload("alignment", b"# STOCKHOLM 1.0\na AC\n//\n")
    sheet = populate_hmmer_alignment_preparation_sheet(operation=operation(**{"--alirange": "1-1", "--dna": True}),
        inputs={"alignment": [value, deepcopy(value), {"content": b"bad", "occurrence": {}}]}, outputs={})
    assert {"occurrence_duplicate", "occurrence_invalid"} <= {i["code"] for i in sheet["issues"]}
    assert len(sheet["input_records"]) == 1
    assert populate_hmmer_alignment_preparation_sheet(operation={"program": []}, inputs={}, outputs={})["issues"][0]["code"] == "operation_invalid"


def test_identical_bytes_in_different_input_occurrences_remain_distinct():
    content = b"# STOCKHOLM 1.0\na AC\n//\n"
    first, second = payload("alignment", content), payload("alignment", content, ordinal=1)
    sheet = populate_hmmer_alignment_preparation_sheet(operation=operation(**{"--alirange": "1-1", "--dna": True}),
        inputs={"alignment": [first, second]}, outputs={})
    assert len(sheet["artifact_occurrences"]) == len(sheet["input_records"]) == 2
    assert len({r["record_key"] for r in sheet["input_records"]}) == 2
    assert not sheet["associations"]  # A native single operand cannot be guessed.
    assert "role_cardinality_invalid" in {i["code"] for i in sheet["issues"]}


