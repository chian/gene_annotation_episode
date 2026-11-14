"""Actual private constructors and saved-descriptor composition; no scientific work.

Libraries, Store, Journal and DurableExecutionStore are real. Services and the
ToolRegistry identity are controlled ports; no native/provider execution or
scientific evidence is claimed. Shared engineering fixture inputs stay in tests.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
from gene_annotation_episode.workflow_budget import active_budget

AXIS = 'a103'
HOMES = ('scientific_process', 'execution_job_submission', 'execution_job_submission/api_job_execution', 'execution_job_submission/local_job_execution', 'execution_job_submission/hpc_job_execution', 'execution_result_acquisition', 'scientific_process/execution_job_submission', 'scientific_process/execution_job_submission/api_job_execution', 'scientific_process/execution_job_submission/local_job_execution', 'scientific_process/execution_job_submission/hpc_job_execution', 'scientific_process/execution_result_acquisition', 'hpc_work_planning/execution_job_submission', 'hpc_work_planning/execution_job_submission/api_job_execution', 'hpc_work_planning/execution_job_submission/local_job_execution', 'hpc_work_planning/execution_job_submission/hpc_job_execution', 'hpc_work_planning/execution_result_acquisition', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', 'scientific_process/hpc_work_planning/execution_job_submission', 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/execution_result_acquisition', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', 'execution_progress_assessment', 'scientific_process/execution_progress_assessment', 'hpc_work_planning/execution_progress_assessment', 'hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'scientific_process/hpc_work_planning/execution_progress_assessment', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution', 'hpc_work_planning/hpc_resource_prediction', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution', 'scientific_process/hpc_work_planning/hpc_resource_prediction')
EXECUTION_HOMES = ('execution_job_submission', 'execution_job_submission/api_job_execution', 'execution_job_submission/local_job_execution', 'execution_job_submission/hpc_job_execution', 'execution_result_acquisition', 'scientific_process/execution_job_submission', 'scientific_process/execution_job_submission/api_job_execution', 'scientific_process/execution_job_submission/local_job_execution', 'scientific_process/execution_job_submission/hpc_job_execution', 'scientific_process/execution_result_acquisition', 'hpc_work_planning/execution_job_submission', 'hpc_work_planning/execution_job_submission/api_job_execution', 'hpc_work_planning/execution_job_submission/local_job_execution', 'hpc_work_planning/execution_job_submission/hpc_job_execution', 'hpc_work_planning/execution_result_acquisition', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', 'scientific_process/hpc_work_planning/execution_job_submission', 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/execution_result_acquisition', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition')
MONITOR_HOMES = ('execution_progress_assessment', 'scientific_process/execution_progress_assessment', 'hpc_work_planning/execution_progress_assessment', 'hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'scientific_process/hpc_work_planning/execution_progress_assessment', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment')
HPC_HOMES = ('hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution', 'hpc_work_planning/hpc_resource_prediction', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution', 'scientific_process/hpc_work_planning/hpc_resource_prediction')


def own(name):
    return import_module('gene_annotation_episode.episodic_workflow.root.' + AXIS + '.' + name)


def forbidden(*args, **kwargs):
    raise AssertionError('reconstruction cannot execute provider, native work or a credit projector')


def caught(call):
    try:
        return {'status': 'returned', 'value': call()}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'failure': getattr(error, 'failure', None)}


def source_hashes():
    axis = Path(__file__).resolve().parents[1]
    root = axis.parents[3]
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(axis.rglob('*.py')) if 'tests' not in path.relative_to(axis).parts}


@contextmanager
def construction_case(output):
    output = Path(output).resolve()
    assert output.is_relative_to(Path(active_budget()['run_directory']).resolve())
    output.mkdir(parents=True, exist_ok=True)
    before_sources = source_hashes()
    source = output / 'instruction-source'
    write_instruction_source(source, AXIS)
    directory = output / 'workflow'
    library = own('scientific_process_library').ScientificProcessLibrary.freeze(
        directory / 'scientific-process-library', source=source)
    catalog = [{'name': 'fixture.inspect', 'resources': 'local',
        'description': 'Inspect an engineering fixture only.',
        'instructions': 'No biological inference or external work.',
        'input_schema': own('domain').obj({})}]
    tools = own('scientific_tool_library').ScientificToolLibrary.freeze(
        directory / 'scientific-tool-library', catalog=catalog, tool_info=True)
    report = {'version': 'private_reconstruction_actual_probe_v1', 'axis': AXIS,
        'source_hashes': before_sources, 'constructors': {}, 'diagnostic_completed': False,
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'controlled_ports': ['services', 'ToolRegistry identity only', 'credit projectors forbidden'],
        'native_or_provider_work': False, 'full_workflow_restoration': False}
    destination = output / 'reconstruction-probe.json'
    def retain():
        destination.write_text(json.dumps(report, indent=2) + '\n')
    retain()
    with patch('subprocess.Popen', forbidden), patch('socket.socket.connect', forbidden), patch('socket.socket.connect_ex', forbidden):
        with own('state').Store(output / 'state') as store:
            store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
            journal = own('episode_journal').Journal(store, AXIS + '-reconstruction-probe')
            backend = own('method_loop.durable').DurableExecutionStore(directory / 'execution')
            services = SimpleNamespace(annotation_task_required=lambda: False)
            registry_port = SimpleNamespace(store=store, clients={})
            direct = {}
            roles = {}
            for home in HOMES:
                module = own(home.replace('/', '.') + '.episode')
                if home == 'scientific_process':
                    constructor = lambda: module.ScientificProcessEpisode(services, library=library,
                        tool_library=tools, child_roles=('scientific_process', 'hpc', 'launch', 'results', 'monitor'))
                elif home in EXECUTION_HOMES:
                    configuration = dict(resources=resources(),
                        initial_information={key: {'fixture_home': home} for key in resources()},
                        handoff_unit=2.5, acquired_record_unit=3.5, log_window_bytes=96,
                        log_roles=['stdout'], require_private_yield=True,
                        results_yield_profiles={'native_unbounded_hpc': {'cutoff': .4, 'parameters': {'uncertainty_alpha': .1}}},
                        task_yield_profiles={'fixture:task': {'cutoff': .3, 'parameters': {'uncertainty_alpha': .1}}})
                    constructor = lambda: module.ExecutionEpisode(services, store=store,
                        run_id=journal.run_id, directory=directory, tool_registry=registry_port, **configuration)
                elif home in MONITOR_HOMES:
                    constructor = lambda: module.MonitorEpisode(services, outcome_page_size=7,
                        information_unit=4.5, yield_settings={'kind': 'information_accumulation',
                            'cutoff': .2, 'uncertainty_alpha': .1})
                else:
                    assert home in HPC_HOMES
                    constructor = lambda: module.HPCEpisode(services, store=store, run_id=journal.run_id,
                        directory=directory, resources=resources(), commissions={},
                        shared_execution_memory={'path': str(output / 'shared-memory.sqlite3')},
                        require_commission_yield=True)
                observed = caught(constructor)
                if observed['status'] == 'returned':
                    binding = observed.pop('value')
                    direct[home] = binding
                    descriptor = binding.as_record()
                    observed.update(binding_path=binding.binding_path,
                        type=type(binding).__module__ + '.' + type(binding).__qualname__, descriptor=descriptor)
                    for role in binding.roles:
                        if binding.credit_kind(role) != 'scientific':
                            roles[role] = {'definition': {'fixture': 'caller_owned', 'role': role}, 'project': forbidden}
                report['constructors'][home] = observed
                retain()
            descriptors = [direct[home].as_record() for home in HOMES if home in direct]
            arguments = dict(store=store, journal=journal, execution_backend=backend,
                descriptors=descriptors, job_episodes=None, resource_estimator=None,
                role_credit_bindings=roles, directory=directory, tool_registry=registry_port)
            composition = own('episode_composition')
            observed = caught(lambda: composition.compose_episode_bindings(services, **arguments))
            rebuilt = None
            if observed['status'] == 'returned':
                rebuilt = observed.pop('value')
                observed.update(descriptors=[binding.as_record() for binding in rebuilt.bindings],
                    binding_paths=[binding.binding_path for binding in rebuilt.bindings],
                    types=[type(binding).__module__ + '.' + type(binding).__qualname__ for binding in rebuilt.bindings],
                    resource_capabilities=[dict(row) for row in rebuilt.resource_capabilities])
            report['composition'] = observed
            if 'scientific_process' in direct:
                descriptor = direct['scientific_process'].as_record()
                report['current_scientific_compatibility'] = composition.scientific_binding_compatible(descriptor, descriptor)
            retain()
            yield SimpleNamespace(axis=AXIS, store=store, journal=journal, backend=backend,
                services=services, tools=registry_port, direct=direct, rebuilt=rebuilt,
                descriptors=descriptors, arguments=arguments, composition=composition,
                report=report, output=output, retain=retain)
    assert source_hashes() == before_sources
    report['diagnostic_completed'] = True
    retain()


def run_probe(output):
    with construction_case(output) as case:
        result = case.report
    return result
