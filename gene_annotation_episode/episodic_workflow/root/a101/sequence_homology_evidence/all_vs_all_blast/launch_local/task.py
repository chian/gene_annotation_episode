"""The task: launch the assigned chunk of the all-vs-all search on the assigned local resource. The episode ends at
handoff.

Nothing here is a choice, so no model is asked: ``decide`` returns the one unit the state calls for. The unit,
``launch_chunk``, cuts the chunk from the set the commissioner passed in custody, builds the native job of that chunk
from the controlled values of the assignment (the contract writes every option token; the job's paths are inside its
own directory, where the set and the chunk are staged), checks that the declared analysis kind is the kind the job is,
keeps the job as a record, and starts it through the library's one local execution point. The job detaches and goes
on after the episode. A refused launch is the outcome of its unit and earns nothing; the next decision repeats the
launch, and only the yield controller ends the episode.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``) and ``blast_executable_directory``,
the directory that holds the BLAST programs."""
import hashlib
from pathlib import Path

from episode_runtime import ToolCall
from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_all_vs_all_chunk_job import (
    QUERY_NAME, SET_NAME, chunk_of, native_chunk_job)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_all_vs_all_job import (
    requested_job_from_native)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    checked_analysis_kind)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource

CHILD_SLOTS = {}
SERVICES = ('job_access',)
JOB_NAME = 'chunk'


def _build(store, arguments, directory):
    """The requested job of the chunk, the files to stage for it and the record of the job, from the set in custody."""
    set_ref = arguments['set_ref']
    set_text = store.get_artifact(set_ref).decode()
    count = arguments['chunk_count']
    chunk = chunk_of(set_text, arguments['chunk_index'], count)
    chunk_ref = set_ref if count == 1 else store.artifact(chunk['text'].encode(), 'text/x-fasta')
    executable = (Path(arguments['executable_directory']) / arguments['program']).resolve()
    parameters = {name: arguments[name] for name in ('evalue', 'max_target_seqs', 'max_hsps') if name in arguments}
    native = native_chunk_job(
        set_text, chunk, program=arguments['program'], parameters=parameters, chunk_index=arguments['chunk_index'],
        chunk_count=count, executable=executable, executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
        directory=directory, set_ref=set_ref, chunk_ref=chunk_ref)
    requested = requested_job_from_native(native)
    checked_analysis_kind(arguments['analysis_kind'], requested)       # the declared kind and the job's own agree
    return requested, {SET_NAME: set_ref, QUERY_NAME: chunk_ref}, store.artifact(canonical(requested),
                                                                                 'application/json')


async def launch_chunk(arguments, ctx):
    """Build the chunk's job and launch it. Returns at handoff, with the record of the job beside the handoff row."""
    resource_id = arguments['resource_id']
    access = ctx.services['job_access']
    directory = Path(access.describe(resource_id)['workspace']) / job_handle(ctx.operation_key, resource_id, JOB_NAME)
    requested, inputs, job_ref = _build(ctx.store, arguments, directory)
    outcome = await execute_on_local_resource(ctx, resource_id, requested['argv'], requested['environment'],
                                              wait=False, inputs=inputs, name=JOB_NAME)
    return {**outcome, 'job_ref': job_ref} if outcome['status'] == 'completed' else outcome


TOOLS = {'launch_chunk': launch_chunk}


def decide(summary, feedback, ctx):
    """The launch of the assigned chunk. No model is asked: nothing here is a choice."""
    assignment = summary['assignment']
    arguments = {name: assignment[name] for name in ('set_ref', 'program', 'evalue', 'max_target_seqs', 'chunk_index',
                                                     'chunk_count', 'resource_id', 'analysis_kind')}
    if 'max_hsps' in assignment:
        arguments['max_hsps'] = assignment['max_hsps']
    return ToolCall('launch_chunk', {**arguments, 'executable_directory': ctx.settings['blast_executable_directory']})


def action(response, summary, records, ctx):
    raise TypeError('all_vs_all_launch_local_asks_no_model_so_no_response_is_ever_acted_on')
