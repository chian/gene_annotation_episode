"""A105's own pairwise BLAST comparison: two held sequence records compared as one unit on the local resource (a copy of the
shape A101's pairwise comparison has, owned by A105; nothing is imported from A101).

``pairwise_blast_comparison`` runs in this order:

1. read the two sequences through custody and make the two FASTA files as artifacts;
2. build the pairwise job (one query against one subject, the native JSON report, ``-outfmt 15``) and check it;
3. run it on the local resource through the inspection point (``execute_on_local_resource`` with ``wait=True``: launch,
   wait for the end, fetch what the job left), with the two files staged in the job's own directory;
4. grade the one report into the pairwise sheet (``literature_pairwise_grading.graded_report``): BLAST reporting no
   alignment is the graded "no reported alignment" result, a normal outcome;
5. keep the grading through the scoped store: the grading artifact, a ``native.blast.pairwise`` source over the fetched
   report (its operands are the query and the reference) and the grading's data-product row.

The outcome has the shape of every tool outcome of an episode (``status``, ``record_refs``, ``changed_record_refs``,
``result``, ``feedback``). ``completed``: ``result`` holds the controlled features code read from the sheet. What can
still go wrong is a fault of the environment (the resource refused the job, the program ended with a nonzero exit code,
the report is not of the two operands): a ``failed`` outcome with its code, reported once."""
import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import (
    PROGRAMS, RESERVED_ENVIRONMENT, _absolute, _options, _relative, finite_json_copy)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pairwise_grading import (
    PROVIDER, graded_report, grading_features, record_grading_product, retain_grading)

JOB_NAME = 'pairwise_blast'
REPORT = 'report.json'
NUCLEOTIDE = ('dna', 'rna')
# The molecules each program compares: the query, then the subject.
PROGRAM_MOLECULES = {'blastp': (('protein',), ('protein',)), 'blastn': (NUCLEOTIDE, NUCLEOTIDE),
                     'blastx': (NUCLEOTIDE, ('protein',)), 'tblastn': (('protein',), NUCLEOTIDE),
                     'tblastx': (NUCLEOTIDE, NUCLEOTIDE)}

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


def _validated_job(value):
    job = finite_json_copy(value)
    error = next(Draft202012Validator(JOB_SCHEMA).iter_errors(job), None)
    if error is not None:
        raise ValueError('blast_pairwise_schema:' + '.'.join(map(str, error.absolute_path)) + ':' + error.validator)
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


def requested_job_from_pairwise(value):
    """The command of the validated job (the report is the one output the command names) with the job beside it."""
    job = _validated_job(value)
    paths = {row['role']: row['path'] for row in job['operands']}
    return {'argv': [job['software']['executable'], *job['options'], '-query', paths['query_sequence'],
                     '-subject', paths['subject_sequence'], '-outfmt', '15', '-out', job['report']['relative_path']],
            'environment': dict(job['environment']), 'blast_pairwise': job}


def _outcome(status, code, *, category, detail=None):
    feedback = {'category': category, 'code': code, 'retryable': False}
    if detail is not None:
        feedback['detail'] = detail
    return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': feedback}


def _sequence(store, ref):
    """The molecule and the residues (upper case) of a subject record the episode holds."""
    record = store.get(ref)
    return record.get('molecule'), store.get_artifact(record['sequence_ref']).decode('ascii').upper()


def _job(store, directory, program, sequences, executable_directory):
    """The requested pairwise job of the two sequences, with the files it stages (``{file name: artifact}``)."""
    operands, inputs = [], {}
    for role, (_, _, residues) in sequences.items():
        name, data = role + '.fasta', ('>' + role + '\n' + residues + '\n').encode()
        artifact = store.artifact(data, 'text/x-fasta')
        operands.append({'role': role, 'path': str(directory / name), 'format': 'fasta',
                         'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data),
                         'artifact_ref': artifact})
        inputs[name] = artifact
    executable = (Path(executable_directory) / program).resolve()
    requested = requested_job_from_pairwise({
        'version': VERSION, 'program': program,
        'software': {'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                     'engine_version': None},
        'environment': {}, 'operands': operands,
        'operand_bindings': [{'operand_role': role, 'record_ordinal': 0, 'native_name': None,
                              'native_accession': None, 'subject_ref': ref, 'reference_ref': None}
                             for role, (ref, _, _) in sequences.items()],
        'options': [], 'report': {'format': 'json15', 'relative_path': REPORT}, 'metadata': {}})
    return requested, inputs


async def pairwise_blast_comparison(ctx, *, program, query_ref, reference_ref, resource_id, executable_directory):
    """Compare the query with the reference by ``program`` on the local resource and keep the graded result.
    ``ctx`` is the unit's context of an episode that declares the service ``job_access``."""
    store, access = ctx.store, ctx.services['job_access']
    sequences = {'query_sequence': (query_ref, *_sequence(store, query_ref)),
                 'subject_sequence': (reference_ref, *_sequence(store, reference_ref))}
    directory = Path(access.describe(resource_id)['workspace']) / job_handle(ctx.operation_key, resource_id, JOB_NAME)
    requested, inputs = _job(store, directory, program, sequences, executable_directory)
    store.artifact(json.dumps(requested, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False),
                   'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, requested['argv'], requested['environment'], wait=True,
                                          inputs=inputs, name=JOB_NAME)
    if ran['status'] != 'completed':
        refused = (ran['launch'] if ran['launch']['status'] != 'completed' else ran['fetch'])['failure']
        return _outcome('failed', refused['code'], category='job', detail=refused['detail'])
    if ran['returncode'] != 0:
        return _outcome('failed', 'pairwise_blast_program_exit_nonzero', category='job',
                        detail={'returncode': ran['returncode'], 'stderr': ran['stderr'][-2000:]})
    (report_ref,) = [item['ref'] for item in ran['fetch']['results'] if item['name'] == REPORT]
    query, subject = sequences['query_sequence'][2], sequences['subject_sequence'][2]
    try:
        grading = graded_report(store.get_artifact(report_ref), program, query, subject)
    except ValueError as error:
        return _outcome('failed', str(error), category='grading')
    sheet = grading['sheet']
    with store.transaction():
        grading_ref = retain_grading(store, native_artifact_ref=report_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': report_ref, 'text_ref': None,
            'request_ref': None, 'version': sheet['input']['search']['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query_ref, reference_ref]}, origin='tool')
        product = record_grading_product(store, grading_ref=grading_ref, grading=grading, source_ref=source['id'],
                                         used=[report_ref])
    refs = [source['id'], grading_ref, product['id']]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': grading_features(grading, grading_ref), 'feedback': None}


__all__ = ['PROGRAM_MOLECULES', 'pairwise_blast_comparison', 'requested_job_from_pairwise']
