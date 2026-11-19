"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: the controlled features code read from each current assay grading
and aggregation sheet the head saved or its children returned (each sheet its own entry, never combined), with its
reference, and the counts of the investigation for the proposed annotation. No model-written text is returned.
Selectable: ``committed_record_refs``, the assessments and sheets the head committed and the sheets its children
returned."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    FINDING_FORM, finding_of)

COMMITTED = 'committed_record_refs'
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the assay grading and aggregation sheets and the counts of '
                     'the A105 experimental-activity investigation', form=FINDING_FORM),
    COMMITTED: Field('record_refs', 'The assessments and sheets this episode committed and the sheets its children '
                     'returned', required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': finding_of(summary['assay_sheets'], summary['aggregation_sheets'],
                                    summary['proposed_annotation_ref'], summary['no_applicable_spans'])}
    if COMMITTED in selection:
        result[COMMITTED] = summary['committed_record_refs']
    return result
