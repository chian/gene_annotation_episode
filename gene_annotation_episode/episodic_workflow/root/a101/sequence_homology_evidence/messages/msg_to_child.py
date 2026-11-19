"""The commission of each child (the old ``to_child_<role>.py``: ``to_child_sequence_homology_evidence``,
``to_child_published_evidence_assessment``, ``to_child_execution_job_submission``,
``to_child_execution_progress_assessment``, ``to_child_execution_result_acquisition``,
``to_child_resource_result_acquisition``, ``to_child_resource_work_submission``).

The old ``prepare_*`` expanded the parent's report-contract form from the fact sources the child required, checked
the child role and binding path, materialized the launch instructions and let the child binding's
``prepare_assignment`` build the assignment. None of that is a commission now: this file writes the child's
assignment from the model's arguments (the child's own properties, under the child's own names) and this episode's
own values, selects the return fields the old ``required_return_sources`` required plus the ones the model wanted,
and a commission the child does not admit fails (no check here).

Every record the child's code reads is named in a ``record_refs`` field of the model's assignment (named records
this episode does not hold fail the run). The credit units the old configuration gave the children
(``handoff_unit``, ``acquired_record_unit``, ``information_unit``) and the work-submission completion target are
this episode's ``child_credit_units``. The child's scope is this episode's scope unless the model chose a narrower
one (``arguments['scope']``; the old ``validate_scope(..., parent_scope=)`` is the child's custody of its
subjects).

Required return fields (old ``required_return_sources``): a launch returns ``execution_handoff_refs`` (the old
launch requirement, always here because every commission of this head evaluates a proposed annotation); the monitor
returns ``monitoring_progress_refs``; a recursive child returns ``committed_record_refs``; the result acquisition
returns ``execution_blast_graded_refs`` and ``execution_phmmer_graded_refs`` (the graded sheets, their sources and the search rows the A101 credit of
this episode reads)."""
from episode_runtime import ChildMessage

LAUNCH_VERSION = 'execution_launch_assignment_v1'
MONITOR_VERSION = 'monitor_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
LITERATURE_VERSION = 'literature_assignment_v1'
RESOURCE_RESULTS_VERSION = 'resource_results_assignment_v1'
RESOURCE_LAUNCH_VERSION = 'resource_launch_assignment_v1'


def _scope(arguments, summary):
    return arguments['scope'] if 'scope' in arguments else summary['scope']


def _scope_refs(scope):
    return list(dict.fromkeys([*scope['subject_refs'], *scope.get('read_selection_refs', [])]))


def _selection(arguments, required):
    return tuple(dict.fromkeys([*required, *arguments.get('selection', [])]))


def _launch(arguments, summary):
    units = summary['child_credit_units']
    return {'version': LAUNCH_VERSION, **arguments['assignment'], 'handoff_unit': units['handoff_unit'],
            'acquired_record_unit': units['acquired_record_unit'], 'scope': _scope(arguments, summary)}


def _monitor(arguments, summary):
    return {'version': MONITOR_VERSION, **arguments['assignment'],
            'information_unit': summary['child_credit_units']['information_unit']}


def _results(arguments, summary):
    return {'version': RESULTS_VERSION, **arguments['assignment'],
            'acquired_record_unit': summary['child_credit_units']['acquired_record_unit']}


def _literature(arguments, summary):
    given = arguments['assignment']
    received = list(dict.fromkeys([*given['question_context_refs'], *given['source_refs']]))
    return {'version': LITERATURE_VERSION, **given, 'scope': _scope(arguments, summary),
            'received_record_refs': received}


def _resource_results(arguments, summary):
    return {'version': RESOURCE_RESULTS_VERSION, **arguments['assignment']}


def _resource_work(arguments, summary):
    scope = _scope(arguments, summary)
    return {'version': RESOURCE_LAUNCH_VERSION, **arguments['assignment'], 'scope': scope,
            'scope_refs': _scope_refs(scope),
            'completion_target': summary['child_credit_units']['completion_target']}


def _recursive(arguments, summary):
    """The old ``prepare_invocation`` of the recursive child: the proposed annotation is inherited and the
    selection (and revision origin of an alternative approach) is the model's, copied from ``process_revise``."""
    scope = _scope(arguments, summary)
    given = arguments['assignment']
    if given.get('proposed_annotation_ref', summary['proposed_annotation_ref']) != summary['proposed_annotation_ref']:
        raise ValueError('child_proposed_annotation_differs_from_original_task')
    return {**given, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
            'proposed_annotation_refs': [summary['proposed_annotation_ref']], 'scope': scope,
            'scope_refs': _scope_refs(scope), 'child_credit_units': dict(summary['child_credit_units'])}


ASSIGNMENTS = {'execution_job_submission': _launch, 'execution_progress_assessment': _monitor,
               'execution_result_acquisition': _results, 'published_evidence_assessment': _literature,
               'resource_result_acquisition': _resource_results, 'resource_work_submission': _resource_work,
               'sequence_homology_evidence': _recursive}


def msg_to_child(slot, arguments, summary):
    assignment = ASSIGNMENTS[slot](arguments, summary)
    if slot in ('execution_job_submission', 'resource_work_submission'):
        required = ('execution_handoff_refs',)
    elif slot == 'execution_progress_assessment':
        required = ('monitoring_progress_refs',)
    elif slot == 'execution_result_acquisition':
        required = ('execution_blast_graded_refs', 'execution_phmmer_graded_refs')
    elif slot == 'sequence_homology_evidence':
        required = ('committed_record_refs',)
    else:
        required = ()
    return ChildMessage(objective=arguments['objective'], message={'purpose': arguments['message']},
                        assignment=assignment, selection=_selection(arguments, required))
