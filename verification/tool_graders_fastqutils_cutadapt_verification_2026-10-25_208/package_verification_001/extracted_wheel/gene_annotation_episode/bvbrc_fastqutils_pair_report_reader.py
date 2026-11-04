"""Four fastq-pair 0.3 stderr counters; they are read records, never pairs."""
from __future__ import annotations

import re
from .bvbrc_fastqutils_fastqc_reader import _Report

_LABELS = {'Left paired': 'fastq_pair_left_paired', 'Right paired': 'fastq_pair_right_paired',
           'Left single': 'fastq_pair_left_single', 'Right single': 'fastq_pair_right_single'}


def parse_fastq_pair_stderr(raw: bytes, *, context: dict) -> dict:
    report = _Report(raw, context, 'fastq_pair_stderr_0_3', 'fastq-pair')
    text = report.text(raw)
    if text is None: return report.finish()
    section = None; offset = 0; seen = {}; compatible = context['producer_version'] in (None, '0.3')
    # -V writes to stdout and exits; ordinary stderr contains no version proof.
    version_section = report.section('unsupported', start=0, end=len(raw))
    report.raw(version_section, name='retained fastq-pair stderr', kind='record', state='complete')
    report.version(version_section, None, '0.3')
    for line in text.splitlines(keepends=True):
        end = offset + len(line.encode('utf-8'))
        matches = list(re.finditer(r'(Left paired|Right paired|Left single|Right single):\s*([^\s]+)', line))
        if matches:
            if section is None or ('Left paired' in seen and matches[0][1] == 'Left paired'):
                if section:
                    section['locator']['byte_end'] = offset
                    for block_index in section['raw_block_ordinals']:
                        report.doc['raw_blocks'][block_index]['locator']['byte_end'] = offset
                section = report.section('fastq_pair_summary', start=offset, end=len(raw)); seen = {}
                report.raw(section, name='fastq-pair four counters', kind='table', state='complete', fields=_LABELS)
            for match in matches:
                label, value = match[1], match[2]
                if label in seen:
                    report.partial(section, 'selection_ambiguous', 'exact_source_cardinality')
                    continue
                population = report.population(section, _LABELS[label], section['ordinal'])
                location = report.loc(section, label, start=offset, end=end)
                row = report.cell(section, _LABELS[label], value, population, locator=location,
                                  force_state=None if compatible else 'incompatible')
                # The producer counters are signed C int, not 64-bit long.
                if row['value'] is not None and row['value'] > 2147483647:
                    row.update(value=None, state='malformed'); row['diagnostic_codes'].append('malformed_native')
                    report.issue('malformed_native', affected=[row['id']], locator=location)
                seen[label] = row
            if {'Left paired', 'Right paired'} <= seen.keys():
                a, b = seen['Left paired'], seen['Right paired']
                if a['value'] is not None and b['value'] is not None and a['value'] != b['value']:
                    for row in (a, b): row['diagnostic_codes'].append('count_inconsistent')
                    report.issue('count_inconsistent', affected=[a['id'], b['id']])
        elif line.strip():
            report.label(version_section, 'native_label', line.rstrip('\r\n'),
                         report.loc(version_section, 'stderr', start=offset, end=end))
        offset = end
    summaries = [s for s in report.doc['sections'] if s['key'] == 'fastq_pair_summary']
    for summary in summaries:
        cells = [c for c in report.doc['cells'] if c['section_ordinal'] == summary['ordinal']]
        if len(cells) != 4:
            report.partial(summary, 'source_row_absent', 'requested_measurement')
    if not summaries: report.partial(None, 'source_row_absent', 'requested_measurement')
    return report.finish()
