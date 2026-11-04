"""Pure parser for retained p3-sra run-centric JSON, preserving every row."""
from __future__ import annotations

import json
import re

from .bvbrc_fastqutils_fastqc_reader import _Report
from .bvbrc_fastqutils_json_tokens import _Numeric, _Pairs, _rows, _valid_text
from .bvbrc_fastqutils_sra_specs import SRA_FIELDS

_DECODER = json.JSONDecoder(object_pairs_hook=_Pairs, parse_int=_Numeric,
    parse_float=_Numeric, parse_constant=_Numeric)
_REFERENCES = {'run_id', 'accession', 'exp_id', 'study_id', 'sample_id', 'sample_taxon'}


def _members(fragment):
    """Exact top-level value spans; decoder never evaluates strings or code."""
    pairs = _DECODER.decode(fragment)
    if type(pairs) is not _Pairs:
        raise ValueError('run_object_required')
    position = len(fragment) - len(fragment.lstrip()) + 1
    result = []
    for _ in pairs:
        while position < len(fragment) and fragment[position].isspace():
            position += 1
        key, position = _DECODER.raw_decode(fragment, position)
        while fragment[position].isspace():
            position += 1
        if fragment[position] != ':':
            raise ValueError('missing_colon')
        position += 1
        while fragment[position].isspace():
            position += 1
        start = position
        value, position = _DECODER.raw_decode(fragment, position)
        result.append((key, value, start, position))
        while position < len(fragment) and fragment[position].isspace():
            position += 1
        if position < len(fragment) and fragment[position] == ',':
            position += 1
    return result


def parse_sra_metadata(raw: bytes, *, context: dict) -> dict:
    report = _Report(raw, context, 'sra_metadata', 'p3-sra')
    text = report.text(raw)
    if text is None:
        return report.finish()
    report.issue('producer_version_unproven', required='native_version')
    if context['producer_version'] is not None:
        report.issue('supplied_version_assumption')
    rows, closed = _rows(text)
    if not closed:
        report.partial(None, 'malformed_native', 'complete_native_bytes')
    if not rows:
        section = report.section('sra_run', start=0, end=len(raw),
            state='complete' if closed else 'malformed')
        report.raw(section, name='p3-sra empty array' if closed else 'invalid p3-sra JSON',
                   kind='record', state='complete' if closed else 'malformed')
    for ordinal, (start, end, fragment, bounded) in enumerate(rows):
        start_byte = len(text[:start].encode('utf-8'))
        end_byte = len(text[:end].encode('utf-8'))
        section = report.section('sra_run', ordinal=ordinal, start=start_byte,
            end=end_byte, state='complete' if bounded else 'partial')
        try:
            members = _members(fragment)
        except (ValueError, RecursionError, IndexError):
            report.raw(section, name='malformed p3-sra row', kind='record', state='malformed')
            report.partial(section)
            continue
        keys = [key for key, _, _, _ in members if _valid_text(key)]
        duplicate_keys = {key for key in keys if keys.count(key) > 1}
        report.raw(section, name='p3-sra run metadata', kind='record',
            state=section['state'], fields=keys)
        population = report.population(section, 'sra_reported_run', ordinal,
            scope='partial' if not bounded or context['transfer_scope'] == 'partial' else 'unknown')
        report.issue('sra_metadata_basis_unproven', affected=[population['id']])
        identity_values = {}
        seen_numeric = set()
        for key, value, first, last in members:
            if not _valid_text(key):
                report.partial(section)
                continue
            locator = report.loc(section, key, row=ordinal,
                start=start_byte + len(fragment[:first].encode('utf-8')),
                end=start_byte + len(fragment[:last].encode('utf-8')))
            if key in SRA_FIELDS:
                # One malformed cell represents a repeated numeric key. Do not
                # select either occurrence as the authoritative measurement.
                if key in seen_numeric:
                    continue
                seen_numeric.add(key)
                metric, _, domain, _ = SRA_FIELDS[key]
                token = fragment[first:last]
                valid_number = type(value) is _Numeric and (
                    domain != 'nonnegative_integer' or re.fullmatch(r'-?(?:0|[1-9][0-9]*)', token))
                codes = []
                if key == 'read_length':
                    codes.append('sra_read_length_basis_unproven')
                elif key == 'n_reads':
                    codes.append('sra_read_types_basis_unproven')
                cell = report.cell(section, metric, token if valid_number else None,
                    population, locator=locator, codes=codes)
                if key in duplicate_keys or (value is not None and not valid_number):
                    cell.update(value=None, state='malformed', native_token=token)
                    cell['diagnostic_codes'].append('malformed_native')
                    report.partial(section, 'malformed_native', 'requested_measurement')
                    report.issue('malformed_native', affected=[cell['id']], required='requested_measurement')
                elif value is None:
                    cell.update(value=None, state='not_measured', native_token='null')
                for code in codes:
                    report.issue(code, affected=[cell['id']])
                continue
            if type(value) is str and _valid_text(value):
                kind = 'reference' if key in _REFERENCES else 'native_label'
                label = report.label(section, kind, value, locator)
                if key in _REFERENCES:
                    identity_values.setdefault(key, []).append(value)
                if key in duplicate_keys:
                    report.issue('metadata_value_conflict', affected=[label['id']],
                        required='source_bound_metadata')
            elif type(value) is list and all(_valid_text(item) for item in value):
                kind = 'filename' if key == 'files' else 'reference' if key.startswith('study_') else 'native_label'
                for index, item in enumerate(value):
                    report.label(section, kind, item, dict(locator, field=key + '/' + str(index)))
                if key == 'files':
                    report.issue('sra_file_association_unproven', affected=[population['id']])
                elif key.startswith('study_'):
                    report.issue('sra_cross_reference_association_unproven', affected=[population['id']])
            elif value is not None:
                report.raw(section, name='unsupported p3-sra field ' + key, locator=locator)
                report.issue('unsupported_report_section', required='supported_parser')
        run_ids = identity_values.get('run_id', [])
        accessions = identity_values.get('accession', [])
        if not run_ids or not accessions or any(not item for item in run_ids + accessions):
            report.partial(section, 'native_header_conflict', 'source_bound_metadata')
        elif len(set(run_ids + accessions)) != 1:
            report.issue('metadata_value_conflict', affected=[population['id']],
                required='source_bound_metadata')
    return report.finish()


__all__ = ['parse_sra_metadata']
