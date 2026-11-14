"""Original selected execution task presentation for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
from .decision_record_fields import _RECORD_TRACKING
from .recorded_operand_display import _execution_opaque_reference
from .decision_steering_display import _interval_result_presentation
from .decision_prompt_text import _pick
from .decision_schema_display import _registered_return_schema_view
from .decision_steering_display import _render_episode_steering
from .decision_schema_display import _schema
from .decision_prompt_text import _section
from .decision_prompt_text import _table
from .molecular_value_presentation import _values
from .decision_prompt_text import text_instructions


def is_selected_execution_context(context):
    task = context.get("selected_execution_task") if isinstance(context, Mapping) else None
    return (isinstance(task, Mapping) and task.get("version") == "selected_execution_task_v1"
        and isinstance(task.get("scientific_question"), str)
        and isinstance(task.get("selected_tool_info"), (list, tuple))
        and isinstance(task.get("requests"), (list, tuple)) and bool(task["requests"]))


_EXECUTION_PRESENTATION_TRACKING = _RECORD_TRACKING | frozenset({
    "$id", "argv", "environment", "cwd", "workspace", "directory", "path", "relative_path",
    "staged_relative_path", "python_executable", "implementation_files", "driver_module", "worker_module",
    "custody", "original_custody", "handoff_proof", "intent", "bundle", "worker", "capture",
    "context_before", "context_after", "assignment_sha256", "original_operation_key", "operation_ref",
    "receipt_key", "result_receipt_key", "started_at", "finished_at", "captured_at", "observed_at",
    "execution_id", "assignment_id", "operational_credit_binding", "native_protein_structure",
    "result_selector_schema", "qualified_files", "family_artifact_refs", "calculation", "calculation_id",
})
def _execution_presentation_values(value):
    """Keep supplied scientific values, without native custody or host coordinates."""
    if isinstance(value, Mapping):
        from gene_annotation_episode.episodic_workflow.root.library.bvbrc_application_value_presentation import select_application_execution_values
        application = select_application_execution_values(value)
        if application is not None:
            return application
        from ..execution_prompt import select_profile_api_execution_values
        api = select_profile_api_execution_values(value)
        if api is not None:
            return api
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import select_macs2_peak_execution_values
        macs2 = select_macs2_peak_execution_values(value)
        if macs2 is not None:
            return macs2
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import select_lumpy_execution_values
        lumpy = select_lumpy_execution_values(value)
        if lumpy is not None:
            return lumpy
        from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_presentation import select_genomic_overlap_execution_values
        overlap = select_genomic_overlap_execution_values(value)
        if overlap is not None:
            return overlap
        from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_presentation import select_chromatin_execution_values
        chromatin = select_chromatin_execution_values(value)
        if chromatin is not None:
            return chromatin
        from gene_annotation_episode.episodic_workflow.root.library.atac_differential_presentation import select_atac_execution_values
        atac = select_atac_execution_values(value)
        if atac is not None:
            return atac
        from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_presentation import select_expression_nmf_execution_values
        nmf = select_expression_nmf_execution_values(value)
        if nmf is not None:
            return nmf
        from gene_annotation_episode.episodic_workflow.root.library.native_profile_presentation import select_native_profile_execution_values
        profile = select_native_profile_execution_values(value)
        if profile is not None:
            return profile
        result = {}
        for key, child in value.items():
            if (key in _EXECUTION_PRESENTATION_TRACKING or key.endswith("_sha256")
                    or key.endswith("_digest") or key.endswith("_path") or key.endswith("_paths")):
                continue
            if (key in {"id", "ref", "handle"} or key.endswith("_ref")) and _execution_opaque_reference(child):
                continue
            if (key.endswith("_refs") or key == "references") and isinstance(child, (list, tuple)):
                child = [item for item in child if not _execution_opaque_reference(item)]
            if key == "body" and isinstance(child, Mapping):
                child = _pick(child, ("native_success", "capture_complete", "issues", "observation",
                    "observation_origin"))
            elif key == "publication" and isinstance(child, Mapping):
                child = _pick(child, ("facts", "delivery_complete"))
            result[key] = _execution_presentation_values(child)
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for child in value:
            result.append(_execution_presentation_values(child))
        return result
    return value


def _execution_schema_view(schema):
    """Remove only schema identity annotations; retain the declared constraints."""
    if isinstance(schema, Mapping):
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import macs2_peak_schema_view
        macs2 = macs2_peak_schema_view(schema)
        if macs2 is not None:
            return macs2
        return {key: _execution_schema_view(child) for key, child in schema.items() if key != "$id"}
    if isinstance(schema, (list, tuple)):
        return [_execution_schema_view(child) for child in schema]
    return schema


def _selected_execution_task(state, instructions):
    task = state["selected_execution_task"]
    parts = ["TASK"]
    _section(parts, "Scientific QUESTION", task["scientific_question"])
    _section(parts, "Assigned job", state.get("goal", {}).get("objective"))
    _section(parts, "Fixed scope", _values(state.get("scope", {})))
    _section(parts, "Parent constraints", _values(_execution_presentation_values(task.get("constraints", {}))))
    for tool in task["selected_tool_info"]:
        _section(parts, "Parent-selected tool guidance: " + tool["name"] + " (" + tool["resources"] + ")",
            tool["description"] + "\n\n" + tool["instructions"])
    for request in task["requests"]:
        _section(parts, "Selected work: " + str(request["resource_id"]),
            _values(_execution_presentation_values({key: request[key] for key in
                ("resource_id", "resource_kind", "endpoint", "constraints") if key in request})))
        _section(parts, "Configured resource", _values(_execution_presentation_values(request["resource"])))
        _section(parts, "Exact assigned scientific request",
            _values(_execution_presentation_values(request["job"])))
    if task.get("selector") is not None:
        _section(parts, "Original result selection", _values(_execution_presentation_values(task["selector"])))
    description = task.get("result_description")
    if isinstance(description, Mapping):
        selected = _pick(description, ("operation", "mode", "output_format", "status_meanings"))
        selected["extractors"] = [_pick(row, ("operation", "observation_basis", "fresh_native_observation",
            "scientific_result_acquisition", "completes_assignment", "calculation_basis",
            "calculator_parameters", "original_calculation_parameters", "original_sheet_and_baseline_preserved",
            "new_producer_observation", "return_fact_sources")) for row in description.get("extractors", ())]
        _section(parts, "Original result meanings", _values(_execution_presentation_values(selected)))
    _section(parts, "Execution method and decision rules", text_instructions(instructions))
    manuals = state.get("selected_launch_instructions") or {}
    for section in manuals.get("sections", ()):
        _section(parts, "Assigned software or resource instructions: " + section["entry_id"]
            + " / " + section["section_id"], section["text"])
    tools = state.get("tools", ())
    if tools:
        _section(parts, "Callable operations", _table(("Operation", "Meaning"),
            ((tool["name"], tool.get("description", "")) for tool in tools)))
        for tool in tools:
            if "instructions" in tool:
                _section(parts, "Supplied instructions for " + tool["name"], tool["instructions"])
            if "input_schema" in tool:
                _section(parts, "Operands for " + tool["name"],
                    _schema(_execution_schema_view(tool["input_schema"]), "arguments", named_definitions=True))
    _section(parts, "Information requested by the parent", state.get("requested_report_purpose"))
    form = state.get("requested_form")
    if form is not None:
        sources = state.get("available_report_facts", {})
        _section(parts, "Parent return form", _schema(_execution_schema_view(
            _registered_return_schema_view(form, sources)), "return"))
        used = {row.get("x-source") for row in form.get("properties", {}).values()}
        _section(parts, "Meaning of requested recorded facts", _table(("Source", "Meaning"),
            ((name, sources[name].get("meaning", "")) for name in sources if name in used)))
    _section(parts, "Return interpretation timing", state.get("report_lifecycle"))
    return "\n".join(parts)


def render_selected_execution_prompt(state, instructions, *, lookup_results=()):
    """Present the detached original execution TASK with current own STEERING."""
    if not is_selected_execution_context(state):
        raise ValueError("selected_execution_task_required")
    state, lookup_results, interval_sections = _interval_result_presentation(state, lookup_results)
    from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import select_macs2_peak_capture_presentation, render_macs2_peak_captures
    macs2 = select_macs2_peak_capture_presentation(state, lookup_results=lookup_results)
    state, lookup_results = macs2['context'], macs2['lookup_results']
    steering = _execution_presentation_values(_pick(state, ("action_yields", "controller", "current_credit",
        "completed_action_reports",
        "last_local_outcome", "feedback", "child_reports", "pending_work", "report_deliveries",
        "waiting_support", "resource_tool_estimates", "job_execution_options", "native_event_targets",
        "pending_child_delivery")))
    lookups = [_execution_presentation_values(value) for value in lookup_results]
    parts = [_selected_execution_task(state, instructions),
        _render_episode_steering(steering, lookups, interval_sections)]
    progress = {}
    if isinstance(state.get("execution_progress"), Mapping):
        progress["execution_progress"] = _pick(state["execution_progress"], ("execution_completed",))
    if isinstance(state.get("practical_progress"), Mapping):
        progress["practical_progress"] = _pick(state["practical_progress"],
            ("credit", "initial_credit", "operational_credit", "requirements", "satisfied_keys"))
    if "practical_completion" in state:
        progress["practical_completion"] = state["practical_completion"]
    if progress:
        _section(parts, "Current execution information", _values(_execution_presentation_values(progress)))
    if macs2['captures']:
        parts.append(render_macs2_peak_captures(macs2['captures']))
    return "\n\n".join(parts)


