"""Candidate tests: actual own-axis factory/Store/readers, controlled host ports.

These tests target the proposed information objects. Full runtime selection and
nonempty scientific custody remain separate connected baselines, as documented.
No model, subprocess, native command, remote operation or live API is invoked.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a107.state import Store
from gene_annotation_episode.episodic_workflow.root.a107.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a107.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_initial_information.information_authority import (
    OriginalInformationSetup, InitialInformationCatalog, reopen_information_catalog)
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_initial_information.information_readers import FactoryInformationReaders
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_initial_information.presentation import resource_information
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_initial_information.legacy_information_provenance import (
    original_global_factory_provenance, check_original_global_factory_provenance)

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a107.'


@pytest.fixture
def original_setup(tmp_path):
    """Fixture explicitly declares its factory; it does not recover one by equality.

    The private owner is retained only for original callback comparison.
    The candidate constructs its own actual factory readers independently.
    """
    with Store(tmp_path / 'store') as store:
        subject, = store.create_problem(raw_sequence='ATGGCT', molecule='dna')['subject_refs']
        inventory = {name: {'fixture': 'retained', 'authority': 'first'} for name in resources()}
        factory = ExecutionServiceFactory(resources(), inventory, 1., 1., 1.,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        definition = plain(factory.as_record())
        home = 'hpc_work_planning/execution_job_submission'
        module = importlib.import_module(PREFIX + home.replace('/', '.') + '.episode')
        directory = (tmp_path / 'workflow').resolve()
        owner = module.ExecutionEpisode(SimpleNamespace(annotation_task_required=lambda: False),
            store=store, run_id='information-authority', directory=directory, tool_registry=None,
            **{name: definition[name] for name in ('resources', 'initial_information',
                'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')})
        source = Path(module.__file__).resolve()
        root = next(parent for parent in source.parents if (parent / 'gene_annotation_episode').is_dir())
        # This fixture records its immediate port constructor only. Production
        # requires the independently audited complete reader source inventory.
        source_record = {'version': 'initial_information_reader_sources_v1', 'sources': [{
            'path': str(source.relative_to(root)), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}]}
        from .test_information_connected import original_initial
        from ..library.execution_initial_information.factory_readers import construct_factory_information_readers
        readers = construct_factory_information_readers(factory, store=store,
            run_id='information-authority', directory=directory, tool_registry=None,
            services=SimpleNamespace(annotation_task_required=lambda: False))
        setup = OriginalInformationSetup.capture('explicit-original-factory', factory, readers)
        path = (('annotation', 'root'),)
        context = BindingContext(readers.run_id, EpisodeRef(readers.run_id, path).episode_id,
            'annotation', path, {'subject_refs': [subject]}, {}, {})
        yield SimpleNamespace(store=store, factory=factory, owner=owner, readers=readers,
            setup=setup, context=context)




def test_equal_factory_values_do_not_supply_missing_provenance(original_setup):
    v = original_setup
    catalog = InitialInformationCatalog([v.setup], [])
    with pytest.raises(ValueError, match='initial_information_recipient_provenance_missing'):
        catalog.readers('@annotation', v.context)
    duplicate = deepcopy(v.setup.as_record())
    duplicate['authority_id'] = 'another-setup'
    record = catalog.as_record()
    record['authorities'] = [duplicate]
    with pytest.raises(ValueError, match='initial_information_authority_unavailable'):
        reopen_information_catalog(record, original_setups=[v.setup])


def test_duplicate_recipient_is_ambiguous_even_with_same_authority(original_setup):
    row = {'recipient': '@annotation', 'authority_id': original_setup.setup.authority_id}
    with pytest.raises(ValueError, match='initial_information_ambiguous_recipient'):
        InitialInformationCatalog([original_setup.setup], [row, row])


def test_original_catalog_reopens_without_touching_receipts(original_setup):
    v = original_setup
    catalog = InitialInformationCatalog([v.setup], [
        {'recipient': '@annotation', 'authority_id': v.setup.authority_id}])
    before = list(v.store.db.iterdump())
    restored = reopen_information_catalog(catalog.as_record(), original_setups=[v.setup])
    assert restored.as_record() == catalog.as_record()
    assert list(v.store.db.iterdump()) == before


@pytest.mark.parametrize('field', ['axis', 'factory', 'definition', 'reader_binding'])
def test_changed_authority_is_rejected(original_setup, field):
    v = original_setup
    catalog = InitialInformationCatalog([v.setup], [])
    record = catalog.as_record()
    authority = record['authorities'][0]
    if field == 'definition':
        authority[field]['initial_information'] = {}
    elif field == 'reader_binding':
        authority[field]['run_id'] = 'unrelated'
    else:
        authority[field] = 'unrelated'
    with pytest.raises(ValueError, match='initial_information_original_authority_required'):
        reopen_information_catalog(record, original_setups=[v.setup])


def test_receiver_identity_is_not_receipt_authority(original_setup):
    v = original_setup
    altered = replace(v.context, episode_id='unrelated')
    catalog = InitialInformationCatalog([v.setup], [
        {'recipient': '@annotation', 'authority_id': v.setup.authority_id}])
    with pytest.raises(ValueError, match='initial_information_receiver_identity_conflict'):
        catalog.readers('@annotation', altered)


def publish_original_setup(v, *, factory_identity):
    """Actual Journal/run.json metadata, controlled pre-loop publication port."""
    journal = Journal(v.store, v.readers.run_id)
    settings = {'episode_application_services': {
        'version': 'episode_application_services_v2', 'factory': factory_identity,
        'definition': plain(v.factory.as_record()), 'inputs': 'actual_tool_registry_v1'},
        'episode_bindings': [v.owner.as_record()]}
    epoch = '2026-11-11T00:00:00+00:00'
    journal.save('runtime_runs', {'settings': json.dumps(settings), 'state': 'created',
        'summary': None, 'started_at': epoch, 'updated_at': epoch})
    v.readers.directory.mkdir(parents=True, exist_ok=True)
    (v.readers.directory / 'run.json').write_text(json.dumps({'run_id': journal.run_id, **settings}) + '\n')
    return journal, settings


@pytest.mark.parametrize('identity', [
    'gene_annotation_episode.execution_service_setup.ExecutionServiceFactory',
    PREFIX + 'execution_service_setup.ExecutionServiceFactory'])
def test_old_factory_provenance_does_not_require_new_catalog(original_setup, identity):
    v = original_setup
    _, settings = publish_original_setup(v, factory_identity=identity)
    assert 'episode_initial_information' not in settings
    before = list(v.store.db.iterdump())
    run_json = (v.readers.directory / 'run.json').read_bytes()
    factory, provenance = original_global_factory_provenance(v.store,
        run_id=v.readers.run_id, directory=v.readers.directory)
    assert plain(factory.as_record()) == plain(v.factory.as_record())
    assert provenance['source']['episode_application_services'] == settings['episode_application_services']
    assert provenance['source']['episode_bindings'] == settings['episode_bindings']
    restored = check_original_global_factory_provenance(provenance, v.store,
        run_id=v.readers.run_id, directory=v.readers.directory)
    assert plain(restored.as_record()) == plain(v.factory.as_record())
    assert list(v.store.db.iterdump()) == before
    assert (v.readers.directory / 'run.json').read_bytes() == run_json


def test_equal_private_bindings_do_not_replace_missing_saved_factory(original_setup):
    v = original_setup
    journal, settings = publish_original_setup(v,
        factory_identity=PREFIX + 'execution_service_setup.ExecutionServiceFactory')
    del settings['episode_application_services']
    prior = journal.row('runtime_runs')
    journal.save('runtime_runs', {'settings': json.dumps(settings), 'state': prior['state'],
        'summary': prior['summary'], 'started_at': prior['started_at'], 'updated_at': prior['updated_at']})
    (v.readers.directory / 'run.json').write_text(json.dumps({'run_id': journal.run_id, **settings}) + '\n')
    with pytest.raises(ValueError, match='initial_information_original_factory_provenance_missing'):
        original_global_factory_provenance(v.store, run_id=v.readers.run_id, directory=v.readers.directory)


def test_changed_run_json_does_not_authorize_an_old_factory(original_setup):
    v = original_setup
    _, settings = publish_original_setup(v,
        factory_identity=PREFIX + 'execution_service_setup.ExecutionServiceFactory')
    changed = deepcopy(settings)
    changed['episode_application_services']['definition']['initial_information'] = {}
    (v.readers.directory / 'run.json').write_text(json.dumps({'run_id': v.readers.run_id, **changed}) + '\n')
    with pytest.raises(ValueError, match='initial_information_original_settings_conflict'):
        original_global_factory_provenance(v.store, run_id=v.readers.run_id, directory=v.readers.directory)
