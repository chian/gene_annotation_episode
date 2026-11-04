"""Read Trim Galore 0.6.10's own report fields, keeping Cutadapt separate."""
from __future__ import annotations

import re
from .bvbrc_fastqutils_fastqc_reader import _Report, _axis

_OPTIONS = {
    'Number of cores used for trimming': 'dimensionless',
    'Quality Phred score cutoff': 'phred',
    '2-colour high quality G-trimming enabled, with quality cutoff': 'phred',
    'Maximum trimming error rate': 'fraction',
    'Minimum required adapter overlap (stringency)': 'bases',
    'Minimum required sequence length for both reads before a sequence pair gets removed': 'bases',
    'Minimum required sequence length before a sequence gets removed': 'bases',
    'Maxiumum tolerated read length after trimming (for smallRNA trimming)': 'bases',
    'Length cut-off for read 1': 'bases', 'Length cut-off for read 2': 'bases',
    'During adapter auto-detection, files are considered already adapter-trimmed if the highest found adapter was found equal to or lower than': 'dimensionless',
}
_REMOVALS = (
    ('Sequences removed because they became shorter than the length cutoff of ', 'short'),
    ('Sequences removed because they contained more Ns than the cutoff of ', 'n'),
    ('Sequences removed because after trimming they were longer than the maximum length cutoff of ', 'long'),
)
_PAIR_COUNT = 'Total number of sequences analysed for the sequence pair length validation:'
_PAIR_REMOVED = 'Number of sequence pairs removed because at least one read was shorter than the length cutoff '


def parse_trim_galore_report(raw: bytes, *, context: dict) -> dict:
    report = _Report(raw, context, 'trim_galore_report_0_6_10', 'Trim Galore')
    text = report.text(raw)
    if text is None: return report.finish()
    lines = text.splitlines(keepends=True)
    offset = 0; section = None; compatible = context['producer_version'] in (None, '0.6.10')
    seen_version = False; populations = {}; row_number = 0; cutadapt = False

    def select(key, start, *, force=False):
        nonlocal section, row_number
        if section is None or section['key'] != key or force:
            if section is not None: section['locator']['byte_end'] = start
            section = report.section(key, start=start)
            report.raw(section, name=key, kind='unsupported_section' if key == 'cutadapt_embedded' else 'table',
                       state='unsupported' if key == 'cutadapt_embedded' else 'complete')
            row_number = 0
        return section

    def pop(key, *, kind='native_report_population'):
        identity = section['key'], section['ordinal'], key
        if identity not in populations:
            populations[identity] = report.population(section, key, section['ordinal'], kind=kind)
        return populations[identity]

    for line in lines:
        token = line.rstrip('\r\n'); end = offset + len(line.encode('utf-8'))
        if token == 'SUMMARISING RUN PARAMETERS':
            select('trim_configuration', offset, force=True); cutadapt = False
        elif token.startswith('RUN STATISTICS FOR INPUT FILE:'):
            select('trim_summary', offset, force=True); cutadapt = False
        elif token.startswith(('This is cutadapt', '=== Summary ===')) and (section is None or section['key'] != 'trim_summary'):
            select('cutadapt_embedded', offset); cutadapt = True
            report.partial(section, 'unsupported_report_section', 'supported_parser')
        elif token.startswith((_PAIR_COUNT, 'Number of sequence pairs removed ', 'Sequence pairs removed as after trimming')):
            select('trim_pair_validation', offset); cutadapt = False
        elif token.startswith(('Using ', 'Unable to auto-detect ', 'AUTO-DETECTING ADAPTER TYPE', 'Adapter type\t')) or re.match(r'^(Illumina|Nextera|smallRNA)\t', token):
            select('trim_adapter_detection', offset); cutadapt = False
        elif section is None:
            select('trim_configuration', offset)
        elif section['key'] == 'trim_adapter_detection' and token.startswith(('Adapter sequence:', 'Maximum trimming error rate:', 'Minimum required')):
            select('trim_configuration', offset)
        loc = report.loc(section, 'line', row=row_number, start=offset, end=end)
        row_number += 1
        if cutadapt:
            offset = end; continue
        if token.startswith('Trim Galore version:'):
            reported = token.split(':', 1)[1].strip()
            compatible = report.version(section, reported, '0.6.10', loc); seen_version = True
        elif token.startswith('Input filename:') or token.startswith('RUN STATISTICS FOR INPUT FILE:'):
            report.label(section, 'filename', token.split(':', 1)[1].strip(), loc)
        elif section['key'] == 'trim_configuration':
            field, colon, value = token.partition(':')
            if field in _OPTIONS and colon:
                numeric = re.fullmatch(r'\s*([^\s]+)(?:\s+bp)?(?:\s+\(default\))?\s*', value)
                report.cell(section, 'trim_native_option', numeric[1] if numeric else value.strip(),
                    axis=_axis('native_label', field), locator=dict(loc, field=field), unit=_OPTIONS[field],
                    force_state=None if compatible else 'incompatible')
            elif colon:
                kind = 'adapter' if 'adapter' in field.lower() else 'option'
                report.label(section, kind, value.strip(), dict(loc, field=field))
        elif section['key'] == 'trim_adapter_detection':
            matches = []
            m = re.fullmatch(r'Using (.+) adapter for trimming \(count: ([^)]+)\)\. Second best hit was (.+) \(count: ([^)]+)\)', token)
            if m: matches = [(m[1], m[2]), (m[3], m[4])]
            elif token.startswith('Unable to auto-detect '):
                matches = re.findall(r'count ([^:,]+): ([^,)]+)', token)
            elif re.match(r'^(Illumina|Nextera|smallRNA)\t', token):
                fields = token.split('\t')
                if len(fields) == 5:
                    matches = [(fields[0], fields[1])]
                    for index, name in ((2, 'Sequence'), (3, 'Sequences analysed'), (4, 'Percentage')):
                        report.label(section, 'native_label', fields[index], dict(loc, field=name))
                else: report.partial(section)
            for name, value in matches:
                report.cell(section, 'trim_adapter_detection_count', value, axis=_axis('adapter', name),
                    locator=dict(loc, field=name), force_state=None if compatible else 'incompatible')
            if token: report.label(section, 'native_label', token, loc)
        elif section['key'] == 'trim_summary':
            m = re.fullmatch(r'([^ ]+) sequences processed in total', token)
            if m:
                report.cell(section, 'trim_processed_count', m[1], pop('trim_processed'),
                    locator=dict(loc, field='sequences processed in total', row_ordinal=None),
                    force_state=None if compatible else 'incompatible')
            else:
                found = False
                for prefix, suffix in _REMOVALS:
                    if not token.startswith(prefix): continue
                    found = True
                    m = re.fullmatch(r'(.+):\s*([^\s]+)\s+\(([^)]+)%\)', token)
                    if not m: report.partial(section); break
                    population = pop('trim_removed_' + suffix)
                    for field, number in (('count', m[2]), ('percent', m[3])):
                        report.cell(section, 'trim_removed_' + suffix + '_' + field, number, population,
                            axis=_axis('native_label', m[1]), locator=dict(loc, field=field, row_ordinal=None),
                            codes=('rounded_native_value',) if field == 'percent' else (),
                            force_state=None if compatible else 'incompatible')
                    break
                if token and not found and not re.fullmatch('=+', token):
                    report.label(section, 'native_label', token, loc)
        elif section['key'] == 'trim_pair_validation':
            if token.startswith(_PAIR_COUNT):
                value = token[len(_PAIR_COUNT):].strip()
                report.cell(section, 'trim_validation_pair_count', value, pop('trim_pairs_in', kind='native_pair_validation'),
                    locator=dict(loc, field=_PAIR_COUNT[:-1], row_ordinal=None), force_state=None if compatible else 'incompatible')
            elif token.startswith(_PAIR_REMOVED):
                m = re.fullmatch(r'(.+):\s*([^\s]+)\s+\(([^)]+)%\)', token)
                if not m: report.partial(section)
                else:
                    population = pop('trim_pairs_removed', kind='native_pair_validation')
                    for field, value in (('count', m[2]), ('percent', m[3])):
                        report.cell(section, 'trim_removed_pair_' + field, value, population, axis=_axis('native_label', m[1]),
                            locator=dict(loc, field=field, row_ordinal=None), codes=('trim_pair_counter_mixed',),
                            force_state=None if compatible else 'incompatible')
                    report.issue('trim_pair_counter_mixed', affected=[population['id']])
            elif token:
                # Separate N/too-long paired counters lack registered numeric slots;
                # do not mislabel them as the single-read N/length counters.
                report.label(section, 'native_label', token, loc)
                report.raw(section, name='additional paired-validation counter', locator=loc)
                report.issue('unsupported_report_section', required='supported_parser')
        offset = end
    if section is not None: section['locator']['byte_end'] = len(raw)
    for block in report.doc['raw_blocks']:
        if block['locator']['byte_end'] is None:
            match = next(s for s in report.doc['sections'] if (s['key'], s['ordinal']) == (block['locator']['block'], block['locator']['block_ordinal']))
            block['locator']['byte_end'] = match['locator']['byte_end']
    if not seen_version:
        if section is None: section = report.section('trim_configuration', start=0, end=len(raw))
        report.version(section, None, '0.6.10')
    if not any(cell['metric'] == 'trim_processed_count' for cell in report.doc['cells']):
        report.partial(None, 'source_row_absent', 'requested_measurement')
    return report.finish()
