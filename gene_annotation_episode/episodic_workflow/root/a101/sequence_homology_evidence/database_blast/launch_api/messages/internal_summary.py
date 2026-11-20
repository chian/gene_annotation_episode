"""Where the launch stands, as a pure function of the view: the commission, the query read from the held records, each
submission made (whether the service accepted it, and for a failure its code, whether the request was sent and how
long the service asks to be left alone) and the handoff rows the episode holds."""


def internal_summary(view):
    parent, records = view.parent_input, view.records
    subject = parent['query_subject_ref']
    summary = {**parent,
               'query': {'subject_ref': subject, 'sequence_ref': records.get(subject)['sequence_ref'],
                         'molecule': records.subject_molecule(subject), 'length': records.subject_length(subject)},
               'submissions': [], 'handoff_refs': [],
               'credit': 0.0 if view.controller_state is None else view.controller_state.current_credit}
    for unit in view.outcomes:
        outcome = unit['outcome']
        summary['submissions'].append({'status': outcome['status'], 'failure_code': outcome['failure_code'],
                                       'sent': outcome['sent'], 'retry_after_seconds': outcome['retry_after_seconds']})
        summary['handoff_refs'].extend(outcome['handoff_refs'])
    return summary
