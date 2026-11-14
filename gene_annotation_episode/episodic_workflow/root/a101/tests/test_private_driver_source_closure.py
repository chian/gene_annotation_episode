"""Static original driver source custody; no imports from captured source or workers."""
import ast
from pathlib import Path

import pytest

from ..native_driver_runtime import _source_closure


@pytest.mark.parametrize('form',['root_relative','private_relative','library_absolute'])
def test_package_member_imports_remain_in_actual_source_snapshot(tmp_path,form):
    package=('gene_annotation_episode' if form=='root_relative' else
        'gene_annotation_episode.episodic_workflow.root.a101'+('.library' if form=='library_absolute' else ''))
    base=tmp_path.joinpath(*package.split('.'))
    base.mkdir(parents=True)
    (tmp_path/'gene_annotation_episode/__init__.py').write_text('')
    (base/'__init__.py').write_text('')
    statement=('from '+package+' import required_science\n' if form=='library_absolute' else 'from . import required_science\n')
    (base/'worker.py').write_text(statement)
    (base/'required_science.py').write_text('ORIGINAL_SCIENTIFIC_VALUE = 3.5\n')
    before={str(path.relative_to(tmp_path)):path.read_bytes() for path in tmp_path.rglob('*.py')}
    closure=_source_closure(tmp_path,[package+'.worker'])
    assert package+'.required_science' in closure
    assert closure[package+'.required_science']==base/'required_science.py'
    assert {str(path.relative_to(tmp_path)):path.read_bytes() for path in tmp_path.rglob('*.py')}==before


def test_current_hmmer_scientific_worker_includes_each_actual_module_member():
    from importlib.util import resolve_name
    original_members = {
        'alignment_data': 'hmmer_alignment_preparation_data',
        'alignment_calculations': 'hmmer_alignment_preparation_calculations',
        'artifact_data': 'hmmer_artifact_data',
        'artifact_calculations': 'hmmer_artifact_calculations',
        'emission_data': 'hmmer_emission_data',
        'emission_calculations': 'hmmer_emission_calculations',
        'fm_data': 'hmmer_fm_data',
        'fm_calculations': 'hmmer_fm_calculations',
        'model_data': 'hmmer_model_data',
        'simulation_data': 'hmmer_simulation_data',
        'simulation_calculations': 'hmmer_simulation_calculations',
        'statistics_data': 'hmmer_statistics_data',
        'statistics_calculations': 'hmmer_statistics_calculations',
    }
    root=Path(__file__).resolve().parents[1]
    repository=root.parents[3]
    package='.'.join(root.relative_to(repository).parts)+'.library'
    worker=root/'library'/'native_hmmer_preparation_worker.py'
    expected={}
    expected_files={}
    layouts=set()
    for alias,member in original_members.items():
        locations=[path for path in (root/(member+'.py'),root/'library'/(member+'.py')) if path.is_file()]
        assert len(locations)==1, (member,locations)
        path,=locations
        layouts.add(path.parent)
        expected[alias]='.'.join(path.relative_to(repository).with_suffix('').parts)
        expected_files[expected[alias]]=path
    assert len(layouts)==1
    actual={}
    for node in ast.walk(ast.parse(worker.read_bytes())):
        if not isinstance(node,ast.ImportFrom):
            continue
        parent=resolve_name('.'*node.level+(node.module or ''),package) if node.level else (node.module or '')
        for imported in node.names:
            alias=imported.asname or imported.name
            if alias not in original_members:
                continue
            assert alias not in actual
            assert imported.name==original_members[alias]
            actual[alias]=parent+'.'+imported.name
    assert actual==expected
    closure=_source_closure(repository,[package+'.native_hmmer_preparation_worker'])
    assert set(expected.values())<=set(closure)
    for name,path in expected_files.items():
        assert closure[name].resolve()==path.resolve()
        assert closure[name].read_bytes()==path.read_bytes()
