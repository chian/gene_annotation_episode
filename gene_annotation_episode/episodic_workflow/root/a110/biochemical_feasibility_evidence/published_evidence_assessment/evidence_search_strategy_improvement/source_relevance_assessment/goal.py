"""What this episode is for: the A110 assessment of which returned sources merit examination, carried from the old
``goal.py`` (``instructions``: the ``literature_search`` role instruction of ``contracts.py`` and the A110 reaction
and resource paragraph) and the old ``episode.py`` at 97308b94c."""

BINDING_PATH = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
GOAL = ('Investigate which returned sources merit examination for the assigned question. Search results are '
        'source-discovery information. Examine original sources and their conditions before asserting biological '
        'evidence. A page child can investigate where and how to examine a selected source.\n'
        'Investigate the reported reaction and resource evidence for this source. Preserve source identity, exact '
        'conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named '
        'predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness '
        'remain unresolved. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call (a source access or acquisition tool, or a reaction grader) or '
        'one commission of the examination of one selected source')
RESULT = ('the controlled features of the reaction sheets and of the typed findings held by the episode and the '
          'investigations it commissioned, with the credit the retained findings earned')
