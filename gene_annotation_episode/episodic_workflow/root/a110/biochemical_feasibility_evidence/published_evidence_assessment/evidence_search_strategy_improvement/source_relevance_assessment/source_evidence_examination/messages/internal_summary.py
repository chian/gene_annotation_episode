"""Where the examination stands, as a pure function of the loop's view: the page assignment and the reaction lead it
selects, custody of the page's source, the first page of the episode's own read outcomes, what each commissioned
investigation returned (its credit and controlled finding), the controlled features of the reaction sheets the
episode and its investigations saved and of the assessments it holds, the latest image the model looked at and what
the yield controller forecasts. Carried from the old ``internal_summary.py`` (``LiteratureSummary.decision_context``:
``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``; the population contexts are the saved reaction sheets of the work table and the
returned sheet features) and from the generic snapshot (``visual_evidence`` of the latest completed ``image.view``,
the yield table, the child reports). The old reads of ``runtime_actions`` and ``runtime_model_calls`` are the unit
outcomes of ``view``. ``component_axis_source_origin``, ``component_axis_source_access`` (they read the old
workflow's journal and the parent's request) and the root-only ``reference_evidence_parent`` context are not
carried."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_finding_features import (
    investigation_finding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_reaction_cells import (
    current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_reaction_instructions import (
    selected_family)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, SOURCE_TABLE, TABLE_PREVIEW_CHARS, candidate_text, page_candidates)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

# The page's input list (nano-graphrag's page: ``PageRunState.processed_chunk_ids`` / ``remaining_chunks``): the
# candidate input units of the assigned representation (table regions and prose chunks, UTF-8 byte offsets, library
# ``page_candidates``). A candidate lying inside a window a child was commissioned with is consumed and offered no more;
# ``input_list`` is the unconsumed candidate ids in document order and the episode's yield estimator stops when it is
# empty. A representation that is not UTF-8 text (a workbook, a PDF, an image) has no text candidates: its basis is
# ``not_utf8``, its list is empty and its children keep their window / workbook selections (nothing to consume).
TEXT_BASIS, BINARY_BASIS = 'text', 'not_utf8'


def handed_windows(arguments):
    """The byte windows a child commission handed out: every span of a passage commission, the one window of a
    coverage or ``window`` table commission; a workbook table selection (``sheet_key``) addresses rows, not bytes."""
    if 'spans' in arguments:
        return [(span['offset'], span['offset'] + span['limit']) for span in arguments['spans']]
    if 'sheet_key' in arguments:
        return []
    return [(arguments['offset'], arguments['offset'] + arguments['limit'])]


def consumed_candidates(children, candidates):
    """The candidate ids the commissioned children were handed, in the order handed (nano-graphrag
    ``processed_chunk_ids`` and ``selected_source_table_ids``): every candidate lying inside a handed window."""
    consumed = []
    for outcome in children:
        for start, end in handed_windows(outcome['arguments']):
            consumed.extend(candidate['candidate_id'] for candidate in candidates
                            if start <= candidate['start'] and candidate['end'] <= end)
    return list(dict.fromkeys(consumed))


OUTCOME_PAGE_SIZE = 8       # the old configuration outcome_page_size default
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Inspect original source records and exact prior operations before '
                   'interpreting them.')


def internal_summary(view):
    parent = view.parent_input
    page = parent['page']
    source = view.records.get(page['source_ref'])
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    last = view.outcomes[-1] if view.outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['kind'] == 'tool'
              and last['tool'] == 'image_view' and last['outcome'].get('status') == 'completed' else [])
    if last is None:
        last_local = None
    elif last['kind'] == 'tool':
        last_local = {'tool': last['tool'], 'outcome': last['outcome']}
    else:
        last_local = {'slot': last['slot'], 'report': last['report']}
    known = [row['id'] for row in view.records.list('assessment')]
    requested = {'requested_reaction_components'} if parent['requested_reaction_components'] else set()
    assignment = dict(page)
    if requested:
        assignment['requested_reaction_components'] = parent['requested_reaction_components']
    content = representation_content(view.records, page['source_ref'], page['representation'])
    try:
        candidates, basis = page_candidates(content), TEXT_BASIS
    except UnicodeDecodeError:
        candidates, basis = [], BINARY_BASIS
    consumed = consumed_candidates(children, candidates)
    unconsumed = [candidate for candidate in candidates if candidate['candidate_id'] not in consumed]
    return {
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
        'literature_assignment': assignment, 'page': page,
        'requested_reaction_components': parent['requested_reaction_components'],
        'family': selected_family(requested, set()),
        'scope': parent['scope'], 'finding_unit': parent['finding_unit'],
        'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'held_record_refs': sorted(view.records.refs()),
        'known_assessment_refs': known,
        'investigations': [outcome['report'] for outcome in children],
        'reaction_sheets': merged_sheet_features(
            current_sheet_features(view.records),
            [features for outcome in children for features in outcome['report']['finding']['reaction_sheets']]),
        'investigation_finding': investigation_finding(view.records, parent['scope'], parent['finding_unit'], known),
        'last_local_outcome': last_local,
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
