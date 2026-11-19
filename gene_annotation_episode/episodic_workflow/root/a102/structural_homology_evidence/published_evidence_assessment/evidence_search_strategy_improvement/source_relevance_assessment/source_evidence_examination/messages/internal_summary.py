"""Where the examination stands, as a pure function of the loop's view: the page assignment, custody of the page's
source, the first page of the episode's own read outcomes, the reports of the children it commissioned, the
structure sheets it saved and its children returned (each its own entry), and the typed answers the commissioned task asks for (carried from the old
``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``; the old reads of ``runtime_actions`` are the unit outcomes of ``view``, the old
reads of ``runtime_report_attempts`` the child reports of ``view``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
    current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('own_literature_outcomes is the latest page of your own tool outcomes, each with its arguments and '
                   'result, in unit order (total counts them all). Source '
                   'delivery does not establish scientific understanding.')


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    tool_outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in tool_outcomes if outcome['tool'] == 'reason']
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    leads = []
    # Own validated leads and each relevant lead source an admitted child return names, in unit order (the old
    # ``lead_dispositions`` merged them by decision order); a child names lead sources only on a leads commission.
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            leads.extend({'source_ref': reference, 'disposition': 'relevant',
                          'proposed_annotation_ref': parent['proposed_annotation_ref']}
                         for reference in (outcome['report']['lead_source_refs']
                                           if task['kind'] == 'verified_source_leads' else ()))
        elif outcome['tool'] == 'reason' and 'literature_source_lead' in outcome['outcome']:
            leads.append(outcome['outcome']['literature_source_lead'])
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(tool_outcomes, offset=max(0, len(tool_outcomes) - OUTCOME_PAGE_SIZE),
                                                limit=OUTCOME_PAGE_SIZE),
        'literature_history_meaning': HISTORY_MEANING,
        'child_reports': [{'slot': outcome['slot'], 'selection': outcome['arguments']['selection'],
                           'report': outcome['report']} for outcome in view.outcomes if outcome['kind'] == 'child'],
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'structure_sheets': merged_sheet_features(
            current_sheet_features(view.records),
            [features for outcome in view.outcomes if outcome['kind'] == 'child'
             for features in outcome['report']['structure_sheets']]),
        'source_leads': leads,
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
