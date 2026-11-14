"""Real pre-action runtime publication and restoration; controlled build port.

No continuation, model, native or scientific action is selected. This validates
the information metadata channel alongside exact current binding descriptors.
Historical closed-credit compatibility remains its separate carrier baseline.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gene_annotation_episode.episodic_workflow.root.a107.tests import private_saved_carriers as carrier
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from .test_information_connected import AXIS, module, original_initial


@pytest.fixture
def operands(tmp_path):
    carrier.write_instruction_source(tmp_path / 'instruction-source', AXIS)
    module('scientific_process_library').ScientificProcessLibrary.freeze(
        tmp_path / 'scientific-process-library', source=tmp_path / 'instruction-source')
    module('scientific_tool_library').ScientificToolLibrary.freeze(
        tmp_path / 'scientific-tool-library', catalog=[])
    with module('state').Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        factory = module('execution_service_setup').ExecutionServiceFactory(resources(), {},
            3., 2., 1., log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        config = module('library/execution_initial_information/information_configuration').InitialInformationConfiguration.original_global_factory(factory)
        yield store, tmp_path, config


def publish(operands, *, resume=False, supply_configuration=True):
    store, directory, configuration = operands
    runtime = module('runtime')
    captured = []
    def before_build(workflow, *args, **kwargs):
        assert args[:2] == ('annotation', 'root')
        captured.append(workflow)
        raise carrier.BeforeRootBuild()
    options = {'initial_information_configuration': configuration} if supply_configuration else {}
    with patch.object(runtime.Workflow, 'build', before_build):
        with pytest.raises(carrier.BeforeRootBuild):
            asyncio.run(runtime._run_bound_workflow(store, module('tools').ToolRegistry(store),
                provider=object(), run_dir=directory / 'workflow', resume=resume,
                controller_factory=carrier.controller_factory, project_credit=carrier.project_credit,
                episode_binding_factories=carrier.factories(AXIS, directory),
                episode_record_receipts=True, initial_known_record_refs=[],
                annotation_child_roles=('hpc', 'scientific_process'), decision_protocol=None, **options))
    assert len(captured) == 1
    return captured[0]


def test_runtime_publishes_complete_separate_information_custody(operands):
    store, directory, configuration = operands
    workflow = publish(operands)
    record = json.loads(workflow.journal.row('runtime_runs')['settings'])
    disk = json.loads((directory / 'workflow/run.json').read_text())
    assert record['episode_bindings'] == workflow.episode_bindings.as_record() == disk['episode_bindings']
    assert record['episode_initial_information'] == workflow.episode_initial_information_catalog.as_record()
    assert record['episode_initial_information_configuration'] == configuration.as_record()
    assert disk['episode_initial_information'] == record['episode_initial_information']
    assert disk['episode_initial_information_configuration'] == record['episode_initial_information_configuration']
    assert not store.db.execute('SELECT 1 FROM runtime_actions WHERE run_id=?', (workflow.run_id,)).fetchone()


@pytest.mark.parametrize('supply', [True, False], ids=['explicit-original-configuration', 'saved-configuration'])
def test_real_runtime_resume_reconstructs_information_without_rewriting_binding_identity(operands, supply):
    _, directory, _ = operands
    original = publish(operands)
    descriptor = deepcopy(original.episode_bindings.as_record())
    information = deepcopy(original.episode_initial_information_record)
    run_json = (directory / 'workflow/run.json').read_bytes()
    restored = publish(operands, resume=True, supply_configuration=supply)
    assert restored.episode_bindings.as_record() == descriptor
    assert restored.episode_initial_information_record == information
    assert (directory / 'workflow/run.json').read_bytes() == run_json
    context, _ = carrier.ancestor(restored, AXIS, (('annotation', 'root'),), restored.store.validate_scope())
    owner = next(binding for binding in restored.episode_bindings._bindings if binding.roles == ('launch',))
    assert restored.episode_bindings._recipient_initial_information(context) == original_initial(owner, context)


def test_real_runtime_rejects_changed_selected_factory_before_any_action(operands):
    store, directory, configuration = operands
    original = publish(operands)
    record = configuration.as_record()
    record['authorities'][0]['factory_definition']['handoff_unit'] = 4.
    changed = type(configuration).from_record(record)
    # Registered execution configuration remains original, so the explicit
    # provider mismatch is caught before any context or action can be acquired.
    before = store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
    with pytest.raises(ValueError, match='initial_information_recipient_configuration_conflict'):
        publish((store, directory, changed), resume=True)
    assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == before
    assert json.loads(original.journal.row('runtime_runs')['settings'])['episode_initial_information_configuration'] == configuration.as_record()


def test_actual_execution_factory_service_return_declares_its_original_information(operands):
    store, directory, configuration = operands
    _, factory = configuration.authorities[0]
    tools = module('tools').ToolRegistry(store)
    application = factory(store, run_id='service-information-construction', directory=directory / 'service',
        tool_registry=tools,
        execution_factory=module('scientific_process/episode').create_execution_bindings,
        monitor_type=module('scientific_process/execution_progress_assessment/episode').MonitorEpisode)
    assert type(application) is module('episode_application_services').EpisodeApplicationServices
    assert application.initial_information_configuration.authorities[0][1] is factory
    assert application.initial_information_configuration.as_record() == configuration.as_record()
    assert len(application.episode_binding_descriptors) == (6 if AXIS == 'a107' else 5)
    assert set(application.role_credit_bindings) == ({'launch', 'launch_api', 'launch_local', 'launch_hpc', 'results', 'monitor'}
        if AXIS == 'a107' else {'launch', 'launch_local', 'launch_hpc', 'results', 'monitor'})
