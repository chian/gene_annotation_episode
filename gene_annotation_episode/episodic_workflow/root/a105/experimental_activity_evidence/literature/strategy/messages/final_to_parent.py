"""The return (A105 scoring paradigm, OWNER_DECISION 10: the levels above the page only receive and pass up controlled
results). Always returned: the Episode's credit (the system hands it in ``completion``) and the finding: the
per-annotation scores and the controlled features of the subscoring rows of the latest web-search return (the whole sheet
as it stands after it), as numbers, counts and vocabulary values; nothing is combined or recomputed here. Selectable:
``sheet_state_refs`` (the persisted sheet states of the latest return, or the states this episode was given when it
commissioned none), ``examined_article_refs`` (the article sources the pages of its web searches examined, so its
parent passes them to its later strategy runs), ``literature_screening_answers`` and ``literature_source_lead_dispositions`` (counts and
references). No model-written text is returned."""
from method_loop import RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    EXAMINED, LEADS, SCREENING, SHEET_STATE_REFS, examined_field, lead_answer, screening_answer, sheet_return_fields)

RETURN_FORM = RecordForm({**sheet_return_fields(), EXAMINED: examined_field()})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': {'scores': list(summary['scores']), 'features': list(summary['features'])}}
    if SHEET_STATE_REFS in selection:
        result[SHEET_STATE_REFS] = list(summary['sheet_state_refs'])
    if EXAMINED in selection:
        result[EXAMINED] = list(summary['examined_article_refs'])
    if SCREENING in selection:
        result[SCREENING] = screening_answer(summary['no_applicable_spans'], summary['screening_covered'])
    if LEADS in selection:
        result[LEADS] = lead_answer(summary['lead_source_refs'])
    return result
