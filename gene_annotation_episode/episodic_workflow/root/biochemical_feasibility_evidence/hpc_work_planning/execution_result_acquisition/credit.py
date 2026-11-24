"""Credit (credit kind ``operational``): ``acquired_record_unit`` times the share of the requested selector's byte
positions that this episode's own acquisitions newly received (the union of the windows of its retained results, so
a position read twice counts once, regardless of read boundaries), averaged over the requested paths.

The windows are those of the result records the Episode holds: the summary reads every result acquisition of this
Episode's collect and read units from its held record (``messages/internal_summary.py``), so a status request, a
refused fetch and a window of bytes already received earn nothing. The commission passes no earlier result, so no
position is already held at the start. Credit is never bounded, clamped or rescaled."""
import math


def _covered(windows, start, end):
    intervals = sorted((max(start, window['offset']), min(end, window['offset'] + window['returned_bytes']))
                       for window in windows
                       if window['offset'] < end and window['offset'] + window['returned_bytes'] > start)
    total, right = 0, start
    for left, stop in intervals:
        if stop > right:
            total += stop - max(left, right)
            right = stop
    return total


def selector_progress(requested, results):
    """Saved byte positions credited once: the mean over the requested paths of the received share of each span.
    ``requested`` is the parent input's ``windows``; ``results`` are the retained results of this episode. A span
    without a requested length ends at the size of the fetched file."""
    if not requested:
        return 0.0
    fractions = []
    for row in requested:
        windows = [window for result in results for window in result['windows'] if window['path'] == row['path']]
        start, length = row['start'], row['length']
        observed_end = max((window['size_bytes'] for window in windows), default=start)
        end = start + length if length is not None else max(start, observed_end)
        if end <= start:
            fractions.append(0.0)
            continue
        fractions.append(_covered(windows, start, end) / (end - start))
    return math.fsum(fractions) / len(fractions)


def credit(summary, records):
    return summary['acquired_record_unit'] * selector_progress(summary['windows'], summary['results'])
