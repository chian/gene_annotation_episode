"""What this episode is for: the A110 investigation of one table or sheet of a source its parent selected, carried
from the old ``goal.py`` (``instructions``: the ``literature_table`` role instruction of ``contracts.py`` and the
A110 reaction and resource paragraph) and the old ``episode.py`` (``goal``, ``unit``, ``result``) at 97308b94c."""

BINDING_PATH = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
GOAL = ('Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and '
        'footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches '
        'keep their native identity. Article XML tables are read through exact original-source windows.\n'
        'Investigate the reported reaction and resource evidence for this source. Preserve source identity, exact '
        'conditions, units, uncertainty and byte anchors. Keep reported product ratios, resource budgets and named '
        'predictions distinct. Unknown replication, calibration, alternative reactions and resource completeness '
        'remain unresolved. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call on the assigned source (an access tool, a reaction grader or a reasoning '
        'commit)')
RESULT = ('the controlled features of the reaction sheets saved from the selected table and of the typed findings '
          'committed on it, with the credit the retained findings earned')
