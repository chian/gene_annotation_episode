"""The input list of an ordered source reading (nano-graphrag ``ReportWindowSource``: the remaining content in document
order, each part once): the byte windows of one source representation not yet read. Pure functions; nothing here reads
or writes the Store."""


def read_ranges(outcomes, source_ref, representation):
    """The byte ranges ``[start, end]`` that completed ``source_read`` units returned for ``representation`` of
    ``source_ref``."""
    ranges = []
    for unit in outcomes:
        outcome = unit['outcome']
        result = outcome.get('result')
        if (unit['kind'] == 'tool' and unit['tool'] == 'source_read' and outcome['status'] == 'completed'
                and result and result['source_ref'] == source_ref and result['representation'] == representation
                and result['end'] > result['start']):
            ranges.append([result['start'], result['end']])
    return ranges


def remaining_windows(size, begin, limit, ranges):
    """The windows of ``[begin, size)`` not covered by ``ranges``, in document order: the unread bytes, cut into
    windows of at most ``limit`` bytes, ``[[start, end], ...]``. Every byte read is consumed; a window read in part
    shrinks to its unread remainder; with everything read the list is empty."""
    unread, cursor = [], begin
    for start, end in sorted(ranges):
        if start > cursor:
            unread.append([cursor, min(start, size)])
        cursor = max(cursor, end)
    if cursor < size:
        unread.append([cursor, size])
    windows = []
    for start, end in unread:
        while start < end:
            windows.append([start, min(end, start + limit)])
            start += limit
    return [window for window in windows if window[0] < size and window[1] > window[0]]


def intersects(windows, offset, limit):
    """Whether the read ``[offset, offset + limit)`` touches an unread window."""
    return any(offset < end and start < offset + limit for start, end in windows)
