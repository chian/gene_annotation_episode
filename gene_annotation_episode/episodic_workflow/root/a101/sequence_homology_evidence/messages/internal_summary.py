"""Where the episode stands, as a pure function of the loop's view: the commission, one row per completed unit
(a selected tool, a reasoning commit, a revision of the process selection or a child commission), what each child
reported, the records this episode committed, the handoff records its children returned, the working state of the
scope and the controller's yield table.

Carried from the old ``internal_summary.py`` (the ``sequence_homology_evidence`` block of the decision context:
selection, initial selection digest, the assignment, the permitted children), ``decision_state.py``,
``standalone_credit_presentation.py`` and ``commissioned_credit_presentation.py`` (goal, scope, working_state,
visible_record_refs, last_local_outcome, controller state, credit binding). The library entries the selection
refers to (evidence axis, thought pattern) are read by ``task.decide`` from the process library of the settings;
the summary holds the selection. The old standalone presentation of proposed annotations, annotation comparisons
and the root's arms is the root episode's; the old own-attempt lookup (``episode.history``) is this unit list,
paged in ``task.decide``. The old ``time_accounting`` is ``ctx.clock`` in ``task.decide``.

For the commissions (``task.commission_fields``, ``msg_to_child``) the summary also holds what a commission is
chosen from and built with: ``held_source_refs`` (the held sources), ``named_refs`` (for each held record, the
held records it names: what travels in custody beside it), ``problem_subject_extents`` (the problem subjects this
episode holds, each with its whole extent: a literature commission that asks about an aligned homolog puts the
problem subjects its question context names into the child's scope), ``revisions`` (the selection and
revision origin of each completed ``process_revise`` unit, by position), ``launches`` (the request of each launch
this episode commissioned, with the handoff rows it returned) and, in ``outstanding_jobs``, the identity of each
job's launch read from its handoff row."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    scientific_digest)

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    ALL, axis_features)

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import JOB_LEDGER, outstanding_jobs

from ..credit import A101SequenceCredit
from ..task import CHILD_SLOTS

EXECUTED = ('completed', 'partial')
EVIDENCE_RECORD_TYPES = ('observation', 'assessment')


def _outstanding(records):
    """The jobs whose handoff row this episode holds and whose closure row it does not hold, with the check rows
    it holds of each: what a monitor commission passes in custody. ``blast_status_target`` is the old
    ``target_identity.is_blast_job`` read from the handoff row (an ``api`` job of the service ``ncbi_blast``):
    the monitor's assignment carries it. ``launch_run_id``, ``launch_episode_id`` and ``job_sha256`` are the
    identity of the launch read from the same row (its system columns and its detail): the execution target of a
    results commission names them."""
    ledger = records.table(JOB_LEDGER)
    found = []
    for job in outstanding_jobs(records):
        row = ledger.get(job['handoff_ref'])
        found.append({**job, 'launch_run_id': row['run_id'], 'launch_episode_id': row['episode_id'],
                      'job_sha256': row['detail']['job_sha256'],
                      'blast_status_target': (job['kind'] == 'api'
                                              and row['detail']['native'].get('service') == 'ncbi_blast')})
    return found


def _named(records, reference):
    """The held records the held record ``reference`` names (an artifact names none). A pass carries only the
    records named, so a commission names these beside the record for a child whose code follows them: a source and
    its artifacts, an observation and its source and subjects, a subject and its sequence."""
    if reference.startswith('artifact_'):
        return []
    return [named for named in dict.fromkeys(records.named_references(reference))
            if named != reference and records.holds(named)]


def internal_summary(view):
    records = view.records
    parent = view.parent_input
    units, child_reports, committed, handoff_refs, last = [], [], [], [], None
    revisions, launches = [], []
    for position, outcome in enumerate(view.outcomes):
        if outcome['kind'] == 'tool':
            result = outcome['outcome']
            row = {'position': position, 'kind': 'tool', 'tool': outcome['tool'],
                   'selected': outcome['arguments'].get('tool'), 'status': result['status'],
                   'record_refs': list(result['record_refs']), 'feedback': result.get('feedback')}
            if outcome['tool'] == 'reason' and result['status'] in EXECUTED:
                committed.extend(ref for ref in result['record_refs'] if ref not in committed)
            if outcome['tool'] == 'process_revise' and result['status'] == 'completed':
                # the selection a recursive commission may name by this position (code copies it)
                revisions.append({'position': position, 'selection': result['result']['selection'],
                                  'revision_origin': result['revision_origin']})
        else:
            report = outcome['report']
            row = {'position': position, 'kind': 'child', 'slot': outcome['slot'], 'status': 'completed',
                   'credit': report['credit'], 'record_refs': list(report['record_refs'])}
            child_reports.append({'slot': outcome['slot'], **report})
            handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
            if outcome['slot'] == 'execution_job_submission':
                # the request this episode launched, by the handoff rows the launch returned: a results
                # commission of one of those jobs is built from it
                launches.append({'position': position, 'handoff_refs': list(report['handoff_refs']),
                                 'request': outcome['message']['assignment']['requests'][
                                     outcome['arguments']['resource_id']]})
        units.append(row)
        last = row
    held = [ref for ref in records.refs() if not ref.startswith('row_')]
    assignment = {'scope': parent['scope'], 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    details = A101SequenceCredit().read_details(records, parent['scope'], known_record_refs=held, assignment=assignment,
                                                details_limit=ALL, details_offset=0)
    return {**parent,
            'path_depth': len(view.path),
            'initial_selection_sha256': scientific_digest(parent['selection']),
            'permitted_children': sorted(CHILD_SLOTS),
            'units': units, 'last_local_outcome': last, 'child_reports': child_reports,
            'committed_record_refs': committed, 'handoff_refs': handoff_refs,
            'held_record_refs': held,
            'held_source_refs': [row['id'] for row in records.list('source')],
            'named_refs': {ref: _named(records, ref) for ref in held},
            'problem_subject_extents': {ref: records.coverage(ref) for ref in records.problem()['subject_refs']},
            'revisions': revisions, 'launches': launches,
            'outstanding_jobs': _outstanding(records),
            'evidence_refs': [row['id'] for kind in EVIDENCE_RECORD_TYPES for row in records.list(kind)],
            'working_state': records.reasoning_view(parent['scope']),
            'reasoning_schema': records.reasoning_schema(),
            'credit_binding': A101SequenceCredit().as_record(), 'axis_findings': axis_features(details),
            'units_consumed': view.units_consumed,
            'action_yields': (None if view.controller_state is None
                              else yield_table(view.controller_state, forecast_unit='native_correspondence_credit'))}
