"""Read one retained Cutadapt 4.9 full text report inside Trim Galore.

The grammar is Cutadapt v4.9 ``report.full_report`` and its helpers. All
locations address the complete supplied artifact. This module appends native
measurements only: no acquisition, program execution, or score calculation.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from .bvbrc_fastqutils_contracts import FastqUtilsContractError, checked_bytes
from .bvbrc_fastqutils_fastqc_reader import _axis

_INTEGER = re.compile(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)\Z')
_HEADER = re.compile(r'This is cutadapt (\S+) with Python .+\Z')
_ADAPTER = re.compile(r"=== (?:(First read|Second read): )?Adapter (.*) ===\Z")
_POLY = re.compile(r'=== (Poly-A|R1 poly-A|R2 poly-A) trimmed ===\Z')
_FILTERS = ('that were too short', 'that were too long', 'with too many N',
            'with too many exp. errors', 'failed CASAVA filter',
            'discarded as trimmed', 'discarded as untrimmed')
_HISTOGRAMS = {
    'Overview of removed sequences': None,
    "Overview of removed sequences (5')": "5'",
    "Overview of removed sequences (3' or within)": "3' or within",
    "Overview of removed sequences at 5' end": "5'",
    "Overview of removed sequences at 3' end": "3'",
}
_TYPES = {"regular 5'": "5'", "regular 3'": "3'",
          "anchored 5'": "5'", "anchored 3'": "3'",
          "non-internal 5'": "5'", "non-internal 3'": "3'",
          'linked': 'linked', "variable 5'/3'": 'anywhere'}
_DECIMALS = {'cutadapt_reported_percent', 'cutadapt_adjacent_base_percent',
             'cutadapt_histogram_expected_count'}
_BASE_FIELDS = {
    'Total basepairs processed': ('cutadapt_processed_bases', 'cutadapt_input_bases'),
    'Quality-trimmed': ('cutadapt_quality_trimmed_bases', 'cutadapt_quality_removed'),
    'Poly-A-trimmed': ('cutadapt_poly_a_trimmed_bases', 'cutadapt_poly_a_removed'),
    'Total written (filtered)': ('cutadapt_written_bases', 'cutadapt_output_bases'),
}


def _coordinate(token):
    """Native nonnegative coordinates without unbounded decimal conversion."""
    if len(token) > 19 or re.fullmatch(r'[0-9]+', token) is None:
        return None
    value = int(token)
    return value if value <= 9223372036854775807 else None


@dataclass(frozen=True)
class _Line:
    text: str
    start: int
    end: int


class _Cutadapt:
    def __init__(self, report, lines, invocation):
        self.r, self.lines, self.invocation = report, lines, invocation
        self.input_population = None
        self.mode = None
        self.mode_conflict = False
        self.multiple_summaries = False

    def loc(self, section, line, field, row=None):
        return self.r.loc(section, field, row=row, start=line.start, end=line.end)

    def section(self, key, lines, *, name=None):
        section = self.r.section(key, start=lines[0].start, end=lines[-1].end)
        self.r.raw(section, name=name or lines[0].text or key, kind='table', state='complete')
        return section

    def population(self, section, key, *, parent=None):
        ordinal = 1 + max((p['population_ordinal'] for p in self.r.doc['populations']
                           if p['population_key'] == key), default=-1)
        population = self.r.population(section, key, ordinal)
        # A malformed sibling does not make this separately printed native
        # population incomplete. Local table failures qualify their own rows.
        population['scope'] = self.r.context['transfer_scope']
        if parent is not None:
            population['parent_population_refs'] = [parent['id']]
        return population

    def fail(self, section, code='malformed_native', *, populations=(), cells=(), required=None):
        required = required or ('supported_parser' if code == 'unsupported_report_section'
                                else 'requested_measurement')
        self.r.partial(section, code, required)
        refs = {p['id'] for p in populations}
        for pop in populations:
            pop['scope'] = 'partial'
        for cell in self.r.doc['cells']:
            if cell['population_ref'] in refs or any(cell is row for row in cells):
                if code not in cell['diagnostic_codes']:
                    cell['diagnostic_codes'].append(code)
                if cell['state'] == 'available':
                    cell['state'] = 'partial'
        affected = list(refs) + [row['id'] for row in cells]
        if affected:
            self.r.issue(code, affected=affected, required=required)

    def unknown(self, section, line):
        self.r.raw(section, name=line.text or 'unrecognized native line',
                   locator=self.loc(section, line, 'unsupported native line'))
        self.fail(section, 'unsupported_report_section')

    def emit(self, section, metric, token, population, line, *, field, axis=None,
             row=None, unit=None):
        native = token
        malformed = False
        if metric not in _DECIMALS and token not in (None, '', 'N/A'):
            malformed = _INTEGER.fullmatch(token) is None
            if not malformed:
                token = token.replace(',', '')
        codes = ('rounded_native_value',) if metric in _DECIMALS - {'cutadapt_histogram_expected_count'} else ()
        if metric == 'cutadapt_histogram_expected_count':
            codes = ('native_estimator',)
        cell = self.r.cell(section, metric, token, population, axis=axis,
            locator=self.loc(section, line, field, row), unit=unit, codes=codes,
            force_state='malformed' if malformed else None)
        cell['native_token'] = native
        if malformed and 'malformed_native' not in cell['diagnostic_codes']:
            cell['diagnostic_codes'].append('malformed_native')
            self.r.issue('malformed_native', affected=[cell['id']], locator=cell['locator'],
                         required='requested_measurement')
        if cell['state'] in ('malformed', 'missing', 'undefined'):
            self.fail(section, 'malformed_native' if malformed else cell['diagnostic_codes'][-1],
                      populations=[population] if population else (), cells=[cell])
        return cell

    def invalidate(self, cells, section, code):
        for cell in cells:
            cell['value'], cell['state'] = None, 'incompatible'
            if code not in cell['diagnostic_codes']:
                cell['diagnostic_codes'].append(code)
        self.fail(section, code, cells=cells)

    def parse(self):
        headers = [(i, _HEADER.fullmatch(line.text)) for i, line in enumerate(self.lines)
                   if line.text.startswith('This is cutadapt')]
        first = next((i for i, line in enumerate(self.lines) if line.text), None)
        for index, match in headers:
            if match:
                self.r.label(self.invocation, 'producer_version', match[1],
                             self.loc(self.invocation, self.lines[index], 'Cutadapt version'))
        if len(headers) != 1 or headers[0][1] is None or headers[0][0] != first:
            code = 'producer_version_unproven' if not headers or headers[0][1] is None else 'native_header_conflict'
            self.invocation['state'] = 'unsupported'
            self.r.raw(self.invocation, name='unverified Cutadapt invocation')
            self.fail(self.invocation, code, required='native_version')
            return
        if headers[0][1][1] != '4.9':
            self.invocation['state'] = 'unsupported'
            self.r.raw(self.invocation, name='unsupported Cutadapt version')
            self.fail(self.invocation, 'unsupported_version', required='supported_parser')
            return
        boundaries = [i for i, line in enumerate(self.lines) if re.fullmatch(r'=== .* ===', line.text)]
        first_body = boundaries[0] if boundaries else len(self.lines)
        empty = []
        for i, line in enumerate(self.lines[:first_body]):
            token = line.text
            if i == first or not token:
                continue
            if token.startswith('Command line parameters:'):
                self.r.label(self.invocation, 'command', token.split(':', 1)[1].strip(),
                             self.loc(self.invocation, line, 'Command line parameters'))
            elif re.fullmatch(r'Processing (single-end|paired-end) reads on [0-9]+ cores? \.\.\.', token):
                mode = 'pairs' if token.startswith('Processing paired-end') else 'reads'
                self.mode_conflict |= self.mode is not None and self.mode != mode
                self.mode = mode
                self.r.label(self.invocation, 'native_label', token,
                             self.loc(self.invocation, line, 'Processing mode'))
            elif token.startswith('Finished in '):
                self.r.label(self.invocation, 'native_label', token,
                             self.loc(self.invocation, line, 'Native timing'))
            elif token == 'No reads processed!':
                empty.append(line)
            else:
                self.unknown(self.invocation, line)
        if empty:
            section = self.section('cutadapt_summary', empty)
            if len(empty) != 1 or boundaries or self.mode is None or self.mode_conflict:
                self.fail(section, 'native_header_conflict')
                return
            pop = self.population(section, 'cutadapt_input_' + self.mode)
            cell = self.emit(section, 'cutadapt_processed_count', '0', pop, empty[0],
                             field='No reads processed!', unit=self.mode, row=0)
            cell['native_token'] = 'No reads processed!'
            self.input_population = pop
            return  # The text prints none of the other zero counters.
        summaries = []
        self.multiple_summaries = sum(self.lines[i].text == '=== Summary ===' for i in boundaries) > 1
        for a, b in zip(boundaries, boundaries[1:] + [len(self.lines)]):
            lines = self.lines[a:b]
            title = lines[0].text
            if title == '=== Summary ===':
                summaries.append(self.summary(lines))
                if self.multiple_summaries:
                    self.input_population = None  # No arbitrary origin for later event populations.
            elif _ADAPTER.fullmatch(title):
                self.adapter(lines)
            elif _POLY.fullmatch(title):
                self.poly_a(lines)
            else:
                section = self.section('unsupported', lines)
                section['state'] = 'unsupported'
                self.r.raw(section, name=title)
                self.fail(section, 'unsupported_report_section')
        if not summaries:
            self.fail(self.invocation, 'source_row_absent')

    def summary(self, lines):
        section = self.section('cutadapt_summary', lines)
        populations, rows = {}, defaultdict(list)
        base_group = None
        declared_modes = {('pairs' if line.text.startswith('Total read pairs processed:') else 'reads')
                          for line in lines if line.text.startswith(('Total reads processed:', 'Total read pairs processed:'))}
        if len(declared_modes) == 1:
            declared = next(iter(declared_modes))
            self.mode_conflict |= self.mode is not None and self.mode != declared
            self.mode = declared
        elif len(declared_modes) > 1:
            self.mode_conflict = True

        def pop(key, identity, parent=None):
            if identity not in populations:
                populations[identity] = self.population(section, key, parent=parent)
            return populations[identity]

        for ordinal, line in enumerate(lines[1:]):
            token = line.text.strip()
            if not token or token == '== Read fate breakdown ==':
                continue
            field, colon, value = token.partition(':')
            if not colon:
                self.unknown(section, line)
                continue
            metric = key = unit = axis = None
            mate = None
            identity = None
            parent = self.input_population
            if field in ('Total reads processed', 'Total read pairs processed'):
                unit = 'pairs' if field == 'Total read pairs processed' else 'reads'
                metric, key = 'cutadapt_processed_count', 'cutadapt_input_' + unit
                identity = (metric, unit)
                parent = None
                base_group = None
            elif field in ('Reads with adapters', 'Read 1 with adapter', 'Read 2 with adapter'):
                metric, key, unit = 'cutadapt_adapter_containing_reads', 'cutadapt_adapter_reads', 'reads'
                mate = field[:6] if field.startswith('Read ') else None
                axis = _axis('native_label', mate) if mate else None
                identity = (metric, mate)
                self.mode_conflict |= self.mode is not None and (self.mode == 'pairs') != bool(mate)
                base_group = None
            elif field == 'Reverse-complemented' and self.mode is not None:
                metric, key, unit = 'cutadapt_reverse_complemented_count', 'cutadapt_reverse_complemented', self.mode
                identity = (metric, None)
                base_group = None
            elif field in ('Reads written (passing filters)', 'Pairs written (passing filters)'):
                unit = 'reads' if field.startswith('Reads') else 'pairs'
                metric, key = 'cutadapt_written_count', 'cutadapt_output_' + unit
                identity = (metric, unit)
                self.mode_conflict |= self.mode is not None and self.mode != unit
                base_group = None
            elif any(field == lead + ' ' + description for lead in ('Reads', 'Pairs') for description in _FILTERS):
                unit = 'reads' if field.startswith('Reads') else 'pairs'
                metric, key = 'cutadapt_filtered_count', 'cutadapt_filtered'
                axis = _axis('native_label', field)
                identity = (metric, field)
                self.mode_conflict |= self.mode is not None and self.mode != unit
                base_group = None
            elif field in _BASE_FIELDS:
                metric, key = _BASE_FIELDS[field]
                unit, identity = 'bases', (metric, None)
                base_group = field
                parent = populations.get(('cutadapt_processed_bases', None), self.input_population)
                if metric == 'cutadapt_processed_bases':
                    parent = self.input_population
            elif field in ('Read 1', 'Read 2') and base_group is not None:
                metric, key = _BASE_FIELDS[base_group]
                mate, unit, identity = field, 'bases', (metric, field)
                self.mode_conflict |= self.mode is not None and self.mode != 'pairs'
                axis = _axis('native_label', field)
                if metric == 'cutadapt_processed_bases':
                    key, parent = 'cutadapt_mate_input_bases', populations.get((metric, None))
                else:
                    if metric == 'cutadapt_written_bases':
                        key = 'cutadapt_mate_output_bases'
                    parent = populations.get(('cutadapt_processed_bases', mate), self.input_population)
            if metric is None:
                self.unknown(section, line)
                continue
            native = re.fullmatch(r'\s*(.*?)\s*(?:\(([^()]*)%\))?\s*', value)
            number, percent = native.groups() if native else (value.strip(), None)
            missing_unit = False
            if unit == 'bases':
                if number.endswith(' bp'):
                    number = number[:-3].rstrip()
                else:
                    missing_unit = True
            population = pop(key, identity, parent)
            if metric == 'cutadapt_processed_count':
                if self.input_population is None:
                    self.input_population = population
                elif self.input_population['id'] != population['id']:
                    self.mode_conflict = True
            cell = self.emit(section, metric, number, population, line, field=field,
                             axis=axis, row=ordinal, unit=unit)
            rows[identity].append(cell)
            if missing_unit:
                self.fail(section, 'malformed_native', populations=[population], cells=[cell])
            if percent is None and metric not in ('cutadapt_processed_count', 'cutadapt_processed_bases') and not (
                    mate and unit == 'bases'):
                self.fail(section, 'source_row_absent', populations=[population])
            if percent is not None:
                label = (base_group + ' / ' + mate) if mate and base_group else field
                pct = self.emit(section, 'cutadapt_reported_percent', percent, population, line,
                                field=field + ' percent', axis=_axis('native_label', label), row=ordinal)
                rows[('percent', identity)].append(pct)
        for identity, duplicates in rows.items():
            if len(duplicates) > 1:
                self.invalidate(duplicates, section, 'selection_ambiguous')
        # Validate the native one-decimal display against its printed operands;
        # do not replace either observation or store a reconstructed count.
        for identity, percentages in rows.items():
            if identity[0] != 'percent' or len(percentages) != 1:
                continue
            counts = rows.get(identity[1], [])
            denominator_key = ('cutadapt_processed_bases', None) if counts and counts[0]['unit'] == 'bases' else (
                'cutadapt_processed_count', self.mode)
            denominators = rows.get(denominator_key, [])
            if len(counts) == len(denominators) == 1 and all(
                    c['value'] is not None for c in [*counts, *denominators, *percentages]):
                fraction = counts[0]['value'] / denominators[0]['value'] if denominators[0]['value'] else 0
                if float(f'{fraction:.1%}'[:-1]) != percentages[0]['value']:
                    self.fail(section, 'count_inconsistent')
                    affected = [*counts, *percentages]
                    for cell in affected:
                        if 'count_inconsistent' not in cell['diagnostic_codes']:
                            cell['diagnostic_codes'].append('count_inconsistent')
                    self.r.issue('count_inconsistent', affected=[c['id'] for c in affected],
                                 required='requested_measurement')
        for required in ('cutadapt_processed_count', 'cutadapt_written_count',
                         'cutadapt_processed_bases', 'cutadapt_written_bases'):
            if not any(identity[0] == required for identity in rows):
                self.fail(section, 'source_row_absent')
        if self.mode_conflict or self.multiple_summaries:
            self.invalidate([c for group in rows.values() for c in group], section,
                            'native_header_conflict' if self.mode_conflict else 'selection_ambiguous')
            return section
        # Only an unambiguous same-invocation, same-unit pair can establish
        # this artifact-local relation. Missing values remain missing values.
        for before, after in [(('cutadapt_processed_count', self.mode), ('cutadapt_written_count', self.mode)),
                              *((('cutadapt_processed_bases', mate), ('cutadapt_written_bases', mate))
                                for mate in (None, 'Read 1', 'Read 2'))]:
            left, right = rows.get(before, []), rows.get(after, [])
            if len(left) == len(right) == 1 and left[0]['unit'] == right[0]['unit']:
                self.r.lineage(populations[before], populations[after], [left[0]['locator'], right[0]['locator']])
        return section

    def adapter(self, lines):
        section = self.section('cutadapt_adapter', lines)
        title = _ADAPTER.fullmatch(lines[0].text)
        self.r.label(section, 'adapter', title[2], self.loc(section, lines[0], 'Adapter name'))
        if title[1]:
            self.r.label(section, 'native_label', title[1], self.loc(section, lines[0], 'Mate heading'))
        candidates = [(i, line) for i, line in enumerate(lines) if line.text.startswith('Sequence:')]
        if len(candidates) != 1:
            self.fail(section, 'selection_ambiguous' if candidates else 'source_row_absent')
            return
        header_index, header = candidates[0]
        fields = {}
        for chunk in header.text.split('; '):
            name, colon, value = chunk.partition(': ')
            if not colon or name in fields:
                self.fail(section, 'malformed_native')
                return
            fields[name] = value
        for name in ('Sequence', 'Type'):
            if name not in fields:
                self.fail(section, 'source_row_absent')
                return
            self.r.label(section, 'adapter' if name == 'Sequence' else 'native_label', fields[name],
                         self.loc(section, header, name))
        adapter_type = _TYPES.get(fields['Type'])
        if adapter_type is None:
            self.unknown(section, header)
            return
        ends = ("5'", "3'") if adapter_type == 'linked' else (
            ("5'", "3' or within") if adapter_type == 'anywhere' else (adapter_type,))
        populations, trimmed = {}, {}

        def pop(end):
            if end not in populations:
                populations[end] = self.population(section, 'cutadapt_adapter_events', parent=self.input_population)
            return populations[end]

        known_fields = {'Sequence', 'Type', 'Length', 'Trimmed', "5' trimmed", "3' trimmed", 'Reverse-complemented'}
        for name, value in fields.items():
            if name not in known_fields:
                self.unknown(section, header)
                continue
            if name == 'Length':
                values = value.split('+') if adapter_type == 'linked' else [value]
                targets = ends if adapter_type == 'linked' else (None if adapter_type == 'anywhere' else ends[0],)
                if len(values) != len(targets):
                    self.fail(section, 'malformed_native')
                    continue
                for target, number in zip(targets, values):
                    self.emit(section, 'cutadapt_adapter_length', number, pop(target), header,
                              field=name, axis=_axis('native_label', target) if len(targets) > 1 else None, row=0)
            elif name in ('Trimmed', "5' trimmed", "3' trimmed", 'Reverse-complemented'):
                number = value[:-6] if value.endswith(' times') else value
                target = name[:2] if name in ("5' trimmed", "3' trimmed") else (
                    None if adapter_type in ('anywhere', 'linked') else ends[0])
                reverse = name == 'Reverse-complemented'
                cell = self.emit(section, 'cutadapt_adapter_reverse_complemented_count' if reverse
                    else 'cutadapt_adapter_trimmed_count', number, pop(target), header, field=name,
                    axis=None if reverse or adapter_type not in ('linked', 'anywhere') else _axis('native_label', name), row=0)
                if not reverse:
                    trimmed[target] = cell
        if 'Length' not in fields or (adapter_type == 'linked' and not all(e + ' trimmed' in fields for e in ends)) or (
                adapter_type != 'linked' and 'Trimmed' not in fields):
            self.fail(section, 'source_row_absent')
        consumed = {0, header_index}
        for i, line in enumerate(lines):
            match = re.fullmatch(r"(\S+) times, it overlapped the (5' end of a read|3' end or was within the read)", line.text)
            if not match:
                continue
            if adapter_type != 'anywhere':
                self.unknown(section, line)
                consumed.add(i)
                continue
            end = "5'" if match[2].startswith("5'") else "3' or within"
            trimmed[end] = self.emit(section, 'cutadapt_adapter_trimmed_count', match[1], pop(end), line,
                field='times, it overlapped the ' + match[2], axis=_axis('native_label', match[2]), row=i)
            consumed.add(i)
        minimum = [(i, line) for i, line in enumerate(lines) if line.text.startswith('Minimum overlap:')]
        errors = [i for i, line in enumerate(lines) if line.text.startswith('No. of allowed errors:')]
        histograms = [i for i, line in enumerate(lines) if line.text in _HISTOGRAMS]
        adjacent = [i for i, line in enumerate(lines) if line.text == 'Bases preceding removed adapters:']
        breaks = sorted(set(errors + histograms + adjacent + [i for i, l in enumerate(lines) if l.text == 'WARNING:'] + [len(lines)]))
        zero = bool(trimmed) and all(c['value'] == 0 for c in trimmed.values())
        if len(minimum) > 1:
            self.fail(section, 'selection_ambiguous')
        elif minimum:
            consumed.add(minimum[0][0])
        for index, endpoint in enumerate(ends):
            # AnywhereAdapter prints one configuration shared by both ends.
            # Both sections retain identical source offsets, never independent
            # observations or an inferred second native block.
            error_index = 0 if adapter_type == 'anywhere' else index
            if error_index >= len(errors):
                if not zero:
                    self.fail(section, 'source_row_absent', populations=[pop(endpoint)])
                continue
            begin = errors[error_index]
            finish = next(b for b in breaks if b > begin)
            config = lines[begin:finish]
            minimum_value = None
            if len(minimum) == 1:
                values = minimum[0][1].text.partition(':')[2].strip().split('+')
                if len(values) == (2 if adapter_type == 'linked' else 1):
                    minimum_value = (values[index if adapter_type == 'linked' else 0], minimum[0][1])
                else:
                    self.fail(section, 'malformed_native', populations=[pop(endpoint)])
            start_line = minimum[0][1] if minimum_value else config[0]
            error_section = self.section('cutadapt_adapter_errors', [start_line, config[-1]],
                name='Shared anywhere adapter configuration' if adapter_type == 'anywhere' else 'Adapter error configuration')
            self.r.label(error_section, 'native_label', fields['Type'], self.loc(error_section, header, 'Type'))
            if len(ends) > 1:
                end_line = next((line for line in lines if _HISTOGRAMS.get(line.text) == endpoint), None)
                if end_line is None and endpoint in header.text:
                    end_line = header
                if end_line is not None:
                    self.r.label(error_section, 'native_label', endpoint,
                                 self.loc(error_section, end_line, 'Adapter end'))
            if minimum_value:
                self.emit(error_section, 'cutadapt_minimum_overlap', minimum_value[0], pop(endpoint), minimum_value[1],
                          field='Minimum overlap', axis=_axis('native_label', endpoint) if len(ends) > 1 else None, row=0)
            elif not fields['Type'].startswith('anchored'):
                self.fail(error_section, 'source_row_absent', populations=[pop(endpoint)])
            self.errors(error_section, config, pop(endpoint))
            consumed.update(range(begin, finish))
        expected_errors = 2 if adapter_type == 'linked' else 1
        if len(errors) > expected_errors:
            self.fail(section, 'selection_ambiguous', populations=list(populations.values()))
        seen_histograms = defaultdict(list)
        for begin in histograms:
            finish = next(b for b in breaks if b > begin)
            endpoint = _HISTOGRAMS[lines[begin].text] or ends[0]
            if endpoint not in ends:
                self.unknown(section, lines[begin])
                continue
            hist = self.section('cutadapt_adapter_histogram', lines[begin:finish])
            self.r.label(hist, 'native_label', lines[begin].text, self.loc(hist, lines[begin], 'Removed-end heading'))
            seen_histograms[endpoint].append(hist)
            cells = self.histogram(hist, lines[begin + 1:finish], pop(endpoint))
            expected = trimmed.get(endpoint)
            if expected is not None and expected['value'] is not None and all(c['value'] is not None for c in cells):
                if sum(c['value'] for c in cells) != expected['value']:
                    self.fail(hist, 'count_inconsistent', populations=[pop(endpoint)], cells=[expected, *cells])
            consumed.update(range(begin, finish))
        for endpoint in ends:
            if len(seen_histograms[endpoint]) > 1:
                self.fail(section, 'selection_ambiguous', populations=[pop(endpoint)])
            elif not seen_histograms[endpoint] and not zero:
                self.fail(section, 'source_row_absent', populations=[pop(endpoint)])
        for begin in adjacent:
            finish = next(b for b in breaks if b > begin)
            adj = self.section('cutadapt_adjacent_bases', lines[begin:finish])
            self.adjacent(adj, lines[begin + 1:finish], pop(ends[-1]))
            consumed.update(range(begin, finish))
        warning = False
        for index, line in enumerate(lines):
            if index in consumed or not line.text:
                continue
            if line.text == 'WARNING:' or warning and line.text.startswith('    '):
                warning = True
                self.r.label(section, 'native_label', line.text, self.loc(section, line, 'Native warning'))
            else:
                warning = False
                self.unknown(section, line)

    def errors(self, section, lines, population):
        inline = lines[0].text.partition(':')[2].strip()
        if inline:
            self.emit(section, 'cutadapt_allowed_errors', inline, population, lines[0],
                      field='No. of allowed errors', row=1)
            for line in lines[1:]:
                if line.text:
                    self.unknown(section, line)
            return
        rows = [(i, line) for i, line in enumerate(lines[1:], 1) if line.text]
        if not rows:
            self.fail(section, 'source_row_absent', populations=[population])
        previous = 0
        for ordinal, line in rows:
            for part in line.text.split('; '):
                match = re.fullmatch(r'([0-9]+)(?:-([0-9]+))? bp: (\S+)', part)
                if match is None:
                    self.r.raw(section, name=part, state='malformed', locator=self.loc(section, line, 'No. of allowed errors'))
                    self.fail(section, 'malformed_native', populations=[population])
                    continue
                lo, hi = _coordinate(match[1]), _coordinate(match[2] or match[1])
                if lo is None or hi is None or lo > hi or lo < 1:
                    self.fail(section, 'malformed_native', populations=[population])
                    continue
                cell = self.emit(section, 'cutadapt_allowed_errors', match[3], population, line,
                    field='No. of allowed errors', axis=_axis('length_closed', part.split(' bp:')[0], lo, hi),
                    row=ordinal)
                if lo <= previous:
                    self.fail(section, 'count_inconsistent', populations=[population], cells=[cell])
                previous = hi

    def histogram(self, section, lines, population):
        rows = [line for line in lines if line.text]
        header = 'length\tcount\texpect\tmax.err\terror counts'
        if not rows or rows[0].text != header:
            self.fail(section, 'native_header_conflict', populations=[population])
            return []
        counts, seen = [], set()
        for ordinal, line in enumerate(rows[1:]):
            fields = line.text.split('\t')
            if len(fields) != 5:
                self.fail(section, 'malformed_native', populations=[population])
                self.r.raw(section, name='malformed histogram row', state='malformed',
                           locator=self.loc(section, line, 'histogram row', ordinal))
            length = _coordinate(fields[0])
            axis = _axis('length_closed', fields[0], length, length)
            cells = []
            for column, metric in enumerate(('cutadapt_histogram_length', 'cutadapt_histogram_count',
                                            'cutadapt_histogram_expected_count', 'cutadapt_histogram_max_errors')):
                if column < len(fields):
                    cell = self.emit(section, metric, fields[column], population, line,
                                     field=header.split('\t')[column], axis=axis, row=ordinal)
                    cells.append(cell)
                    if column == 1:
                        counts.append(cell)
            if length in seen and length is not None:
                self.fail(section, 'selection_ambiguous', populations=[population], cells=cells)
            seen.add(length)
            bins = []
            if len(fields) >= 5:
                for index, number in enumerate(fields[4].split(' ')):
                    bins.append(self.emit(section, 'cutadapt_histogram_error_count', number, population, line,
                        field='error counts', axis=_axis('edit_error_count', str(index), index, index), row=ordinal))
            if len(cells) >= 2 and bins and all(c['value'] is not None for c in [cells[1], *bins]):
                if sum(c['value'] for c in bins) != cells[1]['value']:
                    self.fail(section, 'count_inconsistent', populations=[population], cells=[*cells, *bins])
            # Deliberately no comparison of an observed error index with
            # max.err: indels can make those native coordinates differ.
        return counts

    def adjacent(self, section, lines, population):
        seen = set()
        for ordinal, line in enumerate(lines):
            if not line.text:
                continue
            match = re.fullmatch(r'  (A|C|G|T|none/other): (.*)%', line.text)
            if match is None:
                self.unknown(section, line)
                continue
            cell = self.emit(section, 'cutadapt_adjacent_base_percent', match[2], population, line,
                field='Bases preceding removed adapters', axis=_axis('symbol', match[1]), row=ordinal)
            if match[1] in seen:
                self.fail(section, 'selection_ambiguous', cells=[cell])
            seen.add(match[1])
        if seen != {'A', 'C', 'G', 'T', 'none/other'}:
            self.fail(section, 'source_row_absent')

    def poly_a(self, lines):
        section = self.section('cutadapt_poly_a', lines)
        self.r.label(section, 'native_label', lines[0].text, self.loc(section, lines[0], 'Poly-A mate heading'))
        population = self.population(section, 'cutadapt_poly_a_events', parent=self.input_population)
        warning_start = next((i for i, line in enumerate(lines) if line.text == 'WARNING:'), len(lines))
        rows = [line for line in lines[1:warning_start] if line.text]
        for line in lines[warning_start:]:
            if line.text == 'WARNING:' or line.text.startswith('    '):
                self.r.label(section, 'native_label', line.text, self.loc(section, line, 'Native warning'))
            elif line.text:
                self.unknown(section, line)
        if not rows or rows[0].text != 'length\tcount':
            self.fail(section, 'native_header_conflict', populations=[population])
            return
        seen = set()
        for ordinal, line in enumerate(rows[1:]):
            fields = line.text.split('\t')
            if len(fields) != 2:
                self.fail(section, 'malformed_native', populations=[population])
            length = _coordinate(fields[0])
            axis = _axis('length_closed', fields[0], length, length)
            for index, metric in enumerate(('cutadapt_poly_a_length', 'cutadapt_poly_a_count')):
                if index < len(fields):
                    self.emit(section, metric, fields[index], population, line,
                              field=('length', 'count')[index], axis=axis, row=ordinal)
            if length in seen and length is not None:
                self.fail(section, 'selection_ambiguous', populations=[population])
            seen.add(length)


def append_cutadapt_report(report, raw: bytes, *, start: int, end: int) -> None:
    """Append one selected native invocation; the outer reader finishes once."""
    checked_bytes(raw, content=report.context['content'])
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(raw):
        raise FastqUtilsContractError('shape_invalid', '/cutadapt_range')
    boundaries = {0}
    offset = 0
    for line in raw.splitlines(keepends=True):
        offset += len(line)
        boundaries.add(offset)
    if start not in boundaries or end not in boundaries:
        raise FastqUtilsContractError('shape_invalid', '/cutadapt_range')
    invocation = report.section('cutadapt_embedded', start=start, end=end)
    report.raw(invocation, name='cutadapt_embedded', kind='table', state='complete')
    lines = []
    offset = start
    try:
        for value in raw[start:end].splitlines(keepends=True):
            next_offset = offset + len(value)
            lines.append(_Line(value.rstrip(b'\r\n').decode('utf-8', errors='strict'), offset, next_offset))
            offset = next_offset
    except UnicodeError:
        invocation['state'] = 'malformed'
        report.raw(invocation, name='invalid UTF-8 Cutadapt report', state='malformed')
        report.partial(invocation)
        return
    reader = _Cutadapt(report, lines, invocation)
    reader.parse()
    for section in report.doc['sections']:
        if section['locator']['byte_start'] is None or not start <= section['locator']['byte_start'] < end:
            continue
        for ordinal in section['raw_block_ordinals']:
            block = report.doc['raw_blocks'][ordinal]
            if block['parse_status'] == 'complete' and section['state'] in ('partial', 'malformed', 'unsupported'):
                block['parse_status'] = section['state']


__all__ = ['append_cutadapt_report']
