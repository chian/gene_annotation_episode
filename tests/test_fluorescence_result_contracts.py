"""Closed return/control shapes and saved numerical publication relations."""
from copy import deepcopy

import pytest

from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
from gene_annotation_episode.fluorescence_result_contracts import (validate_fluorescence_projection,
    validate_fluorescence_selector, validate_fluorescence_worker_result)
from gene_annotation_episode.fluorescence_return_views import (FACT_SOURCES, CONTEXT_SOURCE, FAILURE_SOURCE,
    PROJECTION_SOURCE, SAVED_SOURCE, fluorescence_fact_sources, requested_fluorescence_sources,
    select_fluorescence_return_facts, validate_fluorescence_fact_values)
from gene_annotation_episode.fluorescence_result_worker import execute_fluorescence_worker
from gene_annotation_episode.state import Store
from test_fluorescence_event_calculations import _batch, _parameters, _request, _sheet
from test_fluorescence_result_worker import saved_plan, selector


@pytest.mark.parametrize("change", ["extra", "bool_offset", "zero_limit", "duplicate", "unknown_metric", "mode", "context", "saved"])
def test_selector_rejects_ambiguous_or_unavailable_contract(change):
    value = selector()
    if change == "extra": value["narrative"] = "not allowed"
    elif change == "bool_offset": value["selection"]["offset"] = False
    elif change == "zero_limit": value["selection"]["limit"] = 0
    elif change == "duplicate": value["selection"]["requests"].append(deepcopy(value["selection"]["requests"][0]))
    elif change == "unknown_metric": value["selection"]["requests"][0]["metric"] = "confidence"
    elif change == "mode": value["mode"] = "lab_equipment"
    elif change == "context": value["context_fields"] = ["samples", "samples"]
    elif change == "saved": value["mode"] = "saved_sheet_recalculation"
    with pytest.raises(ValueError): validate_fluorescence_selector(value)


def projected():
    sheet = _sheet([_batch([[150]])])
    components = calculate_fluorescence_sheet(sheet, parameters=_parameters())
    selected = dict(requests=[_request("population", "selected_event_count", gate_key="g")], offset=0, limit=1)
    return project_fluorescence_result(sheet, components, selection=selected)


@pytest.mark.parametrize("change", ["bool_count", "wrong_row", "extra", "fraction_unit", "status", "has_more", "pointer"])
def test_projection_validates_relations_without_recalculation(change):
    value = projected()
    if change == "bool_count": value["rows"][0]["value"] = True
    elif change == "wrong_row": value["rows"][0]["request"]["gate_key"] = "another"
    elif change == "extra": value["rows"][0]["conclusion"] = "confidence"
    elif change == "fraction_unit": value["rows"][0]["unit"] = "probability"
    elif change == "status": value["status"] = "unavailable"
    elif change == "has_more": value["has_more"] = True
    elif change == "pointer": value["rows"][0]["operands"] = ["outside:/private"]
    with pytest.raises(ValueError): validate_fluorescence_projection(value)


def test_fact_validator_returns_copies_and_saved_is_only_artifact_grant():
    value = projected()
    copied = validate_fluorescence_fact_values(PROJECTION_SOURCE, [value])
    assert copied == [value] and copied[0] is not value
    copied[0]["rows"][0]["value"] = 900
    assert value["rows"][0]["value"] == 1
    sources = fluorescence_fact_sources()
    def reference_count(value):
        if type(value) is dict:
            return int(value.get("x-reference-namespace") == "artifact") + sum(reference_count(x) for x in value.values())
        return sum(reference_count(x) for x in value) if type(value) is list else 0
    assert reference_count(sources[SAVED_SOURCE]["report_schema"]) == 1
    assert reference_count(sources[CONTEXT_SOURCE]["report_schema"]) == 0
    assert reference_count(sources[PROJECTION_SOURCE]["report_schema"]) == 0
    schema = dict(properties={"selected": sources[PROJECTION_SOURCE]["report_schema"]})
    assert requested_fluorescence_sources(schema) == {PROJECTION_SOURCE}
    groups = {source: [] for source in FACT_SOURCES}
    groups[PROJECTION_SOURCE] = [value]
    assert select_fluorescence_return_facts(groups, schema=schema) == {PROJECTION_SOURCE: [value]}
    with pytest.raises(ValueError): requested_fluorescence_sources(dict(properties={"x": {"x-source": "fluorescence_unknown"}}))
    with pytest.raises(ValueError): validate_fluorescence_fact_values(FAILURE_SOURCE, [dict(code="invented")])


@pytest.mark.parametrize("change", ["mode", "acquired", "outputs", "role", "absent_identity", "diagnostics", "context", "failure"])
def test_worker_result_has_exact_host_contract(tmp_path, change):
    with Store(tmp_path / "store") as store:
        value = execute_fluorescence_worker(saved_plan(store, tmp_path / "case"))
        if change == "mode": value["mode"] = "native_result"
        elif change == "acquired": value["original_events_acquired"] = True
        elif change == "outputs": value["outputs"].reverse()
        elif change == "role": value["outputs"][0]["declaration"]["role"] = "sheet"
        elif change == "absent_identity": value["outputs"][0]["declaration"]["state"] = "absent"
        elif change == "diagnostics": value["outputs"][-1]["declaration"].update(state="absent", sha256=None, size_bytes=None)
        elif change == "context": value["selector"]["context_fields"] = []
        elif change == "failure": value["failures"] = [dict(code="worker_output_malformed", stage="worker", input_index=0, role="event_batch:1")]
        with pytest.raises(ValueError): validate_fluorescence_worker_result(value)
