"""Original explicit reference cells and authenticated retained-reference access."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import SAVED_SOURCE, FACT_SOURCES, GENERIC_SOURCE
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import _boundary, requested_sources, _sequences, _references
from gene_annotation_episode.episodic_workflow.root.communication import plain
import json


class ProteinStructureReturnVisibility:
    @staticmethod
    def _explicit_refs(form, schema):
        """Only schema-declared reference cells; never arbitrary *_ref keys."""
        references, pending = [], [(form, schema)]
        while pending:
            value, node = pending.pop()
            if node.get("x-source") in FACT_SOURCES:
                continue
            if isinstance(value, dict):
                pending.extend((value[key], child) for key, child in reversed(list(node.get("properties", {}).items()))
                               if key in value)
            elif isinstance(value, list):
                pending.extend((item, node.get("items", {})) for item in reversed(value))
            elif node.get("format") == "reference" and isinstance(value, str):
                references.append(value)
        return references

    def _independent_reference(self, context, reference, active=()):
        self._require(context.episode_id not in active)
        if reference not in self._known(context):
            return False
        for current, allowed, before, enabled in self._levels(context):
            if enabled:
                rows = self.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
                    "AND episode_id=? AND result IS NOT NULL ORDER BY decision_index", (self.run_id, current.episode_id))
                for row in rows:
                    if before is not None and row["decision_index"] >= before:
                        continue
                    action, outcome = json.loads(row["action"]), json.loads(row["result"])
                    if (action.get("kind") == "tool" and action.get("tool") != "execution.results.collect"
                            and outcome.get("status") in {"completed", "partial"}
                            and reference in outcome.get("record_refs", [])):
                        return True
            for attempt in self._attempts_at(current, allowed, before, enabled):
                child, form, schema = self._attempt(current, attempt["decision_index"])
                self._values(form, schema)
                if reference not in self._explicit_refs(form, schema):
                    continue
                if child.role == "results" and self.store.get(reference)["record_type"] == "source":
                    # Host verifies the actual original actions even when the
                    # parent's form requested only the generic source handle.
                    self._own(child)
                    rows = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
                        "AND result IS NOT NULL", (self.run_id, child.episode_id))
                    for row in rows:
                        action, outcome = json.loads(row["action"]), json.loads(row["result"])
                        if (action == {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
                                and outcome.get("status") == "completed" and reference in outcome.get("record_refs", [])):
                            return True
                if self._independent_reference(child, reference, (*active, context.episode_id)):
                    return True
        return False

    def _own_result_source(self, context, reference, schema):
        if not any(node.get("x-source") == GENERIC_SOURCE for node in schema.get("properties", {}).values()):
            return False
        if self.store.get(reference)["record_type"] != "source":
            return False
        # _own already authenticated each original collect through the host.
        rows = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND result IS NOT NULL", (self.run_id, context.episode_id))
        for row in rows:
            action, outcome = json.loads(row["action"]), json.loads(row["result"])
            if (action == {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
                    and outcome.get("status") == "completed" and reference in outcome.get("record_refs", [])):
                return True
        return False

    @_boundary
    def retained_reference_access(self, context, reference, namespace):
        self.authenticate(context, allow_unsaved=True)
        if not self.results.owns_reference(reference):
            return None
        if namespace not in {None, "artifact", "source", "reference", "observation", "execution_result",
                              "subject", "execution_handoff", "record"}:
            return False
        groups, own_source = self._received(context), False
        if context.role == "results":
            # A result episode can expose its selected own output. This does
            # not admit its own output as a frozen operand of its assignment.
            schema = plain(context.request)["report_contract"]["measurements"]["schema"]
            requested = requested_sources(schema)
            own = {source: rows if source in requested else [] for source, rows in self._own(context).items()}
            groups = {source: [*groups[source], *own[source]] for source in FACT_SOURCES}
            own_source = self._own_result_source(context, reference, schema)
        allowed = reference in _references(groups) or own_source or self._independent_reference(context, reference)
        if not allowed:
            return False
        record = self.store.get(reference)
        if namespace in {"artifact", "source", "reference", "observation"}:
            return record["record_type"] == namespace
        if namespace == "subject":
            return record["record_type"] in {"input", "reference", "feature", "product"}
        if namespace == "execution_result":
            return record["record_type"] == "source" and record.get("version") == "native_protein_structure_bundle_v1"
        if namespace == "execution_handoff":
            descriptors = [*list(_sequences(groups)), *groups[SAVED_SOURCE]]
            return any(value["custody"]["handoff_ref"] == reference for value in descriptors)
        return True

    @_boundary
    def resolve_received(self, context, reference, namespace):
        # Semantic locators remain locators. D1 exposes no generic read namespace
        # for calculation ids, projection ids or receipt keys.
        if (isinstance(reference, str) and reference.startswith("protein_structure_result_receipt:")) \
                or isinstance(namespace, str) and namespace.startswith("protein_structure_"):
            return False
        return self.retained_reference_access(context, reference, namespace)

