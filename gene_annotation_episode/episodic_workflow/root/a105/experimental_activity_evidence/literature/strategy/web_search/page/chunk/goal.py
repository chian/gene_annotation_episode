"""What this episode is for: naming the method one chunk of a source reports and the extraction of that method's grader inputs
from the chunk."""

BINDING_PATH = 'experimental_activity_evidence/literature/strategy/web_search/page/chunk'
GOAL = ('Name which experimental method of the claim\'s sheet class one chunk of a source reports, or none, and fill the '
        'input form of the grader of that method from the chunk. Extract exactly what the grader needs and nothing else; a '
        'field the chunk does not state stays unavailable.')
UNIT = 'one extraction of the chunk: the method named, and the form of that method filled'
RESULT = ('the held extraction record of the method named (none when the chunk reports no listed method), and the share of '
          'the asked fields newly stated')
