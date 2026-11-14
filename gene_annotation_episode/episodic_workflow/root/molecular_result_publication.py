"""Original molecular result responsibility: molecular_result_publication."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_control_records import read_control, same
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import require
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_result_contracts as supplied
from gene_annotation_episode.domain import identity as record_identity
from .molecular_result_values import _json

class MolecularResultPublication:

    def publish_ordinary_molecular_sequence(self, action, *, custody):
        """Publish through the real registry; grant only the resulting Source."""
        self.require_action(action)
        operation = action.intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        custody = self._validate_ordinary_molecular_sequence_custody(custody, action.intent)
        require(read_control(action.directory / "ordinary-custody.json") == custody)
        registry = getattr(self.owner, "tool_registry", None)
        require(registry is not None and registry.store is self.store and callable(getattr(registry, "_put", None)),
            "molecular_sequence_ordinary_registry_port_required")
        capsule = self.capture_control(action, "ordinary-capsule.json", custody, custody["version"])
        record = self._ordinary_molecular_sequence_source_record(custody, capsule)
        source = registry._put("source", record, origin="tool")
        require(source["id"] == record_identity("source", {"origin": "tool", "record": record}))
        public = supplied.validate_ordinary_molecular_sequence_return(dict(source_ref=source["id"], **supplied.ordinary_molecular_sequence_packet(custody, operation=operation)), operation=operation)
        return public, [source["id"]]

    def read_ordinary_molecular_sequence_publication(self, context, source_ref, *, operation, read_received=None, pending_operation_key=None):
        """Authenticate real action metadata before opening private publication bytes."""
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        with self.store.read_snapshot():
            return self._read_ordinary_molecular_sequence_publication(context, source_ref, operation=operation,
                read_received=read_received, pending_operation_key=pending_operation_key)

    def _read_ordinary_molecular_sequence_publication(self, context, source_ref, *, operation, read_received, pending_operation_key, _seen=()):
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        require(source_ref not in _seen, "molecular_sequence_ordinary_source_cycle")
        if _seen and context.run_id != self.run_id:
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix="molecular_sequence_ordinary_").authenticate(context)
        else:
            self.authenticate(context)
        source = self.store.get(source_ref)
        require(source.get("record_type") == "source" and source.get("origin") == "tool"
            and source.get("provider") == operation
            and source.get("version") == profile['source_version'],
            "molecular_sequence_ordinary_source_required")
        payload = {key: value for key, value in source.items() if key not in ("id", "record_type", "origin")}
        require(source_ref == record_identity("source", {"origin": "tool", "record": payload}),
            "molecular_sequence_ordinary_source_identity_conflict")
        rows = self.db.execute("""SELECT operation.*, action.run_id AS producer_run_id,
            action.episode_id AS producer_episode_id, action.decision_index AS producer_decision_index,
            action.action AS selected_action, action.result AS recorded_outcome
            FROM tool_operations operation JOIN runtime_actions action
              ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index
            WHERE operation.name=? AND json_extract(operation.result,'$.result.source_ref')=?
              AND (json_extract(operation.arguments,'$.mode') IS NULL
                   OR json_extract(operation.arguments,'$.mode')='calculate_saved'
                   OR (operation.name='align_sequences' AND json_extract(operation.arguments,'$.mode')='run_native'))
              AND json_extract(operation.result,'$.status') IN ('completed','partial')""",
            (operation, source_ref)).fetchall()
        require(len(rows) == 1, "molecular_sequence_ordinary_producer_required")
        row = rows[0]
        records = EpisodeReturnRecords(self.store, row["producer_run_id"], failure_prefix="molecular_sequence_ordinary_")
        producer = records.context(row["producer_episode_id"])
        arguments, outcome = _json(row["arguments"].encode()), _json(row["result"].encode())
        intent = self._ordinary_context_intent(producer, arguments, row["operation_key"], operation=operation)
        require(row["scope"] == canonical(plain(producer.scope))
            and same(_json(row["selected_action"].encode()), dict(kind="tool", tool=operation, arguments=arguments))
            and row["id"] == record_identity("operation", {"key": row["operation_key"], "name": operation, "arguments": arguments})
            and outcome.get("operation_ref") == row["id"] and outcome.get("record_refs") == [source_ref],
            "molecular_sequence_ordinary_producer_conflict")
        pending = row["recorded_outcome"] is None
        if pending:
            require(pending_operation_key == row["operation_key"] and context.run_id == producer.run_id
                and context.episode_id == producer.episode_id, "molecular_sequence_ordinary_completed_action_required")
        else:
            actual = _json(row["recorded_outcome"].encode())
            require({key: value for key, value in actual.items() if key != "pending_work_after_action"} == outcome,
                "molecular_sequence_ordinary_outcome_conflict")
        if context.episode_id != producer.episode_id or context.run_id != producer.run_id:
            require(callable(read_received), "molecular_sequence_ordinary_source_admission_required")
        if read_received is not None:
            receipts = EpisodeReceipts.__new__(EpisodeReceipts)
            receipts.store, receipts.db, receipts.run_id = self.store, self.db, context.run_id
            require(source_ref in set(receipts.known(context.episode_id)),
                "molecular_sequence_ordinary_source_not_received")
            admitted = read_received(context, source_ref, "source", source_metadata_only=True)
            require(admitted["failure"] is None and admitted["input"]["witness"]["record"] == source,
                "molecular_sequence_ordinary_source_not_received")
        self.store.validate_scope(plain(producer.scope), parent_scope=plain(context.scope))
        # Source/control IDs and the complete committed producer join above
        # precede every private artifact read below.
        from gene_annotation_episode.molecular_measurement_tools import _publication_bytes
        custody = self._validate_ordinary_molecular_sequence_custody(_json(_publication_bytes(self.store, source["request_ref"])), intent,
            _seen=(*_seen, source_ref))
        capsule = dict(artifact_ref=source["request_ref"], sha256=source["request_ref"][9:],
            size_bytes=self.store.get(source["request_ref"])["size"], format=custody["version"])
        require(payload == self._ordinary_molecular_sequence_source_record(custody, capsule), "molecular_sequence_ordinary_source_control_conflict")
        packet = supplied.validate_ordinary_molecular_sequence_packet(_json(_publication_bytes(self.store, source["artifact_ref"])), operation=operation)
        public = supplied.validate_ordinary_molecular_sequence_return(dict(source_ref=source_ref, **packet), operation=operation)
        require(public == outcome["result"] and packet == supplied.ordinary_molecular_sequence_packet(custody, operation=operation),
            "molecular_sequence_ordinary_saved_values_conflict")
        return dict(admission_kind="source_only", source=source, stored=public, control=custody, grading_ref=None)

    def _ordinary_recorded_operation(self, intent):
        """One current-action/ToolOperation association for execution and facts."""
        operation = intent["tool_name"]
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        selected = self._selected(intent)
        row = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (intent["operation_key"],)).fetchone()
        if row is None:
            return None
        require(row["name"] == operation
            and row["arguments"] == canonical(intent["arguments"]) and row["scope"] == canonical(intent["scope"])
            and row["id"] == record_identity("operation", {"key": intent["operation_key"],
                "name": operation, "arguments": intent["arguments"]}),
            "molecular_sequence_ordinary_action_conflict")
        outcome = _json(row["result"].encode())
        require(outcome.get("operation_ref") == row["id"], "molecular_sequence_ordinary_action_conflict")
        if selected["result"] is not None:
            actual = _json(selected["result"].encode())
            require(same({key: value for key, value in actual.items() if key != "pending_work_after_action"}, outcome),
                "molecular_sequence_ordinary_action_conflict")
        return outcome

    def read_ordinary_molecular_sequence_action_result(self, context, arguments, operation_key, *, operation, read_received=None):
        """Authenticate this recorded action separately from its Source producer."""
        profile = supplied.ordinary_molecular_sequence_profile(operation)
        intent = self._ordinary_context_intent(context, arguments, operation_key, operation=operation)
        outcome = self._ordinary_recorded_operation(intent)
        require(outcome is not None and outcome.get("status") in ("completed", "partial"),
            "molecular_sequence_ordinary_action_conflict")
        if arguments.get("mode") in ("read_stored", "calculate_saved"):
            self._ordinary_original_source_admission(context, arguments["result_ref"], operation_key)
        public = supplied.validate_ordinary_molecular_sequence_return(outcome["result"], operation=operation)
        require(outcome.get("record_refs") == [public["source_ref"]], "molecular_sequence_ordinary_action_conflict")
        publication = self.read_ordinary_molecular_sequence_publication(context, public["source_ref"], operation=operation,
            read_received=read_received if arguments.get("mode") == "read_stored" else None,
            pending_operation_key=operation_key)
        if arguments.get("mode") == "read_stored":
            receipt = read_control(self.action_directory(context.episode_id, operation_key) / "ordinary-read-receipt.json")
            require(type(receipt) is dict and set(receipt) == {"version", "intent", "source_sha256", "public"}
                and receipt["version"] == profile['read_receipt_version'] and same(receipt["intent"], intent)
                and arguments["result_ref"] == public["source_ref"]
                and receipt["source_sha256"] == digest(publication["source"])
                and same(receipt["public"], public)
                and same(self.project_ordinary_molecular_sequence_view(publication, rows=arguments["rows"]), public),
                "molecular_sequence_ordinary_saved_view_conflict")
            return public
        require(publication["control"]["request"]["invocation"]["operation_key"] == operation_key
            and same(publication["stored"], public), "molecular_sequence_ordinary_action_source_conflict")
        return public
