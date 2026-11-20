"""One pairwise BLAST comparison as one unit: one query sequence against one reference sequence on a local resource,
from the job to the graded correspondence of the two.

``pairwise_blast_comparison`` is what an episode's ``pairwise_blast`` tool calls. The episode's model chose the
controlled values (the program, the two sequence records, the local resource); everything else is done here by code,
in this order, inside the one unit that calls it:

1. read the two sequences through custody and make the two FASTA files as artifacts;
2. build the pairwise job with the library's contract and check that the kind derived from the job is ``pairwise``
   (the tool is the declaration of the kind; a job of another kind raises);
3. run it on the local resource through the inspection point (``execute_on_local_resource`` with ``wait=True``:
   launch, wait for the end, fetch what the job left), with the two files staged in the job's own directory;
4. grade the one report the job declares into the pairwise sheet of the job's own two operands;
5. keep the grading through custody: the grading artifact, a ``native.blast.pairwise`` source over the fetched
   report, the search row that enters the search into the A101 sheet's tool profile, and one ``alignment``
   observation for each reported alignment (the query's interval, the reference's interval and the measurements of
   the already graded cell), in the shape the registry's ``sequence.align`` gives its observation. The observation
   is what a reasoning commit assesses against a hypothesis; the A101 credit reads the graded cells of assessed
   observations.

Grading is not a choice of anyone: it follows the fetch in the same unit.

The outcome has the shape of every tool outcome of an episode (``status``, ``record_refs``, ``changed_record_refs``,
``result``, ``feedback``). ``completed``: ``record_refs`` are the source, the grading artifact and the search row,
the search row and the observations, and ``result`` holds the controlled features code read from the sheet with the
references of the observations. ``invalid``: the two molecules are not what
the program compares, or the report is not of the two operands; nothing is kept. ``failed``: the resource refused the
job or the program ended with a nonzero exit code; nothing is graded. ``feedback`` holds the code and ``retryable``:
whether the same call can succeed if made again. The comparison is deterministic, so only a refusal the resource
itself marks as retryable is."""
import hashlib
from pathlib import Path

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    PAIRWISE, checked_analysis_kind)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_pairwise_job import (
    requested_job_from_pairwise)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    SEARCHES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_graders import (
    grade_blast_result)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_pairwise_features import (
    SHEET_SCHEMA, grading_features)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    measurements, number, ref)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search import blast_search

JOB_NAME = 'pairwise_blast'
REPORT = 'report.json'
PROVIDER = 'native.blast.pairwise'
NUCLEOTIDE = ('dna', 'rna')
# The molecules each program compares: the query, then the subject.
PROGRAM_MOLECULES = {'blastp': (('protein',), ('protein',)), 'blastn': (NUCLEOTIDE, NUCLEOTIDE),
                     'blastx': (NUCLEOTIDE, ('protein',)), 'tblastn': (('protein',), NUCLEOTIDE),
                     'tblastx': (NUCLEOTIDE, NUCLEOTIDE)}


def _outcome(status, code, *, category, detail=None, retryable=False):
    feedback = {'category': category, 'code': code, 'retryable': retryable}
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
        'version': 'blast_pairwise_job_v1', 'program': program,
        'software': {'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                     'engine_version': None},
        'environment': {}, 'operands': operands,
        'operand_bindings': [{'operand_role': role, 'record_ordinal': 0, 'native_name': None,
                              'native_accession': None, 'subject_ref': ref, 'reference_ref': None}
                             for role, (ref, _, _) in sequences.items()],
        'options': [], 'report': {'format': 'json15', 'relative_path': REPORT}, 'metadata': {}})
    return requested, inputs


def _graded(store, report_ref, program, query, subject):
    """The grading of the fetched report as the pairwise sheet of the two operands. A report of another sheet type
    or of sequences of other lengths raises ``ValueError``."""
    grading = grade_blast_result(store.get_artifact(report_ref), mode='pairwise', resource='local',
                                 output_format='json2', request={'program': program, 'query_length': len(query)},
                                 _retain_correspondence=True)
    sheet = grading['sheet']
    if sheet['schema'] != SHEET_SCHEMA:
        raise ValueError('blast_pairwise_result_type_conflict')
    if sheet['query']['length'] != len(query) or sheet['reference']['length'] != len(subject):
        raise ValueError('blast_pairwise_result_operand_conflict')
    return grading


def _observations(store, grading, source_ref, program, sequences):
    """One ``alignment`` observation for each alignment of the sheet, projected from its already graded cell (nothing
    is calculated or graded again). The query is the subject of the observation; the reference record is its source
    subject."""
    (query_ref, _, query), (subject_ref, _, subject) = sequences['query_sequence'], sequences['subject_sequence']
    query_unit, subject_unit, model_unit = blast_search.PROGRAM_UNITS[program]
    refs = []
    for hsp in grading['sheet']['hsps']:
        row = blast_search.hsp_row(hsp['native'], component=hsp['components'], program=program,
                                   query_length=len(query), reference_length=len(subject), hit_ordinal=0,
                                   hsp_ordinal=hsp['hsp_index'])
        (start, end), (subject_start, subject_end) = row['query_interval'], row['reference_interval']
        refs.append(store.put('observation', {
            'kind': 'alignment', 'subject_refs': [query_ref], 'source_subject_refs': [subject_ref],
            'source_ref': source_ref, 'anchor': None,
            'measurements': measurements(reference_ref=ref(subject_ref),
                                         **{name: number(value) for name, value in row['measurements'].items()}),
            'dependencies': [query_ref, subject_ref],
            'operand_intervals': [
                {'role': 'query', 'subject_ref': query_ref, 'start': start, 'end': end, 'unit': query_unit,
                 'model_unit': model_unit},
                {'role': 'reference', 'subject_ref': subject_ref, 'start': subject_start, 'end': subject_end,
                 'unit': subject_unit, 'model_unit': model_unit}]}, origin='tool')['id'])
    return refs


async def pairwise_blast_comparison(ctx, *, program, query_ref, reference_ref, resource_id, executable_directory):
    """Compare the query with the reference by ``program`` on the local resource and keep the graded correspondence.
    ``ctx`` is the tool's ``UnitContext`` of an episode that declares the service ``job_access``."""
    store, access = ctx.store, ctx.services['job_access']
    sequences = {'query_sequence': (query_ref, *_sequence(store, query_ref)),
                 'subject_sequence': (reference_ref, *_sequence(store, reference_ref))}
    for (role, (_, molecule, _)), allowed in zip(sequences.items(), PROGRAM_MOLECULES[program]):
        if molecule not in allowed:
            return _outcome('invalid', 'pairwise_blast_molecules_not_comparable', category='arguments_or_reference',
                            detail={'program': program, 'operand': role, 'molecule': molecule})
    directory = Path(access.describe(resource_id)['workspace']) / job_handle(ctx.operation_key, resource_id, JOB_NAME)
    requested, inputs = _job(store, directory, program, sequences, executable_directory)
    checked_analysis_kind(PAIRWISE, requested)
    store.artifact(canonical(requested), 'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, requested['argv'], requested['environment'], wait=True,
                                          inputs=inputs, name=JOB_NAME)
    if ran['status'] != 'completed':
        refused = (ran['launch'] if ran['launch']['status'] != 'completed' else ran['fetch'])['failure']
        operational = refused['detail'].get('operational', {}) if isinstance(refused['detail'], dict) else {}
        return _outcome('failed', refused['code'], category='job', detail=refused['detail'],
                        retryable=operational.get('retryable', False))
    if ran['returncode'] != 0:
        return _outcome('failed', 'pairwise_blast_program_exit_nonzero', category='job',
                        detail={'returncode': ran['returncode'], 'stderr': ran['stderr'][-2000:]})
    (report_ref,) = [item['ref'] for item in ran['fetch']['results'] if item['name'] == REPORT]
    query, subject = sequences['query_sequence'][2], sequences['subject_sequence'][2]
    try:
        grading = _graded(store, report_ref, program, query, subject)
    except (ValueError, ContractError) as error:
        return _outcome('invalid', str(error), category='grading')
    sheet = grading['sheet']
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=report_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': report_ref, 'text_ref': None,
            'request_ref': None, 'version': sheet['input']['search']['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query_ref]}, origin='tool')
        search = store.table(SEARCHES).put({'source_ref': source['id'], 'query_ref': query_ref, 'profile': 'blast'})
        observations = _observations(store, grading, source['id'], program, sequences)
    refs = [source['id'], grading_ref, search['id'], *observations]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {**grading_features(grading, grading_ref), 'observation_refs': observations}, 'feedback': None}


__all__ = ['PROGRAM_MOLECULES', 'pairwise_blast_comparison']
