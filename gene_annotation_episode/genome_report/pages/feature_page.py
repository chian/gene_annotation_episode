"""Section 04: one page per feature: the call, its alternates and the evidence each has, side by side. A strip shows the
feature in its neighbourhood on the sequence, a table sets the call against its alternates, and below it are the names
among all matches inside the feature, the searches that found it and the organisms of the matches."""
from __future__ import annotations

from .. import layout

SECTION = '04'
NO_CALL_TITLE = 'No annotation'
NO_ANNOTATION = 'No annotation was proposed for this feature.'
STRAND_WORDS = {'+': 'forward', '-': 'reverse'}
KIND_WORDS = {'product': 'database product name', 'profile_family': 'protein family',
              'reference_sequence': 'reference sequence'}
AXIS_WORDS = {
    'sequence_homology_evidence': 'sequence similarity', 'structural_homology_evidence': 'structure similarity',
    'gene_context_evidence': 'neighbouring genes', 'evolutionary_history_evidence': 'evolutionary history',
    'experimental_activity_evidence': 'experiments in the literature',
    'perturbation_evidence': 'perturbation experiments', 'partner_presence_evidence': 'partner molecules',
    'sample_context_evidence': 'sample context', 'biochemical_feasibility_evidence': 'biochemical feasibility'}
STATUS_WORDS = {'measured': 'examined', 'measured_zero': 'examined, nothing found', 'unknown': 'not examined'}
LINE_WORDS = {'call': 'on the line of the call', 'alternate': 'on the line of an alternate', 'other': 'on neither'}

LANE = 13
MAX_LANES = 3
STRIP_INSET = 12
MAX_LINES = 6
MAX_CLAIMS = 3
MAX_NAMES = 12
MAX_SEARCHES = 8
MAX_TAXA = 6
LOWER_LEFT_WIDTH = 270
COLUMN_GAP = 20

# The table: name of the column, width, alignment. The first column holds the swatch and its word.
TABLE = (('', 46, 'left'), ('name', 168, 'left'), ('kind of name', 80, 'left'), ('matches', 42, 'right'),
         ('best identity', 44, 'right'), ('typical coverage', 46, 'right'), ('share of matches', 78, 'left'))


def _sequence(data, feature):
    return next(sequence for sequence in data['sequences'] if sequence['ref'] == feature['sequence_ref'])


def _heading(sheet, x, y, value, room):
    layout.text(sheet, x, y, value, layout.SANS_BOLD, 9, room=room)
    layout.rule(sheet, x, y - 4, x + room, layout.INK, 0.6)
    return y - 17


def _caption(sheet, y, value):
    return layout.paragraph(sheet, layout.LEFT, y, value, layout.WIDTH, size=7, color=layout.MUTED)


def _title(feature):
    call = feature['call']
    return call['name'] or call['identifier'] if call else NO_CALL_TITLE


def _lede(feature):
    lede = '%s at %s on the %s strand, %s letters' % (feature['kind'].replace('_', ' '), layout.location(feature),
                                                      STRAND_WORDS[feature['strand']], layout.count(feature['length']))
    if feature['protein']:
        lede += ', protein of %s residues' % layout.count(feature['protein']['length'])
    lede += '; %s.' % layout.STANDING_WORDS[feature['standing']]
    if not feature['chosen']:
        lede += (' Lost to %s; not part of the genome annotation.' % feature['lost_to'] if feature['lost_to']
                 else ' Not part of the genome annotation.')
    if feature['parent']:
        lede += ' Lies inside %s.' % feature['parent']
    return lede


# -- the locus strip ---------------------------------------------------------------------------------------------------

def _window(feature, sequence_length):
    pad = round(0.25 * feature['length'])
    return max(0, feature['start'] - pad), min(sequence_length, feature['end'] + pad)


def _lanes(items, scale):
    """Per item ``(start, end, label width)`` its lane, the first lane where it does not touch an earlier item."""
    ends, placed = [], []
    for start, end, label_width in items:
        left, right = scale(start), max(scale(end), scale(start) + label_width) + 3
        lane = next((index for index, edge in enumerate(ends) if edge <= left), len(ends))
        if lane == len(ends):
            ends.append(right)
        else:
            ends[lane] = right
        placed.append(lane)
    return placed


def _neighbours(data, feature, window):
    rivals = {rival['id'] for rival in feature['rivals']}
    return [other for other in data['features'] if other is not feature
            and other['sequence_ref'] == feature['sequence_ref']
            and other['start'] < window[1] and other['end'] > window[0]
            ], rivals


def _other_versions(feature):
    own = {'start': feature['start'], 'end': feature['end'], 'segments': feature['segments']}
    return [version for version in feature['versions'] if version != own]


def _neighbour_label(other, rivals):
    return other['id'] + (' rival' if other['id'] in rivals else '')


def _place(data, feature, window, scale):
    """The neighbours with their lane on their side of the axis, the lanes each side needs, and the versions' lanes."""
    neighbours, rivals = _neighbours(data, feature, window)
    sides = {'+': [], '-': []}
    sides[feature['strand']].append((feature['start'], feature['end'], 0, None))
    for other in sorted(neighbours, key=lambda row: (row['start'], row['end'], row['id'])):
        label = _neighbour_label(other, rivals)
        sides[other['strand']].append((other['start'], other['end'], 2 * layout.width(label, layout.SANS, 6.5) + 6,
                                       other))
    placed = {}
    for strand, items in sides.items():
        lanes = _lanes([item[:3] for item in items], scale)
        placed[strand] = [(item[3], lane) for item, lane in zip(items, lanes)]
    versions = _other_versions(feature)
    version_lanes = _lanes([(v['start'], v['end'], layout.width(layout.location(v), layout.MONO, 6)) for v in versions],
                           scale)
    return placed, rivals, versions, version_lanes


def _frame_words(feature):
    return 'not read in codons' if feature['frame'] is None else 'reading frame %d' % abs(feature['frame'])


def _draw_feature_bar(sheet, feature, scale, y):
    color = layout.feature_color(feature)
    segments = feature['segments']
    layout.rule(sheet, scale(segments[0]['start']), y + 4, scale(segments[-1]['end']), color, 1)
    for segment in segments:
        left, right = scale(segment['start']), scale(segment['end'])
        layout.box(sheet, left, y - 1, max(right - left, 0.8), 10, fill=color)
    left, right = scale(feature['start']), scale(feature['end'])
    layout.text(sheet, left + 3, y + 2, '%s, %s' % (feature['id'], _frame_words(feature)), layout.SANS_BOLD, 6.5,
                layout.WHITE, room=right - left - 6)


def _draw_neighbour(sheet, other, label, scale, y, room_right):
    left, right = scale(other['start']), scale(other['end'])
    layout.box(sheet, left, y - 1, max(right - left, 0.8), 10, fill=layout.WHITE, stroke=layout.NONCODING)
    if right - left < layout.width(label, layout.SANS, 6.5) + 4:
        left = right
    layout.text(sheet, left + 2, y + 2, label, layout.SANS, 6.5, layout.MUTED, room=room_right - left - 2)


def _tick(sheet, x, y1, y2, color, weight=0.8):
    sheet.setStrokeColor(color)
    sheet.setLineWidth(weight)
    sheet.line(x, y1, x, y2)


def _draw_version(sheet, version, scale, y):
    left, right = scale(version['start']), scale(version['end'])
    layout.rule(sheet, left, y + 3, right, layout.INK, 0.8)
    _tick(sheet, left, y + 1, y + 5, layout.INK)
    _tick(sheet, right, y + 1, y + 5, layout.INK)
    layout.text(sheet, min(left, layout.RIGHT - layout.width(layout.location(version), layout.MONO, 6)), y - 6,
                layout.location(version), layout.MONO, 6, layout.INK)


def _strip(sheet, data, feature, y):
    sequence_length = _sequence(data, feature)['length']
    window = _window(feature, sequence_length)
    x0, x1 = layout.LEFT + STRIP_INSET, layout.RIGHT

    def scale(position):
        return x0 + (min(max(position, window[0]), window[1]) - window[0]) / (window[1] - window[0]) * (x1 - x0)

    placed, rivals, versions, version_lanes = _place(data, feature, window, scale)
    lanes = {strand: min(max([lane + 1 for _, lane in rows] or [1]), MAX_LANES) for strand, rows in placed.items()}
    axis = y - lanes['+'] * LANE - 2
    below = axis - 12
    for strand, sign, base in (('+', '+', axis + 5), ('-', '-', below - 3)):
        layout.text(sheet, layout.LEFT, base + (1 if strand == '+' else -1), sign, layout.MONO_BOLD, 9, layout.MUTED)
    layout.rule(sheet, x0, axis, x1, layout.INK, 0.8)
    for x in (x0, x1):
        _tick(sheet, x, axis - 2, axis + 2, layout.INK)
    hidden = 0
    for strand, rows in placed.items():
        for other, lane in rows:
            if lane >= MAX_LANES:
                hidden += 1
                continue
            row_y = axis + 4 + lane * LANE if strand == '+' else below - 3 - LANE - lane * LANE + 3
            if other is None:
                _draw_feature_bar(sheet, feature, scale, row_y)
            else:
                _draw_neighbour(sheet, other, _neighbour_label(other, rivals), scale, row_y, x1)
    labels = [(window[0], x0, 'left'), (window[1], x1, 'right'), (feature['start'], scale(feature['start']), 'left'),
              (feature['end'], scale(feature['end']), 'right')]
    shown = {}
    for position, x, align in labels[2:] + labels[:2]:
        if all(abs(x - other) > 36 for other, _ in shown.values()):
            shown[(position, align)] = (x, align)
    for (position, _), (x, align) in shown.items():
        layout.text(sheet, x, axis - 9, layout.count(position + (1 if align == 'left' else 0)), layout.MONO, 6.5,
                    layout.MUTED, align)
    y = below - 3 - lanes['-'] * LANE
    for version, lane in zip(versions, version_lanes):
        _draw_version(sheet, version, scale, y - 4 - lane * 12)
    y -= 4 + (max(version_lanes) + 1) * 12 if versions else 0
    sentence = ('The feature in its colour with the features that overlap its neighbourhood in grey outline, on the '
                'sequence drawn to scale; the forward strand is above the line and the reverse strand below.')
    if versions:
        sentence += ' Brackets mark the other positions called for the feature.'
    if hidden:
        sentence += ' %d more overlapping features are not drawn.' % hidden
    return _caption(sheet, y - 8, sentence) - 4


# -- the call and its alternates ---------------------------------------------------------------------------------------

def _lines(feature):
    lines = [('call', feature['call'])] if feature['call'] else []
    return lines + [('alternate', line) for line in feature['alternates']]


def _axes_text(line):
    return '; '.join('%s: %s' % (AXIS_WORDS[axis['axis']], STATUS_WORDS[axis['status']]) for axis in line['axes'])


def _claim_text(claim):
    checked = 'not checked' if claim['commissions'] == 0 else 'checked %d times' % claim['commissions']
    return '%s %s (%s): %s' % (claim['predicate'], claim['partner'], claim['partner_kind'], checked)


def _extra_lines(line, room):
    """The small lines under a row: ``(text, font, size)``."""
    extra = []
    if len(line['names']) > 1:
        names = [name for name in line['names'] if name != line['name']]
        extra.append(('also named: ' + ', '.join(names), layout.SANS, 6.5))
    claims = line['claims']
    extra += [(_claim_text(claim), layout.SANS, 6.5) for claim in claims[:MAX_CLAIMS]]
    if len(claims) > MAX_CLAIMS:
        extra.append(('and %d more checked statements' % (len(claims) - MAX_CLAIMS), layout.SANS, 6.5))
    if line['axes']:
        extra += [(words, layout.MONO, 6) for words in layout.wrap(_axes_text(line), layout.MONO, 6, room)[:3]]
    return extra


def _row_height(line, room):
    return 19 + 8 * len(_extra_lines(line, room))


def _table_header(sheet, y):
    x = layout.LEFT
    for heading, column_width, align in TABLE:
        for index, part in enumerate(layout.wrap(heading, layout.MONO, 6.5, column_width - 6) if heading else []):
            layout.label(sheet, x if align == 'left' else x + column_width - 4, y - 8 * index, part,
                         align=align)
        x += column_width
    layout.rule(sheet, layout.LEFT, y - 12, layout.RIGHT, layout.INK, 0.6)
    return y - 12


def _draw_row(sheet, y, role, line, feature, room):
    x = layout.LEFT
    color = layout.LINE[role]
    layout.box(sheet, x, y - 11, 7, 7, fill=color)
    layout.text(sheet, x + 10, y - 10.5, role, layout.SANS, 7, layout.MUTED, room=34)
    x += TABLE[0][1]
    layout.text(sheet, x, y - 10.5, line['name'] or line['identifier'] or '-',
                layout.SANS_BOLD if role == 'call' else layout.SANS, 8.5, room=TABLE[1][1] - 8)
    x += TABLE[1][1]
    for index, part in enumerate(layout.wrap(KIND_WORDS[line['vocabulary']], layout.SANS, 7, TABLE[2][1] - 6)):
        layout.text(sheet, x, y - 10.5 - 7.5 * index, part, layout.SANS, 7, layout.MUTED)
    x += TABLE[2][1]
    hits = line['hit_count'] or 0
    for value, (_, column_width, _) in zip((layout.count(hits), layout.percent(line['best_identity']),
                                            layout.percent(line['median_feature_coverage'])), TABLE[3:6]):
        layout.text(sheet, x + column_width - 4, y - 10.5, value, layout.MONO, 8, align='right')
        x += column_width
    total = feature['hit_count']
    x += 8
    track = TABLE[6][1] - 18
    layout.box(sheet, x, y - 10, track, 6, fill=layout.PANEL)
    layout.box(sheet, x, y - 10, track * hits / total if total else 0, 6, fill=color)
    line_y = y - 19
    for words, font, size in _extra_lines(line, room):
        layout.text(sheet, layout.LEFT + TABLE[0][1], line_y, words, font, size, layout.MUTED, room=room)
        line_y -= 8
    layout.rule(sheet, layout.LEFT, y - _row_height(line, room) + 3, layout.RIGHT)


def _table(sheet, y, feature, bottom):
    y = _heading(sheet, layout.LEFT, y, 'The call and its alternates', layout.WIDTH)
    lines = _lines(feature)
    if not lines:
        layout.text(sheet, layout.LEFT, y, NO_ANNOTATION, size=9, color=layout.MUTED)
        return y - 20
    room = layout.WIDTH - TABLE[0][1]
    y = _table_header(sheet, y)
    shown = 0
    for role, line in lines[:MAX_LINES]:
        if y - _row_height(line, room) < bottom:
            break
        _draw_row(sheet, y, role, line, feature, room)
        y -= _row_height(line, room)
        shown += 1
    if shown < len(lines):
        layout.text(sheet, layout.LEFT + TABLE[0][1], y - 9, 'and %d more alternates' % (len(lines) - shown),
                    size=7.5, color=layout.MUTED)
        y -= 14
    return y - 6


# -- below the table ---------------------------------------------------------------------------------------------------

def _names_height(feature):
    if not feature['names']:
        return 40
    return 17 + 14 + 10.5 * min(len(feature['names']), MAX_NAMES) + (12 if len(feature['names']) > MAX_NAMES else 0)


def _merged_searches(feature):
    merged = {}
    for search in feature['searches']:
        key = (search['tool'], search['version'], search['database'])
        merged[key] = merged.get(key, 0) + search['hit_count']
    return [{'tool': tool, 'version': version, 'database': database, 'hit_count': hits}
            for (tool, version, database), hits in merged.items()]


def _right_height(feature):
    searches = _merged_searches(feature)
    height = 17 + 10.5 * min(len(searches), MAX_SEARCHES) + (10 if len(searches) > MAX_SEARCHES else 0)
    if feature['hit_taxa']:
        height += 8 + 17 + 10.5 * min(len(feature['hit_taxa']), MAX_TAXA)
    return height


def lower_height(feature):
    return max(_names_height(feature), _right_height(feature))


def _legend(sheet, x, y):
    for role, words in LINE_WORDS.items():
        x = layout.swatch(sheet, x, y, layout.LINE[role], words, 6.5)


def _names(sheet, y, feature):
    room = LOWER_LEFT_WIDTH
    y = _heading(sheet, layout.LEFT, y, 'Names among the matches', room)
    names = feature['names']
    if not names:
        layout.text(sheet, layout.LEFT, y, 'No database match lies inside this feature.', size=8, color=layout.MUTED)
        return
    _legend(sheet, layout.LEFT, y)
    y -= 14
    top = max(row['count'] for row in names)
    bar_left, bar_room = layout.LEFT + 112, 80
    for row in names[:MAX_NAMES]:
        layout.text(sheet, layout.LEFT, y, row['label'], layout.SANS, 7, room=106)
        size = bar_room * row['count'] / top
        layout.box(sheet, bar_left, y - 1, max(size, 0.8), 7, fill=layout.LINE[row['line']])
        layout.text(sheet, bar_left + size + 3, y, layout.count(row['count']), layout.MONO, 6.5)
        layout.text(sheet, layout.LEFT + room, y, layout.percent(row['best_identity'], 1), layout.MONO, 6, layout.MUTED,
                    'right')
        y -= 10.5
    rest = names[MAX_NAMES:]
    if rest:
        layout.text(sheet, layout.LEFT, y - 2, '%d further names with %s matches in all' % (
            len(rest), layout.count(sum(row['count'] for row in rest))), size=7, color=layout.MUTED)


def _searches(sheet, x, y, feature, room):
    y = _heading(sheet, x, y, 'Which searches found it', room)
    searches = _merged_searches(feature)
    for search in searches[:MAX_SEARCHES]:
        found = search['hit_count']
        layout.text(sheet, x, y, layout.tool_name(search), size=7, room=room - 66)
        layout.text(sheet, x + room, y, '%s matches' % layout.count(found) if found else 'found nothing', size=7,
                    color=layout.INK if found else layout.MUTED, align='right')
        y -= 10.5
    if len(searches) > MAX_SEARCHES:
        layout.text(sheet, x, y, 'and %d more searches' % (len(searches) - MAX_SEARCHES), size=7, color=layout.MUTED)
        y -= 10
    return y


def _taxa(sheet, x, y, feature, room):
    y = _heading(sheet, x, y - 8, 'Organisms of the matches', room)
    for taxon in feature['hit_taxa'][:MAX_TAXA]:
        layout.text(sheet, x, y, '%s: %s' % (taxon['name'] or 'taxon %d' % taxon['taxon_id'],
                                             layout.count(taxon['count'])), size=7, room=room)
        y -= 10.5


def _lower(sheet, y, feature):
    _names(sheet, y, feature)
    x = layout.LEFT + LOWER_LEFT_WIDTH + COLUMN_GAP
    room = layout.RIGHT - x
    below = _searches(sheet, x, y, feature, room)
    if feature['hit_taxa']:
        _taxa(sheet, x, below, feature, room)


# -- the page ----------------------------------------------------------------------------------------------------------

def draw_feature(sheet, data, feature):
    y = layout.start_page(sheet, data, SECTION + ' · ' + feature['id'], _title(feature), _lede(feature))
    y = _strip(sheet, data, feature, y)
    low = layout.BOTTOM + lower_height(feature)
    y = _table(sheet, y - 8, feature, low + 30)
    _lower(sheet, y - 8, feature)
    layout.end_page(sheet)


def draw(sheet, data):
    for feature in data['features']:
        draw_feature(sheet, data, feature)
