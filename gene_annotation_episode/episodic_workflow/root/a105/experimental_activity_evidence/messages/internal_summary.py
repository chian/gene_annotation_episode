"""Where the A105 head stands, as a pure function of the loop's view: the commission (the selection, the proposed
annotation, the records given, the constraints, the finding task and its unit, the revision origin and the scope),
the records it holds, its working state, its finding progress and credit definition, its own outcomes, the
controlled features of the current grading and aggregation sheets it saved and its children returned, the examined
spans of a no-applicable-evidence declaration, the returns of the children it commissioned (their credit and the
counts of their findings) and the controller state.

Carried from the old ``internal_summary.py`` (``ScientificSummary.decision_context``), ``decision_inputs.py``
(``working_state``, ``visible_record_refs``, ``current_credit``, ``investigation_progress``, ``credit_binding``,
``controller``, ``last_local_outcome``, ``time_accounting``) and ``to_parent.py`` (the committed records). The old
reads of ``runtime_actions``, ``runtime_forms`` and the receipt ledger are the unit outcomes of ``view`` (a tool
unit's outcome, a child unit's ``report``) and the records this Episode holds."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    no_applicable_spans)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, finding_progress

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size


def committed(view):
    """The assessments and sheets the head's own ``reason`` units committed (the old committed records)."""
    refs = []
    for outcome in view.outcomes:
        if outcome['kind'] == 'tool' and outcome['tool'] == 'reason':
            refs.extend(ref for ref in outcome['outcome']['record_refs']
                        if ref.startswith(('assessment_', 'source_')) and ref not in refs)
    return refs


def internal_summary(view):
    parent = view.parent_input
    records = view.records
    unit = parent['evidence_task']['credit_unit']
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    last = view.outcomes[-1] if view.outcomes else None
    tools = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    # The sheet: what the latest child returned (the whole subscoring sheet as it stands after it, from the states this
    # episode passed to it); before any child returned, the states this episode was given, no scores, no features.
    sheet_state_refs = children[-1]['report']['sheet_state_refs'] if children else parent['sheet_state_refs']
    working_state = records.reasoning_view(parent['scope'])
    # The Store lists the context sources of the problem and of the subjects whether or not this episode holds them;
    # the model is shown only the ones it holds.
    working_state['supplied_context_source_refs'] = [
        ref for ref in working_state['supplied_context_source_refs'] if records.holds(ref)]
    return {
        **{name: parent[name] for name in ('selection', 'proposed_annotation_ref', 'evidence_refs', 'constraints',
                                           'evidence_task', 'revision_origin', 'scope')},
        'held_record_refs': sorted(records.refs()),
        'working_state': working_state,
        'reasoning_schema': records.reasoning_schema(),
        'progress': finding_progress(records, parent['scope'], unit), 'credit_binding': credit_binding(unit),
        'own_outcomes': outcome_page(tools, offset=0, limit=OUTCOME_PAGE_SIZE),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_returns': [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                           'credit': outcome['report']['credit'], 'scores': outcome['report']['scores'],
                           'features': outcome['report']['features']}
                          for outcome in children],
        'sheet_state_refs': sheet_state_refs,
        'given_sheet_state_refs': list(parent['sheet_state_refs']),
        'scores': children[-1]['report']['scores'] if children else [],
        'features': children[-1]['report']['features'] if children else [],
        'no_applicable_spans': no_applicable_spans(view.outcomes, records),
        'committed_record_refs': list(dict.fromkeys([
            *committed(view), *(ref for outcome in children for ref in outcome['report']['committed_record_refs']),
            *sheet_state_refs])),
    }
