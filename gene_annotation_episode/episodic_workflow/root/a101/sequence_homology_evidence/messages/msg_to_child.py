"""The commission of each child (the old ``to_child_<role>.py``: ``to_child_sequence_homology_evidence``,
``to_child_published_evidence_assessment``, ``to_child_execution_job_submission``,
``to_child_execution_progress_assessment``, ``to_child_execution_result_acquisition``,
``to_child_resource_result_acquisition``, ``to_child_resource_work_submission``).

The old ``prepare_*`` expanded the parent's report-contract form from the fact sources the child required, checked
the child role and binding path, materialized the launch instructions and let the child binding's
``prepare_assignment`` build the assignment. None of that is a commission now. A commission is controlled data
only: the model chooses among values this episode holds (``task.commission_fields``: record references, a bound
resource, the position of one of its own revisions, a handoff row, the return fields), and this file builds the
child's assignment, in the child's own form, from those choices and this episode's summary. The model writes no
assignment, no objective and no message: the objective is this episode's own fixed text for the slot and the
message is empty, except that the published evidence assessment is told the value of its own objective vocabulary
the model chose (``_message``). A commission the child does not admit fails (no check here).

Every record the child's code reads is named in a ``record_refs`` field of the assignment: the records the model
chose with every held record those name, and those name in turn (an observation and its source and subjects, a
source and its artifacts, a subject and its sequence: ``_custody`` over the summary's ``named_refs``). The credit units
(``handoff_unit``, ``acquired_record_unit``, ``information_unit``) are this episode's ``child_credit_units``. The
child's scope is this episode's scope unless the model chose a narrower one (``arguments['scope']``; the old
``validate_scope(..., parent_scope=)`` is the child's custody of its subjects). One commission adds to it: the
published evidence assessment asked about the aligned homolog takes the problem subjects its question context names
as subjects of its scope (``_literature``).

Required return fields (old ``required_return_sources``): a launch returns ``execution_handoff_refs`` (the old
launch requirement, always here because every commission of this head evaluates a proposed annotation); the monitor
always returns its credit, finding and ``check_refs`` (its required fields), so nothing is added to the model's
selection of its measurements, and its assignment is ``monitor_assignment_v2``: the handoff row and the check rows
of one outstanding job this episode holds, passed in custody (``_monitor``); a recursive child returns
``committed_record_refs``; the result acquisition returns ``execution_blast_graded_refs`` and
``execution_phmmer_graded_refs`` (the graded sheets, their sources and the search rows the A101 credit of this
episode reads).

The two resource children (``resource_work_submission``, ``resource_result_acquisition``) have no commission here:
their forms still take open records only a model could write (``job_request``, ``requested_data_selector``) and an
``execution_handoff_v1`` record this episode holds nowhere, so nothing controlled can be built for them until they
are ported (``BRANCH_FIX_BLOCKERS_head_a101.md``); ``task.py`` does not offer them."""
from episode_runtime import ChildMessage

LAUNCH_VERSION = 'execution_launch_assignment_v1'
MONITOR_VERSION = 'monitor_assignment_v2'
RESULTS_VERSION = 'execution_results_assignment_v1'
LITERATURE_VERSION = 'literature_assignment_v1'
BLAST_REQUEST_VERSION = 'blast_database_grader_return_request_v1'
BLAST_RETURN_TYPE = 'blast_database_sheet_v1'
BLAST_SERVICE = 'ncbi_blast'
# The value of the published evidence assessment's objective vocabulary that asks about the homolog the question
# context names (``task.LITERATURE_OBJECTIVE``).
ALIGNED_HOMOLOG = 'evidence_about_aligned_homolog'

# The objective of each commission: this episode's own text, never the model's.
OBJECTIVES = {
    'execution_job_submission': 'Launch the requested BLAST search of the query on the API resource and return its '
                                'handoff.',
    'execution_progress_assessment': 'Assess the progress of one outstanding job.',
    'execution_result_acquisition': 'Acquire the graded BLAST return of the handed-off job.',
    'literature': 'Assess the published evidence that bears on the assigned question.',
    'sequence_homology_evidence': 'Investigate the sequence-homology evidence of the assigned scope.',
}
# The return fields every commission of a slot selects (the old ``required_return_sources``).
REQUIRED_RETURN = {
    'execution_job_submission': ('execution_handoff_refs',),
    'execution_progress_assessment': (),
    'execution_result_acquisition': ('execution_blast_graded_refs', 'execution_phmmer_graded_refs'),
    'literature': (),
    'sequence_homology_evidence': ('committed_record_refs',),
}


def _scope(arguments, summary):
    return arguments['scope'] if 'scope' in arguments else summary['scope']


def _selection(slot, arguments):
    return tuple(dict.fromkeys([*REQUIRED_RETURN[slot], *arguments.get('selection', [])]))


def _custody(references, summary):
    """The held records ``references`` with every held record they name, and those name in turn (the summary's
    ``named_refs``): a pass carries only the records named, and the child's code follows the names (an observation
    to its source and subjects, a source to its artifacts, a subject to its sequence)."""
    found, pending = [], list(references)
    while pending:
        reference = pending.pop(0)
        if reference not in found:
            found.append(reference)
            pending.extend(summary['named_refs'][reference])
    return found


def _scope_records(scope, summary):
    """The records of a scope within this episode's scope, for custody: its subjects with what they name, and its
    read selections. A child reads the subjects of its scope, so they are always passed."""
    return _custody([*scope['subject_refs'], *scope.get('read_selection_refs', [])], summary)


def _launch(arguments, summary):
    """The launch of one BLAST search on a bound API resource: the BLAST database grader request of that resource
    (the query subject and, when the model constrained one, the database), the query as the launch's scope, the
    query with the held records it names in custody, and the credit units."""
    units = summary['child_credit_units']
    resource_id, query = arguments['resource_id'], arguments['query_subject_ref']
    request = {'version': BLAST_REQUEST_VERSION, 'resource_id': resource_id, 'return_type': BLAST_RETURN_TYPE,
               'query_subject_ref': query}
    if 'database' in arguments:
        request['database'] = arguments['database']
    return {'version': LAUNCH_VERSION, 'requests': {resource_id: request}, 'immutable_input_versions': [],
            'constraints': {}, 'record_refs': _custody([query], summary),
            'handoff_unit': units['handoff_unit'], 'acquired_record_unit': units['acquired_record_unit'],
            'scope': {'subject_refs': [query]}}


def _monitor(arguments, summary):
    """The assignment of the monitor for one outstanding job. The job is passed as records in custody, never by
    name: the handoff row of the job ledger this episode holds (a launch child returned it in
    ``execution_handoff_refs``, or the commissioner passed it) and the check rows of that job it holds (earlier
    monitors returned them in ``check_refs``), as the baseline of the new check. A handoff this episode does not
    hold as an outstanding job fails here with its ``KeyError``."""
    job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[arguments['handoff_ref']]
    return {'version': MONITOR_VERSION, 'handoff_refs': [job['handoff_ref']],
            'known_progress_refs': job['record_refs'][1:], 'dependency_handoff_refs': [],
            'requested_fields': list(arguments['requested_fields']),
            'information_unit': summary['child_credit_units']['information_unit'],
            'blast_status_target': job['blast_status_target']}


def _results(arguments, summary):
    """The acquisition of the graded BLAST return of one job this episode launched and still holds as outstanding.
    Everything is read from what this episode holds: the handoff row (its reference, its job, its resource and
    the identity of its launch: the execution target), the request this episode launched it with (the selector)
    and, in custody, the rows of the job and the query with the held records it names. A handoff this episode did
    not launch, or does not hold as outstanding, fails here with its error."""
    handoff_ref = arguments['handoff_ref']
    job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[handoff_ref]
    request, = (launch['request'] for launch in summary['launches'] if handoff_ref in launch['handoff_refs'])
    query = request['query_subject_ref']
    target = {'version': 'execution_target_v1', 'handle': handoff_ref, 'run_id': job['launch_run_id'],
              'resource_id': job['resource_id'], 'resource_kind': job['kind'], 'execution_id': job['job'],
              'request_sha256': job['job_sha256'], 'origin_episode_id': job['launch_episode_id'],
              'assignment': {'service': BLAST_SERVICE}, 'scope': {'subject_refs': [query]}}
    return {'version': RESULTS_VERSION, 'handoff_ref': handoff_ref, 'selector': request, 'target': target,
            'acquired_record_unit': summary['child_credit_units']['acquired_record_unit'],
            'record_refs': list(dict.fromkeys([*job['record_refs'], *_custody([query], summary)]))}


def _context_subjects(context, summary):
    """The problem subjects the question's context is about: a context record that is one, and those a context
    record names (an alignment observation names the subjects it aligned: its query and its reference)."""
    named = [ref for record in context for ref in (record, *summary['named_refs'][record])]
    return [ref for ref in dict.fromkeys(named) if ref in summary['problem_subject_extents']]


def _with_subjects(scope, subjects, summary):
    """``scope`` with those of the problem subjects ``subjects`` it does not name, each whole: a scope that
    carries segments takes the whole extent of each added subject (``Store.validate_scope`` wants a segment for
    every subject of such a scope)."""
    added = [ref for ref in subjects if ref not in scope['subject_refs']]
    widened = {**scope, 'subject_refs': [*scope['subject_refs'], *added]}
    if 'segments' in scope:
        widened['segments'] = [*scope['segments'],
                               *(part for ref in added for part in summary['problem_subject_extents'][ref])]
    return widened


def _literature(arguments, summary):
    """The literature assignment: the held records the model chose as the question's context, the held sources
    it chose to start from and, by code, the proposed annotation this episode evaluates (the child's credit is
    read for it, as this episode's is, and the child carries it down its own subtree); in custody, those with
    every held record they name, and the records of the child's scope.

    The child's scope is this episode's, or the narrower one the model chose. When the objective asks about the
    aligned homolog (``evidence_about_aligned_homolog``) the problem subjects the question context names are
    subjects of the child's scope too: the homolog is a held operand outside this episode's own scope, the child
    is asked what is published about it, and the child's record lookups answer for the subjects of its scope only
    (``state.query``: ``subject_outside_assigned_scope``). The child's credit is read for the proposed annotation's
    own subjects, so the added subject changes no credit."""
    context = list(arguments['question_context_refs'])
    sources = list(arguments.get('source_refs', []))
    proposed = summary['proposed_annotation_ref']
    scope = _scope(arguments, summary)
    if arguments['objective'] == ALIGNED_HOMOLOG:
        scope = _with_subjects(scope, _context_subjects(context, summary), summary)
    received = [*_custody([*context, *sources, proposed], summary), *_scope_records(scope, summary)]
    return {'version': LITERATURE_VERSION, 'question_context_refs': context, 'source_refs': sources,
            'proposed_annotation_refs': [proposed], 'scope': scope,
            'received_record_refs': list(dict.fromkeys(received))}


def _recursive(arguments, summary):
    """The old ``prepare_invocation`` of the recursive child: the proposed annotation, the constraints and the
    context are inherited; the selection is this episode's own, or, for an alternative approach, the selection and
    revision origin of the ``process_revise`` unit the model named by its position (copied here by code). The
    records of this episode's scope are passed in custody, and the evidence the model chose with every held
    record it names."""
    assignment = {'selection': summary['selection'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'evidence_refs': _custody(arguments['evidence_refs'], summary),
                  'constraints': summary['constraints'], 'context': summary['context'],
                  'scope': _scope(arguments, summary), 'scope_refs': summary['scope_refs'],
                  'proposed_annotation_refs': [summary['proposed_annotation_ref']],
                  'child_credit_units': dict(summary['child_credit_units'])}
    if 'revision_position' in arguments:
        revision, = (item for item in summary['revisions'] if item['position'] == arguments['revision_position'])
        assignment['selection'] = revision['selection']
        assignment['revision_origin'] = revision['revision_origin']
    return assignment


ASSIGNMENTS = {'execution_job_submission': _launch, 'execution_progress_assessment': _monitor,
               'execution_result_acquisition': _results, 'literature': _literature,
               'sequence_homology_evidence': _recursive}


def _message(slot, arguments):
    """What a commission says beside its assignment. The published evidence assessment is told the objective: the
    value of that child's own fixed vocabulary the model chose (``task.LITERATURE_OBJECTIVE``); the child shows
    its model the value with its own meaning of it. The other children are told nothing."""
    if slot == 'literature':
        return {'objective': arguments['objective']}
    return {}


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective=OBJECTIVES[slot], message=_message(slot, arguments),
                        assignment=ASSIGNMENTS[slot](arguments, summary), selection=_selection(slot, arguments))
