"""Run functions of a test inside units of a real Episode, so that a library function is handed the custody-scoped
store of the real runner (real Store, real journal, real model provider object, real work-table rows).

``run_in_unit(directory, f1, f2, ...)`` runs ``f(store, ctx)`` for each function in its own tool unit of one
Episode and returns their values; what a function raised is raised again in the test. ``in_unit`` makes a test
function ``test(store, ctx, ...)`` run that way."""
import asyncio
import functools
import inspect

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from .unit_episode.episode import UnitEpisode

SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}


class Functions:
    """The service of the Episode: the functions of the test, run one per unit."""

    def __init__(self, functions):
        self.queue = list(functions)
        self.values = []
        self.errors = []

    def run_next(self, ctx):
        function = self.queue.pop(0)
        try:
            self.values.append(function(ctx.store, ctx))
        except BaseException as error:
            self.errors.append(error)
            self.values.append(None)


def run_in_unit(directory, *functions):
    store = Store(directory / 'store')
    try:
        service = Functions(functions)
        collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'calls', directory),
                         'continuation': {'unit_episode': SETTINGS}, 'services': {'functions': lambda: service}}
        linked = link(BindingRegistry([UnitEpisode()]), 'unit_episode',
                      {'assignment': {'held_refs': []}, 'message': {'steps': len(functions)}, 'selection': []},
                      run_id='unit_run', journal=RunJournal(directory / 'journal.sqlite3'),
                      collaborators=collaborators)
        asyncio.run(linked.run())
        if service.errors:
            raise service.errors[0]
        return service.values
    finally:
        store.close()


def in_unit(test):
    """The test ``test(store, ctx, *rest)`` as a pytest function ``(tmp_path, *rest)`` that runs in one unit."""
    signature = inspect.signature(test)
    parameters = list(signature.parameters.values())

    @functools.wraps(test)
    def wrapper(tmp_path, **arguments):
        return run_in_unit(tmp_path, lambda store, ctx: test(store, ctx, **arguments))[0]
    wrapper.__signature__ = signature.replace(parameters=[
        inspect.Parameter('tmp_path', inspect.Parameter.POSITIONAL_OR_KEYWORD), *parameters[2:]])
    return wrapper


def held(store, kind):
    """The held Store records of ``kind`` (``list`` of the scoped store, without the problem reference)."""
    refs = [ref for ref in store.refs() if not ref.startswith(('row_', 'problem_'))]
    return [row for row in map(store.get, refs) if row['record_type'] == kind]
