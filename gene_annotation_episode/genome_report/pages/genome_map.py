"""Section 01, the genome map: every feature call drawn to scale on its sequence. Forward-strand features lie above
the axis, reverse-strand features below it; colour marks the reading frame, the outline how the call stands. The
sequence is drawn as a linear map, in equal rows when it is long, over as many pages as that needs."""
from __future__ import annotations

from math import ceil, floor, log10

from reportlab.lib.colors import Color

from .. import layout

SECTION, TITLE = '01', 'Genome map'
LEDE = 'Where each feature lies on the sequence. Colour marks the reading frame; the outline marks how the call stands.'

BAR, PITCH, TICK_BAND, ROW_GAP = 10.0, 13.0, 14.0, 10.0
AXIS_LEFT, AXIS_RIGHT = layout.LEFT + 10, layout.RIGHT - 10
SINGLE_ROW_LETTERS, ROWS_PER_PAGE, MOST_PAGES, PAGE_BODY = 12000, 8, 6, 540.0
MOST_TICKS = 10
ARROW = 4.0


# -- the rows of a sequence --------------------------------------------------------------------------------------------

def _round_up(value, step):
    return int(ceil(value / step) * step)


def _nice_step(value):
    """The smallest 1, 2 or 5 times a power of ten that is at least ``value``."""
    power = 10 ** floor(log10(value))
    return next(power * factor for factor in (1, 2, 5, 10) if power * factor >= value)


def _row_length(length):
    if length <= SINGLE_ROW_LETTERS:
        return length
    per_row = ceil(length / min(ceil(length / SINGLE_ROW_LETTERS), ROWS_PER_PAGE * MOST_PAGES))
    return _round_up(per_row, _nice_step(per_row / 20))


def _longer(row_length):
    return _round_up(row_length * 1.1, _nice_step(row_length * 1.1 / 20))


def _tick_step(row_length):
    return _nice_step(row_length / MOST_TICKS)


# -- the lanes of a row ------------------------------------------------------------------------------------------------

def _depths(features):
    by_id = {feature['id']: feature for feature in features}

    def depth(feature):
        return 0 if feature['parent'] is None else 1 + depth(by_id[feature['parent']])
    return {feature['id']: depth(feature) for feature in features}


def _visible(feature, r0, r1):
    """The segments of ``feature`` inside the row, cut at its ends."""
    cut = ((max(segment['start'], r0), min(segment['end'], r1), segment) for segment in feature['segments'])
    return [(start, end, segment) for start, end, segment in cut if start < end]


def _lane_group(items, scale, r0, depths):
    """Lanes by greedy first fit: a feature lies in a lane further out than its parent's."""
    lane_of, ends = {}, []
    for feature, visible in sorted(items, key=lambda item: (depths[item[0]['id']], item[0]['start'], -item[0]['end'],
                                                            int(item[0]['id'][1:]))):
        left = AXIS_LEFT + (visible[0][0] - r0) * scale
        right = max(AXIS_LEFT + (visible[-1][1] - r0) * scale, left + 0.8)
        lane = lane_of[feature['parent']] + 1 if feature['parent'] in lane_of else 0
        while lane < len(ends) and ends[lane] + 1.5 > left:
            lane += 1
        if lane == len(ends):
            ends.append(0.0)
        ends[lane] = right
        lane_of[feature['id']] = lane
    return lane_of, len(ends)


def _plan_row(features, r0, r1, row_length, depths):
    """The row's features in lanes: per feature its visible segments and its lane on its side of the axis."""
    scale = (AXIS_RIGHT - AXIS_LEFT) / row_length
    inside = [(feature, _visible(feature, r0, r1)) for feature in features]
    inside = [(feature, visible) for feature, visible in inside if visible]
    groups = {strand: _lane_group([item for item in inside if item[0]['strand'] == strand], scale, r0, depths)
              for strand in ('+', '-', '.')}
    shift = max(groups['.'][1] - 1, 0)
    placed = []
    for feature, visible in inside:
        strand = feature['strand']
        lane = groups[strand][0][feature['id']]
        placed.append((feature, visible, strand, lane + shift if strand == '+' else lane))
    above = groups['+'][1] + shift
    return {'start': r0, 'end': r1, 'scale': scale, 'placed': placed, 'above': above, 'below': groups['-'][1]}


def _above_height(plan):
    return max(3 + plan['above'] * PITCH, BAR / 2 + 3)


def _row_height(plan):
    return _above_height(plan) + TICK_BAND + plan['below'] * PITCH + ROW_GAP


def _pages(plans):
    pages, left = 1, PAGE_BODY
    for plan in plans:
        if left < _row_height(plan):
            pages, left = pages + 1, PAGE_BODY
        left -= _row_height(plan)
    return pages


def _plan_rows(features, length, depths):
    """The row length and the planned rows of a sequence; rows are made longer until the map fits its pages."""
    row_length = _row_length(length)
    while True:
        plans = [_plan_row(features, start, min(start + row_length, length), row_length, depths)
                 for start in range(0, length, row_length)]
        if _pages(plans) <= MOST_PAGES:
            return row_length, plans
        row_length = _longer(row_length)


# -- drawing a row -----------------------------------------------------------------------------------------------------

def _lighter(color):
    return Color(*(channel + (1 - channel) * 0.65 for channel in (color.red, color.green, color.blue)))


def _standing(feature):
    return 'lost' if not feature['chosen'] else feature['standing']


def _outline(sheet, path, color, style):
    """Fill and outline of one segment as its standing says."""
    fill = {'lost': None, 'no_annotation': _lighter(color)}.get(style, color)
    stroke, weight = (layout.STANDING['contested'], 1.5) if style == 'contested' else (color, 0.8)
    if fill is not None:
        sheet.setFillColor(fill)
    sheet.setStrokeColor(stroke)
    sheet.setLineWidth(weight)
    if style == 'lost':
        sheet.setDash(2, 1.5)
    sheet.drawPath(path, stroke=1, fill=int(fill is not None))
    sheet.setDash()


def _segment_path(sheet, left, right, bottom, point):
    """A bar from ``left`` to ``right``; ``point`` ('left' or 'right') makes that end an arrowhead."""
    arrow = min(ARROW, right - left)
    middle = bottom + BAR / 2
    top = bottom + BAR
    path = sheet.beginPath()
    path.moveTo(left, bottom)
    if point == 'right':
        path.lineTo(right - arrow, bottom)
        path.lineTo(right, middle)
        path.lineTo(right - arrow, top)
        path.lineTo(left, top)
    elif point == 'left':
        path.lineTo(right, bottom)
        path.lineTo(right, top)
        path.lineTo(left + arrow, top)
        path.lineTo(left, middle)
    else:
        path.lineTo(right, bottom)
        path.lineTo(right, top)
        path.lineTo(left, top)
    path.close()
    return path


def _continues_mark(sheet, x, bottom):
    sheet.setStrokeColor(layout.INK)
    sheet.setLineWidth(0.9)
    path = sheet.beginPath()
    path.moveTo(x, bottom - 1.5)
    path.lineTo(x - 1.8, bottom + BAR / 3)
    path.lineTo(x + 1.8, bottom + 2 * BAR / 3)
    path.lineTo(x, bottom + BAR + 1.5)
    sheet.drawPath(path, stroke=1, fill=0)


def _bar_label(feature, width):
    name = (feature['call'] or {}).get('name')
    room = width - 4
    if name and room >= layout.width(feature['id'], layout.SANS_BOLD, 6.5) + 22:
        return layout.fit(feature['id'] + ' ' + name, layout.SANS, 6.5, room)
    if room >= layout.width(feature['id'], layout.SANS_BOLD, 6.5):
        return feature['id']
    return None


def _draw_feature(sheet, plan, feature, visible, bottom):
    color, style = layout.feature_color(feature), _standing(feature)
    xs = [(AXIS_LEFT + (start - plan['start']) * plan['scale'], AXIS_LEFT + (end - plan['start']) * plan['scale'])
          for start, end, _ in visible]
    xs = [(left, max(right, left + 0.8)) for left, right in xs]
    middle = bottom + BAR / 2
    sheet.setStrokeColor(color)
    sheet.setLineWidth(0.6)
    for (_, before), (after, _) in zip(xs, xs[1:]):
        sheet.line(before, middle, after, middle)
    for (left, right), (start, end, segment) in zip(xs, visible):
        point = ('right' if feature['strand'] == '+' and end == feature['end']
                 else 'left' if feature['strand'] == '-' and start == feature['start'] else None)
        _outline(sheet, _segment_path(sheet, left, right, bottom, point), color, style)
        if segment['start'] < plan['start']:
            _continues_mark(sheet, left, bottom)
        if segment['end'] > plan['end']:
            _continues_mark(sheet, right, bottom)
    left, right = max(xs, key=lambda pair: pair[1] - pair[0])
    label = _bar_label(feature, right - left - ARROW)
    if label:
        layout.text(sheet, left + 2, bottom + 3.2, label, layout.SANS, 6.5,
                    layout.WHITE if style in ('supported', 'contested') else layout.INK)


def _draw_axis(sheet, plan, axis, row_length):
    r0, r1, scale = plan['start'], plan['end'], plan['scale']
    layout.rule(sheet, AXIS_LEFT, axis, AXIS_LEFT + (r1 - r0) * scale, layout.INK, 0.8)
    step = _tick_step(row_length)
    for position in range(_round_up(r0, step) if r0 else 0, r1 + 1, step):
        x = AXIS_LEFT + (position - r0) * scale
        layout.rule(sheet, x, axis, x, layout.INK, 0.5)
        sheet.line(x, axis, x, axis - 3)
        value = layout.count(max(position, 1))
        half = layout.width(value, layout.SANS, 6.5) / 2
        layout.text(sheet, min(max(x, layout.LEFT + half), layout.RIGHT - half), axis - 11, value, layout.SANS, 6.5,
                    layout.MUTED, 'center')


def _bar_bottom(strand, lane, axis):
    if strand == '-':
        return axis - TICK_BAND - lane * PITCH - BAR - 1
    if strand == '.':
        return axis - BAR / 2
    return axis + 3 + lane * PITCH


def _draw_row(sheet, plan, y, row_length):
    axis = y - _above_height(plan)
    _draw_axis(sheet, plan, axis, row_length)
    for feature, visible, strand, lane in plan['placed']:
        _draw_feature(sheet, plan, feature, visible, _bar_bottom(strand, lane, axis))
    return y - _row_height(plan)


# -- the page ----------------------------------------------------------------------------------------------------------

def _legend_sample(sheet, x, y, color, style, point=None, width=14):
    _outline(sheet, _segment_path(sheet, x, x + width, y - 1, point), color, style)
    return x + width + 4


def _legend_item(sheet, x, y, value, size=7.5):
    layout.text(sheet, x, y, value, layout.SANS, size, layout.MUTED)
    return x + layout.width(value, layout.SANS, size) + 14


def _legend(sheet, y):
    x = layout.LEFT
    for frame in (1, 2, 3):
        x = layout.swatch(sheet, x, y, layout.FRAME[frame], 'frame %d' % frame)
    x = layout.swatch(sheet, x, y, layout.NONCODING, 'not read in codons')
    x = _legend_item(sheet, _legend_sample(sheet, x + 6, y, layout.NONCODING, 'supported', 'right'), y,
                     'arrowhead: where reading stops')
    _continues_mark(sheet, x + 2, y - 1)
    _legend_item(sheet, x + 8, y, 'continues in the next row')
    y -= 14
    x = _legend_item(sheet, _legend_sample(sheet, layout.LEFT, y, layout.NONCODING, 'contested'), y, 'contested')
    x = _legend_item(sheet, _legend_sample(sheet, x, y, layout.NONCODING, 'no_annotation'), y,
                     'located, no annotation')
    _legend_item(sheet, _legend_sample(sheet, x, y, layout.NONCODING, 'lost'), y,
                 'lost to a rival, not part of the annotation')
    return y - 22


def _heading(sheet, y, sequence, continued):
    name = sequence['name'] + (' (continued)' if continued else '')
    layout.text(sheet, layout.LEFT, y, name, layout.SANS_BOLD, 10, room=layout.WIDTH / 2)
    layout.text(sheet, layout.RIGHT, y, '%s letters, GC content %s' % (
        layout.count(sequence['length']), layout.percent(sequence['gc_fraction'], 1)), layout.SANS, 8, layout.MUTED,
        'right')
    return y - 12


def _caption(sequence, features):
    return ('%s, %s letters: %d feature calls drawn to scale; forward-strand features above the line, reverse-strand '
            'below; colour marks the reading frame.' % (sequence['name'], layout.count(sequence['length']),
                                                        len(features)))


def _open_page(sheet, data, continued):
    y = layout.start_page(sheet, data, SECTION, TITLE + (' (continued)' if continued else ''),
                          None if continued else LEDE)
    return _legend(sheet, y)


def _next_page(sheet, data, sequence):
    layout.end_page(sheet)
    return _heading(sheet, _open_page(sheet, data, True), sequence, True)


def _draw_sequence(sheet, data, y, sequence):
    features = [feature for feature in data['features'] if feature['sequence_ref'] == sequence['ref']]
    depths = _depths(data['features'])
    row_length, plans = _plan_rows(features, sequence['length'], depths)
    if y - 12 - _row_height(plans[0]) < layout.BOTTOM:
        y = _next_page(sheet, data, sequence)
    else:
        y = _heading(sheet, y, sequence, False)
    for plan in plans:
        if y - _row_height(plan) < layout.BOTTOM:
            y = _next_page(sheet, data, sequence)
        y = _draw_row(sheet, plan, y, row_length)
    lines = layout.wrap(_caption(sequence, features), layout.SANS, 7.5, layout.WIDTH)
    if y - 11 * len(lines) < layout.BOTTOM:
        y = _next_page(sheet, data, sequence)
    for line in lines:
        y -= 10
        layout.text(sheet, layout.LEFT, y, line, layout.SANS, 7.5, layout.MUTED)
    return y - 16


def draw(sheet, data):
    y = _open_page(sheet, data, False)
    for sequence in data['sequences']:
        y = _draw_sequence(sheet, data, y, sequence)
    layout.end_page(sheet)
