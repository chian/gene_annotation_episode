"""Read the pinned SAMStat 2.2.3 literal HTML payload without executing scripts.

The report's literal observations and producer limitations are retained.  No
source acquisition, rendering, record reconstruction or scoring happens here.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import math
import re

from .bvbrc_fastqutils_contracts import FastqUtilsContractError, validate_contract
from .bvbrc_fastqutils_fastqc_reader import _Report, _axis

_FORMAT = 'samstat_html_2_2_3'
_BINS = ('MAPQ_gt_30', 'MAPQ_lt_30', 'MAPQ_lt_10', 'Unmapped')
_LABELS = ('MAPQ gt 30', 'MAPQ lt 30', 'MAPQ lt 10', 'Unmapped')
_POP_KEYS = ('samstat_mapq_ge30', 'samstat_mapq_10_29', 'samstat_mapq_0_9', 'samstat_unmapped')
_SERIES = re.compile(
    r'(?P<base>(?:len|ins|del)_R[12]|(?:bc|bq)_R[12](?:_end|_norm)?|mis_R[12]|bq_norm_R[12])'
    r'_(?P<body>.+)\Z')
_NUMBER = re.compile(r'[-+]?(?:(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|nan|NaN|Infinity)')
_IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')


@dataclass
class _Token:
    kind: str
    value: str
    start: int
    end: int


@dataclass
class _Node:
    kind: str
    value: object
    start: int
    end: int
    complete: bool = True


def _lex(text, offset):
    """Finite tokens only; quoted/commented executable text stays inert."""
    result = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text.startswith('//', i):
            stop = text.find('\n', i + 2)
            i = len(text) if stop < 0 else stop
            continue
        if text.startswith('/*', i):
            stop = text.find('*/', i + 2)
            if stop < 0:
                result.append(_Token('invalid', text[i:], offset + i, offset + len(text)))
                break
            i = stop + 2
            continue
        start = i
        if text[i] in '\"\'`':
            quote = text[i]
            i += 1
            pieces = []
            valid = quote != '`'
            while i < len(text) and text[i] != quote:
                char = text[i]
                if char == '\\':
                    i += 1
                    if i >= len(text):
                        valid = False
                        break
                    char = text[i]
                    escapes = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f',
                               '\\': '\\', '/': '/', '"': '"', "'": "'"}
                    if char in escapes:
                        pieces.append(escapes[char])
                    elif char in ('u', 'x'):
                        size = 4 if char == 'u' else 2
                        digits = text[i + 1:i + 1 + size]
                        if len(digits) != size or not re.fullmatch('[0-9a-fA-F]+', digits):
                            valid = False
                        else:
                            code = int(digits, 16)
                            if 0xD800 <= code <= 0xDFFF:
                                valid = False
                            else:
                                pieces.append(chr(code))
                            i += size
                    else:
                        valid = False
                else:
                    if char in '\r\n':
                        valid = False
                    pieces.append(char)
                i += 1
            if i < len(text) and text[i] == quote:
                i += 1
            else:
                valid = False
            result.append(_Token('string' if valid else 'invalid', ''.join(pieces), offset + start, offset + i))
            continue
        match = _NUMBER.match(text, i)
        if match and (match.end() == len(text) or not re.match(r'[A-Za-z0-9_$]', text[match.end()])):
            i = match.end()
            result.append(_Token('number', match[0], offset + start, offset + i))
            continue
        match = _IDENT.match(text, i)
        if match:
            i = match.end()
            result.append(_Token('identifier', match[0], offset + start, offset + i))
            continue
        i += 1
        result.append(_Token(text[start], text[start], offset + start, offset + i))
    return result


class _Literals:
    """Recognize literal arrays/objects/references, retaining partial prefixes."""
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def read(self, depth=0):
        if self.i >= len(self.tokens) or depth > 24:
            raise ValueError('incomplete literal')
        token = self.tokens[self.i]
        self.i += 1
        if token.kind in ('string', 'number', 'identifier'):
            return _Node(token.kind, token.value, token.start, token.end)
        if token.kind not in ('[', '{'):
            raise ValueError('not a literal')
        array = token.kind == '['
        close = ']' if array else '}'
        values = [] if array else {}
        node = _Node('array' if array else 'object', values, token.start, token.end, False)
        while self.i < len(self.tokens):
            current = self.tokens[self.i]
            if current.kind == close:
                self.i += 1
                node.end, node.complete = current.end, True
                return node
            try:
                if array:
                    child = self.read(depth + 1)
                    values.append(child)
                else:
                    if current.kind not in ('identifier', 'string') or current.value in values:
                        return node
                    self.i += 1
                    if self.i >= len(self.tokens) or self.tokens[self.i].kind != ':':
                        return node
                    self.i += 1
                    child = self.read(depth + 1)
                    values[current.value] = child
                node.end = child.end
                if not child.complete:
                    return node
            except ValueError:
                return node
            if self.i < len(self.tokens) and self.tokens[self.i].kind == ',':
                self.i += 1
            elif self.i >= len(self.tokens) or self.tokens[self.i].kind != close:
                return node
        return node


def _declarations(script, text):
    tokens = _lex(text[script['body_start']:script['body_end']], script['body_start'])
    result = []
    i = 0
    depth = 0
    while i < len(tokens):
        t = tokens[i]
        if depth == 0 and t.kind == 'identifier' and (_series_info(t.value) is not None or t.value == 'mappingtableval'):
            if i + 1 < len(tokens) and tokens[i + 1].kind in ('=', '.', '['):
                # Native output never mutates a data variable. Preserve the
                # original assignment, but make its identity ambiguous.
                result.append({'name': t.value, 'node': _Node('invalid', None, t.start, t.end, False),
                               'start': t.start, 'end': t.end, 'script': script})
        if depth == 0 and t.kind == 'identifier' and t.value == 'var' and i + 2 < len(tokens):
            name, equals = tokens[i + 1:i + 3]
            if name.kind == 'identifier' and equals.kind == '=':
                known = _SERIES.fullmatch(name.value) is not None or name.value in ('mappingtableval', 'mappingtable_data', 'mapping_table_layout')
                if not known:
                    i += 3
                    continue
                parser = _Literals(tokens)
                parser.i = i + 3
                try:
                    node = parser.read()
                except ValueError:
                    node = _Node('invalid', None, equals.end, equals.end, False)
                # An expression after a literal (e.g. [1] + steal()) is never a literal payload.
                end = parser.i
                if node.complete and end < len(tokens):
                    next_token = tokens[end]
                    newline = '\n' in text[node.end:next_token.start]
                    if next_token.kind != ';' and not (newline and next_token.value in ('var', 'Plotly')):
                        node.complete = False
                result.append({'name': name.value, 'node': node, 'start': t.start,
                               'end': node.end, 'script': script})
                if not node.complete:
                    # Recover only at an actual lexed declaration on a new line;
                    # strings and comments cannot smuggle declarations into data.
                    j = i + 3
                    parentheses = 0
                    braces = 0
                    while j < len(tokens):
                        if tokens[j].kind == '(':
                            parentheses += 1
                        elif tokens[j].kind == ')':
                            parentheses = max(0, parentheses - 1)
                        elif tokens[j].kind == '{':
                            braces += 1
                        elif tokens[j].kind == '}':
                            braces = max(0, braces - 1)
                        if not parentheses and braces <= 1 and tokens[j].value == 'var' and text[text.rfind('\n', 0, tokens[j].start) + 1:tokens[j].start].strip() == '':
                            break
                        j += 1
                    i = j
                else:
                    i = max(i + 3, end)
                continue
        if t.kind in ('(', '[', '{'):
            depth += 1
        elif t.kind in (')', ']', '}'):
            depth = max(0, depth - 1)
        i += 1
    return result


class _HTML(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.lines = [0] + [m.end() for m in re.finditer('\n', text)]
        self.events = []
        self.script = None
        self.style = False
        self.heading = None
        self.closed = False

    def pos(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.pos()
        end = start + len(self.get_starttag_text())
        if tag == 'script':
            self.script = {'kind': 'script', 'start': start, 'body_start': end,
                           'body_end': len(self.text), 'end': len(self.text), 'closed': False}
        elif tag == 'style':
            self.style = True
        elif tag in ('h1', 'h2'):
            self.heading = {'kind': tag, 'start': start, 'end': None, 'text': ''}

    def handle_endtag(self, tag):
        end = self.pos() + len('</' + tag + '>')
        if tag == 'script' and self.script is not None:
            self.script.update(body_end=self.pos(), end=end, closed=True)
            self.events.append(self.script)
            self.script = None
        elif tag == 'style':
            self.style = False
        elif tag in ('h1', 'h2') and self.heading is not None:
            self.heading['end'] = end
            self.events.append(self.heading)
            self.heading = None
        elif tag == 'html':
            self.closed = True

    def handle_data(self, value):
        if self.script is not None or self.style:
            return
        if self.heading is not None:
            self.heading['text'] += value
        else:
            self.events.append({'kind': 'text', 'text': value, 'start': self.pos(), 'end': self.pos() + len(value)})

    def handle_entityref(self, name):
        self.handle_data('&' + name + ';')

    def handle_charref(self, name):
        self.handle_data('&#' + name + ';')


def _series_info(name):
    match = _SERIES.fullmatch(name)
    if not match:
        return None
    base, body = match['base'], match['body']
    family = base.split('_', 1)[0]
    mate = int(re.search(r'R([12])', base)[1])
    suffix = 'end' if '_end' in base else 'relative' if '_norm' in base else 'start'
    if family in ('len', 'ins', 'del'):
        group = body[1:] if body.startswith('_') else None
        symbol = None
    else:
        group, _, symbol = body.rpartition('_')
    if group not in _BINS:
        return None
    slot = _BINS.index(group)
    if family in ('bc', 'mis') and symbol not in ('A', 'C', 'G', 'T', 'N'):
        return None
    if family == 'bq' and symbol != str(slot * 42):
        return None
    key = {'len': 'samstat_length', 'ins': 'samstat_insertion', 'del': 'samstat_deletion',
           'mis': 'samstat_mismatch', 'bc': 'samstat_base_' + suffix,
           'bq': 'samstat_quality_' + suffix}[family]
    return {'base': base, 'family': family, 'mate': mate, 'slot': slot,
            'symbol': symbol, 'suffix': suffix, 'key': key}


def _scalar(node):
    return node.value if node and node.complete and node.kind in ('string', 'number', 'identifier') else None


def _member(node, *path):
    for key in path:
        if node is None or node.kind != 'object':
            return None
        node = node.value.get(key)
    return node


class _Legacy:
    def __init__(self, report, raw, text, reader, mode, prefix):
        self.r, self.raw, self.text = report, raw, text
        self.reader, self.mode, self.prefix = reader, mode, prefix
        self.populations = {}
        self.byte_offsets = [0]
        for char in text:
            self.byte_offsets.append(self.byte_offsets[-1] + len(char.encode('utf-8')))
        self.decls = [d for s in reader.events if s['kind'] == 'script' for d in _declarations(s, text)]
        self.counts = Counter(d['name'] for d in self.decls)
        self.unique = {d['name']: d for d in self.decls if self.counts[d['name']] == 1}

    def loc(self, section, block, field, start, end, row=None):
        return dict(self.r.loc(section, field, row=row, start=self.byte_offsets[start], end=self.byte_offsets[end]), block=block)

    def section(self, key, event, state='complete'):
        return self.r.section(key, start=self.byte_offsets[event['start']], end=self.byte_offsets[event['end']], state=state)

    def population(self, section, mate, slot=None):
        key = ('samstat_report_records' if self.mode == 'alignment' else 'samstat_report_sequences') if slot is None or self.mode == 'fastx' else _POP_KEYS[slot]
        identity = key, mate
        if identity not in self.populations:
            pop = self.r.population(section, key, mate, scope='partial' if self.prefix else 'unknown')
            self.populations[identity] = pop
        return self.populations[identity]

    def cell(self, section, metric, node, population, block, field, row=None, axis=None, codes=(), precision=None, multiplier=1):
        token = self.text[node.start:node.end]
        parsed = _scalar(node)
        code_list = list(codes)
        # _Report's ordinary numeric parser has JSON-like NaN spelling; retain
        # the native legacy spelling separately, never an IEEE NaN in storage.
        number_token = 'NaN' if parsed and re.fullmatch(r'[-+]?nan', str(parsed), re.I) else parsed
        cell = self.r.cell(section, metric, number_token, population, axis=axis,
            locator=self.loc(section, block, field, node.start, node.end, row), codes=code_list)
        cell['native_token'] = token
        if cell['state'] == 'partial':
            cell['state'] = 'available'
        if cell['value'] is not None:
            cell['value'] *= multiplier
        if precision:
            cell['precision'] = precision
        return cell

    def bad(self, section, code='malformed_native'):
        section['state'] = 'malformed'
        self.r.partial(section, code, 'complete_native_bytes' if code == 'malformed_native' else 'requested_measurement')

    def mapping(self, script, section):
        selected = [d for d in self.decls if d['script'] is script and d['name'] == 'mappingtableval']
        self.r.raw(section, name='mappingtableval', kind='table', state='complete', fields=('counts', 'fractions'))
        if len(selected) != 1 or self.counts['mappingtableval'] != 1:
            self.bad(section, 'selection_ambiguous')
            return
        node = selected[0]['node']
        if node.kind != 'array' or not node.value:
            self.bad(section)
            return
        labels = node.value[0]
        if labels.kind != 'array' or not labels.complete or [_scalar(n) for n in labels.value] != [*_LABELS, 'Total']:
            self.bad(section, 'native_header_conflict')
            return
        header = self.unique.get('mappingtable_data')
        if self.counts['mappingtable_data'] > 1:
            self.bad(section, 'selection_ambiguous')
            return
        if header and header['node'].complete:
            hnode = header['node']
            if hnode.kind != 'array' or len(hnode.value) != 1:
                self.bad(section, 'native_header_conflict')
                return
            obj = hnode.value[0]
            columns = _member(obj, 'header', 'values')
            actual = [[_scalar(n) for n in c.value] if c.kind == 'array' else None for c in columns.value] if columns and columns.kind == 'array' else None
            expected = [['<b>Mapping Quality</b>'], ['<b>Read 1</b>'], ['<b>Percentage</b>'], ['<b>Read 2</b>'], ['<b>Percentage</b>']] if actual and len(actual) == 5 else [['<b>Mapping Quality</b>'], ['<b>Sequences</b>'], ['<b>Percentage</b>']]
            if actual != expected or _scalar(_member(obj, 'cells', 'values')) != 'mappingtableval' or (node.complete and len(actual) != len(node.value)):
                self.bad(section, 'native_header_conflict')
                return
        elif not header:
            self.r.partial(section, 'source_row_absent', 'complete_native_bytes')
        if not node.complete or len(node.value) not in (3, 5):
            self.r.partial(section)
        for index, column in enumerate(node.value[1:], 1):
            if index > 4:
                self.bad(section)
                break
            if column.kind != 'array' or not column.complete or len(column.value) != 5:
                self.bad(section)
                continue
            mate = (index + 1) // 2
            pop = self.population(section, mate)
            native_cells = []
            for row, value in enumerate(column.value):
                if value.kind != 'number':
                    self.bad(section)
                    continue
                fraction = index % 2 == 0
                metric = 'samstat_reported_bin_fraction' if fraction else 'samstat_alignment_total_count' if row == 4 else 'samstat_alignment_bin_count'
                axis = _axis('none') if row == 4 else _axis('mapq', _LABELS[row], *[(30, 255), (10, 29), (0, 9)][row]) if row < 3 else _axis('native_label', 'Unmapped')
                codes = ['rounded_native_value'] if fraction else []
                if row == 0:
                    codes.append('samstat_mapq255_merged')
                if fraction and str(value.value).lower() in ('nan', '-nan', '+nan'):
                    count_column = node.value[index - 1]
                    if count_column.complete and count_column.kind == 'array' and len(count_column.value) == 5 and _scalar(count_column.value[-1]) == '0':
                        codes.append('zero_denominator')
                native_cells.append(self.cell(section, metric, value, pop, 'mappingtableval', 'mappingtableval[' + str(index) + ']', row, axis, codes))
            if index % 2 and len(native_cells) == 5 and all(c['value'] is not None for c in native_cells):
                if sum(c['value'] for c in native_cells[:4]) != native_cells[4]['value']:
                    self.bad(section, 'count_inconsistent')
                    for cell in native_cells:
                        cell['diagnostic_codes'].append('count_inconsistent')
        for n in labels.value:
            self.r.label(section, 'native_label', unescape(n.value), self.loc(section, 'mappingtableval', 'labels', n.start, n.end))

    def series(self, declaration, section, info):
        name, node = declaration['name'], declaration['node']
        self.r.raw(section, name=name, kind='record', state='complete' if node.complete else 'malformed',
                   fields=('x', 'y', 'error_y.array', 'name'), locator=self.loc(section, name, 'series', declaration['start'], declaration['end']))
        if self.counts[name] != 1:
            self.bad(section, 'selection_ambiguous')
            return
        if node.kind != 'object' or not node.complete:
            self.bad(section)
            return
        data_decl = self.unique.get(info['base'] + '_data')
        if not data_decl or data_decl['node'].kind != 'array' or not data_decl['node'].complete:
            self.bad(section, 'source_row_absent' if not data_decl else 'malformed_native')
            return
        refs = data_decl['node'].value
        if any(n.kind != 'identifier' or _series_info(n.value) is None or _series_info(n.value)['base'] != info['base'] for n in refs):
            self.bad(section, 'native_header_conflict')
            return
        names = [_scalar(n) for n in refs]
        if any(ref not in self.unique for ref in names):
            self.r.partial(section, 'source_row_absent', 'complete_native_bytes')
        if names.count(name) != 1:
            self.bad(section, 'selection_ambiguous')
            return
        layout_decl = self.unique.get(info['base'] + '_layout')
        layout = layout_decl['node'] if layout_decl else None
        if layout is not None and layout.complete:
            menus = _member(layout, 'updatemenus')
            if menus is not None:
                if menus.kind != 'array' or len(menus.value) != 1:
                    self.bad(section, 'native_header_conflict')
                    return
                buttons = _member(menus.value[0], 'buttons')
                if buttons is None or buttons.kind != 'array':
                    self.bad(section, 'native_header_conflict')
                    return
                for button in buttons.value:
                    args = _member(button, 'args')
                    label = _scalar(_member(button, 'label'))
                    if args is None or args.kind != 'array' or len(args.value) != 2 or _scalar(args.value[0]) != 'visible' or args.value[1].kind != 'array':
                        self.bad(section, 'native_header_conflict')
                        return
                    flags = [_scalar(v) for v in args.value[1].value]
                    if len(flags) != len(names) or any(v not in ('true', 'false') for v in flags):
                        self.bad(section, 'native_header_conflict')
                        return
                    selected_groups = {_LABELS[_series_info(n)['slot']] for n, flag in zip(names, flags) if flag == 'true'}
                    if selected_groups != {label}:
                        self.bad(section, 'native_header_conflict')
                        return
        expected_name = info['symbol'] if info['family'] in ('bc', 'mis') else _LABELS[info['slot']]
        label = _member(node, 'name')
        if _scalar(label) != expected_name:
            self.bad(section, 'native_header_conflict')
            return
        expected_type = 'bar' if info['family'] in ('bc', 'mis') else 'lines'
        if _scalar(_member(node, 'type')) != expected_type or (info['family'] == 'bq' and _scalar(_member(node, 'error_y', 'type')) != 'data'):
            self.bad(section, 'native_header_conflict')
            return
        self.r.label(section, 'native_label', expected_name, self.loc(section, name, 'name', label.start, label.end))
        xs, ys = _member(node, 'x'), _member(node, 'y')
        error = _member(node, 'error_y', 'array')
        arrays = [xs, ys] + ([error] if info['family'] == 'bq' else [])
        if any(a is None or a.kind != 'array' or not a.complete for a in arrays) or not xs.value or len({len(a.value) for a in arrays}) != 1:
            self.bad(section)
            return
        if any(n.kind not in ('string', 'number') for n in xs.value) or any(n.kind != 'number' for a in arrays[1:] for n in a.value):
            self.bad(section)
            return
        labels = [_scalar(n) for n in xs.value]
        clustered = info['family'] != 'len' and (labels[0] == '0' or any('-' in x for x in labels))
        if layout is not None and layout.complete and info['family'] != 'len' and clustered != (_scalar(_member(layout, 'xaxis', 'type')) == 'category'):
            self.bad(section, 'native_header_conflict')
            return
        if len(labels) != len(set(labels)):
            self.bad(section, 'selection_ambiguous')
            return
        if clustered:
            # The pinned cluster writer leaves its last incomplete cluster
            # label empty. Preserve the payload at its native row, with no
            # inferred interval. Other unrecognized coordinate text is invalid.
            named_labels = labels[:-1] if labels[-1] == '' else labels
            if not all(re.fullmatch(r'\d+(?:-\d+)?', x) for x in named_labels):
                self.bad(section)
                return
            order = [int(x.split('-')[0]) for x in named_labels]
            # Native singleton250 and range250-255 legitimately share a start.
            if any(a > b for a, b in zip(order, order[1:])):
                self.bad(section)
                return
        else:
            try:
                numbers = [float(x) for x in labels]
            except ValueError:
                self.bad(section)
                return
            if any(not math.isfinite(x) or x < 0 for x in numbers) or any(a >= b for a, b in zip(numbers, numbers[1:])):
                self.bad(section)
                return
            if info['family'] == 'len' and any(not n.is_integer() for n in numbers):
                self.bad(section)
                return
            if info['family'] != 'len' and (numbers != list(range(1, len(numbers) + 1)) or (info['suffix'] == 'relative' and len(numbers) > 100)):
                self.bad(section)
                return
        pop = self.population(section, info['mate'], info['slot'])
        family = info['family']
        metrics = []
        codes = ['samstat_mapq255_merged'] if info['slot'] == 0 and self.mode == 'alignment' else []
        if family == 'len':
            metrics = [('samstat_length_density', ys, 'y')]
            codes += ['native_estimator']
            if len(ys.value) == 1 and _scalar(ys.value[0]) == '1.000000':
                codes.append('native_fallback_value')
        elif family == 'bq':
            pair = ('samstat_legacy_mean_phred', 'samstat_legacy_phred_sem') if self.mode == 'alignment' else ('samstat_legacy_quality_index_mean', 'samstat_legacy_quality_index_sem')
            metrics = [(pair[0], ys, 'y'), (pair[1], error, 'error_y.array')]
            codes += ['rounded_native_value', 'samstat_quality_coverage_unproven']
            if self.mode == 'fastx':
                codes.append('samstat_fastx_quality_offset_defect')
        else:
            base = {'bc': 'samstat_base_' + str(info['symbol']), 'mis': 'samstat_mismatch_' + str(info['symbol']),
                    'ins': 'samstat_insertion_open', 'del': 'samstat_deletion_open'}[family]
            metrics = [(base + ('_rounded_bin_mean' if clustered else '_count'), ys, 'y')]
            if clustered:
                codes.append('rounded_native_value')
            if family in ('mis', 'ins', 'del'):
                codes.append('samstat_softclip_reconstruction_defect')
        for metric, values, field in metrics:
            for row, (label_text, value) in enumerate(zip(labels, values.value)):
                if clustered:
                    axis = _axis('native_label', unescape(label_text))
                elif family == 'len':
                    axis = _axis('length_closed', label_text, float(label_text), float(label_text))
                elif info['suffix'] == 'end':
                    axis = _axis('base_offset_from_end_0', label_text, int(label_text) - 1, int(label_text) - 1)
                elif info['suffix'] == 'relative':
                    axis = _axis('read_fraction_bin_0_100', label_text, (int(label_text) - 1) / 100, int(label_text) / 100)
                else:
                    axis = _axis('base_closed_1', label_text, int(label_text), int(label_text))
                row_codes = codes + (['missing_requested_value'] if clustered and label_text == '' else [])
                cell = self.cell(section, metric, value, pop, name, field, row, axis, row_codes)
                if clustered and label_text == '':
                    point = xs.value[row]
                    self.r.issue('missing_requested_value', affected=[cell['id']],
                        locator=self.loc(section, name, 'x', point.start, point.end, row), required='requested_measurement')

    def summary(self, event, section):
        value = event['text']
        total = re.fullmatch(r'\s*(\d+[KMG]?) - reads\s*(?:\(exact: (\d+)\))?\s*', value)
        if total:
            group = 2 if total[2] is not None else 1
            token = total[group]
            if token[-1:] in ('K', 'M', 'G'):
                self.bad(section)
                return
            start = event['start'] + total.start(group)
            node = _Node('number', token, start, start + len(token))
            metric = 'samstat_alignment_total_count' if self.mode == 'alignment' else 'samstat_sequence_total_count'
            self.cell(section, metric, node, self.population(section, 0), section['key'], 'report_total')
            self.r.label(section, 'native_label', total[1], self.loc(section, section['key'], 'total_display', event['start'] + total.start(1), event['start'] + total.end(1)))
        pair = re.fullmatch(r'\s*(\d+)([KMG]?) - (paired in sequencing|properly paired) \(([-+\w.]+)%\)\s*', value)
        if pair and self.mode == 'alignment':
            proper = pair[3] == 'properly paired'
            key = 'samstat_proper_pair_flag' if proper else 'samstat_paired_flag'
            pop = self.population(section, 0)
            start = event['start'] + pair.start(1)
            node = _Node('number', pair[1], start, event['start'] + pair.end(2))
            scale = {'': 1, 'K': 1000, 'M': 1000000, 'G': 1000000000}[pair[2]]
            self.cell(section, key + '_record_count_display', node, pop, 'pair_flags', pair[3],
                codes=('rounded_native_value',) if scale > 1 else (),
                precision='native_rounded' if scale > 1 else 'exact_for_retained_population', multiplier=scale)
            start = event['start'] + pair.start(4)
            self.cell(section, key + '_percent', _Node('number', pair[4], start, start + len(pair[4])), pop,
                'pair_flags', pair[3] + ' percent', codes=('rounded_native_value',))

    def link_populations(self):
        report_key = 'samstat_report_records' if self.mode == 'alignment' else 'samstat_report_sequences'
        for (key, mate), pop in self.populations.items():
            if mate and (report_key, 0) in self.populations:
                pop['parent_population_refs'].append(self.populations[report_key, 0]['id'])
            if key != report_key and (report_key, mate) in self.populations:
                pop['parent_population_refs'].append(self.populations[report_key, mate]['id'])
            for (other_key, other_mate), other in self.populations.items():
                if mate and other_mate and mate != other_mate:
                    pop['disjoint_from_refs'].append(other['id'])
                elif key in _POP_KEYS and other_key in _POP_KEYS and key != other_key and mate == other_mate:
                    pop['disjoint_from_refs'].append(other['id'])


def parse_samstat_html_2_2_3(raw: bytes, *, context: dict) -> dict:
    """Supplied HTML bytes + ParseContext -> validated complete NativeDocument."""
    context = validate_contract('ParseContext', context)
    if context['declared_format'] not in ('samstat_html', _FORMAT):
        raise FastqUtilsContractError('shape_invalid', '/declared_format')
    report = _Report(raw, context, context['declared_format'], 'SAMStat')
    report.doc['artifact']['actual_format'] = 'unknown'
    report.doc['artifact']['producer_version'] = None
    text = report.text(raw)
    if text is None:
        return report.finish()
    reader = _HTML(text)
    try:
        reader.feed(text)
        reader.close()
    except (ValueError, AssertionError, RecursionError):
        report.partial()
    if reader.script:
        reader.events.append(reader.script)
    if reader.heading:
        reader.heading['end'] = len(text)
        reader.events.append(reader.heading)
    reader.events.sort(key=lambda e: e['start'])
    headings = [unescape(e['text']).strip() for e in reader.events if e['kind'] == 'h2']
    mode = 'alignment' if 'Mapping statistics' in headings else 'fastx' if 'File statistics' in headings else None
    prefix = any(re.fullmatch(r'Warning: this is partial report based on the first \d+ reads only\.', h) for h in headings)
    parser = _Legacy(report, raw, text, reader, mode, prefix)
    head = report.section('samstat_header', start=0, end=len(raw))
    report.raw(head, name='SAMStat 2.2.3 HTML', kind='header', state='complete' if reader.closed else 'partial')
    versions = []
    for event in reader.events:
        if event['kind'] == 'text':
            match = re.fullmatch(r'\s*\(report produced by: SAMStat version ([^)]+)\)\s*', event['text'])
            if match:
                versions.append(match[1])
                report.label(head, 'producer_version', match[1], parser.loc(head, 'producer', 'version', event['start'] + match.start(1), event['start'] + match.end(1)))
        elif event['kind'] == 'h1':
            report.label(head, 'filename', unescape(event['text']), parser.loc(head, 'h1', 'input_label', event['start'], event['end']))
    if context['producer_version'] is not None:
        report.label(head, 'producer_version', context['producer_version'], report.loc(head, 'supplied_producer_version'))
    if versions != ['2.2.3'] or context['producer_version'] not in (None, '2.2.3') or mode is None or ('Mapping statistics' in headings and 'File statistics' in headings):
        report.doc['parse_scope'] = 'unsupported'
        report.issue('unsupported_version' if versions != ['2.2.3'] or context['producer_version'] not in (None, '2.2.3') else 'native_header_conflict', required='supported_parser')
        if versions and context['producer_version'] is not None and context['producer_version'] != versions[0]:
            report.issue('native_header_conflict', required='native_version')
        if not versions:
            report.issue('producer_version_unproven', required='native_version')
        report.raw(head, name='unsupported native HTML', state='unsupported')
        return report.finish()
    report.doc['artifact']['actual_format'] = _FORMAT
    report.doc['artifact']['producer_version'] = '2.2.3'
    report.issue('samstat_native_prefix' if prefix else 'samstat_input_scope_unproven')
    if not reader.closed:
        report.partial(head, 'partial_transfer', 'complete_native_bytes')
    current = head
    for event in reader.events:
        if event['kind'] == 'h2':
            heading = unescape(event['text']).strip()
            key = 'samstat_summary' if heading in ('Mapping statistics', 'File statistics') else 'samstat_notes'
            current = parser.section(key, event)
            report.label(current, 'native_label', heading)
        elif event['kind'] == 'text' and event['text'].strip():
            text_section = parser.section('samstat_pair_flags', event) if re.search(r' - (?:paired in sequencing|properly paired) ', event['text']) else current
            parser.summary(event, text_section)
            report.label(text_section, 'native_label', unescape(event['text']), parser.loc(text_section, text_section['key'], 'text', event['start'], event['end']))
        elif event['kind'] == 'script':
            declared = [d for d in parser.decls if d['script'] is event]
            if any(d['name'] == 'mappingtableval' for d in declared) and mode == 'alignment':
                section = parser.section('samstat_mapping', event)
                parser.mapping(event, section)
            else:
                sections = {}
                for d in declared:
                    info = _series_info(d['name'])
                    if info is None:
                        if _SERIES.fullmatch(d['name']) and not d['name'].endswith(('_data', '_layout')):
                            unsupported = parser.section('unsupported', event, 'unsupported')
                            report.raw(unsupported, name=d['name'])
                            report.partial(unsupported, 'unsupported_report_section', 'supported_parser')
                        continue
                    if info['base'] not in sections:
                        sections[info['base']] = parser.section(info['key'], event)
                    parser.series(d, sections[info['base']], info)
                section = next(iter(sections.values())) if sections else parser.section('unsupported', event, 'unsupported')
            report.raw(section, name='inert script and rendering instructions', locator=parser.loc(section, 'script', 'inert_bytes', event['start'], event['end']))
            if not event['closed']:
                report.partial(section)
    parser.link_populations()
    return report.finish()
