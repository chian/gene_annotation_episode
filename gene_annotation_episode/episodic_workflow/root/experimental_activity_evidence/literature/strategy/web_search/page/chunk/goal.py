"""What this episode is for: naming the method one chunk of a source reports and the extraction of that method's grader inputs
from the chunk."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page/chunk'
GOAL = ('Name every experimental method able to support the claim that one chunk of a source reports, or none, and fill the '
        'input form of the grader of each method named from the chunk. Extract exactly what the grader needs and nothing else; a '
        'field the chunk does not state stays unavailable.')
UNIT = 'one extraction of the chunk: the methods named, and the form of each one filled'
RESULT = ('the held extraction record of each method named (none when the chunk reports no listed method), and the share of '
          'the asked fields newly stated')
