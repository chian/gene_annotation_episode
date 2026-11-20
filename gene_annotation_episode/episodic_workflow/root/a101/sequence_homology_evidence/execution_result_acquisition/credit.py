"""Credit: the operational credit of the results role.

For the plain file results of a job it is ``acquired_record_unit * newly covered requested-byte fraction``: each
requested byte position counts once, minus what the results already known at the start (the initial results the
parent passed) covered, and the fraction is the mean over the requested paths. It is unbounded, never clamped and
never rescaled. The windows are those of the result records the Episode holds: the summary reads every result
acquisition, the initial ones and those of this Episode's own units, from its held record, so a status check, a
refused fetch and a window of bytes already covered earn nothing.

A graded return (a BLAST database grading, a pairwise BLAST grading or a phmmer grading) earns the credit unit
once, when its grading is saved. The other old credit views belong to classes
that are in no place now (typed native families, API execution, local file sources): credit raises at the call that
would have been made, not at its top."""
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
        everything = _covered((window for _, window in windows), start, end)
        old = _covered((window for initial, window in windows if initial), start, end)
        fractions.append((everything - old) / (end - start))
    return math.fsum(fractions) / len(fractions)


def credit(summary, records):
    family = summary['family']
    if family == 'blast_graded':
        # The verified completion of a BLAST database grader return: a saved grading of the requested sheet type
        # for the original query (the grading tool refuses any other) earns the credit unit once.
        return summary['acquired_record_unit'] if summary['graded_sheets'] else 0.0
    if family == 'phmmer_graded':
        # The verified completion of a local phmmer return: its capture graded and published once (a search that
        # printed no alignment is complete too: it stays in the tool profile).
        return summary['acquired_record_unit'] if summary['execution_completed'] else 0.0
    if family == 'blast_pairwise':
        # The verified completion of a pairwise BLAST return: a saved grading of the pairwise sheet of the job's own
        # operands earns the credit unit once.
        return summary['acquired_record_unit'] if summary['execution_completed'] else 0.0
    if family == 'native_bytes':
        return summary['acquired_record_unit'] * selector_fraction(summary['requested'], summary['results'])
    # old: the native result family's credit_view, api_execution.credit_view, local_file_sources.acquisition_counts
    raise NotImplementedError('unplaced:' + family + '.credit_view')
