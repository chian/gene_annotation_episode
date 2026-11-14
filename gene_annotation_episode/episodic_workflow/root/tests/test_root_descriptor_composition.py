"""Real storage composition and literal descriptor contracts, without science.

The empty binding set consumes no services object, private factory or job. It
retains the real Journal/Store/backend and the original progress-table effects.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

# Keep the absent-owner baseline unambiguous before any dependent imports.
import gene_annotation_episode.episodic_workflow.root.episode_composition as composition
from gene_annotation_episode.episodic_workflow.root import resource_records
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBinding, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import DurableExecutionError, DurableExecutionStore, canonical
from gene_annotation_episode.episodic_workflow.root.progress_observations import ProgressProvider
from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.state import Store


@pytest.fixture
def resources(tmp_path):
    with Store(tmp_path / 'store') as store:
        yield store, Journal(store, 'engineering-descriptor-composition'), DurableExecutionStore(tmp_path / 'backend')


def compose(resources, **changes):
    store, journal, backend = resources
    options = dict(store=store, journal=journal, execution_backend=backend,
        descriptors=[], job_episodes=None, resource_estimator=None, role_credit_bindings={})
    options.update(changes)
    return composition.compose_episode_bindings(None, **options)


def tables(store):
    return tuple(row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))


def uncalled_projector(*args, **kwargs):
    raise AssertionError('composition must not project credit or execute work')




def test_empty_descriptors_construct_real_progress_provider_and_reopen(resources):
    store, journal, backend = resources
    before_changes = store.db.total_changes
    result = compose(resources)
    assert type(result) is composition.EpisodeComposition
    assert result.bindings == result.resource_capabilities == ()
    assert dict(result.role_credit_projectors) == dict(result.role_credit_definitions) == {}
    assert type(result.progress_provider) is ProgressProvider
    assert result.progress_provider.store is store and result.progress_provider.durable_store is backend
    assert result.progress_provider.run_id == journal.run_id
    expected = {'runtime_progress_exposures', 'runtime_progress_notifications', 'runtime_progress_observations',
        'runtime_progress_selections', 'runtime_progress_receipts', 'runtime_progress_deliveries'}
    assert expected <= set(tables(store))
    assert all(store.db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0] == 0 for name in expected)
    assert store.db.total_changes == before_changes
    again = compose(resources)
    assert type(again.progress_provider) is ProgressProvider
    assert store.db.total_changes == before_changes
    with Store(store.path) as reopened:
        restored = compose((reopened, Journal(reopened, journal.run_id), backend))
        assert restored.progress_provider.store is reopened
        assert expected <= set(tables(reopened))
        assert all(reopened.db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0] == 0 for name in expected)
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
    with pytest.raises(FrozenInstanceError):
        result.bindings = ('changed',)


def test_empty_descriptors_without_backend_do_not_create_progress_tables(resources):
    store, _, _ = resources
    before, changes = tables(store), store.db.total_changes
    result = compose(resources, execution_backend=None)
    assert result.progress_provider is None and result.bindings == ()
    assert tables(store) == before and store.db.total_changes == changes


def test_explicit_credit_is_detached_immutable_and_never_evaluated(resources):
    definition = {'version': 'engineering_only', 'meaning': ['caller declared unit'], 'signed_unit': -0.375}
    result = compose(resources, role_credit_bindings={'monitor': {'definition': definition, 'project': uncalled_projector}})
    assert result.role_credit_projectors['monitor'] is uncalled_projector
    assert result.role_credit_definitions['monitor']['signed_unit'] == -0.375
    definition['meaning'].append('mutated after composition')
    assert result.role_credit_definitions['monitor']['meaning'] == ('caller declared unit',)
    with pytest.raises(TypeError):
        result.role_credit_definitions['monitor']['signed_unit'] = 7
    with pytest.raises(TypeError):
        result.role_credit_projectors['monitor'] = None


@pytest.mark.parametrize('changes,reference', [
    ({'descriptors': {}}, 'episode_bindings'),
    ({'descriptors': [None]}, 'episode_bindings'),
    ({'descriptors': [{'configuration': {}}]}, 'episode_bindings'),
    ({'descriptors': [{'binding_id': 'unknown', 'configuration': {}}]}, 'unknown'),
    ({'descriptors': [{'binding_id': 'unknown', 'configuration': []}]}, 'unknown'),
    ({'descriptors': [{'binding_id': 'unknown', 'configuration': {'nonfinite': float('nan')}}]}, 'episode_bindings'),
    ({'role_credit_bindings': []}, 'role_credit_bindings'),
    ({'role_credit_bindings': {'': {'definition': {}, 'project': uncalled_projector}}}, 'role_credit_bindings'),
    ({'role_credit_bindings': {'monitor': {'definition': {}, 'project': None}}}, 'monitor'),
    ({'role_credit_bindings': {'monitor': {'definition': [], 'project': uncalled_projector}}}, 'monitor'),
    ({'role_credit_bindings': {'monitor': {'definition': {}, 'project': uncalled_projector, 'extra': True}}}, 'monitor'),
    ({'execution_backend': None, 'descriptors': [{'binding_id': 'monitor', 'configuration': {}}]}, 'execution_backend'),
])
def test_invalid_operands_fail_before_progress_side_effects(resources, changes, reference):
    store, _, _ = resources
    before, writes = tables(store), store.db.total_changes
    with pytest.raises(DurableExecutionError) as caught:
        compose(resources, **changes)
    assert type(caught.value) is DurableExecutionError
    assert caught.value.failure == {'code': 'unavailable_binding', 'affected_refs': [reference],
        'diagnostic_ref': None, 'partial_record_refs': []}
    assert tables(store) == before and store.db.total_changes == writes


def test_actual_foreign_journal_is_rejected_before_progress_tables(resources, tmp_path):
    store, _, _ = resources
    before, writes = tables(store), store.db.total_changes
    with Store(tmp_path / 'foreign-store') as other:
        foreign = Journal(other, 'engineering-foreign')
        with pytest.raises(DurableExecutionError) as caught:
            compose(resources, journal=foreign)
    assert caught.value.failure['code'] == 'identity_conflict'
    assert caught.value.failure['affected_refs'] == ['journal.store']
    assert tables(store) == before and store.db.total_changes == writes


def test_actual_empty_journal_run_identity_is_rejected(resources):
    store, _, _ = resources
    empty = Journal(store, '')
    before, writes = tables(store), store.db.total_changes
    with pytest.raises(DurableExecutionError) as caught:
        compose(resources, journal=empty)
    assert caught.value.failure['code'] == 'unavailable_binding'
    assert caught.value.failure['affected_refs'] == ['journal.run_id']
    assert tables(store) == before and store.db.total_changes == writes




def descriptor(digest='a' * 64, version='scientific_process_episodes_v8'):
    # Literal comparison input only: no private library, binding or scientific
    # result is constructed or claimed by these compatibility checks.
    return {'version': version, 'binding_id': 'scientific_process', 'implementation_sha256': digest,
        'configuration': {'library': {'identity': 'unopened-engineering-library'},
            'tool_library': {'identity': 'unopened-engineering-tools'}, 'child_roles': ['private_role']}}


@pytest.mark.parametrize('version', [f'scientific_process_episodes_v{i}' for i in range(5, 11)])
def test_exact_supported_descriptor_identity(version):
    saved = descriptor(version=version)
    assert composition.scientific_binding_compatible(deepcopy(saved), saved)
    altered = deepcopy(saved)
    altered['configuration']['library']['identity'] = 'different-library'
    assert not composition.scientific_binding_compatible(altered, saved)


def test_every_original_directed_compatibility_pair_preserves_all_other_operands():
    pairs = composition._SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY
    assert pairs
    for old, new in pairs:
        recorded, actual = descriptor(old), descriptor(new)
        assert composition.scientific_binding_compatible(actual, recorded)
        assert composition.scientific_binding_compatible(recorded, actual) is ((new, old) in pairs)
        for key in ('library', 'tool_library', 'child_roles'):
            different = deepcopy(actual)
            different['configuration'][key] = {'changed': True}
            assert not composition.scientific_binding_compatible(different, recorded)
        for version in ('scientific_process_episodes_v7', 'scientific_process_episodes_v9'):
            assert not composition.scientific_binding_compatible(descriptor(new, version), descriptor(old, version))


@pytest.mark.parametrize('change', [
    {'binding_id': 'other'}, {'version': 'unrecognized'}, {'implementation_sha256': 'bad'},
    {'implementation_sha256': 'A' * 64}, {'configuration': []}, {'extra': True},
])
def test_invalid_descriptor_shape_never_becomes_compatible(change):
    value = {**descriptor(), **change}
    assert not composition.scientific_binding_compatible(value, value)


def test_unlisted_implementation_change_is_rejected():
    assert not composition.scientific_binding_compatible(descriptor('b' * 64), descriptor())


@pytest.mark.parametrize('availability', ['available', 'unavailable', 'authentication_required', 'unknown'])
def test_complete_original_resource_capability_contract(availability):
    value = {'resource_id': 'engineering-unqueried-resource', 'kind': 'local', 'availability': availability,
        'observed_at': 'engineering-literal', 'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': [],
        'local_resources': {}, 'allocation_limits': {'cpu': None, 'memory_bytes': None, 'scratch_bytes': None}}
    validate_schema(value, resource_records.CAPABILITY_SCHEMA)
    assert resource_records._validate(value, resource_records.CAPABILITY_SCHEMA) == value
    for invalid in ({**value, 'availability': 'assumed'}, {**value, 'extra': True},
                    {**value, 'allocation_limits': {'cpu': 0, 'memory_bytes': None, 'scratch_bytes': None}}):
        with pytest.raises(ContractError):
            validate_schema(invalid, resource_records.CAPABILITY_SCHEMA)
        with pytest.raises(ValueError, match='invalid_resource_assignment'):
            resource_records._validate(invalid, resource_records.CAPABILITY_SCHEMA)
