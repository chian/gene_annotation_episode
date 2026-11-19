"""Where the job stands: the commission, every operation run so far, the handoffs and results it established.

Carried from the old ``internal_summary.py`` (``decision_context``: ``execution_assignment``, ``execution_progress``
= the facts), ``api_service.py`` (``facts``, ``decision_context``: the latest received event of each operation,
``api_execution_completed``, ``_completion``), ``hmmer_service.py`` / ``appservice_submission.py`` (``facts``,
``completion``) and ``credit.py`` (the old credit view's non-number fields). A pure function of the view: what the
old service read back from its own files and from the Store is in the outcomes of the tool units.

The tool outcome this reads is the one ``task.launch_operation`` returns."""

OPERATIONAL_CREDIT_BINDING = {'version': 'execution_episode_v1', 'scientific_credit': False,
                              'monitoring_credit': False}


def _initial_identities(parent_input):
    """The (resource_id, execution_id) handoffs and result identities among the records the commission passed.

    The old code read each initial reference back as a handoff target or a result identity. A handoff is now a row
    of the job record (the work table of the job records), whose kind is not defined yet."""
    rows = [ref for ref in parent_input['input_refs'] if ref.startswith('row_')]
    if rows:
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job record kind (handoff row of the job ledger); wanted '
                                  'call: records.table(JOB_LEDGER).get(row_ref) for ' + repr(rows))
    return [], []


def internal_summary(view):
    parent = view.parent_input
    initial_handoffs, initial_results = _initial_identities(parent)
    operations, handoff_refs, handoff_identities = [], [], []
    result_refs, result_identities, progress = [], [], {}
    uncertain = completed = False
    for unit in view.outcomes:
        outcome = unit['outcome']
        operations.append({'operation': outcome['operation'], 'status': outcome['status'],
                           'submission_outcome': outcome['submission_outcome']})
        if outcome['submission_outcome'] == 'unknown':
            uncertain = True
        if outcome['event'] is not None:
            progress[outcome['operation']] = {key: outcome['event'][key] for key in
                                              ('state', 'kind', 'facts', 'failure_code')}
        if outcome['status'] in ('completed', 'partial'):
            if outcome['handoff_ref'] is not None:
                handoff_refs.append(outcome['handoff_ref'])
                handoff_identities.append(outcome['job'])
            result_refs.extend(outcome['result_refs'])
            result_identities.extend(outcome['result_identities'])
        if outcome['status'] == 'completed' and outcome['handoff_ref'] is not None:
            completed = True
    return {'assignment': parent['assignment'], 'input_refs': parent['input_refs'],
            'handoff_unit': parent['handoff_unit'], 'acquired_record_unit': parent['acquired_record_unit'],
            'scientific_question': parent['scientific_question'], 'selected_tool_info': parent['selected_tool_info'],
            'operations': operations, 'received_progress': progress,
            'handoff_refs': list(dict.fromkeys(handoff_refs)),
            'handoff_identities': [list(identity) for identity in
                                   {tuple(identity): None for identity in handoff_identities}],
            'result_refs': list(dict.fromkeys(result_refs)),
            'result_identities': [list(identity) for identity in
                                  {tuple(identity): None for identity in result_identities}],
            'initial_handoff_identities': initial_handoffs, 'initial_result_identities': initial_results,
            'completed': completed, 'submission_uncertain': uncertain,
            'operational_credit_binding': {**OPERATIONAL_CREDIT_BINDING, 'handoff_unit': parent['handoff_unit'],
                                           'acquired_record_unit': parent['acquired_record_unit']}}
