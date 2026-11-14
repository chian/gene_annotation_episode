"""One isolated private Scientific provider import-order check, no workflow.

CLI TREE SELECTION SHA FIRST OUTPUT DEPENDENCY_ROOT...
"""
import ast
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
import textwrap
import traceback

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a101'
FIRST = ('task', 'task_decision', 'task_state', 'waiting', 'report_delivery', 'decision_inputs', 'standalone_credit_presentation', 'commissioned_credit_presentation')
OWNERS = {
    'task': ('ScientificInvestigationTask', ('next', 'apply_response', 'execute')),
    'task_decision': ('ScientificTaskDecision', ('call', 'interpretation_context', 'exchange_schema', 'exchange_response', 'validate_contract_exchange_request', 'validate_contract_exchange_history', 'exchange_decision')),
    'task_state': ('ScientificTaskState', ('__init__', 'record_execution_failure', 'restore_checkpoint', 'restore', 'record_effect')),
    'waiting': ('ScientificWaiting', ('_execute_selected_wait',)),
    'report_delivery': ('ScientificReportDelivery', ('finish',)),
    'decision_inputs': ('ScientificDecisionInputs', ('decision_inputs',)),
    'standalone_credit_presentation': ('StandaloneScientificPresentation', ('decision_state', 'completed_work', 'exchange_yield_table')),
    'commissioned_credit_presentation': ('CommissionedScientificPresentation', ('decision_state', 'exchange_yield_table')),
}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
    assert len(sys.argv) >= 6 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and not sys.flags.optimize
    tree = Path(sys.argv[1]).resolve(strict=True); selection_path = Path(sys.argv[2]).resolve(strict=True)
    pin, first = sys.argv[3:5]; output = Path(sys.argv[5]).resolve()
    assert first in FIRST and not output.exists() and output.parent.is_dir() and output.is_relative_to(tree.parent)
    raw = selection_path.read_bytes(); assert sha(raw) == pin
    selected = json.loads(raw); rows = {r['target']: r for r in selected['rows']}; assert len(rows) == len(selected['rows'])
    dependencies = [Path(p).resolve(strict=True) for p in sys.argv[6:]]
    assert all(p.is_dir() and not (p/'gene_annotation_episode').exists() and not (p/'method_loop').exists() for p in dependencies)
    sys.path[:0] = [str(tree), *map(str, dependencies)]
    record = {'first': first, 'source_selection': {'path': str(selection_path), 'sha256': pin}, 'tree': str(tree),
              'passed': False, 'workflow_or_science_executed': False}
    status = 1
    try:
        importlib.import_module(PACKAGE + '.scientific_process.' + first)
        runtime = importlib.import_module(PACKAGE + '.runtime')
        inverse = importlib.import_module(PACKAGE + '.scientific_process.tests.scientific_path_oracle').before_path_restoration
        fixture_target = PACKAGE.replace('.', '/') + '/scientific_process/tests/fixtures/runtime_provider_originals.txt'
        fixture = (tree/fixture_target).read_bytes(); assert sha(fixture) == rows[fixture_target]['sha256']
        originals = json.loads(fixture); assert set(originals) == set(OWNERS)
        checked = []
        for module, (class_name, names) in OWNERS.items():
            owner = importlib.import_module(PACKAGE + '.scientific_process.' + module)
            cls = getattr(owner, class_name)
            old_class, = [n for n in ast.parse(originals[module]).body if isinstance(n, ast.ClassDef) and n.name == class_name]
            old_methods = {n.name: n for n in old_class.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for name in names:
                fn = vars(cls)[name]
                holder, = ast.parse('class _SourceIndent:\n' + inspect.getsource(fn)).body
                node, = holder.body
                node = inverse(module, name, node)
                assert ast.dump(node, include_attributes=False) == ast.dump(old_methods[name], include_attributes=False)
                assert fn.__globals__ is vars(runtime) and fn.__code__.co_filename == owner.__file__
                assert fn.__module__ == owner.__name__ and fn.__qualname__ == class_name + '.' + name
                checked.append(owner.__name__ + '::' + fn.__qualname__)
        assert len(checked) == 23
        task = importlib.import_module(PACKAGE + '.scientific_process.task').ScientificInvestigationTask
        assert tuple(c.__name__ for c in task.__bases__) == ('ScientificTaskState', 'ScientificTaskDecision', 'ScientificWaiting', 'ScientificReportDelivery', 'ScientificDecisionState', 'ScientificDecisionInputs')
        router = importlib.import_module(PACKAGE + '.scientific_process.decision_state')
        assert router.ScientificDecisionState.credit_presentation.__globals__ is vars(router)
        prompt = importlib.import_module(PACKAGE + '.scientific_process.task_instructions')
        assert task.instruction_composer is prompt.instructions
        origins = {}
        for name, module in tuple(sys.modules.items()):
            if name not in ('gene_annotation_episode', 'method_loop') and not name.startswith(('gene_annotation_episode.', 'method_loop.')): continue
            path = vars(module).get('__file__')
            if path is None:
                assert all(Path(p).resolve().is_relative_to(tree) for p in vars(module)['__path__'])
                continue
            path = Path(path).resolve(strict=True); assert path.is_relative_to(tree)
            target = str(path.relative_to(tree)); assert target in rows
            assert sha(path.read_bytes()) == rows[target]['sha256'] and path.stat().st_mode & 0o7777 == rows[target]['mode']
            origins[name] = str(path)
        record.update(passed=True, checked_definitions=checked, origins=origins)
        status = 0
    except BaseException as error:
        record['failure'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    with output.open('x') as stream: json.dump(record, stream, indent=2, sort_keys=True); stream.write('\n')
    raise SystemExit(status)
if __name__ == '__main__': main()
