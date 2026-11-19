"""What this episode is for: the examination of one selected table or spreadsheet sheet of one source for the A107
partner-presence question. Carried from the old ``goal.py`` (the ``literature_table`` role sentence of the old
``contracts._ROLE_INSTRUCTIONS`` and the A107 partner paragraph)."""

BINDING_PATH = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
GOAL = ('Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and '
        'footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches '
        'keep their native identity. Article XML tables are read through exact original-source windows.\n'
        'Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and '
        'partner roles, normalization, nonpartner conditions, physical measurement identity, source units and '
        'uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target '
        'correspondence or annotation credit. A search or read earns no scientific credit by itself.')
UNIT = ('one model-selected tool call on the assigned source (a source read or locate, or a partner grader '
        'operation)')
RESULT = ('the controlled features of each current partner sheet saved from the selected table or sheet, with the '
          "sheet's reference, and the agreement counts over them")
