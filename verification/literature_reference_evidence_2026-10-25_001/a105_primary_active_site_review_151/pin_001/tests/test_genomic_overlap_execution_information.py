"""Pure information checks using synthetic supplied execution records only.

These tests grant no receipt authority, run no native analysis, and make no
claim of complete Workflow integration. Run through packet438/run_bounded.py.
"""
from copy import deepcopy
from importlib import import_module
import builtins
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.genomic_overlap_contracts import genomic_overlap_schema
from gene_annotation_episode.genomic_overlap_execution_information import (
    describe_genomic_overlap_result, genomic_overlap_result_selector_schema,
)
from gene_annotation_episode.genomic_overlap_return_views import genomic_overlap_fact_sources


fixtures = import_module("verification.tool_graders_genomic_overlap_execution_contracts_2026-10-27_426.fixtures")
KEYS = {"resource_kind", "service_or_program", "operation", "mode", "output_format",
    "called_operation", "selected_outputs", "result_selector_schema", "result_selection",
    "status_operations", "acquisition_operations", "status_meanings", "extractors", "return_fact_sources"}


def target():
    plan, _ = fixtures.fixture()
    requested = plan["requested_job"]
    return {"version": "execution_target_v1", "handle": "synthetic-handoff-438",
        "run_id": "synthetic-run-438", "resource_id": "configured-local-438",
        "resource_kind": "local", "execution_id": plan["identity"]["execution_id"],
        "request_sha256": digest(requested), "origin_episode_id": "synthetic-local-child-438",
        "assignment": {"resource_kind": "local", "resource_id": "configured-local-438",
            "requested_job": requested}, "scope": {"subject_refs": ["synthetic-subject-438"]}}


def selector(kind="pair_metrics", *, saved=False):
    selected = {"version": "genomic_overlap_result_selector_v1", "mode": "native_result",
        "comparison_keys": ["comparison_0", "comparison_2"], "saved_sheet_file": None,
        "parameters": {"version": "genomic_overlap_calculation_parameters_v1", "minimum_overlap_bp": 4,
            "minimum_a_fraction": {"numerator": 0, "denominator": 1},
            "minimum_b_fraction": {"numerator": 1, "denominator": 3}},
        "projection": {"kind": kind, "offset": 1, "limit": 2,
            "measurement_fields": [{"pair_metrics": "unfiltered.jaccard_bp",
                                    "set_metrics": "union_bp", "occurrence_rows": "span_bp"}[kind]],
            "occurrence_keys": [{"set_key": "A", "occurrence_key": "s0_r0"}] if kind == "occurrence_rows" else []}}
    if saved:
        selected.update(mode="saved_sheet_recalculation", saved_sheet_file={
            "artifact_ref": "artifact_" + "a" * 64, "sha256": "a" * 64,
            "size_bytes": 1234, "format": "genomic_region_overlap_sheet_v1"})
    return selected


def collect(description):
    return next(row for row in description["extractors"] if row["operation"] == "execution.results.collect")


def name(function):
    return function.__module__ + "." + function.__qualname__


@pytest.mark.parametrize("kind", ["pair_metrics", "set_metrics", "occurrence_rows"])
def test_original_description_preserves_actual_job_and_explicit_projection(kind):
    original, selected = target(), selector(kind)
    result = describe_genomic_overlap_result(original, called_operation="practical.job.start", selector=selected)
    job = original["assignment"]["requested_job"]["native_genomic_overlap"]
    assert set(result) == KEYS
    assert result["resource_kind"] == "local"
    assert result["status_meanings"]["resource_id"] == "configured-local-438"
    assert result["service_or_program"] == job["program"] == "bedtools_intersect_all_pairs"
    assert result["operation"] == job["request"]["operation"] == "analyze_genomic_region_overlap"
    assert result["mode"] == job["request"]["mode"] == "unstranded_outer_span"
    assert result["output_format"] == "genomic_overlap_native_batch_v1"
    assert result["selected_outputs"] == job["outputs"]
    assert len(result["selected_outputs"]) == 26
    assert result["result_selection"] == selected
    assert result["called_operation"] == "practical.job.start"
    assert result["status_operations"] == ["progress.observe", "execution.results.status"]
    assert result["acquisition_operations"] == ["execution.results.collect"]
    assert [row["operation"] for row in result["extractors"]] == [
        "progress.observe", "execution.results.status", "execution.results.collect"]
    extractor = collect(result)
    assert extractor["native_format"] == "bedtools_intersect_wo_bed4_v1"
    assert extractor["calculator_parameters"] == selected["parameters"]
    assert extractor["original_native_execution"]["program"] == "bedtools"
    assert extractor["original_native_execution"]["executable"] == job["software"]["bedtools_executable"]
    assert extractor["original_native_execution"]["declared_version"] == job["software"]["bedtools_version"]
    assert extractor["original_native_execution"]["operation"] == "intersect"
    assert extractor["original_native_execution"]["options"] == ["-wo", "-sorted"]
    assert extractor["new_native_analysis"] is False
    assert extractor["scientific_annotation_score"] is False
    assert extractor["local_job_policy"] == {"memory_bytes": 20 * 1024**3,
        "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
    assert extractor["swap_bytes"] == 0
    assert "execution.results.read" not in json.dumps(result)


@pytest.mark.parametrize("kind", ["pair_metrics", "set_metrics", "occurrence_rows"])
def test_saved_description_uses_sheet_and_parameters_without_native_probe_or_acquisition(kind):
    selected = selector(kind, saved=True)
    result = describe_genomic_overlap_result(target(), selector=selected)
    extractor = collect(result)
    assert set(result) == KEYS
    assert result["operation"] == "analyze_genomic_region_overlap"
    assert result["service_or_program"] == "bedtools_intersect_all_pairs"
    assert result["output_format"] == "genomic_region_overlap_components_v1"
    assert result["result_selection"] == selected
    assert result["called_operation"] is None
    assert result["status_operations"] == ["execution.results.status"]
    assert result["acquisition_operations"] == ["execution.results.collect"]
    assert [row["operation"] for row in result["extractors"]] == [
        "execution.results.status", "execution.results.collect"]
    assert result["extractors"][0]["fresh_native_observation"] is False
    assert result["extractors"][0]["return_fact_sources"] == []
    assert result["extractors"][0]["completes_assignment"] is False
    assert extractor["calculation_operands"] == {"sheet": selected["saved_sheet_file"],
                                                "parameters": selected["parameters"]}
    assert extractor["native_input_acquisition"] is False
    assert extractor["new_native_analysis"] is False
    assert extractor["original_sheet_and_completed_observations_preserved"] is True
    assert not {"capture", "native_format", "parser", "input_parser", "sheet_population",
                "metadata_extractor", "original_native_execution"} & extractor.keys()
    assert result["status_meanings"]["fresh_native_observation"] is False
    assert result["status_meanings"]["original_receipt_authority_is_current_byte_availability"] is False


@pytest.mark.parametrize("saved", [False, True])
def test_sources_and_data_meanings_preserve_exact_public_return_boundary(saved):
    result = describe_genomic_overlap_result(target(), selector=selector(saved=saved))
    expected = ["genomic_overlap_pair_metrics", "genomic_overlap_saved_sheets", "genomic_overlap_failures"]
    assert result["return_fact_sources"] == expected == list(genomic_overlap_fact_sources())
    assert collect(result)["return_fact_sources"] == expected
    assert collect(result)["complete_data_retained"] is True
    assert collect(result)["projection_scope"] == "selected_comparisons_measurement_fields_occurrence_keys_and_page"
    assert collect(result)["return_source_scope"] == "receiving_form_requested_sources"
    meanings = result["status_meanings"]
    assert meanings["scientific_extents"] == ["complete", "partial", "unavailable"]
    assert meanings["missing_partial_unavailable_are_measured_zero"] is False
    assert meanings["native_success_capture_complete_delivery_complete_are_separate"] is True
    assert meanings["process_liveness_establishes_productive_work"] is False
    assert meanings["status_completes_assignment"] is False


@pytest.mark.parametrize("called", [None, "practical.job.start", "practical.job.status", "practical.job.collect"])
def test_operation_is_only_supplied_receipt_identity_and_selection_is_not_invented(called):
    original = target()
    original["execution_id"] = "/synthetic/practical.job.collect"
    result = describe_genomic_overlap_result(original, called_operation=called)
    assert result["called_operation"] == called
    assert result["result_selection"] is None
    assert collect(result)["calculator_parameters"] is None


@pytest.mark.parametrize("called", ["", "execution.results.collect", "bedtools", "practical.job.restart", 1, [], "practical.job.start\0"])
def test_unknown_called_operation_rejects(called):
    with pytest.raises(ValueError, match="execution_called_operation_invalid"):
        describe_genomic_overlap_result(target(), called_operation=called)


@pytest.mark.parametrize("mutation", [
    lambda t: t.pop("version"),
    lambda t: t.update(extra=True),
    lambda t: t.update(resource_kind="api"),
    lambda t: t.update(resource_kind="hpc"),
    lambda t: t["assignment"].update(resource_kind="hpc"),
    lambda t: t["assignment"].update(resource_id="other-local"),
    lambda t: t["assignment"].pop("resource_id"),
    lambda t: t.update(request_sha256="0" * 64),
    lambda t: t["assignment"]["requested_job"].pop("native_genomic_overlap"),
    lambda t: t["assignment"]["requested_job"]["argv"].append("--extra"),
    lambda t: t["assignment"]["requested_job"]["native_genomic_overlap"]["outputs"].reverse(),
    lambda t: t["assignment"]["requested_job"]["native_genomic_overlap"]["request"]["comparisons"].reverse(),
])
def test_wrong_target_resource_request_or_fixed_outputs_reject(mutation):
    original = target()
    mutation(original)
    with pytest.raises(ValueError):
        describe_genomic_overlap_result(original, selector=selector())


@pytest.mark.parametrize("mutation", [
    lambda s: s.update(version="other_selector"),
    lambda s: s.update(extra=True),
    lambda s: s["comparison_keys"].reverse(),
    lambda s: s["comparison_keys"].append("comparison_0"),
    lambda s: s.update(comparison_keys=["unrequested"]),
    lambda s: s["parameters"].update(minimum_overlap_bp=True),
    lambda s: s["parameters"]["minimum_b_fraction"].update(numerator=4),
    lambda s: s["projection"].update(measurement_fields=["annotation_confidence"]),
    lambda s: s["projection"].update(offset=-1),
    lambda s: s["projection"].update(occurrence_keys=[{"set_key": "A", "occurrence_key": "s0_r0"}]),
    lambda s: s.update(mode="saved_sheet_recalculation"),
    lambda s: s.update(saved_sheet_file=selector(saved=True)["saved_sheet_file"]),
])
def test_wrong_selector_order_fields_parameters_or_mode_reject(mutation):
    selected = selector()
    mutation(selected)
    with pytest.raises(ValueError):
        describe_genomic_overlap_result(target(), selector=selected)


@pytest.mark.parametrize("mutation", [
    lambda s: s["projection"]["occurrence_keys"].append(deepcopy(s["projection"]["occurrence_keys"][0])),
    lambda s: s["projection"]["occurrence_keys"][0].update(set_key="C"),
])
def test_occurrence_selection_reuses_existing_requested_pair_scope(mutation):
    selected = selector("occurrence_rows")
    selected["comparison_keys"] = ["comparison_0"]
    mutation(selected)
    with pytest.raises(ValueError):
        describe_genomic_overlap_result(target(), selector=selected)


@pytest.mark.parametrize("mutation", [
    lambda s: s["saved_sheet_file"].update(format="bedtools_intersect_wo_bed4_v1"),
    lambda s: s["saved_sheet_file"].update(artifact_ref="unrelated-artifact"),
    lambda s: s["saved_sheet_file"].update(size_bytes=False),
])
def test_saved_operand_uses_the_accepted_saved_sheet_identity(mutation):
    selected = selector(saved=True)
    mutation(selected)
    with pytest.raises(ValueError):
        describe_genomic_overlap_result(target(), selector=selected)


@pytest.mark.parametrize("saved", [False, True])
def test_description_containers_and_selector_schema_are_detached(saved):
    original, selected = target(), selector(saved=saved)
    before = deepcopy((original, selected))
    result = describe_genomic_overlap_result(original, selector=selected)
    result["selected_outputs"].clear()
    result["result_selection"]["parameters"]["minimum_overlap_bp"] = 99
    collect(result)["calculator_parameters"]["minimum_overlap_bp"] = 98
    collect(result)["return_fact_sources"].clear()
    assert result["return_fact_sources"] == list(genomic_overlap_fact_sources())
    result["return_fact_sources"].clear()
    result["result_selector_schema"]["$defs"]["Selector"]["properties"].clear()
    if saved:
        collect(result)["calculation_operands"]["sheet"].clear()
    assert (original, selected) == before
    assert genomic_overlap_result_selector_schema()["$defs"]["Selector"]["properties"]


def _reachable(schema):
    found = set()
    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                assert reference.startswith("#/$defs/")
                key = reference[len("#/$defs/"):]
                if key not in found:
                    found.add(key)
                    visit(schema["$defs"][key])
            for key, child in value.items():
                if key not in {"$defs", "$ref"}:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(schema)
    return found


def test_embedded_schema_has_only_unchanged_reachable_g1_definitions_and_its_own_scope():
    original = genomic_overlap_schema("Selector")
    schema = genomic_overlap_result_selector_schema()
    reachable = _reachable(original)
    assert schema["$id"].startswith("urn:gene-annotation:genomic-overlap:result-selector:")
    assert set(schema["$defs"]) == _reachable(schema) == reachable
    assert {key: original["$defs"][key] for key in reachable} == schema["$defs"]
    assert not {"Sheet", "Components", "Projection", "Request"} & reachable
    embedded = {"type": "object", "properties": {"selector": schema}, "required": ["selector"],
        "additionalProperties": False, "$defs": {"Selector": {"not": {}}}}
    Draft202012Validator.check_schema(embedded)
    plain_validator, embedded_validator = Draft202012Validator(original), Draft202012Validator(embedded)
    for saved in (False, True):
        for kind in ("pair_metrics", "set_metrics", "occurrence_rows"):
            chosen = selector(kind, saved=saved)
            for mutation in (lambda s: None, lambda s: s.update(extra=1),
                             lambda s: s["projection"].update(measurement_fields=["unsupported"]),
                             lambda s: s["parameters"].pop("minimum_overlap_bp")):
                mutated = deepcopy(chosen)
                mutation(mutated)
                assert embedded_validator.is_valid({"selector": mutated}) == plain_validator.is_valid(mutated)
            embedded_validator.validate({"selector": chosen})


def test_every_advertised_execution_reader_calculator_and_projection_function_exists():
    from gene_annotation_episode import genomic_overlap_inputs, genomic_overlap_calculations
    from gene_annotation_episode import genomic_overlap_result_worker, genomic_overlap_result_views
    from gene_annotation_episode import genomic_overlap_return_views, genomic_overlap_returns
    from gene_annotation_episode import native_genomic_overlap_capture, native_genomic_overlap_preparation
    from gene_annotation_episode import native_genomic_overlap_driver
    from gene_annotation_episode.native_genomic_overlap_results import NativeGenomicOverlapResults, operation_catalog
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    native = describe_genomic_overlap_result(target(), selector=selector())
    saved = describe_genomic_overlap_result(target(), selector=selector(saved=True))
    assert [row["name"] for row in operation_catalog()] == ["execution.results.status", "execution.results.collect"]
    for value in (native, saved):
        scientific = collect(value)
        assert scientific["implementation"] == name(NativeGenomicOverlapResults.execute)
        assert scientific["preparation"] == name(native_genomic_overlap_preparation.prepare_genomic_overlap_worker)
        assert scientific["result_worker"] == name(genomic_overlap_result_worker.run_genomic_overlap_result_worker)
        assert scientific["worker_output_capture"] == name(native_genomic_overlap_preparation.capture_genomic_overlap_worker_outputs)
        assert scientific["calculators"] == [name(genomic_overlap_calculations.calculate_genomic_overlap_components)]
        assert scientific["projection_implementation"] == name(genomic_overlap_result_views.project_genomic_overlap_result)
        assert scientific["return_source_selection"] == name(genomic_overlap_return_views.requested_genomic_overlap_sources)
    scientific = collect(native)
    for key, function in (
        ("capture", native_genomic_overlap_capture.capture_genomic_overlap_native_files),
        ("worker_plan", native_genomic_overlap_preparation.build_native_genomic_overlap_worker_plan),
        ("parser", genomic_overlap_inputs.parse_bedtools_intersect_wo),
        ("input_parser", genomic_overlap_inputs.parse_region_set),
        ("metadata_extractor", genomic_overlap_inputs.extract_overlap_reference_metadata),
        ("sheet_population", genomic_overlap_inputs.build_genomic_overlap_sheet),
    ):
        assert scientific[key] == name(function)
    assert scientific["original_native_execution"]["implementation"] == name(native_genomic_overlap_driver.run_genomic_overlap_driver)
    assert native["extractors"][0]["implementation"] == name(LocalPracticalOperations.observe_execution)
    assert collect(saved)["worker_plan"] == name(native_genomic_overlap_preparation.build_saved_genomic_overlap_worker_plan)
    assert collect(saved)["saved_input_validation"] == name(genomic_overlap_returns.GenomicOverlapReturns.authenticate_received_saved_sheet)


def test_information_never_opens_files_uses_store_observes_executes_or_calculates(monkeypatch):
    from gene_annotation_episode import genomic_overlap_inputs, genomic_overlap_calculations
    from gene_annotation_episode import genomic_overlap_result_worker, genomic_overlap_result_views
    from gene_annotation_episode import native_genomic_overlap_capture, native_genomic_overlap_preparation
    from gene_annotation_episode import native_genomic_overlap_driver
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    from gene_annotation_episode.state import Store
    original = target()
    native, saved = selector(), selector(saved=True)
    before = deepcopy((original, native, saved))
    def forbidden(*args, **kwargs):
        raise AssertionError("information port performed an effect or scientific calculation")
    with monkeypatch.context() as guard:
        for module, attribute in (
            (builtins, "open"), (io, "open"), (os, "open"), (os, "stat"),
            (Path, "stat"), (Path, "read_bytes"), (Path, "read_text"),
            (subprocess, "Popen"), (subprocess, "run"), (socket, "socket"), (socket, "create_connection"),
            (Store, "__init__"), (Store, "get"), (Store, "get_artifact"), (Store, "artifact"), (Store, "put"),
            (LocalPracticalOperations, "observe_execution"),
            (native_genomic_overlap_capture, "capture_genomic_overlap_native_files"),
            (native_genomic_overlap_preparation, "prepare_genomic_overlap_worker"),
            (native_genomic_overlap_driver, "run_genomic_overlap_driver"),
            (genomic_overlap_result_worker, "run_genomic_overlap_result_worker"),
            (genomic_overlap_inputs, "parse_region_set"), (genomic_overlap_inputs, "parse_bedtools_intersect_wo"),
            (genomic_overlap_inputs, "extract_overlap_reference_metadata"),
            (genomic_overlap_inputs, "build_genomic_overlap_sheet"),
            (genomic_overlap_calculations, "calculate_genomic_overlap_components"),
            (genomic_overlap_result_views, "project_genomic_overlap_result"),
        ):
            guard.setattr(module, attribute, forbidden)
        assert describe_genomic_overlap_result(original, selector=native)["operation"] == "analyze_genomic_region_overlap"
        assert describe_genomic_overlap_result(original, selector=saved)["called_operation"] is None
        assert genomic_overlap_result_selector_schema()["$defs"]["Selector"]
    assert (original, native, saved) == before
