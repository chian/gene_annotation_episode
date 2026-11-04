"""Read-only admission controls over explicit engineered receipt metadata.

These are real Store/receipt/context readers, not native publications or a
claim that an engineered decision container is an executed scientific return.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.protein_structure_action_records import ProteinStructureActionRecords
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from method_loop.identities import EpisodeRef
from test_molecular_sequence_input_bindings import actual_received_input_owner


def _forbidden(*_args, **_kwargs):
    raise AssertionError('receipt admission attempted payload, publication or native work')


@pytest.fixture
def owner(tmp_path):
    with actual_received_input_owner(tmp_path, namespace='source', deliver=False) as value:
        value.records = EpisodeReturnRecords(value.store, value.parent.run_id,
            failure_prefix='return_admission_')
        value.protein = ProteinStructureActionRecords(value.store, value.parent.run_id)
        value.records.authenticate(value.parent)
        yield value


@contextmanager
def _metadata_only(value, monkeypatch):
    before = list(value.store.db.iterdump())
    original = Path.open
    root = value.store.path / 'artifacts'
    def open_metadata(path, *args, **kwargs):
        if path.is_relative_to(root):
            raise AssertionError('receipt admission opened an Artifact body')
        return original(path, *args, **kwargs)
    writes = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE, sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH, sqlite3.SQLITE_REINDEX, sqlite3.SQLITE_ANALYZE}
    with monkeypatch.context() as guard:
        for name in ('get_artifact', 'artifact', 'put', 'commit_reasoning'):
            guard.setattr(value.store, name, _forbidden)
        guard.setattr(Path, 'open', open_metadata)
        guard.setattr(subprocess, 'run', _forbidden)
        guard.setattr(subprocess, 'Popen', _forbidden)
        value.store.db.set_authorizer(lambda operation, *_: sqlite3.SQLITE_DENY
            if operation in writes else sqlite3.SQLITE_OK)
        try:
            yield
        finally:
            value.store.db.set_authorizer(None)
    assert list(value.store.db.iterdump()) == before


def _call(value, index, reports, *, fields=None, response=None, purpose='decision', episode_id=None):
    context = dict(child_reports=deepcopy(reports), **deepcopy(fields or {}))
    request = dict(context=context, schema=dict(type='object', properties={}, required=[], additionalProperties=False))
    value.store.db.execute('INSERT INTO runtime_model_calls VALUES(?,?,?,?,?,?)',
        (value.parent.run_id, episode_id or value.parent.episode_id, index,
            canonical(request), None if response is None else canonical(response), purpose))
    return request


def _receive(value, kind='child_form'):
    value.receipts.receive(value.parent.episode_id, [value.source_ref], kind=kind, source_index=0)


def _read(value, context, cutoff):
    value.records.authenticate(context)
    return value.records.source_admission_before(context, value.source_ref, cutoff)


@pytest.mark.parametrize('inherited', [False, True])
def test_initial_or_frozen_inherited_source_needs_no_own_return_witness(owner, monkeypatch, inherited):
    owner.receipts.receive(owner.parent.episode_id, [owner.source_ref], kind='initial')
    context = owner.child(1) if inherited else owner.parent
    with _metadata_only(owner, monkeypatch):
        result = _read(owner, context, 0)
        legacy = owner.protein._source_at(context, owner.source_ref, 0)
    assert result == legacy == dict(source_ref=owner.source_ref,
        source_sha256=digest(owner.store.get(owner.source_ref)),
        receipt_manifest_sha256=digest(owner.receipts.manifest(context.episode_id)),
        receipt=None, baseline=True, decision_witnesses=[])


def test_old_child_prefix_cannot_gain_a_later_parent_source(owner, monkeypatch):
    old = owner.context
    _receive(owner)
    _call(owner, 0, [dict(form=dict(source_ref=owner.source_ref))], episode_id=old.episode_id)
    new = owner.child(1)
    with _metadata_only(owner, monkeypatch):
        with pytest.raises(ValueError, match='^return_admission_result_not_received$'):
            _read(owner, old, 0)
        result = _read(owner, new, 0)
    assert result['baseline'] is True and result['decision_witnesses'] == []


@pytest.mark.parametrize('kind', ['child_form', 'report_redelivery'])
def test_early_commission_does_not_make_late_own_return_available_at_old_selection(owner, monkeypatch, kind):
    _call(owner, 4, [])
    _receive(owner, kind)
    _call(owner, 5, [dict(form=dict(source_ref=owner.source_ref))])
    with _metadata_only(owner, monkeypatch):
        # The old commission-index predicate alone accepts this late receipt.
        assert owner.records._received_before(owner.parent.episode_id, owner.source_ref, 4) is True
        with pytest.raises(ValueError, match='^return_admission_result_not_received$'):
            _read(owner, owner.parent, 4)
        # The old adapter passed result_not_received to its typed issue
        # constructor, whose unchanged IssueCode rejects that code itself.
        with pytest.raises(ValueError, match='^invalid_schema$') as caught:
            owner.protein._source_at(owner.parent, owner.source_ref, 4)
    assert type(caught.value) is ValueError


@pytest.mark.parametrize('location', ['assignment', 'response', 'later', 'other_episode', 'non_decision'])
def test_only_original_own_decision_child_reports_can_witness_a_return(owner, monkeypatch, location):
    _receive(owner)
    report = [dict(form=dict(source_ref=owner.source_ref))]
    if location == 'assignment': _call(owner, 4, [], fields=dict(assignment=dict(source_ref=owner.source_ref)))
    elif location == 'response': _call(owner, 4, [], response=dict(selection=dict(source_ref=owner.source_ref)))
    elif location == 'later': _call(owner, 5, report)
    elif location == 'other_episode': _call(owner, 4, report, episode_id=owner.context.episode_id)
    else: _call(owner, 4, report, purpose='other')
    with _metadata_only(owner, monkeypatch):
        assert owner.records.decision_witnesses(owner.parent, owner.source_ref, 4) == []
        with pytest.raises(ValueError, match='^return_admission_result_not_received$'):
            _read(owner, owner.parent, 4)


@pytest.mark.parametrize('kind', ['child_form', 'report_redelivery'])
def test_received_return_has_exact_original_decision_and_receipt_identity(owner, monkeypatch, kind):
    _receive(owner, kind)
    report = dict(form=dict(source_ref=owner.source_ref, values=[1, 1.0, True]))
    request = _call(owner, 4, [report])
    receipt = dict(owner.store.db.execute('SELECT receipt_index,receipt_kind,source_index '
        'FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?',
        (owner.parent.run_id, owner.parent.episode_id, owner.source_ref)).fetchone())
    with _metadata_only(owner, monkeypatch):
        result = _read(owner, owner.parent, 4)
        legacy = owner.protein._source_at(owner.parent, owner.source_ref, 4)
        witnesses = owner.records.decision_witnesses(owner.parent, report, 4)
        assert owner.protein._decision_witnesses(owner.parent, report, 4) == witnesses
    assert result == legacy == dict(source_ref=owner.source_ref,
        source_sha256=digest(owner.store.get(owner.source_ref)),
        receipt_manifest_sha256=digest(owner.receipts.manifest(owner.parent.episode_id)),
        receipt=receipt, baseline=False,
        decision_witnesses=[dict(call_index=4, request_sha256=digest(request))])
    assert witnesses == [dict(call_index=4, request_sha256=digest(request))]


@pytest.mark.parametrize('different', [True, 1.0, '1'])
def test_decision_form_witness_keeps_strict_json_primitive_identity(owner, monkeypatch, different):
    actual, changed = dict(native_count=1), dict(native_count=different)
    request = _call(owner, 4, [actual])
    with _metadata_only(owner, monkeypatch):
        assert owner.records.decision_witnesses(owner.parent, actual, 4) == [dict(call_index=4,
            request_sha256=digest(request))]
        assert owner.records.decision_witnesses(owner.parent, changed, 4) == []
        assert owner.protein._decision_witnesses(owner.parent, changed, 4) == []


def test_admission_changes_if_an_original_witness_request_is_tampered(owner, monkeypatch):
    _receive(owner)
    request = _call(owner, 4, [dict(source_ref=owner.source_ref)])
    with _metadata_only(owner, monkeypatch):
        original = _read(owner, owner.parent, 4)
    changed = deepcopy(request)
    changed['context']['new_metadata'] = 'changed'
    owner.store.db.execute('UPDATE runtime_model_calls SET request=? WHERE run_id=? AND episode_id=? AND call_index=4',
        (canonical(changed), owner.parent.run_id, owner.parent.episode_id))
    with _metadata_only(owner, monkeypatch):
        current = _read(owner, owner.parent, 4)
    assert current != original
    assert current['decision_witnesses'] == [dict(call_index=4, request_sha256=digest(changed))]
    assert {key: value for key, value in current.items() if key != 'decision_witnesses'} == {
        key: value for key, value in original.items() if key != 'decision_witnesses'}


@pytest.mark.parametrize('cutoff', [True, -1, 0.0, None])
def test_extracted_guard_preserves_old_protein_invalid_cutoff_issue(owner, monkeypatch, cutoff):
    with _metadata_only(owner, monkeypatch):
        with pytest.raises(ValueError, match='^return_admission_invalid_schema$'):
            owner.records.source_admission_before(owner.parent, owner.source_ref, cutoff)
        with pytest.raises(ProteinStructureOperandError) as caught:
            owner.protein._source_at(owner.parent, owner.source_ref, cutoff)
    assert caught.value.issue['code'] == 'invalid_schema'
    assert caught.value.issue['stage'] == 'authority' and caught.value.issue['field'] == 'receipt'


def test_unrelated_receipt_lineage_error_keeps_the_existing_owner_error(owner, monkeypatch):
    owner.store.db.execute('DELETE FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
        (owner.parent.run_id, owner.parent.episode_id))
    with _metadata_only(owner, monkeypatch):
        with pytest.raises(ValueError, match='^return_admission_receipt_history_unbound$'):
            owner.records.source_admission_before(owner.parent, owner.source_ref, 0)
        with pytest.raises(ProteinStructureOperandError) as caught:
            owner.protein._source_at(owner.parent, owner.source_ref, 0)
    assert caught.value.issue['code'] == 'original_commission_mismatch'


def _returned_file(owner, roots, *, form=None, schema=None, recorded=True, redelivery=False, witnessed=True):
    """Construct an explicit closed-return metadata fixture, not a native result."""
    schema = schema or dict(type='object', properties=dict(handles=dict(type='array',
        items=dict(type='string', format='reference'))), required=['handles'], additionalProperties=False)
    form = deepcopy(form if form is not None else dict(handles=list(roots)))
    store, parent, index = owner.store, owner.parent, 3
    for statement in (
        'CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT,form TEXT,PRIMARY KEY(run_id,episode_id))',
        'CREATE TABLE runtime_report_attempts(run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,'
        'child_episode_id TEXT,contract TEXT,form TEXT,failure TEXT,delivery_ref TEXT,'
        'PRIMARY KEY(run_id,parent_episode_id,decision_index))',
    ): store.db.execute(statement)
    path = (*parent.path, ('results', 'child_3'))
    child_id = EpisodeRef(parent.run_id, path).episode_id
    manifest = owner.receipts.bind(child_id, parent.episode_id)
    contract = deepcopy(plain(parent.request)['report_contract'])
    contract['measurements']['schema'] = deepcopy(schema)
    request = dict(goal={'engineering_fixture': True}, message=dict(scope=owner.scope,
        episode_assignment={}, initial_report={}, knowledge_inheritance=manifest), report_contract=contract)
    child = BindingContext(parent.run_id, child_id, 'results', path, owner.scope, {}, request)
    store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
        (parent.run_id, child_id, canonical(path), canonical(request)))
    selection = dict(kind='episode_child', role='results', scope=owner.scope, assignment={},
        purpose=contract['decision'], schema_json=canonical(schema), initial_report_json='{}',
        goal='Inspect engineered returned metadata')
    outcome = dict(status='completed', result=dict(form=form))
    if recorded: outcome['record_refs'] = list(roots)
    store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)',
        (parent.run_id, parent.episode_id, index, canonical(selection), canonical(outcome)))
    facts = {node['x-source']: deepcopy(form[name]) for name, node in schema['properties'].items() if 'x-source' in node}
    store.db.execute('INSERT INTO runtime_forms VALUES(?,?,?,?)',
        (parent.run_id, child_id, canonical(facts), canonical(form)))
    delivery_ref = 'engineered-file-delivery'
    store.db.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)',
        (parent.run_id, parent.episode_id, index, child_id, canonical(contract),
            None if redelivery else canonical(form), 'engineered-delivery-failure' if redelivery else None, delivery_ref))
    if redelivery:
        index = 4
        response = dict(selection=dict(kind='redeliver_report', delivery_ref=delivery_ref,
            schema_json=canonical(schema), purpose=contract['decision']))
        _call(owner, index, [], response=response)
        store.db.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)',
            (parent.run_id, parent.episode_id, index, child_id, canonical(contract), canonical(form), None, delivery_ref))
    owner.receipts.receive(parent.episode_id, roots,
        kind='report_redelivery' if redelivery else 'child_form', source_index=index)
    cutoff = index + 1
    original = _call(owner, cutoff, [dict(form=form)] if witnessed else [])
    return dict(child=child, form=form, schema=schema, source_index=index, cutoff=cutoff, request=original)


def _file_read(owner, *, namespace='artifact', cutoff, reference=None):
    reference = reference or (owner.source_ref if namespace == 'source' else owner.artifact_ref)
    return owner.records.file_admission_before(owner.parent, reference, namespace, owner.artifact_ref, cutoff)


@pytest.mark.parametrize('namespace', ['artifact', 'source'])
def test_timely_source_report_can_forward_a_file_without_literal_artifact_id(owner, monkeypatch, namespace):
    returned = _returned_file(owner, [owner.source_ref])
    assert owner.artifact_ref not in canonical(returned['form'])
    with _metadata_only(owner, monkeypatch):
        result = _file_read(owner, namespace=namespace, cutoff=returned['cutoff'])
    assert result['selection'] == dict(reference=owner.source_ref if namespace == 'source' else owner.artifact_ref,
        namespace=namespace)
    assert result['baseline'] is False
    assert result['file_receipt']['receipt_kind'] == 'child_form'
    delivery = result['delivery']
    assert delivery['source_index'] == returned['source_index']
    assert delivery['child_episode_id'] == returned['child'].episode_id
    assert delivery['form_sha256'] == digest(returned['form']) and delivery['schema_sha256'] == digest(returned['schema'])
    assert delivery['decision_witnesses'] == [dict(call_index=returned['cutoff'], request_sha256=digest(returned['request']))]
    assert delivery['root_ref'] == owner.source_ref
    assert [row['reference'] for row in delivery['forward_path']] == [owner.source_ref, owner.artifact_ref]
    assert all(row['record_sha256'] == digest(owner.store.get(row['reference'])) for row in delivery['forward_path'])
    assert (result['reference_admission'] is not None) == (namespace == 'source')


def test_timely_material_report_uses_the_same_forward_projection_as_receive(owner, monkeypatch):
    material = owner.store.register_material(source_ref=owner.source_ref, name='Engineered input')
    returned = _returned_file(owner, [material['id']])
    with _metadata_only(owner, monkeypatch):
        assert owner.receipts.forward_references(material) == list(owner.store._refs(material))
        result = _file_read(owner, cutoff=returned['cutoff'])
    assert [row['reference'] for row in result['delivery']['forward_path']] == [material['id'], owner.source_ref, owner.artifact_ref]


def test_direct_returned_file_has_zero_forward_edges(owner, monkeypatch):
    returned = _returned_file(owner, [owner.artifact_ref])
    with _metadata_only(owner, monkeypatch):
        result = _file_read(owner, cutoff=returned['cutoff'])
    assert result['delivery']['root_ref'] == owner.artifact_ref
    assert result['delivery']['forward_path'] == [dict(reference=owner.artifact_ref,
        record_sha256=digest(owner.store.get(owner.artifact_ref)))]


@pytest.mark.parametrize('namespace', ['artifact', 'source'])
def test_late_forwarded_file_cannot_authorize_the_original_selected_action(owner, monkeypatch, namespace):
    returned = _returned_file(owner, [owner.source_ref], witnessed=False)
    _call(owner, returned['cutoff'] + 1, [dict(form=returned['form'])])
    with _metadata_only(owner, monkeypatch):
        assert owner.records._received_before(owner.parent.episode_id, owner.artifact_ref, returned['cutoff']) is True
        with pytest.raises(ValueError, match='^return_admission_(file_not_received|result_not_received)$'):
            _file_read(owner, namespace=namespace, cutoff=returned['cutoff'])


@pytest.mark.parametrize('inherited', [False, True])
def test_initial_and_inherited_file_admission_remain_available_without_form_witness(owner, monkeypatch, inherited):
    owner.receipts.receive(owner.parent.episode_id, [owner.artifact_ref], kind='initial')
    context = owner.child(1) if inherited else owner.parent
    with _metadata_only(owner, monkeypatch):
        result = owner.records.file_admission_before(context, owner.artifact_ref, 'artifact', owner.artifact_ref, 0)
    assert result['baseline'] is True and result['delivery'] is result['file_receipt'] is None


@pytest.mark.parametrize('redelivery', [False, True])
def test_legacy_simple_reference_form_reuses_existing_semantic_projection(owner, monkeypatch, redelivery):
    returned = _returned_file(owner, [owner.source_ref], recorded=False, redelivery=redelivery)
    with _metadata_only(owner, monkeypatch):
        result = _file_read(owner, cutoff=returned['cutoff'])
    assert result['delivery']['root_ref'] == owner.source_ref
    assert result['file_receipt']['receipt_kind'] == ('report_redelivery' if redelivery else 'child_form')


def test_opaque_form_without_recorded_grant_roots_is_controlled_unavailable(owner, monkeypatch):
    schema = dict(type='object', properties=dict(result=dict(type='string', format='identifier',
        **{'x-source': 'engineering_source_hook'})), required=['result'], additionalProperties=False)
    returned = _returned_file(owner, [owner.source_ref], schema=schema,
        form=dict(result=owner.source_ref), recorded=False)
    with _metadata_only(owner, monkeypatch):
        with pytest.raises(ValueError, match='^return_admission_file_admission_projection_unavailable$'):
            _file_read(owner, cutoff=returned['cutoff'])


def test_opaque_form_with_recorded_semantic_roots_keeps_its_original_file_grant(owner, monkeypatch):
    schema = dict(type='object', properties=dict(result=dict(type='string', format='identifier',
        **{'x-source': 'engineering_source_hook'})), required=['result'], additionalProperties=False)
    returned = _returned_file(owner, [owner.source_ref], schema=schema, form=dict(result=owner.source_ref))
    with _metadata_only(owner, monkeypatch):
        result = _file_read(owner, cutoff=returned['cutoff'])
    assert result['delivery']['root_ref'] == owner.source_ref
    assert [row['reference'] for row in result['delivery']['forward_path']] == [owner.source_ref, owner.artifact_ref]


@pytest.mark.parametrize('recorded', [True, False])
def test_identifier_shaped_text_cannot_become_a_recorded_grant_root(owner, monkeypatch, recorded):
    schema = dict(type='object', properties=dict(label=dict(type='string', format='structure_identifier')),
        required=['label'], additionalProperties=False)
    returned = _returned_file(owner, [], schema=schema, form=dict(label=owner.source_ref), recorded=recorded)
    # Adversarial receipt metadata alone cannot invent the missing semantic root.
    owner.receipts.receive(owner.parent.episode_id, [owner.artifact_ref], kind='child_form', source_index=returned['source_index'])
    with _metadata_only(owner, monkeypatch):
        code = 'file_admission_receipt_conflict' if recorded else 'file_admission_projection_unavailable'
        with pytest.raises(ValueError, match='^return_admission_' + code + '$'):
            _file_read(owner, cutoff=returned['cutoff'])


def test_changed_forward_source_metadata_rejects_before_file_bytes(owner, monkeypatch):
    returned = _returned_file(owner, [owner.source_ref])
    source = owner.store.get(owner.source_ref)
    source['provider'] = 'altered immutable source'
    owner.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(source), owner.source_ref))
    with _metadata_only(owner, monkeypatch):
        with pytest.raises(ValueError, match='^return_admission_file_admission_identity_conflict$'):
            _file_read(owner, cutoff=returned['cutoff'])


_PROTECTED = [('ensembl', None), ('public.ncbi.entrez', None), ('public.ncbi.geo', None),
    *[('find_enriched_motifs_with_homer', version) for version in
        ('ordinary_homer_motif_result_v1', 'ordinary_homer_motif_native_capture_v1')],
    ('episode.restriction_input', 'restriction_input_source_v1'),
    ('episode.restriction_result', 'restriction_published_result_v1'),
    *[(provider, 'engineered') for provider in ('analyze_itc_binding_thermodynamics', 'liftover_coordinates',
        'analyze_circular_dichroism_spectra', 'perform_flux_balance_analysis', 'annotate_open_reading_frames',
        'analyze_cas9_mutation_outcomes', 'result.macs2.peaks', 'enrichr')],
    *[('episode.execution_result', version) for version in ('native_infernal_preparation_bundle_v1',
        'native_hmmer_preparation_bundle_v1', 'native_blast_masking_bundle_v1', 'native_blast_utility_bundle_v1',
        'native_blast_database_bundle_v1', 'native_protein_structure_bundle_v1',
        'protein_structure_saved_action_v1', 'native_rna_structure_bundle_v1')]]


@pytest.mark.parametrize('provider,version', _PROTECTED)
def test_all_existing_source_stops_remain_shared_with_receipt_reception(owner, monkeypatch, provider, version):
    source = owner.store.put('source', dict(provider=provider, version=version, accession=None, uri=None,
        artifact_ref=owner.artifact_ref, text_ref=owner.text_ref, request_ref=None, retrieved_at=None), origin='tool')
    before = set(owner.receipts.known(owner.parent.episode_id))
    owner.receipts.receive(owner.parent.episode_id, [source['id']], kind='initial')
    assert set(owner.receipts.known(owner.parent.episode_id)) - before == {source['id']}
    with _metadata_only(owner, monkeypatch):
        assert owner.receipts.forward_references(source) == []


def test_protected_source_does_not_remove_an_explicit_independent_file_root(owner, monkeypatch):
    source = owner.store.put('source', dict(provider='public.ncbi.geo', version=None, accession=None, uri=None,
        artifact_ref=owner.artifact_ref, text_ref=None, request_ref=None, retrieved_at=None), origin='external')
    returned = _returned_file(owner, [source['id'], owner.artifact_ref])
    with _metadata_only(owner, monkeypatch):
        result = _file_read(owner, cutoff=returned['cutoff'])
    assert result['delivery']['root_ref'] == owner.artifact_ref
    assert len(result['delivery']['forward_path']) == 1


def test_protected_forward_edge_cannot_be_invented_by_a_file_receipt_row(owner, monkeypatch):
    source = owner.store.put('source', dict(provider='find_enriched_motifs_with_homer',
        version='ordinary_homer_motif_native_capture_v1', accession=None, uri=None,
        artifact_ref=owner.artifact_ref, text_ref=None, request_ref=None, retrieved_at=None), origin='tool')
    returned = _returned_file(owner, [source['id']])
    with _metadata_only(owner, monkeypatch):
        with pytest.raises(ValueError, match='^return_admission_file_not_received$'):
            _file_read(owner, cutoff=returned['cutoff'])
    owner.receipts.receive(owner.parent.episode_id, [owner.artifact_ref], kind='child_form',
        source_index=returned['source_index'])
    with _metadata_only(owner, monkeypatch):
        with pytest.raises(ValueError, match='^return_admission_file_admission_receipt_conflict$'):
            _file_read(owner, cutoff=returned['cutoff'])


def test_collection_member_projection_keeps_nonadmission_unchanged(owner, monkeypatch):
    record = dict(id='engineered-paged-member', record_type='collection_member', artifact_ref=owner.artifact_ref)
    original = owner.store.get
    monkeypatch.setattr(owner.store, 'get', lambda reference: record if reference == record['id'] else original(reference))
    before = set(owner.receipts.known(owner.parent.episode_id))
    owner.receipts.receive(owner.parent.episode_id, [record['id']], kind='initial')
    assert set(owner.receipts.known(owner.parent.episode_id)) == before
    with _metadata_only(owner, monkeypatch):
        assert owner.receipts.forward_references(record) == []
