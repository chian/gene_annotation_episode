"""Where the assessment stands, as a pure function of the loop's view: the assignment, the custody of sources
(empty, as in the old file), the first page of the episode's own acquisition and read outcomes, the child reports and
the assessment written so far (carried from the old ``internal_summary.py``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8        # the old configuration.outcome_page_size
ACQUISITION_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                     'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset')
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
HISTORY_MEANING = 'Read exact prior outcomes through own_literature_outcomes; source discovery alone is not A101 evidence.'


def internal_summary(view):
    parent = view.parent_input
    tool_outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    written = [outcome['outcome']['report'] for outcome in tool_outcomes if outcome['tool'] == 'report']
    report = written[-1] if written else None
    sources = [] if report is None else sorted({item['source_ref'] for item in report['assessments']})
    return {
        'literature_assignment': parent['assignment'],
        'scope': parent['scope'],
        'received_record_refs': parent['received_record_refs'],
        'held_record_refs': sorted(view.records.refs()),
        # the old file: custody rows are built from a page or from source_refs, and the search assignment has neither
        'literature_source_custody': [],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=ACQUISITION_TOOLS + READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'child_reports': [outcome['report'] for outcome in view.outcomes if outcome['kind'] == 'child'],
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'report': report,
        'report_source_held': {reference: view.records.holds(reference) for reference in sources},
    }
