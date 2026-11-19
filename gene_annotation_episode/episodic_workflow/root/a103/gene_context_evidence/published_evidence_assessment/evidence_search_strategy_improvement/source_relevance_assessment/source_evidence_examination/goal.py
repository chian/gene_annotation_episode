"""What this episode is for: deciding where and how one exact source should be examined for the A103 question.
Carried from the episode's own ``goal.py`` at 97308b94c (the A103 sentence) and the page role sentence of the old
``source_contracts``."""

BINDING_PATH = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
GOAL = ('For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene '
        'identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their '
        'source and scope.\n\n'
        'Investigate where and how this exact source should be examined. Choose ordinary source operations or '
        'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit '
        'some XML headings, tables and footnotes; retained original bytes remain addressable.')
UNIT = ('one model-selected tool call on the assigned source, one child commission (a table, an ordered reading or '
        'targeted passages of the source), or the report of the finding')
RESULT = ('the finding about the examined source for the assigned question: the actual source claim, the actual '
          'source subject and its qualification, reading by reading')
