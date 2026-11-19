"""What this episode is for: the improvement of the search that finds relevant published sources, carried from the
episode's own ``goal.py`` (the A101 sentence) and the strategy role sentence of the old ``source_contracts`` at
97308b94c."""

BINDING_PATH = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
GOAL = ('For A101, identify the actual sequence or region and its aligned homolog before using a source claim. '
        'Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database '
        'labels, and their applicability to the target distinct and source-grounded.\n\n'
        'Investigate which search approach is productive. Keep the information objective and evidence context '
        'separate from a literal provider query. Revise terms or source choices in light of actual search/read '
        'outcomes; a search child can investigate which returned sources deserve examination.')
UNIT = ('one model-selected tool call (an access or acquisition tool), or one commission of the assessment of which '
        'returned sources merit examination, or the report of the search strategy')
RESULT = ('the search approaches tried with what each search and read returned, and the relevant source candidates '
          'found, with what the assessments of returned sources returned')
