"""Received-file custody with real Store/receipt primitives; no scientific run.

All model/source bytes and software identities below are explicitly synthetic
metadata fixtures. They are never parsed as biology or executed.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.flux_balance_operands import (
    bind_flux_balance_job_inputs, validate_flux_balance_input_binding,
    freeze_flux_balance_input_binding, validate_flux_balance_input_binding_receipt,
)
from gene_annotation_episode.native_flux_balance_contracts import (
    flux_balance_environment, SOURCE_FUNCTION_SHA256, DRIVER_MODULE, RUN_PLAN_FILENAME,
)
from gene_annotation_episode.state import Store


pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')


def software():
    pin = lambda path: {'path': path, 'sha256': 'a' * 64, 'size_bytes': 1}
    return {'version': 'fba_software_v1', 'python': pin('/selected/python'), 'python_version': 'synthetic',
        'python_home': '/selected/runtime', 'module_root': '/selected/module',
        'dependency_roots': ['/selected/dependencies'],
        'implementation_files': [pin('/selected/module/gene_annotation_episode/' + name) for name in (
            '__init__.py', 'execution_contracts.py', 'flux_balance_contracts.py', 'native_flux_balance_contracts.py',
            'native_flux_balance_storage.py', 'native_flux_balance_cobra_glpk.py', 'native_flux_balance_driver.py')],
        'runtime_files': [pin('/selected/runtime/lib/os.py'), pin('/selected/dependencies/example.py')],
        'solver_runtime_files': [pin('/selected/libglpk.so')],
        'distributions': [{'name': name, 'version': version} for name, version in (
            ('cobra', '0.32.1'), ('optlang', '1.9.1'), ('swiglpk', '5.0.13'), ('python-libsbml', '5.21.2'))],
        'solver_interface': 'optlang.glpk_interface'}


def bound(value, file=None, pointer=''):
    return {'kind': 'finite', 'value': value, 'native_token': str(value), 'float_hex': float(value).hex(),
            'source': None if file is None else {'file': deepcopy(file), 'pointer': pointer}}


def new_context(f, parent=None):
    path = (('annotation', 'root'),) if parent is None else (*parent.path, ('launch', 'child_0'))
    eid = EpisodeRef(f.run_id, path).episode_id
    manifest = f.receipts.bind(eid, None if parent is None else parent.episode_id)
    request = {'message': {'scope': f.scope, 'episode_assignment': {}, 'knowledge_inheritance': manifest}}
    context = BindingContext(f.run_id, eid, path[-1][0], path, f.scope, {}, request)
    f.journal.save('runtime_episodes', {'episode_id': eid, 'path': canonical(path), 'request': canonical(request),
        'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    return context


def artifact(f, raw, format='json'):
    reference = f.store.artifact(raw)
    return {'artifact_ref': reference, 'sha256': reference[9:], 'size_bytes': len(raw), 'format': format}


def version(reference, sha=None):
    return {'reference': reference, 'version': None, 'content_sha256': sha}


def source(f, file, *, primary=None, field='request_ref'):
    record = {'provider': 'fixture.received', 'accession': 'synthetic694', 'uri': None,
        'artifact_ref': (primary or f.model)['artifact_ref'], 'text_ref': None, 'request_ref': None,
        'version': None, 'retrieved_at': None}
    record[field] = file['artifact_ref']
    return f.store.put('source', record, origin='tool', scope=f.scope)['id']


@pytest.fixture
def selected(tmp_path):
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ACGT', molecule='dna')
        f = SimpleNamespace(store=store, run_id='fba694-custody', scope=store.validate_scope())
        f.journal, f.receipts = Journal(store, f.run_id), EpisodeReceipts(store, f.run_id)
        f.root = new_context(f)
        f.model = artifact(f, b'not parsed synthetic model', 'cobra_json')
        f.path = str(store.path / 'artifacts' / f.model['sha256'][:2] / f.model['sha256'])
        f.receipts.receive(f.root.episode_id, [f.model['artifact_ref']], kind='initial')
        sw = software()
        f.assignment = {'requested_job': {'argv': [sw['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME],
            'environment': flux_balance_environment(sw, attempt_directory=str(tmp_path / 'launch/flux-balance-attempt'),
                                                   lifecycle_directory=str(tmp_path / 'launch')),
            'native_flux_balance': {'version': 'native_flux_balance_job_v1', 'operation': 'perform_flux_balance_analysis',
                'mode': 'steady_state_linear_fba', 'source_alias': 'biomni.tool.systems_biology.perform_flux_balance_analysis',
                'source_function_sha256': SOURCE_FUNCTION_SHA256,
                'model_input': {'file': {'path': f.path, 'sha256': f.model['sha256'], 'size_bytes': f.model['size_bytes']},
                    'artifact_ref': f.model['artifact_ref'], 'format': 'cobra_json', 'original_loader_selection': 'json_file',
                    'repository_identifier': None, 'acquisition_receipt_file': None}, 'constraints': None,
                'objective': {'kind': 'model_default', 'reaction_id': None},
                'solver_options': {'feasibility_tolerance': None, 'optimality_tolerance': None, 'integrality_tolerance': None},
                'software': sw, 'output_prefix': 'outputs', 'flux_output_name': 'flux.csv'}}}
        f.versions = [version(f.model['artifact_ref'], f.model['sha256'])]
        f.calls = []
        f.access = lambda context, reference, namespace: f.calls.append((reference, namespace))
        yield f


def bind(f, context=None, assignment=None, versions=None):
    return bind_flux_balance_job_inputs(f.store, context or f.root, assignment or f.assignment,
        input_versions=f.versions if versions is None else versions, reference_access=f.access)


def checked_receipt(f, receipt, context=None):
    return validate_flux_balance_input_binding_receipt(f.store, receipt, context=context or f.root,
        assignment=f.assignment, input_versions=f.versions, reference_access=f.access)


def with_prior(f, *, field='request_ref', duplicate_uses=True):
    prior = artifact(f, b'{"bounds":{"A/B": 0}}', 'json')
    ref = source(f, prior, field=field)
    f.receipts.receive(f.root.episode_id, [ref], kind='initial')
    f.versions.append(version(ref, f.model['sha256'] if field != 'artifact_ref' else prior['sha256']))
    job = f.assignment['requested_job']['native_flux_balance']
    job['model_input']['acquisition_receipt_file'] = deepcopy(prior)
    if duplicate_uses:
        job['constraints'] = [{'reaction_id': 'R', 'lower': bound(0, prior, '/bounds/A~1B'),
                               'upper': bound(10, prior, '/bounds/A~1B')}]
    return prior, ref


def test_direct_binding_is_detached_read_only_and_preserves_full_selection(selected, monkeypatch):
    f = selected
    before = list(f.store.db.iterdump())
    original = deepcopy(f.assignment)
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('host read scientific bytes'))
    result = bind(f)
    assert result['model']['file'] == f.model
    assert result['model']['uses'] == [{'request_pointer': '/native_flux_balance/model_input', 'source_pointer': None}]
    assert result['input_versions'] == f.versions
    assert result['request_sha256'] == digest(f.root.request)
    assert result['assignment_sha256'] == digest(f.assignment)
    assert result['model']['witnesses'][0]['artifact_field'] is None
    assert validate_flux_balance_input_binding(f.store, result, context=f.root, assignment=f.assignment,
        input_versions=f.versions, reference_access=f.access) == result
    assert list(f.store.db.iterdump()) == before and f.assignment == original
    result['input_versions'][0]['reference'] = 'changed'
    assert f.versions[0]['reference'] == f.model['artifact_ref']


@pytest.mark.parametrize('field', ['artifact_ref', 'text_ref', 'request_ref', 'stdout_ref', 'stderr_ref'])
def test_declared_source_fields_and_multiple_uses_preserve_primary_hash(selected, field, monkeypatch):
    f = selected
    prior, reference = with_prior(f, field=field)
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('host read bytes'))
    row, = bind(f)['prior_sources']
    assert row['file'] == prior
    assert [r['source_pointer'] for r in row['uses']] == [None, '/bounds/A~1B', '/bounds/A~1B']
    assert [r['request_pointer'] for r in row['uses']] == [
        '/native_flux_balance/model_input/acquisition_receipt_file',
        '/native_flux_balance/constraints/0/lower/source/file', '/native_flux_balance/constraints/0/upper/source/file']
    witness, = row['witnesses']
    assert witness['reference'] == reference and witness['artifact_field'] == field
    assert witness['input_version'] == f.versions[-1]


def test_all_explicit_matching_witnesses_retained_in_original_order(selected):
    f = selected
    prior, ref = with_prior(f)
    other = source(f, prior, field='text_ref')
    f.receipts.receive(f.root.episode_id, [other, prior['artifact_ref']], kind='initial')
    f.versions.extend([version(other), version(prior['artifact_ref']), deepcopy(f.versions[-1])])
    result = bind(f)
    assert [w['reference'] for w in result['prior_sources'][0]['witnesses']] == [ref, other, prior['artifact_ref']]
    receipt = freeze_flux_balance_input_binding(f.store, binding=result)
    assert [r['reference'] for r in receipt['witness_records']] == [f.model['artifact_ref'], ref, other, prior['artifact_ref']]
    assert checked_receipt(f, receipt) == receipt


def test_frozen_receipt_survives_later_source_metadata_and_parent_receipts(selected):
    f = selected
    _, ref = with_prior(f)
    child = new_context(f, f.root)
    binding = bind(f, child)
    receipt = freeze_flux_balance_input_binding(f.store, binding=binding)
    before = deepcopy(receipt)
    record = f.store.get(ref)
    record['accession'] = 'later-mutated-metadata'
    f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), ref))
    later = artifact(f, b'late source')
    f.receipts.receive(f.root.episode_id, [later['artifact_ref']], kind='own_action')
    assert checked_receipt(f, receipt, child) == before
    assert checked_receipt(f, receipt, child) == before
    with pytest.raises(ValueError, match='binding_conflict'):
        validate_flux_balance_input_binding(f.store, binding, context=child, assignment=f.assignment,
            input_versions=f.versions, reference_access=f.access)
    with pytest.raises(ValueError, match='witness_record_conflict'):
        freeze_flux_balance_input_binding(f.store, binding=binding)


@pytest.mark.parametrize('mode', ['unreceived', 'later_parent', 'protected_artifact', 'protected_source'])
def test_unreceived_late_and_protected_aliases_fail_without_grants(selected, mode):
    f = selected
    prior, ref = with_prior(f)
    child = new_context(f, f.root)
    if mode == 'unreceived':
        f.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?', (ref,))
    elif mode == 'later_parent':
        f.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?', (ref,))
        f.receipts.receive(f.root.episode_id, [ref], kind='own_action')
    else:
        forbidden = prior['artifact_ref'] if mode == 'protected_artifact' else ref
        f.access = lambda context, reference, namespace: False if reference == forbidden else None
    before = list(f.store.db.iterdump())
    with pytest.raises(ValueError, match='not_received|protected_reference_denied'):
        bind(f, child)
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('defect', ['null_model', 'path', 'hash', 'length', 'format', 'swapped_primary_hash', 'version'])
def test_selected_identity_and_input_version_failures(selected, defect):
    f = selected
    prior, _ = with_prior(f)
    selected_model = f.assignment['requested_job']['native_flux_balance']['model_input']
    if defect == 'null_model': selected_model['artifact_ref'] = None
    elif defect == 'path': selected_model['file']['path'] += '-wrong'
    elif defect == 'hash': selected_model['file']['sha256'] = 'f' * 64
    elif defect == 'length': selected_model['file']['size_bytes'] += 1
    elif defect == 'format': selected_model['format'] = 'unknown'
    elif defect == 'swapped_primary_hash': f.versions[-1]['content_sha256'] = prior['sha256']
    elif defect == 'version': f.versions[-1]['version'] = '42'
    with pytest.raises(ValueError, match='flux_balance_input_'):
        bind(f)


def test_unsupported_auxiliary_relationship_does_not_become_witness(selected):
    f = selected
    prior, ref = with_prior(f)
    record = f.store.get(ref)
    record['request_ref'] = None
    record['auxiliary_artifact_refs'] = [prior['artifact_ref']]
    f.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(record), ref))
    with pytest.raises(ValueError, match='selected_witness_required'):
        bind(f)


def test_unrelated_selected_input_is_preserved_without_becoming_witness(selected):
    f = selected
    subject = f.scope['subject_refs'][0]
    f.receipts.receive(f.root.episode_id, [subject], kind='initial')
    f.versions.insert(0, version(subject))
    binding = bind(f)
    assert binding['input_versions'] == f.versions
    assert [w['reference'] for w in binding['model']['witnesses']] == [f.model['artifact_ref']]
    receipt = freeze_flux_balance_input_binding(f.store, binding=binding)
    assert [r['reference'] for r in receipt['witness_records']] == [f.model['artifact_ref']]
    assert checked_receipt(f, receipt) == receipt


@pytest.mark.parametrize('defect', ['unknown_key', 'missing_record', 'duplicate_record', 'record_bytes',
                                   'record_id', 'witness_hash', 'witness_field', 'wrong_selection', 'uses', 'path'])
def test_malformed_or_conflicting_frozen_control_rejected(selected, defect):
    f = selected
    with_prior(f)
    receipt = freeze_flux_balance_input_binding(f.store, binding=bind(f))
    if defect == 'unknown_key': receipt['extra'] = True
    elif defect == 'missing_record': receipt['witness_records'].pop()
    elif defect == 'duplicate_record': receipt['witness_records'].append(deepcopy(receipt['witness_records'][-1]))
    elif defect == 'record_bytes': receipt['witness_records'][-1]['record']['accession'] = 'forged'
    elif defect == 'record_id': receipt['witness_records'][-1]['record']['id'] = 'source_wrong'
    elif defect == 'witness_hash': receipt['binding']['prior_sources'][0]['witnesses'][0]['record_sha256'] = 'f' * 64
    elif defect == 'witness_field': receipt['binding']['prior_sources'][0]['witnesses'][0]['artifact_field'] = 'text_ref'
    elif defect == 'wrong_selection': receipt['binding']['input_versions'].pop()
    elif defect == 'uses': receipt['binding']['prior_sources'][0]['uses'][0]['source_pointer'] = '/forged'
    elif defect == 'path': receipt['binding']['prior_sources'][0]['path'] = '/outside'
    with pytest.raises(ValueError, match='flux_balance_input_'):
        checked_receipt(f, receipt)


@pytest.mark.parametrize('defect', ['wrong_episode', 'wrong_scope', 'wrong_request', 'wrong_parent', 'prefix'])
def test_context_and_frozen_lineage_must_be_original(selected, defect):
    f = selected
    child = new_context(f, f.root)
    if defect == 'wrong_episode': changed = replace(child, episode_id='not-original')
    elif defect == 'wrong_scope': changed = replace(child, scope={'subject_refs': []})
    elif defect == 'wrong_request':
        request = plain(child.request); request['message']['extra'] = 'forged'
        changed = replace(child, request=request)
    else:
        changed = child
        column = 'parent_episode_id' if defect == 'wrong_parent' else 'through_receipt_index'
        f.store.db.execute(f'UPDATE runtime_receipt_inheritance SET {column}=? WHERE run_id=? AND episode_id=?',
                           ('forged-parent' if defect == 'wrong_parent' else 999999, f.run_id, child.episode_id))
    with pytest.raises(ValueError, match='flux_balance_input_'):
        bind(f, changed)


def test_receipt_validation_detached_and_does_not_read_model_or_prior_bytes(selected, monkeypatch):
    f = selected
    with_prior(f)
    receipt = freeze_flux_balance_input_binding(f.store, binding=bind(f))
    before = list(f.store.db.iterdump())
    for file in [f.model, receipt['binding']['prior_sources'][0]['file']]:
        (f.store.path / 'artifacts' / file['sha256'][:2] / file['sha256']).unlink()
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('metadata validator read bytes'))
    result = checked_receipt(f, receipt)
    result['witness_records'][0]['record']['size'] = 999
    assert receipt['witness_records'][0]['record']['size'] != 999
    assert list(f.store.db.iterdump()) == before


def test_actual_witness_namespaces_and_no_current_source_read_in_frozen_validation(selected, monkeypatch):
    f = selected
    _, ref = with_prior(f)
    kinds = {row['reference']: f.store.get(row['reference'])['record_type'] for row in f.versions}
    kinds[f.assignment['requested_job']['native_flux_balance']['model_input']['acquisition_receipt_file']['artifact_ref']] = 'artifact'
    def exact_access(context, reference, namespace):
        assert namespace == kinds[reference]
    f.access = exact_access
    receipt = freeze_flux_balance_input_binding(f.store, binding=bind(f))
    original_get = f.store.get
    def without_current_source(reference):
        if reference == ref:
            pytest.fail('historical receipt reread mutable source record')
        return original_get(reference)
    monkeypatch.setattr(f.store, 'get', without_current_source)
    assert checked_receipt(f, receipt) == receipt


def test_received_but_unselected_source_never_substitutes_for_a_witness(selected):
    f = selected
    with_prior(f)
    f.versions.pop()
    before = list(f.store.db.iterdump())
    with pytest.raises(ValueError, match='selected_witness_required'):
        bind(f)
    assert list(f.store.db.iterdump()) == before


def test_unrelated_input_content_hash_keeps_existing_sequence_ref_meaning(selected):
    f = selected
    subject = f.scope['subject_refs'][0]
    sequence = f.store.get(subject)['sequence_ref']
    f.receipts.receive(f.root.episode_id, [subject], kind='initial')
    f.versions.insert(0, version(subject, sequence[9:]))
    assert bind(f)['input_versions'] == f.versions
    f.versions[0]['content_sha256'] = f.model['sha256']
    with pytest.raises(ValueError, match='version_conflict'):
        bind(f)


@pytest.mark.parametrize('defect', ['absent_inheritance', 'bad_report_prefix', 'invalid_access_verdict'])
def test_authority_primitive_failures_keep_typed_input_failure_prefix(selected, defect):
    f = selected
    if defect == 'absent_inheritance':
        f.store.db.execute('DELETE FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                           (f.run_id, f.root.episode_id))
    elif defect == 'bad_report_prefix':
        f.store.db.execute('UPDATE runtime_receipt_inheritance SET received_report_prefix=? '
                           'WHERE run_id=? AND episode_id=?', ('{}', f.run_id, f.root.episode_id))
    else:
        f.access = lambda *args: 1
    with pytest.raises(ValueError, match='^flux_balance_input_'):
        bind(f)
