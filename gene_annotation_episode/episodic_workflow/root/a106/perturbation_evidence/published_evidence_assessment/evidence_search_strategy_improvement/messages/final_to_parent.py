"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: for each current intervention grading sheet (G1) and each current
A106 final subscore (G2) the chain below saved and returned (each sheet its own entry, never combined), the
controlled features code read from the sheet (``INVESTIGATION_FINDING_FEATURES_a106.md`` G1 and G2) with the sheet's
reference. No model-written text is returned.

Selectable, as counts and references only: ``literature_source_lead_dispositions`` (how many sources the validated
leads, returned by the searches, found relevant, and those sources)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    finding_form)

LEADS = 'literature_source_lead_dispositions'

LEADS_FORM = RecordForm({
    'relevant_lead_count': Field('integer', 'Sources the latest validated lead per source found relevant'),
    'lead_source_refs': Field('record_refs', 'Those sources'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the current G1 and G2 sheets', form=finding_form()),
    LEADS: Field('record', 'The verified source leads as a count and the relevant sources', form=LEADS_FORM,
                 required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': summary['a106_findings']}
    if LEADS in selection:
        relevant = list(dict.fromkeys(lead['source_ref'] for lead in summary['source_lead_dispositions']
                                      if lead['disposition'] == 'relevant'))
        result[LEADS] = {'relevant_lead_count': len(relevant), 'lead_source_refs': relevant}
    return result
