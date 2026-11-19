"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: for each partner sheet this Episode and its children saved, the
controlled features code read from the sheet's cells (``INVESTIGATION_FINDING_FEATURES_a107.md`` section 2.3, E6)
with the sheet's reference, and the agreement counts over them. No model-written text is returned."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.partner_population_catalog import (
    PARTNER_CELLS_MEANING)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    AGREEMENT, FEATURES, MEANINGS)

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'refs': 'record_refs'}


def feature_field(name, rule, required):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1], required)
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name], required)


SHEET_FORM = RecordForm({name: feature_field(name, rule, required) for name, (rule, required) in FEATURES.items()})
FINDING_FORM = RecordForm({
    # Owner's grading decision (row 6), the meaning of the partner sheet's cells.
    'partner_sheets': Field('list', 'One entry per partner sheet saved by this Episode or its descendants. '
                            + PARTNER_CELLS_MEANING, items=SHEET_FORM),
    **{name: Field('integer', meaning) for name, meaning in AGREEMENT.items()},
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the partner sheets of the examined source',
                     form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'],
            'finding': {'partner_sheets': summary['partner_sheets'], **summary['partner_agreement']}}
