"""Synthetic partial-input regressions; no biological measurements are claimed."""

from copy import deepcopy

import pytest

from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_event_contracts import (
    FluorescenceContractError, canonical, validate_components,
)
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from test_fluorescence_event_calculations import _batch, _cell, _gate, _parameters, _sheet


def _case(*, extent="partial", subset=(0, 1, 2), derived=False):
    missing = extent == "unavailable"
    primary = _batch([] if missing else [[10], [20]], sample="a", extent=extent,
                     state="unavailable" if missing else "available")
    batches = [primary, _batch([[5], [7]], sample="b")]
    populations = [
        dict(key="a.population", sample_key="a", kind="subset", event_ordinals=list(subset)),
        dict(key="b.population", sample_key="b", kind="all", event_ordinals=None),
    ]
    gates = [_gate("a.g", sample="a", kind="pass_all"),
             _gate("b.g", sample="b", kind="pass_all")]
    intensity_domain = "a.raw"
    if derived:
        batches.append(_batch([[4], [9]], sample="a", domain="a.prepared",
            correspondence=[dict(source_ordinal=0, event_ordinal=0),
                            dict(source_ordinal=1, event_ordinal=2)]))
        gates[0] = _gate("a.g", sample="a", domain="a.prepared", lower=0, upper=None)
        intensity_domain = "a.prepared"
    params = _parameters(
        fractions=[dict(gate_key=k + ".g", denominator="parent") for k in ("a", "b")],
        intensities=[dict(gate_key="a.g", domain_key=intensity_domain,
                          channel_key=intensity_domain + ".c0"),
                     dict(gate_key="b.g", domain_key="b.raw", channel_key="b.raw.c0")],
    )
    return _sheet(batches, gates=gates, populations=populations), params


def _check_independent_sample(components):
    for metric, value in (("selected_event_count", 2), ("selected_fraction", 1),
                          ("selected_intensity_mean", 6)):
        cell = _cell(components, metric, gate="b.g")
        assert (cell["value"], cell["state"]) == (value, "present")


def test_partial_primary_preserves_declared_subset_and_other_sample():
    sheet, params = _case()
    before = canonical(sheet)
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    assert canonical(sheet) == before
    assert sheet["population_definitions"][0]["event_ordinals"] == [0, 1, 2]
    membership = result["memberships"][0]
    assert membership["universe_event_ordinals"] == membership["selected"] == [0, 1]
    assert membership["population_complete"] is False
    for metric, number in (("retained_event_count", 2), ("selected_event_count", 2),
                           ("selected_intensity_mean", 15)):
        cell = _cell(result, metric, gate="a.g")
        assert (cell["value"], cell["state"], cell["population"]["extent"]) == (
            number, "qualified", "incomplete")
    fraction = _cell(result, "selected_fraction", gate="a.g")
    assert fraction["value"] is None
    assert "incomplete_population" in {row["code"] for row in fraction["issues"]}
    _check_independent_sample(result)
    assert validate_components(result, sheet=sheet) is result


def test_unavailable_primary_keeps_subset_without_inventing_zeroes():
    sheet, params = _case(extent="unavailable")
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    assert sheet["population_definitions"][0]["event_ordinals"] == [0, 1, 2]
    assert result["memberships"][0]["universe_event_ordinals"] == []
    for cell in result["cells"]:
        if cell["request"]["gate_key"] == "a.g":
            assert cell["value"] is None and cell["state"] == "unavailable"
    _check_independent_sample(result)


def test_complete_primary_still_rejects_nonexistent_subset_member():
    with pytest.raises(FluorescenceContractError, match="invalid_population"):
        _case(extent="complete")


def test_partial_source_can_supply_a_complete_explicit_subset():
    sheet, params = _case(subset=(1, 0))
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    assert sheet["population_definitions"][0]["event_ordinals"] == [1, 0]
    assert result["memberships"][0]["population_complete"] is True
    assert result["memberships"][0]["universe_event_ordinals"] == [0, 1]
    assert (_cell(result, "selected_fraction", gate="a.g")["value"],
            _cell(result, "selected_fraction", gate="a.g")["state"]) == (1, "present")


def test_derived_rows_survive_without_becoming_missing_primary_members():
    sheet, params = _case(derived=True)
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    assert [event["event_ordinal"] for event in sheet["events"]
            if event["domain_key"] == "a.prepared"] == [0, 2]
    assert result["memberships"][0]["universe_event_ordinals"] == [0, 1]
    assert result["memberships"][0]["selected"] == [0]
    assert result["memberships"][0]["unknown"] == [1]
    cell = _cell(result, "selected_intensity_mean", gate="a.g")
    assert (cell["value"], cell["state"]) == (4, "qualified")
    _check_independent_sample(result)


def test_derived_rows_do_not_create_a_missing_primary_population():
    sheet, params = _case(extent="unavailable", derived=True)
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    assert len([e for e in sheet["events"] if e["sample_key"] == "a"]) == 2
    assert result["memberships"][0]["universe_event_ordinals"] == []
    assert _cell(result, "selected_intensity_mean", gate="a.g")["value"] is None
    _check_independent_sample(result)


def test_complete_primary_still_rejects_nonexistent_derived_target():
    with pytest.raises(FluorescenceContractError, match="invalid_domain"):
        _case(extent="complete", subset=(0, 1), derived=True)


def test_component_validation_rejects_false_complete_flag():
    sheet, params = _case()
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    result["memberships"][0]["population_complete"] = True
    with pytest.raises(FluorescenceContractError, match="invalid_components"):
        validate_components(result, sheet=sheet)


def test_component_validation_rejects_invented_primary_member():
    sheet, params = _case()
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    row = result["memberships"][0]
    for name in ("universe_event_ordinals", "parent_true", "selected", "parent_evaluable"):
        row[name].append(2)
    with pytest.raises(FluorescenceContractError, match="invalid_components"):
        validate_components(result, sheet=sheet)


@pytest.mark.parametrize("subset,complete", [((2, 3), False), ((), True)])
def test_empty_retained_subset_distinguishes_incomplete_from_genuinely_empty(subset, complete):
    sheet, params = _case(subset=subset)
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    assert result["memberships"][0]["population_complete"] is complete
    count = _cell(result, "retained_event_count", gate="a.g")
    assert (count["value"], count["state"]) == (0, "present" if complete else "qualified")
    fraction = _cell(result, "selected_fraction", gate="a.g")
    assert fraction["value"] is None
    assert ("incomplete_population" in {r["code"] for r in fraction["issues"]}) is not complete


def test_saved_recalculation_and_requested_view_preserve_exact_qualified_cells(monkeypatch):
    sheet, params = _case()
    saved = deepcopy(sheet)
    result = calculate_fluorescence_sheet(saved, parameters=deepcopy(params))
    selected = [_cell(result, "selected_event_count", gate="a.g"),
                _cell(result, "selected_fraction", gate="a.g"),
                _cell(result, "selected_intensity_mean", gate="b.g")]
    import gene_annotation_episode.fluorescence_event_calculations as calculator

    def no_recalculation(*args, **kwargs):
        raise AssertionError("Projection must copy saved calculated values")

    monkeypatch.setattr(calculator, "calculate_fluorescence_sheet", no_recalculation)
    view = project_fluorescence_result(saved, result,
        selection=dict(requests=[row["request"] for row in selected], offset=0, limit=10))
    # Projector uses saved component order, not caller request order.
    assert {canonical(row) for row in view["rows"]} == {canonical(row) for row in selected}
    assert sheet == saved
