"""What this episode is for: the published evidence that bears on the assigned scientific question, carried from
the episode's own ``goal.py`` (the A101 sentence) and the ``literature`` role sentence of the old
``source_contracts`` at 97308b94c."""

BINDING_PATH = 'sequence_homology_evidence/published_evidence_assessment'
GOAL = ('For A101, identify the actual sequence or region and its aligned homolog before using a source claim. '
        'Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database '
        'labels, and their applicability to the target distinct and source-grounded.\n\n'
        'Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary '
        'searches and source reads directly, or assign a strategy investigation when that narrower question '
        'warrants iteration.')
UNIT = ('one model-selected tool call (an access or acquisition tool), or one commission of the investigation of the '
        'search strategy, or the report of the published evidence')
RESULT = ('the published evidence found for the assigned question, with its source references, the source claim '
          'and subject of each item and what stays unresolved')
