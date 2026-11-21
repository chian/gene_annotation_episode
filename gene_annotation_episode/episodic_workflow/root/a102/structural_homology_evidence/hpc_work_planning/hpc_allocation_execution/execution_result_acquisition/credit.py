"""Credit: ``acquired_record_unit`` times the fraction of the requested byte positions newly covered.

Each requested path counts the union of the retained windows once, whatever the read boundaries; positions the
known results already held (the earlier acquisitions the parent passed) earn nothing; the fraction is averaged over
the requested paths. The windows are those of the result records the Episode holds: the summary reads every result
acquisition, the known ones and those of this Episode's own collect and read units, from its held record
(``messages/internal_summary.py``), so a status request, a refused fetch and a window of bytes already covered earn
nothing.

Credit is cumulative and is never bounded, clamped or rescaled here. The ``min`` and ``max`` below only measure an
interval of bytes; they do not limit the credit."""
import math


def covered(windows, start, end):
    """The number of byte positions of ``[start, end)`` inside the union of the windows."""
    intervals = sorted(((max(start, window['offset']), min(end, window['offset'] + window['returned_bytes']))
                        for window in windows
                        if window['offset'] < end and window['offset'] + window['returned_bytes'] > start))
    total, right = 0, start
    for left, stop in intervals:
        if stop > right:
            total += stop - max(left, right)
            right = stop
    return total


def selector_progress(requested, results):
    """The mean over the requested paths of the share of requested positions covered by windows of results that
    were not known at the start. An interval without a requested length ends at the size of the fetched file."""
    if not requested:
        return 0.0
    fractions = []
    for path, (start, length) in requested.items():
        windows = [(item['initial'], window) for item in results for window in item['windows']
                   if window['path'] == path]
        observed_end = max((window['size_bytes'] for _, window in windows), default=start)
        end = start + length if length is not None else max(start, observed_end)
        if end <= start:
            fractions.append(0.0)
            continue
        all_bytes = covered([window for _, window in windows], start, end)
        old_bytes = covered([window for initial, window in windows if initial], start, end)
        fractions.append((all_bytes - old_bytes) / (end - start))
    return math.fsum(fractions) / len(fractions)


def credit(summary, records):
    return summary['acquired_record_unit'] * selector_progress(summary['requested'], summary['results'])
