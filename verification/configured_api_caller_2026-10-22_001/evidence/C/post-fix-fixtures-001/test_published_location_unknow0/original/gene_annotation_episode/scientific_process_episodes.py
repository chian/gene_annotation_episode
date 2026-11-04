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

from .communication import interpretation_schema, plain, validate_closed_schema, validate_form
from .domain import ContractError, identity, obj, validate_schema
from .episode_bindings import reference_in_context
from .scientific_process_records import (scientific_digest, scientific_invocation_ref,
    validate_child_selection, validate_filled_process, validate_option_ref,
    validate_revision_origin, validate_selection)
from .scientific_process_reports import (build_process_result, merge_process_results,
    report_sources, validate_process_result)
from .scientific_support_metadata import (SUPPORT_ENTRY_VERSION,
    support_observation_kinds, validate_support_entry)


VERSION = "scientific_process_episodes_v5"
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
    "scientific_support_metadata.py", "scientific_process_library.py")


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
_THOUGHT_REF = _ref_schema("thought_pattern", "P")
_TOOLS = {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True}
_SELECTION = obj({"version": {"const": "scientific_process_selection_v2"},
    "annotation_ref": _ANNOTATION_REF, "thought_ref": _THOUGHT_REF,
    "tools": _TOOLS})
_REVISION_ORIGIN = obj({"version": {"const": "scientific_process_revision_origin_v1"},
    "parent_invocation_ref": {"type": "string",
        "pattern": "^scientific_invocation_[a-f0-9]{24}$"},
    "preparation_operation_ref": {"type": "string", "pattern": "^operation_[a-f0-9]{24}$"}})
_ASSIGNMENT = obj({"selection": _SELECTION,
    "evidence_refs": {"type": "array", "items": _REFERENCE, "uniqueItems": True},
    "constraints": {"type": "object"}, "context": {"type": "object"},
    "revision_origin": _REVISION_ORIGIN},
    required=["selection", "evidence_refs", "constraints", "context"])
_REVISION_ARGUMENTS = obj({"thought_ref": _THOUGHT_REF, "tools": _TOOLS})


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
        from .scientific_tool_retrieval import configuration
        self.tool_retrieval = configuration(tool_retrieval)

    def as_record(self):
        files = (*_IMPLEMENTATION_FILES, "scientific_tool_retrieval.py") if self.tool_retrieval else _IMPLEMENTATION_FILES
        implementation = scientific_digest({name: hashlib.sha256(
            Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in files})
        return {"version": "scientific_process_episodes_v6" if self.tool_retrieval else VERSION, "binding_id": ROLE,
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
        for key in ("annotation_ref", "thought_ref"):
            reference = selection[key]
            if reference["library_id"] != self._library_record["library_id"]:
                raise ContractError("scientific_selection_library_mismatch")
            # Resolution checks the selected body's identity, not merely its ID.
            entry = self.library.resolve(reference)
            if key == "annotation_ref":
                if entry.get("entry_version") != SUPPORT_ENTRY_VERSION:
                    raise ContractError("scientific_support_metadata_required")
                validate_support_entry(entry)
        self.tool_library.resolve(selection["tools"])
        return selection

    def _assignment(self, value, scope):
        assignment = _object(value, "scientific_assignment_invalid")
        validate_schema(assignment, _ASSIGNMENT)
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
        self.tool_library.resolve(assignment["selection"]["tools"],
            self.services.tool_catalog(scope))
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
        assignment = self._assignment(selection, scope)
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
        validate_schema(arguments, _REVISION_ARGUMENTS)
        proposal = validate_child_selection(preparation["proposal"])
        prepared_origin = validate_revision_origin(preparation["revision_origin"])
        expected_path = context.path if owner == "self" else context.path[:-1]
        expected_owner = scientific_invocation_ref(context.run_id, expected_path)
        if (preparation["operation_ref"] != origin["preparation_operation_ref"]
                or preparation["owner_invocation_ref"] != expected_owner
                or origin["parent_invocation_ref"] != expected_owner
                or prepared_origin != origin
                or proposal["parent_selection_sha256"] != scientific_digest(initial)
                or proposal["selection"] != assignment["selection"]
                or proposal["selection"] != self._selection({
                    "version": "scientific_process_selection_v2",
                    "annotation_ref": initial["annotation_ref"],
                    "thought_ref": arguments["thought_ref"], "tools": arguments["tools"]})):
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
                or filled["invocation_sha256"] != scientific_digest(original)
                or filled["mechanics_binding"] != self.as_record()):
            raise ContractError("scientific_filled_identity_mismatch")
        if "revision_origin" in assignment:
            self._validate_origin(context, assignment, owner="parent")

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

    def _tool_resolution(self, context, selection):
        entries = self.tool_library.resolve(selection["tools"],
            self.services.tool_catalog(context.scope))
        if any(entry["name"] in {*_COMMON_TOOLS, "process.revise"} for entry in entries):
            raise ContractError("scientific_primitive_uses_common_tool_name")
        return entries

    def catalog(self, context):
        selection = self._original_selection(context)
        entries = deepcopy(plain(self._tool_resolution(context, selection)))
        entries.append({"name": "process.revise", "description":
            "Prepare a pinned thought pattern and selected actual tools for a new child using the original "
            "scientific support and library. Return its selection for a separately selected episode_child "
            "commission with the child's job, scope, constraints and typed form. Copy result.selection "
            "and revision_origin into that assignment; request scientific_process_results in the form "
            "when process provenance and existing closed results are needed. Changes no current "
            "process, starts no child and records no biological observation. Supply the actual tool names "
            "returned by process.tools for the desired alternative investigation.",
            "input_schema": deepcopy(_REVISION_ARGUMENTS)})
        return entries

    def common_tool_names(self, context):
        # Runtime applies this after adding its helpers, so retain selected
        # primitives and the child-selection preparation as well as retrieval.
        return (*_COMMON_TOOLS, *(entry["name"] for entry in self.catalog(context)))

    def decision_context(self, context, current_view):
        selection = self._original_selection(context)
        annotation, thought = (self.library.resolve(selection[key]) for key in
            ("annotation_ref", "thought_ref"))
        resolved = self._tool_resolution(context, selection)
        def selected_fields(entry, names):
            return {name: deepcopy(entry[name]) for name in names if name in entry}
        return {"scientific_process": {"selection": selection,
            "initial_selection_sha256": scientific_digest(plain(context.assignment["selection"])),
            "annotation": selected_fields(annotation, ("id", "name", "description", "support")),
            "annotation_support_routes": self.services.scientific_support_routes(context,
                observation_kinds=support_observation_kinds(annotation)),
            "thought": selected_fields(thought, ("id", "name", "description", "use_when",
                "live_alternatives", "decision_guidance", "outcome_contingencies", "boundary")),
            "tools": deepcopy(resolved),
            "assignment": plain(context.assignment), "permitted_children": list(self._child_roles)}}

    async def execute(self, context, tool_name, arguments, operation_key):
        selection = self._original_selection(context)
        try:
            if not isinstance(operation_key, str) or not operation_key:
                raise ContractError("operation_key_required")
            entries = {entry["name"]: entry for entry in self.catalog(context)}
            if tool_name not in entries:
                raise ContractError("scientific_operation_unavailable")
            arguments = _object(arguments, "scientific_arguments_invalid")
            validate_schema(arguments, entries[tool_name]["input_schema"])
            if tool_name == "process.revise":
                proposed = self._selection({"version": "scientific_process_selection_v2",
                    "annotation_ref": selection["annotation_ref"],
                    "thought_ref": validate_option_ref(arguments["thought_ref"]),
                    "tools": arguments["tools"]})
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
            scope=context.scope, operation_key=operation_key)
        return await outcome if inspect.isawaitable(outcome) else outcome

    def fact_sources(self, role):
        self._role(role)
        return report_sources(self.library, self.tool_library)

    def facts(self, context, completion_snapshot):
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)
        return {"scientific_process_results": merge_process_results(own, received)}

    def resolve(self, context, reference, namespace):
        self.validate_context(context)
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
        for name, node in plain(original_schema)["properties"].items():
            if node.get("x-source") == "scientific_process_results":
                for value in plain(form)[name]:
                    validate_process_result(value, library=self.library, tool_library=self.tool_library)

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


__all__ = ["ScientificProcessEpisodes", "ROLE", "ROLES", "VERSION"]
