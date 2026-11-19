"""Where the A103 head stands, as a pure function of the loop's view: the assignment, the selected process (the
evidence axis and thought pattern entries and the tool catalog, once obtained), the current credit view, the first page
of the episode's own outcomes, the latest completed image view, what its children returned, the records held, the
records it committed, the ungraded held measurements and the finding: the controlled features code reads from the
held A103 attachment sheets (``investigation_finding.context_finding``).

Carried from the old ``internal_summary.py`` (``decision_context``: the selection, the evidence axis and thought
pattern fields, the child tool information, the assignment) and from the old ``task.py`` decision state (the credit
view with its components, the last outcome, the visual evidence rule, the controller state, the report update). The
old ``initial_decision_context`` (``received_execution_context``: the A103 execution findings of the received records,
by ``a103_hpc.execution_findings``) has no module in the library today and is not shown (reported unplaced)."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.investigation_finding import (
    context_finding, ungraded_measurements)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from .. import credit as credit_file

OUTCOME_PAGE_SIZE = 8

CREDIT_KEYS = ('credit', 'axis_components', 'a103_sheet', 'target_sheets', 'tool_attachments',
               'source_contributions')


def visual_evidence(outcomes):
    """The pixels of the most recent unit when it was a completed ``image.view`` operation (the old rule read the last
    completed action's ``visual_inputs``); nothing otherwise."""
    if not outcomes:
        return []
    last = outcomes[-1]
    if (last['kind'] == 'tool' and last['tool'] == 'operation' and last['arguments'].get('name') == 'image.view'
            and last['outcome'].get('status') == 'completed'):
        return last['outcome'].get('visual_inputs') or []
    return []


def internal_summary(view):
    parent = view.parent_input
    library = catalog = None
    committed, child_reports, revisions = [], [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            child_reports.append({'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                                  **outcome['report']})
            continue
        name, result = outcome['tool'], outcome['outcome']
        if name == 'process_library':
            library = result
        elif name == 'tool_catalog':
            catalog = result['catalog']
        elif name == 'reason':
            for reference in result.get('record_refs', ()):
                if reference not in committed:
                    committed.append(reference)
        elif name == 'process_revise' and result.get('status') == 'completed':
            revisions.append({'selection': result['result']['selection'],
                              'revision_origin': result['revision_origin']})
    credit_view = credit_file.credit_view(view.records, parent)
    controller = view.controller_state
    return {
        'assignment': parent,
        'depth': len(view.path),
        'library': library,
        'catalog': catalog,
        'held_record_refs': sorted(view.records.refs()),
        'credit_view': {key: credit_view[key] for key in CREDIT_KEYS if key in credit_view},
        'own_outcomes': outcome_page([outcome for outcome in view.outcomes if outcome['kind'] == 'tool'],
                                     offset=0, limit=OUTCOME_PAGE_SIZE),
        'last_outcome': None if not view.outcomes else view.outcomes[-1],
        'visual_evidence': visual_evidence(view.outcomes),
        'child_reports': child_reports,
        'revisions': revisions,
        'committed_record_refs': committed,
        'units_consumed': view.units_consumed,
        'action_yields': None if controller is None else yield_table(controller, forecast_unit='credit'),
        'finding': context_finding(view.records, credit_view, parent['scope']),
        'ungraded_measurement_refs': ungraded_measurements(view.records, parent['scope']),
    }
