"""Where the ordered reading stands, as a pure function of the loop's view: the assignment, custody of the page's
source, the first page of the episode's own read and population outcomes, the controlled features of the current
partner sheets it saved (read back from their cell rows through the scoped reader), the latest failed population
attempt and the controller's yield table.

Carried from the old ``internal_summary.py`` (``decision_context``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``; ``facts`` -> the
features of the held partner sheets; ``_population_task_context``) and from the old
``SourceDecisionSummary._decision_snapshot`` (the controller state). The old reads of ``runtime_actions`` and
``sqlite_master`` are ``view.outcomes`` and ``view.records``."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    agreement, current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.readers.partner_presence_evidence.source_bytes import (
    source_window_selection)
from gene_annotation_episode.episodic_workflow.episode_support.readers.partner_presence_evidence.source_windows import (
    read_ranges, remaining_windows)
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


def input_windows(view, page, window):
    """The input list (nano-graphrag ``ReportWindowSource``): the windows of the page's source, in the page's
    representation, not yet read, in document order. They run from the assigned window's offset to the end of the
    representation, cut at the assigned window's limit; a ``source_read`` that returned bytes consumes them, so the
    list shrinks to the unread remainder and is empty when everything has been read."""
    source = view.records.get(page['source_ref'])
    artifact_ref, representation, _ = source_window_selection(source, page['representation'])
    size = view.records.get(artifact_ref)['size']
    consumed = read_ranges(view.outcomes, page['source_ref'], representation)
    return (remaining_windows(size, window['offset'], window['limit'], consumed), representation, consumed)


def internal_summary(view):
    parent = view.parent_input
    page = parent['page']
    source = view.records.get(page['source_ref'])
    windows, representation, consumed = input_windows(view, page, parent['window'])
    sheets = current_sheet_features(view.records, view.outcomes)
    return {
        'literature_assignment': {'version': 'reading_assignment_v1', 'page': page, 'selection': parent['window']},
        'scope': parent['scope'],
        'partner_requested': parent['components'] is not None,
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
        # The input list: the unread byte windows [start, end] of the page's source representation, document order.
        'input_list': windows,
        'input_representation': representation,
        'consumed_ranges': consumed,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
