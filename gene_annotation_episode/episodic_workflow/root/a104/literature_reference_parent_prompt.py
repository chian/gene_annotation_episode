"""Text TASK/STEERING for an explicitly assigned source-evidence parent.

This presentation owns no investigation choice, child, model call, score,
source acquisition or continuation. The parent retains its actual caller job;
child source interpretation instructions are not substituted for that job.
"""
from __future__ import annotations

from collections.abc import Mapping

from .literature_experimental_prompt import (
    SAVED_NUMERICAL_RETURN_TASK, _pick, _safe, _schema, _section, _steering, _table, _values,
    CONTRACT_INFORMATION_TASK, _requested_contract_task,
)
from .evolutionary_history_evidence_prompt import text_instructions
from .composition_information import CONTRACT_INFORMATION_PROFILE, is_contract_information
from .schema_information_text import render_schema_information
from .literature_numerical_return_presentation import state_view
from .literature_task_selection import A105_ASSAY_SELECTION_TASK, selected_literature_task_sections
from .literature_parent_prompt import REFERENCE_PARENT_TASK


VERSION = "reference_evidence_parent_v1"


def _descriptor(state):
    marker = state.get("literature_experimental_work") if isinstance(state, Mapping) else None
    descriptor = state.get("reference_evidence_parent") if isinstance(state, Mapping) else None
    if (not isinstance(marker, Mapping)
            or marker.get("version") != "literature_experimental_task_v1"
            or marker.get("aspect") != "reference_evidence_parent"
            or not isinstance(descriptor, Mapping) or descriptor.get("version") != VERSION):
        raise ValueError("reference_evidence_parent_context_required")
    references = descriptor.get("source_refs")
    if (not isinstance(references, (list, tuple))
            or any(not isinstance(reference, str) or not reference for reference in references)
            or len(set(references)) != len(references)):
        raise ValueError("reference_evidence_parent_source_assignment_required")
    return descriptor


def _text_or_values(value):
    return _values(value) if isinstance(value, (Mapping, list, tuple)) else value


def _task(state, instructions, descriptor, *, selected_sections=None):
    normalized = text_instructions(instructions)
    parent_task, axis_task = REFERENCE_PARENT_TASK, A105_ASSAY_SELECTION_TASK
    parts = ["TASK", "", parent_task, "", axis_task,
             "", SAVED_NUMERICAL_RETURN_TASK]
    sections = selected_literature_task_sections(state) if selected_sections is None else selected_sections
    for aspect, task in sections:
        if task not in normalized:
            _section(parts, "Selected scientific instructions: " + aspect.removeprefix('literature_').removesuffix('_cells').replace('_', ' '), task)
    additional = (normalized.replace(parent_task, "")
        .replace(axis_task, "").replace(SAVED_NUMERICAL_RETURN_TASK, "").strip())
    if additional:
        parts.extend(["", additional])
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(['', CONTRACT_INFORMATION_TASK])
    goal = state.get("goal", {})
    _section(parts, "Assigned source-evidence question", _values(_pick(goal,
        ("objective", "task_context") if profile else ("objective", "task_context", "result_contract")))
        if isinstance(goal, Mapping) else str(goal))
    if (profile and isinstance(goal, Mapping) and goal.get('result_contract') is not None
            and goal['result_contract'] != state.get('requested_form')):
        _section(parts, 'Assigned result contract', render_schema_information(goal['result_contract'], title='Assigned result contract'))
    _section(parts, "Assigned scientific scope", _values(state.get("scope", {})))
    if descriptor['source_refs']:
        _section(parts, "Caller-selected source assignment", _values({"source_refs": descriptor["source_refs"]}))
    else:
        _section(parts, 'Experimental source discovery',
            'The caller supplied target material and no experimental source. Discover relevant publications using the target material below. Target sequence sources are query material; assign acquired publications as experimental sources once available.')
    references = set(descriptor["source_refs"])
    custody = [_pick(row, ("source_ref", "artifact_ref", "text_ref", "stdout_ref", "stderr_ref", "version"))
        for row in descriptor.get("source_custody", ())
        if isinstance(row, Mapping) and row.get("source_ref") in references]
    if custody:
        _section(parts, "Available representations of assigned sources", _values(custody))
    working = state.get("working_state", {})
    material = {name: [_safe(row) for row in working[name]]
        for name in ("subjects", "materials", "material_links") if working.get(name)}
    material.update(_pick(working, ("target_binding", "read_library_access", "supplied_context_source_refs")))
    if material:
        _section(parts, "Supplied material and scoped access", _values(material))
    if descriptor.get("supplied_context"):
        _section(parts, "Original caller-provided biological question and context",
            _values(descriptor["supplied_context"]))
    constraints = _pick(state, ("constraints", "selected_constraints"))
    if constraints:
        _section(parts, "Caller constraints", _values(constraints))
    tools = state.get("tools", ())
    if tools:
        _section(parts, "Available own operations", _table(("Operation", "Meaning"),
            ((row["name"], row.get("description", "")) for row in tools)))
        for row in tools:
            if "input_schema" in row:
                _section(parts, "Operands for " + row["name"], _schema(row["input_schema"], "arguments"))
    populations = descriptor.get("child_population_operations", ())
    if populations:
        _section(parts, "Population operations available within literature children",
            _table(("Child operation", "Input capability and meaning"),
                ((row["name"], row["description"]) for row in populations)))
    _section(parts, "Permitted child investigations and their construction", _text_or_values(state.get("child_options")))
    _section(parts, "Information requested from this parent", _text_or_values(state.get("requested_report_purpose")))
    requested = state.get("requested_form")
    needed = set()
    if isinstance(requested, Mapping):
        _section(parts, "This parent's requested typed return", render_schema_information(requested, title='Parent requested return')
            if profile else _schema(requested, "return"))
        needed = {node.get("x-source") for node in requested.get("properties", {}).values()}
    sources = state.get("available_report_facts", {})
    selected = {name: row for name, row in sources.items()
        if isinstance(row, Mapping) and (name.startswith("literature_") or name in needed)}
    if selected:
        _section(parts, "Available source-evidence return meanings", _table(("Source", "Meaning"),
            ((name, row.get("meaning", "")) for name, row in selected.items())))
        for name, row in selected.items():
            if not profile and isinstance(row.get("report_schema"), Mapping):
                _section(parts, "Declared typed projection for " + name,
                    _schema(row["report_schema"], "child_return." + name))
    _section(parts, "Return interpretation timing", state.get("report_lifecycle"))
    return "\n".join(parts)


def render_reference_evidence_parent_prompt(state, instructions, *, lookup_results=()):
    """Render this parent's full task and its own selected factual steering."""
    sections = selected_literature_task_sections(state, lookup_results)
    from .literature_rate_observation_prompt import grid_state_view
    from .literature_endpoint_signal_render import state_view as endpoint_state_view
    from .literature_endpoint_signal_render import sanitize_private
    lookup_results = sanitize_private(lookup_results, state.get('literature_endpoint_receipt_bindings', {}))
    from .literature_kinetic_summary_precision_render import state_view as summary_state_view, sanitize_private as summary_private
    lookup_results = summary_private(lookup_results, state.get('literature_summary_precision_receipt_bindings', {}))
    state = endpoint_state_view(grid_state_view(state_view(state), lookup_results), lookup_results)
    state = summary_state_view(state, lookup_results)
    from .literature_measurement_comparison_render import state_view as comparison_state_view, sanitize_private as comparison_private
    lookup_results = comparison_private(lookup_results, state.get('literature_measurement_comparison_receipt_bindings', {}))
    state = comparison_state_view(state, lookup_results)
    from .literature_concentration_window_render import state_view as window_state_view, sanitize_private as window_private
    lookup_results = window_private(lookup_results, state.get('literature_concentration_window_receipt_bindings', {}))
    state = window_state_view(state, lookup_results)
    from .literature_numerical_return_presentation import common_assessment_lookup
    from .literature_compiled_assay_render import is_common_row, rows_from_values
    if any(common_assessment_lookup(outcome) for outcome in lookup_results) or any(is_common_row(row) for row in rows_from_values(lookup_results)):
        state = {**state, 'literature_common_assessment_work': {'version': 'literature_common_assessment_task_v1'}}
    descriptor = _descriptor(state)
    # The shared mechanical renderer selects own outcomes, received records and
    # admitted forms. Do not seed it with a child's assignment or task/history.
    steering_fields = ("action_yields", "controller", "working_state", "last_local_outcome",
        "literature_completed_work", "literature_current_scoring_sheets", "completed_action_reports",
        "feedback", "current_report_update", "requested_form", "child_reports", "pending_work", "waiting_support", "current_report_basis_refs",
        "shared_information_context",
        "literature_ratio_source_return_meanings", "literature_controlled_response_return_bindings",
        "literature_gel_return_bindings", "literature_gel_return_records", "literature_rate_source_display",
        "literature_received_fact_display", "literature_rate_source_domain_display",
        "literature_rate_source_meaning_display", "literature_endpoint_receipt_bindings", "literature_summary_precision_receipt_bindings", "literature_measurement_comparison_receipt_bindings", "literature_concentration_window_receipt_bindings")
    steering_state = {name: state[name] for name in steering_fields if name in state}
    if state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE:
        return _requested_contract_task(_task(state, instructions, descriptor, selected_sections=sections), lookup_results) + '\n\n' + _steering(
            steering_state, [row for row in lookup_results if not is_contract_information(row)],
            evidence_axis=descriptor.get('evidence_axis'))
    return _task(state, instructions, descriptor, selected_sections=sections) + "\n\n" + _steering(
        steering_state, lookup_results, evidence_axis=descriptor.get('evidence_axis'))


__all__ = ["VERSION", "REFERENCE_PARENT_TASK", "render_reference_evidence_parent_prompt"]
