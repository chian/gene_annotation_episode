"""Literature specializations of the application's ordinary Episode loop.

This binding supplies operands, available ordinary operations and source
custody. The shared source owns decisions, reasoning commits, commissioning,
waits, report updates and continuation. In particular, a reading selection is
information for an investigation, never a script that this binding executes.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path

from .communication import plain, validate_form
from .domain import ContractError, REF, identity, obj, validate_schema
from .episode_bindings import reference_in_context


VERSION = "literature_episode_binding_v1"
ROLES = ("literature", "literature_strategy", "literature_search",
         "literature_page", "literature_table", "literature_ordered",
         "literature_targeted")

_REFERENCES = {"type": "array", "items": REF, "uniqueItems": True}
_REPRESENTATION = {"type": "string", "enum": ["text", "original", "stdout", "stderr"]}
_NATURAL = {"type": "integer", "minimum": 0}
_POSITIVE = {"type": "integer", "minimum": 1}
_TEXT = {"type": "string", "minLength": 1}
_WINDOW = obj({"source_ref": REF, "representation": _REPRESENTATION,
               "offset": _NATURAL, "limit": _POSITIVE})
_TABLE = obj({"source_ref": REF, "sheet_key": _TEXT, "offset": _NATURAL,
    "limit": _NATURAL, "header_row": {"type": ["integer", "null"], "minimum": 1},
    "where": {**obj({"column": {"type": ["string", "null"], "pattern": "^[A-Z]+$"},
        "match": {"enum": ["equals", "contains"]}, "value": _TEXT,
        "case_sensitive": {"type": "boolean"}}), "type": ["object", "null"]}})
_PAGE = obj({"version": {"const": "page_assignment_v1"}, "source_ref": REF,
    "representation": _REPRESENTATION, "artifact_ref": REF,
    "question_context_refs": _REFERENCES, "prior_delivery_refs": _REFERENCES})

_CHILDREN = {"literature": ("literature_strategy",),
    "literature_strategy": ("literature_search",),
    "literature_search": ("literature_page",),
    "literature_page": ("literature_table", "literature_ordered", "literature_targeted"),
    "literature_table": (), "literature_ordered": (), "literature_targeted": ()}

_ACCESS_TOOLS = ("state.query", "source.read", "image.view", "source.archive.members",
    "source.archive.extract", "source.xlsx.sheets", "source.xlsx.rows",
    "source.pdf.info", "source.pdf.text", "source.pdf.page", "execution.estimate")
_ACQUISITION_TOOLS = ("public.literature.search", "public.literature.read",
    "public.ncbi.search", "public.pmc.versions", "public.pmc.files", "public.pmc.asset")
_READ_TOOLS = ("source.read", "source.xlsx.rows", "source.pdf.text", "image.view")

_ROLE_INSTRUCTIONS = {
    "literature": "Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.",
    "literature_strategy": "Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.",
    "literature_search": "Investigate which returned sources merit examination for the assigned question. Search results are source-discovery information. Examine original sources and their conditions before asserting biological evidence. A page child can investigate where and how to examine a selected source.",
    "literature_page": "Investigate where and how this exact source should be examined. Choose ordinary source operations or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML headings, tables and footnotes; retained original bytes remain addressable.",
    "literature_table": "Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.",
    "literature_ordered": "Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes.",
    "literature_targeted": "Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.",
}


class LiteratureEpisodes:
    """C7 binding for C10 assignments; no model connection or private loop."""

    roles = ROLES
    entry_roles = ("literature",)

    def __init__(self, services, *, outcome_page_size=8):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError("positive_literature_outcome_page_size_required")
        self.services = services
        self.outcome_page_size = outcome_page_size

    def as_record(self):
        return {"version": VERSION, "binding_id": "literature",
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "configuration": {"outcome_page_size": self.outcome_page_size}}

    @staticmethod
    def _role(role):
        if role not in ROLES:
            raise ValueError("unsupported_literature_role:" + str(role))
        return role

    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    def assignment_schema(self, role):
        self._role(role)
        if role == "literature_page":
            schema = _PAGE
        elif role in {"literature_table", "literature_ordered", "literature_targeted"}:
            selection = ({"anyOf": [_TABLE, _WINDOW]} if role == "literature_table" else _WINDOW if role == "literature_ordered"
                else obj({"spans": {"type": "array", "minItems": 1, "items": _WINDOW}}))
            schema = obj({"version": {"const": "reading_assignment_v1"},
                          "page": _PAGE, "selection": selection})
        else:
            version, field = {
                "literature": ("literature_assignment_v1", "source_refs"),
                "literature_strategy": ("strategy_assignment_v1", "prior_search_refs"),
                "literature_search": ("search_assignment_v1", "search_result_refs"),
            }[role]
            schema = obj({"version": {"const": version}, "question_context_refs": _REFERENCES,
                          field: _REFERENCES})
        return deepcopy(schema)

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ("tool", "reason", "child", "wait", "redeliver_report")

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        # These are available branches, never automatically instantiated work.
        return _CHILDREN[parent.role]

    def child_roles(self, role):
        self._role(role)
        return _CHILDREN[role]

    def _require(self, reference, scope, namespace=None):
        if not self.services.reference_in_scope(reference, scope, namespace):
            raise ContractError("literature_reference_unavailable", detail={
                "reference": reference, "namespace": namespace})
        return self.services.read_record(reference)

    @staticmethod
    def _artifact(source, representation):
        if representation == "original":
            return source["artifact_ref"]
        if representation == "text":
            # Match the existing source.read fallback exactly.
            return source.get("text_ref") or source["artifact_ref"]
        return source.get(representation + "_ref")

    def _validate_page(self, page, scope):
        source = self._require(page["source_ref"], scope, "source")
        if self._artifact(source, page["representation"]) != page["artifact_ref"]:
            raise ContractError("literature_source_artifact_mismatch", detail={
                "reference": page["source_ref"], "artifact_ref": page["artifact_ref"],
                "representation": page["representation"]})
        self._require(page["artifact_ref"], scope, "artifact")
        for reference in (*page["question_context_refs"], *page["prior_delivery_refs"]):
            self._require(reference, scope)
        # prior_delivery_refs are provenance only. They do not assert reading
        # coverage, successful extraction or understanding.

    def _validate_assignment(self, role, assignment, scope):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema(role))
        if role in {"literature_page",
                "literature_table", "literature_ordered", "literature_targeted"}:
            page = value if role == "literature_page" else value["page"]
            self._validate_page(page, scope)
            if role != "literature_page":
                selected = value["selection"]
                windows = selected["spans"] if role == "literature_targeted" else [selected]
                for window in windows:
                    if window["source_ref"] != page["source_ref"]:
                        raise ContractError("literature_reading_source_mismatch")
                    if "representation" in window and window["representation"] != page["representation"]:
                        raise ContractError("literature_reading_representation_mismatch")
                    if "representation" in window:
                        artifact = self.services.read_record(page["artifact_ref"])
                        if window["offset"] > artifact["size"]:
                            raise ContractError("source_offset_out_of_bounds")
        else:
            for field, references in value.items():
                if field.endswith("_refs"):
                    for reference in references:
                        self._require(reference, scope, None if field == "question_context_refs" else "source")
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        # Common composition validates scope containment, ownership, the
        # original form and the operation identity. Never replace them here.
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        value = self._validate_assignment(role, selection, scope)
        if parent.role == "literature_page" and role in _CHILDREN["literature_page"]:
            original = self._validate_assignment(parent.role, parent.assignment, parent.scope)
            if not self._within_source(value["page"]["source_ref"], original["source_ref"], scope):
                raise ContractError("literature_reading_outside_assigned_source")
        return value

    def instructions(self, context):
        self._role(context.role)
        return (_ROLE_INSTRUCTIONS[context.role] + "\n"
            "This is an iterative scientific investigation in the shared Episode loop. "
            "Earlier outcomes and admitted child forms inform later choices; no child order, "
            "reading quota or complete-document requirement is prescribed. A one-off search/read "
            "is an ordinary tool. A supplied reading selector is context, not an automatically "
            "executed action. Preserve the source's actual subject, experimental conditions, "
            "representation, version and UTF-8 byte anchors. Distinguish source claims from "
            "their applicability to the fixed target. Negative findings and qualifications can "
            "advance the investigation. Commit interpretations with the common reasoning action "
            "and update only the parent's declared typed form in that same work call. "
            "Navigation, byte coverage and repeated reading earn no scientific credit by themselves. "
            "The configured controller owns continuation; this binding has no stop rule.")

    def decision_context(self, context, current_view):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope)
        page = (assignment if context.role == "literature_page" else assignment.get("page"))
        sources = ([page["source_ref"]] if page else assignment.get("source_refs", []))
        custody = []
        for reference in sources:
            source = self._require(reference, context.scope, "source")
            custody.append({"source_ref": reference, **{key: source.get(key) for key in
                ("version", "artifact_ref", "text_ref", "stdout_ref", "stderr_ref", "parent_source_refs")}})
        return {"literature_assignment": assignment, "literature_source_custody": custody,
            "own_literature_outcomes": plain(self.services.own_outcomes(context.episode_id,
                tools=(*_ACQUISITION_TOOLS, *_READ_TOOLS), offset=0, limit=self.outcome_page_size)),
            "literature_history_meaning": "Own outcome metadata only. Read exact previous outcomes through episode.history. Source delivery does not establish understanding, absence or resolved science."}

    def catalog(self, context):
        self._role(context.role)
        available = self.services.tool_catalog(context.scope)
        entries = ([{"name": name, **entry} for name, entry in available.items()]
                   if isinstance(available, Mapping) else list(available))
        allowed = set(_ACCESS_TOOLS)
        if context.role in {"literature", "literature_strategy", "literature_search"}:
            allowed.update(_ACQUISITION_TOOLS)
        result = []
        for entry in entries:
            if entry["name"] not in allowed:
                continue
            entry = deepcopy(plain(entry))
            if entry["name"] == "public.ncbi.search":
                entry["input_schema"]["properties"]["database"] = {"enum": ["pubmed"]}
            if entry["name"] == "execution.estimate":
                branches = [branch for branch in entry["input_schema"].get("anyOf", ())
                    if branch.get("properties", {}).get("tool", {}).get("const") in {
                        "source.xlsx.sheets", "source.xlsx.rows"}]
                if not branches:
                    continue
                entry["input_schema"] = {"anyOf": branches}
            result.append(entry)
        return result

    def _within_source(self, reference, root, scope):
        pending, seen = [reference], set()
        while pending:
            current = pending.pop()
            if current == root:
                return True
            if current in seen:
                continue
            seen.add(current)
            source = self._require(current, scope, "source")
            pending.extend(source.get("parent_source_refs", ()))
        return False

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope)
        entries = {entry["name"]: entry for entry in self.catalog(context)}
        if tool_name not in entries:
            raise ContractError("tool_not_available_to_literature_role")
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]["input_schema"])
        page = assignment if context.role == "literature_page" else assignment.get("page")
        if page:
            selected_arguments = arguments["arguments"] if tool_name == "execution.estimate" else arguments
            source_ref = selected_arguments.get("source_ref")
            if tool_name == "source.archive.extract":
                member = self._require(arguments["member_ref"], context.scope, "archive_member")
                source_ref = member["source_ref"]
            if source_ref is not None and not self._within_source(source_ref, page["source_ref"], context.scope):
                raise ContractError("literature_reading_outside_assigned_source")
            if (context.role == "literature_table" and tool_name == "source.xlsx.rows"
                    and "sheet_key" in assignment["selection"]):
                if arguments["sheet_key"] != assignment["selection"]["sheet_key"]:
                    raise ContractError("literature_table_sheet_mismatch")
        return arguments

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            # The common source records this actual failed own attempt. It
            # supplies feedback for another selected action, never a completed
            # scientific observation or an automatic retry.
            return {"status": "invalid", "operation_ref": identity("operation", {
                "key": operation_key, "name": tool_name, "arguments": plain(arguments)}),
                "record_refs": [], "changed_record_refs": [], "result": None,
                "feedback": {"category": "arguments_or_reference", "code": str(error),
                    **({"detail": error.detail} if error.detail else {})}}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope,
                                              operation_key=operation_key)
        return await outcome if inspect.isawaitable(outcome) else outcome

    def fact_sources(self, role):
        self._role(role)
        # Common scientific facts already expose actual changed assessments,
        # observations, annotation accounts and report-basis references.
        return {}

    def facts(self, context, completion_snapshot):
        self._role(context.role)
        return {}

    def resolve(self, context, reference, namespace):
        self._role(context.role)
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope)
        validate_form(form, original_schema,
                      lambda reference, namespace: self.resolve(context, reference, namespace))

    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        return self.services.scientific_credit(context, receiver_selection)


__all__ = ["LiteratureEpisodes", "ROLES", "VERSION"]
