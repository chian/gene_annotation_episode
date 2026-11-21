"""The input list of a document-order reading (nano-graphrag ``ReportWindowSource``: the remaining text in document order,
each window once). The windows of a source read from an assigned start are consecutive byte windows of the assigned size,
``[[start, end], ...]``; a window is consumed once the bytes of it have been read (the union of the completed reads of that
exact artifact covers it) and is no longer offered. Pure functions: nothing here reads or writes the Store."""


def reading_windows(start, limit, size):
    """The consecutive windows of ``limit`` bytes from byte ``start`` to the end (``size``) of the artifact, in document
    order; the last one may be shorter. Empty when ``start`` is not before ``size``."""
    if start < 0 or limit < 1:
        raise ValueError('reading_windows_need_a_natural_start_and_a_positive_limit')
    return [[offset, min(offset + limit, size)] for offset in range(start, size, limit)]


def read_spans(outcomes, artifact_ref):
    """The byte spans ``[[start, end], ...]`` the completed ``source_read`` outcomes returned of the artifact
    ``artifact_ref`` (the exact artifact identity; a read of another representation is not a read of this one)."""
    spans = []
    for outcome in outcomes:
        if outcome['kind'] != 'tool' or outcome['tool'] != 'source_read' or outcome['outcome']['status'] != 'completed':
            continue
        result = outcome['outcome']['result']
        if result['artifact_ref'] == artifact_ref:
            spans.append([result['start'], result['end']])
    return spans


def remaining_windows(windows, spans):
    """The windows not yet consumed, in document order: a window is consumed when the union of ``spans`` covers all of it."""
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [[start, end] for start, end in windows
            if not any(low <= start and end <= high for low, high in merged)]
