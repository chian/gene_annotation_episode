"""What this episode is for: the A103 head's literature investigation, working out which published evidence bears on
the assigned gene-context question. Carried from the episode's own ``goal.py`` at 97308b94c (the A103 sentence and
the ``literature`` role sentence of the old ``source_contracts``) and from its old ``episode.py`` (``unit``,
``result``)."""

BINDING_PATH = 'gene_context_evidence/published_evidence_assessment'
GOAL = ('For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene '
        'identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their '
        'source and scope.\n\n'
        'Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary '
        'searches and source reads directly, or assign a strategy investigation when that narrower question '
        'warrants iteration.')
UNIT = 'One literature action or child literature commission'
RESULT = 'Assessed literature findings with their record references'
