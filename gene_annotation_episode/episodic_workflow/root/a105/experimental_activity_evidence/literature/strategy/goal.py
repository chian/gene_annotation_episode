"""What this episode is for: the A105 investigation of which search approach is productive for the assigned
question, carried from the old ``goal.py`` (``LiteratureGoal.instructions``: the role instruction of
``literature_strategy``) at 97308b94c. The planning question is ``PLANNING_QUESTION``; ``task.py`` and
``messages/internal_summary.py`` show it to the model."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy'
GOAL = ('Investigate which search approach is productive. Keep the information objective and evidence context '
        'separate from a literal provider query. Revise terms in light of what the earlier searches returned.\n'
        'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted '
        'child forms inform later choices. You write queries and hand the search child one at a time; you do not run '
        'them or read any paper: the search child runs them. Nothing here is assessed by a reasoning commit: what the '
        'leaves below extract is graded automatically. Negative findings can advance the investigation. A '
        'verified_source_leads commission has no cost: once 8 units are attempted and 4 observed, a unit is flat when '
        'the upper bound of its expected next marginal credit is at or below the adaptive threshold (the larger of one '
        'result and 0.1 x the median of recent productive credits), and the work stops after 4 flat units in a row.')
UNIT = ('one model-selected unit for the assigned search strategy: the writing of a query or one commission of the '
        'search child with a written query')
RESULT = ('the typed investigation finding of the search-strategy investigation (the per-annotation scores and the '
          'controlled features of the grading sheet rows), with the source-lead dispositions the parent selects')
PLANNING_QUESTION = ('Which query should be proposed next, using the actual findings the earlier searches returned? '
                     'Revise the approach from outcomes while preserving the original objective.')
