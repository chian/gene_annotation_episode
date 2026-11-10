"""Attribute a selected wider child report to its actual evidence acquisition.

The original child has already completed. Receiving an additional saved subset
is this selected action; merely reformatting held evidence is not another
controller observation. Receipt changes and the new observation's input commit
together, without revising the original child completion.
"""
from __future__ import annotations

import json

from method_loop.durable import canonical

from .episode_journal import WorkflowError


def _custody(workflow, source):
    return {
        'record_refs': set(() if workflow.receipts is None else
                           workflow.receipts.known(source.episode_id)),
        'progress_refs': set(() if workflow.progress_provider is None else
            workflow.progress_provider.received_progress_refs(source.episode_id)),
        'evidence_tokens': set(workflow.episode_bindings.received_evidence_tokens(
            workflow.binding_context(source))),
    }


def acquire_report_evidence(workflow, source, selection, index, *,
                            original_attempt, admitted, schema):
    """Receive a selected report and freeze its own input iff custody expands.

    The caller has validated and saved this exact typed report attempt. Replay
    uses its recorded result; it never revalues either the original child or
    this acquisition against later sibling information.
    """
    from .runtime import Record

    journal = workflow.journal
    origin = {'child_episode_id': original_attempt['child_episode_id'],
              'original_decision_index': original_attempt['decision_index'],
              'delivery_ref': original_attempt['delivery_ref']}
    if (selection.get('kind') != 'redeliver_report'
            or selection.get('delivery_ref') != origin['delivery_ref']
            or index <= origin['original_decision_index']):
        raise WorkflowError('report_acquisition_origin_conflict')
    with workflow.store.transaction():
        original = journal.row('runtime_actions', source.episode_id,
                               origin['original_decision_index'])
        if (original is None or original['result'] is None or original['credit'] is None
                or json.loads(original['result']).get('status') != 'completed'):
            raise WorkflowError('report_acquisition_requires_completed_original_child')
        old = journal.row('runtime_actions', source.episode_id, index)
        if old is not None:
            if canonical(json.loads(old['action'])) != canonical(selection):
                raise WorkflowError('report_acquisition_selection_conflict')
            if old['result'] is not None:
                outcome = json.loads(old['result'])
                if outcome.get('report_origin') != origin:
                    raise WorkflowError('report_acquisition_origin_conflict')
                if outcome['status'] == 'delivery_only':
                    return None
                if outcome['status'] != 'completed' or old['credit'] is None:
                    raise WorkflowError('report_acquisition_completion_conflict')
                source.last_outcome, source.last_outcome_index = outcome, index
                return Record(outcome['controller_input'])
        journal.save('runtime_actions', {'episode_id': source.episode_id,
            'decision_index': index, 'action': canonical(selection), 'result': None, 'credit': None})
        with journal.measure('runtime_actions', source.episode_id, index):
            before = _custody(workflow, source)
            references = workflow.receive_form(source, admitted.as_record(), schema, index,
                                                redelivery=True)
            after = _custody(workflow, source)
            additions = {key: sorted(after[key] - before[key]) for key in before}
            acquired = any(additions.values())
            outcome = {'status': 'completed' if acquired else 'delivery_only',
                'record_refs': references, 'changed_record_refs': [],
                'progress_refs': additions['progress_refs'], 'report_origin': origin,
                'received_evidence_additions': additions}
            if acquired and (workflow.execution_binding is not None
                    or workflow.wait_inputs_version == 'wait_inputs_binding_v2'
                    or workflow.completed_action_inputs_version is not None):
                outcome['pending_work_after_action'] = workflow.pending_work(source)
            # Host projections can consult the recorded own outcome. Publish
            # it inside this transaction before projecting actual parent credit.
            journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': index, 'action': canonical(selection),
                'result': canonical(outcome), 'credit': None})
            if not acquired:
                return None
            credit = workflow.source_credit_view(source)['credit']
            controller_input = workflow.controller_value(source, index, credit)
            outcome['controller_input'] = controller_input.as_record()
            journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': index, 'action': canonical(selection),
                'result': canonical(outcome), 'credit': credit})
        if workflow.execution_binding is not None:
            workflow.completions.stage(source.episode_id, index,
                label=f'redeliver_report:{index}', kind='own_action',
                controller_input=controller_input, child_return=None)
        source.last_outcome, source.last_outcome_index = outcome, index
        return controller_input
