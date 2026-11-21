"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source, the
first page of the episode's own read outcomes, the controlled features of the current structure sheets it saved,
and the typed answers the commissioned task asks for (carried from the old ``internal_summary.py``:
``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``; the old reads of ``runtime_actions`` are the unit outcomes of ``view``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
    current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, page_candidates, report_windows)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('own_literature_outcomes is the latest page of your own tool outcomes, each with its arguments and '
                   'result, in unit order (total counts them all). Source '
                   'delivery does not establish scientific understanding.')


def read_spans(outcomes, source_ref, representation):
    """The byte spans of the page source's commissioned representation that completed ``source.read`` units delivered
    (nano-graphrag ``PageRunState.processed_chunk_ids``: what was handed out is processed)."""
    spans = []
    for outcome in outcomes:
        if outcome['kind'] != 'tool' or outcome['tool'] != 'source_read':
            continue
        result = outcome['outcome'].get('result')
        if outcome['outcome']['status'] in ('completed', 'partial') and result is not None \
                and result['source_ref'] == source_ref and result['representation'] == representation:
            spans.append((result['start'], result['end']))
    return spans


def input_state(records, page, window, outcomes):
    """The input list of the reading (nano-graphrag ``report_binding`` remaining chunks in document order): the source's
    content candidates (prose chunks and table regions, all read as prose here) from the starting window on, the
    ones fully inside a delivered ``source.read`` span consumed; ``input_list`` is the remaining candidates as
    ``[[start, end], ...]`` windows in document order (``report_windows``), ``consumed_candidate_ids`` the consumed ones."""
    content = representation_content(records, page['source_ref'], page['representation'])
    candidates = [{**candidate, 'candidate_type': PROSE_CHUNK} for candidate in page_candidates(content)
                  if candidate['end'] > window['offset']]
    spans = read_spans(outcomes, page['source_ref'], page['representation'])
    consumed = [candidate['candidate_id'] for candidate in candidates
                if any(start <= candidate['start'] and candidate['end'] <= end for start, end in spans)]
    remaining = {candidate['candidate_id'] for candidate in candidates} - set(consumed)
    return {'input_list': report_windows(candidates, remaining), 'consumed_candidate_ids': consumed,
            'input_candidates_total': len(candidates)}


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    # The old assignment validation that read the page's artifact: the window starts within the artifact.
    if parent['window']['offset'] > view.records.get(page['artifact_ref'])['size']:
        raise ValueError('source_offset_out_of_bounds')
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason']
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': parent['window'],
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(outcomes, offset=max(0, len(outcomes) - OUTCOME_PAGE_SIZE),
                                                limit=OUTCOME_PAGE_SIZE),
        'literature_history_meaning': HISTORY_MEANING,
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        **input_state(view.records, page, parent['window'], view.outcomes),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'structure_sheets': current_sheet_features(view.records),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons
                         if 'literature_source_lead' in outcome],
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
