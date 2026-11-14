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
FIRST_MODULES = ('from_parent', 'goal', 'task_state')


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
    record = {'version': 'a104_incoming_goal_cold_import_v1', 'first_module': first,
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
        incoming = importlib.import_module(PACKAGE + '.from_parent')
        state = importlib.import_module(PACKAGE + '.task_state')
        goal = importlib.import_module(PACKAGE + '.goal')
        assert runtime.DecisionSource.__init__ is incoming.__init__
        assert episode.AnnotationTask.__init__ is incoming.__init__
        assert improvement.ImprovementTask.__init__ is incoming.__init__
        assert '__init__' not in vars(state)
        assert '__init__' not in vars(episode.AnnotationTask) and '__init__' not in vars(improvement.ImprovementTask)
        assert incoming.__init__.__code__.co_filename == incoming.__file__
        assert incoming.__init__.__globals__ is vars(runtime)
        assert incoming.__init__.__qualname__ == 'DecisionSource.__init__'
        assert goal.prepare_goal.__globals__ is vars(runtime)
        assert goal.prepare_goal.__code__.co_filename == goal.__file__
        for name in ('bind_execution_context', 'suspension_changed', 'restore_checkpoint', 'restore', 'record_effect', 'checkpoint'):
            assert getattr(runtime.DecisionSource, name) is getattr(state, name)
            assert getattr(state, name).__globals__ is vars(runtime)
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
            incoming_constructor_owner=incoming.__name__, goal_owner=goal.__name__,
            shared_private_constructor_identity_preserved=True,
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
