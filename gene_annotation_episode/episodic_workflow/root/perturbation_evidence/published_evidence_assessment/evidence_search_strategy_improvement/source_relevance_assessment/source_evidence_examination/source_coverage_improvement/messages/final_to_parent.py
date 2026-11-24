"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity signal
and nothing restates it) and the finding: for each current intervention grading sheet (G1) and each current A106 final
subscore (G2) the Episode saved, the controlled features code read from the sheet with the sheet's reference. No
model-written text is returned.

Selectable, as counts and references only: ``literature_source_lead_dispositions`` (how many sources were verified by an
extraction, and those sources) and ``record_refs`` (the perturbation sheets the extractions saved)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    finding_form)

LEADS = 'literature_source_lead_dispositions'

LEADS_FORM = RecordForm({
    'relevant_lead_count': Field('integer', 'Sources verified by an extraction'),
    'lead_source_refs': Field('record_refs', 'Those sources'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the current G1 and G2 sheets', form=finding_form()),
    LEADS: Field('record', 'The verified sources as a count and the sources', form=LEADS_FORM, required=False),
    'record_refs': Field('record_refs', 'The perturbation sheets the extractions saved', required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': summary['a106_findings']}
    if LEADS in selection:
        result[LEADS] = {'relevant_lead_count': len(summary['lead_source_refs']),
                         'lead_source_refs': summary['lead_source_refs']}
    if 'record_refs' in selection:
        result['record_refs'] = summary['sheet_refs']
    return result
