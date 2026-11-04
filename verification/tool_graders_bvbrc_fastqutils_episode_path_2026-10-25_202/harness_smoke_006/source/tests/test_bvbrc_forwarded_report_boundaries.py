"""Received-only forwarding with actual executor/admission and selected Journal rows.

These are synthetic host cases, not a Workflow/model/live-service claim. The
separate selected-process tests exercise the actual Workflow boundary.
"""
from copy import deepcopy
import pytest

from gene_annotation_episode.bvbrc_data_schema import json_digest
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.state import Store

from bvbrc_host_fixture import HostFixture, fact_form
from test_api_bvbrc_data_v2 import envelope, request, row_selector


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('forwarding verification attempted network access')
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)


def record_forwarding(fixture, child, form, facts):
    """Record the original selected child closure; host must validate admission."""
    contract = plain(child.request)['report_contract']
    schema = contract['measurements']['schema']
    parent = fixture.parent
    index = int(child.path[-1][1].removeprefix('child_'))
    fixture.journal.save('runtime_forms', {'episode_id': child.episode_id,
        'facts': canonical(facts), 'form': canonical(form)})
    fixture.journal.save('runtime_report_attempts', {
        'parent_episode_id': parent.episode_id, 'decision_index': index,
        'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24],
        'child_episode_id': child.episode_id, 'contract': canonical(contract),
        'form': canonical(form), 'failure': None})
    return fixture.api.record_bvbrc_admission(parent, form, schema,
        f'{fixture.run_id}:{parent.episode_id}:{index}:typed_form')


def test_mixed_received_families_forward_without_expanding_other_source_fields(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        fixture = HostFixture(store, tmp_path/'run', monkeypatch)
        schema = fact_form('execution_bvbrc_counts', 'execution_bvbrc_numeric_rows', 'execution_bvbrc_pages')
        scientific = fixture.context('scientific_process', {}, parent=fixture.parent, schema=schema)
        count_child, count = fixture.acquire(request('genome', mode='count'),
            body=envelope([], total=2), parent=scientific, sources=('execution_bvbrc_counts',))
        fixture.admit(count_child, parent=scientific)
        numeric_child, numeric = fixture.acquire(
            request('genome', fields=['genome_id', 'genome_length']),
            row_selector(numbers=('genome_length',), metadata=('genome_id',)),
            body=envelope([{'genome_id': 'synthetic-genome', 'genome_length': 19}]),
            parent=scientific, sources=('execution_bvbrc_numeric_rows',))
        fixture.admit(numeric_child, parent=scientific)
        host = fixture.api.bvbrc_data
        facts = host.received_facts(scientific, schema)
        counts, = facts['execution_bvbrc_counts']
        measurements, = facts['execution_bvbrc_numeric_rows']
        assert counts['source_ref'] == count['record_refs'][0]
        assert counts['reported_value'] == 2
        assert measurements['source_ref'] == numeric['record_refs'][0]
        assert measurements['measurements'][0]['value'] == 19
        # Both complete sheets contain page facts and the second sheet contains
        # a count of one. None of those facts was received by this child.
        assert facts['execution_bvbrc_pages'] == []
        assert len(facts['execution_bvbrc_counts']) == 1
        form = {name: facts[node['x-source']] for name, node in schema['properties'].items()}
        received = record_forwarding(fixture, scientific, form, facts)
        assert set(received) == {count['record_refs'][0], numeric['record_refs'][0]}
        values = host.received_context(fixture.parent)
        assert {value['fact_source']: value['facts'] for value in values} == facts
        assert [cell['atoms'][0]['string_value'] for value in values for cell in value['cells']
            if cell['field'] == 'genome_id'] == ['synthetic-genome']
        for value in values:
            assert value['admission_key'] == json_digest({
                'run_id': fixture.run_id, 'receiver_episode_id': fixture.parent.episode_id,
                'original_schema': schema, 'form_field': value['form_field'],
                'fact_source': value['fact_source'], 'facts': value['facts']})
        assert len(fixture.calls) == 2
        before = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions')]
        fixture.api = fixture.reopen()
        assert fixture.api.received_bvbrc_context(fixture.parent) == values
        assert before == [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions')]
        assert len(fixture.calls) == 2
        assert store.count('annotation') == store.count('observation') == 0

        forged = deepcopy(form)
        forged['facts_0'][0]['reported_value'] = 999
        with pytest.raises(ReportBoundaryError) as error:
            fixture.api.bvbrc_data.validate_received_report(scientific, forged, schema)
        assert error.value.diagnostic['code'] == 'bvbrc_recorded_facts_mismatch'


def test_global_source_and_received_page_do_not_supply_unreceived_count(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        fixture = HostFixture(store, tmp_path/'run', monkeypatch)
        schema = fact_form('execution_bvbrc_counts')
        scientific = fixture.context('scientific_process', {}, parent=fixture.parent, schema=schema)
        producer, outcome = fixture.acquire(request('genome', mode='count'),
            body=envelope([], total=2), parent=scientific, sources=('execution_bvbrc_pages',))
        host = fixture.api.bvbrc_data
        # Merely sharing scope/store does not deliver the producer's source.
        assert host.received_facts(scientific, schema) == {'execution_bvbrc_counts': []}
        fixture.admit(producer, parent=scientific)
        # Receiving its page (and thereby its actual source identity) still does
        # not deliver the count fact family from the same complete sheet.
        assert host.possession(scientific, outcome['record_refs'][0]) == 'admitted_return'
        assert host.received_facts(scientific, schema) == {'execution_bvbrc_counts': []}
        row = deepcopy(host.facts(producer, schema)['execution_bvbrc_counts'][0])
        with pytest.raises(ReportBoundaryError) as error:
            host.validate_received_report(scientific, {'facts_0': [row]}, schema)
        assert error.value.diagnostic['code'] == 'bvbrc_recorded_facts_mismatch'
        facts = {'execution_bvbrc_counts': []}
        record_forwarding(fixture, scientific, {'facts_0': []}, facts)
        values = host.received_context(fixture.parent)
        assert len(values) == 1 and values[0]['facts'] == values[0]['cells'] == []
        assert not host.resolve_received(fixture.parent, row['population_ref'], 'bvbrc_data_population')
        assert len(fixture.calls) == 1
