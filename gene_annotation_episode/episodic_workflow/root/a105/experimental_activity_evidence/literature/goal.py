"""What this episode is for: the A105 investigation of which published evidence bears on the assigned scientific
question, carried from the old ``goal.py`` (``LiteratureGoal.instructions``) at 97308b94c. ``messages/internal_summary.py``
shows it to the model."""

BINDING_PATH = 'experimental_activity_evidence/literature'
GOAL = ('Investigate which published evidence bears on the assigned scientific question. You run no search, obtain no '
        'paper and read no paper yourself; you assign the strategy investigation, which writes the searches and has '
        'them run.\n'
        'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted '
        'child forms inform later choices; no child order, reading quota or complete-document requirement is '
        'prescribed. Negative findings and qualifications can advance the investigation. Nothing here is assessed by '
        'a reasoning commit: what the leaves below extract is graded automatically. Navigation and repeated reading '
        'earn no scientific credit by themselves. A numerical accumulation controller (adaptive gamma, no input list) '
        'decides continuation at no cost: after 8 units attempted and 4 observed it fits a yield model, a unit is flat '
        "when the upper bound of the expected next marginal credit is at or below gamma (the larger of one result's "
        'resolution and 0.1 x the median of the recent productive credits), and it stops after 4 flat units in a row.')
UNIT = ('one model-selected unit for the assigned published-evidence question: a read of a held record or one '
        'commission of the search-strategy investigation')
RESULT = ('the typed investigation finding of the published-evidence investigation (the per-annotation scores and the '
          'controlled features of the grading sheet rows), with the source-lead dispositions the parent selects')
