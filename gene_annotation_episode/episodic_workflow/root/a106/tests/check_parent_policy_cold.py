"""One isolated process: new A106 policy owners and their live namespaces only."""
import importlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import sys

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
first, output = sys.argv[1:]
allowed = ('runtime', 'library.parent_task_report_forms', 'action_admission',
    'library.unbound_child_action_options', 'scientific_process.completion_snapshot')
assert first in allowed
importlib.import_module(PACKAGE + '.' + first)
rt = importlib.import_module(PACKAGE + '.runtime')
functions = {}
for name, members in {
    'library.parent_task_report_forms': ('form_inputs', 'child_request_form'),
    'action_admission': ('parent_common_action_permission', 'filter_parent_task_credit_roles',
        'validate_parent_child_choice', 'filter_parent_tool_actions',
        'validate_parent_tool_selection', 'parent_tool_catalog', 'parent_tool_rejection'),
    'library.unbound_child_action_options': ('append_unbound_child_options', '_default_scientific_child_roles'),
}.items():
    owner = importlib.import_module(PACKAGE + '.' + name)
    for member in members:
        fn = getattr(owner, member)
        assert fn.__globals__ is vars(rt)
        assert Path(fn.__code__.co_filename).resolve() == Path(owner.__file__).resolve()
        functions[name + '.' + member] = {'module': fn.__module__, 'qualname': fn.__qualname__,
            'defining_file': str(Path(fn.__code__.co_filename).resolve())}
assert rt.Workflow._default_scientific_child_roles is importlib.import_module(
    PACKAGE + '.library.unbound_child_action_options')._default_scientific_child_roles
assert rt.Workflow._default_scientific_child_roles.__qualname__ == 'Workflow._default_scientific_child_roles'
assert rt.Workflow._default_scientific_child_roles.__module__ == rt.__name__
for name in ('report', 'annotation_improvement.report'):
    assert importlib.import_module(PACKAGE + '.' + name).facts.__globals__ is vars(rt)
leaf = importlib.import_module(PACKAGE + '.scientific_process.completion_snapshot')
assert leaf.completion_snapshot.__globals__ is vars(leaf)
assert leaf.completion_snapshot.__closure__ is None
for forbidden in ('scientific_process.to_parent', 'scientific_process.scientific_contracts'):
    assert PACKAGE + '.' + forbidden not in sys.modules
snapshot = {}
leaf.completion_snapshot(SimpleNamespace(journal=SimpleNamespace(row=lambda *_: {'initial_credit': 0.0}),
    source_controller_credit=lambda _: None, services=SimpleNamespace(scientific_parent_invocation=lambda _: None)),
    SimpleNamespace(episode_id='supplied_boundary'), 'supplied_context', snapshot,
    {'credit': 0.0, 'episode_yield': None})
assert snapshot == {'initial_credit': 0.0, 'credit': 0.0, 'controller_credit': None,
    'episode_yield': None, 'parent_invocation_ref': None}
for forbidden in ('scientific_process.to_parent', 'scientific_process.scientific_contracts'):
    assert PACKAGE + '.' + forbidden not in sys.modules
origins = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
    if name.startswith(PACKAGE) and getattr(module, '__file__', None)}
Path(output).write_text(json.dumps({'first': first, 'policy_live_runtime_globals': True,
    'functions': functions, 'pure_scientific_leaf': True, 'original_report_consumer_globals': True,
    'unrelated_scientific_provider_modules_absent': True, 'origins': origins,
    'scientific_or_native_execution': False}, indent=2, sort_keys=True) + '\n')
