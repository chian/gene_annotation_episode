"""What this episode is for: the A105 reading of the passages of one source its parent selected, carried from the
old ``goal.py`` of ``literature_targeted`` (``LiteratureGoal.instructions``) at 97308b94c."""

BINDING_PATH = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
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
UNIT = ('one model-selected tool call on the assigned source (an access tool, a population sheet, or a reasoning '
        'commit coupled with its grading sheets)')
RESULT = ('the investigation finding of the supplied passages for the assigned question: the controlled features '
          'read from each grading and aggregation sheet saved, with its reference, and the counts of the '
          "investigation; with the commissioned task's answers (screening, relevant lead sources) the parent selects")
