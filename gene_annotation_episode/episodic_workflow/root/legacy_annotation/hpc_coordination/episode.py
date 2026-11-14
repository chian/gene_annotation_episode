"""Fixed private hpc episode and its substantive implementations."""
from importlib import import_module
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.allocation_records as allocation_records
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.child_commissioning as child_commissioning
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.credit as credit
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.execution_configuration as execution_configuration
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.from_parent as from_parent
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.goal as goal
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_operations as hpc_operations
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.internal_summary as internal_summary
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.model_records as model_records
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.to_parent as to_parent
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.report_fields as report_fields
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.report_delivery as report_delivery
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.reference_custody as reference_custody
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.reference_access as reference_access
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.waiting as waiting
yield_implementation = import_module('.yield_estimator', __package__)
from .binding_identity import as_record
from .task import HPCCoordinationTask
from gene_annotation_episode.episodic_workflow.root.library.hpc_launch_context import initial_decision_context, original_launch_handoff

class HPCCoordinationEpisodes:
    roles = ('hpc',)
    entry_roles = ()
    binding_path = 'legacy_annotation/hpc_coordination'
    commissioning_parent = 'legacy_annotation'
    replaces_default_instructions = True
    as_record = as_record
    decision_source_type = HPCCoordinationTask
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
    _tool_request = from_parent._tool_request
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
    initial_decision_context = initial_decision_context
    original_launch_handoff = original_launch_handoff

    @staticmethod
    def child_message_exchange(role, *, child_binding=None):
        if role == 'hpc_prediction':
            from .hpc_resource_prediction.episode import HPCResourcePredictionEpisodes
            if type(child_binding) is HPCResourcePredictionEpisodes:
                from .to_child_hpc_resource_prediction import prepare_request
                from .from_child_hpc_resource_prediction import admit_return
                return prepare_request, admit_return
        if role == 'hpc_execution':
            from .hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes
            if type(child_binding) is HPCAllocationExecutionEpisodes:
                from .to_child_hpc_allocation_execution import prepare_request
                from .from_child_hpc_allocation_execution import admit_return
                return prepare_request, admit_return
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
_declared_child_message_exchange = vars(HPCCoordinationEpisodes)["child_message_exchange"]
