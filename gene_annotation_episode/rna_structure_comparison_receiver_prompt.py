"""Preserve a receiving parent's task when selected RNA comparison facts arrive.

This boundary uses the supplied annotation or legacy scientific assignment. It
does not construct an RNA investigation, read records, or change a return form.
The provider owns selection and reconstruction of this receiving context.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit

from .rna_structure_comparison_prompt import render_rna_comparison_requested_return
from .scientific_process_prompt import (
    _pick, _record, _scalar, _schema, _section, _table, _values,
    render_episode_steering, text_instructions,
)


def _text(value):
    return _values(value) if isinstance(value, (Mapping, list, tuple)) else _scalar(value)


def _goal(parts, state):
    goal = state.get("goal")
    if not isinstance(goal, Mapping):
        if goal is not None:
            _section(parts, "Assigned work", _text(goal))
        return
    supplied = _pick(goal, ("objective", "task_context"))
    contract = goal.get("result_contract")
    same_form = contract is not None and contract == state.get("requested_form")
    schema = isinstance(contract, Mapping) and "type" in contract
    if "result_contract" in goal and not same_form and not schema:
        supplied["result_contract"] = contract
    if supplied:
        _section(parts, "Assigned work", _values(supplied))
    if same_form:
        _section(parts, "Assigned result contract", "The parent return form below is this goal's result contract.")
    elif schema:
        # A distinct goal schema can itself request RNA facts. Reuse the exact
        # requested-return meanings rather than expanding its source catalog.
        _section(parts, "Assigned result contract", render_rna_comparison_requested_return({
            "requested_form": contract,
            "available_report_facts": state.get("available_report_facts", {}),
        }))


def _guidance(parts, process):
    axis = process.get("evidence_axis", process.get("annotation"))
    if isinstance(axis, Mapping):
        title = "Supplied investigation guidance"
        if axis.get("name"):
            title += ": " + axis["name"]
        body = "\n\n".join(_text(axis[name]) for name in
            ("description", "investigation_instructions") if axis.get(name) is not None)
        if body:
            _section(parts, title, body)
        if axis.get("support") is not None:
            _section(parts, "Assigned scientific support and its operands", _values(axis["support"]))
    thought = process.get("thought_pattern", process.get("thought"))
    if isinstance(thought, Mapping):
        title = "Supplied reasoning guidance"
        if thought.get("name"):
            title += ": " + thought["name"]
        body = "\n\n".join(_text(thought[name]) for name in
            ("description", "use_when") if thought.get(name) is not None)
        if body:
            _section(parts, title, body)
        for field, label in (("live_alternatives", "Alternatives to distinguish"),
                ("decision_guidance", "How to choose and revise the investigation")):
            if thought.get(field):
                _section(parts, label, "\n".join("- " + item for item in thought[field]))
        if thought.get("outcome_contingencies"):
            _section(parts, "How outcomes affect the next choice", _table(
                ("If observed", "Then consider"), ((row["if_observed"], row["then_consider"])
                    for row in thought["outcome_contingencies"])))
        _section(parts, "Limits of this reasoning approach", thought.get("boundary"))
    for tool in process.get("child_tool_info", process.get("tools", ())):
        title = "Selected tool: " + tool["name"]
        if tool.get("resources") is not None:
            title += " (" + _scalar(tool["resources"]) + ")"
        body = "\n\n".join(_text(tool[name]) for name in
            ("description", "instructions") if tool.get(name) is not None)
        _section(parts, title, body)
        if "input_schema" in tool:
            _section(parts, "Selected tool operands for " + tool["name"],
                _schema(tool["input_schema"], "arguments"))
    routes = process.get("annotation_support_routes")
    if isinstance(routes, Mapping):
        # The older instructions explicitly describe these supplied meanings.
        # Their policy identity and implementation digests remain host data.
        selected = _pick(routes, ("status", "reason", "integration_arithmetic", "policy", "routes"))
        if selected:
            _section(parts, "Supplied annotation support mapping", _values(selected))


def _source_operands(working):
    """Copy only callable Source metadata from its declared inventory slot."""
    rows = []
    sources = working.get("sources", ())
    if not isinstance(sources, (list, tuple)):
        return rows
    for source in sources:
        if (not isinstance(source, Mapping) or source.get("record_type") != "source"
                or not isinstance(source.get("id"), str) or not source["id"]
                or not isinstance(source.get("provider"), str)):
            continue
        uri = source.get("uri")
        web_uri = None
        if isinstance(uri, str) and not any(character.isspace() or ord(character) < 32 for character in uri):
            try:
                parsed = urlsplit(uri)
                parsed.port  # Validate a supplied port without normalizing the URI.
                if (parsed.scheme.lower() in {"http", "https"} and parsed.hostname
                        and parsed.username is None and parsed.password is None):
                    web_uri = uri
            except ValueError:
                pass
        rows.append((source["id"], source["provider"], source.get("accession"), source.get("version"), web_uri))
    return rows


def _task(state, instructions):
    parts = ["TASK", "", text_instructions(instructions)]
    _goal(parts, state)
    if "scope" in state:
        _section(parts, "Fixed scope", _values(state["scope"]))
    constraints = _pick(state, ("constraints", "selected_constraints"))
    if constraints:
        _section(parts, "Caller constraints", _values(constraints))

    process = state.get("scientific_process", {})
    assignment = process.get("assignment", {})
    if "constraints" in assignment:
        _section(parts, "Parent constraints", _values(assignment["constraints"]))
    if "context" in assignment:
        _section(parts, "Parent-supplied context", _values(assignment["context"]))
    if assignment.get("evidence_refs"):
        _section(parts, "Parent-selected evidence operands", _values(assignment["evidence_refs"]))

    working = state.get("working_state", {})
    material = {name: [_record(row) for row in working[name]] for name in
        ("subjects", "materials", "collections", "material_links") if working.get(name)}
    material.update(_pick(working, ("target_binding", "read_library_access", "supplied_context_source_refs")))
    if material:
        _section(parts, "Supplied material and scoped access", _values(material))
    sources = _source_operands(working)
    if sources:
        _section(parts, "Callable supplied Sources", _table(
            ("Source operand", "Provider", "Accession", "Recorded version", "HTTP(S) resource URI"), sources))
    _guidance(parts, process)

    selected_manuals = state.get("selected_launch_instructions") or {}
    for section in selected_manuals.get("sections", ()):
        _section(parts, "Assigned software or resource instructions: " + section["entry_id"]
            + " / " + section["section_id"], section["text"])
    tools = state.get("tools", ())
    if tools:
        _section(parts, "Callable operations", _table(("Operation", "Meaning"),
            ((tool["name"], tool.get("description", "")) for tool in tools)))
        for tool in tools:
            if tool.get("instructions") is not None:
                title = "Operation guidance for " + tool["name"]
                if "resources" in tool:
                    title += " (resources: " + _scalar(tool["resources"]) + ")"
                _section(parts, title, _text(tool["instructions"]))
            if "input_schema" in tool:
                _section(parts, "Operands for " + tool["name"], _schema(tool["input_schema"], "arguments"))
    if "permitted_children" in process:
        _section(parts, "Permitted child roles", _values(process["permitted_children"]))
    if state.get("child_options") is not None:
        _section(parts, "Child construction and requested facts", _text(state["child_options"]))
    if state.get("job_episode_options") is not None:
        _section(parts, "Configured job child roles and requested facts", _text(state["job_episode_options"]))
    parts.extend(["", render_rna_comparison_requested_return(state)])
    if process.get("selection"):
        # Pinned option identities are actionable operands of the unchanged
        # child-assignment contract, rather than unused host provenance.
        _section(parts, "Callable selection operands for child assignment (copy exact values)",
            _values(process["selection"]))
    return "\n".join(parts)


def render_rna_comparison_receiver_prompt(
    state: Mapping, instructions: str, *, lookup_results: Sequence = ()
) -> str:
    """Repeat the supplied parent TASK and render only supplied decision facts.

    An empty service-supplied received group is permitted: the same general task
    can precede its first RNA return. Routing remains the provider's decision.
    """
    return _task(state, instructions) + "\n\n" + render_episode_steering(
        state, lookup_results=lookup_results)


__all__ = ["render_rna_comparison_receiver_prompt"]
