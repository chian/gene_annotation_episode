"""What the A102 head sends each of its children (carried from the eight ``to_child_*.py`` files and the
``child_message_owners.py`` role table at ``97308b94c``).

Every old ``to_child_*`` did the same: the model chose the child's goal, purpose, typed return form and initial
report; a required return source had to appear in the form exactly once; the role had to be allowed; the assignment
the model chose was prepared for the child (a monitor's against the monitor's own form; the literature child's with
this parent's own request envelope; the head's own with its filled invocation). Here the parent writes the commission:
the objective is the model's ``goal`` and the ``purpose`` rides in the message (except for ``literature`` and ``monitor``: a fixed objective and an empty message; the monitor's assignment is ``monitor_assignment_v2``, the handoff row and the check rows of one outstanding job this head holds), the typed return form is the selection
of the child's own declared fields (rule 5), and the assignment carries the old assignment keys under their names.
The record references the model names, and the ones this head adds (the proposed annotation, the scope's records),
travel as ``record_refs`` fields: a record this head does not hold fails the commission with ``CustodyError``.

The old roles ``launch`` and ``results`` each had two homes, so each has two slots here (``execution_launch``,
``resource_launch``, ``execution_results``, ``resource_results``). What this head fills beyond the model's choice
(new fields of the children's forms, which the old head did not send because the old children took them from their
runner): ``scope`` for the children whose forms take one, ``credit_unit`` of the literature task
(this head's own ``context.evidence_task.credit_unit``) and the credit units in ``arguments['units']``
(``handoff_unit``, ``completion_target``, ``acquired_record_unit``, ``information_unit``: this head's settings,
read in ``task.action``). A wrong commission raises: an unknown slot is a ``KeyError``, a missing unit or field is a
``KeyError``.

The old closed-commission replay of the head's own invocation (``prepare_invocation`` with ``closed_context``:
journal rows, ``EpisodeReturnRecords``) and the old filled-process record are old-runner machinery, not carried.
"""
from __future__ import annotations

from episode_runtime import ChildMessage

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    LAUNCH_VERSION as RESOURCE_LAUNCH_VERSION, RESULTS_VERSION as RESOURCE_RESULTS_VERSION)

EXECUTION_LAUNCH_VERSION = 'execution_launch_assignment_v1'
EXECUTION_RESULTS_VERSION = 'execution_results_assignment_v1'
LITERATURE_VERSION = 'literature_assignment_v1'
MONITOR_VERSION = 'monitor_assignment_v2'
AXIS = 'A102'


def only(source, names):
    """The optional assignment fields the model supplied."""
    return {name: source[name] for name in names if name in source}


def structural_homology_evidence(chosen, units, summary):
    return {'selection': chosen['selection'], 'evidence_refs': chosen['evidence_refs'],
            'constraints': chosen['constraints'], 'context': summary['context'], 'scope': summary['scope'],
            'scope_refs': summary['scope_refs'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
            **only(chosen, ('revision_origin',))}


def literature(chosen, units, summary):
    received = list(dict.fromkeys([*chosen['received_record_refs'], *summary['proposed_annotation_ref']]))
    return {'version': LITERATURE_VERSION, 'question_context_refs': chosen['question_context_refs'],
            'source_refs': chosen['source_refs'],
            'literature_task': {**chosen['literature_task'], 'evidence_axis': AXIS,
                                'credit_unit': units['credit_unit']},
            'proposed_annotation_ref': summary['proposed_annotation_ref'][0],
            'scope': summary['scope'], 'received_record_refs': received}


def execution_launch(chosen, units, summary):
    return {'version': EXECUTION_LAUNCH_VERSION, 'requests': chosen['requests'],
            'immutable_input_versions': chosen['immutable_input_versions'], 'constraints': chosen['constraints'],
            'scope': summary['scope'], 'handoff_unit': units['handoff_unit'],
            **only(chosen, ('launch_instructions', 'input_refs', 'already_handed_off_resource_ids',
                            'scientific_task'))}


def resource_launch(chosen, units, summary):
    return {'version': RESOURCE_LAUNCH_VERSION, 'work_refs': chosen['work_refs'],
            'input_refs': chosen['input_refs'], 'allowed_kinds': chosen['allowed_kinds'],
            'completion_target': units['completion_target'], **only(chosen, ('resource_id', 'job_refs'))}


def execution_results(chosen, units, summary):
    return {'version': EXECUTION_RESULTS_VERSION, 'handoff_ref': chosen['handoff_ref'],
            'selector': chosen['selector'], 'acquired_record_unit': units['acquired_record_unit'],
            'resource_kind': chosen['resource_kind'], **only(chosen, ('known_result_refs',))}


def resource_results(chosen, units, summary):
    return {'version': RESOURCE_RESULTS_VERSION, 'job_refs': chosen['job_refs'],
            'requested_names': chosen['requested_names']}


def hpc(chosen, units, summary):
    return {'scope': summary['scope'], 'input_refs': chosen['input_refs'],
            **only(chosen, ('commission_id', 'commission_source_ref', 'tool_request'))}


def monitor(chosen, units, summary):
    """The assignment of the monitor for one outstanding job. The job is passed as records in custody, never by
    name: the handoff row of the job ledger this head holds (a launch child returned it, or the commissioner
    passed it) and the check rows of that job it holds (earlier monitors returned them in ``check_refs``), as the
    baseline of the new check. A handoff this head does not hold as an outstanding job fails here with its
    ``KeyError``."""
    job = {item['handoff_ref']: item for item in summary['outstanding_jobs']}[chosen['handoff_ref']]
    return {'version': MONITOR_VERSION, 'handoff_refs': [job['handoff_ref']],
            'known_progress_refs': job['record_refs'][1:], 'dependency_handoff_refs': [],
            'requested_fields': list(chosen['requested_fields']), 'information_unit': units['information_unit']}


ASSIGNMENTS = {'structural_homology_evidence': structural_homology_evidence, 'literature': literature,
               'execution_launch': execution_launch, 'resource_launch': resource_launch,
               'execution_results': execution_results, 'resource_results': resource_results, 'hpc': hpc,
               'monitor': monitor}


# No text passes to the literature child: its objective is fixed by the slot and its message is empty (controlled
# messaging; the model chooses only the assignment and the selection).
LITERATURE_OBJECTIVE = 'assess_published_evidence'
# Nor to the monitor: the model chooses the held handoff record, the fields to observe and the selection.
MONITOR_OBJECTIVE = 'assess_job_progress'


def msg_to_child(slot, arguments, summary):
    assignment = ASSIGNMENTS[slot](arguments['assignment'], arguments['units'], summary)
    if slot == 'literature':
        return ChildMessage(objective=LITERATURE_OBJECTIVE, message={}, assignment=assignment,
                            selection=tuple(arguments['selection']))
    if slot == 'monitor':
        return ChildMessage(objective=MONITOR_OBJECTIVE, message={}, assignment=assignment,
                            selection=tuple(arguments['selection']))
    return ChildMessage(objective=arguments['goal'], message={'purpose': arguments['purpose']},
                        assignment=assignment, selection=tuple(arguments['selection']))
