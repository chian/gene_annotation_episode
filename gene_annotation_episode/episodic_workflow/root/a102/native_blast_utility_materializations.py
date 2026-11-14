"""Pure v2 BLAST preparation selection, realization and custody relationships.

No filesystem reads, processes, discovery, scoring, or input repair. The supplied
lexical reader owns list syntax; these functions own the exact selected joins.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import PurePosixPath
import re

from . import native_blast_utility_contracts as c
from .blast_utility_contracts import validate_blast_utility_operation
from .native_blast_database_contracts import validate_native_blast_database_operand
from .native_blast_standard_database_contracts import _schema as strict_schema


def _require(condition, code):
    if not condition:
        c._error(code)


def _relative(value):
    path = c._producer_path(value, absolute=False)
    _require(not any(part.startswith('.') for part in path.parts)
             and path.parts[0] not in {'inputs', 'tmp', 'cache', 'bundle.json', 'owner.json'},
             'reserved_materialization_or_output_path')
    return path


def _family(relative, prefix):
    p, q = PurePosixPath(relative), PurePosixPath(prefix)
    return p.parent == q.parent and p.name.startswith(q.name + '.')


def _overlap(a, b):
    p, q = PurePosixPath(a), PurePosixPath(b)
    return p == q or p in q.parents or q in p.parents


def _lists(job):
    """Exact selected list bindings, before any bytes are read."""
    p, mode = job['operation']['parameters'], job['operation']['mode']
    result = []
    if mode == 'aggregate_databases':
        for name in ('classic_list', 'vdb_list'):
            selected = p[name]
            if selected is not None and selected['source'] == 'file':
                result.append({'input_key': selected['input_occurrence_id'], 'grammar': 'blast_database_lines',
                    'entries': [{'ordinal': e['ordinal'], 'line_number': e['line_number'], 'token_ordinal': 0,
                        'original_token': e['native_reference'], 'target': {'kind': 'database',
                            'database_key': e['database_key'], 'native_path_index': e['native_path_index']}}
                                for e in selected['entries']]})
    if mode == 'create_profile_database':
        result.append({'input_key': p['profile_list_occurrence_id'], 'grammar': 'profile_whitespace_tokens',
            'entries': [{'ordinal': e['ordinal'], 'line_number': e['line_number'],
                'token_ordinal': e['token_ordinal'], 'original_token': e['native_reference'],
                'target': {'kind': 'input', 'input_key': e['input_occurrence_id']}} for e in p['profile_entries']]})
    return result


def validate_preparation_job(job):
    strict_schema(job, c.NATIVE_BLAST_UTILITY_JOB_V2_SCHEMA)
    op = validate_blast_utility_operation(job['operation'])
    _require(op['version'] == 'blast_utility_operation_v2' and
             (op['program'], op['mode']) in c.PREPARATION_MODES, 'unsupported_program_mode')
    c._path(job['software']['executable'], absolute=True)
    for key, value in job['environment'].items():
        _require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) is not None and '\0' not in value,
                 'environment_invalid')
        _require(key not in c._RESERVED_ENV, 'producer_owned_environment')
    inputs, dbs = {}, {}
    formats = {'sequence_input': {'fasta'}, 'taxid_map': {'text'}, 'identifier_list':
        {'text', 'gi_list_binary', 'seqid_list_binary'}, 'database_list': {'text'}, 'profile_list': {'text'},
        'profile_input': {'pssm_asn1_text', 'pssm_asn1_binary'}}
    for row in job['inputs']:
        c._producer_path(row['path'], absolute=True)
        _require(type(row['size_bytes']) is int and row['input_key'] not in inputs, 'input_selection_conflict')
        _require(row['format'] in formats[row['role']], 'input_format_conflict')
        inputs[row['input_key']] = row
    _require(list(inputs) == op['input_occurrence_ids'], 'input_selection_conflict')
    for db in job['databases']:
        _require(db['database_key'] not in dbs and db['role'] == 'target', 'database_selection_conflict')
        if db['manifest']['version'] == 'native_blast_standard_prepared_database_manifest_v1':
            c._database(db)
        else:
            validate_native_blast_database_operand(db)
        dbs[db['database_key']] = db
    p, mode = op['parameters'], op['mode']
    expected_dbs = {op['database_key']} if op['database_key'] is not None else set()
    if mode == 'aggregate_volumes':
        expected_dbs |= {e['database_key'] for e in p['volume_entries']}
    if mode == 'aggregate_databases':
        for name, vdb in (('classic_list', False), ('vdb_list', True)):
            selected = p[name]
            if selected is None:
                continue
            for entry in selected['entries']:
                key = entry['database_key']; expected_dbs.add(key)
                _require(key in dbs and (dbs[key]['kind'] == 'vdb') == vdb, 'database_list_kind_conflict')
                _require(type(entry['native_path_index']) is int and
                         0 <= entry['native_path_index'] < len(dbs[key]['native_paths']), 'database_path_index_invalid')
    _require(set(dbs) == expected_dbs, 'database_selection_conflict')
    for db in dbs.values():
        if db['kind'] != 'vdb':
            _require(db['kind'] in {'blast_nucleotide_sequence', 'blast_protein_sequence'}, 'database_kind_conflict')
            _require(op['molecule'] == ('protein' if db['kind'] == 'blast_protein_sequence' else 'dna'),
                     'database_molecule_conflict')
    def inp(key, role, fmt):
        _require(key in inputs and inputs[key]['role'] == role and inputs[key]['format'] == fmt,
                 'input_role_or_format_conflict')
    if mode in {'convert_gi_list', 'convert_seqid_list', 'inspect_seqid_list'}:
        inp(p['input_occurrence_id'], 'identifier_list', 'seqid_list_binary' if mode == 'inspect_seqid_list' else 'text')
    elif mode == 'create_subset_alias' and p['restriction']['kind'] != 'oid_masks':
        inp(p['restriction']['occurrence_id'], 'identifier_list', p['restriction']['format'])
    elif mode == 'create_megablast_index' and p['input_format'] == 'fasta':
        inp(p['input_occurrence_id'], 'sequence_input', 'fasta')
    elif mode == 'create_profile_database':
        inp(p['profile_list_occurrence_id'], 'profile_list', 'text')
        for e in p['profile_entries']:
            inp(e['input_occurrence_id'], 'profile_input', p['input_format'])
        if p['taxid_map_occurrence_id'] is not None:
            inp(p['taxid_map_occurrence_id'], 'taxid_map', 'text')
    for selected in _lists(job):
        inp(selected['input_key'], 'profile_list' if mode == 'create_profile_database' else 'database_list', 'text')
    _validate_materialization_selection(job, inputs, dbs)
    _validate_outputs(job)
    return job


def _validate_materialization_selection(job, inputs, dbs):
    p, mode, mat = job['operation']['parameters'], job['operation']['mode'], job['materializations']
    expected = _lists(job)
    requested = [{k: v for k, v in row.items() if k != 'relative_path'} for row in mat['list_files']]
    _require(requested == expected and len({r['input_key'] for r in requested}) == len(requested),
             'materialized_list_selection_conflict')
    copy_keys = [r['database_key'] for r in mat['database_copies']]
    required_copies = (list(dict.fromkeys(e['database_key'] for e in p['volume_entries'])) if mode == 'aggregate_volumes'
        else [p['source_database_key']] if mode == 'create_megablast_index' and not p['old_style_index'] else [])
    _require(copy_keys == required_copies, 'database_copy_selection_conflict')
    destinations = []
    for row in mat['list_files']:
        destinations.append(str(_relative(row['relative_path'])))
        for entry in row['entries']:
            _require(all(type(entry[k]) is int for k in ('ordinal', 'line_number', 'token_ordinal')),
                     'list_location_invalid')
    for copy in mat['database_copies']:
        db = dbs[copy['database_key']]
        sources = [r['source_path'] for r in copy['files']]
        _require(len(set(sources)) == len(sources) and set(sources) == {r['path'] for r in db['manifest']['files']},
                 'database_copy_closure_conflict')
        _require([r['source_path'] for r in copy['native_paths']] == db['native_paths'],
                 'database_copy_native_paths_conflict')
        # The initial port has no selected alias lexical relocation contract.
        _require(not any(PurePosixPath(s).suffix in {'.nal', '.pal', '.nvl', '.pvl'} for s in sources),
                 'database_alias_relocation_unsupported')
        prefix_map = {r['source_path']: str(_relative(r['relative_path'])) for r in copy['native_paths']}
        _require(len(set(prefix_map.values())) == len(prefix_map), 'database_copy_namespace_collision')
        for item in copy['files']:
            relative = str(_relative(item['relative_path'])); destinations.append(relative)
            matches = [src for src in prefix_map if _family(item['source_path'], src)]
            _require(len(matches) == 1 and relative == prefix_map[matches[0]] + item['source_path'][len(matches[0]):],
                     'database_copy_relocation_unresolved')
        if mode == 'aggregate_volumes':
            entries = [e for e in p['volume_entries'] if e['database_key'] == copy['database_key']]
            _require(len(entries) == len(copy['native_paths']), 'volume_copy_population_conflict')
            for entry in entries:
                ordinal = entry['ordinal']
                index = entry['native_path_index']
                _require(type(index) is int and 0 <= index < len(copy['native_paths']), 'database_path_index_invalid')
                _require(copy['native_paths'][index]['relative_path'] == p['output_prefix'] + '.' + str(ordinal).zfill(2),
                         'volume_copy_namespace_conflict')
            _require(len({e['native_path_index'] for e in entries}) == len(entries),
                     'volume_copy_population_conflict')
    for i, path in enumerate(destinations):
        _require(not any(_overlap(path, other) for other in destinations[i+1:]), 'materialization_path_overlap')


def _validate_outputs(job):
    op, outputs = job['operation'], job['outputs']
    p, mode = op['parameters'], op['mode']
    _require(len({r['output_key'] for r in outputs}) == len(outputs), 'duplicate_output_key')
    roles = [r['role'] for r in outputs]
    _require(roles.count('stdout') == roles.count('stderr') == 1, 'output_stream_selection_conflict')
    mat = job['materializations']
    copies = {r['database_key']: r for r in mat['database_copies']}
    for row in outputs:
        _relative(row['relative_path'])
        file = row['population'] == 'file'
        _require(row['path_kind'] == ('file' if file else 'prefix'), 'output_kind_conflict')
        _require((row['database_key'] is not None) == (row['population'] == 'staged_database_members'),
                 'output_database_conflict')
        _require(file == (row['role'] not in {'database_family', 'index_family'}), 'output_population_conflict')
        expected = {'stdout': 'blast_seqid_list_info_text' if mode == 'inspect_seqid_list' else 'text',
            'stderr': 'text', 'statistics': 'text', 'database_family': 'blastdb_family',
            'index_family': 'blast_index_family', 'identifier_list':
                'gi_list_binary' if mode == 'convert_gi_list' else 'seqid_list_binary'}[row['role']]
        _require(row['format'] == expected, 'output_format_conflict')
    extra = [r for r in outputs if r['role'] not in {'stdout', 'stderr'}]
    if mode in {'inspect_seqid_list', 'show_filters'}:
        _require(not extra, 'output_selection_conflict')
    elif mode in {'convert_gi_list', 'convert_seqid_list'}:
        _require(len(extra) == 1 and extra[0]['role'] == 'identifier_list' and
                 extra[0]['relative_path'] == p['output_path'], 'output_selection_conflict')
    elif mode == 'create_megablast_index':
        stats = [r for r in extra if r['role'] == 'statistics']
        _require([r['relative_path'] for r in stats] == ([] if p['statistics_path'] is None else [p['statistics_path']]),
                 'statistics_selection_conflict')
        family = [r for r in extra if r['role'] != 'statistics']
        if p['old_style_index']:
            _require(len(family) == 1 and family[0]['role'] == 'index_family' and
                     family[0]['population'] == 'prefix_members' and family[0]['relative_path'] == p['output_prefix'],
                     'index_output_selection_conflict')
        else:
            prefixes = [r['relative_path'] for r in copies[p['source_database_key']]['native_paths']]
            _require([r['relative_path'] for r in family] == prefixes and all(r['role'] == 'index_family' and
                     r['population'] == 'staged_database_members' and r['database_key'] == p['source_database_key']
                     for r in family), 'index_output_selection_conflict')
    else:
        _require(len(extra) == 1 and extra[0]['role'] == 'database_family' and
                 extra[0]['population'] == 'prefix_members' and extra[0]['relative_path'] == p['output_prefix'],
                 'database_output_prefix_conflict')
    for i, row in enumerate(outputs):
        for other in outputs[i+1:]:
            _require(not _overlap(row['relative_path'], other['relative_path']) and
                not (row['path_kind'] == 'prefix' and _family(other['relative_path'], row['relative_path'])) and
                not (other['path_kind'] == 'prefix' and _family(row['relative_path'], other['relative_path'])),
                'output_path_overlap')
        for item in mat['list_files']:
            _require(not _overlap(row['relative_path'], item['relative_path']) and
                     not (row['path_kind'] == 'prefix' and _family(item['relative_path'], row['relative_path'])),
                     'output_overlaps_materialized_list')
        for copy in mat['database_copies']:
            for item in copy['files']:
                _require(not _overlap(row['relative_path'], item['relative_path']), 'output_overlaps_copied_input')
                if row['path_kind'] == 'prefix' and _family(item['relative_path'], row['relative_path']):
                    _require(mode == 'aggregate_volumes' or row['population'] == 'staged_database_members' and
                             row['database_key'] == copy['database_key'], 'output_overlaps_unrelated_copy')


def preparation_path_maps(job, attempt_directory):
    root = c._producer_path(attempt_directory, absolute=True)
    inputs = {r['input_key']: str(root / c.staged_relative(r)) for r in job['inputs']}
    inputs.update({r['input_key']: str(root / r['relative_path']) for r in job['materializations']['list_files']})
    databases = {r['database_key']: list(r['native_paths']) for r in job['databases']}
    databases.update({r['database_key']: [str(root / p['relative_path']) for p in r['native_paths']]
                      for r in job['materializations']['database_copies']})
    return {'input_paths': inputs, 'database_paths': databases}


def _target_token(entry, paths):
    target = entry['target']
    if target['kind'] == 'input':
        token = paths['input_paths'][target['input_key']]
    else:
        token = paths['database_paths'][target['database_key']][target['native_path_index']]
    _require(not any(ch.isspace() for ch in token), 'materialization_token_whitespace')
    return token


def copy_receipt_plan(job):
    dbs = {r['database_key']: r for r in job['databases']}
    result = []
    for copy in job['materializations']['database_copies']:
        files = {r['path']: r for r in dbs[copy['database_key']]['manifest']['files']}
        for row in copy['files']:
            result.append({'kind': 'database_copy', 'database_key': copy['database_key'], **row,
                'expected': {k: files[row['source_path']][k] for k in ('sha256', 'size_bytes')},
                'staged': None, 'final': None})
    return result


def realize_blast_utility_materializations(job: dict, *, input_contents: dict, attempt_directory: str) -> dict:
    """Validate supplied list bytes and replace exactly their selected spans."""
    job = c.validate_native_blast_utility_job(job)
    _require(job['version'] == c.JOB_VERSION_V2, 'materialization_v2_required')
    inputs = {r['input_key']: r for r in job['inputs']}
    required = {r['input_key'] for r in job['materializations']['list_files']}
    _require(type(input_contents) is dict and required <= set(input_contents) <= set(inputs), 'list_contents_population')
    paths = preparation_path_maps(job, attempt_directory)
    result = {**paths, 'list_bytes': {}, 'materialization_plan': input_receipt_plan(job) + copy_receipt_plan(job)}
    for selected in job['materializations']['list_files']:
        raw, receipt = realize_selected_list(job, selected, input_contents[selected['input_key']], paths)
        result['list_bytes'][selected['relative_path']] = raw
        result['materialization_plan'].append(receipt)
    return result


def input_receipt_plan(job):
    return [{'kind': 'input_copy', 'input_key': r['input_key'], 'source_path': r['path'],
        'relative_path': c.staged_relative(r), 'expected': {k: r[k] for k in ('sha256', 'size_bytes')},
        'staged': None, 'final': None} for r in job['inputs']]


def realize_selected_list(job, selected, raw, paths):
    from .blast_preparation_inputs import parse_blast_preparation_list
    inputs = {r['input_key']: r for r in job['inputs']}
    key, operand = selected['input_key'], inputs[selected['input_key']]
    _require(type(raw) is bytes and len(raw) == operand['size_bytes'] and
             hashlib.sha256(raw).hexdigest() == operand['sha256'], 'list_original_identity_mismatch')
    occurrence = {'occurrence_id': key, 'direction': 'input', 'role': operand['role'], 'ordinal': 0,
        'artifact_ref': operand['artifact_ref'] or 'artifact_' + operand['sha256'], 'native_path': operand['path'],
        'native_format': 'text', 'completeness': 'complete', 'sha256': operand['sha256'], 'size_bytes': len(raw)}
    doc = parse_blast_preparation_list(raw, grammar=selected['grammar'], occurrence=occurrence)
    _require(not doc['failures'] and len(doc['rows']) == len(selected['entries']), 'materialization_list_invalid')
    pieces, end, entries = [], 0, []
    for actual, expected in zip(doc['rows'], selected['entries']):
        _require(all(actual[k] == expected[k] for k in ('ordinal', 'line_number', 'token_ordinal', 'original_token')),
                 'materialization_list_binding_conflict')
        token = _target_token(expected, paths)
        pieces += [raw[end:actual['start_byte']], token.encode('utf-8')]
        end = actual['end_byte']; entries.append({**deepcopy(expected), 'realized_token': token})
    realized = b''.join([*pieces, raw[end:]])
    receipt = {'kind': 'list_rewrite', 'input_key': key,
        'original_sha256': operand['sha256'], 'relative_path': selected['relative_path'],
        'sha256': hashlib.sha256(realized).hexdigest(), 'size_bytes': len(realized),
        'grammar': selected['grammar'], 'entries': entries}
    return realized, receipt


def compile_preparation_job(job, *, input_paths, database_paths, output_directory):
    _require(type(input_paths) is dict and type(database_paths) is dict, 'complete_path_mapping_required')
    if output_directory == '.':
        expected = {'input_paths': {r['input_key']: r['path'] for r in job['inputs']},
                    'database_paths': {r['database_key']: r['native_paths'] for r in job['databases']}}
        root = PurePosixPath('.')
    else:
        root = c._producer_path(output_directory, absolute=True)
        expected = preparation_path_maps(job, str(root))
    _require(input_paths == expected['input_paths'] and database_paths == expected['database_paths'],
             'selected_realized_path_conflict')
    original = [job['software']['executable'], *[r['path'] for r in job['inputs']],
                *[r['path'] for db in job['databases'] for r in db['manifest']['files']]]
    for out in job['outputs']:
        path = str(root / out['relative_path'])
        _require(path not in original and not (out['path_kind'] == 'prefix' and any(_family(x, path) for x in original)),
                 'output_aliases_input')
    op, args = job['operation'], [job['software']['executable']]
    p, mode = op['parameters'], op['mode']
    molecule = 'prot' if op['molecule'] == 'protein' else 'nucl'
    def output(name): return str(root / p[name])
    def db(key): return ' '.join(database_paths[key])
    if mode == 'convert_gi_list':
        return args + ['-gi_file_in', input_paths[p['input_occurrence_id']], '-gi_file_out', output('output_path')]
    if mode == 'convert_seqid_list':
        args += ['-seqid_file_in', input_paths[p['input_occurrence_id']], '-seqid_file_out', output('output_path'),
                 '-seqid_title', p['title']]
        if p['seqid_database_key'] is not None:
            args += ['-seqid_db', db(p['seqid_database_key']), '-seqid_dbtype', molecule]
    elif mode == 'inspect_seqid_list':
        args += ['-seqid_file_info', input_paths[p['input_occurrence_id']]]
    elif op['program'] == 'blastdb_aliastool':
        args += ['-out', output('output_prefix'), '-dbtype', molecule, '-title', p['title']]
        if mode == 'create_subset_alias':
            args += ['-db', db(p['source_database_key'])]
            restriction = p['restriction']
            flag = {'gi_list': '-gilist', 'seqid_list': '-seqidlist', 'taxid_list': '-taxidlist', 'oid_masks': '-oid_masks'}[restriction['kind']]
            args += [flag, str(restriction['value']) if restriction['kind'] == 'oid_masks' else input_paths[restriction['occurrence_id']]]
        elif mode == 'aggregate_volumes':
            args += ['-num_volumes', str(p['num_volumes'])]
        else:
            for name, flag in (('classic_list', '-dblist'), ('vdb_list', '-vdblist')):
                selected = p[name]
                if selected is None: continue
                if selected['source'] == 'file':
                    args += [flag + '_file', input_paths[selected['input_occurrence_id']]]
                else:
                    tokens = [database_paths[e['database_key']][e['native_path_index']] for e in selected['entries']]
                    _require(not any(any(ch.isspace() for ch in x) for x in tokens), 'database_inline_token')
                    args += [flag, ' '.join(tokens)]
    elif op['program'] == 'makembindex':
        if mode == 'show_filters':
            return args + ['-input', db(p['source_database_key']), '-iformat', 'blastdb', '-show_filters']
        args += ['-input', input_paths[p['input_occurrence_id']] if p['input_format'] == 'fasta' else db(p['source_database_key']),
                 '-iformat', p['input_format'], '-old_style_index', str(p['old_style_index']).lower(),
                 '-legacy', str(p['legacy']).lower(), '-idmap', str(p['idmap']).lower(), '-verbosity', p['verbosity']]
        if p['output_prefix'] is not None: args += ['-output', output('output_prefix')]
        if p['statistics_path'] is not None: args += ['-stat', output('statistics_path')]
        for key, flag in (('db_mask', '-db_mask'), ('nmer', '-nmer'), ('ws_hint', '-ws_hint'),
                          ('stride', '-stride'), ('volume_size_mb', '-volsize')):
            if p[key] is not None: args += [flag, str(p[key])]
    else:
        args += ['-in', input_paths[p['profile_list_occurrence_id']], '-out', output('output_prefix'),
                 '-dbtype', p['profile_type'], '-title', p['title'], '-blastdb_version', str(p['database_format_version']),
                 '-max_smp_vol', str(p['max_smp_per_volume']), '-index', str(p['create_sequence_indexes']).lower(),
                 '-threshold', str(p['word_score_threshold']), '-scale', str(p['scale']), '-matrix', p['matrix'],
                 '-obsr_threshold', str(p['observations_threshold']), '-exclude_invalid', str(p['exclude_invalid']).lower()]
        if p['input_format'] == 'pssm_asn1_binary': args.append('-binary')
        if p['force_threshold']: args.append('-force')
        for key, flag in (('gap_open', '-gapopen'), ('gap_extend', '-gapextend'), ('taxid', '-taxid')):
            if p[key] is not None: args += [flag, str(p[key])]
        if p['taxid_map_occurrence_id'] is not None: args += ['-taxid_map', input_paths[p['taxid_map_occurrence_id']]]
    _require(not any('\0' in x for x in args), 'command_nul')
    return args


def output_member_kind(job, relative):
    suffix = PurePosixPath(relative).suffix
    if suffix in {'.nal', '.pal', '.nvl', '.pvl'}: return 'alias_file', 'blast_alias_text'
    if suffix in {'.njs', '.pjs'}: return 'database_metadata', 'blastdb_metadata_json'
    if job['operation']['program'] == 'makembindex':
        if suffix in {'.idx', '.shd'}: return 'index_file', 'blast_index_binary'
        if relative.endswith('.idx.map'): return 'index_file', 'blast_index_map_text'
        return 'index_file', 'unknown'
    if job['operation']['program'] == 'makeprofiledb':
        if suffix == '.aux': return 'profile_file', 'blast_profile_aux_text'
        if suffix in {'.rps', '.loo', '.freq', '.wcounts', '.obsr', '.blocks'}: return 'profile_file', 'blastdb_binary'
    if suffix in {'.gil', '.bgl'}: return 'identifier_list', 'gi_list_binary'
    if suffix == '.bsl': return 'identifier_list', 'seqid_list_binary'
    # Only known BLAST writer components receive a binary format label.
    known = {'nhr','nin','nsq','ndb','nog','nos','not','ntf','nto','nsi','nsd','nni','nnd',
             'phr','pin','psq','pdb','pog','pos','pot','ptf','pto','psi','psd','pni','pnd'}
    return 'database_file', 'blastdb_binary' if suffix.lstrip('.') in known else 'unknown'


def copied_relative_paths(job):
    return {r['relative_path'] for copy in job['materializations']['database_copies'] for r in copy['files']}


def validate_materialization_failure(row, job):
    _require(job['version'] == c.JOB_VERSION_V2, 'materialization_v2_required')
    candidates = [{'input_key': r['input_key'], 'database_key': None, 'relative_path': r['relative_path']}
                  for r in job['materializations']['list_files']]
    candidates += [{'input_key': None, 'database_key': copy['database_key'], 'relative_path': r['relative_path']}
                   for copy in job['materializations']['database_copies'] for r in copy['files']]
    _require({k: row[k] for k in ('input_key', 'database_key', 'relative_path')} in candidates,
             'materialization_failure_association')


def validate_preparation_bundle_tail(bundle, plan):
    from .blast_preparation_contracts import MATERIALIZATION_RECEIPT_SCHEMA
    job, root = plan['requested_job']['native_blast_utility'], PurePosixPath(plan['attempt_directory'])
    paths = preparation_path_maps(job, str(root))
    _require(type(bundle['materializations']) is list, 'materialization_receipts_invalid')
    receipts = bundle['materializations']
    for row in receipts:
        strict_schema(row, MATERIALIZATION_RECEIPT_SCHEMA)
    input_copies = input_receipt_plan(job)
    _require(len(receipts) >= len(input_copies), 'input_copy_receipt_population')
    for actual, expected, original in zip(receipts, input_copies, bundle['inputs']):
        for phase in ('staged', 'final'):
            pair = c.measurement_pair(original, phase + '_')
            expected[phase] = None if pair[0] is None else {'size_bytes': pair[0], 'sha256': pair[1]}
        _require(actual == expected, 'input_copy_receipt_conflict')
    receipts = receipts[len(input_copies):]
    copies, lists = copy_receipt_plan(job), job['materializations']['list_files']
    _require(len(receipts) >= len(copies) and len(receipts) <= len(copies) + len(lists), 'materialization_receipt_population')
    def has(code, **where):
        return c.producer_failure(code, **where) in bundle['failures']
    for actual, expected in zip(receipts, copies):
        _require({k:v for k,v in actual.items() if k not in {'staged', 'final'}} ==
                 {k:v for k,v in expected.items() if k not in {'staged', 'final'}}, 'database_copy_receipt_conflict')
        assoc = {'input_key': None, 'database_key': actual['database_key'], 'relative_path': actual['relative_path']}
        _require(actual['staged'] == actual['expected'] or not bundle['started'] and any(has(code, **assoc) for code in
                 ('materialization_unavailable', 'materialization_identity_mismatch', 'materialization_scratch_limit')),
                 'database_copy_staged_conflict')
        _require(has('materialization_changed', **assoc) == (actual['staged'] != actual['final']), 'database_copy_final_conflict')
    by_key = {r['input_key']: r for r in receipts[len(copies):] if r['kind'] == 'list_rewrite'}
    _require(len(by_key) == len(receipts) - len(copies), 'list_receipt_duplicate')
    expected_order = [r['input_key'] for r in lists if r['input_key'] in by_key]
    _require(list(by_key) == expected_order, 'list_receipt_order')
    originals = {r['input_key']: r for r in job['inputs']}
    for selected in lists:
        row = by_key.get(selected['input_key'])
        assoc = {'input_key': selected['input_key'], 'database_key': None, 'relative_path': selected['relative_path']}
        if row is None:
            _require(not bundle['started'] and has('materialization_binding_invalid', **assoc), 'list_receipt_missing')
            continue
        expected_entries = [{**entry, 'realized_token': _target_token(entry, paths)} for entry in selected['entries']]
        _require(row['relative_path'] == selected['relative_path'] and row['grammar'] == selected['grammar'] and
                 row['original_sha256'] == originals[row['input_key']]['sha256'] and row['entries'] == expected_entries,
                 'list_receipt_binding_conflict')
    _require(not bundle['started'] or not any(f['stage'] == 'materializations' and f['code'] != 'materialization_changed'
                                            for f in bundle['failures']), 'materialization_preflight_conflict')
    artifacts, slots, seen, ordered = bundle['artifacts'], {}, set(), []
    _require(type(artifacts) is list, 'bundle_outputs_conflict')
    excluded = copied_relative_paths(job)
    files = [r for r in job['outputs'] if r['population'] == 'file']
    families = [r for r in job['outputs'] if r['population'] != 'file']
    _require(len(artifacts) >= len(files), 'bundle_outputs_conflict')
    for i, row in enumerate(artifacts):
        _require(type(row) is dict and set(row) == {'output_key','role','ordinal','relative_path','format','sha256','size_bytes','completeness'},
                 'bundle_output_shape')
        relative = row['relative_path']; c._producer_path(relative, absolute=False)
        _require(relative not in seen and relative not in excluded, 'bundle_output_collision'); seen.add(relative)
        if i < len(files):
            selected = files[i]
            _require(all(row[k] == selected[k] for k in ('output_key','role','relative_path','format')), 'bundle_file_selection_conflict')
        else:
            matches = [f for f in families if _family(relative, f['relative_path'])]
            _require(len(matches) == 1 and matches[0]['output_key'] == row['output_key'], 'bundle_family_identity_conflict')
            _require((row['role'], row['format']) == output_member_kind(job, relative), 'bundle_family_format_conflict')
            ordered.append((families.index(matches[0]), relative))
        ordinal = slots.get(row['role'], 0)
        _require(type(row['ordinal']) is int and row['ordinal'] == ordinal, 'bundle_output_ordinal_conflict')
        slots[row['role']] = ordinal + 1
        pair = c.measurement_pair(row)
        _require((has('missing_output', relative_path=relative) or has('invalid_output', relative_path=relative)) == (pair[0] is None),
                 'bundle_output_failure_conflict')
        _require(row['completeness'] == c.native_blast_utility_output_completeness(bundle, pair[0] is not None),
                 'bundle_output_completeness_conflict')
    _require(ordered == sorted(ordered), 'bundle_family_order_conflict')
    for family in families:
        rows = [r for r in artifacts if r['output_key'] == family['output_key']]
        _require(rows or any(has(code, relative_path=family['relative_path']) for code in
                 ('missing_output', 'invalid_output', 'output_inventory_incomplete')), 'bundle_family_absence_failure_required')
        _require(not bundle['inventory_complete'] or all(r['sha256'] is not None for r in rows), 'bundle_inventory_capture_conflict')
    _require(bundle['inventory_complete'] != any(f['code'] == 'output_inventory_incomplete' for f in bundle['failures']),
             'bundle_inventory_failure_conflict')
