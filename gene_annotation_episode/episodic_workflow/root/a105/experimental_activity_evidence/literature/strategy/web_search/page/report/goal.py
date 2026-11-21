"""What this episode is for: naming the method each window of a source read in document order reports, and the extraction of that
method's grader inputs from the window."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page/report'
GOAL = ('Name which experimental method of the claim\'s sheet class each window of a source read in document order reports, '
        'or none, and fill the input form of the grader of that method from the window. Extract exactly what the grader '
        'needs and nothing else; a field a window does not state stays unavailable.')
UNIT = 'one extraction of the next window: the method named, and the form of that method filled'
RESULT = ('the held extraction record of each window that reports a listed method, and the share of the asked fields newly '
          'stated')
