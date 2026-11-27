"""Section 03: one row per feature call, chosen or not, grouped by sequence, over as many pages as the rows need."""
from __future__ import annotations

from .. import layout

SECTION, TITLE = '03', 'Feature table'
LEDE = ('Every feature call, in position order. A call in grey lost to a rival feature call and is not part of '
        'the genome annotation.')
COLUMNS = (('id', 24, 'left', layout.MONO), ('type', 74, 'left', layout.SANS),
           ('positions and strand', 112, 'left', layout.MONO), ('letters', 34, 'right', layout.MONO),
           ('call', 80, 'left', layout.SANS), ('standing', 64, 'left', layout.SANS_BOLD),
           ('matches', 34, 'right', layout.MONO), ('identity', 36, 'right', layout.MONO),
           ('alternates', 46, 'right', layout.MONO))
MIN_ROOM = 60


def _row(feature):
    call = feature['call']
    standing = layout.STANDING_WORDS[feature['standing']]
    row = [feature['id'], feature['kind'], '%s (%s)' % (layout.location(feature), feature['strand']),
           layout.count(feature['length']), call['name'] if call else 'no annotation', standing,
           layout.count(feature['hit_count']), '-' if not call else layout.percent(call['best_identity'], 1),
           layout.count(len(feature['alternates']))]
    if feature['chosen']:
        row[5] = (standing, layout.STANDING[feature['standing']])
        return row
    row[5] = 'lost to ' + feature['lost_to'] if feature['lost_to'] else 'not chosen'
    return [(value, layout.MUTED) for value in row]


def _groups(data):
    groups = {sequence['ref']: [] for sequence in data['sequences']}
    for feature in data['features']:
        groups[feature['sequence_ref']].append(feature)
    return [(sequence, groups[sequence['ref']]) for sequence in data['sequences']]


def _new_page(sheet, data, lede):
    return layout.start_page(sheet, data, SECTION, TITLE, lede)


def draw(sheet, data):
    several = len(data['sequences']) > 1
    y = _new_page(sheet, data, LEDE)
    for sequence, features in _groups(data):
        if not features:
            continue
        rows = [_row(feature) for feature in features]
        if y - MIN_ROOM < layout.BOTTOM:
            layout.end_page(sheet)
            y = _new_page(sheet, data, '(continued)')
        if several:
            layout.text(sheet, layout.LEFT, y, '%s, %s letters' % (sequence['name'], layout.count(sequence['length'])),
                        layout.SERIF_BOLD, 11, room=layout.WIDTH)
            y -= 16
        index = 0
        while True:
            y, index = layout.table(sheet, y, COLUMNS, rows, index, size=7.5)
            if index == len(rows):
                break
            layout.end_page(sheet)
            y = _new_page(sheet, data, '(continued)')
        y -= 20
    layout.end_page(sheet)
