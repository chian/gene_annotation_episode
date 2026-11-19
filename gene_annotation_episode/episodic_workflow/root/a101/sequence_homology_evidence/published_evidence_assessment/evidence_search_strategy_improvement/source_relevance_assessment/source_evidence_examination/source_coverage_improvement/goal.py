"""What this episode is for: the ordered reading of one source for the A101 question, carried from the episode's own
``goal.py`` (the A101 sentence) and the ordered-reading role sentence of the old ``source_contracts`` at 97308b94c."""

BINDING_PATH = ('sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                'source_relevance_assessment/source_evidence_examination/source_coverage_improvement')
GOAL = ('For A101, identify the actual sequence or region and its aligned homolog before using a source claim. '
        'Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database '
        'labels, and their applicability to the target distinct and source-grounded.\n\n'
        'Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte '
        'continuations and retain representation identity. Decide whether to continue, reread, change the '
        'examined window or interpret obtained evidence from actual outcomes.')
UNIT = 'one model-selected tool call on the assigned source (one ordered reading action), or the report of the interpretation'
RESULT = 'the interpretation of the source read in order for the assigned question, window by window, with its coverage'
