"""Metadata privacy and real receipt controls, not disorder-worker evidence.

The public packet contains literal retained231 values. ToolOperation candidate
rows are explicitly engineered to exercise classification; they establish no
native production, numerical execution, model delivery or producer custody.
"""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from gene_annotation_episode import protein_disorder_result_contracts as contracts
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
from test_molecular_sequence_input_bindings import actual_received_input_owner
from test_protein_disorder_result_contracts import prepared


@contextmanager
def publication(tmp_path, *, status='completed', deliver=True, explicit_files=()):
    with actual_received_input_owner(tmp_path, deliver=False) as value:
        store = value.store
        store.db.execute('CREATE TABLE tool_operations(operation_key TEXT PRIMARY KEY,id TEXT,name TEXT,'
            'arguments TEXT,scope TEXT,result TEXT)')
        arguments, sheet, components = prepared()
        packet = contracts.ordinary_disorder_packet(arguments=arguments, sheet=sheet, components=components)
        assert packet['version'] == 'ordinary_protein_disorder_values_v1'
        primary = store.artifact(canonical(packet), 'application/json')
        private = {role: store.artifact(('engineering private ' + role).encode(), 'application/octet-stream')
            for role in ('native_response', 'transport', 'sheet', 'components', 'control', 'diagnostic')}
        original_file = store.artifact(b'original separately admitted operand', 'application/octet-stream')
        original = store.put('source', dict(provider='engineering_original_operand', accession=None,
            uri=None, artifact_ref=original_file, text_ref=None, request_ref=None, version=None,
            retrieved_at=None), origin='tool')
        source = store.put('source', dict(provider=contracts.TOOL, accession=None, uri=None,
            artifact_ref=primary, text_ref=None, request_ref=private['control'],
            auxiliary_artifact_refs=[private[role] for role in ('native_response', 'transport', 'sheet', 'components')],
            parent_source_refs=[original['id']], version=contracts.SOURCE_VERSION, retrieved_at=None), origin='tool')
        public = contracts.project_ordinary_disorder_return(packet, source['id'])
        key = 'engineering-disorder-metadata-candidate'
        operation = identity('operation', dict(key=key, name=contracts.TOOL, arguments=arguments))
        outcome = dict(status=status, operation_ref=operation, record_refs=[source['id']],
            changed_record_refs=[source['id']], result=public, feedback=None)
        store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)', (key, operation,
            contracts.TOOL, canonical(arguments), canonical(value.scope), canonical(outcome)))
        failed = dict(status='failed', operation_ref='engineering-failure', record_refs=[], result=None,
            feedback=dict(diagnostic_ref=private['diagnostic']))
        store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)', (key + ':failed',
            'engineering-failure', contracts.TOOL, '{}', canonical(value.scope), canonical(failed)))
        value.refs = dict(source=source['id'], packet=primary, original_source=original['id'],
            original_file=original_file, **private)
        value.public, value.source = public, source
        if deliver:
            value.receipts.receive(value.parent.episode_id, [source['id']], kind='initial')
        if explicit_files:
            value.receipts.receive(value.parent.episode_id, [value.refs[role] for role in explicit_files], kind='initial')
        value.context = value.child(1)
        yield value


def verdict(value, role, *, context=None, private_only=False, providers=None):
    return molecular_reference_restriction(value.store, value.context if context is None else context,
        value.refs[role], 'source' if role.endswith('source') else 'artifact',
        private_only=private_only, providers=providers)


@pytest.mark.parametrize('status', ['completed', 'partial'])
def test_disorder_source_receipt_carries_only_top_source_not_private_files_or_original_mappings(tmp_path, status):
    with publication(tmp_path, status=status) as value:
        assert value.public['version'] == 'ordinary_protein_disorder_values_v1'
        assert value.public['source_ref'] == value.refs['source']
        assert value.receipts.forward_references(value.source) == []
        assert set(value.receipts.known(value.context.episode_id)) == {value.refs['source']}
        assert verdict(value, 'source') is True
        assert verdict(value, 'packet') is False
        for role in ('native_response', 'transport', 'sheet', 'components', 'control', 'diagnostic'):
            assert verdict(value, role) is False
        assert verdict(value, 'original_source') is None
        assert verdict(value, 'original_file') is None


def test_explicit_private_file_receipts_do_not_override_controls_but_public_packet_file_remains_separate(tmp_path):
    roles = ('packet', 'native_response', 'transport', 'sheet', 'components', 'control', 'diagnostic', 'original_file')
    with publication(tmp_path, explicit_files=roles) as value:
        known = set(value.receipts.known(value.context.episode_id))
        assert all(value.refs[role] in known for role in roles)
        assert verdict(value, 'packet') is True
        for role in ('native_response', 'transport', 'sheet', 'components', 'control', 'diagnostic'):
            assert verdict(value, role) is False
        assert verdict(value, 'original_file') is None
        assert molecular_reference_restriction(value.store, value.context, value.refs['source'], 'artifact') is False
        assert molecular_reference_restriction(value.store, value.context, value.refs['packet'], 'source') is False


def test_unreceived_disorder_source_and_packet_are_denied_without_implicit_custody(tmp_path):
    with publication(tmp_path, deliver=False) as value:
        assert set(value.receipts.known(value.context.episode_id)) == set()
        assert verdict(value, 'source') is False and verdict(value, 'packet') is False
        assert molecular_reference_restriction(value.store, None, value.refs['source'], 'source') is False
        assert verdict(value, 'control', private_only=True) is False
        assert verdict(value, 'source', private_only=True) is None


def test_late_parent_source_delivery_does_not_retroactively_enter_an_older_child_prefix(tmp_path):
    with publication(tmp_path, deliver=False) as value:
        earlier = value.context
        value.receipts.receive(value.parent.episode_id, [value.refs['source']], kind='initial')
        later = value.child(2)
        assert verdict(value, 'source', context=earlier) is False
        assert verdict(value, 'source', context=later) is True
        assert set(value.receipts.known(later.episode_id)) == {value.refs['source']}
        assert verdict(value, 'packet', context=later) is False


@pytest.mark.parametrize('change', ['scope', 'request', 'run'])
def test_disorder_public_source_requires_the_actual_saved_receiving_context(tmp_path, change):
    with publication(tmp_path) as value:
        context = value.context
        if change == 'scope':
            context = replace(context, scope={'subject_refs': []})
        elif change == 'request':
            request = plain(context.request)
            request['message']['episode_assignment'] = {'changed': True}
            context = replace(context, request=request, assignment=request['message']['episode_assignment'])
        else:
            context = replace(context, run_id='unreceived-run')
        assert verdict(value, 'source', context=context) is False


def test_disorder_privacy_is_metadata_only_and_does_not_forward_grant_or_read_payloads(tmp_path, monkeypatch):
    with publication(tmp_path) as value:
        def rows():
            names = [row[0] for row in value.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name: sorted([tuple(row) for row in value.store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')], key=repr)
                for name in names}
        before, changes = rows(), value.store.db.total_changes
        known = set(value.receipts.known(value.context.episode_id))
        def forbidden(*args, **kwargs):
            pytest.fail('disorder reference policy read private bytes, traversed mappings or changed custody')
        monkeypatch.setattr(value.store, 'get_artifact', forbidden)
        monkeypatch.setattr(value.store, 'artifact', forbidden)
        monkeypatch.setattr(value.store, '_refs', forbidden)
        monkeypatch.setattr(Path, 'open', forbidden)
        assert value.receipts.forward_references(value.source) == []
        for role in ('source', 'packet', 'native_response', 'transport', 'sheet', 'components', 'control', 'diagnostic'):
            verdict(value, role)
            verdict(value, role, private_only=True)
        assert rows() == before and value.store.db.total_changes == changes
        assert set(value.receipts.known(value.context.episode_id)) == known


def test_disorder_registration_does_not_classify_other_provider_subsets(tmp_path):
    with publication(tmp_path) as value:
        assert verdict(value, 'control', providers=('analyze_arsenic_speciation_hplc_icpms',)) is None
        assert verdict(value, 'control', providers=(contracts.TOOL,)) is False
        assert verdict(value, 'source', providers=()) is None
