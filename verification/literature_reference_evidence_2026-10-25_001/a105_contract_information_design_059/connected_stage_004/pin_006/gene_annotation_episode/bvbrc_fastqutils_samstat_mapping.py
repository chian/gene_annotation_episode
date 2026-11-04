"""Fractions of explicitly selected native SAMstat report record strata.

The four retained integer bins are the denominator. These are neither distinct
read/molecule fractions nor estimates of completeness of the original input.
No parsing, acquisition, lineage inference or quality-score conversion occurs.
"""
from __future__ import annotations

import re

from .bvbrc_fastqutils_contracts import FastqUtilsContractError, validate_contract, validate_sheet
from .bvbrc_fastqutils_identity import decode_reference
from .bvbrc_fastqutils_retention import _component

_VERSIONS = {'samstat_html_2_2_3': '2.2.3', 'samstat_html_2_5_0': '2.5.0'}
_COUNTS = {'samstat_alignment_bin_count', 'samstat_alignment_total_count'}


def _bin_index(cell):
    axis = cell['axis']
    if axis['kind'] == 'mapq':
        bounds = axis['lower'], axis['upper']
        if bounds in ((30, 255), (10, 29), (0, 9)):
            return ((30, 255), (10, 29), (0, 9)).index(bounds)
    elif (axis['kind'] == 'native_label' and axis['label'] == 'Unmapped'
          and axis['lower'] is None and axis['upper'] is None):
        return 3
    return None


def _count_operands(sheet, population_refs):
    """Retain every count, including duplicates/invalid axes, in bin order."""
    result = []
    for ref in dict.fromkeys(population_refs):
        rows = [c for c in sheet['measurements'] if c['population_ref'] == ref and c['metric'] in _COUNTS]
        def order(cell):
            if cell['metric'] == 'samstat_alignment_total_count':
                return 5
            index = _bin_index(cell)
            return 4 if index is None else index
        result.extend(sorted(rows, key=order))
    return result


def _report_mode(document):
    """Native labels establish mode; paths and count presence never do."""
    actual = document['artifact']['actual_format']
    if actual == 'samstat_html_2_2_3':
        labels = {r['value'] for r in document['labels'] if r['kind'] == 'native_label'
                  and r['section_key'] == 'samstat_summary'
                  and r['value'] in {'Mapping statistics', 'File statistics'}}
        alignment, sequence = 'Mapping statistics' in labels, 'File statistics' in labels
    elif actual == 'samstat_html_2_5_0':
        labels = {r['value'] for r in document['labels'] if r['kind'] == 'native_label'
                  and r['locator']['field'] == 'input_format'}
        if labels - {'SAM', 'BAM', 'FASTQ', 'FASTA'}:
            return 'conflicting' if len(labels) > 1 else 'unknown'
        alignment, sequence = bool(labels & {'SAM', 'BAM'}), bool(labels & {'FASTQ', 'FASTA'})
        if len(labels) > 1:
            return 'conflicting'
    else:
        return 'unknown'
    return 'conflicting' if alignment and sequence else 'alignment' if alignment else 'sequence' if sequence else 'unknown'


def _mapping_conflicts(document):
    # _Report stores diagnostic locators as dict repr. Rebuild its declared
    # field order so canonical JSON key sorting cannot lose a saved conflict.
    fields = ('member', 'block', 'block_ordinal', 'row_ordinal', 'field', 'byte_start', 'byte_end')
    locations = {str({key: s['locator'][key] for key in fields})
                 for s in document['sections'] if s['key'] == 'samstat_mapping'}
    return [d['code'] for d in document['diagnostics'] if d['locator'] in locations
            and d['code'] in {'selection_ambiguous', 'native_header_conflict'}]


def calculate_samstat_report_mapping(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]:
    """CalculationBinding -> exactly two ordinary, inspectable Components."""
    validate_sheet(sheet)
    job = validate_contract('CalculationBinding', job)
    if (job['method'] != 'samstat_report_mapping_v1' or type(parameters_sha256) is not str
            or not re.fullmatch('[a-f0-9]{64}', parameters_sha256)
            or job['quality_thresholds'] or any(job[k] is not None for k in
                ('comparison_kind', 'read_key_rule', 'lineage_ref', 'lineage_basis'))):
        raise FastqUtilsContractError('shape_invalid')
    population_index = {p['id']: p for p in sheet['populations']}
    cell_index = {c['id']: c for c in sheet['measurements']}
    for refs, kind, index in ((job['population_refs'], 'population', population_index),
                              (job['operand_measurement_refs'], 'cell', cell_index)):
        for ref in refs:
            parts = decode_reference(ref, expected_kind=kind)
            if parts['analysis_id'] != sheet['analysis_id'] or ref not in index:
                raise FastqUtilsContractError('reference_invalid')
    populations = [population_index[ref] for ref in dict.fromkeys(job['population_refs'])]
    cells = [cell_index[ref] for ref in dict.fromkeys(job['operand_measurement_refs'])]
    codes = list(job['diagnostic_codes']) + ['samstat_report_population_only']
    problems = set()
    partial = False
    if job['state'] != 'ready':
        problems.add('incompatible' if job['state'] == 'incompatible' else 'missing')
    if 'samstat_caller_failure' in codes:
        problems.add('failed')
    identity_valid = True

    def problem(state, code):
        problems.add(state)
        codes.append(code)

    if len(populations) not in (1, 2):
        problem('missing' if not populations else 'incompatible', 'missing_denominator' if not populations else 'incompatible_population')
        identity_valid = False
    if (len(populations) != len(job['population_refs']) or len(cells) != len(job['operand_measurement_refs'])):
        problem('incompatible', 'selection_ambiguous')
        identity_valid = False
    documents = {d['artifact']['id']: d for d in sheet['documents']}
    for population in populations:
        valid = (population['population_key'] == 'samstat_report_records'
            and population['population_ordinal'] in (0, 1, 2)
            and population['kind'] == 'native_report_population'
            and population['representation'] == 'native_report'
            and len(population['member_artifact_refs']) == 1 and len(population['document_ids']) == 1
            and not population['member_record_refs'] and population['association_ref'] is None
            and population['pair_key_rule'] is None)
        if not valid:
            problem('incompatible', 'incompatible_population')
            identity_valid = False
            continue
        document = documents[population['member_artifact_refs'][0]]
        artifact = document['artifact']
        if population['document_ids'] != [document['document_id']]:
            problem('incompatible', 'document_identity_conflict')
            identity_valid = False
        if artifact['actual_format'] not in _VERSIONS or artifact['producer_version'] != _VERSIONS.get(artifact['actual_format']):
            problem('incompatible', 'unsupported_version')
            identity_valid = False
        mode = _report_mode(document)
        if mode != 'alignment':
            problem('missing' if mode == 'unknown' else 'incompatible',
                    'source_row_absent' if mode == 'unknown' else 'native_header_conflict' if mode == 'conflicting' else 'incompatible_population')
            identity_valid = False
        doc_codes = {d['code'] for d in document['diagnostics']}
        for code in _mapping_conflicts(document):
            problem('incompatible', code)
        codes.extend(code for code in ('samstat_input_scope_unproven', 'samstat_native_prefix', 'partial_transfer') if code in doc_codes)
        if population['scope'] == 'unknown':
            codes.append('samstat_input_scope_unproven')
        partial |= population['scope'] == 'partial' or document['parse_scope'] != 'complete' or artifact['transfer_scope'] != 'complete'
        if artifact['transfer_scope'] == 'partial':
            codes.append('partial_transfer')
        if document['parse_scope'] in ('unsupported', 'malformed'):
            problem('incompatible', 'unsupported_format' if document['parse_scope'] == 'unsupported' else 'malformed_native')
    if len(populations) == 2:
        left, right = populations
        if (left['document_ids'] != right['document_ids'] or left['member_artifact_refs'] != right['member_artifact_refs']
                or {left['population_ordinal'], right['population_ordinal']} != {1, 2}
                or right['id'] not in left['disjoint_from_refs'] or left['id'] not in right['disjoint_from_refs']):
            problem('incompatible', 'incompatible_population')
            identity_valid = False

    # Inspect the full selected population, not merely a convenient subset in
    # a hand-made binding. Never silently use its unbound cells for arithmetic.
    native_counts = _count_operands(sheet, [p['id'] for p in populations])
    if {c['id'] for c in cells} != {c['id'] for c in native_counts}:
        problem('incompatible', 'incompatible_population')
        problem('incompatible', 'missing_requested_value')
        identity_valid = False
    bins_by_population = []
    for population in populations:
        rows = [c for c in native_counts if c['population_ref'] == population['id']]
        bins = [[] for _ in range(4)]
        totals = []
        for cell in rows:
            codes.extend(cell['diagnostic_codes'])
            if 'count_inconsistent' in cell['diagnostic_codes']:
                problem('incompatible', 'count_inconsistent')
            if (cell['artifact_ref'] not in population['member_artifact_refs'] or cell['unit'] != 'alignment_records'
                    or cell['meaning'] != 'observed_count' or cell['precision'] != 'exact_for_retained_population'):
                problem('incompatible', 'incompatible_population')
            if cell['state'] in ('malformed', 'incompatible', 'undefined'):
                problem('incompatible', 'malformed_native' if cell['state'] == 'malformed' else 'count_inconsistent')
            elif cell['state'] == 'failed':
                problem('failed', 'missing_requested_value')
            elif cell['state'] not in ('available', 'partial') or cell['value'] is None:
                problem('truncated' if cell['state'] == 'truncated' else 'missing', 'missing_requested_value')
            partial |= cell['state'] == 'partial'
            if cell['metric'] == 'samstat_alignment_total_count':
                if cell['axis'] != {'kind': 'none', 'label': None, 'lower': None, 'upper': None}:
                    problem('incompatible', 'malformed_native')
                totals.append(cell)
            else:
                index = _bin_index(cell)
                if index is None:
                    problem('incompatible', 'malformed_native')
                else:
                    bins[index].append(cell)
        if any(not group for group in bins):
            problem('missing', 'missing_requested_value')
        if any(len(group) > 1 for group in bins) or len(totals) > 1:
            problem('incompatible', 'selection_ambiguous')
        complete = all(len(group) == 1 and group[0]['state'] in ('available', 'partial')
                       and type(group[0]['value']) is int and group[0]['value'] >= 0 for group in bins)
        if complete:
            values = [group[0]['value'] for group in bins]
            bins_by_population.append(values)
            codes.append('samstat_mapq255_merged')
            if any(total['value'] is not None and total['value'] != sum(values) for total in totals):
                problem('incompatible', 'count_inconsistent')
        else:
            bins_by_population.append(None)
    total = unmapped = high = None
    if identity_valid and bins_by_population and all(row is not None for row in bins_by_population):
        total = sum(sum(row) for row in bins_by_population)
        unmapped = sum(row[3] for row in bins_by_population)
        high = sum(row[0] for row in bins_by_population)
    if 'incompatible' in problems:
        state = 'incompatible'
    elif 'failed' in problems:
        state = 'failed'
    elif problems or total is None:
        state = 'truncated' if partial or 'truncated' in problems else 'missing'
    elif total == 0:
        state = 'undefined'
        codes.append('zero_denominator')
    else:
        state = 'partial' if partial else 'available'
    return [_component(sheet, job, parameters_sha256, metric, state=state,
        value=numerator / total if state in ('available', 'partial') else None,
        unit='fraction', cells=cells, populations=populations, numerator=numerator,
        denominator=total, codes=codes) for metric, numerator in (
            ('samstat_report_mapped_record_fraction', None if total is None else total - unmapped),
            ('samstat_report_ge30_record_fraction', high))]


__all__ = ['calculate_samstat_report_mapping']
