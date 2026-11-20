"""The BLAST data-preparation job: a closed job built by code from controlled commission fields.

Preparation sets up databases and data for later work (a custom database to search, masked sequences). It produces
a prepared-data record, never an evidence sheet. Two kinds are placed: ``database_build`` (``makeblastdb`` over a
FASTA the commissioner holds) and ``masking`` (``dustmasker`` or ``segmasker`` over a FASTA the commissioner holds).

Nothing here reads a file, runs a program or writes a record. A commission is a plain record of controlled values:
a kind from a fixed vocabulary, record references (resolved by the caller through custody into the bytes passed
here), booleans, a value from a fixed set and numbers in a range. There is no command, no path and no free text. A
wrong commission raises ``ValueError`` with a stable ``blast_preparation_*`` code and nothing repairs it.

**Declared and derived kind.** The commission declares its kind. ``derive_kind`` reads the kind again from the
compiled job (the program its first step runs), and ``compile_preparation`` raises when the two differ.

**What is compiled.** ``compile_preparation`` returns the job a ``JobAccess`` route runs (a command and its
environment), the plan the job reads (``plan.json``), the driver's source bytes and the names under which they are
staged. The staged names map to custody artifacts the caller stores; the route writes them into the job's directory.
The driver (``tools/.../blast_preparation_driver.py``) is standard-library only and stands in for no shell: it runs
the plan's argv steps in order and writes one receipt, so the same job runs on a local resource or on a cluster.
"""
from __future__ import annotations

import hashlib
import json
import re

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import (
    finite_json_copy, native_blast_digest)

PLAN_VERSION = 'blast_preparation_job_v1'
RECEIPT_VERSION = 'blast_preparation_receipt_v1'
KINDS = ('database_build', 'masking')
MOLECULES = ('protein', 'nucleotide')
DB_VERSIONS = (4, 5)
MASKING_PROGRAMS = ('dustmasker', 'segmasker')
MASKING_OUTPUTS = ('interval', 'fasta')
KIND_OF_PROGRAM = {'makeblastdb': 'database_build', 'dustmasker': 'masking', 'segmasker': 'masking'}
PREPARED_KIND = {('database_build', 'protein'): 'blast_protein_database',
                 ('database_build', 'nucleotide'): 'blast_nucleotide_database',
                 ('masking', 'fasta'): 'masked_sequences', ('masking', 'interval'): 'mask_intervals'}
DBTYPE = {'protein': 'prot', 'nucleotide': 'nucl'}
# Staged file names inside the job's directory, and where a database or a mask is written.
INPUT_NAME, PLAN_NAME, DRIVER_NAME = 'input.fasta', 'plan.json', 'driver.py'
DATABASE_PREFIX, MASK_OUTPUT = 'db/prepared', 'masked.out'
RECEIPT_NAME = 'receipt.json'
_I32 = 2 ** 31 - 1
# Numeric parameters of each masking program: (kind, minimum, maximum), as the native tools define them.
MASKING_PARAMETERS = {'dustmasker': {'window': ('integer', 1, _I32), 'level': ('integer', 0, _I32),
                                     'linker': ('integer', 0, _I32)},
                      'segmasker': {'window': ('integer', 1, _I32), 'locut': ('number', 0, None),
                                    'hicut': ('number', 0, None)}}
_SHA = re.compile(r'^[0-9a-f]{64}$')
_AMINO = re.compile(r'^[A-Za-z*\-]+$')
_NUCLEOTIDE = re.compile(r'^[A-Za-z\-]+$')


def _fail(code):
    raise ValueError('blast_preparation_' + code)


def describe_fasta(data, *, molecule, parse_seqids):
    """The records and residues of a FASTA, counted from its bytes. A FASTA the native tools would refuse raises:
    no record, an empty record, a sequence line before a header, a residue outside the molecule's letters, or (when
    sequence identifiers are parsed) a repeated identifier."""
    if type(data) is not bytes or molecule not in MOLECULES:
        _fail('fasta_input_invalid')
    text = data.decode('utf-8', errors='replace')
    letters = _AMINO if molecule == 'protein' else _NUCLEOTIDE
    records, residues, current, seen, held = 0, 0, None, set(), 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('>'):
            if current is not None and held == 0:
                _fail('fasta_empty_record')
            identifier = line[1:].split()[0] if line[1:].split() else ''
            if not identifier:
                _fail('fasta_record_without_identifier')
            if parse_seqids and identifier in seen:
                _fail('fasta_repeated_identifier')
            seen.add(identifier)
            current, held = identifier, 0
            records += 1
        else:
            if current is None or not letters.match(line):
                _fail('fasta_residue_invalid')
            held += len(line)
            residues += len(line)
    if records == 0 or held == 0:
        _fail('fasta_has_no_complete_record')
    return {'records': records, 'residues': residues}


def _number(value, low, high, integer):
    if type(value) is bool:
        return False
    if integer:
        ok = type(value) is int
    else:
        ok = type(value) in (int, float) and value == value and value not in (float('inf'), float('-inf'))
    return ok and (low is None or value >= low) and (high is None or value <= high)


def validate_commission(fields):
    """The controlled fields of one preparation commission, as a closed record, or the stable error.

    ``database_build``: ``kind``, ``molecule``, ``input_ref``, ``parse_seqids`` (boolean), ``hash_index`` (boolean),
    ``db_version`` (4 or 5). ``masking``: ``kind``, ``molecule``, ``input_ref``, ``program``, ``output_format`` and
    the numeric parameters of that program, each optional and in its native range."""
    fields = finite_json_copy(fields)
    kind = fields.get('kind') if type(fields) is dict else None
    if kind not in KINDS:
        _fail('kind_not_in_vocabulary')
    if kind == 'database_build':
        if set(fields) != {'kind', 'molecule', 'input_ref', 'parse_seqids', 'hash_index', 'db_version'}:
            _fail('database_build_fields')
        if (fields['molecule'] not in MOLECULES or type(fields['parse_seqids']) is not bool
                or type(fields['hash_index']) is not bool or type(fields['db_version']) is not int
                or fields['db_version'] not in DB_VERSIONS):
            _fail('database_build_values')
    else:
        base = {'kind', 'molecule', 'input_ref', 'program', 'output_format'}
        if not base <= set(fields) or fields.get('program') not in MASKING_PROGRAMS:
            _fail('masking_fields')
        allowed = MASKING_PARAMETERS[fields['program']]
        if set(fields) - base - set(allowed):
            _fail('masking_parameter_unknown')
        if fields['output_format'] not in MASKING_OUTPUTS or fields['molecule'] not in MOLECULES:
            _fail('masking_values')
        if (fields['program'] == 'segmasker') != (fields['molecule'] == 'protein'):
            _fail('masking_program_molecule_conflict')
        for name in set(fields) & set(allowed):
            kind_name, low, high = allowed[name]
            if not _number(fields[name], low, high, kind_name == 'integer'):
                _fail('masking_parameter_out_of_range:' + name)
    if type(fields['input_ref']) is not str or not fields['input_ref']:
        _fail('input_ref_required')
    return fields


def _identity(artifact_ref, data, counts):
    return {'name': INPUT_NAME, 'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data),
            'artifact_ref': artifact_ref, **counts}


def _software(value):
    if (type(value) is not dict or set(value) != {'executable', 'sha256', 'engine_version'}
            or type(value['executable']) is not str or not value['executable'].startswith('/')
            or '..' in value['executable'].split('/') or not _SHA.match(str(value['sha256']))
            or value['engine_version'] is not None and type(value['engine_version']) is not str):
        _fail('software_identity_invalid')
    return {key: value[key] for key in ('executable', 'sha256', 'engine_version')}


def _masking_argv(software, fields):
    argv = [software['executable'], '-in', INPUT_NAME, '-out', MASK_OUTPUT, '-outfmt', fields['output_format']]
    for name in sorted(set(fields) & set(MASKING_PARAMETERS[fields['program']])):
        argv += ['-' + name, str(fields[name])]
    return argv


def compile_preparation(fields, *, input_bytes, software, python, scratch_bytes=None):
    """The job, plan and staged files of one commission.

    ``fields``: the controlled commission. ``input_bytes``: the bytes of the FASTA ``fields['input_ref']`` names,
    read by the caller through custody. ``software``: ``{program: {executable, sha256, engine_version}}`` of the
    resource that will run the job, from its configuration (the commission carries no path). ``python``: the
    absolute interpreter of that resource. ``scratch_bytes``: the resource policy's scratch bound when it has one;
    an input that alone exceeds it is a commission to another resource and raises.

    Returns ``{'job': {'command', 'env'}, 'plan', 'plan_bytes', 'inputs': {name: 'input'|'plan'|'driver'},
    'kind', 'prepared_kind', 'key', 'estimates'}``. The caller stores the plan and the driver as artifacts and
    passes ``{name: artifact_ref}`` as the launch's inputs."""
    fields = validate_commission(fields)
    kind = fields['kind']
    if type(python) is not str or not python.startswith('/'):
        _fail('python_executable_required')
    counts = describe_fasta(input_bytes, molecule=fields['molecule'],
                            parse_seqids=fields.get('parse_seqids', False))
    if scratch_bytes is not None and len(input_bytes) > scratch_bytes:
        _fail('input_exceeds_resource_scratch')
    identity = _identity(fields['input_ref'], input_bytes, counts)
    if kind == 'database_build':
        build = _software(software['makeblastdb'])
        argv = [build['executable'], '-in', INPUT_NAME, '-dbtype', DBTYPE[fields['molecule']], '-out',
                DATABASE_PREFIX, '-blastdb_version', str(fields['db_version'])]
        argv += (['-parse_seqids'] if fields['parse_seqids'] else []) + (['-hash_index'] if fields['hash_index'] else [])
        key = native_blast_digest({'kind': kind, 'input': identity['sha256'],
                                   'options': {k: fields[k] for k in ('molecule', 'parse_seqids', 'hash_index',
                                                                      'db_version')}})[:24]
        argv += ['-title', key]
        steps = [{'name': 'build', 'argv': argv, 'software': build}]
        for tool, flags in (('blastdbcmd', ['-db', DATABASE_PREFIX, '-info']),
                            ('blastdbcheck', ['-db', DATABASE_PREFIX, '-dbtype', DBTYPE[fields['molecule']],
                                              '-full'])):
            checker = _software(software[tool])
            steps.append({'name': 'info' if tool == 'blastdbcmd' else 'check',
                          'argv': [checker['executable'], *flags], 'software': checker})
        prepared = PREPARED_KIND[(kind, fields['molecule'])]
        operation = {'molecule': fields['molecule'], 'parse_seqids': fields['parse_seqids'],
                     'hash_index': fields['hash_index'], 'db_version': fields['db_version'],
                     'output_prefix': DATABASE_PREFIX}
    else:
        tool = _software(software[fields['program']])
        key = native_blast_digest({'kind': kind, 'input': identity['sha256'],
                                   'options': {k: v for k, v in fields.items() if k != 'input_ref'}})[:24]
        steps = [{'name': 'build', 'argv': _masking_argv(tool, fields), 'software': tool}]
        prepared = PREPARED_KIND[(kind, fields['output_format'])]
        operation = {'molecule': fields['molecule'], 'program': fields['program'],
                     'output_format': fields['output_format'], 'output_name': MASK_OUTPUT,
                     'parameters': {k: fields[k] for k in sorted(set(fields) & set(MASKING_PARAMETERS[
                         fields['program']]))}}
    plan = {'version': PLAN_VERSION, 'kind': kind, 'prepared_kind': prepared, 'key': key, 'input': identity,
            'operation': operation, 'steps': steps, 'receipt': RECEIPT_NAME}
    plan = finite_json_copy(plan)
    if derive_kind(plan) != kind:
        _fail('declared_and_derived_kind_differ')
    plan_bytes = json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()
    return {'job': {'command': [python, DRIVER_NAME, PLAN_NAME], 'env': {}}, 'plan': plan, 'plan_bytes': plan_bytes,
            'inputs': {INPUT_NAME: 'input', PLAN_NAME: 'plan', DRIVER_NAME: 'driver'}, 'kind': kind,
            'prepared_kind': prepared, 'key': key,
            # Duration and size are unknown before the first run of a kind: only what is known is recorded.
            'estimates': {'input_bytes': len(input_bytes), 'input_records': counts['records'],
                          'input_residues': counts['residues']}}


def derive_kind(plan):
    """The kind of a compiled plan, read from the program its first step runs (never from the declared field)."""
    if type(plan) is not dict or type(plan.get('steps')) is not list or not plan['steps']:
        _fail('plan_has_no_steps')
    program = plan['steps'][0]['argv'][0].rsplit('/', 1)[-1]
    if program not in KIND_OF_PROGRAM:
        _fail('program_not_a_preparation_program')
    return KIND_OF_PROGRAM[program]


def validate_plan(plan):
    """A plan as the driver and the receipt reader read it: closed, with a kind that agrees with its steps."""
    plan = finite_json_copy(plan)
    if (type(plan) is not dict or plan.get('version') != PLAN_VERSION or plan.get('kind') not in KINDS
            or derive_kind(plan) != plan['kind']):
        _fail('plan_invalid_or_kind_conflict')
    return plan


__all__ = ['KINDS', 'PREPARED_KIND', 'PLAN_VERSION', 'RECEIPT_VERSION', 'RECEIPT_NAME', 'INPUT_NAME', 'PLAN_NAME',
           'DRIVER_NAME', 'DATABASE_PREFIX', 'MASK_OUTPUT', 'compile_preparation', 'derive_kind', 'describe_fasta',
           'validate_commission', 'validate_plan']
