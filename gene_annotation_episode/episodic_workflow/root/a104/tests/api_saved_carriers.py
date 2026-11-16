"""Supported A104 closed-carrier capture/read, with exact descriptor custody.

Actual Workflow.build/on_close/facts write the archive and carrier. An actual
controlled-response API action supplies the API payload and credit. The parent
Launch carrier uses its actual execution.capabilities action. Only the loop's
completed UnitRecord is supplied by the harness; no model/continuation loop is
claimed. These are explicit standalone invocations of existing private homes,
not API authorization by an HPC plan. No hash alias or saved-row rewriting.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from .api_cases import HOMES, Responses, assignment, canonical, error_record, module, rows

CLOSED = 'execution_closed_operational_credit_v1'
SCHEMA = {'type': 'object', 'properties': {'completed': {
    'type': 'boolean', 'x-source': 'execution_completed'}},
    'required': ['completed'], 'additionalProperties': False}


def write(path, value):
    path.write_text(json.dumps(canonical(value), indent=2, sort_keys=True) + '\n')


def forbidden(*args, **kwargs):
    raise AssertionError('closed_read_reprojected_or_acquired_new_work')


def build_case(store, directory, home, role, client):
    """Explicit literal own-home constructors, including original operands.

    A direct factory record is retained as such. It is never relabeled as the
    former global ExecutionServiceFactory or inferred from equal descriptors.
    """
    from .api_cases import resources
    runtime = module('runtime')
    run_id = 'a104-closed-' + hashlib.sha256((home + ':' + role).encode()).hexdigest()[:16]
    tools = module('tools').ToolRegistry(store, clients=client)
    paths = [home.rsplit('/', 1)[0]]
    paths += [paths[0] + '/' + leaf for leaf in ('api_job_execution', 'local_job_execution', 'hpc_job_execution')]
    paths += [paths[0].removesuffix('execution_job_submission') + 'execution_result_acquisition']
    def factory(path):
        def construct(services):
            return module(path + '/episode').ExecutionEpisode(services, store=store,
                directory=directory / 'execution', run_id=run_id, resources=resources(),
                initial_information={}, tool_registry=tools, handoff_unit=3., acquired_record_unit=2.,
                log_window_bytes=1024, log_roles=('stdout', 'stderr'),
                require_private_yield=True, task_yield_profiles={
                    'launch_api:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
                    'launch:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
                    'results:api_uniprot': {'cutoff': .5, 'parameters': {}}})
        return construct
    workflow = runtime.Workflow(store, tools, object(), directory / 'workflow', run_id,
        controller_factory=forbidden, project_credit=lambda *args, **kwargs: 0,
        episode_binding_factories=[factory(path) for path in paths],
        episode_record_receipts=True, initial_known_record_refs=[],
        annotation_child_roles=(), root_role=role,
        wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)
    # Root-role standalone invocation is a supported constructor interface;
    # factory/caller provenance remains explicit rather than a forged run row.
    return workflow, {'kind': 'explicit_literal_private_factories_v1',
        'home_paths': paths, 'root_role': role,
        'factory_implementation': __name__ + '.build_case',
        'descriptors': workflow.episode_bindings.as_record(),
        'historical_global_factory_authority_claimed': False}


def estimator_provenance(owner, context):
    controller = owner.yield_controller(context, 0., 'original-carrier-epoch')
    contextual = getattr(controller.estimator, 'estimate_with_context', None)
    return {'practical_estimator': owner.practical_estimator(context).as_record(),
        'controller_type': type(controller).__module__ + '.' + type(controller).__qualname__,
        'controller_state': controller.state().as_record(), 'cost': controller.cost,
        'settings': controller.settings.as_record(),
        'contextual_estimator': None if contextual is None else contextual.as_record(),
        'handoff_unit': owner.handoff_unit, 'acquired_record_unit': owner.acquired_record_unit}


def close_actual_action(workflow, episode, tool, value):
    """Supply one observed completed unit for this actual already-returned action."""
    runtime = module('runtime')
    source = episode.source
    role, key = source.path[-1]
    unit_ref = module('method_loop.identities').UnitRef(source.episode_id, 0)
    unit = module('method_loop.episode').UnitRecord(tool + ':0', value, None, 'controlled-unit-closure', unit_ref)
    record = module('method_loop.episode').EpisodeRecord(role, key, 1, 'controlled_fixture',
        (unit,), None, episode.request, path=source.path, end_reason='controlled completed-unit frame',
        episode_ref=module('method_loop.identities').EpisodeRef(workflow.run_id, source.path))
    observed = {'label': unit.unit_label, 'unit_ref': unit_ref.as_record(), 'credit': value.as_record(),
        'step': None, 'decision_index': 0}
    workflow.journal.save('runtime_observations', {'episode_id': source.episode_id,
        'unit_index': 0, 'observation': runtime._json(observed)})
    episode.on_close(record)
    facts = workflow.facts(source, completion_record=record)
    assert CLOSED in facts
    form = module('communication').form_with_facts({}, SCHEMA, facts)
    workflow.specialist(source).validate_report(workflow.binding_context(source), form, SCHEMA)
    workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
        'facts': runtime._json({**facts, 'interpretations': {}}), 'form': runtime._json(form)})
    return facts, form


def capture_one(directory, home, role):
    directory.mkdir(parents=True)
    client = Responses()
    runtime = module('runtime')
    with module('state').Store(directory / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        workflow, factory = build_case(store, directory, home, role, client)
        requested = assignment(scope['subject_refs'][0])
        producer = None
        if role == 'results':
            api = workflow.build('launch_api', 'original-producer', 'Acquire original API handoff', scope,
                episode_assignment=requested)
            returned = asyncio.run(api.source.execute({'kind': 'tool', 'tool': 'api.uniprot.record', 'arguments': {}}, 0))
            producer_action = dict(workflow.journal.row('runtime_actions', api.source.episode_id, 0))
            producer = json.loads(producer_action['result'])
            assert producer['status'] == 'completed'
            close_actual_action(workflow, api, 'api.uniprot.record', returned)
            handoff, = producer['record_refs']
            selected_assignment = {'version': 'execution_results_assignment_v1',
                'handoff_ref': handoff, 'selector': {}}
        else:
            selected_assignment = requested if role == 'launch_api' else {
                'version': 'execution_launch_assignment_v1', 'requests': {'uniprot': requested},
                'immutable_input_versions': [], 'constraints': {}}
        contract = runtime.TypedReportContract('Return original completion status', SCHEMA, lambda *_: True)
        # Initial references, actual own-role initialization, input validation,
        # projection and report validation remain application implementations.
        episode = workflow.build(role, 'original', 'Controlled original API carrier', scope,
            contract=contract, episode_assignment=selected_assignment)
        source, context = episode.source, workflow.binding_context(episode.source)
        owner = workflow.specialist(source)
        assert type(source) is getattr(owner, 'decision_source_type', runtime.DecisionSource)
        original_estimator = estimator_provenance(owner, context)
        tool = {'launch_api': 'api.uniprot.record', 'launch': 'execution.capabilities',
            'results': 'api.uniprot.collect'}[role]
        selection = {'kind': 'tool', 'tool': tool, 'arguments': {}}
        value = asyncio.run(source.execute(selection, 0))
        saved_action = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
        payload = json.loads(saved_action['result'])
        assert payload['status'] == 'completed'
        assert len(client.calls) == (0 if role == 'launch' else 1)
        facts, form = close_actual_action(workflow, episode, tool, value)
        selected = {**workflow.record_selection(source.episode_id), **workflow.progress_selection(source)}
        descriptor = owner.as_record()
        assert module('execution_contracts').digest(descriptor) == facts[CLOSED]['binding_sha256']
        with patch.object(owner, '_live_project_credit', forbidden), patch.object(store, 'get_artifact', forbidden):
            assert owner.credit_view(context, selected) == facts[CLOSED]['view']
        snapshot = rows(store)
        result = {'home': owner.binding_path,
            'api_home': home, 'role': role, 'directory': str(directory.resolve()),
            'run_id': workflow.run_id, 'factory': factory,
            'context': context.as_record(), 'descriptor': descriptor, 'selection': selected,
            'request': episode.request.as_record(), 'carrier': facts[CLOSED],
            'form': form, 'facts': facts, 'action_row': saved_action, 'controller_input': value.as_record(),
            'logical_rows': snapshot, 'transport_calls': client.calls,
            'original_estimator_provenance': original_estimator, 'actual_api_producer_outcome': producer,
            'controlled_port': 'Completed UnitRecord observation/closure; actual selected service/capabilities action',
            'whole_loop_or_hpc_admission_claimed': False}
        write(directory / 'capture.json', result)
    result['files'] = {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob('*')) if path.is_file() and path.name != 'capture.json'}
    write(directory / 'capture.json', result)
    return result

