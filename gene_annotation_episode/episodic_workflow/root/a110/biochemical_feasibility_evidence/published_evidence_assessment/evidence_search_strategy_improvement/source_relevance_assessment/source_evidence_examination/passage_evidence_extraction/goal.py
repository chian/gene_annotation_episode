"""What this episode is for: the A110 reading of the passages of one source its parent selected, carried from the old
``goal.py`` (``instructions``: the ``literature_targeted`` role instruction of ``contracts.py`` and the A110
reaction and resource paragraph) at 97308b94c."""

BINDING_PATH = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
GOAL = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
        'qualifications or alternative passages as needed and revise the interpretation from actual outcomes. '
        'Separate spans remain separate; never concatenate them into a fabricated quotation.\n'
        'Investigate the reported reaction and resource evidence for this source. Preserve source identity, exact '
        'conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named '
        'predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness '
        'remain unresolved. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call on the assigned source (an access tool, a reaction grader or a reasoning '
        'commit)')
RESULT = ('the controlled features of the reaction sheets saved from the supplied passages and of the typed '
          'findings committed on them, with the credit the retained findings earned')
