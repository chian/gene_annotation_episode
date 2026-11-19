"""Pure contracts for selected Infernal jobs; no filesystem access or execution.

The caller supplies native options and all operands. Compilation adds only the
declared input/output format and path flags. It neither prepares indexes nor
repairs a scientifically different native request.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator


PROGRAMS = ('cmsearch', 'cmscan', 'cmalign')
PRESSED_SUFFIXES = ('i1f', 'i1i', 'i1m', 'i1p')
RESERVED_ENVIRONMENT = frozenset({'TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME'})
_TEXT = {'type': 'string', 'minLength': 1, 'pattern': '^[^\x00]+$'}
_NULL_TEXT = {'anyOf': [_TEXT, {'type': 'null'}]}
_SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}


def _object(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


def _array(items):
    return {'type': 'array', 'items': items}


def finite_json_copy(value):
    def check(item):
        if item is None or type(item) in (str, int, bool):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                check(child)
            return
        raise ValueError('native_infernal_finite_json_required')
    check(value)
    return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))


def native_infernal_digest(value):
    return hashlib.sha256(json.dumps(finite_json_copy(value), sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _path(value, *, absolute):
    path = PurePosixPath(value)
    if (not value or any(c in value for c in ('\x00', '\n', '\r', '\\'))
            or value.startswith('//') or '..' in value.split('/')
            or path.is_absolute() != absolute or str(path) != value
            or value in ('.', '/', '..')):
        raise ValueError('native_infernal_normalized_path_required')


def operand_contract(program):
    if program not in PROGRAMS:
        raise ValueError('native_infernal_unknown_program')
    required = {'models': 'infernal_ascii', 'sequences': 'fasta'}
    optional = {}
    if program == 'cmscan':
        required.update({'models_' + suffix: 'infernal_' + suffix for suffix in PRESSED_SUFFIXES})
        optional = {'clanin': 'text', 'glist': 'text'}
    elif program == 'cmalign':
        optional = {'mapali': 'stockholm'}
    return required, optional


def output_contract(program):
    if program not in PROGRAMS:
        raise ValueError('native_infernal_unknown_program')
    required = {'stdout': 'infernal_stdout', 'stderr': 'text'}
    if program == 'cmalign':
        required.update(stockholm='stockholm', scores='cmalign_sfile', inserts='cmalign_ifile')
        optional = {'local_ends': 'cmalign_elfile', 'traceback': 'cmalign_tfile'}
    else:
        required['tblout'] = 'infernal_tblout'
        optional = {'included_msa': 'stockholm'} if program == 'cmsearch' else {}
    return required, optional


_INPUT_ROLES = ['models', 'sequences', 'clanin', 'glist', 'mapali'] + [
    'models_' + suffix for suffix in PRESSED_SUFFIXES]
_OUTPUT_ROLES = ['stdout', 'stderr', 'tblout', 'stockholm', 'scores', 'inserts',
                 'local_ends', 'traceback', 'included_msa']
NATIVE_INFERNAL_JOB_SCHEMA = _object({
    'version': {'const': 'native_infernal_job_v1'}, 'program': {'enum': list(PROGRAMS)},
    'software': _object({'executable': _TEXT, 'sha256': _SHA, 'engine_version': _NULL_TEXT}),
    'environment': {'type': 'object', 'additionalProperties': {'type': 'string'}},
    'operands': _array(_object({'role': {'enum': _INPUT_ROLES}, 'path': _TEXT,
        'format': {'enum': ['infernal_ascii', 'fasta', 'text', 'stockholm'] +
                          ['infernal_' + suffix for suffix in PRESSED_SUFFIXES]},
        'sha256': _SHA, 'size_bytes': {'type': 'integer', 'minimum': 0}, 'artifact_ref': _NULL_TEXT})),
    'operand_bindings': _array(_object({'operand_role': {'enum': _INPUT_ROLES},
        'record_ordinal': {'type': 'integer', 'minimum': 0}, 'native_name': _NULL_TEXT,
        'native_accession': _NULL_TEXT, 'subject_ref': _NULL_TEXT, 'reference_ref': _NULL_TEXT})),
    'options': _array(_TEXT),
    'outputs': _array(_object({'role': {'enum': _OUTPUT_ROLES},
        'format': {'enum': ['infernal_stdout', 'text', 'infernal_tblout', 'stockholm',
            'cmalign_sfile', 'cmalign_ifile', 'cmalign_elfile', 'cmalign_tfile']},
        'relative_path': _TEXT})),
    'table_format': {'enum': [None, 1, 2, 3]},
    'metadata': {'type': 'object'}, 'grading_parameters': {'type': 'object'},
})
NATIVE_INFERNAL_REQUESTED_JOB_SCHEMA = _object({
    'argv': {'type': 'array', 'minItems': 1, 'items': _TEXT},
    'environment': {'type': 'object', 'additionalProperties': {'type': 'string'}},
    'native_infernal': NATIVE_INFERNAL_JOB_SCHEMA,
})


def _schema(value, schema):
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error is not None:
        raise ValueError('native_infernal_schema:' + '.'.join(map(str, error.absolute_path))
                         + ':' + error.validator)


_OUTPUT_FLAGS = {'-o', '-A', '--tblout', '--fmt', '--sfile', '--tfile', '--ifile',
    '--elfile', '--mapali', '--clanin', '--glist', '--tformat', '--qformat',
    '--informat', '--outformat', '--regress'}
_SEARCH_FLAGS = {'-g', '--acc', '--noali', '--notextw', '--verbose', '--cut_ga',
    '--cut_nc', '--cut_tc', '--max', '--nohmm', '--mid', '--default', '--rfam',
    '--hmmonly', '--notrunc', '--anytrunc', '--nonull3', '--cyk', '--acyk',
    '--toponly', '--bottomonly'}
_ALIGN_FLAGS = {'-g', '--optacc', '--cyk', '--sample', '--notrunc', '--sub',
    '--hbanded', '--fixedtau', '--nonbanded', '--small', '--mapstr', '--noss',
    '--dnaout', '--noprob', '--matchonly', '--miss', '--ileaved', '--verbose'}


def native_options(job):
    """Parse selected native operands; do not silently fix incompatible choices."""
    program = job['program']
    if program == 'cmalign':
        flags = _ALIGN_FLAGS
        values = {'--cpu': 'integer', '--seed': 'integer', '--tau': 'tau',
            '--mxsize': 'positive', '--maxtau': 'maxtau',
            '--flanktoins': 'flanktoins', '--flankselfins': 'flankselfins'}
    else:
        flags = _SEARCH_FLAGS | ({'--nomiss'} if program == 'cmsearch' else {'--oclan', '--oskip'})
        values = {'--cpu': 'integer', '--textw': 'textw', '-Z': 'positive',
            '-E': 'positive', '-T': 'real', '--incE': 'positive', '--incT': 'real',
            '--FZ': 'real', '--Fmid': 'real', '--mxsize': 'matrix',
            '--smxsize': 'matrix', '--wcx': 'wcx'}
    result, tokens, i = {}, job['options'], 0
    while i < len(tokens):
        flag = tokens[i]
        i += 1
        if flag in _OUTPUT_FLAGS:
            raise ValueError('native_infernal_compiler_owned_option:' + flag)
        if flag not in flags | values.keys():
            raise ValueError('native_infernal_unsupported_option:' + flag)
        if flag in result:
            raise ValueError('native_infernal_duplicate_option:' + flag)
        result[flag] = None
        if flag in flags:
            continue
        if i == len(tokens):
            raise ValueError('native_infernal_option_operand_required:' + flag)
        raw, kind = tokens[i], values[flag]
        i += 1
        try:
            number = float(raw)
            valid = math.isfinite(number)
            if kind in {'integer', 'textw'}:
                valid &= bool(re.fullmatch(r'[+]?\d+', raw))
                valid &= number >= (120 if kind == 'textw' else 0)
            if kind == 'positive':
                valid &= number > 0
            if kind == 'matrix':
                valid &= number > .1
            if kind == 'wcx':
                valid &= number >= 1.25
            if kind == 'tau':
                valid &= 1e-18 < number < 1
            if kind in {'maxtau', 'flanktoins', 'flankselfins'}:
                valid &= 0 < number < {'maxtau': .5, 'flanktoins': .4, 'flankselfins': .9}[kind]
        except (ValueError, OverflowError):
            valid = False
        if not valid:
            raise ValueError('native_infernal_invalid_option_operand:' + flag)
        result[flag] = raw
    # Ordinary native compatibility checks are left to the native executable,
    # except when they affect the compiler's declared input/output contract.
    roles = {row['role'] for row in job['operands']}
    outputs = {row['role'] for row in job['outputs']}
    if program == 'cmalign' and 'local_ends' in outputs and '-g' in result:
        raise ValueError('native_infernal_global_alignment_has_no_EL_output')
    if program == 'cmscan':
        if ('--oclan' in result or '--oskip' in result or 'clanin' in roles) and job['table_format'] != 2:
            raise ValueError('native_infernal_overlap_options_require_format2')
        if '--oclan' in result and 'clanin' not in roles:
            raise ValueError('native_infernal_clan_input_required')
        if 'glist' in roles and '-g' in result:
            raise ValueError('native_infernal_glist_and_global_conflict')
    if '--nomiss' in result and 'included_msa' not in outputs:
        raise ValueError('native_infernal_nomiss_requires_alignment_output')
    if ('--mapstr' in result or '--noss' in result) and 'mapali' not in roles:
        raise ValueError('native_infernal_mapali_input_required')
    return result


def validate_native_infernal_job(value):
    job = finite_json_copy(value)
    _schema(job, NATIVE_INFERNAL_JOB_SCHEMA)
    _path(job['software']['executable'], absolute=True)
    for key, value in job['environment'].items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) or '\x00' in value:
            raise ValueError('native_infernal_invalid_environment')
        if key in RESERVED_ENVIRONMENT:
            raise ValueError('native_infernal_compiler_owned_environment:' + key)
    program = job['program']
    fmt = job['table_format']
    if (program == 'cmalign' and fmt is not None or program != 'cmalign' and
            (type(fmt) is not int or fmt not in ({1, 3} if program == 'cmsearch' else {1, 2, 3}))):
        raise ValueError('native_infernal_program_table_format_conflict')
    required, optional = operand_contract(program)
    roles = {}
    for row in job['operands']:
        if row['role'] in roles or {**required, **optional}.get(row['role']) != row['format']:
            raise ValueError('native_infernal_operand_role_format_conflict')
        _path(row['path'], absolute=True)
        roles[row['role']] = row
    if required.keys() - roles.keys():
        raise ValueError('native_infernal_missing_operands:' + ','.join(sorted(required.keys() - roles.keys())))
    if program == 'cmscan':
        for suffix in PRESSED_SUFFIXES:
            if roles['models_' + suffix]['path'] != roles['models']['path'] + '.' + suffix:
                raise ValueError('native_infernal_pressed_input_association:' + suffix)
    seen = set()
    for binding in job['operand_bindings']:
        key = binding['operand_role'], binding['record_ordinal']
        if (type(binding['record_ordinal']) is not int or key in seen or
                binding['operand_role'] not in {'models', 'sequences', 'mapali'} & roles.keys()):
            raise ValueError('native_infernal_input_record_binding_conflict')
        seen.add(key)
    required, optional = output_contract(program)
    outputs, paths = {}, []
    for row in job['outputs']:
        role, path = row['role'], row['relative_path']
        if role in outputs or {**required, **optional}.get(role) != row['format']:
            raise ValueError('native_infernal_output_role_format_conflict')
        _path(path, absolute=False)
        if path.split('/')[0] in {'inputs', 'tmp', 'cache', 'bundle.json', '.bundle.json.writing',
                '.native-infernal-owner.json', '..native-infernal-owner.json.writing'}:
            raise ValueError('native_infernal_reserved_output_path')
        current = PurePosixPath(path)
        if any(current == old or current in old.parents or old in current.parents for old in paths):
            raise ValueError('native_infernal_output_path_overlap')
        paths.append(current)
        outputs[role] = row
    if required.keys() - outputs.keys():
        raise ValueError('native_infernal_missing_outputs:' + ','.join(sorted(required.keys() - outputs.keys())))
    parameters = job['grading_parameters']
    key, allowed = ('population', {'all', 'newly_aligned', 'inherited'}) if program == 'cmalign' else (
        'hit_scope', {'reported', 'included'})
    if (set(parameters) - {key} or key in parameters and
            (type(parameters[key]) is not str or parameters[key] not in allowed)):
        raise ValueError('native_infernal_grading_parameters_invalid')
    native_options(job)
    return job


def compile_native_infernal_job(job, *, input_paths=None, output_directory='.'):
    job = validate_native_infernal_job(job)
    paths = {row['role']: row['path'] for row in job['operands']}
    if input_paths is not None:
        if type(input_paths) is not dict or input_paths.keys() != paths.keys():
            raise ValueError('native_infernal_complete_staged_paths_required')
        for path in input_paths.values():
            if type(path) is not str:
                raise ValueError('native_infernal_normalized_path_required')
            _path(path, absolute=True)
        paths = dict(input_paths)
    if output_directory != '.':
        _path(output_directory, absolute=True)
    if job['program'] == 'cmscan':
        for suffix in PRESSED_SUFFIXES:
            if paths['models_' + suffix] != paths['models'] + '.' + suffix:
                raise ValueError('native_infernal_staged_pressed_association:' + suffix)
    outputs = deepcopy(job['outputs'])
    out = {row['role']: str(PurePosixPath(output_directory) / row['relative_path']) for row in outputs}
    argv = [job['software']['executable'], *job['options']]
    if job['program'] == 'cmalign':
        for role, flag in (('stockholm', '-o'), ('scores', '--sfile'), ('inserts', '--ifile'),
                           ('local_ends', '--elfile'), ('traceback', '--tfile')):
            if role in out:
                argv += [flag, out[role]]
        if 'mapali' in paths:
            argv += ['--mapali', paths['mapali']]
        argv += ['--informat', 'fasta']
        if '--ileaved' not in job['options']:
            argv += ['--outformat', 'Stockholm']
    else:
        argv += ['--tblout', out['tblout'], '--fmt', str(job['table_format'])]
        if 'included_msa' in out:
            argv += ['-A', out['included_msa']]
        for role in ('clanin', 'glist'):
            if role in paths:
                argv += ['--' + role, paths[role]]
        argv += ['--tformat' if job['program'] == 'cmsearch' else '--qformat', 'fasta']
    argv += [paths['models'], paths['sequences']]
    return {'argv': argv, 'environment': dict(job['environment']), 'outputs': outputs}


def requested_job_from_infernal(job):
    job = validate_native_infernal_job(job)
    compiled = compile_native_infernal_job(job)
    return {'argv': compiled['argv'], 'environment': compiled['environment'], 'native_infernal': job}


def validate_native_infernal_requested_job(value):
    request = finite_json_copy(value)
    _schema(request, NATIVE_INFERNAL_REQUESTED_JOB_SCHEMA)
    if request != requested_job_from_infernal(request['native_infernal']):
        raise ValueError('native_infernal_requested_job_compiler_mismatch')
    return request
