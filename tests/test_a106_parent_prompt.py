"""Axis selection in the actual parent renderer, without a model or workflow."""
from copy import deepcopy

import pytest

from gene_annotation_episode.literature_perturbation_prompt import A106_PARENT_TASK
from gene_annotation_episode.literature_task_selection import A105_ASSAY_SELECTION_TASK
from test_literature_reference_parent_prompt import render, split, state


@pytest.mark.parametrize("axis,expected", [
    (None, A105_ASSAY_SELECTION_TASK),
    ("A106", A106_PARENT_TASK),
])
def test_parent_axis_selects_its_investigation_before_any_child_return(axis, expected):
    value = state()
    if axis is not None:
        value["reference_evidence_parent"]["evidence_axis"] = axis
    value["goal"]["objective"] = "Investigate the assigned experimental evidence question."
    value["goal"].pop("result_contract")
    value["requested_form"] = None
    value["available_report_facts"] = {}
    before = deepcopy(value)
    task, _ = split(render(value))
    for instructions in (A105_ASSAY_SELECTION_TASK, A106_PARENT_TASK):
        assert (instructions in task) == (instructions == expected)
    if axis == "A106":
        assert "The A105 source-search" not in task
        assert "literature.a106.finalize" in task
        assert "changed_assessment_refs" in task
        assert "investigation_finding" in task
    assert value == before


def test_a106_child_return_keeps_parent_job_and_places_result_in_steering():
    value = state()
    value["reference_evidence_parent"]["evidence_axis"] = "A106"
    value["goal"]["objective"] = "Investigate this molecule's contribution to survival."
    value["goal"].pop("result_contract")
    value["requested_form"] = None
    value["available_report_facts"] = {}
    value["child_reports"] = [{"a106_subscore": [{
        "component": "experimental_subscore", "value": None, "unit": "natural_log_ratio",
        "status": "unavailable", "conclusion": "Fixture-specific survival finding.",
    }]}]
    task, steering = split(render(value))
    assert A106_PARENT_TASK in task and A105_ASSAY_SELECTION_TASK not in task
    assert "Investigate this molecule's contribution to survival." in task
    assert "Fixture-specific survival finding." not in task
    assert "Fixture-specific survival finding." in steering
