"""Private native terminal summary."""
from __future__ import annotations
from .terminal_contracts import deepcopy, plain

class TerminalSummary:

    def initial_decision_context(self, context):
        return {'execution_resource_information': deepcopy(self.initial_information)}

    def _resource_information(self, kind):
        configuration = self.resources[kind]
        return {'resource_kind': kind, 'workspace': configuration['workspace'], **{name: deepcopy(configuration[name]) for name in ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler') if name in configuration}, 'inventory_snapshot': deepcopy(self.initial_information.get(kind))}

    def decision_context(self, context, current_view):
        state = self.state(context)
        return {'execution_assignment': plain(context.assignment), 'execution_resource': self._resource_information(context.assignment['resource_kind']), 'coordinator_workspace': str(self.directory.resolve()), 'execution_progress': state.credit_view(), 'execution_completion': state.completion_proof()}
