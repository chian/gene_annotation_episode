"""Original AppService publication and typed-return custody repository.

Historical owner checks describe authenticated saved forms. The private caller
supplies recursive received-fact access; this repository selects no live task.
"""
from __future__ import annotations
import json
from ..communication import plain, validate_form
from ..episode_return_records import EpisodeReturnRecords
from .bvbrc_application_facts import FACT_SOURCE, IDENTIFIER_NAMESPACE, _PREFIX, project_application_facts, validate_application_rows


class BVBRCApplicationReturnRecords(EpisodeReturnRecords):
    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix=_PREFIX)
        self.api = execution

    def _authenticate(self, context):
        self.authenticate(context, allow_unsaved=True)
        self.api.appservice.custody.authenticate(context, allow_unsaved=True)
        self._require(context.role == context.path[-1][0], "publication_owner_conflict")

    def _original_invocation(self, context, body):
        self._require(body.get("run_id") == self.run_id and body.get("episode_id") == context.episode_id
            and self._equal(body.get("scope"), context.scope) and self._equal(body.get("assignment"), context.assignment)
            and self._equal(body["publication_inputs"].get("selector"), context.assignment.get("selector")), "publication_owner_conflict")

    def _possessed_sources(self, context, rows):
        for reference in dict.fromkeys(row["source_ref"] for row in rows):
            self._require(self.store.get(reference).get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)

    def _attempt(self, context, index):
        self._authenticate(context)
        child, form, schema = self.api.appservice.custody._attempt(context, index)
        validate_form(form, schema, lambda *_: True)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original_index = int(child.path[-1][1].removeprefix("child_"))
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        original = plain(child.request)["report_contract"]
        if selected.get("kind") in {"episode_child", "child", "job_child"}:
            self._require(self._equal(selected.get("scope"), child.scope)
                and selected.get("purpose") == original["decision"], "original_commission_conflict")
        if self._equal(schema, original["measurements"]["schema"]):
            frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen["form"] is not None
                and self._equal(json.loads(frozen["form"]), form), "frozen_form_conflict")
        return child, form, schema

    def _values(self, form, schema):
        validate_form(form, schema, lambda *_: True)
        selected = None
        for name, node in schema["properties"].items():
            if node.get("x-source") == FACT_SOURCE:
                rows = validate_application_rows(form[name])
                self._require(selected is None or self._equal(selected, rows), "returned_facts_conflict")
                selected = rows
        return {FACT_SOURCE: [] if selected is None else selected}

    def _frozen(self, context, values):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            frozen = json.loads(row["facts"])
            self._require(all(key in frozen and self._equal(frozen[key], rows) for key, rows in values.items()), "frozen_facts_conflict")

    def _original_publication(self, context, reference):
        publications = self.api.appservice.publications
        body = publications.read(reference, context.scope, episode_id=context.episode_id)
        self._original_invocation(context, body)
        saved = body["publication"]["adapter_result"]
        values = [None if saved[name + "_content"] is None else publications.read_content_source(
            saved[name + "_content"]["source_ref"], context.scope) for name in ("sheet", "components")]
        return project_application_facts(body, sheet=values[0], components=values[1])

    def _validate_historical(self, context, form, schema, *, received_facts):
        self._authenticate(context)
        values = self._values(form, schema)
        self._frozen(context, values)
        if context.role == "results":
            expected = []
            for reference in dict.fromkeys(row["source_ref"] for row in values[FACT_SOURCE]):
                expected.extend(self._original_publication(context, reference)[FACT_SOURCE])
            self._require(self._equal(values[FACT_SOURCE], expected), "returned_facts_conflict")
        elif context.role in {"annotation", "perturbation_evidence"}:
            received = received_facts(context, schema)
            self._require(all(any(self._equal(row, original) for original in received[FACT_SOURCE])
                for row in values[FACT_SOURCE]), "returned_facts_conflict")
        else:
            raise ValueError(_PREFIX + "unsupported_return_owner")
        self._possessed_sources(context, values[FACT_SOURCE])

    def _resolve(self, context, rows, reference, namespace):
        if namespace in {None, "source", "execution_result"} and any(row["source_ref"] == reference for row in rows):
            self._possessed_sources(context, [row for row in rows if row["source_ref"] == reference])
            return True
        if namespace == IDENTIFIER_NAMESPACE:
            return any(row["field"] == reference for row in rows)
        return None

