"""What this episode is for: the examination of one exact source for the A101 question, carried from the episode's own
``goal.py`` (the A101 sentence) and the page role sentence of the old ``source_contracts`` at 97308b94c."""

BINDING_PATH = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
GOAL = ('For A101, identify the actual sequence or region and its aligned homolog before using a source claim. '
        'Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database '
        'labels, and their applicability to the target distinct and source-grounded.\n\n'
        'Investigate where and how this exact source should be examined. Choose ordinary source operations or '
        'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit '
        'some XML headings, tables and footnotes; retained original bytes remain addressable.')
UNIT = ('one model-selected tool call on the assigned source, or one commission of a table, ordered-reading or '
        'targeted-passage investigation of it, or the report of the interpretation')
RESULT = ('the interpretation of where and how the assigned source was examined for the assigned question, reading '
          'by reading, with what the child investigations returned')
