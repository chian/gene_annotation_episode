import hashlib
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from gene_annotation_episode.infernal_preparation_artifacts import (
    CHECK_NAMES, COMPONENT_NAMES, ISSUE_CODES, ROW_FIELDS,
    parse_infernal_artifact_operation, populate_infernal_artifact_sheet,
    validate_infernal_artifact_sheet,
)

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native"
OWN = ROOT / "verification/tool_graders_infernal_preparation_models_2026-10-26_248/native"


def payload(data, role, fmt, ref=None, completeness="complete"):
    if type(data) is str:
        data = data.encode()
    return {"artifact": {"role": role, "format": fmt, "artifact_ref": ref or role,
        "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "completeness": completeness}, "content": data}


def operation(program, mode, **settings):
    return {"program": program, "mode": mode, "engine_version": "1.1.5", "settings": settings}


def populate(op, inputs, outputs):
    artifacts = [p["artifact"] for mapping in (inputs, outputs) for group in mapping.values() for p in group]
    return populate_infernal_artifact_sheet(operation=op, artifacts=artifacts, inputs=inputs, outputs=outputs)


def native_payload(case, filename, role, fmt, *, base=NATIVE, **kwargs):
    return payload((base / case / filename).read_bytes(), role, fmt, **kwargs)


def native_case(case, program, mode, output_files, *, input_model="model.cm", input_format="infernal_cm_ascii", settings=None, key_file=False, index=False, base=NATIVE):
    inputs = {"models": [native_payload(case, input_model, "models", input_format, base=base)]}
    if key_file:
        inputs["keys"] = [native_payload(case, "keys.txt", "keys", "key_file", base=base)]
    if index:
        inputs["ssi"] = [native_payload(case, input_model+".ssi", "ssi", "infernal_ssi", ref="input_ssi", base=base)]
    if mode == "single_key":
        inputs["request"] = [native_payload(case, "request.json", "request", "infernal_request_json", base=base)]
    outputs = {role: [native_payload(case, filename, role, fmt, base=base)] for role, filename, fmt in output_files}
    outputs["stdout"] = [native_payload(case, "stdout.txt", "stdout", "infernal_stdout", base=base)]
    outputs["stderr"] = [native_payload(case, "stderr.txt", "stderr", "infernal_stderr", base=base)]
    return populate(operation(program, mode, **(settings or {})), inputs, outputs)


def calculate(sheet, parameters=None):
    got = validate_infernal_artifact_sheet(sheet, parameters=parameters or {})
    assert all(set(r["components"]) <= COMPONENT_NAMES for r in got["rows"])
    assert all(c["check"] in CHECK_NAMES for r in got["rows"] for c in r["checks"])
    assert all(i["code"] in ISSUE_CODES for i in got["issues"])
    json.dumps(got, allow_nan=False)
    return got


def checks(calculation):
    return {c["check"]: c["outcome"] for c in calculation["rows"][0]["checks"]}


@pytest.mark.parametrize("case,mode,fmt,role,expected_bytes", [
    ("cmconvert_ascii", "ascii", "infernal_cm_ascii", "converted_models", 10395),
    ("cmconvert_binary", "binary", "infernal_cm_binary", "converted_models", 7166),
    ("cmconvert_legacy", "legacy_ascii", "infernal_cm_legacy_ascii", "converted_models", 5038),
    ("cmconvert_ml_hmm", "maximum_likelihood_hmm", "hmmer_hmm_ascii", "converted_hmms", 3267),
    ("cmconvert_filter_hmm", "filter_hmm", "hmmer_hmm_ascii", "converted_hmms", 3009),
])
def test_all_five_native_conversion_modes(case, mode, fmt, role, expected_bytes):
    sheet = native_case(case, "cmconvert", mode, [(role, "converted.out", fmt)])
    got = calculate(sheet)
    comp = got["rows"][0]["components"]
    assert comp["input_model_count"]["value"] == 1
    assert comp["output_artifact_count"]["value"] == 3
    assert comp["output_byte_count"]["value"] == expected_bytes
    assert checks(got)["output_format"] == "pass"
    if mode == "binary":
        assert comp["output_model_count"]["state"] == "missing"
        assert checks(got)["model_identity_preserved"] == "unknown"
        assert sheet["output_records"][0]["content_validation"] == "opaque_header_only"
    else:
        assert comp["output_model_count"]["value"] == 1
        assert checks(got)["model_identity_preserved"] == "pass"
        assert checks(got)["conversion_semantics"] == "pass"
    assert all(set(r) == ROW_FIELDS[r["kind"]] for r in sheet["native_rows"])
    if mode == "legacy_ascii":
        assert all(f is None for f in sheet["output_records"][0]["calibration"].values())


def test_native_fetch_missing_key_is_not_successful_request():
    sheet = native_case("cmfetch_missing_unindexed", "cmfetch", "key_file", [("fetched_models", "fetched.cm", "infernal_cm_ascii")], input_model="models.cm", key_file=True)
    rows = [r for r in sheet["native_rows"] if r["kind"] == "key_request"]
    assert [(r["requested_key"], r["outcome"]) for r in rows] == [("absent_key", "missing"), ("tRNA5", "satisfied")]
    comp = calculate(sheet)["rows"][0]["components"]
    assert {name: comp[name]["value"] for name in ("input_model_count", "output_model_count", "requested_key_count", "satisfied_key_count", "missing_key_count")} == {
        "input_model_count": 2, "output_model_count": 1, "requested_key_count": 2, "satisfied_key_count": 1, "missing_key_count": 1}
    assert checks(calculate(sheet))["requested_keys_satisfied"] == "fail"
    receipt = json.loads((NATIVE / "cmfetch_missing_unindexed/receipt.json").read_text())
    assert receipt["returncode"] == 0


@pytest.mark.parametrize("case,index", [("cmfetch_multiple_indexed", True), ("cmfetch_multiple_unindexed", False)])
def test_fetch_order_follows_native_route(case, index):
    sheet = native_case(case, "cmfetch", "key_file", [("fetched_models", "fetched.cm", "infernal_cm_ascii")], input_model="models.cm", key_file=True, index=index)
    comp = calculate(sheet)["rows"][0]["components"]
    assert comp["requested_key_count"]["value"] == comp["satisfied_key_count"]["value"] == 2
    assert checks(calculate(sheet))["requested_keys_satisfied"] == "pass"
    rows = [r for r in sheet["output_records"] if r["kind"] == "model"]
    assert [r["name"] for r in rows] == (["tRNA5-hand", "tRNA5"] if index else ["tRNA5", "tRNA5-hand"])


def test_single_key_provenance_and_missing_request():
    sheet = native_case("cmfetch_single", "cmfetch", "single_key", [("fetched_models", "fetched.cm", "infernal_cm_ascii")], input_model="models.cm", settings={"key": "tRNA5"})
    row = [r for r in sheet["native_rows"] if r["kind"] == "key_request"][0]
    assert row["locator"]["artifact_ref"] == "request" and row["locator"]["line_start"] is None
    assert row["outcome"] == "satisfied"
    assert calculate(sheet)["rows"][0]["components"]["requested_key_count"]["value"] == 1
    data = (NATIVE / "cmcalibrate_tiny/model.cm").read_bytes()
    missing = populate(operation("cmfetch", "single_key", key="fixture246"), {"models": [payload(data, "models", "infernal_cm_ascii")]},
        {"fetched_models": [payload(data, "fetched_models", "infernal_cm_ascii")], "stdout": [payload("", "stdout", "infernal_stdout")]})
    assert "artifact_key_provenance_missing" in {i["code"] for i in missing["issues"]}
    assert not any(r["kind"] == "key_request" for r in missing["native_rows"])
    assert calculate(missing)["rows"][0]["components"]["requested_key_count"]["state"] == "missing"


def test_aliases_can_share_one_returned_model():
    data = (NATIVE / "cmcalibrate_tiny/model.cm").read_bytes()
    sheet = populate(operation("cmfetch", "key_file", **{"-f": True}),
        {"models": [payload(data, "models", "infernal_cm_ascii")], "keys": [payload("# selected aliases\nfixture246 ignored\nTEST246\n", "keys", "key_file")]},
        {"fetched_models": [payload(data, "fetched_models", "infernal_cm_ascii")], "stdout": [payload("Retrieved 1 CMs.\n", "stdout", "infernal_stdout")]})
    keys = [r for r in sheet["native_rows"] if r["kind"] == "key_request"]
    assert [r["match_kind"] for r in keys] == ["name", "accession"]
    assert keys[0]["output_model_keys"] == keys[1]["output_model_keys"]
    comp = calculate(sheet)["rows"][0]["components"]
    assert comp["requested_key_count"]["value"] == comp["satisfied_key_count"]["value"] == 2
    assert comp["output_model_count"]["value"] == 1


def test_cross_model_name_accession_ambiguity_and_duplicate_requests():
    data = (NATIVE / "cmcalibrate_tiny/model.cm").read_bytes()
    other = data.replace(b"fixture246", b"other-model").replace(b"TEST246", b"fixture246")
    for keys, outcome in (("fixture246\n", "ambiguous"), ("fixture246\nfixture246\n", "invalid")):
        sheet = populate(operation("cmfetch", "key_file"),
            {"models": [payload(data+other, "models", "infernal_cm_ascii")], "keys": [payload(keys, "keys", "key_file")]},
            {"fetched_models": [payload(data, "fetched_models", "infernal_cm_ascii")], "stdout": [payload("Retrieved 1 CMs.\n", "stdout", "infernal_stdout")]})
        rows = [r for r in sheet["native_rows"] if r["kind"] == "key_request"]
        assert all(r["outcome"] == outcome and r["match_kind"] == "both" for r in rows)
        assert checks(calculate(sheet))["requested_keys_satisfied"] == "fail"


def index_sheet():
    return native_case("cmfetch_index", "cmfetch", "index", [("ssi", "models.cm.ssi", "infernal_ssi")], input_model="models.cm")


def press_sheet():
    return native_case("cmpress_uncalibrated", "cmpress", "press", [(r, "model.cm."+r, f) for r,f in (
        ("i1m", "infernal_cm_binary"), ("i1i", "infernal_ssi"), ("i1f", "infernal_i1f"), ("i1p", "infernal_i1p"))])


def bound_parameters(sheet):
    source = next(a for a in sheet["artifacts"] if a["role"] == "models")
    return {"artifact_bindings": [{"artifact_ref": a["artifact_ref"], "artifact_sha256": a["sha256"],
        "source_artifact_ref": source["artifact_ref"], "source_sha256": source["sha256"],
        "expected_attempt_id": "retained-attempt", "actual_attempt_id": "retained-attempt",
        "staged_source_stem": "outputs/models.cm", "actual_relative_path": "outputs/models.cm."+a["role"], "regular_file": True}
        for a in sheet["artifacts"] if a["role"] in {"ssi", "i1m", "i1i", "i1f", "i1p"}]}


def test_native_index_reports_counts_without_invented_accession_zero():
    sheet = index_sheet()
    row = sheet["native_rows"][0]
    assert row["values"]["model_count"]["value"] == 2
    assert row["values"]["indexed_name_count"]["value"] == 2
    assert row["values"]["indexed_accession_count"]["state"] == "missing"
    got = calculate(sheet, bound_parameters(sheet))
    assert checks(got)["source_binding"] == "pass"
    assert checks(got)["index_content_decoded"] == "unknown"
    assert got["rows"][0]["components"]["output_byte_count"]["value"] == 263


def test_press_quartet_and_calibration_are_separate():
    sheet = press_sheet()
    got = calculate(sheet, bound_parameters(sheet))
    chk = checks(got)
    assert chk["output_set_complete"] == chk["quartet_binding"] == "pass"
    assert chk["model_calibration_present"] == "fail" and chk["model_filter_present"] == "pass"
    assert chk["index_content_decoded"] == "unknown"
    comp = got["rows"][0]["components"]
    assert comp["output_model_count"]["state"] == "not_measured"
    assert comp["output_artifact_count"]["value"] == 6
    assert comp["output_byte_count"]["value"] == 15691
    assert checks(calculate(sheet))["source_binding"] == "unknown"


@pytest.mark.parametrize("field,new,code", [
    ("source_sha256", "0"*64, "artifact_binding_source_mismatch"),
    ("artifact_sha256", "0"*64, "artifact_binding_digest_mismatch"),
    ("actual_attempt_id", "another-attempt", "artifact_binding_attempt_mismatch"),
    ("actual_relative_path", "wrong.cm.i1m", "artifact_binding_stem_mismatch"),
    ("regular_file", False, "artifact_not_regular_file"),
])
def test_stale_or_cross_attempt_binary_binding(field, new, code):
    sheet = press_sheet()
    params = bound_parameters(sheet)
    params["artifact_bindings"][0][field] = new
    got = calculate(sheet, params)
    assert code in {i["code"] for i in got["issues"]}


def test_partial_output_retained_and_missing_quartet_member():
    sheet = press_sheet()
    sheet["artifacts"] = [a for a in sheet["artifacts"] if a["role"] != "i1p"]
    sheet["output_records"] = [r for r in sheet["output_records"] if r["locator"]["artifact_ref"] != "i1p"]
    sheet["associations"] = []
    assert checks(calculate(sheet))["output_set_complete"] == "fail"
    assert calculate(sheet)["rows"][0]["components"]["output_artifact_count"]["value"] == 5


def test_corrupt_binary_does_not_validate_from_suffix():
    case = "cmpress_uncalibrated"
    original = native_payload(case, "model.cm", "models", "infernal_cm_ascii")
    outputs = {}
    for role, fmt in (("i1m", "infernal_cm_binary"), ("i1i", "infernal_ssi"), ("i1f", "infernal_i1f"), ("i1p", "infernal_i1p")):
        data = (NATIVE / case / ("model.cm."+role)).read_bytes()
        outputs[role] = [payload(b"oops"+data[4:] if role == "i1m" else data, role, fmt)]
    outputs["stdout"] = [native_payload(case, "stdout.txt", "stdout", "infernal_stdout")]
    sheet = populate(operation("cmpress", "press"), {"models": [original]}, outputs)
    got = calculate(sheet)
    row = next(r for r in got["rows"] if r["record_key"].startswith("i1m#"))
    assert any(c["check"] == "artifact_signature" and c["outcome"] == "fail" for c in row["checks"])


def test_saved_sheet_recalculation_without_any_reader_or_execution():
    sheet = json.loads(json.dumps(press_sheet()))
    params = bound_parameters(sheet)
    expected = calculate(sheet, params)
    with patch("builtins.open", side_effect=AssertionError("file")), patch("socket.socket", side_effect=AssertionError("network")), patch("subprocess.Popen", side_effect=AssertionError("native")), patch("gene_annotation_episode.infernal_preparation_artifacts.extract_infernal_models", side_effect=AssertionError("parser")):
        assert calculate(sheet, params) == expected
        changed = deepcopy(params)
        changed["artifact_bindings"][0]["source_sha256"] = "1"*64
        assert calculate(sheet, changed) != expected


def test_calculator_rejects_forged_key_association():
    sheet = native_case("cmfetch_missing_unindexed", "cmfetch", "key_file", [("fetched_models", "fetched.cm", "infernal_cm_ascii")], input_model="models.cm", key_file=True)
    row = next(r for r in sheet["native_rows"] if r["kind"] == "key_request")
    row["outcome"] = "satisfied"
    with pytest.raises(ValueError, match="relationship"):
        calculate(sheet)


def test_role_maps_are_always_lists_and_phantom_artifacts_rejected():
    data = (NATIVE / "cmcalibrate_tiny/model.cm").read_bytes()
    p = payload(data, "models", "infernal_cm_ascii")
    with pytest.raises(TypeError):
        populate_infernal_artifact_sheet(operation=operation("cmpress", "press"), artifacts=[p["artifact"]], inputs={"models": p}, outputs={})
    with pytest.raises(ValueError, match="payload"):
        populate_infernal_artifact_sheet(operation=operation("cmpress", "press"), artifacts=[p["artifact"]], inputs={}, outputs={})


def test_malformed_native_count_does_not_become_zero():
    p = payload("Indexed many CMs (2 names).\n", "stdout", "infernal_stdout")
    got = parse_infernal_artifact_operation(p["content"], operation=operation("cmfetch", "index"), artifact=p["artifact"])
    assert got["rows"][0]["values"]["model_count"]["state"] == "missing"
    assert "artifact_summary_malformed" in {i["code"] for i in got["issues"]}


@pytest.mark.parametrize("mode,fmt", [("binary", "infernal_cm_binary"), ("legacy", "infernal_cm_legacy_ascii")])
def test_actual_binary_and_legacy_input_roundtrip(mode, fmt):
    sheet = native_case("cmconvert_"+mode+"_to_ascii", "cmconvert", "ascii",
        [("converted_models", "converted.cm", "infernal_cm_ascii")], input_format=fmt, base=OWN)
    got = calculate(sheet)
    assert got["rows"][0]["components"]["output_model_count"]["value"] == 1
    assert checks(got)["model_identity_preserved"] == ("unknown" if mode == "binary" else "pass")
    model = next(r for r in sheet["output_records"] if r["kind"] == "model")
    assert model["fields"]["CLEN"]["value"] == 12
    assert model["filter_hmm"] is not None
    assert (model["calibration"]["ECMLC"] is None) == (mode == "legacy")


@pytest.mark.parametrize("route,count,index", [("unindexed", 1, False), ("indexed", 2, True)])
def test_actual_alias_native_multiplicity(route, count, index):
    sheet = native_case("cmfetch_alias_"+route, "cmfetch", "key_file", [("fetched_models", "fetched.cm", "infernal_cm_ascii")],
        input_model="models.cm", key_file=True, index=index, base=OWN)
    comp = calculate(sheet)["rows"][0]["components"]
    assert comp["requested_key_count"]["value"] == comp["satisfied_key_count"]["value"] == 2
    assert comp["output_model_count"]["value"] == count


def test_actual_all_missing_rc_zero_empty_fetch():
    sheet = native_case("cmfetch_missing_all_unindexed", "cmfetch", "key_file", [("fetched_models", "fetched.cm", "infernal_cm_ascii")],
        input_model="models.cm", key_file=True, base=OWN)
    got = calculate(sheet)
    assert got["rows"][0]["components"]["output_model_count"]["value"] == 0
    assert got["rows"][0]["components"]["missing_key_count"]["value"] == 1
    assert checks(got)["output_population_complete"] == "pass"
    assert checks(got)["requested_keys_satisfied"] == "fail"
    assert json.loads((OWN / "cmfetch_missing_all_unindexed/receipt.json").read_text())["returncode"] == 0


def test_actual_duplicate_request_failure_preserves_originals():
    sheet = native_case("cmfetch_duplicate_request_failure", "cmfetch", "key_file", [("fetched_models", "fetched.cm", "infernal_cm_ascii")],
        input_model="models.cm", key_file=True, base=OWN)
    got = calculate(sheet)
    assert got["rows"][0]["components"]["input_model_count"]["value"] == 1
    assert got["rows"][0]["components"]["output_model_count"]["state"] == "missing"
    assert checks(got)["requested_keys_unique"] == "fail"
    assert json.loads((OWN / "cmfetch_duplicate_request_failure/receipt.json").read_text())["returncode"] == 1


def test_actual_calibrated_press_and_failed_duplicate_cleanup():
    output_files = [(r, "models.cm."+r, f) for r,f in (
        ("i1m", "infernal_cm_binary"), ("i1i", "infernal_ssi"), ("i1f", "infernal_i1f"), ("i1p", "infernal_i1p"))]
    sheet = native_case("cmpress_calibrated", "cmpress", "press", output_files, input_model="models.cm", base=OWN)
    assert checks(calculate(sheet, bound_parameters(sheet)))["model_calibration_present"] == "pass"
    assert checks(calculate(sheet, bound_parameters(sheet)))["quartet_binding"] == "pass"
    failure = OWN / "cmpress_duplicate_failure"
    # Check retained actual cleanup; do not fabricate quartet members.
    assert not any((failure / ("models.cm."+r)).exists() for r in ("i1m", "i1i", "i1f", "i1p"))
    sheet = native_case("cmpress_duplicate_failure", "cmpress", "press", [], input_model="models.cm", base=OWN)
    got = calculate(sheet)
    assert checks(got)["model_names_unique"] == "fail"
    assert checks(got)["output_set_complete"] == "fail"
    assert got["rows"][0]["components"]["input_model_count"]["value"] == 2
    assert got["rows"][0]["components"]["output_artifact_count"]["value"] == 2
    assert json.loads((failure / "receipt.json").read_text())["returncode"] == 1


def test_native_count_mismatch_and_wrong_output_format():
    sheet = press_sheet()
    sheet["native_rows"][0]["values"]["model_count"]["value"] = 3
    assert "artifact_native_count_mismatch" in {i["code"] for i in calculate(sheet)["issues"]}
    data = (NATIVE / "cmconvert_filter_hmm/converted.out").read_bytes()
    source = native_payload("cmconvert_filter_hmm", "model.cm", "models", "infernal_cm_ascii")
    sheet = populate(operation("cmconvert", "ascii"), {"models": [source]},
        {"converted_models": [payload(data, "converted_models", "hmmer_hmm_ascii")], "stdout": [payload("", "stdout", "infernal_stdout")]})
    assert checks(calculate(sheet))["output_format"] == "fail"


def test_retained_input_evidence_digests_unchanged():
    manifest = json.loads((NATIVE.parent / "NATIVE_EVIDENCE_001.json").read_text())
    relevant = [r for r in manifest["runs"] if r["case"].startswith(("cmconvert_", "cmfetch_", "cmpress_"))]
    assert len(relevant) == 11
    for run in relevant:
        for item in run["artifacts"]:
            path = NATIVE / run["case"] / item["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_partial_key_capture_cannot_establish_whole_requested_population():
    data = (NATIVE / "cmcalibrate_tiny/model.cm").read_bytes()
    sheet = populate(operation("cmfetch", "key_file"), {"models": [payload(data, "models", "infernal_cm_ascii")],
        "keys": [payload("fixture246\n", "keys", "key_file", completeness="partial")]},
        {"fetched_models": [payload(data, "fetched_models", "infernal_cm_ascii")], "stdout": [payload("Retrieved 1 CMs.\n", "stdout", "infernal_stdout")]})
    assert next(r for r in sheet["native_rows"] if r["kind"] == "key_request")["outcome"] == "invalid"
    assert calculate(sheet)["rows"][0]["components"]["requested_key_count"]["state"] == "missing"


def test_binary_conversion_validates_actual_signature():
    original = native_payload("cmconvert_binary", "model.cm", "models", "infernal_cm_ascii")
    bad = payload(b"oops-binary", "converted_models", "infernal_cm_binary")
    sheet = populate(operation("cmconvert", "binary"), {"models": [original]},
        {"converted_models": [bad], "stdout": [payload("", "stdout", "infernal_stdout")]})
    got = calculate(sheet)
    assert checks(got)["output_format"] == "fail"
    assert checks(got)["artifact_signature"] == "fail"
