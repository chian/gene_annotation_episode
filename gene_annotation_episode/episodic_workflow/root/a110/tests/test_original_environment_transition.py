"""Compare the pinned original A110 validator with its finite policy successor.

The authenticated original source fixture is retained beside these tests as
nonimportable data. This executes only that original pure validator, with the
actual A110 contract globals; no worker, subprocess or transport is started.
"""
import ast
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import native_atac_differential_contracts as owner


@pytest.fixture
def original_validator():
    raw=(Path(__file__).resolve().parent / 'fixtures' / 'received_execution_original' / 'native_atac_differential_contracts.py.source').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='5f6db5dc3bd2be457acfbcfc06d0e796230b3910d3a919f74854f6abad3a9d5c'
    function=next(node for node in ast.parse(raw).body if isinstance(node,ast.FunctionDef) and node.name=='_environment')
    namespace=dict(owner.__dict__)
    exec(compile(ast.Module(body=[function],type_ignores=[]),'<original-a110-environment>','exec'),namespace)
    return namespace['_environment']


def environment():
    return {'PYTHONNOUSERSITE':'1','PYTHONSAFEPATH':'1','PYTHONDONTWRITEBYTECODE':'1',
        **{name:'/retained/explicit/'+name.lower() for name in
            ('PYTHONHOME','TMP','TEMP','TMPDIR','XDG_CACHE_HOME','PIP_CACHE_DIR')}}


@pytest.mark.parametrize('counts',[{}, {'OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'7'},
    {'OPENBLAS_NUM_THREADS':'literal-metadata','OMP_NUM_THREADS':'original-value'}])
def test_original_count_rejection_becomes_unchanged_metadata_acceptance(original_validator,counts):
    value={**environment(),**counts}
    before=deepcopy(value)
    with pytest.raises(ValueError,match='invalid_native_environment'):
        original_validator(value)
    assert owner._environment(value) is None
    assert value==before


@pytest.mark.parametrize('key,value',[
    ('PYTHONNOUSERSITE','0'),('PYTHONSAFEPATH','0'),('PYTHONDONTWRITEBYTECODE','0'),
    ('BAD-NAME','metadata'),('OPENBLAS_NUM_THREADS',7),('OMP_NUM_THREADS','bad\x00value'),
    ('TMPDIR','relative/path'),
])
def test_noncount_rejections_keep_original_type_and_code(original_validator,key,value):
    supplied={**environment(),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1',key:value}
    before=deepcopy(supplied)
    with pytest.raises(ValueError) as old:
        original_validator(supplied)
    with pytest.raises(type(old.value)) as current:
        owner._environment(supplied)
    assert str(current.value)==str(old.value)
    assert supplied==before
