"""Pure native HOMER readers and the single retained-data selector/calculator.

Reported numbers are observations, not a reimplementation of HOMER's scoring.
The only numerical summary is an fsum of explicitly retained input weights.
"""
from copy import deepcopy
import hashlib
import math
import re

from . import homer_motif_contracts as c
from .bvbrc_alignment_values import native_number, numeric_cell


_FILE_KEYS = {'role', 'native_relative_path', 'content', 'artifact', 'capture'}
_SERIES_ROLES = ('known_results', 'denovo_pwm', 'denovo_combined_pwm', 'denovo_nonredundant_pwm')
_KNOWN_PREFIX = ['Motif Name', 'Consensus', 'P-value', 'Log P-value', 'q-value (Benjamini)']


def _path(value):
    c.native_path(value)


def _file(value):
    c.require(type(value) is dict and set(value) == _FILE_KEYS, 'file_input_invalid')
    c.require(value['role'] in c.ROLES, 'file_role_invalid')
    _path(value['native_relative_path'])
    content, artifact, extent = value['content'], value['artifact'], value['capture']
    c.require(content is None or type(content) is bytes, 'file_content_invalid')
    metadata = dict(file_id='pending', role=value['role'], native_relative_path=value['native_relative_path'],
        artifact=artifact, capture=extent, decode_state='unavailable', issues=[])
    c.validated('File', metadata)
    c.require(type(extent['byte_start_0based']) is int and extent['byte_start_0based'] == 0,
        'prefix_capture_required')
    if extent['state'] == 'missing':
        c.require(content is None and artifact is None and extent['byte_end_0based_exclusive'] == 0,
            'missing_capture_conflict')
    else:
        c.require(content is not None and artifact is not None, 'captured_bytes_required')
        c.require(artifact['size_bytes'] == len(content)
            and artifact['sha256'] == hashlib.sha256(content).hexdigest()
            and extent['byte_end_0based_exclusive'] == len(content), 'captured_byte_identity_conflict')
        total = extent['original_size_bytes']
        c.require(total is None or total >= len(content), 'capture_size_conflict')
        c.require(extent['state'] != 'complete' or total == len(content), 'complete_capture_size_conflict')
        c.require(extent['state'] != 'truncated' or total is None or total > len(content), 'truncated_capture_size_conflict')
        metadata['decode_state'] = 'complete'
    metadata['file_id'] = c.identity('homer_file', [value['role'], value['native_relative_path'], artifact])
    return metadata


def _location(file, start, end, line_start, line_end=None):
    artifact = {key: file['artifact'][key] for key in ('raw_artifact_ref', 'source_ref', 'sha256')}
    return dict(artifact=artifact, byte_start_0based=start, byte_end_0based_exclusive=end,
        line_start_1based=line_start, line_end_1based_inclusive=line_end or line_start, xml_path=None)


def _lines(file, content):
    result, offset = [], 0
    if content is None: return result
    for ordinal, raw in enumerate(content.splitlines(keepends=True)):
        body = raw.rstrip(b'\r\n')
        try:
            text, valid = body.decode('utf-8'), True
        except UnicodeDecodeError:
            text, valid = body.decode('utf-8', 'backslashreplace'), False
            file['decode_state'] = 'partial'
            file['issues'].append('native_utf8_invalid')
        complete = file['capture']['state'] == 'complete' or raw.endswith(b'\n')
        result.append(dict(ordinal=ordinal, fields=text.split('\t'), text=text, raw=body,
            valid=valid, complete=complete,
            location=_location(file, offset, offset + len(raw), ordinal + 1)))
        offset += len(raw)
    return result


def _absent(field):
    return dict(availability='not_provided', number=None, unit=c.NUMBER_FIELDS[field], precision='not_provided')


def _number(field, token, location, precision):
    return dict(availability='provided', number=c.field_number(field, token, location),
        unit=c.NUMBER_FIELDS[field], precision=c.native_precision(token, precision))


def _representation(kind, fields, location):
    return dict(kind=kind, raw_fields=list(fields), location=deepcopy(location),
        numbers={field: _absent(field) for field in c.NUMBER_FIELDS}, native_gap_field=None,
        extra_fields=[], native_auxiliary_measurements=[], native_auxiliary_absent_fields=list(c.AUXILIARY_FIELDS),
        pwm_rows=[], issues=[])


def _auxiliary(rep, location):
    present = []
    for extra_ordinal, extra in enumerate(rep['extra_fields']):
        for token_ordinal, raw in enumerate(extra.split(',')):
            field, separator, token = raw.partition(':')
            if not separator or field not in c.AUXILIARY_FIELDS: continue
            metadata = deepcopy(c.AUXILIARY_FIELDS[field])
            unit = metadata.pop('unit')
            number = c.auxiliary_number(field, token, location)
            reported = dict(availability='provided', number=number, unit=unit,
                precision=c.native_precision(token, 'fixed_2' if field == 'Multiplicity' else 'fixed_1'))
            rep['native_auxiliary_measurements'].append(dict(field=field,
                extra_field_ordinal_0based=extra_ordinal, token_ordinal_0based=token_ordinal,
                raw_field=raw, reported=reported, **metadata))
            if field in present: rep['issues'].append('native_auxiliary_field_repeated')
            if number['state'] != 'available': rep['issues'].append('native_auxiliary_' + field + '_' + number['state'])
            if reported['precision'] == 'native_token': rep['issues'].append('native_auxiliary_print_precision_unclassified')
            present.append(field)
    rep['native_auxiliary_absent_fields'] = [field for field in c.AUXILIARY_FIELDS if field not in present]


def _observation(file, ordinal, line, representation=None):
    return dict(occurrence_id=c.identity('homer_occurrence', [file['file_id'], ordinal]),
        ordinal_0based=ordinal, location=deepcopy(line['location']), raw_fields=list(line['fields']),
        parse_state='complete', name=None, consensus=None, pwm_state='not_provided',
        representations=[] if representation is None else [representation], issues=[])


def _qualify(row):
    for rep in row['representations']:
        for field, record in rep['numbers'].items():
            number = record['number']
            if number is not None and number['state'] != 'available':
                rep['issues'].append('native_' + field + '_' + number['state'])
            if number is not None and record['precision'] == 'native_token':
                rep['issues'].append('native_' + field + '_print_precision_unclassified')
        rep['issues'] = list(dict.fromkeys(rep['issues']))
    if row['parse_state'] == 'complete' and (row['issues'] or any(r['issues'] for r in row['representations'])):
        row['parse_state'] = 'qualified'
    return row


def _series(file, execution):
    branch = 'known_outcome' if file['role'] == 'known_results' else 'denovo_outcome'
    return dict(series_id=c.identity('homer_series', file['file_id']), file_id=file['file_id'], role=file['role'],
        phase='final_saved_output', capture_state=file['capture']['state'], native_outcome=execution[branch],
        raw_header=[], displayed_totals=dict(target=None, background=None,
            meaning='wrapper_inferred_from_first_rounded_motif'), observations=[], issues=[])


def _known(file, lines, execution):
    series = _series(file, execution)
    if not lines:
        series['issues'].append('known_header_unavailable')
        return series
    header = lines[0]
    series['raw_header'] = list(header['fields'])
    fields = header['fields']
    target = re.fullmatch(r'# of Target Sequences with Motif\(of ([0-9]+)\)', fields[5]) if len(fields) == 9 else None
    background = re.fullmatch(r'# of Background Sequences with Motif\(of ([0-9]+)\)', fields[7]) if len(fields) == 9 else None
    valid = (header['valid'] and header['complete'] and fields[:5] == _KNOWN_PREFIX
        and target is not None and background is not None
        and fields[6] == '% of Target Sequences with Motif' and fields[8] == '% of Background Sequences with Motif')
    if valid:
        for role, match in (('target', target), ('background', background)):
            series['displayed_totals'][role] = native_number(match[1], source_location=header['location'], integer=True, minimum=0)
    else: series['issues'].append('known_header_truncated' if not header['complete'] else 'known_header_unrecognized')
    for ordinal, line in enumerate(lines[1:]):
        rep = _representation('known_table', line['fields'], line['location'])
        row = _observation(file, ordinal, line, rep)
        values = line['fields']
        if not line['complete']:
            row['parse_state'] = 'truncated'
            row['issues'].append('known_native_row_truncated')
        elif not valid or not line['valid'] or len(values) != 9:
            row['parse_state'] = 'malformed'
            row['issues'].append('known_native_row_unparsed')
        else:
            row['name'], row['consensus'] = values[:2]
            for field, token in c.representation_tokens('known_table', values).items():
                if field.endswith('percentage') and not values[c.TABLE_COLUMNS[field]].endswith('%'):
                    rep['issues'].append('native_percentage_suffix_missing')
                rep['numbers'][field] = _number(field, token, line['location'], c.expected_precision('known_table', field))
        series['observations'].append(_qualify(row))
    return series


def _pwms(file, lines):
    records, current = [], None
    for line in lines:
        if line['text'].startswith('>'):
            current = dict(header=line, rows=[])
            records.append(current)
        elif current is None:
            current = dict(header=None, rows=[line])
            records.append(current)
        else: current['rows'].append(line)
    observations = []
    for ordinal, record in enumerate(records):
        header = record['header']
        first = header or record['rows'][0]
        last = record['rows'][-1] if record['rows'] else first
        loc = deepcopy(first['location'])
        loc['byte_end_0based_exclusive'] = last['location']['byte_end_0based_exclusive']
        loc['line_end_1based_inclusive'] = last['location']['line_end_1based_inclusive']
        fields = list(header['fields']) if header is not None else list(first['fields'])
        if header is not None: fields[0] = fields[0][1:]
        rep = _representation('native_pwm', fields, loc)
        row = _observation(file, ordinal, first, rep)
        row['location'] = deepcopy(loc)
        if header is None or not header['valid'] or len(fields) < 6:
            row['parse_state'] = 'malformed'
            row['issues'].append('native_pwm_header_unparsed')
        else:
            row['consensus'], row['name'] = fields[:2]
            rep['native_gap_field'], rep['extra_fields'] = fields[4], fields[6:]
            _auxiliary(rep, header['location'])
            tokens = c.representation_tokens('native_pwm', fields)
            if 'p_value' not in tokens: rep['issues'].append('native_pwm_statistics_unparsed')
            for field, token in tokens.items():
                rep['numbers'][field] = _number(field, token, header['location'], c.expected_precision('native_pwm', field))
        for row_ordinal, line in enumerate(record['rows']):
            cells = [native_number(token, source_location=line['location'], minimum=0, maximum=1)
                for token in line['fields']] if line['valid'] and line['complete'] else []
            rep['pwm_rows'].append(dict(ordinal_0based=row_ordinal, raw_fields=list(line['fields']),
                location=deepcopy(line['location']), cells=cells))
            if not line['valid'] or len(line['fields']) != 4 or any(n['state'] != 'available' for n in cells):
                rep['issues'].append('native_pwm_row_qualified')
            if not line['complete']:
                row['parse_state'] = 'truncated'
                row['issues'].append('native_pwm_row_truncated')
        expected_length = len(row['consensus']) if row['consensus'] else None
        if not record['rows']: rep['issues'].append('native_pwm_rows_missing')
        if expected_length is not None and len(record['rows']) != expected_length:
            rep['issues'].append('native_pwm_length_mismatch')
        if file['capture']['state'] == 'truncated' and ordinal == len(records) - 1 and (
                not last['complete'] or expected_length is None or len(record['rows']) < expected_length):
            row['parse_state'] = 'truncated'
            row['issues'].append('native_pwm_record_capture_truncated')
        row['pwm_state'] = 'provided' if record['rows'] and not rep['issues'] and row['parse_state'] == 'complete' else 'partial'
        observations.append(_qualify(row))
    return observations


def _population_rows(file, lines):
    rows = []
    for line in lines:
        fields = line['fields']
        row = dict(ordinal_0based=line['ordinal'], member_id=fields[0] or None, raw_fields=list(fields),
            location=deepcopy(line['location']), state='complete', length_bp=None,
            group=None, weight=None, issues=[])
        if not line['complete']: row['state'] = 'truncated'
        elif not line['valid'] or len(fields) < 2 or not fields[0]: row['state'] = 'malformed'
        elif file['role'] == 'sequence_table':
            row['length_bp'] = len(fields[1])
            if not fields[1]: row['issues'].append('native_sequence_empty')
        else:
            row['group'] = c.native_group(fields[1])
            if row['group'] is None: row['issues'].append('native_group_semantics_unresolved')
            if len(fields) >= 3:
                row['weight'] = native_number(fields[2], source_location=line['location'], minimum=0)
                if row['weight']['state'] != 'available': row['issues'].append('native_group_weight_qualified')
            else: row['issues'].append('native_group_weight_not_reported')
        if row['state'] != 'complete': row['issues'].append('native_population_row_' + row['state'])
        rows.append(row)
    return rows


def _populations(files, lines_by_id):
    seq_files = [f for f in files if f['role'] == 'sequence_table']
    group_files = [f for f in files if f['role'] == 'group_weights']
    seq = [r for f in seq_files for r in _population_rows(f, lines_by_id[f['file_id']])]
    groups = [r for f in group_files for r in _population_rows(f, lines_by_id[f['file_id']])]
    memberships = c.population_memberships(seq, groups)
    sequence_ids, group_ids = [f['file_id'] for f in seq_files], [f['file_id'] for f in group_files]
    state = c.population_state(files, sequence_ids, group_ids, seq, groups, memberships)
    issues = []
    if len(seq_files) != 1 or len(group_files) != 1: issues.append('population_file_selection_ambiguous_or_missing')
    if not seq or not groups: issues.append('native_input_population_not_established')
    if any(m['state'] != 'unique' for m in memberships): issues.append('native_input_membership_incomplete_or_ambiguous')
    if state != 'complete': issues.append('reported_input_weight_sum_unavailable')
    return dict(state=state, sequence_file_ids=sequence_ids, group_file_ids=group_ids,
        sequence_rows=seq, group_rows=groups, memberships=memberships, issues=issues)


def parse_homer_motif_sheet(files, *, invocation, execution):
    invocation, execution = c.validated('Invocation', invocation), c.validated('Execution', execution)
    c.require(type(files) is list, 'files_invalid')
    metadata = [_file(value) for value in files]
    c.require(len({f['native_relative_path'] for f in metadata}) == len(metadata), 'duplicate_file_path')
    lines_by_id = {f['file_id']: _lines(f, value['content']) for f, value in zip(metadata, files)}
    series, sidecars, auxiliary = [], [], []
    for file in metadata:
        lines = lines_by_id[file['file_id']]
        if file['role'] == 'known_results': series.append(_known(file, lines, execution))
        elif file['role'] in _SERIES_ROLES:
            row = _series(file, execution)
            row['observations'] = _pwms(file, lines)
            series.append(row)
        elif file['role'] == 'known_pwm':
            sidecars.append(dict(file_id=file['file_id'], native_ordinal_0based=c.known_pwm_ordinal(file['native_relative_path']),
                linked_series_id=None, linked_ordinal_0based=None, state='unlinked',
                observations=_pwms(file, lines), issues=[]))
        elif file['role'] in ('normalization_table', 'native_log'):
            for line in lines:
                auxiliary.append(dict(file_id=file['file_id'], ordinal_0based=line['ordinal'],
                    phase='native_diagnostic' if file['role'] == 'native_log' else 'native_normalization_report_unspecified',
                    raw_fields=list(line['fields']), raw_hex=None if line['valid'] else line['raw'].hex(),
                    location=deepcopy(line['location']), complete=line['complete']))
    known = [s for s in series if s['role'] == 'known_results']
    for sidecar in sidecars:
        ordinal, observations = sidecar['native_ordinal_0based'], sidecar['observations']
        candidates = [(s, r) for s in known for r in s['observations'] if r['ordinal_0based'] == ordinal]
        duplicates = sum(s['native_ordinal_0based'] == ordinal for s in sidecars) if ordinal is not None else 0
        if len(candidates) > 1 or duplicates > 1:
            sidecar['state'] = 'ambiguous'
            if len(candidates) == 1: candidates[0][1]['pwm_state'] = 'conflict'
        elif len(candidates) == 1 and len(observations) == 1:
            s, target = candidates[0]
            source = observations[0]
            if c.sidecar_matches(source, target):
                sidecar.update(state='linked', linked_series_id=s['series_id'], linked_ordinal_0based=ordinal)
                target['representations'].extend(deepcopy(source['representations']))
                target['pwm_state'] = source['pwm_state']
            else:
                sidecar['state'] = 'conflict'
                target['pwm_state'] = 'conflict'
        if sidecar['state'] != 'linked': sidecar['issues'].append('known_pwm_' + sidecar['state'])
    for series_value in known:
        for row in series_value['observations']: _qualify(row)
    sheet = dict(version=c.SHEET_VERSION, invocation=invocation, execution=execution, files=metadata,
        series=series, sidecars=sidecars, populations=_populations(metadata, lines_by_id),
        auxiliary_rows=auxiliary, issues=[])
    return c.validate_homer_sheet(sheet)


def _evidence(files):
    return [dict(content=dict(source_ref=f['artifact']['source_ref'], artifact_field='artifact_ref',
        artifact_ref=f['artifact']['raw_artifact_ref'], sha256=f['artifact']['sha256'],
        byte_count=f['artifact']['size_bytes']), pointer='') for f in files if f['artifact'] is not None]


def calculate_homer_components(sheet, *, selector):
    sheet, selector = c.validate_homer_sheet(sheet), c.validate_homer_selector(selector)
    by_id = {s['series_id']: s for s in sheet['series']}
    c.require(all(key in by_id for key in selector['series_ids']), 'selected_series_missing')
    files = {file['file_id']: file for file in sheet['files']}
    available_series = []
    for series in sheet['series']:
        native_name = files[series['file_id']]['native_relative_path'].rsplit('/', 1)[-1]
        length = next((length for length in sheet['invocation']['selected_motif_lengths']
            if series['role'] == 'denovo_pwm' and native_name == 'homerMotifs.motifs' + str(length)), None)
        available_series.append(dict(series_id=series['series_id'], role=series['role'],
            requested_motif_length_bp=length, capture_state=series['capture_state'],
            native_outcome=series['native_outcome']))
    ordered = [(key, row['occurrence_id']) for key in selector['series_ids'] for row in by_id[key]['observations']]
    chosen = set(ordered[selector['offset']:selector['offset'] + selector['limit']])
    selected, counts = [], []
    for key in selector['series_ids']:
        series = deepcopy(by_id[key])
        series['observations'] = [r for r in series['observations'] if (key, r['occurrence_id']) in chosen]
        selected.append(series)
        counts.append(dict(series_id=key, role=series['role'],
            captured_occurrences=len(by_id[key]['observations']), selected_occurrences=len(series['observations']),
            capture_state=series['capture_state'], native_outcome=series['native_outcome']))
    populations = sheet['populations']
    weight_completeness = {group: 'complete' if c.reported_group_weight_complete(sheet['files'], populations, group)
        else 'unavailable' for group in ('target', 'background')}
    facts = dict(state=populations['state'], selected_window_bp=sheet['invocation']['selected_window_bp'],
        captured_sequence_occurrences=len(populations['sequence_rows']), captured_group_occurrences=len(populations['group_rows']),
        unique_joined_target_members=sum(m['state'] == 'unique' and m['group'] == 'target' for m in populations['memberships']),
        unique_joined_background_members=sum(m['state'] == 'unique' and m['group'] == 'background' for m in populations['memberships']),
        observed_sequence_lengths_bp=sorted({r['length_bp'] for r in populations['sequence_rows'] if r['length_bp'] is not None}),
        reported_weight_completeness=weight_completeness,
        meaning='captured_input_occurrences_not_effective_native_denominators')
    weight_sums = []
    population_files = [f for f in sheet['files'] if f['file_id'] in
        populations['sequence_file_ids'] + populations['group_file_ids']]
    for group in ('target', 'background'):
        value, state, issues = None, 'missing', []
        if weight_completeness[group] == 'complete':
            values = [r['weight']['value'] for r in populations['group_rows'] if r['group'] == group]
            try:
                value = math.fsum(values)
                if not math.isfinite(value): raise OverflowError('nonfinite reported input weight sum')
                state = 'available'
            except (OverflowError, ValueError):
                value, state = None, 'failed'
                issues.append('reported_input_weight_sum_nonfinite')
        else: issues.append('reported_input_weight_population_unavailable')
        cell = numeric_cell(value, state=state, unit='relative_weight', origin='calculated',
            population_id=c.identity('homer_input_population', [populations['sequence_file_ids'], populations['group_file_ids'], group]),
            method_id='homer_reported_input_weight_fsum_v1', evidence=_evidence(population_files))
        weight_sums.append(dict(group=group, meaning='reported_input_weight_sum',
            basis='derived_from_reported_weights', cell=cell, issues=issues))
    return c.validated('Components', dict(version=c.COMPONENTS_VERSION, selector=selector,
        available_series=available_series,
        execution=deepcopy(sheet['execution']), selected_series=selected, counts=counts,
        population_facts=facts, reported_input_weight_sums=weight_sums,
        issues=deepcopy(sheet['issues'] + populations['issues'])))


def project_homer_return(components, *, source_ref):
    components = c.validated('Components', components)
    def public(node):
        if type(node) is dict:
            return {key: public(value) for key, value in node.items()
                if key not in ('source_location', 'location', 'file_id', 'evidence', 'requirement_ids')}
        if type(node) is list: return [public(value) for value in node]
        return deepcopy(node)
    result = public(components)
    result.update(version=c.RETURN_VERSION, source_ref=source_ref)
    return c.validated('Return', result)


validate_homer_sheet = c.validate_homer_sheet
validate_homer_selector = c.validate_homer_selector
homer_record_schema = c.homer_record_schema

__all__ = ['parse_homer_motif_sheet', 'validate_homer_sheet', 'validate_homer_selector',
    'calculate_homer_components', 'project_homer_return', 'homer_record_schema']
