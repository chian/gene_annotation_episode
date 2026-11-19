"""The task: call the commissioned library function of each plan step through ``ctx.store``.

A plan step is ``{'function': 'dotted.module:name', 'keywords': {...}}``; the function is a test-side wrapper that
receives the unit's context and calls the library function under test with ``ctx.store``. The task always offers a
unit; when the plan is done it offers ``idle``. The Episode ends when its yield controller stops it."""
from importlib import import_module

from episode_runtime import Rejected, ToolCall

CHILD_SLOTS = {}
SERVICES = ()


def call(arguments, ctx):
    module, name = arguments['function'].split(':')
    return getattr(import_module(module), name)(ctx, **arguments['keywords'])


def idle(arguments, ctx):
    return {'idle': True}


TOOLS = {'call': call, 'idle': idle}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    return ToolCall('call', summary['plan'][step])


def action(response, summary, records, ctx):
    raise Rejected({'status': 'invalid', 'category': 'no_model_decision', 'detail': 'this task decides by plan'})
