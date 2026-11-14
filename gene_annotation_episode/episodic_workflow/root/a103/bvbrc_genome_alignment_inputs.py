"""Extract GenomeAlignment inputs from saved receipts and explicitly supplied bytes.

The inspected producer logs native paths but retains no byte-at-invocation
proof. Candidate FASTA records therefore stay separate from observed path
placeholders. Their real lengths never become unresolved member denominators.
No Store, filesystem, network, native process or model is used by these calls.
"""
from copy import deepcopy
import hashlib
import re

from .bvbrc_appservice_contracts import ContractValidationError, _finite_json, _same, validate_contract
from .bvbrc_genome_alignment_input_contracts import (
    DIAGNOSTIC_CODES, validate_genome_alignment_inputs,
)
from .bvbrc_genome_alignment_retained_records import (
    PREFIX, RETAINED_RECORD_ERRORS, _canonical, _digest, _require,
    supplied_content, supplied_evidence, validate_retained_record_arguments,
    validate_genome_alignment_retained_records,
)


_RECIPES = ('progressiveMauve', 'mauveAligner')
_MODES = ('multiple_files_concatenated', 'single_file_entries')
_OPTIONS = (
    ('seedWeight', 'seed-weight'),
    ('maxGappedAlignerLength', 'max-gapped-aligner-length'),
    ('maxBreakpointDistanceScale', 'max-breakpoint-distance-scale'),
    ('conservationDistanceScale', 'conservation-distance-scale'),
    ('weight', 'weight'), ('minScaledPenalty', 'min-scaled-penalty'),
    ('hmmPGoHomologous', 'hmm-p-go-homologous'),
    ('hmmPGoUnrelated', 'hmm-p-go-unrelated'),
)
# The exact inspected source can supply an explicitly labelled expectation,
# never a deployed-program or native-version attestation.
_P3_SOURCE_SHA256 = '708528e8740b6bb17ffdd7d5cbd36965b5ad9d96a1395e88361d87b94225dd60'
_DNA = re.compile(r'[ACGTRYSWKMBDHVNacgtryswkmbdhvn]*\Z')
_COMMAND = re.compile(r'Running (progressiveMauve|mauveAligner) with params:  (--output=.+)\Z')
_EXIT = re.compile(r'child process exited with code (-?[0-9]+|null)\Z')
_KINDS = ('genome_alignment_invocation', 'genome_alignment_staged_file',
          'genome_alignment_contig_identity', 'genome_alignment_feature_mapping',
          'genome_alignment_interval_mapping', 'genome_alignment_producer')


def _shape(value, fields):
    _require(type(value) is dict and set(value) == set(fields), 'argument_invalid')


def _text(value, *, nullable=False, empty=False):
    _require(nullable and value is None or type(value) is str and (empty or bool(value)), 'argument_invalid')


def _uint(value, *, nullable=False):
    _require(nullable and value is None or type(value) is int and value >= 0, 'argument_invalid')


def _enum(value, choices, *, nullable=False):
    _require(nullable and value is None or type(value) is str and value in choices, 'argument_invalid')


def _array(value, check):
    _require(type(value) is list, 'argument_invalid')
    for item in value:
        check(item)


def _contract(name, value):
    try:
        validate_contract(name, value)
    except ContractValidationError as error:
        raise ValueError(PREFIX + 'argument_invalid') from error


def _artifact_shape(value):
    _shape(value, ('raw_artifact_ref', 'source_ref', 'sha256'))
    for key in ('raw_artifact_ref', 'source_ref'):
        _text(value[key])
    _require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None,
             'argument_invalid')


def _interval_shape(value):
    _array(value, _uint)
    _require(len(value) == 2, 'argument_invalid')


def _occurrence_shape(value):
    _shape(value, ('input_binding_id', 'member_id', 'occurrence_index'))
    _text(value['input_binding_id'])
    _text(value['member_id'])
    _uint(value['occurrence_index'])


def _segment_shape(value):
    _shape(value, ('segment_id', 'file_id', 'record_id', 'feature_interval_0based_half_open',
                   'record_interval_0based_half_open', 'strand', 'transformation_id', 'evidence'))
    for key in ('segment_id', 'file_id', 'record_id', 'transformation_id'):
        _text(value[key])
    for key in ('feature_interval_0based_half_open', 'record_interval_0based_half_open'):
        _interval_shape(value[key])
    _enum(value['strand'], ('+', '-'))
    _array(value['evidence'], lambda v: _contract('SourceEvidence', v))


def _retrieval_shape(value):
    _shape(value, ('query', 'requested_record_limit', 'reported_total_records',
                   'returned_records', 'state', 'evidence'))
    _text(value['query'], nullable=True, empty=True)
    for key in ('requested_record_limit', 'reported_total_records'):
        _uint(value[key], nullable=True)
    _uint(value['returned_records'])
    _enum(value['state'], ('complete', 'partial', 'unknown', 'conflicting'))
    _array(value['evidence'], lambda v: _contract('SourceEvidence', v))


def validate_genome_alignment_supplied_value_shapes(supplied_values: tuple) -> None:
    """Check wrapper and six frozen metadata variants; admit no native claims."""
    _require(type(supplied_values) is tuple, 'argument_invalid')
    for row in supplied_values:
        _shape(row, ('evidence', 'value'))
        _contract('SourceEvidence', row['evidence'])
        value = row['value']
        try:
            _finite_json(value)
        except ContractValidationError as error:
            raise ValueError(PREFIX + 'argument_invalid') from error
        # ResultSelector metadata can also carry an actual receipt /value for
        # host collection. It is not one of this provider's metadata variants.
        if type(value) is not dict or type(value.get('kind')) is not str or value['kind'] not in _KINDS:
            continue
        kind = value['kind']
        fields = {
            _KINDS[0]: ('argv', 'program_version', 'ordered_file_ids', 'mode'),
            _KINDS[1]: ('file_id', 'native_path_token', 'content', 'genome_occurrence_indices', 'retrieval'),
            _KINDS[2]: ('file_id', 'record_id', 'sequence_id', 'accession', 'accession_version', 'genome_occurrence_indices'),
            _KINDS[3]: ('feature', 'original_length', 'genome_occurrence_index', 'segments'),
            _KINDS[4]: ('bbcols_artifact', 'xmfa_artifact', 'mappings', 'omitted_native_interval_indices'),
            _KINDS[5]: ('application_id', 'recipe', 'producer_source', 'native_version', 'output_artifacts'),
        }[kind]
        _shape(value, ('kind', 'original_task_id', *fields))
        _text(value['original_task_id'])
        if kind == _KINDS[0]:
            _array(value['argv'], lambda v: _text(v, empty=True))
            _array(value['ordered_file_ids'], _text)
            _text(value['program_version'], nullable=True)
            _enum(value['mode'], _MODES)
        elif kind == _KINDS[1]:
            _text(value['file_id'])
            _text(value['native_path_token'])
            _contract('ContentBinding', value['content'])
            _array(value['genome_occurrence_indices'], _uint)
            _retrieval_shape(value['retrieval'])
        elif kind == _KINDS[2]:
            for key in ('file_id', 'record_id'):
                _text(value[key])
            for key in ('sequence_id', 'accession', 'accession_version'):
                _text(value[key], nullable=True)
            _array(value['genome_occurrence_indices'], _uint)
        elif kind == _KINDS[3]:
            _occurrence_shape(value['feature'])
            _uint(value['original_length'])
            _uint(value['genome_occurrence_index'])
            _array(value['segments'], _segment_shape)
        elif kind == _KINDS[4]:
            _artifact_shape(value['bbcols_artifact'])
            _artifact_shape(value['xmfa_artifact'])
            _require(type(value['mappings']) is list, 'argument_invalid')
            for mapping in value['mappings']:
                _shape(mapping, ('native_interval_index_0based', 'xmfa_block_index'))
                for item in mapping.values():
                    _uint(item)
            _array(value['omitted_native_interval_indices'], _uint)
        else:
            _enum(value['application_id'], ('GenomeAlignment',))
            _enum(value['recipe'], _RECIPES)
            _contract('ContentBinding', value['producer_source'])
            _text(value['native_version'], nullable=True)
            _array(value['output_artifacts'], _artifact_shape)


class _Reports:
    def __init__(self):
        self.requirements = []
        self.diagnostics = []

    def add(self, suffix, path, *, kind='input_metadata', role=None, refs=(),
            identity=None, severity='qualification', requirement=True):
        code = suffix if suffix.startswith(PREFIX) else PREFIX + suffix
        assert code in DIAGNOSTIC_CODES
        refs = list(dict.fromkeys(refs))
        diagnostic = {'code': code, 'phase': 'association', 'path': path,
                      'severity': severity, 'evidence_refs': refs}
        if diagnostic not in self.diagnostics:
            self.diagnostics.append(diagnostic)
        if not requirement:
            return None
        requirement_id = 'ga_requirement_' + _digest([code, kind, role, refs, identity or path])
        row = {'requirement_id': requirement_id, 'kind': kind, 'role': role,
               'source_refs': refs, 'reason_code': code}
        if row not in self.requirements:
            self.requirements.append(row)
        return requirement_id


def _record_evidence(row, pointer):
    return {'content': deepcopy(row['receipt_content']), 'pointer': pointer}


def _retained(original_task, records, data, report):
    accepted = []
    # Detect a conflicting source even if one of its representations fails
    # its own byte checks. It must never win by input order.
    groups = {}
    for index, row in enumerate(records):
        groups.setdefault(row['record']['source_ref'], []).append((index, row))
    conflicts = {ref for ref, rows in groups.items()
                 if any(not _same(rows[0][1], row) for _, row in rows[1:])}
    for index, row in enumerate(records):
        record, path = row['record'], '/retained_records/' + str(index)
        ref = record['source_ref']
        if ref in conflicts:
            report.add('metadata_record_unverified', path, refs=(ref,), severity='error', identity=ref)
        try:
            checked = validate_genome_alignment_retained_records(original_task,
                retained_records=(row,), supplied_bytes=data)[0]
        except ValueError as error:
            if str(error) not in RETAINED_RECORD_ERRORS:
                raise
            role = (record['value']['artifact']['role'] if record['contract'] == 'AcquisitionReceipt'
                    else 'genome_alignment_invocation' if record['contract'] == 'TaskInfoReceipt' and
                    record['value']['file'] in ('stdout', 'stderr') else None)
            kind = ('original_task' if str(error) == PREFIX + 'metadata_task_conflict' else
                    'output_bytes' if record['contract'] == 'AcquisitionReceipt' and
                    str(error) in (PREFIX + 'content_missing', PREFIX + 'content_digest_conflict')
                    else 'input_metadata')
            report.add(str(error), path, kind=kind, role=role, refs=(ref,), severity='error', identity=ref)
            continue
        if ref not in conflicts and not any(_same(checked, item[1]) for item in accepted):
            accepted.append((index, checked))
    # The original handoff's exact request includes bindings absent from
    # OriginalTask. Reject differently bound requests without losing the handoff.
    handoffs = [row for _, row in accepted if row['record']['contract'] == 'TaskHandoff']
    if handoffs:
        request = handoffs[0]['record']['value']['receipt']['snapshot']['selected_operands']['native_operands']['request']
        kept = []
        for index, row in accepted:
            value = row['record']['value']
            snapshot = value['snapshot'] if row['record']['contract'] == 'AcquisitionReceipt' else value['receipt']['snapshot']
            if not _same(snapshot['selected_operands']['native_operands']['request'], request):
                report.add('metadata_task_conflict', f'/retained_records/{index}/record/value',
                           kind='original_task', refs=(row['record']['source_ref'],), severity='error')
            else:
                kept.append((index, row))
        accepted = kept
    return accepted


def _occurrences(task, accepted, report):
    ids = task['submitted_parameters']['genome_ids']
    handoffs = [r for _, r in accepted if r['record']['contract'] == 'TaskHandoff']
    handoff = handoffs[0] if handoffs else None
    bindings = ([] if handoff is None else handoff['record']['value']['receipt']['snapshot']
                ['selected_operands']['native_operands']['request']['input_bindings'])
    if handoff is None:
        report.add('metadata_record_unverified', '/original_task/submission_receipt_ref',
                   kind='original_task', refs=(task['submission_receipt_ref'],))
    result = []
    for index, genome_id in enumerate(ids):
        pointer = '/genome_ids/' + str(index)
        evidence = ([] if handoff is None else
                    [_record_evidence(handoff, '/value/original_task/submitted_parameters' + pointer)])
        matches = []
        for binding_index, binding in enumerate(bindings):
            scalar = (binding['kind'] in ('inline_parameter', 'supplied_link') and
                      binding['parameter_pointer'] == pointer and _same(binding['inline_value'], genome_id))
            group = (binding['kind'] == 'inline_parameter' and binding['parameter_pointer'] == '/genome_ids'
                     and _same(binding['inline_value'], ids))
            if scalar or group:
                matches.append((binding_index, binding))
        binding_id = None
        if len(matches) == 1:
            binding_index, binding = matches[0]
            binding_id = binding['binding_id']
            evidence.append(_record_evidence(handoff,
                f'/value/receipt/snapshot/selected_operands/native_operands/request/input_bindings/{binding_index}'))
        elif len(matches) > 1:
            report.add('genome_occurrence_conflict', '/genome_occurrences/' + str(index),
                       kind='original_task', refs=(handoff['record']['source_ref'],), severity='error')
        if genome_id in ids[:index]:
            report.add('duplicate_genome_occurrence', '/genome_occurrences/' + str(index),
                       refs=tuple(e['content']['source_ref'] for e in evidence), requirement=False)
        result.append({'occurrence_index': index, 'genome_id': genome_id,
                       'parameter_pointer': pointer, 'input_binding_id': binding_id, 'evidence': evidence})
    return result


def _log_candidate(value, raw, genome_ids):
    """Decode the pinned producer's emitted token/event grammar, not shell text."""
    snapshot = value['receipt']['snapshot']
    _require(value['body_complete'] and value['local_window'] is None and
             snapshot['transport']['body_complete'] and 200 <= snapshot['transport']['status'] < 300 and
             value['receipt']['status'] in ('ok', 'partial'), 'invocation_missing')
    try:
        text = raw.decode('utf-8')
    except UnicodeError as error:
        raise ValueError(PREFIX + 'invocation_missing') from error
    _require('\x00' not in text and '\r' not in text, 'invocation_conflict')
    lines = text.split('\n')
    starts = [i for i, line in enumerate(lines) if line.startswith('Running ') and ' with params:' in line]
    _require(bool(starts), 'invocation_missing')
    _require(len(starts) == 1, 'invocation_conflict')
    start = starts[0]
    match = _COMMAND.fullmatch(lines[start])
    _require(match is not None, 'invocation_conflict')
    recipe, output = match.groups()
    _require(len(output) > len('--output=') and not output[len('--output='):].startswith('--'), 'invocation_conflict')
    count = len(genome_ids) * (2 if recipe == 'mauveAligner' else 1)
    # Every operand must have its own newline. EOF while still in the argument
    # group is missing, even if it happens to follow a plausible path token.
    _require(start + count + 1 < len(lines) - 1 or
             start + count + 1 < len(lines) and bool(lines[start + count + 1]), 'invocation_missing')
    operands = lines[start + 1:start + 1 + count]
    _require(len(operands) == count and all(operands), 'invocation_missing')
    paths = operands[::2] if recipe == 'mauveAligner' else operands
    _require(all(p.startswith('/') and not p.startswith('--') for p in paths), 'invocation_conflict')
    if recipe == 'mauveAligner':
        _require(all(operands[2*i+1] == path + '.sml' for i, path in enumerate(paths)), 'invocation_conflict')
    events = []
    for line in lines[:start]:
        if line.startswith('Fetching genome: '):
            events.append(('genome', line[len('Fetching genome: '):]))
        elif line.startswith('Writing ') and line.endswith('...'):
            events.append(('path', line[len('Writing '):-3]))
    expected = [event for genome_id, path in zip(genome_ids, paths)
                for event in (('genome', genome_id), ('path', path))]
    _require(events == expected, 'invocation_conflict')
    option_tokens, last_option = [], -1
    cursor = start + 1 + count
    names = [name for _, name in _OPTIONS]
    while cursor < len(lines) and lines[cursor].startswith('--'):
        token = lines[cursor]
        name, sep, argument = token[2:].partition('=')
        _require(sep and argument and name in names and names.index(name) > last_option,
                 'invocation_conflict')
        _require(cursor < len(lines) - 1, 'invocation_missing')
        last_option = names.index(name)
        option_tokens.append(token)
        cursor += 1
    _require(cursor < len(lines) - 1 or cursor < len(lines) and bool(lines[cursor]), 'invocation_missing')
    # The fixed number of file operands followed by ordered named options is
    # complete. A further file-looking token cannot be native stdout guessed
    # away as a delimiter. Ordinary program output is retained by the receipt.
    _require(not lines[cursor].startswith('/') and not lines[cursor].startswith('Fetching genome: '),
             'invocation_conflict')
    exits = [m.group(1) for line in lines[cursor:] if (m := _EXIT.fullmatch(line)) is not None]
    _require(len(exits) <= 1, 'invocation_conflict')
    return {'argv': [recipe, output, *operands, *option_tokens], 'paths': paths,
            'recipe': recipe, 'exit': exits[0] if exits else None}


def _retrieval(count=0):
    return {'query': None, 'requested_record_limit': None, 'reported_total_records': None,
            'returned_records': count, 'state': 'unknown', 'evidence': []}


def _placeholder(path, indices, evidence, report, *, ordinal=None):
    file_id = 'ga_path_' + _digest([path, ordinal])
    location = '/files/' + file_id
    ids = [report.add('staged_file_missing', location, kind='input_bytes',
                      role='genome_alignment_staged_input', refs=tuple(e['content']['source_ref'] for e in evidence)),
           report.add('staged_file_run_unverified', location, kind='byte_version_evidence',
                      role='genome_alignment_staged_input'),
           report.add('genome_census_unknown', location, role='genome_alignment_staged_input')]
    if path is None:
        ids.append(report.add('native_path_missing', location, role='genome_alignment_staged_input'))
    return {'file_id': file_id, 'native_path_token': path, 'path_state': 'bound' if path is not None else 'missing',
            'artifact': None, 'content': None, 'format': 'FastA', 'genome_occurrence_indices': indices,
            'same_run_state': 'missing', 'record_completeness': 'unknown', 'records': [],
            'retrieval': _retrieval(), 'path_evidence': deepcopy(evidence) if path is not None else [],
            'same_run_evidence': [], 'requirement_ids': ids}


def _invocation(task, accepted, data, report):
    requested = task['submitted_parameters'].get('recipe')
    invocation = {'requested_recipe': requested if requested in _RECIPES else None,
        'effective_recipe': None, 'recipe_basis': 'unknown', 'observed_argv': None,
        'observed_program_version': None, 'mode': 'unknown', 'mode_basis': 'unknown',
        'ordered_file_ids': [], 'evidence': []}
    ids, candidates, had_problem = task['submitted_parameters']['genome_ids'], [], False
    for index, row in accepted:
        record, value = row['record'], row['record']['value']
        if record['contract'] != 'TaskInfoReceipt' or value['file'] != 'stdout':
            continue
        path = f'/retained_records/{index}/record/value/receipt/snapshot'
        try:
            candidate = _log_candidate(value, supplied_content(value['receipt']['snapshot']['content'], data), ids)
        except ValueError as error:
            if str(error) not in (PREFIX + 'invocation_missing', PREFIX + 'invocation_conflict'):
                raise
            report.add(str(error), path, role='genome_alignment_invocation',
                       refs=(record['source_ref'],), severity='error')
            had_problem = had_problem or str(error) == PREFIX + 'invocation_conflict'
            continue
        candidates.append((candidate, _record_evidence(row, '/value/receipt/snapshot')))
    # Partial older snapshots do not erase a complete independent later record;
    # a genuine contradictory complete command must not be resolved by recency.
    unique = []
    for candidate, _ in candidates:
        if not any(candidate['argv'] == prior['argv'] for prior in unique):
            unique.append(candidate)
    if len(unique) > 1 or had_problem:
        invocation.update(recipe_basis='conflicting', mode_basis='conflicting')
        report.add('invocation_conflict', '/invocation', role='genome_alignment_invocation',
                   refs=tuple(e['content']['source_ref'] for _, e in candidates), severity='error')
        return invocation, []
    if not unique:
        report.add('invocation_missing', '/invocation', role='genome_alignment_invocation')
        return invocation, []
    candidate = unique[0]
    evidence = [e for _, e in candidates]
    recipe = candidate['recipe']
    invocation.update(effective_recipe=recipe, recipe_basis='observed_argv',
                      observed_argv=candidate['argv'], evidence=evidence)
    if requested is not None and requested != recipe:
        invocation.update(effective_recipe=None, recipe_basis='conflicting')
        report.add('recipe_conflict', '/invocation/requested_recipe', role='genome_alignment_invocation', severity='error')
    files, by_path = [], {}
    for index, path in enumerate(candidate['paths']):
        if path not in by_path:
            file = _placeholder(path, [], evidence, report)
            by_path[path] = file
            files.append(file)
        by_path[path]['genome_occurrence_indices'].append(index)
        invocation['ordered_file_ids'].append(by_path[path]['file_id'])
    if len(candidate['paths']) > 1:
        invocation.update(mode='multiple_files_concatenated', mode_basis='observed_invocation')
    elif recipe == 'progressiveMauve':
        invocation.update(mode='single_file_entries', mode_basis='observed_invocation')
    else:
        report.add('invocation_missing', '/invocation/mode', role='genome_alignment_invocation')
    exits = {c['exit'] for c, _ in candidates if c['exit'] is not None}
    if exits != {'0'}:
        report.add('native_execution_unverified', '/invocation', kind='output_metadata',
                   role='genome_alignment_primary', refs=tuple(e['content']['source_ref'] for e in evidence))
    return invocation, files


def _fasta(raw, artifact, file_id):
    """Read every DNA FASTA record; keep valid neighbors with original ordinals.

    A malformed record is not shortened into a different sequence. Its bytes
    remain in the bound artifact and its ordinal remains absent from the parsed
    list, with partial completeness reported. EOF without LF is not by itself a
    transport truncation signal in FASTA.
    """
    parts = raw.split(b'\n')
    lines = [part + b'\n' for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    records, issues, invalid_symbols, current, offset, ordinal = [], [], [], None, 0, 0

    def finish(end, line_end):
        if current is None:
            return
        if current['valid'] and current['parts']:
            records.append({'record_id': file_id + ':record:' + str(current['ordinal']),
                'entry_1based': current['ordinal'], 'header': current['header'],
                'sequence': ''.join(current['parts']), 'source_location': {
                    'artifact': deepcopy(artifact), 'byte_start_0based': current['start'],
                    'byte_end_0based_exclusive': end, 'line_start_1based': current['line'],
                    'line_end_1based_inclusive': line_end, 'xml_path': None}})
        else:
            issues.append(current['ordinal'])

    for number, line in enumerate(lines, 1):
        # Accept native LF and CRLF line endings; embedded controls are invalid.
        body = line[:-2] if line.endswith(b'\r\n') else line[:-1] if line.endswith(b'\n') else line
        if body.startswith(b'>'):
            finish(offset, number - 1)
            ordinal += 1
            try:
                header = body[1:].decode('utf-8')
                valid = not any(c in header for c in '\r\x00')
            except UnicodeError:
                header, valid = None, False
            current = {'header': header, 'valid': valid, 'parts': [], 'ordinal': ordinal,
                       'start': offset, 'line': number}
        elif current is None:
            if body:
                issues.append(0)
        else:
            try:
                sequence = body.decode('ascii')
                valid = _DNA.fullmatch(sequence) is not None
            except UnicodeError:
                sequence, valid = '', False
            if not valid:
                invalid_symbols.append(current['ordinal'])
            current['valid'] = current['valid'] and valid
            if sequence:
                current['parts'].append(sequence)
        offset += len(line)
    finish(len(raw), len(lines))
    if not records:
        issues.append(0)
    return records, sorted(set(issues)), sorted(set(invalid_symbols))


def _candidate_file(value, evidence, data, accepted, report, index):
    content, file_id = deepcopy(value['content']), value['file_id']
    path = f'/supplied_values/{index}/value'
    refs = (evidence['content']['source_ref'], content['source_ref'])
    ids = [report.add('metadata_record_unverified', path, role='genome_alignment_staged_input', refs=refs),
           report.add('staged_file_run_unverified', path, kind='byte_version_evidence',
                      role='genome_alignment_staged_input', refs=refs),
           report.add('genome_census_unknown', path, role='genome_alignment_staged_input', refs=refs)]
    artifact, records, completeness, partial = None, [], 'unknown', False
    same_run_state = 'missing'
    try:
        raw = supplied_content(content, data)
    except ValueError as error:
        if str(error) not in RETAINED_RECORD_ERRORS:
            raise
        ids.append(report.add(str(error), path + '/content', kind='input_bytes',
                              role='genome_alignment_staged_input', refs=refs, severity='error'))
        if str(error) == PREFIX + 'content_digest_conflict':
            same_run_state = 'conflicting'
        content = None
    else:
        artifact = {'raw_artifact_ref': content['artifact_ref'], 'source_ref': content['source_ref'],
                    'sha256': content['sha256']}
        records, issues, invalid_symbols = _fasta(raw, artifact, file_id)
        if invalid_symbols:
            ids.append(report.add('source_sequence_mismatch', path + '/content', kind='input_bytes',
                                  role='genome_alignment_staged_input', refs=refs, severity='error'))
        partial, transfer_unknown, transport_incomplete = bool(issues), False, False
        same_run_state = 'unverified'
        for _, row in accepted:
            if row['record']['contract'] != 'AcquisitionReceipt':
                continue
            acquired = row['record']['value']['artifact']
            if all(acquired[k] == artifact[k] for k in artifact):
                transfer = acquired['transfer']
                transport_incomplete = transport_incomplete or not transfer['body_complete'] or transfer['object_complete'] == 'no'
                transfer_unknown = transfer_unknown or transfer['object_complete'] == 'unknown'
        if transport_incomplete:
            # Withhold an unterminated final population member: a truncated
            # transport can end after any valid-looking nucleotide. Earlier
            # records delimited by another header still remain full records.
            records = [r for r in records if r['source_location']['byte_end_0based_exclusive'] < len(raw)]
        partial = partial or transport_incomplete
        # Supplied bytes are a complete retained representation unless an
        # actual matching acquisition explicitly qualifies its transfer.
        completeness = 'partial' if partial else 'unknown' if transfer_unknown else 'complete'
        if partial:
            ids.append(report.add('source_records_partial', path + '/content', kind='input_bytes',
                                  role='genome_alignment_staged_input', refs=refs, severity='error'))
    return {'file_id': file_id, 'native_path_token': value['native_path_token'],
            'path_state': 'unverified', 'artifact': artifact, 'content': content, 'format': 'FastA',
            'genome_occurrence_indices': [], 'same_run_state': same_run_state,
            'record_completeness': completeness, 'records': records,
            'retrieval': _retrieval(len(records)), 'path_evidence': [deepcopy(evidence)],
            'same_run_evidence': [], 'requirement_ids': ids}


def _metadata_conflicts(value, files, genome_ids):
    """Reject contradictory typed assertions without admitting their cause."""
    kind, conflicts = value['kind'], []
    indices = value.get('genome_occurrence_indices')
    if indices is not None and (len(set(indices)) != len(indices) or
                               any(i >= len(genome_ids) for i in indices)):
        conflicts.append('genome_occurrence_conflict')
    if kind == 'genome_alignment_staged_file':
        population = value['retrieval']
        if population['state'] == 'complete' and (population['reported_total_records'] is None or
                population['reported_total_records'] != population['returned_records'] or not population['evidence']):
            conflicts.append('genome_census_unknown')
    elif kind == 'genome_alignment_feature_mapping':
        if value['genome_occurrence_index'] >= len(genome_ids):
            conflicts.append('genome_occurrence_conflict')
        segment_ids = []
        for segment in value['segments']:
            segment_ids.append(segment['segment_id'])
            a, b = segment['feature_interval_0based_half_open']
            x, y = segment['record_interval_0based_half_open']
            source = [f for f in files if f['file_id'] == segment['file_id']]
            records = [r for f in source for r in f['records'] if r['record_id'] == segment['record_id']]
            if (b < a or y < x or b - a != y - x or b > value['original_length'] or
                    len(records) != 1 or y > len(records[0]['sequence'])):
                conflicts.append('feature_map_conflict')
        if len(segment_ids) != len(set(segment_ids)):
            conflicts.append('feature_map_conflict')
    elif kind == 'genome_alignment_interval_mapping':
        internal = [m['native_interval_index_0based'] for m in value['mappings']]
        exported = [m['xmfa_block_index'] for m in value['mappings']]
        omitted = value['omitted_native_interval_indices']
        if (len(set(internal)) != len(internal) or len(set(exported)) != len(exported) or
                len(set(omitted)) != len(omitted) or set(internal) & set(omitted)):
            conflicts.append('interval_join_conflict')
    return list(dict.fromkeys(conflicts))


def extract_genome_alignment_inputs(original_task: dict, *, supplied_values: tuple,
                                   supplied_bytes: dict[str, bytes], retained_records: tuple) -> dict:
    """Return the frozen InputExtraction shape from supplied data only."""
    validate_retained_record_arguments(original_task, retained_records=retained_records,
                                      supplied_bytes=supplied_bytes)
    validate_genome_alignment_supplied_value_shapes(supplied_values)
    report = _Reports()
    task = deepcopy(original_task)
    if task['required_application_id'] != 'GenomeAlignment' or task['native_application_id'] != 'GenomeAlignment':
        report.add('application_mismatch', '/original_task', kind='original_task', severity='error')
        return {'status': 'invalid', 'value': None, 'requirements': report.requirements, 'diagnostics': report.diagnostics}
    genome_ids = task['submitted_parameters'].get('genome_ids')
    if type(genome_ids) is not list or not genome_ids or any(type(g) is not str or not g for g in genome_ids):
        report.add('genome_input_missing', '/original_task/submitted_parameters/genome_ids',
                   kind='original_task', severity='error')
        return {'status': 'invalid', 'value': None, 'requirements': report.requirements, 'diagnostics': report.diagnostics}
    accepted = _retained(task, retained_records, supplied_bytes, report)
    occurrences = _occurrences(task, accepted, report)
    invocation, files = _invocation(task, accepted, supplied_bytes, report)
    requested = task['submitted_parameters'].get('recipe')
    if requested is not None and requested not in _RECIPES:
        invocation['recipe_basis'] = 'conflicting'
        invocation['effective_recipe'] = None
        report.add('recipe_conflict', '/original_task/submitted_parameters/recipe',
                   role='genome_alignment_invocation', severity='error')
    source_evidence, metadata = [], []
    for index, wrapper in enumerate(supplied_values):
        evidence, value = wrapper['evidence'], wrapper['value']
        path, refs = f'/supplied_values/{index}', (evidence['content']['source_ref'],)
        supported = type(value) is dict and type(value.get('kind')) is str and value['kind'] in _KINDS
        try:
            _require(_same(supplied_evidence(evidence, supplied_bytes), value))
        except ValueError as error:
            if str(error) not in RETAINED_RECORD_ERRORS:
                raise
            report.add(str(error), path + '/evidence', role=value['kind'] if supported else None,
                       refs=refs, severity='error')
            continue
        if not supported:
            report.add('metadata_type_unsupported', path + '/value', refs=refs)
            continue
        metadata.append((index, value, evidence))
        if value['original_task_id'] != task['task_id']:
            report.add('metadata_task_conflict', path + '/value/original_task_id',
                       kind='original_task', refs=refs, severity='error')
            # Bytes remain independently interpretable candidate data.
            if value['kind'] != 'genome_alignment_staged_file':
                continue
        if value['kind'] == 'genome_alignment_producer':
            try:
                source = supplied_content(value['producer_source'], supplied_bytes)
            except ValueError as error:
                if str(error) not in RETAINED_RECORD_ERRORS:
                    raise
                report.add(str(error), path + '/value/producer_source', role=value['kind'], refs=refs, severity='error')
            else:
                if hashlib.sha256(source).hexdigest() == _P3_SOURCE_SHA256:
                    source_evidence.append(evidence)
    staged = [(i, v, e) for i, v, e in metadata if v['kind'] == 'genome_alignment_staged_file']
    staged_groups = {}
    for item in staged:
        staged_groups.setdefault(item[1]['file_id'], []).append(item)
    used_ids = {f['file_id'] for f in files}
    for file_id, group in staged_groups.items():
        contradictory = file_id in used_ids or any(not _same(group[0][1], item[1]) for item in group[1:])
        if contradictory:
            # Preserve each conflicting byte candidate under a detached local
            # identity; an asserted ID does not authorize a path/record join.
            for index, value, evidence in group:
                report.add('native_path_conflict', f'/supplied_values/{index}/value/file_id',
                           role='genome_alignment_staged_input', refs=(evidence['content']['source_ref'],), severity='error')
                candidate = deepcopy(value)
                candidate['file_id'] = 'ga_candidate_' + _digest([file_id, value['content'], index])
                files.append(_candidate_file(candidate, evidence, supplied_bytes, accepted, report, index))
        else:
            index, value, evidence = group[0]
            candidate = _candidate_file(value, evidence, supplied_bytes, accepted, report, index)
            if value['original_task_id'] != task['task_id']:
                candidate['same_run_state'] = 'conflicting'
            files.append(candidate)
        used_ids.add(file_id)
    for index, value, evidence in metadata:
        kind, path = value['kind'], f'/supplied_values/{index}/value'
        for conflict in _metadata_conflicts(value, files, genome_ids):
            report.add(conflict, path, role=kind, refs=(evidence['content']['source_ref'],), severity='error')
        if kind == 'genome_alignment_staged_file':
            continue
        report.add('metadata_record_unverified', path, role=kind,
                   refs=(evidence['content']['source_ref'],))
        if kind == 'genome_alignment_contig_identity':
            matched = [f for f in files if f['file_id'] == value['file_id'] and
                       any(r['record_id'] == value['record_id'] for r in f['records'])]
            if not matched or any(i >= len(genome_ids) for i in value['genome_occurrence_indices']):
                report.add('contig_identity_conflict', path, role=kind,
                           refs=(evidence['content']['source_ref'],), severity='error')
        elif kind == 'genome_alignment_feature_mapping':
            report.add('feature_map_missing', path, role=kind, refs=(evidence['content']['source_ref'],))
        elif kind == 'genome_alignment_interval_mapping':
            report.add('interval_join_missing', path, kind='scientific_metadata',
                       role='genome_alignment_bbcols', refs=(evidence['content']['source_ref'],))
        elif kind == 'genome_alignment_invocation' and invocation['observed_argv'] is not None:
            if (value['argv'] != invocation['observed_argv'] or value['mode'] != invocation['mode'] or
                    value['ordered_file_ids'] != invocation['ordered_file_ids']):
                report.add('invocation_conflict', path, role=kind,
                           refs=(evidence['content']['source_ref'],), severity='error')
        elif kind == 'genome_alignment_producer' and invocation['observed_argv'] is not None:
            if value['recipe'] != invocation['observed_argv'][0]:
                report.add('recipe_conflict', path, role=kind,
                           refs=(evidence['content']['source_ref'],), severity='error')
    if source_evidence and requested is None and invocation['recipe_basis'] == 'unknown':
        invocation.update(effective_recipe='progressiveMauve', recipe_basis='retained_source_default',
                          evidence=deepcopy(source_evidence))
        # Only source expectations: no working path is invented.
        for index in range(len(genome_ids)):
            file = _placeholder(None, [], source_evidence, report, ordinal=index)
            files.append(file)
            invocation['ordered_file_ids'].append(file['file_id'])
        invocation.update(mode='multiple_files_concatenated' if len(genome_ids) > 1 else 'single_file_entries',
                          mode_basis='source_and_submitted_parameters')
    # Qualify inspected-source option behavior without rewriting observed argv.
    for parameter, option in _OPTIONS:
        supplied = task['submitted_parameters'].get(parameter)
        observed_options = (invocation['observed_argv'] or [])[1:]
        if type(supplied) in (int, float) and supplied == 0 and not any(
                token.startswith('--' + option + '=') for token in observed_options):
            report.add('explicit_zero_not_forwarded', '/original_task/submitted_parameters/' + parameter,
                       role='genome_alignment_invocation')
        if (invocation['observed_argv'] or [None])[0] == 'mauveAligner' and option not in ('max-gapped-aligner-length', 'weight') and supplied:
            report.add('source_option_unsupported', '/original_task/submitted_parameters/' + parameter,
                       role='genome_alignment_invocation')
    if invocation['observed_argv'] is None:
        report.add('native_execution_unverified', '/invocation', kind='output_metadata',
                   role='genome_alignment_primary')
    member_bindings = []
    if invocation['mode'] == 'multiple_files_concatenated':
        namespaces = ['mauve1_member_1based', 'mauve_sidecar_member_0based'] if (
            invocation['effective_recipe'] == 'progressiveMauve') else ['mauve_v4_member_0based'] if (
            invocation['effective_recipe'] == 'mauveAligner') else []
        for namespace in namespaces:
            for index, file_id in enumerate(invocation['ordered_file_ids']):
                member = {'namespace': namespace, 'index': index + (namespace == 'mauve1_member_1based')}
                requirement = report.add('member_join_missing', '/member_bindings/' + str(len(member_bindings)),
                                         role='genome_alignment_staged_input', identity=[namespace, index, file_id])
                member_bindings.append({'member': member, 'state': 'unverified', 'genome_occurrence_indices': [],
                    'components': [], 'source_length': None, 'evidence': deepcopy(invocation['evidence']),
                    'requirement_ids': [requirement, *next(f for f in files if f['file_id'] == file_id)['requirement_ids']]})
    contigs = []
    for file in files:
        for record in file['records']:
            req = report.add('contig_identity_missing', '/files/' + file['file_id'] + '/records/' + record['record_id'],
                             role='genome_alignment_contig_identity', refs=(file['content']['source_ref'],))
            contigs.append({'file_id': file['file_id'], 'record_id': record['record_id'], 'sequence_id': None,
                'accession': None, 'accession_version': None, 'genome_occurrence_indices': [],
                'state': 'unverified', 'evidence': [], 'requirement_ids': [req, *file['requirement_ids']]})
    report.add('genome_census_unknown', '/genome_census_state', role='genome_alignment_staged_input')
    report.add('feature_map_missing', '/feature_bindings', role='genome_alignment_feature_mapping')
    if not files:
        report.add('staged_file_missing', '/files', kind='input_bytes', role='genome_alignment_staged_input')
    value = {'schema_version': 'bvbrc_genome_alignment_inputs_v1', 'original_task': task,
        'genome_occurrences': occurrences, 'invocation': invocation, 'files': files,
        'member_bindings': member_bindings, 'contig_bindings': contigs, 'feature_bindings': [],
        'original_maps': [], 'xmfa_source_inputs': None, 'genome_census_state': 'unknown',
        'requirements': report.requirements, 'diagnostics': report.diagnostics}
    value = validate_genome_alignment_inputs(value)
    return {'status': 'partial' if report.requirements or report.diagnostics else 'ok', 'value': value,
            'requirements': deepcopy(value['requirements']), 'diagnostics': deepcopy(value['diagnostics'])}


__all__ = ['extract_genome_alignment_inputs', 'validate_genome_alignment_retained_records',
           'validate_genome_alignment_supplied_value_shapes']
