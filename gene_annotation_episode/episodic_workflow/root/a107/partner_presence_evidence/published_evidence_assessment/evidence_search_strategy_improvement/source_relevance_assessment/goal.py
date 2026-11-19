"""What this episode is for: deciding which of the located sources merit examination for the A107 partner question,
carried from the old ``goal.py`` (the ``literature_search`` role sentence of the old ``contracts._ROLE_INSTRUCTIONS``
followed by the A107 partner sentences) at 97308b94c."""

BINDING_PATH = ('partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                'source_relevance_assessment')
GOAL = ('Investigate which returned sources merit examination for the assigned question. Search results are '
        'source-discovery information. Examine original sources and their conditions before asserting biological '
        'evidence. A page child can investigate where and how to examine a selected source.\n'
        'Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and '
        'partner roles, normalization, nonpartner conditions, physical measurement identity, source units and '
        'uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target '
        'correspondence or annotation credit. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call (a source operation, an acquisition operation, a partner population operation '
        'or a partner grader operation), or one commission of a source-examination child for one located '
        'source')
RESULT = ('the controlled features of each partner sheet this episode and its descendants saved, with the '
          "sheet's reference, and the agreement counts over them")
