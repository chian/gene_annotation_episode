"""Credit: the acquired-record unit times the mean, over the requested paths, of the fraction of the requested byte
positions newly covered by retained windows.

Carried from the old ``credit.py`` (``ResultsCredit._generic_result_selector_progress`` and the native branch of
``_live_project_credit``; rule ``execution_received_selector_coverage_credit_v2``): each requested path counts the
union of the retained windows once, whatever the read boundaries; byte positions the earlier results passed in
custody (the old initial known records) already cover earn nothing. The old ``handoff_unit * handoff_count`` term was
the configured handoff unit times a count fixed at zero: it never earned credit and is not carried. The old
``credit_kind`` and the pinned closed credit view (``closed_credit.py``) are machinery: the system hands the credit
its controller last saw to ``final_to_parent``. The count-based credit of local file sources and the credit views of
the typed and API result hosts are not carried (their result host is BLOCKED-ON-JOB-SERVICE, see
``messages/read_from_parent.py``).

Credit is cumulative and never bounded, clamped or rescaled here; the ``min`` and ``max`` below only measure an
interval of bytes."""
import math


def _covered(windows, start, end):
    """The number of byte positions of ``[start, end)`` inside the union of the windows."""
    intervals = sorted((max(start, window['offset']), min(end, window['offset'] + window['returned_bytes']))
                       for window in windows
                       if window['offset'] < end and window['offset'] + window['returned_bytes'] > start)
    total, right = 0, start
    for left, stop in intervals:
        if stop > right:
            total += stop - max(left, right)
            right = stop
    return total


def selector_progress(requested, initial, own):
    """Library candidate (the old ``_generic_result_selector_progress``): the mean newly covered fraction of the
    requested byte positions. ``initial`` and ``own`` are lists of retained results, each with its windows."""
    if not requested:
        return 0.0
    fractions = []
    for path, (start, length) in requested.items():
        old = [window for body in initial for window in body['windows'] if window['path'] == path]
        every = old + [window for body in own for window in body['windows'] if window['path'] == path]
        observed_end = max((window['size_bytes'] for window in every), default=start)
        end = start + length if length is not None else max(start, observed_end)
        if end <= start:
            fractions.append(0.0)
            continue
        fractions.append((_covered(every, start, end) - _covered(old, start, end)) / (end - start))
    return math.fsum(fractions) / len(fractions)


def credit(summary, records):
    return summary['acquired_record_unit'] * selector_progress(summary['requested'], summary['initial'],
                                                               summary['own'])
