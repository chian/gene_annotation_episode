"""Narrow actual A104 constructor/descriptor/admission/reopen observation.

This diagnostic retains returned and raised outcomes separately. Completion of
the probe does not assert admission, scientific validation or saved restoration.
The only supplied operation is a controlled engineering catalog; none executes.
"""
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
import traceback

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104'
def own(name): return import_module(PREFIX + '.' + name)
def forbidden(*args, **kwargs): raise AssertionError('original scientific diagnostic forbids acquisition')
def observe(callback):
    try:
        value = callback()
        return {'status': 'returned', 'value': own('communication').plain(value)}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'code': getattr(error, 'code', None), 'traceback': traceback.format_exc()}

def run(output):
    from gene_annotation_episode.workflow_budget import active_budget
    from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
    output = Path(output).resolve()
    assert output.is_relative_to(Path(active_budget()['run_directory']).resolve()) and not output.exists()
    output.mkdir(parents=True)
    result = {'version': 'a104_original_scientific_head_probe_v1', 'observations': {},
        'source_scope': 'original current descriptor, actual own binding and Workflow constructors',
        'full_registry_claimed': False, 'historical_saved_restoration_claimed': False,
        'scientific_or_native_execution_claimed': False}
    def retain(): (output / 'probe.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    store = None
    try:
        write_instruction_source(output / 'instruction-source', 'a104')
        library = own('scientific_process_library').ScientificProcessLibrary.freeze(output / 'library', source=output / 'instruction-source')
        catalog = [{'name': 'fixture.inspect', 'resources': 'local',
            'description': 'Controlled engineering operation; not evidence.',
            'instructions': 'No scientific interpretation or acquisition.',
            'input_schema': own('domain').obj({'record': {'type': 'string'}})}]
        tool_library = own('scientific_tool_library').ScientificToolLibrary.freeze(output / 'tools', catalog=catalog, tool_info=True)
        store = own('state').Store(output / 'state')
        problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        target = problem['subject_refs'][0]; scope = store.validate_scope()
        services = SimpleNamespace(tool_catalog=lambda scope: deepcopy(catalog),
            tool_information_catalog=lambda scope: deepcopy(catalog),
            reference_in_scope=lambda ref, scope, namespace: ref == target and namespace in (None, 'subject'),
            scientific_credit=lambda context, selection: {'credit': 0.},
            scientific_received_results=lambda context: [], scientific_frozen_results=lambda context: [],
            scientific_reference=lambda *args: False, execute_tool=forbidden)
        binding = own('scientific_process.episode').ScientificProcessEpisode(services,
            library=library, tool_library=tool_library, child_roles=('scientific_process',))
        descriptor = binding.as_record()
        result['original_descriptor'] = descriptor
        result['observations']['binding_constructor'] = {'status': 'returned',
            'type': type(binding).__module__ + '.' + type(binding).__qualname__}
        result['observations']['self_descriptor_compatible'] = observe(lambda:
            own('episode_composition').scientific_binding_compatible(descriptor, descriptor))
        result['observations']['generic_descriptor_reopen'] = observe(lambda:
            own('episode_composition').reopen_scientific_binding(services, descriptor=descriptor,
                directory=output).as_record())
        selected = {'version': own('scientific_process_records').SELECTION_VERSION,
            'evidence_axis': library.reference('A104'), 'thought_pattern': library.reference('P01'),
            'child_tool_info': [{'name': 'fixture.inspect', 'resources': 'local'}]}
        assignment = {'selection': selected, 'evidence_refs': [target], 'constraints': {}, 'context': {}}
        schema = own('domain').obj({'status': {'type': 'string', 'enum': ['unresolved']}})
        invocation = {'objective': 'Original unresolved A104 question', 'purpose': 'Return original unresolved status',
            'report_schema': schema, 'initial_report': {'status': 'unresolved'}}
        parent_path = (('annotation', 'original'),)
        identities = own('method_loop.identities'); run_id = 'a104-original-head-probe'
        parent = own('episode_bindings').BindingContext(run_id,
            identities.EpisodeRef(run_id, parent_path).episode_id, 'annotation', parent_path, scope, {}, {}, (target,))
        prepared = None
        def prepare():
            nonlocal prepared
            prepared = binding.prepare_invocation(parent, 'scientific_process', assignment, scope,
                'original-head-invocation', invocation=invocation)
            return prepared
        result['observations']['prepare_invocation'] = observe(prepare)
        if prepared is not None:
            path = parent_path + (('scientific_process', 'original_child'),)
            request = {'goal': {'objective': invocation['objective']},
                'report_contract': {'decision': invocation['purpose'], 'measurements': {'schema': schema}},
                'message': {'scope': scope, 'episode_assignment': prepared['assignment'],
                    'scientific_process': prepared['scientific_process'],
                    'scientific_invocation_ref': own('scientific_process_records').scientific_invocation_ref(run_id, path),
                    'initial_report': invocation['initial_report']}}
            context = own('episode_bindings').BindingContext(run_id,
                identities.EpisodeRef(run_id, path).episode_id, 'scientific_process', path,
                scope, prepared['assignment'], request, (target,))
            result['original_prepared_request'] = request
            result['observations']['validate_context'] = observe(lambda: binding.validate_context(context))
            result['observations']['validate_execution_context'] = observe(lambda: binding.validate_execution_context(context))
        runtime = own('runtime')
        for standalone in (False, True):
            label = 'standalone' if standalone else 'parented'; holder = {}
            def constructor():
                tools = own('tools').ToolRegistry(store)
                def factory(original_services):
                    original_services.tool_catalog = lambda scope: deepcopy(catalog)
                    original_services.tool_information_catalog = lambda scope: deepcopy(catalog)
                    original_services.execute_tool = forbidden
                    return own('scientific_process.episode').ScientificProcessEpisode(original_services,
                        library=library, tool_library=tool_library, child_roles=('scientific_process',))
                workflow = runtime.Workflow(store, tools, SimpleNamespace(complete=forbidden), output / label,
                    run_id + '-' + label, controller_factory=forbidden, project_credit=lambda *args, **kwargs: {'credit': 0.},
                    episode_binding_factories=[factory], episode_record_receipts=True,
                    initial_known_record_refs=[target], annotation_child_roles=('scientific_process',),
                    root_role='scientific_process' if standalone else 'annotation',
                    wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)
                holder['workflow'] = workflow
                return {'binding_records': workflow.episode_bindings.as_record(), 'root_role': workflow.root_role}
            result['observations'][label + '_workflow_constructor'] = observe(constructor)
            if 'workflow' not in holder: continue
            workflow = holder['workflow']; owner = workflow.scientific_process_binding
            parent_id = identities.EpisodeRef(workflow.run_id, parent_path).episode_id
            workflow.receipts.bind(parent_id); workflow.receipts.receive(parent_id, [target], kind='initial')
            parent = own('episode_bindings').BindingContext(workflow.run_id, parent_id, 'annotation', parent_path,
                scope, {}, {}, (target,))
            def build():
                filled = owner.prepare_invocation(parent, 'scientific_process', assignment, scope,
                    'original-workflow-invocation', invocation=invocation)
                contract = runtime.TypedReportContract(invocation['purpose'], schema, lambda ref: ref == target)
                goal = None if standalone else runtime.EpisodeGoal.root(objective='Original annotation', result_contract={'role': 'annotation'})
                episode = workflow.build('scientific_process', 'original_child', invocation['objective'], scope,
                    parent=goal, parent_path=() if standalone else parent_path,
                    contract=contract, initial=invocation['initial_report'],
                    episode_assignment=filled['assignment'], scientific_process=filled['scientific_process'])
                holder['episode'] = episode
                return {'request': episode.request.as_record(), 'episode_id': episode.source.episode_id,
                    'task_type': type(episode.source).__module__ + '.' + type(episode.source).__qualname__}
            result['observations'][label + '_actual_build'] = observe(build)
            if 'episode' in holder:
                result['observations'][label + '_actual_admission'] = observe(lambda:
                    owner.validate_execution_context(workflow.binding_context(holder['episode'].source)))
            retain()
        result['runtime_episode_rows'] = [dict(row) for row in store.db.execute('SELECT * FROM runtime_episodes ORDER BY run_id,episode_id')]
        result['original_versions'] = {'descriptor': descriptor['version'],
            'self_compatible': result['observations']['self_descriptor_compatible']}
    except Exception as error:
        result['setup_failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'traceback': traceback.format_exc()}
        raise
    finally:
        if store is not None:
            try: store.close()
            except Exception as error:
                result['close_failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
                    'message': str(error), 'traceback': traceback.format_exc()}
        retain()
    assert 'close_failure' not in result
    return result
