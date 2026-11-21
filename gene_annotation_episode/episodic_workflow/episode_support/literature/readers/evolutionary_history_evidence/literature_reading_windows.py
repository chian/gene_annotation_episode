"""The input list of a document-order source reader (nano-graphrag ``ReportWindowSource``: the remaining text read in
document order, each window once; ``report_binding.py`` remaining chunks, ``provider_binding.py``
``PageRunState.processed_chunk_ids`` / ``remaining_chunks``).

Pure functions over bytes and integers; nothing here reads or writes the Store."""


def reading_windows(content, offset, limit):
    """The windows of the UTF-8 bytes ``content`` from byte ``offset`` to the end, in document order: consecutive
    ``[start, end]`` byte windows of at most ``limit`` bytes, each ending on a character boundary (the first window
    starts at ``offset``, as the reader was commissioned to start there). Empty when ``offset`` is at or beyond the
    end of the content."""
    if limit < 1 or offset < 0:
        raise ValueError('reading_window_out_of_range')
    windows, start = [], offset
    while start < len(content):
        end = min(len(content), start + limit)
        while end < len(content) and end > start + 1 and content[end] & 0xC0 == 0x80:
            end -= 1
        if end < len(content) and content[end] & 0xC0 == 0x80:    # one character longer than the window
            while end < len(content) and content[end] & 0xC0 == 0x80:
                end += 1
        windows.append([start, end])
        start = end
    return windows


def consumed_ranges(outcomes, source_ref, representation):
    """The byte ranges the episode's completed ``source_read`` units returned for the source's ``representation``:
    ``[[start, end], ...]`` merged and sorted. A read that did not complete, or of another source or representation,
    consumes nothing."""
    ranges = []
    for outcome in outcomes:
        if outcome['kind'] != 'tool' or outcome['tool'] != 'source_read':
            continue
        result = outcome['outcome']
        read = result.get('result') if isinstance(result, dict) else None
        if result.get('status') != 'completed' or not isinstance(read, dict):
            continue
        if read.get('source_ref') != source_ref or read.get('representation') != representation:
            continue
        ranges.append([read['start'], read['end']])
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def covered(ranges, start, end):
    """Whether ``[start, end]`` lies entirely inside one of the merged ``ranges``."""
    return any(low <= start and end <= high for low, high in ranges)


def remaining_windows(windows, ranges):
    """The input list: the windows not yet entirely read, in document order."""
    return [window for window in windows if not covered(ranges, window[0], window[1])]
