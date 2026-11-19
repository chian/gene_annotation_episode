"""What this episode is for: the A101 passage reading of one source, carried from its goal at 97308b94c."""

BINDING_PATH = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
GOAL = ('For A101, identify the actual sequence or region and its aligned homolog before using a source claim. '
        'Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database '
        'labels, and their applicability to the target distinct and source-grounded.\n\n'
        'Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
        'qualifications or alternative passages as needed and revise the interpretation from actual outcomes. '
        'Separate spans remain separate; never concatenate them into a fabricated quotation.')
UNIT = 'one model-selected tool call on the assigned source, or the report of the interpretation'
RESULT = 'the interpretation of what the supplied passages say for the assigned question, span by span'
