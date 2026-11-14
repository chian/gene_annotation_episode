"""Real Workflow registration/settings and cached operational replay.

The runtime registers settings and constructs its actual private registry. The
test intercepts only the first annotation build, after those durable writes.
No annotation action or root controller/score is supplied. Later standalone
API/Launch/Results actions use the existing controlled carrier helper. Their
completed-unit closure is explicit; this is not a complete scientific iterator.
Immutable archives are separate from the original writable runtime directory.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from . import api_saved_carriers as carriers
from .api_cases import HOMES, Responses, error_record, module, rows
from .saved_binding_workflow import constructor_options

VERSION = 'a104_actual_registered_private_settings_v1'
GOAL = 'Engineering preservation of registered private bindings and saved actions'
ROLES = ('launch_api', 'launch', 'results')


def forbidden_root(*args, **kwargs):
    raise AssertionError('registered_boundary_must_not_execute_annotation_or_invent_root_credit')


def file_map(directory):
    return {str(file.relative_to(directory)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(directory.rglob('*')) if file.is_file()}


class RegistrationBoundary(BaseException):
    """The actual root build was reached after durable registration."""


class PrivateServices:
    """Explicit fixture caller, not an automatic resolver of saved callables."""
    def __init__(self, home):
        assert home in HOMES
        self.home = home
        root = home.rsplit('/', 1)[0]
        self.paths = [root, *(root + '/' + leaf for leaf in
            ('api_job_execution', 'local_job_execution', 'hpc_job_execution')),
            root.removesuffix('execution_job_submission') + 'execution_result_acquisition']
        self.calls = []

    def as_record(self):
        return {'version': VERSION, 'home': self.home, 'home_paths': self.paths,
            'constructor_operands': 'saved_binding_workflow.constructor_options',
            'projectors': 'actual_each_private_owner.project_credit',
            'historical_global_service_claimed': False}

    def __call__(self, store, *, run_id, directory, job_episodes=None,
                 resource_estimator=None, tool_registry=None):
        assert job_episodes is None and resource_estimator is None and tool_registry is not None
        owners = [module(home + '/episode').ExecutionEpisode(None,
            **constructor_options(store, Path(directory), run_id, tool_registry)) for home in self.paths]
        projectors = {}
        for owner in owners:
            for role in owner.roles:
                assert role not in projectors and owner.credit_kind(role) != 'scientific'
                projectors[role] = {'project': owner.project_credit,
                    'definition': {'version': 'execution_received_information_credit_v1',
                        'handoff_unit': owner.handoff_unit, 'acquired_record_unit': owner.acquired_record_unit,
                        'practical_units': 'original_assignment_progress_requirements',
                        'baseline': 'original_received_information', 'repeated_gain': 0}}
        application = module('episode_application_services').EpisodeApplicationServices(
            tuple(owner.as_record() for owner in owners), projectors, owners[0].job_progress_provider)
        self.calls.append({'run_id': run_id, 'directory': str(Path(directory).resolve()),
            'descriptors': deepcopy(application.episode_binding_descriptors),
            'owners': owners, 'projectors': projectors,
            'provider': application.job_progress_provider})
        return application


def registered_workflow(store, directory, home, client, *, resume=False, changes=None):
    runtime = module('runtime')
    services = PrivateServices(home)
    tools = module('tools').ToolRegistry(store, clients=client)
    reached = []
    original_build = runtime.Workflow.build
    def stop_after_registration(workflow, name, key, goal, scope, **kwargs):
        assert name == 'annotation' and key == 'root' and goal == GOAL and not kwargs
        assert not reached and workflow.store is store and workflow.tools is tools
        reached.append(workflow)
        raise RegistrationBoundary()
    arguments = dict(provider=object(), run_dir=Path(directory), resume=resume,
        controller_factory=forbidden_root, project_credit=forbidden_root,
        binding_definitions={'controller': {'version': 'unentered_annotation_controller_fixture_v1'},
            'credit': {'version': 'unentered_annotation_credit_fixture_v1'}},
        goal=GOAL, episode_record_receipts=True, initial_known_record_refs=[],
        annotation_child_roles=(), episode_service_factory=services,
        episode_service_binding=services.as_record(), episode_service_inputs='actual_tool_registry_v1')
    if changes is not None:
        # Negative tests change explicit supplied operands, never the stored row.
        arguments.update(changes)
    with patch.object(runtime.Workflow, 'build', stop_after_registration):
        try:
            asyncio.run(runtime._run_bound_workflow(store, tools, **arguments))
        except RegistrationBoundary:
            pass
        else:
            raise AssertionError('actual_runtime_did_not_reach_registration_boundary')
    assert runtime.Workflow.build is original_build and len(reached) == len(services.calls) == 1
    workflow, = reached
    call, = services.calls
    saved = dict(workflow.journal.row('runtime_runs'))
    settings = json.loads(saved['settings'])
    assert saved['state'] == 'created' and saved['summary'] is None
    assert settings['episode_bindings'] == workflow.episode_bindings.as_record() == list(call['descriptors'])
    assert settings['directory'] == call['directory'] == str(Path(directory).resolve())
    assert settings['episode_application_services'] == module('episode_application_services').service_binding(
        services, services.as_record(), inputs='actual_tool_registry_v1')
    assert settings['episode_job_progress_provider'] == module('episode_application_services').job_progress_binding(
        call['provider']) == workflow.episode_job_progress_provider_binding
    for role, original in call['projectors'].items():
        assert workflow.role_credit_projectors[role] is original['project']
        assert settings['episode_role_credit_bindings'][role]['definition'] == original['definition']
    assert json.loads((Path(directory) / 'run.json').read_bytes()) == {'run_id': workflow.run_id, **settings}
    return workflow, {'kind': VERSION, 'home_paths': services.paths,
        'factory_implementation': __name__ + '.PrivateServices',
        'actual_settings': settings, 'actual_runtime_run': saved,
        'actual_run_json_sha256': hashlib.sha256((Path(directory) / 'run.json').read_bytes()).hexdigest(),
        'descriptors': settings['episode_bindings'],
        'historical_settings_claimed': False, 'annotation_build_intercepted_after_registration': True}


def build_case(store, directory, home, role, client):
    assert role in ROLES
    return registered_workflow(store, Path(directory) / 'workflow', home, client)


def capture(output):
    output = Path(output).resolve()
    assert not output.exists()
    output.mkdir(parents=True)
    observations = []
    for ordinal, (home, role) in enumerate((home, role) for home in HOMES for role in ROLES):
        live = output / 'live' / str(ordinal)
        record = {'home': home, 'role': role, 'live': str(live), 'status': 'entered'}
        try:
            with patch.object(carriers, 'build_case', build_case):
                captured = carriers.capture_one(live, home, role)
            assert captured['factory']['kind'] == VERSION
            archive = output / 'archives' / str(ordinal)
            archive.parent.mkdir(exist_ok=True)
            shutil.copytree(live, archive)
            files = file_map(live)
            assert file_map(archive) == files
            record.update(status='captured', archive=str(archive), files=files,
                descriptor=captured['descriptor'], actual_settings=captured['factory']['actual_settings'],
                run_id=captured['run_id'])
        except Exception as error:
            import traceback
            record.update(status='raised', error=error_record(error), traceback=traceback.format_exc())
            # Retain genuine partial registration without adding any settings.
            marker = live / 'workflow/run.json'
            if marker.is_file(): record['actual_partial_run_json'] = json.loads(marker.read_bytes())
        observations.append(record)
        carriers.write(output / 'registration_index.json', observations)
    assert len(observations) == 18
    return observations


def authenticate_capture(captured):
    captured = Path(captured).resolve()
    raw = (captured / 'registration_index.json').read_bytes()
    index = json.loads(raw)
    assert len(index) == 18 and {(row['home'], row['role']) for row in index} == {
        (home, role) for home in HOMES for role in ROLES}
    assert all(row['status'] == 'captured' for row in index), 'no_positive_capture_from_failed_baseline'
    for row in index:
        archive, live = Path(row['archive']), Path(row['live'])
        assert archive.is_relative_to(captured / 'archives') and live.is_relative_to(captured / 'live')
        assert file_map(archive) == row['files']
        saved = json.loads((archive / 'capture.json').read_bytes())
        assert saved['directory'] == str(live) and saved['api_home'] == row['home'] and saved['role'] == row['role']
        assert saved['factory']['actual_settings'] == row['actual_settings']
        assert saved['descriptor'] == row['descriptor'] and saved['run_id'] == row['run_id']
        assert saved['factory']['kind'] == VERSION and saved['factory']['historical_settings_claimed'] is False
    return {'index_sha256': hashlib.sha256(raw).hexdigest(), 'records': index}


def reopen(captured, output, *, custody):
    captured, output = Path(captured).resolve(), Path(output).resolve()
    assert authenticate_capture(captured) == custody and not output.exists()
    output.mkdir(parents=True)
    observations = []
    for entry in custody['records']:
        live, archive = Path(entry['live']), Path(entry['archive'])
        result = {'home': entry['home'], 'role': entry['role'], 'status': 'entered'}
        saved = json.loads((archive / 'capture.json').read_bytes())
        store = None
        try:
            # Resume at the actual immutable directory in settings, never a
            # remapped archive. Authenticate all original runtime files first.
            assert file_map(live) == entry['files']
            store = module('state').Store(live / 'store')
            assert rows(store) == saved['logical_rows']
            clients = Responses()
            workflow, registered = registered_workflow(store, live / 'workflow',
                entry['home'], clients, resume=True)
            assert registered == saved['factory']
            assert workflow.run_id == saved['run_id'] and rows(store) == saved['logical_rows']
            owner = workflow.episode_bindings.for_binding_path(saved['home'])
            context = module('episode_bindings').BindingContext(**saved['context'])
            assert owner.as_record() == saved['descriptor']
            assert carriers.estimator_provenance(owner, context) == saved['original_estimator_provenance']
            before = rows(store)
            with ExitStack() as guards:
                for path in registered['home_paths']:
                    guards.enter_context(patch.object(workflow.episode_bindings.for_binding_path(path),
                        '_live_project_credit', carriers.forbidden))
                with patch.object(store, 'get_artifact', carriers.forbidden):
                    assert owner.credit_view(context, saved['selection']) == saved['carrier']['view']
                contract_record = saved['request']['report_contract']
                contract = module('runtime').TypedReportContract(contract_record['decision'],
                    contract_record['measurements']['schema'], lambda *_: True)
                child = workflow.build(saved['role'], saved['context']['path'][-1][1],
                    saved['request']['goal']['objective'], saved['context']['scope'], contract=contract,
                    initial=saved['request']['message']['initial_report'],
                    episode_assignment=saved['context']['assignment'])
                assert child.request.as_record() == saved['request']
                assert workflow.binding_context(child.source).as_record() == saved['context']
                child.source.restore(); child.source.restore_checkpoint()
                queue = list(child.source._unfinished_own_actions)
                assert queue == [0]
                returned = asyncio.run(child.source.execute(json.loads(saved['action_row']['action']), 0))
                assert returned.as_record() == saved['controller_input']
                assert child.source.last_outcome == json.loads(saved['action_row']['result'])
                assert child.source.last_outcome_index == 0 and list(child.source._unfinished_own_actions) == queue
                assert dict(workflow.journal.row('runtime_actions', child.source.episode_id, 0)) == saved['action_row']
            assert rows(store) == before and clients.calls == []
            result.update(status='returned', actual_settings=registered['actual_settings'],
                actual_runtime_run=registered['actual_runtime_run'], request=child.request.as_record(),
                context=workflow.binding_context(child.source).as_record(), action_row=saved['action_row'],
                payload=child.source.last_outcome, controller_input=returned.as_record(),
                queue_before=queue, queue_after=list(child.source._unfinished_own_actions),
                closed_view=saved['carrier']['view'], no_provider_acquisition=True,
                full_iterator_restoration_claimed=False)
        except Exception as error:
            import traceback
            result.update(status='raised', error=error_record(error), traceback=traceback.format_exc())
        finally:
            if store is not None: store.close()
            assert file_map(archive) == entry['files']
            result['original_archive_unchanged'] = True
            observations.append(result)
            carriers.write(output / 'reopen.json', observations)
    assert authenticate_capture(captured) == custody
    return observations
