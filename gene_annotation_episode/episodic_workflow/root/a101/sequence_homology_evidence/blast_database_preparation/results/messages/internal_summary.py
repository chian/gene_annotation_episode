"""Where the results stand, as a pure function of the view: the commission (the parent input), what each unit did,
the last acquisition's job state while the job has not ended, and the prepared-data record once written (its
reference, state, whether it is usable, its failure codes and its controlled features)."""


def internal_summary(view):
    parent = view.parent_input
    acquisitions, prepared, last_tool, state = 0, None, None, None
    for unit in view.outcomes:
        last_tool = unit['tool']
        outcome = unit['outcome']
        if unit['tool'] == 'prepared_data_acquire':
            acquisitions += 1
            if outcome['status'] == 'completed' and outcome['prepared'] is not None:
                prepared = outcome['prepared']
            state = outcome.get('state') if outcome['status'] == 'completed' else 'refused'
    return {'handoff_ref': parent['handoff_ref'], 'declared_kind': parent['declared_kind'],
            'prepared_unit': parent['prepared_unit'], 'acquisitions': acquisitions, 'last_tool': last_tool,
            'job_state': state, 'prepared': prepared,
            'prepared_refs': [] if prepared is None else [prepared['ref']]}
