"""The task: launch the commissioned preparation job on the assigned local resource, and end at the handoff.

Nothing here is a model choice. ``decide`` is made by code: the one unit is ``launch_preparation_job``, which builds
the job from the commission (``compile_preparation``: the commission's controlled fields, the staged FASTA read
through custody, the resource's software and Python from this episode's settings, and the resource's scratch bound
from the job service) and launches it through the library's one inspection point for local execution. A commission
that does not compile raises its error; a launch the resource refuses is the unit's returned ``failed`` outcome.
Once a handoff is held the only unit offered is ``handoff_read``, which earns nothing: a second launch would start
a second job.

Settings this episode reads (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``) and
``resources``: ``{resource_id: {'python': <absolute interpreter>, 'software': {program: {'executable', 'sha256',
'engine_version'}}}}``, the run's configuration of the resource's programs (a commission carries no path)."""
from episode_runtime import ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    compile_preparation)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence.blast_preparation_run import (
    launch_preparation)

CHILD_SLOTS = {}
SERVICES = ('job_access',)


async def launch_preparation_job(arguments, ctx):
    """Build and launch the commissioned job; returns the job service's launch outcome."""
    resource_id = arguments['resource_id']
    access = ctx.services['job_access']
    described = access.describe(resource_id)
    if described['kind'] != 'local':
        raise ValueError('blast_preparation_launch_local_requires_a_local_resource')
    configured = ctx.settings['resources'][resource_id]
    compiled = compile_preparation(arguments['fields'], input_bytes=ctx.store.get_artifact(arguments['fields']['input_ref']),
                                   software=configured['software'], python=configured['python'],
                                   scratch_bytes=described['policy']['scratch_bytes'])
    return await launch_preparation(ctx, resource_id, compiled)


def handoff_read(arguments, ctx):
    """The handoff rows this Episode already holds, read again. It starts nothing and earns nothing."""
    return {'status': 'completed', 'handoff_refs': list(arguments['handoff_refs'])}


TOOLS = {'launch_preparation_job': launch_preparation_job, 'handoff_read': handoff_read}


def decide(summary, feedback, ctx):
    if summary['handoff_refs']:
        return ToolCall('handoff_read', {'handoff_refs': summary['handoff_refs']})
    return ToolCall('launch_preparation_job', {'fields': summary['fields'], 'resource_id': summary['resource_id']})


def action(response, summary, records, ctx):
    """``decide`` returns the unit itself, so no model response ever reaches this function."""
    raise ValueError('blast_preparation_launch_local_decides_by_code')
