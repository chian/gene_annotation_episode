"""Pure views of retained HOMER bytes and explicitly synthetic parser controls.

The ZIP contains original data from the completed 428 engineering native run
and failed 426 prefix. Its Source/Artifact descriptors below are engineered
inputs to a pure parser, not runtime producer or receipt evidence. No native
program, acquisition, Store publication or new biological outcome is created.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import zipfile

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.homer_motif_contracts import (
    OPERATION, homer_record_schema, validate_homer_selector, validate_homer_sheet,
)
from gene_annotation_episode.homer_motif_measurements import (
    calculate_homer_components, parse_homer_motif_sheet, project_homer_return,
)


FIXTURE = Path(__file__).with_name("fixtures") / "homer_v51_selected_regions.zip"
FIXTURE_SHA256 = "f4aad8991e2bceb7b555726891c4fbaf9b6c6eabfaa1f903ea629631dc9c7a68"
SOURCE = "source_" + "a" * 24
HEADER = ("Motif Name\tConsensus\tP-value\tLog P-value\tq-value (Benjamini)\t"
    "# of Target Sequences with Motif(of 2)\t% of Target Sequences with Motif\t"
    "# of Background Sequences with Motif(of 3)\t% of Background Sequences with Motif\n")
ROW = "engineered\tAC\t1e-1\t-2.303e+00\t0.0000\t1.0\t50.00%\t0.0\t0.00%\n"
PWM = (">AC\tengineered\t4.500000\t-2.302585\t0\tT:1.0(50.00%),B:0.0(0.00%),P:1e-1\n"
    "0.333\t0.333\t0.333\t0.000\n0.001\t0.001\t0.001\t0.997\n")


@pytest.fixture(scope="module", autouse=True)
def no_native_work():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Pure HOMER measurement tests must not execute programs")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(subprocess, "run", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(os, "system", forbidden)
        yield


@pytest.fixture(scope="module")
def retained():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256
    with zipfile.ZipFile(FIXTURE) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == len(set(names)) == 89
        manifest = json.loads(archive.read("manifest.json"))
        files = {name: archive.read(name) for name in names if name != "manifest.json"}
    assert len(files) == 88
    assert sum(map(len, files.values())) == 452666
    assert set(files) == set(manifest["files"])
    for name, raw in files.items():
        assert manifest["files"][name] == {
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    return manifest, files


def descriptor(role, path, raw, *, original_size=None, state="complete"):
    """Engineering metadata for the exact supplied bytes; no authority grant."""
    digest = hashlib.sha256(raw).hexdigest()
    return {"role": role, "native_relative_path": path, "content": raw,
        "artifact": {"raw_artifact_ref": "artifact_" + digest,
            "source_ref": "source_" + digest[:24], "sha256": digest,
            "size_bytes": len(raw)},
        "capture": {"state": state, "byte_start_0based": 0,
            "byte_end_0based_exclusive": len(raw),
            "original_size_bytes": len(raw) if original_size is None else original_size}}


def case_files(retained, case="successful"):
    _, data = retained
    result = []
    for member, raw in data.items():
        prefix, path = member.split("/", 1)
        if prefix != case:
            continue
        if path == "knownResults.txt":
            role = "known_results"
        elif path.startswith("knownResults/"):
            role = "known_pwm"
        elif path.startswith("homerResults/"):
            role = "denovo_nonredundant_pwm"
        elif path == "homerMotifs.all.motifs":
            role = "denovo_combined_pwm"
        elif path.startswith("homerMotifs.motifs"):
            role = "denovo_pwm"
        else:
            role = {"seq.tsv": "sequence_table", "group.adj": "group_weights",
                "seq.autonorm.tsv": "normalization_table", "native_stderr.txt": "native_log"}[path]
        result.append(descriptor(role, path, raw))
    return result


def invocation():
    return {"invocation_id": "retained-engineering-fixture", "operation": OPERATION,
        "selected_window_bp": 200, "selected_motif_lengths": [8, 10, 12],
        "native_parameters": {"background": "explicit_supplied_BED", "statistic": "binomial",
            "gc_weighting": True, "nlen": 3, "threads": 1},
        "software": [{"name": "HOMER", "version": "v5.1 with recorded extractor/SVG repairs",
            "sha256": "c900b47fdf053c3105dab51fd4f003f46418d5deb2dfb5523d85147ac41a1d30"}]}


def execution(*, failed=False):
    outcome = "failed" if failed else "succeeded"
    return {"wrapper_returncode": 0, "wrapper_outcome": "succeeded",
        "known_outcome": outcome, "denovo_outcome": outcome}


def parse(files, *, failed=False):
    return parse_homer_motif_sheet(files, invocation=invocation(), execution=execution(failed=failed))


@pytest.fixture(scope="module")
def complete_sheet(retained):
    return parse(case_files(retained))


def series_for(sheet, role, path=None):
    paths = {row["file_id"]: row["native_relative_path"] for row in sheet["files"]}
    matches = [series for series in sheet["series"]
        if series["role"] == role and (path is None or paths[series["file_id"]] == path)]
    assert len(matches) == 1
    return matches[0]


def selection(*series, offset=0, limit=10000):
    return {"series_ids": [row["series_id"] for row in series], "offset": offset, "limit": limit}


def number(row, field, representation=0):
    return row["representations"][representation]["numbers"][field]


def pwm_records(raw):
    """Read only the fixture's valid header/matrix boundaries as a golden oracle."""
    records = []
    for line in raw.decode().splitlines():
        if line.startswith(">"):
            records.append((line[1:].split("\t"), []))
        else:
            records[-1][1].append(line.split("\t"))
    return records


def test_retained_fixture_manifest_and_original_precision(retained):
    manifest, files = retained
    assert manifest["cases"]["successful"]["original_run"] == "check428_homer_repaired_selected_regions_native"
    assert manifest["cases"]["failed"]["original_run"] == "check426_homer_selected_regions_native"
    rows = [line.split("\t") for line in files["successful/knownResults.txt"].decode().splitlines()]
    assert len(rows[1:]) == 1049
    assert rows[0][5] == "# of Target Sequences with Motif(of 100)"
    assert rows[0][7] == "# of Background Sequences with Motif(of 956)"
    assert rows[1][2:] == ["1e-78", "-1.800e+02", "0.0000", "100.0", "100.00%", "158.8", "16.61%"]
    duplicates = Counter(tuple(row[:2]) for row in rows[1:])
    assert sorted(value for value in duplicates.values() if value > 1) == [2, 2]
    assert len([name for name in files if name.startswith("successful/knownResults/")]) == 53


def test_complete_known_rows_preserve_duplicates_and_both_precisions(retained, complete_sheet):
    _, files = retained
    known = series_for(complete_sheet, "known_results")
    original_rows = [line.split("\t") for line in files["successful/knownResults.txt"].decode().splitlines()[1:]]
    rows = known["observations"]
    assert len(rows) == 1049
    assert [row["ordinal_0based"] for row in rows] == list(range(1049))
    assert [row["raw_fields"] for row in rows] == original_rows
    assert len({row["occurrence_id"] for row in rows}) == 1049
    for a, b in ((138, 139), (666, 667)):
        assert rows[a]["raw_fields"] == rows[b]["raw_fields"]
        assert rows[a]["occurrence_id"] != rows[b]["occurrence_id"]
    nf1 = rows[0]
    assert [rep["kind"] for rep in nf1["representations"]] == ["known_table", "native_pwm"]
    assert number(nf1, "ln_p_value")["number"]["raw_token"] == "-1.800e+02"
    assert number(nf1, "ln_p_value", 1)["number"]["raw_token"] == "-180.016288"
    assert number(nf1, "site_threshold")["availability"] == "not_provided"
    assert number(nf1, "site_threshold", 1)["number"]["raw_token"] == "6.734334"
    assert number(nf1, "q_value")["number"]["value"] == 0
    assert number(nf1, "q_value")["number"]["raw_token"] == "0.0000"
    assert number(nf1, "q_value")["precision"] == "fixed_4"
    assert number(nf1, "q_value", 1)["availability"] == "not_provided"
    assert known["displayed_totals"]["target"]["value"] == 100
    assert known["displayed_totals"]["background"]["value"] == 956
    assert known["displayed_totals"]["meaning"] == "wrapper_inferred_from_first_rounded_motif"
    assert len(complete_sheet["sidecars"]) == 53
    assert all(sidecar["state"] == "linked" for sidecar in complete_sheet["sidecars"])
    assert rows[53]["pwm_state"] == "not_provided"


@pytest.mark.parametrize("length,expected_count", [(8, 7), (10, 10), (12, 10)])
def test_complete_native_pwm_order_and_every_cell(retained, complete_sheet, length, expected_count):
    _, files = retained
    path = "homerMotifs.motifs" + str(length)
    series = series_for(complete_sheet, "denovo_pwm", path)
    expected = pwm_records(files["successful/" + path])
    assert len(series["observations"]) == len(expected) == expected_count
    for ordinal, (row, (header, matrix)) in enumerate(zip(series["observations"], expected)):
        assert row["ordinal_0based"] == ordinal
        assert row["consensus"] == header[0] and row["name"] == header[1]
        assert row["pwm_state"] == "provided"
        representation = row["representations"][0]
        assert representation["raw_fields"] == header
        assert [item["ordinal_0based"] for item in representation["pwm_rows"]] == list(range(len(matrix)))
        assert [item["raw_fields"] for item in representation["pwm_rows"]] == matrix
        assert [[cell["raw_token"] for cell in item["cells"]] for item in representation["pwm_rows"]] == matrix
        assert [[cell["value"] for cell in item["cells"]] for item in representation["pwm_rows"]] == [
            [float(Decimal(token)) for token in line] for line in matrix]
    if length == 8:
        first = series["observations"][0]
        assert number(first, "site_threshold")["number"]["raw_token"] == "8.236954"
        assert number(first, "ln_p_value")["number"]["raw_token"] == "-466.553334"
        assert number(first, "p_value")["number"]["raw_token"] == "1e-202"
        assert number(first, "target_weight")["number"]["value"] == 100
        assert number(first, "target_weight")["number"]["value"] != 201
        log = files["successful/native_stderr.txt"]
        assert b"T:201.0" in log and b"P:1e-162" in log


def test_all_known_sidecar_and_combined_models_retain_ordered_native_cells(retained, complete_sheet):
    _, files = retained
    observations = {sidecar["file_id"]: sidecar["observations"] for sidecar in complete_sheet["sidecars"]}
    observations.update({series["file_id"]: series["observations"] for series in complete_sheet["series"]})
    examined = Counter()
    for file in complete_sheet["files"]:
        role = file["role"]
        if role not in {"known_pwm", "denovo_combined_pwm", "denovo_nonredundant_pwm"}:
            continue
        golden = pwm_records(files["successful/" + file["native_relative_path"]])
        actual = observations[file["file_id"]]
        assert len(actual) == len(golden)
        for ordinal, (row, (header, matrix)) in enumerate(zip(actual, golden)):
            assert row["ordinal_0based"] == ordinal
            assert (row["consensus"], row["name"]) == tuple(header[:2])
            representation = row["representations"][0]
            assert representation["raw_fields"] == header
            assert [item["raw_fields"] for item in representation["pwm_rows"]] == matrix
            assert [[cell["raw_token"] for cell in item["cells"]] for item in representation["pwm_rows"]] == matrix
        examined[role] += len(actual)
    assert examined == {"known_pwm": 53, "denovo_combined_pwm": 27, "denovo_nonredundant_pwm": 19}


def test_retained_native_auxiliary_values_keep_units_and_unknown_coordinate_origin(complete_sheet):
    first = series_for(complete_sheet, "denovo_pwm", "homerMotifs.motifs8")["observations"][0]
    representation = first["representations"][0]
    values = representation["native_auxiliary_measurements"]
    assert [value["field"] for value in values] == ["Tpos", "Tstd", "Bpos", "Bstd", "StrandBias", "Multiplicity"]
    assert [value["reported"]["number"]["raw_token"] for value in values] == ["84.7", "40.1", "108.1", "70.6", "7.6", "2.01"]
    assert [value["reported"]["precision"] for value in values] == ["fixed_1"] * 5 + ["fixed_2"]
    assert representation["native_auxiliary_absent_fields"] == []
    for value in values[:4]:
        assert value["reported"]["unit"] == "bp"
        assert value["coordinate_origin"] == "native_scan_offset_not_authenticated"
    spread = values[1]
    assert spread["definition"] == "native_position_spread"
    assert spread["weighting"] == "squared_weighted_residual_divided_by_site_weight_sum"
    assert "not_standard_error_of_mean" in spread["qualifications"]
    assert values[4]["reported"]["unit"] == "log2_ratio"
    assert "native_small_mass_plus_minus_10_or_zero_sentinels" in values[4]["qualifications"]
    assert values[5]["reported"]["unit"] == "weighted_sites_per_weighted_positive_sequence"
    assert values[5]["denominator"] == "weighted_target_sequences_with_sites"
    assert "native_default_one_if_denominator_le_0_01" in values[5]["qualifications"]
    known = series_for(complete_sheet, "known_results")["observations"][0]
    for rep in known["representations"]:
        assert rep["native_auxiliary_measurements"] == []
        assert set(rep["native_auxiliary_absent_fields"]) == {"Tpos", "Tstd", "Bpos", "Bstd", "StrandBias", "Multiplicity"}


def test_repeated_native_auxiliary_fields_preserve_both_occurrences():
    lines = PWM.splitlines()
    lines[0] += "\tTpos:1.0,Tpos:2.0,Multiplicity:1.00"
    row = parse([descriptor("known_pwm", "knownResults/known1.motif",
        ("\n".join(lines) + "\n").encode())])["sidecars"][0]["observations"][0]
    rep = row["representations"][0]
    assert [(value["field"], value["reported"]["number"]["raw_token"]) for value in rep["native_auxiliary_measurements"]] == [
        ("Tpos", "1.0"), ("Tpos", "2.0"), ("Multiplicity", "1.00")]
    assert "native_auxiliary_field_repeated" in rep["issues"]
    assert row["parse_state"] == "qualified"


def test_native_auxiliary_zero_missing_and_underflow_remain_distinct():
    lines = PWM.splitlines()
    lines[0] += "\tTpos:0.0,Tstd:NA,Bpos:1e-999,StrandBias:0.0"
    rep = parse([descriptor("known_pwm", "knownResults/known1.motif",
        ("\n".join(lines) + "\n").encode())])["sidecars"][0]["observations"][0]["representations"][0]
    values = {value["field"]: value["reported"]["number"] for value in rep["native_auxiliary_measurements"]}
    assert values["Tpos"]["state"] == "available" and values["Tpos"]["value"] == 0
    assert values["Tstd"]["state"] == "not_measured" and values["Tstd"]["value"] is None
    assert values["Bpos"]["token_kind"] == "underflow" and values["Bpos"]["value"] is None
    assert set(rep["native_auxiliary_absent_fields"]) == {"Bstd", "Multiplicity"}


def test_actual_populations_and_independent_decimal_weight_sums(retained, complete_sheet):
    _, files = retained
    populations = complete_sheet["populations"]
    assert populations["state"] == "complete"
    assert len(populations["sequence_rows"]) == len(populations["group_rows"]) == 1100
    assert {row["length_bp"] for row in populations["sequence_rows"]} == {201}
    assert Counter(row["group"] for row in populations["memberships"]) == {"target": 100, "background": 1000}
    components = calculate_homer_components(complete_sheet, selector=selection())
    facts = components["population_facts"]
    assert facts["selected_window_bp"] == 200 and facts["observed_sequence_lengths_bp"] == [201]
    assert facts["unique_joined_target_members"] == 100
    assert facts["unique_joined_background_members"] == 1000
    assert facts["reported_weight_completeness"] == {"target": "complete", "background": "complete"}
    assert facts["meaning"] == "captured_input_occurrences_not_effective_native_denominators"
    expected = {"target": Decimal(0), "background": Decimal(0)}
    for line in files["successful/group.adj"].decode().splitlines():
        _, group, token = line.split("\t")
        expected["background" if group == "0" else "target"] += Decimal(token)
    for row in components["reported_input_weight_sums"]:
        cell = row["cell"]
        assert cell["state"] == "available" and cell["origin"] == "calculated"
        assert row["meaning"] == "reported_input_weight_sum" and row["basis"] == "derived_from_reported_weights"
        assert cell["unit"] == "relative_weight" and cell["numerator"] is cell["denominator"] is None
        assert abs(Decimal.from_float(cell["value"]) - expected[row["group"]]) <= Decimal.from_float(math.ulp(cell["value"]))
    assert expected["background"] != Decimal(956)


def test_saved_selection_preserves_caller_series_order_and_original_occurrences(complete_sheet):
    known = series_for(complete_sheet, "known_results")
    d12 = series_for(complete_sheet, "denovo_pwm", "homerMotifs.motifs12")
    d8 = series_for(complete_sheet, "denovo_pwm", "homerMotifs.motifs8")
    selector = selection(d12, known, d8, offset=9, limit=4)
    saved = json.loads(json.dumps(complete_sheet, allow_nan=False))
    before = deepcopy(saved)
    result = calculate_homer_components(saved, selector=selector)
    assert saved == before
    assert result["selector"] == selector
    assert [s["series_id"] for s in result["selected_series"]] == selector["series_ids"]
    assert [[r["ordinal_0based"] for r in s["observations"]] for s in result["selected_series"]] == [[9], [0, 1, 2], []]
    assert result["selected_series"][0]["observations"] == [d12["observations"][9]]
    assert result["selected_series"][1]["observations"] == known["observations"][:3]
    assert [(x["captured_occurrences"], x["selected_occurrences"]) for x in result["counts"]] == [(10, 1), (1049, 3), (7, 0)]
    assert project_homer_return(result, source_ref=SOURCE)["selected_series"][1]["observations"][0]["raw_fields"] == known["observations"][0]["raw_fields"]


def test_projection_is_source_only_and_schema_valid(complete_sheet):
    component = calculate_homer_components(complete_sheet,
        selector=selection(series_for(complete_sheet, "known_results"), limit=1))
    before = deepcopy(component)
    public = project_homer_return(component, source_ref=SOURCE)
    assert component == before and public["source_ref"] == SOURCE
    def check(value):
        if isinstance(value, dict):
            assert not set(value) & {"source_location", "location", "file_id", "evidence", "requirement_ids", "raw_artifact_ref"}
            for child in value.values(): check(child)
        elif isinstance(value, list):
            for child in value: check(child)
    check(public)
    for kind, value in (("Sheet", complete_sheet), ("Selector", component["selector"]),
            ("Components", component), ("Return", public)):
        Draft202012Validator(homer_record_schema(kind)).validate(value)


def test_malformed_known_row_keeps_original_ordinal_and_later_valid_row():
    raw = (HEADER + ROW + "bad\tonly\n" + ROW.replace("engineered", "later")).encode()
    rows = parse([descriptor("known_results", "knownResults.txt", raw)])["series"][0]["observations"]
    assert [row["ordinal_0based"] for row in rows] == [0, 1, 2]
    assert [row["parse_state"] for row in rows] == ["complete", "malformed", "complete"]
    assert rows[1]["raw_fields"] == ["bad", "only"] and rows[2]["name"] == "later"


def test_truncated_known_prefix_keeps_complete_earlier_records():
    raw = (HEADER + ROW + "later\tAC\t1e-").encode()
    file = descriptor("known_results", "knownResults.txt", raw, state="truncated", original_size=len(raw) + 30)
    series = parse([file])["series"][0]
    assert series["capture_state"] == "truncated"
    assert [row["ordinal_0based"] for row in series["observations"]] == [0, 1]
    assert series["observations"][0]["raw_fields"] == ROW.rstrip().split("\t")
    assert series["observations"][0]["parse_state"] == "complete"
    assert series["observations"][1]["parse_state"] == "truncated"


def test_truncated_pwm_preserves_preceding_complete_model():
    first = (">AAAAAAAA\tfirst\t4.500000\t-2.302585\t0\tT:1.0(50.00%),B:0.0(0.00%),P:1e-1\n"
        + "0.250\t0.250\t0.250\t0.250\n" * 8)
    raw = (first + ">AAAAAAAA\tpartial\t4.500000\t-2.302585\t0\tT:1.0(50.00%),B:0.0(0.00%),P:1e-1\n0.333\t0.").encode()
    series = parse([descriptor("denovo_pwm", "homerMotifs.motifs8", raw,
        state="truncated", original_size=len(raw) + 30)])["series"][0]
    assert len(series["observations"]) == 2
    assert series["observations"][0]["pwm_state"] == "provided"
    assert series["observations"][0]["representations"][0]["pwm_rows"][0]["raw_fields"] == ["0.250"] * 4
    assert series["observations"][1]["parse_state"] == "truncated"


def test_missing_sidecar_and_q_stay_not_provided_and_pwm_is_not_renormalized():
    known = parse([descriptor("known_results", "knownResults.txt", (HEADER + ROW).encode())])["series"][0]["observations"][0]
    assert known["pwm_state"] == "not_provided" and len(known["representations"]) == 1
    pwm = parse([descriptor("known_pwm", "knownResults/known1.motif", PWM.encode())])["sidecars"][0]
    assert pwm["state"] == "unlinked"
    representation = pwm["observations"][0]["representations"][0]
    assert representation["numbers"]["q_value"] == {"availability": "not_provided", "number": None,
        "unit": "probability", "precision": "not_provided"}
    cells = representation["pwm_rows"][0]["cells"]
    assert [cell["value"] for cell in cells] == [0.333, 0.333, 0.333, 0]
    assert sum(Decimal(cell["raw_token"]) for cell in cells) == Decimal("0.999")


def test_complete_eight_base_header_with_only_seven_rows_is_not_padded():
    raw = (">AAAAAAAA\tseven-of-eight\t4.500000\t-2.302585\t0\tT:1.0(50.00%),B:0.0(0.00%),P:1e-1\n"
        + "0.250\t0.250\t0.250\t0.250\n" * 7).encode()
    row = parse([descriptor("denovo_pwm", "homerMotifs.motifs8", raw)])["series"][0]["observations"][0]
    assert row["consensus"] == "AAAAAAAA"
    assert len(row["representations"][0]["pwm_rows"]) == 7
    assert row["pwm_state"] == "partial" and row["parse_state"] != "complete"


def test_printed_zero_precision_is_not_invented_for_shorter_token():
    short = ROW.rstrip("\n").split("\t")
    short[4] = "0"
    rows = parse([descriptor("known_results", "knownResults.txt",
        (HEADER + "\t".join(short) + "\n" + ROW).encode())])["series"][0]["observations"]
    q_short, q_fixed = number(rows[0], "q_value"), number(rows[1], "q_value")
    assert q_short["number"]["value"] == q_fixed["number"]["value"] == 0
    assert (q_short["number"]["raw_token"], q_short["precision"]) == ("0", "native_token")
    assert (q_fixed["number"]["raw_token"], q_fixed["precision"]) == ("0.0000", "fixed_4")
    assert rows[0]["parse_state"] == "qualified"


@pytest.mark.parametrize("token,kind,state", [("not-a-number", "malformed", "failed"),
    ("NaN", "nonfinite", "failed"), ("inf", "nonfinite", "failed"),
    ("1e999", "overflow", "failed"), ("1e-999", "underflow", "failed"),
    ("NA", "native_na", "not_measured"), ("", "blank", "missing")])
def test_bad_or_unrepresentable_native_p_is_never_observed_zero(token, kind, state):
    fields = ROW.rstrip("\n").split("\t")
    fields[2] = token
    row = parse([descriptor("known_results", "knownResults.txt", (HEADER + "\t".join(fields) + "\n").encode())])["series"][0]["observations"][0]
    actual = number(row, "p_value")["number"]
    assert actual["raw_token"] == token and actual["token_kind"] == kind and actual["state"] == state
    assert actual["value"] is None and row["parse_state"] == "qualified"


def test_invalid_probability_retains_finite_value_with_incompatible_state():
    raw = (HEADER + ROW.replace("1e-1", "-0.5")).encode()
    row = parse([descriptor("known_results", "knownResults.txt", raw)])["series"][0]["observations"][0]
    assert number(row, "p_value")["number"]["state"] == "incompatible"
    assert number(row, "p_value")["number"]["value"] == -0.5


def test_zero_reported_weights_are_valid_without_inventing_effective_mass():
    sheet = parse([descriptor("sequence_table", "seq.tsv", b"T\tAC\nB\tGT\n"),
        descriptor("group_weights", "group.adj", b"T\t1\t0.000000\nB\t0\t0.000000\n")])
    assert sheet["populations"]["state"] == "complete"
    result = calculate_homer_components(sheet, selector=selection())
    assert {x["group"]: (x["cell"]["state"], x["cell"]["value"]) for x in result["reported_input_weight_sums"]} == {
        "target": ("available", 0), "background": ("available", 0)}
    assert result["population_facts"]["unique_joined_target_members"] == result["population_facts"]["unique_joined_background_members"] == 1


def test_native_extra_group_fields_are_retained_without_changing_weight():
    sheet = parse([descriptor("sequence_table", "seq.tsv", b"T\tAC\nB\tGT\n"),
        descriptor("group_weights", "group.adj", b"T\t1\t0.250000\textra\nB\t0\t0.750000\textra\n")])
    assert sheet["populations"]["state"] == "complete"
    assert sheet["populations"]["group_rows"][0]["raw_fields"] == ["T", "1", "0.250000", "extra"]
    assert [row["group"] for row in sheet["populations"]["group_rows"]] == ["target", "background"]
    components = calculate_homer_components(sheet, selector=selection())
    assert {row["group"]: row["cell"]["value"] for row in components["reported_input_weight_sums"]} == {
        "target": 0.25, "background": 0.75}


def test_nonbinary_native_group_code_is_qualified_unknown():
    # Native optimizeArray and motifScan classify code 2 differently.
    sheet = parse([descriptor("sequence_table", "seq.tsv", b"T\tAC\nB\tGT\n"),
        descriptor("group_weights", "group.adj", b"T\t2\t0.250000\nB\t0\t0.750000\n")])
    group = sheet["populations"]["group_rows"][0]
    assert group["raw_fields"] == ["T", "2", "0.250000"] and group["group"] is None
    assert group["weight"]["raw_token"] == "0.250000"
    assert sheet["populations"]["state"] == "partial"
    components = calculate_homer_components(sheet, selector=selection())
    assert all(row["cell"]["value"] is None for row in components["reported_input_weight_sums"])


def test_unreported_optional_weight_does_not_become_one_for_summary():
    sheet = parse([descriptor("sequence_table", "seq.tsv", b"T\tAC\nB\tGT\n"),
        descriptor("group_weights", "group.adj", b"T\t1\nB\t0\t0.500000\n")])
    assert sheet["populations"]["group_rows"][0]["weight"] is None
    assert sheet["populations"]["group_rows"][0]["raw_fields"] == ["T", "1"]
    components = calculate_homer_components(sheet, selector=selection())
    cells = {row["group"]: row["cell"] for row in components["reported_input_weight_sums"]}
    assert cells["target"]["state"] != "available" and cells["target"]["value"] is None
    assert cells["background"]["state"] == "available" and cells["background"]["value"] == 0.5


@pytest.mark.parametrize("token", ["NaN", "1e-999", "-1"])
def test_invalid_group_weight_never_disappears_into_available_sum(token):
    sheet = parse([descriptor("sequence_table", "seq.tsv", b"T\tAC\nB\tGT\n"),
        descriptor("group_weights", "group.adj", ("T\t1\t" + token + "\nB\t0\t1.000000\n").encode())])
    actual = sheet["populations"]["group_rows"][0]["weight"]
    assert actual["raw_token"] == token and actual["state"] != "available"
    components = calculate_homer_components(sheet, selector=selection())
    cells = {row["group"]: row["cell"] for row in components["reported_input_weight_sums"]}
    assert cells["target"]["state"] != "available" and cells["target"]["value"] is None
    assert cells["background"]["state"] == "available" and cells["background"]["value"] == 1


@pytest.mark.parametrize("weight", [None, "NaN", "1e-999"])
def test_bad_or_missing_weight_preserves_known_physical_memberships(weight):
    background = "B\t0\n" if weight is None else "B\t0\t" + weight + "\n"
    sheet = parse([descriptor("sequence_table", "seq.tsv", b"T\tAC\nB\tGT\n"),
        descriptor("group_weights", "group.adj", ("T\t1\t1.000000\n" + background).encode())])
    components = calculate_homer_components(sheet, selector=selection())
    facts = components["population_facts"]
    assert facts["captured_sequence_occurrences"] == facts["captured_group_occurrences"] == 2
    assert facts["unique_joined_target_members"] == facts["unique_joined_background_members"] == 1
    assert facts["reported_weight_completeness"] == {"target": "complete", "background": "unavailable"}
    cells = {row["group"]: row["cell"] for row in components["reported_input_weight_sums"]}
    assert cells["target"]["state"] == "available" and cells["target"]["value"] == 1
    assert cells["background"]["state"] != "available" and cells["background"]["value"] is None


def test_ambiguous_member_id_qualifies_weight_sum_instead_of_deduplicating():
    sheet = parse([descriptor("sequence_table", "seq.tsv", b"same\tAC\nsame\tGT\n"),
        descriptor("group_weights", "group.adj", b"same\t1\t1.000000\n")])
    assert len(sheet["populations"]["sequence_rows"]) == 2
    assert sheet["populations"]["memberships"][0]["state"] == "ambiguous"
    component = calculate_homer_components(sheet, selector=selection())
    assert component["population_facts"]["state"] == "partial"
    assert all(x["cell"]["state"] != "available" and x["cell"]["value"] is None for x in component["reported_input_weight_sums"])


def test_ambiguous_known_sidecar_does_not_choose_first_table():
    sheet = parse([descriptor("known_results", "one/knownResults.txt", (HEADER + ROW).encode()),
        descriptor("known_results", "two/knownResults.txt", (HEADER + ROW).encode()),
        descriptor("known_pwm", "knownResults/known1.motif", PWM.encode())])
    assert sheet["sidecars"][0]["state"] == "ambiguous"
    assert all(row["pwm_state"] != "provided" and len(row["representations"]) == 1
        for series in sheet["series"] for row in series["observations"])


def test_two_sidecars_for_same_native_rank_remain_ambiguous():
    sheet = parse([descriptor("known_results", "knownResults.txt", (HEADER + ROW).encode()),
        descriptor("known_pwm", "a/known1.motif", PWM.encode()),
        descriptor("known_pwm", "b/known1.motif", PWM.encode())])
    assert [sidecar["state"] for sidecar in sheet["sidecars"]] == ["ambiguous", "ambiguous"]
    row = sheet["series"][0]["observations"][0]
    assert len(row["representations"]) == 1 and row["pwm_state"] != "provided"


@pytest.mark.parametrize("mutate", ["sha256", "size_bytes", "content"])
def test_byte_identity_conflict_rejects_capture(mutate):
    value = descriptor("known_results", "knownResults.txt", (HEADER + ROW).encode())
    if mutate == "sha256": value["artifact"]["sha256"] = "0" * 64
    elif mutate == "size_bytes": value["artifact"]["size_bytes"] += 1
    else: value["content"] += b"changed"
    with pytest.raises(ValueError):
        parse([value])


def test_duplicate_native_path_is_rejected_even_with_different_roles():
    a = descriptor("known_results", "same.txt", (HEADER + ROW).encode())
    b = descriptor("native_log", "same.txt", b"literal log\n")
    with pytest.raises(ValueError, match="duplicate_file_path"):
        parse([a, b])


@pytest.mark.parametrize("selector", [
    {"series_ids": [], "offset": True, "limit": 1},
    {"series_ids": [], "offset": 0, "limit": 1.5},
    {"series_ids": [], "offset": -1, "limit": 1},
    {"series_ids": ["duplicate", "duplicate"], "offset": 0, "limit": 1},
])
def test_selector_rejects_bool_fraction_negative_and_duplicate_series(selector):
    with pytest.raises(ValueError): validate_homer_selector(selector)


def test_unknown_series_is_not_implicitly_replaced(complete_sheet):
    with pytest.raises(ValueError, match="selected_series_missing"):
        calculate_homer_components(complete_sheet, selector={"series_ids": ["absent"], "offset": 0, "limit": 1})


def test_failed426_empty_native_tables_remain_unavailable(retained):
    sheet = parse(case_files(retained, "failed"), failed=True)
    assert sheet["execution"]["wrapper_returncode"] == 0
    assert sheet["execution"]["known_outcome"] == sheet["execution"]["denovo_outcome"] == "failed"
    assert all(not series["observations"] for series in sheet["series"])
    component = calculate_homer_components(sheet, selector=selection(*sheet["series"]))
    assert component["population_facts"]["state"] == "unavailable"
    assert all(row["cell"]["state"] != "available" and row["cell"]["value"] is None
        for row in component["reported_input_weight_sums"])
    public = project_homer_return(component, source_ref=SOURCE)
    assert public["execution"]["known_outcome"] == "failed"
    assert all(row["captured_occurrences"] == 0 and row["native_outcome"] == "failed" for row in public["counts"])


def test_saved_tampering_cannot_change_native_token_or_original_ordinal(complete_sheet):
    wrong = deepcopy(complete_sheet)
    row = series_for(wrong, "known_results")["observations"][0]
    number(row, "p_value")["number"]["value"] = 0
    with pytest.raises(ValueError): validate_homer_sheet(wrong)
    wrong = deepcopy(complete_sheet)
    series_for(wrong, "known_results")["observations"][0]["ordinal_0based"] = True
    with pytest.raises(ValueError): validate_homer_sheet(wrong)


@pytest.mark.parametrize("field", ["file_identity", "row_location", "number_location"])
def test_saved_artifact_and_location_associations_are_required(complete_sheet, field):
    sheet = deepcopy(complete_sheet)
    row = series_for(sheet, "known_results")["observations"][0]
    if field == "file_identity":
        file = next(file for file in sheet["files"] if file["role"] == "known_results")
        file["artifact"]["sha256"] = "f" * 64
    elif field == "row_location":
        row["location"]["artifact"]["raw_artifact_ref"] = "artifact_" + "f" * 64
    else:
        number(row, "p_value")["number"]["source_location"]["artifact"]["source_ref"] = "source_" + "f" * 24
    with pytest.raises(ValueError): validate_homer_sheet(sheet)


def test_saved_number_units_cannot_change_native_percent_to_fraction(complete_sheet):
    sheet = deepcopy(complete_sheet)
    row = series_for(sheet, "known_results")["observations"][0]
    number(row, "target_percentage")["unit"] = "fraction"
    with pytest.raises(ValueError): validate_homer_sheet(sheet)


@pytest.mark.parametrize("capture", ["missing", "empty", "header_only", "truncated_header"])
def test_zero_known_occurrences_preserve_header_capture_and_native_outcome(capture):
    """Synthetic zero-row captures do not attest a successful enrichment analysis."""
    if capture == "missing":
        file = {"role": "known_results", "native_relative_path": "knownResults.txt",
            "content": None, "artifact": None,
            "capture": {"state": "missing", "byte_start_0based": 0,
                "byte_end_0based_exclusive": 0, "original_size_bytes": None}}
    else:
        raw = b"" if capture == "empty" else HEADER.encode()
        if capture == "truncated_header":
            raw = raw[:40]
        file = descriptor("known_results", "knownResults.txt", raw,
            state="truncated" if capture == "truncated_header" else "complete",
            original_size=len(HEADER.encode()) if capture == "truncated_header" else len(raw))
    expected_issue = ([] if capture == "header_only" else
        ["known_header_truncated" if capture == "truncated_header" else "known_header_unavailable"])
    for failed in (False, True):
        sheet = parse([file], failed=failed)
        series = sheet["series"][0]
        native_outcome = "failed" if failed else "succeeded"
        assert series["observations"] == [] and series["native_outcome"] == native_outcome
        assert series["capture_state"] == file["capture"]["state"]
        assert series["issues"] == expected_issue
        if capture == "header_only":
            assert series["raw_header"] == HEADER.rstrip("\n").split("\t")
            assert series["displayed_totals"]["target"]["raw_token"] == "2"
            assert series["displayed_totals"]["background"]["raw_token"] == "3"
        else:
            assert series["displayed_totals"]["target"] is None
            assert series["displayed_totals"]["background"] is None
            assert bool(series["raw_header"]) == (capture == "truncated_header")
        component = calculate_homer_components(sheet, selector=selection(series))
        assert component["counts"] == [{"series_id": series["series_id"], "role": "known_results",
            "captured_occurrences": 0, "selected_occurrences": 0,
            "capture_state": file["capture"]["state"], "native_outcome": native_outcome}]
        public = project_homer_return(component, source_ref=SOURCE)
        assert public['available_series'] == [dict(series_id=series['series_id'], role='known_results',
            requested_motif_length_bp=None, capture_state=file['capture']['state'], native_outcome=native_outcome)]
        saved = public["selected_series"][0]
        assert public["counts"] == component["counts"]
        assert saved["observations"] == [] and saved["issues"] == expected_issue
        assert saved["raw_header"] == series["raw_header"]
        assert saved["capture_state"] == series["capture_state"]
        assert saved["native_outcome"] == native_outcome
        assert saved["displayed_totals"]["meaning"] == "wrapper_inferred_from_first_rounded_motif"
        for group in ("target", "background"):
            total = saved["displayed_totals"][group]
            if capture == "header_only":
                assert total["state"] == "available" and total["raw_token"] == ("2" if group == "target" else "3")
            else:
                assert total is None
        assert public["population_facts"]["state"] == "unavailable"
        assert all(row["cell"]["value"] is None and row["cell"]["state"] != "available"
            for row in public["reported_input_weight_sums"])


def test_unselected_retained_series_are_addressable_without_another_native_run(complete_sheet):
    known = series_for(complete_sheet, 'known_results')
    original = project_homer_return(calculate_homer_components(complete_sheet,
        selector=selection(known, limit=1)), source_ref=SOURCE)
    assert [row['series_id'] for row in original['available_series']] == [
        row['series_id'] for row in complete_sheet['series']]
    assert len(original['selected_series']) == 1
    lengths = {row['requested_motif_length_bp']: row for row in original['available_series']
        if row['role'] == 'denovo_pwm'}
    assert set(lengths) == {8, 10, 12}
    assert all(row['requested_motif_length_bp'] is None for row in original['available_series']
        if row['role'] != 'denovo_pwm')
    selected = lengths[10]
    recalculated = project_homer_return(calculate_homer_components(complete_sheet,
        selector=dict(series_ids=[selected['series_id']], offset=0, limit=1)), source_ref=SOURCE)
    assert recalculated['available_series'] == original['available_series']
    assert recalculated['selected_series'][0]['series_id'] == selected['series_id']
    expected = series_for(complete_sheet, 'denovo_pwm', 'homerMotifs.motifs10')['observations'][0]
    actual = recalculated['selected_series'][0]['observations'][0]
    assert actual['consensus'] == expected['consensus']
    assert actual['representations'][0]['raw_fields'] == expected['representations'][0]['raw_fields']


@pytest.mark.parametrize('fault', ['duplicate', 'missing_selected', 'wrong_role', 'boolean_length'])
def test_retained_series_catalog_cannot_conflict_with_the_selected_view(complete_sheet, fault):
    from gene_annotation_episode.homer_motif_contracts import validated
    known = series_for(complete_sheet, 'known_results')
    public = project_homer_return(calculate_homer_components(complete_sheet,
        selector=selection(known, limit=1)), source_ref=SOURCE)
    selected = next(row for row in public['available_series'] if row['series_id'] == known['series_id'])
    if fault == 'duplicate': public['available_series'].append(deepcopy(selected))
    elif fault == 'missing_selected': public['available_series'].remove(selected)
    elif fault == 'wrong_role': selected['role'] = 'denovo_pwm'
    else: next(row for row in public['available_series']
        if row['role'] == 'denovo_pwm')['requested_motif_length_bp'] = True
    with pytest.raises(ValueError): validated('Return', public)


@pytest.mark.parametrize('role,path', [('denovo_pwm', 'homerMotifs.motifs99'),
    ('denovo_nonredundant_pwm', 'homerResults/motif8.motif')])
def test_catalog_length_is_not_inferred_from_unselected_filename_or_final_rank(role, path):
    sheet = parse([descriptor(role, path, PWM.encode())])
    component = calculate_homer_components(sheet, selector=selection(sheet['series'][0]))
    assert component['available_series'][0]['requested_motif_length_bp'] is None
