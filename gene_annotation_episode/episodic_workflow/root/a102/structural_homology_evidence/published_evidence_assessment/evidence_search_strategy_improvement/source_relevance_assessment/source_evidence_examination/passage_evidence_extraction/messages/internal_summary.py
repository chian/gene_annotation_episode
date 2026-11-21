"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source, the
first page of the episode's own read outcomes, the controlled features of the current structure sheets it saved, and the typed answers the
commissioned task asks for (carried from the old ``internal_summary.py``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``; the old reads of
``runtime_actions`` are the unit outcomes of ``view``).

The input list (nano-graphrag's processed/remaining chunks): ``input_list`` holds the commissioned passages not yet
processed, as ``[start, end]`` windows in commission order (``spans_total`` counts the commissioned passages). A
passage is consumed once the episode's own ``no_applicable_evidence`` declaration examined it, or a validated source
lead's witness lies inside it; it is then no longer offered. The yield estimator ends the episode on an empty list."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
    current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view',
              'structure_populate')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding.')


def remaining_windows(spans, examined, leads):
    """The input list (nano-graphrag: processed chunks are consumed, the remaining ones are offered in document
    order): the commissioned passages not yet processed, as ``[start, end]`` byte windows of the page's source and
    representation, in the order commissioned. A passage is processed (consumed) where the episode's own
    ``no_applicable_evidence`` declarations examined it (the uncovered remainder of a partly examined passage stays
    in the list), and wholly when a validated source lead's witness lies inside it."""
    remaining = []
    for window in spans:
        start, end = window['offset'], window['offset'] + window['limit']
        key = (window['source_ref'], window['representation'])
        if any((lead['witness']['source_ref'], lead['witness']['representation']) == key
               and start <= lead['witness']['start'] and lead['witness']['end'] <= end for lead in leads):
            continue
        covered = sorted((max(span['start'], start), min(span['end'], end)) for span in examined
                         if (span['source_ref'], span['representation']) == key
                         and span['start'] < end and start < span['end'])
        cursor = start
        for covered_start, covered_end in covered:
            if covered_start > cursor:
                remaining.append([cursor, covered_start])
            cursor = max(cursor, covered_end)
        if cursor < end:
            remaining.append([cursor, end])
    return remaining


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason']
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': parent['spans']},
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'structure_sheets': current_sheet_features(view.records),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons
                         if 'literature_source_lead' in outcome],
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['spans_total'] = len(parent['spans'])
    summary['input_list'] = remaining_windows(parent['spans'], summary['no_applicable_evidence'],
                                              summary['source_leads'])
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
