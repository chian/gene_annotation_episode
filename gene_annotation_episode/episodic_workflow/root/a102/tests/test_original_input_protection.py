"""Exact original denial order plus real Store scope/content validation."""
import pytest

from .input_protection_checks import (
    FAMILIES, actual_store, observe, original_validator, restored_validator,
)


@pytest.fixture(scope='module')
def store(tmp_path_factory):
    with actual_store(tmp_path_factory.mktemp('a102-input-protection')) as value:
        yield value


@pytest.mark.parametrize('family', FAMILIES)
def test_restored_guard_rejects_before_byte_access(store, family):
    expected = observe(original_validator(), store, denied=family)
    actual = observe(restored_validator(), store, denied=family)
    assert actual == expected
    assert actual['outcome']['status'] == 'raised'
    assert actual['artifact_reads'] == []
    assert actual['access_calls'] == list(FAMILIES[:FAMILIES.index(family) + 1])
    if family == 'protein':
        assert actual['outcome']['exception_type'].endswith('.ProteinStructureOperandError')
    else:
        assert actual['outcome']['message'] == family + '_input_protected_reference_denied'


@pytest.mark.parametrize('options', [{}, {'content_mismatch': True}, {'revision_mismatch': True}, {'unscoped': True}])
def test_original_scope_revision_and_hash_validation(store, options):
    expected = observe(original_validator(), store, **options)
    actual = observe(restored_validator(), store, **options)
    assert actual == expected
    assert actual['outcome']['status'] == ('raised' if options else 'returned')
    if options.get('unscoped'):
        assert actual['outcome']['message'] == 'execution_input_outside_assigned_scope'
        assert not actual['artifact_reads']
    elif options:
        assert actual['outcome']['message'] == 'execution_input_version_conflict'
