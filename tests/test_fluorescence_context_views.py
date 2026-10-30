"""Requested definition pages contain only the actual saved cell dependencies."""
from copy import deepcopy

import pytest

from gene_annotation_episode.fluorescence_context_views import project_fluorescence_context
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_result_contracts import CONTEXT_FIELDS, validate_fluorescence_context
from test_fluorescence_event_calculations import _batch, _basis, _file, _gate, _location, _parameters, _request, _sheet


def test_pagination_selects_actual_page_dependencies_and_requested_fields():
    a, b = _batch([[100, 500]], sample="a"), _batch([[150, 600]], sample="b")
    gates = [_gate("a.g", sample="a"), _gate("b.g", sample="b")]
    sheet = _sheet([a, b], gates=gates)
    parameters = _parameters(fractions=[dict(gate_key=row["key"], denominator="parent") for row in gates])
    components = calculate_fluorescence_sheet(sheet, parameters=parameters)
    selected = dict(requests=[_request("fraction", "selected_fraction", gate_key=row["key"], denominator="parent")
        for row in gates], offset=1, limit=1)
    before = deepcopy((sheet, components, selected))
    context = project_fluorescence_context(sheet, components, selection=selected, context_fields=list(CONTEXT_FIELDS))
    assert [row["key"] for row in context["samples"]] == ["b"]
    assert [row["key"] for row in context["channels"]] == ["b.raw.c0"]
    assert [row["key"] for row in context["gates"]] == ["b.g"]
    assert [row["key"] for row in context["sources"]] == ["b.raw.source"]
    assert "metadata" not in context["sources"][0]
    assert "correspondence" not in context["domains"][0]
    assert "event_ordinals" not in context["populations"][0]
    assert not context["control_pairs"] and not context["native_reports"]
    assert (sheet, components, selected) == before
    only = project_fluorescence_context(sheet, components, selection=selected, context_fields=["samples"])
    assert only["samples"] == context["samples"]
    assert all(not only[field] for field in CONTEXT_FIELDS if field != "samples")
    only["samples"][0]["label"] = "modified copy"
    assert sheet["samples"][1]["label"] != "modified copy"


def test_parent_gate_and_prepared_domain_closure_does_not_copy_correspondence():
    raw = _batch([[100, 999], [150, 998]])
    prepared = _batch([[5], [6]], domain="s.prepared", correspondence=[dict(source_ordinal=i, event_ordinal=i) for i in range(2)])
    gates = [_gate("child", parent=dict(kind="gate", key="parent"), domain="s.prepared", lower=5, upper=None), _gate("parent")]
    sheet = _sheet([raw, prepared], gates=gates)
    request = dict(gate_key="child", domain_key="s.prepared", channel_key="s.prepared.c0")
    components = calculate_fluorescence_sheet(sheet, parameters=_parameters(intensities=[request]))
    selected = dict(requests=[_request("intensity", "selected_intensity_mean", **request)], offset=0, limit=1)
    context = project_fluorescence_context(sheet, components, selection=selected, context_fields=["gates", "channels", "domains"])
    assert [row["key"] for row in context["gates"]] == ["child", "parent"]
    assert [row["key"] for row in context["channels"]] == ["s.raw.c0", "s.prepared.c0"]
    assert [row["key"] for row in context["domains"]] == ["s.raw", "s.prepared"]
    assert all("correspondence" not in row for row in context["domains"])
    assert not context["samples"] and not context["sources"]


def test_control_page_resolves_both_branches_but_no_unrelated_sample():
    batches = [_batch([[100]], sample=s) for s in ("a", "b", "unused")]
    gates = [_gate(s + ".g", sample=s) for s in ("a", "b", "unused")]
    pair = dict(key="pair", target_gate_key="a.g", control_gate_key="b.g", denominator="parent", comparison_basis=_basis())
    sheet = _sheet(batches, gates=gates, controls=[pair])
    parameters = _parameters(controls=[dict(control_key="pair", include_legacy_clipping=False)])
    components = calculate_fluorescence_sheet(sheet, parameters=parameters)
    selected = dict(requests=[_request("control", "control_difference_percentage_points", control_key="pair")], offset=0, limit=1)
    context = project_fluorescence_context(sheet, components, selection=selected, context_fields=["samples", "control_pairs"])
    assert [row["key"] for row in context["samples"]] == ["a", "b"]
    assert context["control_pairs"] == [pair] and not context["gates"]


def test_existing_saved_native_link_context_resolves_requested_definition_only():
    linked = _request("population", "selected_event_count", gate_key="g")
    report = dict(key="report", file=_file(), source_key="s.raw.source", location=_location(), label="reported count",
        value=1, raw="1", unit="events", component_request=linked, decimal_places=0)
    sheet = _sheet([_batch([[150]])], reports=[report])
    components = calculate_fluorescence_sheet(sheet, parameters=_parameters(native=["report"]))
    selected = dict(requests=[_request("native_comparison", "native_value", native_report_key="report")], offset=0, limit=1)
    context = project_fluorescence_context(sheet, components, selection=selected, context_fields=list(CONTEXT_FIELDS))
    assert context["native_reports"] == [report]
    assert [row["key"] for row in context["gates"]] == ["g"]


def test_empty_page_has_no_definition_leak():
    sheet = _sheet([_batch([[150]])])
    components = calculate_fluorescence_sheet(sheet, parameters=_parameters())
    selected = dict(requests=[_request("population", "selected_event_count", gate_key="g")], offset=2, limit=1)
    context = project_fluorescence_context(sheet, components, selection=selected, context_fields=list(CONTEXT_FIELDS))
    assert all(not context[field] for field in CONTEXT_FIELDS)


@pytest.mark.parametrize("change", ["metadata", "correspondence", "events", "wrong_sample", "cycle", "unrequested"])
def test_context_rejects_unrequested_data_and_broken_references(change):
    sheet = _sheet([_batch([[150]])])
    components = calculate_fluorescence_sheet(sheet, parameters=_parameters())
    selected = dict(requests=[_request("population", "selected_event_count", gate_key="g")], offset=0, limit=1)
    value = project_fluorescence_context(sheet, components, selection=selected, context_fields=list(CONTEXT_FIELDS))
    if change == "metadata": value["sources"][0]["metadata"] = []
    elif change == "correspondence": value["domains"][0]["correspondence"] = []
    elif change == "events": value["events"] = []
    elif change == "wrong_sample": value["domains"][0]["sample_key"] = "foreign"
    elif change == "cycle": value["gates"][0]["parent"] = dict(kind="gate", key="g")
    elif change == "unrequested": value["context_fields"].remove("samples")
    with pytest.raises(ValueError): validate_fluorescence_context(value)
