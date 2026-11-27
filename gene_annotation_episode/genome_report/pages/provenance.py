"""Section 06: where every figure in the report comes from: the run, its sequences, the tools, databases and versions
it used, the records it kept, and how to read the report's words and numbers."""
from __future__ import annotations

from .. import layout

SECTION, TITLE = '06', 'Provenance'
LEDE = 'Where every figure in this report comes from, and how its words and numbers are meant.'
READING = (
    'Positions are counted from 1 and the last position named is included.',
    'A feature in several ranges is written join(a..b,c..d).',
    '"Identity" is the share of aligned letters that are the same.',
    '"Coverage of the feature" is the share of the feature\'s letters a match lies on.',
    '"Coverage of the reference" is the share of the matched database sequence the match covers.',
    'An e-value is the number of matches this good expected by chance in that database.',
    'A call is "well supported" when no alternate comes close to it and "contested" when one does; it has '
    '"no annotation" when the feature was located but nothing could be said about what it is.',
    'The report is drawn by code from the run\'s records and shows no score.',
)
SEQUENCES = (('name', 120, 'left', layout.SANS), ('molecule', 70, 'left', layout.SANS),
             ('record reference', 190, 'left', layout.MONO), ('letters', 64, 'right', layout.MONO),
             ('GC content', 60, 'right', layout.MONO))
TOOLS = (('provider', 176, 'left', layout.MONO), ('database', 130, 'left', layout.SANS),
         ('version', 96, 'left', layout.SANS), ('uses', 40, 'right', layout.MONO),
         ('observations', 62, 'right', layout.MONO))
SIZE = 7.5
ROW = 15


class _Flow:
    def __init__(self, sheet, data):
        self.sheet, self.data = sheet, data
        self.y = layout.start_page(sheet, data, SECTION, TITLE, LEDE)

    def new_page(self):
        layout.end_page(self.sheet)
        self.y = layout.start_page(self.sheet, self.data, SECTION, TITLE, '(continued)')

    def ensure(self, room):
        if self.y - room < layout.BOTTOM:
            self.new_page()

    def heading(self, heading, room):
        self.ensure(16 + room)
        layout.text(self.sheet, layout.LEFT, self.y, heading, layout.SERIF_BOLD, 12, room=layout.WIDTH)
        self.y -= 16

    def table(self, heading, columns, rows):
        self.heading(heading, 20 + 2 * ROW)
        index = 0
        while True:
            self.y, index = layout.table(self.sheet, self.y, columns, rows, index, size=SIZE)
            if index == len(rows):
                break
            self.new_page()
        self.y -= 24

    def pairs(self, heading, pairs, columns=1):
        self.heading(heading, ROW * -(-len(pairs) // columns))
        room = layout.WIDTH / columns
        for start in range(0, len(pairs), columns):
            self.ensure(ROW)
            for column, (name, value) in enumerate(pairs[start:start + columns]):
                left = layout.LEFT + column * room
                layout.text(self.sheet, left, self.y, name, layout.SANS, 8.5, layout.MUTED, room=120)
                layout.text(self.sheet, left + 130, self.y, value, layout.MONO, 8.5)
            self.y -= ROW
        self.y -= 10

    def sentences(self, heading, sentences):
        self.heading(heading, 2 * ROW)
        for sentence in sentences:
            room = 12 * len(layout.wrap(sentence, layout.SANS, 8.5, layout.WIDTH))
            self.ensure(room)
            self.y = layout.paragraph(self.sheet, layout.LEFT, self.y, sentence, layout.WIDTH, layout.SANS, 8.5,
                                      leading=12) - 3

    def finish(self):
        layout.end_page(self.sheet)


def _run(data):
    run = data['run']
    return [('run', run['run_id']), ('journal', data['provenance']['journal']), ('how the run ended', run['ended_by']),
            ('parts of the run', layout.count(run['episodes'])), ('steps', layout.count(run['units']))]


def _sequences(data):
    return [[sequence['name'], sequence['molecule'], sequence['ref'], layout.count(sequence['length']),
             layout.percent(sequence['gc_fraction'], 1)] for sequence in data['sequences']]


def _tools(data):
    return [[tool['provider'], tool['database'] or '-', tool['version'] or '-', layout.count(tool['sources']),
             layout.count(tool['observations'])] for tool in data['provenance']['tools']]


def draw(sheet, data):
    flow = _Flow(sheet, data)
    flow.pairs('Run', _run(data))
    flow.table('Sequences', SEQUENCES, _sequences(data))
    flow.table('Tools, databases and versions', TOOLS, _tools(data))
    flow.pairs('Records the run kept', [(kind, layout.count(number))
                                        for kind, number in data['provenance']['record_counts'].items()], 2)
    flow.sentences('Reading this report', READING)
    flow.finish()
