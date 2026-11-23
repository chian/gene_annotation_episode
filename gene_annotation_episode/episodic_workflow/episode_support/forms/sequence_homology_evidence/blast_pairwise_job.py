"""A101's pairwise BLAST job: one query sequence against one subject sequence, graded from the native JSON report.

The job declares only what the grader needs: the two operands (each a FASTA file, with the digest and the custody
artifact that identify it) and the one report (the native JSON document, ``-outfmt 15``). It declares no stdout or
stderr output and nothing here honours, writes or checks a path for them: the compiled command names the report
and nothing else. This is A101's own contract: the shared native BLAST contract (``native_blast_contracts``, which
every axis and the native driver use, and which requires stdout and stderr outputs) is not changed and is not the job
this family grades. A request is the compiled command with the job beside it, and the two must agree."""
import re

from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import (
    PROGRAMS, RESERVED_ENVIRONMENT, _absolute, _options, _relative, finite_json_copy)

VERSION = 'blast_pairwise_job'
_STR = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000]+$'}
_NULL_STR = {'anyOf': [_STR, {'type': 'null'}]}
_SHA = {'type': 'string', 'pattern': '^[0-9a-fA-F]{64}$'}
_ABS = {'type': 'string', 'pattern': '^/[^\\u0000\\n\\r]+$'}


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


JOB_SCHEMA = _object({
    'version': {'const': VERSION}, 'program': {'enum': list(PROGRAMS)},
    'software': _object({'executable': _ABS, 'sha256': _SHA, 'engine_version': _NULL_STR}),
    'environment': {'type': 'object', 'additionalProperties': {'type': 'string'}},
    'operands': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': _object({
        'role': {'enum': ['query_sequence', 'subject_sequence']}, 'path': _ABS, 'format': {'const': 'fasta'},
        'sha256': _SHA, 'size_bytes': {'type': 'integer', 'minimum': 0}, 'artifact_ref': _NULL_STR})},
    'operand_bindings': {'type': 'array', 'items': _object({
        'operand_role': {'enum': ['query_sequence', 'subject_sequence']}, 'record_ordinal': {'const': 0},
        'native_name': _NULL_STR, 'native_accession': _NULL_STR, 'subject_ref': _NULL_STR,
        'reference_ref': _NULL_STR})},
    'options': {'type': 'array', 'items': _STR},
    'report': _object({'format': {'const': 'json15'}, 'relative_path': _STR}),
    'metadata': {'type': 'object'},
})
REQUESTED_JOB_SCHEMA = _object({
    'argv': {'type': 'array', 'minItems': 1, 'items': _STR},
    'environment': {'type': 'object', 'additionalProperties': {'type': 'string'}},
    'blast_pairwise': JOB_SCHEMA,
})


def _schema(value, schema):
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error is not None:
        raise ValueError('blast_pairwise_schema:' + '.'.join(map(str, error.absolute_path)) + ':' + error.validator)


def validate_pairwise_job(value):
    job = finite_json_copy(value)
    _schema(job, JOB_SCHEMA)
    _absolute(job['software']['executable'])
    for key, item in job['environment'].items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) or '\0' in item:
            raise ValueError('blast_pairwise_invalid_environment')
        if key in RESERVED_ENVIRONMENT:
            raise ValueError('blast_pairwise_compiler_owned_environment:' + key)
    roles = set()
    for row in job['operands']:
        if row['role'] in roles:
            raise ValueError('blast_pairwise_duplicate_operand_role')
        roles.add(row['role'])
        _absolute(row['path'])
    if roles != {'query_sequence', 'subject_sequence'}:
        raise ValueError('blast_pairwise_query_and_subject_required')
    seen = set()
    for row in job['operand_bindings']:
        if row['operand_role'] in seen:
            raise ValueError('blast_pairwise_duplicate_record_binding')
        seen.add(row['operand_role'])
    _relative(job['report']['relative_path'])
    _options(job)
    return job


def compile_pairwise_job(job):
    """The command of the validated job: the report is the one output the command names."""
    job = validate_pairwise_job(job)
    paths = {row['role']: row['path'] for row in job['operands']}
    return {'argv': [job['software']['executable'], *job['options'], '-query', paths['query_sequence'],
                     '-subject', paths['subject_sequence'], '-outfmt', '15', '-out', job['report']['relative_path']],
            'environment': dict(job['environment'])}


def requested_job_from_pairwise(job):
    job = validate_pairwise_job(job)
    compiled = compile_pairwise_job(job)
    return {'argv': compiled['argv'], 'environment': compiled['environment'], 'blast_pairwise': job}


def validate_pairwise_requested_job(value):
    request = finite_json_copy(value)
    _schema(request, REQUESTED_JOB_SCHEMA)
    if request != requested_job_from_pairwise(request['blast_pairwise']):
        raise ValueError('blast_pairwise_requested_job_compiler_mismatch')
    return request


__all__ = ['VERSION', 'compile_pairwise_job', 'requested_job_from_pairwise', 'validate_pairwise_job',
           'validate_pairwise_requested_job']
