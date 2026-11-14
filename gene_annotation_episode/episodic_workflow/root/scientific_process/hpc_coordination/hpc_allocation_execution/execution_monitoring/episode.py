from importlib import import_module
from .task import MonitorTask
from . import execution_configuration
from . import from_parent
from . import goal
from . import credit
from . import internal_summary
from . import progress_observation
from . import to_child_execution_monitoring
from . import to_parent
_yield = import_module('.yield_estimator', __package__)
from .binding_identity import as_record
from .from_child_execution_monitoring import admit_return

class MonitorEpisodes:
    roles = ('monitor',)
    entry_roles = ()
    binding_path = 'scientific_process/hpc_coordination/hpc_allocation_execution/execution_monitoring'
    commissioning_parent = 'scientific_process/hpc_coordination/hpc_allocation_execution'
    decision_source_type = MonitorTask
    as_record = as_record
    __init__ = execution_configuration.__init__
    _role = staticmethod(from_parent._role)
    required_return_sources = from_parent.required_return_sources
    assignment_schema = from_parent.assignment_schema
    _assignment = from_parent._assignment
    prepare_assignment = from_parent.prepare_assignment
    instructions = goal.instructions
    credit_kind = credit.credit_kind
    credit_view = credit.credit_view
    _own_progress_refs = internal_summary._own_progress_refs
    _received = internal_summary._received
    decision_context = internal_summary.decision_context
    permitted_common_actions = progress_observation.permitted_common_actions
    catalog = progress_observation.catalog
    _snapshot = progress_observation._snapshot
    execute = progress_observation.execute
    child_roles = to_child_execution_monitoring.child_roles
    allowed_children = to_child_execution_monitoring.allowed_children
    fact_sources = to_parent.fact_sources
    facts = to_parent.facts
    resolve = to_parent.resolve
    validate_report = to_parent.validate_report
    yield_controller = _yield.yield_controller
    _is_blast_job = _yield._is_blast_job

    @staticmethod
    def child_message_exchange(role):
        if role == 'monitor':
            return to_child_execution_monitoring.prepare_request, admit_return
        return None


# Exact private declaration identity; custom callbacks retain runtime fallback.
_declared_child_message_exchange = vars(MonitorEpisodes)["child_message_exchange"]
