"""Source-format fixtures only; authentic wrapper execution is separate evidence."""

import builtins
from copy import deepcopy
import io
import json
from pathlib import Path

import pytest

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_event_sheet import validate_fluorescence_sheet
from gene_annotation_episode.fluorescence_native_report_contracts import (
    FACS_PROFILE, CYTOKINE_LOG_PROFILE, CYTOKINE_CSV_PROFILE, PROFILE_SOURCES,
    make_fluorescence_report_binding, validate_report_input, validate_report_parse_result,
)
from gene_annotation_episode.fluorescence_native_reports import parse_fluorescence_native_reports
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from test_fluorescence_event_calculations import (
    _batch, _cell, _control_sheet, _file, _gate, _parameters, _request, _sheet,
)


FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_fluorescence_native_reports_2026-10-28_590"


def _input(batch, *, basename=None):
    result = {name: deepcopy(batch[name]) for name in ("source", "sample", "channels", "domain")}
    result.update(parser="table_snapshot", path="/synthetic-fixture/" + (basename or batch["sample"]["key"] + ".fcs"), format_spec=None)
    result["source"].update(extent="unavailable", native_event_count=None)
    for channel in result["channels"]:
        channel.pop("domain_key")
        channel["measurement_origin"] = "observed"
    return result


def _inputs_from_sheet(sheet):
    inputs = []
    for domain in sheet["measurement_domains"]:
        inputs.append(_input(dict(domain=domain,
            sample=next(row for row in sheet["samples"] if row["key"] == domain["sample_key"]),
            source=next(row for row in sheet["input_sources"] if row["key"] == domain["source_key"]),
            channels=[row for row in sheet["channels"] if row["domain_key"] == domain["key"]])))
    return inputs


def _definitions(sheet=None):
    return dict(populations=deepcopy(sheet["population_definitions"]) if sheet else [],
                gates=deepcopy(sheet["gate_definitions"]) if sheet else [],
                control_pairs=deepcopy(sheet["control_pairs"]) if sheet else [], native_reports=[])


def _report_input(raw, fields, *, profile=FACS_PROFILE, source="report.source"):
    return dict(file=_file(raw, profile), path="/synthetic-fixture/report", source_key=source,
                profile=profile, fields=fields, association_file=None)


def _facs_field(key, metric, request=None, occurrence=0):
    return dict(key=key, locator=dict(kind="facs_metric", metric=metric, occurrence=occurrence), component_request=request)


def _log_field(key, condition, metric, request=None, marker=None):
    return dict(key=key, locator=dict(kind="cytokine_log_metric", condition_ordinal=condition,
        metric=metric, marker_occurrence=marker), component_request=request)


def _csv_field(key, row, column, condition, label, request=None):
    return dict(key=key, locator=dict(kind="cytokine_csv_cell", row_ordinal=row, column_ordinal=column,
        condition_label=condition, column_label=label), component_request=request)


def _entry(field, inputs, gates, *, domains=None, samples=None, control=None):
    # Each test supplies its actual dependency set; no production join helper is
    # used to manufacture expected support.
    return dict(report_key=field["key"], component_request=deepcopy(field["component_request"]),
        event_sources=[dict(file=deepcopy(row["source"]["file"]), dataset_position=row["source"]["dataset_position"])
                       for row in inputs],
        sample_keys=samples or [row["sample"]["key"] for row in inputs],
        domain_keys=domains or [row["domain"]["key"] for row in inputs],
        gates=deepcopy(gates), control_pair=deepcopy(control))


def _attach(report, entries):
    association = dict(version="fluorescence_report_association_v1", report_file=deepcopy(report["file"]), fields=entries)
    raw = core.canonical(association) + b"\n"
    report["association_file"] = _file(raw, "json")
    return raw


def _facs_case(raw=None, *, source="report.source"):
    raw = raw if raw is not None else (FIXTURES / "source_format_facs_fixture.log").read_bytes()
    batch = _batch([[150], [250], [0]])
    batch["channels"][0].update(native_name="GFP", label="GFP")
    gates = [_gate(upper=200), _gate("lower", upper=None)]
    sheet = _sheet([batch], gates=gates)
    inputs = [_input(batch)]
    fields = [
        _facs_field("original", "original_count", _request("population", "parent_event_count", gate_key="g")),
        _facs_field("selected", "selected_count", _request("population", "selected_event_count", gate_key="g")),
        _facs_field("percent", "selected_percent", _request("fraction", "selected_percent", gate_key="g", denominator="parent")),
        _facs_field("mean", "selected_mean", _request("intensity", "selected_intensity_mean", gate_key="g", domain_key="s.raw", channel_key="s.raw.c0")),
        _facs_field("median", "selected_median", _request("intensity", "selected_intensity_median", gate_key="g", domain_key="s.raw", channel_key="s.raw.c0")),
        _facs_field("lower_count", "lower_remaining_count", _request("population", "selected_event_count", gate_key="lower")),
        _facs_field("upper_count", "upper_remaining_count", _request("population", "selected_event_count", gate_key="g")),
    ]
    report = _report_input(raw, fields, source=source)
    association_raw = _attach(report, [_entry(field, inputs, [gates[1] if field["key"] == "lower_count" else gates[0]]) for field in fields])
    binding = make_fluorescence_report_binding(report, definitions=_definitions(sheet), event_inputs=inputs, preparations=[])
    return raw, binding, association_raw, sheet


def _parse(raw, binding, association_raw=None):
    return parse_fluorescence_native_reports(raw, binding=binding, association_raw=association_raw)


def _add_reports(sheet, *results):
    sheet = deepcopy(sheet)
    for result in results:
        sheet["input_sources"].append(deepcopy(result["source"]))
        sheet["native_reports"].extend(deepcopy(result["reports"]))
        sheet["issues"].extend(deepcopy(result["issues"]))
    validate_fluorescence_sheet(sheet)
    return sheet


def _codes(result):
    return {row["code"] for row in result["issues"]}


def test_facs_exact_tokens_utf8_byte_locations_precision_and_shared_delta():
    raw, binding, association, sheet = _facs_case()
    before = core.canonical(binding)
    result = _parse(raw, binding, association)
    assert result["issues"] == []
    assert [row["value"] for row in result["reports"]] == [3, 1, 33.33, 150, 150, 2, 1]
    assert [row["raw"] for row in result["reports"]] == ["3", "1", "33.33", "150.00", "150.00", "2", "1"]
    assert [row["decimal_places"] for row in result["reports"]] == [0, 0, 2, 2, 2, 0, 0]
    assert [row["unit"] for row in result["reports"]] == ["events", "events", "percent", "instrument_units", "instrument_units", "events", "events"]
    for row in result["reports"]:
        location = row["location"]
        assert raw[location["byte_start"]:location["byte_end"]].decode() == row["raw"]
        assert location["line_start"] == raw[:location["byte_start"]].count(b"\n") + 1
        assert location["line_end"] == location["line_start"]
    assert result["provenance"]["producer_execution"] == "unverified"
    assert result["provenance"]["artifact_origin"] == "received_supplied"
    assert result["provenance"]["profile_source"] == PROFILE_SOURCES[FACS_PROFILE]
    saved = _add_reports(sheet, result)
    components = calculate_fluorescence_sheet(saved, parameters=_parameters(
        fractions=[dict(gate_key="g", denominator="parent")],
        intensities=[dict(gate_key="g", domain_key="s.raw", channel_key="s.raw.c0")],
        native=[row["key"] for row in result["reports"]]))
    selected = _cell(components, "selected_percent")
    assert selected["value"] == 100 * (1 / 3)
    assert _cell(components, "native_minus_calculated", gate=None, report="percent")["value"] == 33.33 - selected["value"]
    assert _cell(components, "native_minus_calculated", gate=None, report="mean")["value"] == 0
    assert core.canonical(binding) == before
    assert validate_report_parse_result(result, binding=binding) == result


@pytest.mark.parametrize("failure", ["missing", "wrong_digest", "malformed", "wrong_report", "wrong_source", "wrong_dataset",
    "wrong_sample", "wrong_domain", "wrong_gate", "missing_gate", "extra", "duplicate_json_key", "no_declared_file"])
def test_failed_associations_preserve_actual_numbers_units_and_selected_links(failure):
    raw, binding, association, _ = _facs_case()
    valid = _parse(raw, binding, association)
    if failure == "missing":
        association = None
    elif failure == "wrong_digest":
        association += b" "
    elif failure == "no_declared_file":
        binding["report_input"]["association_file"] = None
    else:
        data = json.loads(association)
        entry = data["fields"][0]
        if failure == "wrong_report":
            data["report_file"] = _file(b"wrong report")
        elif failure == "wrong_source":
            entry["event_sources"][0]["file"] = _file(b"wrong events")
        elif failure == "wrong_dataset":
            entry["event_sources"][0]["dataset_position"] = 1
        elif failure == "wrong_sample":
            entry["sample_keys"] = ["duplicate sample label"]
        elif failure == "wrong_domain":
            entry["domain_keys"] = ["as_supplied"]
        elif failure == "wrong_gate":
            entry["gates"][0]["lower"]["value"] = 101
        elif failure == "missing_gate":
            entry["gates"] = []
        elif failure == "extra":
            entry["value"] = 999
        association = core.canonical(data) + b"\n"
        if failure == "malformed":
            association = b"{broken"
        elif failure == "duplicate_json_key":
            association = association.replace(b'{"fields":', b'{"fields":[],"fields":', 1)
        binding["report_input"]["association_file"] = _file(association, "json")
    result = _parse(raw, binding, association)
    assert result["reports"] == valid["reports"]
    assert result["issues"] == [core.issue("native_population_unknown", "input", source_key="report.source")]


def test_failed_support_is_saved_once_and_only_its_source_delta_is_unavailable(monkeypatch):
    raw, binding, association, sheet = _facs_case()
    result = _parse(raw, binding, None)
    other_binding = deepcopy(binding)
    other_binding["report_input"]["source_key"] = "independent.source"
    other_binding["report_input"]["fields"] = [_facs_field("independent", "selected_percent",
        _request("fraction", "selected_percent", gate_key="g", denominator="parent"))]
    other_association = _attach(other_binding["report_input"], [_entry(other_binding["report_input"]["fields"][0],
        binding["event_inputs"], [binding["definitions"]["gates"][0]])])
    independent = _parse(raw, other_binding, other_association)
    saved = _add_reports(sheet, result, independent)
    parameters = _parameters(fractions=[dict(gate_key="g", denominator="parent")], native=["percent", "independent"])
    baseline = calculate_fluorescence_sheet(saved, parameters=parameters)
    expected_issue = core.issue("native_population_unknown", "input", source_key="report.source")
    delta = _cell(baseline, "native_minus_calculated", gate=None, report="percent")
    assert delta["value"] is None and delta["issues"] == [expected_issue]
    assert "sheet:/issues/0" in delta["operands"]
    assert _cell(baseline, "native_value", gate=None, report="percent")["value"] == 33.33
    assert _cell(baseline, "native_minus_calculated", gate=None, report="independent")["value"] == 33.33 - 100 * (1 / 3)
    reloaded = json.loads(core.canonical(saved))

    def forbidden(*args, **kwargs):
        raise AssertionError("saved-only calculation must not access files, native libraries or acquisition")

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"flowio", "flowutils", "numpy", "socket", "subprocess", "requests", "openai"}:
            forbidden()
        return original_import(name, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(io, "open", forbidden)
        guard.setattr(Path, "open", forbidden)
        guard.setattr(builtins, "__import__", guarded_import)
        recalculated = calculate_fluorescence_sheet(reloaded, parameters=parameters)
        requests = [row["request"] for row in recalculated["cells"] if row["request"]["kind"] == "native_comparison"]
        view = project_fluorescence_result(reloaded, recalculated,
            selection=dict(requests=requests, offset=0, limit=len(requests)))
    assert core.canonical(recalculated) == core.canonical(baseline)
    assert view["rows"] == [row for row in recalculated["cells"] if row["request"] in requests]


@pytest.mark.parametrize("failure", ["extra_number", "profile", "locator", "bool_ordinal", "duplicate_key", "duplicate_locator",
    "field_source_collision", "event_source_collision", "metric", "denominator", "missing_gate", "forged_domain", "extra_binding"])
def test_malformed_caller_bindings_are_contract_errors(failure):
    raw, binding, association, _ = _facs_case()
    report = binding["report_input"]
    if failure == "extra_number":
        report["fields"][0]["value"] = 999
    elif failure == "profile":
        report["profile"] = "pandas_to_string"
    elif failure == "locator":
        report["fields"][0]["locator"] = dict(kind="cytokine_csv_cell", row_ordinal=0, column_ordinal=1,
            condition_label="Mtb300", column_label="IFN-γ")
    elif failure == "bool_ordinal":
        report["fields"][0]["locator"]["occurrence"] = True
    elif failure == "duplicate_key":
        report["fields"][1]["key"] = report["fields"][0]["key"]
    elif failure == "duplicate_locator":
        report["fields"][1]["locator"] = deepcopy(report["fields"][0]["locator"])
    elif failure == "field_source_collision":
        report["fields"][0]["key"] = report["source_key"]
    elif failure == "event_source_collision":
        report["source_key"] = binding["event_inputs"][0]["source"]["key"]
    elif failure == "metric":
        report["fields"][2]["component_request"]["metric"] = "selected_fraction"
    elif failure == "denominator":
        report["fields"][2]["component_request"]["denominator"] = "evaluable"
    elif failure == "missing_gate":
        report["fields"][0]["component_request"]["gate_key"] = "missing"
    elif failure == "forged_domain":
        binding["definitions"]["gates"][0]["domain_key"] = "unselected"
    else:
        binding["measurements"] = [999]
    with pytest.raises(ValueError):
        _parse(raw, binding, association)


@pytest.mark.parametrize("failure", ["value", "link", "source", "profile_hash", "verified_claim", "span", "unit", "report_count"])
def test_result_validator_keeps_closed_identity_contract(failure):
    raw, binding, association, _ = _facs_case()
    result = _parse(raw, binding, association)
    if failure == "value":
        result["reports"][0]["value"] = 999
    elif failure == "link":
        result["reports"][0]["component_request"] = None
    elif failure == "source":
        result["source"]["file"] = _file(b"other")
    elif failure == "profile_hash":
        result["provenance"]["profile_source"]["function_sha256"] = "0" * 64
    elif failure == "verified_claim":
        result["provenance"]["producer_execution"] = "verified"
    elif failure == "span":
        result["reports"][0]["location"]["byte_end"] = len(raw) + 1
    elif failure == "unit":
        result["reports"][0]["unit"] = "confidence"
    else:
        result["reports"].pop()
    with pytest.raises(ValueError):
        validate_report_parse_result(result, binding=binding)


@pytest.mark.parametrize("token", ["", "nan", "inf", "-inf", "not-a-number", "33.3", "1e309"])
def test_bad_native_tokens_preserve_raw_and_do_not_become_zero(token):
    raw = (FIXTURES / "source_format_facs_fixture.log").read_bytes().replace(b"33.33%", token.encode() + b"%")
    raw, binding, association, _ = _facs_case(raw)
    result = _parse(raw, binding, association)
    row = result["reports"][2]
    assert row["raw"] == token and row["value"] is None
    assert row["component_request"] == binding["report_input"]["fields"][2]["component_request"]
    assert result["reports"][0]["value"] == 3
    assert "native_population_unknown" not in _codes(result)
    assert "native_report_uninterpretable" in _codes(result) or "invalid_numeric_token" in _codes(result)


def test_missing_truncated_error_and_bad_artifact_keep_specific_partial_data():
    full = (FIXTURES / "source_format_facs_fixture.log").read_bytes()
    raw = full[:full.index(b"Enrichment percentage:")] + b"Enrichment percentage: 33.3"
    raw, binding, association, _ = _facs_case(raw)
    result = _parse(raw, binding, association)
    assert [row["value"] for row in result["reports"][:3]] == [3, 1, None]
    assert result["reports"][2]["raw"] == "33.3"
    assert result["reports"][3]["raw"] is None
    assert all(value is None for value in result["reports"][3]["location"].values())
    assert "truncated_source" in _codes(result)
    mismatch = _parse(raw + b"x", binding, association)
    assert _codes(mismatch) == {"retained_artifact_mismatch"}
    assert mismatch["source"]["extent"] == "unavailable"
    assert all(row["value"] is None and row["raw"] is None for row in mismatch["reports"])
    raw = full[:full.index(b"## Enrichment Results")] + b"## Error\nAn error occurred during cell sorting: Original population: 999 cells\nOriginal population: 888 cells\n"
    raw, binding, association, _ = _facs_case(raw)
    failed = _parse(raw, binding, association)
    assert failed["reports"][0]["value"] is None
    assert failed["reports"][5]["value"] == 2


def test_native_empty_denominator_zero_is_retained_without_reconstructing_counts():
    raw = (FIXTURES / "source_format_facs_fixture.log").read_bytes().replace(b"33.33%", b"0.00%")
    raw = raw.replace(b"Original population: 3", b"Original population: 0").replace(b"Sorted population: 1", b"Sorted population: 0")
    batch = _batch([], width=1)
    batch["channels"][0].update(native_name="GFP", label="GFP")
    gate = _gate(upper=200)
    sheet = _sheet([batch], gates=[gate])
    inputs = [_input(batch)]
    field = _facs_field("percent", "selected_percent", _request("fraction", "selected_percent", gate_key="g", denominator="parent"))
    report = _report_input(raw, [field])
    association = _attach(report, [_entry(field, inputs, [gate])])
    binding = make_fluorescence_report_binding(report, definitions=_definitions(sheet), event_inputs=inputs, preparations=[])
    parsed = _parse(raw, binding, association)
    saved = _add_reports(sheet, parsed)
    components = calculate_fluorescence_sheet(saved, parameters=_parameters(
        fractions=[dict(gate_key="g", denominator="parent")], native=["percent"]))
    assert _cell(components, "native_value", gate=None, report="percent")["value"] == 0
    assert _cell(components, "selected_percent")["value"] is None
    assert _cell(components, "native_minus_calculated", gate=None, report="percent")["value"] is None
    assert saved["events"] == []


def _cytokine_sheet():
    sheet = _control_sheet()
    for sample in sheet["samples"]:
        sample["condition"] = "Mtb300" if sample["key"] == "target" else "unstimulated"
    for channel in sheet["channels"]:
        channel["native_name"] = "CD4-A" if channel["ordinal"] == 0 else "IFN-A"
        channel["label"] = channel["native_name"]
    return sheet


def test_cytokine_csv_native_clipped_zero_and_shared_signed_difference_are_distinct():
    raw = (FIXTURES / "source_format_cytokine_fixture.csv").read_bytes()
    sheet = _cytokine_sheet()
    inputs = _inputs_from_sheet(sheet)
    fields = [_csv_field("target_percent", 1, 1, "Mtb300", "IFN-γ",
        _request("fraction", "selected_percent", gate_key="target.marker", denominator="parent")),
        _csv_field("clipped", 1, 3, "Mtb300", "IFN-γ (background-subtracted)",
        _request("control", "legacy_nonnegative_difference_percentage_points", control_key="pair")),
        _csv_field("absent_control_bg", 0, 3, "unstimulated", "IFN-γ (background-subtracted)")]
    report = _report_input(raw, fields, profile=CYTOKINE_CSV_PROFILE)
    association = _attach(report, [_entry(fields[0], inputs[:1], sheet["gate_definitions"][:2]),
        _entry(fields[1], inputs, sheet["gate_definitions"], control=sheet["control_pairs"][0])])
    binding = make_fluorescence_report_binding(report, definitions=_definitions(sheet), event_inputs=inputs, preparations=[])
    result = _parse(raw, binding, association)
    assert [row["value"] for row in result["reports"]] == [50, 0, None]
    assert [row["raw"] for row in result["reports"]] == ["50.0", "0.0", ""]
    assert [row["unit"] for row in result["reports"]] == ["percent", "percentage_points", "percentage_points"]
    assert all(row["decimal_places"] is None for row in result["reports"])
    assert "native_population_unknown" not in _codes(result)
    for row in result["reports"]:
        span = row["location"]
        assert raw[span["byte_start"]:span["byte_end"]].decode() == row["raw"]
    saved = _add_reports(sheet, result)
    components = calculate_fluorescence_sheet(saved, parameters=_parameters(
        controls=[dict(control_key="pair", include_legacy_clipping=True)], native=["clipped", "target_percent"]))
    assert _cell(components, "control_difference_percentage_points", gate=None, control="pair")["value"] == -25
    assert _cell(components, "legacy_nonnegative_difference_percentage_points", gate=None, control="pair")["value"] == 0
    assert _cell(components, "native_minus_calculated", gate=None, report="clipped")["value"] == 0


def test_cytokine_log_exact_condition_marker_occurrences_and_counts():
    raw = (FIXTURES / "source_format_cytokine_fixture.log").read_bytes()
    sheet = _cytokine_sheet()
    inputs = _inputs_from_sheet(sheet)
    fields = [_log_field("target", 1, "marker_percent", _request("fraction", "selected_percent",
        gate_key="target.marker", denominator="parent"), marker=0),
        _log_field("parent", 1, "parent_count", _request("population", "parent_event_count", gate_key="target.marker")),
        _log_field("original", 1, "original_count", _request("population", "parent_event_count", gate_key="target.parent")),
        _log_field("control", 0, "marker_percent", marker=0),
        _log_field("IL17", 1, "marker_percent", marker=1)]
    report = _report_input(raw, fields, profile=CYTOKINE_LOG_PROFILE)
    association = _attach(report, [_entry(fields[0], inputs[:1], sheet["gate_definitions"][:2]),
        _entry(fields[1], inputs[:1], sheet["gate_definitions"][:2]),
        _entry(fields[2], inputs[:1], sheet["gate_definitions"][:1])])
    binding = make_fluorescence_report_binding(report, definitions=_definitions(sheet), event_inputs=inputs, preparations=[])
    result = _parse(raw, binding, association)
    assert result["issues"] == []
    assert [row["value"] for row in result["reports"]] == [50, 4, 6, 75, 25]
    for row in result["reports"]:
        span = row["location"]
        assert raw[span["byte_start"]:span["byte_end"]].decode() == row["raw"]


def test_repeated_log_aliases_conditions_and_csv_labels_are_positional():
    raw = ("# Cytokine Production Analysis by Flow Cytometry\n\n## Data Loading and Preprocessing\n"
        "Processing repeated condition from file: same.fcs\n"
        "- Identified channels: CD4=CD4-A, Cytokines=IFN-A, IFN-B\n"
        "- Applied CD4+ gating: 3 cells (from 4 total)\n"
        "- IFN-γ+ frequency: 33.33% of CD4+ T cells\n"
        "- IFN-γ+ frequency: 66.67% of CD4+ T cells\n"
        "Processing repeated condition from file: same.fcs\n"
        "- IFN-γ+ frequency: 0.00% of CD4+ T cells\n"
        "## Results Summary\n- IFN-γ+ frequency: 99.99% of CD4+ T cells\n").encode()
    fields = [_log_field("first", 0, "marker_percent", marker=0),
        _log_field("second", 0, "marker_percent", marker=1), _log_field("next", 1, "marker_percent", marker=0)]
    binding = make_fluorescence_report_binding(_report_input(raw, fields, profile=CYTOKINE_LOG_PROFILE),
        definitions=_definitions(), event_inputs=[], preparations=[])
    result = _parse(raw, binding)
    assert [row["value"] for row in result["reports"]] == [33.33, 66.67, 0]
    assert len({row["location"]["byte_start"] for row in result["reports"]}) == 3
    csv_raw = ',IFN-γ\r\n"répeated, condition",33.333333333333336\r\n"répeated, condition",0.0\r\n'.encode()
    fields = [_csv_field("a", 0, 1, "répeated, condition", "IFN-γ"), _csv_field("b", 1, 1, "répeated, condition", "IFN-γ")]
    binding = make_fluorescence_report_binding(_report_input(csv_raw, fields, profile=CYTOKINE_CSV_PROFILE),
        definitions=_definitions(), event_inputs=[], preparations=[])
    result = _parse(csv_raw, binding)
    assert [row["value"] for row in result["reports"]] == [33.333333333333336, 0]
    for row in result["reports"]:
        span = row["location"]
        assert csv_raw[span["byte_start"]:span["byte_end"]].decode() == row["raw"]


def test_csv_multiline_labels_truncated_records_and_label_mismatch_remain_located():
    raw = ',IFN-γ,IL-17\n"Mtb\n300",33.333333333333336,2.0\ncontrol,nan,\n"broken'.encode()
    fields = [_csv_field("a", 0, 1, "Mtb\n300", "IFN-γ"), _csv_field("b", 1, 1, "control", "IFN-γ"),
        _csv_field("blank", 1, 2, "control", "IL-17"), _csv_field("missing", 2, 1, "broken", "IFN-γ")]
    binding = make_fluorescence_report_binding(_report_input(raw, fields, profile=CYTOKINE_CSV_PROFILE),
        definitions=_definitions(), event_inputs=[], preparations=[])
    result = _parse(raw, binding)
    assert [row["value"] for row in result["reports"]] == [33.333333333333336, None, None, None]
    assert result["reports"][0]["location"]["line_start"] == 3
    assert result["reports"][0]["location"]["record_ordinal"] == 0
    assert "truncated_source" in _codes(result)
    binding["report_input"]["fields"][0]["locator"]["condition_label"] = "wrong"
    mismatched = _parse(raw, binding)
    assert mismatched["reports"][0]["value"] == result["reports"][0]["value"]
    assert "native_format_mismatch" in _codes(mismatched)


def test_binding_is_independent_and_preparation_dependencies_use_original_source_identity():
    raw, binding, _, _ = _facs_case()
    report = binding["report_input"]
    report["fields"] = [report["fields"][2]]
    original = binding["event_inputs"][0]
    output_channels = [{k: v for k, v in original["channels"][0].items() if k != "measurement_origin"}]
    output_channels[0]["key"] = "s.prepared.c0"
    recipe = dict(version="fluorescence_preparation_recipe_v1", method="fcs_scale_flowio_1_4_0",
                  parameters=dict(metadata_policy="strict_present_fcs_metadata_v1"))
    preparation = dict(key="scaling", input=dict(kind="event_input", index=0),
        output=dict(key="s.prepared", source_key="s.prepared.source", sample_key="s", channels=output_channels,
                    comparison_basis=deepcopy(original["domain"]["comparison_basis"])),
        recipe_file=_file(core.canonical(recipe) + b"\n", "json"), recipe=recipe)
    gate = _gate(domain="s.prepared", upper=200)
    definitions = deepcopy(binding["definitions"])
    definitions["gates"] = [gate]
    association = _attach(report, [_entry(report["fields"][0], [original], [gate], domains=["s.raw", "s.prepared"])])
    independent = make_fluorescence_report_binding(report, definitions=definitions, event_inputs=[original], preparations=[preparation])
    before = core.canonical(independent)
    definitions["gates"][0]["lower"]["value"] = 999
    report["fields"][0]["key"] = "changed"
    assert core.canonical(independent) == before
    result = _parse(raw, independent, association)
    assert result["issues"] == [] and result["reports"][0]["value"] == 33.33
    assert "events" not in independent
    assert independent["preparations"][0] == preparation
    assert validate_report_input(independent["report_input"], definitions=independent["definitions"],
        event_inputs=independent["event_inputs"], preparations=independent["preparations"]) == independent["report_input"]


@pytest.mark.parametrize("fault", ["threshold", "inclusivity", "intermediate_stage", "parameter", "subset", "unknown_unit"])
def test_consistently_supplied_facs_association_still_checks_actual_report_meaning(fault):
    raw, binding, _, _ = _facs_case()
    field = binding["report_input"]["fields"][2 if fault != "unknown_unit" else 3]
    binding["report_input"]["fields"] = [field]
    gate = binding["definitions"]["gates"][0]
    if fault == "threshold":
        gate["lower"]["value"] = 101
    elif fault == "inclusivity":
        gate["lower"]["inclusive"] = False
    elif fault == "intermediate_stage":
        gate["upper"] = None
    elif fault == "parameter":
        binding["event_inputs"][0]["channels"][0]["native_name"] = "other"
    elif fault == "subset":
        binding["definitions"]["populations"][0].update(kind="subset", event_ordinals=[0, 1])
    else:
        binding["event_inputs"][0]["channels"][0]["unit"] = None
    association = _attach(binding["report_input"], [_entry(field, binding["event_inputs"], [gate])])
    result = _parse(raw, binding, association)
    assert result["reports"][0]["value"] == (150 if fault == "unknown_unit" else 33.33)
    if fault == "unknown_unit":
        assert result["reports"][0]["unit"] is None
    else:
        assert _codes(result) == {"native_population_unknown"}


def test_csv_mismatched_requested_column_preserves_native_unit_and_number():
    raw = b",IFN-\xce\xb3,IFN-\xce\xb3 (background-subtracted)\nMtb300,50.0,0.0\n"
    field = _csv_field("column", 0, 2, "Mtb300", "IFN-γ")
    binding = make_fluorescence_report_binding(_report_input(raw, [field], profile=CYTOKINE_CSV_PROFILE),
        definitions=_definitions(), event_inputs=[], preparations=[])
    result = _parse(raw, binding)
    assert result["reports"][0]["value"] == 0
    assert result["reports"][0]["unit"] == "percentage_points"
    assert result["reports"][0]["label"] == "Mtb300: IFN-γ (background-subtracted)"
    assert _codes(result) == {"native_format_mismatch"}


def test_invalid_encoding_keeps_earlier_complete_report_tokens():
    full = (FIXTURES / "source_format_facs_fixture.log").read_bytes()
    raw = full[:full.index(b"Mean GFP")] + b"Mean GFP: \xff"
    raw, binding, association, _ = _facs_case(raw)
    result = _parse(raw, binding, association)
    assert [row["value"] for row in result["reports"][:3]] == [3, 1, 33.33]
    assert result["reports"][3]["value"] is None
    assert "input_encoding_invalid" in _codes(result)


def test_chained_preparation_binding_uses_per_kind_identity_index_without_fabricated_state():
    raw, binding, _, _ = _facs_case()
    original = binding["event_inputs"][0]
    recipe1 = dict(version="fluorescence_preparation_recipe_v1", method="fcs_scale_flowio_1_4_0",
                   parameters=dict(metadata_policy="strict_present_fcs_metadata_v1"))
    channels1 = [{key: value for key, value in original["channels"][0].items() if key != "measurement_origin"}]
    channels1[0]["key"] = "s.scaled.c0"
    first = dict(key="scaling", input=dict(kind="event_input", index=0),
        output=dict(key="s.scaled", source_key="s.scaled.source", sample_key="s", channels=channels1,
                    comparison_basis=deepcopy(original["domain"]["comparison_basis"])),
        recipe_file=_file(core.canonical(recipe1) + b"\n", "json"), recipe=recipe1)
    recipe2 = dict(version="fluorescence_preparation_recipe_v1", method="spill_compensate_flowutils_1_2_2",
        parameters=dict(matrix_file=_file(b"synthetic matrix support"), dataset_position=0, keyword="spill",
            input_domain_basis=deepcopy(original["domain"]["comparison_basis"]),
            axes=[dict(native_label="GFP", input_channel_key="s.scaled.c0", input_ordinal=0)]))
    channels2 = deepcopy(channels1)
    channels2[0]["key"] = "s.prepared.c0"
    second = dict(key="compensation", input=dict(kind="preparation", index=0),
        output=dict(key="s.prepared", source_key="s.prepared.source", sample_key="s", channels=channels2,
                    comparison_basis=deepcopy(original["domain"]["comparison_basis"])),
        recipe_file=_file(core.canonical(recipe2) + b"\n", "json"), recipe=recipe2)
    definitions = deepcopy(binding["definitions"])
    gate = _gate(domain="s.prepared", upper=200)
    definitions["gates"] = [gate]
    field = binding["report_input"]["fields"][2]
    report = _report_input(raw, [field])
    association = _attach(report, [_entry(field, [original], [gate], domains=["s.raw", "s.scaled", "s.prepared"])])
    binding = make_fluorescence_report_binding(report, definitions=definitions, event_inputs=[original], preparations=[first, second])
    result = _parse(raw, binding, association)
    assert result["issues"] == [] and result["reports"][0]["value"] == 33.33
    assert binding["preparations"] == [first, second]
    assert all("state" not in item["output"] and "file" not in item["output"] for item in binding["preparations"])


def test_cytokine_relocated_input_joins_by_file_and_dataset_instead_of_path_label():
    raw = (FIXTURES / "source_format_cytokine_fixture.log").read_bytes()
    sheet = _cytokine_sheet()
    inputs = _inputs_from_sheet(sheet)
    inputs[0]["path"] = "/retained/content-addressed/renamed-input.bin"
    field = _log_field("target", 1, "marker_percent", _request("fraction", "selected_percent",
        gate_key="target.marker", denominator="parent"), marker=0)
    report = _report_input(raw, [field], profile=CYTOKINE_LOG_PROFILE)
    association = _attach(report, [_entry(field, inputs[:1], sheet["gate_definitions"][:2])])
    binding = make_fluorescence_report_binding(report, definitions=_definitions(sheet), event_inputs=inputs, preparations=[])
    result = _parse(raw, binding, association)
    assert result["issues"] == [] and result["reports"][0]["value"] == 50
    binding["event_inputs"][0]["path"] = "/matching-label/target.fcs"
    binding["event_inputs"][0]["source"]["file"] = _file(b"different source with matching basename")
    wrong_source = _parse(raw, binding, association)
    assert wrong_source["reports"] == result["reports"]
    assert _codes(wrong_source) == {"native_population_unknown"}


@pytest.mark.parametrize("token", ["nan", ""])
@pytest.mark.parametrize("fault", ["record_ordinal", "line_start", "line_end", "byte_start", "byte_end", "label"])
def test_even_invalid_or_empty_retained_tokens_require_complete_location_and_label(token, fault):
    raw = (FIXTURES / "source_format_facs_fixture.log").read_bytes().replace(b"33.33%", token.encode() + b"%")
    raw, binding, association, _ = _facs_case(raw)
    result = _parse(raw, binding, association)
    assert result["reports"][2]["raw"] == token and result["reports"][2]["value"] is None
    if fault == "label":
        result["reports"][2]["label"] = None
    else:
        result["reports"][2]["location"][fault] = None
    with pytest.raises(ValueError):
        validate_report_parse_result(result, binding=binding)


@pytest.mark.parametrize("native_name,method,output_unit,accepted", [
    ("Time", "fcs_scale_flowio_1_4_0", "seconds", True),
    ("tImE", "fcs_scale_flowio_1_4_0", None, True),
    ("Time-A", "fcs_scale_flowio_1_4_0", "seconds", False),
    (None, "fcs_scale_flowio_1_4_0", "seconds", False),
    ("Time", "spill_compensate_flowutils_1_2_2", "seconds", False),
    ("Time", "spill_compensate_flowutils_1_2_2", "ticks", True),
])
def test_only_selected_scaling_time_channel_allows_prospective_unit_change(native_name, method, output_unit, accepted):
    raw, binding, _, _ = _facs_case()
    original = binding["event_inputs"][0]
    original["channels"][0].update(native_name=native_name, unit="ticks")
    output_channel = {key: value for key, value in original["channels"][0].items() if key != "measurement_origin"}
    output_channel.update(key="s.prepared.c0", unit=output_unit)
    if method == "fcs_scale_flowio_1_4_0":
        parameters = dict(metadata_policy="strict_present_fcs_metadata_v1")
    else:
        parameters = dict(matrix_file=_file(b"synthetic matrix support"), dataset_position=0,
            keyword="spill", input_domain_basis=deepcopy(original["domain"]["comparison_basis"]),
            axes=[dict(native_label="Time", input_channel_key="s.raw.c0", input_ordinal=0)])
    recipe = dict(version="fluorescence_preparation_recipe_v1", method=method, parameters=parameters)
    request = dict(key="preparation", input=dict(kind="event_input", index=0),
        output=dict(key="s.prepared", source_key="s.prepared.source", sample_key="s", channels=[output_channel],
                    comparison_basis=deepcopy(original["domain"]["comparison_basis"])),
        recipe_file=_file(core.canonical(recipe) + b"\n", "json"), recipe=recipe)
    arguments = dict(definitions=binding["definitions"], event_inputs=[original], preparations=[request])
    report = _report_input(raw, [])
    if accepted:
        selected = make_fluorescence_report_binding(report, **arguments)
        assert selected["preparations"][0]["output"]["channels"][0]["unit"] == output_unit
        assert "state" not in selected["preparations"][0]["output"]
    else:
        with pytest.raises(ValueError):
            make_fluorescence_report_binding(report, **arguments)
