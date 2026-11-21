"""The task: run the plan of the commission, one execution through the local wrapper per unit.

A plan step is the arguments of one call of ``execute_on_local_resource``: ``{'resource_id', 'command',
'environment', 'wait', 'inputs', 'cut'}``. ``cut`` is true when the test wants the unit cut after the execution
(the switch service says whether it is still wanted). The task asks no model. It always offers a unit and never
ends the Episode: after the plan it offers ``idle``; the yield controller stops the Episode at the plan's last
step."""
from episode_runtime import Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource

CHILD_SLOTS = {}
SERVICES = ('job_access', 'switch')


def idle(arguments, ctx):
    return {'idle': True}


async def execute(arguments, ctx):
    outcome = await execute_on_local_resource(ctx, arguments['resource_id'], arguments['command'],
                                              arguments['environment'], wait=arguments['wait'],
                                              inputs=arguments['inputs'])
    if arguments['cut'] and ctx.services['switch'].fail:
        raise RuntimeError('cut after the execution of ' + ctx.operation_key)
    return outcome


TOOLS = {'idle': idle, 'execute': execute}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    return ToolCall('execute', summary['plan'][step])


def action(response, summary, records, ctx):
    raise Rejected('this episode asks no model')
