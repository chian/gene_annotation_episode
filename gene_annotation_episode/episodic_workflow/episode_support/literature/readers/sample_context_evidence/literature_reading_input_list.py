"""The input list of an ordered source reading (nano-graphrag ``ReportWindowSource`` / ``PageRunState.remaining_chunks``): the
content candidates of the page source (``literature_page_content.page_candidates``: table regions and prose chunks, UTF-8
byte offsets of the commissioned representation) that lie at or after the window the reading starts from and have not
yet been read, in document order. A candidate is consumed once the reading's own ``source.read`` windows of that source and
representation cover its bytes entirely; a consumed candidate is never listed again. Pure: nothing here reads the Store."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, page_candidates, report_windows)


def covered(ranges, start, end):
    """Whether ``[start, end)`` lies inside the union of the byte ``ranges`` ``[(start, end), ...]``."""
    position = start
    for low, high in sorted(ranges):
        if low > position:
            break
        position = max(position, high)
        if position >= end:
            return True
    return position >= end


def read_ranges(outcomes, source_ref, representation):
    """The byte ranges the ``source_read`` units read of ``source_ref`` in ``representation``."""
    ranges = []
    for outcome in outcomes:
        if outcome['kind'] != 'tool' or outcome['tool'] != 'source_read' or outcome['outcome']['status'] not in (
                'completed', 'partial'):
            continue
        result = outcome['outcome']['result']
        if result['source_ref'] == source_ref and result['representation'] == representation:
            ranges.append((result['start'], result['end']))
    return ranges


def input_list(content, start_offset, ranges):
    """``{'consumed_ids', 'input_list', 'windows'}``: the candidate ids already read, the unread candidates at or after
    ``start_offset`` in document order (``candidate_id``, ``candidate_type``, ``start``, ``end``) and the remaining prose
    as the report windows ``[[start, end], ...]``."""
    candidates = [candidate for candidate in page_candidates(content) if candidate['end'] > start_offset]
    consumed = [candidate['candidate_id'] for candidate in candidates
                if covered(ranges, candidate['start'], candidate['end'])]
    remaining = [{key: candidate[key] for key in ('candidate_id', 'candidate_type', 'start', 'end')}
                 for candidate in candidates if candidate['candidate_id'] not in consumed]
    prose = {item['candidate_id'] for item in remaining if item['candidate_type'] == PROSE_CHUNK}
    return {'consumed_ids': consumed, 'input_list': remaining, 'windows': report_windows(candidates, prose)}


def offered_offset(remaining, offset):
    """Whether a read starting at ``offset`` begins inside an unread candidate."""
    return any(item['start'] <= offset < item['end'] for item in remaining)
