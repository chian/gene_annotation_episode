"""Fresh isolated private-policy import identities, without task construction.

CLI TREE SELECTION_JSON SELECTION_SHA FIRST_MODULE OUTPUT_JSON DEPENDENCY_ROOT...
The owning runner supplies -I -B -S and authenticates dependency inventories.
"""
import ast
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
import traceback

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
FIRST_MODULES = (
    'library.hpc_handoff_return_form',
    'runtime',
    'hpc_work_planning.task',
    'scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.task',
)
ORIGINAL_SHA = 'e3227bc4c23bf0f5f60b311abc45d7d36929f95db789901acd1551c9e0f7b1bc'

def sha(raw): return hashlib.sha256(raw).hexdigest()

def main():
    assert len(sys.argv) >= 6
    tree = Path(sys.argv[1]).resolve(strict=True)
    selection_path, pin, first = Path(sys.argv[2]).resolve(strict=True), sys.argv[3], sys.argv[4]
    output = Path(sys.argv[5]).resolve()
    assert first in FIRST_MODULES and not output.exists() and output.parent.is_dir()
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    assert output.is_relative_to(tree.parent)
    raw = selection_path.read_bytes(); assert sha(raw) == pin
    selection = json.loads(raw); rows = {row['target']: row for row in selection['rows']}
    assert len(rows) == len(selection['rows'])
    for target in rows:
        assert not Path(target).is_absolute() and '..' not in Path(target).parts
    dependencies = [Path(value).resolve(strict=True) for value in sys.argv[6:]]
    assert all(path.is_dir() and path != tree for path in dependencies)
    sys.path[:0] = [str(tree), *map(str, dependencies)]
    record = {'version':'a104_hpc_handoff_policy_cold_v1','first_module':first,
        'source_selection':{'path':str(selection_path),'sha256':pin},
        'tree':str(tree),'dependency_roots':list(map(str,dependencies)),
        'application_workflow_executed':False,'constructors_executed':False,'passed':False}
    status = 1
    try:
        importlib.import_module(PACKAGE + '.' + first)
        runtime = importlib.import_module(PACKAGE + '.runtime')
        policy = importlib.import_module(PACKAGE + '.library.hpc_handoff_return_form')
        assert policy.validate_hpc_handoff_return_form.__globals__ is vars(runtime)
        assert policy.validate_hpc_handoff_return_form.__builtins__ is runtime.Workflow.selected.__builtins__
        assert policy.private_handoff_validator.__globals__ is vars(policy)
        assert policy.validate_hpc_handoff_return_form.__module__ == policy.__name__
        assert policy.validate_hpc_handoff_return_form.__qualname__ == 'validate_hpc_handoff_return_form'
        assert Path(policy.validate_hpc_handoff_return_form.__code__.co_filename).resolve() == Path(policy.__file__).resolve()
        assert len(policy.PRIVATE_TASKS) == 8
        classes = []
        for module_name, class_name in policy.PRIVATE_TASKS.items():
            module = importlib.import_module(module_name)
            cls = vars(module)[class_name]
            assert vars(module)['_hpc_handoff_original_task'] is cls
            assert vars(cls)['child_return_form_policy'] is policy.HPC_HANDOFF_RETURN_POLICY
            assert cls.__module__ == module_name and cls.__qualname__ == class_name
            assert vars(cls)['next'].__globals__ is vars(runtime)
            # Exact class identity admission needs no workflow/path/schema operands.
            source = object.__new__(cls)
            assert vars(source) == {}
            assert policy.private_handoff_validator(source) is policy.validate_hpc_handoff_return_form
            declaration = importlib.import_module(module_name[:-4] + 'episode')
            declared = [value for value in vars(declaration).values() if type(value) is type
                        and value.__module__ == declaration.__name__
                        and vars(value).get('decision_source_type') is cls]
            assert len(declared) == 1
            classes.append({'module':module_name,'class':class_name,
                            'declaration':declaration.__name__ + '.' + declared[0].__name__})
        fixture = tree / PACKAGE.replace('.','/') / 'tests/fixtures/source_request_assembly/a104_implicit_parent_original_runtime.txt'
        original = fixture.read_bytes(); assert sha(original) == ORIGINAL_SHA
        workflow, = [n for n in ast.parse(original).body if isinstance(n,ast.ClassDef) and n.name=='Workflow']
        method, = [n for n in workflow.body if isinstance(n,ast.FunctionDef) and n.name=='selected']
        assignment, = [n for n in ast.walk(method) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='hpc_launch' for t in n.targets)]
        branch, = [n for n in ast.walk(method) if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.values[0],ast.Name) and n.test.values[0].id=='hpc_launch']
        current, = ast.parse(inspect.getsource(policy.validate_hpc_handoff_return_form)).body
        assert [ast.dump(n) for n in current.body] == [ast.dump(assignment),ast.dump(branch)]
        origins = {}
        for name, module in tuple(sys.modules.items()):
            if not (name in ('gene_annotation_episode','method_loop') or name.startswith(('gene_annotation_episode.','method_loop.'))):
                continue
            file = vars(module).get('__file__')
            if file is None:
                paths = vars(module).get('__path__')
                assert paths is not None and all(Path(path).resolve().is_relative_to(tree) for path in paths), name
                continue
            path = Path(file).resolve(strict=True)
            assert path.is_relative_to(tree), ('canonical_or_foreign_project_origin',name,str(path))
            target = str(path.relative_to(tree)); assert target in rows, (name,target)
            row = rows[target]; digest = sha(path.read_bytes())
            assert row.get('descriptor_byte_operand_only') is not True, ('descriptor_bytes_imported',name,target)
            assert digest == row['source']['sha256'], (name,target)
            assert path.stat().st_mode & 0o7777 == row['mode'], (name,target,'mode')
            origins[name] = {'target':target,'sha256':digest,'path':str(path)}
        assert PACKAGE + '.' + first in origins and policy.__name__ in origins and runtime.__name__ in origins
        record.update(passed=True,private_classes=classes,private_class_count=8,
                      validator_globals=runtime.__name__,project_origins=origins,
                      original_policy_AST_preserved=True,captured_builtins_identity=True)
        status = 0
    except BaseException as error:
        record.update(error={'type':type(error).__module__ + '.' + type(error).__qualname__,
                             'message':str(error),'traceback':traceback.format_exc()})
    finally:
        with output.open('x') as stream: json.dump(record,stream,indent=2); stream.write('\n')
    return status

if __name__ == '__main__': raise SystemExit(main())
