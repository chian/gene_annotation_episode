"""What this episode is for: the A110 ordered reading of one source its parent selected, carried from the old
``goal.py`` (``instructions``: the ``literature_ordered`` role instruction of ``contracts.py`` and the A110
reaction and resource paragraph) at 97308b94c."""

BINDING_PATH = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
GOAL = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte '
        'continuations and retain representation identity. Decide whether to continue, change the examined '
        'window or interpret obtained evidence from actual outcomes.\n'
        'Investigate the reported reaction and resource evidence for this source. Preserve source identity, exact '
        'conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named '
        'predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness '
        'remain unresolved. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call on the assigned source (an access tool, a reaction grader or a reasoning '
        'commit)')
RESULT = ('the controlled features of the reaction sheets saved from the source, read in document order window by '
          'window, and of the typed findings committed on it, with the credit the retained findings earned')
