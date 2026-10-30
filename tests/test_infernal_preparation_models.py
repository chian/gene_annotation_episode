"""Retained native files are independent fixtures, not regenerated expectations."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gene_annotation_episode.infernal_preparation_models import (
    ISSUE_CODES, OPAQUE_SIGNATURES, ROW_FIELDS, extract_infernal_models,
)

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native"


def artifact(data, fmt="infernal_cm_ascii", ref="fixture/models", completeness="complete"):
    if isinstance(data, str):
        data = data.encode()
    return {"role": "models", "format": fmt, "artifact_ref": ref,
        "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "completeness": completeness}


def extract(data, fmt="infernal_cm_ascii", **kwargs):
    return extract_infernal_models(data, artifact=artifact(data, fmt, **kwargs), format=fmt, engine_version="1.1.5")


@pytest.fixture
def calibrated():
    return (NATIVE / "cmcalibrate_tiny/model.cm").read_bytes()


def test_calibrated_native_fields_and_algorithm_identity(calibrated):
    got = extract(calibrated)
    assert got["population_complete"] and got["issues"] == []
    assert len(got["records"]) == 1
    row = got["records"][0]
    assert set(row) == ROW_FIELDS["model"]
    assert row["name"] == "fixture246" and row["accession"] == "TEST246"
    assert row["fields"]["CLEN"]["value"] == 12
    assert row["fields"]["NSEQ"]["value"] == 3
    assert row["fields"]["CKSUM"]["value"] == 1727146044
    assert {k: v["value"] for k,v in row["topology"].items()} == {
        "base_pair_nodes": 4, "bifurcation_nodes": 0, "total_nodes": 10, "total_states": 40}
    fit = row["calibration"]["ECMLC"]
    assert fit["algorithm"] == "cm_local_cyk"
    assert fit["lambda"]["value"] == .44855
    assert fit["mu_orig"]["value"] == -2.53576
    assert fit["mu_extrap"]["value"] == -7.66916
    assert fit["random_hit_count"]["value"] == 4409
    assert fit["calibration_dbsize_nt"]["value"] == 10000
    assert fit["tail_probability_mass"]["native_token"] == "0.100000"
    assert row["filter_hmm"]["fields"]["EFFN"]["value"] == 2.364258
    assert row["fields"]["EFFN"]["value"] == 3
    assert row["filter_hmm"]["stats"][2]["algorithm"] == "FORWARD"
    assert row["filter_hmm"]["stats"][2]["location"]["value"] == -1.8467
    assert row["efp7gf"]["location"]["value"] == -2.1516
    assert row["fields"]["GA"]["state"] == "missing"
    assert [x["value"] for x in row["null_background"]] == [0, 0, 0, 0]
    assert all(x["unit"] == "log2_odds" for x in row["null_background"])
    assert row["locator"]["byte_end"] == len(calibrated)
    hloc = row["filter_hmm"]["locator"]
    assert calibrated[hloc["byte_start"]:hloc["byte_end"]].startswith(b"HMMER3/f")


def test_unstructured_and_uncalibrated_native():
    got = extract((NATIVE / "cmbuild_noss/built.cm").read_bytes())
    assert got["population_complete"]
    row = got["records"][0]
    assert row["topology"]["base_pair_nodes"]["value"] == 0
    assert all(fit is None for fit in row["calibration"].values())


def test_legacy_native_grammar():
    got = extract((NATIVE / "cmconvert_legacy/converted.out").read_bytes(), "infernal_cm_legacy_ascii")
    assert got["population_complete"] and got["issues"] == []
    row = got["records"][0]
    assert row["writer_version"] == "converted from 1.1.5"
    assert row["alphabet"] == "1"
    assert row["fields"]["EFFN"]["native_token"] == "3.000"
    assert row["fields"]["W"]["state"] == "missing"
    assert row["filter_hmm"] is None and all(f is None for f in row["calibration"].values())
    assert row["topology"]["total_states"]["value"] == 40


@pytest.mark.parametrize("case", ["cmconvert_filter_hmm", "cmconvert_ml_hmm"])
def test_standalone_native_hmm(case):
    got = extract((NATIVE / case / "converted.out").read_bytes(), "hmmer_hmm_ascii")
    assert got["population_complete"] and got["issues"] == []
    row = got["records"][0]
    assert row["model_type"] == "hmm"
    assert row["filter_hmm"]["fields"]["LENG"]["value"] == 12
    assert all(cell["state"] == "missing" for cell in row["fields"].values())
    assert all(cell["state"] == "missing" for cell in row["topology"].values())


def test_writer_version_is_not_execution_version(calibrated):
    data = calibrated.replace(b"INFERNAL1/a [1.1.5 | Sep 2023]", b"INFERNAL1/a [1.1.4 | Dec 2020]")
    assert extract(data)["records"][0]["writer_version"] == "1.1.4 | Dec 2020"


def test_population_and_partial_sibling(calibrated):
    got = extract(calibrated + calibrated[:600])
    assert len(got["records"]) == 2 and not got["population_complete"]
    assert got["records"][0]["content_validation"] == "parsed_headers_and_boundaries"
    assert got["records"][1]["content_validation"] == "partial"
    assert got["records"][1]["fields"]["CLEN"]["value"] == 12
    assert got["records"][0]["record_key"] != got["records"][1]["record_key"]


def test_missing_filter_does_not_consume_next_model(calibrated):
    cm = calibrated.split(b"HMMER3/f")[0]
    got = extract(cm + calibrated)
    assert len(got["records"]) == 2
    assert got["records"][0]["content_validation"] == "partial"
    assert got["records"][1]["content_validation"] == "parsed_headers_and_boundaries"


def test_unterminated_filter_retains_current_cm_fields(calibrated):
    got = extract(calibrated[:-10])
    assert not got["population_complete"]
    assert got["records"][0]["content_validation"] == "partial"
    assert got["records"][0]["fields"]["CLEN"]["value"] == 12
    assert got["records"][0]["filter_hmm"]["fields"]["LENG"]["value"] == 12


@pytest.mark.parametrize("change,code", [
    ((b"CLEN     12", b"CLEN     nan"), "model_number_invalid"),
    ((b"NODES    10", b"NODES    11"), "model_topology_mismatch"),
    ((b"ECMGC    0.37365", b"ECMGC    -0.37365"), "model_number_invalid"),
    ((b"NAME     fixture246", b"NAME     fixture246\nNAME     other"), "model_header_duplicate"),
    ((b"NAME  fixture246", b"NAME  other"), "model_filter_mismatch"),
    ((b"     S     0", b"     X     0"), "model_body_invalid"),
])
def test_bad_native_content_preserves_useful_cells(calibrated, change, code):
    got = extract(calibrated.replace(*change))
    assert not got["population_complete"]
    assert code in {i["code"] for i in got["issues"]}
    assert got["records"][0]["fields"]["NSEQ"]["value"] == 3
    assert all(i["code"] in ISSUE_CODES for i in got["issues"])
    json.dumps(got, allow_nan=False)


@pytest.mark.parametrize("fmt,path", [
    ("infernal_cm_binary", "cmconvert_binary/converted.out"),
    ("infernal_ssi", "cmfetch_index/models.cm.ssi"),
    ("infernal_i1f", "cmpress_uncalibrated/model.cm.i1f"),
    ("infernal_i1p", "cmpress_uncalibrated/model.cm.i1p"),
])
def test_native_opaque_has_no_model_population(fmt, path):
    data = (NATIVE / path).read_bytes()
    got = extract(data, fmt)
    assert got["records"] == [] and not got["population_complete"]
    assert [i["code"] for i in got["issues"]] == ["model_opaque_content"]
    assert "model_binary_signature_invalid" in {i["code"] for i in extract(b"BAD!"+data[4:], fmt)["issues"]}
    assert "model_binary_header_truncated" in {i["code"] for i in extract(OPAQUE_SIGNATURES[fmt], fmt)["issues"]}


def test_capture_custody_and_completeness(calibrated):
    art = artifact(calibrated)
    art["sha256"] = "0"*64
    got = extract_infernal_models(calibrated, artifact=art, format=art["format"])
    assert not got["population_complete"] and got["records"]
    assert "model_artifact_digest_mismatch" in {i["code"] for i in got["issues"]}
    got = extract(calibrated, completeness="partial")
    assert not got["population_complete"]
    assert got["records"][0]["content_validation"] == "parsed_headers_and_boundaries"


def test_no_io_and_saved_json(calibrated):
    with patch("builtins.open", side_effect=AssertionError("unexpected file access")), patch("socket.socket", side_effect=AssertionError("network")), patch("subprocess.Popen", side_effect=AssertionError("subprocess")):
        got = extract(calibrated)
        assert json.loads(json.dumps(got)) == got
    stream = calibrated.decode().splitlines(keepends=True)
    assert extract_infernal_models(iter(stream), artifact=artifact(calibrated), format="infernal_cm_ascii") == got


def test_wrong_api_format_is_not_native_failure(calibrated):
    with pytest.raises(ValueError):
        extract_infernal_models(calibrated, artifact=artifact(calibrated), format="hmmer_hmm_ascii")


def test_actual_multi_model_record_boundaries():
    data = (NATIVE / "cmfetch_index/models.cm").read_bytes()
    got = extract(data)
    assert got["population_complete"] and len(got["records"]) == 2, got["issues"]
    assert [x["name"] for x in got["records"]] == ["tRNA5", "tRNA5-hand"]
    assert got["records"][0]["locator"]["byte_end"] == got["records"][1]["locator"]["byte_start"]
