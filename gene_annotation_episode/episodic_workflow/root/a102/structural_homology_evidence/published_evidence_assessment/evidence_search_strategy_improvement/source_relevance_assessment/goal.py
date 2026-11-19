"""What this episode is for: the A102 investigation of which returned search results merit examination, carried
from the old ``goal.py`` of ``literature_search`` at 97308b94c."""

BINDING_PATH = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
GOAL = ('Investigate which returned sources merit examination for the assigned question. Search results are '
        'source-discovery information. Examine original sources and their conditions before asserting biological '
        'evidence. A page child can investigate where and how to examine a selected source.\n'
        'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted '
        'child forms inform later choices; no child order, reading quota or complete-document requirement is '
        'prescribed. A one-off search/read is an ordinary tool. A supplied reading selector is context, not an '
        "automatically executed action. Preserve the source's actual subject, experimental conditions, "
        'representation, version and UTF-8 byte anchors. Distinguish source claims from their applicability to the '
        'fixed target. Negative findings and qualifications can advance the investigation. Commit interpretations '
        "with the common reasoning action and update only the parent's declared typed form in that same work call. "
        'Navigation, byte coverage and repeated reading earn no scientific credit by themselves. The commissioned '
        "task's own yield settings guide continuation.")
UNIT = ('one model-selected tool call (a literature acquisition, an access tool on a source, a structure grading '
        'that saves a source-geometry sheet, or a reasoning commit) or one commissioned examination of one selected source by a page child')
RESULT = ('the controlled features of the current source-geometry sheets saved by the Episode or returned by its '
          "children, with the commissioned task's typed answers (screening answers, source-lead dispositions)")
