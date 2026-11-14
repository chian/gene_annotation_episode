"""Fixed private hpc_prediction episode and its substantive implementations."""
from importlib import import_module
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.child_commissioning as child_commissioning
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.credit as credit
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.execution_configuration as execution_configuration
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.from_parent as from_parent
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.goal as goal
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.hpc_operations as hpc_operations
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.internal_summary as internal_summary
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.model_records as model_records
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.to_parent as to_parent
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.report_fields as report_fields
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.report_delivery as report_delivery
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.reference_custody as reference_custody
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.reference_access as reference_access
import gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_coordination.hpc_resource_prediction.waiting as waiting
yield_implementation = import_module('.yield_estimator', __package__)
from .binding_identity import as_record
from .task import HPCResourcePredictionTask

class HPCResourcePredictionEpisodes:
    roles = ('hpc_prediction',)
    entry_roles = ()
    binding_path = 'legacy_annotation/hpc_coordination/hpc_resource_prediction'
    commissioning_parent = 'legacy_annotation/hpc_coordination'
    replaces_default_instructions = True
    as_record = as_record
    decision_source_type = HPCResourcePredictionTask
    __init__ = execution_configuration.__init__
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
    instructions = goal.instructions
    decision_context = internal_summary.decision_context
    catalog = hpc_operations.catalog
    _queue = model_records._queue
    _candidates = staticmethod(model_records._candidates)
    _features = staticmethod(model_records._features)
    _comparisons = model_records._comparisons
    continuation_for_action = waiting.continuation_for_action
    activity_advice = internal_summary.activity_advice
    practical_estimator = waiting.practical_estimator
    _known = reference_custody._known
    resolve_received_reference = reference_custody.resolve_received_reference
    read_evidence = reference_custody.read_evidence
    execute = hpc_operations.execute
    fact_sources = report_fields.fact_sources
    facts = report_delivery.facts
    resolve = reference_access.resolve
    frozen_reference = reference_access.frozen_reference
    validate_report = to_parent.validate_report
    credit_view = credit.credit_view
