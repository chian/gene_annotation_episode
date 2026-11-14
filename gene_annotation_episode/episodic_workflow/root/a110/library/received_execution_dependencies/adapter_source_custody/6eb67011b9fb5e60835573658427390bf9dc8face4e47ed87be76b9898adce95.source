"""Retained FastQC 0.12.1 tables, categories and source locations.

No graph reconstruction, acquisition, or numerical component calculation.
The private report builder is also used by the other native text/JSON readers.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import io
import math
import re
import zipfile
import zlib

from .bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, checked_bytes, validate_contract, validate_native_document,
)
from .bvbrc_fastqutils_identity import artifact_ref, native_ref, population_ref, requirement_ref
from .bvbrc_fastqutils_metric_specs import metric_spec

_MODULES = (
    ('Basic Statistics', 'basic_statistics'),
    ('Per base sequence quality', 'per_base_quality'),
    ('Per tile sequence quality', 'per_tile_quality'),
    ('Per sequence quality scores', 'per_sequence_quality'),
    ('Per base sequence content', 'per_base_content'),
    ('Per sequence GC content', 'per_sequence_gc'),
    ('Per base N content', 'per_base_n'),
    ('Sequence Length Distribution', 'length_distribution'),
    ('Sequence Duplication Levels', 'duplication'),
    ('Overrepresented sequences', 'overrepresented'),
    ('Adapter Content', 'adapter_content'),
    ('Kmer Content', 'kmer_content'),
)
_MODULE_MAP = {name: ('fastqc_' + key, slot) for slot, (name, key) in enumerate(_MODULES)}
_HEADERS = {
    'fastqc_basic_statistics': ['Measure', 'Value'],
    'fastqc_per_base_quality': ['Base', 'Mean', 'Median', 'Lower Quartile', 'Upper Quartile', '10th Percentile', '90th Percentile'],
    'fastqc_per_tile_quality': ['Tile', 'Base', 'Mean'],
    'fastqc_per_sequence_quality': ['Quality', 'Count'],
    'fastqc_per_base_content': ['Base', 'G', 'A', 'T', 'C'],
    'fastqc_per_sequence_gc': ['GC Content', 'Count'],
    'fastqc_per_base_n': ['Base', 'N-Count'],
    'fastqc_length_distribution': ['Length', 'Count'],
    'fastqc_duplication': ['Duplication Level', 'Percentage of total'],
    'fastqc_overrepresented': ['Sequence', 'Count', 'Percentage', 'Possible Source'],
    'fastqc_kmer_content': ['Sequence', 'Count', 'PValue', 'Obs/Exp Max', 'Max Obs/Exp Position'],
}
_NONE = {'kind': 'none', 'label': None, 'lower': None, 'upper': None}
_UNKNOWN_ENCODING = {'basis': 'unknown', 'encoding': 'unknown', 'metadata_id': None,
                     'evidence': None, 'declaration': None, 'native_locator': None}


def _axis(kind, label=None, lower=None, upper=None):
    return {'kind': kind, 'label': label, 'lower': lower, 'upper': upper}


def _bin(token, kind='base_closed_1', label=None):
    match = re.fullmatch(r'([0-9]+)(?:-([0-9]+))?', token)
    if not match:
        raise ValueError('native_bin')
    lower = int(match[1]); upper = int(match[2] or match[1])
    if lower > upper or (kind in ('base_closed_1', 'tile_base_closed_1') and lower < 1):
        raise ValueError('native_bin')
    return _axis(kind, token if label is None else label, lower, upper)


def _number(token, domain):
    if token is None or token.strip() in ('', 'N/A'):
        return None, 'missing', 'missing_requested_value'
    if not re.fullmatch(r'[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|[-+]?(?:NaN|Infinity)', token.strip()):
        return None, 'malformed', 'malformed_native'
    try:
        value = Decimal(token.strip())
    except (InvalidOperation, ValueError):
        return None, 'malformed', 'malformed_native'
    if not value.is_finite():
        return None, 'undefined', 'nonfinite_native'
    if domain in ('nonnegative_integer', 'integer_0_100'):
        if value != value.to_integral_value() or value < 0 or (domain == 'integer_0_100' and value > 100):
            return None, 'malformed', 'malformed_native'
        # Native Java longs/Counters cannot represent arbitrarily large counts.
        if value > 9223372036854775807:
            return None, 'malformed', 'malformed_native'
        return int(value), 'available', None
    number = float(value)
    if not math.isfinite(number):
        return None, 'undefined', 'nonfinite_native'
    if (domain == 'nonnegative_number' and number < 0) or (domain == 'number_0_1' and not 0 <= number <= 1):
        return None, 'malformed', 'malformed_native'
    return number, 'available', None


class _Report:
    """Build the closed native-document port; no scientific calculation."""
    def __init__(self, raw, context, expected, producer, compression='none'):
        self.context = validate_contract('ParseContext', context)
        checked_bytes(raw, content=self.context['content'])
        if self.context['declared_format'] != expected:
            raise FastqUtilsContractError('shape_invalid', '/declared_format')
        c = self.context; binding = c['content']; self.ref = artifact_ref(c)
        self.doc = {
            'schema_version': 'fastqutils_native_v2', 'analysis_id': c['analysis_id'],
            'document_id': c['document_id'], 'parse_scope': 'complete',
            'artifact': {'id': self.ref, 'source_ref': binding['source_ref'],
                'content_ref': binding['artifact_ref'], 'task_ref': c['task_ref'],
                'sha256': binding['sha256'], 'byte_count': binding['byte_count'],
                'native_name': c['native_name'], 'declared_format': expected, 'actual_format': expected,
                'compression': compression, 'transfer_scope': c['transfer_scope'],
                'producer_name': producer, 'producer_version': c['producer_version'],
                'identity': c['identity'], 'document_id': c['document_id'], 'content_binding': deepcopy(binding)},
            **{key: [] for key in ('cells', 'categories', 'raw_blocks', 'sequence_records', 'alignment_records',
                'diagnostics', 'sections', 'labels', 'populations', 'native_lineage', 'alignment_headers',
                'reference_dictionary', 'requirements')},
        }
        if c['transfer_scope'] == 'partial':
            self.doc['parse_scope'] = 'partial'
            self.issue('partial_transfer', required='complete_native_bytes')

    def loc(self, section, field, *, row=None, start=None, end=None, member=None):
        return {'member': member, 'block': section['key'], 'block_ordinal': section['ordinal'],
                'row_ordinal': row, 'field': field, 'byte_start': start, 'byte_end': end}

    def section(self, key, *, member=None, start=None, end=None, state='complete', ordinal=None):
        if ordinal is None:
            ordinal = sum(s['key'] == key for s in self.doc['sections'])
        section = {'key': key, 'ordinal': ordinal, 'state': state, 'cell_refs': [], 'category_refs': [],
                   'label_refs': [], 'raw_block_ordinals': []}
        section['locator'] = self.loc(section, 'section', member=member, start=start, end=end)
        self.doc['sections'].append(section)
        return section

    def raw(self, section, *, name, kind='unsupported_section', state='unsupported', fields=(), locator=None):
        section['raw_block_ordinals'].append(len(self.doc['raw_blocks']))
        self.doc['raw_blocks'].append({'artifact_ref': self.ref, 'locator': deepcopy(locator or section['locator']),
            'kind': kind, 'native_name': name, 'parse_status': state, 'field_names': list(fields)})

    def issue(self, code, *, affected=(), locator=None, required=None, state='unresolved'):
        self.doc['diagnostics'].append({'code': code, 'source_refs': [self.doc['artifact']['source_ref']],
            'locator': None if locator is None else str(locator), 'affected_refs': list(affected)})
        if required:
            scope = '/documents/' + self.context['document_id'] + '/requirements/' + str(len(self.doc['requirements']))
            self.doc['requirements'].append({'id': requirement_ref(self.context['analysis_id'], scope, code),
                'code': code, 'affected_refs': list(affected), 'required_data': required, 'state': state,
                'source_refs': [self.doc['artifact']['source_ref']]})

    def partial(self, section=None, code='malformed_native', required='complete_native_bytes'):
        if self.doc['parse_scope'] == 'complete':
            self.doc['parse_scope'] = 'partial'
        if section and section['state'] == 'complete':
            section['state'] = 'partial'
        self.issue(code, locator=section['locator'] if section else None, required=required)

    def label(self, section, kind, value, locator=None):
        row = {'id': native_ref('label', self.context, len(self.doc['labels'])), 'artifact_ref': self.ref,
               'locator': deepcopy(locator or section['locator']), 'kind': kind, 'value': value,
               'section_key': section['key'], 'section_ordinal': section['ordinal']}
        self.doc['labels'].append(row); section['label_refs'].append(row['id'])
        return row

    def version(self, section, reported, expected, locator=None):
        if reported is not None:
            self.label(section, 'producer_version', reported, locator)
        if reported is None:
            self.issue('producer_version_unproven', required='native_version')
        if (reported is not None and reported != expected) or (
                self.context['producer_version'] is not None and self.context['producer_version'] != expected):
            self.partial(section, 'unsupported_version', 'supported_parser')
            return False
        return True

    def population(self, section, key, ordinal, *, kind='native_report_population', estimator=False, scope=None):
        scope = scope or self.context['transfer_scope']
        if section['state'] in ('partial', 'malformed') and scope == 'complete':
            scope = 'partial'
        row = {'id': population_ref(self.context, key, ordinal), 'association_ref': None, 'kind': kind,
               'scope': scope, 'representation': 'native_estimator' if estimator else 'native_report',
               'member_artifact_refs': [self.ref], 'member_record_refs': [], 'parent_population_refs': [],
               'disjoint_from_refs': [], 'pair_key_rule': None, 'quality_encoding': 'unknown',
               'encoding_evidence_refs': [], 'document_ids': [self.context['document_id']],
               'population_key': key, 'population_ordinal': ordinal, 'section_key': section['key'],
               'section_ordinal': section['ordinal'], 'encoding_basis': deepcopy(_UNKNOWN_ENCODING)}
        self.doc['populations'].append(row)
        return row

    def cell(self, section, metric, token, population=None, *, axis=None, locator=None, unit=None, codes=(), force_state=None):
        spec = metric_spec(metric)
        value, state, code = _number(token, spec['value_domain'])
        diagnostics = list(codes)
        if code:
            diagnostics.append(code)
        if force_state and state == 'available':
            state = force_state
            if state not in ('available', 'partial'):
                value = None
        if state == 'available' and population and population['scope'] == 'partial':
            state = 'partial'
        row = {'id': native_ref('cell', self.context, len(self.doc['cells'])), 'artifact_ref': self.ref,
            'locator': deepcopy(locator or section['locator']), 'metric': metric, 'axis': deepcopy(axis or _NONE),
            'population_ref': population['id'] if population else None, 'association_ref': None,
            'state': state, 'value': value, 'native_token': token, 'unit': unit or spec['units'][0],
            'meaning': spec['meaning'], 'precision': spec['precision'], 'diagnostic_codes': diagnostics,
            'section_key': section['key'], 'section_ordinal': section['ordinal']}
        self.doc['cells'].append(row); section['cell_refs'].append(row['id'])
        if state == 'malformed' and self.doc['parse_scope'] == 'complete':
            self.doc['parse_scope'] = 'partial'
        if code:
            self.issue(code, affected=[row['id']], locator=row['locator'], required='requested_measurement')
        return row

    def category(self, section, name, token):
        mapped = {'[OK]': 'pass', '[PASS]': 'pass', '[WARN]': 'warn', '[WARNING]': 'warn', '[FAIL]': 'fail'}
        value = mapped.get(token, token)
        row = {'id': native_ref('category', self.context, len(self.doc['categories'])), 'artifact_ref': self.ref,
               'locator': deepcopy(section['locator']), 'association_ref': None, 'native_label': name,
               'value': value if value in ('pass', 'warn', 'fail') else 'unrecognized',
               'native_token': token, 'section_key': section['key'], 'section_ordinal': section['ordinal']}
        self.doc['categories'].append(row); section['category_refs'].append(row['id'])

    def lineage(self, before, after, locators):
        row = {'id': native_ref('lineage', self.context, len(self.doc['native_lineage'])),
               'kind': 'native_report_before_after', 'before_population_ref': before['id'],
               'after_population_ref': after['id'], 'document_ids': [self.context['document_id']],
               'source_refs': [self.doc['artifact']['source_ref']], 'locators': deepcopy(locators),
               'scope': 'artifact_local', 'task_stage_ref': None}
        self.doc['native_lineage'].append(row)
        self.issue('native_report_local_lineage', affected=[row['id']])

    def text(self, raw, *, member=None):
        try:
            return raw.decode('utf-8', errors='strict')
        except UnicodeError:
            section = self.section('unsupported', member=member, start=0, end=len(raw), state='malformed')
            self.raw(section, name='invalid UTF-8', state='malformed')
            self.partial(section)
            return None

    def finish(self):
        if not self.doc['cells'] and not self.doc['categories'] and self.doc['parse_scope'] == 'partial':
            self.doc['parse_scope'] = 'malformed'
        validate_native_document(self.doc)
        return self.doc


def _table(report, section, population, headers, rows, *, compatible=True):
    key = section['key']
    expected = _HEADERS.get(key)
    valid_header = (headers == expected if expected else headers and headers[0] == 'Position' and len(headers) > 1)
    if not rows and not headers and key not in ('fastqc_overrepresented', 'fastqc_kmer_content', 'fastqc_adapter_content'):
        report.partial(section, 'source_row_absent', 'requested_measurement')
        return
    if (rows or headers) and not valid_header:
        report.partial(section, 'native_header_conflict', 'supported_parser')
        return
    for ordinal, (fields, location) in enumerate(rows):
        if len(fields) != len(headers):
            report.partial(section)
            continue
        base = dict(location, block=key, block_ordinal=section['ordinal'], row_ordinal=ordinal)
        def emit(metric, token, field, axis=None, unit=None, codes=(), scalar=False):
            loc = dict(base, field=field, row_ordinal=None if scalar else ordinal)
            return report.cell(section, metric, token, population, axis=axis, locator=loc, unit=unit, codes=codes,
                               force_state=None if compatible else 'incompatible')
        try:
            if key == 'fastqc_basic_statistics':
                field, value = fields
                basic = {'Total Sequences': 'fastqc_total_sequences',
                         'Sequences flagged as poor quality': 'fastqc_flagged_sequences', '%GC': 'fastqc_gc_percent'}
                if field in basic:
                    codes = ('truncated_native_display',) if field == '%GC' else ()
                    emit(basic[field], value, field, scalar=True, codes=codes)
                elif field == 'Total Bases':
                    match = re.fullmatch(r'(.+?)\s+(bp|kbp|Mbp|Gbp)', value)
                    if not match:
                        report.partial(section); continue
                    cell = emit('fastqc_total_bases_display', match[1], field, unit=match[2], scalar=True,
                                codes=('truncated_native_display',))
                    cell['native_token'] = value
                elif field == 'Sequence length':
                    axis = _bin(value, 'length_closed')
                    for metric, number in [('fastqc_min_length', axis['lower']), ('fastqc_max_length', axis['upper'])]:
                        cell = emit(metric, str(number), field, scalar=True); cell['native_token'] = value
                else:
                    kind = {'Filename': 'filename', 'Encoding': 'encoding_inference'}.get(field, 'native_label')
                    report.label(section, kind, value, dict(base, field=field, row_ordinal=None))
            elif key == 'fastqc_per_base_quality':
                axis = _bin(fields[0])
                for i, suffix in enumerate(('mean', 'median', 'lower_quartile', 'upper_quartile', 'p10', 'p90'), 1):
                    emit('fastqc_base_quality_' + suffix, fields[i], headers[i], axis)
            elif key == 'fastqc_per_tile_quality':
                if not re.fullmatch(r'\d+', fields[0]): raise ValueError('tile')
                emit('fastqc_tile_quality_deviation', fields[2], 'Mean', _bin(fields[1], 'tile_base_closed_1', fields[0]))
            elif key == 'fastqc_per_sequence_quality':
                axis = _bin(fields[0], 'quality_score')
                emit('fastqc_sequence_quality_count', fields[1], 'Count', axis)
            elif key == 'fastqc_per_base_content':
                for i in range(1, 5):
                    emit('fastqc_base_content_percent', fields[i], headers[i], _bin(fields[0], label=headers[i]))
            elif key == 'fastqc_per_sequence_gc':
                axis = _bin(fields[0], 'native_label')
                if axis['upper'] > 100: raise ValueError('GC')
                emit('fastqc_sequence_gc_smoothed_count', fields[1], 'Count', axis, codes=('native_estimator',))
            elif key == 'fastqc_per_base_n':
                emit('fastqc_n_percent', fields[1], 'N-Count', _bin(fields[0]))
            elif key == 'fastqc_length_distribution':
                emit('fastqc_length_bin_count', fields[1], 'Count', _bin(fields[0], 'length_closed'))
            elif key == 'fastqc_duplication':
                emit('fastqc_duplication_bin_percent', fields[1], headers[1], _axis('duplication_bin', fields[0]),
                     codes=('native_estimator',))
            elif key == 'fastqc_overrepresented':
                axis = _axis('sequence', fields[0])
                emit('fastqc_overrepresented_count', fields[1], 'Count', axis)
                emit('fastqc_overrepresented_percent', fields[2], 'Percentage', axis)
                report.label(section, 'possible_source', fields[3], dict(base, field='Possible Source'))
            elif key == 'fastqc_adapter_content':
                for i in range(1, len(headers)):
                    emit('fastqc_adapter_percent', fields[i], headers[i], _bin(fields[0], label=headers[i]))
                    report.label(section, 'adapter', headers[i], dict(base, field=headers[i]))
            elif key == 'fastqc_kmer_content':
                axis = _axis('sequence', fields[0])
                for i, metric in enumerate(('fastqc_kmer_scaled_count', 'fastqc_kmer_pvalue', 'fastqc_kmer_obs_exp_max'), 1):
                    emit(metric, fields[i], headers[i], axis, codes=('native_estimator',) if i < 3 else ())
                report.label(section, 'native_label', fields[4], dict(base, field='Max Obs/Exp Position'))
        except ValueError:
            report.partial(section)


def _data(report, raw, member=None):
    text = report.text(raw, member=member)
    if text is None: return
    lines = text.splitlines(keepends=True)
    offsets = []; offset = 0
    for line in lines:
        offsets.append(offset); offset += len(line.encode('utf-8'))
    version_section = report.section('unsupported', member=member, start=0, end=offsets[1] if len(lines) > 1 else len(raw))
    version = re.fullmatch(r'##FastQC\t([^\r\n]+)[\r\n]*', lines[0]) if lines else None
    report.raw(version_section, name='FastQC header', kind='header', state='complete' if version else 'malformed')
    compatible = report.version(version_section, version[1] if version else None, '0.12.1')
    if not version:
        report.partial(version_section, 'native_header_conflict', 'supported_parser')
    i = 1 if version else 0
    while i < len(lines):
        text_line = lines[i].rstrip('\r\n')
        if not text_line.startswith('>>') or text_line == '>>END_MODULE':
            if text_line:
                s = report.section('unsupported', member=member, start=offsets[i], end=offsets[i] + len(lines[i].encode('utf-8')),
                                   state='unsupported')
                report.raw(s, name='unrecognized FastQC text')
                report.partial(s, 'unsupported_report_section', 'supported_parser')
            i += 1; continue
        name, separator, status = text_line[2:].partition('\t')
        end = i + 1
        while end < len(lines) and not lines[end].startswith('>>'): end += 1
        closed = end < len(lines) and lines[end].rstrip('\r\n') == '>>END_MODULE'
        stop = offsets[end] + len(lines[end].encode('utf-8')) if closed else offsets[end] if end < len(lines) else len(raw)
        key, slot = _MODULE_MAP.get(name, ('unsupported', None))
        section = report.section(key, member=member, start=offsets[i], end=stop,
                                 state='complete' if closed and slot is not None else 'partial' if slot is not None else 'unsupported')
        if separator and status and name:
            report.category(section, name, status)
        else:
            report.partial(section)
        if slot is None:
            report.raw(section, name=name or 'unnamed module')
            report.partial(section, 'unsupported_report_section', 'supported_parser')
        else:
            population = report.population(section, 'fastqc_module', slot + 12 * section['ordinal'],
                kind='native_qc_population', estimator=slot in (2, 5, 8, 9, 11))
            headers = []; rows = []
            for j in range(i + 1, end):
                line = lines[j].rstrip('\r\n')
                location = report.loc(section, 'row', member=member, start=offsets[j], end=offsets[j] + len(lines[j].encode('utf-8')))
                if line.startswith('#Total Deduplicated Percentage\t') and key == 'fastqc_duplication':
                    report.cell(section, 'fastqc_total_deduplicated_percent', line.split('\t', 1)[1], population,
                        locator=dict(location, field='Total Deduplicated Percentage'), codes=('native_estimator',),
                        force_state=None if compatible else 'incompatible')
                elif line.startswith('#'):
                    if headers:
                        report.partial(section, 'native_header_conflict', 'supported_parser')
                    headers = line[1:].split('\t')
                elif line:
                    rows.append((line.split('\t'), location))
            report.raw(section, name=name, kind='table', state=section['state'], fields=headers)
            _table(report, section, population, headers, rows, compatible=compatible)
            if not closed: report.partial(section)
            if section['state'] == 'partial' and population['scope'] == 'complete': population['scope'] = 'partial'
        i = end + 1 if closed else end


class _HTMLModules(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text = text; self.modules = []; self.current = None; self.depth = 0
        self.h2 = False; self.cell = None; self.row = None; self.parts = []
        self.line_offsets = [0]
        for match in re.finditer('\n', text): self.line_offsets.append(match.end())
        self.closed_html = False

    def byte_position(self):
        line, column = self.getpos()
        return len(self.text[:self.line_offsets[line - 1] + column].encode('utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.current: self.depth += 1
            elif 'module' in attrs.get('class', '').split():
                self.current = {'name': '', 'status': None, 'headers': [], 'rows': [], 'start': self.byte_position(), 'end': None, 'text': []}
                self.depth = 1
        if not self.current: return
        if tag == 'h2': self.h2 = True
        if tag == 'img' and self.h2: self.current['status'] = attrs.get('alt')
        if tag == 'tr': self.row = []; self.row_start = self.byte_position(); self.header_row = False
        if tag in ('td', 'th') and self.row is not None:
            self.cell = []; self.header_row = self.header_row or tag == 'th'

    def handle_endtag(self, tag):
        if tag == 'html': self.closed_html = True
        if not self.current: return
        if tag == 'h2': self.h2 = False
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell)); self.cell = None
        if tag == 'tr' and self.row is not None:
            if self.header_row: self.current['headers'] = self.row
            else: self.current['rows'].append((self.row, self.row_start, self.byte_position() + len('</tr>')))
            self.row = None
        if tag == 'div':
            self.depth -= 1
            if self.depth == 0:
                self.current['end'] = self.byte_position() + len('</div>')
                self.modules.append(self.current); self.current = None

    def handle_data(self, value):
        self.parts.append(value)
        if self.current:
            self.current['text'].append(value)
            if self.h2: self.current['name'] += value
            if self.cell is not None: self.cell.append(value)


def _html(report, raw, member=None):
    text = report.text(raw, member=member)
    if text is None: return
    reader = _HTMLModules(text)
    try:
        reader.feed(text); reader.close()
    except (ValueError, AssertionError):
        report.partial()
    if reader.current:
        reader.modules.append(reader.current)
    version_section = report.section('unsupported', member=member, start=0, end=len(raw))
    plain = ''.join(reader.parts)
    version = re.search(r'Produced by\s+FastQC\s+\(version\s+([^\)]+)\)', plain)
    report.raw(version_section, name='FastQC HTML document', kind='header', state='complete' if reader.closed_html else 'partial')
    compatible = report.version(version_section, version[1] if version else None, '0.12.1')
    if not reader.closed_html or not reader.modules:
        report.partial(version_section)
    for module in reader.modules:
        name = module['name'].strip(); key, slot = _MODULE_MAP.get(name, ('unsupported', None))
        section = report.section(key, member=member, start=module['start'], end=module['end'],
                                 state='complete' if module['end'] is not None else 'partial')
        if module['status'] and name: report.category(section, name, module['status'])
        else: report.partial(section)
        if slot is None:
            report.raw(section, name=name or 'unnamed module'); report.partial(section, 'unsupported_report_section', 'supported_parser'); continue
        graph_only = slot not in (0, 9, 11)
        population = report.population(section, 'fastqc_module', slot + 12 * section['ordinal'], kind='native_qc_population',
            estimator=slot in (2, 5, 8, 9, 11), scope='unknown' if graph_only else None)
        report.raw(section, name=name, kind='unsupported_section' if graph_only else 'table',
                   state='unsupported' if graph_only else section['state'], fields=module['headers'])
        if graph_only:
            report.partial(section, 'not_retained_by_service', 'full_fastqc_data')
            continue
        rows = [(values, report.loc(section, 'row', member=member, start=start, end=end))
                for values, start, end in module['rows']]
        _table(report, section, population, module['headers'], rows, compatible=compatible)
        if not rows and slot == 0: report.partial(section, 'source_row_absent', 'requested_measurement')
        if not rows and slot in (9, 11):
            empty_message = 'No overrepresented sequences' if slot == 9 else 'No overrepresented Kmers'
            if empty_message not in ''.join(module['text']):
                report.partial(section, 'source_row_absent', 'requested_measurement')


def parse_fastqc_data(raw: bytes, *, context: dict) -> dict:
    report = _Report(raw, context, 'fastqc_data_0_12_1', 'FastQC')
    _data(report, raw)
    return report.finish()


def parse_fastqc_html(raw: bytes, *, context: dict) -> dict:
    report = _Report(raw, context, 'fastqc_html_0_12_1', 'FastQC')
    _html(report, raw)
    return report.finish()


def parse_fastqc_zip(raw: bytes, *, context: dict) -> dict:
    report = _Report(raw, context, 'fastqc_zip_0_12_1', 'FastQC', 'zip')
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, ValueError):
        section = report.section('unsupported', start=0, end=len(raw), state='malformed')
        report.raw(section, name='invalid ZIP archive', state='malformed'); report.partial(section)
        return report.finish()
    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        data_parents = {name.rsplit('/', 1)[0] if '/' in name else '' for name in names if name.endswith('fastqc_data.txt')}
        parsed = 0
        for info in infos:
            name = info.filename
            if info.is_dir(): continue
            invalid_path = name.startswith(('/', '\\')) or '\\' in name or any(part in ('.', '..', '') for part in name.split('/')) or bool(re.match(r'^[A-Za-z]:', name))
            duplicate = names.count(name) > 1
            if invalid_path or duplicate:
                section = report.section('unsupported', member=name, state='malformed')
                report.raw(section, name=name, state='malformed')
                report.partial(section, 'artifact_collision' if duplicate else 'malformed_native', 'complete_native_bytes')
                continue
            try:
                body = archive.read(info)
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, OSError, ValueError, zlib.error):
                section = report.section('unsupported', member=name, state='malformed')
                report.raw(section, name=name, state='malformed'); report.partial(section)
                continue
            leaf = name.rsplit('/', 1)[-1]; parent = name.rsplit('/', 1)[0] if '/' in name else ''
            if leaf == 'fastqc_data.txt':
                _data(report, body, name); parsed += 1
            elif leaf == 'fastqc_report.html' and parent not in data_parents:
                _html(report, body, name); parsed += 1
            else:
                section = report.section('unsupported', member=name, start=0, end=len(body), state='unsupported')
                report.raw(section, name=name)
        if not parsed:
            report.partial(None, 'source_row_absent', 'full_fastqc_data')
    return report.finish()
