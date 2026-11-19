"""What this episode is for: the examination of one selected table or spreadsheet sheet of one source for the A103
question, carried from the episode's own ``goal.py`` at 97308b94c (the A103 sentence) and the table role sentence
of the old ``source_contracts``."""

BINDING_PATH = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
GOAL = ('For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene '
        'identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their '
        'source and scope.\n\n'
        'Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and '
        'footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches '
        'keep their native identity. Article XML tables are read through exact original-source windows.')
UNIT = ('one model-selected tool call on the assigned source (one table or sheet reading action), or the report of '
        'the finding')
RESULT = ('the finding of the selected table or sheet of the source for the assigned question: the actual source '
          'claim, the actual source subject and its qualification, reading by reading, with its rows, headers, '
          'conditions and footnotes')
