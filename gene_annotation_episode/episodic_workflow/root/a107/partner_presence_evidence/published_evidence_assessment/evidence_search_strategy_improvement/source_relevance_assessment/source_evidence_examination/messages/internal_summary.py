"""Where the examination stands, as a pure function of the view: the assignment, the custody of the page's source, the
Episode's own outcomes, the child reports (credit and controlled sheet features), the features of the partner sheets
its own graders saved (read back from their cell rows through the scoped reader) merged with those its children
returned, the agreement counts over them and the yield forecast of its controller (old ``internal_summary.py``:
``LiteratureSummary`` and ``SourceDecisionSummary``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    agreement, current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, SOURCE_TABLE, TABLE_PREVIEW_CHARS, candidate_text, page_candidates)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

# The page's input list (nano-graphrag's page: ``PageRunState.processed_chunk_ids`` / ``remaining_chunks``): the
# candidate input units of the examined representation (table regions and prose chunks, UTF-8 byte offsets, library
# ``page_candidates``). A candidate lying inside a window a child was commissioned with is consumed and offered no more;
# ``input_list`` is the unconsumed candidate ids in document order and the episode's yield estimator stops when it is
# empty. A representation that is not UTF-8 text (a workbook, a PDF) has no text candidates: its basis is ``not_utf8``,
# its list is empty and its children keep their window / workbook selections (nothing to consume).
TEXT_BASIS, BINARY_BASIS = 'text', 'not_utf8'


def handed_windows(selection):
    """The byte windows a child commission handed out: the one window of a window selection, every span of a ``spans``
    selection; a workbook table selection (``sheet_key``) addresses rows, not bytes, and hands out none."""
    if 'spans' in selection:
        return [(span['offset'], span['offset'] + span['limit']) for span in selection['spans']]
    if 'sheet_key' in selection:
        return []
    return [(selection['offset'], selection['offset'] + selection['limit'])]


def consumed_candidates(children, candidates):
    """The candidate ids the commissioned children were handed, in the order handed (nano-graphrag
    ``processed_chunk_ids`` and ``selected_source_table_ids``): every candidate lying inside a handed window."""
    consumed = []
    for outcome in children:
        for start, end in handed_windows(outcome['arguments']['selection']):
            consumed.extend(candidate['candidate_id'] for candidate in candidates
                            if start <= candidate['start'] and candidate['end'] <= end)
    return list(dict.fromkeys(consumed))


OUTCOME_PAGE_SIZE = 8
OWN_TOOLS = ('source_read', 'source_locate', 'literature_partner_populate', 'literature_partner_source_populate')
HISTORY_MEANING = ('Own outcome metadata only. Inspect original source records and exact prior operations before '
                   'interpreting them.')
SOURCE_FIELDS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')


def internal_summary(view):
    parent = view.parent_input
    page = parent['page']
    source = view.records.get(page['source_ref'])
    child_reports = [outcome['report'] for outcome in view.outcomes if outcome['kind'] == 'child']
    returned = [features for report in child_reports for features in report['partner_sheets']]
    sheets = merged_sheet_features(current_sheet_features(view.records, view.outcomes), returned)
    content = representation_content(view.records, page['source_ref'], page['representation'])
    try:
        candidates, basis = page_candidates(content), TEXT_BASIS
    except UnicodeDecodeError:
        candidates, basis = [], BINARY_BASIS
    consumed = consumed_candidates([outcome for outcome in view.outcomes if outcome['kind'] == 'child'], candidates)
    unconsumed = [candidate for candidate in candidates if candidate['candidate_id'] not in consumed]
    summary = {**parent,
               'input_list': [candidate['candidate_id'] for candidate in unconsumed],
               'input_list_basis': basis,
               'content_candidates': candidates,
               'consumed_candidate_ids': consumed,
               'unconsumed_candidates': unconsumed,
               'unconsumed_candidate_ids': [candidate['candidate_id'] for candidate in unconsumed],
               'unconsumed_table_ids': [candidate['candidate_id'] for candidate in unconsumed
                                        if candidate['candidate_type'] == SOURCE_TABLE],
               'unconsumed_chunk_ids': [candidate['candidate_id'] for candidate in unconsumed
                                        if candidate['candidate_type'] == PROSE_CHUNK],
               'table_previews': {candidate['candidate_id']: candidate_text(content, candidate)[:TABLE_PREVIEW_CHARS]
                                  for candidate in unconsumed if candidate['candidate_type'] == SOURCE_TABLE},
               'held_record_refs': sorted(view.records.refs()),
               # The page's source and the held sources derived from it (a dataset, a supplement, a literal source).
               'source_custody': [{'source_ref': row['id'], 'provider': row['provider'],
                                   **{key: row.get(key) for key in SOURCE_FIELDS}}
                                  for row in [source, *(row for row in view.records.list('source')
                                                        if page['source_ref'] in row.get('parent_source_refs', ()))]],
               'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                       tools=OWN_TOOLS, tool_of=lambda row: row.get('tool')),
               'literature_history_meaning': HISTORY_MEANING,
               'child_reports': child_reports,
               'partner_sheets': sheets,
               'partner_agreement': agreement(sheets),
               'units_consumed': view.units_consumed}
    if view.controller_state is not None:
        summary['yield_table'] = yield_table(view.controller_state, forecast_unit='finding')
    return summary
