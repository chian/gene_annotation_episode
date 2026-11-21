"""What this episode is for: which hit of one search merits examination for the assigned organism-context question. It
is nano-graphrag's web search: it receives a query (``search_query_ref``), the provider search runs automatically, Jev
scores every hit once automatically, the model picks ONE unprocessed hit, the paper is obtained when its page is built,
and a hit picked is done. It cannot read or extract and nothing in it is assessed by a reasoning commit.

Carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature_search`` at 97308b94c, with the
source reads, the reasoning commit and the other task kinds removed."""

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
ROLE_INSTRUCTION = (
    "Choose which hit of the search you were given merits examination for whether the proposed protein function fits "
    "the actual organism's biology and sample conditions (physiology, environment, availability of substrates and "
    "cofactors, localization). The provider search has run and Jev has scored every hit against the question; the "
    "scores and the hits' ranks, titles and descriptions are planning evidence, not a rule that the highest score "
    "must be chosen. Pick one unprocessed hit at a time; the paper is fetched and its page is built from it, and "
    "whether it holds an observation, and where, is what the page and its leaves find out: you do not read it and "
    "you cannot extract from it. A hit you picked is done. The configured controller alone decides when this episode "
    "stops.")
GOAL = ROLE_INSTRUCTION
UNIT = ('the provider search of the query given, Jev\'s measurement of its hits (both made by code), one '
        'model-selected hit to fetch, or one child commission (the examination of the paper that hit names, made by '
        'code after its fetch)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved (the '
          "children's), with the sheet and graded assessment references, and the verified source leads as counts "
          'and references')
