"""Fixed original job_launch implementation and its private task connection."""
from .task import HomologySubmissionTask
from .binding_identity import as_record
from . import configuration
from . import credit
from . import from_parent
from . import goal
from . import homology_operations
from . import to_parent
from gene_annotation_episode.episodic_workflow.root.library import homology_custody
from gene_annotation_episode.episodic_workflow.root.library import homology_custody_configuration
from gene_annotation_episode.episodic_workflow.root.library import homology_native_events
from gene_annotation_episode.episodic_workflow.root.library import homology_received_records

class HomologySubmissionEpisodes:
    roles = ('job_launch',)
    entry_roles = ('job_launch',)
    binding_path = 'homology_job_submission'
    commissioning_parent = 'annotation'
    decision_source_type = HomologySubmissionTask
    as_record = as_record
    jobs = homology_custody_configuration.jobs
    parser_policy = homology_custody_configuration.parser_policy
    _job_credit_calculator = homology_custody_configuration._job_credit_calculator
    monitoring_projector = homology_custody_configuration.monitoring_projector
    _role_credit_bindings = homology_custody_configuration._role_credit_bindings
    statistics = homology_custody_configuration.statistics
    native_event_provider = homology_custody_configuration.native_event_provider
    __init__ = configuration.__init__
    with_native_events = homology_native_events.with_native_events
    recover_native_events = homology_native_events.recover_native_events
    bind_job_native_events = homology_native_events.bind_job_native_events
    recover_statistics = homology_native_events.recover_statistics
    instructions = goal.instructions
    fact_sources = to_parent.fact_sources
    commission_schemas = from_parent.commission_schemas
    _query = staticmethod(homology_custody._query)
    prospective_execution_classes = homology_custody.prospective_execution_classes
    prospective_execution_options = homology_custody.prospective_execution_options
    assign = from_parent.assign
    assignment = staticmethod(homology_custody.assignment)
    working_state = homology_custody.working_state
    _launch_credit = credit._launch_credit
    initial_credit = credit.initial_credit
    binding_for = credit.binding_for
    credit_kind = credit.credit_kind
    has_information_channel = credit.has_information_channel
    credit_view = credit.credit_view
    resolve = homology_custody.resolve
    catalog = homology_operations.catalog
    execute = homology_operations.execute
    _execute = homology_operations._execute
    latest_sample = homology_custody.latest_sample
    recorded_sample = staticmethod(homology_custody.recorded_sample)
    latest_checked_status = homology_custody.latest_checked_status
    facts = to_parent.facts
    validate_report = to_parent.validate_report
    _validate_launch_return = to_parent._validate_launch_return
    _validate_role_return_sources = to_parent._validate_role_return_sources
    _validate_recorded_return = homology_received_records._validate_recorded_return
    received_timing_records = homology_received_records.received_timing_records

    def child_roles(self, role):
        if role != 'job_launch':
            raise ValueError('unknown_job_episode_role')
        return ()
