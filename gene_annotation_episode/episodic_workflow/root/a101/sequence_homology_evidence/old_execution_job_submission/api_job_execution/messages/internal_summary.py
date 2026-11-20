"""Where the launch stands, from the loop's view: the assigned job with its query read from the held records, the
submissions made (the built request, whether the service accepted it, and for a failure its code and whether the
request was sent), the handoff rows it holds, the lookups and what they returned, and the credit its controller
holds."""


def internal_summary(view):
    parent, records = view.parent_input, view.records
    subject = parent['query_subject_ref']
    summary = {**parent,
               'query': {'subject_ref': subject, 'sequence_ref': records.get(subject)['sequence_ref'],
                         'molecule': records.subject_molecule(subject), 'length': records.subject_length(subject)},
               'submissions': [], 'lookups': [], 'handoff_refs': [],
               'credit': 0.0 if view.controller_state is None else view.controller_state.current_credit}
    for unit in view.outcomes:
        outcome = unit['outcome']
        if unit['tool'] == 'submit':
            summary['submissions'].append({
                'request': unit['arguments']['request'], 'status': outcome['status'],
                'failure_code': outcome['failure_code'], 'sent': outcome['sent'],
                'retry_after_seconds': outcome['retry_after_seconds']})
            summary['handoff_refs'].extend(outcome['handoff_refs'])
        else:
            summary['lookups'].append({'tool': unit['tool'], 'operation': unit['arguments']['operation'],
                                       'arguments': unit['arguments']['arguments'], 'status': outcome['status'],
                                       'result': outcome['result'], 'feedback': outcome['feedback']})
    return summary
