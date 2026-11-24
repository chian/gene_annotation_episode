"""What this episode is for: the A108 extraction of one chunk of one source's text, for the assigned organism-context
question (nano-graphrag's chunk leaf: it extracts its one chunk and nothing else)."""

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
GOAL = ('Extract what the chunk reports for the assigned organism-context question: whether the proposed protein '
        'function fits the actual organism, its physiology, environment, availability of substrates and cofactors, '
        'and localization, at the resolution the chunk states (organism, strain, sample, condition). Extract exactly '
        'what the chunk says and nothing else; what it does not state stays unstated.')
UNIT = ('one extraction of the chunk: the typed commit of what it reports with its grading, whose subscoring sheet is '
        'saved in the same unit')
RESULT = ('the controlled features code reads from the A108 subscoring sheets saved, with the sheet and graded '
          "assessment references, and the commission's source leads as a count and references")
