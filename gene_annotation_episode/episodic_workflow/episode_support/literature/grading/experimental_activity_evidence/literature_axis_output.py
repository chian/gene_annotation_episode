"""A105 axis output: the main scoring sheet to the per-candidate axis output. Pure: arguments in, controlled records out.

Implements OWNER_DECISION 7 (one scalar tanh(net / AXIS_SCALAR_DIVISOR) in [-1, 1], with support and opposition also
returned so conflict stays visible), OWNER_DECISION 6 (rows sharing a dependence_unit_ref collapse to one unit before the
sum) and OWNER_DECISION 11 (the per-candidate credit goes up unchanged; it is not combined here).

Two separate channels per candidate, never mixed:
* SCORE channel (AXIS_SCORE_CHANNEL): target_id, the (normalized) target the score is about (OWNER_DECISION 18), read from
  the candidate's main rows, which must all agree (ValueError otherwise; placeholder rows carry the commissioned target).
  The credit channel does not carry it. Per dependence unit the mean of the support and of the opposition over its rows
  that have a known status (an unknown row never enters, never counts as zero or opposition); S_k = sum over units of
  the unit support, O_k = sum over units of the unit opposition, net = S_k - O_k, scalar = tanh(net / AXIS_SCALAR_DIVISOR).
  Status: unknown when no row has a known status (support, opposition, net, scalar are null); measured_zero when every
  known row is a measured zero (all 0.0, scalar 0.0); otherwise measured. A row with no dependence_unit_ref is its own unit.
  The score never reads resolution or credit.
* CREDIT channel (AXIS_CREDIT_CHANNEL): resolution_main = mean over the rows of the candidate (one per commissioned class
  N_k, placeholder rows for a class with no subscoring row count R = 0) of the row resolution; credit = U_main(before) -
  U_main(after) with U_main = 1 - resolution_main. merge_main stores per row credit = R(after) - R(before), so
  U(before) - U(after) = mean of the row credits over N_k; that mean is the credit. The credit never reads status,
  support, opposition, net or scalar.

The main sheet already holds the commissioned classes (N_k) as rows: a class without a subscoring row is a placeholder row
(source_row_ref NO_ROW_REF: status unknown, null scores, resolution 0.0, credit 0.0), and a row of an uncommissioned class
or candidate was refused by merge_main. Nothing is added or repaired here.

Returns {'score': {assertion_ref: record}, 'credit': {assertion_ref: record}}; each assembled axis record is checked
with validate_axis.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    AXIS_CREDIT_CHANNEL,
    AXIS_SCALAR_DIVISOR,
    AXIS_SCORE_CHANNEL,
    normalize_identity_ref,
    validate_axis,
    validate_main_row,
)


def _score(rows):
    units = {}
    for index, row in enumerate(rows):
        if row['row_status'] == 'unknown':
            continue
        key = row['dependence_unit_ref'] if row['dependence_unit_ref'] is not None else f"own:{index}"
        units.setdefault(key, []).append(row)
    if not units:
        return {'support': None, 'opposition': None, 'net': None, 'scalar': None, 'status': 'unknown'}
    support = math.fsum(math.fsum(r['support'] for r in members) / len(members) for members in units.values())
    opposition = math.fsum(math.fsum(r['opposition'] for r in members) / len(members) for members in units.values())
    net = support - opposition
    zero = all(r['row_status'] == 'measured_zero' for members in units.values() for r in members)
    return {'support': support, 'opposition': opposition, 'net': net,
            'scalar': math.tanh(net / AXIS_SCALAR_DIVISOR), 'status': 'measured_zero' if zero else 'measured'}


def axis_output(main_sheet):
    """OWNER_DECISIONS 7, 6 and 11: per candidate, the score channel and the credit channel of the main sheet."""
    by_candidate = {}
    for main_row in main_sheet:
        validate_main_row(main_row)
        by_candidate.setdefault(main_row['assertion_ref'], []).append(main_row)
    score, credit = {}, {}
    for assertion_ref in sorted(by_candidate):
        rows = by_candidate[assertion_ref]
        targets = {normalize_identity_ref(r['target_id']) for r in rows}
        if len(targets) != 1:
            raise ValueError(f'the main rows of {assertion_ref} are about different targets {sorted(targets)}: one score is about one target (OWNER_DECISION 18)')
        axis = {'assertion_ref': assertion_ref, 'target_id': targets.pop(), **_score(rows)}
        axis['resolution_main'] = math.fsum(r['resolution'] for r in rows) / len(rows)
        axis['credit'] = math.fsum(r['credit'] for r in rows) / len(rows)
        validate_axis(axis)
        score[assertion_ref] = {name: axis[name] for name in AXIS_SCORE_CHANNEL}
        credit[assertion_ref] = {name: axis[name] for name in AXIS_CREDIT_CHANNEL}
    return {'score': score, 'credit': credit}
