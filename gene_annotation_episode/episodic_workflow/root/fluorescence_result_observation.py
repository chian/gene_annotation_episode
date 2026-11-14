"""Original selected-action and native-observation qualification used by fluorescence receipts."""
from .molecular_result_actions import MolecularResultActions
from gene_annotation_episode.native_control_records import require, same
from .progress_records import validate_resource_observation

from gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_contracts import validate_fluorescence_policy

class FluorescenceResultObservation:

    _selected = MolecularResultActions._selected


    def validate_observation(self, value, intent):
        from .terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
        if is_terminal_target(intent['target']):
            return validate_terminal_observation(value, intent, self.store, self.owner.run_id)
        from gene_annotation_episode.native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value["native"]
        validate_fluorescence_policy(native.get("metadata", {}).get("policy"))
        require(native.get("execution_id") == intent["target"]["execution_id"]
            and native.get("version") == native_version and type(native.get("terminal")) is bool
            and type(native.get("quiescent")) is bool)
        require(not native["terminal"] or native["quiescent"] and native["state"] == "returned")
        if native["terminal"]:
            require(type(native["metadata"].get("service_exit")) is dict
                and value["state"] in {"completed", "failed"})
        return value

