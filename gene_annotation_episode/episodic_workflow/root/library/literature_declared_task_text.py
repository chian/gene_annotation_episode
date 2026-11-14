"""Original supplied-state literature declared task text; no runtime ownership selection."""
import gene_annotation_episode.episodic_workflow.root.library.literature_numerical_return_presentation as _numerical_return
from collections.abc import Mapping
from .literature_task_selection import A105_ASSAY_SELECTION_TASK, selected_literature_task_sections
from gene_annotation_episode.episodic_workflow.root.library.literature_a108_prompt import A108_CONTEXT_TASK, A108_READING_TASK
from gene_annotation_episode.episodic_workflow.root.library.decision_outcome_presentation import _band
from gene_annotation_episode.episodic_workflow.root.library.decision_schema_display import _schema
from gene_annotation_episode.episodic_workflow.root.library.decision_prompt_text import text_instructions
from gene_annotation_episode.episodic_workflow.root.composition_information import (CONTRACT_INFORMATION_PROFILE, CONTRACT_ARGUMENT_TRANSPORT,
    is_contract_information, requested_contract_information)
from gene_annotation_episode.schema_information_text import render_schema_information
from .literature_text_values import _pick, _safe, _scalar, _section, _table, _values

CONTRACT_INFORMATION_TASK = """Choose among the listed operations for the assigned evidence question. Request an operation's full argument contract through request_context, composition_information, episode.operation_contract when useful. Select the actual operation name. All listed operations remain available. The lookup supplies instructions within this same decision and creates no completed action or observation. You may invoke an operation directly; the host validates its original complete argument contract.

For a permitted child's declared recorded-fact return type, request episode.return_contract with its role and source. Copy the exact declared projection into your chosen top-level field either literally or by a field containing only $ref with value episode-fact:<source>. The host expands that explicit reference to the original complete closed type before commissioning. Choose your own field names and requested components. Keep bound facts out of initial_report_json and use separate constrained interpretation fields as already instructed."""

SAVED_NUMERICAL_RETURN_TASK = """When requesting saved numerical components listed as available recorded return sources, choose a top-level return field whose declaration contains only $ref with the exact value episode-fact:<source>, using that source's declared name. The host expands this explicitly selected declaration to the original complete closed type before commissioning; the numerical sheet itself remains with the host. Choose the needed components through the child assignment. Keep bound fact fields out of initial_report_json; the runtime fills them from saved results. Use separate constrained fields for interpretations and unresolved questions, preserving the parent's requested meanings. Do not ask the child to rewrite saved numerical cells as model-authored report values."""


EXPERIMENTAL_TASK = """Evaluate what the assigned experimental evidence establishes about the reference molecule and the assigned functional or structural question. The assigned work and source selection below define the actual experiment or information question; a public searchable target name or an initial target annotation is not required.

Establish the actual organism, genotype, assayed molecule or construct, preparation, experimental system, reference and test arms, conditions, intended changed variable and controls before interpreting the comparison. Determine whether molecules replace one another or coexist. Keep the deliberately tested difference separate from other condition differences. Identify the measured endpoint, units, normalization, comparison denominator, uncertainty type and magnitude, repetition basis, and exact source locations.

Distinguish a preparation signal from an effect isolated to the molecule. In particular, a no-inhibitor reference is not a no-enzyme blank, and oxygen consumption is not automatically identified product formation. Ask what product identification, blank, contaminant, calibration or coupling experiment actually establishes; retain limitations when those measurements are absent. A complementary endpoint can address a named weakness without becoming independent replication. Compare the measured endpoint with the specific functional assertion rather than accepting the paper's broad conclusion as a measured result.

Select ordinary searches, source reads, neighboring context, tables, figures or the permitted narrower literature investigations when they can resolve this question. Revise the search or reading approach using actual outcomes. The available child relationships are alternatives, not a mandatory sequence, reading quota or requirement to inspect every page. Supplied source selectors are operands for your decisions, not automatically executed instructions.

For a single reported measurement, preserve its quantity role and analyte without inventing comparison arms. An apparent Km is a kinetic parameter, not an activity rate or a binding affinity. Read literal specific activity or analyte-bound Km from a selected original passage when that syntax is available; keep untyped plus-minus spread unspecified. A subject name appearing in a paragraph does not itself establish which molecule produced a measured effect. Inspect assay conditions and attribution separately.

For a source-rate comparison, identify exact reported operands and their experimental relationships for the requested numerical cells. Preserve the source's units and printed limits. Do not invent an unknown denominator, reaction volume, calibration, control value or product attribution. Distinguish SD, SEM, confidence intervals, detection limits and mathematical bounds. Three measurements do not by themselves establish three independent biological preparations or independence between arms. Select a statistical observation model only when supported; otherwise preserve the unknown model or dependence and return usable partial cells. Nondetection is not an observed zero, and an unavailable score is not a score of zero.

Interpret source meaning and nominate supported operands; leave parsing, validation, unit conversion and arithmetic to the deterministic operations. Repeated representations of one experiment do not add independent evidence. Keep contradictory results and qualifications. Do not invent an overall reliability category, target-transfer weight or annotation probability. Sequence or structural target correspondence and combined annotation credit are separate work.

Return only the parent's declared typed information with the actual subject, conditions, endpoint, uncertainty and necessary unavailable reasons. Retain full structured evidence for scoped later access; do not restate recorded facts with another model call. Source acquisition, bookkeeping and report construction do not manufacture scientific progress. Each selected own action has its ordinary accounting, and the configured controller owns continuation."""


def _task(state, instructions, *, selected_sections=None):
    normalized = text_instructions(instructions)
    # The episode's scientific role leads; shared loop instructions follow it.
    is_a108 = state.get('literature_experimental_work', {}).get('evidence_axis') == 'A108'
    axis_task = A108_CONTEXT_TASK if is_a108 else A105_ASSAY_SELECTION_TASK
    reading_task = A108_READING_TASK if is_a108 else EXPERIMENTAL_TASK
    parts = ["TASK", "", axis_task, "", reading_task]
    additional = normalized.replace(axis_task, '').replace(reading_task, '').strip()
    if additional:
        parts.extend(['', additional])
    if SAVED_NUMERICAL_RETURN_TASK not in normalized:
        parts.extend(["", SAVED_NUMERICAL_RETURN_TASK])
    sections = selected_literature_task_sections(state) if selected_sections is None else selected_sections
    for aspect, task in sections:
        if task not in normalized:
            _section(parts, "Selected scientific instructions: " + aspect.removeprefix('literature_').removesuffix('_cells').replace('_', ' '), task)
    profile = state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE
    if profile:
        parts.extend(['', CONTRACT_INFORMATION_TASK])
    goal = state.get("goal", {})
    _section(parts, "Assigned organism-context question" if is_a108 else "Assigned experimental question", _values(_pick(goal,
        ("objective", "task_context") if profile else ("objective", "task_context", "result_contract")))
        if isinstance(goal, Mapping) else _scalar(goal))
    if (profile and isinstance(goal, Mapping) and goal.get('result_contract') is not None
            and goal['result_contract'] != state.get('requested_form')):
        _section(parts, 'Assigned result contract', render_schema_information(goal['result_contract'], title='Assigned result contract'))
    _section(parts, "Assigned scope", _values(state.get("scope", {})))
    assignment = _pick(state.get("literature_assignment", {}), (
        "requested_assay_grading_components", "requested_a105_aggregation_components",
        "requested_a108_grading_components", "requested_a108_aggregation_components",
        "requested_concentration_window_components", "requested_measurement_comparison_components", "requested_kinetic_summary_precision_components",
        "question_context_refs", "source_refs", "prior_search_refs", "search_result_refs",
        "source_ref", "representation", "artifact_ref", "page", "selection", "requested_product_coupling_components", "requested_measurement_validation_components", "requested_calibration_recovery_components", "requested_rate_observation_components", "requested_rate_grid_components", "requested_rate_replicate_components",
        "requested_ion_discrimination_components", "requested_channel_components", "requested_compiled_assay_components", "requested_compiled_assay_components_v2", "requested_compiled_assay_components_v3", "requested_product_partition_components", "requested_completion_time_components", "requested_active_site_components", "requested_rate_components", "requested_quantity_components", "requested_assay_components", "requested_ratio_components", "requested_ratio_source_components", "requested_binding_components", "requested_binding_model_components", "requested_transport_components", "requested_perturbation_components", "requested_perturbation_summary_components", "requested_structure_components", "requested_reaction_components", "requested_reaction_native_positions", "requested_figure_components", "requested_endpoint_signal_components", "requested_partner_components", "requested_amount_components", "requested_optical_components", "requested_kinetic_components", "requested_kinetic_model_components", "requested_binding_interaction_components", "requested_binding_interaction_model_components", "requested_controlled_response_components", "requested_controlled_response_views", "requested_controlled_response_component_keys", "requested_gel_components", "requested_gel_views", "requested_gel_component_keys", "constraints", "context"))
    # Version labels identify host assignment schemas, not source science.
    if isinstance(assignment.get("page"), Mapping):
        assignment["page"] = {key: value for key, value in assignment["page"].items() if key != "version"}
    _section(parts, "Parent assignment and selected source operands", _values(assignment))
    custody = [_pick(row, ("source_ref", "artifact_ref", "text_ref", "stdout_ref", "stderr_ref", "version"))
               for row in state.get("literature_source_custody", ())]
    if custody:
        _section(parts, "Representations available for selected sources", _values(custody))
    working = state.get("working_state", {})
    material = {name: [_safe(row) for row in working[name]]
                for name in ("subjects", "materials", "material_links") if working.get(name)}
    material.update(_pick(working, ("target_binding", "read_library_access", "supplied_context_source_refs")))
    if material:
        _section(parts, "Supplied material and scoped access", _values(material))
    tools = state.get("tools", ())
    if tools:
        _section(parts, "Available selected operations", _table(("Operation", "Meaning"),
            ((row["name"], row.get("description", "")) for row in tools)))
        for tool in tools:
            if "input_schema" in tool and not (profile and tool.get('argument_transport') == CONTRACT_ARGUMENT_TRANSPORT):
                _section(parts, "Operands for " + tool["name"], _schema(tool["input_schema"], "arguments"))
    _section(parts, "Permitted narrower investigations", state.get("child_options"))
    _section(parts, "Information requested by the parent", state.get("requested_report_purpose"))
    form = state.get("requested_form")
    if isinstance(form, Mapping):
        _section(parts, "Parent's typed return meanings", render_schema_information(form, title='Parent requested return')
            if profile else _schema(form, "return"))
        needed = {node.get("x-source") for node in form.get("properties", {}).values()}
        sources = state.get("available_report_facts", {})
        _section(parts, "Requested recorded facts", _table(("Source", "Meaning"),
            ((name, row.get("meaning", "")) for name, row in sources.items() if name in needed)))
    _section(parts, "Return interpretation timing", state.get("report_lifecycle"))
    return "\n".join(parts)


def _requested_contract_task(task, lookup_results):
    """Render only explicit contract meaning/text, keeping host payload out."""
    parts = [task]
    selected = requested_contract_information([{'lookup_result': row} for row in lookup_results])
    for outcome in selected:
        result = outcome['result']
        name = (result['operation'] if 'operation' in result else result['source'] + ' for ' + result['role'])
        _section(parts, 'Requested operation/return information: ' + name, result['meaning'])
        compact = _numerical_return.requested_return_text(result)
        _section(parts, 'Requested recorded return declaration' if compact is not None else 'Complete requested contract',
            result['text'] if compact is None else compact)
    return '\n'.join(parts)



