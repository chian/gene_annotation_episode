"""Retired definitions are absent; live catalogs and descriptors keep their source."""
from __future__ import annotations
import ast
import importlib
import inspect
import json
from pathlib import Path
import pytest
from gene_annotation_episode.episodic_workflow.root.a110.tests.descriptor_membership_source_proof import restore_exact_membership
AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = ['/'.join(filter(None, (prefix, child))) for prefix in PREFIXES for child in
    ('execution_job_submission', 'execution_job_submission/local_job_execution', 'execution_job_submission/hpc_job_execution', 'execution_result_acquisition')]
dump = lambda node: ast.dump(node, include_attributes=False)


@pytest.mark.parametrize('home', HOMES)
def test_actual_unused_function_retirement_and_live_custody(home):
    fixture = json.loads((Path(__file__).parent / 'fixtures/organization_original/unused_execution_functions.json').read_bytes())
    accounts = [row for row in fixture['source_accounts'] if row['home'] == home]
    transitions = {row['target']: row for row in fixture['descriptor_source_membership_transitions']}
    assert len(transitions) == len(fixture['descriptor_source_membership_transitions'])
    assert accounts
    for account in accounts:
        module = importlib.import_module(account['path'][:-3].replace('/', '.'))
        tree = ast.parse(Path(module.__file__).read_bytes())
        for removed in account['retired_functions']:
            assert not hasattr(module, removed['function'])
            original, = ast.parse(removed['original_source']).body
            assert dump(original) == removed['before_AST']
            descriptor = removed.get('unchanged_descriptor_AST_sha256')
            if descriptor:
                import hashlib
                actual, = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'as_record']
                transition = transitions.get(account['path'])
                if transition is None:
                    assert hashlib.sha256(dump(actual).encode()).hexdigest() == descriptor
                else:
                    restored = restore_exact_membership(actual, transition, descriptor)
                    assert hashlib.sha256(dump(restored).encode()).hexdigest() == descriptor
                    axis_root = Path(__file__).resolve().parents[1]
                    axis_prefix = Path('gene_annotation_episode/episodic_workflow/root/a110')
                    for group in transition['groups']:
                        before, after = group['before'], group['after']
                        assert {row['path'] for row in group['removed']} == {str(axis_prefix / name) for name in before if name not in after}
                        assert {row['path'] for row in group['added']} == {str(axis_prefix / name) for name in after if name not in before}
                        for removed_path in group['removed']:
                            assert not (axis_root / Path(removed_path['path']).relative_to(axis_prefix)).exists()
                        for added_path in group['added']:
                            path = axis_root / Path(added_path['path']).relative_to(axis_prefix)
                            assert hashlib.sha256(path.read_bytes()).hexdigest() == added_path['sha256']
                cls, = [node for node in tree.body if isinstance(node, ast.ClassDef)]
                owner = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode').ExecutionEpisode
                assert inspect.getattr_static(owner, 'as_record') is getattr(module, cls.name).__dict__['as_record']
        retained = account.get('retained_function')
        if retained:
            actual = getattr(module, retained['function'])
            namespace = dict(vars(module))
            exec(compile(retained['original_source'], '<original-native-contract-function>', 'exec'), namespace)
            assert actual() == namespace[retained['function']]()
            consumer = importlib.import_module(retained['actual_consumer'][:-3].replace('/', '.'))
            cls, = [value for name, value in vars(consumer).items() if name == 'NativeResourceInformation']
            assert cls.resource_tool_contracts.__globals__[retained['function']] is actual
        for imported in account['removed_unused_imports']:
            acquisition = imported.get('first_module_acquisition')
            if acquisition is None: continue
            consumer = importlib.import_module(imported['path'][:-3].replace('/', '.'))
            provider = importlib.import_module(acquisition['module'])
            assert vars(consumer)[acquisition['alias']] is provider
            assert not hasattr(consumer, 'launch_operation_catalog')
            assert not hasattr(provider, 'launch_operation_catalog')
            assert Path(consumer.__file__).parent.joinpath('__init__.py').read_bytes() == b''
