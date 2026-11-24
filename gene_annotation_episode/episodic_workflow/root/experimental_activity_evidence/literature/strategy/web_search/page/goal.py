"""What this episode is for (nano-graphrag's page): the A105 page of ONE paper that a search handed it for the claim.
Jev has assessed every table region and prose chunk of the paper against the information needs of the claim (automatic,
first); the page chooses which one leaf child reads next. The page does not read the text and does not extract. A leaf
extracts its item; the update of the subscoring sheet from what the leaves returned is automatic (``task.py``)."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page'
GOAL = ("Choose, from Jev's assessment of the paper's table regions and prose chunks against the information needs of "
        'the claim, which one candidate a leaf child reads next: one table region, one prose chunk, or the remaining '
        'prose in order. Whether the paper reports an experiment is what the leaves find out; the page does not read '
        "or extract. A candidate handed to a leaf is done. The commissioned task's own yield settings guide continuation.")
UNIT = ('one automatic step on the assigned paper (Jev\'s assessment of its candidates; the update of the subscoring '
        'sheet from the leaf records returned), or one model-selected leaf child on one candidate of the paper')
RESULT = ("the typed investigation finding of the paper for the claim (the per-annotation scores and the controlled "
          "features of the subscoring rows), with the persisted sheet states and the source-lead answer the parent "
          'selects')
PLANNING_QUESTION = ('Which one unconsumed candidate of the paper should a leaf child read next, given Jev\'s '
                     'assessment against the information needs of the claim and what the leaves returned?')
