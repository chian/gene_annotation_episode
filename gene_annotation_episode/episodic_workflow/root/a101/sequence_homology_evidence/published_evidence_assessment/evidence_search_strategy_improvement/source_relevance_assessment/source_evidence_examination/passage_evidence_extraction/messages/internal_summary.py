"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source,
the first page of the episode's own read outcomes and the interpretation written so far (carried from the old
``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8        # the old configuration.outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = 'Read exact prior outcomes through own_literature_outcomes; source discovery alone is not A101 evidence.'


def internal_summary(view):
    parent = view.parent_input
    page = parent['page']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    written = [outcome['outcome']['report'] for outcome in outcomes if outcome['tool'] == 'report']
    report = written[-1] if written else None
    sources = [] if report is None else sorted({item['source_ref'] for item in report['passages']})
    return {
        'literature_assignment': {'version': 'reading_assignment_v1', 'page': page,
                                  'selection': {'spans': parent['spans']}},
        'scope': parent['scope'],
        'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=READ_TOOLS, tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'report': report,
        'report_source_held': {reference: view.records.holds(reference) for reference in sources},
    }
