"""Section 02, the organism: where the sequence was placed, the alternates, and what each classifier assigned. The
lineages of all candidate organisms are merged into one tree; beside it, row by row, a matrix shows for every taxon what
each classifier run put there. Assignments to taxa outside the tree are listed below it."""
from __future__ import annotations

from math import sqrt

from .. import layout

RANK_WORDS = {'R': 'root', 'D': 'domain', 'K': 'kingdom', 'P': 'phylum', 'C': 'class', 'O': 'order', 'F': 'family',
              'G': 'genus', 'S': 'species', 'U': 'unclassified'}
ROW = 12.5
STEP = 9.0
DOT = 4.2
CELL = 54.0
TREE_MIN = 232.0
ID_ROOM = 34.0
MARKER_COLOR = {'leader': layout.LINE['call'], 'rival': layout.LINE['alternate'], 'agreed': layout.INK,
                'candidate': layout.MUTED}
MARKER_WORD = {'leader': 'placed', 'rival': 'alternate', 'agreed': 'shared', 'candidate': 'candidate'}
MARKER_MEANING = {'leader': 'organism the sequence is placed in', 'rival': 'closest alternate',
                  'agreed': 'deepest taxon the placed organism and the alternate share',
                  'candidate': 'another candidate'}
DOT_MEANING = 'dot area: share of the largest number in the column; a number with decimals is the tool\'s own measure'
FOOTER = 64.0
CAPTION = ('Each line is a taxon on the lineage of a candidate organism, from the top of the taxonomy down; each '
           'column is one classifier run and its dot shows what it put at exactly that taxon.')
STRAY_HEADING = 'Assigned by a classifier to a taxon that is not on any candidate\'s lineage'
STRAY_COLUMNS = (('Taxon', 190, 'left', layout.SANS), ('Taxon id', 60, 'left', layout.MONO),
                 ('Tool', 80, 'left', layout.SANS), ('Database', 110, 'left', layout.SANS),
                 ('Count or measure', 64, 'right', layout.MONO))


def rank_word(rank_code):
    letter, level = rank_code[0], rank_code[1:]
    word = RANK_WORDS[letter]
    return 'below ' + word if level and int(level) else word


def _taxon_name(node):
    return node['name'] or 'taxon %d' % node['taxon_id']


def _build_tree(candidates, agreed_taxon_id):
    nodes, roots = {}, []
    for candidate in candidates:
        parent = None
        for step in candidate['lineage']:
            node = nodes.get(step['taxon_id'])
            if node is None:
                node = nodes[step['taxon_id']] = {'taxon_id': step['taxon_id'], 'name': step['name'], 'rank': None,
                                                  'markers': [], 'children': [], 'path': False}
                (roots if parent is None else parent['children']).append(node)
            node['name'] = node['name'] or step['name']
            parent = node
    for candidate in candidates:
        node = nodes[candidate['taxon_id']]
        node['name'], node['rank'] = candidate['name'], rank_word(candidate['rank_code'])
        node['markers'].append({'leader': 'leader', 'rival': 'rival', 'other': 'candidate'}[candidate['role']])
        if candidate['role'] == 'leader':
            for step in candidate['lineage']:
                nodes[step['taxon_id']]['path'] = True
    if agreed_taxon_id is not None:
        nodes[agreed_taxon_id]['markers'].append('agreed')
    return nodes, roots


def _rows(nodes, roots):
    """The tree in reading order: per line the chain of nodes from its root down to it."""
    rows = []

    def walk(node, chain):
        chain = chain + [node]
        rows.append(chain)
        for child in node['children']:
            walk(child, chain)

    for root in roots:
        walk(root, [])
    return rows


def _lede(organism, nodes):
    candidates = {row['taxon_id']: row for row in organism['candidates']}
    leader, rival = organism['leader_taxon_id'], organism['rival_taxon_id']
    if leader is None:
        return 'No organism could be placed.'
    sentence = 'Placed in %s (%s).' % (candidates[leader]['name'], rank_word(candidates[leader]['rank_code']))
    if rival is not None:
        sentence += ' The closest alternate is %s (%s)' % (candidates[rival]['name'],
                                                            rank_word(candidates[rival]['rank_code']))
        agreed = organism['agreed_taxon_id']
        sentence += '; both lie in %s.' % _taxon_name(nodes[agreed]) if agreed is not None else '.'
    return sentence


def _runs(assignments):
    runs = sorted({(row['tool'], row['database'] or '') for row in assignments})
    cells = {(run, row['taxon_id']): row for row in assignments for run in [(row['tool'], row['database'] or '')]}
    largest = {run: max(_number(row) for row in assignments if (row['tool'], row['database'] or '') == run)
               for run in runs}
    return runs, cells, largest



def _number(assigned):
    return assigned['count'] if assigned['count'] is not None else assigned['model_score']


def _number_words(assigned):
    """A count as a whole number; a tool's own measure as the tool gave it, to two decimals."""
    return layout.count(assigned['count']) if assigned['count'] is not None else '%.2f' % assigned['model_score']


def _marker_pills(sheet, x, y, markers):
    for marker in markers:
        word = MARKER_WORD[marker].upper()
        pill = layout.width(word, layout.MONO_BOLD, 5.5) + 6
        color = MARKER_COLOR[marker]
        if marker == 'candidate':
            layout.box(sheet, x, y - 2, pill, 8, fill=layout.WHITE, stroke=color, weight=0.5)
            layout.text(sheet, x + 3, y + 0.3, word, layout.MONO_BOLD, 5.5, color)
        else:
            layout.box(sheet, x, y - 2, pill, 8, fill=color)
            layout.text(sheet, x + 3, y + 0.3, word, layout.MONO_BOLD, 5.5, layout.WHITE)
        x += pill + 3
    return x


def _pills_width(markers):
    return sum(layout.width(MARKER_WORD[marker].upper(), layout.MONO_BOLD, 5.5) + 9 for marker in markers)


def _connectors(sheet, chain, top, step):
    """The thin lines that join a line's taxon to its parent and carry on to its later siblings; the stretch from
    the top down to the placed organism is bold."""
    middle = top - ROW / 2 - 1
    depth = len(chain) - 1
    for level in range(depth):
        parent, child = chain[level], chain[level + 1]
        x = layout.LEFT + level * step + 2
        last = parent['children'][-1] is child
        onward = parent['path'] and _path_below(parent, child)
        if level == depth - 1:
            _segment(sheet, x, top, x, middle, child['path'])
            _segment(sheet, x, middle, x + step - 2, middle, child['path'])
            if not last:
                _segment(sheet, x, middle, x, top - ROW, onward)
        elif not last:
            _segment(sheet, x, top, x, top - ROW, onward)


def _path_below(parent, child):
    later = parent['children'][parent['children'].index(child) + 1:]
    return any(sibling['path'] for sibling in later)


def _segment(sheet, x1, y1, x2, y2, bold):
    sheet.setStrokeColor(layout.LINE['call'] if bold else layout.RULE)
    sheet.setLineWidth(1.6 if bold else 0.6)
    sheet.line(x1, y1, x2, y2)


def _tree_line(sheet, chain, top, step, tree_right):
    node = chain[-1]
    x = layout.LEFT + (len(chain) - 1) * step + 4
    base = top - ROW + 3.5
    font = layout.SANS_BOLD if node['path'] else layout.SANS
    layout.text(sheet, tree_right - 4, base, node['taxon_id'], layout.MONO, 6, layout.MUTED, 'right')
    room = tree_right - 4 - ID_ROOM - _pills_width(node['markers']) - x
    name = _taxon_name(node)
    rank = node['rank'] and ' ' + node['rank']
    if rank and room - layout.width(rank, layout.SANS, 6.5) < layout.width(name, font, 7.5):
        rank = None
    name = layout.fit(name, font, 7.5, room - (layout.width(rank, layout.SANS, 6.5) if rank else 0))
    layout.text(sheet, x, base, name, font, 7.5)
    end = x + layout.width(name, font, 7.5)
    if rank:
        layout.text(sheet, end, base, rank, layout.SANS, 6.5, layout.MUTED)
        end += layout.width(rank, layout.SANS, 6.5)
    _marker_pills(sheet, end + 4, base, node['markers'])


def _dot(sheet, x, y, share):
    sheet.setFillColor(layout.INK)
    sheet.circle(x, y, max(DOT * sqrt(min(share, 1)), 0.9), stroke=0, fill=1)


def _cell(sheet, x, base, cell_width, assigned, largest):
    _dot(sheet, x + DOT + 2, base + 2.5, _number(assigned) / largest if largest else 0)
    layout.text(sheet, x + cell_width - 3, base, _number_words(assigned), layout.MONO, 6.5, align='right')


def _matrix_head(sheet, y, runs, left, cell_width):
    for index, (tool, database) in enumerate(runs):
        x = left + index * cell_width + 3
        layout.text(sheet, x, y - 1, tool, layout.MONO_BOLD, 6, room=cell_width - 5)
        layout.text(sheet, x, y - 8, database, layout.MONO, 6, layout.MUTED, room=cell_width - 5)


def _page(sheet, data, lede):
    return layout.start_page(sheet, data, '02', 'Organism' if lede else 'Organism (continued)', lede)


def _tree_pages(sheet, data, lede, rows, runs, cells, largest):
    cell_width = min(CELL, (layout.WIDTH - TREE_MIN) / len(runs)) if runs else 0
    left = layout.RIGHT - cell_width * len(runs)
    step = min(STEP, (left - layout.LEFT - 120) / max(len(chain) for chain in rows))
    index = 0
    while True:
        y = _page(sheet, data, lede) - 6
        lede = None
        layout.label(sheet, layout.LEFT, y, 'Taxon, its rank and taxon id')
        _matrix_head(sheet, y, runs, left, cell_width)
        y -= 14
        layout.rule(sheet, layout.LEFT, y, layout.RIGHT, layout.INK, 0.6)
        first = y
        while index < len(rows) and y - ROW >= layout.BOTTOM:
            chain = rows[index]
            _connectors(sheet, chain, y, step)
            _tree_line(sheet, chain, y, step, left)
            for column, run in enumerate(runs):
                assigned = cells.get((run, chain[-1]['taxon_id']))
                if assigned:
                    _cell(sheet, left + column * cell_width, y - ROW + 3.5, cell_width, assigned, largest[run])
            y -= ROW
            layout.rule(sheet, layout.LEFT, y, layout.RIGHT, layout.RULE, 0.3)
            index += 1
        for column in range(len(runs) + 1):
            x = left + column * cell_width
            sheet.setStrokeColor(layout.RULE)
            sheet.setLineWidth(0.3)
            sheet.line(x, y, x, first + 14)
        if index == len(rows):
            return y
        layout.end_page(sheet)


def _legend(sheet, y, markers):
    y = layout.paragraph(sheet, layout.LEFT, y, CAPTION, layout.WIDTH, layout.SANS, 7, layout.MUTED) - 4
    x = layout.LEFT
    entries = [(marker, MARKER_MEANING[marker]) for marker in MARKER_WORD if marker in markers]
    for marker, meaning in entries + [(None, DOT_MEANING)]:
        room = layout.width(meaning, layout.SANS, 7) + (_pills_width([marker]) if marker else 2 * DOT + 4) + 8
        if x > layout.LEFT and x + room > layout.RIGHT:
            x, y = layout.LEFT, y - 12
        if marker:
            x = _marker_pills(sheet, x, y, [marker])
        else:
            _dot(sheet, x + DOT, y + 2.5, 1)
            x += 2 * DOT + 4
        layout.text(sheet, x, y, meaning, layout.SANS, 7, layout.MUTED)
        x += layout.width(meaning, layout.SANS, 7) + 14
    return y - 8


def _stray_rows(assignments, nodes):
    return [[row['name'], str(row['taxon_id']), row['tool'], row['database'] or '-', _number_words(row)]
            for row in assignments if row['taxon_id'] not in nodes]


def _stray_pages(sheet, data, y, rows):
    index = 0
    while True:
        layout.text(sheet, layout.LEFT, y, STRAY_HEADING, layout.SANS_BOLD, 8.5)
        y, index = layout.table(sheet, y - 14, STRAY_COLUMNS, rows, index)
        if index == len(rows):
            return
        layout.end_page(sheet)
        y = _page(sheet, data, None)


def draw(sheet, data):
    organism = data['organism']
    nodes, roots = _build_tree(organism['candidates'], organism['agreed_taxon_id'])
    lede = _lede(organism, nodes)
    rows = _rows(nodes, roots)
    runs, cells, largest = _runs(organism['assignments'])
    stray = _stray_rows(organism['assignments'], nodes)
    if rows:
        y = _tree_pages(sheet, data, lede, rows, runs, cells, largest)
        if y - FOOTER < layout.BOTTOM:
            layout.end_page(sheet)
            y = _page(sheet, data, None)
        else:
            y -= 12
        y = _legend(sheet, y, {marker for node in nodes.values() for marker in node['markers']})
    else:
        y = _page(sheet, data, lede)
    if stray:
        _stray_pages(sheet, data, y - 10, stray)
    elif not rows:
        layout.text(sheet, layout.LEFT, y, 'No classifier assigned the sequence to a taxon.', layout.SANS, 8.5,
                    layout.MUTED)
    layout.end_page(sheet)
