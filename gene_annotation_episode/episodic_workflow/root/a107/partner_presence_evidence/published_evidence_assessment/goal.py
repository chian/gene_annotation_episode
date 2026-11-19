"""What this episode is for: improving the published partner-requirement, omission/addback and coexpression evidence
retained for the assigned question. Carried from the old ``goal.py`` (the ``literature`` role sentence of the old
``contracts._ROLE_INSTRUCTIONS`` followed by the A107 partner sentences) at 97308b94c."""

BINDING_PATH = 'partner_presence_evidence/published_evidence_assessment'
GOAL = ('Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary '
        'searches and source reads directly, or assign a strategy investigation when that narrower question '
        'warrants iteration.\n'
        'Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and '
        'partner roles, normalization, nonpartner conditions, physical measurement identity, source units and '
        'uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target '
        'correspondence or annotation credit. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call (a source operation, an acquisition operation, a partner population operation '
        'or a partner grader operation), or one commission of an evidence-search-strategy-improvement child '
        'for a narrower search-strategy question')
RESULT = ('the controlled features of each partner sheet this episode and its descendants saved, with the '
          "sheet's reference, and the agreement counts over them")
