"""Synthetic shared-core fixtures; no preparation or biological run is claimed."""

import builtins
from copy import deepcopy
import io
import json
from pathlib import Path

import pytest

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_event_sheet import validate_fluorescence_sheet
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from test_fluorescence_event_calculations import (
    _batch, _cell, _control_sheet, _file, _gate, _native_report, _parameters, _request, _sheet,
)


def _preparation(state="applied"):
    return dict(state=state,
                method="synthetic selected preparation" if state == "applied" else None,
                parameters_file=_file(b"synthetic preparation parameters") if state == "applied" else None)


def _prepared_batches(rows=((100,), (0,)), original_rows=((110,), (20,)), *,
                      preparation="compensation", sample="s", correspondence=None):
    """Explicit synthetic parent/child values; this does not execute preparation."""
    primary = _batch(original_rows, sample=sample)
    for event in primary["events"]:
        for cell in event["values"]:
            if cell["measurement"]["value"] is not None:
                cell["measurement"]["state"] = "observed"
    mapping = correspondence if correspondence is not None else [
        dict(source_ordinal=index, event_ordinal=index) for index in range(len(rows))]
    prepared = _batch(rows, sample=sample, domain=sample + ".prepared", correspondence=mapping)
    prepared["domain"][preparation] = _preparation()
    for event in prepared["events"]:
        for cell in event["values"]:
            if cell["measurement"]["value"] is not None:
                cell["measurement"].update(state="derived", raw=None)
    return primary, prepared


def _native_case(*, rows=((150,), (0,), (0,)), denominator="parent"):
    sheet = _sheet([_batch(rows)])
    link = _request("fraction", "selected_percent", gate_key="g", denominator=denominator)
    for key in ("report_a", "report_b"):
        report = _native_report(key, 33.33, component=deepcopy(link))
        report["file"] = _file(("synthetic report fixture " + key + ": 33.33").encode())
        report["source_key"] = key + ".source"
        sheet["input_sources"].append(dict(key=report["source_key"], file=deepcopy(report["file"]),
            dataset_position=0, format_profile="synthetic_report_fixture", extent="complete",
            native_event_count=None, metadata=[]))
        sheet["native_reports"].append(report)
    validate_fluorescence_sheet(sheet)
    parameters = _parameters(fractions=[dict(gate_key="g", denominator=denominator)],
                             native=["report_a", "report_b"])
    return sheet, parameters


def test_legacy_domains_parse_and_sheet_validate_without_scaling_or_byte_changes():
    batch = _batch([[110], [20]])
    sheet = _sheet([batch])
    originals = [core.canonical(value) for value in (batch["domain"], batch, sheet)]
    core._domain(batch["domain"])
    assert core.validate_event_parse_result(batch) is batch
    assert validate_fluorescence_sheet(sheet) is sheet
    calculate_fluorescence_sheet(sheet, parameters=_parameters())
    assert [core.canonical(value) for value in (batch["domain"], batch, sheet)] == originals
    assert "scaling" not in batch["domain"]
    assert "scaling" not in sheet["measurement_domains"][0]


@pytest.mark.parametrize("state", ["not_applied", "applied", "unknown", "failed"])
def test_optional_scaling_uses_existing_preparation_shape_without_defaults(state):
    batch = _batch([[110], [20]])
    batch["domain"]["scaling"] = _preparation(state)
    before = core.canonical(batch)
    assert core.validate_event_parse_result(batch) is batch
    sheet = _sheet([batch])
    assert sheet["measurement_domains"][0] == batch["domain"]
    assert core.canonical(batch) == before


@pytest.mark.parametrize("fault", ["missing_method", "missing_parameters", "wrong_identity",
                                   "bool_size", "wrong_state", "extra_preparation_key",
                                   "null_scaling", "extra_domain_key", "extra_old_domain_key"])
def test_scaling_and_domain_keys_remain_closed(fault):
    batch = _batch([[1]])
    domain = batch["domain"]
    domain["scaling"] = _preparation()
    if fault == "missing_method":
        domain["scaling"]["method"] = None
    elif fault == "missing_parameters":
        domain["scaling"]["parameters_file"] = None
    elif fault == "wrong_identity":
        domain["scaling"]["parameters_file"]["artifact_ref"] = "artifact_" + "0" * 64
    elif fault == "bool_size":
        domain["scaling"]["parameters_file"]["size_bytes"] = True
    elif fault == "wrong_state":
        domain["scaling"]["state"] = "scaled"
    elif fault == "extra_preparation_key":
        domain["scaling"]["parameters"] = {}
    elif fault == "null_scaling":
        domain["scaling"] = None
    else:
        if fault == "extra_old_domain_key":
            domain.pop("scaling")
        domain["invented_preparation"] = _preparation()
    with pytest.raises(core.FluorescenceContractError, match="invalid_domain"):
        core.validate_event_parse_result(batch)


@pytest.mark.parametrize("boundary", ["parse", "sheet"])
@pytest.mark.parametrize("fault", ["primary", "unmapped", "not_applied", "unknown", "failed",
                                   "bool", "nan", "positive_inf", "negative_inf", "raw_bool"])
def test_derived_restrictions_apply_to_common_parse_and_saved_sheet(boundary, fault):
    primary, prepared = _prepared_batches()
    sheet = _sheet([primary, prepared])
    target = primary if fault == "primary" else prepared
    measurement = target["events"][0]["values"][0]["measurement"]
    if fault == "primary":
        target["domain"]["scaling"] = _preparation()
        measurement.update(state="derived", raw=None)
    elif fault == "unmapped":
        target["domain"]["correspondence"] = target["domain"]["correspondence"][1:]
    elif fault in {"not_applied", "unknown", "failed"}:
        target["domain"]["compensation"] = _preparation(fault)
    elif fault == "raw_bool":
        measurement["raw"] = False
    else:
        measurement["value"] = dict(bool=True, nan=float("nan"),
            positive_inf=float("inf"), negative_inf=float("-inf"))[fault]
    with pytest.raises(core.FluorescenceContractError, match="invalid_event"):
        if boundary == "parse":
            core.validate_event_parse_result(target)
        else:
            # Bypass the builder to verify the saved-sheet path independently.
            sheet["measurement_domains"] = [deepcopy(primary["domain"]), deepcopy(prepared["domain"])]
            sheet["events"] = deepcopy(primary["events"] + prepared["events"])
            validate_fluorescence_sheet(sheet)


@pytest.mark.parametrize("preparation", ["scaling", "compensation", "transformation"])
def test_derived_values_use_the_selected_domain_and_preserve_original_events(preparation):
    primary, prepared = _prepared_batches(preparation=preparation)
    before = core.canonical([primary, prepared])
    gates = [_gate("raw", lower=105, upper=None),
             _gate("prepared", domain="s.prepared", lower=105, upper=None)]
    sheet = _sheet([primary, prepared], gates=gates)
    original_sheet = core.canonical(sheet)
    parameters = _parameters(fractions=[dict(gate_key=key, denominator="parent")
                                        for key in ("raw", "prepared")])
    result = calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert [entry["selected"] for entry in result["memberships"]] == [[0], []]
    for gate, selected, fraction in (("raw", 1, .5), ("prepared", 0, 0)):
        assert _cell(result, "parent_event_count", gate=gate)["value"] == 2
        assert _cell(result, "selected_event_count", gate=gate)["value"] == selected
        assert _cell(result, "selected_fraction", gate=gate)["value"] == fraction
        assert _cell(result, "selected_fraction", gate=gate)["state"] == "present"
    assert [row["event_ordinal"] for row in prepared["events"]] == [0, 1]
    assert all(row["sample_key"] == "s" for row in sheet["events"])
    assert core.canonical([primary, prepared]) == before
    assert core.canonical(sheet) == original_sheet
    assert all(row["values"][0]["measurement"]["raw"] is None for row in prepared["events"])


def test_derived_values_follow_explicit_correspondence_not_generated_row_order():
    primary, prepared = _prepared_batches(correspondence=[
        dict(source_ordinal=0, event_ordinal=1), dict(source_ordinal=1, event_ordinal=0)])
    sheet = _sheet([primary, prepared], gates=[_gate(domain="s.prepared", lower=50, upper=None)])
    result = calculate_fluorescence_sheet(sheet, parameters=_parameters())
    assert result["memberships"][0]["selected"] == [1]
    assert result["memberships"][0]["rejected"] == [0]
    assert [(row["source_ordinal"], row["event_ordinal"]) for row in prepared["events"]] == [(0, 1), (1, 0)]


def test_derived_intensities_share_calculator_with_equivalent_observed_values():
    primary, prepared = _prepared_batches(rows=((100,), (50,)))
    sheet = _sheet([primary, prepared], gates=[_gate(domain="s.prepared", lower=0, upper=None)])
    parameters = _parameters(fractions=[dict(gate_key="g", denominator="parent")],
        intensities=[dict(gate_key="g", domain_key="s.prepared", channel_key="s.prepared.c0")])
    result = calculate_fluorescence_sheet(sheet, parameters=parameters)
    for metric, number in (("selected_intensity_count", 2), ("selected_intensity_sum", 150),
                           ("selected_intensity_mean", 75), ("selected_intensity_median", 75)):
        cell = _cell(result, metric)
        assert (cell["value"], cell["state"]) == (number, "present")
    equivalent = deepcopy(sheet)
    for event in equivalent["events"]:
        if event["domain_key"] == "s.prepared":
            event["values"][0]["measurement"]["state"] = "observed"
    observed = calculate_fluorescence_sheet(equivalent, parameters=parameters)
    assert result["cells"] == observed["cells"]
    assert result["memberships"] == observed["memberships"]
    assert result["sheet_sha256"] != observed["sheet_sha256"]


def test_prepared_domain_preserves_untouched_observed_and_predicted_columns():
    primary, prepared = _prepared_batches(rows=((100, 3), (50, 7)),
                                         original_rows=((110, 3), (60, 7)))
    primary["events"][1]["values"][1]["measurement"]["state"] = "supplied_predicted"
    for source, destination in zip(primary["events"], prepared["events"]):
        destination["values"][1]["measurement"] = deepcopy(source["values"][1]["measurement"])
    before = core.canonical(prepared)
    sheet = _sheet([primary, prepared], gates=[_gate(domain="s.prepared", lower=0, upper=None)])
    result = calculate_fluorescence_sheet(sheet, parameters=_parameters(
        intensities=[dict(gate_key="g", domain_key="s.prepared", channel_key="s.prepared.c1")]))
    assert _cell(result, "selected_intensity_sum")["value"] == 10
    assert _cell(result, "selected_intensity_mean")["value"] == 5
    assert [row["values"][1]["measurement"]["state"] for row in prepared["events"]] == [
        "observed", "supplied_predicted"]
    assert core.canonical(prepared) == before


def test_derived_negative_zero_and_missing_values_keep_existing_population_rules():
    primary, prepared = _prepared_batches(rows=((-5,), (0,), (None,)),
                                         original_rows=((5,), (10,), (20,)))
    sheet = _sheet([primary, prepared], gates=[_gate(domain="s.prepared", lower=-10, upper=None)])
    result = calculate_fluorescence_sheet(sheet, parameters=_parameters(
        fractions=[dict(gate_key="g", denominator=name) for name in ("parent", "evaluable")],
        intensities=[dict(gate_key="g", domain_key="s.prepared", channel_key="s.prepared.c0")]))
    assert result["memberships"][0]["selected"] == [0, 1]
    assert result["memberships"][0]["unknown"] == [2]
    assert _cell(result, "selected_fraction", denominator="parent")["value"] is None
    assert (_cell(result, "selected_fraction", denominator="evaluable")["value"],
            _cell(result, "selected_fraction", denominator="evaluable")["state"]) == (1, "qualified")
    assert _cell(result, "selected_intensity_sum")["value"] == -5
    assert _cell(result, "selected_intensity_mean")["value"] == -2.5


def test_derived_control_values_use_existing_signed_and_clipped_calculations():
    sheet = _control_sheet(prepared_control=True)
    parameters = _parameters(controls=[dict(control_key="pair", include_legacy_clipping=True)])
    supplied = calculate_fluorescence_sheet(sheet, parameters=parameters)
    sheet["measurement_domains"][2]["compensation"] = _preparation()
    for event in sheet["events"]:
        if event["domain_key"] == "control.prepared":
            for cell in event["values"]:
                cell["measurement"].update(state="derived", raw=None)
    derived = calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert derived["cells"] == supplied["cells"]
    assert _cell(derived, "selected_fraction", gate="target.marker")["value"] == .5
    assert _cell(derived, "selected_fraction", gate="control.marker")["value"] == .75
    assert _cell(derived, "control_difference_percentage_points", gate=None, control="pair")["value"] == -25
    assert _cell(derived, "legacy_nonnegative_difference_percentage_points", gate=None, control="pair")["value"] == 0


def test_source_scoped_native_issue_suppresses_only_delta_and_deduplicates_qualifications():
    sheet, parameters = _native_case()
    supported = calculate_fluorescence_sheet(sheet, parameters=parameters)
    linked = _cell(supported, "selected_percent")
    baseline_delta = _cell(supported, "native_minus_calculated", gate=None, report="report_a")
    assert linked["value"] == 100 * (1 / 3)
    assert baseline_delta["value"] == 33.33 - linked["value"]
    assert baseline_delta["value"] != 0
    association_issue = core.issue("native_population_unknown", "input", source_key="report_a.source")
    sheet["issues"] = [deepcopy(association_issue), deepcopy(association_issue)]
    before = core.canonical(sheet)
    result = calculate_fluorescence_sheet(sheet, parameters=parameters)
    delta = _cell(result, "native_minus_calculated", gate=None, report="report_a")
    assert (delta["value"], delta["state"], delta["population"]["extent"]) == (None, "unavailable", "unavailable")
    assert delta["issues"] == [association_issue]
    assert delta["operands"] == baseline_delta["operands"] + ["sheet:/issues/0", "sheet:/issues/1"]
    assert _cell(result, "native_value", gate=None, report="report_a") == _cell(
        supported, "native_value", gate=None, report="report_a")
    assert _cell(result, "selected_percent") == linked
    for metric in ("native_value", "native_minus_calculated"):
        assert _cell(result, metric, gate=None, report="report_b") == _cell(
            supported, metric, gate=None, report="report_b")
    assert sheet["native_reports"][0]["component_request"] == linked["request"]
    assert (sheet["native_reports"][0]["value"], sheet["native_reports"][0]["unit"],
            sheet["native_reports"][0]["decimal_places"]) == (33.33, "percent", 2)
    assert core.canonical(sheet) == before
    assert core.validate_components(result, sheet=sheet) is result


@pytest.mark.parametrize("source,stage,code", [
    ("s.raw.source", "input", "native_population_unknown"),
    ("report_a.source", "parse", "native_population_unknown"),
    ("report_a.source", "input", "source_unavailable"),
    (None, "input", "native_population_unknown"),
])
def test_unrelated_or_noninput_issue_keeps_exact_native_subtraction(source, stage, code):
    sheet, parameters = _native_case()
    baseline = calculate_fluorescence_sheet(sheet, parameters=parameters)
    sheet["issues"].append(core.issue(code, stage, source_key=source))
    result = calculate_fluorescence_sheet(sheet, parameters=parameters)
    for metric in ("native_value", "native_minus_calculated"):
        assert _cell(result, metric, gate=None, report="report_a") == _cell(
            baseline, metric, gate=None, report="report_a")


def test_unlocated_report_does_not_match_an_unlocated_association_issue():
    sheet, parameters = _native_case()
    sheet["native_reports"][0]["source_key"] = None
    baseline = calculate_fluorescence_sheet(sheet, parameters=parameters)
    sheet["issues"].append(core.issue("native_population_unknown", "input"))
    result = calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(result, "native_minus_calculated", gate=None, report="report_a") == _cell(
        baseline, "native_minus_calculated", gate=None, report="report_a")


def test_unlinked_report_retains_existing_behavior_with_matching_source_issue():
    sheet, parameters = _native_case()
    sheet["native_reports"][0]["component_request"] = None
    baseline = calculate_fluorescence_sheet(sheet, parameters=parameters)
    sheet["issues"].append(core.issue("native_population_unknown", "input", source_key="report_a.source"))
    result = calculate_fluorescence_sheet(sheet, parameters=parameters)
    for metric in ("native_value", "native_minus_calculated"):
        assert _cell(result, metric, gate=None, report="report_a") == _cell(
            baseline, metric, gate=None, report="report_a")


def test_association_issue_preserves_linked_qualifications_and_actual_token_failure():
    sheet, parameters = _native_case(rows=((150,), (0,), (None,)), denominator="evaluable")
    baseline = calculate_fluorescence_sheet(sheet, parameters=parameters)
    linked = _cell(baseline, "selected_percent", denominator="evaluable")
    assert (linked["value"], linked["state"]) == (50, "qualified")
    association_issue = core.issue("native_population_unknown", "input", source_key="report_a.source")
    sheet["issues"].append(association_issue)
    result = calculate_fluorescence_sheet(sheet, parameters=parameters)
    delta = _cell(result, "native_minus_calculated", gate=None, report="report_a")
    assert delta["issues"] == linked["issues"] + [association_issue]
    assert _cell(result, "selected_percent", denominator="evaluable") == linked
    assert "native_report_uninterpretable" not in {row["code"] for row in delta["issues"]}
    sheet["native_reports"][0].update(value=None, raw="not a number")
    malformed = calculate_fluorescence_sheet(sheet, parameters=parameters)
    native = _cell(malformed, "native_value", gate=None, report="report_a")
    assert (native["value"], native["state"]) == (None, "unavailable")
    assert {row["code"] for row in native["issues"]} == {"native_report_uninterpretable"}
    assert association_issue in _cell(malformed, "native_minus_calculated", gate=None, report="report_a")["issues"]


def test_saved_only_recalculation_and_projection_keep_native_dependency_without_io(monkeypatch):
    sheet, parameters = _native_case()
    sheet["issues"].append(core.issue("native_population_unknown", "input", source_key="report_a.source"))
    baseline = calculate_fluorescence_sheet(sheet, parameters=parameters)
    saved = json.loads(core.canonical(sheet))
    before = core.canonical(saved)
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"flowio", "flowutils", "numpy", "socket", "subprocess", "urllib",
                                  "requests", "openai", "anthropic"}:
            raise AssertionError("External work during saved calculation: " + name)
        return original_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved core calculation must not read or prepare inputs")

    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", guarded_import)
        context.setattr(builtins, "open", forbidden)
        context.setattr(io, "open", forbidden)
        context.setattr(Path, "open", forbidden)
        recalculated = calculate_fluorescence_sheet(saved, parameters=deepcopy(parameters))
        selected = [_cell(recalculated, "native_value", gate=None, report="report_a"),
                    _cell(recalculated, "native_minus_calculated", gate=None, report="report_a"),
                    _cell(recalculated, "selected_percent"),
                    _cell(recalculated, "native_minus_calculated", gate=None, report="report_b")]
        view = project_fluorescence_result(saved, recalculated,
            selection=dict(requests=[cell["request"] for cell in selected], offset=0, limit=4))
    assert core.canonical(recalculated) == core.canonical(baseline)
    assert view["rows"] == selected
    assert view["rows"][0]["value"] == 33.33
    assert view["rows"][1]["value"] is None
    assert view["rows"][1]["issues"] == saved["issues"]
    assert "sheet:/issues/0" in view["rows"][1]["operands"]
    assert view["rows"][2]["value"] == 100 * (1 / 3)
    assert view["rows"][3]["value"] == 33.33 - view["rows"][2]["value"]
    assert core.canonical(saved) == before
