"""Native input helpers remain with actual callers; obsolete owners lose them."""
from __future__ import annotations
import ast
import importlib
import inspect
import json
from pathlib import Path
import pytest
AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = ['/'.join(filter(None, (prefix, child))) for prefix in PREFIXES
    for child in ('execution_job_submission', 'execution_result_acquisition')]
dump = lambda node: ast.dump(node, include_attributes=False)


@pytest.mark.parametrize('home', HOMES)
def test_native_parent_input_defining_custody(home):
    fixture = json.loads((Path(__file__).parent / 'fixtures/organization_original/native_parent_input_custody.json').read_bytes())
    account, = [item for item in fixture['source_accounts'] if item['home'] == home]
    module = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode')
    owner = module.ExecutionEpisode
    assert not hasattr(owner, account['retired_method'])
    if account['retired_class']:
        assert account['retired_class'] not in {cls.__name__ for cls in owner.__mro__}
        assert not (Path(module.__file__).parent / 'original_request_inputs.py').exists()
    for native in account['substantive_retained_counterparts']:
        native_module = importlib.import_module(native['path'][:-3].replace('/', '.'))
        native_owner = importlib.import_module(native_module.__name__.rsplit('.', 1)[0] + '.episode').ExecutionEpisode
        descriptor = getattr(native_module, native['class']).__dict__[native['method']]
        assert inspect.getattr_static(native_owner, native['method']) is descriptor
        assert descriptor.__module__ == native_module.__name__
        cls, = [item for item in ast.parse(Path(native_module.__file__).read_bytes()).body if isinstance(item, ast.ClassDef) and item.name == native['class']]
        method, = [item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name == native['method']]
        assert dump(method) == account['before_AST']
    assert account['retained_private_callers'] == []
