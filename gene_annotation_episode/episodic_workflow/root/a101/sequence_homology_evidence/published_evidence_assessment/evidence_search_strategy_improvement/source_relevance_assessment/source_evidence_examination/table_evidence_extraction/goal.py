"""What this episode is for: the examination of one selected table or spreadsheet sheet of one source for the A101
question, carried from the episode's own ``goal.py`` (the A101 sentence) and the table role sentence of the old
``source_contracts`` at 97308b94c."""

BINDING_PATH = ('sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                'source_relevance_assessment/source_evidence_examination/table_evidence_extraction')
GOAL = ('For A101, identify the actual sequence or region and its aligned homolog before using a source claim. '
        'Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database '
        'labels, and their applicability to the target distinct and source-grounded.\n\n'
        'Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and '
        'footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches '
        'keep their native identity. Article XML tables are read through exact original-source windows.')
UNIT = ('one model-selected tool call on the assigned source (one table or sheet reading action), or the report of '
        'the interpretation')
RESULT = ('the interpretation of the selected table or sheet of the source for the assigned question, reading by '
          'reading, with its rows, headers, conditions and footnotes')
