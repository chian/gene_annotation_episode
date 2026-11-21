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


SEARCH_TOOLS = ('public_literature_search', 'public_ncbi_search')


def candidate_sources(parent, outcomes, records):
    """The candidate sources of the episode's input list (nano-graphrag's web search state: the search results and
    candidate sources), in the order they arrived: the prior search results the assignment names, then the source
    records the episode's own searches returned and this episode holds."""
    found = list(parent['prior_search_refs'])
    for outcome in outcomes:
        if outcome['kind'] == 'tool' and outcome['tool'] in SEARCH_TOOLS:
            found.extend(ref for ref in outcome['outcome'].get('record_refs', ())
                         if ref.startswith('source_') and records.holds(ref))
    return list(dict.fromkeys(found))


def internal_summary(view):
    parent = view.parent_input
    catalog, report, child_reports = None, None, []
    # The input list: candidate sources not yet handed to the assessment child. A source handed out in a commission
    # is consumed and is no longer offered (nano-graphrag ``PageRunState.processed_chunk_ids`` / ``remaining_chunks``).
    consumed = list(dict.fromkeys(ref for outcome in view.outcomes if outcome['kind'] == 'child'
                                  for ref in outcome['arguments']['search_result_refs']))
    input_list = [ref for ref in candidate_sources(parent, view.outcomes, view.records) if ref not in consumed]
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
        'input_list': input_list,
        'consumed_search_result_refs': consumed,
        'units_consumed': view.units_consumed,
        'action_yields': None if controller is None else yield_table(controller, forecast_unit='credit'),
        'report': report,
        'report_lifecycle': REPORT_LIFECYCLE,
        'finding': finding_of(report),
    }
