"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: the controlled features code read from each current assay grading
and aggregation sheet the Episode saved or its children returned (each sheet its own entry, never combined), with
its reference, and the counts of the investigation. No model-written text is returned. Selectable:
``literature_screening_answers`` and ``literature_source_lead_dispositions`` (counts and references)."""
from method_loop import RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SCREENING, finding_of, lead_answer, return_fields, screening_answer)

RETURN_FORM = RecordForm(return_fields())


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': finding_of(summary['assay_sheets'], summary['aggregation_sheets'],
                                    summary['proposed_annotation_ref'], summary['no_applicable_spans'])}
    if SCREENING in selection:
        result[SCREENING] = screening_answer(summary['no_applicable_spans'], summary['screening_covered'])
    if LEADS in selection:
        result[LEADS] = lead_answer(summary['lead_source_refs'])
    return result
