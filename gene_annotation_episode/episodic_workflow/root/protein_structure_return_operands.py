"""Original received sequence, saved-sheet, alignment and transform authority."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.alignment_site_native import immutable_record
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE, SequenceUse, SavedSheetUse
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import _error, _boundary, _validate, _sequences
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinResultAuthorityRecord
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import validate_alignment_descriptor, validate_declared_transform_record, validate_saved_sheet_descriptor, validate_structure_sequence_descriptor
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical
import json
import re


class ProteinStructureReturnOperands:
    def _original(self, context, descriptor, source):
        record = self.results.read_result_authority(descriptor["custody"], scope=plain(context.scope))
        self._require(self._equal(record["custody"], descriptor["custody"]))
        candidates = list(_sequences(record["facts"])) if source == SEQUENCE_SOURCE else record["facts"][source]
        self._require(any(self._equal(descriptor, original) for original in candidates))
        return deepcopy(record)

    @_boundary
    def received_sequence_descriptors(self, context, reference_ref):
        result, seen = [], set()
        for source, row in self._deliveries(context):
            for descriptor in _sequences({source: [row]}):
                if descriptor["reference_ref"] == reference_ref and canonical(descriptor) not in seen:
                    self._original(context, descriptor, SEQUENCE_SOURCE)
                    result.append(deepcopy(descriptor))
                    seen.add(canonical(descriptor))
        return result

    @_boundary
    def authenticate_received_sequence(self, context, descriptor, *, required_use: SequenceUse
                                       ) -> ProteinResultAuthorityRecord:
        descriptor = _validate(validate_structure_sequence_descriptor, descriptor)
        if required_use not in {"sequence_align", "structure_correspondence"}:
            raise _error("invalid_schema", field="descriptor")
        self.authenticate(context, allow_unsaved=True)
        if required_use not in descriptor["allowed_uses"] or not any(self._equal(descriptor, candidate)
                for candidate in self.received_sequence_descriptors(context, descriptor["reference_ref"])):
            raise _error("sequence_not_received", field="descriptor")
        return self._original(context, descriptor, SEQUENCE_SOURCE)

    @_boundary
    def authenticate_received_saved_sheet(self, context, descriptor, *, required_use: SavedSheetUse
                                         ) -> ProteinResultAuthorityRecord:
        descriptor = _validate(validate_saved_sheet_descriptor, descriptor)
        if required_use not in {"recalculate", "select_projection", "use_transform"}:
            raise _error("invalid_schema", field="descriptor")
        self.authenticate(context, allow_unsaved=True)
        if required_use not in descriptor["allowed_uses"] or not any(self._equal(descriptor, candidate)
                for candidate in self._received(context)[SAVED_SOURCE]):
            raise _error("saved_sheet_not_received", field="descriptor")
        record = self._original(context, descriptor, SAVED_SOURCE)
        self._require(record["selector"]["return_saved_sheet"] is True
            and descriptor["allowed_uses"] == ["recalculate", "select_projection", "use_transform"]
            and self._equal(record["sheet_file"], descriptor["sheet_file"])
            and self._equal(record["original_components_file"], descriptor["original_components_file"]))
        return record

    def _completed_alignment(self, context, alignment, before):
        prefix = f"{self.run_id}:{context.episode_id}:"
        key = alignment["original_operation_key"]
        if not key.startswith(prefix) or re.fullmatch(r"0|[1-9][0-9]*", key[len(prefix):]) is None:
            return False
        index = int(key[len(prefix):])
        if before is not None and index >= before:
            return False
        row = self.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, index)).fetchone()
        if row is None or row["result"] is None:
            return False
        arguments = {"query_ref": alignment["query_reference_ref"], "reference_ref": alignment["reference_reference_ref"],
                     "molecule": "protein", "mode": alignment["mode"]}
        self._require(self._equal(json.loads(row["action"]), {"kind": "tool", "tool": "sequence.align", "arguments": arguments}))
        original = self.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        self._require(original is not None and original["name"] == "sequence.align"
            and self._equal(json.loads(original["arguments"]), arguments)
            and self._equal(json.loads(original["scope"]), context.scope))
        outcome, saved = json.loads(row["result"]), json.loads(original["result"])
        if "pending_work_after_action" in outcome:
            from .waiting import validate_pending
            validate_pending(outcome.pop("pending_work_after_action"))
        operation_ref = identity("operation", {"key": key, "name": "sequence.align", "arguments": arguments})
        self._require(self._equal(outcome, saved) and saved.get("status") == "completed"
            and original["id"] == operation_ref == saved.get("operation_ref")
            and {alignment["observation_ref"], alignment["source_ref"]} <= set(saved.get("record_refs", [])))
        return True

    def _alignment_received(self, context, alignment, active=()):
        self._require(context.episode_id not in active)
        if not {alignment["observation_ref"], alignment["source_ref"]} <= self._known(context):
            return False
        for current, allowed, before, enabled in self._levels(context):
            if enabled and self._completed_alignment(current, alignment, before):
                return True
            for attempt in self._attempts_at(current, allowed, before, enabled):
                child, form, schema = self._attempt(current, attempt["decision_index"])
                self._values(form, schema)
                if alignment["observation_ref"] in self._explicit_refs(form, schema) \
                        and self._alignment_received(child, alignment, (*active, context.episode_id)):
                    return True
        return False

    @_boundary
    def authenticate_received_alignment(self, context, alignment) -> None:
        alignment = _validate(validate_alignment_descriptor, alignment)
        self.authenticate(context, allow_unsaved=True)
        records = {}
        for key, kind in (("observation_ref", "observation"), ("source_ref", "source")):
            record = self.store.get(alignment[key])
            if record["record_type"] != kind:
                raise _error("conflicting_identity", field="alignment")
            try:
                immutable_record(record)
            except ValueError as error:
                raise _error("conflicting_identity", field="alignment") from error
            records[kind] = record
        if (records["observation"].get("source_ref") != alignment["source_ref"]
                or records["observation"].get("kind") != "alignment"
                or records["source"].get("provider") != "biopython.alignment"):
            raise _error("alignment_operand_mismatch", field="alignment", stage="correspondence")
        if not self._alignment_received(context, alignment):
            raise _error("alignment_not_received", field="alignment")

    @_boundary
    def received_transform_projections(self, context, transform):
        transform = _validate(validate_declared_transform_record, transform)
        if transform["origin"] != "received_fitted" or transform["received_from"] is None:
            raise _error("invalid_transform", field="rotation")
        received = transform["received_from"]
        self.authenticate_received_saved_sheet(context, received["saved_sheet"], required_use="use_transform")
        record = self.results.read_result_authority(received["calculation_custody"], scope=plain(context.scope))
        self._require(self._equal(record["custody"], received["calculation_custody"]))
        candidates = []
        for value in self._received(context)[PROJECTION_SOURCE]:
            calculation = value["calculation"]
            if (value["family"] == "transform" and calculation is not None
                    and self._equal(value["custody"], received["calculation_custody"])
                    and calculation["calculation_id"] == received["calculation_id"]
                    and self._equal(calculation["components_file"], received["components_file"])
                    and {"rotation", "translation"} <= set(value["selection"]["fields"])):
                self._require(any(self._equal(value, original) for original in record["facts"][PROJECTION_SOURCE]))
                candidates.append(deepcopy(value))
        return candidates

