"""Present assigned monitoring data without unrelated scientific fact catalogs."""
from collections.abc import Mapping
import json

from .episode_work_report import render_completed_action_reports


def is_monitor_context(state):
    assignment = state.get('monitor_assignment') if isinstance(state, Mapping) else None
    return isinstance(assignment, Mapping) and assignment.get('version') == 'monitor_assignment_v1'


def _requested_sources(value):
    if isinstance(value, Mapping):
        if isinstance(value.get('x-source'), str):
            yield value['x-source']
        for child in value.values():
            yield from _requested_sources(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _requested_sources(child)


def render_monitor_prompt(state, instructions, *, lookup_results=()):
    requested = set(_requested_sources(state.get('requested_form')))
    requested.update(('episode_yield', 'credit', 'committed_record_refs',
        'changed_record_refs', 'interpretation_basis_refs', 'observations_after_report_basis'))
    # These are report-source definitions, not scientific observations. Preserve
    # every definition selected by the actual form and the monitoring interface.
    contracts = {name: value for name, value in state.get('available_report_facts', {}).items()
        if name in requested or name.startswith('monitoring_')}
    visible = {name: value for name, value in state.items()
        if name not in ('available_report_facts', 'completed_action_reports')}

    def saved(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))

    sections = ['TASK\n' + instructions, 'Actual monitor state\n' + saved(visible)]
    if 'completed_action_reports' in state:
        sections.append(render_completed_action_reports(state['completed_action_reports']))
    if contracts:
        sections.append('Selected report fact contracts\n' + saved(contracts))
    if lookup_results:
        sections.append('Explicitly requested information\n' + saved(lookup_results))
    return '\n\n'.join(sections)
