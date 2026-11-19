"""What this episode is for: the ordered reading of one source for the A107 partner question, carried from the old
``goal.py`` (the ``literature_ordered`` role sentence of the old ``contracts._ROLE_INSTRUCTIONS`` followed by the A107
partner sentences) at 97308b94c."""

BINDING_PATH = ('partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                'source_relevance_assessment/source_evidence_examination/source_coverage_improvement')
GOAL = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte '
        'continuations and retain representation identity. Decide whether to continue, reread, change the examined '
        'window or interpret obtained evidence from actual outcomes.\n'
        'Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and '
        'partner roles, normalization, nonpartner conditions, physical measurement identity, source units and '
        'uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target '
        'correspondence or annotation credit. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call on the assigned source (a source read or locate, or a partner grader '
        'operation)')
RESULT = ('the controlled features of each current partner sheet saved from the source read in order, with the '
          "sheet's reference, and the agreement counts over them")
