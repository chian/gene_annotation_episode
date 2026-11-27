"""The one look of every page of the report: the page, the type, the colours, and the few drawing helpers the pages
share. A page module draws with these and adds only what is its own. Everything is drawn by code from the report's
data, with the PDF's standard fonts and no clock or random value, so the same data gives the same file.

Units are points; the origin is the bottom left corner of the page; ``y`` runs up."""
from __future__ import annotations

from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

PAGE_WIDTH, PAGE_HEIGHT = 612.0, 792.0
MARGIN = 54.0
LEFT, RIGHT = MARGIN, PAGE_WIDTH - MARGIN
TOP, BOTTOM = PAGE_HEIGHT - 72.0, 60.0
WIDTH = RIGHT - LEFT

SERIF, SERIF_BOLD = 'Times-Roman', 'Times-Bold'
SANS, SANS_BOLD = 'Helvetica', 'Helvetica-Bold'
MONO, MONO_BOLD = 'Courier', 'Courier-Bold'

INK = HexColor('#141413')
MUTED = HexColor('#6b6a65')
RULE = HexColor('#d9d7cf')
PANEL = HexColor('#f5f4ef')
WHITE = HexColor('#ffffff')

# One colour per reading frame (1, 2, 3 on a strand); a feature that is not read in codons is NONCODING.
FRAME = {1: HexColor('#4a7bd0'), 2: HexColor('#d9703f'), 3: HexColor('#55ab7d')}
NONCODING = HexColor('#8a8a86')
# Where a match stands: on the line of the call, on the line of an alternate, or on neither.
LINE = {'call': HexColor('#2f5fb3'), 'alternate': HexColor('#d9703f'), 'other': HexColor('#b5b3ab')}
# How a call stands.
STANDING = {'supported': HexColor('#3d8f63'), 'contested': HexColor('#c98a1b'), 'no_annotation': HexColor('#8a8a86')}
STANDING_WORDS = {'supported': 'well supported', 'contested': 'contested', 'no_annotation': 'no annotation'}


def canvas(path, title):
    sheet = Canvas(str(path), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1)
    sheet.setTitle(title)
    return sheet


# -- text --------------------------------------------------------------------------------------------------------------

def clean(value):
    """Text the standard fonts can show: anything outside Latin-1 becomes a question mark."""
    return str(value).encode('latin-1', 'replace').decode('latin-1')


def width(value, font, size):
    return stringWidth(clean(value), font, size)


def fit(value, font, size, room):
    """``value``, cut with three dots when it is wider than ``room``."""
    value = clean(value)
    if stringWidth(value, font, size) <= room:
        return value
    while value and stringWidth(value + '...', font, size) > room:
        value = value[:-1]
    return value + '...'


def wrap(value, font, size, room):
    """``value`` as lines no wider than ``room``, broken at spaces."""
    lines, line = [], ''
    for word in clean(value).split():
        trial = word if not line else line + ' ' + word
        if line and stringWidth(trial, font, size) > room:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


def text(sheet, x, y, value, font=SANS, size=9, color=INK, align='left', room=None):
    """One line of text at the baseline ``y``; cut to ``room`` when it is given."""
    value = clean(value) if room is None else fit(value, font, size, room)
    sheet.setFont(font, size)
    sheet.setFillColor(color)
    {'left': sheet.drawString, 'right': sheet.drawRightString, 'center': sheet.drawCentredString}[align](x, y, value)


def paragraph(sheet, x, y, value, room, font=SANS, size=9, color=INK, leading=None):
    """``value`` wrapped to ``room`` from the baseline ``y`` down; gives the baseline below the last line."""
    leading = leading or size * 1.4
    for line in wrap(value, font, size, room):
        text(sheet, x, y, line, font, size, color)
        y -= leading
    return y


def label(sheet, x, y, value, color=MUTED, align='left'):
    """A small capital label, as above a table column or a tile."""
    text(sheet, x, y, clean(value).upper(), MONO, 6.5, color, align)


# -- shapes ------------------------------------------------------------------------------------------------------------

def rule(sheet, x1, y, x2, color=RULE, weight=0.5):
    sheet.setStrokeColor(color)
    sheet.setLineWidth(weight)
    sheet.line(x1, y, x2, y)


def box(sheet, x, y, w, h, fill=None, stroke=None, weight=0.5):
    """A rectangle whose bottom left corner is ``(x, y)``."""
    if fill is not None:
        sheet.setFillColor(fill)
    if stroke is not None:
        sheet.setStrokeColor(stroke)
        sheet.setLineWidth(weight)
    sheet.rect(x, y, w, h, fill=int(fill is not None), stroke=int(stroke is not None))


def swatch(sheet, x, y, color, value, size=7.5):
    """A legend entry: a square of ``color`` and its meaning; gives the x after it."""
    box(sheet, x, y - 0.5, 7, 7, fill=color)
    text(sheet, x + 10, y, value, SANS, size, MUTED)
    return x + 10 + width(value, SANS, size) + 14


# -- the page ----------------------------------------------------------------------------------------------------------

def start_page(sheet, data, section, title, lede=None):
    """Open a page: the running head, the section number and title, an optional sentence below. Gives the ``y`` at
    which the page's own content starts."""
    text(sheet, LEFT, PAGE_HEIGHT - 40, 'GENOME ANNOTATION REPORT   ' + data['run']['run_id'], MONO, 7, MUTED)
    text(sheet, RIGHT, PAGE_HEIGHT - 40, ', '.join(sequence['name'] for sequence in data['sequences']), MONO, 7, MUTED,
         'right', WIDTH / 2)
    rule(sheet, LEFT, PAGE_HEIGHT - 46, RIGHT, INK, 0.8)
    y = TOP
    text(sheet, LEFT, y, section, MONO, 8, MUTED)
    y -= 22
    lines = wrap(title, SERIF_BOLD, 20, WIDTH)
    for line in lines[:2]:
        text(sheet, LEFT, y, line if len(lines) <= 2 or line is lines[0] else line + ' ...', SERIF_BOLD, 20,
             room=WIDTH)
        y -= 23
    y += 7
    if lede:
        y = paragraph(sheet, LEFT, y, lede, WIDTH * 0.85, SANS, 9.5, MUTED) - 4
    return y - 6


def end_page(sheet):
    """Close the page: its number at the foot."""
    rule(sheet, LEFT, BOTTOM - 14, RIGHT)
    text(sheet, RIGHT, BOTTOM - 26, 'page %d' % sheet.getPageNumber(), MONO, 7, MUTED, 'right')
    sheet.showPage()


def table(sheet, y, columns, rows, start=0, bottom=BOTTOM, x=LEFT, row_height=15, size=8):
    """Rows of a table from ``rows[start]`` down from ``y`` until ``bottom``; gives ``(y below, next row)``.

    ``columns``: per column ``(heading, width, align, font)``. A row is one value per column; a value that is a pair
    ``(text, colour)`` is drawn in that colour."""
    # A column read from the left that follows one read from the right starts a little further in.
    inset = [6 if align == 'left' and index and columns[index - 1][2] != 'left' else 0
             for index, (_, _, align, _) in enumerate(columns)]
    cursor = x
    for (heading, column_width, align, _), gap in zip(columns, inset):
        label(sheet, cursor + gap if align == 'left' else cursor + column_width - 4, y, heading,
              align='left' if align == 'left' else 'right')
        cursor += column_width
    y -= 5
    rule(sheet, x, y, cursor, INK, 0.6)
    index = start
    while index < len(rows) and y - row_height >= bottom:
        y -= row_height
        cursor = x
        for value, (_, column_width, align, font), gap in zip(rows[index], columns, inset):
            value, color = value if isinstance(value, tuple) else (value, INK)
            if align == 'left':
                text(sheet, cursor + gap, y + 4.5, value, font, size, color, room=column_width - 6 - gap)
            else:
                text(sheet, cursor + column_width - 4, y + 4.5, value, font, size, color, 'right')
            cursor += column_width
        rule(sheet, x, y, cursor)
        index += 1
    return y, index


def tiles(sheet, y, items, x=LEFT, room=WIDTH, per_row=5, height=58):
    """Number tiles: per item ``(number, meaning)``. Gives the ``y`` below them."""
    tile = room / per_row
    for index, (number, meaning) in enumerate(items):
        column, row = index % per_row, index // per_row
        left, top = x + column * tile, y - row * height
        box(sheet, left, top - height, tile, height, fill=WHITE, stroke=RULE)
        text(sheet, left + 9, top - 24, number, MONO, 16, room=tile - 14)
        for line, words in enumerate(wrap(meaning, SANS, 7, tile - 16)[:2]):
            text(sheet, left + 9, top - 37 - 9 * line, words, SANS, 7, MUTED)
    return y - height * ((len(items) + per_row - 1) // per_row)


# -- how values are written --------------------------------------------------------------------------------------------

def span(start, end):
    """Positions as a reader counts them: the first letter is 1 and the last one named is included."""
    return '%s..%s' % (count(start + 1), count(end))


def location(feature):
    """A feature's positions: one range, or ``join(...)`` of its ranges."""
    ranges = [span(segment['start'], segment['end']) for segment in feature['segments']]
    return ranges[0] if len(ranges) == 1 else 'join(%s)' % ','.join(ranges)


def count(value):
    return format(value, ',')


def percent(fraction, digits=0):
    return '-' if fraction is None else '%.*f%%' % (digits, 100 * fraction)


def evalue(value):
    return '0' if value == 0 else '%.0e' % value


def feature_color(feature):
    return NONCODING if feature['frame'] is None else FRAME[abs(feature['frame'])]


def tool_name(row):
    """A search as a reader names it: the tool, its version and the database it read."""
    return ' '.join(part for part in (row['tool'], row.get('version'),
                                      row.get('database') and 'against ' + row['database']) if part)
