"""Where the ordered reading stands, as a pure function of the loop's view: the assignment, custody of the page's
source, the first page of the episode's own read and population outcomes, the controlled features of the current
partner sheets it saved (read back from their cell rows through the scoped reader), the latest failed population
attempt and the controller's yield table.

The input list (nano-graphrag's source table: a region is consumed once processed): ``input_list`` holds the one selection
of the commission, ``[[offset, end]]`` (bytes of the window, or the matching rows of the table), until a partner grader
has completed on it, and is empty after that; ``consumed_inputs`` holds what has been processed.

Carried from the old ``internal_summary.py`` (``decision_context``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``; ``facts`` -> the
features of the held partner sheets; ``_population_task_context``) and from the old
``SourceDecisionSummary._decision_snapshot`` (the controller state). The old reads of ``runtime_actions`` and
``sqlite_master`` are ``view.outcomes`` and ``view.records``."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    agreement, current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8        # the old configuration.outcome_page_size
POPULATION_TOOLS = ('literature_partner_populate', 'literature_partner_source_populate')
READ_TOOLS = ('source_read', 'source_locate')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Inspect original source records and exact prior operations before '
                   'interpreting them.')
FAILED = ('invalid', 'failed', 'error')


def latest_failed_population(outcomes):
    """The old ``_population_task_context`` row: the latest completed unit, when it was a population tool and
    failed, with its feedback code."""
    if not outcomes:
        return None
    last = outcomes[-1]
    if last['kind'] != 'tool' or last['tool'] not in POPULATION_TOOLS or last['outcome']['status'] not in FAILED:
        return None
    return {'tool': last['tool'], 'status': last['outcome']['status'], 'feedback': last['outcome']['feedback']}


def derived_sources(records, page_source_ref):
    """The held sources whose parents name the page's source."""
    return [row for row in records.list('source') if page_source_ref in row.get('parent_source_refs', ())]


def selection_range(selection):
    """The one input item of the commission (nano-graphrag's selected table region): ``[start, end]`` of the byte window
    or of the table's matching rows; an empty selection holds no item."""
    start, end = selection['offset'], selection['offset'] + selection['limit']
    return [[start, end]] if end > start else []


def processed_inputs(outcomes, items):
    """The items consumed: the selection is processed once a partner grader has completed on it (nano-graphrag's
    ``processed_row_ids``: a row is consumed when its query has been made, not when it has been read). A read or a locate
    does not consume it; a failed grader call does not either."""
    graded = any(row['kind'] == 'tool' and row['tool'] in POPULATION_TOOLS and row['outcome']['status'] not in FAILED
                 for row in outcomes)
    return list(items) if graded else []


def internal_summary(view):
    parent = view.parent_input
    page = parent['page']
    items = selection_range(parent['selection'])
    consumed = processed_inputs(view.outcomes, items)
    source = view.records.get(page['source_ref'])
    sheets = current_sheet_features(view.records, view.outcomes)
    return {
        'literature_assignment': {'version': 'reading_assignment_v1', 'page': page, 'selection': parent['selection']},
        'finding_unit': parent['finding_unit'],
        'scope': parent['scope'],
        'partner_requested': False,
        # The page's source and the held sources derived from it (a dataset, a supplement, a literal witness source).
        'literature_source_custody': [{'source_ref': row['id'], 'provider': row['provider'],
                                       **{key: row.get(key) for key in CUSTODY_KEYS}}
                                      for row in [source, *derived_sources(view.records, page['source_ref'])]],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(*READ_TOOLS, *POPULATION_TOOLS),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_selected_population_attempt': latest_failed_population(view.outcomes),
        'partner_sheets': sheets,
        'partner_agreement': agreement(sheets),
        'input_list': [item for item in items if item not in consumed],
        'consumed_inputs': consumed,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
