"""What this episode is for: the A108 extraction of the prose windows of one source in document order (nano-graphrag's
report leaf: it takes the windows it is given, each once, in order)."""

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
GOAL = ('Extract what the window reports for the assigned organism-context question: whether the proposed protein '
        'function fits the actual organism, its physiology, environment, availability of substrates and cofactors, '
        'and localization, at the resolution the window states (organism, strain, sample, condition). The windows of '
        'the source come one at a time in document order, each once. Extract exactly what the window says and nothing '
        'else; what it does not state stays unstated.')
UNIT = ('one extraction of the next window: the typed commit of what it reports with its grading, whose subscoring '
        'sheet is saved in the same unit')
RESULT = ('the controlled features code reads from the A108 subscoring sheets saved with the graded interpretations of '
          'the windows, with the sheet and assessment references, the cell rows of the requested components and the '
          "commission's source leads as a count and references")
