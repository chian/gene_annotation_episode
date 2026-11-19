"""The task: run the commissioned scenarios one per unit; a scenario that fails an assertion fails the run."""
from episode_runtime import Rejected, ToolCall

from ..library_scenarios import SCENARIOS

CHILD_SLOTS = {}
SERVICES = ()


def scenario(arguments, ctx):
    """Run one named scenario on the scoped store of this unit."""
    return SCENARIOS[arguments['name']](ctx, **arguments.get('keywords', {}))


def idle(arguments, ctx):
    return {'idle': True}


TOOLS = {'scenario': scenario, 'idle': idle}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    return ToolCall('scenario', summary['plan'][step])


def action(response, summary, records, ctx):
    raise Rejected({"status": "invalid", "category": "no_model_decision", "detail": "this task decides by its plan"})
