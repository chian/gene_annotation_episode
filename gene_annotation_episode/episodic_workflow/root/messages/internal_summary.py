"""Where the annotation stands, from the loop's view: what the commissioner gave, the claims made and, for each of the
nine axes, what its head's returns add up to. Only the reports ``messages/read_from_child.py`` made and the outcomes of
the root's own tool are read (numbers, flags, looked-up names and record references); a head's own result is not.

For each axis: ``credit`` (the axis credit; 0 before its head's first return), ``credit_after_each_return`` (the axis
credit after each return, in order), ``finding`` (the numbers and flags of its latest finding), ``annotation_rows``
(the rows of a head that scores the annotations it finds: those of its latest return that carried any), ``claim_rows``
(the rows of a head that checks claims, by claim: the latest row its sheet gave each claim), ``claim_sheets`` (by
claim, the sheet states of the head's latest return on that claim, which go back to it when it is commissioned on that
claim again), ``claim_commissions`` (by claim, how often the head was commissioned on it), ``record_refs`` (every record
its head returned so far, which goes back to that head at its next commission) and ``outstanding_job_refs`` (the job
records its head left outstanding at its latest return). ``commissions`` lists the axes commissioned, in order.

The axis credit is made from what the head's returned credit measures (``read_from_child.CREDIT_RETURNED``): a
``standing`` return is the axis credit itself; a ``rise`` return is added to the axis credit before it.

Claims. ``claims`` lists the claims the tool ``make_claims`` made, each with the annotation it was made from (the tool
was called for that annotation: nothing attaches a claim to an annotation afterwards), what it says (predicate and the
looked-up name of its molecule) and its records; ``claims_made`` holds the annotations the tool was called for.

The root's scoring sheet (``annotations``): one line per candidate annotation (same vocabulary and identifier, or name
when it has no identifier: the identity the sequence-homology head gives its candidates), with one row per axis that
scored it. An axis that scores annotations gives its row directly. An axis that checks claims gives the annotation one
row made from its rows of that annotation's claims (``claim_axis_row``): the support of the claims of known status
summed, their opposition summed, and the score ``tanh((support - opposition) / CLAIM_SCALAR_DIVISOR)``, which for one
claim is exactly the scalar that head's own sheet gives it (A105's rule for its sheet, applied over the claims of one
annotation: each claim is a separate thing the annotation says, checked on its own).

The merger of the axes is the root's hypervolume (``credit.hypervolume``, the owner's rule for the root): the score of
an annotation is ``prod_i (1 + K * s_i) ** w_i - 1`` over the nine axes, where ``s_i`` is the score axis ``i`` gives
that annotation. The concept: the axes are independent kinds of evidence, and an annotation stands on how many of
them agree. So the axes multiply: an annotation scored on one axis alone has exactly that axis's score (times ``K``),
and the same evidence spread over several axes scores more than it would on one. An axis that has not scored the
annotation, or whose row for it is of unknown status, takes ``s_i = 0``: its factor is 1, so it neither adds nor erases
what the other axes established (the offset ``credit.EPSILON`` of the hypervolume), and the row keeps its status, so
unknown is never read as a measured zero. An axis whose score is negative (its evidence says the annotation does not
hold) has a factor below 1 and discounts what the other axes built; it cannot reach 0 or below (``credit.axis_gain``
fails there). The same arithmetic over the axis credits is the annotation credit; the score reads no credit and the
credit reads no score.

An annotation with no row of known status has status unknown and no score. The sheet is ordered: the annotations of
known status by score, highest first, then the unknown ones; the first, when its status is known, is the best
annotation."""
import math

from ..credit import AXIS_WEIGHTS, hypervolume
from .read_from_child import CREDIT_RETURNED

ROW_FIELDS = ('status', 'score', 'support', 'opposition')
# net -> the score of an axis that checks claims: tanh(net / CLAIM_SCALAR_DIVISOR), the divisor that head's sheet uses.
CLAIM_SCALAR_DIVISOR = 2.0


def annotation_key(annotation):
    """The identity of a candidate annotation: its vocabulary and its identifier, or its name when it has none."""
    return annotation['vocabulary'] + ':' + (annotation['identifier'] if 'identifier' in annotation
                                             else annotation['name'])


def claim_axis_row(rows):
    """The row an axis that checks claims gives one annotation, from its rows of that annotation's claims."""
    known = [row for row in rows if row['status'] != 'unknown']
    if not known:
        return {'status': 'unknown'}
    support = math.fsum(row['support'] for row in known)
    opposition = math.fsum(row['opposition'] for row in known)
    return {'status': 'measured_zero' if all(row['status'] == 'measured_zero' for row in known) else 'measured',
            'score': math.tanh((support - opposition) / CLAIM_SCALAR_DIVISOR),
            'support': support, 'opposition': opposition}


def scoring_sheet(axes, claims):
    """The root's scoring sheet from the rows of the axes and the claims (see the module text)."""
    table, identities = {}, {}
    for slot, axis in axes.items():
        for row in axis['annotation_rows']:
            key = annotation_key(row)
            identities.setdefault(key, {name: row[name] for name in ('vocabulary', 'name', 'identifier') if name in row})
            table.setdefault(key, {})[slot] = row
        by_annotation = {}
        for claim in claims:
            if claim['claim_ref'] in axis['claim_rows']:
                key = annotation_key(claim['annotation'])
                identities.setdefault(key, claim['annotation'])
                by_annotation.setdefault(key, []).append(axis['claim_rows'][claim['claim_ref']])
        for key, rows in by_annotation.items():
            table.setdefault(key, {})[slot] = claim_axis_row(rows)
    sheet = []
    for key, by_axis in table.items():
        annotation = dict(identities[key])
        known = {slot: row for slot, row in by_axis.items() if row['status'] != 'unknown'}
        if known:
            annotation.update(
                status='measured_zero' if all(row['status'] == 'measured_zero' for row in known.values())
                else 'measured',
                score=hypervolume({slot: known[slot]['score'] if slot in known else 0.0 for slot in AXIS_WEIGHTS}))
        else:
            annotation['status'] = 'unknown'
        sheet.append({**annotation, 'rows': [{'axis': slot, **{field: row[field] for field in ROW_FIELDS if field in row}}
                                             for slot, row in by_axis.items()]})
    return sorted(sheet, key=lambda annotation: (annotation['status'] == 'unknown', -annotation.get('score', 0.0)))


def internal_summary(view):
    axes = {slot: {'credit': 0.0, 'credit_after_each_return': [], 'finding': {}, 'record_refs': [],
                   'outstanding_job_refs': [], 'annotation_rows': [], 'claim_rows': {}, 'claim_sheets': {},
                   'claim_commissions': {}}
            for slot in AXIS_WEIGHTS}
    claims, claims_made, commissions = [], [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'tool':
            annotation = outcome['arguments']['annotation']
            claims_made.append(annotation_key(annotation))
            claims.extend({**claim, 'annotation': annotation} for claim in outcome['outcome']['result']['claims'])
            continue
        slot, report = outcome['slot'], outcome['report']
        axis = axes[slot]
        commissions.append(slot)
        axis['credit'] = axis['credit'] + report['credit'] if CREDIT_RETURNED[slot] == 'rise' else report['credit']
        axis['credit_after_each_return'].append(axis['credit'])
        axis['finding'] = report['finding']
        if report['annotation_rows']:
            axis['annotation_rows'] = report['annotation_rows']
        axis['claim_rows'].update({row['claim_ref']: row for row in report['claim_rows']})
        if 'claim_ref' in outcome['arguments']:
            claim_ref = outcome['arguments']['claim_ref']
            axis['claim_sheets'][claim_ref] = report['sheet_state_refs']
            axis['claim_commissions'][claim_ref] = axis['claim_commissions'].get(claim_ref, 0) + 1
        axis['record_refs'].extend(ref for ref in report['record_refs'] if ref not in axis['record_refs'])
        axis['outstanding_job_refs'] = report['outstanding_job_refs']
    return {**view.parent_input, 'axes': axes, 'claims': claims, 'claims_made': claims_made,
            'annotations': scoring_sheet(axes, claims), 'commissions': commissions}
