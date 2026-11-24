"""What this episode is for: the A106 search for which returned papers merit examination for the assigned question,
carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_search`` at 97308b94c.

It is nano-graphrag's web search: it receives one query (``search_query_ref``, a record of its strategy); the provider
search runs automatically and Jev scores every hit once, automatically; the model picks ONE unprocessed hit; the
paper is obtained when its page is built; a hit picked is done. It cannot read a paper or extract from one. The old
text also joined the perturbation task text and the A106 sub-score task text; those describe the reading and grading,
which belong to the leaves, and are not this episode's."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
ROLE_INSTRUCTION = ('Investigate which returned papers merit examination for the assigned question: intervention '
                    'experiments (a gene, protein or region of it removed, replaced, truncated, varied or restored) '
                    'with a measured outcome that shows what the supplied molecule contributes. The search for the '
                    'query you were handed runs for you, and every hit it returned is measured once against the '
                    'question. Pick one unprocessed hit at a time; its paper is obtained and examined for you. A '
                    'hit you picked is done. A search result, its title or its abstract is discovery information, '
                    'not evidence. You cannot read a paper or extract from one.')
GOAL = ROLE_INSTRUCTION
UNIT = ('one unit: the provider search of the handed query, Jev\'s measurement of the new hits, the pick of one '
        'unprocessed hit (its paper is obtained), or the examination of that paper')
RESULT = ('the credit of the verified source leads the picked papers gave for the assigned question, with the '
          'controlled features of the graded sheets the examinations saved and the sources verified as leads')
