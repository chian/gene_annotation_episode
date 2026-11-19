"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: for each current source-geometry sheet the Episode saved, the
controlled features code read from the sheet (``INVESTIGATION_FINDING_FEATURES_a102.md`` section 2.13) and the
sheet's reference. No model-written text is returned.

Selectable, as counts and references only: ``literature_screening_answers`` (how many spans the own
``no_applicable_evidence`` declarations examined, and whether they cover every commissioned span) and
``literature_source_lead_dispositions`` (how many sources the validated leads found relevant,
and those sources)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
    FEATURES, MEANINGS)

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean', 'refs': 'record_refs'}


def feature_field(name, rule):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name])


SHEET_FORM = RecordForm({name: feature_field(name, rule) for name, rule in FEATURES.items()})
FINDING_FORM = RecordForm({
    'structure_sheets': Field('list', 'One entry per current source-geometry sheet saved from the supplied passages',
                              items=SHEET_FORM),
})
SCREENING_FORM = RecordForm({
    'examined_span_count': Field('integer', 'Spans the own no_applicable_evidence declarations examined'),
    'commissioned_spans_covered': Field('boolean', 'Whether those declarations cover every commissioned span'),
})
LEADS_FORM = RecordForm({
    'relevant_lead_count': Field('integer', 'Sources the latest validated lead per source found relevant'),
    'lead_source_refs': Field('record_refs', 'Those sources'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the saved structure sheets', form=FINDING_FORM),
    SCREENING: Field('record', 'The screening answer as counts', form=SCREENING_FORM, required=False),
    LEADS: Field('record', 'The verified source leads as a count and the relevant sources', form=LEADS_FORM,
                 required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': {'structure_sheets': summary['structure_sheets']}}
    if SCREENING in selection:
        result[SCREENING] = {'examined_span_count': len(summary['no_applicable_evidence']),
                             'commissioned_spans_covered': bool(summary['screening_answers'])}
    if LEADS in selection:
        relevant = list(dict.fromkeys(lead['source_ref'] for lead in summary['source_lead_dispositions']
                                      if lead['disposition'] == 'relevant'))
        result[LEADS] = {'relevant_lead_count': len(relevant), 'lead_source_refs': relevant}
    return result
