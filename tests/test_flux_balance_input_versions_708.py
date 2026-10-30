"""Shared version custody using real Stores/commissions and synthetic metadata.

All model, prior, primary, software and source bytes are synthetic test data.
They are never scientifically decoded or executed. No native solver is run.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import os

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_input_versions import validate_execution_input_versions
from gene_annotation_episode.flux_balance_execution_inputs import FluxBalanceExecutionInputs
from test_flux_balance_operands_694 import (
    selected as operands, artifact, source, version, with_prior,
)
from test_flux_balance_execution_inputs_704 import selected as receiving


pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')


def owner_for(f):
    owner = SimpleNamespace(store=f.store, run_id=f.run_id, directory=f.store.path.parent / 'run708',
        resolve_received_reference=f.access)
    owner.flux_balance_inputs = FluxBalanceExecutionInputs(owner)
    return protections(owner)


def protections(owner):
    for prefix in ('atac', 'chromatin', 'protein'):
        setattr(owner, '_' + prefix + '_reference_access', lambda *_: None)
    return owner


def check(f, *, owner=None, context=None, versions=None, scope=None, assignments=None):
    owner = owner or owner_for(f)
    context = context or f.root
    return validate_execution_input_versions(owner, f.versions if versions is None else versions,
        plain(context.scope) if scope is None else scope, context=context,
        flux_balance_assignments=[f.assignment] if assignments is None else assignments)


def forbid_bytes(monkeypatch, store):
    monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('host read scientific bytes'))


def test_direct_artifact_uses_metadata_without_bytes_grants_or_writes(operands, monkeypatch):
    f = operands
    before = list(f.store.db.iterdump())
    Path(f.path).unlink()
    forbid_bytes(monkeypatch, f.store)
    assert check(f) is None
    assert list(f.store.db.iterdump()) == before
    assert not (f.store.path.parent / 'run708').exists()


@pytest.mark.parametrize('field', ['artifact_ref', 'text_ref', 'request_ref', 'stdout_ref', 'stderr_ref'])
def test_source_field_witness_keeps_primary_hash_and_selected_prior_separate(operands, monkeypatch, field):
    f = operands
    prior, ref = with_prior(f, field=field)
    before = list(f.store.db.iterdump())
    forbid_bytes(monkeypatch, f.store)
    check(f)
    assert f.versions[-1]['reference'] == ref
    assert f.versions[-1]['content_sha256'] == (prior['sha256'] if field == 'artifact_ref' else f.model['sha256'])
    assert list(f.store.db.iterdump()) == before


def test_source_sequence_primary_is_independent_of_selected_prior(operands, monkeypatch):
    f = operands;prior, ref = with_prior(f)
    primary = artifact(f, b'synthetic sequence primary708')
    record = f.store.get(ref);record['sequence_ref'] = primary['artifact_ref']
    f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), ref))
    f.versions[-1]['content_sha256'] = primary['sha256']
    forbid_bytes(monkeypatch, f.store)
    check(f)
    f.versions[-1]['content_sha256'] = prior['sha256']
    with pytest.raises(ValueError, match='flux_balance_input_version_conflict'):
        check(f)


@pytest.mark.parametrize('fault', ['revision', 'content_hash', 'unreceived', 'source_alias', 'artifact_alias'])
def test_invalid_selected_witnesses_fail_without_state_change(operands, monkeypatch, fault):
    f = operands;prior, ref = with_prior(f)
    owner = owner_for(f)
    if fault == 'revision': f.versions[-1]['version'] = 'not-original'
    elif fault == 'content_hash': f.versions[-1]['content_sha256'] = prior['sha256']
    elif fault == 'unreceived':
        f.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?', (ref,))
    else:
        denied = ref if fault == 'source_alias' else prior['artifact_ref']
        owner.resolve_received_reference = lambda context, reference, namespace: False if reference == denied else None
    before = list(f.store.db.iterdump())
    forbid_bytes(monkeypatch, f.store)
    with pytest.raises(ValueError, match='flux_balance_input_'):
        check(f, owner=owner)
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('prefix', ['atac', 'chromatin', 'protein', 'expression_nmf', 'fluorescence', 'flux_balance'])
def test_existing_shared_protected_alias_checks_remain(operands, monkeypatch, prefix):
    f = operands;owner = owner_for(f)
    if prefix in {'expression_nmf', 'fluorescence', 'flux_balance'}:
        setattr(owner, 'native_' + prefix + '_results', object())
    setattr(owner, '_' + prefix + '_reference_access', lambda *_: False)
    forbid_bytes(monkeypatch, f.store)
    with pytest.raises(ValueError): check(f, owner=owner)


@pytest.mark.parametrize('change', ['mutate', 'delete'])
def test_frozen_original_source_is_used_without_current_record_read(receiving, monkeypatch, change):
    f = receiving;context = f.child();f.inputs.initialize(context)
    owner = protections(f.owner)
    if change == 'mutate':
        record = f.store.get(f.source);record['accession'] = 'later source'
        f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), f.source))
    else: f.store.db.execute('DELETE FROM records WHERE id=?', (f.source,))
    original = f.store.get
    def without_source(ref):
        assert ref != f.source, 'frozen shared validator rebound to current source'
        return original(ref)
    monkeypatch.setattr(f.store, 'get', without_source)
    monkeypatch.setattr(f.inputs, 'validate_selected', lambda *_a, **_k: pytest.fail('rebound frozen inputs'))
    forbid_bytes(monkeypatch, f.store)
    before = list(f.store.db.iterdump())
    check(f, owner=owner, context=context)
    assert list(f.store.db.iterdump()) == before


def test_never_initialized_receiving_context_uses_current_admission(receiving, monkeypatch):
    f = receiving;context = f.child(saved=False);owner = protections(f.owner)
    calls = []
    original = f.inputs.validate_selected
    def current(*args, **kwargs):
        calls.append(args[0].episode_id)
        return original(*args, **kwargs)
    monkeypatch.setattr(f.inputs, 'validate_selected', current)
    forbid_bytes(monkeypatch, f.store)
    before = list(f.store.db.iterdump())
    check(f, owner=owner, context=context)
    assert calls == [context.episode_id]
    assert not f.inputs._directory(context).exists()
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('fault', ['receipt_missing', 'descriptor_missing', 'both_missing', 'forged_receipt'])
def test_existing_control_failures_never_rebind_current_sources(receiving, monkeypatch, fault):
    f = receiving;context = f.child();f.inputs.initialize(context);owner = protections(f.owner)
    root = f.inputs._directory(context)
    if fault in {'receipt_missing', 'both_missing'}: (root / 'input-binding.json').unlink()
    if fault in {'descriptor_missing', 'both_missing'}: (root / 'input-binding-file.json').unlink()
    if fault == 'forged_receipt':
        path = root / 'input-binding.json';path.chmod(0o600)
        value = json.loads(path.read_text())
        value['witness_records'][0]['record']['accession'] = 'fabricated'
        path.write_text(canonical(value))
    monkeypatch.setattr(f.inputs, 'validate_selected', lambda *_a, **_k: pytest.fail('rebound missing/forged control'))
    with pytest.raises(ValueError, match='flux_balance_'):
        check(f, owner=owner, context=context)


@pytest.mark.parametrize('fault', ['hash', 'revision', 'order', 'scope'])
def test_frozen_receiving_selection_and_scope_must_be_exact(receiving, fault):
    f = receiving;context = f.child();f.inputs.initialize(context);owner = protections(f.owner)
    versions = deepcopy(f.versions);scope = plain(context.scope)
    if fault == 'hash': versions[0]['content_sha256'] = 'f' * 64
    elif fault == 'revision': versions[0]['version'] = 'another'
    elif fault == 'order': versions = [*versions, deepcopy(versions[0])]
    else:
        span = deepcopy(f.store.coverage(scope['subject_refs'][0])[0]);span['end'] -= 1
        scope['segments'] = [span]
    with pytest.raises(ValueError, match='flux_balance_input_(version|scope)_conflict'):
        check(f, owner=owner, context=context, versions=versions, scope=scope)


def test_unrelated_selected_content_still_reads_generic_primary_bytes(operands, monkeypatch):
    f = operands;owner = owner_for(f)
    unrelated = artifact(f, b'unrelated synthetic primary708')
    ref = source(f, unrelated, primary=unrelated, field='artifact_ref')
    f.receipts.receive(f.root.episode_id, [ref], kind='initial')
    f.versions.append(version(ref, unrelated['sha256']))
    original = f.store.get_artifact;reads = []
    def tracked(reference):
        reads.append(reference)
        return original(reference)
    monkeypatch.setattr(f.store, 'get_artifact', tracked)
    check(f, owner=owner)
    assert reads == [unrelated['artifact_ref']]
    path = f.store.path / 'artifacts' / unrelated['sha256'][:2] / unrelated['sha256']
    path.write_bytes(b'different synthetic bytes with unchanged metadata')
    with pytest.raises(ValueError, match='^artifact_digest_mismatch$'):
        check(f, owner=owner)
    # With no FBA assignment the original generic implementation owns failure.
    path.write_bytes(b'unrelated synthetic primary708')
    with pytest.raises(ValueError, match='execution_input_version_conflict'):
        check(f, owner=owner, versions=[dict(f.versions[-1], content_sha256='f' * 64)], assignments=[])
    assert reads == [unrelated['artifact_ref']] * 3


def test_frozen_unrelated_source_stays_generic_and_uses_current_bytes(receiving, monkeypatch):
    f = receiving;owner = protections(f.owner)
    unrelated = f.records.source(b'synthetic unrelated original708')
    ref = unrelated['source_ref']
    f.records.receipts.receive(f.records.root.episode_id, [ref], kind='initial')
    versions = [*f.versions, version(ref, unrelated['sha256'])]
    launch = plain(f.parent.assignment);launch['immutable_input_versions'] = versions
    parent = f.records.child(f.records.root, 'launch', launch, 1)
    context = f.records.child(parent, 'launch_local', f.assignment, 0)
    frozen = f.inputs.initialize(context)
    assert ref not in [row['reference'] for row in frozen['receipt']['witness_records']]
    original = f.store.get_artifact;reads = []
    def tracked(reference):
        reads.append(reference)
        return original(reference)
    monkeypatch.setattr(f.store, 'get_artifact', tracked)
    check(f, owner=owner, context=context, versions=versions)
    assert reads == [unrelated['artifact_ref']]
    replacement = f.store.artifact(b'synthetic unrelated current708')
    record = f.store.get(ref);record['artifact_ref'] = replacement
    f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), ref))
    with pytest.raises(ValueError, match='execution_input_version_conflict'):
        check(f, owner=owner, context=context, versions=versions)
    assert reads == [unrelated['artifact_ref'], replacement]


def test_current_binding_record_digest_must_still_match(operands, monkeypatch):
    f = operands;_, ref = with_prior(f);owner = owner_for(f)
    original = owner.flux_balance_inputs.validate_selected
    def changed_after_binding(*args, **kwargs):
        binding = original(*args, **kwargs)
        record = f.store.get(ref);record['accession'] = 'changed between binding and consumption'
        f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), ref))
        return binding
    monkeypatch.setattr(owner.flux_balance_inputs, 'validate_selected', changed_after_binding)
    with pytest.raises(ValueError, match='flux_balance_input_witness_record_conflict'):
        check(f, owner=owner)


def test_conflicting_valid_bindings_do_not_choose_a_convenient_record(operands, monkeypatch):
    f = operands;_, ref = with_prior(f);owner = owner_for(f)
    original = owner.flux_balance_inputs.validate_selected;calls = []
    def next_binding(*args, **kwargs):
        if calls:
            record = f.store.get(ref);record['accession'] = 'second authenticated snapshot'
            f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), ref))
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(owner.flux_balance_inputs, 'validate_selected', next_binding)
    with pytest.raises(ValueError, match='flux_balance_input_witness_record_conflict'):
        check(f, owner=owner, assignments=[f.assignment, deepcopy(f.assignment)])
    assert len(calls) == 2


def test_consistent_repeated_bindings_keep_one_selected_identity(operands, monkeypatch):
    f = operands;with_prior(f);forbid_bytes(monkeypatch, f.store)
    before = list(f.store.db.iterdump())
    check(f, assignments=[f.assignment, deepcopy(f.assignment)])
    assert list(f.store.db.iterdump()) == before
