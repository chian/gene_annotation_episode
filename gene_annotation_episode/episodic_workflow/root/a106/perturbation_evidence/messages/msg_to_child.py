"""The commissions of this episode's five children (carried from the old ``to_child_published_evidence_assessment.py``
(role ``literature``), ``to_child_execution_job_submission.py`` (role ``launch``), ``to_child_execution_progress_
assessment.py`` (role ``monitor``), ``to_child_execution_result_acquisition.py`` (role ``results``) and
``to_child_perturbation_evidence.py`` (the recursive role) at 97308b94c).

The old ``prepare_*`` validated the child scope, expanded the report contract form from the fact sources the child
binding required, checked the initial report against the interpretation schema, checked the role against the allowed
children, checked the binding path, materialized the launch instructions and let the child binding's
``prepare_assignment`` build the child's assignment from the model's assignment. Here each child declares what it
returns and this commission selects the fact sources it wants (the old fact-source names: the ones the old
``required_return_sources`` required and the ones the model asks for in ``return_facts``); the assignment is the
child's own: nothing is checked here, a commission the child does not admit fails, and a record this episode does not
hold fails the run. The child's scope is this episode's own (the old model-selected sub-scope is not carried).

``literature``: ``literature_assignment_v1`` from the model's records and the one task, ``verified_source_leads`` (the
task's ``credit_unit`` is this episode's own, where the old child binding filled it), the proposed annotation of this
episode (a child may not change it), the scope and every record this episode names for the child: the question context
and the proposed annotation. No source is named: a paper reaches the chain only through its search.

``launch``: ``execution_launch_assignment_v1`` from the model's arguments, the scope and ``handoff_unit`` which
``task.action`` took from the settings; the resources that already have a usable handoff from earlier launches of this
episode are passed as ``received_handoff_resources`` (the old initial known handoff records).

``monitor``: ``monitor_assignment_v2`` for one job this episode holds as outstanding (``summary['outstanding_jobs']``):
the job's handoff row of the job ledger and the check rows of it this episode holds, passed in custody, the fields
the model asked to be observed and ``information_unit`` which ``task.action`` took from the settings. The model names
the job by its held handoff reference; it writes no assignment.

``results``: ``execution_results_assignment_v1`` (the handoff, named in custody, the selector and the API service of
the original job).

``perturbation_evidence``: the old ``prepare_invocation``: the selection and revision origin of a ``process.revise``
preparation, the proposed annotation inherited from this episode, the records of evidence and the constraints the
model chose (this episode's own when it chose none), this episode's task context, the scope and the records the
child reads through them. The closed-commission replay of the old method is the system's resume."""
from episode_runtime import ChildMessage

LITERATURE_VERSION = 'literature_assignment_v1'
LAUNCH_VERSION = 'execution_launch_assignment_v1'
MONITOR_VERSION = 'monitor_assignment_v2'
RESULTS_VERSION = 'execution_results_assignment_v1'
# The sources the old ``required_return_sources`` of each child binding required, plus the ones that keep this
# episode's summary informed (a launch's completion). A monitor always returns its credit, its finding and its
# check rows (``check_refs``); nothing more of it is required here.
REQUIRED = {'literature': (), 'launch': ('execution_handoff_refs',), 'monitor': (),
            'results': (), 'perturbation_evidence': ('perturbation_evidence_results', 'committed_record_refs')}
ALWAYS = {'literature': (), 'launch': ('execution_completed',), 'monitor': (),
          'results': ('execution_completed',), 'perturbation_evidence': ()}


def selection(slot, arguments, *extra):
    """The selected return fields: those the old binding required, those this episode's summary reads and those
    the model asked for, once each and in a fixed order."""
    return tuple(dict.fromkeys((*REQUIRED[slot], *ALWAYS[slot], *extra, *arguments.get('return_facts', ()))))


def literature(arguments, summary):
    task = {**arguments['literature_task'], 'credit_unit': summary['task']['credit_unit']}
    received = [*arguments['question_context_refs'], summary['proposed_annotation_ref']]
    assignment = {'version': LITERATURE_VERSION, 'question_context_refs': arguments['question_context_refs'],
                  'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'scope': summary['scope'], 'received_record_refs': list(dict.fromkeys(received))}
    return assignment, selection('literature', arguments, 'literature_source_lead_dispositions')


def launch(arguments, summary):
    assignment = {'version': LAUNCH_VERSION, 'requests': arguments['requests'],
                  'immutable_input_versions': arguments['immutable_input_versions'],
                  'constraints': arguments['constraints'], 'scope': summary['scope'],
                  'handoff_unit': arguments['handoff_unit']}
    if arguments.get('launch_instructions') is not None:
        assignment['launch_instructions'] = arguments['launch_instructions']
    if 'record_refs' in arguments:
        assignment['record_refs'] = arguments['record_refs']
    if summary['handoff_resources']:
        assignment['received_handoff_resources'] = summary['handoff_resources']
    return assignment, selection('launch', arguments)


def monitor(arguments, summary):
    """The commission of the monitor for one outstanding job. The job is passed as records in custody, never by
    name: the handoff row of the job ledger this episode holds and the check rows of that job it holds (earlier
    monitors returned them in ``check_refs``), as the baseline of the new check. A handoff this episode does not
    hold as an outstanding job fails here with its ``KeyError``."""
    job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[arguments['handoff_ref']]
    assignment = {'version': MONITOR_VERSION, 'handoff_refs': [job['handoff_ref']],
                  'known_progress_refs': job['record_refs'][1:], 'dependency_handoff_refs': [],
                  'requested_fields': list(arguments['requested_fields']),
                  'information_unit': arguments['information_unit']}
    return assignment, selection('monitor', arguments)


def results(arguments, summary):
    assignment = {'version': RESULTS_VERSION, 'handoff_ref': [arguments['handoff_ref']],
                  'selector': arguments['selector'], 'service': arguments['service']}
    return assignment, selection('results', arguments)


def own_kind(arguments, summary):
    evidence = arguments.get('evidence_refs', summary['evidence_refs'])
    assignment = {'selection': arguments['selection'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'evidence_refs': evidence, 'constraints': arguments.get('constraints', summary['constraints']),
                  'context': summary['context'], 'revision_origin': arguments['revision_origin'],
                  'scope': summary['scope'],
                  'received_record_refs': list(dict.fromkeys([summary['proposed_annotation_ref'], *evidence,
                                                              *summary['received_record_refs']]))}
    return assignment, selection('perturbation_evidence', arguments)


COMMISSIONS = {'literature': literature, 'launch': launch, 'monitor': monitor, 'results': results,
               'perturbation_evidence': own_kind}
# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVES = {'literature': 'assess_published_evidence', 'launch': 'launch_execution_requests',
              'monitor': 'assess_execution_progress', 'results': 'acquire_execution_results',
              'perturbation_evidence': 'revise_perturbation_process'}


def msg_to_child(slot, arguments, summary):
    assignment, selected = COMMISSIONS[slot](arguments, summary)
    return ChildMessage(objective=OBJECTIVES[slot], message={},
                        assignment=assignment, selection=selected)
