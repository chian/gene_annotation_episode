"""What this episode is for: improving the search strategy for the A107 partner question, carried from the old
``goal.py`` (the ``literature_strategy`` role sentence of the old ``contracts._ROLE_INSTRUCTIONS`` followed by the
A107 partner sentences) at 97308b94c."""

BINDING_PATH = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
GOAL = ('Investigate which search approach is productive. Keep the information objective and evidence context '
        'separate from a literal provider query. Revise terms or source choices in light of actual search/read '
        'outcomes; a search child can investigate which returned sources deserve examination.\n'
        'Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and '
        'partner roles, normalization, nonpartner conditions, physical measurement identity, source units and '
        'uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target '
        'correspondence or annotation credit. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call (a source operation, an acquisition operation, a partner population operation '
        'or a partner grader operation), or one commission of a source-relevance-assessment child for the '
        'sources a search located')
RESULT = ('the controlled features of each partner sheet this episode and its descendants saved, with the '
          "sheet's reference, and the agreement counts over them")
