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


