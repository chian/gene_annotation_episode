"""What this episode is for: deciding which of the returned sources merit examination for the A103 question.
Carried from the episode's own ``goal.py`` at 97308b94c (the A103 sentence and the ``literature_search`` role
sentence of the old ``source_contracts``). ``UNIT`` and ``RESULT`` are the earlier port's own statements."""

BINDING_PATH = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
GOAL = ('For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene '
        'identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their '
        'source and scope.\n\n'
        'Investigate which returned sources merit examination for the assigned question. Search results are '
        'source-discovery information. Examine original sources and their conditions before asserting biological '
        'evidence. A page child can investigate where and how to examine a selected source.')
UNIT = ('one model-selected tool call (an access or acquisition operation), one child commission (the examination '
        'of one chosen source), or the report of the relevance judgements')
RESULT = 'The sources judged relevant, with their judgements'
