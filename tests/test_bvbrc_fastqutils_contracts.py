"""Typed input/identity boundaries using explicitly synthetic contract examples."""

import pytest

from gene_annotation_episode import bvbrc_fastqutils_contracts as c
from gene_annotation_episode import bvbrc_fastqutils_identity as identity


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), (1, 2), {1: 'value'}, b'bytes', '\ud800'])
def test_non_json_or_nonfinite_values_never_acquire_a_canonical_hash(value):
    with pytest.raises(c.FastqUtilsContractError, match='nonfinite_json'):
        c.json_sha256({'input': value})


def test_cyclic_input_and_non_string_mapping_keys_are_rejected():
    a = []; a.append(a)
    with pytest.raises(c.FastqUtilsContractError):
        c.validate_finite_json(a)
    assert c.canonical_json(0) != c.canonical_json(False) != c.canonical_json(0.0)


@pytest.mark.parametrize('pointer', ['/a~1b/~0/0', '/unicode/α', ''])
def test_reference_roundtrip_preserves_rfc6901_pointer(pointer):
    ref = identity.encode_reference('label', 'analysis', pointer)
    assert identity.decode_reference(ref) == {'kind': 'label', 'analysis_id': 'analysis', 'pointer': pointer}
    with pytest.raises(c.FastqUtilsContractError):
        identity.decode_reference(ref, expected_kind='cell')


@pytest.mark.parametrize('reference', [
    'bvbrc_fastqutils_cell:analysis/%2fdata',
    'bvbrc_fastqutils_cell:%61nalysis/%2Fdata',
    'bvbrc_fastqutils_cell:analysis/%FF',
    'bvbrc_fastqutils_cell:analysis/%2Fbad~2escape',
    'bvbrc_fastqutils_cell:analysis/%2Fdata/extra',
    'bvbrc_fastqutils_unknown:analysis/%2Fdata',
])
def test_noncanonical_or_invalid_identity_is_rejected(reference):
    with pytest.raises(c.FastqUtilsContractError):
        identity.decode_reference(reference)


def test_pointer_dereference_uses_exact_keys_and_canonical_array_indices():
    value = {'a/b': {'~': [3, {'x': 4}]}}
    result = c.pointer_value(value, '/a~1b/~0/1')
    result['x'] = 9
    assert value['a/b']['~'][1]['x'] == 4
    for pointer in ['/a~1b/~0/01', '/a~1b/~0/-', '/a~1b/~0/2', '/a~2b']:
        with pytest.raises(c.FastqUtilsContractError):
            c.pointer_value(value, pointer)


