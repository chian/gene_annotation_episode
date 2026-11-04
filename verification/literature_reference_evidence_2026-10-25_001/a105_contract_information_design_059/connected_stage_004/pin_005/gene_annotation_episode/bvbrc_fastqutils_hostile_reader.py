"""Hostile 1.1.0 JSON report rows, with native primary-record populations."""
from __future__ import annotations

import json
from .bvbrc_fastqutils_fastqc_reader import _Report


from .bvbrc_fastqutils_json_tokens import _Numeric, _Pairs, _valid_text, _rows


def parse_hostile_json(raw: bytes, *, context: dict) -> dict:
    report = _Report(raw, context, 'hostile_json_1_1_0', 'Hostile')
    text = report.text(raw)
    if text is None: return report.finish()
    rows, closed = _rows(text)
    if not rows and closed:
        section = report.section('hostile_report', start=0, end=len(raw))
        report.raw(section, name='empty Hostile report array', kind='table', state='complete')
        report.version(section, None, '1.1.0')
    if not closed: report.partial(None, 'malformed_native', 'complete_native_bytes')
    for ordinal, (start, end, fragment, bounded) in enumerate(rows):
        start_byte = len(text[:start].encode('utf-8')); end_byte = len(text[:end].encode('utf-8'))
        section = report.section('hostile_report', ordinal=ordinal, start=start_byte, end=end_byte,
                                 state='complete' if bounded else 'partial')
        try:
            pairs = json.loads(fragment, object_pairs_hook=_Pairs, parse_int=_Numeric,
                               parse_float=_Numeric, parse_constant=_Numeric)
        except (ValueError, RecursionError):
            report.raw(section, name='malformed Hostile JSON row', kind='record', state='malformed')
            report.partial(section); continue
        if not isinstance(pairs, _Pairs):
            report.raw(section, name='non-object Hostile row', kind='record', state='malformed')
            report.partial(section); continue
        values = {}; duplicates = set()
        for key, value in pairs:
            if not _valid_text(key):
                report.partial(section)
                continue
            if key in values: duplicates.add(key)
            values[key] = value
        report.raw(section, name='Hostile SampleReport', kind='record', state=section['state'], fields=[k for k, _ in pairs if _valid_text(k)])
        for duplicate in duplicates:
            report.issue('malformed_native', locator=f'/{ordinal}/{duplicate}', required='requested_measurement')
        version = values.get('version')
        version = version if _valid_text(version) and 'version' not in duplicates else None
        compatible = report.version(section, version, '1.1.0', report.loc(section, 'version', row=ordinal, start=start_byte, end=end_byte))
        populations = {}
        for key in ('in', 'out', 'removed'):
            populations[key] = report.population(section, 'hostile_' + key, ordinal)
        cells = {}
        numeric_fields = ('reads_in', 'reads_out', 'reads_removed', 'reads_removed_proportion')
        order = list(dict.fromkeys(k for k, _ in pairs if k in numeric_fields))
        order.extend(k for k in numeric_fields if k not in order)
        for key in order:
            metric = 'hostile_removed_proportion' if key == 'reads_removed_proportion' else 'hostile_' + key
            population = populations['in'] if key == 'reads_removed_proportion' else populations[key[len('reads_'):]]
            value = values.get(key)
            # Native JSON number types only; a quoted count or boolean is not a measurement.
            native = str(value) if isinstance(value, _Numeric) else None if key not in values else json.dumps(value, ensure_ascii=True)
            codes = ('unsupported_version',) if not compatible else ()
            cell = report.cell(section, metric, native, population,
                locator=report.loc(section, key, row=ordinal, start=start_byte, end=end_byte),
                codes=codes, force_state=None if compatible else 'incompatible')
            if key in duplicates or (key in values and not isinstance(value, _Numeric)):
                cell.update(value=None, state='malformed'); cell['diagnostic_codes'].append('malformed_native')
                report.issue('malformed_native', affected=[cell['id']], locator=f'/{ordinal}/{key}', required='requested_measurement')
            cells[key] = cell
            if key not in values:
                report.partial(section, 'source_row_absent', 'requested_measurement')
        for key, value in pairs:
            if not _valid_text(key): continue
            if key in cells or key == 'version' or key in duplicates: continue
            loc = report.loc(section, key, row=ordinal, start=start_byte, end=end_byte)
            if key == 'options' and type(value) is list and all(type(v) is str for v in value):
                for index, option in enumerate(value):
                    try: option.encode('utf-8')
                    except UnicodeError:
                        report.partial(section); continue
                    report.label(section, 'option', option, dict(loc, field='options/' + str(index)))
            elif type(value) is str:
                try: value.encode('utf-8')
                except UnicodeError:
                    report.partial(section); continue
                kind = 'aligner' if key == 'aligner' else 'reference' if key == 'index' else 'path' if key.endswith('_path') else 'filename' if key.endswith('_name') else 'native_label'
                report.label(section, kind, value, loc)
            elif value is not None:
                report.raw(section, name='unsupported Hostile field ' + key, locator=loc)
                report.issue('unsupported_report_section', locator=f'/{ordinal}/{key}', required='supported_parser')
        before, after, removed, proportion = [cells[k] for k in ('reads_in', 'reads_out', 'reads_removed', 'reads_removed_proportion')]
        if all(c['value'] is not None for c in (before, after)):
            report.lineage(populations['in'], populations['out'], [before['locator'], after['locator']])
            if before['value'] == 0 and proportion['value'] == 0:
                proportion['diagnostic_codes'].append('native_fallback_value')
                report.issue('native_fallback_value', affected=[proportion['id']])
            if (after['value'] > before['value'] or
                (removed['value'] is not None and removed['value'] != before['value'] - after['value'])):
                for c in (before, after, removed): c['diagnostic_codes'].append('count_inconsistent')
                report.issue('count_inconsistent', affected=[c['id'] for c in (before, after, removed)])
        if proportion['value'] is not None:
            proportion['diagnostic_codes'].append('rounded_native_value')
    if not rows and not closed:
        section = report.section('unsupported', start=0, end=len(raw), state='malformed')
        report.raw(section, name='incomplete or non-array Hostile report', state='malformed')
    return report.finish()
