"""Where the annotation stands, from the loop's view: what the commissioner gave and, for each of the nine axes,
what its head's returns add up to. Only the reports ``messages/read_from_child.py`` made are read (numbers, flags
and record references); a head's own result is not.

For each axis: ``credit`` (the axis credit; 0 before its head's first return), ``credit_after_each_return`` (the axis
credit after each return, in order), ``finding`` (the numbers and flags of its latest finding), ``annotation_rows``
(its head's scoring sheet: one row per candidate annotation it scored, see below), ``record_refs`` (every
record its head returned so far, which goes back to that head at its next commission), ``sheet_state_refs`` (the
sheet states of its latest return, for a head that takes them back) and ``outstanding_job_refs`` (the job records its
head left outstanding at its latest return). ``commissions`` lists the axes commissioned, in order.

The axis credit is made from what the head's returned credit measures (``read_from_child.CREDIT_RETURNED``): a
``standing`` return is the axis credit itself; a ``rise`` return is added to the axis credit before it.

The root's scoring sheet (``annotations``): the merger of the heads' scoring sheets. Each axis holds
``annotation_rows``: the rows of the latest return of its head that carried any (a head that changed nothing returns no
rows, and its sheet stands as it was). ``scoring_sheet`` puts the rows of all axes together by annotation (same
vocabulary, name and identifier) and gives each annotation one score.

The merger is the root's hypervolume (``credit.hypervolume``, the owner's rule for the root): the score of an
annotation is ``prod_i (1 + K * s_i) ** w_i - 1`` over the nine axes, where ``s_i`` is the score axis ``i`` gives that
annotation, as its head returned it. The concept: the axes are independent kinds of evidence, and an annotation stands
on how many of them agree. So the axes multiply: an annotation scored on one axis alone has exactly that axis's score
(times ``K``), and the same evidence spread over several axes scores more than it would on one. An axis that has not
scored the annotation, or whose row for it is of unknown status, takes ``s_i = 0``: its factor is 1, so it neither adds
nor erases what the other axes established (the offset ``credit.EPSILON`` of the hypervolume), and the row keeps its
status, so unknown is never read as a measured zero. An axis whose score is negative (its evidence says the annotation
does not hold) has a factor below 1 and discounts what the other axes built; it cannot reach 0 or below
(``credit.axis_gain`` fails there). The same arithmetic over the axis credits is the annotation credit; the score reads
no credit and the credit reads no score.

Every annotation keeps its rows, one per axis that scored it, so what each axis said stays visible. An annotation with
no row of known status has status unknown and no score. The sheet is ordered: the annotations of known status by score,
highest first, then the unknown ones; the first, when its status is known, is the best annotation."""
from ..credit import AXIS_WEIGHTS, hypervolume
from .read_from_child import CREDIT_RETURNED

ROW_FIELDS = ('status', 'score', 'support', 'opposition')


def scoring_sheet(axes):
    """The root's scoring sheet from the annotation rows of the axes (see the module text)."""
    table = {}
    for slot, axis in axes.items():
        for row in axis['annotation_rows']:
            table.setdefault((row['vocabulary'], row.get('name'), row.get('identifier')), {})[slot] = row
    sheet = []
    for (vocabulary, name, identifier), by_axis in table.items():
        annotation = {'vocabulary': vocabulary, **({} if name is None else {'name': name}),
                      **({} if identifier is None else {'identifier': identifier})}
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
                   'sheet_state_refs': [], 'outstanding_job_refs': [], 'annotation_rows': []}
            for slot in AXIS_WEIGHTS}
    for outcome in view.outcomes:
        axis, report = axes[outcome['slot']], outcome['report']
        axis['credit'] = (axis['credit'] + report['credit'] if CREDIT_RETURNED[outcome['slot']] == 'rise'
                          else report['credit'])
        axis['credit_after_each_return'].append(axis['credit'])
        axis['sheet_state_refs'] = report['sheet_state_refs']
        axis['finding'] = report['finding']
        if report['annotation_rows']:
            axis['annotation_rows'] = report['annotation_rows']
        axis['record_refs'].extend(ref for ref in report['record_refs'] if ref not in axis['record_refs'])
        axis['outstanding_job_refs'] = report['outstanding_job_refs']
    return {**view.parent_input, 'axes': axes, 'annotations': scoring_sheet(axes),
            'commissions': [outcome['slot'] for outcome in view.outcomes]}
