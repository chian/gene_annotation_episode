"""The input list of a passage-reading episode (nano-graphrag's processed chunk ids / remaining chunks, over the
byte windows a parent assigned): a pure function of the assignment's windows and the episode's own unit outcomes.

A window is processed when the episode has read all of its bytes through a completed ``source.read`` of the same
source and representation, and has afterwards committed what it read: a ``reason`` commit that recorded records or a
completed reaction sheet population. A read alone does not consume it (the reasoning over it is still to be done); a
commit consumes every window read before it. A processed window is no longer offered. Nothing here reads or writes the
Store."""
READ_TOOLS = ('source_read',)
COMMIT_TOOLS = ('reason', 'literature_reaction_populate', 'literature_reaction_source_populate')


def _committed(outcome):
    result = outcome['outcome']
    if outcome['tool'] == 'reason':
        return bool(result.get('record_refs')) or bool(result.get('changed_record_refs'))
    return result.get('status') == 'completed'


def _covered(window, reads):
    """Whether the read intervals together cover ``window`` (a ``[start, end]`` pair)."""
    position, end = window
    for start, stop in sorted(reads):
        if start <= position < stop:
            position = stop
        if position >= end:
            return True
    return position >= end


def processed_windows(windows, source_ref, representation, outcomes):
    """The windows (``[start, end]`` pairs) processed so far, in the order given."""
    reads, processed = [], []
    for outcome in outcomes:
        if outcome['kind'] != 'tool':
            continue
        if outcome['tool'] in READ_TOOLS and outcome['outcome'].get('status') == 'completed':
            result = outcome['outcome']['result']
            if result['source_ref'] == source_ref and result['representation'] == representation:
                reads.append((result['start'], result['end']))
        elif outcome['tool'] in COMMIT_TOOLS and _committed(outcome):
            processed.extend(window for window in windows
                             if window not in processed and _covered(window, reads))
    return processed


def input_list(windows, source_ref, representation, outcomes):
    """The assigned windows not yet processed, in assignment order."""
    done = processed_windows(windows, source_ref, representation, outcomes)
    return [window for window in windows if window not in done]
