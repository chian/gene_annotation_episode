"""Four fresh imports for the two incoming defining owners; no constructors."""
import importlib
import inspect
import json
from pathlib import Path
import sys

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a101'
ORDERS = ('runtime', 'from_parent', 'annotation_improvement.from_parent', 'annotation_improvement.task')
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
raw_tree, raw_dependencies, first, output = sys.argv[1:]
tree, dependencies = Path(raw_tree).resolve(), Path(raw_dependencies).resolve()
assert tree.is_dir() and dependencies.is_dir() and first in ORDERS
assert not (dependencies / 'gene_annotation_episode').exists()
assert not (dependencies / 'method_loop').exists()
sys.path[:0] = [str(tree), str(dependencies)]
importlib.import_module(PACKAGE + '.' + first)
runtime = importlib.import_module(PACKAGE + '.runtime')
annotation = importlib.import_module(PACKAGE + '.episode').AnnotationTask
improvement = importlib.import_module(PACKAGE + '.annotation_improvement.task').ImprovementTask
root_owner = importlib.import_module(PACKAGE + '.from_parent')
improvement_owner = importlib.import_module(PACKAGE + '.annotation_improvement.from_parent')
state_owner = importlib.import_module(PACKAGE + '.library.decision_source_state')
original = runtime._a101_annotation_original_source_type
assert runtime.DecisionSource is original
assert annotation.__mro__ == (annotation, original, object)
assert improvement.__mro__ == (improvement, original, object)
for cls, owner in ((original, root_owner), (annotation, root_owner), (improvement, improvement_owner)):
    assert inspect.getattr_static(cls, '__init__') is owner.__init__
    assert owner.__init__.__globals__ is vars(runtime)
    assert Path(inspect.getsourcefile(owner.__init__)).resolve() == Path(owner.__file__).resolve()
assert root_owner.__init__.__module__ == runtime.__name__
assert root_owner.__init__.__qualname__ == 'DecisionSource.__init__'
assert '__init__' not in vars(state_owner)
for name in ('bind_execution_context', 'suspension_changed', 'restore_checkpoint', 'restore', 'record_effect', 'checkpoint'):
    assert inspect.getattr_static(original, name) is getattr(state_owner, name)
    assert getattr(state_owner, name).__globals__ is vars(runtime)
retired = tree.joinpath(*PACKAGE.split('.'), 'annotation_improvement', 'task_state.py')
assert not retired.exists()
assert PACKAGE + '.annotation_improvement.task_state' not in sys.modules
origins = {name: str(Path(module.__file__).resolve()) for name, module in tuple(sys.modules.items())
           if getattr(module, '__file__', None) and (name == 'gene_annotation_episode'
               or name.startswith('gene_annotation_episode.') or name == 'method_loop'
               or name.startswith('method_loop.'))}
Path(output).write_text(json.dumps({'first': first, 'passed': True, 'tree': str(tree),
    'isolated': bool(sys.flags.isolated), 'no_site': bool(sys.flags.no_site),
    'public_constructor_identity_and_metadata': True, 'live_runtime_globals': True,
    'state_definitions_retained': True, 'retired_module_absent': True,
    'origins': origins, 'application_objects_constructed': False,
    'scientific_or_native_execution': False}, indent=2) + '\n')
