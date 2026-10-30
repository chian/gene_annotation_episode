"""A1 supplied-byte reader tests: native259 fixtures plus explicit mutations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_artifact_data import (
    populate_hmmer_artifact_sheet, ROW_FIELDS, ISSUE_CODES, BUNDLE_ROLES,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259"
NATIVE = FIXTURES / "native"


def payload(content, role, direction="input", ordinal=0, oid=None, completeness="complete"):
    oid = oid or direction + "/" + role + "/" + str(ordinal)
    return {"occurrence": {"occurrence_id": oid, "direction": direction, "role": role, "ordinal": ordinal,
        "artifact_ref": "retained:" + oid, "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content), "completeness": completeness}, "content": content}


def model_format(content):
    if content.startswith(b"HMMER2"):
        return "hmmer2_ascii"
    return "hmmer3_ascii" if not content or content.startswith(b"HMMER3") else "hmmer_binary"


def populate(operation, inputs, outputs, bindings=None):
    extractions = [extract_hmmer_models(p["content"], occurrence=p["occurrence"], format=model_format(p["content"]))
        for mapping in (inputs, outputs) for role, values in mapping.items()
        if role in {"models", "converted_models", "fetched_models", "binary_models"} for p in values]
    return populate_hmmer_artifact_sheet(operation=operation, inputs=inputs, outputs=outputs,
        model_extractions=extractions, artifact_bindings=bindings)


def native_case(name):
    """Caller-side acquisition helper only. The production ports receive bytes."""
    directory = NATIVE / name
    receipt = json.loads((directory / "receipt.json").read_text())
    program = name.split("_", 1)[0]
    if program == "hmmconvert":
        mode = "binary" if name == "hmmconvert_binary" else "legacy_hmmer2" if name.endswith("legacy2") else "ascii"
        source_path = Path(receipt["argv"][-1])
    elif program == "hmmfetch":
        mode = "index" if name == "hmmfetch_index" else "single_key" if name == "hmmfetch_single" else "key_file"
        source_path = directory / "models.hmm" if mode == "index" else Path(receipt["argv"][-2])
    else:
        mode, source_path = "index", directory / "models.hmm"
    operation = {"program": program, "mode": mode, "engine_version": "3.4", "settings": {"native_argv": receipt["argv"][1:]}}
    if mode == "single_key":
        operation["settings"]["key"] = receipt["argv"][-1]
    inputs = {"models": [payload(source_path.read_bytes(), "models")]}
    if mode == "key_file":
        inputs["keys"] = [payload(Path(receipt["argv"][-1]).read_bytes(), "keys")]
    indexed = name in {"hmmfetch_indexed_alias", "hmmfetch_indexed_missing", "hmmfetch_duplicate"}
    if indexed:
        inputs["ssi"] = [payload((NATIVE / "hmmfetch_index/models.hmm.ssi").read_bytes(), "ssi")]
    outputs = {role: [payload((directory / (role + ".log")).read_bytes(), role, "output")] for role in ("stdout", "stderr")}
    if program == "hmmconvert":
        outputs["converted_models"] = [payload(outputs["stdout"][0]["content"], "converted_models", "output")]
    elif program == "hmmfetch" and mode != "index":
        outputs["fetched_models"] = [payload(outputs["stdout"][0]["content"], "fetched_models", "output")]
    elif program == "hmmfetch":
        outputs["ssi"] = [payload((directory / "models.hmm.ssi").read_bytes(), "ssi", "output")]
    elif name == "hmmpress_success":
        for role, suffix in zip(BUNDLE_ROLES, ("h3m", "h3i", "h3f", "h3p")):
            outputs[role] = [payload((directory / ("models.hmm." + suffix)).read_bytes(), role, "output")]
    bindings = []
    suffixes = {"binary_models": ".h3m", "ssi_index": ".h3i", "msv_profiles": ".h3f", "remaining_profiles": ".h3p", "ssi": ".ssi"}
    for mapping in (inputs, outputs):
        for role, values in mapping.items():
            if role not in suffixes:
                continue
            for p in values:
                bindings.append({"artifact_occurrence_id": p["occurrence"]["occurrence_id"],
                    "source_occurrence_id": inputs["models"][0]["occurrence"]["occurrence_id"],
                    "source_sha256": inputs["models"][0]["occurrence"]["sha256"],
                    "producer_attempt_id": "retained-259-hmmfetch_index" if indexed else "retained-259-" + name,
                    "staged_source_stem": "models.hmm", "actual_relative_path": "models.hmm" + suffixes[role]})
    return operation, inputs, outputs, bindings


def native_sheet(name):
    return populate(*native_case(name))


def issues(sheet):
    return {issue["code"] for issue in sheet["issues"]}


@pytest.mark.parametrize("name", ["hmmconvert_ascii", "hmmconvert_binary", "hmmconvert_legacy2", "hmmconvert_binary_to_ascii"] +
    ["hmmconvert_3"+r for r in "abcde"] + ["hmmconvert_annotated_3"+r for r in "abcdef"])
def test_native_conversion_occurrences_and_full_m1_data(name):
    sheet = native_sheet(name)
    assert len(sheet["model_extractions"]) == 2
    assert len(sheet["artifact_occurrences"]) == 4
    output = next(e for e in sheet["model_extractions"] if e["occurrence"]["direction"] == "output")
    assert output["population"]["decoded_count"] == 1
    assert output["population"]["complete"]
    if output["records"]:
        assert len(output["records"][0]["positions"]) == 12
        assert len(output["records"][0]["positions"][4]["match"]["cells"]) == 20
        assert output["records"][0]["record_key"].startswith("output/converted_models/")
    assert "conversion_stdout_mismatch" not in issues(sheet)
    assert all(row.keys() == ROW_FIELDS[row["kind"]] for row in sheet["native_rows"] + sheet["associations"])
    assert issues(sheet) <= ISSUE_CODES


@pytest.mark.parametrize("name,returned", [("hmmfetch_single",1),("hmmfetch_unindexed_alias",1),("hmmfetch_indexed_alias",2),
    ("hmmfetch_unindexed_missing",1),("hmmfetch_indexed_missing",1),("hmmfetch_duplicate",1)])
def test_native_fetch_relations_preserve_key_and_output_multiplicity(name, returned):
    sheet = native_sheet(name)
    assert len(sheet["output_records"]) == returned
    resolutions = [a for a in sheet["associations"] if a["kind"] == "key_resolution"]
    assert resolutions[0]["state"] == "resolved"
    if name.endswith("alias"):
        assert len(resolutions) == 2
        assert resolutions[0]["source_record_keys"] == resolutions[1]["source_record_keys"]
        assert (resolutions[0]["output_record_keys"] == resolutions[1]["output_record_keys"]) == (returned == 1)
    if name.endswith("missing"):
        assert resolutions[1]["state"] == "missing"
        assert resolutions[0]["output_record_keys"]
    if name.endswith("duplicate"):
        assert resolutions[1]["lookup_state"] == "duplicate_error"
        assert resolutions[1]["output_record_keys"] == []
        assert "key_duplicate" in issues(sheet)


def test_keys_first_token_comments_and_byte_locators():
    operation, inputs, outputs, bindings = native_case("hmmfetch_unindexed_alias")
    content = b"# comment\n  tiny_protein ignored # tail\r\n\n\tTINY001 other\nA#B note\n"
    inputs["keys"] = [payload(content, "keys")]
    sheet = populate(operation, inputs, outputs, bindings)
    keys = [r for r in sheet["native_rows"] if r["kind"] == "requested_key"]
    assert [r["key"] for r in keys] == ["tiny_protein", "TINY001", "A#B"]
    assert [r["locator"]["line"] for r in keys] == [2, 4, 5]
    for row in keys:
        loc = row["locator"]
        assert content[loc["token_byte_start"]:loc["token_byte_end"]].decode() == row["key"]
    assert keys[0]["tokens"] == ["tiny_protein", "ignored", "#", "tail"]


def test_key_line_grammar_does_not_split_standalone_cr_or_vertical_tab():
    operation,inputs,outputs,bindings = native_case("hmmfetch_unindexed_alias")
    inputs["keys"] = [payload(b"tiny_protein\rignored\n\vTINY001 tail\nA\vB ignored\n", "keys")]
    keys = [r for r in populate(operation,inputs,outputs,bindings)["native_rows"] if r["kind"] == "requested_key"]
    assert [r["key"] for r in keys] == ["tiny_protein","TINY001","A\vB"]
    assert [r["locator"]["line"] for r in keys] == [1,2,3]


def test_identical_source_records_do_not_collapse_or_imply_unique_selection():
    operation, inputs, outputs, bindings = native_case("hmmfetch_single")
    inputs["models"] = [payload(inputs["models"][0]["content"]*2, "models")]
    sheet = populate(operation, inputs, outputs)
    assert len(sheet["input_records"]) == 2
    a = sheet["associations"][0]
    assert len(a["source_record_keys"]) == 2
    assert a["selected_source_record_keys"] == ["input/models/0#model/0"]
    assert "model_label_duplicate" in issues(sheet)


def test_same_bytes_in_separate_occurrences_stay_separate():
    operation, inputs, outputs, _ = native_case("hmmconvert_ascii")
    content = inputs["models"][0]["content"]
    inputs["models"].append(payload(content, "models", ordinal=1))
    outputs["converted_models"].append(payload(content, "converted_models", "output", ordinal=1))
    outputs["stdout"].append(payload(content, "stdout", "output", ordinal=1))
    sheet = populate(operation, inputs, outputs)
    assert len(sheet["input_records"]) == len(sheet["output_records"]) == 2
    assert sheet["input_records"][0]["record_key"] != sheet["input_records"][1]["record_key"]


@pytest.mark.parametrize("name", ["hmmfetch_index", "hmmpress_success"])
def test_native_summaries_and_opaque_framing(name):
    sheet = native_sheet(name)
    summary = next(r for r in sheet["native_rows"] if r["kind"] == "index_summary")
    assert (summary["model_count"],summary["primary_name_count"],summary["accession_count"]) == (1,1,1)
    ssi = next(r for r in sheet["native_rows"] if r["kind"] == "artifact_metadata" and r["format"] == "ssi")
    assert ssi["measured_size_bytes"] == 165 and ssi["byte_order"] == "big"
    assert ssi["offset_width"] == 8 and ssi["decoded_record_count"] is None
    if name == "hmmpress_success":
        model = next(e for e in sheet["model_extractions"] if e["occurrence"]["role"] == "binary_models")
        assert model["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
        assert model["records"][0]["length"] == 12
        framing = [r for r in sheet["native_rows"] if r["kind"] == "artifact_metadata" and r["format"] in {"msv_profiles","remaining_profiles"}]
        assert len(framing) == 2 and all(r["framing_state"] == "prefix_and_terminal_marker" for r in framing)


def test_native_press_duplicate_failure_keeps_two_sources_and_diagnostics():
    sheet = native_sheet("hmmpress_duplicate")
    assert len(sheet["input_records"]) == 2
    assert not sheet["output_records"]
    assert {"required_role_missing", "model_label_duplicate", "native_diagnostic"} <= issues(sheet)
    assert any(r["kind"] == "diagnostic" and r["code"] == "duplicate_key" for r in sheet["native_rows"])


def test_missing_accession_clause_means_actual_zero():
    operation, inputs, outputs, bindings = native_case("hmmfetch_index")
    outputs["stdout"] = [payload(b"Indexed 1 HMMs (1 names).\n", "stdout", "output")]
    sheet = populate(operation, inputs, outputs, bindings)
    summary = next(r for r in sheet["native_rows"] if r["kind"] == "index_summary")
    assert summary["accession_count"] == 0 and not summary["accession_clause_supplied"]


@pytest.mark.parametrize("content", [b"Indexed NaN HMMs (1 names).\n", b"Pressed and indexed 1 HMMs (1 names).\n"])
def test_wrong_program_or_malformed_summary_does_not_become_counts(content):
    operation,inputs,outputs,bindings = native_case("hmmfetch_index")
    outputs["stdout"] = [payload(content,"stdout","output")]
    sheet = populate(operation,inputs,outputs,bindings)
    assert not any(r["kind"] == "index_summary" for r in sheet["native_rows"])
    assert "native_summary_invalid" in issues(sheet)


@pytest.mark.parametrize("change,code", [("hash","occurrence_digest_mismatch"),("size","occurrence_size_mismatch"),
    ("ordinal","occurrence_ordinal_invalid"),("role","occurrence_role_mismatch"),("id","occurrence_id_duplicate")])
def test_supplied_occurrence_errors_are_explicit(change, code):
    operation, inputs, outputs, bindings = native_case("hmmconvert_ascii")
    occurrence = outputs["converted_models"][0]["occurrence"]
    if change == "hash": occurrence["sha256"] = "0"*64
    if change == "size": occurrence["size_bytes"] += 1
    if change == "ordinal": occurrence["ordinal"] = 4
    if change == "role": occurrence["role"] = "models"
    if change == "id": occurrence["occurrence_id"] = inputs["models"][0]["occurrence"]["occurrence_id"]
    sheet = populate(operation, inputs, outputs, bindings)
    assert code in issues(sheet)


def test_m1_envelope_must_match_exact_supplied_bytes():
    operation, inputs, outputs, _ = native_case("hmmconvert_ascii")
    source = inputs["models"][0]
    extraction = extract_hmmer_models(source["content"], occurrence=source["occurrence"], format="hmmer3_ascii")
    extraction["records"][0]["positions"][0]["match"]["cells"][0]["probability"] = .75
    sheet = populate_hmmer_artifact_sheet(operation=operation, inputs=inputs, outputs=outputs, model_extractions=[extraction])
    assert {"model_extraction_mismatch","model_extraction_missing"} <= issues(sheet)
    assert not sheet["input_records"]


def test_partial_and_malformed_trailing_models_preserve_complete_prefix():
    operation, inputs, outputs, _ = native_case("hmmconvert_ascii")
    full = inputs["models"][0]["content"]
    broken = full[:-200]
    outputs["converted_models"] = [payload(full+broken, "converted_models", "output", completeness="partial")]
    outputs["stdout"] = [payload(full+broken, "stdout", "output", completeness="partial")]
    sheet = populate(operation, inputs, outputs)
    assert len(sheet["output_records"]) == 2
    assert sheet["output_records"][0]["terminated"] is True
    assert sheet["output_records"][1]["terminated"] is False
    assert sheet["model_extractions"][1]["population"]["state"] == "partial"


@pytest.mark.parametrize("field,value", [("source_sha256","0"*64),("source_occurrence_id","unrelated"),
    ("actual_relative_path","../models.hmm.ssi"),("staged_source_stem","wrong")])
def test_wrong_or_stale_supplied_bindings_are_not_custody(field,value):
    operation, inputs, outputs, bindings = native_case("hmmfetch_index")
    bindings[0][field] = value
    assert "artifact_binding_mismatch" in issues(populate(operation,inputs,outputs,bindings))


def test_conversion_stdout_alias_has_same_bytes_but_no_extra_population():
    operation, inputs, outputs, _ = native_case("hmmconvert_ascii")
    outputs["stdout"] = [payload(b"wrong", "stdout", "output")]
    sheet = populate(operation,inputs,outputs)
    assert "conversion_stdout_mismatch" in issues(sheet)
    assert len(sheet["output_records"]) == 1


def test_invalid_arguments_return_specific_issues():
    result = populate_hmmer_artifact_sheet(operation={},inputs={},outputs={},model_extractions=[])
    assert issues(result) == {"operation_invalid"}
    operation, inputs, outputs, _ = native_case("hmmconvert_ascii")
    result = populate_hmmer_artifact_sheet(operation=operation,inputs=None,outputs=outputs,model_extractions=None)
    assert {"payload_invalid","model_extraction_invalid"} <= issues(result)


def test_extraction_has_no_io_or_native_side_effect(monkeypatch):
    args = native_case("hmmfetch_indexed_alias")
    def forbidden(*args, **kwargs):
        raise AssertionError("pure artifact extraction attempted I/O")
    import builtins, subprocess, socket, os
    monkeypatch.setattr(builtins,"open",forbidden)
    monkeypatch.setattr(Path,"open",forbidden)
    monkeypatch.setattr(subprocess,"Popen",forbidden)
    monkeypatch.setattr(socket,"socket",forbidden)
    monkeypatch.setattr(os,"system",forbidden)
    assert len(populate(*args)["output_records"]) == 2
