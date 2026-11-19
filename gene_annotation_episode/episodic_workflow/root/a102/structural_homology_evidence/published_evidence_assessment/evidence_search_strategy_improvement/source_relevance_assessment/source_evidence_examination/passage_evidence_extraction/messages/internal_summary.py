"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source, the
first page of the episode's own read outcomes, the interpretation written so far, and the typed answers the
commissioned task asks for (carried from the old ``internal_summary.py``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``; the old reads of
``runtime_actions`` are the unit outcomes of ``view``).

The structure population context of the old file (``literature_experimental_work``, owned population sources,
the latest failed population attempt) belongs to the population route, which is not built; ``decide`` raises
when the settings ask for it. The root-only ``reference_evidence_parent`` context is not this episode's."""
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding.')


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    written = [outcome['outcome']['report'] for outcome in outcomes if outcome['tool'] == 'report']
    report = written[-1] if written else None
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason']
    sources = [] if report is None else sorted({item['source_ref'] for item in report['passages']})
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': parent['spans']},
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    if parent['requested_structure_components'] is not None:
        assignment['requested_structure_components'] = parent['requested_structure_components']
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
        'report': report,
        'report_source_held': {reference: view.records.holds(reference) for reference in sources},
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons
                         if 'literature_source_lead' in outcome],
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
