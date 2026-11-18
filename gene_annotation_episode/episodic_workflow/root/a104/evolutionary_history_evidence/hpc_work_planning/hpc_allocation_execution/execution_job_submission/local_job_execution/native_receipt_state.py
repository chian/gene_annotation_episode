"""Private original A104 LocalExecution service native_receipt_state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import PracticalState
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import assess_validations
from gene_annotation_episode.episodic_workflow.root.a104.library.native_terminal_transport import digest

class LocalExecutionNativeReceiptState:

    def _state_directory(self, context):
        return self.directory / 'practical-execution' / digest({'run_id': context.run_id, 'episode_id': context.episode_id})

    def initialize(self, context):
        assignment = self._assignment(context)
        directory = self._state_directory(context)
        state = PracticalState(directory, context.run_id, context.episode_id, assignment, **{} if (directory / 'assignment.json').is_file() else {'initial_outcome': {'facts': {}}, 'initial_validations': assess_validations(assignment, {'facts': {}}, assignment['initial_context'])})
        self._states[context.episode_id] = state
        return state

    def state(self, context):
        return self._states.get(context.episode_id) or self.initialize(context)
