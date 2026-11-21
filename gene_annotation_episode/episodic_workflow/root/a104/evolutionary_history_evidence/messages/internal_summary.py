"""Where the episode stands: the parent input, what its units did, what its children returned, the A104 credit view
of the records it holds, the controller state and the working state of the Store, from the loop's view.

Carried from the old ``internal_summary.py`` (``decision_context``: ``selection``, ``initial_selection_sha256``,
``assignment``, ``permitted_children``; the library views of the axis, the thought pattern and the tools need the
frozen libraries, they are added by ``decide`` from the settings; ``_component_scoring_facts`` and
``current_report_facts`` are ``{}``) and from the old ``decision_context.py`` and ``decision_inputs.py`` (current
credit, evidence vector, credit binding, working state, visible record references, last local outcome, feedback,
controller state). Pure: no clock, no service, no state between calls."""
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.construction_records import (
    scientific_digest)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.finding import (
    sheet_features, target_features)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import outstanding_jobs

from ..credit import credit_projector, credit_view

PERMITTED_CHILDREN = ('evolutionary_history_evidence', 'hpc')
OWN = 'evolutionary_history_evidence'
FORECAST_UNIT = 'one unit of A104 evolutionary-history credit'
CREDIT_VIEW_FIELDS = ('credit', 'target_sheets', 'source_contribution_count')


def _unit_row(position, outcome):
    row = {'position': position, 'kind': outcome['kind']}
    if outcome['kind'] == 'tool':
        row.update(tool=outcome['tool'], status=outcome['outcome'].get('status'))
    else:
        row.update(slot=outcome['slot'], ended_by=outcome['completion']['ended_by'])
    return row


def internal_summary(view):
    parent = view.parent_input
    outcomes = list(view.outcomes)
    last = outcomes[-1] if outcomes else None
    produced, committed, child_returns, child_sheets = [], [], [], []
    failed = 0
    for outcome in outcomes:
        produced.extend(ref for ref in outcome.get('produced', ()) if ref not in produced)
        if outcome['kind'] == 'tool':
            status = outcome['outcome'].get('status')
            failed += status not in ('completed', 'partial')
            if outcome['tool'] == 'reason':
                committed.extend(ref for ref in outcome.get('produced', ()) if ref not in committed)
        else:
            child_returns.append({'slot': outcome['slot'], **outcome['report']})
            if outcome['slot'] == OWN:
                child_sheets.extend(outcome['report']['finding']['sheets'])
    feedback = None
    if last is not None and last['kind'] == 'tool' and last['outcome'].get('status') not in ('completed', 'partial'):
        feedback = last['outcome'].get('feedback')
    summary = {**parent,
               'goal': view.goal.as_record(),
               'path_depth': len(view.path),
               'units_consumed': view.units_consumed,
               'unit_index': [_unit_row(position, outcome) for position, outcome in enumerate(outcomes)],
               'last_outcome': last,
               'last_feedback': feedback,
               'failed_units': failed,
               'child_returns': child_returns,
               'produced_refs': produced,
               'committed_record_refs': committed,
               # the jobs whose handoff row this episode holds and whose closure row it does not hold, with the
               # check rows it holds of each: what a monitor commission passes in custody
               'outstanding_jobs': outstanding_jobs(view.records),
               'initial_selection_sha256': scientific_digest(parent['selection']),
               'permitted_children': list(PERMITTED_CHILDREN),
               'reasoning_schema': view.records.reasoning_schema(),
               'visible_record_refs': list(view.records.refs())}
    projected = credit_view(summary, view.records)
    summary.update(credit_view={name: projected[name] for name in CREDIT_VIEW_FIELDS if name in projected},
                   a104_sheets=[*sheet_features(view.records, produced), *child_sheets],
                   a104_targets=target_features(projected),
                   credit_binding=credit_projector(parent).as_record(),
                   working_state=view.records.reasoning_view(parent['scope']),
                   controller=None if view.controller_state is None
                   else yield_table(view.controller_state, forecast_unit=FORECAST_UNIT))
    return summary
