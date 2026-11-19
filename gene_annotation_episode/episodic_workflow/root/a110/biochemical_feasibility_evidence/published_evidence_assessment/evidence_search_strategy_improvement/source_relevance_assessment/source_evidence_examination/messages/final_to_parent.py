"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: the controlled features code read from the typed assessments the
Episode holds (its children's returned findings among them; ``INVESTIGATION_FINDING_FEATURES_a110.md`` sections 1,
2.3 and 3.3, with their record references) and, for each current reaction sheet it saved or its investigations
returned, the features code read from the sheet with the sheet's reference (each sheet its own entry, never
combined). No model-written text is returned."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.finding_forms import (
    investigation_finding_form)

FINDING_FORM = investigation_finding_form('One entry per current reaction sheet saved from the examined source, by '
                                          'the Episode or its investigations')
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the held assessments and the saved reaction sheets',
                     form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'],
            'finding': {**summary['investigation_finding'], 'reaction_sheets': summary['reaction_sheets']}}
