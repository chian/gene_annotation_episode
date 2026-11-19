"""What this episode is for: the assessment of which returned sources merit examination for the A101 question,
carried from the episode's own ``goal.py`` (the A101 sentence) and the search role sentence of the old
``source_contracts`` at 97308b94c."""

BINDING_PATH = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
GOAL = ('For A101, identify the actual sequence or region and its aligned homolog before using a source claim. '
        'Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database '
        'labels, and their applicability to the target distinct and source-grounded.\n\n'
        'Investigate which returned sources merit examination for the assigned question. Search results are '
        'source-discovery information. Examine original sources and their conditions before asserting biological '
        'evidence. A page child can investigate where and how to examine a selected source.')
UNIT = ('one model-selected tool call (an access or acquisition tool), or one commission of the examination of a '
        'selected source, or the report of the relevance assessment')
RESULT = ('the assessment of which of the found sources merit examination for the assigned question, source by '
          'source, with what the examinations of selected sources returned')
