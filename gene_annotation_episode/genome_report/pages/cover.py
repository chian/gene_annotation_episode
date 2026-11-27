"""The first page: what was called on the sequence and where it was placed, the numbers of the run, the calls at a
glance, and how to read the report."""
from __future__ import annotations

from .. import layout

GLANCE_SHOWN = 12
SECTIONS = ('01 Genome map, 02 Organism, 03 Feature table, 04 Features (one or two pages each), '
            '05 What the run could not settle, 06 Provenance.')


def _organism_name(data):
    leader = data['organism']['leader_taxon_id']
    return next(row['name'] for row in data['organism']['candidates'] if row['taxon_id'] == leader)


def _headline(data, chosen):
    sequences = data['sequences']
    letters = sum(sequence['length'] for sequence in sequences)
    placed = 'organism not placed' if data['organism']['leader_taxon_id'] is None \
        else 'placed in ' + _organism_name(data)
    if len(sequences) == 1:
        return '%d features on a %s-letter sequence, %s' % (len(chosen), layout.count(letters), placed)
    return '%d features on %d sequences (%s letters), %s' % (len(chosen), len(sequences), layout.count(letters), placed)


def _standing_count(chosen, standing):
    return sum(feature['standing'] == standing for feature in chosen)


def _lede(chosen):
    return '%d calls are well supported, %d are contested and %d have no annotation.' % (
        _standing_count(chosen, 'supported'), _standing_count(chosen, 'contested'),
        _standing_count(chosen, 'no_annotation'))


def _tiles(data, chosen):
    sequences = data['sequences']
    letters = sum(sequence['length'] for sequence in sequences)
    gc = sum(sequence['gc_fraction'] * sequence['length'] for sequence in sequences) / letters
    lost = len(data['features']) - len(chosen)
    items = [(layout.count(letters), 'letters'), (layout.percent(gc, 1), 'GC content')]
    if len(sequences) > 1:
        items.append((layout.count(len(sequences)), 'sequences'))
    items += [(layout.count(len(chosen)), 'features called'),
              (layout.count(_standing_count(chosen, 'supported')), 'well supported'),
              (layout.count(_standing_count(chosen, 'contested')), 'contested'),
              (layout.count(_standing_count(chosen, 'no_annotation')), 'no annotation')]
    if lost:
        items.append((layout.count(lost), 'feature calls that lost to a rival'))
    items += [(layout.count(len(data['searches'])), 'searches made'),
              (layout.count(sum(search['observation_count'] == 0 for search in data['searches'])),
               'searches that found nothing')]
    return items


def _glance(sheet, y, chosen):
    layout.text(sheet, layout.LEFT, y, 'The calls at a glance', layout.SERIF_BOLD, 13)
    y -= 8
    layout.rule(sheet, layout.LEFT, y, layout.RIGHT, layout.INK, 0.6)
    for feature in chosen[:GLANCE_SHOWN]:
        y -= 14
        standing = layout.STANDING[feature['standing']]
        call = feature['call']
        layout.box(sheet, layout.LEFT + 2, y + 1.5, 7, 7, fill=standing)
        layout.text(sheet, layout.LEFT + 16, y + 2, feature['id'], layout.MONO_BOLD, 8)
        layout.text(sheet, layout.LEFT + 46, y + 2, feature['kind'], layout.SANS, 8, room=100)
        layout.text(sheet, layout.LEFT + 152, y + 2, layout.location(feature), layout.MONO, 8, room=120)
        name, color = (call['name'], layout.INK) if call else ('no annotation', standing)
        layout.text(sheet, layout.LEFT + 280, y + 2, name, layout.SANS, 8, color, room=layout.WIDTH - 280)
        layout.rule(sheet, layout.LEFT, y, layout.RIGHT)
    if len(chosen) > GLANCE_SHOWN:
        y -= 14
        layout.text(sheet, layout.LEFT, y + 2, 'and %d more: see the feature table' % (len(chosen) - GLANCE_SHOWN),
                    layout.SANS, 8, layout.MUTED)
    return y


def _legend(sheet, y):
    height = 158
    layout.box(sheet, layout.LEFT, y - height, layout.WIDTH, height, fill=layout.PANEL)
    inner = layout.WIDTH - 24
    x, y = layout.LEFT + 12, y - 20
    layout.text(sheet, x, y, 'How to read this report', layout.SERIF_BOLD, 13)
    for term, sentence in (('call', 'the annotation chosen for a feature.'),
                           ('alternate', 'another annotation considered for the same feature.'),
                           ('match', 'a database sequence or family that resembles the feature.')):
        y -= 15
        layout.text(sheet, x, y, 'A ' + term + ' is', layout.SANS_BOLD, 8.5)
        layout.text(sheet, x + layout.width('A ' + term + ' is', layout.SANS_BOLD, 8.5) + 4, y, sentence,
                    layout.SANS, 8.5, room=inner)
    meanings = {'supported': 'no alternate comes close to the call',
                'contested': 'an alternate comes close to the call',
                'no_annotation': 'the feature was located but nothing could be said about what it is'}
    y -= 4
    for standing, meaning in meanings.items():
        y -= 14
        layout.box(sheet, x, y - 0.5, 8, 8, fill=layout.STANDING[standing])
        word = layout.STANDING_WORDS[standing]
        layout.text(sheet, x + 14, y, word, layout.SANS_BOLD, 8.5)
        layout.text(sheet, x + 14 + layout.width(word, layout.SANS_BOLD, 8.5) + 6, y, meaning, layout.SANS, 8.5,
                    room=inner - 80)
    y -= 18
    layout.paragraph(sheet, x, y, 'Sections that follow: ' + SECTIONS, inner, layout.SANS, 8, layout.MUTED)


def draw(sheet, data):
    chosen = [feature for feature in data['features'] if feature['chosen']]
    y = layout.start_page(sheet, data, 'REPORT', _headline(data, chosen), _lede(chosen))
    y = layout.tiles(sheet, y, _tiles(data, chosen)) - 22
    y = _glance(sheet, y, chosen) - 24
    _legend(sheet, y)
    layout.end_page(sheet)
