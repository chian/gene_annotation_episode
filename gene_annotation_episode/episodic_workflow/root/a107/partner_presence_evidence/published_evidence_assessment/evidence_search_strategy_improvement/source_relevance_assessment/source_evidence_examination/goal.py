"""What this episode is for: the examination of one exact source for the A107 partner question, carried from the old
``goal.py`` (the ``literature_page`` role sentence of the old ``contracts._ROLE_INSTRUCTIONS`` followed by the A107
partner sentences) at 97308b94c."""

BINDING_PATH = ('partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                'source_relevance_assessment/source_evidence_examination')
GOAL = ('Investigate where and how this exact source should be examined. Choose ordinary source operations or '
        'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit '
        'some XML headings, tables and footnotes; retained original bytes remain addressable.\n'
        'Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and '
        'partner roles, normalization, nonpartner conditions, physical measurement identity, source units and '
        'uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target '
        'correspondence or annotation credit. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call on the assigned source (a source read or locate, or a partner grader '
        'operation), or one commission of a table, ordered-reading or targeted-passage investigation of it')
RESULT = ('the controlled features of each partner sheet this episode and its children saved from the assigned '
          "source, with the sheet's reference, and the agreement counts over them")
