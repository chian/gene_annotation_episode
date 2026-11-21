"""What this episode is for (nano-graphrag's page): the A106 page of ONE paper that a search handed it for the claim.
Jev has assessed every table region and prose chunk of the paper against the information needs of the claim (automatic,
first); the page chooses which one leaf child reads next. The page does not read the text, does not extract and commits
no reasoning. A leaf extracts its item and grades it on its own sheets; a candidate handed to a leaf is done."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
GOAL = ("Choose, from Jev's assessment of the paper's table regions and prose chunks against the information needs of "
        'the claim, which one candidate a leaf child reads next: one table region, one prose chunk, or the remaining '
        'prose in order. Whether the paper reports an intervention experiment is what the leaves find out; the page '
        'does not read or extract. A candidate handed to a leaf is done. The commissioned task\'s own yield settings '
        'guide continuation.')
UNIT = ('one automatic step on the assigned paper (Jev\'s assessment of its candidates), or one model-selected leaf '
        'child on one candidate of the paper')
RESULT = ('the typed investigation findings of the paper for the claim (the controlled features of the intervention '
          'grading sheets and the A106 final subscores its leaves saved) and the source-lead answer the parent selects')
PLANNING_QUESTION = ('Which one unconsumed candidate of the paper should a leaf child read next, given Jev\'s '
                     'assessment against the information needs of the claim and what the leaves returned?')
