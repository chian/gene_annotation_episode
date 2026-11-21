"""The return (A105 scoring paradigm, OWNER_DECISION 10: the page updates the subscoring sheet and the levels above only
receive controlled results). Always returned: the Episode's credit (the system hands it in ``completion``) and the
finding: the per-annotation scores and the controlled features of the subscoring rows the page's latest sheet update
produced, as numbers, counts and vocabulary values. Selectable: ``sheet_state_refs`` (the persisted subscoring-sheet states,
the whole sheet as it stands after this page, or, when the page ran no update, the states it was given),
``literature_screening_answers`` and ``literature_source_lead_dispositions`` (counts and references). The leaf records, the
graders and the converted results stay in this episode; no model-written text is returned."""
from method_loop import RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SCREENING, SHEET_STATE_REFS, lead_answer, screening_answer, sheet_finding_of, sheet_return_fields)

RETURN_FORM = RecordForm(sheet_return_fields())


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': sheet_finding_of(summary['sheet_update'])}
    if SHEET_STATE_REFS in selection:
        result[SHEET_STATE_REFS] = summary['sheet_state_refs']
    if SCREENING in selection:
        result[SCREENING] = screening_answer(summary['no_applicable_spans'], summary['screening_covered'])
    if LEADS in selection:
        result[LEADS] = lead_answer(summary['lead_source_refs'])
    return result
