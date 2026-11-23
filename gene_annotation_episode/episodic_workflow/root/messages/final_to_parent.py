"""The return of the annotation: controlled data only. Always returned: ``credit`` (the annotation credit its
controller stopped on, which the system hands in ``completion``) and ``finding``: the root's scoring sheet
(``annotations``: every candidate annotation the axis heads scored, with its score, the hypervolume over the scores
the axes give it, and the row of each axis that scored it, the highest score first), the best annotation (``best_annotation``:
the first of the sheet, present when its status is known), the claims made from the annotations (``claims``), how many
commissions the root made and, for each of the
nine axes, its credit, how often it was commissioned and how many job records its head left outstanding. Selectable, returned in custody: ``record_refs`` (the records the axis heads returned) and
``outstanding_job_refs`` (the records of the jobs still outstanding, with which a later run can return to them)."""
from method_loop import ChoiceField, Field, RecordForm

from ..credit import AXIS_WEIGHTS
from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.claim_generation import (
    PARTNER_KINDS, PREDICATES as CLAIM_PREDICATES)

from .internal_summary import IDENTITY_FIELDS
from .read_from_child import FUNCTION_SOURCES, ROW_STATUS, VOCABULARIES

_ABSENT = ' (absent when the status is unknown)'
AXIS_ROW_FORM = RecordForm({
    'axis': ChoiceField('text', 'The axis whose head scored the annotation', tuple(AXIS_WEIGHTS)),
    'status': ChoiceField('text', 'Whether that evidence is measured, measured as exactly zero, or unknown', ROW_STATUS),
    'score': Field('number', "The score that axis gives the annotation, on the axis's own scale; negative when its "
                             'evidence says the annotation does not hold' + _ABSENT, required=False),
    'support': Field('number', "The summed support of the annotation's claims, for an axis that checks claims",
                     required=False),
    'opposition': Field('number', "The summed opposition of the annotation's claims, for such an axis", required=False),
})
FUNCTION_IDENTIFIER_FORM = RecordForm({
    'source': ChoiceField('text', 'Where the identifier is from', FUNCTION_SOURCES),
    'identifier': Field('text', 'The function-level identifier exactly as its source gives it'),
    'hit_count': Field('integer', 'The proteins behind the annotation that carry it'),
})
MEMBER_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the annotation', VOCABULARIES),
    'name': Field('text', 'Its name exactly as its source gives it', required=False),
    'identifier': Field('text', 'Its own identifier: a family accession or a record reference', required=False),
    'axis': ChoiceField('text', 'The axis whose head named it', tuple(AXIS_WEIGHTS)),
    'score': Field('number', 'The score that axis gave it'),
})
ANNOTATION_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate annotation: product (a database search\'s '
                                      'function), profile_family (a family of a profile database) or '
                                      'reference_sequence (a sequence record it was compared with)', VOCABULARIES),
    'name': Field('text', 'The name of the annotation exactly as its source gives it', required=False),
    'identifier': Field('text', 'The identifier of the annotation: a family accession or a record reference',
                        required=False),
    'status': ChoiceField('text', 'Whether the merged evidence is measured, measured as exactly zero, or unknown',
                          ROW_STATUS),
    'score': Field('number', 'The annotation score: the hypervolume prod_i (1 + k * s_i) ** w_i - 1 over the scores '
                             's_i the axes give the annotation (0 for an axis that has not scored it)' + _ABSENT,
                   required=False),
    'function_identifiers': Field('list', 'The function-level identifiers of the proteins behind the annotation',
                                  items=FUNCTION_IDENTIFIER_FORM, required=False),
    'hits_without_identifier': Field('integer', 'The proteins behind it that carry no such identifier', required=False),
    'rows': Field('list', 'One row per axis whose head scored the annotation', items=AXIS_ROW_FORM),
    'members': Field('list', 'Every annotation on this line (the names the heads gave this one function), with the axis '
                             'that named it and the score that axis gave it', items=MEMBER_FORM),
})
ANNOTATION_IDENTITY_FORM = RecordForm({name: ANNOTATION_FORM.fields[name] for name in IDENTITY_FIELDS})
CLAIM_FORM = RecordForm({
    'claim_ref': Field('text', 'The claim: a hypothesis record the root made from the annotation'),
    'annotation': Field('record', 'The candidate annotation the claim was made from', form=ANNOTATION_IDENTITY_FORM),
    'predicate': ChoiceField('text', 'What the claim says the protein does to the molecule', CLAIM_PREDICATES),
    'partner': Field('text', 'The molecule of the claim, by the name it was found under in a database'),
    'partner_kind': ChoiceField('text', 'Whether the molecule is a protein or a small molecule', PARTNER_KINDS),
    'commissions': Field('integer', 'How often a head was commissioned on the claim'),
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
    'claims': Field('list', 'The claims made from the candidate annotations', items=CLAIM_FORM),
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
                          'claims': [{'claim_ref': claim['claim_ref'], 'annotation': claim['annotation'],
                                      'predicate': claim['predicate'], 'partner': claim['partner'],
                                      'partner_kind': claim['partner_kind'],
                                      'commissions': sum(axis['claim_commissions'].get(claim['claim_ref'], 0)
                                                         for axis in axes.values())}
                                     for claim in summary['claims']],
                          **({'best_annotation': annotations[0]}
                             if annotations and annotations[0]['status'] != 'unknown' else {}),
                          'commissions': len(summary['commissions']),
                          'axes': {slot: {'credit': axis['credit'], 'commissions': len(axis['credit_after_each_return']),
                                          'outstanding_jobs': axis['outstanding_jobs']}
                                   for slot, axis in axes.items()}}}
    if 'record_refs' in selection:
        result['record_refs'] = list(dict.fromkeys(ref for axis in axes.values() for ref in axis['record_refs']))
    if 'outstanding_job_refs' in selection:
        result['outstanding_job_refs'] = list(dict.fromkeys(
            ref for axis in axes.values() for ref in axis['outstanding_job_refs']))
    return result
