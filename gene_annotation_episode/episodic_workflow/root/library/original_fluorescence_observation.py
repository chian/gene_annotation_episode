"""Original public fluorescence delegated observation and selected-action custody.

These are the original two GenomicOverlapResultReceipts methods actually used
by the public fluorescence receipt owner. Its historical policy stays distinct
from the adapted current Root fluorescence observation policy.
"""
import json
from gene_annotation_episode.native_control_records import require, same
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation

POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}


class OriginalFluorescenceObservation:

    def _selected(self, intent):
        row = self.owner._selected_result_action(intent["episode_id"], intent["operation_key"],
            intent["tool_name"], intent["arguments"])
        require(same(json.loads(row["action"]), {"kind": "tool", "tool": intent["tool_name"], "arguments": {}}))
        return row


    def validate_observation(self, value, intent):
        from gene_annotation_episode.episodic_workflow.root.terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
        if is_terminal_target(intent['target']):
            return validate_terminal_observation(value, intent, self.store, self.owner.run_id)
        from gene_annotation_episode.native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value["native"]
        require(native.get("execution_id") == intent["target"]["execution_id"]
            and native.get("version") == native_version and type(native.get("terminal")) is bool
            and type(native.get("quiescent")) is bool and same(native.get("metadata", {}).get("policy"), POLICY))
        require(not native["terminal"] or native["quiescent"] and native["state"] == "returned")
        if native["terminal"]:
            require(type(native["metadata"].get("service_exit")) is dict
                and value["state"] in {"completed", "failed"})
        return value

