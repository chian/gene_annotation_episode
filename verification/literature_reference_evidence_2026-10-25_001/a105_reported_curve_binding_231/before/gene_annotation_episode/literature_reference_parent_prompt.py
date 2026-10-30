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
from .scientific_process_prompt import text_instructions
from .composition_information import CONTRACT_INFORMATION_PROFILE, is_contract_information
from .schema_information_text import render_schema_information
from .literature_numerical_return_presentation import state_view


VERSION = "reference_evidence_parent_v1"

REFERENCE_PARENT_TASK = """Evaluate what the assigned experimental sources establish about the reference molecule and its possible function. Keep the actual caller question, supplied material, scientific scope and constraints below as your job. A function can emerge from the evidence; an initial annotation or public searchable name is not required. Decide which uncertainty is useful to resolve next, choose among the permitted source operations and literature investigations, and revise your interpretation using actual outcomes.

Establish which organism, genotype, molecule, construct, preparation and experimental system each result concerns. Distinguish the source organism from an expression host, a tagged construct from a native molecule, and a reference preparation from the supplied annotation target. Preserve the actual measured entity, endpoint, units, normalization, comparison numerator and denominator, conditions, intended experimental change and controls. A shared name, source paper or equal number does not establish a common experiment or molecular identity.

Judge the bearing of the measured endpoint on the specific functional assertion. Molecular conversion, transport and binding experiments answer different questions from growth, survival or other perturbation/restoration phenotypes. A recovery-growth result is not an enzyme activity measurement. A band-signal ratio is not calibrated molar or active protein amount. A no-inhibitor reference is not a no-enzyme blank. Oxygen consumption does not itself identify product formation or a quantitative productive coupling ratio. Keep the source's observation separate from the authors' inference and from your interpretation.

Keep experimental comparability outside the deliberately tested difference separate from isolation of the measured effect. Ask which amounts or conditions could explain a comparison, whether molecules replace one another or coexist, and which contributors remain in a mixed readout. Similar conditions do not prove attribution. A complementary experiment can address a named weakness without becoming independent replication. Preserve contradictions and source-representation conflicts; measurements on different endpoints or conditions are not automatically inconsistent repeats.

When a narrower literature investigation is useful, define its actual question, source scope, constraints and requested typed information. Ask for the numerical components and experimental relationships needed for your next decision, including relevant uncertainty, controls, unavailable reasons and source identity. Use the declared return projections to construct a closed form; retain actual reference meanings and select only the needed components. Children own their iterative source search, reading and interpretation choices. Their permitted relationships are alternatives, not a required itinerary, reading quota or automatic sequence.

Integrate only information actually received through your own outcomes or requested admitted child forms. A globally stored source or a reference needed for validation is not delivered scientific knowledge. Read scoped evidence when needed. Preserve units, bounds, uncertainty definitions, experimental meaning and dependence when comparing results. Missing values remain unknown; nondetection is not exact zero. Do not interchange SD, SEM, confidence intervals or untyped error bars. Convert them only when the required statistical information and assumptions support the calculation. Do not count technical repetitions as independent experiments or repeated representations as new evidence. Models identify source meanings and supported operands; deterministic operations perform parsing, validation, unit conversion and arithmetic.

A numerical source-effect component evaluates its declared experiment and endpoint. It is not a probability of function, target annotation support or investigation-progress credit. Source findings may qualify or weaken a proposed function while still being useful information. Sequence/structural correspondence and later combination into annotation credit remain separate work. Do not invent target-transfer weights, reliability categories, missing controls, covariance or scientific progress. Do not manufacture target assessments merely to give source processing credit or hasten stopping.

Retain valid partial results and actionable source limitations. Your task remains this parent investigation after a child return; the admitted return is evidence for your next decision, not another task prompt. Use ordinary reasoning to integrate findings and update only your declared typed report when one is requested. Do not add a second model call to restate recorded facts or compose a report. Source navigation, bookkeeping and report construction add no scientific contribution by themselves. The configured controller owns continuation; there is no source-completion gate or fixed action count."""


def _descriptor(state):
    marker = state.get("literature_experimental_work") if isinstance(state, Mapping) else None
    descriptor = state.get("reference_evidence_parent") if isinstance(state, Mapping) else None
    if (not isinstance(marker, Mapping)
            or marker.get("version") != "literature_experimental_task_v1"
            or marker.get("aspect") != "reference_evidence_parent"
            or not isinstance(descriptor, Mapping) or descriptor.get("version") != VERSION):
        raise ValueError("reference_evidence_parent_context_required")
    references = descriptor.get("source_refs")
    if (not isinstance(references, (list, tuple)) or not references
            or any(not isinstance(reference, str) or not reference for reference in references)
            or len(set(references)) != len(references)):
        raise ValueError("reference_evidence_parent_source_assignment_required")
    return descriptor


def _text_or_values(value):
    return _values(value) if isinstance(value, (Mapping, list, tuple)) else value


def _task(state, instructions, descriptor):
    normalized = text_instructions(instructions)
    parts = ["TASK", "", REFERENCE_PARENT_TASK, "", SAVED_NUMERICAL_RETURN_TASK]
    if state.get("literature_completion_time_work", {}).get("version") == "literature_completion_time_task_v1":
        from .literature_completion_time_prompt import COMPLETION_TIME_TASK
        parts.extend(["", COMPLETION_TIME_TASK])
    if state.get("literature_active_site_work", {}).get("version") == "literature_active_site_task_v1":
        from .literature_active_site_prompt import ACTIVE_SITE_TASK
        parts.extend(["", ACTIVE_SITE_TASK])
    if state.get("literature_product_partition_work", {}).get("version") == "literature_product_partition_task_v1":
        from .literature_product_partition_prompt import PRODUCT_PARTITION_TASK
        parts.extend(["", PRODUCT_PARTITION_TASK])
    from .literature_product_coupling_render import task_relevant as coupling_task_relevant
    from .literature_product_coupling_prompt import PRODUCT_COUPLING_TASK
    if coupling_task_relevant(state) and PRODUCT_COUPLING_TASK not in normalized:
        parts.extend(["", PRODUCT_COUPLING_TASK])
    from .literature_measurement_validation_render import task_relevant as validation_task_relevant
    from .literature_measurement_validation_prompt import MEASUREMENT_VALIDATION_TASK
    if validation_task_relevant(state) and MEASUREMENT_VALIDATION_TASK not in normalized:
        parts.extend(["", MEASUREMENT_VALIDATION_TASK])
    from .literature_compiled_assay_render import common_task_relevant
    from .literature_compiled_assay_prompt import COMMON_ASSESSMENT_TASK
    if common_task_relevant(state) and COMMON_ASSESSMENT_TASK not in normalized:
        parts.extend(['', COMMON_ASSESSMENT_TASK])
    additional = normalized.replace(REFERENCE_PARENT_TASK, "").replace(SAVED_NUMERICAL_RETURN_TASK, "").strip()
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
    _section(parts, "Caller-selected source assignment", _values({"source_refs": descriptor["source_refs"]}))
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
    state = state_view(state)
    from .literature_numerical_return_presentation import common_assessment_lookup
    from .literature_compiled_assay_render import is_common_row, rows_from_values
    if any(common_assessment_lookup(outcome) for outcome in lookup_results) or any(is_common_row(row) for row in rows_from_values(lookup_results)):
        state = {**state, 'literature_common_assessment_work': {'version': 'literature_common_assessment_task_v1'}}
    descriptor = _descriptor(state)
    # The shared mechanical renderer selects own outcomes, received records and
    # admitted forms. Do not seed it with a child's assignment or task/history.
    steering_fields = ("action_yields", "controller", "working_state", "last_local_outcome",
        "feedback", "current_report_update", "child_reports", "pending_work", "current_report_basis_refs",
        "literature_ratio_source_return_meanings", "literature_controlled_response_return_bindings",
        "literature_gel_return_bindings", "literature_gel_return_records", "literature_rate_source_display",
        "literature_received_fact_display", "literature_rate_source_domain_display",
        "literature_rate_source_meaning_display")
    steering_state = {name: state[name] for name in steering_fields if name in state}
    if state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE:
        return _requested_contract_task(_task(state, instructions, descriptor), lookup_results) + '\n\n' + _steering(
            steering_state, [row for row in lookup_results if not is_contract_information(row)])
    return _task(state, instructions, descriptor) + "\n\n" + _steering(steering_state, lookup_results)


__all__ = ["VERSION", "REFERENCE_PARENT_TASK", "render_reference_evidence_parent_prompt"]
