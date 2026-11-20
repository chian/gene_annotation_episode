"""Where the episode stands, as a pure function of the view: the commission (the parent input), what each unit did and
earned, the handoff of the job, whether its end event was seen and at which cursor, and the saved gradings with the
controlled features code reads from them. The job record is read from custody (the artifact the launch unit kept),
and the job rows (the handoff, a check, the closure) from the job ledger rows the episode holds, never from a
service."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_pairwise_features import (
    saved_grading_features)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import (
    JOB_LEDGER, checks, closure, job_rows)

END_EVENT = 'state_changed'


def _job_record_refs(records):
    """The job ledger rows chosen for the parent: the latest check (the state last observed) and the closure (with it
    the parent no longer counts the job as outstanding)."""
    refs = []
    for job in dict.fromkeys(row['job'] for row in job_rows(records)):
        closed = closure(records, job)
        refs.extend(row['id'] for row in (*checks(records, job)[-1:], *([] if closed is None else [closed])))
    return refs


def _observed(records):
    """The latest observation of the job among the rows the episode holds (a check or the closure), or ``None``."""
    rows = [row for row in job_rows(records) if row['event'] in ('check', 'closure')]
    return max(rows, key=lambda row: row['at']) if rows else None


def internal_summary(view):
    parent, records = view.parent_input, view.records
    controller = view.controller_state
    scores = [] if controller is None else list(controller.as_record()['scores'])
    units, handoff, ended, cursor, graded = [], None, False, 0, []
    for index, unit in enumerate(view.outcomes):
        outcome, tool = unit['outcome'], unit['tool']
        row = {'action': tool, 'status': outcome['status']}
        if outcome['status'] != 'completed':
            row['failure_code'] = outcome['failure']['code'] if 'failure' in outcome else outcome['feedback']['code']
        elif tool == 'launch_job':
            handoff = {'handoff_ref': outcome['handoff_ref'], 'job_ref': outcome['job_ref']}
        elif tool == 'wait_for_end':
            ended = ended or outcome['woke_on'] == END_EVENT
            cursor = max(cursor, outcome['event_cursor'])
        elif outcome['result']['grading_artifact_ref'] not in {item['sheet_refs'][0] for item in graded}:
            graded.append({'source_ref': outcome['result']['result_ref'],
                           'search_ref': outcome['result']['search_ref'],
                           **saved_grading_features(records, outcome['result']['grading_artifact_ref'])})
        if index < len(scores):
            row['credit_earned'] = scores[index]
        units.append(row)
    event_target = report_name = job_spec = None
    if handoff is not None:
        job_spec = json.loads(records.get_artifact(handoff['job_ref']))['blast_pairwise']
        report_name = job_spec['report']['relative_path']
        event_target = records.table(JOB_LEDGER).get(handoff['handoff_ref'])['detail']['native']['event_target']
    observed = _observed(records)
    complete = bool(graded)
    refs = [ref for item in graded for ref in (item['source_ref'], item['sheet_refs'][0], item['search_ref'])]
    return {'assignment': parent, 'information_unit': parent['information_unit'], 'units': units,
            'handoff_ref': None if handoff is None else handoff['handoff_ref'], 'event_target': event_target,
            'event_cursor': cursor, 'ended': ended, 'job_spec': job_spec, 'report_name': report_name,
            'job': {'last_observed_state': None if observed is None else observed['detail']['state']},
            'pairwise_sheets': [{key: value for key, value in item.items() if key not in ('source_ref', 'search_ref')}
                                for item in graded],
            'execution_completed': complete,
            'execution_progress': {'execution_handoff_refs': [] if handoff is None else [handoff['handoff_ref']],
                                   'execution_job_record_refs': _job_record_refs(records),
                                   'execution_blast_graded_refs': refs, 'execution_completed': complete},
            'units_consumed': view.units_consumed}
