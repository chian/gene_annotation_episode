"""Selected v2 downloads and authenticated publications, controlled transport.

The real host, receipt custody, provider, immutable contents and return binder run.
The Journal actions and public native bytes are fixtures, not a live service job
or a shared method_loop execution.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode.bvbrc_appservice_publication import AppServicePublications
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.state import Store
from test_bvbrc_proteome_directional import native
from test_bvbrc_proteome_directional_projection import forbid_construction, selector
from test_bvbrc_proteome_directional_returns import DirectionalDriver


COUNT = selector('directional_count', 'report', 'displayed_query_count')
SOURCE = 'bvbrc_proteome_directional_counts'


@pytest.fixture
def driver(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('controlled publication test attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    with Store(tmp_path / 'state') as store:
        yield DirectionalDriver(store, tmp_path)


def start(d, *, missing_optional=False):
    d.start(key='2011', fields={'count': COUNT}, sources=(SOURCE,))
    if missing_optional:
        selected = deepcopy(d.selected)
        extra = deepcopy(selected['adapter']['parameters']['directional_documents'][0])
        extra.update(document_id='optional-absent', report_key='optional-absent', requirement_id='optional-absent')
        selected['adapter']['parameters']['directional_documents'].append(extra)
        selected['requirements'].append(dict(requirement_id='optional-absent', role=extra['role'], required=False,
            declared_format=deepcopy(extra['declared_format']), producer_rule_evidence=None, exact_object=None))
        # Freeze the additional optional selection in a real new child commission
        # before its first acquisition. The earlier unexecuted child stays intact.
        d.context = d.saved.child(d.parent, 'results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': d.handoff['source_ref'], 'selector': selected}, 23, schema=d.schema)
        d.selected = selected
        d.api.initialize(d.context)
    d.acquire_manifest()


def action_directory(d, operation_key=None):
    key = operation_key or d.native['value']['origin']['operation_key']
    return d.api._manifest(d.context) / 'actions' / digest(key)


def save_forged_publication(d, publication, outcome):
    """Deliberate test corruption preserving every outer authentication link."""
    content = d.api.appservice.publications._put_content(publication['origin'], 'bundle_publication',
        publication, d.native['value']['snapshot']['retrieved_at'])
    outcome['result']['publication_ref'] = content['source_ref']
    outcome['result']['result_record_refs'] = deepcopy(publication['result_record_refs'])
    directory = action_directory(d)
    (directory / 'bundle_publication.json').write_text(canonical({'content': content, 'value': publication}) + '\n')
    (directory / 'outcome.json').write_text(canonical(outcome) + '\n')
    # Without this deliberately forged outer action copy, receipt authentication
    # would already reject and never reach the v2 publication relationships.
    d.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
        (canonical(outcome), d.context.run_id, d.context.episode_id, int(publication['origin']['operation_key'].rsplit(':', 1)[1])))


def test_exact_narrow_request_completes_with_unrelated_retained_missing_inputs(driver):
    d = driver
    start(d, missing_optional=True)
    body = d.acquire_native()
    saved = body['publication']['adapter_result']
    assert saved['status'] == 'ok'
    assert saved['facts']['count']['cell']['value'] == 1
    assert saved['missing_requirements']
    assert body['bundle']['status'] == 'ok'
    assert body['status'] == 'completed'
    assert body['publication']['requested_form_status'] == 'satisfied'
    proof = d.api._completion(d.context)
    assert proof is not None and d.api.verify_completion(d.context, proof)
    d.admit_numeric()
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('malformed', [False, True])
def test_all_incomplete_bytes_publish_real_saved_sheet_without_completing(driver, malformed):
    d = driver
    start(d)
    d.client.native_complete = False
    body = d.acquire_native(raw=b'not a native report\n' if malformed else None)
    publication = body['publication']
    assert body['bundle']['artifacts']
    assert all(not row['transfer']['body_complete'] and row['transfer']['object_complete'] != 'yes'
        for row in body['bundle']['artifacts'])
    assert body['bundle']['status'] == 'partial'
    assert publication['adapter_result']['status'] in {'ok', 'partial'}
    assert publication['adapter_result']['sheet_content'] is not None
    assert publication['result_record_refs'] == [body['source_ref']]
    assert body['status'] == publication['requested_form_status'] == 'partial'
    assert publication['completion_proof'] is None and d.api._completion(d.context) is None
    assert any(row['reason_code'] == 'download_incomplete' for row in publication['missing_requirements'])
    if not malformed:
        assert publication['adapter_result']['facts']['count']['cell']['value'] == 1
    assert d.api.read_result(body['source_ref'], d.context.scope) == body
    d.admit_numeric()
    assert d.family.received_report_facts(d.parent)[SOURCE]
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_result_reference_exception_is_exactly_scoped_to_saved_v2_sheet():
    inputs = {'adapter': {'adapter_id': 'bvbrc_proteome', 'adapter_version': '2'}}
    bundle = {'artifacts': [{'transfer': {'body_complete': False, 'object_complete': 'no'}}]}
    content = {'source_ref': 'actual-bundle-source'}
    result = dict(adapter_id='bvbrc_proteome', adapter_version='2', status='partial', sheet_content={'source_ref': 'sheet'})
    refs = AppServicePublications._result_references
    assert refs(inputs, bundle, content, result) == ['actual-bundle-source']
    for changed in (None, {**result, 'status': 'invalid'}, {**result, 'status': 'failed'},
                    {**result, 'sheet_content': None}, {**result, 'adapter_version': '1'},
                    {**result, 'adapter_id': 'other'}):
        assert refs(inputs, bundle, content, changed) == []
    assert refs({'adapter': None}, bundle, content, result) == []
    assert refs({'adapter': {**inputs['adapter'], 'adapter_version': '1'}}, bundle, content, result) == []
    bundle['artifacts'][0]['transfer'] = {'body_complete': True, 'object_complete': 'yes'}
    assert refs({'adapter': None}, bundle, content, None) == ['actual-bundle-source']


def test_catalog_and_publication_cross_validate_frozen_v2_requirement_meaning(driver, monkeypatch):
    d = driver
    start(d)
    body = d.acquire_native()
    altered = deepcopy(d.selected)
    altered['requirements'][0]['declared_format']['version'] = '2.2.21'
    with pytest.raises(ValueError):
        d.service.result_catalog(d.query, altered)
    inputs = deepcopy(body['publication_inputs'])
    inputs['selector'] = altered
    def forbidden(*args, **kwargs):
        pytest.fail('selector mismatch reached provider construction')
    monkeypatch.setattr(adapter, 'consume_bundle', forbidden)
    with pytest.raises(ValueError):
        d.api.appservice.publications._grade(d.context, inputs, body['bundle'], body['publication']['origin'],
            d.native['value']['snapshot']['retrieved_at'], current_acquisition=d.native)


@pytest.mark.parametrize('mutation', ['extra_result_ref', 'missing_result_ref', 'missing_proof', 'wrong_outcome'])
def test_authenticated_read_rejects_result_ref_proof_and_outcome_changes(driver, mutation):
    d = driver
    start(d)
    body = d.acquire_native()
    directory = action_directory(d)
    retained = _read(directory / 'bundle_publication.json')
    outcome = _read(directory / 'outcome.json')
    publication = deepcopy(retained['value'])
    if mutation == 'extra_result_ref': publication['result_record_refs'].append(d.native['source_ref'])
    elif mutation == 'missing_result_ref': publication['result_record_refs'] = []
    elif mutation == 'missing_proof': publication['completion_proof'] = None
    else: outcome['status'] = 'partial'
    # Save an actual Store content object so rejection tests the authenticated
    # relationship checks after byte/origin loading, not only a changed digest.
    save_forged_publication(d, publication, outcome)
    expected = {'extra_result_ref': 'appservice_bundle_result_references_conflict',
        'missing_result_ref': 'not_an_appservice_acquired_result',
        'missing_proof': 'appservice_bundle_completion_conflict', 'wrong_outcome': 'appservice_bundle_completion_conflict'}[mutation]
    with pytest.raises(ValueError, match=expected):
        d.api.read_result(body['source_ref'], d.context.scope)


def test_partial_publication_rejects_fabricated_completion_proof(driver):
    d = driver
    start(d)
    d.client.native_complete = False
    body = d.acquire_native()
    publication = deepcopy(body['publication'])
    publication['completion_proof'] = {'version': 'practical_completion_v1', 'run_id': d.context.run_id,
        'episode_id': d.context.episode_id, 'assignment_sha256': digest(d.context.assignment),
        'endpoint': 'completed_job_outputs', 'operation_key': publication['origin']['operation_key'],
        'receipt_sha256': digest(publication), 'validation_keys': ['requested_service_result']}
    directory = action_directory(d)
    outcome = _read(directory / 'outcome.json')
    save_forged_publication(d, publication, outcome)
    with pytest.raises(ValueError, match='completion_conflict'):
        d.api.read_result(body['source_ref'], d.context.scope)


def test_latest_partial_supersedes_completion_but_historical_admission_survives(driver, monkeypatch):
    d = driver
    start(d)
    args = d.native_arguments()
    _, first_key = d.selection('download', args, context=d.context)
    _, later_key = d.selection('download', args, context=d.context)
    publications = d.api.appservice.publications
    grade = publications._grade
    d.client.body, d.client.native_complete = b'not a native report\n', False
    def interrupted(context, inputs, bundle, origin, stamp, *, current_acquisition):
        if origin['operation_key'] == later_key:
            raise KeyboardInterrupt()
        return grade(context, inputs, bundle, origin, stamp, current_acquisition=current_acquisition)
    monkeypatch.setattr(publications, '_grade', interrupted)
    with pytest.raises(KeyboardInterrupt): d.invoke(d.context, 'download', args, later_key)
    later_directory = action_directory(d, later_key)
    retained = _read(later_directory / 'call_response.json')
    frozen_inputs = _read(later_directory / 'publication_inputs.json')
    assert frozen_inputs['prior_acquisition_receipt_refs'] == [d.manifest['source_ref']]
    monkeypatch.setattr(publications, '_grade', grade)
    d.client.body, d.client.native_complete = native('2011'), True
    first = d.invoke(d.context, 'download', args, first_key)
    assert first['status'] == 'completed'
    d.native = d.records.read(first['result']['support_receipt_ref'])
    original = deepcopy(d.publication())
    form, key, refs = d.admit_numeric()
    proof = d.api._completion(d.context)
    assert proof['operation_key'] == first_key
    calls = deepcopy(d.client.calls)
    later = d.invoke(d.context, 'download', args, later_key)
    assert later['status'] == 'partial' and d.client.calls == calls
    publication = _read(later_directory / 'bundle_publication.json')['value']
    assert publication['completion_proof'] is None and publication['result_record_refs']
    assert d.api._completion(d.context) is None and not d.api.verify_completion(d.context, proof)
    latest = d.api.facts(d.context, {})[SOURCE]
    assert latest and latest[0]['source_ref'] != form['fact0'][0]['source_ref']
    assert _read(later_directory / 'call_response.json') == retained
    assert _read(later_directory / 'publication_inputs.json') == frozen_inputs
    forbidden = forbid_construction(monkeypatch)
    monkeypatch.setattr(d.client, 'rpc', forbidden)
    monkeypatch.setattr(d.client, 'download', forbidden)
    actions = [dict(row) for row in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')]
    assert d.api.read_result(original['source_ref'], d.context.scope) == original
    assert d.family.received_report_facts(d.parent)[SOURCE] == form['fact0']
    assert d.family.received_form_references(d.parent, form, d.schema, key) == refs
    assert form['fact0'][0]['value']['cell']['value'] == 1
    assert d.invoke(d.context, 'download', args, later_key) == later
    assert [dict(row) for row in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')] == actions

