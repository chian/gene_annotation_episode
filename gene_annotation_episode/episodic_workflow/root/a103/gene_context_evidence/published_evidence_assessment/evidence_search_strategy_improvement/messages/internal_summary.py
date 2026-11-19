"""Where the strategy investigation stands, as a pure function of the loop's view: the assignment, custody of the
sources of the prior searches, the first page of the episode's own acquisition and read outcomes, the tool catalog
(once obtained), the latest completed image view, what the child returned, the records held and the strategy report
written so far (carried from the old ``internal_summary.py``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``; and from the old
``decision_state.py``: the visual evidence rule, the controller state and the report-lifecycle sentence).

The old summary built the source custody from ``assignment.get('source_refs', [])``, a field the strategy assignment
does not have (it names ``prior_search_refs``), so it was always empty. Here it is built from ``prior_search_refs``."""
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from .final_to_parent import finding_of

OUTCOME_PAGE_SIZE = 8        # the old configuration.outcome_page_size
# The old ``_ACQUISITION_TOOLS`` and ``_READ_TOOLS`` as the model's tool names.
OUTCOME_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                 'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset',
                 'source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
                 'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
SOURCE_KEYS = ('provider', 'accession', 'uri')
HISTORY_MEANING = 'Read exact prior outcomes through own_literature_outcomes; source discovery alone is not A103 evidence.'
REPORT_LIFECYCLE = 'The report is the last actual strategy judgment; later tool outcomes are facts, not a new judgment.'


def visual_evidence(outcomes):
    """The pixels of the most recent unit when it was a completed ``image_view`` (the old rule read the last
    completed action's ``visual_inputs``); nothing otherwise."""
    if not outcomes:
        return []
    last = outcomes[-1]
    if last['kind'] == 'tool' and last['tool'] == 'image_view' and last['outcome'].get('status') == 'completed':
        return last['outcome'].get('visual_inputs') or []
    return []


def internal_summary(view):
    parent = view.parent_input
    catalog, report, child_reports = None, None, []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            child_reports.append({'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                                  'search_result_refs': outcome['arguments']['search_result_refs'],
                                  **outcome['report']})
        elif outcome['tool'] == 'tool_catalog':
            catalog = outcome['outcome']['catalog']
        elif outcome['tool'] == 'report' and outcome['outcome']['status'] == 'reported':
            report = outcome['outcome']['report']
    custody = []
    for reference in parent['prior_search_refs']:
        source = view.records.get(reference)
        custody.append({'source_ref': reference, **{key: source.get(key) for key in CUSTODY_KEYS + SOURCE_KEYS}})
    controller = view.controller_state
    return {
        'assignment': parent,
        'source_custody': custody,
        'held_record_refs': sorted(view.records.refs()),
        'catalog': catalog,
        'own_literature_outcomes': outcome_page(
            [outcome for outcome in view.outcomes if outcome['kind'] == 'tool'], offset=0, limit=OUTCOME_PAGE_SIZE,
            tools=OUTCOME_TOOLS, tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'visual_evidence': visual_evidence(view.outcomes),
        'child_reports': child_reports,
        'units_consumed': view.units_consumed,
        'action_yields': None if controller is None else yield_table(controller, forecast_unit='credit'),
        'report': report,
        'report_lifecycle': REPORT_LIFECYCLE,
        'finding': finding_of(report),
    }
