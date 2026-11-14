"""One fresh isolated A104 import-order control; invoked by the coordinator.

CLI: TREE SELECTION_JSON SELECTION_SHA FIRST_MODULE OUTPUT_JSON DEPENDENCY_ROOT...
The coordinator supplies -I -B -S, sequential children, owned paths and original
dependency inventories. This helper creates no workflow, task or native work.
"""
from __future__ import annotations
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
ORIGINAL_RUNTIME_SHA = 'e3227bc4c23bf0f5f60b311abc45d7d36929f95db789901acd1551c9e0f7b1bc'
FIRST_MODULES = ('runtime', 'action_admission', 'library.parent_task_report_forms',
    'library.unbound_child_action_options', 'scientific_process.completion_snapshot')


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    assert len(sys.argv) >= 6
    tree = Path(sys.argv[1]).resolve(strict=True)
    selection_path, pin, first = Path(sys.argv[2]).resolve(strict=True), sys.argv[3], sys.argv[4]
    output = Path(sys.argv[5]).resolve()
    assert first in FIRST_MODULES and not output.exists() and output.parent.is_dir()
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    assert output.is_relative_to(tree.parent)
    raw = selection_path.read_bytes(); assert sha(raw) == pin
    selection = json.loads(raw)
    rows = {row['target']: row for row in selection['rows']}
    assert len(rows) == len(selection['rows'])
    for target in rows:
        assert not Path(target).is_absolute() and '..' not in Path(target).parts
    dependencies = [Path(value).resolve(strict=True) for value in sys.argv[6:]]
    assert all(path.is_dir() and path != tree for path in dependencies)
    # Isolated stdlib search entries remain. No cwd/repository fallback is added.
    sys.path[:0] = [str(tree), *map(str, dependencies)]
    record = {'version': 'a104_policy_cold_import_v1', 'first_module': first,
        'source_selection': {'path': str(selection_path), 'sha256': pin},
        'tree': str(tree), 'dependency_roots': list(map(str, dependencies)),
        'application_workflow_executed': False, 'passed': False}
    status = 1
    try:
        importlib.import_module(PACKAGE + '.' + first)
        runtime = importlib.import_module(PACKAGE + '.runtime')
        episode = importlib.import_module(PACKAGE + '.episode')
        improvement = importlib.import_module(PACKAGE + '.annotation_improvement.episode')
        assert runtime.DecisionSource is runtime._annotation_original_decision_source
        assert episode.AnnotationTask.__bases__ == (runtime.DecisionSource,)
        assert improvement.ImprovementTask.__bases__ == (runtime.DecisionSource,)
        assert runtime.DecisionSource.__bases__ == (object,)
        assert runtime.DecisionSource.__module__ == PACKAGE + '.runtime'
        fixture = tree / Path(PACKAGE.replace('.', '/')) / 'tests/fixtures/source_request_assembly/a104_implicit_parent_original_runtime.txt'
        data = fixture.read_bytes(); assert sha(data) == ORIGINAL_RUNTIME_SHA
        cls, = [node for node in ast.parse(data).body if isinstance(node, ast.ClassDef) and node.name == 'DecisionSource']
        names = [node.name for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        assert len(names) == 21
        for name in names:
            function = vars(runtime.DecisionSource)[name]
            assert function.__globals__ is vars(runtime), name
            assert function.__qualname__ == 'DecisionSource.' + name
        for module_name, function_name in (('task', 'next'), ('provider', 'call'),
                ('task_outcomes', 'execute'), ('instructions', 'instructions'), ('to_parent', 'finish'),
                ('to_child_execution_job_submission', 'prepare_parent_request'),
                ('scientific_process.from_child_scientific_process', 'admit_parent_return'),
                ('annotation_improvement.task', 'next'),
                ('annotation_improvement.provider', 'call'),
                ('annotation_improvement.task_outcomes', 'execute'),
                ('annotation_improvement.instructions', 'instructions'),
                ('annotation_improvement.to_parent', 'finish'),
                ('annotation_improvement.to_child_annotation_improvement', 'prepare_parent_request')):
            function = getattr(importlib.import_module(PACKAGE + '.' + module_name), function_name)
            expected_namespace = (importlib.import_module(PACKAGE + '.runtime_prompt')
                                  if module_name in ('instructions', 'annotation_improvement.instructions') else runtime)
            assert function.__globals__ is vars(expected_namespace), (module_name, function_name)
        for module_name, functions in (
            ('action_admission', ('parent_common_action_permission', 'filter_parent_task_credit_roles',
                'filter_parent_common_actions', 'validate_parent_axis_choice', 'validate_parent_tool_selection',
                'parent_catalog', 'parent_tool_admission')),
            ('library.parent_task_report_forms', ('form_inputs', 'child_request_form')),
            ('library.unbound_child_action_options', ('append_unbound_child_options', '_default_scientific_child_roles')),
        ):
            module = importlib.import_module(PACKAGE + '.' + module_name)
            for name in functions:
                assert getattr(module, name).__globals__ is vars(runtime), (module_name, name)
        defaults = importlib.import_module(PACKAGE + '.library.unbound_child_action_options')
        assert runtime.Workflow._default_scientific_child_roles is defaults._default_scientific_child_roles
        assert defaults._default_scientific_child_roles.__module__ == runtime.__name__
        assert defaults._default_scientific_child_roles.__qualname__ == 'Workflow._default_scientific_child_roles'
        science = importlib.import_module(PACKAGE + '.scientific_process.completion_snapshot')
        assert science.completion_snapshot.__globals__ is vars(science)
        origins = {}
        for name, module in tuple(sys.modules.items()):
            if not (name in ('gene_annotation_episode', 'method_loop')
                    or name.startswith(('gene_annotation_episode.', 'method_loop.'))):
                continue
            file = vars(module).get('__file__')
            if file is None:
                package_paths = vars(module).get('__path__')
                assert package_paths is not None and all(Path(path).resolve().is_relative_to(tree) for path in package_paths), name
                continue
            path = Path(file).resolve(strict=True)
            assert path.is_relative_to(tree), ('canonical_or_foreign_project_origin', name, str(path))
            target = str(path.relative_to(tree)); assert target in rows, (name, target)
            digest = sha(path.read_bytes()); row = rows[target]
            assert row.get('descriptor_byte_operand_only') is not True, ('descriptor_bytes_imported', name, target)
            assert digest == row['source']['sha256'], (name, target)
            assert path.stat().st_mode & 0o7777 == row['mode'], (name, target, 'mode')
            origins[name] = {'target': target, 'sha256': digest, 'path': str(path)}
        assert PACKAGE + '.' + first in origins and PACKAGE + '.runtime' in origins and PACKAGE + '.episode' in origins
        record.update(passed=True, public_methods_checked=names, project_origins=origins,
            public_class={'module': runtime.DecisionSource.__module__, 'qualname': runtime.DecisionSource.__qualname__},
            private_class={'module': episode.AnnotationTask.__module__, 'qualname': episode.AnnotationTask.__qualname__},
            improvement_class={'module': improvement.ImprovementTask.__module__, 'qualname': improvement.ImprovementTask.__qualname__})
        status = 0
    except BaseException as error:
        record.update(error={'type': type(error).__module__ + '.' + type(error).__qualname__,
                            'message': str(error), 'traceback': traceback.format_exc()})
    with output.open('x') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
    raise SystemExit(status)


if __name__ == '__main__': main()
