"""What this episode is for: the extraction of one kind of experiment's grader inputs from a source read in document order,
window after window."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page/report'
GOAL = ('Fill the input form of the grader of one kind of experiment from each window of a source read in document order. '
        'Extract exactly what the grader needs and nothing else; a field a window does not state stays unavailable.')
UNIT = 'one extraction of the next window'
RESULT = ('the held extraction record of each window, and the share of the asked fields newly stated')
