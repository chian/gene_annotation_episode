"""Complete original pure contract exports and reflective schema initialization."""
import ast
import hashlib
from importlib import import_module
from pathlib import Path

import pytest


def original_exports():
    raw=(Path(__file__).parent/'fixtures/retained_protein_contract/original_contract.py.txt').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='8f270de4553bbedd3edd8d6c8ac24cbb11df84ff123dc9309364d2d5286d3903'
    tree=ast.parse(raw)
    public=next(n.value for n in tree.body if isinstance(n,ast.Assign) and
                any(isinstance(t,ast.Name) and t.id=='PUBLIC_TYPE_NAMES' for t in n.targets))
    assert isinstance(public,ast.Call) and isinstance(public.func,ast.Name) and public.func.id=='tuple'
    split,=public.args
    assert isinstance(split,ast.Call) and isinstance(split.func,ast.Attribute) and split.func.attr=='split'
    names=split.func.value.value.split()
    result=[]
    # Preserve module binding order without importing or executing the fixture.
    bound_names={}
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            bound_names.setdefault(node.name,None)
        elif isinstance(node,(ast.Import,ast.ImportFrom)):
            for alias in node.names:
                assert alias.name!='*'
                name=alias.asname or (alias.name.split('.')[0] if isinstance(node,ast.Import) else alias.name)
                bound_names.setdefault(name,None)
        elif isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            for target in targets:
                assert isinstance(target,ast.Name)
                bound_names.setdefault(target.id,None)
        else:
            assert isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__all__' for t in node.targets):
            values=node.value.elts
        elif isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='__all__':
            assert isinstance(node.op,ast.Add)
            values=node.value.elts
        else:
            continue
        for value in values:
            if isinstance(value,ast.Starred):
                if isinstance(value.value,ast.Name):
                    assert value.value.id=='PUBLIC_TYPE_NAMES'
                    result.extend(names)
                else:
                    original=ast.parse('[name for name in globals() if name.startswith("validate_")]',mode='eval').body
                    assert ast.dump(value.value,include_attributes=False)==ast.dump(original,include_attributes=False)
                    result.extend(name for name in bound_names if name.startswith('validate_'))
            else:
                result.append(ast.literal_eval(value))
    return tuple(names),result


@pytest.mark.parametrize('axis',['a101','a105','a106','a108'])
def test_complete_original_contract_namespace_and_raw_atom_schema(axis):
    module=import_module('gene_annotation_episode.episodic_workflow.root.'+axis+
                         '.library.retained_input_authority.protein_structure_contracts')
    public,exports=original_exports()
    assert module.PUBLIC_TYPE_NAMES==public
    assert module.__all__==exports
    assert all(hasattr(module,name) for name in exports)
    definitions=module.protein_structure_schema_definitions()
    assert set(public)<=set(definitions)
    raw=definitions['RawAtomRow']
    assert set(raw['properties'])=={'identity','xyz_A','occupancy','b_iso','state','issues'}
    assert set(raw['required'])==set(raw['properties']) and raw['additionalProperties'] is False
    assert module.ParsedStructure.__annotations__['atoms'] is not None
    assert module.protein_structure_schema_definitions()==definitions
