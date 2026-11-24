"""What this episode is for: the A108 extraction of one table region of one source (nano-graphrag's table leaf: it
extracts its one table region and nothing else)."""

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
GOAL = ('Extract what the table region reports for the assigned organism-context question: whether the proposed '
        'protein function fits the actual organism, its physiology, environment, availability of substrates and '
        'cofactors, and localization, at the resolution the table states (organism, strain, sample, condition). Read '
        'the rows with their headers, conditions and footnotes together. Extract exactly what the table says and '
        'nothing else; what it does not state stays unstated.')
UNIT = ('one extraction of the table region: the typed commit of what it reports with its grading, whose subscoring '
        'sheet is saved in the same unit')
RESULT = ('the controlled features code reads from the A108 subscoring sheets saved, with the sheet and graded '
          "assessment references, the cell rows of the requested components and the commission's source leads as a "
          'count and references')
