"""Pure selected native-database contracts; no discovery, I/O or scoring.

The schemas describe custody and invocation, not numerical result sheets. The
accepted contract is workload 327/001, producer boundary N (331).
All public validators return independent finite JSON values and raise ValueError
with a stable native_blast_standard_database_* code. A valid record proves no deployment.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.blast_program_context import resolve_blast_program_context
PROGRAMS = ('blastn', 'blastp', 'blastx', 'tblastn', 'tblastx')
RESERVED_ENVIRONMENT = frozenset({'TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE'})
TABULAR_FIELDS = frozenset('qseqid qgi qacc qaccver qlen sseqid sallseqid sgi sallgi sacc saccver sallacc slen qstart qend sstart send qseq sseq evalue bitscore score length pident nident mismatch positive gapopen gaps ppos frames qframe sframe btop staxid ssciname scomname sblastname sskingdom staxids sscinames scomnames sblastnames sskingdoms stitle salltitles sstrand qcovs qcovhsp qcovus'.split())
_PREFIX = 'native_blast_standard_database_'
_STR = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\x00]+$'}
_SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
_INT = {'type': 'integer', 'minimum': 0}
_BOOL = {'type': 'boolean'}
_ABS = {'type': 'string', 'minLength': 1}
_KEY = {'type': 'string', 'minLength': 1, 'pattern': '^[^/\\\\\\x00]+$'}
_ENV = {'type': 'object', 'additionalProperties': {'type': 'string'}}
_METADATA_TUPLES = (('query_identity', 'native_blast_database_query_metadata_v1'), ('sequence_database', 'native_blast_database_sequence_metadata_v1'), ('sequence_database', 'native_blast_database_sequence_metadata_v2'), ('sequence_database', 'native_blast_database_sequence_metadata_v3'))

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _array(items, **extra):
    return {'type': 'array', 'items': items, **extra}
PROVENANCE_SCHEMA = _object({'source_ref': _STR, 'pointer': {'type': 'string'}})
FILE_IDENTITY_SCHEMA = _object({'path': _ABS, 'sha256': _SHA, 'size_bytes': _INT, 'artifact_ref': _nullable(_STR)})
_FILE = _object({'path': _ABS, 'sha256': _SHA, 'size_bytes': _INT})
DATABASE_IDENTITY_SCHEMA = _object({'namespace': _STR, 'value': _STR, 'version': _nullable(_STR), 'release': _nullable(_STR), 'scope': _nullable(_STR), 'preparation_type': {'const': 'sequence_database'}, 'source': PROVENANCE_SCHEMA})
SOFTWARE_SCHEMA = _object({'executable': _ABS, 'sha256': _SHA, 'engine_version': _nullable(_STR)})
PREPARED_DATABASE_SCHEMA = _object({'version': {'const': 'native_blast_standard_prepared_database_manifest_v1'}, 'database_key': _KEY, 'kind': {'enum': ['blast_protein_sequence', 'blast_nucleotide_sequence']}, 'identity': DATABASE_IDENTITY_SCHEMA, 'native_paths': _array(_ABS, minItems=1, uniqueItems=True), 'files': _array(_FILE, minItems=1), 'preparation': _object({'method': {'enum': ['makeblastdb', 'publisher_package', 'other_recorded']}, 'preparation_type': {'const': 'sequence_database'}, 'software': _object({'name': _STR, 'version': _nullable(_STR), 'executable_sha256': _nullable(_SHA)}), 'argv': _nullable(_array(_STR, minItems=1)), 'source': PROVENANCE_SCHEMA, 'input_manifest': _nullable(FILE_IDENTITY_SCHEMA), 'receipt': FILE_IDENTITY_SCHEMA}), 'metadata_manifests': _array(FILE_IDENTITY_SCHEMA), 'access': _object({'mode': {'const': 'prepared_local'}, 'offline_configuration': _nullable(FILE_IDENTITY_SCHEMA)}), 'inventory_complete': _BOOL})
DATABASE_OPERAND_SCHEMA = _object({'database_key': _KEY, 'role': {'const': 'target'}, 'kind': PREPARED_DATABASE_SCHEMA['properties']['kind'], 'identity': DATABASE_IDENTITY_SCHEMA, 'native_paths': _array(_ABS, minItems=1, uniqueItems=True), 'manifest_file': FILE_IDENTITY_SCHEMA, 'manifest': PREPARED_DATABASE_SCHEMA})
OUTPUT_SELECTION_SCHEMA = _object({'output_key': _KEY, 'role': {'enum': ['stdout', 'stderr', 'primary_report']}, 'path_kind': {'const': 'file'}, 'relative_path': _STR, 'format': {'enum': ['text', 'json15', 'tabular6', 'tabular7']}, 'fields': _array({'enum': sorted(TABULAR_FIELDS)}, uniqueItems=True), 'delimiter': _nullable({'type': 'string', 'minLength': 1, 'maxLength': 1}), 'required': _BOOL})
MODEL_SCHEMA = {'type': 'object', 'properties': {'temperature_bits': {'type': 'number', 'exclusiveMinimum': 0}, 'function_priors': _nullable({'type': 'object', 'additionalProperties': {'type': 'number', 'minimum': 0}})}, 'additionalProperties': False}
NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA = _object({'version': {'const': 'native_blast_standard_database_job_v1'}, 'program': {'enum': list(PROGRAMS)}, 'mode': {'const': 'database'}, 'software': SOFTWARE_SCHEMA, 'environment': _ENV, 'inputs': _array(_object({'input_key': _KEY, 'role': {'enum': ['query_sequence', 'query_pssm', 'metadata']}, 'path': _ABS, 'format': {'enum': ['fasta', 'scoremat_asn_text', 'json', 'text']}, 'sha256': _SHA, 'size_bytes': _INT, 'artifact_ref': _nullable(_STR)}), minItems=1), 'query': _object({'kind': {'enum': ['sequence', 'pssm']}, 'input_key': _KEY}), 'databases': _array(DATABASE_OPERAND_SCHEMA, minItems=1, maxItems=1), 'options': _array(_STR), 'outputs': _array(OUTPUT_SELECTION_SCHEMA, minItems=3, maxItems=3), 'metadata_inputs': _array({'oneOf': [_object({'input_key': _KEY, 'consumer': {'const': consumer}, 'schema_id': {'const': schema}}) for consumer, schema in _METADATA_TUPLES]}, uniqueItems=True), 'grading_parameters': _object({'sequence_database_model': _nullable(MODEL_SCHEMA)})})
NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA = _object({'argv': _array(_STR, minItems=1), 'environment': _ENV, 'native_blast_standard_database': NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA})

def _fail(code):
    raise ValueError(_PREFIX + code)

def _copy(value, _active=None):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or (type(value) is dict and all((type(k) is str for k in value))):
        active = set() if _active is None else _active
        identity = id(value)
        if identity in active:
            _fail('finite_json_required')
        active.add(identity)
        try:
            if type(value) is list:
                return [_copy(v, active) for v in value]
            return {k: _copy(v, active) for k, v in value.items()}
        finally:
            active.remove(identity)
    _fail('finite_json_required')

def _digest(value):
    return hashlib.sha256(json.dumps(_copy(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def _schema(value, schema, path='$'):
    """Validate the ordinary JSON-schema subset used by these closed records."""
    if 'anyOf' in schema:
        for candidate in schema['anyOf']:
            try:
                _schema(value, candidate, path)
                return
            except ValueError:
                pass
        _fail('schema:' + path + ':anyOf')
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        _fail('schema:' + path + ':const')
    if 'enum' in schema and (not any((type(value) is type(v) and value == v for v in schema['enum']))):
        _fail('schema:' + path + ':enum')
    kind = schema.get('type')
    types = {'object': (dict,), 'array': (list,), 'string': (str,), 'integer': (int,), 'number': (int, float), 'boolean': (bool,), 'null': (type(None),)}
    if kind and type(value) not in types[kind]:
        _fail('schema:' + path + ':type')
    if kind == 'object':
        properties = schema.get('properties', {})
        if set(schema.get('required', [])) - value.keys():
            _fail('schema:' + path + ':required')
        for key, item in value.items():
            child = properties.get(key, schema.get('additionalProperties', True))
            if child is False:
                _fail('schema:' + path + ':additionalProperties')
            if type(child) is dict:
                _schema(item, child, path + '.' + key)
    if kind == 'array':
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', math.inf):
            _fail('schema:' + path + ':length')
        if schema.get('uniqueItems') and len({_digest(v) for v in value}) != len(value):
            _fail('schema:' + path + ':uniqueItems')
        for index, item in enumerate(value):
            _schema(item, schema.get('items', {}), path + '[' + str(index) + ']')
    if kind == 'string':
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', math.inf) or ('pattern' in schema and re.fullmatch(schema['pattern'], value) is None):
            _fail('schema:' + path + ':string')
    if kind in ('number', 'integer'):
        if kind == 'number':
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                _fail('schema:' + path + ':finite_number')
        if value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf) or ('exclusiveMinimum' in schema and value <= schema['exclusiveMinimum']):
            _fail('schema:' + path + ':range')

def _absolute(value):
    if type(value) is not str or not value.startswith('/') or value.startswith('//') or any((c in value for c in ('\x00', '\n', '\r'))) or ('..' in value.split('/')) or (str(PurePosixPath(value)) != value):
        _fail('absolute_normalized_path_required')

def _relative(value):
    if type(value) is not str or not value or value.startswith('/') or any((c in ('.', '..') for c in value.split('/'))) or any((ord(c) < 32 or ord(c) == 127 for c in value)) or (str(PurePosixPath(value)) != value):
        _fail('confined_relative_path_required')

def _inside(path, root, *, equal=False):
    p, r = (PurePosixPath(path), PurePosixPath(root))
    return r in p.parents or (equal and p == r)

def _overlap(a, b):
    return a == b or _inside(a, b) or _inside(b, a)

def _environment(env, *, job=False):
    _schema(env, _ENV)
    for key, value in env.items():
        if re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', key) is None or '\x00' in value:
            _fail('environment_invalid')
        if job and key in RESERVED_ENVIRONMENT:
            _fail('producer_owned_environment:' + key)

def _provenance(value):
    _schema(value, PROVENANCE_SCHEMA)
    if value['pointer'] and (not value['pointer'].startswith('/')) or re.search('~(?![01])', value['pointer']):
        _fail('provenance_pointer_invalid')

def _file_identity(value):
    _schema(value, FILE_IDENTITY_SCHEMA)
    _absolute(value['path'])

def _database(db):
    _schema(db, DATABASE_OPERAND_SCHEMA)
    manifest = db['manifest']
    for field in ('database_key', 'kind', 'identity', 'native_paths'):
        if db[field] != manifest[field]:
            _fail('database_manifest_operand_mismatch:' + field)
    _prepared_database_relationships(manifest, extra_identities=[db['manifest_file']])

def _prepared_database_relationships(manifest, *, extra_identities=()):
    """Shared existing manifest relationships, independent of a search operand."""
    _provenance(manifest['identity']['source'])
    _provenance(manifest['preparation']['source'])
    if manifest['preparation']['preparation_type'] != 'sequence_database':
        _fail('database_preparation_type_mismatch')
    if not manifest['inventory_complete']:
        _fail('database_complete_inventory_required')
    for path in manifest['native_paths']:
        _absolute(path)
        if any((c.isspace() for c in path)):
            _fail('database_whitespace_path_forbidden')
    files = set()
    for row in manifest['files']:
        _absolute(row['path'])
        if row['path'] in files:
            _fail('database_inventory_duplicate_path')
        files.add(row['path'])
    for native in manifest['native_paths']:
        if not any((p.startswith(native + '.') for p in files)):
            _fail('database_native_path_not_in_inventory')
    identities = [*extra_identities, manifest['preparation']['receipt'], *manifest['metadata_manifests'], *[v for v in (manifest['preparation']['input_manifest'], manifest['access']['offline_configuration']) if v is not None]]
    by_path = {row['path']: (row['sha256'], row['size_bytes']) for row in manifest['files']}
    for row in identities:
        _file_identity(row)
        identity = (row['sha256'], row['size_bytes'])
        if row['path'] in by_path and by_path[row['path']] != identity:
            _fail('database_file_identity_conflict')
        by_path[row['path']] = identity

def validate_standard_prepared_blast_database_manifest(manifest: dict) -> dict:
    """Validate supplied prepared-manifest facts without constructing a search.

    The returned manifest is a detached finite-JSON copy. This reuses the same
    manifest relationships as the original database-operand validator. It neither
    supplies an identity for an unsaved manifest nor checks native file contents.
    """
    manifest = _copy(manifest)
    _schema(manifest, PREPARED_DATABASE_SCHEMA)
    _prepared_database_relationships(manifest)
    return manifest
_COMPILER_FLAGS = frozenset({'-query', '-in_pssm', '-db', '-out', '-outfmt'})
_FORBIDDEN_FLAGS = frozenset({'-remote', '-subject', '-subject_loc', '-entrez_query', '-phi_pattern', '-import_search_strategy', '-export_search_strategy', '-html', '-gilist', '-seqidlist', '-negative_gilist', '-negative_seqidlist', '-taxids', '-negative_taxids', '-taxidlist', '-negative_taxidlist', '-no_taxid_expansion', '-db_soft_mask', '-db_hard_mask', '-filtering_db', '-window_masker_taxid', '-window_masker_db', '-use_index', '-index_name', '-ipglist', '-negative_ipglist'})
_GENCODES = set(range(1, 7)) | set(range(9, 17)) | set(range(21, 32)) | {33}
_TASKS = {'blastn': {'blastn', 'blastn-short', 'dc-megablast', 'megablast', 'rmblastn'}, 'blastp': {'blastp', 'blastp-fast', 'blastp-short'}, 'blastx': {'blastx', 'blastx-fast'}, 'tblastn': {'tblastn', 'tblastn-fast'}}

def _option_grammar(program):
    if type(program) is not str or program not in PROGRAMS:
        _fail('program_unsupported')
    flags = {'-lcase_masking', '-parse_deflines', '-show_gis', '-subject_besthit'}
    values = {'-query_loc': 'range', '-evalue': 'real', '-word_size': 'word_size', '-qcov_hsp_perc': 'percent', '-max_hsps': 'positive_integer', '-max_target_seqs': 'positive_integer', '-xdrop_ungap': 'real', '-searchsp': 'uint63', '-dbsize': 'int64', '-soft_masking': 'boolean', '-culling_limit': 'nonnegative_integer', '-best_hit_overhang': 'open_half', '-best_hit_score_edge': 'open_half', '-window_size': 'nonnegative_integer', '-num_threads': 'positive_integer'}
    if program != 'tblastx':
        flags.add('-ungapped')
        values.update({'-task': 'task', '-gapopen': 'integer', '-gapextend': 'integer', '-xdrop_gap': 'real', '-xdrop_gap_final': 'real', '-mt_mode': 'mt_mode'})
    if program in {'blastn', 'blastx', 'tblastx'}:
        values['-strand'] = 'strand'
    if program == 'blastn':
        flags.add('-no_greedy')
        values.update({'-perc_identity': 'percent', '-penalty': 'nonpositive_integer', '-reward': 'nonnegative_integer', '-min_raw_gapped_score': 'integer', '-template_type': 'template_type', '-template_length': 'template_length', '-dust': 'dust', '-off_diagonal_range': 'nonnegative_integer'})
    else:
        values.update({'-matrix': 'matrix', '-threshold': 'nonnegative', '-seg': 'seg'})
        if program != 'tblastx':
            flags.add('-use_sw_tback')
            values['-comp_based_stats'] = 'composition'
    if program in {'blastx', 'tblastx'}:
        values['-query_gencode'] = 'gencode'
    if program in {'tblastn', 'tblastx'}:
        values['-db_gencode'] = 'gencode'
    if program in {'blastx', 'tblastn', 'tblastx'}:
        values.update({'-sum_stats': 'boolean', '-max_intron_length': 'nonnegative_integer'})
    return (flags, values)

def standard_blast_database_program_spec(program: str) -> dict:
    """Return declared grammar and coordinate units, never availability or score."""
    flags, values = _option_grammar(program)
    protein_query = program in {'blastp', 'tblastn'}
    protein_target = program in {'blastp', 'blastx'}
    kinds = ['sequence', 'pssm'] if program == 'tblastn' else ['sequence']
    aliases = {kind: ['psitblastn' if kind == 'pssm' else program] for kind in kinds}
    contexts = {kind: resolve_blast_program_context(execution_program=program, reported_program=aliases[kind][0], scientific_mode='database', query_kind=kind, reference_kind='sequence', native_version=None) for kind in kinds}
    return {'program': program, 'query_kinds': kinds, 'query_formats': {kind: 'scoremat_asn_text' if kind == 'pssm' else 'fasta' for kind in kinds}, 'query_molecules': ['protein'] if protein_query else ['dna', 'rna'], 'database_kind': 'blast_protein_sequence' if protein_target else 'blast_nucleotide_sequence', 'query_coordinate_unit': 'aa' if protein_query else 'nt', 'reference_coordinate_unit': 'aa' if protein_target else 'nt', 'alignment_coordinate_unit': 'nt' if program == 'blastn' else 'aa', 'native_program_aliases': aliases, 'program_contexts': contexts, 'admitted_options': [{'name': name, 'operand_kind': 'flag' if name in flags else values[name]} for name in sorted(flags | values.keys())]}

def validate_standard_blast_database_options(program: str, options: list[str], *, query_kind: str) -> dict:
    """Validate selected tokens and return a detached flag-to-original-value map.

    Valueless flags map to None. Exact token spelling/order remains in the job;
    scientific interpretation may derive typed effective values separately.
    """
    flags, values = _option_grammar(program)
    if type(query_kind) is not str or query_kind not in ({'sequence', 'pssm'} if program == 'tblastn' else {'sequence'}):
        _fail('program_query_kind_conflict')
    tokens = _copy(options)
    _schema(tokens, _array(_STR))
    selected, index = ({}, 0)
    while index < len(tokens):
        flag = tokens[index]
        if flag in _COMPILER_FLAGS:
            _fail('compiler_owned_option:' + flag)
        if flag in _FORBIDDEN_FLAGS:
            _fail('forbidden_option:' + flag)
        if flag not in flags | values.keys():
            _fail('unsupported_option:' + flag)
        if flag in selected:
            _fail('duplicate_option:' + flag)
        selected[flag], index = (None, index + 1)
        if flag in flags:
            continue
        if index == len(tokens):
            _fail('option_operand_required:' + flag)
        raw, kind = (tokens[index], values[flag])
        selected[flag], index = (raw, index + 1)
        valid = False
        if kind == 'range':
            match = re.fullmatch('([1-9][0-9]*)-([1-9][0-9]*)', raw)
            valid = bool(match and int(match[1]) <= int(match[2]) and (query_kind == 'sequence'))
        elif kind == 'boolean':
            valid = raw.lower() in {'true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0'}
        elif kind == 'composition':
            valid = raw in {'D', 'd', '0', 'F', 'f', '1', '2', 'T', 't', '3'}
        elif kind == 'matrix':
            valid = re.fullmatch('[A-Za-z][A-Za-z0-9_-]*', raw) is not None
        elif kind in {'strand', 'task', 'template_type'}:
            valid = raw in ({'plus', 'minus', 'both'} if kind == 'strand' else _TASKS[program] if kind == 'task' else {'coding', 'coding_and_optimal', 'optimal'})
        elif kind in {'seg', 'dust'}:
            parts = raw.split()
            valid = raw in {'yes', 'no'}
            if len(parts) == 3:
                try:
                    valid = re.fullmatch('[0-9]+', parts[0]) is not None and int(parts[0]) > 0 and all((math.isfinite(float(v)) and float(v) >= 0 for v in parts[1:]))
                    if kind == 'dust':
                        valid = valid and all((re.fullmatch('[0-9]+', v) is not None for v in parts))
                except (ValueError, OverflowError):
                    valid = False
        else:
            try:
                number = float(raw)
                valid = math.isfinite(number)
                integer = 'integer' in kind or kind in {'int64', 'uint63', 'mt_mode', 'word_size', 'gencode', 'template_length'}
                if integer:
                    valid = valid and re.fullmatch('[+-]?[0-9]+', raw) is not None
                    if valid:
                        number = int(raw)
                        valid = -2 ** 63 <= number < 2 ** 63 if kind in {'int64', 'uint63'} else -2 ** 31 <= number < 2 ** 31
                if kind == 'positive_integer':
                    valid = valid and number >= 1
                if kind in {'nonnegative_integer', 'nonnegative', 'uint63'}:
                    valid = valid and number >= 0
                if kind == 'nonpositive_integer':
                    valid = valid and number <= 0
                if kind == 'percent':
                    valid = valid and 0 <= number <= 100
                if kind == 'open_half':
                    valid = valid and 0 < number < 0.5
                if kind == 'mt_mode':
                    valid = valid and number in {0, 1, 2}
                if kind == 'word_size':
                    valid = valid and number >= (4 if program == 'blastn' else 2)
                if kind == 'gencode':
                    valid = valid and number in _GENCODES
                if kind == 'template_length':
                    valid = valid and number in {16, 18, 21}
            except (ValueError, OverflowError):
                valid = False
        if not valid:
            _fail('invalid_option_operand:' + flag)
    for first, second in (('-culling_limit', '-best_hit_overhang'), ('-culling_limit', '-best_hit_score_edge')):
        if first in selected and second in selected:
            _fail('conflicting_options:' + first + ':' + second)
    for flag, required in (('-mt_mode', '-num_threads'), ('-template_type', '-template_length'), ('-template_length', '-template_type')):
        if flag in selected and required not in selected:
            _fail('required_option:' + flag + ':' + required)
    return selected

def _options(job):
    return validate_standard_blast_database_options(job['program'], job['options'], query_kind=job['query']['kind'])

def validate_standard_blast_database_job(job: dict) -> dict:
    job = _copy(job)
    _schema(job, NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA)
    _absolute(job['software']['executable'])
    _environment(job['environment'], job=True)
    inputs = _unique(job['inputs'], 'input_key')
    for row in inputs.values():
        _absolute(row['path'])
    q = job['query']
    spec = standard_blast_database_program_spec(job['program'])
    if q['kind'] not in spec['query_kinds']:
        _fail('program_query_kind_conflict')
    if q['input_key'] not in inputs:
        _fail('query_input_required')
    expected = {'sequence': ('query_sequence', 'fasta'), 'pssm': ('query_pssm', 'scoremat_asn_text')}[q['kind']]
    for key, row in inputs.items():
        if key == q['input_key']:
            if (row['role'], row['format']) != expected:
                _fail('query_input_role_format_conflict')
        elif row['role'] != 'metadata':
            _fail('exactly_one_query_input_required')
    for row in job['metadata_inputs']:
        if row['input_key'] not in inputs or inputs[row['input_key']]['role'] != 'metadata' or inputs[row['input_key']]['format'] != 'json':
            _fail('metadata_descriptor_input_conflict')
        if (row['consumer'], row['schema_id']) not in _METADATA_TUPLES:
            _fail('metadata_schema_unsupported')
    databases = _unique(job['databases'], 'database_key')
    db = job['databases'][0]
    if db['role'] != 'target' or db['kind'] != spec['database_kind']:
        _fail('program_database_role_conflict')
    for db in databases.values():
        _database(db)
    outputs = _unique(job['outputs'], 'output_key')
    roles = _unique(job['outputs'], 'role')
    if inputs.keys() & outputs.keys():
        _fail('input_output_key_collision')
    if roles.keys() != {'stdout', 'stderr', 'primary_report'}:
        _fail('required_output_roles_missing')
    boundaries = []
    for row in outputs.values():
        _relative(row['relative_path'])
        role, fmt = (row['role'], row['format'])
        if row['path_kind'] != 'file' or not row['required']:
            _fail('required_file_output_contract_invalid')
        boundaries.append(row['relative_path'])
        if role in {'stdout', 'stderr'} and fmt != 'text':
            _fail('stream_output_format_invalid')
        if role == 'primary_report' and fmt not in {'json15', 'tabular6', 'tabular7'}:
            _fail('primary_report_format_invalid')
        if fmt in {'tabular6', 'tabular7'}:
            delimiter = row['delimiter']
            if not {'qseqid', 'sseqid'} <= set(row['fields']):
                _fail('explicit_table_locator_fields_required')
            if delimiter is not None and (len(delimiter.encode()) != 1 or (delimiter != '\t' and (delimiter.isspace() or ord(delimiter) < 32 or ord(delimiter) == 127))):
                _fail('invalid_table_delimiter')
            if 'qcovus' in row['fields'] and job['program'] != 'blastn':
                _fail('program_tabular_field_conflict:qcovus')
        elif row['fields'] or row['delimiter'] is not None:
            _fail('non_tabular_layout_conflict')
    _disjoint(boundaries, 'output_path_overlap')
    model = job['grading_parameters']['sequence_database_model']
    if model is not None and model.get('function_priors') is not None:
        priors = model['function_priors']
        if not priors or any((not key.strip() or '\x00' in key for key in priors)) or (not any((v > 0 for v in priors.values()))):
            _fail('model_function_priors_invalid')
    _options(job)
    return job

def _unique(rows, key):
    values = {r[key]: r for r in rows}
    if len(values) != len(rows):
        _fail('duplicate:' + key)
    return values

def _disjoint(paths, code):
    for i, path in enumerate(paths):
        if any((_overlap(path, other) for other in paths[i + 1:])):
            _fail(code)

def _compile(job, *, input_paths, database_paths, output_directory):
    job = validate_standard_blast_database_job(job)
    inputs, databases = (_copy(input_paths), _copy(database_paths))
    if type(inputs) is not dict or inputs.keys() != {r['input_key'] for r in job['inputs']}:
        _fail('complete_input_path_mapping_required')
    for path in inputs.values():
        _absolute(path)
    _disjoint(list(inputs.values()), 'input_path_overlap')
    if databases != {r['database_key']: r['native_paths'] for r in job['databases']}:
        _fail('selected_database_paths_mismatch')
    if output_directory != '.':
        _absolute(output_directory)
    outputs = [{**r, 'path': str(PurePosixPath(output_directory) / r['relative_path'])} for r in job['outputs']]
    boundaries = [str(PurePosixPath(r['path']).parent) if r['path_kind'] == 'prefix' else r['path'] for r in outputs]
    if any((_overlap(a, b) for a in inputs.values() for b in boundaries)):
        _fail('input_output_path_overlap')
    q = job['query']
    argv = [job['software']['executable'], *job['options'], '-query' if q['kind'] == 'sequence' else '-in_pssm', inputs[q['input_key']], '-db', ' '.join(databases[job['databases'][0]['database_key']])]
    report = next((r for r in outputs if r['role'] == 'primary_report'))
    fmt = {'json15': '15', 'tabular6': '6', 'tabular7': '7'}[report['format']]
    if report['fields']:
        fmt += ('' if report['delimiter'] in {None, '\t'} else ' delim=' + report['delimiter']) + ' ' + ' '.join(report['fields'])
    argv.extend(['-outfmt', fmt, '-out', report['path']])
    return {'argv': argv, 'environment': _copy(job['environment']), 'outputs': outputs}

def requested_job_from_standard_blast_database(job):
    job = validate_standard_blast_database_job(job)
    compiled = _compile(job, input_paths={r['input_key']: r['path'] for r in job['inputs']}, database_paths={r['database_key']: r['native_paths'] for r in job['databases']}, output_directory='.')
    return {'argv': compiled['argv'], 'environment': compiled['environment'], 'native_blast_standard_database': job}

def validate_standard_blast_database_requested_job(request):
    request = _copy(request)
    _schema(request, NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA)
    if request != requested_job_from_standard_blast_database(request['native_blast_standard_database']):
        _fail('requested_job_compiler_mismatch')
    return request
