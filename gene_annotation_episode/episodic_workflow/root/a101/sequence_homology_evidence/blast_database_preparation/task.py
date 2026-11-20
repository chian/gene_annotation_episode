"""The task: establish the prepared-data record of one commissioned build or masking. Every decision is made by
code; the one choice a model could make here (which program, which resource) is the commissioner's, not this
episode's.

Order of the units, decided from what the episode holds:

1. No handoff is held: commission ``launch_local`` (it builds the job from the controlled commission, launches it
   on the local resource and returns its handoff row and the artifact of the plan the job runs). A launch the
   resource refused is the child's report with no handoff; the next unit is a launch again.
2. A handoff is held and no prepared-data record is: commission ``results`` (it asks the job, waits while it runs,
   fetches only its receipt, checks the product against the plan and writes the record, usable or not). A job that
   had not ended comes back as not established and the next unit is ``results`` again.
3. A prepared-data record is held: only ``state_read`` is offered, which earns nothing; the yield controller then
   ends the episode.

The resource must be a local one: a cluster resource is refused here with its error. The cluster launch and the
monitor of a long job are added to this task when their shared design is written; nothing here pretends to handle
them. The task always offers a unit and never ends the episode: only the yield controller does."""
from episode_runtime import ChildCall, ToolCall

PREFIX = 'sequence_homology_evidence/blast_database_preparation/'
CHILD_SLOTS = {'launch_local': PREFIX + 'launch_local', 'results': PREFIX + 'results'}
SERVICES = ('job_access',)


def state_read(arguments, ctx):
    """The prepared-data and handoff references this Episode holds, read again. It starts nothing, earns nothing."""
    return {'status': 'completed', 'prepared_refs': list(arguments['prepared_refs']),
            'handoff_refs': list(arguments['handoff_refs'])}


TOOLS = {'state_read': state_read}


def decide(summary, feedback, ctx):
    if ctx.services['job_access'].read('describe', summary['resource_id'])['kind'] != 'local':
        raise ValueError('blast_database_preparation_resource_must_be_local')
    if summary['prepared_refs']:
        return ToolCall('state_read', {'prepared_refs': summary['prepared_refs'],
                                       'handoff_refs': summary['handoff_refs']})
    if not summary['handoff_refs']:
        return ChildCall('launch_local', {})
    return ChildCall('results', {})


def action(response, summary, records, ctx):
    """``decide`` returns the unit itself, so no model response ever reaches this function."""
    raise ValueError('blast_database_preparation_decides_by_code')
