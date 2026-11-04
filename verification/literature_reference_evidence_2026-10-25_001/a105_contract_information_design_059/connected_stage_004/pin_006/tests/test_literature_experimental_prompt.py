"""Pure literature TASK/STEERING checks over explicitly synthetic state."""
from copy import deepcopy
from types import MappingProxyType

import pytest

from gene_annotation_episode.decision_context import INSTRUCTIONS
from gene_annotation_episode.literature_experimental_prompt import (
    EXPERIMENTAL_TASK, VERSION, is_literature_experimental_context,
    render_literature_experimental_prompt,
)


def state():
    return {
        "literature_experimental_work": {"version": VERSION, "aspect": "source_rate_comparison"},
        "goal": {"goal_id": "PRIVATE_GOAL", "parent_goal_id": "PRIVATE_PARENT",
            "objective": "Determine what the reference preparation's oxygen-rate comparison establishes.",
            "task_context": {"construct": "His-tagged reference preparation", "constraint": "selected experiment only"}},
        "scope": {"subject_refs": ["input_selected"]},
        "literature_assignment": {"version": "PRIVATE_ASSIGNMENT_VERSION", "question_context_refs": ["reference_assayed"],
            "source_refs": ["source_selected"], "requested_rate_components": ["rate_difference", "source_signed_index"],
            "parent_history": "PRIVATE_PARENT_HISTORY"},
        "literature_source_custody": [{"source_ref": "source_selected", "artifact_ref": "artifact_original",
            "text_ref": "artifact_text", "version": "publisher-original", "sha256": "PRIVATE_SOURCE_HASH"}],
        "working_state": {"problem_ref": "PRIVATE_PROBLEM", "subjects": [{"id": "input_selected", "record_type": "input",
            "molecule": "protein", "length": 5, "sequence_ref": "artifact_sequence", "name": "selected reference snippet"}],
            "materials": [{"id": "material_selected", "name": "supplied.faa", "source_ref": "source_supplied"}],
            "sources": [{"id": "source_inventory", "label": "UNREQUESTED_SOURCE_INVENTORY"}],
            "references": [{"id": "reference_assayed", "record_type": "reference", "label": "Actual assayed preparation",
                "source_ref": "source_selected", "context_refs": ["context_measured"]},
                {"id": "reference_unrequested", "label": "UNREQUESTED_REFERENCE"}],
            "contexts": [{"id": "context_measured", "name": "30 degrees C; inhibitor absent",
                "source_ref": "source_selected", "attributes": []}],
            "observations": [{"id": "observation_unrequested", "value": "UNREQUESTED_OBSERVATION"}]},
        "tools": [{"name": "source.read", "description": "Read an exact retained source window.",
            "input_schema": {"type": "object", "properties": {"source_ref": {"type": "string", "format": "reference"},
                "offset": {"type": "integer", "minimum": 0}}, "required": ["source_ref"], "additionalProperties": False}}],
        "child_options": "A page investigation can select a targeted passage investigation; no fixed child order.",
        "requested_report_purpose": "Return the measured contrast and specific unavailable reasons.",
        "requested_form": {"type": "object", "properties": {
            "measurements": {"type": "array", "items": {"type": "number"}, "x-source": "literature_rate_cells",
                "description": "Source-rate cells; no target-transfer credit."}}, "required": ["measurements"], "additionalProperties": False},
        "available_report_facts": {
            "literature_rate_cells": {"meaning": "Saved source measurements with their conditions and limitations."},
            "unrequested": {"meaning": "UNREQUESTED_FACT_DEFINITION"}},
        "report_lifecycle": "Later source facts do not silently rewrite an earlier interpretation.",
        "controller": {"scores": [999], "epoch": "PRIVATE_EPOCH", "estimate": {"turns": 3,
            "expected_next_gain": {"value": .2, "lower": -.1, "upper": .6, "status_code": 0,
                "uncertainty_code": 2, "alpha": .05}, "diagnostics": {"fit": "PRIVATE_FIT"}},
            "decision": {"continuation_cost": .001}},
        "action_yields": {"rows": [{"category": "tool/source.read", "completed_actions": 2,
            "total_yield": -.25, "attempted_uncompleted": 1,
            "expected_yield": {"status": "unavailable", "unavailable_reason": "parameters_unbound", "band": None}}]},
        "own_literature_outcomes": {"records": ["PRIVATE_OUTCOME_INVENTORY"]},
        "waiting_support": {"own_completed_action_history": ["PRIVATE_OWN_HISTORY"],
            "local_return_history": {"samples": ["PRIVATE_CHILD_HISTORY"]}},
        "restored_episode_history": {"entries": ["PRIVATE_RESTORE_HISTORY"]},
        "parent_history": "PRIVATE_PARENT_HISTORY",
        "last_local_outcome": None, "feedback": None, "child_reports": [],
        "current_report_update": {}, "current_report_basis_refs": [], "pending_work": {"items": []},
    }


def render(value=None, **kwargs):
    return render_literature_experimental_prompt(state() if value is None else value,
        "Examine the parent's assigned reference experiment iteratively.\n" + INSTRUCTIONS, **kwargs)


def test_actual_assignment_and_complete_experimental_task_repeat_on_each_render():
    before = state()
    after = deepcopy(before)
    after["feedback"] = {"code": "condition_mismatch", "field": "test_condition"}
    for text in (render(before), render(after), render(after, lookup_results=[{"result": {"text": "Neighboring source passage."}}])):
        assert text.startswith("TASK\n\n")
        assert text.count("\n\nSTEERING\n") == 1
        task, steering = text.split("\n\nSTEERING\n")
        assert EXPERIMENTAL_TASK in task
        assert "Determine what the reference preparation's oxygen-rate comparison establishes." in task
        assert "His-tagged reference preparation" in task
        assert "selected experiment only" in task
        assert "no-inhibitor reference is not a no-enzyme blank" in task
        assert "Three measurements do not by themselves establish three independent biological preparations" in task
        assert "Sequence or structural target correspondence and combined annotation credit are separate work" in task
        assert "source.read" in task and "arguments.source_ref" in task
        assert "source_selected" in task and "artifact_original" in task
        assert "supplied.faa" in task and "selected reference snippet" in task
        assert "no fixed child order" in task
        assert "Return the measured contrast and specific unavailable reasons." in task
        assert "Source-rate cells; no target-transfer credit." in task
        assert "Saved source measurements with their conditions and limitations." in task
        assert "parameters_unbound" in steering
        assert "| tool/source.read | 2 | -0.25 | unavailable | parameters_unbound | 1 |" in steering


def test_host_history_inventory_and_unrequested_records_are_excluded():
    text = render()
    assert "PRIVATE_" not in text
    assert "UNREQUESTED_" not in text
    assert "Actual assayed preparation" in text
    assert "30 degrees C; inhibitor absent" in text
    assert "decision_bootstrap supplies" not in text
    assert "base_revision" not in text and "removed_fields" not in text
    assert "request_context" in text and "select_action" in text
    assert '"goal"' not in text and '"literature_assignment"' not in text


def test_selected_source_quote_keeps_limits_units_and_locations_without_claiming_a_product_rate():
    sample = state()
    source_text = "Preparation oxygen consumption was <0.1 µmol/min; product coupling was not measured."
    sample["last_local_outcome"] = {"status": "completed", "operation_ref": "PRIVATE_OPERATION",
        "record_refs": [], "changed_record_refs": [], "result": {"text": source_text,
            "source_ref": "source_selected", "artifact_ref": "artifact_original", "representation": "original",
            "start": 120, "end": 214, "next_offset": 214, "content_sha256": "PRIVATE_CONTENT_HASH",
            "qualification": "Nondetection is not exact zero."}}
    text = render(sample)
    assert source_text in text
    assert "Nondetection is not exact zero." in text
    assert "| start | 120 |" in text and "| end | 214 |" in text
    assert "PRIVATE_" not in text


def test_numerical_cells_preserve_signed_values_unknowns_uncertainty_and_proposed_origin():
    sample = state()
    sample["last_local_outcome"] = {"status": "partial", "operation_ref": "PRIVATE_OPERATION",
        "record_refs": ["source_sheet"], "result": {"sheet_ref": "source_sheet", "cells": {
            "rate_difference": {"value": -.25, "unit": "umol/min", "status": "populated", "origin": "derived",
                "unavailable_reason": None, "conditional_on": []},
            "source_signed_index": {"value": None, "unit": "dimensionless", "status": "unavailable", "origin": "proposed",
                "unavailable_reason": "dependence_unknown", "conditional_on": ["independent_groups"]}},
            "source_uncertainty": {"reference": {"kind": "sd", "magnitude": .1,
                "count": 3, "sampling_basis": "technical_measurements"}},
            "extraction": {"private_history": "PRIVATE_EXTRACTION_HISTORY"},
            "calculation_implementation": "PRIVATE_CALCULATOR"}}
    text = render(sample)
    steering = text.split("\n\nSTEERING\n")[1]
    assert "| rate_difference | -0.25 | umol/min | populated |" in steering
    assert "| source_signed_index | unknown | dimensionless | unavailable | dependence_unknown | independent_groups | proposed |" in steering
    assert "technical_measurements" in steering and "reference.kind | sd" in steering
    assert "reference.count | 3" in steering and "reference.magnitude | 0.1" in steering
    assert "PRIVATE_" not in text


def test_requested_child_values_and_linked_subject_qualifications_are_preserved():
    sample = state()
    sample["child_reports"] = [{"measurements": [{"component": "rate_difference", "value": .5,
        "unit": "umol/min", "status": "populated", "assayed_subject_ref": "reference_assayed",
        "qualification": "Source preparation only; molecule-specific product rate unknown."}]}]
    text = render(sample)
    assert "Source preparation only; molecule-specific product rate unknown." in text
    assert "Actual assayed preparation" in text and "30 degrees C; inhibitor absent" in text
    assert "measurements[0].value | 0.5" in text
    assert "UNREQUESTED_" not in text


def test_supplied_censor_bounds_and_sampling_intervals_are_not_lost_or_reinterpreted():
    sample = state()
    sample["last_local_outcome"] = {"status": "partial", "result": {"cells": {
        "test_rate": {"value": None, "unit": "umol/min", "status": "unavailable",
            "unavailable_reason": "censored_measurement", "origin": "reported", "conditional_on": [],
            "bound": "lt", "threshold": .1, "lower": 0, "upper": .1,
            "uncertainty": {"kind": "detection_limit", "sampling_basis": "instrument_limit"}},
        "source_effect": {"value": -.2, "unit": "umol/min", "status": "populated",
            "unavailable_reason": None, "origin": "derived", "conditional_on": [],
            "uncertainty": {"kind": "confidence_interval", "lower": -.4, "upper": -.1,
                "level": .95, "sampling_basis": "independent_preparations"}}}}}
    text = render(sample)
    assert "| test_rate | unknown | umol/min | unavailable | censored_measurement |" in text
    assert "test_rate.bound | lt" in text and "test_rate.threshold | 0.1" in text
    assert "detection_limit" in text and "instrument_limit" in text
    assert "confidence_interval" in text and "source_effect.uncertainty.lower | -0.4" in text
    assert "source_effect.uncertainty.level | 0.95" in text
    assert "independent_preparations" in text


def test_lookup_and_actionable_failure_are_not_a_transcript_or_extra_task():
    sample = state()
    sample["feedback"] = {"category": "arguments_or_reference", "code": "wrong_subject",
                          "field": "subject", "private_history": "PRIVATE_FAILURE_HISTORY"}
    lookup = {"status": "completed", "operation_ref": "PRIVATE_LOOKUP_OPERATION", "result": {
        "text": "The assay used the source preparation; independent preparations were not specified.",
        "source_ref": "source_selected", "start": 8, "end": 99, "section_sha256": "PRIVATE_SECTION_HASH"}}
    text = render(sample, lookup_results=[lookup])
    assert "wrong_subject" in text and "| field | subject |" in text
    assert "independent preparations were not specified" in text
    assert "| start | 8 |" in text
    assert "PRIVATE_" not in text
    assert text.count(EXPERIMENTAL_TASK) == 1


def test_pending_only_exposes_decision_relevant_handles_and_states():
    sample = state()
    sample["pending_work"] = {"items": [{"handle": "child_selected", "role": "literature_page",
        "lifecycle_state": "executing", "return_available": False,
        "private_history": "PRIVATE_CHILD_TRACE", "pid": "PRIVATE_PID"}]}
    text = render(sample)
    assert "child_selected" in text and "executing" in text and "false" in text
    assert "PRIVATE_" not in text


def test_renderer_has_no_mutation_or_dependency_on_backend_history():
    sample = state()
    sample["last_local_outcome"] = {"status": "invalid", "result": None,
        "feedback": {"code": "missing_source", "field": "source_ref"}}
    lookups = [{"result": {"text": "Scoped returned text."}}]
    before = deepcopy((sample, lookups))
    first = render(sample, lookup_results=lookups)
    assert render(sample, lookup_results=lookups) == first
    assert (sample, lookups) == before


def test_expanded_instructions_do_not_duplicate_the_experimental_task():
    text = render_literature_experimental_prompt(state(), INSTRUCTIONS + "\n" + EXPERIMENTAL_TASK)
    assert text.count(EXPERIMENTAL_TASK) == 1


@pytest.mark.parametrize("value", [None, [], {}, {"literature_experimental_work": None},
    {"literature_experimental_work": {"version": "another_version"}}])
def test_only_explicit_supported_marker_selects_the_renderer(value):
    assert not is_literature_experimental_context(value)
    with pytest.raises(ValueError, match="literature_experimental_context_required"):
        render_literature_experimental_prompt(value, INSTRUCTIONS)


def test_marker_accepts_readonly_mappings():
    sample = state()
    sample["literature_experimental_work"] = MappingProxyType(sample["literature_experimental_work"])
    assert is_literature_experimental_context(MappingProxyType(sample))
    assert render(sample).startswith("TASK\n\n")


def test_single_source_quantity_assignment_and_untyped_spread_reach_text():
    value = state()
    value['literature_assignment']['requested_quantity_components'] = ['reported_value', 'reported_spread']
    value['last_local_outcome'] = {'status': 'completed', 'result': {
        'subject': 'P', 'quantity': 'apparent_km', 'analyte': 'substrate A',
        'source_ref': 'source_selected', 'artifact_ref': 'artifact_original',
        'section_id': 'results_section', 'paragraph_id': 'kinetics_paragraph',
        'expression_start': 14, 'expression_end': 48, 'coordinate_unit': 'paragraph_unicode_characters',
        'text': 'P: apparent Km = 650 ± 20 uM for substrate A.',
        'source_uncertainty': {'kind': 'unspecified', 'magnitude': 20, 'count': None},
        'cells': {'reported_value': {'value': 650, 'unit': 'uM', 'status': 'populated',
            'unavailable_reason': None, 'conditional_on': [], 'origin': 'reported'}}}}
    task, steering = render(value).split('\n\nSTEERING\n')
    assert 'requested_quantity_components' in task
    assert 'reported_spread' in task
    assert 'without inventing comparison arms' in task
    for fact in ('apparent_km', 'substrate A', 'results_section', 'kinetics_paragraph',
                 'paragraph_unicode_characters', 'unspecified', '650', '20'):
        assert fact in steering


def test_assay_context_and_operand_unknowns_are_factual_steering_without_internal_graph_dump():
    from gene_annotation_episode.literature_assay_prompt import ASSAY_TASK
    value = state()
    value['literature_assignment']['requested_assay_components'] = ['corrected_activity','source_presence_index']
    value['last_local_outcome'] = {'status':'completed','result':{
        'source_kind':'primary_source','interpretation_kind':'episode_source_interpretation',
        'assay_interpretation':{
            'molecule':{'value':'enzyme P','witness':{'quote':'enzyme P'}},
            'condition':None,
            'endpoint':{'value':'oxygen_consumption','witnesses':[{'quote':'oxygen electrode'}]},
            'arrangement':{'value':'single_preparation','witnesses':[{'quote':'one preparation'}]}},
        'primitive_observations':{
            'E':{'value':.18,'unit':'uM','witness':{'quote':'180 nM enzyme P'},'measurement_key':'PRIVATE_MEASUREMENT_KEY'},
            'g':None},
        'model_assumptions':{'variance_status':'unknown','observation_model':'none','covariance_origin':None},
        'cells':{'source_presence_index':{'value':None,'unit':'dimensionless','status':'unavailable',
            'unavailable_reason':'correction_inputs_unreported','conditional_on':[],'origin':'proposed'}}}}
    task,steering=render(value).split('\n\nSTEERING\n')
    assert ASSAY_TASK in task
    assert 'requested_assay_components' in task
    assert 'oxygen_consumption' in steering and 'oxygen electrode' in steering
    assert '180 nM enzyme P' in steering and '0.18' in steering
    assert 'correction_inputs_unreported' in steering
    assert 'unknown' in steering and 'primary_source' in steering
    assert 'PRIVATE_MEASUREMENT_KEY' not in steering
