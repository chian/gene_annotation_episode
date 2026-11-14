"""Connect private A101 launch_local operational responsibilities."""
from __future__ import annotations
from importlib import import_module as _original_yield_import
OriginalContinuation = _original_yield_import('.yield', __package__).OriginalContinuation
from .task import OperationalTask
from .execution_contracts import RESOURCE_ROLES
from .credit import ResourceEpisodeCredit
from .configuration import OperationalConfiguration
from .binding_record import OperationalBindingRecord
from .goal import OperationalGoal
from .from_parent import OperationalAssignment
from .to_parent import OperationalReport
from .received_evidence import ReceivedOperationalEvidence
from .internal_summary import OperationalSummary
from .execution_operations import OperationalOperations

class ResourceEpisode(OperationalConfiguration, OperationalBindingRecord, OperationalGoal, OperationalAssignment, OperationalReport, ReceivedOperationalEvidence, OperationalSummary, OperationalOperations, ResourceEpisodeCredit):
    decision_source_type = OperationalTask
    _original_continuation_owner = ('launch_local', OriginalContinuation.original_continuation_controller)
    binding_path = 'scientific_process/resource_work_submission/local_resource_work_execution'
    commissioning_parent = 'scientific_process/resource_work_submission'
    "C7 binding; all iteration/commissioning remains in shared method_loop.\n\n    Adapter API: resource_id, capability(), as_record(), prepare_assignment(\n    context, role, launch_assignment, scope, operation_key), catalog(context),\n    execute(context, tool_name, arguments, operation_key), fact_sources(role),\n    facts(context, completion_snapshot), resolve(context, reference, namespace),\n    validate_report(context, form, original_schema), credit_view(context,\n    receiver_selection). An optional decision_context(context) supplies actual\n    prospective duration information. An adapter's tool list is authoritative.\n    "
    roles = ('launch_local',)
    entry_roles = ()

    def child_roles(self, role):
        self.credit_kind(role)
        return ()

    def contract_information_profile(self, context):
        return self._contract_information_profile if context.role == 'launch' else None

    def permitted_common_actions(self, context):
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def allowed_children(self, parent, caller_capabilities):
        self.credit_kind(parent.role)
        return ()

    def context_hook_applies(self, context):
        """Own role hooks; the original Launch parent admits external delivery."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        return role == 'launch_local' if role in ('launch', 'launch_local', 'launch_hpc', 'launch_api', 'results') else False
