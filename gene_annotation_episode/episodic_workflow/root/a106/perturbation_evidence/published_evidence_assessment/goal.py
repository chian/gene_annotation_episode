"""What this episode is for: the A106 investigation of which published evidence bears on the assigned scientific
question, carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of role ``literature`` at 97308b94c.

It is a level above the search level of nano-graphrag's shape: it cannot search, fetch or read a paper. It hands its
strategy child the question and the one task (``verified_source_leads``); the chain below it writes the searches, runs
them, picks the hits, obtains the papers, reads them and grades what they report. The old text also joined the
perturbation task text and the A106 sub-score task text; those describe the reading and grading, which belong to the
leaves, and are not this episode's."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment'
ROLE_INSTRUCTION = ('Investigate which published evidence bears on the assigned scientific question: intervention '
                    'experiments (a gene, protein or region of it removed, replaced, truncated, varied or restored) '
                    'with a measured outcome that shows what the supplied molecule contributes. You cannot search, '
                    'fetch or read a paper yourself. Commission the search strategy investigation (the strategy '
                    'child), which writes the searches and returns the credit and the controlled features of the '
                    'graded sheets below it; a source it verified as a lead for the question comes back as a '
                    'reference. Your own reading is of the records you hold.')
GOAL = ROLE_INSTRUCTION
UNIT = ('one model-selected unit: a read of the records this episode holds, or the commission of the search '
        'strategy investigation')
RESULT = ('the credit of the verified source leads for the assigned question, with the controlled features of the '
          'graded sheets the chain below saved and the sources it verified as leads')
