"""Actual closed A104 scientific requests/actions with original descriptor custody.

The selected engineering operation and completed UnitRecord frame are explicit
test controls. Actual Workflow, Store, Journal, admission, original controller,
closure, facts, saved form and copied-Store readers remain application methods.
No model continuation, scientific evidence or complete HPC registry is claimed.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import traceback
from unittest.mock import patch
from .head_cases import TASKS, build_case, forbidden, own, plain
from .head_cases import COMMISSION_ONLY_TASKS, original_build_denial
from .head_comparison import comparable, scientific_digest

def digest(raw): return hashlib.sha256(raw).hexdigest()
def write(path, value): path.write_text(json.dumps(plain(value), indent=2, sort_keys=True) + '\n')
def rows(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    def value(item): return {'bytes_sha256': digest(item)} if isinstance(item, bytes) else item
    return {name: sorted([[value(item) for item in row] for row in store.db.execute('SELECT * FROM "'
        + name.replace('"', '""') + '"')], key=lambda row: json.dumps(row, sort_keys=True)) for name in names}
def error_record(error):
    return {'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error),
        'code': getattr(error, 'code', None), 'diagnostic': plain(getattr(error, 'diagnostic', None))}
def observe(callback):
    try:
        value = callback()
        return {'status': 'returned', 'value': plain(value.as_record() if hasattr(value, 'as_record') else value)}
    except Exception as error:
        return {'status': 'raised', 'error': error_record(error), 'traceback': traceback.format_exc()}

def expected_initial_receipts(receipts, references):
    """Read the original receive traversal, including its semantic exclusions.

    This projection adds no receipts and reads no artifact bytes. The actual
    own-axis forward_references method retains protected source boundaries;
    collection members stay on their original paged admission path.
    """
    pending, seen = list(references), set()
    admitted = set()
    while pending:
        reference = pending.pop()
        if reference in seen:
            continue
        seen.add(reference)
        record = receipts.store.get(reference)
        if record.get('record_type') == 'collection_member':
            continue
        admitted.add(reference)
        pending.extend(ref for ref in receipts.forward_references(record) if ref not in seen)
    return sorted(admitted)

@contextmanager
def original_fixture(directory):
    from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import ScientificHeadBoundaryChecks
    class Harness(ScientificHeadBoundaryChecks): axis = 'a104'
    original = ScientificHeadBoundaryChecks.scientific.__wrapped__(Harness(), directory)
    value = next(original)
    try: yield value
    finally: original.close()

def record_actual_decision(value, selection):
    """Make a real measured call with one explicitly controlled provider reply.

    This fixture retains the original direct-action boundary. The standalone
    root's schema may reject this tool before ordinary iterator acquisition;
    that observation is saved and does not become an admitted model choice.
    """
    host, task = value.workflow, value.task
    context = {'role': task.path[-1][0], 'scope': plain(task.scope),
        'current_credit': host.source_credit_view(task)['credit'],
        'visible_record_refs': list(host.receipts.known(task.episode_id)),
        **value.binding.decision_context(host.binding_context(task), None)}
    schema = host.action_schema(task)
    response = {'selection': deepcopy(selection), 'report_update': deepcopy(task.report_values)}
    # Match only the real advertised tool branch. An absent branch remains a
    # rejected controlled response; adding a synthetic schema would broaden it.
    branches = schema['properties']['selection']['anyOf']
    matching = [branch for branch in branches if branch.get('properties', {}).get(
        'tool', {}).get('const') == selection['tool']]
    assert len(matching) <= 1
    if matching and value.runtime._json_tool_arguments(matching[0]):
        response['selection']['arguments'] = value.runtime._json(selection['arguments'])
    dispatched = []
    async def complete(episode_id, purpose, instructions, actual_context, output_schema):
        assert episode_id == task.episode_id and purpose == 'REASONING'
        assert output_schema == value.runtime._action_generation_schema(schema)
        dispatched.append({'episode_id': episode_id, 'purpose': purpose,
            'instructions': instructions, 'context': plain(actual_context), 'output_schema': output_schema})
        return deepcopy(response)
    with patch.object(host.provider, 'complete', complete):
        returned, index, actual_context, original_schema = asyncio.run(task.call(context, schema))
    assert index == 0 and task.calls == 1 and len(dispatched) == 1
    assert returned == response and original_schema == schema
    decoded = value.runtime._decode_recorded_action_response(returned, original_schema)
    assert decoded == {'selection': selection, 'report_update': task.report_values}
    row = dict(host.journal.row('runtime_model_calls', task.episode_id, index))
    request = json.loads(row['request'])
    assert row['purpose'] == 'decision' and json.loads(row['response']) == response
    assert request['context'] == actual_context and request['schema'] == schema
    assert row['timing'] is not None, 'actual_model_call_measurement_missing'
    validation = observe(lambda: value.runtime.Draft202012Validator(schema).validate(decoded))
    return {'model_call_row': row, 'provider_dispatch': dispatched[0],
        'decoded_response': decoded, 'ordinary_response_schema_validation': validation,
        'controlled_provider_response': True, 'ordinary_iterator_acquisition_claimed': False,
        'direct_action_execution_is_separate': True}

def close_actual(value, controller_input, selection):
    host, task, episode = value.workflow, value.task, value.episode
    from dataclasses import replace
    method = own('method_loop.episode')
    action_before = dict(host.journal.row('runtime_actions', task.episode_id, 0))
    assert json.loads(action_before['action']) == selection
    assert action_before['result'] is not None
    assert host.journal.row('runtime_observations', task.episode_id, 0) is None
    # This explicit finite engineering source contains the actual returned
    # action. It neither selects new science nor changes the original task's
    # response/admission outcome. The ordinary method loop owns observation,
    # controller advance, source exhaustion and both original callbacks.
    leaf = value.runtime.ActionLeaf(deepcopy(selection), extract=lambda _: controller_input,
        result=lambda _, returned: returned, label='tool:0', decision_index=0)
    class ReturnedEngineeringSource:
        def __init__(self):
            self.workflow = host
            self.remaining = iter((leaf,))
            self.reads = []
        def next(self, view):
            item = next(self.remaining, None)
            self.reads.append({'episode_id': view.episode_ref.episode_id,
                'returned_label': None if item is None else item.label,
                'controller_state': plain(view.controller_state.as_record())})
            return item
    source = ReturnedEngineeringSource()
    controlled = replace(episode, source=source)
    assert type(controlled) is type(episode)
    assert controlled.request is episode.request and controlled.grain is episode.grain
    assert controlled.on_unit is episode.on_unit and controlled.on_close is episode.on_close
    assert controlled.build_result is episode.build_result
    if value.standalone:
        context = host.context
    else:
        parent = value.parent_initialization
        saved_parent = own('episode_return_records').EpisodeReturnRecords(host.store, host.run_id,
            failure_prefix='shared_information_').context(parent['episode_id'])
        assert plain(saved_parent.request) == parent['request']
        assert episode.request.goal.parent_goal_id == saved_parent.request['goal']['goal_id']
        context = type(host.context).from_commission(tree=host.tree, run_id=host.run_id,
            parent_path=task.path[:-1], parent_goal_id=episode.request.goal.parent_goal_id,
            child_goal_id=episode.request.goal.goal_id, grain=episode.grain.name, key=episode.key,
            runtime=host.context.runtime)
    record = asyncio.run(controlled.run_async(context))
    completion = method.EpisodeCompletion.from_record(record)
    unit, = record.unit_records
    assert unit.unit_ref.episode_id == task.episode_id and unit.unit_ref.unit_index == 0
    assert unit.unit_label == 'tool:0' and unit.controller_input.as_record() == controller_input.as_record()
    step = unit.controller_step
    if record.ended_by == method.END_EXHAUSTED:
        assert step.stop is False and source.reads[-1]['returned_label'] is None
    assert dict(host.journal.row('runtime_actions', task.episode_id, 0)) == action_before
    observed = json.loads(host.journal.row('runtime_observations', task.episode_id, 0)['observation'])
    assert observed['credit'] == controller_input.as_record() and observed['step'] == plain(step.as_record())
    assert observed['unit_ref'] == unit.unit_ref.as_record() and observed['decision_index'] == 0
    returned = asyncio.run(task.finish(record))
    assert returned.as_record() == {'form': value.original.invocation['initial_report']}
    context = host.binding_context(task)
    value.binding.validate_report(context, returned.as_record()['form'], value.original.form)
    assert host.services.scientific_closed_request(context) == plain(task.request.as_record())
    return {'controller_input': controller_input.as_record(), 'controller_step': step.as_record(),
        'controller_state': record.controller_state.as_record(), 'closed_form': returned.as_record(),
        'observation': observed, 'completion': completion.as_record(),
        'finite_engineering_source_reads': source.reads, 'original_method_loop_and_callbacks': True,
        'ordinary_model_selection_claimed': False}

def capture_one(directory, task_name, standalone):
    directory.mkdir(parents=True)
    with original_fixture(directory) as original:
        value = build_carrier_case(original, task_name=task_name, standalone=standalone)
        selection = {'kind': 'tool', 'tool': 'fixture.inspect', 'arguments': {'record': original.target}}
        decision = record_actual_decision(value, selection)
        # Keep actual Workflow.execute routing, including any original root
        # denial. It must remain an observed invalid outcome, not be replaced
        # with the controlled service result that was never acquired.
        controller_input = asyncio.run(value.task.execute(selection, 0))
        action = dict(value.workflow.journal.row('runtime_actions', value.task.episode_id, 0))
        result = json.loads(action['result'])
        assert json.loads(action['action']) == selection and action['credit'] == 0.
        closed = close_actual(value, controller_input, selection)
        context = value.workflow.binding_context(value.task)
        saved = {'version': 'a104_original_scientific_carrier_v1', 'task_name': task_name,
            'standalone': standalone, 'directory': str(directory.resolve()),
            'run_id': value.workflow.run_id, 'binding_descriptor': value.binding.as_record(),
            'request': plain(value.task.request.as_record()), 'context': context.as_record(),
            'assignment': value.assignment, 'filled': value.prepared,
            'library_record': value.original.library.as_record(), 'tool_library_record': value.original.tool_library.as_record(),
            'catalog': value.original.catalog, 'declaration': value.declaration, 'task_key': value.key,
            'initial_known_record_refs': [value.original.target, value.proposed],
            'factory_provenance': {'kind': 'explicit_literal_scientific_only_factory',
                'function': __name__ + '.construct_saved', 'child_roles': ['scientific_process'],
                'historical_generic_factory_claimed': False},
            'root_projector': value.workflow.project_credit.as_record(),
            'root_projector_class': type(value.workflow.project_credit).__module__ + '.' + type(value.workflow.project_credit).__qualname__,
            'parent_initialization': value.parent_initialization,
            'selection': selection, 'action_row': action, 'returned_payload': result,
            'controlled_decision_boundary': decision,
            'acquired_operations': value.acquired, 'closed': closed, 'logical_rows': rows(value.store),
            'scope': 'genuine closed request/action; engineering service and completed-frame controls, no biological evidence'}
        write(directory / 'capture.json', saved)
    saved['files'] = {str(path.relative_to(directory)): digest(path.read_bytes())
        for path in sorted(directory.rglob('*')) if path.is_file() and path.name != 'capture.json'}
    write(directory / 'capture.json', saved)
    return saved

def capture(output):
    output.mkdir(parents=True); index = []
    for task_name in (None, *TASKS):
        for standalone in (False, True):
            directory = output / ('default' if task_name is None else task_name) / ('standalone' if standalone else 'parented')
            if standalone and task_name in COMMISSION_ONLY_TASKS:
                directory.mkdir(parents=True)
                with original_fixture(directory) as original:
                    denial = original_build_denial(original, task_name=task_name)
                record = {'version': 'a104_original_scientific_build_denial_v1',
                    'task_name': task_name, 'standalone': True, 'observation': denial,
                    'closed_carrier': False, 'files': {str(path.relative_to(directory)): digest(path.read_bytes())
                        for path in directory.rglob('*') if path.is_file()}}
                filename = directory / 'build_denial.json'; write(filename, record)
                index.append({'task_name': task_name, 'standalone': True,
                    'build_denial': str(filename.resolve()), 'build_denial_sha256': digest(filename.read_bytes())})
                write(output / 'capture_index.json', index)
                continue
            saved = capture_one(directory, task_name, standalone)
            index.append({'task_name': task_name, 'standalone': standalone,
                'capture': str((directory / 'capture.json').resolve()),
                'capture_sha256': digest((directory / 'capture.json').read_bytes()),
                'original_descriptor': saved['binding_descriptor']})
            write(output / 'capture_index.json', index)
    assert len(index) == 2 * (1 + len(TASKS))
    return index

def custody(directory):
    directory = Path(directory).resolve()
    index_path = directory / 'capture_index.json'; raw = index_path.read_bytes(); index = json.loads(raw)
    expected = {(name, standalone) for name in (None, *TASKS) for standalone in (False, True)}
    assert len(index) == len(expected) and {(row['task_name'], row['standalone']) for row in index} == expected
    proofs = []; denial_proofs = []
    for row in index:
        denied = row['standalone'] and row['task_name'] in COMMISSION_ONLY_TASKS
        assert ('build_denial' in row) is bool(denied)
        if denied:
            assert set(row) == {'task_name', 'standalone', 'build_denial', 'build_denial_sha256'}
            path = Path(row['build_denial']).resolve()
            assert path.is_relative_to(directory) and path.name == 'build_denial.json'
            metadata = path.read_bytes(); assert digest(metadata) == row['build_denial_sha256']
            saved = json.loads(metadata)
            assert saved['version'] == 'a104_original_scientific_build_denial_v1' and saved['closed_carrier'] is False
            assert (saved['task_name'], saved['standalone']) == (row['task_name'], row['standalone'])
            assert saved['observation']['returned_task'] is saved['observation']['closed_carrier'] is False
            assert set(saved['files']) == {str(item.relative_to(path.parent)) for item in path.parent.rglob('*')
                if item.is_file() and item != path}
            for relative, expected_hash in saved['files'].items():
                file = (path.parent / relative).resolve()
                assert file.is_relative_to(path.parent) and digest(file.read_bytes()) == expected_hash
            denial_proofs.append({'task_name': row['task_name'], 'standalone': True,
                'build_denial': str(path), 'build_denial_sha256': digest(metadata), 'closed_carrier': False})
            continue
        path = Path(row['capture']).resolve()
        assert path.is_relative_to(directory) and path.name == 'capture.json'
        metadata = path.read_bytes(); assert digest(metadata) == row['capture_sha256']
        saved = json.loads(metadata)
        assert saved['version'] == 'a104_original_scientific_carrier_v1'
        assert (saved['task_name'], saved['standalone']) == (row['task_name'], row['standalone'])
        assert saved['binding_descriptor'] == row['original_descriptor']
        assert saved['request']['message']['scientific_process']['mechanics_binding'] == saved['binding_descriptor']
        assert Path(saved['directory']).resolve() == path.parent
        assert set(saved['files']) == {str(item.relative_to(path.parent)) for item in path.parent.rglob('*')
            if item.is_file() and item != path}
        for relative, expected_hash in saved['files'].items():
            file = (path.parent / relative).resolve()
            assert file.is_relative_to(path.parent) and digest(file.read_bytes()) == expected_hash
        proofs.append({'task_name': row['task_name'], 'standalone': row['standalone'],
            'capture': str(path), 'capture_sha256': digest(metadata), 'original_descriptor': saved['binding_descriptor']})
    assert len(proofs) == 17 and len(denial_proofs) == 3
    return {'index_sha256': digest(raw), 'captures': proofs, 'build_denials': denial_proofs,
        'exact_distinct_task_and_placement_pairs': True}

def construct_saved(store, copied, saved):
    """Actual constructor with the exact captured literal factory operands."""
    library = own('scientific_process_library').ScientificProcessLibrary(copied / 'scientific-process-library')
    tools_library = own('scientific_tool_library').ScientificToolLibrary(copied / 'scientific-tool-library')
    assert library.as_record() == saved['library_record'] and tools_library.as_record() == saved['tool_library_record']
    binding_type = own('scientific_process.episode').ScientificProcessEpisode
    selector = own('scientific_process.task_projector' if hasattr(binding_type, 'decision_source_type')
        else 'a104_scientific_process_binding')
    projector = selector.original_task_projector(saved['assignment'])
    root_projector = projector if saved['standalone'] else own('a104_credit').A104EvolutionaryCredit()
    assert root_projector.as_record() == saved['root_projector']
    assert type(root_projector).__module__ + '.' + type(root_projector).__qualname__ == saved['root_projector_class']
    def factory(services):
        services.tool_catalog = lambda scope: deepcopy(saved['catalog'])
        services.tool_information_catalog = lambda scope: deepcopy(saved['catalog'])
        services.execute_tool = forbidden
        return binding_type(services, library=library, tool_library=tools_library,
            child_roles=('scientific_process',), yield_bindings={saved['task_key']: saved['declaration']})
    workflow = own('runtime').Workflow(store, own('tools').ToolRegistry(store),
        SimpleNamespace(complete=forbidden, has_session=lambda *args: False), Path(saved['directory']) / 'workflow',
        saved['run_id'], controller_factory=forbidden, project_credit=root_projector,
        episode_binding_factories=[factory], episode_record_receipts=True,
        initial_known_record_refs=saved['initial_known_record_refs'], annotation_child_roles=('scientific_process',),
        root_role='scientific_process' if saved['standalone'] else 'annotation',
        wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)
    return workflow

def reopen(captured, output, *, authenticated_custody, original_source_sha256, current_source_sha256):
    captured = Path(captured).resolve()
    assert custody(captured) == authenticated_custody
    output.mkdir(parents=True); results = []
    for ordinal, item in enumerate(json.loads((captured / 'capture_index.json').read_bytes())):
        if 'build_denial' in item:
            saved = json.loads(Path(item['build_denial']).read_bytes())
            fresh_directory = output / ('denial-' + str(ordinal)); fresh_directory.mkdir()
            with original_fixture(fresh_directory) as fixture:
                current = original_build_denial(fixture, task_name=item['task_name'])
            original_digest = scientific_digest(original_source_sha256)
            current_digest = scientific_digest(current_source_sha256)
            old_paths, new_paths = [], []
            assert comparable(saved['observation'], original_digest, descriptors=old_paths) == comparable(
                current, current_digest, descriptors=new_paths), 'original_build_denial_payload_changed'
            assert old_paths == new_paths
            result = {'task_name': item['task_name'], 'standalone': True, 'build_denial': True,
                'original_denial_sha256': item['build_denial_sha256'], 'observation': current,
                'closed_carrier': False, 'full_original_denial_payload_equal': True,
                'fresh_descriptor_paths': old_paths, 'capture_unchanged': custody(captured) == authenticated_custody}
            results.append(result); write(output / 'reopen.json', results)
            continue
        original = Path(item['capture']).parent; saved = json.loads((original / 'capture.json').read_bytes())
        copied = output / str(ordinal); shutil.copytree(original, copied)
        for relative, expected in saved['files'].items(): assert digest((copied / relative).read_bytes()) == expected
        result = {'task_name': saved['task_name'], 'standalone': saved['standalone'],
            'saved_descriptor': saved['binding_descriptor'], 'copied_files_verified_before_constructor': True}
        store = None
        try:
            store = own('state').Store(copied / 'state')
            assert store.db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            assert rows(store) == saved['logical_rows'], 'supported_store_changed_saved_rows'
            workflow = construct_saved(store, copied, saved)
            assert rows(store) == saved['logical_rows'], 'supported_workflow_changed_saved_rows'
            if saved['standalone']:
                assert saved['parent_initialization'] is None
            else:
                parent = saved['parent_initialization']
                assert dict(workflow.journal.row('runtime_episodes', parent['episode_id'])) == parent['runtime_episode_row']
                records = own('episode_return_records').EpisodeReturnRecords(store, workflow.run_id,
                    failure_prefix='shared_information_')
                restored_parent = records.context(parent['episode_id'])
                assert plain(restored_parent.request) == parent['request']
                assert plain(restored_parent.path) == parent['path']
                assert plain(restored_parent.scope) == parent['scope']
                assert plain(restored_parent.assignment) == parent['assignment']
                assert expected_initial_receipts(workflow.receipts, parent['initial_receipt_inputs']) == parent['initial_receipt_closure']
                assert list(workflow.receipts.known(parent['episode_id'], baseline=True)) == parent['initial_receipt_closure']
                assert expected_initial_receipts(workflow.receipts, [*parent['initial_receipt_closure'], *parent['child_initial_receipt_inputs']]) == parent['child_initial_receipt_closure']
                assert list(workflow.receipts.known(saved['context']['episode_id'], baseline=True)) == parent['child_initial_receipt_closure']
            binding = workflow.scientific_process_binding
            context = own('episode_bindings').BindingContext(**saved['context'])
            result['current_descriptor'] = binding.as_record()
            result['closed_request'] = observe(lambda: workflow.services.scientific_closed_request(context))
            result['original_context_validation'] = observe(lambda: binding.validate_context(context))
            result['new_dispatch_admission'] = observe(lambda: binding.validate_execution_context(context))
            assert result['new_dispatch_admission']['status'] == 'raised'
            result['generic_reopen'] = observe(lambda: own('episode_composition').reopen_scientific_binding(
                workflow.services, descriptor=saved['binding_descriptor'], directory=Path(saved['directory'])).as_record())
            def replay():
                runtime = own('runtime'); request = saved['request']; declaration = request['report_contract']
                contract = runtime.TypedReportContract(declaration['decision'], declaration['measurements']['schema'], lambda *_: True)
                assert plain(contract.as_record()) == declaration, 'saved_report_contract_changed'
                parent_path = tuple(tuple(item) for item in saved['context']['path'][:-1])
                parent_goal = None if saved['standalone'] else runtime.EpisodeGoal.root(
                    objective='Original annotation parent', result_contract={'role': 'annotation'})
                episode = workflow.build('scientific_process', saved['context']['path'][-1][1],
                    request['goal']['objective'], request['message']['scope'], parent=parent_goal,
                    parent_path=parent_path, contract=contract, initial=request['message']['initial_report'],
                    episode_assignment=saved['context']['assignment'],
                    scientific_process=request['message']['scientific_process'])
                assert plain(episode.request.as_record()) == request, 'saved_complete_request_changed'
                assert workflow.binding_context(episode.source).as_record() == saved['context'], 'saved_context_changed'
                episode.source.restore(); episode.source.restore_checkpoint()
                before_unfinished_queue = list(episode.source._unfinished_own_actions)
                value = asyncio.run(episode.source.execute(saved['selection'], 0)).as_record()
                assert plain(value) == saved['closed']['controller_input'], 'saved_controller_input_changed'
                assert episode.source.last_outcome == saved['returned_payload'], 'saved_returned_payload_changed'
                assert episode.source.last_outcome_index == 0
                after_unfinished_queue = list(episode.source._unfinished_own_actions)
                assert after_unfinished_queue == before_unfinished_queue, 'cached_replay_changed_scheduler_owned_queue'
                form = asyncio.run(episode.source.finish(runtime.Record({'credit': 0.}))).as_record()
                assert form == saved['closed']['closed_form'], 'saved_typed_form_changed'
                return {'request': plain(episode.request.as_record()), 'context': workflow.binding_context(episode.source).as_record(),
                    'controller_input': value, 'returned_payload': episode.source.last_outcome, 'form': form,
                    'unfinished_queue_before': before_unfinished_queue, 'unfinished_queue_after': after_unfinished_queue,
                    'full_iterator_restoration_established': False}
            with patch.object(workflow, 'execute', forbidden): result['saved_action_and_form_replay'] = observe(replay)
            result['rows_unchanged'] = rows(store) == saved['logical_rows']
            assert result['rows_unchanged']
        except Exception as error:
            result['constructor_or_probe_failure'] = {'error': error_record(error), 'traceback': traceback.format_exc()}
        finally:
            if store is not None:
                try: store.close()
                except Exception as error: result['close_failure'] = {'error': error_record(error), 'traceback': traceback.format_exc()}
            result['capture_unchanged'] = custody(captured) == authenticated_custody
            results.append(result); write(output / 'reopen.json', results)
    assert all('constructor_or_probe_failure' not in row and 'close_failure' not in row and row['capture_unchanged'] for row in results)
    return results

def compare(original, current, *, original_source_sha256, current_source_sha256):
    key = lambda row: (row['task_name'], row['standalone'])
    old, new = {key(row): row for row in original}, {key(row): row for row in current}
    assert old.keys() == new.keys() and len(old) == len(original) == len(current)
    differences = []
    for identity in old:
        if old[identity].get('build_denial') is True or new[identity].get('build_denial') is True:
            assert old[identity]['build_denial'] is new[identity]['build_denial'] is True
            assert old[identity]['original_denial_sha256'] == new[identity]['original_denial_sha256']
            assert comparable(old[identity], scientific_digest(original_source_sha256)) == comparable(
                new[identity], scientific_digest(current_source_sha256)), 'connected_original_build_denial_changed'
            continue
        assert old[identity]['saved_descriptor'] == new[identity]['saved_descriptor']
        for name in ('closed_request', 'original_context_validation', 'new_dispatch_admission', 'saved_action_and_form_replay'):
            earlier, later = deepcopy(old[identity][name]), deepcopy(new[identity][name])
            # Tracebacks are retained as separate diagnostics; source line
            # relocation is not an exception-identity change.
            earlier.pop('traceback', None); later.pop('traceback', None)
            if earlier != later: differences.append({'identity': identity, 'boundary': name, 'original': earlier, 'current': later})
    return {'introduced_boundary_changes': differences, 'saved_descriptors_and_payloads_compared_exactly': True,
        'generic_reopen_is_separate_diagnostic': True}
def build_carrier_case(original, *, task_name=None, standalone=False):
    v = SimpleNamespace(**vars(original)); store = v.store
    scope = plain(v.context.scope)
    v.form = deepcopy(original.form)
    v.form['properties']['status']['description'] = 'The assigned engineering question remains unresolved; no scientific support is asserted.'
    v.invocation = {**deepcopy(original.invocation), 'report_schema': v.form}
    assert task_name is None or task_name in TASKS
    assert tuple(own('a104_investigation').TASKS) == TASKS
    payload = {key: [] for key in store.reasoning_schema()['properties']}
    payload['hypotheses'] = [{'alias': 'original', 'subject_refs': [v.target],
        'predicate': 'biological_role', 'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}]
    committed = store.commit_reasoning(payload, scope, 'a104-head-original-proposed-annotation')
    assert committed['status'] in ('completed', 'partial')
    proposed = committed['aliases']['original']
    assignment = deepcopy(v.assignment)
    assignment['proposed_annotation_ref'] = proposed
    assignment['evidence_refs'].append(proposed)
    if task_name is not None:
        assignment['context']['a104_task'] = {'name': task_name, 'allowed_tasks': list(TASKS)}
    selector_module = ('scientific_process.task_projector'
        if hasattr(type(v.binding), 'decision_source_type') else 'a104_scientific_process_binding')
    projector = own(selector_module).original_task_projector(assignment)
    key = 'A104:' + (task_name if task_name is not None else projector.as_record()['kind'])
    declaration = {'kind': projector.yield_method, 'cutoff': .25,
        'parameters': {'uncertainty_alpha': .1}, 'credit_definition': projector.as_record()}
    runtime = own('runtime')
    tools = own('tools').ToolRegistry(store)
    acquired = []; outcome = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
        'result': {'controlled_boundary': 'selected engineering operation'}, 'feedback': None}
    def execute_tool(name, arguments, **operands):
        acquired.append({'name': name, 'arguments': deepcopy(arguments), 'operands': plain(operands)})
        return deepcopy(outcome)
    def factory(services):
        services.tool_catalog = lambda scope: deepcopy(v.catalog)
        services.tool_information_catalog = lambda scope: deepcopy(v.catalog)
        services.execute_tool = execute_tool
        return own('scientific_process.episode').ScientificProcessEpisode(services,
            library=v.library, tool_library=v.tool_library, child_roles=('scientific_process',),
            yield_bindings={key: declaration})
    root_projector = projector if standalone else own('a104_credit').A104EvolutionaryCredit()
    host = runtime.Workflow(store, tools,
        SimpleNamespace(complete=forbidden, has_session=lambda *args: False), v.directory / 'workflow',
        'a104-private-scientific-head', controller_factory=forbidden, project_credit=root_projector,
        episode_binding_factories=[factory], episode_record_receipts=True,
        initial_known_record_refs=[v.target, proposed], annotation_child_roles=('scientific_process',),
        root_role='scientific_process' if standalone else 'annotation',
        wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)
    binding = host.scientific_process_binding
    parent_path = (('annotation', 'original_parent'),)
    parent_id = own('method_loop.identities').EpisodeRef(host.run_id, parent_path).episode_id
    parent_episode = None
    if standalone:
        parent = own('episode_bindings').BindingContext(host.run_id, parent_id, 'annotation', parent_path,
            scope, {'proposed_annotation_ref': proposed}, {}, (v.target, proposed))
        host.receipts.bind(parent_id); host.receipts.receive(parent_id, [v.target, proposed], kind='initial')
    else:
        parent_episode = host.build('annotation', 'original_parent', 'Original annotation parent', scope,
            episode_assignment={'proposed_annotation_ref': proposed})
        parent = host.binding_context(parent_episode.source)
        assert parent.episode_id == parent_id and parent.path == parent_path
        assert plain(parent.scope) == scope and plain(parent.assignment) == {'proposed_annotation_ref': proposed}
        initial_receipt_inputs = [*scope['subject_refs'], *host.initial_known_record_refs]
        initial_receipt_closure = expected_initial_receipts(host.receipts, initial_receipt_inputs)
        assert list(host.receipts.known(parent_id)) == initial_receipt_closure
        assert host.journal.row('runtime_episodes', parent_id)['state'] == 'active'
    prepared = binding.prepare_invocation(parent, 'scientific_process', assignment, scope,
        'a104-original-head-invocation', invocation=v.invocation)
    parent_goal = None if standalone else parent_episode.request.goal
    contract = runtime.TypedReportContract(v.invocation['purpose'], v.form,
        lambda reference: reference in (v.target, proposed))
    build_arguments = {'parent': parent_goal, 'parent_path': () if standalone else parent_path,
        'contract': contract, 'initial': v.invocation['initial_report'],
        'episode_assignment': prepared['assignment'], 'scientific_process': prepared['scientific_process']}
    episode = host.build('scientific_process', 'original_child', v.invocation['objective'], scope,
        **build_arguments)
    task = episode.source
    binding.validate_execution_context(host.binding_context(task))
    assert host.specialist(task) is binding
    assert host.journal.row('runtime_episodes', task.episode_id) is not None
    parent_initialization = None
    if not standalone:
        repository = host.shared_information_repository()
        recovered_parent = repository.parent(host.binding_context(task), require_active=True)
        assert recovered_parent.episode_id == parent_id
        assert plain(recovered_parent.request) == plain(parent.request)
        inheritance = dict(store.db.execute('SELECT * FROM runtime_receipt_inheritance '
            'WHERE run_id=? AND episode_id=?', (host.run_id, task.episode_id)).fetchone())
        assert inheritance['parent_episode_id'] == parent_id
        child_initial_receipt_inputs = list(dict.fromkeys([*prepared['assignment']['evidence_refs'],
            *([prepared['assignment']['proposed_annotation_ref']]
              if prepared['assignment'].get('proposed_annotation_ref') else [])]))
        child_initial_receipt_closure = expected_initial_receipts(host.receipts,
            [*initial_receipt_closure, *child_initial_receipt_inputs])
        assert list(host.receipts.known(task.episode_id)) == child_initial_receipt_closure
        parent_initialization = {'episode_id': parent_id, 'path': plain(parent.path),
            'scope': plain(parent.scope), 'assignment': plain(parent.assignment),
            'request': plain(parent.request), 'runtime_episode_row': dict(host.journal.row('runtime_episodes', parent_id)),
            'child_receipt_inheritance': inheritance, 'root_projector': root_projector.as_record(),
            'actual_parent_built_before_child': True, 'manual_parent_journal_insert': False,
            'initial_receipt_inputs': initial_receipt_inputs,
            'initial_receipt_closure': initial_receipt_closure,
            'child_initial_receipt_inputs': child_initial_receipt_inputs,
            'child_initial_receipt_closure': child_initial_receipt_closure,
            'selected_child_projector': projector.as_record()}
    return SimpleNamespace(workflow=host, binding=binding, task=task, episode=episode,
        store=store, original=v, runtime=runtime, projector=projector, proposed=proposed,
        assignment=assignment, prepared=prepared, declaration=declaration, key=key,
        acquired=acquired, outcome=outcome, standalone=standalone, task_name=task_name,
        build_arguments=build_arguments, parent_initialization=parent_initialization)

