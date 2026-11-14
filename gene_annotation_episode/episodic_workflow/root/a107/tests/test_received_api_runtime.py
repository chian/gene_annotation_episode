"""Separate received-API configuration in actual pre-action runtime metadata."""
import asyncio
from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from .test_information_runtime import operands
from .test_information_connected import module
from .test_information_authority import original_setup, publish_original_setup
from gene_annotation_episode.episodic_workflow.root.a107.tests import private_saved_carriers as carrier


def publish(operands, received, *, resume=False, supply=True):
    store, directory, initial = operands
    captured = []
    def before_build(workflow, *args, **kwargs):
        assert args[:2] == ('annotation', 'root')
        captured.append(workflow)
        raise carrier.BeforeRootBuild()
    options = {'initial_information_configuration': initial}
    if supply:
        options['received_api_configuration'] = received
    runtime = module('runtime')
    with patch.object(runtime.Workflow, 'build', before_build):
        with pytest.raises(carrier.BeforeRootBuild):
            asyncio.run(runtime._run_bound_workflow(store, module('tools').ToolRegistry(store),
                provider=object(), run_dir=directory / 'workflow', resume=resume,
                controller_factory=carrier.controller_factory, project_credit=carrier.project_credit,
                episode_binding_factories=carrier.factories('a107', directory),
                episode_record_receipts=True, initial_known_record_refs=[],
                annotation_child_roles=('hpc', 'scientific_process'), decision_protocol=None, **options))
    assert len(captured) == 1
    return captured[0]


@pytest.mark.parametrize('supply', [True, False])
def test_actual_runtime_keeps_separate_received_declaration_and_exact_resume(operands, supply):
    store, directory, initial = operands
    _, factory = initial.authorities[0]
    cls = module('library/received_api_information/received_api_authority').ReceivedAPIConfiguration
    configuration = cls.original_global_factory(factory)
    workflow = publish(operands, configuration)
    settings = json.loads(workflow.journal.row('runtime_runs')['settings'])
    disk = (directory / 'workflow/run.json').read_bytes()
    descriptors = deepcopy(workflow.episode_bindings.as_record())
    assert settings['episode_received_api_configuration'] == configuration.as_record()
    assert settings['episode_received_api_information'] == workflow.episode_received_api_catalog.as_record()
    assert settings['episode_initial_information_configuration'] == initial.as_record()
    resumed = publish(operands, configuration, resume=True, supply=supply)
    assert resumed.episode_received_api_catalog.as_record() == settings['episode_received_api_information']
    assert resumed.episode_bindings.as_record() == descriptors
    assert (directory / 'workflow/run.json').read_bytes() == disk
    assert not store.db.execute('SELECT 1 FROM runtime_actions').fetchone()


def test_initial_only_mapping_cannot_become_receiving_authority(operands):
    store, directory, initial = operands
    authority = module('library/received_api_information/received_api_authority')
    with pytest.raises(TypeError, match='received_api_explicit_configuration_required'):
        authority.ReceivedAPICatalog(initial, [])
    _, factory = initial.authorities[0]
    multi = authority.ReceivedAPIConfiguration([('a', factory), ('b', type(factory).from_record(factory.as_record()))],
        [{'recipient': '@annotation', 'authority_id': 'a'}])
    catalog = multi.construct(store=store, run_id='separate-receiving-declaration',
        directory=directory, tool_registry=module('tools').ToolRegistry(store), services=None)
    with pytest.raises(ValueError, match='received_api_recipient_provenance_missing'):
        catalog.configured('@untagged-custom')


def test_original_factory_service_result_declares_both_independent_channels(operands):
    store, directory, initial = operands
    _, factory = initial.authorities[0]
    application = factory(store, run_id='separate-api-factory', directory=directory / 'service',
        tool_registry=module('tools').ToolRegistry(store),
        execution_factory=module('scientific_process/episode').create_execution_bindings,
        monitor_type=module('scientific_process/execution_progress_assessment/episode').MonitorEpisode)
    assert application.initial_information_configuration.authorities[0][1] is factory
    assert application.received_api_configuration.authorities[0][1] is factory
    assert application.initial_information_configuration is not application.received_api_configuration
    assert application.received_api_configuration.as_record()['authorities'][0]['factory_definition'] == factory.as_record()


@pytest.mark.parametrize('identity', [
    'gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup.ExecutionServiceFactory',
    'gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup.ExecutionServiceFactory'])
def test_authentic_legacy_global_factory_needs_no_new_receiving_catalog(original_setup, identity):
    v = original_setup
    _, settings = publish_original_setup(v, factory_identity=identity)
    assert 'episode_received_api_information' not in settings
    authority = module('library/received_api_information/received_api_authority')
    configuration = authority.ReceivedAPIConfiguration.original_global_factory(v.factory)
    catalog = configuration.construct(store=v.store, run_id=v.readers.run_id,
        directory=v.readers.directory, tool_registry=v.owner.tool_registry, services=v.owner.services)
    workflow = module('runtime').Workflow.__new__(module('runtime').Workflow)
    workflow.store, workflow.run_id, workflow.directory = v.store, v.readers.run_id, v.readers.directory
    workflow.received_api_configuration, workflow.episode_received_api_catalog = configuration, catalog
    before, disk = tuple(v.store.db.iterdump()), (v.readers.directory / 'run.json').read_bytes()
    workflow.check_original_received_api_information(settings)
    provenance = workflow.episode_received_api_original_provenance['original_factory_provenance']
    assert provenance['source']['episode_bindings'] == settings['episode_bindings']
    assert provenance['source']['episode_application_services'] == settings['episode_application_services']
    assert tuple(v.store.db.iterdump()) == before
    assert (v.readers.directory / 'run.json').read_bytes() == disk


def test_unrelated_saved_factory_identity_is_not_receiving_authority(original_setup):
    v = original_setup
    _, settings = publish_original_setup(v, factory_identity='unrelated.module.ExecutionServiceFactory')
    authority = module('library/received_api_information/received_api_authority')
    configuration = authority.ReceivedAPIConfiguration.original_global_factory(v.factory)
    catalog = configuration.construct(store=v.store, run_id=v.readers.run_id,
        directory=v.readers.directory, tool_registry=v.owner.tool_registry, services=v.owner.services)
    workflow = module('runtime').Workflow.__new__(module('runtime').Workflow)
    workflow.store, workflow.run_id, workflow.directory = v.store, v.readers.run_id, v.readers.directory
    workflow.received_api_configuration, workflow.episode_received_api_catalog = configuration, catalog
    before = tuple(v.store.db.iterdump())
    with pytest.raises(ValueError, match='initial_information_original_factory_identity_unavailable'):
        workflow.check_original_received_api_information(settings)
    assert tuple(v.store.db.iterdump()) == before
