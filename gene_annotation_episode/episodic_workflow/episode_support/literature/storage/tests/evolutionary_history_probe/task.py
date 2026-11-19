"""The task: run the plan's library calls, one per unit.

Each call builds the named repository on ``ctx.store`` and calls the named method with the plan's arguments, the
way a tool of an episode calls a support-library function. The task always offers a unit; the Episode ends when its
yield controller stops it."""
from dataclasses import dataclass
from importlib import import_module

from episode_runtime import ToolCall, Rejected

CHILD_SLOTS = {}
SERVICES = ()

@dataclass(frozen=True)
class PopulationContext:
    """What a population call is given besides its arguments: the scope, the assignment and the role."""
    scope: dict
    assignment: dict
    role: str

def call(arguments, ctx):
    """Run ``method`` of ``repository`` (``module:Class``) on the Episode's scoped store."""
    module, name = arguments['repository'].split(':')
    repository = getattr(import_module(module), name)(ctx.store)
    context = PopulationContext(arguments['scope'], arguments.get('assignment', {}), arguments.get('role', 'literature_page'))
    return getattr(repository, arguments['method'])(context, *arguments['call'], ctx.operation_key, **arguments['keywords'])

def read(arguments, ctx):
    """Run a read-only ``method`` of ``repository`` that takes plain arguments (no context)."""
    module, name = arguments['repository'].split(':')
    repository = getattr(import_module(module), name)(ctx.store)
    return getattr(repository, arguments['method'])(*arguments['call'], **arguments['keywords'])

def function(arguments, ctx):
    """Run a module-level library function that takes the scoped store first."""
    function = getattr(import_module(arguments['module']), arguments['name'])
    return function(ctx.store, *arguments['call'], **arguments['keywords'])


TOOLS = {'call': call, 'read': read, 'function': function}

def resolve(value, outcomes):
    """A plan argument ``{'from_step': i, 'path': [...]}`` is what step ``i`` returned, followed along ``path``."""
    if isinstance(value, dict) and set(value) == {'from_step', 'path'}:
        found = outcomes[value['from_step']]
        for key in value['path']:
            found = found[key]
        return found
    if isinstance(value, dict):
        return {key: resolve(item, outcomes) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, outcomes) for item in value]
    return value

def decide(summary, feedback, ctx):
    step = summary['plan'][len(summary['outcomes'])]
    return ToolCall(step['tool'], resolve(step['arguments'], summary['outcomes']))

def action(response, summary, records, ctx):
    raise Rejected({'status': 'invalid', 'category': 'no_model_decision', 'detail': 'this task decides by its plan'})
