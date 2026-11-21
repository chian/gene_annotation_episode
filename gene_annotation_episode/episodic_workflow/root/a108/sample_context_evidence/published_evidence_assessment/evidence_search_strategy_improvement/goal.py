"""What this episode is for: which searches are productive for the assigned organism-context question. It is
nano-graphrag's strategy: it proposes searches, one query at a time, and hands each to the search level; it cannot
search, fetch or read a paper, and nothing in it is assessed by a reasoning commit. A query handed out is done.

Carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_strategy`` at 97308b94c, with the
ordinary searches, source reads, reasoning commit and the other task kinds removed."""

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
ROLE_INSTRUCTION = (
    "Investigate which searches are productive for whether the proposed protein function fits the actual organism's "
    "biology and sample conditions: physiology, environment, availability of substrates and cofactors, and "
    "localization. The supplied organism, strain and sample context is a job operand, not evidence. Write one "
    "literature search at a time (write_search: a literal provider query, written from the information the question "
    "needs and the context records, never copied from the objective), then hand it to the search child with its "
    "objective; the child runs it, picks a paper and has the paper examined. A search you handed out is done: write "
    "the next one in the light of what the child returned (its credit and the features of its findings). You run no "
    "search, fetch no paper and read no paper yourself, and nothing you write is returned. The configured controller "
    "alone decides when this episode stops.")
GOAL = ROLE_INSTRUCTION
UNIT = ('one model-selected search written as a record of this episode, or one child commission (the search of one '
        'written query)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved (the '
          "children's), with the sheet and graded assessment references, and the verified source leads as counts "
          'and references')
