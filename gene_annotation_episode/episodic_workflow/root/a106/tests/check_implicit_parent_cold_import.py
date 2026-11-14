"""Coordinator-only single cold-process A106 owner import check.

Usage: check_cold_import.py FIRST_MODULE OUTPUT_JSON
The coordinator supplies its authenticated copied source view and run-owned
environment. Each invocation is one serialized child of its owning workflow.
"""
import importlib
import inspect
import json
from pathlib import Path
import sys

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
first, output = sys.argv[1:]
allowed = ('runtime', 'from_parent', 'task_state', 'library.annotation_exchange_protocol',
           'library.annotation_provider_protocol', 'library.annotation_selection_protocol',
           'library.annotation_execution_protocol', 'to_parent', 'decision_waiting',
           'received_outcomes', 'report_receiving', 'episode', 'instructions',
           'annotation_improvement.episode', 'annotation_improvement.from_parent',
           'annotation_improvement.instructions', 'annotation_improvement.to_parent',
           'annotation_improvement.yield_estimator', 'scientific_process.incoming_message_owners')
assert first in allowed
importlib.import_module(PACKAGE + '.' + first)
runtime = importlib.import_module(PACKAGE + '.runtime')
private = importlib.import_module(PACKAGE + '.episode')
names = []
for name, function in vars(runtime.DecisionSource).items():
    if not inspect.isfunction(function): continue
    assert function.__globals__ is vars(runtime), name
    assert function.__qualname__ == 'DecisionSource.' + name, name
    names.append(name)
assert len(names) == 21
assert private.AnnotationTask.__mro__ == (private.AnnotationTask, runtime.DecisionSource, object)
for name in ('next', 'call', 'execute'):
    assert getattr(private.AnnotationTask, name).__globals__ is vars(runtime)
prompt = importlib.import_module(PACKAGE + '.runtime_prompt')
assert private.AnnotationTask.instruction_composer.__globals__ is vars(prompt)
improvement = importlib.import_module(PACKAGE + '.annotation_improvement.episode')
assert improvement.ImprovementTask.__mro__ == (improvement.ImprovementTask, runtime.DecisionSource, object)
for name in ('__init__', 'next', 'call', 'execute', 'finish'):
    assert getattr(improvement.ImprovementTask, name).__globals__ is vars(runtime)
assert improvement.ImprovementTask.instruction_composer.__globals__ is vars(prompt)
root_incoming = importlib.import_module(PACKAGE + '.from_parent')
private_incoming = importlib.import_module(PACKAGE + '.annotation_improvement.from_parent')
assert inspect.getattr_static(runtime.DecisionSource, '__init__') is root_incoming.__init__
assert inspect.getattr_static(private.AnnotationTask, '__init__') is root_incoming.__init__
assert inspect.getattr_static(improvement.ImprovementTask, '__init__') is private_incoming.__init__
assert PACKAGE + '.annotation_improvement.task_state' not in sys.modules
incoming = []
for home in ('execution_job_submission', 'execution_progress_assessment',
             'execution_result_acquisition', 'published_evidence_assessment'):
    owner = importlib.import_module(PACKAGE + '.scientific_process.from_child_' + home)
    for name in ('admit_return', 'admit_unowned_return'):
        assert getattr(owner, name).__globals__ is vars(runtime)
        incoming.append(home + '.' + name)
for name in ('waiting_support', 'receive_outcome', '_receive_form'):
    assert getattr(runtime.Workflow, name).__globals__ is vars(runtime), name
origins = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if name.startswith(PACKAGE) and getattr(module, '__file__', None)}
Path(output).write_text(json.dumps({'first': first, 'public_methods': sorted(names),
    'live_runtime_globals': True, 'private_c3': [cls.__module__ + '.' + cls.__qualname__ for cls in private.AnnotationTask.__mro__],
    'improvement_c3': [cls.__module__ + '.' + cls.__qualname__ for cls in improvement.ImprovementTask.__mro__],
    'scientific_incoming_functions': incoming,
    'origins': origins, 'scientific_or_native_execution': False}, indent=2) + '\n')
