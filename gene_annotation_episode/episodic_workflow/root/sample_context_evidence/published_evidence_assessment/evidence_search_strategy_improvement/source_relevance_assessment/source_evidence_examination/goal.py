"""What this episode is for (nano-graphrag's page): the A108 page of ONE paper that a search handed it for the claim.
Jev has assessed every table region and prose chunk of the paper against the information needs of the claim (automatic,
first); the page chooses which one leaf child reads next. The page does not read the text and does not extract: whether
the paper holds an organism-context observation is what the leaves find out. A leaf extracts, grades and saves its
subscoring sheet; the page only passes the candidate."""

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
GOAL = ("Choose, from Jev's assessment of the paper's table regions and prose chunks against the information needs of "
        'the claim, which one candidate a leaf child reads next: one table region, one prose chunk, or the remaining '
        'prose in order. Whether the paper reports an organism-context observation is what the leaves find out; the '
        'page does not read or extract. A candidate handed to a leaf is done.')
UNIT = ("one automatic step on the assigned paper (Jev's assessment of its candidates), or one model-selected leaf "
        'child on one candidate of the paper')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets the leaves saved, with '
          'the sheet and graded assessment references, the relevant source-lead answer and the cell references the '
          'parent selects')
PLANNING_QUESTION = ("Which one unconsumed candidate of the paper should a leaf child read next, given Jev's "
                     'assessment against the information needs of the claim and what the leaves returned?')
