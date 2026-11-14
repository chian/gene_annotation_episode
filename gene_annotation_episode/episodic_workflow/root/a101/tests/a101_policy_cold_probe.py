"""Actual defining-owner cold cycles; no application objects are constructed."""
import importlib
import inspect
import json
from pathlib import Path
import sys

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a101'
ORDERS = ('runtime', 'action_admission', 'library.child_report_forms',
          'library.unbound_child_action_options', 'library.source_report_records',
          'scientific_process.completion_report')
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
raw_tree, raw_dependencies, first, output = sys.argv[1:]
tree, dependencies = Path(raw_tree).resolve(), Path(raw_dependencies).resolve()
assert tree.is_dir() and dependencies.is_dir() and first in ORDERS
assert not (dependencies / 'gene_annotation_episode').exists()
assert not (dependencies / 'method_loop').exists()
sys.path[:0] = [str(tree), str(dependencies)]
importlib.import_module(PACKAGE + '.' + first)
runtime = importlib.import_module(PACKAGE + '.runtime')
owners = {}
for name, functions in {
    'action_admission': ('restricted_common_action', 'restrict_credit_child_roles', 'restrict_root_tool_actions',
        'validate_annotation_child_choice', 'validate_root_tool_selection', 'root_tool_catalog', 'root_tool_rejection', 'root_child_return_sources'),
    'library.child_report_forms': ('annotation_report_example', 'interpretation_report_example', 'child_scope_schema', 'scientific_child_request_schema'),
    'library.unbound_child_action_options': ('append_unbound_child_options', '_default_scientific_child_roles'),
    'library.source_report_records': ('facts',),
    'scientific_process.completion_report': ('enrich_completion_snapshot',),
}.items():
    module = importlib.import_module(PACKAGE + '.' + name)
    for symbol in functions:
        function = getattr(module, symbol)
        assert function.__globals__ is vars(runtime), (name, symbol)
        assert Path(inspect.getsourcefile(function)).resolve() == Path(module.__file__).resolve()
    owners[name] = list(functions)
for method, module in (('root_child_return_sources', 'action_admission'),
                       ('_default_scientific_child_roles', 'library.unbound_child_action_options'),
                       ('facts', 'library.source_report_records')):
    function = getattr(runtime.Workflow, method)
    assert function is getattr(importlib.import_module(PACKAGE + '.' + module), method)
    assert (function.__module__, function.__qualname__) == (runtime.__name__, 'Workflow.' + method)
original = runtime._a101_annotation_original_source_type
assert runtime.DecisionSource is original
for name in ('episode', 'annotation_improvement.episode'):
    module = importlib.import_module(PACKAGE + '.' + name)
    cls = module.AnnotationTask if name == 'episode' else module.ImprovementTask
    assert cls.__mro__ == (cls, original, object)
origins = {name: str(Path(module.__file__).resolve()) for name, module in tuple(sys.modules.items())
    if getattr(module, '__file__', None) and (name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.')
        or name == 'method_loop' or name.startswith('method_loop.'))}
Path(output).write_text(json.dumps({'first': first, 'passed': True, 'tree': str(tree),
    'isolated': bool(sys.flags.isolated), 'no_site': bool(sys.flags.no_site), 'owners': owners,
    'origins': origins, 'application_objects_constructed': False, 'scientific_or_native_execution': False}, indent=2) + '\n')
