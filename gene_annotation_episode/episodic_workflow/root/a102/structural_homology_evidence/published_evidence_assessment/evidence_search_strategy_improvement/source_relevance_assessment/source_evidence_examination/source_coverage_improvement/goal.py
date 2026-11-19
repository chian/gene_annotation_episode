"""What this episode is for: the A102 reading of one source in document order from a starting window, carried from
the old ``goal.py`` of ``literature_ordered`` at 97308b94c."""

BINDING_PATH = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
GOAL = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte '
        'continuations and retain representation identity. Decide whether to continue, reread, change the examined '
        'window or interpret obtained evidence from actual outcomes.\n'
        'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted '
        'child forms inform later choices; no child order, reading quota or complete-document requirement is '
        'prescribed. A one-off search/read is an ordinary tool. A supplied reading selector is context, not an '
        "automatically executed action. Preserve the source's actual subject, experimental conditions, "
        'representation, version and UTF-8 byte anchors. Distinguish source claims from their applicability to the '
        'fixed target. Negative findings and qualifications can advance the investigation. Commit interpretations '
        "with the common reasoning action and update only the parent's declared typed form in that same work call. "
        'Navigation, byte coverage and repeated reading earn no scientific credit by themselves. The commissioned '
        "task's own yield settings guide continuation.")
UNIT = ('one model-selected tool call on the assigned source (an access tool that reads, rereads or moves the '
        'examined window, a structure grading that saves a source-geometry sheet, or a reasoning commit)')
RESULT = ('the controlled features of the current source-geometry sheets saved from the source, read in document '
          "order from the starting window, with the commissioned task's typed answers (screening answers, "
          'source-lead dispositions)')
