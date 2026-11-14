"""Exact private counterpart selection and complete original metadata outputs."""
import os
from copy import deepcopy
from types import SimpleNamespace

import pytest

from .api_cases import Case, HOMES as API_HOMES, module, rows
from .native_progress_cases import HOMES, NativeProgressCase
from .native_metadata_cases import FAMILIES, check_metadata, original_describe

PHASE = os.environ['A104_NATIVE_RESULT_PHASE']
assert PHASE in {'baseline', 'connected'}
ROLES = ('execution_result_acquisition', 'execution_job_submission',
    'execution_job_submission/api_job_execution', 'execution_job_submission/local_job_execution',
    'execution_job_submission/hpc_job_execution')
OWNERS = [(home.removesuffix('execution_result_acquisition') + role, home)
    for home in HOMES for role in ROLES]


@pytest.mark.parametrize('owner_home,result_home', OWNERS)
def test_actual_constructor_counterpart(tmp_path, owner_home, result_home):
    case = NativeProgressCase(tmp_path, result_home)
    try:
        owner = module(owner_home + '/episode').ExecutionEpisode(
            SimpleNamespace(annotation_task_required=lambda: False), store=case.store,
            directory=tmp_path / 'selected-owner', run_id=case.run_id, resources=case.resources,
            initial_information={}, tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
            log_window_bytes=8, log_roles=('stdout', 'stderr'))
        assert owner.binding_path == owner_home
        provider = owner.job_progress_provider
        assert type(provider) is module('execution_progress').ExecutionProgressProvider
        descriptor = provider.as_record()
        if PHASE == 'connected':
            assert provider.native_result_owner == provider.targets.native_result_owner == result_home
            assert descriptor['configuration']['native_result_owner'] == result_home
        else:
            assert not hasattr(provider, 'native_result_owner')
            assert not hasattr(provider.targets, 'native_result_owner')
            assert 'native_result_owner' not in descriptor['configuration']
    finally:
        case.close()


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('family', FAMILIES, ids=[family[0] for family in FAMILIES])
@pytest.mark.parametrize('bound', (True, False), ids=('private_counterpart', 'public_unbound'))
def test_complete_metadata_and_selector_results(tmp_path, home, family, bound):
    check_metadata(tmp_path, home, family, phase=PHASE, bound=bound)


@pytest.mark.parametrize('owner', ('unknown/results', '', ['execution_result_acquisition']))
def test_unknown_owner_is_not_reinterpreted(tmp_path, owner):
    with module('state').Store(tmp_path / 'store') as store:
        constructor = module('execution_progress').ExecutionTargetReader
        expected = ValueError if PHASE == 'connected' else TypeError
        with pytest.raises(expected) as caught:
            constructor(store, run_id='unknown-owner-control', directory=tmp_path / 'read',
                resources={}, api_execution=None, native_result_owner=owner)
        if PHASE == 'connected':
            assert str(caught.value) == 'native_result_counterpart_owner_invalid'
        else:
            assert 'native_result_owner' in str(caught.value)


@pytest.mark.parametrize('home', HOMES)
def test_actual_global_factory_uses_its_configured_scientific_counterpart(tmp_path, home):
    case = NativeProgressCase(tmp_path / 'native', home)
    try:
        factory = module('execution_service_setup').ExecutionServiceFactory(
            resources=case.resources, initial_information={}, handoff_unit=1.,
            acquired_record_unit=1., monitoring_information_unit=1., log_window_bytes=8)
        application = factory(case.store, run_id=case.run_id, directory=tmp_path / 'factory')
        provider = application.job_progress_provider
        # The global factory selects its first scientific Launch binding.
        # It does not infer this name from the supplied physical target.
        if PHASE == 'connected':
            assert provider.native_result_owner == 'scientific_process/execution_result_acquisition'
        else:
            assert not hasattr(provider, 'native_result_owner')
        public = module('episode_monitoring').ProgressProvider(case.store,
            module('method_loop.durable').DurableExecutionStore(tmp_path / 'public'),
            run_id=case.run_id, job_provider=provider)
        services = module('episode_services').WorkflowServices(SimpleNamespace(progress_provider=public))
        before = rows(case.store)
        assert services.describe_progress_target(case.reference, case.scope) == provider.describe_target(case.reference, case.scope)
        assert rows(case.store) == before
    finally:
        case.close()


@pytest.mark.parametrize('api_home', API_HOMES)
def test_native_counterpart_preserves_explicit_api_observer(tmp_path, api_home):
    case = Case(tmp_path, api_home)
    try:
        returned = case.act('api.uniprot.record')
        assert returned['status'] == 'completed'
        reference = returned['result']['handoff_ref']
        launch_home = api_home.removesuffix('/api_job_execution')
        launch = module(launch_home + '/episode').ExecutionEpisode(case.services, **case.options)
        target = launch.job_progress_provider.targets.read_target(reference, case.scope)
        observer = launch.job_progress_provider.targets.api_observer
        original = observer.observe_target(target, operation_key=case.run_id + ':original-observer:0')
        visits = []
        def configured(actual, **operands):
            visits.append({'target': deepcopy(actual), 'operands': deepcopy(operands)})
            return deepcopy(original)
        result_home = launch_home.removesuffix('execution_job_submission') + 'execution_result_acquisition'
        arguments = {'native_result_owner': result_home} if PHASE == 'connected' else {}
        provider = module('execution_progress').ExecutionProgressProvider(case.store,
            run_id=case.run_id, directory=case.options['directory'], resources=case.options['resources'],
            api_execution=launch.api_execution, api_observer=SimpleNamespace(observe_target=configured),
            log_window_bytes=8, log_roles=('stdout', 'stderr'), **arguments)
        before, calls = rows(case.store), deepcopy(case.client.calls)
        assert provider.targets.describe_target(reference, case.scope) == original_describe()(
            provider.targets, reference, case.scope)
        key = case.run_id + ':explicit-observer:0'
        assert provider.targets.observe_target(target, operation_key=key) == original
        assert visits == [{'target': target, 'operands': {'operation_key': key}}]
        assert provider.targets.api_execution is launch.api_execution
        assert rows(case.store) == before and case.client.calls == calls
    finally:
        case.close()
