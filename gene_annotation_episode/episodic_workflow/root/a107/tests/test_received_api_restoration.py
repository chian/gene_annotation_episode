"""Actual A107 API source/result/received custody, with no live transport."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from .fixtures.received_api_fixture import ReceivedAPIFixture, module


@pytest.fixture(autouse=True)
def no_uncontrolled_native_boundary(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('received API test attempted uncontrolled transport/process execution')
    monkeypatch.setattr('socket.create_connection', denied)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', denied)
    monkeypatch.setattr('subprocess.Popen', denied)


@pytest.fixture(params=('bvbrc_minhash', 'bvbrc_data'))
def received(tmp_path, request):
    value = ReceivedAPIFixture(tmp_path, request.param, connect=True)
    authority = module('library/received_api_information/received_api_authority')
    value.configuration = authority.ReceivedAPIConfiguration.original_global_factory(value.case.factory)
    value.catalog = value.configuration.construct(store=value.case.store, run_id=value.case.run_id,
        directory=value.case.directory / 'workflow', tool_registry=value.case.tools, services=value.case.services)
    annotation = module('annotation_received_api_information').received_api_reports
    value.case.registry.configure_received_api_information(value.catalog, annotation)
    general = module('library/received_execution_information/received_configuration')
    value.execution_configuration = general.ReceivedExecutionConfiguration.original_global_factory(value.case.factory)
    value.execution_catalog = value.execution_configuration.construct(store=value.case.store, run_id=value.case.run_id,
        directory=value.case.directory / 'workflow', tool_registry=value.case.tools, services=value.case.services)
    execution_annotation = module('annotation_received_execution_information').received_execution_information
    value.case.registry.configure_received_execution_information(value.execution_catalog, execution_annotation)
    try:
        yield value
    finally:
        value.close()


def owner(received, context=None):
    return received.case.registry._recipient_received_api_reports(context or received.parent)


def test_original_nonempty_saved_admission_and_payload_are_preserved(received):
    h = received
    before_actions = h.action_state()
    references = owner(h).received_form_references(h.parent, h.form, h.schema, h.operation_key)
    assert references
    expected = h.host.received_facts(h.parent, h.schema)
    assert any(expected.values())
    assert owner(h).received_report_facts(h.parent) == expected
    assert owner(h).received_report_sources('partner_presence_evidence')
    before = h.state()
    assert owner(h).received_form_references(h.parent, h.form, h.schema, h.operation_key) == references
    assert h.state() == before and h.action_state() == before_actions and len(h.calls) == 1
    if h.service == 'bvbrc_minhash':
        values = owner(h).initial_minhash_information(h.parent)['received_minhash_values']
        assert values == h.host.received_context(h.parent)
        assert len(next(row['facts'] for row in values if row['fact_source'] == 'bvbrc_minhash_matches')) == 2
        assert owner(h).resolve_received_reference(h.parent, '83333.1', 'bvbrc_minhash_genome') is True
        assert owner(h).resolve_received_reference(h.parent, '99999.1', 'bvbrc_minhash_genome') is False
        # Native result identifiers stay with this actual result owner.
        assert h.owner.resolve(h.result, '83333.1', 'bvbrc_minhash_genome') is True
    else:
        records = h.case.store.db.execute('SELECT * FROM runtime_bvbrc_admissions WHERE run_id=? AND receiver_episode_id=?',
            (h.case.run_id, h.parent.episode_id)).fetchall()
        assert len(records) == 1 and records[0]['operation_key'] == h.operation_key
    for reference in references:
        assert owner(h).resolve_received_reference(h.parent, reference, 'execution_result') is True
    owner(h).validate_received_report(h.parent, h.form, h.schema)
    assert h.state() == before


def test_original_root_forward_retains_same_received_values_and_no_scope_grant(received):
    h = received
    h.record_original_admission()
    form, key = h.forward_to_root()
    before = h.state()
    root_owner = owner(h, h.case.root)
    assert root_owner.received_report_facts(h.case.root) == h.host.received_facts(h.case.root, h.schema)
    root_owner.validate_received_report(h.case.root, form, h.schema)
    assert root_owner.received_form_references(h.case.root, form, h.schema, key)
    assert h.state() == before
    other = h.with_contract(h.case.root.path + (('partner_presence_evidence', 'child_9'),),
        h.plain(h.parent.assignment), h.contract)
    assert not any(owner(h, other).received_report_facts(other).values())
    if h.service == 'bvbrc_minhash':
        assert owner(h, other).initial_minhash_information(other) == {'received_minhash_values': []}
        assert owner(h, other).resolve_received_reference(other, '83333.1', 'bvbrc_minhash_genome') is False


@pytest.mark.parametrize('mutation', ('form', 'schema', 'operation', 'receiver', 'frozen_form'))
def test_actual_received_reader_refuses_altered_original_custody(received, mutation):
    h = received
    h.record_original_admission()
    context, form, schema, key = h.parent, deepcopy(h.form), deepcopy(h.schema), h.operation_key
    if mutation == 'form':
        form[next(name for name, value in form.items() if value)] = []
    elif mutation == 'schema':
        schema['description'] = 'Unselected replacement schema'
    elif mutation == 'operation':
        key = key.replace(':1:typed_form', ':01:typed_form')
    elif mutation == 'receiver':
        context = replace(context, episode_id=h.case.root.episode_id)
    else:
        altered = deepcopy(h.facts)
        altered[next(name for name, value in altered.items() if value)] = []
        h.case.store.db.execute('UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?',
            (h.canonical(altered), h.case.run_id, h.result.episode_id))
    before = h.state()
    with pytest.raises((ValueError, TypeError)):
        owner(h, context).received_form_references(context, form, schema, key)
    assert h.state() == before and len(h.calls) == 1


def test_reader_reconstruction_and_original_action_replay_do_not_acquire_again(received, monkeypatch):
    h = received
    h.record_original_admission()
    original = deepcopy(h.host.received_context(h.parent))
    before = h.state()
    authority = module('library/received_api_information/received_api_authority')
    reopened = authority.ReceivedAPIConfiguration.from_record(h.configuration.as_record())
    catalog = reopened.construct(store=h.case.store, run_id=h.case.run_id,
        directory=h.case.directory / 'workflow', tool_registry=h.case.tools, services=h.case.services)
    dependency = catalog.received('partner_presence_evidence', h.parent)
    assert dependency.received_report_facts(h.parent) == h.host.received_facts(h.parent, h.schema)
    assert h.host.received_context(h.parent) == original
    def denied(*args, **kwargs):
        raise AssertionError('Original saved API replay attempted a new acquisition or grade')
    service = h.api.services['received-service']
    monkeypatch.setattr(service, 'invoke', denied)
    operation = ('api.bvbrc.minhash.result' if h.service == 'bvbrc_minhash'
        else module('api_bvbrc').DATA_RESULT_OPERATION)
    actual = asyncio.run(h.api.execute(h.result, operation, {}, f'{h.case.run_id}:{h.result.episode_id}:0'))
    assert actual == h.result_outcome and h.state() == before and len(h.calls) == 1


def test_full_and_partial_registry_outcomes_remain_explicit(received, tmp_path):
    """Retain general-reader conflicts separately; never treat them as success."""
    h = received
    h.record_original_admission()
    h.forward_to_root()
    partial = module('episode_bindings').EpisodeBindingRegistry([binding for binding in h.case.bindings
        if binding.binding_path == 'partner_presence_evidence'
        or binding.binding_path.startswith('hpc_work_planning')
        or binding.binding_path.startswith('partner_presence_evidence/hpc_work_planning')])
    partial.configure_initial_information(h.case.catalog, module('annotation_initial_information').initial_information)
    partial.configure_received_api_information(h.catalog, module('annotation_received_api_information').received_api_reports)
    partial.configure_received_execution_information(h.execution_catalog,
        module('annotation_received_execution_information').received_execution_information)
    assert len(partial._bindings) == 31 and len(h.case.registry._bindings) == 43
    rows = []
    for name, registry in (('full-43', h.case.registry), ('hpc-only-31', partial)):
        for context in (h.parent, h.case.root):
            api = registry._recipient_received_api_reports(context)
            assert api.received_report_facts(context) == h.host.received_facts(context, h.schema)
            for boundary, callback in (
                ('sources', lambda: registry.received_report_sources(context.role, path=context.path)),
                ('facts', lambda: registry.received_report_facts(context)),
                ('initial', lambda: registry.initial_decision_context(context)),
                ('validation', lambda: registry.validate_received_report(context, h.form, h.schema)),
                ('reference', lambda: registry.resolve_received_reference(context,
                    next(row['source_ref'] for value in h.facts.values() for row in value if 'source_ref' in row), 'execution_result'))):
                try:
                    result = {'status': 'returned', 'value': callback()}
                except Exception as error:
                    result = {'status': 'raised', 'type': type(error).__name__, 'message': str(error)}
                rows.append({'tree': name, 'context': context.as_record(), 'boundary': boundary, **result})
    (tmp_path / 'full_registry_received_outcomes.json').write_text(json.dumps({
        'api_dependency_checked': True, 'full_received_path_integration_complete': all(row['status'] == 'returned' for row in rows),
        'boundaries': rows}, indent=2) + '\n')
    # This diagnostic intentionally retains pre-existing general-reader
    # failures. A required integration gate below fails until they are repaired.
    failed = [row for row in rows if row['status'] != 'returned']
    assert not failed, 'full_received_path_still_incomplete_see_full_registry_received_outcomes.json'


def test_actual_runtime_receipt_projection_and_replay_preserve_original_action_credit(received):
    h = received
    before_actions = h.action_state()
    # The real registry is used. Any unrelated uncorrected parent callback
    # failure remains a failure rather than being filtered out by this test.
    references = h.runtime_receive(h.case.registry)
    assert references
    assert set(references) <= set(h.receipts.known(h.parent.episode_id))
    before = h.state()
    assert h.runtime_receive(h.case.registry) == references
    assert h.runtime_receive(h.case.registry, redelivery=True) == references
    assert h.state() == before and h.action_state() == before_actions and len(h.calls) == 1
