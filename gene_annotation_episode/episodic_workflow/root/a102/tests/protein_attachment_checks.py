"""Real private constructors and saved-parameter attachment identity dispatch.

The minimal transform selects an existing legacy-reader branch. It is not an
authenticated fitted transform or a scientific saved-result fixture.
"""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace

HOMES = ('execution_job_submission/api_job_execution', 'execution_job_submission', 'execution_job_submission/hpc_job_execution', 'execution_job_submission/local_job_execution', 'execution_result_acquisition', 'hpc_work_planning/execution_job_submission/api_job_execution', 'hpc_work_planning/execution_job_submission', 'hpc_work_planning/execution_job_submission/hpc_job_execution', 'hpc_work_planning/execution_job_submission/local_job_execution', 'hpc_work_planning/execution_result_acquisition', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', 'scientific_process/execution_job_submission/api_job_execution', 'scientific_process/execution_job_submission', 'scientific_process/execution_job_submission/hpc_job_execution', 'scientific_process/execution_job_submission/local_job_execution', 'scientific_process/execution_result_acquisition', 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission', 'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/execution_result_acquisition', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition')
PREFIX = 'gene_annotation_episode.episodic_workflow.root.a102'
CONFIG = {'kind': 'api', 'service': 'bvbrc_appservice',
    'execution_contract': 'bvbrc_appservice_execution_v1',
    'endpoints': {'AppService': 'https://app.example.invalid/rpc',
        'Workspace': 'https://workspace.example.invalid/rpc'}, 'scientific_adapters': []}
TRANSFORM = {'origin': 'received_fitted', 'received_from': {
    'saved_sheet': {'version': 'protein_structure_saved_sheet_v1'}}}


def observe(home, store, directory):
    cls = import_module(PREFIX + '.' + home.replace('/', '.') + '.episode').ExecutionEpisode
    services = SimpleNamespace(reference_in_context=lambda *args: True)
    binding = cls(services, store=store, directory=directory, run_id='protein-attachment-run',
        resources={'selected-api': deepcopy(CONFIG)}, initial_information={},
        tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2,
        acquired_record_unit=3, log_window_bytes=32, log_roles=[])
    authority = SimpleNamespace(legacy_returns=binding.native_protein_structure_returns,
        store=store, run_id=binding.run_id)
    module = import_module(PREFIX + '.protein_structure_tools')
    def call():
        try:
            result = module._selected_legacy_parameter_reader(authority, deepcopy(TRANSFORM))
        except Exception as error:
            return {'status': 'raised', 'exception_type': type(error).__module__ + '.' + type(error).__qualname__,
                'message': str(error)}
        return {'status': 'returned', 'value': result}
    report = {'constructor': 'returned', 'concrete_class': cls.__module__ + '.' + cls.__qualname__,
        'original_attached_reader': call(), 'negative_cases': {},
        'actual_result_receipt_or_transform_authenticated': False}
    for field, changed in (('store', None), ('run_id', 'another-run')):
        original = getattr(authority, field)
        setattr(authority, field, changed)
        report['negative_cases']['different_' + field] = call()
        setattr(authority, field, original)
    for value, key in ((None, 'no_transform'),
            ({'origin': 'caller'}, 'caller_transform'),
            ({'origin': 'received_fitted', 'received_from': {'saved_sheet': {'version': 'protein_structure_saved_sheet_v2'}}},
             'different_sheet_version')):
        report[key] = module._selected_legacy_parameter_reader(authority, value)
    return report
