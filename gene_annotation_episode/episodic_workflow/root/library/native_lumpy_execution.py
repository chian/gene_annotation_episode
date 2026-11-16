"""One explicitly selected LUMPY PE/SR command on the existing native lifecycle.

This owner authenticates supplied Files, software and one original attempt. It
does not extract signals, filter/annotate calls, interpret VCF or calculate
scientific measurements. The shared VCF result owner retains that authority.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import sys

from jsonschema import Draft202012Validator, validators

from gene_annotation_episode.acquisition_types import AcquisitionError
from gene_annotation_episode.local_job_policy import LocalJobPolicy, check_scratch_budget
import gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts as shared
from .native_atac_file_records import _directory
from .native_atac_control_files import _immutable, _read_control
from .native_atac_file_records import _regular
from .native_atac_control_files import _stage
from .native_atac_file_records import confined_file, declaration
from .native_atac_control_files import decode_json
from .native_driver_runtime_verification import verify_driver_runtime
from .native_atac_differential_reference import extract_atac_bam_header
from .retained_file_pin import file_pin


OPERATION = 'detect_and_characterize_structural_variations'
MODE = 'lumpy_pe_sr_vcf'
DRIVER_MODULE = 'gene_annotation_episode.episodic_workflow.root.library.native_lumpy_execution'

RUN_PLAN_FILENAME = 'lumpy-plan.json'
ATTEMPT_DIRECTORY_NAME = 'lumpy-attempt'
OWNER_FILENAME = '.native-lumpy-owner.json'
STARTED_FILENAME = '.native-lumpy-started.json'
SEAL_FILENAME = 'lumpy-seal.json'
REQUEST_VERSION = 'lumpy_request_v1'
PLAN_VERSION = 'lumpy_run_plan_v1'
SEAL_VERSION = 'lumpy_command_seal_v1'
POLICY = deepcopy(shared.POLICY)
require, canonical, digest = shared.require, shared.canonical, shared.digest
failure, unique_failures = shared.failure, shared.unique_failures
obj, arr, enum, nullable = shared._obj, shared._arr, shared._enum, shared._null
TEXT, ID, BOOL = deepcopy(shared._TEXT), deepcopy(shared._ID), deepcopy(shared._BOOL)
FILE, PIN = deepcopy(shared._FILE), deepcopy(shared._PIN)
INTEGER = {'type': 'integer', 'minimum': -(2**31), 'maximum': 2**31 - 1}
NATIVE_TOKEN = {'type': 'string', 'minLength': 1, 'maxLength': 512,
    'pattern': r'^[^\x00-\x20\x7f,:]+$'}
SONAME = {'type': 'string', 'minLength': 1, 'maxLength': 255,
    'pattern': r'^[A-Za-z0-9_+.-]+\.so(?:\.[A-Za-z0-9_+.-]+)*$'}
DECIMAL = {'type': 'string', 'minLength': 1, 'maxLength': 512,
    'pattern': r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$'}
_COMMON = dict(signal_key={**ID, 'maxLength': 500}, output_sample_label=NATIVE_TOKEN,
    declared_sample_id=nullable(TEXT), reference_id=nullable(TEXT), bam=FILE,
    read_group=nullable(NATIVE_TOKEN))
PE = obj(kind={'const': 'paired_end'}, **_COMMON, histogram=FILE,
    parameters=obj(mean=DECIMAL, stdev=DECIMAL, read_length=INTEGER,
        min_non_overlap=INTEGER, discordant_z=INTEGER, back_distance=INTEGER,
        weight=INTEGER, min_mapping_threshold=INTEGER))
SR = obj(kind={'const': 'split_read'}, **_COMMON,
    parameters=obj(back_distance=INTEGER, min_non_overlap=INTEGER, weight=INTEGER,
        min_mapping_threshold=INTEGER, min_clip=INTEGER))
REQUEST = obj(version={'const': REQUEST_VERSION}, operation={'const': OPERATION},
    mode={'const': MODE}, run_key=ID, signals=arr({'oneOf': [PE, SR]}, minItems=1),
    parameters=obj(minimum_sample_weight=INTEGER, trim_threshold=DECIMAL, probability_output=BOOL))
NATIVE_RUNTIME = obj(executable=PIN, loader=PIN,
    libraries=arr(obj(name=SONAME, file=PIN)), reported_version=nullable(TEXT))
SOFTWARE = obj(driver_runtime=shared.driver_runtime_schema(), native_runtime=NATIVE_RUNTIME)
JOB = obj(request=REQUEST, software=SOFTWARE,
    input_bindings=arr(obj(input_key=ID, file=FILE, path=TEXT), minItems=1))
REQUESTED = obj(argv=arr(TEXT, minItems=6, maxItems=6), environment=deepcopy(shared._ENV), native_lumpy=JOB)
SPEC = obj(file_key=ID, role=enum('vcf', 'stderr', 'bam_header', 'seal'),
    relative_path=TEXT, format=ID, required=BOOL)
PLAN = obj(version={'const': PLAN_VERSION}, identity=deepcopy(shared._IDENTITY),
    requested_job=REQUESTED, attempt_directory=TEXT, policy={'const': POLICY}, outputs=arr(SPEC, minItems=4))
INPUT_SEAL = obj(input_key=ID, signal_key=ID, role=enum('bam', 'histogram'),
    file=FILE, staging_state=enum('verified', 'failed', 'not_attempted'),
    staged=deepcopy(shared._DECL), staging_temporary=deepcopy(shared._DECL))
SEAL = obj(version={'const': SEAL_VERSION}, identity=deepcopy(shared._IDENTITY),
    producer_ref=ID, software_sha256=deepcopy(shared._SHA), argv=arr(TEXT), environment=deepcopy(shared._ENV),
    inputs=arr(INPUT_SEAL, minItems=1), input_inspections=arr(shared.atac_execution_schema('HeaderExtraction')),
    started_at=nullable(TEXT), finished_at=nullable(TEXT), returncode=nullable({'type': 'integer'}),
    outcome=enum('succeeded', 'failed', 'not_run'),
    outputs=arr(obj(specification=SPEC, declaration=deepcopy(shared._DECL)), minItems=3),
    failures=arr(shared.atac_execution_schema('Failure')))
SCHEMAS = {'Binding': obj(operation={'const': OPERATION}, mode={'const': MODE}, software=SOFTWARE),
    'NativeRuntime': NATIVE_RUNTIME, 'SoftwareBinding': SOFTWARE, 'Request': REQUEST, 'NativeJob': JOB, 'RequestedJob': REQUESTED,
    'RunPlan': PLAN, 'CommandSeal': SEAL}
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    'integer', lambda checker, value: type(value) is int))
_REQUIRED_MODULES = (
    DRIVER_MODULE,
    'gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_reference',
    'gene_annotation_episode.__init__',
    'gene_annotation_episode.episodic_workflow.__init__',
    'gene_annotation_episode.episodic_workflow.root.__init__',
    'gene_annotation_episode.episodic_workflow.root.library.__init__',
)

_REQUIRED_DEPENDENCIES = ('jsonschema', 'attrs', 'referencing', 'rpds-py', 'jsonschema-specifications')


def _same(left, right):
    return canonical(left) == canonical(right)


def _record(kind, value):
    try:
        canonical(value)
        _STRICT(SCHEMAS[kind]).validate(value)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('invalid_lumpy_' + kind.lower()) from error
    except Exception as error:
        from jsonschema.exceptions import ValidationError
        if not isinstance(error, ValidationError):
            raise
        raise ValueError('invalid_lumpy_' + kind.lower()) from error
    return deepcopy(value)


def lumpy_execution_schema(kind, *, bindings=None):
    require(type(kind) is str and kind in SCHEMAS, 'unsupported_lumpy_execution_schema')
    schema = deepcopy(SCHEMAS[kind])
    if bindings is not None:
        require(kind == 'RequestedJob', 'unsupported_lumpy_execution_schema')
        choices = [{'properties': {'native_lumpy': {'properties': {
            'software': {'const': row['software']}, 'request': {'properties': {
                'operation': {'const': OPERATION}, 'mode': {'const': MODE}}}}}}}
            for row in validate_lumpy_bindings(bindings)]
        schema = {'allOf': [schema, {'anyOf': choices} if choices else {'not': {}}]}
    return schema


def _file(value):
    require(value['artifact_ref'] == 'artifact_' + value['sha256']
        and type(value['size_bytes']) is int, 'artifact_digest_mismatch')


def _decimal(value, *, nonzero=False):
    try:
        number = Decimal(value)
        floating = float(value)
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise ValueError('invalid_lumpy_native_number') from error
    require(number.is_finite() and math.isfinite(floating)
        and (not nonzero or number != 0 and floating != 0)
        and (number == 0 or floating != 0), 'invalid_lumpy_native_number')


def _grammar_path(value):
    path = shared.path_value(value, absolute=True)
    require(not any(char in value for char in ',:'), 'invalid_lumpy_native_path')
    return path


def _runtime(value):
    value = _record('NativeRuntime', value)
    for pin in [value['executable'], value['loader'], *(row['file'] for row in value['libraries'])]:
        shared.path_value(pin['path'], absolute=True)
    names = [row['name'] for row in value['libraries']]
    require(len(names) == len(set(names)), 'native_dependency_unavailable')
    root = PurePosixPath(value['executable']['path']).parent.parent
    require(root.name == 'native' and PurePosixPath(value['executable']['path']) == root / 'bin/lumpy'
        and PurePosixPath(value['loader']['path']) == root / 'loader'
        and all(PurePosixPath(row['file']['path']) == root / 'lib' / row['name'] for row in value['libraries'])
        and ':' not in str(root), 'native_dependency_unavailable')
    return deepcopy(value)


def _current_driver(driver):
    return DRIVER_MODULE in {row['module'] for row in driver['implementation_files']}


def _current_module_sources(module_root):
    """Authenticate the actual current source closure, including package ports.

    The original source walker follows every function-local import. Explicit
    package members and ancestor initializers complete its current -m closure;
    no old supplied inventory is rewritten or reinterpreted by this function.
    """
    import ast
    from .native_driver_source import _source_closure
    root = Path(module_root)
    seeds = list(_REQUIRED_MODULES)
    while True:
        sources = _source_closure(module_root, seeds)
        additional = set()
        for name, path in sources.items():
            package = name.rsplit('.', 1)[0]
            parts = package.split('.')
            additional.update('.'.join(parts[:count]) + '.__init__'
                              for count in range(1, len(parts) + 1))
            for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
                if not isinstance(node, ast.ImportFrom):
                    continue
                base = parts[:len(parts) - node.level + 1] if node.level else []
                imported = '.'.join([*base, *([node.module] if node.module else [])])
                if imported != 'gene_annotation_episode' and not imported.startswith('gene_annotation_episode.'):
                    continue
                directory = root / imported.replace('.', '/')
                if not directory.is_dir():
                    continue
                for alias in node.names:
                    member = directory / alias.name
                    if member.with_suffix('.py').is_file():
                        additional.add(imported + '.' + alias.name)
                    elif (member / '__init__.py').is_file():
                        additional.add(imported + '.' + alias.name + '.__init__')
        additional.difference_update(sources)
        if not additional:
            return sources
        seeds = sorted(set(sources) | additional)


def _verify_lumpy_driver_runtime(driver):
    # Preserve the original file/dependency verification and error order first.
    verify_driver_runtime(driver)
    if _current_driver(driver):
        selected = Path(driver['module_root']) / (DRIVER_MODULE.replace('.', '/') + '.py')
        require(Path(__file__).resolve(strict=True) == selected.resolve(strict=True),
                'native_dependency_unavailable')
        required = _current_module_sources(driver['module_root'])
        supplied = {row['module']: row['sha256'] for row in driver['implementation_files']}
        require(set(required) <= set(supplied), 'native_dependency_unavailable')
        # The original verifier above checked every supplied file's bytes. This
        # checks that no actual current source/package operand was omitted.


def _software(value):
    result = _record('SoftwareBinding', value)
    shared.validate_driver_runtime(result['driver_runtime'],
        required_modules=_REQUIRED_MODULES,
        required_dependencies=_REQUIRED_DEPENDENCIES)
    _runtime(result['native_runtime'])
    return result


def validate_lumpy_bindings(values):
    require(type(values) is list, 'invalid_lumpy_bindings')
    result = [_record('Binding', row) for row in values]
    for row in result:
        _software(row['software'])
    require(len({digest(row) for row in result}) == len(result), 'invalid_lumpy_bindings')
    return result


def validate_lumpy_request(value):
    value = _record('Request', value)
    require(len({row['signal_key'] for row in value['signals']}) == len(value['signals']), 'lumpy_signal_key_conflict')
    require(value['parameters']['minimum_sample_weight'] != 0, 'invalid_lumpy_native_number')
    _decimal(value['parameters']['trim_threshold'])
    for signal in value['signals']:
        _file(signal['bam'])
        require(signal['bam']['format'] == 'bam', 'invalid_lumpy_bam_format')
        p = signal['parameters']
        required = ('read_length', 'min_non_overlap', 'discordant_z', 'back_distance', 'weight') if signal['kind'] == 'paired_end' else ('back_distance', 'weight')
        require(all(p[key] != 0 for key in required), 'invalid_lumpy_native_number')
        if signal['kind'] == 'paired_end':
            _file(signal['histogram'])
            require(signal['histogram']['format'] == 'lumpy_insert_histogram', 'invalid_lumpy_histogram_format')
            _decimal(p['mean'], nonzero=True)
            _decimal(p['stdev'], nonzero=True)
    return value


def _input_occurrences(request):
    result = []
    for ordinal, signal in enumerate(request['signals']):
        for role in ('bam', 'histogram') if signal['kind'] == 'paired_end' else ('bam',):
            result.append(dict(input_key=signal['signal_key'] + ':' + role, signal_key=signal['signal_key'],
                role=role, file=deepcopy(signal[role]), relative_path=f'inputs/{ordinal:06d}.' + ('bam' if role == 'bam' else 'histo')))
    return result


def validate_lumpy_native_job(value):
    value = _record('NativeJob', value)
    request = validate_lumpy_request(value['request'])
    _software(value['software'])
    occurrences = _input_occurrences(request)
    require([row['input_key'] for row in value['input_bindings']] == [row['input_key'] for row in occurrences], 'lumpy_input_binding_conflict')
    paths = {}
    for binding, occurrence in zip(value['input_bindings'], occurrences):
        require(_same(binding['file'], occurrence['file']), 'lumpy_input_binding_conflict')
        path = shared.path_value(binding['path'], absolute=True)
        if path in paths:
            require(_same(paths[path], binding['file']), 'lumpy_input_binding_conflict')
        paths[path] = binding['file']
    return value


def _current_environment(value):
    require(type(value) is dict and all(type(k) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k)
        and type(v) is str and "\0" not in v for k, v in value.items()), "invalid_native_environment")
    require(all(value.get(k) == "1" for k in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE")),
        "invalid_native_environment")
    for name in ("PYTHONHOME", "TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR"):
        shared.path_value(value.get(name), absolute=True)


def requested_job_from_lumpy(job, *, environment):
    job = validate_lumpy_native_job(job)
    _current_environment(environment)
    driver = job['software']['driver_runtime']

    require(environment.get('PYTHONPATH') == os.pathsep.join([driver['module_root'], *shared._dependency_roots(driver)]), 'native_dependency_unavailable')
    return dict(argv=[driver['python_executable'], '-B', '-S', '-m',
        DRIVER_MODULE, RUN_PLAN_FILENAME],
        environment=deepcopy(environment), native_lumpy=job)


def validate_lumpy_requested_job(value):
    value = _record('RequestedJob', value)
    require(_same(value, requested_job_from_lumpy(value['native_lumpy'], environment=value['environment'])))
    return value


def lumpy_output_files(request):
    request = validate_lumpy_request(request)
    rows = [dict(file_key='vcf', role='vcf', relative_path='native/result.vcf', format='vcf', required=True),
        dict(file_key='stderr', role='stderr', relative_path='native/stderr.log', format='native_stderr', required=True)]
    rows.extend(dict(file_key='header:' + signal['signal_key'], role='bam_header',
        relative_path=f'headers/{ordinal:06d}.sam', format='sam_header_text', required=False)
        for ordinal, signal in enumerate(request['signals']))
    return [*rows, dict(file_key='seal', role='seal', relative_path=SEAL_FILENAME, format=SEAL_VERSION, required=True)]


def _elf_metadata(pin):
    """Read bounded ELF metadata from this supplied file, without discovery."""
    with _regular(pin['path']) as stream:
        before = os.fstat(stream.fileno())
        require(before.st_size == pin['size_bytes'], 'native_dependency_unavailable')
        def read_at(offset, size):
            require(type(offset) is int and type(size) is int and offset >= 0 and size >= 0
                and offset <= before.st_size and size <= before.st_size - offset, 'native_dependency_unavailable')
            stream.seek(offset)
            raw = stream.read(size)
            require(len(raw) == size, 'native_dependency_unavailable')
            return raw
        ident = read_at(0, 16)
        require(ident[:4] == b'\x7fELF' and ident[4] in (1, 2) and ident[5] in (1, 2)
            and ident[6] == 1 and ident[7] in (0, 3) and ident[8] == 0, 'native_dependency_unavailable')
        bits, endian = ident[4], '<' if ident[5] == 1 else '>'
        fmt = endian + ('HHIIIIIHHHHHH' if bits == 1 else 'HHIQQQIHHHHHH')
        header = struct.unpack(fmt, read_at(16, struct.calcsize(fmt)))
        kind, machine, version, _, phoff, _, _, ehsize, phsize, phcount, *_ = header
        require(kind in (2, 3) and version == 1 and ehsize >= 16 + struct.calcsize(fmt)
            and phcount not in (0, 65535), 'native_dependency_unavailable')
        pfmt = endian + ('IIIIIIII' if bits == 1 else 'IIQQQQQQ')
        require(phsize >= struct.calcsize(pfmt) and phoff <= before.st_size
            and phcount <= (before.st_size - phoff) // phsize, 'native_dependency_unavailable')
        loads, dynamics, interpreters = [], [], []
        for index in range(phcount):
            fields = struct.unpack(pfmt, read_at(phoff + index * phsize, struct.calcsize(pfmt)))
            if bits == 1:
                ptype, offset, address, _, file_size, _, _, _ = fields
            else:
                ptype, _, offset, address, _, file_size, _, _ = fields
            require(offset <= before.st_size and file_size <= before.st_size - offset, 'native_dependency_unavailable')
            if ptype == 1:
                loads.append((address, file_size, offset))
            elif ptype == 2:
                dynamics.append((offset, file_size))
            elif ptype == 3:
                raw = read_at(offset, file_size)
                require(raw.endswith(b'\0') and b'\0' not in raw[:-1], 'native_dependency_unavailable')
                interpreters.append(raw[:-1].decode('ascii'))
        require(len(dynamics) == 1 and len(interpreters) <= 1, 'native_dependency_unavailable')
        dfmt = endian + ('iI' if bits == 1 else 'qQ')
        dsize = struct.calcsize(dfmt)
        offset, length = dynamics[0]
        require(length % dsize == 0, 'native_dependency_unavailable')
        entries, terminated = [], False
        for position in range(offset, offset + length, dsize):
            tag, value = struct.unpack(dfmt, read_at(position, dsize))
            if tag == 0:
                terminated = True
                break
            entries.append((tag, value))
        require(terminated and not any(tag in (0x7fffffff, 0x7ffffffd, 0x6ffffefc, 0x6ffffefb)
            for tag, _ in entries), 'native_dependency_unavailable')
        def singleton(tag):
            values = [value for key, value in entries if key == tag]
            require(len(values) == 1, 'native_dependency_unavailable')
            return values[0]
        address, length = singleton(5), singleton(10)
        tables = [offset + address - start for start, size, offset in loads
            if start <= address and address - start <= size and length <= size - (address - start)]
        require(len(set(tables)) == 1, 'native_dependency_unavailable')
        strings = read_at(tables[0], length)
        def string(index):
            require(index < len(strings), 'native_dependency_unavailable')
            end = strings.find(b'\0', index)
            require(end >= index, 'native_dependency_unavailable')
            return strings[index:end].decode('ascii')
        needed = [string(value) for tag, value in entries if tag == 1]
        sonames = [string(value) for tag, value in entries if tag == 14]
        paths = [string(value) for tag, value in entries if tag in (15, 29)]
        require(len(sonames) <= 1 and len(needed) == len(set(needed)), 'native_dependency_unavailable')
        after = os.fstat(stream.fileno())
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'native_dependency_unavailable')
    return dict(elf_class=bits, byte_order=ident[5], osabi=ident[7], abi_version=ident[8],
        machine=machine, type=kind, interpreter=interpreters[0] if interpreters else None,
        soname=sonames[0] if sonames else None, needed=needed, search_paths=paths)


def _verify_native_runtime(value):
    runtime = _runtime(value)
    selected = [('executable', runtime['executable']), ('loader', runtime['loader']),
        *[(row['name'], row['file']) for row in runtime['libraries']]]
    metadata = {}
    for name, pin in selected:
        require(file_pin(pin['path']) == pin, 'native_dependency_unavailable')
        metadata[name] = _elf_metadata(pin)
    executable, loader = metadata['executable'], metadata['loader']
    require(loader['type'] == 3 and loader['interpreter'] is None and loader['soname'] is not None
        and executable['interpreter'] is not None
        and PurePosixPath(executable['interpreter']).is_absolute()
        and PurePosixPath(executable['interpreter']).name == loader['soname'], 'native_dependency_unavailable')
    signature = (loader['elf_class'], loader['byte_order'], loader['machine'], loader['abi_version'])
    require(all((row['elf_class'], row['byte_order'], row['machine'], row['abi_version']) == signature
        for row in metadata.values()), 'native_dependency_unavailable')
    declarations = {row['name']: row['file'] for row in runtime['libraries']}
    for name, pin in declarations.items():
        require(metadata[name]['type'] == 3 and metadata[name]['soname'] == name, 'native_dependency_unavailable')
        if name == loader['soname']:
            require(pin['sha256'] == runtime['loader']['sha256']
                and pin['size_bytes'] == runtime['loader']['size_bytes'], 'native_dependency_unavailable')
    supplied = set(declarations) | {loader['soname']}
    library_root = PurePosixPath(runtime['executable']['path']).parent.parent / 'lib'
    for name, pin in selected:
        row = metadata[name]
        require(all(re.fullmatch(SONAME['pattern'], needed) and needed in supplied for needed in row['needed']), 'native_dependency_unavailable')
        for raw in row['search_paths']:
            for entry in raw.split(':'):
                expanded = entry.replace('${ORIGIN}', str(PurePosixPath(pin['path']).parent)).replace(
                    '$ORIGIN', str(PurePosixPath(pin['path']).parent))
                require(entry and '$' not in expanded and PurePosixPath(expanded).is_absolute()
                    and os.path.normpath(expanded) == str(library_root), 'native_dependency_unavailable')
    for pin in (runtime['executable'], runtime['loader']):
        with _regular(pin['path']) as stream:
            require(os.fstat(stream.fileno()).st_mode & 0o111, 'native_dependency_unavailable')
    return metadata


def validate_lumpy_run_plan(value):
    value = _record('RunPlan', value)
    requested = validate_lumpy_requested_job(value['requested_job'])
    identity = value['identity']
    execution = _grammar_path(identity['execution_id'])
    attempt = _grammar_path(value['attempt_directory'])
    require(execution.name == 'native.json' and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME
        and identity['attempt_id'] == digest(identity['operation_key'])
        and identity['requested_job_sha256'] == digest(requested))
    require(_same(value['outputs'], lumpy_output_files(requested['native_lumpy']['request'])))
    return value


def lumpy_driver_argv(plan):
    plan = validate_lumpy_run_plan(plan)
    return [*plan['requested_job']['argv'][:-1], str(PurePosixPath(plan['identity']['execution_id']).parent / RUN_PLAN_FILENAME)]


def _driver_environment(plan):
    driver = plan['requested_job']['native_lumpy']['software']['driver_runtime']
    root = PurePosixPath(plan['attempt_directory'])
    environment = {**plan['requested_job']['environment'],
        'PYTHONPATH': os.pathsep.join([driver['module_root'], *shared._dependency_roots(driver)]),
        'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'), 'TMPDIR': str(root / 'tmp'),
        'XDG_CACHE_HOME': str(root / 'cache'), 'PIP_CACHE_DIR': str(root / 'cache/pip')}
    environment.pop('OMP_NUM_THREADS', None)
    environment.pop('OPENBLAS_NUM_THREADS', None)
    return environment


def _native_environment(plan):
    root = PurePosixPath(plan['attempt_directory'])
    return dict(PATH='/usr/bin:/bin', LC_ALL='C.UTF-8',
            TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'), TMPDIR=str(root / 'tmp'), XDG_CACHE_HOME=str(root / 'cache'))


def lumpy_command_argv(plan):
    plan = validate_lumpy_run_plan(plan)
    job = plan['requested_job']['native_lumpy'];request = job['request'];runtime = job['software']['native_runtime']
    root = PurePosixPath(plan['attempt_directory']);parameters = request['parameters']
    command = [runtime['loader']['path'], '--inhibit-cache', '--library-path',
        str(PurePosixPath(runtime['executable']['path']).parent.parent / 'lib'), runtime['executable']['path']]
    if parameters['probability_output']:
        command.append('-P')
    command.extend(['-msw', str(parameters['minimum_sample_weight']), '-tt', parameters['trim_threshold'], '-t', str(root / 'tmp/interchrom-')])
    for ordinal, signal in enumerate(request['signals']):
        p = signal['parameters'];entries = [('bam_file', str(root / f'inputs/{ordinal:06d}.bam'))]
        if signal['kind'] == 'paired_end':
            entries.extend([('histo_file', str(root / f'inputs/{ordinal:06d}.histo')),
                *[(key, str(p[key])) for key in ('mean', 'stdev', 'read_length', 'min_non_overlap', 'discordant_z')]])
        else:
            entries.append(('min_non_overlap', str(p['min_non_overlap'])))
        entries.extend((key, str(p[key])) for key in ('back_distance', 'weight'))
        entries.extend([('id', signal['output_sample_label']), ('min_mapping_threshold', str(p['min_mapping_threshold']))])
        if signal['kind'] == 'split_read':
            entries.append(('min_clip', str(p['min_clip'])))
        if signal['read_group'] is not None:
            entries.append(('read_group', signal['read_group']))
        command.extend(['-pe' if signal['kind'] == 'paired_end' else '-sr', ','.join(key + ':' + value for key, value in entries)])
    return command


def _producer_ref(plan):
    return 'lumpy_producer_' + digest({'identity': plan['identity'], 'command': MODE})


def _input_specs(request):
    return [dict(relative_path=row['relative_path'], format=row['file']['format']) for row in _input_occurrences(request)]


def _temporary_input_spec(occurrence):
    path = PurePosixPath(occurrence['relative_path'])
    return dict(relative_path=str(path.with_name('.' + path.name + '.staging')), format=occurrence['file']['format'])


def _check_declaration(value, spec):
    require(value['relative_path'] == spec['relative_path'] and value['format'] == spec['format'])
    require((type(value['size_bytes']) is int and type(value['sha256']) is str) if value['state'] == 'present'
        else value['size_bytes'] is None and value['sha256'] is None)


def validate_lumpy_seal(value, *, plan):
    plan = validate_lumpy_run_plan(plan);value = _record('CommandSeal', value)
    job = plan['requested_job']['native_lumpy'];request = job['request']
    require(_same(value['identity'], plan['identity']) and value['producer_ref'] == _producer_ref(plan)
        and value['software_sha256'] == digest(job['software'])
        and _same(value['argv'], lumpy_command_argv(plan)) and _same(value['environment'], _native_environment(plan)))
    occurrences = _input_occurrences(request)
    require(len(value['inputs']) == len(occurrences))
    for actual, expected in zip(value['inputs'], occurrences):
        require(_same({key: actual[key] for key in ('input_key', 'signal_key', 'role', 'file')},
            {key: expected[key] for key in ('input_key', 'signal_key', 'role', 'file')}))
        _check_declaration(actual['staged'], dict(relative_path=expected['relative_path'], format=expected['file']['format']))
        _check_declaration(actual['staging_temporary'], _temporary_input_spec(expected))
        if actual['staging_state'] == 'verified':
            require(actual['staged']['state'] == 'present' and actual['staging_temporary']['state'] == 'absent'
                and all(actual['staged'][key] == expected['file'][key] for key in ('sha256', 'size_bytes')))
        elif actual['staging_state'] == 'failed':
            require(any(problem['stage'] == 'input' and problem['binding_key'] == actual['input_key']
                and problem['artifact_ref'] == actual['file']['artifact_ref'] for problem in value['failures']))
        else:
            require(actual['staged']['state'] == actual['staging_temporary']['state'] == 'absent')
    expected_outputs = [row for row in plan['outputs'] if row['role'] != 'seal']
    require(_same([row['specification'] for row in value['outputs']], expected_outputs))
    for row in value['outputs']:
        _check_declaration(row['declaration'], row['specification'])
    inspections = value['input_inspections'];ordinals = [row['input_ordinal'] for row in inspections]
    require(ordinals == sorted(set(ordinals)) and all(type(index) is int and 0 <= index < len(request['signals']) for index in ordinals))
    verified_bams = {row['signal_key'] for row in value['inputs'] if row['role'] == 'bam' and row['staging_state'] == 'verified'}
    require(ordinals == [i for i, signal in enumerate(request['signals']) if signal['signal_key'] in verified_bams])
    for row in inspections:
        ordinal = row['input_ordinal'];signal = request['signals'][ordinal]
        shared.validate_atac_record('HeaderExtraction', row)
        require(row['input_key'] == signal['signal_key'] + ':bam' and row['callpeak_run_key'] == request['run_key']
            and _same(row['input_file'], signal['bam']))
        expected = next(output for output in value['outputs'] if output['specification']['file_key'] == 'header:' + signal['signal_key'])
        require(_same(row['header'], expected['declaration']))
        if row['producer_outcome'] == 'succeeded':
            require(row['supplied_extent'] == 'complete' and row['header']['state'] == 'present')
        else:
            require(bool(row['failures']))
        require({digest(problem) for problem in row['failures']} <= {digest(problem) for problem in value['failures']})
    if value['outcome'] == 'not_run':
        require(value['started_at'] is value['finished_at'] is value['returncode'] is None and bool(value['failures']))
        require(all(row['declaration']['state'] == 'absent' for row in value['outputs'] if row['specification']['role'] in ('vcf', 'stderr')))
        if all(row['staging_state'] == 'verified' for row in value['inputs']):
            require(any(row['stage'] == 'execution' and row['code'] in ('native_dependency_unavailable', 'resource_limit')
                for row in value['failures']))
    else:
        require(len(inspections) == len(request['signals']) and all(row['staging_state'] == 'verified' for row in value['inputs']))
        try:
            start, end = datetime.fromisoformat(value['started_at']), datetime.fromisoformat(value['finished_at'])
            require(start.tzinfo is not None and end.tzinfo is not None and end >= start)
        except (TypeError, ValueError) as error:
            raise ValueError('original_attempt_mismatch') from error
        require(value['returncode'] == 0 if value['outcome'] == 'succeeded' else value['returncode'] != 0)
        if value['outcome'] == 'failed':
            code = 'native_dependency_unavailable' if value['returncode'] is None else 'native_nonzero_exit'
            require(any(row['code'] == code for row in value['failures']))
        if value['outcome'] == 'succeeded':
            for row in value['outputs']:
                if row['specification']['required'] and row['declaration']['state'] == 'absent':
                    require(any(problem['code'] == 'native_output_unavailable' and problem['file_key'] ==
                        row['specification']['file_key'] for problem in value['failures']))
    return value


def run_lumpy(plan):
    """Stage original bytes and seal one call, preserving failed/partial output."""
    plan = validate_lumpy_run_plan(plan)
    directory = _directory(plan['attempt_directory']);seal_path = confined_file(directory, SEAL_FILENAME)
    if directory.exists() and any(directory.iterdir()):
        require(_same(_read_control(confined_file(directory, OWNER_FILENAME)), plan))
        require(seal_path.exists(), 'unsealed_native_attempt')
        saved = validate_lumpy_seal(_read_control(seal_path), plan=plan)
        for row in saved['outputs']:
            require(_same(declaration(row['specification'], directory), row['declaration']))
        for row in saved['inputs']:
            require(_same(declaration(row['staged'], directory), row['staged']))
            require(_same(declaration(row['staging_temporary'], directory), row['staging_temporary']))
        return saved
    require(_current_driver(plan['requested_job']['native_lumpy']['software']['driver_runtime']),
            'selected_worker_identity_conflict')
    directory.mkdir(parents=True, exist_ok=True)

    _immutable(directory / OWNER_FILENAME, plan)
    _immutable(directory / STARTED_FILENAME, dict(plan=plan, started_at=datetime.now(timezone.utc).isoformat()))
    for name in ('inputs', 'headers', 'native', 'tmp', 'cache/pip'):
        (directory / name).mkdir(parents=True, exist_ok=True)
    job = plan['requested_job']['native_lumpy'];request = job['request']
    policy = LocalJobPolicy(**plan['policy']);problems, staged, inspections = [], {}, []
    runtime_available = True
    try:
        _verify_lumpy_driver_runtime(job['software']['driver_runtime'])
        _verify_native_runtime(job['software']['native_runtime'])
    except (OSError, ValueError, ImportError, UnicodeError):
        runtime_available = False
        problems.append(failure('native_dependency_unavailable', 'execution', step_key=request['run_key'], requirement='native_runtime'))
    occurrences = _input_occurrences(request)
    staging_states = {row['input_key']: 'not_attempted' for row in occurrences}
    if runtime_available:
        for occurrence, binding in zip(occurrences, job['input_bindings']):
            try:
                staged[occurrence['input_key']] = _stage(binding,
                    dict(relative_path=occurrence['relative_path']), directory=directory, policy=policy)
                staging_states[occurrence['input_key']] = 'verified'
            except (OSError, ValueError, AcquisitionError) as error:
                staging_states[occurrence['input_key']] = 'failed'
                code = ('resource_limit' if isinstance(error, AcquisitionError) else
                    'artifact_digest_mismatch' if str(error) == 'artifact_digest_mismatch' else 'input_unavailable')
                problems.append(failure(code, 'input', step_key=request['run_key'], binding_key=binding['input_key'],
                    artifact_ref=binding['file']['artifact_ref'], requirement='resource_allocation'
                        if code == 'resource_limit' else 'matching_file_identity'))
        for ordinal, signal in enumerate(request['signals']):
            input_key = signal['signal_key'] + ':bam'
            if input_key not in staged:
                continue
            relative = f'headers/{ordinal:06d}.sam'
            observed = extract_atac_bam_header(input_path=staged[input_key], input_file=signal['bam'],
                input_key=input_key, callpeak_run_key=request['run_key'], input_ordinal=ordinal,
                output_path=confined_file(directory, relative), output_relative_path=relative, policy=policy)
            inspections.append(observed)
            problems.extend(observed['failures'])
    started = finished = returncode = None
    outcome = 'not_run'
    if len(staged) == len(occurrences):
        try:
            _verify_lumpy_driver_runtime(job['software']['driver_runtime'])
            _verify_native_runtime(job['software']['native_runtime'])
            check_scratch_budget(directory.parent, policy)
        except (OSError, ValueError, ImportError, UnicodeError, AcquisitionError) as error:
            problems.append(failure('resource_limit' if isinstance(error, AcquisitionError) else 'native_dependency_unavailable',
                'execution', step_key=request['run_key'], requirement='resource_allocation'
                    if isinstance(error, AcquisitionError) else 'native_runtime'))
        else:
            started = datetime.now(timezone.utc).isoformat()
            try:
                with confined_file(directory, 'native/result.vcf').open('xb') as stdout, \
                        confined_file(directory, 'native/stderr.log').open('xb') as stderr:
                    completed = subprocess.run(lumpy_command_argv(plan), cwd=directory,
                        env=_native_environment(plan), stdout=stdout, stderr=stderr, check=False)
                    returncode = completed.returncode
                outcome = 'succeeded' if returncode == 0 else 'failed'
                if returncode != 0:
                    problems.append(failure('native_nonzero_exit', 'execution', step_key=request['run_key'], requirement='original_native_outcome'))
            except OSError:
                outcome = 'failed'
                problems.append(failure('native_dependency_unavailable', 'execution', step_key=request['run_key'], requirement='native_runtime'))
            finished = datetime.now(timezone.utc).isoformat()
    outputs = [dict(specification=spec, declaration=declaration(spec, directory))
        for spec in plan['outputs'] if spec['role'] != 'seal']
    if outcome == 'succeeded':
        for row in outputs:
            if row['specification']['required'] and row['declaration']['state'] == 'absent':
                problems.append(failure('native_output_unavailable', 'execution', step_key=request['run_key'],
                    file_key=row['specification']['file_key'], requirement='complete_native_output'))
    seal = validate_lumpy_seal(dict(version=SEAL_VERSION, identity=plan['identity'], producer_ref=_producer_ref(plan),
        software_sha256=digest(job['software']), argv=lumpy_command_argv(plan), environment=_native_environment(plan),
        inputs=[dict(**{key: row[key] for key in ('input_key', 'signal_key', 'role', 'file')},
            staging_state=staging_states[row['input_key']],
            staged=declaration(dict(relative_path=row['relative_path'], format=row['file']['format']), directory),
            staging_temporary=declaration(_temporary_input_spec(row), directory)) for row in occurrences],
        input_inspections=inspections, started_at=started, finished_at=finished, returncode=returncode,
        outcome=outcome, outputs=outputs, failures=unique_failures(problems)), plan=plan)
    _immutable(seal_path, seal)
    return seal


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    require(type(arguments) is list and len(arguments) == 1, 'lumpy_plan_path_required')
    plan = validate_lumpy_run_plan(_read_control(Path(arguments[0])))
    require(_current_driver(plan['requested_job']['native_lumpy']['software']['driver_runtime']),
            'selected_worker_identity_conflict')
    seal = run_lumpy(plan)

    # Header inspection qualifies the evidence. It does not override a real
    # successful native exit, and that exit does not establish valid VCF output.
    return 0 if seal['outcome'] == 'succeeded' else 1


__all__ = ['OPERATION', 'MODE', 'POLICY', 'DRIVER_MODULE', 'RUN_PLAN_FILENAME', 'ATTEMPT_DIRECTORY_NAME',
    'OWNER_FILENAME', 'STARTED_FILENAME', 'SEAL_FILENAME', 'REQUEST_VERSION', 'PLAN_VERSION', 'SEAL_VERSION',
    'lumpy_execution_schema', 'validate_lumpy_bindings', 'validate_lumpy_request', 'validate_lumpy_native_job',
    'validate_lumpy_requested_job', 'validate_lumpy_run_plan', 'requested_job_from_lumpy', 'lumpy_driver_argv',
    'lumpy_command_argv', 'lumpy_output_files', 'run_lumpy', 'validate_lumpy_seal']


if __name__ == '__main__':
    raise SystemExit(main())
