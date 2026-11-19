"""What this episode is for: the A104 reading of the passages of one source its parent selected, carried from the
old ``goal.py`` of ``literature_targeted`` at 97308b94c."""

BINDING_PATH = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
GOAL = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
        'qualifications or alternative passages as needed and revise the interpretation from actual outcomes. '
        'Separate spans remain separate; never concatenate them into a fabricated quotation.\n'
        'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted '
        'child forms inform later choices; no child order, reading quota or complete-document requirement is '
        'prescribed. A one-off search/read is an ordinary tool. A supplied reading selector is context, not an '
        "automatically executed action. Preserve the source's actual subject, experimental conditions, "
        'representation, version and UTF-8 byte anchors. Distinguish source claims from their applicability to the '
        'fixed target. Negative findings and qualifications can advance the investigation. Commit interpretations '
        "with the common reasoning action and update only the parent's declared typed form in that same work call. "
        'Navigation, byte coverage and repeated reading earn no scientific credit by themselves. The commissioned '
        "task's own yield settings guide continuation.")
UNIT = ('one model-selected tool call on the assigned source (a catalog lookup, an access tool, a reasoning commit, '
        'or the report of the interpretation)')
RESULT = ('the interpretation of what the supplied passages say for the assigned question, span by span, with '
          "the commissioned task's typed answers (screening answers, source-lead dispositions)")
