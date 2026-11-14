"""Real descriptor methods over disposable copies of authenticated source bytes."""
import ast
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
from types import FunctionType, SimpleNamespace

HERE = Path(__file__).resolve().parent
AXIS = HERE.parent.parent
PACKAGE = __package__.removesuffix('.library.tests')
FIXTURES = HERE / 'fixtures/hpc_handoff_contract'
DATA = json.loads((FIXTURES / 'descriptor_authority.json').read_text())
ORIGINAL = (FIXTURES / 'descriptor_before.py.source').read_bytes()
assert hashlib.sha256(ORIGINAL).hexdigest() == DATA['original_fixture_sha256']
shape = lambda node: ast.dump(node, include_attributes=False)


class Memory:
    def as_record(self):
        return {'controlled_memory': 'descriptor-input'}


def supplied_configuration(complete):
    return SimpleNamespace(resources=[{'resource': 'controlled'}], commissions=[{'commission': 'controlled'}],
        memory=Memory() if complete else None, private_yield_binding=complete,
        initial_information=[{'initial': 'controlled'}], handoff_unit='controlled-handoff',
        acquired_record_unit='controlled-acquired', log_window_bytes=4096, log_roles=('stdout', 'stderr'),
        results_yield_profiles={'controlled-result': {'credit': 1}} if complete else {},
        task_yield_profiles={'controlled-task': {'credit': 2}} if complete else {})


def check_descriptor_source_sensitivity(tmp_path, complete):
    # Each real method keeps Path/hash/digest implementations. Only __file__ and
    # the axis-runtime file locator point at an isolated byte-for-byte copy.
    copy_root = tmp_path / 'axis_sources'
    for name, expected in DATA['production_sources'].items():
        source = AXIS / name
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        target = copy_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    policy = copy_root / DATA['policy_member']
    policy_before = policy.read_bytes()
    assert hashlib.sha256(policy_before).hexdigest() == DATA['policy_sha256']
    fixture_tree = ast.parse(ORIGINAL)
    observed = []
    for row in DATA['descriptors']:
        module = importlib.import_module(PACKAGE + '.' + row['home'].replace('/', '.') + '.binding_record')
        actual = getattr(module, row['class']).as_record
        actual_tree = ast.parse(Path(module.__file__).read_bytes())
        cls, = [node for node in actual_tree.body if isinstance(node, ast.ClassDef) and node.name == row['class']]
        method, = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'as_record']
        assert hashlib.sha256(shape(method).encode()).hexdigest() == row['current_method_AST']
        oracle_cls, = [node for node in fixture_tree.body if isinstance(node, ast.ClassDef) and node.name == row['oracle_class']]
        oracle_method, = oracle_cls.body
        assert hashlib.sha256(shape(oracle_method).encode()).hexdigest() == row['original_method_AST']
        namespace = dict(actual.__globals__)
        namespace['__file__'] = str(copy_root / row['home'] / 'binding_record.py')
        if 'axis_runtime' in namespace:
            namespace['axis_runtime'] = SimpleNamespace(__file__=str(copy_root / 'runtime.py'))
        exec(compile(ast.Module(body=[oracle_cls], type_ignores=[]), str(FIXTURES / 'descriptor_before.py.source'), 'exec'), namespace)
        original = namespace[row['oracle_class']].as_record
        current = FunctionType(actual.__code__, namespace, actual.__name__, actual.__defaults__, actual.__closure__)
        current.__kwdefaults__ = actual.__kwdefaults__
        configuration = supplied_configuration(complete)
        before = original(configuration)
        after = current(configuration)
        assert before.keys() == after.keys()
        old_identity = {key: value for key, value in before.items() if key != 'implementation_sha256'}
        new_identity = {key: value for key, value in after.items() if key != 'implementation_sha256'}
        assert old_identity == new_identity
        assert before['implementation_sha256'] != after['implementation_sha256']
        assert row['after_members'] == row['before_members'] + [DATA['policy_member']]
        policy.write_bytes(policy_before + b'\n# Controlled descriptor sensitivity input.\n')
        try:
            before_changed = original(configuration)
            after_changed = current(configuration)
        finally:
            policy.write_bytes(policy_before)
        assert before_changed == before
        assert {key: value for key, value in after_changed.items() if key != 'implementation_sha256'} == new_identity
        assert after_changed['implementation_sha256'] != after['implementation_sha256']
        assert current(configuration) == after
        observed.append({'home': row['home'], 'configuration': deepcopy(new_identity),
            'original_digest': before['implementation_sha256'], 'current_digest': after['implementation_sha256'],
            'changed_policy_digest': after_changed['implementation_sha256']})
    assert len(observed) == 16 and len({row['home'] for row in observed}) == 16
    (tmp_path / 'descriptor_sensitivity.json').write_text(json.dumps(observed, indent=2) + '\n')
