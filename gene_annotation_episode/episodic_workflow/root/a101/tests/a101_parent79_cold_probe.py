"""Cold defining-owner imports on the exact A101 parent79 control snapshot."""
import importlib
import inspect
import json
from pathlib import Path
import sys

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a101'
ORDERS = ('runtime', 'annotation_improvement.episode', 'annotation_improvement.task',
          'annotation_improvement.from_parent', 'annotation_improvement.task_instructions',
          'annotation_improvement.to_parent', 'annotation_improvement.yield_estimator',
          'annotation_improvement.from_child_annotation_improvement',
          'scientific_process.incoming_message_owners',
          'scientific_process.from_child_execution_job_submission')
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
raw_tree, raw_dependencies, first, output = sys.argv[1:]
tree, dependencies = Path(raw_tree).resolve(), Path(raw_dependencies).resolve()
assert tree.is_dir() and dependencies.is_dir()
assert not (dependencies / 'gene_annotation_episode').exists()
assert not (dependencies / 'method_loop').exists()
sys.path[:0] = [str(tree), str(dependencies)]
assert first in ORDERS
importlib.import_module(PACKAGE + '.' + first)
runtime = importlib.import_module(PACKAGE + '.runtime')
prompt = importlib.import_module(PACKAGE + '.runtime_prompt')
annotation = importlib.import_module(PACKAGE + '.episode').AnnotationTask
improvement = importlib.import_module(PACKAGE + '.annotation_improvement.episode').ImprovementTask
original = runtime._a101_annotation_original_source_type
assert runtime.DecisionSource is original
assert annotation.__mro__ == (annotation, original, object)
assert improvement.__mro__ == (improvement, original, object)
names = []
for name, function in vars(original).items():
    if inspect.isfunction(function):
        assert function.__globals__ is vars(runtime), name
        assert function.__qualname__ == 'DecisionSource.' + name, name
        names.append(name)
assert len(names) == 21
for private in (annotation, improvement):
    for name, descriptor in vars(private).items():
        function = descriptor.__func__ if isinstance(descriptor, staticmethod) else descriptor
        if not inspect.isfunction(function):
            continue
        expected = prompt if name == 'instruction_composer' else runtime
        assert function.__globals__ is vars(expected), (private.__name__, name)
for name in ('waiting_support', 'wait_estimate', 'validate_wait_selection',
             'perform_selected_wait', 'receive_outcome', 'receive_form', '_receive_form', 'facts'):
    assert getattr(runtime.Workflow, name).__globals__ is vars(runtime), name
for home in ('execution_job_submission', 'execution_progress_assessment',
             'execution_result_acquisition', 'published_evidence_assessment',
             'resource_work_submission', 'resource_result_acquisition'):
    owner = importlib.import_module(PACKAGE + '.scientific_process.from_child_' + home)
    for name in ('admit_return', 'admit_unowned_return'):
        function = getattr(owner, name)
        assert function.__globals__ is vars(runtime), (home, name)
        assert Path(inspect.getsourcefile(function)).resolve() == Path(owner.__file__).resolve()
origins = {name: str(Path(module.__file__).resolve()) for name, module in tuple(sys.modules.items())
           if getattr(module, '__file__', None) and (name == 'gene_annotation_episode'
               or name.startswith('gene_annotation_episode.') or name == 'method_loop'
               or name.startswith('method_loop.'))}
Path(output).write_text(json.dumps({'first': first, 'passed': True, 'tree': str(tree),
    'isolated': bool(sys.flags.isolated), 'no_site': bool(sys.flags.no_site),
    'public_methods': sorted(names), 'live_runtime_globals': True,
    'prompt_namespace': prompt.__name__,
    'private_c3': [[cls.__module__ + '.' + cls.__qualname__ for cls in private.__mro__]
                  for private in (annotation, improvement)],
    'origins': origins, 'application_objects_constructed': False,
    'scientific_or_native_execution': False}, indent=2) + '\n')
