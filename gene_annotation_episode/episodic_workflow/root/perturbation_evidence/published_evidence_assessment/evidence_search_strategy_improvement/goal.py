"""What this episode is for: the A106 investigation of which search approach is productive for the assigned question,
carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_strategy`` at 97308b94c.

It is nano-graphrag's strategy: it proposes searches, one query at a time, and hands each to its search child; it
cannot search, fetch or read a paper. The old text also joined the perturbation task text and the A106 sub-score task
text; those describe the reading and grading, which belong to the leaves, and are not this episode's."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
ROLE_INSTRUCTION = ('Investigate which search approach is productive for the assigned question: write the literature '
                    'searches that would find intervention experiments (a gene, protein or region of it removed, '
                    'replaced, truncated, varied or restored) with a measured outcome that shows what the supplied '
                    'molecule contributes. Write one query at a time (write_search), then hand it to the search child, '
                    'which runs it, measures its hits, picks the paper worth examining and has it examined. A query '
                    'handed to the child is done. Write the next query from what the earlier ones returned. You '
                    'cannot search, fetch or read a paper yourself; the query is the only text you write, and it '
                    'stays in this episode as a record that the child receives by reference.')
GOAL = ROLE_INSTRUCTION
UNIT = ('one model-selected unit: the writing of one search query, a read of the records this episode holds, or the '
        'commission of the search child with one written query')
RESULT = ('the credit of the verified source leads the searches found for the assigned question, with the controlled '
          'features of the graded sheets the chain below saved and the sources it verified as leads')
