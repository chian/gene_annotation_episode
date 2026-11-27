"""Section 04: a second page per feature with the matches laid along it: where each lies on the feature, which family
models were found in its protein, how many matches cover each part of it, whether the ends of the matches agree with
the ends of the feature, how long the matched proteins are, and the best matches in a table."""
from __future__ import annotations

from statistics import median

from .. import layout

SECTION = '04'
ROWS_SHOWN, ROW = 40, 6.4
BELOW_ROWS = 345
BINS = 120
TABLE_ROWS = 10
END_SLACK, FEATURE_SLACK = 3, 9
LABEL_ROOM = 112
IDENTITY_ROOM = 30
COLUMNS = (('name', 96, 'left', layout.SANS), ('accession', 76, 'left', layout.MONO),
           ('search', 110, 'left', layout.SANS), ('identity', 32, 'right', layout.MONO),
           ('feature', 32, 'right', layout.MONO), ('reference', 40, 'right', layout.MONO),
           ('e-value', 34, 'right', layout.MONO), ('organism', 84, 'left', layout.SANS))
LEDE = 'The %s best of %s matches inside %s (%s), drawn where they lie on the feature.'
CAPTION = ('Each bar is one match placed where it lies on the feature, best first, with its percent identity at the '
           'right; the boxes above are protein family models found in the feature\'s protein; the columns below count, '
           'for each of %d equal slices of the feature, how many of the listed matches cover it.' % BINS)
MINUS_CAPTION = (' The feature is on the minus strand, so it is drawn in reading order: its last letter on the '
                 'sequence is at the left.')
NO_MATCHES_LEDE = 'No match lies inside %s (%s); the protein family models in its protein are drawn where they lie.'
MODELS_CAPTION = 'Each box is a protein family model found in the feature\'s protein, drawn where it lies.'
TABLE_CAPTION = ('Identity is over the aligned part. Feature is the share of the feature\'s letters the match lies on; '
                 'reference is the share of the match\'s own sequence it covers.')


def _reading(feature, position):
    """The place of a sequence position along the feature as read, 0 at its first letter and 1 at its last."""
    length = feature['end'] - feature['start']
    along = (position - feature['start']) / length
    return 1 - along if feature['strand'] == '-' else along


def _heading(sheet, x, y, value):
    layout.text(sheet, x, y, value, layout.SERIF_BOLD, 11.5)
    return y - 14


def _caption(sheet, x, y, value, room):
    return layout.paragraph(sheet, x, y, value, room, layout.SANS, 7, layout.MUTED, 8.5)


# -- the coverage picture ----------------------------------------------------------------------------------------------

def _plot():
    left = layout.LEFT + LABEL_ROOM + 6
    return left, layout.RIGHT - IDENTITY_ROOM - 4


def _bar(sheet, feature, x0, x1, start, end, y, height, color):
    """A bar for the sequence positions ``start`` to ``end``, clipped to the feature."""
    first, last = max(start, feature['start']), min(end, feature['end'])
    a, b = sorted((_reading(feature, first), _reading(feature, last)))
    layout.box(sheet, x0 + a * (x1 - x0), y, max(b - a, 0) * (x1 - x0) + 0.6, height, fill=color)


def _feature_bar(sheet, feature, x0, x1, y):
    layout.text(sheet, layout.LEFT, y + 2, feature['id'] + ' ' + feature['kind'], layout.SANS_BOLD, 7.5,
                room=LABEL_ROOM)
    color = layout.feature_color(feature)
    for first, last in zip(feature['segments'], feature['segments'][1:]):
        _bar(sheet, feature, x0, x1, first['end'], last['start'], y + 4, 0.8, layout.MUTED)
    for segment in feature['segments']:
        _bar(sheet, feature, x0, x1, segment['start'], segment['end'], y, 8, color)


def _lanes(feature, x0, x1):
    """The profile matches with the lane each is drawn in and whether its name fits inside its box."""
    ends, placed = [], []
    for match in feature['profile_matches']:
        a, b = sorted((_reading(feature, match['start']), _reading(feature, match['end'])))
        left, right = x0 + a * (x1 - x0), x0 + b * (x1 - x0)
        inside = layout.width(match['name'], layout.SANS, 6.5) + 4 <= right - left
        reach = right if inside else right + layout.width(match['name'], layout.SANS, 6.5) + 6
        lane = next((index for index, end in enumerate(ends) if end + 2 <= left), len(ends))
        if lane == len(ends):
            ends.append(reach)
        else:
            ends[lane] = reach
        placed.append((match, left, right, lane, inside))
    return placed, len(ends)


def _profile_track(sheet, feature, x0, x1, y):
    placed, lanes = _lanes(feature, x0, x1)
    layout.text(sheet, layout.LEFT, y - 7, 'protein family models', layout.SANS, 6.5, layout.MUTED, room=LABEL_ROOM)
    for match, left, right, lane, inside in placed:
        top = y - lane * 11
        layout.box(sheet, left, top - 9, max(right - left, 1), 9, fill=layout.PANEL, stroke=layout.MUTED, weight=0.5)
        if inside:
            layout.text(sheet, (left + right) / 2, top - 6.6, match['name'], layout.SANS, 6.5, layout.INK, 'center')
        else:
            layout.text(sheet, right + 3, top - 6.6, match['name'], layout.SANS, 6.5, layout.INK,
                        room=layout.RIGHT - right - 3)
    return y - 11 * lanes - 4


def _match_rows(sheet, feature, hits, x0, x1, y):
    shown = max(5, min(ROWS_SHOWN, int((y - layout.BOTTOM - BELOW_ROWS) / ROW)))
    for hit in hits[:shown]:
        layout.text(sheet, layout.LEFT, y - 4.9, hit['label'], layout.SANS, 5.6, layout.INK, room=LABEL_ROOM)
        layout.rule(sheet, x0, y - ROW / 2, x1, layout.PANEL, 0.4)
        _bar(sheet, feature, x0, x1, hit['start'], hit['end'], y - ROW + 1, ROW - 2, layout.LINE[hit['line']])
        layout.text(sheet, layout.RIGHT, y - 4.9, layout.percent(hit['identity']), layout.MONO, 5.6, layout.MUTED,
                    'right')
        y -= ROW
    return y


def _depth(feature, hits):
    depth = [0] * BINS
    for hit in hits:
        first, last = max(hit['start'], feature['start']), min(hit['end'], feature['end'])
        a, b = sorted((_reading(feature, first), _reading(feature, last)))
        for index in range(int(a * BINS), min(BINS, int(b * BINS - 1e-9) + 1)):
            depth[index] += 1
    return depth


def _depth_strip(sheet, feature, hits, x0, x1, y):
    height = 26
    depth = _depth(feature, hits)
    peak = max(depth)
    layout.text(sheet, layout.LEFT, y - 8, 'matches covering each slice', layout.SANS, 6.5, layout.MUTED,
                room=LABEL_ROOM)
    layout.text(sheet, layout.LEFT, y - 17, 'most: %d of %d' % (peak, len(hits)), layout.MONO, 6.5, layout.MUTED)
    step = (x1 - x0) / BINS
    layout.rule(sheet, x0, y - height, x1, layout.MUTED, 0.5)
    for index, value in enumerate(depth):
        layout.box(sheet, x0 + index * step, y - height, step + 0.2, height * value / peak, fill=layout.MUTED)
    return y - height


def _axis(sheet, feature, x0, x1, y):
    first, last = (feature['end'], feature['start'] + 1) if feature['strand'] == '-' else (feature['start'] + 1,
                                                                                         feature['end'])
    for index, fraction in enumerate((0, 0.25, 0.5, 0.75, 1)):
        x = x0 + fraction * (x1 - x0)
        position = round(first + fraction * (last - first))
        layout.rule(sheet, x, y, x, layout.MUTED, 0.5)
        sheet.line(x, y, x, y - 3)
        layout.text(sheet, x, y - 10, layout.count(position), layout.MONO, 6.5, layout.MUTED,
                    ('left', 'center', 'center', 'center', 'right')[index])
    return y - 18


def _legend(sheet, feature, hits, y):
    x = layout.LEFT
    entries = [(layout.PANEL, 'protein family model')] if feature['profile_matches'] else []
    if hits:
        entries = [(layout.LINE['call'], 'on the line of the call'),
                   (layout.LINE['alternate'], 'on the line of an alternate'),
                   (layout.LINE['other'], 'on neither')] + entries
    for color, meaning in entries:
        x = layout.swatch(sheet, x, y, color, meaning, 7)
    return y - 12


def _picture(sheet, feature, hits, y):
    x0, x1 = _plot()
    layout.rule(sheet, layout.LEFT, y + 4, layout.RIGHT)
    _feature_bar(sheet, feature, x0, x1, y - 8)
    y -= 16
    if feature['profile_matches']:
        y = _profile_track(sheet, feature, x0, x1, y)
    y -= 2
    if hits:
        y = _match_rows(sheet, feature, hits, x0, x1, y)
        y = _depth_strip(sheet, feature, hits, x0, x1, y - 6)
    y = _axis(sheet, feature, x0, x1, y)
    y = _legend(sheet, feature, hits, y - 2)
    caption = (CAPTION if hits else MODELS_CAPTION) + (MINUS_CAPTION if feature['strand'] == '-' else '')
    return _caption(sheet, layout.LEFT, y - 2, caption, layout.WIDTH)


# -- the ends ----------------------------------------------------------------------------------------------------------

def _ends(feature, hits):
    """How many matches reach the first and the last letter of their own sequence, and how many of those also begin
    and end at the feature's first and last letter. Gives ``(a, b, c, d)``."""
    first = feature['end'] if feature['strand'] == '-' else feature['start']
    last = feature['start'] if feature['strand'] == '-' else feature['end']
    begins, ends = [], []
    for hit in hits:
        if None in (hit['reference_start'], hit['reference_end'], hit['reference_length']):
            continue
        near = (hit['end'], hit['start']) if feature['strand'] == '-' else (hit['start'], hit['end'])
        if hit['reference_start'] <= END_SLACK:
            begins.append(abs(near[0] - first) <= FEATURE_SLACK)
        if hit['reference_length'] - hit['reference_end'] <= END_SLACK:
            ends.append(abs(near[1] - last) <= FEATURE_SLACK)
    return len(begins), sum(begins), len(ends), sum(ends)


def _agreement_bar(sheet, x, y, room, total, agree):
    layout.box(sheet, x, y, room, 7, fill=layout.RULE)
    if total:
        layout.box(sheet, x, y, room * agree / total, 7, fill=layout.LINE['call'])
        layout.text(sheet, x + room + 6, y + 0.5, '%d agree, %d do not' % (agree, total - agree), layout.SANS, 7,
                    layout.MUTED)


def _ends_panel(sheet, feature, hits, x, y, room):
    y = _heading(sheet, x, y, 'Do the ends agree with the relatives?')
    if not any(None not in (hit['reference_start'], hit['reference_end'], hit['reference_length']) for hit in hits):
        return layout.paragraph(sheet, x, y, 'The matches carry no positions on their own sequences.', room,
                                layout.SANS, 8.5)
    a, b, c, d = _ends(feature, hits)
    bar = room - 100
    for sentence, total, agree in (('Of %d matches that reach the first letter of their own sequence, %d begin at '
                                    'this feature\'s first letter.' % (a, b), a, b),
                                   ('Of %d matches that reach the last letter of their own sequence, %d end at '
                                    'this feature\'s last letter.' % (c, d), c, d)):
        y = layout.paragraph(sheet, x, y, sentence, room, layout.SANS, 8.5, leading=11)
        _agreement_bar(sheet, x, y - 2, bar, total, agree)
        y -= 18
    return y


# -- the lengths -------------------------------------------------------------------------------------------------------

def _length_panel(sheet, feature, lengths, x, y, room):
    y = _heading(sheet, x, y, 'Length against the relatives')
    own = feature['protein']['length']
    sentence = 'This feature\'s protein has %s residues; its %d protein matches have %s to %s (median %s).' % (
        layout.count(own), len(lengths), layout.count(min(lengths)), layout.count(max(lengths)),
        layout.count(round(median(lengths))))
    y = layout.paragraph(sheet, x, y, sentence, room, layout.SANS, 8.5, leading=11)
    low, high = min(lengths + [own]), max(lengths + [own])
    pad = max((high - low) * 0.06, 1)
    low, high = low - pad, high + pad
    left, right = x + 4, x + room - 8
    base = y - 40
    stacks = {}
    for length in sorted(lengths):
        column = round((left + (length - low) / (high - low) * (right - left)) / 3)
        stacks[column] = stacks.get(column, 0) + 1
        sheet.setFillColor(layout.MUTED)
        sheet.circle(column * 3, base + 2.5 + (stacks[column] - 1) * 3 % 30, 1.3, stroke=0, fill=1)
    mark = left + (own - low) / (high - low) * (right - left)
    layout.rule(sheet, mark, base - 1, mark, layout.feature_color(feature), 1.2)
    layout.text(sheet, mark, base + 36, 'this feature: %s' % layout.count(own), layout.SANS_BOLD, 6.5,
                layout.feature_color(feature), 'center' if left + 40 < mark < right - 40 else
                'left' if mark <= left + 40 else 'right')
    layout.rule(sheet, left, base, right, layout.MUTED, 0.5)
    for fraction in (0, 0.5, 1):
        tick = round(low + fraction * (high - low))
        layout.text(sheet, left + fraction * (right - left), base - 9, layout.count(tick), layout.MONO, 6.5,
                    layout.MUTED, ('left', 'center', 'right')[int(fraction * 2)])
    layout.text(sheet, left, base - 18, 'residues, one dot per match', layout.SANS, 6.5, layout.MUTED)
    return base - 22


# -- the table ---------------------------------------------------------------------------------------------------------

def _organism(hit):
    if hit['taxon_name']:
        return hit['taxon_name']
    return '-' if hit['taxon_id'] is None else 'taxon %d' % hit['taxon_id']


def _table_row(hit):
    return [hit['label'], hit['accession'], hit['tool'] + ' ' + hit['database'],
            layout.percent(hit['identity'], 1), layout.percent(hit['feature_coverage']),
            layout.percent(hit['target_coverage']), layout.evalue(hit['evalue']), _organism(hit)]


def _table(sheet, hits, y):
    y = _heading(sheet, layout.LEFT, y, 'The best matches')
    rows = [_table_row(hit) for hit in hits[:TABLE_ROWS]]
    y, _ = layout.table(sheet, y, COLUMNS, rows, row_height=12, size=7)
    return _caption(sheet, layout.LEFT, y - 8, TABLE_CAPTION, layout.WIDTH)


# -- the page ----------------------------------------------------------------------------------------------------------

def _below(sheet, feature, hits, y):
    lengths = [hit['reference_length'] for hit in hits
               if hit['reference_type'] == 'protein' and hit['reference_length'] is not None]
    if feature['protein'] and lengths:
        half = layout.WIDTH / 2 - 12
        y = min(_ends_panel(sheet, feature, hits, layout.LEFT, y, half),
                _length_panel(sheet, feature, lengths, layout.LEFT + half + 24, y, half))
    else:
        y = _ends_panel(sheet, feature, hits, layout.LEFT, y, layout.WIDTH)
    _table(sheet, hits, y - 10)


def draw_feature(sheet, data, feature):
    hits = feature['hits']
    if not hits and not feature['profile_matches']:
        return
    lede = (LEDE % (len(hits), layout.count(feature['hit_count']), feature['id'], layout.location(feature)) if hits
            else NO_MATCHES_LEDE % (feature['id'], layout.location(feature)))
    y = layout.start_page(sheet, data, '04 · ' + feature['id'], 'Matches along ' + feature['id'], lede)
    y = _picture(sheet, feature, hits, _heading(sheet, layout.LEFT, y, 'Where the matches lie') - 2) - 8
    if hits:
        _below(sheet, feature, hits, y)
    layout.end_page(sheet)


def draw(sheet, data):
    for feature in data['features']:
        draw_feature(sheet, data, feature)
