"""Credit: ``acquired_record_unit`` times the fraction of the requested byte positions newly covered.

Carried from the old ``credit.py`` (``_generic_result_selector_progress`` and the native branch of
``_live_project_credit``; rule ``execution_received_selector_coverage_credit_v2``): each requested path counts the
union of the acquired windows once, whatever the read boundaries; positions the parent's known results already
held (the initial known records) earn nothing; the fraction is averaged over the requested paths. The old
``handoff_unit * handoff_count`` term was always zero (the handoff count was fixed at 0) and is not written. The
old ``credit_kind`` is deleted; the old closed credit view (``closed_credit.py``) is machinery: the system hands the
credit its controller last saw to ``final_to_parent``.

Credit is cumulative and is never bounded, clamped or rescaled here. The ``min`` and ``max`` below only measure an
interval of bytes (the old interval arithmetic); they do not limit the credit. The local-file, protein-structure and
API credit views are not carried (their selectors are not: ``messages/read_from_parent.py``)."""
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
    """The old ``_generic_result_selector_progress``: the mean over the requested paths of the share of requested
    positions covered by windows of results that were not known at the start."""
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
