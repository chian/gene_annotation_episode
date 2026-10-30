"""Native hmmstat associations, populations and explicit missing values."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_statistics_data import parse_hmmstat_summary, populate_hmmstat_sheet


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
OPERATION = {"program": "hmmstat", "mode": "summary", "engine_version": "3.4", "settings": {}}


def payload(content, role, direction, *, ordinal=0, completeness="complete", identity=None):
    digest = hashlib.sha256(content).hexdigest()
    return {"occurrence": {"occurrence_id": identity or f"{direction}/{role}/{ordinal}",
        "direction": direction, "role": role, "ordinal": ordinal,
        "artifact_ref": "artifact_" + digest, "sha256": digest,
        "size_bytes": len(content), "completeness": completeness}, "content": content}


def make_sheet(model_bytes, summary_bytes, *, model_format="hmmer3_ascii", completeness="complete"):
    models = payload(model_bytes, "models", "input", completeness=completeness)
    summary = payload(summary_bytes, "summary", "output", completeness=completeness)
    extraction = extract_hmmer_models(model_bytes, occurrence=models["occurrence"], format=model_format)
    return populate_hmmstat_sheet(operation=OPERATION, inputs={"models": [models]},
        outputs={"summary": [summary]}, model_extraction=extraction)


def native_case(kind="dna"):
    model_bytes = (NATIVE / f"hmmbuild_{kind}" / "profile.hmm").read_bytes()
    summary_bytes = (NATIVE / f"hmmstat_{kind}" / "stdout.log").read_bytes()
    return make_sheet(model_bytes, summary_bytes)


@pytest.mark.parametrize("kind", ["protein", "dna", "rna", "annotated"])
def test_native_complete_population_and_exact_ordered_association(kind):
    sheet = native_case(kind)
    assert sheet["issues"] == []
    assert sheet["summary"]["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
    row = sheet["native_rows"][0]
    assert len(row["tokens"]) == 10
    assert row["values"]["nseq"] == 3 and row["values"]["eff_nseq"] == 3 and row["values"]["M"] == 12
    assert row["locator"]["byte_end"] > row["locator"]["byte_start"]
    assert sheet["associations"] == [{"native_record_key": row["record_key"],
        "model_record_keys": ["input/models/0#model/0"], "state": "validated", "fields": []}]
    assert len(sheet["model_extraction"]["records"][0]["positions"]) == 12


def test_stdout_alias_is_retained_as_occurrence_without_double_rows():
    models = payload((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes(), "models", "input")
    summary_bytes = (NATIVE / "hmmstat_dna/stdout.log").read_bytes()
    outputs = {role: [payload(summary_bytes, role, "output")] for role in ("summary", "stdout")}
    sheet = populate_hmmstat_sheet(operation=OPERATION, inputs={"models": [models]}, outputs=outputs,
        model_extraction=extract_hmmer_models(**models, format="hmmer3_ascii"))
    assert len(sheet["native_rows"]) == 1
    assert len(sheet["artifact_occurrences"]) == 3
    assert sheet["artifact_occurrences"][1]["artifact_ref"] == sheet["artifact_occurrences"][2]["artifact_ref"]
    assert sheet["artifact_occurrences"][1]["occurrence_id"] != sheet["artifact_occurrences"][2]["occurrence_id"]


def test_identical_model_occurrences_do_not_collapse_on_labels_or_bytes():
    model_bytes = (NATIVE / "hmmbuild_dna/profile.hmm").read_bytes()
    sheet = make_sheet(model_bytes * 2, b"1 tiny_dna TINYDNA001 3 3.00 12 1.01 1.01 .89 .01\n"
        b"2 tiny_dna TINYDNA001 3 3.00 12 1.01 1.01 .89 .01\n")
    assert len(sheet["associations"]) == 2
    assert [x["model_record_keys"] for x in sheet["associations"]] == [
        ["input/models/0#model/0"], ["input/models/0#model/1"]]
    assert all(x["state"] == "validated" for x in sheet["associations"])


@pytest.mark.parametrize("row", [b"1 wrong TINYDNA001 3 3.00 12 1.01 1.01 .89 .01\n",
    b"1 tiny_dna WRONG 3 3.00 12 1.01 1.01 .89 .01\n",
    b"1 tiny_dna TINYDNA001 4 3.00 12 1.01 1.01 .89 .01\n",
    b"1 tiny_dna TINYDNA001 3 4.00 12 1.01 1.01 .89 .01\n",
    b"1 tiny_dna TINYDNA001 3 3.00 13 1.01 1.01 .89 .01\n"])
def test_contradictory_native_identity_cannot_join(row):
    sheet = make_sheet((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes(), row)
    assert sheet["associations"][0]["state"] == "conflicting"


def test_missing_and_empty_are_distinct_and_prefix_rows_survive():
    data = b"1 tiny_dna TINYDNA001 3 3.00 12 1.01 1.01 .89 .01\nBROKEN 2 ROW\n"
    extraction = parse_hmmstat_summary(**payload(data, "summary", "output"), operation=OPERATION)
    assert extraction["population"]["state"] == "partial"
    assert len(extraction["rows"]) == 2 and extraction["rows"][0]["values"]["M"] == 12
    assert extraction["rows"][1]["tokens"] == ["BROKEN", "2", "ROW"]
    empty = parse_hmmstat_summary(**payload(b"", "summary", "output"), operation=OPERATION)
    assert empty["population"] == {"decoded_count": 0, "complete": True, "state": "decoded"}
    models = payload((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes(), "models", "input")
    missing = populate_hmmstat_sheet(operation=OPERATION, inputs={"models": [models]}, outputs={},
        model_extraction=extract_hmmer_models(**models, format="hmmer3_ascii"))
    assert missing["summary"] is None
    assert any(x["code"] == "summary_missing_or_repeated" for x in missing["issues"])


def test_nonfinite_values_and_native_unknown_counts_are_not_zero():
    data = b"1 model - -1 -1.00 12 -nan inf -.12 0.00\n"
    extraction = parse_hmmstat_summary(**payload(data, "summary", "output"), operation=OPERATION)
    row = extraction["rows"][0]
    assert row["states"]["nseq"] == row["states"]["eff_nseq"] == "native_missing_sentinel"
    assert row["values"]["nseq"] is None
    assert row["states"]["relent"] == row["states"]["info"] == "nonfinite"
    assert row["values"]["relent"] is None
    assert row["values"]["p_relE"] == -.12
    assert row["values"]["compKL"] == 0 and row["states"]["compKL"] == "present"


def test_tampered_extraction_and_wrong_summary_digest_do_not_bind():
    models = payload((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes(), "models", "input")
    output = payload((NATIVE / "hmmstat_dna/stdout.log").read_bytes(), "summary", "output")
    extraction = extract_hmmer_models(**models, format="hmmer3_ascii")
    mutated = deepcopy(extraction)
    mutated["records"][0]["positions"][0]["match"]["cells"][0]["probability"] = .123
    sheet = populate_hmmstat_sheet(operation=OPERATION, inputs={"models": [models]},
        outputs={"summary": [output]}, model_extraction=mutated)
    assert sheet["associations"][0]["state"] == "unresolved"
    assert any(x["code"] == "model_extraction_mismatch" for x in sheet["issues"])
    output["occurrence"]["sha256"] = "0" * 64
    sheet = populate_hmmstat_sheet(operation=OPERATION, inputs={"models": [models]},
        outputs={"summary": [output]}, model_extraction=extraction)
    assert sheet["associations"][0]["state"] == "unresolved"
    assert any(x["code"] == "occurrence_digest_mismatch" for x in sheet["issues"])


def test_partial_capture_keeps_prefix_model_association():
    model_bytes = (NATIVE / "hmmbuild_dna/profile.hmm").read_bytes()
    summary_bytes = (NATIVE / "hmmstat_dna/stdout.log").read_bytes()
    sheet = make_sheet(model_bytes + b"HMMER3/f [3.4]\nNAME truncated\n", summary_bytes, completeness="partial")
    assert sheet["associations"][0]["state"] == "validated"
    assert sheet["model_extraction"]["population"]["complete"] is False
    assert sheet["summary"]["population"]["complete"] is False


def test_supported_binary_preserves_model_population_and_summary_association():
    data = (NATIVE / "hmmconvert_binary/stdout.log").read_bytes()
    sheet = make_sheet(data, b"1 tiny_protein TINY001 3 3.00 12 4.38 4.10 4.38 .79\n", model_format="hmmer_binary")
    assert sheet["model_extraction"]["population"] == {
        "decoded_count": 1, "complete": True, "state": "decoded"}
    assert sheet["native_rows"][0]["values"]["M"] == 12
    assert sheet["associations"][0]["state"] == "validated"
    assert sheet["associations"][0]["model_record_keys"] == ["input/models/0#model/0"]


def test_unknown_binary_layout_does_not_invent_model_population():
    # A constructed unsupported magic is distinct from the supported native fixture.
    data = b"xxxx" + (NATIVE / "hmmconvert_binary/stdout.log").read_bytes()[4:]
    sheet = make_sheet(data, b"1 tiny_protein TINY001 3 3.00 12 4.38 4.10 4.38 .79\n", model_format="hmmer_binary")
    assert sheet["model_extraction"]["population"]["decoded_count"] is None
    assert sheet["model_extraction"]["population"]["state"] == "unsupported"
    assert sheet["native_rows"][0]["values"]["M"] == 12
    assert sheet["associations"][0]["state"] == "unresolved"


def test_duplicate_native_index_does_not_reuse_model_identity():
    line = b"1 tiny_dna TINYDNA001 3 3.00 12 1.01 1.01 .89 .01\n"
    sheet = make_sheet((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes() * 2, line * 2)
    assert all(a["state"] == "conflicting" for a in sheet["associations"])
