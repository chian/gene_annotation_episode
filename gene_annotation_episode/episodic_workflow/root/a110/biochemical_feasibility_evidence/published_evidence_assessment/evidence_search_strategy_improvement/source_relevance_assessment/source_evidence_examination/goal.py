"""What this episode is for: the A110 examination of one exact source, carried from the old ``goal.py``
(``instructions``: the ``literature_page`` role instruction of ``contracts.py`` and the A110 reaction and resource
paragraph) and the old ``episode.py`` at 97308b94c."""

BINDING_PATH = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
GOAL = ('Investigate where and how this exact source should be examined. Choose ordinary source operations or '
        'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit '
        'some XML headings, tables and footnotes; retained original bytes remain addressable.\n'
        'Investigate the reported reaction and resource evidence for this source. Preserve source identity, exact '
        'conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named '
        'predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness '
        'remain unresolved. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call on the assigned source (an access tool or a reaction grader) '
        'or one commission of a table, ordered-reading or targeted-passage investigation of it')
RESULT = ('the controlled features of the reaction sheets saved from the assigned source and of the typed findings '
          'held on it, by the episode and the investigations it commissioned, with the credit the retained findings '
          'earned')
