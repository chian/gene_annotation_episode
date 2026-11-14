"""Actual current-descriptor reconstruction observations for all 57 A104 homes.

Required reusable diagnostic candidate; promote to own tests before execution.
No source action, model, provider request or native job is selected. Exact
returned/raised records are retained independently; completion is not success.
"""
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace

BINDINGS = (
    ("execution_job_submission/api_job_execution", "execution", "ExecutionEpisode"),
    ("execution_job_submission", "execution", "ExecutionEpisode"),
    ("execution_job_submission/hpc_job_execution", "execution", "ExecutionEpisode"),
    ("execution_job_submission/local_job_execution", "execution", "ExecutionEpisode"),
    ("execution_progress_assessment", "monitor", "MonitorEpisode"),
    ("execution_result_acquisition", "execution", "ExecutionEpisode"),
    ("hpc_work_planning", "hpc", "HPCEpisode"),
    ("hpc_work_planning/execution_job_submission/api_job_execution", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/execution_job_submission", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/execution_job_submission/hpc_job_execution", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/execution_job_submission/local_job_execution", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/execution_progress_assessment", "monitor", "MonitorEpisode"),
    ("hpc_work_planning/execution_result_acquisition", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/hpc_allocation_execution", "hpc", "HPCEpisode"),
    ("hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/hpc_allocation_execution/execution_job_submission", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/hpc_allocation_execution/execution_progress_assessment", "monitor", "MonitorEpisode"),
    ("hpc_work_planning/hpc_allocation_execution/execution_result_acquisition", "execution", "ExecutionEpisode"),
    ("hpc_work_planning/hpc_resource_prediction", "hpc", "HPCEpisode"),
    ("published_evidence_assessment", "literature", "LiteratureEpisode"),
    ("published_evidence_assessment/evidence_search_strategy_improvement", "literature", "LiteratureEpisode"),
    ("published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment", "literature", "LiteratureEpisode"),
    ("published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination", "literature", "LiteratureEpisode"),
    ("published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction", "literature", "LiteratureEpisode"),
    ("published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement", "literature", "LiteratureEpisode"),
    ("published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction", "literature", "LiteratureEpisode"),
    ("scientific_process", "scientific", "ScientificProcessEpisode"),
    ("scientific_process/execution_job_submission/api_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/execution_job_submission", "execution", "ExecutionEpisode"),
    ("scientific_process/execution_job_submission/hpc_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/execution_job_submission/local_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/execution_progress_assessment", "monitor", "MonitorEpisode"),
    ("scientific_process/execution_result_acquisition", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning", "hpc", "HPCEpisode"),
    ("scientific_process/hpc_work_planning/execution_job_submission/api_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/execution_job_submission", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/execution_job_submission/local_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/execution_progress_assessment", "monitor", "MonitorEpisode"),
    ("scientific_process/hpc_work_planning/execution_result_acquisition", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/hpc_allocation_execution", "hpc", "HPCEpisode"),
    ("scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment", "monitor", "MonitorEpisode"),
    ("scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition", "execution", "ExecutionEpisode"),
    ("scientific_process/hpc_work_planning/hpc_resource_prediction", "hpc", "HPCEpisode"),
    ("scientific_process/published_evidence_assessment", "literature", "LiteratureEpisode"),
    ("scientific_process/published_evidence_assessment/evidence_search_strategy_improvement", "literature", "LiteratureEpisode"),
    ("scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment", "literature", "LiteratureEpisode"),
    ("scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination", "literature", "LiteratureEpisode"),
    ("scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction", "literature", "LiteratureEpisode"),
    ("scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement", "literature", "LiteratureEpisode"),
    ("scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction", "literature", "LiteratureEpisode"),
)

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
def module(name): return importlib.import_module(PREFIX + name.replace('/', '.'))
def forbidden(*args, **kwargs): raise AssertionError('restoration_diagnostic_forbids_work')

def diagnose(directory, retain, *, inspect_constructed=None):
    from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
    from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
    from .api_cases import Responses, resources as api_resources, error_record
    directory = Path(directory)
    assert not directory.exists()
    directory.mkdir(parents=True)
    write_instruction_source(directory / 'instruction-source', 'a104')
    library = module('scientific_process_library').ScientificProcessLibrary.freeze(
        directory / 'scientific-process-library', source=directory / 'instruction-source')
    catalog = [{'name': 'fixture.inspect', 'resources': 'local',
        'description': 'Engineering restoration operand; no scientific evidence.',
        'instructions': 'No action or acquisition is executed.',
        'input_schema': module('domain').obj({'record': {'type': 'string'}})}]
    tools_library = module('scientific_tool_library').ScientificToolLibrary.freeze(
        directory / 'scientific-tool-library', catalog=catalog, tool_info=True)
    run_id = 'a104-saved-binding-observations'
    clients = Responses()
    def observe(identity, call):
        row = {'boundary': identity}
        try: row.update(status='returned', value=module('communication').plain(call()))
        except Exception as error: row.update(status='raised', error=error_record(error))
        retain(row)
    with module('state').Store(directory / 'store') as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        journal = module('episode_journal').Journal(store, run_id)
        backend = module('method_loop.durable').DurableExecutionStore(directory / 'episode-execution')
        actual_tools = module('tools').ToolRegistry(store, clients=clients)
        services = SimpleNamespace(workflow=SimpleNamespace(store=store, run_id=run_id),
            annotation_task_required=lambda: False, execute_tool=forbidden)
        shared_resources = {**resources(), **api_resources()}
        for home, kind, class_name in BINDINGS:
            def roundtrip(home=home, kind=kind, class_name=class_name):
                cls = getattr(module(home + '/episode'), class_name)
                if kind == 'scientific':
                    before = cls(services, library=library, tool_library=tools_library,
                        child_roles=('scientific_process',))
                elif kind in {'literature', 'monitor'}:
                    before = cls(services)
                elif kind == 'hpc':
                    before = cls(services, store=store, run_id=run_id, directory=directory,
                        resources=shared_resources, commissions={})
                elif kind == 'execution':
                    before = cls(services, store=store, run_id=run_id, directory=directory,
                        resources=shared_resources, initial_information={},
                        tool_registry=actual_tools, handoff_unit=1., acquired_record_unit=1.,
                        log_window_bytes=1024, log_roles=('stdout', 'stderr'))
                else: raise AssertionError('undeclared_test_kind')
                descriptor = before.as_record()
                retained_constructor = {'descriptor': deepcopy(descriptor),
                    'actual_type': type(before).__module__ + '.' + type(before).__qualname__,
                    'roles': list(before.roles), 'binding_path': before.binding_path,
                    'configured_directory': str(directory), 'run_id': run_id,
                    'provider_calls': deepcopy(clients.calls)}
                if kind == 'literature':
                    from .source_descriptor_boundaries import settings
                    retained_constructor['settings'] = settings(before)
                retain({'boundary': 'actual_constructor:' + home, 'status': 'returned',
                    'value': retained_constructor})
                # Exact original own binding callables; no synthetic progress,
                # foreign projector, parent substitute or inferred authority.
                projectors = {}
                for role in before.roles:
                    if before.credit_kind(role) == 'scientific': continue
                    if kind == 'execution':
                        callback = before.project_credit
                        definition = {'version': 'execution_received_information_credit_v1',
                            'handoff_unit': before.handoff_unit,
                            'acquired_record_unit': before.acquired_record_unit,
                            'practical_units': 'original_assignment_progress_requirements',
                            'baseline': 'original_received_information', 'repeated_gain': 0}
                    elif kind == 'hpc':
                        callback = before.credit_view
                        definition = {'version': 'hpc_credit_v1',
                            'operands': 'original_commission', 'polling_credit': 0}
                    elif kind == 'monitor':
                        reader = module('execution_service_setup')._ProgressReader(store, run_id)
                        callback = before.information_credit(reader, information_unit=.01)
                        definition = callback.as_record()
                    else: raise AssertionError('undeclared_non_scientific_test_kind')
                    projectors[role] = {'project': callback, 'definition': definition}
                kwargs = dict(store=store, journal=journal, execution_backend=backend,
                    descriptors=[deepcopy(descriptor)], job_episodes=None,
                    resource_estimator=None, role_credit_bindings=projectors,
                    directory=directory, tool_registry=actual_tools)
                if inspect_constructed is not None:
                    inspect_constructed(home, kind, before, services, kwargs)
                outcome = module('episode_composition').compose_episode_bindings(services, **kwargs)
                restored, = outcome.bindings
                record = {'original': descriptor, 'restored': restored.as_record(),
                    'original_type': type(before).__module__ + '.' + type(before).__qualname__,
                    'restored_type': type(restored).__module__ + '.' + type(restored).__qualname__,
                    'same_descriptor': descriptor == restored.as_record(),
                    'same_class': type(before) is type(restored),
                    'projector_identity': {role: outcome.role_credit_projectors[role] is value['project']
                        for role, value in projectors.items()},
                    'definitions': module('communication').plain(outcome.role_credit_definitions),
                    'original_definitions': {role: value['definition'] for role, value in projectors.items()},
                    'capabilities': module('communication').plain(outcome.resource_capabilities),
                    'expected_capabilities': before.capabilities() if kind == 'execution' else [],
                    'actual_backend_identity': outcome.progress_provider.durable_store is backend,
                    'actual_store_identity': outcome.progress_provider.store is store,
                    'actual_run_id': outcome.progress_provider.run_id,
                    'provider_calls': deepcopy(clients.calls)}
                if kind == 'literature':
                    from .source_descriptor_boundaries import settings
                    record.update(original_settings=settings(before), restored_settings=settings(restored))
                return record
            observe('saved_descriptor:' + home, roundtrip)
        assert clients.calls == [], 'constructor_or_reconstruction_acquired_provider_data'

