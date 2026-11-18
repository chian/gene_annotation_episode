"""Private A103 supplied gene-context task and evidence presentation."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import json
from .episode_work_report import render_completed_action_reports
from .decision_context import INSTRUCTIONS, TEXT_INSTRUCTIONS
from .alignment_result_presentation import alignment_report_presentation
from .schema_information_text import render_schema_information, schema_fingerprint

INSTRUCTION_STATUS = "published_investigation_instructions"

def is_published_scientific_context(context):
    process = context.get("gene_context_evidence") if isinstance(context, Mapping) else None
    axis = process.get("evidence_axis") if isinstance(process, Mapping) else None
    return isinstance(axis, Mapping) and axis.get("instruction_status") == INSTRUCTION_STATUS


def text_instructions(instructions):
    """Replace only the existing exchange protocol's JSON-reading directions."""
    return instructions.replace(INSTRUCTIONS, TEXT_INSTRUCTIONS).replace(
        "After its decision_lookup_result arrives", "After the requested information arrives")


def _scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _cell(value):
    return _scalar(value).replace("|", "\\|").replace("\n", "<br>")


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "None supplied."
    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)])


def _rows(value, path=""):
    """Exact finite values, with paths retaining arbitrary caller field names."""
    if isinstance(value, Mapping):
        if not value:
            yield path or "value", "empty object"
        for name, child in value.items():
            yield from _rows(child, f"{path}.{name}" if path else name)
    elif isinstance(value, (list, tuple)):
        if not value:
            yield path or "value", "empty array"
        for index, child in enumerate(value):
            yield from _rows(child, f"{path}[{index}]")
    else:
        yield path or "value", _scalar(value)


def _literal(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _values(value):
    return _table(("Field", "Supplied value"), _rows(value))


def _section(parts, title, body):
    if body is not None:
        parts.extend(["", title, "", body])


def _pick(value, names):
    return {name: value[name] for name in names if name in value}


def _schema_rows(schema, path="return", presence="required"):
    """Explain actual declared fields without converting contracts to prose guesses.

    Unusual JSON-schema keywords remain explicit constraint rows; the separate
    output schema is still the authoritative response contract. No constraints
    are inferred or weakened for presentation.
    """
    if isinstance(schema, bool):
        yield path, presence, "any value" if schema else "no permitted value", ""
        return
    kind = schema.get("type", "declared value")
    if isinstance(kind, list):
        kind = " or ".join(kind)
    meaning = schema.get("description", "")
    if "x-source" in schema:
        meaning += ("; " if meaning else "") + "recorded fact from " + schema["x-source"]
    if "format" in schema:
        kind += "; " + schema["format"]
    if schema.get("x-reference-namespace") is not None:
        kind += " to " + schema["x-reference-namespace"]
    yield path, presence, kind, meaning
    special = {"type", "description", "properties", "required", "items", "anyOf", "oneOf",
        "allOf", "if", "then", "else", "not", "$defs", "definitions", "title", "$schema", "$id",
        "format", "x-source", "x-reference-namespace"}
    for name, value in schema.items():
        if name not in special:
            for field, literal in _rows(value, name):
                yield path, "constraint", field, literal
    for name, child in schema.get("properties", {}).items():
        yield from _schema_rows(child, path + "." + name,
            "required" if name in schema.get("required", ()) else "optional")
    if "items" in schema:
        yield from _schema_rows(schema["items"], path + "[]", "each item")
    for operator in ("anyOf", "oneOf", "allOf"):
        for index, branch in enumerate(schema.get(operator, ())):
            yield from _schema_rows(branch, f"{path} ({operator} {index + 1})", operator)
    for operator in ("if", "then", "else", "not"):
        if operator in schema:
            yield from _schema_rows(schema[operator], f"{path} ({operator})", operator)
    for field in ("$defs", "definitions"):
        for name, child in schema.get(field, {}).items():
            yield from _schema_rows(child, field + "/" + name, "definition")


def _schema(schema, path, *, named_definitions=False):
    if named_definitions:
        return render_schema_information(schema, title=path)
    return _table(("Field", "Presence", "Type or constraint", "Meaning or value"),
        _schema_rows(schema, path))


def _registered_return_schema_view(form, sources):
    """Project only exact supplied registered arrays whose values the host fills.

    The complete original schema remains the host contract. Unmatched schemas,
    caller-composed fields and constraints outside the registered item tree keep
    their complete presentation; source names alone never authorize projection.
    """
    shown = deepcopy(form)
    if not isinstance(shown, Mapping) or not isinstance(sources, Mapping):
        return shown
    for name, node in shown.get("properties", {}).items():
        if not isinstance(node, Mapping) or node.get("type") != "array":
            continue
        source = node.get("x-source")
        registered = sources.get(source) if isinstance(source, str) else None
        if not isinstance(registered, Mapping) or "report_schema" not in registered:
            continue
        if schema_fingerprint(node) != schema_fingerprint(registered["report_schema"]):
            continue
        shallow = {key: value for key, value in node.items() if key != "items"}
        meanings = [node.get("description", ""), "Automatically supplied recorded values.",
            registered.get("meaning", "")]
        shallow["description"] = " ".join(value for value in meanings if value)
        shown["properties"][name] = shallow
    return shown


_RECORD_TRACKING = frozenset({"origin", "record_type", "operation_key", "run_id",
    "episode_id", "problem_ref", "sha256", "digest", "created_at", "updated_at",
    "parse_key", "parser_version", "metadata_preview_characters", "auxiliary_artifact_refs"})


def _record(record):
    if not isinstance(record, Mapping):
        return record
    return {key: value for key, value in record.items() if key not in _RECORD_TRACKING}


def _task(state, instructions):
    process = state["gene_context_evidence"]
    assignment = process.get("assignment", {})
    goal = state.get("goal", {})
    parts = ["TASK", "", text_instructions(instructions)]
    assigned_goal = _pick(goal, ("objective", "task_context")) if isinstance(goal, Mapping) else goal
    _section(parts, "Assigned work", _values(assigned_goal) if isinstance(goal, Mapping) else _scalar(goal))
    if isinstance(goal, Mapping) and "result_contract" in goal:
        contract, form = goal["result_contract"], state.get("requested_form")
        # An identical return contract is displayed once in Parent return form.
        # A distinct supplied goal contract retains its complete separate view.
        if form is None or schema_fingerprint(contract) != schema_fingerprint(form):
            _section(parts, "Assigned result contract", _schema(_registered_return_schema_view(
                contract, state.get("available_report_facts", {})), "result_contract", named_definitions=True))
    _section(parts, "Fixed scope", _values(state.get("scope", {})))
    _section(parts, "Parent constraints", _values(assignment.get("constraints", {})))
    _section(parts, "Parent-supplied context", _values(assignment.get("context", {})))
    if assignment.get("evidence_refs"):
        _section(parts, "Parent-selected evidence operands", _values(assignment["evidence_refs"]))

    working = state.get("working_state", {})
    material = {name: [_record(row) for row in working[name]] for name in
        ("subjects", "materials", "collections", "material_links") if working.get(name)}
    material.update(_pick(working, ("target_binding", "read_library_access", "supplied_context_source_refs")))
    if material:
        _section(parts, "Supplied material and scoped access", _values(material))

    selected_sources = set(assignment.get("evidence_refs", ())) | set(
        working.get("supplied_context_source_refs", ()))
    source_operands = [{"source_ref": row["id"], **_pick(row,
        ("origin", "provider", "accession", "version", "uri"))}
        for row in working.get("sources", ()) if row.get("id") in selected_sources]
    if source_operands:
        _section(parts, "Selected source operands (metadata only)",
            "These are received source identities and provenance for navigation. "
            "Read the actual contents to establish what each source supports.\n\n"
            + _values(source_operands))

    axis = process["evidence_axis"]
    _section(parts, "Investigate the supplied target: " + axis.get("name", ""),
        axis["investigation_instructions"])
    thought = process.get("thought_pattern", {})
    _section(parts, "Reason about the evidence: " + thought.get("name", ""),
        "\n\n".join(_scalar(thought[name]) for name in ("description", "use_when") if name in thought))
    for field, label in (("live_alternatives", "Alternatives to distinguish"),
            ("decision_guidance", "How to choose and revise the investigation")):
        if thought.get(field):
            _section(parts, label, "\n".join("- " + item for item in thought[field]))
    if thought.get("outcome_contingencies"):
        _section(parts, "How outcomes affect the next choice", _table(
            ("If observed", "Then consider"), ((row["if_observed"], row["then_consider"])
                for row in thought["outcome_contingencies"])))
    _section(parts, "Limits of this reasoning approach", thought.get("boundary"))

    for tool in process.get("child_tool_info", ()):
        _section(parts, "Selected tool: " + tool["name"] + " (" + tool["resources"] + ")",
            tool["description"] + "\n\n" + tool["instructions"])
    selected_manuals = state.get("selected_launch_instructions") or {}
    for section in selected_manuals.get("sections", ()):
        _section(parts, "Assigned software or resource instructions: " + section["entry_id"]
            + " / " + section["section_id"], section["text"])
    tools = state.get("tools", ())
    if tools:
        _section(parts, "Callable operations", _table(("Operation", "Meaning"),
            ((tool["name"], tool.get("description", "")) for tool in tools)))
        for tool in tools:
            if "input_schema" in tool:
                _section(parts, "Operands for " + tool["name"],
                    _schema(tool["input_schema"], "arguments", named_definitions=True))
    _section(parts, "Permitted child roles", _values(process.get("permitted_children", [])))
    _section(parts, "Child construction and requested facts", state.get("child_options"))
    _section(parts, "Evidence through child returns",
        "Choose each child's return facts to carry the evidence needed for your question. "
        "committed_record_refs carries the acquired scientific record references; select the provider's "
        "coverage/completeness facts when interpreting acquired rows or an empty result. "
        "A job handle, usable handoff or null failure field alone does not return the search data. "
        "Keep a completed empty acquisition distinct from partial or unavailable acquisition, and "
        "keep those acquisition facts separate from evidence for a biological function.")
    if state.get('contract_information_profile') == 'operation_contract_information_v1':
        _section(parts, "Discover and select exact return contracts",
            "Within this pending decision, request_context with view=composition_information, "
            "operation=episode.return_contract and arguments containing the permitted child's role "
            "and source returns its exact frozen fact type and meaning. In your chosen closed child "
            "form, a top-level field may contain only $ref with value episode-fact:<source>. "
            "For example, records can reference episode-fact:committed_record_refs. "
            "The host expands your explicit selection to its original type and fills recorded facts; "
            "leave those fact fields out of initial_report_json. Choose the relevant sources and "
            "return their actual saved grading results, numerical status, qualifications and missing inputs. "
            "Reporting does not require another supported/contradicted, function, path or scope verdict: "
            "use the grading sheet's existing criteria and status, without inventing a score threshold "
            "or asking a child to judge the same result again. Contract lookup creates no evidence, "
            "child, completed action or credit.")
    _section(parts, "Information requested by the parent", state.get("requested_report_purpose"))
    if state.get("requested_form") is not None:
        form = state["requested_form"]
        sources = state.get("available_report_facts", {})
        _section(parts, "Parent return form", _schema(_registered_return_schema_view(form, sources), "return"))
        used = {row.get("x-source") for row in form.get("properties", {}).values()}
        _section(parts, "Meaning of requested recorded facts", _table(("Source", "Meaning"),
            ((name, sources[name].get("meaning", "")) for name in sources if name in used)))
    _section(parts, "Return interpretation timing", state.get("report_lifecycle"))

    # These are the exact values required by a separately chosen child's typed
    # assignment, not scientific evidence or narrated library provenance.
    if process.get("selection"):
        _section(parts, "Callable selection operands for child assignment (copy exact values)",
            _values(process["selection"]))
    return "\n".join(parts)


def _band(band):
    if not isinstance(band, Mapping):
        return "unavailable", "unavailable"
    code = band.get("status_code")
    if code not in (None, 0):
        status = {-1: "insufficient completed actions", -2: "unidentifiable"}.get(code,
            "unavailable (status " + str(code) + ")")
        return "unavailable", status
    if "value" not in band:
        return "unavailable", "unavailable"
    uncertainty = "lower=" + _scalar(band.get("lower")) + "; upper=" + _scalar(band.get("upper"))
    if "uncertainty_code" in band:
        uncertainty += "; " + {0: "exact", 1: "Chebyshev bound", 2: "approximate Laplace model band"}.get(
            band["uncertainty_code"], "unavailable uncertainty")
    if "alpha" in band:
        uncertainty += "; alpha=" + _scalar(band["alpha"])
    return _scalar(band["value"]), uncertainty


def _references(value):
    if isinstance(value, Mapping):
        for key, child in value.items():
            if (key in {"id", "ref"} or key.endswith("_ref")) and isinstance(child, str):
                yield child
            elif (key == "dependencies" or key.endswith("_refs")) and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _received_records(state):
    """Only current interpretations and records explicitly linked to this turn.

    Do not turn a scoped source inventory into received source content. No Store
    reads are performed; unresolved references remain operands for a later read.
    """
    working = state.get("working_state", {})
    # A Source is a storage/provenance envelope, not the acquired source's
    # scientific content. Do not expand received references into metadata here.
    # Explicit source operands remain in supplied material and action outcomes.
    fields = ("features", "products", "terms", "references", "contexts", "observations",
        "hypotheses", "assessments", "annotations", "interpretation_accounts")
    records = {row["id"]: row for field in fields for row in working.get(field, ())
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)}
    revision_status = {row["record_ref"]: row["is_current_revision"]
        for row in working.get("received_revision_status", ())}
    current = [row["id"] for field in ("annotations", "interpretation_accounts")
        for row in working.get(field, ()) if revision_status.get(row["id"], True)]
    selected = list(dict.fromkeys([*current,
        *state.get("gene_context_evidence", {}).get("assignment", {}).get("evidence_refs", ()),
        *state.get("current_report_basis_refs", ()),
        *_references(state.get("current_report_update", {})),
        *_references(state.get("last_local_outcome", {})),
        *_references(state.get("child_reports", []))]))
    found = {}
    for reference in selected:
        if reference in found or reference not in records:
            continue
        row = records[reference]
        found[reference] = _record(row)
        selected.extend(ref for ref in _references(row) if ref not in found)
    return list(found.values())


def _feedback(value):
    """Keep actionable feedback without its private host diagnostic address."""
    if not isinstance(value, Mapping):
        return value
    return {key: child for key, child in value.items() if key != "diagnostic_ref"}


def _outcome(value):
    if not isinstance(value, Mapping):
        return value
    # Native result and feedback values are exact; operation receipts and full
    # estimator/tracking envelopes are not presentation. Revision preparation
    # is the exception: its origin is an operand required to commission it.
    shown = _pick(value, ("status", "record_refs", "changed_record_refs", "result", "feedback",
        "error_code", "errors", "conflicts", "notices", "aliases",
        "revision_origin", "automatic_preview", "visual_inputs", "child_completion"))
    if "feedback" in shown:
        shown["feedback"] = _feedback(shown["feedback"])
    proposal = shown.get("result")
    if isinstance(proposal, Mapping) and proposal.get("version") == "gene_context_evidence_child_selection_v1":
        from .gene_context_evidence_records import (
            SELECTION_VERSION, selector_selection, validate_child_selection, validate_revision_origin)
        from .tool_information import parent_view
        try:
            prepared = validate_child_selection(proposal)
            validate_revision_origin(shown.get("revision_origin"))
        except (ValueError, TypeError):
            return shown
        selected = prepared["selection"]
        if selected["version"] == SELECTION_VERSION:
            # The existing child-assignment interface accepts exact selectors
            # and restores/authenticates the original pinned tool information.
            # Full child instructions remain in the saved preparation, rather
            # than being copied into this parent's latest-outcome table.
            shown["result"] = {**prepared, "selection": selector_selection(selected)}
            shown["prepared_child_tools"] = parent_view(selected["child_tool_info"])
            shown["preparation_use"] = (
                "Commission a separate gene_context_evidence child with result.selection and revision_origin. "
                "The host restores the complete pinned tool descriptions and instructions and authenticates "
                "them against the original preparation. This preparation does not change the current episode.")
    return shown


def _lookup(result):
    """Render only the explicit reply, never the recorded exchange transcript."""
    if not isinstance(result, Mapping):
        return _values(result)
    if result.get("view") == "own_attempts":
        parts = [_table(("Attempt operand", "Category", "Status", "Completed gain"),
            ((row["decision_index"], row.get("category"), row["status"], row.get("completed_gain"))
                for row in result.get("records", ())))]
        for row in result.get("records", ()):
            data = {"inputs": _bounded_inputs(row.get("inputs", {}))}
            publications = row.get("published_references", {})
            data["published_references"] = _pick(publications, ("values", "total", "included", "complete"))
            if not row.get("input_fields", {}).get("complete", True):
                data["more_input_query"] = row["input_fields"].get("detail_query")
            _section(parts, "Attempt " + str(row["decision_index"]), _values(data))
        _section(parts, "Lookup page", _values(_pick(result,
            ("total", "offset", "returned_count", "next_query", "unavailable_reasons"))))
        return "\n".join(parts)
    if result.get("view") == "own_attempt_detail":
        return _values(_bounded_inputs(_pick(result, ("decision_index", "pointer", "slice_unit",
            "offset", "total", "included", "values", "has_more", "next_query"))))
    content = result.get("result", result)
    if isinstance(content, Mapping) and content.get('information_kind') in (
            'operation_contract_information_v1', 'return_contract_information_v1'):
        parts = [_scalar(content.get('meaning', ''))]
        if content.get('information_kind') == 'return_contract_information_v1':
            parts.append('Child role: '+_scalar(content['role'])+'; fact source: '+_scalar(content['source']))
            parts.append('Explicit form reference: episode-fact:'+_scalar(content['source']))
        parts.append(_scalar(content['text']))
        return '\n\n'.join(parts)
    if isinstance(content, Mapping) and "text" in content:
        parts = [_scalar(content["text"])]
        page = _pick(content, ("entry_id", "section_id", "coordinate_unit", "offset", "returned_lines",
            "total_lines", "next_query"))
        if page:
            _section(parts, "Selected instruction window", _values(page))
        return "\n".join(parts)
    # Composition lookups have an ordinary outcome envelope. Library-specific
    # projections remove the instruction provenance while retaining selectable
    # option operands; no evidence records are fetched to decorate this reply.
    return _values(_information(_outcome(result) if "status" in result else result))


def _bounded_inputs(value):
    if isinstance(value, Mapping):
        if value.get("representation") == "bounded_selected_input_v1":
            return {"value_type": value["value_type"], **_pick(value,
                ("total", "included", "complete", "detail_query")),
                **({"values": _bounded_inputs(value["values"])} if "values" in value else {})}
        return {key: _bounded_inputs(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_bounded_inputs(child) for child in value]
    return value


def _information(value):
    if isinstance(value, Mapping):
        # P entries retain their source rows in the immutable library. They are
        # instruction provenance, not target evidence in a lookup continuation.
        if value.get("slot") == "thought_pattern":
            return {key: _information(child) for key, child in value.items() if key != "evidence"}
        if "option_ref" in value and "entry" in value:
            return {"option_ref": value["option_ref"], "entry": _information(value["entry"])}
        if "entries" in value and "library" in value:
            return {key: _information(child) for key, child in value.items() if key != "library"}
        if value.get("content_role") in {"tool_and_resource_instructions_not_scientific_evidence",
                "launch_instructions_not_inventory_or_scientific_evidence"}:
            return {key: _information(child) for key, child in value.items() if key not in
                {"version", "library_id", "entry_count", "content_role", "section_sha256"}}
        return {key: _information(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_information(child) for child in value]
    return value


def _progress(row):
    """Current already-received progress, retaining measured facts and read operands."""
    result = _pick(row, ("target_handle", "observed_at", "result_available", "committed_record_refs"))
    status = row.get("execution_status", {})
    result["execution_status"] = _pick(status, ("handle", "observed_at", "lifecycle_state", "liveness",
        "result_available", "return_available", "failure", "resource_kind"))
    if isinstance(status.get("native"), Mapping):
        result["native_status"] = _pick(status["native"], ("state", "outcome", "returncode", "failure_code",
            "elapsed_seconds", "duration_measure", "measurements", "outputs"))
    result["measurements"] = row.get("measurements", [])
    result["log_windows"] = [_pick(window, ("source_ref", "artifact_ref", "start_byte", "end_byte",
        "observed_at")) for window in row.get("log_windows", ())]
    result["dependencies"] = [_pick(child, ("handle", "kind", "observed_at", "state"))
        for child in row.get("dependencies", ())]
    return result


def _steering(state, lookup_results):
    parts = ["STEERING"]
    if 'completed_action_reports' in state:
        parts.extend(['', render_completed_action_reports(state['completed_action_reports'])])
    if state.get('pending_child_delivery') is not None:
        _section(parts, 'Complete the original child return', _values(state['pending_child_delivery']))
    if state.get('resource_context') is not None:
        _section(parts, 'Local budget, shared capacity and Aurora planning', _values(state['resource_context']))
    if state.get('execution_initial_information') or state.get('execution_resource_information'):
        for name, title in (
                ('execution_resource_capabilities', 'Actual configured execution resources'),
                ('execution_initial_information', 'Retained initial resource observations'),
                ('execution_resource_information', 'Retained resource observations')):
            if state.get(name) not in (None, {}, []):
                _section(parts, title, json.dumps({name: state[name]}, ensure_ascii=False,
                    allow_nan=False, separators=(',', ':')))
    if state.get('shared_information_context') is not None:
        _section(parts, 'Shared-parent information needs and available deliveries',
            _values(state['shared_information_context']))
    for key, title in (
            ('a103_sheet', 'Current gene-context scoring sheet'),
            ('received_gene_context_execution', 'Received genomic context execution outcomes'),
            ('tool_attachments', 'Saved measurement-specific context attribution'),
            ('source_contributions', 'Saved source contributions'),
            ('literature_current_scoring_sheets', 'Saved received gene-context evidence sheets')):
        if state.get(key):
            _section(parts, title, _literal(state[key]))
    yields = state.get("action_yields", {})
    rows = []
    for row in yields.get("rows", ()):
        expected = row.get("expected_yield", {})
        point, uncertainty = _band(expected.get("band"))
        if expected.get("status") == "unavailable":
            point = "unavailable"
            uncertainty = expected.get("unavailable_reason") or uncertainty
        rows.append((row["category"], row["completed_actions"], row["total_yield"], point,
            uncertainty, row.get("attempted_uncompleted")))
    _section(parts, "Own completed actions", _table(("Category", "Completed", "Total signed yield",
        "Expected next yield", "Uncertainty or unavailable reason", "Uncompleted attempts"), rows))
    controller = state.get("controller", {})
    estimate = controller.get("estimate", {})
    if estimate:
        point, uncertainty = _band(estimate.get("expected_next_gain"))
        _section(parts, "Current continuation expectation", _table(
            ("Completed actions", "Expected next gain", "Uncertainty", "Continuation cost"),
            [(estimate.get("turns"), point, uncertainty,
                controller.get("decision", {}).get("continuation_cost"))]))
    metrics = _pick(state, ("current_credit", "annotation_score", "monitoring_information_credit"))
    if metrics:
        _section(parts, "Current separate measures", _values(metrics))
    progress = {key: state[key] for key in ("credit_binding", "investigation_progress")
        if state.get(key) is not None}
    if progress:
        _section(parts, "Scientific progress definition and current findings",
            _literal(progress))
    if yields.get("unavailable_reasons"):
        _section(parts, "Yield information limits", _values(yields["unavailable_reasons"]))
    records = _received_records(state)
    if records:
        _section(parts, "Current interpretations and their received evidence", _values(records))
    if state.get("current_report_update"):
        _section(parts, "Current return interpretation", _values(state["current_report_update"]))
    # Completed-work accounts summarize outcomes and earned credit; they omit
    # source bodies, exact witnesses and command streams. Preserve the latest
    # authorized tool return so the episode can use what it actually acquired.
    if state.get("last_local_outcome") is not None:
        _section(parts, "Last own action outcome", _values(_information(_outcome(state["last_local_outcome"]))))
    if state.get("feedback") is not None and state["feedback"] != (state.get("last_local_outcome") or {}).get("feedback"):
        _section(parts, "Actionable feedback", _values(_feedback(state["feedback"])))
    if state.get("child_reports") and 'completed_action_reports' not in state:
        _section(parts, "Admitted child returns", _values([
            alignment_report_presentation(report) for report in state["child_reports"]]))
    if state.get("received_bvbrc_values"):
        _section(parts, "Received BV-BRC Data API values", _values([
            _pick(group, ("form_field", "fact_source", "facts", "cells", "unavailable"))
            for group in state["received_bvbrc_values"]]))
    pending = state.get("pending_work", {})
    if pending.get("items"):
        rows = []
        for row in pending["items"]:
            current = _pick(row, ("handle", "role", "lifecycle_state", "selected_at", "observed_at",
                "latest_progress_ref", "return_available", "event_target", "original_assignment"))
            resource = row.get("resource_selection")
            if resource is not None:
                current["resource_selection"] = _pick(resource, ("resource_id", "kind", "allocation"))
            rows.append(current)
        _section(parts, "Pending work", _values(rows))
        wanted = {row.get("latest_progress_ref") for row in pending["items"]}
        progress = [_progress(row) for row in state.get("waiting_support", {}).get("progress_records", ())
            if row.get("progress_ref") in wanted and row.get("progress_ref") is not None]
        if progress:
            _section(parts, "Latest received progress for pending work", _values(progress))
    if state.get("resource_tool_estimates"):
        _section(parts, "Execution duration expectations", _values([_pick(row,
            ("job_ref", "proposal_ref", "execution_class_ref", "current_condition_state", "status", "phase",
             "cpu_threads", "memory_limit_bytes", "scratch_limit_bytes", "successful_duration_samples",
             "outcome_support", "expected_total_seconds", "observed_min_seconds", "observed_max_seconds",
             "forecast_duration_measure", "elapsed_seconds", "timing_relation"))
            for row in state["resource_tool_estimates"]]))
    if state.get("job_execution_options"):
        _section(parts, "Operands for the duration expectations", _values(state["job_execution_options"]))
    if state.get("native_event_targets"):
        _section(parts, "Available native event operands", _values([
            {"target": _pick(row["target"], ("handle", "job_ref", "resource_id", "event", "cause")),
                "after_cursor": row["after_cursor"]} for row in state["native_event_targets"]]))
    deliveries = [row for row in state.get("report_deliveries", ())
        if row.get("status") == "pending" or row.get("timing_receipt_issues")]
    if deliveries:
        _section(parts, "Report delivery issues", _values(deliveries))
    parse_failures = [_record(row) for row in state.get("working_state", {}).get("parse_attempts", ())
        if row.get("status") not in {None, "completed"} or row.get("error_count", 0)]
    if parse_failures:
        _section(parts, "Supplied material parsing issues", _values(parse_failures))
    for result in lookup_results:
        _section(parts, "Requested information; continue the same decision", _lookup(result))
    return "\n".join(parts)


def render_episode_steering(state, *, lookup_results=()):
    from .native_profile_presentation import select_native_profile_presentation, render_native_profile_results
    selected = select_native_profile_presentation(state, lookup_results=lookup_results)
    parts = [_steering(selected['context'], selected['lookup_results'])]
    if selected['projections']:
        parts.append(render_native_profile_results(selected['projections']))
    return '\n'.join(parts)


def render_gene_context_evidence_prompt(state, instructions, *, lookup_results=()):
    """Complete recurring TASK plus current, mechanically selected STEERING."""
    if not is_published_scientific_context(state):
        raise ValueError("published_scientific_instructions_required")
    return _task(state, instructions) + "\n\n" + render_episode_steering(state,
        lookup_results=lookup_results)


__all__ = ["is_published_scientific_context", "text_instructions", "render_episode_steering", "render_gene_context_evidence_prompt"]

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
_EXECUTION_OPAQUE_PREFIXES = ("artifact_", "source_", "observation_", "reference_", "operation_",
    "episode_", "goal_", "input_", "scientific_invocation_", "progress_", "execution_")


def _execution_opaque_reference(value):
    if not isinstance(value, str):
        return False
    for prefix in _EXECUTION_OPAQUE_PREFIXES:
        if value.startswith(prefix):
            suffix = value[len(prefix):]
            return 24 <= len(suffix) <= 64 and all(character in "0123456789abcdef" for character in suffix)
    return False


def _execution_presentation_values(value):
    """Keep supplied scientific values, without native custody or host coordinates."""
    if isinstance(value, Mapping):
        from .execution_prompt import select_profile_api_execution_values
        api = select_profile_api_execution_values(value)
        if api is not None:
            return api
        from .native_profile_presentation import select_native_profile_execution_values
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
    steering = _execution_presentation_values(_pick(state, ("action_yields", "controller", "current_credit",
        "completed_action_reports",
        "last_local_outcome", "feedback", "child_reports", "pending_work", "report_deliveries",
        "waiting_support", "resource_tool_estimates", "job_execution_options", "native_event_targets",
        "pending_child_delivery")))
    lookups = [_execution_presentation_values(value) for value in lookup_results]
    parts = [_selected_execution_task(state, instructions),
        render_episode_steering(steering, lookup_results=lookups)]
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
    return "\n\n".join(parts)


__all__ += ["is_selected_execution_context", "render_selected_execution_prompt"]
