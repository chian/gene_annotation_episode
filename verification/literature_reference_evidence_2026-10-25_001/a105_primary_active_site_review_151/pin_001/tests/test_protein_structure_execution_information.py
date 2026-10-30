"""Result-library descriptions; no claims of native execution or authority."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from gene_annotation_episode.execution_progress import ExecutionTargetReader
from gene_annotation_episode.native_protein_structure_contracts import NATIVE_FORMATS, output_files
from gene_annotation_episode.protein_structure_execution_information import describe_protein_structure_result
from gene_annotation_episode.protein_structure_result_views import protein_structure_fact_sources
from test_protein_structure_selection import native, selector, saved


def target(name="held_out"):
    request = native(name)["request"]
    return {"resource_kind": "local", "resource_id": "local", "handle": "synthetic-handoff",
        "assignment": {"requested_job": {"native_protein_structure": {
            "program": "protein_structure_python", "request": request,
            "outputs": output_files(request["operation"])} }}}


def describe(value, selected=None):
    return describe_protein_structure_result(value, called_operation="practical.job.start", selector=selected)


def collect(value):
    return next(row for row in value["extractors"] if row["operation"] == "execution.results.collect")


@pytest.mark.parametrize("name,family", [("inspect", "structure_inventory"),
    ("extract", "extracted_sequence"), ("held_out", "comparison_summary"), ("supplied", "comparison_summary")])
def test_original_operation_describes_its_real_native_format_and_selected_fields(name, family):
    original, selected = target(name), selector(family)
    result = describe(original, selected)
    operation = original["assignment"]["requested_job"]["native_protein_structure"]["request"]["operation"]
    assert result["operation"] == operation
    assert collect(result)["native_format"] == NATIVE_FORMATS[operation]
    assert collect(result)["calculators"] == []
    assert collect(result)["return_fact_sources"] == list(protein_structure_fact_sources())
    assert result["result_selection"] == selected
    assert result["called_operation"] == "practical.job.start"
    assert result["status_operations"] == ["progress.observe", "execution.results.status"]
    assert result["acquisition_operations"] == ["execution.results.collect"]
    assert all(row["operation"] != "execution.results.read" for row in result["extractors"])
    assert result["status_meanings"]["process_liveness_establishes_productive_work"] is False
    if operation == "compare":
        assert collect(result)["original_calculation_parameters"] == original["assignment"]["requested_job"]["native_protein_structure"]["request"]["parameters"]
        assert collect(result)["calculation_basis"] == "original_recorded_native_baseline"
    else:
        assert "sheet_population" not in collect(result)
        assert "original_calculation_parameters" not in collect(result)


def test_saved_sheet_reports_explicit_calculation_and_no_fresh_producer_observation():
    selected, request = saved()
    selected["parameters"]["distance_threshold_A"] = 7.5
    original = target()
    assert original["assignment"]["requested_job"]["native_protein_structure"]["request"] == request
    result = describe(original, selected)
    extractor = collect(result)
    assert extractor["calculators"] == ["gene_annotation_episode.protein_structure_calculations.calculate_protein_structure_components"]
    assert extractor["calculator_parameters"]["distance_threshold_A"] == 7.5
    assert extractor["original_sheet_and_baseline_preserved"] is True
    assert extractor["new_producer_observation"] is False
    assert "capture" not in extractor and "native_format" not in extractor and "sheet_population" not in extractor
    assert result["status_operations"] == ["execution.results.status"]
    assert result["extractors"][0]["fresh_native_observation"] is False
    assert result["extractors"][0]["return_fact_sources"] == []
    assert result["extractors"][0]["completes_assignment"] is False


def test_information_does_not_select_a_projection_when_no_selector_was_supplied():
    result = describe(target())
    assert "result_selection" not in result


def test_information_defensively_copies_the_original_request_and_selection():
    original, selected = target(), selector()
    before = deepcopy((original, selected))
    result = describe(original, selected)
    result["result_selection"]["projections"].clear()
    result["selected_outputs"].clear()
    collect(result)["original_calculation_parameters"]["distance_threshold_A"] = 999
    result["result_selector_schema"].clear()
    assert (original, selected) == before
    assert describe(original, selected)["result_selector_schema"]


@pytest.mark.parametrize("change", ["hpc", "api", "not_protein", "wrong_fields", "changed_original_parameters", "bad_called_operation"])
def test_incompatible_information_request_is_rejected(change):
    original, selected = target(), selector()
    called = "practical.job.start"
    if change in {"hpc", "api"}: original["resource_kind"] = change
    elif change == "not_protein": del original["assignment"]["requested_job"]["native_protein_structure"]
    elif change == "wrong_fields": selected = selector("structure_inventory")
    elif change == "changed_original_parameters":
        selected["parameters"] = deepcopy(original["assignment"]["requested_job"]["native_protein_structure"]["request"]["parameters"])
        selected["parameters"]["distance_threshold_A"] = 999
    else: called = ""
    with pytest.raises(ValueError):
        describe_protein_structure_result(original, called_operation=called, selector=selected)


def test_description_never_reads_scientific_bytes_observes_or_calculates(monkeypatch):
    from gene_annotation_episode import protein_structure_calculations, protein_structure_sheet
    from gene_annotation_episode import native_protein_structure_acquisition
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    original, selected = target(), selector()
    saved_selection, _ = saved()
    def forbidden(*args, **kwargs):
        raise AssertionError("information acquired scientific data")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(native_protein_structure_acquisition, "capture_local_protein_structure_bundle", forbidden)
    monkeypatch.setattr(LocalPracticalOperations, "observe_execution", forbidden)
    monkeypatch.setattr(protein_structure_calculations, "calculate_protein_structure_components", forbidden)
    monkeypatch.setattr(protein_structure_sheet, "parse_native_protein_comparison", forbidden)
    assert describe(original, selected)["operation"] == "compare"
    assert describe(original, saved_selection)["operation"] == "compare"


def test_actual_target_reader_selects_protein_information_after_authenticated_target(monkeypatch):
    original, selected = target(), selector()
    calls = []
    reader = object.__new__(ExecutionTargetReader)
    reader.api_execution = None
    def read_target(handle, scope):
        calls.append((handle, scope))
        return deepcopy(original)
    reader.read_target = read_target
    reader.store = SimpleNamespace(get=lambda handle: {"artifact_ref": "handoff-fixture"},
        get_artifact=lambda reference: json.dumps({"receipt": {"tool_name": "practical.job.start"}}).encode())
    result = reader.describe_target("synthetic-handoff", {"subject_refs": ["synthetic-subject"]}, selector=selected)
    assert calls == [("synthetic-handoff", {"subject_refs": ["synthetic-subject"]})]
    assert result == describe(original, selected)


def test_ordinary_local_target_keeps_existing_information():
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    reader = object.__new__(ExecutionTargetReader)
    reader.api_execution = None
    reader.operations = {"local": object.__new__(LocalPracticalOperations)}
    reader.read_target = lambda handle, scope: {"resource_kind": "local", "resource_id": "local",
        "assignment": {"requested_job": {"argv": ["ordinary-program"]}}}
    reader.store = SimpleNamespace(get=lambda handle: {"artifact_ref": "handoff-fixture"},
        get_artifact=lambda reference: json.dumps({"receipt": {"tool_name": "practical.job.start"}}).encode())
    result = reader.describe_target("synthetic-handoff", {})
    assert result["service_or_program"] == "ordinary-program"
    assert result["acquisition_operations"] == ["execution.results.status", "execution.results.collect", "execution.results.read"]
