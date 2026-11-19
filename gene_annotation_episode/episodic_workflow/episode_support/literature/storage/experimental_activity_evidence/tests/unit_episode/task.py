"""The task: run the functions of the test, one per unit, through the service that holds them. When none is left
the unit is ``idle``."""
from episode_runtime import ToolCall

CHILD_SLOTS = {}
SERVICES = ('functions',)


def idle(arguments, ctx):
    """Nothing is left to run: this unit does nothing."""
    return {'idle': True}


def run(arguments, ctx):
    """Run the next function of the test with the scoped store and the unit context; what it returned or raised
    stays with the service for the test to read."""
    ctx.services['functions'].run_next(ctx)
    return {'ran': arguments['step']}


TOOLS = {'idle': idle, 'run': run}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= summary['steps_planned']:
        return ToolCall('idle', {})
    return ToolCall('run', {'step': step})


def action(response, summary, records, ctx):
    raise ValueError('this episode asks no model')
