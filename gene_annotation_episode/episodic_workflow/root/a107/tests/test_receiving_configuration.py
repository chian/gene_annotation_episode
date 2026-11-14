"""Actual original constructor and receiving catalog boundary preservation.

No native operation, provider or network is called. The original constructor
case is baselineable before the receiving implementation exists.
"""
from copy import deepcopy
import importlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a107.'


def module(name): return importlib.import_module(PREFIX + name)


@pytest.fixture
def actual_case(tmp_path):
    class CallerStore(module('state').Store):
        pass
    with CallerStore(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        services = SimpleNamespace(annotation_task_required=lambda: False)
        factory = module('execution_service_setup').ExecutionServiceFactory(
            resources(), {}, 1., 2., 3., log_window_bytes=1024,
            require_private_execution_yield=True,
            results_yield_profiles={'native_unbounded_local': {'cutoff': .1, 'parameters': {'uncertainty_alpha': .1}}},
            task_yield_profiles={'caller-task': {'cutoff': .2, 'parameters': {'uncertainty_alpha': .2}}})
        directory = Path(os.path.relpath(tmp_path / 'workflow', Path.cwd()))
        assert not directory.is_absolute()
        values = module('communication').plain(factory.as_record())
        constructor = {key: values[key] for key in ('resources', 'initial_information',
            'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')}
        constructor.update(require_private_yield=values['require_private_execution_yield'],
            results_yield_profiles=values['results_yield_profiles'], task_yield_profiles=values['task_yield_profiles'])
        owner = module('hpc_work_planning.execution_result_acquisition.episode').ExecutionEpisode(
            services, store=store, directory=directory, run_id='receiving-original-constructor',
            tool_registry=None, **constructor)
        yield SimpleNamespace(store=store, services=services, directory=directory,
            factory=factory, original=owner, constructor=constructor)


def test_original_constructor_accepts_store_subclass_and_relative_directory(actual_case):
    case = actual_case
    assert case.original.store is case.store and case.original.services is case.services
    assert case.original.directory == case.directory and not case.original.directory.is_absolute()
    assert case.original.private_yield_binding is True
    assert case.original.results_yield_profiles == case.constructor['results_yield_profiles']
    assert case.original.task_yield_profiles == case.constructor['task_yield_profiles']


def setup(case):
    cls = module('library.received_execution_information.received_configuration').ReceivedExecutionConfiguration
    configuration = cls.original_global_factory(case.factory)
    catalog = configuration.construct(store=case.store, run_id=case.original.run_id,
        directory=case.directory, tool_registry=None, services=case.services)
    return configuration, catalog, catalog.setup_for('@annotation')


def test_receiving_constructor_preserves_original_ports_and_all_settings(actual_case):
    case = actual_case
    configuration, catalog, selected = setup(case)
    owner = selected.check()
    assert owner.store is case.store and owner.services is case.services and owner.tool_registry is None
    assert owner.directory == case.original.directory
    for name in ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit',
            'log_window_bytes', 'log_roles', 'private_yield_binding', 'results_yield_profiles', 'task_yield_profiles'):
        assert getattr(owner, name) == getattr(case.original, name)
    before = list(case.store.db.iterdump())
    reopened = type(configuration).from_record(configuration.as_record())
    assert reopened.as_record() == configuration.as_record()
    assert catalog.as_record()['configuration'] == configuration.as_record()
    assert list(case.store.db.iterdump()) == before


@pytest.mark.parametrize('field', ['private_yield_binding', 'results_yield_profiles', 'task_yield_profiles', 'services', 'store', 'tool_registry'])
def test_changed_original_constructor_operand_is_refused(actual_case, field):
    _, _, selected = setup(actual_case)
    owner = selected.check()
    if field == 'private_yield_binding': replacement = False
    elif field in {'results_yield_profiles', 'task_yield_profiles'}: replacement = {}
    else: replacement = object()
    setattr(owner, field, replacement)
    with pytest.raises(ValueError, match='received_execution_(reader_configuration|original_service_ports)_changed'):
        selected.check()


@pytest.mark.parametrize('field', ['resources', 'log_window_bytes', 'log_roles'])
def test_missing_saved_factory_operand_does_not_gain_current_defaults(actual_case, field):
    configuration, _, _ = setup(actual_case)
    saved = deepcopy(configuration.as_record())
    saved['authorities'][0]['factory_definition'].pop(field)
    with pytest.raises((TypeError, ValueError)):
        type(configuration).from_record(saved)
