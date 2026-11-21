"""What this episode is for: the extraction of one experiment's grader inputs from one byte window of a source that holds a
table."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page/table'
GOAL = ('Fill the input form of the grader of one kind of experiment from one byte window of a source that holds a table. '
        'Extract exactly what the grader needs and nothing else; a field the window does not state stays unavailable.')
UNIT = 'one extraction of the window'
RESULT = ('the held extraction record of the experiment, and the share of the asked fields newly stated')
