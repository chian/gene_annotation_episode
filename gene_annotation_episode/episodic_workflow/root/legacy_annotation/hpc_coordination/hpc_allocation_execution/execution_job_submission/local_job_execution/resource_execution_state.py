"""Original fixed local execution execution_state responsibilities; source candidate."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import assess_validations, validate_assignment
from .resource_state_records import PracticalState
from gene_annotation_episode.episodic_workflow.root.terminal_execution import digest


class LocalExecutionState:
    def _assignment(self,context):
        assignment=validate_assignment(plain(context.assignment))
        kind='local' if context.role=='launch_local' else None
        if assignment['resource_kind']!=kind or kind not in self.resources:
            raise ValueError('execution_resource_assignment_mismatch')
        self._operations(kind).validate_assignment(assignment)
        return assignment

    def _state_directory(self,context):
        # Preserve the host receipt location and source identity. No model must
        # construct this path or maintain an additional job ledger.
        return self.directory/'practical-execution'/digest({
            'run_id':context.run_id,'episode_id':context.episode_id})

    def initialize(self,context):
        assignment=self._assignment(context);directory=self._state_directory(context)
        state=PracticalState(directory,context.run_id,context.episode_id,assignment,
            **({} if (directory/'assignment.json').is_file() else {
                'initial_outcome':{'facts':{}},
                'initial_validations':assess_validations(assignment,{'facts':{}},assignment['initial_context'])}))
        self._states[context.episode_id]=state
        return state

    def state(self,context):
        return self._states.get(context.episode_id) or self.initialize(context)

    def prepare_assignment(self,parent,role,selection,scope,operation_key):
        assignment=validate_assignment(plain(selection))
        if role!='launch_local' or assignment['resource_kind']!='local':
            raise ValueError('execution_resource_assignment_mismatch')
        return self._operations(assignment['resource_kind']).validate_assignment(assignment)

