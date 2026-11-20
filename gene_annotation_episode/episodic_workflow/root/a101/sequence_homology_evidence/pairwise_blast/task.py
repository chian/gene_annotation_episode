"""The task: a pairwise BLAST of one query sequence against one subject sequence, from the launch to the graded
correspondence. Nothing here is a decision of a model: ``decide`` returns the next unit from the state of the
episode, so the model is never asked (``action`` exists because the system requires the member; it is never
reached).

The units, in the order the state calls for them:

- ``launch_job``: builds the job from the commission and launches it. The two FASTA artifacts are made from the two
  subject records the commission names (a record the episode does not hold, or two molecules the program cannot
  compare, fails the run with its error), the library's pairwise job is built, its kind is derived from the job and
  checked against the declared kind, and the job is launched through the local-resource inspection point with the two
  files staged into the job's own directory. The command names them by their path there (``<workspace>/<handle>``,
  the handle from the public ``job_handle``). The job record is kept in custody as an artifact. The launch returns at
  the handoff and the job runs on without the episode.
- ``wait_for_end``: the system's defined wait on the job's end event (the ``native_events`` service, the one event of
  the job's own target, no reconsideration time). It reports readiness only and earns nothing.
- ``fetch_and_grade``: one coupled step. It fetches only the one report the job declares through the job service and
  then, in the same unit, grades it into the pairwise sheet of the job's own two operands and keeps the grading with
  its source and its search row, all through custody. A report of other sequences is refused (an invalid outcome,
  nothing kept).

A failed or refused unit is the outcome of that unit and earns nothing; the next decision repeats the step the state
calls for. Only the yield controller ends the episode.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``) and ``blast_executable_directory``,
the directory that holds the BLAST programs."""
import hashlib
from pathlib import Path

from episode_runtime import ToolCall
from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    checked_analysis_kind)
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
    SHEET_SCHEMA)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'native_events')
JOB_NAME = 'job'
NUCLEOTIDE = ('dna', 'rna')
# The molecules each program compares: the query, then the subject.
PROGRAM_MOLECULES = {'blastp': (('protein',), ('protein',)), 'blastn': (NUCLEOTIDE, NUCLEOTIDE),
                     'blastx': (NUCLEOTIDE, ('protein',)), 'tblastn': (('protein',), NUCLEOTIDE),
                     'tblastx': (NUCLEOTIDE, NUCLEOTIDE)}


def _sequence(store, ref):
    """The molecule and the residues (upper case) of a subject record the episode holds."""
    record = store.get(ref)
    return record.get('molecule'), store.get_artifact(record['sequence_ref']).decode('ascii').upper()


def _invalid(code):
    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': code}}


# -- the units ---------------------------------------------------------------------------------------------------
async def launch_job(arguments, ctx):
    """Build the pairwise job from the two records, check its kind, and launch it. Returns at handoff."""
    store, access, program = ctx.store, ctx.services['job_access'], arguments['program']
    sequences = {role: (ref, *_sequence(store, ref)) for role, ref in (
        ('query_sequence', arguments['query_ref']), ('subject_sequence', arguments['subject_ref']))}
    for (role, (_, molecule, _)), allowed in zip(sequences.items(), PROGRAM_MOLECULES[program]):
        if molecule not in allowed:
            raise ValueError('pairwise_blast_molecules_not_comparable:' + program + ':' + role + ':' + repr(molecule))
    resource_id = arguments['resource_id']
    directory = Path(access.describe(resource_id)['workspace']) / job_handle(ctx.operation_key, resource_id, JOB_NAME)
    operands, inputs = [], {}
    for role, (_, _, residues) in sequences.items():
        name, data = role + '.fasta', ('>' + role + '\n' + residues + '\n').encode()
        artifact = store.artifact(data, 'text/x-fasta')
        operands.append({'role': role, 'path': str(directory / name), 'format': 'fasta',
                         'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data),
                         'artifact_ref': artifact})
        inputs[name] = artifact
    executable = (Path(arguments['executable_directory']) / program).resolve()
    requested = requested_job_from_pairwise({
        'version': 'blast_pairwise_job_v1', 'program': program,
        'software': {'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                     'engine_version': None},
        'environment': {}, 'operands': operands,
        'operand_bindings': [{'operand_role': role, 'record_ordinal': 0, 'native_name': None,
                              'native_accession': None, 'subject_ref': ref, 'reference_ref': None}
                             for role, (ref, _, _) in sequences.items()],
        'options': [], 'report': {'format': 'json15', 'relative_path': 'report.json'}, 'metadata': {}})
    checked_analysis_kind(arguments['analysis_kind'], requested)       # the declared kind and the job's own agree
    job_ref = store.artifact(canonical(requested), 'application/json')
    outcome = await execute_on_local_resource(ctx, resource_id, requested['argv'], requested['environment'],
                                              wait=False, inputs=inputs, name=JOB_NAME)
    return {**outcome, 'job_ref': job_ref} if outcome['status'] == 'completed' else outcome


async def wait_for_end(arguments, ctx):
    """Wait for the job's end event after the cursor last seen. The receipt of the event comes into custody."""
    outcome = await ctx.services['native_events'].wait(ctx, {
        'version': 'event_condition_v1', 'reconsider_at': None,
        'events': [{'handle': arguments['event_target'], 'event': 'state_changed',
                    'after_cursor': arguments['after_cursor']}]})
    if outcome['status'] != 'completed':
        return {'status': 'failed', 'failure': {'code': outcome['feedback']['code'],
                                                'detail': outcome['feedback']['detail']}}
    wake = outcome['result']
    return {'status': 'completed', 'woke_on': wake['reason'], 'observed_at': wake['observed_at'],
            'event_cursor': max([arguments['after_cursor'], *(event['cursor'] for event in wake['events'])]),
            'receipt_refs': outcome['record_refs']}


def _grade(ctx, report_ref, arguments):
    """Grade the fetched native JSON report of the job's one query against its one subject into the pairwise sheet
    and keep the grading. Which sequences the report must be about is the job's own declaration: each operand is a
    FASTA artifact this episode holds (its digest is the job's), and the sheet's query and subject lengths must be
    those of the two records. A report of other sequences, or of another sheet type, is refused and nothing is kept.
    The result is retained as a ``native.blast.pairwise`` source over the fetched artifact with the full grading
    artifact beside it, and the search enters the A101 sheet's tool profile from the identity of its producer."""
    store, job = ctx.store, arguments['job']
    try:
        if not store.holds(report_ref):
            raise ValueError('blast_pairwise_result_not_held')
        for operand in job['operands']:
            if operand['artifact_ref'] is None or not store.holds(operand['artifact_ref']):
                raise ValueError('blast_pairwise_operand_not_held:' + operand['role'])
            if hashlib.sha256(store.get_artifact(operand['artifact_ref'])).hexdigest() != operand['sha256']:
                raise ValueError('blast_pairwise_operand_digest_conflict:' + operand['role'])
        _, query = _sequence(store, arguments['query_ref'])
        _, subject = _sequence(store, arguments['subject_ref'])
        grading = grade_blast_result(store.get_artifact(report_ref), mode='pairwise', resource='local',
                                     output_format='json2', request={'program': job['program'],
                                                                     'query_length': len(query)},
                                     _retain_correspondence=True)
        sheet = grading['sheet']
        if sheet['schema'] != SHEET_SCHEMA:
            raise ValueError('blast_pairwise_result_type_conflict')
        if sheet['query']['length'] != len(query) or sheet['reference']['length'] != len(subject):
            raise ValueError('blast_pairwise_result_operand_conflict')
    except (ValueError, ContractError) as error:
        return _invalid(str(error))
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider='native.blast.pairwise', native_artifact_ref=report_ref,
                                          grading=grading)
        source = store.put('source', {
            'provider': 'native.blast.pairwise', 'accession': None, 'uri': None, 'artifact_ref': report_ref,
            'text_ref': None, 'request_ref': None, 'version': sheet['input']['search']['version'],
            'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [arguments['query_ref']]}, origin='tool')
        search = store.table(SEARCHES).put({'source_ref': source['id'], 'query_ref': arguments['query_ref'],
                                            'profile': 'blast'})
    return {'status': 'completed', 'record_refs': [source['id'], grading_ref, search['id']],
            'changed_record_refs': [source['id'], grading_ref, search['id']],
            'result': {'result_ref': source['id'], 'grading_artifact_ref': grading_ref, 'search_ref': search['id'],
                       'sheet_schema': sheet['schema']}, 'feedback': None}


def fetch_and_grade(arguments, ctx):
    """One coupled step: fetch the job's report, then grade it. A fetch the job service refuses (the job service
    refuses the results of a job that has not ended) is the failed outcome it returns; nothing is graded."""
    name = arguments['report_name']
    fetched = ctx.services['job_access'].fetch(ctx, arguments['handoff_ref'], names=[name])
    if fetched['status'] != 'completed':
        return fetched
    report = next((item['ref'] for item in fetched['results'] if item['name'] == name), None)
    if report is None:
        return _invalid('pairwise_blast_report_not_fetched')
    return {**_grade(ctx, report, arguments), 'closure_ref': fetched['closure_ref'], 'report_ref': report}


TOOLS = {'launch_job': launch_job, 'wait_for_end': wait_for_end, 'fetch_and_grade': fetch_and_grade}


# -- the decision: by code, from the state ------------------------------------------------------------------------
def decide(summary, feedback, ctx):
    """The next unit, from the state of the episode. No model is asked: nothing here is a choice."""
    assignment = summary['assignment']
    if summary['handoff_ref'] is None:
        return ToolCall('launch_job', {
            'resource_id': assignment['resource_id'], 'program': assignment['program'],
            'analysis_kind': assignment['analysis_kind'], 'query_ref': assignment['query_ref'],
            'subject_ref': assignment['subject_ref'],
            'executable_directory': ctx.settings['blast_executable_directory']})
    if not summary['ended']:
        return ToolCall('wait_for_end', {'event_target': summary['event_target'],
                                         'after_cursor': summary['event_cursor']})
    return ToolCall('fetch_and_grade', {
        'handoff_ref': summary['handoff_ref'], 'report_name': summary['report_name'], 'job': summary['job_spec'],
        'query_ref': assignment['query_ref'], 'subject_ref': assignment['subject_ref']})


def action(response, summary, records, ctx):
    raise TypeError('pairwise_blast_asks_no_model_so_no_response_is_ever_acted_on')
