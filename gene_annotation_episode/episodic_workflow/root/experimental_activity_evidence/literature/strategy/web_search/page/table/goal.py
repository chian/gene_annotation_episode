"""What this episode is for: naming the method one table region of a source reports and the extraction of that method's grader
inputs from it."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page/table'
GOAL = ('Name every experimental method able to support the claim that one byte window of a source that holds a table reports, '
        'or none, and fill the input form of the grader of each method named from the window. Extract exactly what the grader '
        'needs and nothing else; a field the window does not state stays unavailable.')
UNIT = 'one extraction of the window: the methods named, and the form of each one filled'
RESULT = ('the held extraction record of each method named (none when the window reports no listed method), and the share of '
          'the asked fields newly stated')
