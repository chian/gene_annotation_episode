from __future__ import annotations
from pathlib import PurePosixPath
import re
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_contracts as c
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_utility_contracts import validate_blast_utility_operation
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_contracts import validate_native_blast_database_operand
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_contracts import _schema as strict_schema

def _require(condition, code):
    if not condition:
        c._error(code)

def _relative(value):
    path = c._producer_path(value, absolute=False)
    _require(not any((part.startswith('.') for part in path.parts)) and path.parts[0] not in {'inputs', 'tmp', 'cache', 'bundle.json', 'owner.json'}, 'reserved_materialization_or_output_path')
    return path

def _family(relative, prefix):
    p, q = (PurePosixPath(relative), PurePosixPath(prefix))
    return p.parent == q.parent and p.name.startswith(q.name + '.')

def _overlap(a, b):
    p, q = (PurePosixPath(a), PurePosixPath(b))
    return p == q or p in q.parents or q in p.parents

def _lists(job):
    """Exact selected list bindings, before any bytes are read."""
    p, mode = (job['operation']['parameters'], job['operation']['mode'])
    result = []
    if mode == 'aggregate_databases':
        for name in ('classic_list', 'vdb_list'):
            selected = p[name]
            if selected is not None and selected['source'] == 'file':
                result.append({'input_key': selected['input_occurrence_id'], 'grammar': 'blast_database_lines', 'entries': [{'ordinal': e['ordinal'], 'line_number': e['line_number'], 'token_ordinal': 0, 'original_token': e['native_reference'], 'target': {'kind': 'database', 'database_key': e['database_key'], 'native_path_index': e['native_path_index']}} for e in selected['entries']]})
    if mode == 'create_profile_database':
        result.append({'input_key': p['profile_list_occurrence_id'], 'grammar': 'profile_whitespace_tokens', 'entries': [{'ordinal': e['ordinal'], 'line_number': e['line_number'], 'token_ordinal': e['token_ordinal'], 'original_token': e['native_reference'], 'target': {'kind': 'input', 'input_key': e['input_occurrence_id']}} for e in p['profile_entries']]})
    return result

def validate_preparation_job(job):
    strict_schema(job, c.NATIVE_BLAST_UTILITY_JOB_V2_SCHEMA)
    op = validate_blast_utility_operation(job['operation'])
    _require(op['version'] == 'blast_utility_operation_v2' and (op['program'], op['mode']) in c.PREPARATION_MODES, 'unsupported_program_mode')
    c._path(job['software']['executable'], absolute=True)
    for key, value in job['environment'].items():
        _require(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', key) is not None and '\x00' not in value, 'environment_invalid')
        _require(key not in c._RESERVED_ENV, 'producer_owned_environment')
    inputs, dbs = ({}, {})
    formats = {'sequence_input': {'fasta'}, 'taxid_map': {'text'}, 'identifier_list': {'text', 'gi_list_binary', 'seqid_list_binary'}, 'database_list': {'text'}, 'profile_list': {'text'}, 'profile_input': {'pssm_asn1_text', 'pssm_asn1_binary'}}
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
    p, mode = (op['parameters'], op['mode'])
    expected_dbs = {op['database_key']} if op['database_key'] is not None else set()
    if mode == 'aggregate_volumes':
        expected_dbs |= {e['database_key'] for e in p['volume_entries']}
    if mode == 'aggregate_databases':
        for name, vdb in (('classic_list', False), ('vdb_list', True)):
            selected = p[name]
            if selected is None:
                continue
            for entry in selected['entries']:
                key = entry['database_key']
                expected_dbs.add(key)
                _require(key in dbs and (dbs[key]['kind'] == 'vdb') == vdb, 'database_list_kind_conflict')
                _require(type(entry['native_path_index']) is int and 0 <= entry['native_path_index'] < len(dbs[key]['native_paths']), 'database_path_index_invalid')
    _require(set(dbs) == expected_dbs, 'database_selection_conflict')
    for db in dbs.values():
        if db['kind'] != 'vdb':
            _require(db['kind'] in {'blast_nucleotide_sequence', 'blast_protein_sequence'}, 'database_kind_conflict')
            _require(op['molecule'] == ('protein' if db['kind'] == 'blast_protein_sequence' else 'dna'), 'database_molecule_conflict')

    def inp(key, role, fmt):
        _require(key in inputs and inputs[key]['role'] == role and (inputs[key]['format'] == fmt), 'input_role_or_format_conflict')
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
    p, mode, mat = (job['operation']['parameters'], job['operation']['mode'], job['materializations'])
    expected = _lists(job)
    requested = [{k: v for k, v in row.items() if k != 'relative_path'} for row in mat['list_files']]
    _require(requested == expected and len({r['input_key'] for r in requested}) == len(requested), 'materialized_list_selection_conflict')
    copy_keys = [r['database_key'] for r in mat['database_copies']]
    required_copies = list(dict.fromkeys((e['database_key'] for e in p['volume_entries']))) if mode == 'aggregate_volumes' else [p['source_database_key']] if mode == 'create_megablast_index' and (not p['old_style_index']) else []
    _require(copy_keys == required_copies, 'database_copy_selection_conflict')
    destinations = []
    for row in mat['list_files']:
        destinations.append(str(_relative(row['relative_path'])))
        for entry in row['entries']:
            _require(all((type(entry[k]) is int for k in ('ordinal', 'line_number', 'token_ordinal'))), 'list_location_invalid')
    for copy in mat['database_copies']:
        db = dbs[copy['database_key']]
        sources = [r['source_path'] for r in copy['files']]
        _require(len(set(sources)) == len(sources) and set(sources) == {r['path'] for r in db['manifest']['files']}, 'database_copy_closure_conflict')
        _require([r['source_path'] for r in copy['native_paths']] == db['native_paths'], 'database_copy_native_paths_conflict')
        _require(not any((PurePosixPath(s).suffix in {'.nal', '.pal', '.nvl', '.pvl'} for s in sources)), 'database_alias_relocation_unsupported')
        prefix_map = {r['source_path']: str(_relative(r['relative_path'])) for r in copy['native_paths']}
        _require(len(set(prefix_map.values())) == len(prefix_map), 'database_copy_namespace_collision')
        for item in copy['files']:
            relative = str(_relative(item['relative_path']))
            destinations.append(relative)
            matches = [src for src in prefix_map if _family(item['source_path'], src)]
            _require(len(matches) == 1 and relative == prefix_map[matches[0]] + item['source_path'][len(matches[0]):], 'database_copy_relocation_unresolved')
        if mode == 'aggregate_volumes':
            entries = [e for e in p['volume_entries'] if e['database_key'] == copy['database_key']]
            _require(len(entries) == len(copy['native_paths']), 'volume_copy_population_conflict')
            for entry in entries:
                ordinal = entry['ordinal']
                index = entry['native_path_index']
                _require(type(index) is int and 0 <= index < len(copy['native_paths']), 'database_path_index_invalid')
                _require(copy['native_paths'][index]['relative_path'] == p['output_prefix'] + '.' + str(ordinal).zfill(2), 'volume_copy_namespace_conflict')
            _require(len({e['native_path_index'] for e in entries}) == len(entries), 'volume_copy_population_conflict')
    for i, path in enumerate(destinations):
        _require(not any((_overlap(path, other) for other in destinations[i + 1:])), 'materialization_path_overlap')

def _validate_outputs(job):
    op, outputs = (job['operation'], job['outputs'])
    p, mode = (op['parameters'], op['mode'])
    _require(len({r['output_key'] for r in outputs}) == len(outputs), 'duplicate_output_key')
    roles = [r['role'] for r in outputs]
    _require(roles.count('stdout') == roles.count('stderr') == 1, 'output_stream_selection_conflict')
    mat = job['materializations']
    copies = {r['database_key']: r for r in mat['database_copies']}
    for row in outputs:
        _relative(row['relative_path'])
        file = row['population'] == 'file'
        _require(row['path_kind'] == ('file' if file else 'prefix'), 'output_kind_conflict')
        _require((row['database_key'] is not None) == (row['population'] == 'staged_database_members'), 'output_database_conflict')
        _require(file == (row['role'] not in {'database_family', 'index_family'}), 'output_population_conflict')
        expected = {'stdout': 'blast_seqid_list_info_text' if mode == 'inspect_seqid_list' else 'text', 'stderr': 'text', 'statistics': 'text', 'database_family': 'blastdb_family', 'index_family': 'blast_index_family', 'identifier_list': 'gi_list_binary' if mode == 'convert_gi_list' else 'seqid_list_binary'}[row['role']]
        _require(row['format'] == expected, 'output_format_conflict')
    extra = [r for r in outputs if r['role'] not in {'stdout', 'stderr'}]
    if mode in {'inspect_seqid_list', 'show_filters'}:
        _require(not extra, 'output_selection_conflict')
    elif mode in {'convert_gi_list', 'convert_seqid_list'}:
        _require(len(extra) == 1 and extra[0]['role'] == 'identifier_list' and (extra[0]['relative_path'] == p['output_path']), 'output_selection_conflict')
    elif mode == 'create_megablast_index':
        stats = [r for r in extra if r['role'] == 'statistics']
        _require([r['relative_path'] for r in stats] == ([] if p['statistics_path'] is None else [p['statistics_path']]), 'statistics_selection_conflict')
        family = [r for r in extra if r['role'] != 'statistics']
        if p['old_style_index']:
            _require(len(family) == 1 and family[0]['role'] == 'index_family' and (family[0]['population'] == 'prefix_members') and (family[0]['relative_path'] == p['output_prefix']), 'index_output_selection_conflict')
        else:
            prefixes = [r['relative_path'] for r in copies[p['source_database_key']]['native_paths']]
            _require([r['relative_path'] for r in family] == prefixes and all((r['role'] == 'index_family' and r['population'] == 'staged_database_members' and (r['database_key'] == p['source_database_key']) for r in family)), 'index_output_selection_conflict')
    else:
        _require(len(extra) == 1 and extra[0]['role'] == 'database_family' and (extra[0]['population'] == 'prefix_members') and (extra[0]['relative_path'] == p['output_prefix']), 'database_output_prefix_conflict')
    for i, row in enumerate(outputs):
        for other in outputs[i + 1:]:
            _require(not _overlap(row['relative_path'], other['relative_path']) and (not (row['path_kind'] == 'prefix' and _family(other['relative_path'], row['relative_path']))) and (not (other['path_kind'] == 'prefix' and _family(row['relative_path'], other['relative_path']))), 'output_path_overlap')
        for item in mat['list_files']:
            _require(not _overlap(row['relative_path'], item['relative_path']) and (not (row['path_kind'] == 'prefix' and _family(item['relative_path'], row['relative_path']))), 'output_overlaps_materialized_list')
        for copy in mat['database_copies']:
            for item in copy['files']:
                _require(not _overlap(row['relative_path'], item['relative_path']), 'output_overlaps_copied_input')
                if row['path_kind'] == 'prefix' and _family(item['relative_path'], row['relative_path']):
                    _require(mode == 'aggregate_volumes' or (row['population'] == 'staged_database_members' and row['database_key'] == copy['database_key']), 'output_overlaps_unrelated_copy')

def preparation_path_maps(job, attempt_directory):
    root = c._producer_path(attempt_directory, absolute=True)
    inputs = {r['input_key']: str(root / c.staged_relative(r)) for r in job['inputs']}
    inputs.update({r['input_key']: str(root / r['relative_path']) for r in job['materializations']['list_files']})
    databases = {r['database_key']: list(r['native_paths']) for r in job['databases']}
    databases.update({r['database_key']: [str(root / p['relative_path']) for p in r['native_paths']] for r in job['materializations']['database_copies']})
    return {'input_paths': inputs, 'database_paths': databases}

def compile_preparation_job(job, *, input_paths, database_paths, output_directory):
    _require(type(input_paths) is dict and type(database_paths) is dict, 'complete_path_mapping_required')
    if output_directory == '.':
        expected = {'input_paths': {r['input_key']: r['path'] for r in job['inputs']}, 'database_paths': {r['database_key']: r['native_paths'] for r in job['databases']}}
        root = PurePosixPath('.')
    else:
        root = c._producer_path(output_directory, absolute=True)
        expected = preparation_path_maps(job, str(root))
    _require(input_paths == expected['input_paths'] and database_paths == expected['database_paths'], 'selected_realized_path_conflict')
    original = [job['software']['executable'], *[r['path'] for r in job['inputs']], *[r['path'] for db in job['databases'] for r in db['manifest']['files']]]
    for out in job['outputs']:
        path = str(root / out['relative_path'])
        _require(path not in original and (not (out['path_kind'] == 'prefix' and any((_family(x, path) for x in original)))), 'output_aliases_input')
    op, args = (job['operation'], [job['software']['executable']])
    p, mode = (op['parameters'], op['mode'])
    molecule = 'prot' if op['molecule'] == 'protein' else 'nucl'

    def output(name):
        return str(root / p[name])

    def db(key):
        return ' '.join(database_paths[key])
    if mode == 'convert_gi_list':
        return args + ['-gi_file_in', input_paths[p['input_occurrence_id']], '-gi_file_out', output('output_path')]
    if mode == 'convert_seqid_list':
        args += ['-seqid_file_in', input_paths[p['input_occurrence_id']], '-seqid_file_out', output('output_path'), '-seqid_title', p['title']]
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
                if selected is None:
                    continue
                if selected['source'] == 'file':
                    args += [flag + '_file', input_paths[selected['input_occurrence_id']]]
                else:
                    tokens = [database_paths[e['database_key']][e['native_path_index']] for e in selected['entries']]
                    _require(not any((any((ch.isspace() for ch in x)) for x in tokens)), 'database_inline_token')
                    args += [flag, ' '.join(tokens)]
    elif op['program'] == 'makembindex':
        if mode == 'show_filters':
            return args + ['-input', db(p['source_database_key']), '-iformat', 'blastdb', '-show_filters']
        args += ['-input', input_paths[p['input_occurrence_id']] if p['input_format'] == 'fasta' else db(p['source_database_key']), '-iformat', p['input_format'], '-old_style_index', str(p['old_style_index']).lower(), '-legacy', str(p['legacy']).lower(), '-idmap', str(p['idmap']).lower(), '-verbosity', p['verbosity']]
        if p['output_prefix'] is not None:
            args += ['-output', output('output_prefix')]
        if p['statistics_path'] is not None:
            args += ['-stat', output('statistics_path')]
        for key, flag in (('db_mask', '-db_mask'), ('nmer', '-nmer'), ('ws_hint', '-ws_hint'), ('stride', '-stride'), ('volume_size_mb', '-volsize')):
            if p[key] is not None:
                args += [flag, str(p[key])]
    else:
        args += ['-in', input_paths[p['profile_list_occurrence_id']], '-out', output('output_prefix'), '-dbtype', p['profile_type'], '-title', p['title'], '-blastdb_version', str(p['database_format_version']), '-max_smp_vol', str(p['max_smp_per_volume']), '-index', str(p['create_sequence_indexes']).lower(), '-threshold', str(p['word_score_threshold']), '-scale', str(p['scale']), '-matrix', p['matrix'], '-obsr_threshold', str(p['observations_threshold']), '-exclude_invalid', str(p['exclude_invalid']).lower()]
        if p['input_format'] == 'pssm_asn1_binary':
            args.append('-binary')
        if p['force_threshold']:
            args.append('-force')
        for key, flag in (('gap_open', '-gapopen'), ('gap_extend', '-gapextend'), ('taxid', '-taxid')):
            if p[key] is not None:
                args += [flag, str(p[key])]
        if p['taxid_map_occurrence_id'] is not None:
            args += ['-taxid_map', input_paths[p['taxid_map_occurrence_id']]]
    _require(not any(('\x00' in x for x in args)), 'command_nul')
    return args
