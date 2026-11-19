"""Credit (old ``ResultsCredit._generic_result_selector_progress`` and the generic native branch of
``_live_project_credit``): the acquired-record unit times the mean, over the requested paths, of the fraction of the
requested byte positions newly covered by retained windows. Byte positions the earlier results passed in custody
already cover earn nothing, and each position is credited once however the reads are split. The old handoff term was
the configured handoff unit times a count fixed at zero, so it never earned credit and is not carried. Never
bounded, clamped or rescaled.

The typed, API and local-file-source branches of the old credit lived in result hosts that the system does not
provide (BLOCKED-ON-JOB-SERVICE); ``messages/read_from_parent.py`` raises for those targets, so they do not reach
this function."""
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
