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
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
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


def capture(output):
    output.mkdir(parents=True)
    observations = []
    for home in HOMES:
        for role in ('launch_api', 'launch', 'results'):
            target = output / home.replace('/', '__') / role
            try:
                result = capture_one(target, home, role)
                observations.append({'home': home, 'role': role, 'status': 'captured',
                    'capture': str((target / 'capture.json').resolve()),
                    'capture_sha256': hashlib.sha256((target / 'capture.json').read_bytes()).hexdigest(),
                    'descriptor': result['descriptor'], 'carrier': result['carrier']})
            except Exception as error:
                import traceback
                observations.append({'home': home, 'role': role, 'status': 'raised',
                    'error': error_record(error), 'traceback': traceback.format_exc()})
            write(output / 'capture_index.json', observations)
    assert len(observations) == 18
    if any(row['status'] != 'captured' for row in observations):
        raise AssertionError('actual_closed_carrier_capture_incomplete_see_retained_observations')
    return observations


def capture_custody(captured):
    """Bind every metadata byte and exact owner before any Store constructor."""
    captured = Path(captured).resolve()
    index_path = captured / 'capture_index.json'
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    expected = {(home, role) for home in HOMES for role in ('launch_api', 'launch', 'results')}
    assert len(index) == len(expected) == 18
    assert {(row['home'], row['role']) for row in index} == expected
    assert all(row['status'] == 'captured' for row in index)
    metadata = []
    for row in index:
        path = Path(row['capture']).resolve()
        assert path.is_relative_to(captured) and path.name == 'capture.json'
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == row['capture_sha256']
        saved = json.loads(raw)
        assert (saved['api_home'], saved['role']) == (row['home'], row['role'])
        assert saved['descriptor'] == row['descriptor'] and saved['carrier'] == row['carrier']
        assert Path(saved['directory']).resolve() == path.parent
        expected_home = (row['home'] if row['role'] == 'launch_api' else row['home'].rsplit('/', 1)[0]
            if row['role'] == 'launch' else row['home'].rsplit('/', 1)[0].removesuffix('execution_job_submission')
            + 'execution_result_acquisition')
        assert saved['home'] == expected_home
        assert saved['descriptor']['binding_id'] == saved['home']
        assert set(saved['files']) == {str(file.relative_to(path.parent)) for file in path.parent.rglob('*')
            if file.is_file() and file != path}
        for relative, wanted in saved['files'].items():
            file = (path.parent / relative).resolve()
            assert file.is_relative_to(path.parent) and file.is_file()
            assert hashlib.sha256(file.read_bytes()).hexdigest() == wanted
        metadata.append({'home': row['home'], 'role': row['role'],
            'capture': str(path), 'capture_sha256': digest,
            'descriptor': saved['descriptor'], 'carrier': saved['carrier']})
    return {'captured_directory': str(captured), 'index_sha256': hashlib.sha256(index_bytes).hexdigest(),
        'metadata': metadata, 'exact_eighteen_distinct_owners': True}


def compare_reopen_boundaries(original, current):
    """Changed task class locations are recorded; returned scientific/credit
    payloads and exact exception identities remain the original boundaries.

    Descriptor composition stays separately diagnostic. A changed/refused
    closed read or saved-action replay raises after all observations are saved.
    """
    def keyed(values):
        result = {(row['home'], row['role']): row for row in values}
        assert len(result) == len(values) == 18
        return result
    old, new = keyed(original), keyed(current)
    assert old.keys() == new.keys()
    differences, compared = [], []
    for key in old:
        for boundary in ('closed_read', 'saved_source_replay'):
            previous, actual = deepcopy(old[key].get(boundary)), deepcopy(new[key].get(boundary))
            assert previous is not None and actual is not None
            original_type = previous.pop('source_type', None)
            current_type = actual.pop('source_type', None)
            if previous != actual:
                differences.append({'home': key[0], 'role': key[1], 'boundary': boundary,
                    'original': previous, 'current': actual})
            compared.append({'home': key[0], 'role': key[1], 'boundary': boundary,
                'original_source_type': original_type, 'current_source_type': current_type,
                'full_payload_or_exception_identity_equal': previous == actual})
    return {'comparisons': compared, 'introduced_boundary_changes': differences,
        'saved_descriptor_composition_is_separate_diagnostic': True}


def reopen(captured, output, *, authenticated_custody):
    """Read an exact copied Store with its supported constructor.

    Current literal construction and saved-descriptor composition are distinct
    observations. A fingerprint mismatch remains a denial, never an alias.
    """
    assert capture_custody(captured) == authenticated_custody
    output.mkdir(parents=True)
    index = json.loads((captured / 'capture_index.json').read_text())
    assert len(index) == 18 and all(value['status'] == 'captured' for value in index)
    results = []
    for ordinal, row in enumerate(index):
        saved_path = Path(row['capture'])
        assert saved_path.is_relative_to(captured.resolve())
        saved = json.loads(saved_path.read_text())
        original = saved_path.parent
        for relative, expected in saved['files'].items():
            assert hashlib.sha256((original / relative).read_bytes()).hexdigest() == expected
        copied = output / str(ordinal)
        shutil.copytree(original, copied)
        for relative, expected in saved['files'].items():
            assert hashlib.sha256((copied / relative).read_bytes()).hexdigest() == expected
        result = {'home': saved['home'], 'role': saved['role'], 'original_descriptor': saved['descriptor'],
            'copied_bytes_verified_before_constructor': True}
        store = None
        try:
            store = module('state').Store(copied / 'store')
            assert store.db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            assert rows(store) == saved['logical_rows']
            client = Responses()
            # Original directory/configuration remains an original operand.
            # A closed read may not open artifacts or acquire fresh work.
            workflow, factory = build_case(store, Path(saved['directory']), saved['api_home'], saved['role'], client)
            assert rows(store) == saved['logical_rows'], 'supported_reconstruction_changed_original_metadata'
            owner = workflow.episode_bindings.for_binding_path(saved['home'])
            context = module('episode_bindings').BindingContext(**saved['context'])
            result['current_descriptor'] = owner.as_record()
            result['current_estimator_provenance'] = estimator_provenance(owner, context)
            assert result['current_estimator_provenance'] == saved['original_estimator_provenance'], 'original_estimator_callback_identity_changed'
            before = rows(store)
            with patch.object(owner, '_live_project_credit', forbidden):
                with patch.object(store, 'get_artifact', forbidden):
                    try:
                        value = owner.credit_view(context, saved['selection'])
                        assert value == saved['carrier']['view']
                        result['closed_read'] = {'status': 'returned', 'view': value}
                    except Exception as error:
                        result['closed_read'] = {'status': 'raised', 'error': error_record(error)}
                try:
                    declared = saved['request']['report_contract']
                    contract = module('runtime').TypedReportContract(declared['decision'],
                        declared['measurements']['schema'], lambda *_: True)
                    assert contract.as_record() == declared
                    child = workflow.build(saved['role'], saved['context']['path'][-1][1],
                        saved['request']['goal']['objective'], saved['context']['scope'],
                        contract=contract, initial=saved['request']['message']['initial_report'],
                        episode_assignment=saved['context']['assignment'])
                    assert child.request.as_record() == saved['request']
                    assert workflow.binding_context(child.source).as_record() == saved['context']
                    child.source.restore()
                    child.source.restore_checkpoint()
                    selected = json.loads(saved['action_row']['action'])
                    original_payload = json.loads(saved['action_row']['result'])
                    returned = asyncio.run(child.source.execute(selected, 0)).as_record()
                    assert returned == saved['controller_input']
                    assert child.source.last_outcome == original_payload
                    assert child.source.last_outcome_index == 0
                    assert child.source._unfinished_own_actions == []
                    result['saved_source_replay'] = {'status': 'restored_original_request_action_payload_and_credit',
                        'source_type': type(child.source).__module__ + '.' + type(child.source).__qualname__,
                        'controller_input': returned, 'original_payload': original_payload}
                except Exception as error:
                    result['saved_source_replay'] = {'status': 'raised', 'error': error_record(error)}
            try:
                module('episode_composition').compose_episode_bindings(workflow.services, store=store,
                    journal=workflow.journal, execution_backend=workflow.execution_backend,
                    descriptors=saved['factory']['descriptors'], job_episodes=None,
                    resource_estimator=None, role_credit_bindings={}, directory=Path(saved['directory']) / 'workflow',
                    tool_registry=workflow.tools)
                result['saved_descriptor_composition'] = {'status': 'returned'}
            except Exception as error:
                result['saved_descriptor_composition'] = {'status': 'raised', 'error': error_record(error)}
            assert rows(store) == before and client.calls == []
            result['rows_unchanged_after_reads'] = True
            result['current_matches_original_descriptor'] = result['current_descriptor'] == saved['descriptor']
        except Exception as error:
            import traceback
            result['constructor_or_probe_failure'] = {'error': error_record(error), 'traceback': traceback.format_exc()}
        finally:
            if store is not None:
                try:
                    store.close()
                except Exception as error:
                    result['close_failure'] = error_record(error)
            try:
                result['original_capture_files_unchanged'] = all(
                    hashlib.sha256((original / relative).read_bytes()).hexdigest() == expected
                    for relative, expected in saved['files'].items())
            except Exception as error:
                result['original_capture_files_unchanged'] = False
                result['capture_custody_failure'] = error_record(error)
            results.append(result)
            write(output / 'reopen.json', results)
    assert all('constructor_or_probe_failure' not in result and 'close_failure' not in result
        and result['original_capture_files_unchanged'] for result in results)
    # Restoration refusals are explicit observations. They are not treated as
    # successful saved workflow restoration or suppressed by the runner.
    return results
