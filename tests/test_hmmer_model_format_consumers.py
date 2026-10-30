"""Shared numerical consumers of retained binary/H2 and labeled synthetic data.

The retained conversion files establish authentic source bytes. Synthetic H2
score/label mutations test availability. Constructed command logs test source
grammar and comparison semantics; neither is an authentic native observation.
"""
from copy import deepcopy
import builtins
import json
import math
from pathlib import Path
import socket
import struct
import subprocess

import pytest

from gene_annotation_episode.hmmer_model_data import ALPHABETS, TRANSITIONS, extract_hmmer_models
from gene_annotation_episode.hmmer_model_calculations import (
    calculate_hmmer_model_components, validate_hmmer_probability_cell,
    validate_hmmer_probability_vector,
)
from gene_annotation_episode.hmmer_model_source_cells import hmmer2_probability_cell
from gene_annotation_episode.hmmer_artifact_calculations import calculate_hmmer_artifact_components
from gene_annotation_episode.hmmer_emission_calculations import calculate_hmmemit_components
from gene_annotation_episode.hmmer_emission_data import populate_hmmemit_sheet
from gene_annotation_episode.hmmer_statistics_calculations import calculate_hmmstat_components, native_hmmstat_parameters
from test_hmmer_artifact_data import NATIVE, native_sheet, native_case, payload, populate
from test_hmmer_emission_data import arguments as emission_arguments
from test_hmmer_statistics_data import make_sheet as statistics_sheet


FILES = {"hmmer_binary": "hmmconvert_binary/stdout.log",
         "hmmer2_ascii": "hmmconvert_legacy2/stdout.log",
         "hmmer3_ascii": "hmmconvert_ascii/stdout.log"}


def extraction(fmt, content=None):
    content = (NATIVE / FILES[fmt]).read_bytes() if content is None else content
    return extract_hmmer_models(**payload(content, "models"), format=fmt)


def row(result, kind):
    return next(r for r in result["rows"] if r["kind"] == kind)


def checks(result, code):
    return [c["state"] for c in result["checks"] if c.get("code", c.get("name")) == code]


def synthetic_in_range_h2():
    """Explicit synthetic scores: every match emission has score0 vs actualNULE."""
    lines = (NATIVE / FILES["hmmer2_ascii"]).read_bytes().splitlines()
    for index, line in enumerate(lines):
        tokens = line.split()
        if tokens and tokens[0].isdigit() and len(tokens) >= 21:
            tokens[1:21] = [b"0"] * 20
            lines[index] = b" ".join(tokens)
    return b"\n".join(lines) + b"\n"


def emission_sheet(fmt, style="consensus", content=None):
    content = (NATIVE / FILES[fmt]).read_bytes() if content is None else content
    args = emission_arguments(style, model=content)
    args["model_extraction"] = extract_hmmer_models(content,
        occurrence=args["inputs"]["models"][0]["occurrence"], format=fmt)
    return populate_hmmemit_sheet(**args)


def test_retained_binary_uses_exact_native_cells_in_common_formulas():
    saved = extraction("hmmer_binary")
    native = saved["records"][0]
    assert native["locator"]["line_start"] is native["locator"]["line_end"] is None
    result = calculate_hmmer_model_components(saved, background=dict.fromkeys(ALPHABETS["amino"], .05))
    r = result["rows"][0]
    f, y = 0.666663408279419, 0.3333340883255005
    assert native["positions"][4]["match"]["cells"][4]["probability"] == f
    assert native["positions"][4]["match"]["cells"][19]["probability"] == y
    assert r["positions"][4]["entropy"]["value"] == pytest.approx(-f*math.log2(f)-y*math.log2(y), abs=1e-15)
    assert r["positions"][4]["match"]["mass"]["value"] == f+y
    assert r["mean_match_entropy"]["state"] == "present"
    assert r["sequence_count"]["value"] == 3
    ratio_sources = {i["native_field"]: i["role"] for i in r["effective_sequence_ratio"]["inputs"] if "native_field" in i}
    assert ratio_sources == {"NSEQ": "denominator", "EFFN": "numerator"}
    assert all(c["state"] == "pass" for c in result["checks"] if c["code"] == "probability_mass")
    assert any(i.get("qualification") == "binary_layout_interpretation" for i in r["positions"][4]["entropy"]["inputs"])


def test_retained_h2_invalid_nominal_does_not_erase_in_range_position_or_counts():
    saved = extraction("hmmer2_ascii")
    native = saved["records"][0]
    assert saved["population"]["complete"] is True
    original = native["positions"][0]["match"]["cells"][0]
    assert original["source"]["score"] == 3666
    assert original["source"]["nominal_probability"] > 1
    assert original["probability"] is None
    assert native["representation"]["legacy"]["null_emissions"]["cells"][0]["source"]["score"] == 656
    result = calculate_hmmer_model_components(saved, background=dict.fromkeys(ALPHABETS["amino"], .05))
    r = result["rows"][0]
    assert r["sequence_count"]["value"] == 3
    assert r["effective_sequence_count"]["state"] == "missing"
    assert r["positions"][0]["entropy"]["state"] == "incompatible"
    assert r["mean_match_entropy"]["value"] is None
    assert r["mean_match_entropy"]["state"] == "incompatible"
    # Independently evaluate the two explicit source scores/reference integers.
    f32 = lambda value: struct.unpack("<f", struct.pack("<f", value))[0]
    f = f32(f32(f32(.05)*math.exp(-333*.00069314718))*math.exp(4070*.00069314718))
    y = f32(f32(f32(.05)*math.exp(-717*.00069314718))*math.exp(3454*.00069314718))
    p5 = r["positions"][4]
    assert p5["entropy"]["state"] == p5["relative_entropy"]["state"] == "present"
    assert p5["entropy"]["value"] == pytest.approx(-f*math.log2(f)-y*math.log2(y), abs=1e-15)
    assert p5["match"]["mass"]["value"] == f+y
    assert p5["match"]["mass_residual"]["value"] == f+y-1
    assert any(i.get("qualification") == "hmmer2_quantized_nominal" for i in p5["entropy"]["inputs"])
    assert any(i["code"] == "nominal_probability_out_of_range" for i in result["issues"])
    assert any(c["code"] == "probability_mass" and c["field"] == "match" and c["position"] == 1
               and c["state"] == "unknown" for c in result["checks"])


def test_h2_absent_initial_and_terminal_states_have_dependent_unavailability():
    result = calculate_hmmer_model_components(extraction("hmmer2_ascii"))
    r = result["rows"][0]
    assert r["composition"]["mass"]["state"] == "missing"
    assert r["initial"]["insert"]["mass"]["state"] == "incompatible"
    assert all(g["mass"]["state"] == "incompatible" for g in r["initial"]["transitions"].values())
    assert r["positions"][-1]["insert"]["mass"]["state"] == "incompatible"
    assert all(g["mass"]["state"] == "incompatible" for g in r["positions"][-1]["transitions"].values())
    for c in result["checks"]:
        if c["code"] == "probability_mass" and (c["field"].startswith("initial.") or
                c["position"] == 12 and c["field"] in {"insert", "transitions"}):
            assert c["state"] == "not_applicable"
    assert r["positions"][0]["transitions"]["I"]["mass"]["state"] == "present"
    assert r["positions"][0]["transitions"]["D"]["mass"]["state"] == "present"


@pytest.mark.parametrize("exit_case", ["zero", "nonzero", "missing", "labels_invalid"])
def test_h2_match_transition_subtotal_keeps_exit_population_explicit(exit_case):
    native = extraction("hmmer2_ascii")["records"][0]
    exit_row = native["representation"]["legacy"]["entry_exit"][0]
    exit_row["cells"][1] = hmmer2_probability_cell("-1000" if exit_case == "nonzero" else "*", reference={"kind": "unit"})
    if exit_case == "missing":
        exit_row["cells"] = []
    if exit_case == "labels_invalid":
        native["issues"].append({"code": "transition_labels_invalid"})
    vector = validate_hmmer_probability_vector(native["positions"][0]["transitions"], record=native,
        field="transitions", position_ordinal=0, symbols=TRANSITIONS, indices=(0, 1, 2))
    assert vector["state"] == "present" and len(vector["values"]) == 3
    assert vector["qualification"] == ("hmmer2_quantized_nominal" if exit_case == "zero" else "hmmer2_core_subvector")
    assert vector["issue_code"] == (None if exit_case == "zero" else "transition_population_excludes_exit")


@pytest.mark.parametrize("mutation", ["token", "score", "reference", "nominal", "probability", "nule", "nule_alphabet", "representation"])
def test_h2_saved_cell_changes_cannot_change_source_meaning(mutation):
    native = extraction("hmmer2_ascii")["records"][0]
    cell = native["positions"][4]["match"]["cells"][4]
    if mutation == "token": cell["token"] = "4071"
    elif mutation == "score": cell["source"]["score"] += 1
    elif mutation == "reference": cell["source"]["reference"]["cell_index"] = 5
    elif mutation == "nominal": cell["source"]["nominal_probability"] = .1
    elif mutation == "probability": cell["probability"] = .1
    elif mutation == "nule": native["representation"]["legacy"]["null_emissions"]["cells"][4]["source"]["score"] += 1
    elif mutation == "nule_alphabet":
        null = hmmer2_probability_cell("0", reference={"kind": "uniform_alphabet", "denominator": 4})
        native["representation"]["legacy"]["null_emissions"]["cells"][4] = null
        cell = hmmer2_probability_cell("0", reference={"kind": "nule", "cell_index": 4}, reference_cell=null)
    else: native.pop("representation")
    result = validate_hmmer_probability_cell(cell, record=native, field="match", position_ordinal=4, cell_index=4)
    assert result["state"] == "incompatible" and result["probability"] is None


@pytest.mark.parametrize("mutation", ["raw", "bounds", "slot", "byte_order", "probability", "representation", "signed_zero"])
def test_binary_saved_cell_changes_are_checked_against_declared_source(mutation):
    native = extraction("hmmer_binary")["records"][0]
    index = 1 if mutation == "signed_zero" else 0
    cell = native["positions"][0]["match"]["cells"][index]
    if mutation == "raw": cell["source"]["raw_hex"] = "0000003f"
    elif mutation == "bounds": cell["source"]["byte_end"] += 1
    elif mutation == "slot":
        cell["source"]["byte_start"] += 4
        cell["source"]["byte_end"] += 4
    elif mutation == "byte_order": native["representation"]["byte_order"] = "big"
    elif mutation == "probability": cell["probability"] = True
    elif mutation == "representation": native.pop("representation")
    else: cell["probability"] = -0.0
    result = validate_hmmer_probability_cell(cell, record=native, field="match", position_ordinal=0, cell_index=index)
    assert result["state"] == "incompatible" and result["probability"] is None


@pytest.mark.parametrize("field,raw,state", [("NSEQ", struct.pack("<i", -1), "missing"),
    ("NSEQ", struct.pack("<i", -2), "incompatible"), ("EFFN", struct.pack("<f", -1), "missing"),
    ("EFFN", struct.pack("<f", -2), "incompatible"), ("EFFN", struct.pack("<f", math.nan), "incompatible")])
def test_binary_native_count_sentinel_and_invalid_domain_stay_distinct(field, raw, state):
    content = (NATIVE / FILES["hmmer_binary"]).read_bytes()
    native = extraction("hmmer_binary", content)["records"][0]
    source = next(n for n in native["representation"]["native_fields"] if n["field"] == field)
    content = content[:source["byte_start"]] + raw + content[source["byte_end"]:]
    result = calculate_hmmer_model_components(extraction("hmmer_binary", content))
    name = {"NSEQ": "sequence_count", "EFFN": "effective_sequence_count"}[field]
    assert result["rows"][0][name]["state"] == state
    assert result["rows"][0][name]["value"] is None
    assert result["rows"][0]["effective_sequence_ratio"]["state"] == state


@pytest.mark.parametrize("field", ["sequence_count", "effective_sequence_count"])
@pytest.mark.parametrize("mutation", ["common", "raw", "native_value"])
def test_binary_count_common_projection_must_match_retained_source(field, mutation):
    saved = extraction("hmmer_binary")
    native = saved["records"][0]
    tag = "NSEQ" if field == "sequence_count" else "EFFN"
    source = next(n for n in native["representation"]["native_fields"] if n["field"] == tag)
    if mutation == "common": native[field] = 7
    elif mutation == "raw": source["raw_hex"] = struct.pack("<i" if tag == "NSEQ" else "<f", 7).hex()
    else: source["value"] = 7
    result = calculate_hmmer_model_components(saved)
    assert result["rows"][0][field]["state"] == "incompatible"
    assert result["rows"][0][field]["value"] is None
    assert result["rows"][0]["effective_sequence_ratio"]["state"] == "incompatible"


@pytest.mark.parametrize("field,ordinal", [("match", 0), ("initial.insert", None),
    ("insert", 5), ("initial.transitions", None), ("transitions", 5), ("composition", None)])
def test_binary_cell_locator_is_tied_to_field_position_and_cell(field, ordinal):
    native = extraction("hmmer_binary")["records"][0]
    if field.startswith("initial."):
        cell = native["initial"][field.removeprefix("initial.")]["cells"][0]
    elif field == "composition":
        cell = native["composition"]["cells"][0]
    else:
        cell = native["positions"][ordinal][field]["cells"][0]
    assert validate_hmmer_probability_cell(cell, record=native, field=field, position_ordinal=ordinal, cell_index=0)["state"] == "present"
    cell["source"]["byte_start"] += 4
    cell["source"]["byte_end"] += 4
    assert validate_hmmer_probability_cell(cell, record=native, field=field, position_ordinal=ordinal, cell_index=0)["state"] == "incompatible"


def test_h2_absent_nule_and_structural_zero_have_distinct_saved_meaning():
    native = extraction("hmmer2_ascii")["records"][0]
    native["representation"]["legacy"]["null_emissions"] = None
    for token, state, code in [("*", "present", None), ("0", "missing", "probability_reference_missing")]:
        cell = hmmer2_probability_cell(token, reference={"kind": "nule", "cell_index": 0})
        checked = validate_hmmer_probability_cell(cell, record=native, field="match", position_ordinal=0, cell_index=0)
        assert checked["state"] == state and checked["issue_code"] == code
    native["representation"]["legacy"]["null_emissions"] = {"malformed": True}
    zero = hmmer2_probability_cell("*", reference={"kind": "nule", "cell_index": 0})
    assert validate_hmmer_probability_cell(zero, record=native, field="match", position_ordinal=0, cell_index=0)["probability"] == 0


def test_h2_zero_nule_operand_explains_incompatible_finite_log_odds():
    native = extraction("hmmer2_ascii")["records"][0]
    nulls = native["representation"]["legacy"]["null_emissions"]
    nulls["cells"][0] = hmmer2_probability_cell("*", reference={"kind": "uniform_alphabet", "denominator": 20})
    cell = hmmer2_probability_cell("100", reference={"kind": "nule", "cell_index": 0}, reference_cell=nulls["cells"][0])
    checked = validate_hmmer_probability_cell(cell, record=native, field="match", position_ordinal=0, cell_index=0)
    assert checked["state"] == "incompatible" and checked["issue_code"] == "distribution_invalid"
    assert checked["inputs"][0]["reference_state"] == "structural_zero"
    assert checked["inputs"][0]["reference_probability"] == 0.0
    assert checked["inputs"][0]["reference_reason"] == "finite_log_odds_against_zero_null"


@pytest.mark.parametrize("field", ["match", "insert"])
def test_record_incompatible_nule_invalidates_only_dependent_emission(field):
    native = extraction("hmmer2_ascii")["records"][0]
    null = hmmer2_probability_cell("0", reference={"kind": "uniform_alphabet", "denominator": 4})
    native["representation"]["legacy"]["null_emissions"]["cells"][4] = null
    cell = hmmer2_probability_cell("0", reference={"kind": "nule", "cell_index": 4}, reference_cell=null)
    native["positions"][4][field]["cells"][4] = cell
    dependent = validate_hmmer_probability_cell(cell, record=native, field=field, position_ordinal=4, cell_index=4)
    assert dependent["state"] == "incompatible" and dependent["probability"] is None
    assert dependent["inputs"][0]["reference_state"] == "incompatible"
    independent = native["positions"][4][field]["cells"][19]
    assert validate_hmmer_probability_cell(independent, record=native, field=field,
        position_ordinal=4, cell_index=19)["state"] == "present"


def test_duplicate_nule_is_malformed_reference_and_structural_zero_remains_independent():
    content = (NATIVE / FILES["hmmer2_ascii"]).read_bytes()
    line = next(line for line in content.splitlines(keepends=True) if line.startswith(b"NULE"))
    saved = extraction("hmmer2_ascii", content.replace(line, line + line))
    native = saved["records"][0]
    assert native["representation"]["legacy"]["null_emissions"] is None
    assert any(i["code"] == "header_duplicate" and i["field"] == "NULE" for i in native["issues"])
    for index, state in [(4, "incompatible"), (0, "present")]:
        cell = native["positions"][4]["match"]["cells"][index]
        checked = validate_hmmer_probability_cell(cell, record=native, field="match", position_ordinal=4, cell_index=index)
        assert checked["state"] == state
    assert calculate_hmmer_model_components(saved)["rows"][0]["sequence_count"]["value"] == 3


def test_h2_in_range_mean_uses_explicit_background_and_pure_saved_recalculation(monkeypatch):
    saved = json.loads(json.dumps(extraction("hmmer2_ascii", synthetic_in_range_h2())))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved recalculation attempted acquisition")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    first = calculate_hmmer_model_components(saved)
    q = dict.fromkeys(ALPHABETS["amino"], .9/19)
    q["A"] = .1
    second = calculate_hmmer_model_components(saved, background=q, probability_tolerance=.01)
    assert first["rows"][0]["mean_match_entropy"]["state"] == "present"
    assert first["rows"][0]["mean_match_relative_entropy"]["state"] == "missing"
    assert second["rows"][0]["mean_match_relative_entropy"]["state"] == "present"
    assert second["rows"][0]["mean_match_entropy"] == first["rows"][0]["mean_match_entropy"]
    assert saved == before
    json.dumps(second, allow_nan=False)


@pytest.mark.parametrize("fmt", ["hmmer_binary", "hmmer2_ascii"])
def test_old_saved_unsupported_extractions_remain_as_saved(fmt, monkeypatch):
    saved = extraction(fmt)
    saved.update(records=[], population={"decoded_count": None, "complete": False, "state": "unsupported"},
        issues=[{"code": "decoder_unavailable", "stage": "extraction", "record_key": None,
                 "line": None, "field": "format", "details": {"format": fmt}}])
    before = deepcopy(saved)
    monkeypatch.setattr(builtins, "open", lambda *a, **k: pytest.fail("Reopened old extraction"))
    result = calculate_hmmer_model_components(saved)
    assert result["rows"] == [] and checks(result, "population_complete") == ["not_applicable"]
    assert saved == before


@pytest.mark.parametrize("synthetic", [False, True])
def test_h2_statistics_keep_summary_but_do_not_assert_h3_occupancy_or_rounding(synthetic):
    content = synthetic_in_range_h2() if synthetic else (NATIVE / FILES["hmmer2_ascii"]).read_bytes()
    sheet = statistics_sheet(content, (NATIVE / "hmmstat_protein/stdout.log").read_bytes(), model_format="hmmer2_ascii")
    assert sheet["associations"][0]["state"] == "validated"
    result = calculate_hmmstat_components(sheet, **native_hmmstat_parameters("3.4", "amino"))
    r = result["rows"][0]
    c = r["components"]
    assert c["sequence_count"]["value"] == 3 and c["effective_sequence_count"]["state"] == "missing"
    for name in ("occupancy_sum", "entry_occupancy_sum", "weighted_emission_relative_entropy",
                 "mean_entry_transition_term", "position_relative_entropy", "composition_weight_sum", "composition_relative_entropy"):
        assert c[name]["state"] == "incompatible" and c[name]["value"] is None
    assert all(p["occupancy"]["state"] == p["entry_transition_term"]["state"] == "incompatible" for p in r["positions"])
    assert checks(result, "native_rounding_agreement") == ["unknown"] * 4
    assert len(r["native_comparisons"]) == 4
    assert all(n["native_value"] is not None and n["native_parameters_match"] is None for n in r["native_comparisons"])
    if synthetic:
        assert c["mean_match_entropy"]["state"] == "present"
        assert r["native_comparisons"][0]["difference"]["value"] is not None
    assert c["mean_match_entropy"] == result["model_components"]["rows"][0]["mean_match_entropy"]


@pytest.mark.parametrize("fmt", ["hmmer_binary", "hmmer2_ascii"])
def test_consensus_uses_shared_cells_and_preserves_generated_counts(fmt):
    result = calculate_hmmemit_components(emission_sheet(fmt))
    consensus = row(result, "consensus")
    assert consensus["actual_sequence"] == "ACDEFGHIKLMN"
    assert row(result, "model")["captured_sample_count"]["value"] == 1
    assert row(result, "generated_record")["length"]["value"] == 12
    assert checks(result, "consensus_length") == ["pass"]
    if fmt == "hmmer_binary":
        assert consensus["expected_sequence"] == "ACDEFGHIKLMN"
        assert checks(result, "consensus_agreement") == ["pass"]
        assert consensus["positions"][4]["maximum_probability"]["value"] == 0.666663408279419
    else:
        assert consensus["positions"][0]["maximum_probability"]["state"] == "incompatible"
        assert consensus["positions"][0]["maximum_probability"]["value"] is None
        assert consensus["positions"][4]["maximum_probability"]["state"] == "present"
        assert consensus["certain_mismatch_count"]["state"] == "incompatible"
        assert checks(result, "consensus_agreement") == ["unknown"]


def test_h2_in_range_consensus_retains_raw_nominal_result_without_native_equivalence():
    result = calculate_hmmemit_components(emission_sheet("hmmer2_ascii", content=synthetic_in_range_h2()))
    consensus = row(result, "consensus")
    assert len(consensus["expected_sequence"]) == 12
    assert all(p["maximum_probability"]["state"] == "present" for p in consensus["positions"])
    assert consensus["mismatch_count"]["value"] is not None
    assert consensus["certain_mismatch_count"]["value"] is None
    assert checks(result, "consensus_agreement") == ["unknown"]
    assert checks(result, "sample_population_count") == ["pass"]


@pytest.mark.parametrize("style", ["core", "alignment"])
def test_h2_generated_population_and_alignment_geometry_do_not_depend_on_entropy(style):
    result = calculate_hmmemit_components(emission_sheet("hmmer2_ascii", style))
    assert row(result, "model")["captured_sample_count"]["value"] == 3
    assert checks(result, "sample_population_count") == ["pass"]
    if style == "alignment":
        assert checks(result, "alignment_geometry") == checks(result, "rf_matches_model_length") == ["pass"]


def test_binary_artifact_body_validation_and_custody_are_separate():
    result = calculate_hmmer_artifact_components(native_sheet("hmmpress_success"))
    artifacts = {r["format"]: r for r in result["rows"] if r["kind"] == "artifact"}
    assert artifacts["hmmer_binary"]["decoded_record_count"]["value"] == 1
    assert artifacts["hmmer_binary"]["internal_content_state"] == "decoded"
    assert artifacts["hmmer_binary"]["authenticated_custody_state"] == "unknown"
    for fmt in ("ssi", "msv_profiles", "remaining_profiles"):
        assert artifacts[fmt]["internal_content_state"] == "unknown"
        assert artifacts[fmt]["decoded_record_count"]["value"] is None


@pytest.mark.parametrize("case", ["truncated", "domain", "partial"])
def test_binary_artifact_complete_invalid_vs_partial_capture(case):
    operation, inputs, outputs, bindings = native_case("hmmpress_success")
    content = outputs["binary_models"][0]["content"]
    if case == "truncated": content = content[:-2]
    elif case == "domain": content = content[:16] + struct.pack("<f", 1.5) + content[20:]
    outputs["binary_models"] = [payload(content, "binary_models", "output",
        completeness="partial" if case == "partial" else "complete")]
    result = calculate_hmmer_artifact_components(populate(operation, inputs, outputs, bindings))
    artifact = next(r for r in result["rows"] if r["kind"] == "artifact" and r["format"] == "hmmer_binary")
    assert artifact["internal_content_state"] == ("partial" if case == "partial" else "invalid")
    check = next(c for c in result["checks"] if c["code"] == "binary_internal_content" and c["row_key"] == artifact["row_key"])
    assert check["state"] == ("unknown" if case == "partial" else "fail")


def test_binary_unknown_layout_after_valid_prefix_keeps_internal_content_unknown():
    operation, inputs, outputs, bindings = native_case("hmmpress_success")
    content = outputs["binary_models"][0]["content"] + b"xxxx"
    outputs["binary_models"] = [payload(content, "binary_models", "output")]
    result = calculate_hmmer_artifact_components(populate(operation, inputs, outputs, bindings))
    artifact = next(r for r in result["rows"] if r["kind"] == "artifact" and r["format"] == "hmmer_binary")
    assert artifact["decoded_record_count"]["value"] == 1
    assert artifact["internal_content_state"] == "unknown"
    check = next(c for c in result["checks"] if c["code"] == "binary_internal_content" and c["row_key"] == artifact["row_key"])
    assert check["state"] == "unknown"


def test_h2_artifact_comparable_cells_do_not_claim_whole_model_equivalence():
    result = calculate_hmmer_artifact_components(native_sheet("hmmconvert_legacy2"))
    comparison = row(result, "model_comparison")
    assert comparison["compared_cell_count"]["value"] > 0
    assert comparison["max_absolute_probability_difference"]["state"] == "incompatible"
    assert checks(result, "model_probability_equivalence") == ["unknown"]
    assert not any(o["field"] == "header.m->m" for o in comparison["optional_fields"])
    assert any(o["field"] == "header.NULE" and o["state"] == "gained" for o in comparison["optional_fields"])
    assert any(i.get("population") == "common_core_probability_slots" for i in comparison["output_cell_count"]["inputs"])


@pytest.mark.parametrize("name", ["hmmconvert_binary", "hmmconvert_binary_to_ascii"])
def test_retained_binary_optional_metadata_uses_typed_values_without_inventing_command_log(name):
    sheet = native_sheet(name)
    before = deepcopy(sheet)
    result = calculate_hmmer_artifact_components(sheet)
    optional = {o["field"]: o for o in row(result, "model_comparison")["optional_fields"]}
    effn = optional["header.EFFN"]
    assert effn["state"] == "retained"
    expected = ([["3.000000"]], [["3.0"]])
    if name == "hmmconvert_binary_to_ascii":
        expected = expected[::-1]
    assert (effn["source_value"], effn["output_value"]) == expected
    assert "header.COM" not in optional
    for record in sheet["input_records"] + sheet["output_records"]:
        assert record["effective_sequence_count"] == 3.0
        assert not any(h["tag"] == "COM" for h in record["headers"])
        if "representation" in record:
            fields = {f["field"]: f for f in record["representation"]["native_fields"]}
            assert fields["COM.length"]["value"] == 0
            assert fields["COM"]["value"] is None
            assert fields["COM"]["state"] == "native_missing_sentinel"
    assert sheet == before


def synthetic_command_log_sheet(ascii_commands, binary_log, mode, case):
    """Construct grammar evidence in memory; retain the original native files.

    p7_hmmfile.c:multiline writes numbered ASCII lines; write_bin_string stores
    the unnumbered log with its NUL and byte count. Re-extract each constructed
    artifact so all digests, record identities and locators describe its bytes.
    """
    ascii_original = (NATIVE / FILES["hmmer3_ascii"]).read_bytes()
    binary_original = (NATIVE / FILES["hmmer_binary"]).read_bytes()
    original = extraction("hmmer_binary", binary_original)["records"][0]
    fields = {f["field"]: f for f in original["representation"]["native_fields"]}
    size, log = fields["COM.length"], fields["COM"]
    assert size["value"] == 0 and log["state"] == "native_missing_sentinel"
    headers = b"".join(f"COM   [{i}] {command}\n".encode()
                       for i, command in enumerate(ascii_commands, 1))
    assert not any(line.startswith(b"COM ") for line in ascii_original.splitlines())
    assert ascii_original.count(b"NSEQ  ") == 1
    ascii_content = ascii_original.replace(b"NSEQ  ", headers + b"NSEQ  ", 1)
    log_bytes = binary_log.encode() + b"\0"
    binary_content = (binary_original[:size["byte_start"]]
        + struct.pack("<i", len(log_bytes)) + log_bytes + binary_original[log["byte_end"]:])
    source, output = (ascii_content, binary_content) if mode == "binary" else (binary_content, ascii_content)
    supplied = []
    for content, role, direction in [(source, "models", "input"), (output, "converted_models", "output")]:
        oid = f"synthetic/command-log/{mode}/{case}/{direction}/{role}/0"
        item = payload(content, role, direction, oid=oid)
        item["occurrence"]["artifact_ref"] = "synthetic:" + oid
        supplied.append(item)
    operation = {"program": "hmmconvert", "mode": mode, "engine_version": "synthetic-format-fixture", "settings": {}}
    sheet = populate(operation, {"models": [supplied[0]]}, {"converted_models": [supplied[1]]})
    return sheet, {item["occurrence"]["occurrence_id"]: item for item in supplied}


@pytest.mark.parametrize("mode", ["binary", "ascii"])
@pytest.mark.parametrize("case", ["equivalent", "changed_text", "reordered", "line_boundaries"])
def test_synthetic_binary_command_log_comparison_preserves_meaning_and_raw_sources(mode, case, monkeypatch):
    commands = ("hmmbuild --amino synthetic.hmm synthetic.sto", "hmmconvert -b synthetic.hmm")
    binary_log = "\n".join(commands)
    if case == "changed_text":
        binary_log = binary_log.replace("synthetic.sto", "changed.sto")
    elif case == "reordered":
        binary_log = "\n".join(reversed(commands))
    elif case == "line_boundaries":
        binary_log = "hmmbuild --amino synthetic.hmm\nsynthetic.sto hmmconvert -b synthetic.hmm"
        assert binary_log.split() == "\n".join(commands).split()
    sheet, supplied = synthetic_command_log_sheet(commands, binary_log, mode, case)
    assert sheet["issues"] == []
    ascii_tokens = [[f"[{i}]", *command.split()] for i, command in enumerate(commands, 1)]
    binary_tokens = [binary_log.split()]
    for extracted in sheet["model_extractions"]:
        assert extracted["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
        occurrence = extracted["occurrence"]
        item = supplied[occurrence["occurrence_id"]]
        assert occurrence == item["occurrence"]
        record = extracted["records"][0]
        assert record["record_key"] == occurrence["occurrence_id"] + "#model/0"
        assert record["locator"]["artifact_ref"] == occurrence["artifact_ref"]
        assert (record["locator"]["byte_start"], record["locator"]["byte_end"]) == (0, len(item["content"]))
        headers = [h for h in record["headers"] if h["tag"] == "COM"]
        if extracted["format"] == "hmmer_binary":
            fields = {f["field"]: f for f in record["representation"]["native_fields"]}
            log = fields["COM"]
            assert log["value"] == headers[0]["value"] == binary_log
            assert log["state"] == "present" and headers[0]["line"] is None
            assert bytes.fromhex(log["raw_hex"]) == binary_log.encode() + b"\0"
            assert item["content"][log["byte_start"]:log["byte_end"]] == bytes.fromhex(log["raw_hex"])
            assert fields["COM.length"]["value"] == len(binary_log.encode()) + 1
        else:
            assert [h["tokens"] for h in headers] == ascii_tokens
            for i, (header, command) in enumerate(zip(headers, commands), 1):
                assert header["value"] == f"[{i}] {command}"
                assert item["content"].splitlines()[header["line"] - 1] == f"COM   [{i}] {command}".encode()
    saved = json.loads(json.dumps(sheet))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved command-log comparison attempted acquisition")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    result = calculate_hmmer_artifact_components(saved)
    comparison = row(result, "model_comparison")
    optional = next(o for o in comparison["optional_fields"] if o["field"] == "header.COM")
    expected_source, expected_output = (ascii_tokens, binary_tokens) if mode == "binary" else (binary_tokens, ascii_tokens)
    assert optional == {"field": "header.COM", "source_present": True, "output_present": True,
        "source_value": expected_source, "output_value": expected_output,
        "state": "retained" if case == "equivalent" else "changed"}
    assert comparison["source_record_key"] == saved["input_records"][0]["record_key"]
    assert comparison["output_record_key"] == saved["output_records"][0]["record_key"]
    assert saved == before == sheet
