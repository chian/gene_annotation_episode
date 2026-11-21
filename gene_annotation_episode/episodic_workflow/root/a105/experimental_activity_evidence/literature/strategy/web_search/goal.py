"""What this episode is for: the A105 assessment of which returned papers merit examination for the assigned question,
carried from the old ``goal.py`` (``LiteratureGoal.instructions``: the role instruction of ``literature_search``) at
97308b94c. The planning question is ``PLANNING_QUESTION``; ``task.py`` and ``messages/internal_summary.py`` show it to
the model."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search'
GOAL = ('Investigate which returned papers merit examination for the assigned question. Search results are '
        'source-discovery information: you receive one query, its provider search is run for you and Jev measures every '
        'hit once. You pick one unprocessed hit; its paper is obtained and examined as a page. You read nothing and '
        'extract nothing yourself.\n'
        'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted '
        'child forms inform later choices. Nothing here is assessed by a reasoning commit: what the leaves below '
        'extract is graded automatically. A numerical controller with no cost decides continuation: after 8 units it '
        'fits the yield of the units and stops after 4 units in a row whose expected next credit is at most its '
        'adaptive threshold, not when the search results run out.')
UNIT = ('one unit for the assigned search results: the provider search of the query, the measurement of the hits, the '
        'pick of one hit, or the examination of its paper as a page')
RESULT = ('the typed investigation finding of the assessment of which of the returned papers merit examination for '
          'the assigned question (the per-annotation scores and the controlled features of the grading sheet rows), '
          'with the source-lead dispositions the parent selects')
PLANNING_QUESTION = ('Which unprocessed hit should be examined next, using the Jev measurements and the measured '
                     'results of the pages already examined? Preserve the original objective.')
