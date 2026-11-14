"""Private original A104 HPCExecution service native_internal_summary."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class HPCExecutionNativeInternalSummary:

    def initial_decision_context(self, context):
        return {'execution_resource_information': deepcopy(self.initial_information)}

    def _resource_information(self, kind):
        configuration = self.resources[kind]
        return {'resource_kind': kind, 'workspace': configuration['workspace'], **{name: deepcopy(configuration[name]) for name in ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler') if name in configuration}, 'inventory_snapshot': deepcopy(self.initial_information.get(kind))}

    def decision_context(self, context, current_view):
        state = self.state(context)
        return {'execution_assignment': plain(context.assignment), 'execution_resource': self._resource_information(context.assignment['resource_kind']), 'coordinator_workspace': str(self.directory.resolve()), 'execution_progress': state.credit_view(), 'execution_completion': state.completion_proof()}
