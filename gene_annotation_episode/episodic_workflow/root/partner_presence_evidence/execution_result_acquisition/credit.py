"""Credit: the operational credit of the results role.

For the plain file results of a job it is ``acquired_record_unit * newly covered requested-byte fraction``: each
requested byte position counts once, minus what the results already known at the start (the initial results the
parent passed) covered, and the fraction is the mean over the requested paths. It is unbounded, never clamped and
never rescaled. The windows are those of the result records the Episode holds: the summary reads every result
acquisition, the initial ones and those of this Episode's own units, from its held record, so a status request, a
refused fetch and a window of bytes already covered earn nothing. A handoff earns nothing here.

Only the plain file results reach this function: the other families (the typed native result classes, the API
execution, the local file sources, whose credit was ``acquired_record_unit * count``) are refused by
``read_from_parent`` where their old class would have been called (``unplaced:<family>.credit_view``)."""
import math


def _covered(windows, start, end):
    """The number of byte positions of ``[start, end)`` the windows cover once."""
    intervals = sorted((max(start, window['offset']), min(end, window['offset'] + window['returned_bytes']))
                       for window in windows
                       if window['offset'] < end and window['offset'] + window['returned_bytes'] > start)
    total, right = 0, start
    for left, stop in intervals:
        if stop > right:
            total += stop - max(left, right)
            right = stop
    return total


def selector_fraction(requested, results):
    """The mean over the requested paths of the newly covered fraction of the requested interval: what all held
    results cover minus what the initial results covered. An interval without a requested length ends at the size
    of the fetched file."""
    if not requested:
        return 0.0
    fractions = []
    for path, (start, length) in requested.items():
        windows = [(result['initial'], window) for result in results for window in result['windows']
                   if window['path'] == path]
        observed_end = max((window['size_bytes'] for _, window in windows), default=start)
        end = start + length if length is not None else max(start, observed_end)
        if end <= start:
            fractions.append(0.0)
            continue
        everything = _covered([window for _, window in windows], start, end)
        old = _covered([window for initial, window in windows if initial], start, end)
        fractions.append((everything - old) / (end - start))
    return math.fsum(fractions) / len(fractions)


def credit(summary, records):
    return summary['acquired_record_unit'] * selector_fraction(summary['requested'], summary['results'])
