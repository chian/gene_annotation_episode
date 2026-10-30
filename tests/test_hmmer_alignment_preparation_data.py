"""B1 parsing tests: retained native 259 data and labelled synthetic errors."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_alignment_preparation_data import (
    ISSUE_CODES, ROW_FIELDS, populate_hmmer_alignment_preparation_sheet,
)
from gene_annotation_episode.hmmer_model_data import extract_hmmer_models

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259"


def payload(role, content, direction="input", ordinal=0, oid=None):
    occurrence = {"occurrence_id": oid or f"{direction}:{role}:{ordinal}", "direction": direction,
        "role": role, "ordinal": ordinal, "artifact_ref": "retained:" + role + ":" + str(ordinal),
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content), "completeness": "complete"}
    return {"occurrence": occurrence, "content": content}


def operation(program="alimask", mode="mask_alignment", **settings):
    return {"program": program, "mode": mode, "engine_version": "3.4", "settings": settings}


def native_build(case="protein"):
    directory = NATIVE / "native" / ("hmmbuild_" + case)
    input_name = {"singlemx": "protein_single", "annotated": "protein_annotated"}.get(case, case)
    inputs = {"alignment": [payload("alignment", (NATIVE / "inputs" / (input_name + ".sto")).read_bytes())]}
    outputs = {"models": [payload("models", (directory / "profile.hmm").read_bytes(), "output")],
               "stdout": [payload("stdout", (directory / "stdout.log").read_bytes(), "output")]}
    if (directory / "resaved.sto").exists():
        outputs["resaved_alignment"] = [payload("resaved_alignment", (directory / "resaved.sto").read_bytes(), "output")]
    argv = json.loads((directory / "intent.json").read_text())["argv"][1:-2]
    settings = {}
    index = 0
    values = {"--cpu", "--seed", "-o", "-O", "--informat", "--symfrac", "--fragthresh", "--wid", "--mxfile"}
    while index < len(argv):
        flag = argv[index]
        if flag in values:
            value = argv[index + 1]
            settings[flag] = int(value) if flag in {"--cpu", "--seed"} else float(value) if flag in {"--symfrac", "--fragthresh", "--wid"} else value
            index += 2
        else:
            settings[flag] = True
            index += 1
    selected = operation("hmmbuild", "build_single_sequence_matrix" if case == "singlemx" else "build_alignment", **settings)
    model = outputs["models"][0]
    extraction = extract_hmmer_models(model["content"], occurrence=model["occurrence"], format="hmmer3_ascii")
    return selected, inputs, outputs, extraction


def build_sheet(case="protein"):
    selected, inputs, outputs, extraction = native_build(case)
    return populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)


def mask_sheet(content, output=None, *, mode="mask_alignment", stdout=None, **settings):
    selected = operation(mode=mode, **settings)
    outputs = {}
    if output is not None:
        outputs["masked_alignment"] = [payload("masked_alignment", output, "output")]
    if stdout is not None:
        outputs["stdout"] = [payload("stdout", stdout, "output")]
    return populate_hmmer_alignment_preparation_sheet(operation=selected,
        inputs={"alignment": [payload("alignment", content)]}, outputs=outputs)


@pytest.mark.parametrize("case", ["protein", "dna", "rna", "annotated", "singlemx"])
def test_retained_native_build_complete_shapes(case):
    sheet = build_sheet(case)
    assert sheet["schema"] == "hmmer_alignment_preparation_sheet_v1"
    assert sheet["associations"][0]["status"] == "validated"
    assert sheet["model_extraction"]["population"]["complete"]
    assert len(sheet["model_extraction"]["records"][0]["positions"]) == 12
    assert all(issue["code"] in ISSUE_CODES for issue in sheet["issues"])
    for row in sheet["native_rows"]:
        assert set(row) == ROW_FIELDS[row["kind"]]
        if row["kind"] == "build_summary":
            assert row["locator"]["record_ordinal"] == 0
    source = sheet["input_records"][0]
    assert "".join(event["raw"] for event in source["original_events"]).encode() == native_build(case)[1]["alignment"][0]["content"]
    assert source["locator"]["byte_end"] == native_build(case)[1]["alignment"][0]["occurrence"]["size_bytes"]


def test_singlemx_distinct_model_name_and_empty_selected_resaved():
    selected, inputs, outputs, extraction = native_build("singlemx")
    selected["settings"]["-O"] = "selected.sto"
    outputs["resaved_alignment"] = [payload("resaved_alignment", b"", "output")]
    sheet = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    summary = next(row for row in sheet["native_rows"] if row["kind"] == "build_summary")
    assert summary["name"] == "single_protein"
    assert extraction["records"][0]["headers"][0]["value"] == "single"
    assert sheet["associations"][0]["status"] == "validated"
    assert sheet["associations"][0]["resaved_record_key"] is None
    assert "resaved_alignment_empty" in {issue["code"] for issue in sheet["issues"]}


def test_source_resaved_distinct_coordinates_and_gs_gr_events():
    sheet = build_sheet()
    assert sheet["input_records"][0]["column_count"] == 14
    assert next(r for r in sheet["output_records"] if r["kind"] == "alignment")["column_count"] == 12
    source = b"# STOCKHOLM 1.0\n#=GF ID duplicates\n#=GS same WT 1.0\nsame Ac.\nsame aG-\n#=GR same PP 99.\n#=GR same PP 98.\n#=GC RF xx.\n\nsame dE\nsame dF\n#=GR same PP 99\n#=GR same PP 98\n#=GC RF xx\n//\n"
    row = mask_sheet(source, **{"--alirange": "1-1", "--amino": True})["input_records"][0]
    assert [r["aligned_sequence"] for r in row["rows"]] == ["Ac.dE", "aG-dF"]
    assert [r["occurrence"] for r in row["rows"]] == [0, 1]
    assert len({r["record_key"] for r in row["rows"]}) == 2
    assert row["rows"][0]["column_annotations"]["PP"]["text"] == "99.99"
    assert row["rows"][0]["weight"]["state"] == "incompatible"


def test_custody_mismatch_and_supplied_arrays_cannot_rebind():
    selected, inputs, outputs, extraction = native_build()
    inputs["alignment"][0]["occurrence"]["sha256"] = "0" * 64
    sheet = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    assert sheet["associations"][0]["status"] == "conflicting"
    assert "occurrence_digest_mismatch" in {i["code"] for i in sheet["issues"]}
    forged = deepcopy(extraction)
    forged["records"][0]["positions"][0]["match"]["cells"][0]["probability"] = .123
    rejected = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=forged)
    assert rejected["model_extraction"] is None
    assert "model_extraction_mismatch" in {i["code"] for i in rejected["issues"]}


def test_partial_models_and_missing_summary_row_do_not_shift_occurrences():
    selected, inputs, outputs, extraction = native_build()
    original = inputs["alignment"][0]["content"]
    inputs["alignment"] = [payload("alignment", original + original)]
    model = outputs["models"][0]["content"]
    outputs["models"] = [payload("models", model + model[:model.index(b"      8")], "output")]
    extraction = extract_hmmer_models(outputs["models"][0]["content"], occurrence=outputs["models"][0]["occurrence"], format="hmmer3_ascii")
    sheet = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    assert len(sheet["associations"]) == 2
    assert sheet["associations"][0]["status"] == "validated"
    assert sheet["associations"][1]["summary_record_key"] is None
    assert sheet["model_extraction"]["records"][0]["terminated"]
    assert not sheet["model_extraction"]["records"][1]["terminated"]


def test_selected_redirected_summary_never_falls_back_to_stdout():
    selected, inputs, outputs, extraction = native_build()
    selected["settings"]["-o"] = "missing.txt"
    sheet = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    assert not any(row["kind"] == "build_summary" for row in sheet["native_rows"])
    assert any(i["code"] == "role_missing" and i["field"] == "output.summary" for i in sheet["issues"])
    del selected["settings"]["-o"]
    outputs["summary"] = []  # Original selected role is known even when capture is absent.
    empty = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    assert not any(row["kind"] == "build_summary" for row in empty["native_rows"])


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


def test_malformed_summary_numbers_and_invalid_row_width_remain_partial():
    selected, inputs, outputs, extraction = native_build()
    raw = outputs["stdout"][0]["content"].replace(b"3.00  4.376", b"nan   4.376")
    outputs["stdout"] = [payload("stdout", raw, "output")]
    sheet = populate_hmmer_alignment_preparation_sheet(operation=selected, inputs=inputs, outputs=outputs, model_extraction=extraction)
    row = next(r for r in sheet["native_rows"] if r["kind"] == "build_summary")
    assert row["eff_nseq"] is None and not row["valid"]
    assert row["native_tokens"]["eff_nseq"] == "nan"
    malformed = mask_sheet(b"# STOCKHOLM 1.0\na ACGT\nb AC\n#=GC RF xxxx\n#=GC MM m.\n//\n", **{"--alirange": "1-1", "--dna": True})
    assert {"row_geometry_invalid", "annotation_geometry_invalid"} <= {i["code"] for i in malformed["issues"]}
