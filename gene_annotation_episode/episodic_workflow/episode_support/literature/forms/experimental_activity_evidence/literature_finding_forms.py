"""The controlled forms of what an A105 literature episode returns to its parent: the investigation finding (the
features code reads from the saved assay grading sheets, ``literature_assay_grading_features``), and the selectable
answers of the commissioned literature task as counts and record references. No field holds model text: every text
field is a fixed vocabulary the form validates (``ChoiceField``).

Each episode builds its own ``RETURN_FORM`` from these in its ``final_to_parent.py`` and fills it from its summary
with ``finding_of``, ``lead_answer`` and ``screening_answer``."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assay_grading_features import (
    AGGREGATION_FEATURES, AGGREGATION_MEANINGS, AGGREGATION_OPTIONAL, COUNT_MEANINGS, FEATURES, MEANINGS, OPTIONAL,
    assay_counts)

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
FIELD_TYPES = {'number': 'number', 'nonnegative': 'number', 'count': 'integer', 'boolean': 'boolean',
               'refs': 'record_refs'}


def feature_field(name, rule, meanings=MEANINGS, optional=OPTIONAL):
    if rule[0] == 'choice':
        return ChoiceField('text', meanings[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], meanings[name], required=name not in optional)


SHEET_FORM = RecordForm({name: feature_field(name, rule) for name, rule in FEATURES.items()})
AGGREGATION_FORM = RecordForm({name: feature_field(name, rule, AGGREGATION_MEANINGS, AGGREGATION_OPTIONAL)
                               for name, rule in AGGREGATION_FEATURES.items()})
FINDING_FORM = RecordForm({
    'assay_sheets': Field('list', 'One entry per current assay grading sheet saved by the Episode or returned by '
                          'its children: the controlled features of the sheet', items=SHEET_FORM),
    'aggregation_sheets': Field('list', 'One entry per current across-experiment aggregation sheet saved by the '
                                'Episode or returned by its children', items=AGGREGATION_FORM),
    **{name: Field('integer', meaning) for name, meaning in COUNT_MEANINGS.items()},
    'no_applicable_span_count': Field('integer', 'Examined spans declared, source-grounded, to hold no applicable '
                                      'experiment or result'),
})
LEAD_FORM = RecordForm({
    'relevant_lead_count': Field('integer', 'Distinct sources validated as relevant leads for the commissioned '
                                 'question'),
    'lead_source_refs': Field('record_refs', 'The sources validated as relevant leads'),
})
SCREENING_FORM = RecordForm({
    'examined_span_count': Field('integer', 'Examined spans declared to hold no applicable evidence'),
    'commissioned_spans_covered': Field('boolean', 'Whether those declarations cover every commissioned span'),
})


def return_fields():
    """The fields of an A105 literature episode's return: credit and finding always, the two answers selectable."""
    return {
        'credit': Field('number', "The Episode's credit when its controller stopped it"),
        'finding': Field('record', 'The controlled features of the assay grading sheets and the counts of the '
                         'investigation', form=FINDING_FORM),
        SCREENING: Field('record', 'The screening answer to the commissioned spans', form=SCREENING_FORM,
                         required=False),
        LEADS: Field('record', 'The validated relevant source leads for the commissioned question', form=LEAD_FORM,
                     required=False),
    }


def finding_of(sheets, aggregations, assertion_ref, no_applicable_spans):
    return {'assay_sheets': sheets, 'aggregation_sheets': aggregations, **assay_counts(sheets, assertion_ref),
            'no_applicable_span_count': len(no_applicable_spans)}


def lead_answer(source_refs):
    return {'relevant_lead_count': len(source_refs), 'lead_source_refs': list(source_refs)}


def screening_answer(no_applicable_spans, covered):
    return {'examined_span_count': len(no_applicable_spans), 'commissioned_spans_covered': covered}


__all__ = ['SCREENING', 'LEADS', 'SHEET_FORM', 'FINDING_FORM', 'LEAD_FORM', 'SCREENING_FORM', 'return_fields',
           'finding_of', 'lead_answer', 'screening_answer']
