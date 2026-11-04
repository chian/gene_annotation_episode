"""Present exact operational operands to HPC episodes and their Launch children."""
from __future__ import annotations

import json
from collections.abc import Mapping


def is_hpc_context(state):
    return isinstance(state, Mapping) and (
        'hpc_commission' in state or 'hpc_portfolio_preparation' in state)


def render_hpc_prompt(state, instructions, *, lookup_results=()):
    # These identities, file bytes and native argv are executable operands.
    # The generic scientific prose renderer omits them; do not send this task
    # through that renderer or reconstruct bytes from conversational summaries.
    supplied = dict(state)
    gate = state.get('hpc_activity_decision')
    if gate:
        supplied['tools'] = [row for row in state.get('tools', ()) if row['name'] in gate['allowed_tools']]
        supplied.pop('child_options', None)
    sources = {'episode_yield', 'credit', 'execution_completed', 'execution_handoff_refs',
               'execution_result_refs', 'committed_record_refs', 'changed_record_refs'}

    def requested(value):
        if isinstance(value, Mapping):
            if isinstance(value.get('x-source'), str):
                sources.add(value['x-source'])
            for child in value.values():
                requested(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                requested(child)

    requested(state.get('requested_form'))
    supplied['available_report_facts'] = {key: value for key, value in
        state.get('available_report_facts', {}).items() if key in sources or key.startswith('hpc_')}
    if lookup_results:
        supplied['lookup_results'] = list(lookup_results)
    return ('TASK\n'+instructions+'\n\nThis is an operational HPC task. '
        'Use the permitted tools and child episodes; do not manufacture biological observations '
        'to report an operational issue. The frozen preparation payload below is directly available '
        'to both Launch and launch_hpc. Do not copy its file contents into a child goal. '
        'Preserve exact file contents, identifiers and argv.\n\nSupplied operational operands (JSON):\n'+
        json.dumps(supplied, ensure_ascii=False, allow_nan=False))
