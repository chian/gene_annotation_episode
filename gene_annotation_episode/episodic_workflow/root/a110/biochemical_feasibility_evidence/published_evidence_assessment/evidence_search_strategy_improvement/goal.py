"""What this episode is for: the A110 improvement of the search strategy for applicable published evidence, carried
from the old ``goal.py`` (``instructions``: the ``literature_strategy`` role instruction of ``contracts.py`` and the
A110 reaction and resource paragraph) and the old ``episode.py`` at 97308b94c."""

BINDING_PATH = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
GOAL = ('Investigate which search approach is productive. Keep the information objective and evidence context '
        'separate from a literal provider query. Revise terms or source choices in light of actual search/read '
        'outcomes; a search child can investigate which returned sources deserve examination.\n'
        'Investigate the reported reaction and resource evidence for this source. Preserve source identity, exact '
        'conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named '
        'predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness '
        'remain unresolved. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call (a source access or acquisition tool, or a reaction grader) or '
        'one commission of the assessment of which returned sources merit examination')
RESULT = ('the controlled features of the reaction sheets and of the typed findings held by the episode and the '
          'investigations it commissioned, with the credit the retained findings earned')
