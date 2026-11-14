"""Original factual reads and mechanical selection of actual private owners."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import AcquisitionError, CHECKED_STATUS_SCHEMA, ContractError, EXECUTION_OBSERVATION_SCHEMA, HANDOFF_SCHEMA, Mapping, REFERENCE_FORMATS, RESULT_PROGRESS_SCHEMA, ROLES, ReportBoundaryError, SAMPLE_SCHEMA, _result_progress, deepcopy, json, recorded_coverage, recorded_estimate, recorded_forecasts, reference, resource_report_source, sqlite3, subprocess, validate_recorded_estimates

def read_unclassified_facts(owner, source, *, credit_view=None):
    assignment = owner.assignment(source)
    try:
        handoff = owner.jobs.handoff(assignment['job_ref'])
        owner.jobs.check_handoff(handoff)
        failure = None
    except (sqlite3.Error, subprocess.SubprocessError):
        handoff, failure = (None, 'receiving_interface_unavailable')
    except (ValueError, KeyError, OSError, AcquisitionError) as error:
        handoff = None
        try:
            row = owner.jobs._row(assignment['job_ref'])
            handle = owner.jobs.directory / assignment['job_ref'] / 'native.handle.json'
            unreadable = False
            try:
                prepared = handle.is_file() and json.loads(handle.read_text()).get('stage') == 'prepared'
            except (OSError, ValueError, TypeError, AttributeError):
                prepared, unreadable = (False, True)
            failure = 'receiving_interface_unavailable' if unreadable else 'submission_unconfirmed' if prepared else 'job_not_submitted' if not row['submission_requested'] else 'submission_unconfirmed' if not handle.is_file() else 'native_handle_identity_mismatch' if str(error) == 'native_handle_does_not_describe_registered_job' else 'receiving_interface_unavailable'
        except (sqlite3.Error, ValueError, KeyError):
            failure = 'receiving_interface_unavailable'
    facts = {'job_ref': assignment['job_ref'], 'job_cpu': assignment['cpu'], 'job_handoff': handoff, 'job_handoff_state': 'usable' if handoff else 'unavailable', 'job_handoff_failure': failure, 'job_sample': owner.latest_sample(source), 'resource_tool_estimates': recorded_forecasts(source.workflow.store, run_id=source.workflow.run_id, episode_id=source.episode_id)}
    if 'search_modes' in owner.jobs.config:
        facts['job_search_mode'] = assignment['search_mode']
    if owner.has_information_channel(source.path[-1][0]):
        information = owner.credit_view(source) if credit_view is None else credit_view
        facts.update(monitoring_information_credit=information['monitoring_information_credit'], monitoring_findings=information['monitoring_findings'])
    return facts

def read_facts_for_role(binding, source, *, credit_view=None):
    role = source.path[-1][0]
    if role == 'job_launch':
        from ..homology_job_submission.to_parent import read_facts
    elif role == 'job_monitor':
        from ..homology_job_monitoring.to_parent import read_facts
    elif role == 'job_results':
        from ..homology_result_acquisition.to_parent import read_facts
    else:
        read_facts = read_unclassified_facts
    return read_facts(binding, source, credit_view=credit_view)

def project_credit_view_for_role(binding, source):
    if source.path[-1][0] == 'job_monitor':
        from ..homology_job_monitoring.credit import project_credit_view
    elif source.path[-1][0] == 'job_results':
        from ..homology_result_acquisition.credit import project_credit_view
    else:
        from ..homology_job_submission.credit import project_credit_view
    return project_credit_view(binding, source)
