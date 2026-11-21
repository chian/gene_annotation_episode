"""The input list of an A103 source examination page, ported from nano-graphrag's page (``page_binding.py``,
``provider_binding.py`` ``PageRunState.processed_chunk_ids`` / ``remaining_chunks``, ``report_binding.py`` remaining
chunks in document order): the items the page works through are the candidate input units of its source (the table
regions and prose chunks ``literature_page_content.page_candidates`` finds, byte intervals of the commissioned
representation). An item handed to a child is consumed and no longer offered; the list shrinks as children are
commissioned and the page's yield estimator stops the episode when it is empty.

What a child consumes (by the window it was commissioned with, byte offsets of the page's representation):

- ``table_evidence_extraction`` with a byte window: every table region the window overlaps. With a workbook sheet
  selection it consumes no listed item (a sheet is not a byte-interval candidate).
- ``source_coverage_improvement``: every candidate lying inside its first window and, when it reported, inside the
  extent its finding says it covered (document-order reading).
- ``passage_evidence_extraction``: every candidate lying inside one of its spans.

Every function is pure: nothing here reads or writes the Store."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, SOURCE_TABLE, page_candidates, report_windows)

TABLE_SLOT = 'table_evidence_extraction'
COVERAGE_SLOT = 'source_coverage_improvement'
PASSAGE_SLOT = 'passage_evidence_extraction'


def selection_windows(slot, selection):
    """The byte windows ``[start, end)`` a commission's selection names: ``[]`` for a workbook sheet selection."""
    if slot == PASSAGE_SLOT:
        return [(span['offset'], span['offset'] + span['limit']) for span in selection['spans']]
    if 'sheet_key' in selection:
        return []
    return [(selection['offset'], selection['offset'] + selection['limit'])]


def handled_ids(slot, selection, candidates):
    """The candidate ids a window of ``selection`` hands to the child: the table regions it overlaps (table child), or
    the candidates lying wholly inside it."""
    handled = []
    for start, end in selection_windows(slot, selection):
        for candidate in candidates:
            inside = start <= candidate['start'] and candidate['end'] <= end
            overlaps = candidate['start'] < end and start < candidate['end']
            if inside or (slot == TABLE_SLOT and candidate['candidate_type'] == SOURCE_TABLE and overlaps):
                handled.append(candidate['candidate_id'])
    return handled


def consumed_ids(commissions, candidates):
    """The candidate ids the commissioned children consumed, in the order consumed. ``commissions`` are
    ``{'slot', 'selection', 'finding'}`` in commission order (the finding is the child's returned one)."""
    consumed = []
    for commission in commissions:
        consumed.extend(handled_ids(commission['slot'], commission['selection'], candidates))
        finding = commission['finding']
        if commission['slot'] == COVERAGE_SLOT and finding['reported']:
            extent = {'offset': finding['covered_offset'], 'limit': max(finding['covered_limit'], 1)}
            consumed.extend(handled_ids(COVERAGE_SLOT, extent, candidates))
    return list(dict.fromkeys(consumed))


def input_list_state(content, commissions):
    """The page's input list over the bytes ``content`` of its commissioned representation: every candidate, the
    consumed ids, the unconsumed candidates in document order and the windows of the remaining prose chunks."""
    candidates = page_candidates(content)
    consumed = consumed_ids(commissions, candidates)
    unconsumed = [item for item in candidates if item['candidate_id'] not in consumed]
    return {'candidates': candidates, 'consumed': consumed, 'unconsumed': unconsumed,
            'input_list': [item['candidate_id'] for item in unconsumed],
            'remaining_windows': report_windows(candidates, {item['candidate_id'] for item in unconsumed}),
            'unconsumed_table_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == SOURCE_TABLE],
            'unconsumed_chunk_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == PROSE_CHUNK]}


def selection_offered(slot, selection, unconsumed):
    """Whether a commission's selection names only unconsumed input: every byte window of it hands at least one
    unconsumed candidate to the child (a workbook sheet selection names no listed item and is not checked)."""
    unconsumed_ids = {item['candidate_id'] for item in unconsumed}
    for window in selection_windows(slot, selection):
        probe = {'spans': [{'offset': window[0], 'limit': window[1] - window[0]}]} if slot == PASSAGE_SLOT \
            else {'offset': window[0], 'limit': window[1] - window[0]}
        if not unconsumed_ids.intersection(handled_ids(slot, probe, unconsumed)):
            return False
    return True
