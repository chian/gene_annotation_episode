"""The input list of a reader of one selected region of a source (nano-graphrag's processed chunk / processed row ids):
the region is ``[start, end)`` of the selection (the bytes of an exact window, or the matching rows of an XLSX table
selection), the items of the list are the spans of it still to be processed, in document order. A span is consumed when
it has been read by a completed read call of the region and a reasoning commit has completed after that read (the
region has then been read and what it states committed); a read alone leaves it on the list until the commit.

Pure functions over the episode's unit outcomes (``{'kind': 'tool', 'tool', 'arguments', 'outcome'}``, the arguments being
the tool call's envelope with the model's ``arguments``). Nothing is written to the Store."""
READ_TOOL, ROWS_TOOL, COMMIT_TOOL = 'source_read', 'source_xlsx_rows', 'reason'
WINDOW_DEFAULTS = {'offset': 0, 'limit': 12000, 'representation': 'text'}


def region(selection):
    """The selected region as ``[start, end)``: bytes of a window, matching rows of a table selection."""
    return [selection['offset'], selection['offset'] + selection['limit']]


def read_span(selection, tool, arguments):
    """The span ``[start, end)`` of the region a read call reads, or ``None`` when the call reads something else (another
    source, representation, sheet, header row or row filter, or is not the region's read tool)."""
    if 'sheet_key' in selection:
        if tool != ROWS_TOOL or arguments.get('source_ref') != selection['source_ref'] \
                or arguments.get('sheet_key') != selection['sheet_key'] \
                or arguments.get('header_row') != selection.get('header_row') \
                or arguments.get('where') != selection.get('where'):
            return None
        return [arguments['offset'], arguments['offset'] + arguments['limit']]
    if tool != READ_TOOL or arguments.get('source_ref') != selection['source_ref'] \
            or arguments.get('representation', WINDOW_DEFAULTS['representation']) != selection['representation']:
        return None
    offset = arguments.get('offset', WINDOW_DEFAULTS['offset'])
    return [offset, offset + arguments.get('limit', WINDOW_DEFAULTS['limit'])]


def subtract(spans, taken):
    """``spans`` (ordered, disjoint) less the span ``taken``."""
    start, end = taken
    remaining = []
    for first, last in spans:
        if end <= first or last <= start:
            remaining.append([first, last])
            continue
        if first < start:
            remaining.append([first, start])
        if end < last:
            remaining.append([end, last])
    return remaining


def consumed_and_remaining(selection, outcomes):
    """``(consumed, input_list)``: the spans of the region processed so far and the spans still to process, each in
    document order. Failed reads and unfinished commits consume nothing."""
    pending, consumed = [], []
    for outcome in outcomes:
        if outcome['kind'] != 'tool':
            continue
        status = outcome['outcome'].get('status') if isinstance(outcome['outcome'], dict) else None
        if outcome['tool'] == COMMIT_TOOL and status in ('completed', 'partial'):
            consumed, pending = consumed + pending, []
        elif status == 'completed':
            span = read_span(selection, outcome['tool'], outcome['arguments']['arguments'])
            if span is not None and span[0] < span[1]:
                pending.append(span)
    remaining = [region(selection)] if region(selection)[0] < region(selection)[1] else []
    for span in consumed:
        remaining = subtract(remaining, span)
    return sorted(consumed), remaining


def is_consumed_read(selection, tool, arguments, consumed):
    """Whether a read call reads only spans of the region that are consumed (it is then not offered again)."""
    span = read_span(selection, tool, arguments)
    if span is None or span[0] >= span[1]:
        return False
    rest = [span]
    for taken in consumed:
        rest = subtract(rest, taken)
    return not rest
