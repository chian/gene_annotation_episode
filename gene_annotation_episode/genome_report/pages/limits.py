"""Section 05: what the run could not settle. Searches that found nothing, tools never tried and tools that failed are
kept apart, then the calls to check first and how each part of the run ended."""
from __future__ import annotations

from .. import layout

SECTION, TITLE = '05', 'What the run could not settle'
LEDE = ('What was searched without result, what was never tried, and what failed. The three are kept apart: only the '
        'first says anything about the genome.')
ENDED = {'yield_stop': 'stopped when further work was judged not worth its cost'}
ROW = 15
SIZE = 7.5


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

    def heading(self, heading, sentence):
        lines = layout.wrap(sentence, layout.SANS, 8.5, layout.WIDTH)
        self.ensure(20 + 12 * len(lines) + 14 + 20 + 2 * ROW)
        self.y -= 4
        layout.text(self.sheet, layout.LEFT, self.y, heading, layout.SERIF_BOLD, 12, room=layout.WIDTH)
        self.y = layout.paragraph(self.sheet, layout.LEFT, self.y - 15, sentence, layout.WIDTH, layout.SANS, 8.5,
                                  layout.MUTED, 12) - 2

    def part(self, subheading, columns, rows):
        if subheading:
            self.ensure(14 + 20 + 2 * ROW)
            layout.text(self.sheet, layout.LEFT, self.y, subheading, layout.SANS_BOLD, 8.5)
            self.y -= 12
        if not rows:
            self.ensure(16)
            layout.text(self.sheet, layout.LEFT, self.y, 'None.', layout.SANS, 8.5)
            self.y -= 16
            return
        index = 0
        while True:
            self.ensure(20 + 2 * ROW)
            self.y, index = layout.table(self.sheet, self.y, columns, rows, index, size=SIZE)
            if index == len(rows):
                break
            self.new_page()
        self.y -= 14

    def finish(self):
        layout.end_page(self.sheet)


def _lines(value, font, size, room):
    lines = []
    for line in layout.wrap(value, font, size, room) or ['']:
        while layout.width(line, font, size) > room:
            cut = len(line)
            while cut > 1 and layout.width(line[:cut], font, size) > room:
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
        lines.append(line)
    return lines


def _wrapped(columns, cells):
    columns_lines = [_lines(cell, column[3], SIZE, column[1] - 6) for cell, column in zip(cells, columns)]
    height = max(len(lines) for lines in columns_lines)
    return [[lines[i] if i < len(lines) else '' for lines in columns_lines] for i in range(height)]


def _wrapped_rows(columns, entries):
    return [row for cells in entries for row in _wrapped(columns, cells)]


def _searched(data):
    columns = (('searched', 130, 'left', layout.SANS), ('search', 214, 'left', layout.SANS),
               ('part of the run', 160, 'left', layout.MONO))
    rows = [['the whole sequence' if search['operand'] == 'sequence' else search['operand'],
             layout.tool_name(search), search['episode']]
            for search in data['searches'] if search['observation_count'] == 0]
    return columns, rows


def _unmatched(data):
    columns = (('id', 50, 'left', layout.MONO), ('type', 150, 'left', layout.SANS),
               ('positions', 304, 'left', layout.MONO))
    rows = [[feature['id'], feature['kind'], layout.location(feature)] for feature in data['features']
            if feature['hit_count'] == 0 and not feature['profile_matches']]
    return columns, rows


def _not_tried(data):
    columns = (('part of the run', 190, 'left', layout.MONO), ('tools', 314, 'left', layout.MONO))
    return columns, _wrapped_rows(columns, [[row['episode'], ', '.join(row['tools'])] for row in data['not_tried']])


def _failures(data):
    columns = (('part of the run', 190, 'left', layout.MONO), ('tool', 120, 'left', layout.MONO),
               ('status', 80, 'left', layout.SANS), ('failure code', 114, 'left', layout.MONO))
    return columns, _wrapped_rows(columns, [[row['episode'], row['tool'], row['status'], row['failure_code']]
                                            for row in data['failures']])


def _contested(data):
    columns = (('id', 36, 'left', layout.MONO), ('positions', 100, 'left', layout.MONO),
               ('call', 120, 'left', layout.SANS), ('alternates', 248, 'left', layout.SANS))
    entries = [[feature['id'], layout.location(feature), feature['call']['name'],
                ', '.join(alternate['name'] for alternate in feature['alternates'])]
               for feature in data['features'] if feature['chosen'] and feature['standing'] == 'contested']
    return columns, _wrapped_rows(columns, entries)


def _no_annotation(data):
    columns = (('id', 50, 'left', layout.MONO), ('type', 150, 'left', layout.SANS),
               ('positions', 304, 'left', layout.MONO))
    rows = [[feature['id'], feature['kind'], layout.location(feature)] for feature in data['features']
            if feature['chosen'] and feature['standing'] == 'no_annotation']
    return columns, rows


def _endings(data):
    groups = {}
    for episode in data['episodes']:
        group = groups.setdefault(episode['binding_path'], {'ran': 0, 'units': 0, 'ended': []})
        group['ran'] += 1
        group['units'] += episode['units']
        if episode['ended_by'] not in group['ended']:
            group['ended'].append(episode['ended_by'])
    columns = (('part of the run', 192, 'left', layout.MONO), ('how it ended', 216, 'left', layout.SANS),
               ('times run', 50, 'right', layout.MONO), ('steps', 46, 'right', layout.MONO))
    entries = [[path, '; '.join(ENDED.get(ended, ended) for ended in group['ended']),
                layout.count(group['ran']), layout.count(group['units'])] for path, group in groups.items()]
    rows = []
    for entry in entries:
        lines = _wrapped(columns, entry)
        for line in lines[1:]:
            line[2] = line[3] = ''
        rows.extend(lines)
    return columns, rows


def draw(sheet, data):
    flow = _Flow(sheet, data)
    flow.heading('Looked and found nothing', 'The search ran and returned no match: this is evidence of absence in '
                 'that database.')
    flow.part('Searches with no match', *_searched(data))
    flow.part('Features with no match at all', *_unmatched(data))
    flow.heading('Did not look', 'The tool was available to that part of the run and was never used before the run '
                 'stopped: nothing is known either way.')
    flow.part(None, *_not_tried(data))
    flow.heading('Tried and failed', 'The tool or service did not complete: this says nothing about the genome.')
    flow.part(None, *_failures(data))
    flow.heading('Calls a reader should check first', 'These calls are the ones a reader is least able to take as '
                 'given.')
    flow.part('Contested: an alternate comes close to the call', *_contested(data))
    flow.part('No annotation: the feature was located but nothing could be said about what it is',
              *_no_annotation(data))
    flow.heading('How each part of the run ended', 'Each part of the run stops on its own estimate of what further '
                 'work would yield.')
    flow.part(None, *_endings(data))
    flow.finish()
