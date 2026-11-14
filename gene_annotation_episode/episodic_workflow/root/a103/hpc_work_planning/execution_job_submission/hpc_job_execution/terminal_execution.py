"""Original native adapter identity and private responsibilities."""
from __future__ import annotations
from .terminal_contracts import Path, VERSION, deepcopy, json, plain
from .terminal_goal import TerminalGoal
from .terminal_operations import TerminalOperations
from .terminal_state import TerminalState
from .terminal_assignment import TerminalAssignment
from .terminal_summary import TerminalSummary
from .terminal_report import TerminalReport
from .terminal_credit import TerminalCredit

class TerminalExecutionBehavior(TerminalGoal, TerminalOperations, TerminalState, TerminalAssignment, TerminalSummary, TerminalReport, TerminalCredit):

    def __init__(self, services, *, directory, resources, store=None, initial_information=None, flux_balance_input_reader=None):
        self.services, self.directory, self.store = (services, Path(directory), store)
        self.resources = json.loads(json.dumps(plain(resources), allow_nan=False))
        if not self.resources or not set(self.resources) <= {'local', 'hpc'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information = plain(initial_information or {})
        if not set(self.initial_information) <= set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        self._states = {}

    def as_record(self):
        return {'binding_id': 'terminal_execution', 'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information)}}

    def child_roles(self, role):
        return ()

    def credit_kind(self, role):
        return 'operational'

    def permitted_common_actions(self, context):
        return ('tool',)

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def practical_estimator(self, context):
        from gene_annotation_episode.episodic_workflow.root.a103.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(self.state(context).verify_completion)
