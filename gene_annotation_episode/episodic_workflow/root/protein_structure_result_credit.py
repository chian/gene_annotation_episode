"""Original operational acquisition credit and inherited bundle exclusion."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_records import VERSION
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import digest
import json


class ProteinStructureResultCredit:
    def credit_view(self, context, receiver_selection) -> dict:
        selection = self.owner._selection(context, receiver_selection)
        known, initial = set(selection["known_record_refs"]), set(selection["initial_known_record_refs"])
        acquired, inherited = set(), set()
        for receipt in self.receipts.completed_receipts(context):
            body, publication = receipt["body"], receipt["publication"]
            if (body["intent"]["assignment"]["selector"]["acquisition"] == "complete_bound_bundle"
                    and publication["source_record"] is not None and publication["source_record"]["id"] in known):
                acquired.add(digest(body["bundle"]["identity"]))
        # A source can have several original collections. Authenticate every
        # matching completed receipt; never choose a sorted-first source index.
        if initial:
            rows = self.store.db.execute("SELECT episode_id,decision_index,result FROM runtime_actions "
                "WHERE run_id=? AND result IS NOT NULL AND json_extract(result,'$.result.version')=? "
                "ORDER BY episode_id,decision_index", (self.owner.run_id, VERSION))
            for row in rows:
                candidate = json.loads(row["result"])["result"]
                if not set(candidate["publication"]["record_refs"]) & initial:
                    continue
                receipt = self.receipts.read_completed(episode_id=row["episode_id"],
                    operation_key=candidate["body"]["intent"]["operation_key"], scope=plain(context.scope))
                if receipt["body"]["bundle"] is not None:
                    inherited.add(digest(receipt["body"]["bundle"]["identity"]))
        count = len(acquired - inherited)
        value = self.owner.acquired_record_unit * count
        return {"credit": value, "operational_credit": value, "new_handoff_count": 0,
            "new_acquired_record_count": count, "operational_credit_binding": {"version": VERSION,
                "handoff_unit": self.owner.handoff_unit, "acquired_record_unit": self.owner.acquired_record_unit,
                "scientific_credit": False, "monitoring_credit": False}}

