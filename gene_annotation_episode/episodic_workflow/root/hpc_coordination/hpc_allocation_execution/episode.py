"""Fixed private hpc_execution episode and its substantive implementations."""
from importlib import import_module
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.allocation_records as allocation_records
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.child_commissioning as child_commissioning
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.credit as credit
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.execution_configuration as execution_configuration
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.from_parent as from_parent
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.goal as goal
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.hpc_operations as hpc_operations
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.internal_summary as internal_summary
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.model_records as model_records
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.to_parent as to_parent
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.report_fields as report_fields
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.report_delivery as report_delivery
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.reference_custody as reference_custody
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.reference_access as reference_access
import gene_annotation_episode.episodic_workflow.root.hpc_coordination.hpc_allocation_execution.waiting as waiting
yield_implementation = import_module('.yield', __package__)
from .binding_identity import as_record
from .task import HPCAllocationExecutionTask

class HPCAllocationExecutionEpisodes:
    roles = ('hpc_execution',)
    entry_roles = ()
    binding_path = 'hpc_coordination/hpc_allocation_execution'
    commissioning_parent = 'hpc_coordination'
    replaces_default_instructions = True
    as_record = as_record
    decision_source_type = HPCAllocationExecutionTask
    __init__ = execution_configuration.__init__
    targets = property(execution_configuration.targets)
    yield_controller = yield_implementation.yield_controller
    credit_kind = credit.credit_kind
    child_roles = child_commissioning.child_roles
    allowed_children = child_commissioning.allowed_children
    assignment_schema = from_parent.assignment_schema
    commission_identity = staticmethod(from_parent.commission_identity)
    _commission = from_parent._commission
    prepare_assignment = from_parent.prepare_assignment
    permitted_common_actions = hpc_operations.permitted_common_actions
    state = model_records.state
    initialize = model_records.initialize
    _current_model = staticmethod(model_records._current_model)
    _quality = staticmethod(model_records._quality)
    _history = staticmethod(model_records._history)
    _shared_history = model_records._shared_history
    _observe_queue = model_records._observe_queue
    export_closed = model_records.export_closed
    instructions = goal.instructions
    decision_context = internal_summary.decision_context
    catalog = hpc_operations.catalog
    _queue = model_records._queue
    _candidates = staticmethod(model_records._candidates)
    _features = staticmethod(model_records._features)
    _comparisons = model_records._comparisons
    _freeze = allocation_records._freeze
    _candidate = allocation_records._candidate
    _last_forecast = staticmethod(allocation_records._last_forecast)
    _collected_unit_ids = staticmethod(allocation_records._collected_unit_ids)
    _uncollected_completed_unit_ids = allocation_records._uncollected_completed_unit_ids
    continuation_for_action = waiting.continuation_for_action
    activity_advice = internal_summary.activity_advice
    practical_estimator = waiting.practical_estimator
    _target = allocation_records._target
    _known = reference_custody._known
    resolve_received_reference = reference_custody.resolve_received_reference
    read_evidence = reference_custody.read_evidence
    _window = allocation_records._window
    _allocation = allocation_records._allocation
    _measure = allocation_records._measure
    _publish = allocation_records._publish
    execute = hpc_operations.execute
    fact_sources = report_fields.fact_sources
    facts = report_delivery.facts
    resolve = reference_access.resolve
    frozen_reference = reference_access.frozen_reference
    validate_report = to_parent.validate_report
    credit_view = credit.credit_view

    @staticmethod
    def child_message_exchange(role, *, child_binding=None):
        if role == 'launch':
            from .execution_job_submission.episode import ExecutionSubmissionBinding
            if type(child_binding) is ExecutionSubmissionBinding:
                from .to_child_execution_job_submission import prepare_request
                from .from_child_execution_job_submission import admit_return
                return prepare_request, admit_return
        if role == 'results':
            from .execution_result_acquisition.episode import ResultAcquisitionBinding
            if type(child_binding) is ResultAcquisitionBinding:
                from .to_child_execution_result_acquisition import prepare_request
                from .from_child_execution_result_acquisition import admit_return
                return prepare_request, admit_return
        if role == 'launch':
            from .resource_job_submission.episode import ResourceSubmissionBinding
            if type(child_binding) is ResourceSubmissionBinding:
                from .to_child_resource_job_submission import prepare_request
                from .from_child_resource_job_submission import admit_return
                return prepare_request, admit_return
        if role == 'results':
            from .resource_result_acquisition.episode import ResourceAcquisitionBinding
            if type(child_binding) is ResourceAcquisitionBinding:
                from .to_child_resource_result_acquisition import prepare_request
                from .from_child_resource_result_acquisition import admit_return
                return prepare_request, admit_return
        if role == 'monitor':
            from .execution_monitoring.episode import MonitorEpisodes
            if type(child_binding) is MonitorEpisodes:
                from .to_child_execution_monitoring import prepare_request
                from .from_child_execution_monitoring import admit_return
                return prepare_request, admit_return
        return None


# Exact private declaration identity; custom callbacks retain runtime fallback.
_declared_child_message_exchange = vars(HPCAllocationExecutionEpisodes)["child_message_exchange"]
