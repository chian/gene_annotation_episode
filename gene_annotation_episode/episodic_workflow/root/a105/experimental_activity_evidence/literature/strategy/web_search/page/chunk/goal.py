"""What this episode is for: the extraction of one experiment's grader inputs from one chunk of a source's text."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page/chunk'
GOAL = ('Fill the input form of the grader of one kind of experiment from one chunk of a source. Extract exactly '
        'what the grader needs and nothing else; a field the chunk does not state stays unavailable.')
UNIT = 'one extraction of the chunk, with the grader run on what it extracted'
RESULT = ('the held extraction record of the experiment, and the share of the asked fields newly stated')
