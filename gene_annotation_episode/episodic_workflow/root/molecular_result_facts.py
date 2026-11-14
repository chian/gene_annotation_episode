"""Original molecular result responsibility: molecular_result_facts."""
from __future__ import annotations
import json
from .communication import validate_form
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .episode_receipts import RECEIVED_REPORT_PREFIX_VERSION, _validate_report_prefix
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_control_records import read_control, same
from .molecular_result_actions import unique
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import FACT_SOURCES, SAVED_SOURCE, require, select_molecular_sequence_return_facts, validate_molecular_sequence_fact_values
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_result_contracts as supplied
from .molecular_result_values import PREFIX, PUBLIC_VERSION, VERSION, _facts

class MolecularResultFacts:

    def own_fact_groups(self, context, *, verify_artifacts):
        require(type(verify_artifacts) is bool and self.applies(context)); groups = _facts()
        for receipt in self._completed(context):
            if verify_artifacts:
                for row in receipt["source_files"].values():
                    if row["file"] is not None: retained_native_file(self.store, row["file"])
            for source in FACT_SOURCES: groups[source].extend(receipt["facts"][source])
        return {source: unique(rows) for source, rows in groups.items()}

    def facts(self, context):
        groups = self.own_fact_groups(context, verify_artifacts=False)
        if plain(context.assignment).get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            return {**groups, "calculation_delivery_complete": self.calculation_completion(context) is not None}
        return {**groups, "execution_completed": self.completion(context) is not None}

    def _values(self, form, schema):
        validate_form(plain(form), plain(schema), lambda *_: True)
        groups = {}
        for name, node in plain(schema)["properties"].items():
            source = node.get("x-source")
            if source in FACT_SOURCES:
                values = validate_molecular_sequence_fact_values(source, plain(form)[name])
                require(source not in groups or same(groups[source], values)); groups[source] = values
        return groups

    def _received(self, context, sources, *, allowed=None):
        self.authenticate(context); require(context.role in ("annotation", "scientific_process"))
        groups = {source: [] for source in sources}; witnesses = []
        attempts = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index", (self.run_id, context.episode_id)).fetchall()
        actual = []
        for attempt in attempts:
            witness = {k: attempt[k] for k in ("decision_index", "delivery_ref", "child_episode_id")}
            witness.update(contract_sha256=digest(json.loads(attempt["contract"])), form_sha256=digest(json.loads(attempt["form"])))
            actual.append(witness)
        if allowed is not None: require(all(any(same(w, current) for current in actual) for w in allowed), "molecular_sequence_frozen_report_prefix_conflict")
        for attempt, witness in zip(attempts, actual):
            if allowed is not None and not any(same(witness, w) for w in allowed): continue
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not any(node.get("x-source") in sources for node in schema.get("properties", {}).values()): continue
            child, form, schema = self._attempt(context, attempt["decision_index"])
            values = self._values(form, schema)
            if not any(source in values for source in sources): continue
            frozen = json.loads(self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?", (self.run_id, child.episode_id)).fetchone()[0])
            if self.applies(child): expected = self.own_fact_groups(child, verify_artifacts=False)
            else:
                require(PREFIX in frozen, "molecular_sequence_frozen_report_prefix_required")
                expected, _ = self._received(child, sources, allowed=_validate_report_prefix(frozen[PREFIX])["attempts"])
            for source in sources:
                for value in values.get(source, []):
                    require(any(same(value, item) for item in expected.get(source, [])), "molecular_sequence_returned_value_conflict")
                    groups[source].append(value)
            witnesses.append(witness)
        return {source: unique(values) for source, values in groups.items()}, witnesses

    def received_facts(self, context, schema):
        sources = tuple(select_molecular_sequence_return_facts(_facts(), schema=plain(schema)))
        groups = self.own_fact_groups(context, verify_artifacts=False) if self.applies(context) else self._received(context, sources)[0]
        return select_molecular_sequence_return_facts(groups, schema=plain(schema))

    def facts_for_closure(self, context, schema):
        if self.applies(context): return self.received_facts(context, schema)
        sources = tuple(select_molecular_sequence_return_facts(_facts(), schema=plain(schema)))
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)).fetchone()
        allowed = None if frozen is None else _validate_report_prefix(json.loads(frozen[0])[PREFIX])["attempts"]
        groups, witnesses = self._received(context, sources, allowed=allowed)
        return {**select_molecular_sequence_return_facts(groups, schema=plain(schema)), PREFIX: _validate_report_prefix({"version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": witnesses})}

    def validate_received_report(self, context, form, schema):
        values = self._values(form, schema)
        if not values: return
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)).fetchone()
        if self.applies(context): expected = self.own_fact_groups(context, verify_artifacts=frozen is None)
        else:
            allowed = None if frozen is None else _validate_report_prefix(json.loads(frozen[0])[PREFIX])["attempts"]
            expected = self._received(context, values, allowed=allowed)[0]
        for source, rows in values.items(): require(all(any(same(row, original) for original in expected.get(source, [])) for row in rows), "molecular_sequence_returned_value_conflict")

    def record_admission(self, context, form, schema, operation_key):
        child, actual, declared = self._attempt(context, self._admission_index(context, operation_key))
        require(same(form, actual) and same(schema, declared))
        self.validate_received_report(child, actual, declared)
        return list(dict.fromkeys(row["artifact_ref"] for row in self._values(actual, declared).get(SAVED_SOURCE, [])))

    def resolve_own(self, context, reference, namespace):
        return namespace in (None, "artifact") and self.applies(context) and any(row["artifact_ref"] == reference for row in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE])

    def resolve_received(self, context, reference, namespace):
        return namespace in (None, "artifact") and context.role in ("annotation", "scientific_process") and any(row["artifact_ref"] == reference for row in self._received(context, (SAVED_SOURCE,))[0][SAVED_SOURCE])

    def owns_reference(self, reference):
        if type(reference) is not str or not reference.startswith("artifact_"): return False
        for row in self.db.execute("SELECT episode_id,decision_index,action,result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL", (self.run_id,)):
            value = json.loads(row["result"])
            if value.get("result", {}).get("version") not in (PUBLIC_VERSION, "molecular_sequence_public_result_v2"): continue
            receipt = read_control(self.action_directory(row["episode_id"], f'{self.run_id}:{row["episode_id"]}:{row["decision_index"]}') / "receipt.json")
            require(receipt is not None)
            if value["result"]["version"] == "molecular_sequence_public_result_v2":
                context = self.context(row["episode_id"])
                action = json.loads(row["action"])
                intent = self.intent(context, None, action.get("tool"), action.get("arguments"),
                    f'{self.run_id}:{row["episode_id"]}:{row["decision_index"]}')
                receipt = self._validate_supplied_receipt(receipt, intent)
                require(same(value, self._outcome(receipt)), "molecular_sequence_completed_action_conflict")
                if self._supplied_produced_component(receipt) == reference: return True
                continue
            if any(source["file"] is not None and source["file"]["artifact_ref"] == reference for source in receipt["source_files"].values()): return True
        return False

    def credit_view(self, context, receiver_selection):
        if plain(context.assignment).get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            # This reports acquisition only. Investigation value and the
            # configured controller's credit/continuation are not estimated.
            return {"new_acquired_record_count": 0, "new_handoff_count": 0,
                "operational_credit_binding": {"version": supplied.CALCULATION_RECORD_VERSION,
                    "basis": "supplied_measurements_without_native_acquisition"}}
        # No authenticated original scientific producer hook exists here yet.
        # This says nothing about investigation value or parent scientific yield.
        return {"credit": 0, "operational_credit": 0, "new_acquired_record_count": 0, "new_handoff_count": 0,
            "operational_credit_binding": {"version": VERSION, "basis": "no_verified_original_molecular_acquisition"}}

    def completion(self, context):
        if plain(context.assignment).get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            return None  # No invented original practical/native receipt.
        for receipt in self._completed(context):
            if receipt["delivery_complete"]:
                return dict(version="practical_completion_v1", run_id=self.run_id, episode_id=context.episode_id,
                    assignment_sha256=digest(plain(context.assignment)), endpoint="usable_handoff", operation_key=receipt["intent"]["operation_key"],
                    receipt_sha256=digest(receipt), validation_keys=["selected_molecular_typed_delivery"])
        return None
