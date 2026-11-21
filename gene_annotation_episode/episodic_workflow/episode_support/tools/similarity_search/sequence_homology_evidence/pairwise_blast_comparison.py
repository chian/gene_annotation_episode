"""One pairwise BLAST comparison: the check of the request, and the comparison as one unit.

The episode's model fills out one request: ``program``, ``query_ref``, ``reference_ref``, ``resource_id``. Two
functions of this module do the rest, deterministically:

``check_pairwise_request`` examines the request against what the episode holds and the bound resources, before
anything runs. It returns the things to fix (one entry per problem: the field, a code and what to choose from); an
empty list means the request can run. The episode's ``action`` rejects a request with problems, so no unit is made
and the model corrects the request.

``pairwise_blast_comparison`` runs a request that passed the check, as one unit, in this order:

1. read the two sequences through custody and make the two FASTA files as artifacts;
2. build the pairwise job with the library's contract and check that the kind derived from the job is ``pairwise``
   (the tool is the declaration of the kind; a job of another kind raises);
3. run it on the local resource through the inspection point (``execute_on_local_resource`` with ``wait=True``:
   launch, wait for the end, fetch what the job left), with the two files staged in the job's own directory;
4. grade the one report the job declares into the pairwise sheet of the job's own two operands;
5. keep the grading through custody: the grading artifact, a ``native.blast.pairwise`` source over the fetched
   report (its operands are the query and the reference), the search row that enters the search into the A101
   sheet's tool profile, and one ``alignment`` observation for each reported alignment (the query's interval, the
   reference's interval and the measurements of the already graded cell), in the shape the registry's
   ``sequence.align`` gives its observation. The A101 native-correspondence projection reads the graded cell of
   each such observation from the grading artifact on its source.

Grading is not a choice of anyone: it follows the fetch in the same unit.

The outcome has the shape of every tool outcome of an episode (``status``, ``record_refs``, ``changed_record_refs``,
``result``, ``feedback``). ``completed``: ``record_refs`` are the source, the grading artifact, the search row and
the observations, and ``result`` holds the controlled features code read from the sheet with the references of the
observations. A request that passed the check needs no second call: what can still go wrong is a fault of the
environment (the resource refused the job, the program ended with a nonzero exit code, the report is not of the two
operands). That is a ``failed`` outcome with its code and ``retryable`` false; it is reported once and is not
something the model repairs by calling again."""
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
    record_grading_product, retain_tool_grading)
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


def check_pairwise_request(request, *, sequences, scope_subjects, resources, made):
    """The things to fix in a pairwise request, before anything runs; an empty list means it can run.

    ``request`` holds ``program`` (one of ``PROGRAM_MOLECULES``), ``query_ref``, ``reference_ref`` (each a key of
    ``sequences``) and ``resource_id`` (a key of ``resources``); the caller's schema has already bound each to those
    sets. ``sequences`` is ``{record: molecule}`` of the sequence records the episode holds, ``scope_subjects`` the
    subjects of its scope, ``resources`` ``{resource id: kind}`` of the bound resources, and ``made``
    ``{(query, reference, program): 'completed' | 'failed'}`` of the comparisons the episode already holds or already
    saw fail. The conditions, each one problem with the field it concerns:

    1. the query is a subject of the episode's scope (the comparison is about the scope's own sequence);
    2. the reference is another record than the query;
    3. the program compares a query of the query's molecule with a reference of the reference's molecule;
    4. the resource is a local resource;
    5. the same comparison (query, reference, program) is not already held;
    6. the same comparison has not already failed (a failure after a passed check is a fault of the environment and
       cannot be repaired by the same call)."""
    query, reference, program = request['query_ref'], request['reference_ref'], request['program']
    problems = []
    if query not in scope_subjects:
        problems.append({'field': 'query_ref', 'code': 'query_is_not_a_sequence_of_the_scope',
                         'choose_from': [ref for ref in scope_subjects if ref in sequences]})
    if reference == query:
        problems.append({'field': 'reference_ref', 'code': 'reference_is_the_query',
                         'choose_from': [ref for ref in sequences if ref != query]})
    queries, references = PROGRAM_MOLECULES[program]
    if sequences[query] not in queries or sequences[reference] not in references:
        problems.append({'field': 'program', 'code': 'program_does_not_compare_these_molecules',
                         'query_molecule': sequences[query], 'reference_molecule': sequences[reference],
                         'choose_from': [name for name, (takes, against) in PROGRAM_MOLECULES.items()
                                         if sequences[query] in takes and sequences[reference] in against]})
    if resources[request['resource_id']] != 'local':
        problems.append({'field': 'resource_id', 'code': 'resource_is_not_local',
                         'choose_from': [name for name, kind in resources.items() if kind == 'local']})
    if (query, reference, program) in made:
        problems.append({'field': 'reference_ref', 'code': {
            'completed': 'comparison_already_held', 'failed': 'comparison_already_failed_and_cannot_be_retried'}[
                made[query, reference, program]]})
    return problems


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
    or of sequences of other lengths raises ``ValueError``. A report of no alignment has no reference on its sheet
    (status ``no_reported_alignment``): that is a graded result, not an error."""
    grading = grade_blast_result(store.get_artifact(report_ref), mode='pairwise', resource='local',
                                 output_format='json2', request={'program': program, 'query_length': len(query)},
                                 _retain_correspondence=True)
    sheet = grading['sheet']
    if sheet['schema'] != SHEET_SCHEMA:
        raise ValueError('blast_pairwise_result_type_conflict')
    reference = sheet['reference']
    if sheet['query']['length'] != len(query) or (reference is not None and reference['length'] != len(subject)):
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
    directory = Path(access.describe(resource_id)['workspace']) / job_handle(ctx.operation_key, resource_id, JOB_NAME)
    requested, inputs = _job(store, directory, program, sequences, executable_directory)
    checked_analysis_kind(PAIRWISE, requested)
    store.artifact(canonical(requested), 'application/json')
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
        grading = _graded(store, report_ref, program, query, subject)
    except (ValueError, ContractError) as error:
        return _outcome('failed', str(error), category='grading')
    sheet = grading['sheet']
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=report_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': report_ref, 'text_ref': None,
            'request_ref': None, 'version': sheet['input']['search']['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [query_ref, reference_ref]}, origin='tool')
        search = store.table(SEARCHES).put({'source_ref': source['id'], 'query_ref': query_ref, 'profile': 'blast'})
        observations = _observations(store, grading, source['id'], program, sequences)
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[report_ref])
    refs = [source['id'], grading_ref, search['id'], grading_product['id'], *observations]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {**grading_features(grading, grading_ref), 'observation_refs': observations}, 'feedback': None}


__all__ = ['PROGRAM_MOLECULES', 'PROVIDER', 'check_pairwise_request', 'pairwise_blast_comparison']
