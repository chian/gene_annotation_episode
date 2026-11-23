"""The return of the annotation: controlled data only. Always returned: ``credit`` (the annotation credit its
controller stopped on, which the system hands in ``completion``) and ``finding``: the root's scoring sheet
(``annotations``: every candidate annotation the axis heads scored, with its score, the hypervolume over the scores
the axes give it, and the row of each axis that scored it, the highest score first), the best annotation (``best_annotation``:
the first of the sheet, present when its status is known), how many commissions the root made and, for each of the
nine axes, its credit, how often it was commissioned and how many job records its head left outstanding. Selectable, returned in custody: ``record_refs`` (the records the axis heads returned) and
``outstanding_job_refs`` (the records of the jobs still outstanding, with which a later run can return to them)."""
from method_loop import ChoiceField, Field, RecordForm

from ..credit import AXIS_WEIGHTS
from .read_from_child import ROW_STATUS, VOCABULARIES

_ABSENT = ' (absent when the status is unknown)'
AXIS_ROW_FORM = RecordForm({
    'axis': ChoiceField('text', 'The axis whose head scored the annotation', tuple(AXIS_WEIGHTS)),
    'status': ChoiceField('text', 'Whether that evidence is measured, measured as exactly zero, or unknown', ROW_STATUS),
    'score': Field('number', "The score that axis gives the annotation, on the axis's own scale; negative when its "
                             'evidence says the annotation does not hold' + _ABSENT, required=False),
    'support': Field('number', 'The support behind that score, for an axis whose sheet keeps support and opposition '
                               'apart', required=False),
    'opposition': Field('number', 'The opposition behind that score, for such an axis', required=False),
})
ANNOTATION_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate annotation: product (a database search\'s '
                                      'function), profile_family (a family of a profile database), reference_sequence '
                                      '(a sequence record it was compared with) or proposed_annotation (a hypothesis '
                                      'record)', VOCABULARIES),
    'name': Field('text', 'The name of the annotation exactly as its source gives it', required=False),
    'identifier': Field('text', 'The identifier of the annotation: a family accession or a record reference',
                        required=False),
    'status': ChoiceField('text', 'Whether the merged evidence is measured, measured as exactly zero, or unknown',
                          ROW_STATUS),
    'score': Field('number', 'The annotation score: the hypervolume prod_i (1 + k * s_i) ** w_i - 1 over the scores '
                             's_i the axes give the annotation (0 for an axis that has not scored it)' + _ABSENT,
                   required=False),
    'rows': Field('list', 'One row per axis whose head scored the annotation', items=AXIS_ROW_FORM),
})
AXIS_FORM = RecordForm({
    'credit': Field('number', 'The axis credit: what its head returned at its latest return, 0 before the first'),
    'commissions': Field('integer', 'How often the axis was commissioned'),
    'outstanding_jobs': Field('integer', 'How many job records its head left outstanding at its latest return'),
})
AXES_FORM = RecordForm({slot: Field('record', 'The state of the ' + slot + ' axis', form=AXIS_FORM)
                        for slot in AXIS_WEIGHTS})
FINDING_FORM = RecordForm({
    'annotations': Field('list', "The root's scoring sheet: every candidate annotation the axis heads scored, the "
                                 'highest score first, the ones of unknown status last', items=ANNOTATION_FORM),
    'best_annotation': Field('record', 'The best annotation: the first of the scoring sheet (absent while no '
                                       'annotation has a known status)', form=ANNOTATION_FORM, required=False),
    'commissions': Field('integer', 'How many axis commissions the root made'),
    'axes': Field('record', 'The state of each of the nine axes', form=AXES_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The annotation credit when the Episode's controller stopped it"),
    'finding': Field('record', 'Where the annotation stands on each of the nine axes', form=FINDING_FORM),
    'record_refs': Field('record_refs', 'The records the axis heads returned', required=False),
    'outstanding_job_refs': Field('record_refs', 'The records of the jobs the axis heads left outstanding',
                                  required=False),
})


def final_to_parent(summary, completion, selection):
    axes, annotations = summary['axes'], summary['annotations']
    result = {'credit': completion['credit'],
              'finding': {'annotations': annotations,
                          **({'best_annotation': annotations[0]}
                             if annotations and annotations[0]['status'] != 'unknown' else {}),
                          'commissions': len(summary['commissions']),
                          'axes': {slot: {'credit': axis['credit'], 'commissions': len(axis['credit_after_each_return']),
                                          'outstanding_jobs': len(axis['outstanding_job_refs'])}
                                   for slot, axis in axes.items()}}}
    if 'record_refs' in selection:
        result['record_refs'] = list(dict.fromkeys(ref for axis in axes.values() for ref in axis['record_refs']))
    if 'outstanding_job_refs' in selection:
        result['outstanding_job_refs'] = list(dict.fromkeys(
            ref for axis in axes.values() for ref in axis['outstanding_job_refs']))
    return result
