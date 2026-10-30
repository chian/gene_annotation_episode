"""Support-custody regressions using explicitly synthetic control populations."""

from copy import deepcopy

import pytest

from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_event_contracts import (
    canonical, control_comparison_files, issue, validate_components,
)
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from test_fluorescence_event_calculations import _cell, _control_sheet, _parameters


@pytest.mark.parametrize("prepared,expected_count", [(False, 7), (True, 8)])
def test_comparison_files_preserve_exact_distinct_field_locations(prepared, expected_count):
    sheet = _control_sheet(prepared_control=prepared)
    before = canonical(sheet)
    files = control_comparison_files(sheet, control_key="pair")
    assert len(files) == expected_count
    assert len({row["pointer"] for row in files}) == expected_count
    for row in files:
        value = sheet
        for token in row["pointer"].removeprefix("sheet:/").split("/"):
            value = value[int(token)] if isinstance(value, list) else value[token]
        assert row["file"] == value
    files[0]["file"]["format"] = "changed detached copy"
    assert canonical(sheet) == before


@pytest.mark.parametrize("code", ["source_unavailable", "retained_artifact_mismatch"])
def test_missing_or_wrong_support_blocks_only_the_named_control_difference(code):
    sheet = _control_sheet()
    sheet["control_pairs"].append({**deepcopy(sheet["control_pairs"][0]), "key": "other_pair"})
    observed_failure = issue(code, "input", control_key="pair")
    sheet["issues"].append(observed_failure)
    params = _parameters(controls=[dict(control_key=key, include_legacy_clipping=True)
                                   for key in ("pair", "other_pair")])
    result = calculate_fluorescence_sheet(sheet, parameters=params)
    assert _cell(result, "selected_fraction", gate="target.marker")["value"] == .5
    assert _cell(result, "selected_fraction", gate="control.marker")["value"] == .75
    for metric in ("control_difference_fraction", "control_difference_percentage_points",
                   "legacy_nonnegative_difference_percentage_points"):
        cell = _cell(result, metric, gate=None, control="pair")
        assert cell["value"] is None and cell["state"] == "unavailable"
        assert cell["population"]["extent"] == "unavailable"
        assert observed_failure in cell["issues"]
        assert "control_pair_incompatible" not in {row["code"] for row in cell["issues"]}
    assert "sheet:/issues/0" in _cell(result, "control_difference_fraction", gate=None,
                                      control="pair")["operands"]
    unaffected = _cell(result, "control_difference_fraction", gate=None, control="other_pair")
    assert (unaffected["value"], unaffected["state"]) == (-.25, "present")
    assert validate_components(result, sheet=sheet) is result


def test_unlocated_metadata_failure_does_not_disable_an_unrelated_comparison():
    sheet = _control_sheet()
    sheet["issues"].append(issue("source_unavailable", "input"))
    result = calculate_fluorescence_sheet(sheet,
        parameters=_parameters(controls=[dict(control_key="pair", include_legacy_clipping=False)]))
    cell = _cell(result, "control_difference_fraction", gate=None, control="pair")
    assert (cell["value"], cell["state"]) == (-.25, "present")


def test_saved_calculation_and_projection_keep_the_unavailable_comparison(monkeypatch):
    import builtins
    from pathlib import Path

    sheet = _control_sheet()
    sheet["issues"].append(issue("source_unavailable", "input", control_key="pair"))
    params = _parameters(controls=[dict(control_key="pair", include_legacy_clipping=False)])

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved scientific calculations must not fetch support")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    result = calculate_fluorescence_sheet(deepcopy(sheet), parameters=params)
    cell = _cell(result, "control_difference_fraction", gate=None, control="pair")
    view = project_fluorescence_result(sheet, result,
        selection=dict(requests=[cell["request"]], offset=0, limit=1))
    assert view["rows"] == [cell]
    assert view["rows"][0]["value"] is None
