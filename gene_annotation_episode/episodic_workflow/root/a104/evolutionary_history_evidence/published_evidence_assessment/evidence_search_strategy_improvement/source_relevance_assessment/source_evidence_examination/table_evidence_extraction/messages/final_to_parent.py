"""The return. Always returned: ``credit`` (the system hands it in ``completion``; it is the productivity signal and
nothing restates it) and ``finding``: the controlled features code read from the assay-grading sheets this Episode and
its children saved (the A104 copy of the A105 grader, ``INVESTIGATION_FINDING_FEATURES_a105.md``;
each with the sheet's reference), the features of the assessments their readings committed
(``INVESTIGATION_FINDING_FEATURES_a104.md`` section 5), the counts of graded experiments for the commissioned
assertion, and the references a receiver needs to read the sheets. No model-written text is returned. Selectable,
each controlled: ``literature_screening_answers`` (whether the commissioned spans were examined with no applicable
evidence, and how many spans and bytes) and ``literature_source_lead_dispositions`` (how many relevant source leads
were validated, and their sources)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_assay_grading_features import (
    COUNT_MEANINGS, FEATURES, MEANINGS, OPTIONAL, assay_counts)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_assessment_features import (
    FEATURES as ASSESSMENT_FEATURES)

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
FIELD_TYPES = {'number': 'number', 'nonnegative': 'number', 'count': 'integer', 'boolean': 'boolean',
               'refs': 'record_refs'}


def sheet_field(name, rule):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name], required=name not in OPTIONAL)


def assessment_field(rule, meaning):
    if rule[0] == 'choice':
        return ChoiceField('text', meaning, rule[1])
    return Field(FIELD_TYPES[rule[0]], meaning)


SHEET_FORM = RecordForm({name: sheet_field(name, rule) for name, rule in FEATURES.items()})
ASSESSMENT_FORM = RecordForm({name: assessment_field(rule, meaning)
                              for name, (rule, meaning) in ASSESSMENT_FEATURES.items()})
FINDING_FORM = RecordForm({
    'assay_sheets': Field('list', 'One entry per current assay-grading sheet, own or returned by a child',
                          items=SHEET_FORM),
    'assessments': Field('list', 'One entry per assessment the readings committed, own or returned by a child',
                         items=ASSESSMENT_FORM),
    **{name: Field('integer', meaning) for name, meaning in COUNT_MEANINGS.items()},
    'sheet_record_refs': Field('record_refs', 'The records a receiver needs to read the saved sheets and the '
                               'committed interpretation they grade (references only)'),
})
SCREENING_FORM = RecordForm({
    'answered': Field('boolean', 'Whether the no-applicable-evidence declarations cover every commissioned span'),
    'examined_span_count': Field('integer', 'Spans the declarations examined'),
    'examined_byte_total': Field('integer', 'Bytes the declarations examined'),
})
LEADS_FORM = RecordForm({
    'relevant_lead_count': Field('integer', 'Validated source leads judged relevant for the commissioned question'),
    'lead_source_refs': Field('record_refs', 'The sources of those relevant leads'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the saved sheets and committed assessments',
                     form=FINDING_FORM),
    SCREENING: Field('record', 'The screening answer of a screening commission', form=SCREENING_FORM,
                     required=False),
    LEADS: Field('record', 'The relevant source leads of a verified_source_leads commission', form=LEADS_FORM,
                 required=False),
})


def screening(summary):
    spans = summary['no_applicable_evidence']
    return {'answered': bool(summary['screening_answers']), 'examined_span_count': len(spans),
            'examined_byte_total': sum(span['end'] - span['start'] for span in spans)}


def leads(summary):
    relevant = [lead for lead in summary['source_lead_dispositions'] if lead['disposition'] == 'relevant']
    return {'relevant_lead_count': len(relevant),
            'lead_source_refs': list(dict.fromkeys(lead['source_ref'] for lead in relevant))}


def final_to_parent(summary, completion, selection):
    sheets = summary['assay_sheets']
    result = {'credit': completion['credit'],
              'finding': {'assay_sheets': sheets, 'assessments': summary['assessments'],
                          **assay_counts(sheets, summary['proposed_annotation_ref']),
                          'sheet_record_refs': summary['sheet_record_refs']}}
    if SCREENING in selection:
        result[SCREENING] = screening(summary)
    if LEADS in selection:
        result[LEADS] = leads(summary)
    return result
