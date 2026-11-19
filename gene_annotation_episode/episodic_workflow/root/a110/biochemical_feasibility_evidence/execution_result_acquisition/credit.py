"""Credit: carried from the old ``credit.py`` (``ResultsCredit._generic_result_selector_progress`` and
``_live_project_credit``; credit kind ``operational``). ``acquired_record_unit`` times the share of the requested
selector's byte positions that this episode's own acquisitions newly received (the union of the windows of its
completed outcomes, so a position read twice counts once, regardless of read boundaries), averaged over the
requested paths. Binding ``execution_received_selector_coverage_credit_v2``, qualification
``original_selector_byte_position_union_current_filesystem_version_unverified``.

Carried unchanged otherwise: the old ``handoff_unit * new_handoff_count`` term is always zero (``handoff_count =
0``) and is not written; the positions already in the initial refs are none (the one initial ref is the handoff,
which has no windows). Credit is never bounded, clamped or rescaled. The old closed-credit pinning
(``closed_credit.py``) is old-runner machinery: the system hands ``final_to_parent`` the credit the controller
stopped on. The local file source and flux balance branches (``acquisition_counts``, ``credit_view`` of
``NativeFluxBalanceResults``) have no carried home (``messages/read_from_parent.py``)."""
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
    ``requested`` is the parent input's ``windows``; ``results`` are the result bodies this episode acquired."""
    if not requested:
        return 0.0
    fractions = []
    for row in requested:
        windows = [window for body in results for window in body['windows'] if window['path'] == row['path']]
        start, length = row['start'], row['length']
        observed_end = max((window['size_bytes'] for window in windows), default=start)
        end = start + length if length is not None else max(start, observed_end)
        if end <= start:
            fractions.append(0.0)
            continue
        fractions.append(_covered(windows, start, end) / (end - start))
    return math.fsum(fractions) / len(fractions)


def credit_binding(summary):
    """The old ``operational_credit_binding`` of the credit view (what the model was shown as ``credit_binding``)."""
    return {'version': 'execution_received_selector_coverage_credit_v2',
            'acquired_record_unit': summary['acquired_record_unit'],
            'qualification': 'original_selector_byte_position_union_current_filesystem_version_unverified'}


def credit(summary, records):
    value = summary['acquired_record_unit'] * selector_progress(summary['windows'], summary['results'])
    if not math.isfinite(value):
        raise ValueError('finite_execution_result_credit_required')
    return value
