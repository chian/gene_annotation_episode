"""Original negative guards only; this does not prove positive receipt custody."""
import pytest
from .negative_guard_checks import HOMES, VERSIONS, run_probe


@pytest.fixture(scope='module')
def observations(tmp_path_factory):
    return run_probe(tmp_path_factory.mktemp('negative-execution-guards'))['owners']


@pytest.mark.parametrize('home', HOMES)
def test_original_negative_guards(home, observations):
    row = observations[home]
    assert row['constructor']['status'] == 'returned'
    assert row['practical'] == {'status': 'returned', 'value': False}
    assert row['api_handoff'] == {'status': 'returned', 'value': False}
    assert row['ordinary'] == {'status': 'returned', 'value': True}
    assert set(row['bundles']) == set(VERSIONS)
    for version in VERSIONS:
        boundary = row['bundles'][version]
        assert boundary['received']['status'] == 'returned'
        selection, handoffs, results = boundary['received']['value']
        assert selection['known_record_refs'] == [boundary['reference']]
        assert handoffs == results == {}
        assert boundary['received_generic_parser_calls'] == []
        assert boundary['resolve'] == {'status': 'returned', 'value': False}
        assert boundary['resolve_generic_parser_calls'] == []
