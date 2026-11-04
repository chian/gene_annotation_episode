"""Read only the original scientific relationships and admitted result fields.

This adapter has no execution or credit authority. It neither installs tables
nor expands a child history, and returns detached finite JSON records only.
"""
from __future__ import annotations

import json
import re

from method_loop import EpisodeGoal
from method_loop.identities import EpisodeRef, normalize_structural_path

from .communication import plain
from .domain import identity
from .scientific_process_records import (scientific_digest, scientific_invocation_ref,
    validate_child_selection, validate_revision_origin, validate_selection,
    selection_fields, LEGACY_SELECTION_VERSION)
from .scientific_process_reports import credit_binding_ref, validate_process_result


NAMESPACES = frozenset({"scientific_invocation", "scientific_preparation",
    "scientific_process_library", "scientific_option_digest", "scientific_credit_binding"})
_OPERATION = re.compile(r"operation_[0-9a-f]{24}\Z")


def _detached(value):
    # The existing canonicalizer rejects nonfinite numbers and non-JSON values.
    from method_loop.durable import canonical
    return json.loads(canonical(plain(value)))


def _load(value):
    return None if value is None else json.loads(value)


_EPISODE_FIELDS = """path,
    json_extract(request,'$.goal') AS goal,
    json_extract(request,'$.message.scope') AS scope,
    json_extract(request,'$.message.scientific_invocation_ref') AS invocation_ref,
    json_extract(request,'$.message.episode_assignment.selection') AS selection,
    json_extract(request,'$.message.scientific_process.selection') AS filled_selection,
    json_extract(request,'$.message.episode_assignment.revision_origin') AS revision_origin"""


class ScientificProcessProvenance:
    def __init__(self, store, journal, *, library, tool_library=None):
        if journal.db is not store.db:
            raise ValueError("scientific_provenance_requires_same_store_connection")
        if not isinstance(journal.run_id, str) or not journal.run_id:
            raise ValueError("scientific_provenance_run_required")
        self.store, self.journal, self.library = store, journal, library
        self.tool_library = tool_library

    def _saved(self, path, *, request=None):
        episode_id = EpisodeRef(self.journal.run_id, path).episode_id
        fields, parameters = _EPISODE_FIELDS, []
        if request is not None:
            # Compare the complete original request inside SQLite. Key order
            # is immaterial; no saved request/model context is hydrated here.
            fields += """, NOT EXISTS (
                SELECT fullkey,type,atom FROM json_tree(request)
                EXCEPT SELECT fullkey,type,atom FROM json_tree(?))
                AND NOT EXISTS (
                SELECT fullkey,type,atom FROM json_tree(?)
                EXCEPT SELECT fullkey,type,atom FROM json_tree(request)) AS request_matches"""
            encoded = json.dumps(request, allow_nan=False)
            parameters.extend((encoded, encoded))
        row = self.store.db.execute("SELECT " + fields +
            " FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (*parameters, self.journal.run_id, episode_id)).fetchone()
        if row is None:
            return None
        value = {name: _load(row[name]) for name in
                 ("path", "goal", "scope", "selection", "filled_selection", "revision_origin")}
        value.update(episode_id=episode_id, invocation_ref=row["invocation_ref"])
        if (value["path"] != plain(path)
                or request is not None and not row["request_matches"]):
            raise ValueError("scientific_provenance_original_request_mismatch")
        EpisodeGoal.from_record(value["goal"])
        marker = value["invocation_ref"]
        if marker is not None and marker != scientific_invocation_ref(self.journal.run_id, path):
            raise ValueError("scientific_provenance_invocation_mismatch")
        if value["revision_origin"] is not None:
            value["revision_origin"] = validate_revision_origin(value["revision_origin"])
        return value

    def _parent(self, path, request, scope):
        if len(path) == 1:
            if request["goal"]["parent_goal_id"]:
                raise ValueError("scientific_provenance_parent_mismatch")
            return None
        parent = self._saved(path[:-1])
        if parent is None:
            raise ValueError("scientific_provenance_saved_parent_required")
        if (request["goal"]["parent_goal_id"] != parent["goal"]["goal_id"]
                or request["goal"]["task_context"] != parent["goal"]["task_context"]
                or self.store.validate_scope(scope, parent["scope"]) != scope):
            raise ValueError("scientific_provenance_parent_mismatch")
        return parent

    def _authenticate(self, context, *, require_saved=False):
        path = normalize_structural_path(context.path)
        request = _detached(context.request)
        scope, assignment = _detached(context.scope), _detached(context.assignment)
        if (context.run_id != self.journal.run_id or path[-1][0] != context.role
                or EpisodeRef(context.run_id, path).episode_id != context.episode_id
                or request.get("message", {}).get("scope") != scope
                or request["message"].get("episode_assignment", {}) != assignment):
            raise ValueError("scientific_provenance_context_mismatch")
        EpisodeGoal.from_record(request["goal"])
        if self.store.validate_scope(scope) != scope:
            raise ValueError("scientific_provenance_scope_mismatch")
        marker = request["message"].get("scientific_invocation_ref")
        if marker is not None and marker != scientific_invocation_ref(context.run_id, path):
            raise ValueError("scientific_provenance_invocation_mismatch")
        saved = self._saved(path, request=request)
        if require_saved and saved is None:
            raise ValueError("scientific_provenance_saved_owner_required")
        parent = self._parent(path, request, scope)
        return path, request, saved, parent

    def _selection(self, owner):
        if owner["path"][-1][0] != "scientific_process" or owner["invocation_ref"] is None:
            raise ValueError("scientific_preparation_owner_invalid")
        selection = validate_selection(owner["selection"])
        if selection != validate_selection(owner["filled_selection"]):
            raise ValueError("scientific_preparation_original_selection_mismatch")
        library_id = self.library.as_record()["library_id"]
        for name in selection_fields(selection)[:2]:
            if selection[name]["library_id"] != library_id:
                raise ValueError("scientific_preparation_library_mismatch")
            self.library.resolve(selection[name])
        if self.tool_library is not None:
            if selection['version'] == LEGACY_SELECTION_VERSION:
                self.tool_library.resolve(selection['tools'])
            else:
                self.tool_library.resolve_tool_info(selection['child_tool_info'])
        return selection

    def _preparation(self, owner, preparation_ref):
        if not isinstance(preparation_ref, str) or not _OPERATION.fullmatch(preparation_ref):
            raise ValueError("scientific_preparation_reference_invalid")
        selection = self._selection(owner)
        rows = self.store.db.execute("""SELECT decision_index,
            json_extract(action,'$.kind') AS kind,
            json_extract(action,'$.tool') AS tool,
            json_extract(action,'$.arguments') AS arguments,
            json_extract(result,'$.status') AS status,
            json_extract(result,'$.operation_ref') AS operation_ref,
            json_extract(result,'$.record_refs') AS record_refs,
            json_extract(result,'$.changed_record_refs') AS changed_record_refs,
            json_extract(result,'$.result') AS proposal,
            json_extract(result,'$.revision_origin') AS revision_origin,
            json_extract(result,'$.feedback') AS feedback
            FROM runtime_actions WHERE run_id=? AND episode_id=?
            AND json_extract(result,'$.operation_ref')=? LIMIT 2""",
            (self.journal.run_id, owner["episode_id"], preparation_ref)).fetchall()
        if len(rows) != 1:
            raise ValueError("scientific_preparation_unavailable")
        row = rows[0]
        if type(row["decision_index"]) is not int or row["decision_index"] < 0:
            raise ValueError("scientific_preparation_operation_key_invalid")
        if (row["kind"] != "tool" or row["tool"] != "process.revise"
                or row["status"] != "completed" or row["feedback"] is not None
                or _load(row["record_refs"]) != [] or _load(row["changed_record_refs"]) != []):
            raise ValueError("scientific_preparation_outcome_invalid")
        arguments = _load(row["arguments"])
        axis_field, thought_field, tools_field = selection_fields(selection)
        if not isinstance(arguments, dict) or set(arguments) != {thought_field, tools_field}:
            raise ValueError("scientific_preparation_arguments_invalid")
        proposal = validate_child_selection(_load(row["proposal"]))
        proposed_tools = arguments[tools_field]
        if selection['version'] != LEGACY_SELECTION_VERSION:
            if self.tool_library is None:
                raise ValueError('scientific_preparation_tool_library_required')
            proposed_tools = self.tool_library.resolve_tool_info(proposed_tools)
        proposed = validate_selection({'version': selection['version'],
            axis_field: selection[axis_field], thought_field: arguments[thought_field],
            tools_field: proposed_tools})
        for name in (axis_field, thought_field):
            self.library.resolve(proposed[name])
        if self.tool_library is not None and selection['version'] == LEGACY_SELECTION_VERSION:
            self.tool_library.resolve(proposed["tools"])
        origin = validate_revision_origin(_load(row["revision_origin"]))
        expected_operation = identity("operation", {
            "key": f'{self.journal.run_id}:{owner["episode_id"]}:{row["decision_index"]}',
            "name": "process.revise", "arguments": arguments})
        if (row["operation_ref"] != expected_operation
                or proposal["parent_selection_sha256"] != scientific_digest(selection)
                or proposal["selection"] != proposed
                or origin["parent_invocation_ref"] != owner["invocation_ref"]
                or origin["preparation_operation_ref"] != preparation_ref):
            raise ValueError("scientific_preparation_identity_mismatch")
        return _detached({"operation_ref": preparation_ref,
            "owner_invocation_ref": owner["invocation_ref"], "owner_selection": selection,
            "arguments": arguments, "proposal": proposal, "revision_origin": origin})

    def preparation(self, context, preparation_ref, *, owner="self"):
        if owner not in ("self", "parent"):
            raise ValueError("scientific_preparation_owner_invalid")
        with self.store.read_snapshot():
            _, _, saved, parent = self._authenticate(context, require_saved=owner == "self")
            selected_owner = saved if owner == "self" else parent
            if selected_owner is None:
                raise ValueError("scientific_preparation_saved_owner_required")
            return self._preparation(selected_owner, preparation_ref)

    def _received_results(self, episode_id):
        rows = self.store.db.execute("""SELECT
            json_extract(attempts.form, '$.' || json_quote(fields.key)) AS results,
            json_type(attempts.form, '$.' || json_quote(fields.key)) AS result_type
            FROM runtime_report_attempts attempts
            JOIN json_each(attempts.contract,'$.measurements.schema.properties') fields
            WHERE attempts.run_id=? AND attempts.parent_episode_id=?
            AND attempts.failure IS NULL AND attempts.form IS NOT NULL
            AND json_extract(fields.value,'$.x-source')='scientific_process_results'
            ORDER BY attempts.decision_index, fields.id""", (self.journal.run_id, episode_id))
        result, seen = [], {}
        for row in rows:
            if row["result_type"] != "array":
                raise ValueError("scientific_received_results_invalid")
            for item in _load(row["results"]):
                item = validate_process_result(item, library=self.library, tool_library=self.tool_library)
                reference = item["invocation_ref"]
                body_digest = scientific_digest(item)
                if reference in seen:
                    if seen[reference] != body_digest:
                        raise ValueError("scientific_process_result_conflict")
                else:
                    seen[reference] = body_digest
                    result.append(item)
        return result

    def received_results(self, context):
        with self.store.read_snapshot():
            self._authenticate(context)
            return self._received_results(context.episode_id)

    def frozen_results(self, context):
        """Read this original episode's literal closing source, without projection.

        Missing closure/source is distinct from a recorded empty array. Only the
        declared process-result position is loaded; other facts, interpretations
        and archived histories remain outside this validation port.
        """
        with self.store.read_snapshot():
            self._authenticate(context, require_saved=True)
            row = self.store.db.execute("""SELECT
                json_type(facts, '$.scientific_process_results') AS source_type,
                json_extract(facts, '$.scientific_process_results') AS results
                FROM runtime_forms WHERE run_id=? AND episode_id=?""",
                (self.journal.run_id, context.episode_id)).fetchone()
            if row is None or row["source_type"] is None:
                return None
            if row["source_type"] != "array":
                raise ValueError("scientific_frozen_results_invalid")
            return _detached(_load(row["results"]))

    def parent_invocation(self, context):
        with self.store.read_snapshot():
            _, _, _, parent = self._authenticate(context)
            return None if parent is None else parent["invocation_ref"]

    def resolve(self, context, reference, namespace, *, credit_metadata=None):
        if namespace not in NAMESPACES or not isinstance(reference, str):
            return False
        with self.store.read_snapshot():
            _, request, saved, parent = self._authenticate(context)
            if namespace == "scientific_process_library":
                return reference == self.library.as_record()["library_id"]
            if namespace == "scientific_option_digest":
                for header in self.library.headers():
                    option = header["option_ref"]
                    if reference == option["entry_sha256"]:
                        self.library.resolve(option)
                        return True
                return False
            received = self._received_results(context.episode_id)
            if namespace == "scientific_credit_binding":
                actual = credit_binding_ref(credit_metadata)
                return reference == actual or any(reference == row["credit_binding_ref"] for row in received)
            invocations = {request["message"].get("scientific_invocation_ref")}
            if parent is not None:
                invocations.add(parent["invocation_ref"])
            preparations = set()
            origin = request["message"].get("episode_assignment", {}).get("revision_origin")
            if origin is not None:
                origin = validate_revision_origin(origin)
                if parent is None:
                    raise ValueError("scientific_provenance_parent_mismatch")
                prepared = self._preparation(parent, origin["preparation_operation_ref"])
                if (prepared["revision_origin"] != origin or prepared["proposal"]["selection"]
                        != plain(context.assignment)["selection"]):
                    raise ValueError("scientific_preparation_identity_mismatch")
                preparations.add(origin["preparation_operation_ref"])
            for row in received:
                invocations.update((row["invocation_ref"], row["parent_invocation_ref"]))
                preparations.add(row["preparation_operation_ref"])
            if namespace == "scientific_invocation":
                return reference in invocations
            if reference in preparations:
                return True
            if saved is None or saved["path"][-1][0] != "scientific_process":
                return False
            try:
                self._preparation(saved, reference)
            except ValueError:
                return False
            return True


__all__ = ["ScientificProcessProvenance", "NAMESPACES"]
