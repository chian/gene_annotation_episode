"""Fill one ordinary scientific Episode role from composable A/P options and actual retrieved tools.

The binding supplies the decision problem and actual callable restrictions.
The common Episode loop owns iteration; the caller's projection owns credit.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import re

from .communication import (ReportBoundaryError, interpretation_schema, plain,
    validate_closed_schema, validate_form)
from .domain import ContractError, identity, obj, validate_schema
from .episode_bindings import reference_in_context
from .scientific_process_records import (scientific_digest, scientific_invocation_ref,
    validate_child_selection, validate_filled_process, validate_option_ref,
    validate_revision_origin, validate_selection, selection_fields, selector_selection,
    SELECTION_VERSION, LEGACY_SELECTION_VERSION)
from .scientific_process_reports import (build_process_result, merge_process_results,
    report_sources, validate_process_result)
from .scientific_support_metadata import (SUPPORT_ENTRY_VERSION,
    support_observation_kinds, validate_support_entry)
from .evidence_axis_contracts import (VERSION as EVIDENCE_AXIS_VERSION,
    validate_evidence_axis_entry)
from .evidence_axis_instructions import (VERSION as INSTRUCTION_VERSION,
    instruction_view, validate_instruction_entry)
from .scientific_process_library import evidence_axis_instruction_view
from .alignment_site_returns import (alignment_site_fact_sources,
    requested_site_projections, project_site_action_return, validate_frozen_site_return)
from .restriction_mapping_returns import (restriction_mapping_fact_sources,
    requested_restriction_projections, project_restriction_action_return,
    validate_frozen_restriction_return)
from .molecular_measurement_tools import (itc_parameter_fact_sources,
    merge_itc_parameter_facts, requested_itc_parameter_fields,
    validate_frozen_itc_parameter_return)


VERSION = "scientific_process_episodes_v8"
ROLE = "scientific_process"
ROLES = (ROLE,)
_COMMON_TOOLS = ("process.search", "process.entry", "process.sources", "process.tools",
    "knowledge.search", "knowledge.entry", "knowledge.read", "episode.history",
    "episode.credit", "episode.annotation_score", "episode.monitoring_information",
    "episode.estimate_wait")
_REFERENCE = {"type": "string", "pattern": r"^[a-z][a-z_]*_[a-f0-9]{24,64}$"}
_SHA256 = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
_SCIENTIFIC_NAMESPACES = frozenset({"scientific_invocation", "scientific_preparation",
    "scientific_process_library", "scientific_option_digest", "scientific_credit_binding"})
_IMPLEMENTATION_FILES = ("scientific_process_episodes.py", "scientific_process_setup.py",
    "scientific_process_records.py", "scientific_process_reports.py",
    "scientific_process_provenance.py", "scientific_tool_library.py",
    "scientific_support_metadata.py", "scientific_process_library.py",
    "evidence_axis_instructions.py", "episode_services.py", "resource_tool_information.py",
    "scientific_tool_retrieval.py", "tool_schema_validation.py",
    "alignment_site_action_records.py", "alignment_site_returns.py",
    "alignment_site_native.py", "episode_return_records.py",
    "restriction_mapping_action_records.py", "restriction_mapping_references.py",
    "restriction_mapping_returns.py", "restriction_mapping_bound_contracts.py",
    "restriction_mapping_publication.py", "restriction_mapping_jobs.py",
    "restriction_mapping_inputs.py", "restriction_mapping_worker.py",
    "restriction_mapping_contracts.py", "restriction_mapping_readers.py",
    "restriction_mapping_registry.py", "restriction_mapping_selection.py",
    "episode_contract_information.py", "episode_journal.py", "native_file_capture.py",
    "molecular_measurement_tools.py")
_ITC_PARAMETER_SOURCE = "itc_binding_parameters"


def _object(value, code):
    if not isinstance(value, Mapping):
        raise ContractError(code)
    try:
        scientific_digest(value)
        result = json.loads(json.dumps(plain(value), allow_nan=False))
        return result
    except (TypeError, ValueError, OverflowError) as error:
        raise ContractError(code) from error


def _ref_schema(slot, prefix):
    return obj({"version": {"const": "scientific_process_option_ref_v1"},
        "library_id": _SHA256, "slot": {"const": slot},
        "option_id": {"type": "string", "pattern": "^" + prefix + "[0-9]+$"},
        "entry_sha256": _SHA256})


_ANNOTATION_REF = _ref_schema("annotation_distinction", "A")
_EVIDENCE_AXIS = deepcopy(_ANNOTATION_REF)
_EVIDENCE_AXIS['properties']['slot'] = {'enum': ['evidence_axis', 'annotation_distinction']}
_THOUGHT_REF = _ref_schema("thought_pattern", "P")
_TOOLS = {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True}
_LEGACY_SELECTION = obj({"version": {"const": LEGACY_SELECTION_VERSION},
    "annotation_ref": _ANNOTATION_REF, "thought_ref": _THOUGHT_REF,
    "tools": _TOOLS})
_TOOL_SELECTOR = obj({'name': {'type': 'string', 'minLength': 1},
                     'resources': {'enum': ['api', 'local', 'hpc']}})
_TOOL_INFO = obj({**_TOOL_SELECTOR['properties'],
    'description': {'type': 'string', 'minLength': 1},
    'instructions': {'type': 'string', 'minLength': 1}})
_SELECTION = obj({'version': {'const': SELECTION_VERSION},
    'evidence_axis': _EVIDENCE_AXIS, 'thought_pattern': _THOUGHT_REF,
    'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
_CANONICAL_SELECTION = deepcopy(_SELECTION)
_CANONICAL_SELECTION['properties']['child_tool_info']['items'] = _TOOL_INFO
_REVISION_ORIGIN = obj({"version": {"const": "scientific_process_revision_origin_v1"},
    "parent_invocation_ref": {"type": "string",
        "pattern": "^scientific_invocation_[a-f0-9]{24}$"},
    "preparation_operation_ref": {"type": "string", "pattern": "^operation_[a-f0-9]{24}$"}})
_ASSIGNMENT = obj({"selection": _SELECTION,
    "evidence_refs": {"type": "array", "items": _REFERENCE, "uniqueItems": True},
    "constraints": {"type": "object"}, "context": {"type": "object"},
    "revision_origin": _REVISION_ORIGIN},
    required=["selection", "evidence_refs", "constraints", "context"])
_RECORDED_ASSIGNMENT = deepcopy(_ASSIGNMENT)
_RECORDED_ASSIGNMENT['properties']['selection'] = {'anyOf': [_CANONICAL_SELECTION, _LEGACY_SELECTION]}
_REVISION_ARGUMENTS = obj({'thought_pattern': _THOUGHT_REF,
    'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
_LEGACY_REVISION_ARGUMENTS = obj({"thought_ref": _THOUGHT_REF, "tools": _TOOLS})


class ScientificProcessEpisodes:
    """One recursive C7 role with parent-selected A/P and actual tool assignment data."""

    roles = ROLES
    entry_roles = ROLES

    def __init__(self, services, *, library, tool_library, child_roles, tool_retrieval=None):
        if (not isinstance(child_roles, (tuple, list)) or not child_roles
                or any(not isinstance(role, str) or not role for role in child_roles)
                or len(set(child_roles)) != len(child_roles) or ROLE not in child_roles):
            raise ContractError("scientific_child_roles_invalid")
        self.services, self.library, self.tool_library = services, library, tool_library
        self._child_roles = tuple(child_roles)
        self._library_record = _object(library.as_record(), "scientific_library_invalid")
        self._tools_record = _object(tool_library.as_record(), "scientific_tool_library_invalid")
        axes = [header['option_ref'] for header in library.headers()
                if header['option_ref']['slot'] in ('evidence_axis', 'annotation_distinction')]
        # This existing runtime capability is binding-wide. Opt in only for a
        # wholly instruction-only publication; legacy and mixed catalogs retain
        # their original default instruction composition.
        self.replaces_default_instructions = bool(axes) and all(
            library.resolve(reference).get('entry_version') == INSTRUCTION_VERSION
            for reference in axes)
        from .scientific_tool_retrieval import configuration
        self.tool_retrieval = configuration(tool_retrieval)

    def as_record(self):
        implementation = scientific_digest({name: hashlib.sha256(
            Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in _IMPLEMENTATION_FILES})
        return {"version": VERSION, "binding_id": ROLE,
            "implementation_sha256": implementation, "configuration": {
                "library": deepcopy(self._library_record),
                "tool_library": deepcopy(self._tools_record),
                "child_roles": list(self._child_roles),
                **({"tool_retrieval": deepcopy(self.tool_retrieval)} if self.tool_retrieval else {})}}

    @staticmethod
    def _role(role):
        if role != ROLE:
            raise ContractError("scientific_process_role_not_bound")

    def child_roles(self, role):
        self._role(role)
        return self._child_roles

    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    def assignment_schema(self, role):
        self._role(role)
        return deepcopy(_ASSIGNMENT)

    def _selection(self, value):
        selection = validate_selection(value)
        fields = selection_fields(selection)
        for key in fields[:2]:
            reference = selection[key]
            if reference["library_id"] != self._library_record["library_id"]:
                raise ContractError("scientific_selection_library_mismatch")
            # Resolution checks the selected body's identity, not merely its ID.
            entry = self.library.resolve(reference)
            if key == fields[0]:
                if entry.get('entry_version') == INSTRUCTION_VERSION:
                    validate_instruction_entry(entry)
                elif entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
                    validate_evidence_axis_entry(entry)
                elif entry.get("entry_version") != SUPPORT_ENTRY_VERSION:
                    raise ContractError("scientific_support_metadata_required")
                else:
                    validate_support_entry(entry)
        if selection['version'] == LEGACY_SELECTION_VERSION:
            self.tool_library.resolve(selection['tools'])
        else:
            self.tool_library.resolve_tool_info(selection['child_tool_info'])
        return selection

    def _assignment(self, value, scope, *, materialize=False):
        assignment = _object(value, "scientific_assignment_invalid")
        if (materialize and isinstance(assignment.get('selection'), dict)
                and assignment['selection'].get('version') == SELECTION_VERSION):
            # Descriptions and resource-specific instructions are host facts.
            # The model chooses only the exact name/resource identity pair.
            selected = assignment['selection']
            selected['child_tool_info'] = self.tool_library.resolve_tool_info(
                selected.get('child_tool_info'), self._information_catalog(scope))
        validate_schema(assignment, _RECORDED_ASSIGNMENT)
        assignment["selection"] = self._selection(assignment["selection"])
        if "revision_origin" in assignment:
            assignment["revision_origin"] = validate_revision_origin(assignment["revision_origin"])
        for reference in assignment["evidence_refs"]:
            if (not re.fullmatch(_REFERENCE["pattern"], reference)
                    or not self.services.reference_in_scope(reference, scope, None)):
                raise ContractError("scientific_evidence_reference_unavailable", detail={
                    "reference": reference})
        # Construction must bind actual current callables before publishing a
        # child or computing its initial credit. Recovery repeats the same
        # comparison, never substituting another operation for a stale name.
        self._tool_resolution_for(assignment['selection'], scope)
        return assignment

    @staticmethod
    def _invocation(invocation, scope):
        value = _object(invocation, "scientific_invocation_invalid")
        if (set(value) != {"objective", "purpose", "report_schema", "initial_report"}
                or not isinstance(value["objective"], str) or not value["objective"]
                or not isinstance(value["purpose"], str) or not value["purpose"]
                or not isinstance(value["initial_report"], dict)):
            raise ContractError("scientific_invocation_invalid")
        schema = validate_closed_schema(value["report_schema"])
        requested_site_projections(schema)
        requested_restriction_projections(schema)
        requested_itc_parameter_fields(schema)
        validate_schema(value["initial_report"], interpretation_schema(schema))
        return {"objective": value["objective"],
            "scope": _object(scope, "scientific_scope_invalid"),
            "purpose": value["purpose"], "report_schema": schema,
            "initial_report": value["initial_report"]}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if parent is None:
            raise ContractError("scientific_parent_invocation_required")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        assignment = self._assignment(selection, scope, materialize=True)
        if "revision_origin" in assignment:
            self._validate_origin(parent, assignment, owner="self")
        return assignment

    def _validate_origin(self, context, assignment, *, owner):
        origin = validate_revision_origin(assignment["revision_origin"])
        preparation = _object(self.services.scientific_preparation(context,
            origin["preparation_operation_ref"], owner=owner),
            "scientific_revision_preparation_invalid")
        if set(preparation) != {"operation_ref", "owner_invocation_ref", "owner_selection",
                "arguments", "proposal", "revision_origin"}:
            raise ContractError("scientific_revision_preparation_invalid")
        initial = self._selection(preparation["owner_selection"])
        arguments = _object(preparation["arguments"], "scientific_revision_preparation_invalid")
        proposal = validate_child_selection(preparation["proposal"])
        argument_schema = (_LEGACY_REVISION_ARGUMENTS if proposal['selection']['version'] == LEGACY_SELECTION_VERSION
                           else _REVISION_ARGUMENTS)
        validate_schema(arguments, argument_schema)
        prepared_origin = validate_revision_origin(preparation["revision_origin"])
        expected_path = context.path if owner == "self" else context.path[:-1]
        expected_owner = scientific_invocation_ref(context.run_id, expected_path)
        if (preparation["operation_ref"] != origin["preparation_operation_ref"]
                or preparation["owner_invocation_ref"] != expected_owner
                or origin["parent_invocation_ref"] != expected_owner
                or prepared_origin != origin
                or proposal["parent_selection_sha256"] != scientific_digest(initial)
                or proposal["selection"] != assignment["selection"]
                or proposal["selection"] != self._proposed_selection(initial, arguments,
                    proposal['selection']['version'], context.scope)):
            raise ContractError("scientific_revision_preparation_mismatch")

    def prepare_invocation(self, parent, role, inputs, scope, operation_key, *, invocation):
        original = self._invocation(invocation, scope)
        assignment = self.prepare_assignment(parent, role, inputs, scope, operation_key)
        filled = validate_filled_process({"version": "filled_scientific_process_v1",
            "selection": assignment["selection"],
            "assignment_sha256": scientific_digest(assignment),
            "invocation_sha256": scientific_digest(original),
            "mechanics_binding": self.as_record()})
        return {"assignment": assignment, "scientific_process": filled}

    def restore_closed_process(self, context) -> dict | None:
        """Restore only the original mechanics identity of an exact closed request."""
        self._role(context.role)
        read_closed = getattr(self.services, 'scientific_closed_request', None)
        if not callable(read_closed):
            return None
        original = read_closed(context)
        if original is None:
            return None
        original = _object(original, 'scientific_closed_request_invalid')
        candidate = _object(context.request, 'scientific_filled_request_required')
        try:
            saved = validate_filled_process(original['message']['scientific_process'])
            filled = validate_filled_process(candidate['message']['scientific_process'])
            saved_binding = saved['mechanics_binding']
            saved_hash = saved_binding['implementation_sha256']
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_closed_request_invalid') from error
        if not isinstance(saved_hash, str) or re.fullmatch(_SHA256['pattern'], saved_hash) is None:
            raise ContractError('scientific_closed_implementation_identity_invalid')
        current = self.as_record()
        # No other mechanics field, assignment operand or requested meaning is
        # relaxed. The candidate must carry today's binding or this exact saved
        # binding; an unrelated caller-supplied hash is not a replay identity.
        if ({**saved_binding, 'implementation_sha256': current['implementation_sha256']} != current
                or filled['mechanics_binding'] not in (current, saved_binding)):
            raise ContractError('scientific_filled_identity_mismatch')
        candidate['message']['scientific_process']['mechanics_binding']['implementation_sha256'] = saved_hash
        if (candidate != original
                or plain(context.scope) != original['message'].get('scope')
                or plain(context.assignment) != original['message'].get('episode_assignment')):
            raise ContractError('scientific_filled_identity_mismatch')
        return saved

    def validate_context(self, context):
        self._role(context.role)
        request = _object(context.request, "scientific_filled_request_required")
        try:
            message = request["message"]
            filled = validate_filled_process(message["scientific_process"])
            contract = request["report_contract"]
            original = self._invocation({"objective": request["goal"]["objective"],
                "purpose": contract["decision"],
                "report_schema": contract["measurements"]["schema"],
                "initial_report": message["initial_report"]}, message["scope"])
            assignment = self._assignment(context.assignment, context.scope)
        except (KeyError, TypeError) as error:
            raise ContractError("scientific_filled_request_required") from error
        if (assignment != message.get("episode_assignment")
                or plain(context.scope) != message["scope"]
                or message.get("scientific_invocation_ref") != scientific_invocation_ref(
                    context.run_id, context.path)
                or filled["selection"] != assignment["selection"]
                or filled["assignment_sha256"] != scientific_digest(assignment)
                or filled["invocation_sha256"] != scientific_digest(original)):
            raise ContractError("scientific_filled_identity_mismatch")
        if (filled['mechanics_binding'] != self.as_record()
                and self.restore_closed_process(context) != filled):
            raise ContractError("scientific_filled_identity_mismatch")
        if "revision_origin" in assignment:
            self._validate_origin(context, assignment, owner="parent")

    def validate_execution_context(self, context) -> None:
        """Historical closure permits inspection/replay, never new dispatch."""
        self.validate_context(context)
        if plain(context.request['message']['scientific_process']['mechanics_binding']) != self.as_record():
            raise ContractError('scientific_execution_identity_mismatch')

    def _original_selection(self, context):
        self.validate_context(context)
        return validate_selection(context.assignment["selection"])

    def permitted_common_actions(self, context):
        self.validate_context(context)
        return ("tool", "reason", "child", "wait", "redeliver_report")

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        return self._child_roles

    def instructions(self, context):
        self.validate_context(context)
        selection = context.assignment['selection']
        axis = self.library.resolve(selection[selection_fields(selection)[0]])
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            return (
                "Determine what the supplied target does within the parent's assigned question, scope "
                "and constraints. Start with the supplied sequence, selected file contents or snippets, "
                "preserving their boundaries, completeness and known context. No initial candidate "
                "annotation or publicly searchable name is required. Possible functions can emerge "
                "from the evidence and be compared or revised. Apply the complete selected investigation "
                "instructions and thought-pattern guidance on every decision. Use actual outcomes and "
                "received child results to choose and revise your approach. Selected instructions "
                "describe how to investigate; they are not evidence about this target. Preserve the "
                "measured subject, conditions, controls, native measurements, uncertainty and limits of "
                "inference when interpreting evidence. Missing information remains unknown.\n\n"
                "Choose an available tool action, commit a scientific interpretation through the "
                "reasoning action, commission a scoped child with its own typed return form, or wait "
                "for selected pending work when that informs the investigation. Use only the selected "
                "actual tools and their supplied resource instructions; choose callable operands "
                "through the declared response contract. Preserve the parent's exact requested result "
                "meanings and allowed values. Recorded facts come from actual records. Keep inherited "
                "information distinct from new findings and completed work distinct from attempts. "
                "Return valid partial findings and specific failures through the requested form.\n\n"
                "Keep the assigned evidence axis, thought pattern and selected tools for this episode. "
                "process.revise prepares a different thought pattern and/or tool selection for a new "
                "child; it does not change this episode or start that child. To commission that "
                "alternative, copy its selection and revision_origin into a separately selected child "
                "assignment with the child's job, scope, constraints and typed return. Children own "
                "their iterative choices. The configured controller "
                "owns continuation. Waiting and unchanged observations do not manufacture progress.")
        return ("Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. "
            "The selected scientific support proposition and operands define the support problem; "
            "the thought pattern supplies alternatives "
            "and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. "
            "Choose your own actions using actual outcomes and received child forms. The selection is no "
            "prescribed sequence or automatic compatibility verdict. Library sources are instruction "
            "provenance, not scientific evidence about this target. Inspect actual source subjects, "
            "conditions and target applicability before interpreting evidence. annotation_support_routes "
            "describes the actual separately bound annotation policy's kind dispatch. An unmapped kind "
            "has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot "
            "declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself "
            "earns no credit and never replaces or filters the actual projectors, annotation formula or "
            "continuation rule. Keep the parent's objective, scope, constraints "
            "and exact typed form; support metadata never adds form fields or scoring axes. Use common reasoning "
            "to commit scientific interpretations. Keep the originally assigned scientific support, "
            "thought pattern and selected tool set throughout this episode. Explicit process.revise prepares "
            "a selection for a new child; a separately selected episode_child action commissions that "
            "child with its own job, scope, constraints and typed return form. Preparation changes no "
            "current process and starts no child. Copy both result.selection and revision_origin into "
            "that child's assignment to identify it as an alternative approach. Request the recorded "
            "scientific_process_results source in child forms when their process relationships and "
            "existing closed credit/yield are needed for steering. Only retrieved actual tools are available; "
            "their descriptions do not grant execution. The configured controller owns continuation.")

    def _information_catalog(self, scope):
        # Older injected ordinary-only service ports have no resource routes.
        # This fallback grants no operation beyond their original direct map.
        callback = getattr(self.services, 'tool_information_catalog', self.services.tool_catalog)
        return callback(scope)

    def _tool_resolution_for(self, selection, scope):
        return (self.tool_library.resolve(selection['tools'], self.services.tool_catalog(scope))
            if selection['version'] == LEGACY_SELECTION_VERSION else
            self.tool_library.resolve_invocations(selection['child_tool_info'], self._information_catalog(scope)))

    def _tool_resolution(self, context, selection):
        entries = self._tool_resolution_for(selection, context.scope)
        if any(entry["name"] in {*_COMMON_TOOLS, "process.revise"} for entry in entries):
            raise ContractError("scientific_primitive_uses_common_tool_name")
        return entries

    def _proposed_selection(self, initial, arguments, version, scope):
        axis_field = selection_fields(initial)[0]
        if version == LEGACY_SELECTION_VERSION:
            validate_schema(arguments, _LEGACY_REVISION_ARGUMENTS)
            return self._selection({'version': version, 'annotation_ref': initial[axis_field],
                'thought_ref': arguments['thought_ref'], 'tools': arguments['tools']})
        validate_schema(arguments, _REVISION_ARGUMENTS)
        return self._selection({'version': SELECTION_VERSION, 'evidence_axis': initial[axis_field],
            'thought_pattern': arguments['thought_pattern'], 'child_tool_info':
                self.tool_library.resolve_tool_info(arguments['child_tool_info'], self._information_catalog(scope))})

    def catalog(self, context):
        selection = self._original_selection(context)
        resolved = self._tool_resolution(context, selection)
        if selection['version'] != LEGACY_SELECTION_VERSION:
            direct = [{'name': row['name'], 'resources': row['resources']} for row in resolved
                      if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
            resolved = self.tool_library.resolve_invocations(direct, self.services.tool_catalog(context.scope))
        entries = [{key: deepcopy(value) for key, value in row.items()
                    if key not in {'instructions', 'invocation_route'}} for row in plain(resolved)]
        description = (
            "Prepare a pinned thought pattern and selected actual tools for a new child using the original "
            "scientific support and library. Return its selection for a separately selected episode_child "
            "commission with the child's job, scope, constraints and typed form. Copy result.selection "
            "and revision_origin into that assignment; request scientific_process_results in the form "
            "when process provenance and existing closed results are needed. Changes no current "
            "process, starts no child and records no biological observation. Supply the actual tool names "
            "returned by process.tools for the desired alternative investigation.")
        axis = self.library.resolve(selection[selection_fields(selection)[0]])
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            description = (
                "Prepare a different thought pattern and/or selected actual tools for a new child "
                "investigating the same evidence axis. Return its selection for a separately selected "
                "episode_child commission with the child's job, scope, constraints and typed return "
                "form. Copy result.selection and revision_origin into that assignment. Changes no "
                "current process, starts no child and records no biological observation. Select the "
                "actual tool/resource choices returned by process.tools for the desired investigation.")
        entries.append({"name": "process.revise", "description": description,
            "input_schema": deepcopy(_LEGACY_REVISION_ARGUMENTS
                if selection['version'] == LEGACY_SELECTION_VERSION else _REVISION_ARGUMENTS)})
        return entries

    def common_tool_names(self, context):
        # Runtime applies this after adding its helpers, so retain selected
        # primitives and the child-selection preparation as well as retrieval.
        return (*_COMMON_TOOLS, *(entry["name"] for entry in self.catalog(context)))

    def decision_context(self, context, current_view):
        selection = self._original_selection(context)
        annotation, thought = (self.library.resolve(selection[key]) for key in selection_fields(selection)[:2])
        resolved = self._tool_resolution(context, selection)
        def selected_fields(entry, names):
            return {name: deepcopy(entry[name]) for name in names if name in entry}
        fields = selection_fields(selection)
        current = selection['version'] == SELECTION_VERSION
        assignment = plain(context.assignment)
        if current:
            assignment = {**assignment, 'selection': selector_selection(selection)}
        published = annotation.get('entry_version') == INSTRUCTION_VERSION
        if published:
            axis_view = instruction_view(annotation)
        elif annotation.get('entry_version') == EVIDENCE_AXIS_VERSION:
            axis_view = evidence_axis_instruction_view(annotation)
        else:
            axis_view = selected_fields(annotation, ("id", "name", "description", "support"))
        return {"scientific_process": {"selection": selector_selection(selection),
            "initial_selection_sha256": scientific_digest(plain(context.assignment["selection"])),
            ('evidence_axis' if current else 'annotation'): axis_view,
            **({} if published else {"annotation_support_routes": self.services.scientific_support_routes(context,
                observation_kinds=support_observation_kinds(annotation))}),
            ('thought_pattern' if current else 'thought'): selected_fields(thought, ("id", "name", "description", "use_when",
                "live_alternatives", "decision_guidance", "outcome_contingencies", "boundary")),
            **({'child_tool_info': deepcopy(selection[fields[2]])} if current else {'tools': deepcopy(resolved)}),
            "assignment": assignment, "permitted_children": list(self._child_roles)}}

    async def execute(self, context, tool_name, arguments, operation_key):
        self.validate_execution_context(context)
        selection = validate_selection(context.assignment['selection'])
        try:
            if not isinstance(operation_key, str) or not operation_key:
                raise ContractError("operation_key_required")
            entries = {entry["name"]: entry for entry in self.catalog(context)}
            if tool_name not in entries:
                raise ContractError("scientific_operation_unavailable")
            arguments = _object(arguments, "scientific_arguments_invalid")
            validate_schema(arguments, entries[tool_name]["input_schema"])
            if tool_name == 'sequence.align':
                self.services.authenticate_structure_alignment_operands(context, arguments)
            elif tool_name == 'execution.estimate' and arguments['tool'] == 'sequence.align':
                self.services.authenticate_structure_alignment_operands(context, arguments['arguments'])
            if tool_name in {'material.from_source', 'material.parse', 'material.read',
                             'source.read', 'source.locate'}:
                self.services.authenticate_source_byte_operands(context, tool_name, arguments)
            if tool_name == "process.revise":
                proposed = self._proposed_selection(selection, arguments, selection['version'], context.scope)
                self._tool_resolution(context, proposed)
                child_selection = validate_child_selection({
                    "version": "scientific_process_child_selection_v1",
                    "parent_selection_sha256": scientific_digest(selection),
                    "selection": proposed})
                operation_ref = identity("operation", {
                    "key": operation_key, "name": tool_name, "arguments": arguments})
                origin = validate_revision_origin({"version": "scientific_process_revision_origin_v1",
                    "parent_invocation_ref": scientific_invocation_ref(context.run_id, context.path),
                    "preparation_operation_ref": operation_ref})
                return {"status": "completed", "operation_ref": operation_ref,
                    "record_refs": [], "changed_record_refs": [], "result": child_selection,
                    "revision_origin": origin, "feedback": None}
        except ValueError as error:
            return {"status": "invalid", "operation_ref": identity("operation", {
                "key": operation_key, "name": tool_name}), "record_refs": [],
                "changed_record_refs": [], "result": None,
                "feedback": {"category": "arguments_or_reference", "code": str(error),
                    **({"detail": error.detail} if getattr(error, "detail", None) else {})}}
        outcome = self.services.execute_tool(tool_name, arguments,
            scope=context.scope, operation_key=operation_key,
            **({'permitted_record_refs': context.received_record_refs}
               if tool_name in {'result.blast.hsp', 'source.locate',
                   'find_restriction_sites', 'find_restriction_enzymes'} else {}))
        return await outcome if inspect.isawaitable(outcome) else outcome

    def fact_sources(self, role):
        self._role(role)
        return {**report_sources(self.library, self.tool_library),
                **alignment_site_fact_sources(), **restriction_mapping_fact_sources(),
                **itc_parameter_fact_sources()}

    def facts(self, context, completion_snapshot):
        from .scientific_process_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)
        def project(value):
            return project_process_result(value, library=self.library,
                tool_library=self.tool_library)
        facts = {"scientific_process_results": merge_process_results(
            None if own is None else project(own), [project(value) for value in received])}
        schema = plain(context.request)['report_contract']['measurements']['schema']
        for source, requested in requested_site_projections(schema).items():
            facts[source], cursor = [], None
            while True:
                page = self.services.alignment_site_own_action_results(context,
                    source=source, selection=requested['selection'],
                    after_decision_index=cursor, limit=64)
                facts[source].extend(project_site_action_return(record, requested['fields'])
                    for record in page['records'])
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
        for source, requested in requested_restriction_projections(schema).items():
            facts[source], cursor = [], None
            while True:
                page = self.services.restriction_mapping_own_action_results(context,
                    selection=requested['selection'], after_decision_index=cursor, limit=64)
                facts[source].extend(project_restriction_action_return(record, requested['fields'])
                    for record in page['records'])
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
        if requested_itc_parameter_fields(schema):
            facts[_ITC_PARAMETER_SOURCE] = merge_itc_parameter_facts(
                self.services.itc_parameter_received_facts(context),
                self.services.itc_parameter_own_facts(context))
        return facts

    def received_report_sources(self, role):
        # Scientific roles declare their own source above; the registry rejects
        # duplicate own/received names. Annotation has no such specialist map.
        return itc_parameter_fact_sources() if role == 'annotation' else {}

    def received_report_facts(self, context):
        if context.role != 'annotation':
            return {}
        schema = plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {})
        if not requested_itc_parameter_fields(schema):
            return {}
        return {_ITC_PARAMETER_SOURCE: merge_itc_parameter_facts(
            self.services.itc_parameter_received_facts(context))}

    def _validate_itc_parameter_report(self, context, form, schema):
        fields = requested_itc_parameter_fields(plain(schema))
        if not fields:
            return
        try:
            frozen = self.services.itc_parameter_frozen_facts(context)
            if frozen is None:
                raise ValueError('itc_parameter_facts_not_frozen')
            validate_frozen_itc_parameter_return(plain(form), plain(schema), frozen)
        except ValueError as error:
            raise ReportBoundaryError('Return differs from the frozen ITC parameter facts',
                code=str(error), field=fields[0]) from error

    def validate_received_report(self, context, form, schema):
        # Scientific roles use their own validate_report branch. This hook also
        # runs for annotation receivers, without adding a new episode binding.
        if context.role == 'annotation':
            self._validate_itc_parameter_report(context, form, schema)

    def resolve(self, context, reference, namespace):
        self.validate_context(context)
        if namespace == 'restriction_enzyme':
            return self.services.restriction_mapping_reference(context, reference, namespace)
        if namespace is None or namespace in _SCIENTIFIC_NAMESPACES:
            if self.services.scientific_reference(context, reference, namespace):
                return True
            if namespace in _SCIENTIFIC_NAMESPACES:
                return False
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace:
            self.resolve(context, reference, namespace))
        self._validate_itc_parameter_report(context, form, original_schema)
        fields = [name for name, node in plain(original_schema)["properties"].items()
                  if node.get("x-source") == "scientific_process_results"]
        projections = requested_site_projections(plain(original_schema))
        if projections:
            try:
                frozen_sites = self.services.alignment_site_frozen_facts(context,
                    sources=tuple(projections))
            except ValueError as error:
                raise ReportBoundaryError('Original site results unavailable',
                    code=str(error)) from error
            validate_frozen_site_return(plain(form), plain(original_schema), frozen_sites)
        restrictions = requested_restriction_projections(plain(original_schema))
        if restrictions:
            try:
                frozen = self.services.restriction_mapping_frozen_facts(context,
                    sources=tuple(restrictions))
            except ValueError as error:
                raise ReportBoundaryError('Original restriction results unavailable',
                    code=str(error)) from error
            validate_frozen_restriction_return(plain(form), plain(original_schema), frozen)
        if not fields:
            return
        # The child's source was frozen before the existing admission callback.
        # Comparing it here also protects the blocking and redelivery paths;
        # no closure quantity is recomputed while validating a returned form.
        try:
            read_frozen = getattr(self.services, "scientific_frozen_results", None)
            if not callable(read_frozen):
                raise ValueError("scientific_frozen_results_unavailable")
            frozen = read_frozen(context)
        except ValueError as error:
            raise ReportBoundaryError("Original process results unavailable",
                code=str(error), field=fields[0]) from error
        for name in fields:
            values = plain(form)[name]
            try:
                for value in values:
                    validate_process_result(value, library=self.library, tool_library=self.tool_library)
                if frozen is None or scientific_digest(values) != scientific_digest(frozen):
                    raise ValueError("scientific_process_result_source_mismatch")
            except ValueError as error:
                raise ReportBoundaryError("Return differs from the original process result",
                    code=str(error), field=name) from error

    def credit_view(self, context, receiver_selection):
        self.validate_context(context)
        return self.services.scientific_credit(context, receiver_selection)

    def initial_references(self, context):
        if context.role != ROLE:
            return []
        self.validate_context(context)
        return list(context.assignment["evidence_refs"])

    def received_form_references(self, context, form, schema, operation_key):
        # The existing typed form/receipt path owns scientific references.
        return []

    def resolve_received_reference(self, context, reference, namespace):
        if namespace != 'restriction_enzyme':
            return None
        # This registry port also runs for the actual receiving parent's role.
        # It precedes generic Store fallback and grants only proved names.
        return self.services.restriction_mapping_reference(context, reference, namespace)


__all__ = ["ScientificProcessEpisodes", "ROLE", "ROLES", "VERSION"]
