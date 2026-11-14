"""The nominal Monitor request retains scientific lookup and error ordering.

Controls compare real private callbacks against the authenticated original
ActionExecution body, with explicit registry/transport ports and no model/native
work. The nominal selected child is always the actual private Monitor binding.
"""
from copy import deepcopy
import hashlib
import importlib
import json
import pytest
from . import test_monitor_directional_boundaries as exchange
from . import test_monitor_source_identity as identity

HOMES = exchange.HOMES
ROOT = exchange.ROOT
PRIOR_ENDPOINT_SHA = '66e627247d5c618db42cc5cbcd9f03ac9808e98c5eb63fab208a6b4df8ed3010'
SCENARIOS = ('absent', 'distinct', 'lookup_error', 'membership_error',
             'materialize_error', 'invalid_initial', 'unavailable', 'invalid_assignment')


class LookupFailure(ValueError):
    pass


def exercise(callback, home, scenario):
    def prepared(workflow, source, selection, index, scope, role, owner):
        registry = workflow.episode_bindings
        events = registry.events
        actual_child = registry.binding
        actual_class = importlib.import_module(ROOT+'.'+home.replace('/', '.')+'.episode').MonitorEpisodes
        assert type(actual_child) is actual_class
        class Roles:
            def __contains__(self, key):
                events.append(('scientific_membership', key))
                if scenario == 'membership_error':
                    raise LookupFailure('controlled_role_membership_failure')
                return scenario != 'absent'
        registry.roles = Roles()
        def lookup(key, *, owner):
            events.append(('scientific_lookup', key, owner))
            assert owner == home and key == 'scientific_process'
            if scenario in ('lookup_error', 'materialize_error', 'invalid_initial', 'unavailable'):
                raise LookupFailure('controlled_scientific_lookup_failure')
            assert registry.scientific is not actual_child
            return registry.scientific
        registry.for_role = lookup
        prior_materialize = workflow.launch_instructions.materialize
        def materialize(value):
            prior_materialize(value)
            if scenario == 'materialize_error':
                raise LookupFailure('controlled_materialization_failure')
        workflow.launch_instructions.materialize = materialize
        return callback(workflow, source, selection, index, scope, role, owner)
    base = {'invalid_initial':'invalid_initial', 'unavailable':'unavailable',
            'invalid_assignment':'expanded_types'}.get(scenario, 'valid')
    return exchange.outgoing(prepared, home, base)


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('scenario', SCENARIOS)
def test_recursive_monitor_scientific_predicate_events_and_error_order(home, scenario):
    cls = importlib.import_module(ROOT+'.'+home.replace('/', '.')+'.episode').MonitorEpisodes
    callback, incoming = cls.child_message_exchange('monitor')
    assert callback.__module__ == ROOT+'.'+home.replace('/', '.')+'.to_child_execution_monitoring'
    observed = exercise(callback, home, scenario)
    expected = exercise(exchange.original_callbacks()[0], home, scenario)
    assert observed == expected
    result, events = observed
    names = [event[0] for event in events]
    if scenario in ('absent', 'distinct'):
        assert result[0] == 'returned' and result[1][4:] == (None, None)
        assert result[1][3]['target_handle'] == 'execution:child'
    else:
        assert result[0] == 'raised'
    if scenario in ('invalid_initial', 'unavailable'):
        assert 'materialize' not in names and 'scientific_membership' not in names
    elif scenario == 'materialize_error':
        assert names[-1] == 'materialize' and result[2] == 'controlled_materialization_failure'
    else:
        assert names.count('scientific_membership') == 1
        assert names.index('materialize') < names.index('scientific_membership')
        if scenario in ('absent', 'membership_error'):
            assert 'scientific_lookup' not in names
        else:
            assert names.count('scientific_lookup') == 1
            assert names.index('scientific_membership') < names.index('scientific_lookup')
        if scenario == 'lookup_error':
            assert names[-1] == 'scientific_lookup' and result[2] == 'controlled_scientific_lookup_failure'
        if scenario == 'membership_error':
            assert names[-1] == 'scientific_membership' and result[2] == 'controlled_role_membership_failure'


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('configured', (False, True))
def test_recursive_endpoint_bytes_refresh_descriptor_without_credit_change(home, configured):
    # Exercise the existing meaningful exact-member/configuration contract only;
    # other descriptor mutation and absent-file cases are unchanged boundaries.
    identity.test_actual_descriptor_members_bytes_and_original_configuration(home, configured)
    module, instance = identity.bound(home, configured)
    root = identity.actual_root(module, home)
    hashes = {name: identity.sha((root/name).read_bytes()) for name in identity.members(home)}
    endpoint = home+'/to_child_execution_monitoring.py'
    assert hashes[endpoint] != PRIOR_ENDPOINT_SHA
    historical = dict(hashes, **{endpoint: PRIOR_ENDPOINT_SHA})
    old_digest = identity.sha(json.dumps(historical, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode())
    current = instance.as_record()
    assert current['implementation_sha256'] == identity.independent_fingerprint(root, home)
    assert current['implementation_sha256'] != old_digest
    assert current['configuration'] == identity.original_configuration(instance)
