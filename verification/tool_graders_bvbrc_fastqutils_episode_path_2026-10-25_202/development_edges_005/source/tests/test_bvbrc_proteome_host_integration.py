"""Real configured host/publication/typed-return integration, controlled transport.

No live service, configured-model presentation or complete Workflow is claimed.
"""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_proteome_returns import FACT_SOURCES
from gene_annotation_episode.bvbrc_proteome_fact_contracts import encode_reference
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components
from gene_annotation_episode.state import Store
from bvbrc_proteome_host_fixture import ProteomeDriver, raw_native, MEAN


@pytest.fixture
def driver(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('controlled proteome test attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    with Store(tmp_path / 'state') as store:
        yield ProteomeDriver(store, tmp_path)


@pytest.mark.parametrize('fmt', ['genome_comparison_json_v1', 'genome_comparison_tsv_v1'])
def test_actual_host_native_numbers_original_submission_and_two_parent_boundaries(driver, fmt):
    d = driver
    fields = __import__('test_bvbrc_proteome_bundle_projection').selected_fields()
    fields['endpoint'] = {**MEAN, 'summary': 'subject_endpoint_difference_summary'}
    d.start(fmt, fields=fields)
    assert d.service.scientific_adapters[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)][0] is adapter
    selected = d.frozen_assignment['selector']['adapter']['parameters']['native_documents'][0]
    assert set(selected) == {'document_id', 'requirement_id', 'role', 'declared_format', 'source_contract'}
    d.acquire_manifest()
    assert d.api._completion(d.context) is None
    body = d.acquire_native()
    assert plain(d.context.assignment) == d.frozen_assignment
    values = body['publication']['adapter_result']['facts']
    assert values['mean']['cell']['value'] == .4375
    assert values['endpoint']['cell']['value'] == .625
    assert values['zero']['cell']['value'] == 0
    assert values['denominator']['cell']['value'] is None
    assert values['ratio']['denominator']['value'] is None
    assert values['inventory_count']['cell']['value'] == 2
    assert values['association']['reference_identifier'] == 'r1'
    assert values['association']['subject_identifier'] == 's1'
    assert values['association']['reference_join_ref'] is None
    assert values['association']['subject_join_ref'] is None
    assert values['selection']['selection'] == 'pass'
    assert d.sheet['input_index_result']['value']['reference_original_index'] == 2
    assert d.sheet['input_index_result']['value']['parameter_source']['kind'] == 'submitted'
    assert len(d.sheet['inventory_results']) == 2
    assert len(d.sheet['feature_results']) == len(d.sheet['genome_results']) == len(d.sheet['sequence_results']) == 1
    assert d.sheet['joins_result']['value']['requested_native_links'] == []
    assert all(row['input_record_count']['value'] is None for row in d.sheet['joins_result']['value']['track_bindings'])
    assert body['bundle']['artifacts'][0]['requirement_ids'] == ['native']
    assert d.sheet['input_resolution'][0]['content']['source_ref'] == d.native['value']['artifact']['source_ref']
    assert d.store.get_artifact(d.native['value']['artifact']['raw_artifact_ref']) == raw_native(fmt)
    assert body['publication']['adapter_result']['status'] == 'partial'
    assert d.api._completion(d.context) is None
    form, _, refs = d.admit_numeric()
    assert set(refs) == {body['source_ref'], d.native['value']['artifact']['source_ref'],
        d.sheet['inventory_results'][0]['value']['source']['content']['source_ref']}
    assert set(d.family.received_report_facts(d.parent)) == set(FACT_SOURCES)
    forwarded, _, more_refs = d.admit_numeric(to_grandparent=True)
    assert forwarded == form and more_refs == refs
    assert d.family.received_report_facts(d.grandparent) == d.family.received_report_facts(d.parent)
    assert d.family.received_report_facts(d.outer_root) == {}  # No requested form means no expansion.
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
    if fmt == 'genome_comparison_json_v1' and os.environ.get('PROTEOME_EXAMPLE_DIRECTORY'):
        directory = Path(os.environ['PROTEOME_EXAMPLE_DIRECTORY'])
        directory.mkdir(parents=True, exist_ok=True)
        for name, value in [('ASSIGNMENT', d.frozen_assignment), ('PUBLICATION', body), ('SHEET', d.sheet),
            ('COMPONENTS', d.components), ('TYPED_FORM', form), ('SUPPLIED_DATA', d.supplied),
            ('NATIVE_ACQUISITION', d.native), ('SUBMISSION', d.handoff),
            ('COMMANDS', d.client.calls), ('RECEIVED', d.family.received_report_facts(d.grandparent))]:
            (directory / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
        (directory / 'native.json').write_bytes(raw_native(fmt))
        (directory / 'submitted_request_wrapper.json').write_bytes(d.store.get_artifact(d.submission_content['artifact_ref']))


def test_narrow_actual_native_request_completes_with_explicit_missing_dependencies(driver):
    d = driver
    d.start(fields={'mean': MEAN})
    d.acquire_manifest()
    body = d.acquire_native()
    saved = body['publication']['adapter_result']
    assert saved['status'] == 'ok' and saved['facts']['mean']['cell']['value'] == .4375
    assert saved['missing_requirements']
    assert body['publication']['requested_form_status'] == 'satisfied'
    proof = d.api._completion(d.context)
    assert proof is not None and d.api.verify_completion(d.context, proof)
    d.admit_numeric()


def forbid_scientific_construction(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved replay repeated scientific construction or acquisition')
    names = {
        'bvbrc_proteome_native': ['parse_genome_comparison'],
        'bvbrc_proteome_inputs': ['index_original_inputs', 'read_protein_fasta', 'read_feature_metadata',
            'read_genome_metadata', 'read_feature_sequences'],
        'bvbrc_proteome_joins': ['build_native_joins'], 'bvbrc_proteome_sheet': ['build_native_sheet'],
        'bvbrc_proteome_calculators': ['calculate_native_components'],
        'bvbrc_proteome_bundle_resolution': ['consume_bundle', 'parse_genome_comparison', 'index_original_inputs',
            'read_protein_fasta', 'read_feature_metadata', 'read_genome_metadata', 'read_feature_sequences',
            'build_native_joins', 'build_native_sheet', 'calculate_native_components'],
        'bvbrc_proteome_bundle_adapter': ['consume_bundle']}
    for module_name, functions in names.items():
        module = importlib.import_module('gene_annotation_episode.' + module_name)
        for name in functions: monkeypatch.setattr(module, name, forbidden)
    return forbidden


def test_saved_replay_and_explicit_recalculation_preserve_original_observations(driver, monkeypatch):
    d = driver
    d.start(fields={'mean': MEAN})
    d.acquire_manifest()
    body = deepcopy(d.acquire_native())
    form, key, refs = d.admit_numeric()
    original = deepcopy(d.last_outcome)
    actions = [dict(row) for row in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')]
    calls = deepcopy(d.client.calls)
    sheet, components = deepcopy(d.sheet), deepcopy(d.components)
    forbidden = forbid_scientific_construction(monkeypatch)
    monkeypatch.setattr(d.client, 'rpc', forbidden)
    monkeypatch.setattr(d.client, 'download', forbidden)
    operation = d.native['value']['origin']['operation_key']
    assert d.invoke(d.context, 'download', d.native_args, operation) == original
    assert d.api.read_result(body['source_ref'], d.context.scope) == body
    assert d.family.received_report_facts(d.parent)[FACT_SOURCES[0]] == form['fact0']
    assert d.family.received_form_references(d.parent, form, d.schema, key) == refs
    revised = calculate_native_components(sheet['native_sheet_result']['value'], parameters={
        **sheet['parameters']['calculation_parameters'], 'minimum_identity_fraction': .9})
    assert components['value']['tracks'][0]['selection_counts']['pass']['value'] == 1
    assert revised['value']['tracks'][0]['selection_counts']['pass']['value'] == 0
    assert revised['value']['sheet_sha256'] == components['value']['sheet_sha256']
    assert d.sheet == sheet and d.components == components and d.client.calls == calls
    assert [dict(row) for row in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')] == actions
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('later_kind', ['partial', 'empty'])
def test_latest_recovered_publication_never_revives_old_success(driver, monkeypatch, later_kind):
    """Two explicit overlapping selections; no model scheduling claim."""
    d = driver
    d.start(fields={'mean': MEAN}, supplementary=False)
    d.acquire_manifest()
    args = d.native_arguments()
    _, first_key = d.selection('download', args, context=d.context)
    _, later_key = d.selection('download', args, context=d.context)
    publications = d.api.appservice.publications
    grade = publications._grade
    d.client.body = b'{"genome_names":{},"feature_matches":[]}' if later_kind == 'partial' else raw_native(d.fmt)
    d.client.native_complete = later_kind == 'partial'
    def interrupted(context, inputs, bundle, origin, stamp, *, current_acquisition):
        # Interrupt after the real acquisition and publication inputs are saved,
        # before any scientific construction. Recovery restores the real method.
        if origin['operation_key'] == later_key:
            raise KeyboardInterrupt()
        return grade(context, inputs, bundle, origin, stamp, current_acquisition=current_acquisition)
    monkeypatch.setattr(publications, '_grade', interrupted)
    with pytest.raises(KeyboardInterrupt): d.invoke(d.context, 'download', args, later_key)
    later_directory = d.api._manifest(d.context) / 'actions' / digest(later_key)
    retained = _read(later_directory / 'call_response.json')
    frozen_inputs = _read(later_directory / 'publication_inputs.json')
    assert frozen_inputs['prior_acquisition_receipt_refs'] == [d.manifest['source_ref']]
    monkeypatch.setattr(publications, '_grade', grade)
    d.client.body, d.client.native_complete = raw_native(d.fmt), True
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
    assert publication['completion_proof'] is None
    assert bool(publication['result_record_refs']) is (later_kind == 'partial')
    assert d.api._completion(d.context) is None and not d.api.verify_completion(d.context, proof)
    latest = d.api.facts(d.context, {})[FACT_SOURCES[0]]
    assert latest == [] if later_kind == 'empty' else latest[0]['value']['cell']['value'] is None
    assert _read(later_directory / 'call_response.json') == retained
    assert _read(later_directory / 'publication_inputs.json') == frozen_inputs
    forbid_scientific_construction(monkeypatch)
    assert d.api.read_result(original['source_ref'], d.context.scope) == original
    assert d.family.received_report_facts(d.parent)[FACT_SOURCES[0]] == form['fact0']
    assert d.family.received_form_references(d.parent, form, d.schema, key) == refs
    assert form['fact0'][0]['value']['cell']['value'] == .4375


def test_required_incomplete_transfer_cannot_complete_narrow_request(driver):
    d = driver
    d.start(fields={'mean': MEAN}, supplementary=False)
    d.acquire_manifest()
    args = d.native_arguments()
    d.client.body, d.client.native_complete = raw_native(d.fmt), False
    d.native = d.call('download', args, context=d.context)
    directory = d.api._manifest(d.context) / 'actions' / digest(d.native['value']['origin']['operation_key'])
    publication = _read(directory / 'bundle_publication.json')['value']
    saved = publication['adapter_result']
    assert saved['facts']['mean']['cell']['value'] == .4375
    assert publication['requested_form_status'] == 'partial'
    assert any(row['reason_code'] == 'download_incomplete' for row in publication['missing_requirements'])
    assert d.api._completion(d.context) is None


def test_wrong_manifest_task_never_reaches_scientific_download(driver):
    d = driver
    d.start(fields={'mean': MEAN}, supplementary=False)
    d.acquire_manifest(native_task='other-task')
    args = {'objects': [{'kind': 'manifest_member', 'manifest_receipt_ref': d.manifest['source_ref'], 'output_index': 0}],
        'generation': 0, 'predecessor_receipt_ref': None}
    calls = deepcopy(d.client.calls)
    context, key = d.selection('download_capability', args)
    result = d.invoke(context, 'download_capability', args, key)
    assert result['status'] == 'invalid' and result['feedback']['code'] == 'task_manifest_mismatch'
    assert d.client.calls == calls


def test_actual_typed_boundary_rejects_wrong_owner_source_values_expansion_and_sibling(driver):
    d = driver
    d.start(fields={'mean': MEAN}, supplementary=False)
    d.acquire_manifest()
    d.acquire_native()
    facts = d.family.facts(d.context, {})
    form = {name: facts[node['x-source']] for name, node in d.schema['properties'].items()}
    d.family.validate_received_report(d.context, form, d.schema)
    for key, value in [('run_id', 'wrong-run'), ('episode_id', 'wrong-owner'), ('scope', {}), ('assignment', {})]:
        with pytest.raises(ValueError):
            d.api.proteome_returns.facts(replace(d.context, **{key: value}), d.schema)
    unreceived = d.saved.source(b'controlled source with no received custody')['source_ref']
    for change in ('value', 'source', 'unrequested'):
        altered = deepcopy(form)
        row = altered['fact0'][0]
        if change == 'value': row['value']['cell']['value'] = .9
        elif change == 'source': row['source_ref'] = unreceived
        else:
            extra = deepcopy(row)
            extra['field'] = encode_reference('field', d.sheet['analysis_id'], '/facts/unrequested')
            altered['fact0'].append(extra)
        with pytest.raises(ValueError): d.family.validate_received_report(d.context, altered, d.schema)
    assert not d.api.resolve(d.context, unreceived, 'source')
    sibling = d.saved.child(d.parent, 'results', d.frozen_assignment, 23, schema=d.schema)
    assert not d.family.resolve(sibling, form['fact0'][0]['field'], 'bvbrc_proteome_field')
    with pytest.raises(ValueError): d.family.validate_received_report(sibling, form, d.schema)
    d.admit_numeric()


def test_actual_saved_return_rejects_tampered_retained_bundle_and_sheet_bytes(driver):
    d = driver
    d.start(fields={'mean': MEAN}, supplementary=False)
    d.acquire_manifest()
    body = d.acquire_native()
    publication = body['publication']
    targets = [('membership', publication['bundle_content'], body['bundle']),
        ('source', publication['adapter_result']['sheet_content'], d.sheet),
        ('primary', publication['adapter_result']['sheet_content'], d.sheet),
        ('hash', publication['bundle_content'], body['bundle']),
        ('task', publication['bundle_content'], body['bundle'])]
    for kind, content, original in targets:
        changed = deepcopy(original)
        if kind == 'membership': changed['artifacts'][0]['requirement_ids'] = ['other']
        elif kind == 'source': changed['input_resolution'][0]['content']['source_ref'] = 'other'
        elif kind == 'primary': changed['native_sheet_result']['value']['primary_source_ref'] = 'other'
        elif kind == 'hash': changed['artifacts'][0]['sha256'] = '0' * 64
        else: changed['original_task']['task_id'] = 'other-task'
        sha = content['sha256']
        path = d.store.path / 'artifacts' / sha[:2] / sha
        retained = path.read_bytes()
        try:
            path.write_text(json.dumps(changed))
            with pytest.raises(ValueError, match='artifact_digest_mismatch'):
                d.api.proteome_returns.facts(d.context, d.schema)
        finally:
            path.write_bytes(retained)
    assert d.api.proteome_returns.facts(d.context, d.schema)[FACT_SOURCES[0]][0]['value']['cell']['value'] == .4375


def test_later_unrelated_recovered_status_preserves_latest_publication_completion(driver, monkeypatch):
    d = driver
    d.start(fields={'mean': MEAN}, supplementary=False)
    d.acquire_manifest()
    native_args = d.native_arguments()
    _, native_key = d.selection('download', native_args)
    status_args = {'handoff_ref': d.handoff['source_ref']}
    _, status_key = d.selection('status', status_args)
    rpc = d.client.rpc
    d.client.value = {'123': {'id': '123', 'application_id': 'GenomeComparison', 'state_code': 'C'}}
    def interrupted(request):
        error = KeyboardInterrupt()
        error.snapshot = rpc(request)
        raise error
    monkeypatch.setattr(d.client, 'rpc', interrupted)
    with pytest.raises(KeyboardInterrupt): d.invoke(d.context, 'status', status_args, status_key)
    monkeypatch.setattr(d.client, 'rpc', rpc)
    d.client.body = raw_native(d.fmt)
    original = d.invoke(d.context, 'download', native_args, native_key)
    assert original['status'] == 'completed'
    proof = d.api._completion(d.context)
    calls = deepcopy(d.client.calls)
    status = d.invoke(d.context, 'status', status_args, status_key)
    assert status['status'] == 'completed' and 'publication_ref' not in status['result']
    assert d.client.calls == calls and d.api._completion(d.context) == proof
