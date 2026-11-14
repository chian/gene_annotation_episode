"""Actual private job_launch to_parent."""
from __future__ import annotations
from .message_contracts import AcquisitionError, CHECKED_STATUS_SCHEMA, ContractError, EXECUTION_OBSERVATION_SCHEMA, HANDOFF_SCHEMA, Mapping, REFERENCE_FORMATS, RESULT_PROGRESS_SCHEMA, ROLES, ReportBoundaryError, SAMPLE_SCHEMA, _result_progress, deepcopy, json, recorded_coverage, recorded_estimate, recorded_forecasts, reference, resource_report_source, sqlite3, subprocess, validate_recorded_estimates
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_fact_readers import read_facts_for_role

def read_facts(owner, source, *, credit_view=None):
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
    facts['job_checked_status'] = owner.latest_checked_status(source)
    if owner.has_information_channel(source.path[-1][0]):
        information = owner.credit_view(source) if credit_view is None else credit_view
        facts.update(monitoring_information_credit=information['monitoring_information_credit'], monitoring_findings=information['monitoring_findings'])
    return facts

