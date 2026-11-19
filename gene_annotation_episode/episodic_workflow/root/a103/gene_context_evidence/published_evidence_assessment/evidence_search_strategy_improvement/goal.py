"""What this episode is for: improving the literature search strategy so that relevant sources are found for the A103
question. Carried from the episode's own ``goal.py`` at 97308b94c (the A103 sentence and the ``literature_strategy``
role sentence of the old ``source_contracts``) and from its old ``episode.py`` (``unit``, ``result``)."""

BINDING_PATH = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
GOAL = ('For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene '
        'identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their '
        'source and scope.\n\n'
        'Investigate which search approach is productive. Keep the information objective and evidence context '
        'separate from a literal provider query. Revise terms or source choices in light of actual search/read '
        'outcomes; a search child can investigate which returned sources deserve examination.')
UNIT = ('one model-selected tool call (an access or acquisition operation), one child commission (the assessment of '
        'which returned sources merit examination), or the report of the search strategy')
RESULT = 'The improved search strategy and the sources it found'
