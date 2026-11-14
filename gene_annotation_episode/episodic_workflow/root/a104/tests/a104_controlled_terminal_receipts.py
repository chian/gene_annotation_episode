"""Explicit controlled saved-terminal ports with real Store/Journal custody.

No native program executes and these rows are not genuine historical producer
receipts. Scientific job descriptors come from required original fixtures;
fresh controlled identity/commission/return records are separately labeled.
The legacy plan policy is descriptive receipt data only. Current execution
configuration is independently fixed to 5 GiB and contains no wall-time field.
"""
from copy import deepcopy
from importlib import import_module
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
HOMES = ('hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')


def module(name):
    return import_module(PREFIX + name.replace('/', '.'))


def retained_descriptor(case, family):
    if family == 'fluorescence':
        return json.loads((case.directory / 'original-native-plan.json').read_bytes())
    with case.open_store() as store:
        row = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND "
            "json_extract(result,'$.result.version')='native_protein_structure_acquired_result_v1' ORDER BY rowid",
            (case.manifest['original_run_id'],)).fetchone()
        return json.loads(row['result'])['result']['body']['capture']['original_plan']


def construct(directory, store, case, family, home, *, returncode, publish_saved=True):
    contracts = module('execution_contracts')
    canonical, digest = contracts.canonical, contracts.digest
    Journal = module('episode_journal').Journal
    Receipts = module('episode_receipts').EpisodeReceipts
    Context = module('episode_bindings').BindingContext
    EpisodeRef = module('method_loop.identities').EpisodeRef
    Goal = module('method_loop.episode').EpisodeGoal
    Custody = module('bvbrc_appservice_custody').AppServiceCustody
    PracticalState = module('practical_execution_state').PracticalState
    practical = module('practical_execution_records')
    information_class = module('practical_receipt_information').PracticalReceiptInformation
    terminal = module('terminal_scientific_evidence')
    directory = Path(directory).resolve()
    workspace = directory / 'workspace'
    workspace.mkdir(parents=True)
    run_id = 'controlled-terminal-' + family
    journal, receipts = Journal(store, run_id), Receipts(store, run_id)
    problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    scope = {'subject_refs': problem['subject_refs']}
    empty = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    contexts = []

    def save(role, slot, assignment, *, objective):
        parent = contexts[-1] if contexts else None
        path = (() if parent is None else parent.path) + ((role, slot),)
        episode_id = EpisodeRef(run_id, path).episode_id
        goal = (Goal.root(objective=objective, result_contract=empty) if parent is None else
            Goal.child(Goal.from_record(parent.request['goal']), objective=objective, result_contract=empty))
        manifest = receipts.bind(episode_id, None if parent is None else parent.episode_id)
        request = {'goal': goal.as_record(), 'message': {'scope': scope, 'initial_report': {},
            'episode_assignment': deepcopy(assignment), 'knowledge_inheritance': manifest},
            'report_contract': None if parent is None else Custody._report_contract('Retain the controlled result', empty)}
        context = Context(run_id, episode_id, role, path, scope, assignment, request)
        journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        if parent is not None:
            index = int(slot.removeprefix('child_'))
            selection = {'kind': 'episode_child', 'role': role, 'assignment': deepcopy(assignment),
                'scope': scope, 'goal': objective, 'purpose': 'Retain the controlled result',
                'schema_json': canonical(empty), 'initial_report_json': '{}'}
            journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index,
                'action': canonical(selection), 'result': None, 'credit': None})
        contexts.append(context)
        return context

    save('scientific_process' if home.startswith('scientific_process/') else 'annotation',
        'root', {}, objective='Controlled saved-terminal contract connection')
    save('hpc', 'child_0', {}, objective='Controlled commissioning lineage')
    if home.endswith('/hpc_allocation_execution'):
        save('hpc_execution', 'child_0', {}, objective='Controlled allocation lineage')
    seed = retained_descriptor(case, family)
    original_seed = deepcopy(seed)
    # A fresh controlled transport call uses this resource's generic command
    # contract. Its retained scientific descriptors are read-only saved data.
    requested_job = (deepcopy(seed['requested_job']) if publish_saved else
        {'argv': ['/controlled-native-unavailable'], 'environment': {}})
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'controlled-' + family,
        'resource_id': 'local', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': requested_job,
        'progress_requirements': [{'key': 'handoff', 'credit': 1., 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}}
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'local': deepcopy(assignment)},
        'immutable_input_versions': [], 'constraints': {}}
    parent = save('launch', 'child_0', launch, objective='Controlled original Launch selection')
    context = save('launch_local', 'child_0', assignment, objective='Controlled saved local result')
    # This existing own-axis validator checks the whole original selection,
    # goal, scope, initial report, schema and receipt-inheritance chain. The
    # terminal reader must independently authenticate the same commission.
    admitted, index = Custody(store, run_id)._commission(context)
    assert admitted.episode_id == parent.episode_id and index == 0
    resources = {'local': {'kind': 'local', 'workspace': str(workspace),
        'policy': {'memory_bytes': 5 * 1024**3, 'scratch_bytes': 4 * 1024**3}}}
    options = dict(store=store, run_id=run_id, directory=directory, resources=resources,
        initial_information={}, tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))
    services = SimpleNamespace(annotation_task_required=lambda: False)
    launch_binding = module(home + '/execution_job_submission/local_job_execution/episode').ExecutionEpisode(services, **options)
    result_binding = module(home + '/execution_result_acquisition/episode').ExecutionEpisode(services, **options)
    if not publish_saved:
        return SimpleNamespace(store=store, journal=journal, run_id=run_id, context=context, parent=parent,
            scope=scope, launch_binding=launch_binding, result_binding=result_binding, options=options,
            family=family, source_case=case, resources=resources)
    operation_key = f'{run_id}:{context.episode_id}:0'
    command_dir = workspace / '.episode-execution' / digest({'run_id': run_id, 'episode_id': context.episode_id}) / 'commands' / digest(operation_key)
    command_dir.mkdir(parents=True)
    execution_id = str(command_dir / 'intent.json')
    plan = deepcopy(seed)
    plan['identity'] = {**plan['identity'], 'run_id': run_id, 'episode_id': context.episode_id,
        'resource_id': 'local', 'execution_id': execution_id, 'attempt_id': digest(operation_key),
        'operation_key': operation_key, 'requested_job_sha256': digest(assignment['requested_job']),
        'assignment_sha256': digest(assignment)}
    selected_module = module('library.native_' + ('protein_structure' if family == 'protein' else family) + '_contracts')
    plan['attempt_directory'] = str(command_dir / selected_module.ATTEMPT_DIRECTORY_NAME)
    filename = selected_module.RUN_PLAN_FILENAME
    validator = getattr(selected_module, 'validate_' + ('protein_structure' if family == 'protein' else family) + '_run_plan')
    assert validator(seed) == seed
    assert validator(plan) == plan
    path = command_dir / filename
    raw = canonical(plan).encode('utf-8') + b'\n'
    path.write_bytes(raw)
    captured = directory / 'controlled-captured-plan.json'
    captured.write_bytes(raw)
    file_digest = hashlib.sha256(raw).hexdigest()
    snapshot = {'path': str(path), 'phase': 'before', 'available': True,
        'captured_path': str(captured), 'sha256': file_digest, 'size_bytes': len(raw), 'source_stable_during_read': True}
    after = {**snapshot, 'phase': 'after'}
    argv = (selected_module.driver_argv(plan) if family == 'protein' else selected_module.fluorescence_driver_argv(plan))
    arguments = {'cmd': argv, 'workdir': str(workspace), 'env': deepcopy(assignment['requested_job']['environment'])}
    command = {'argv': argv, 'environment': arguments['env'], 'returncode': returncode, 'execution_id': execution_id}
    executed = {**deepcopy(arguments), 'target': 'resource', 'command_sha256': digest(arguments),
        'intent_path': execution_id, 'returncode': returncode, 'finished_at': '2026-11-11T00:00:00+00:00'}
    proof = {'version': 'terminal_scientific_command_proof_v1',
        'profile': 'native_protein_structure' if family == 'protein' else 'native_fluorescence',
        'original_plan': plan, 'plan_snapshot': snapshot, 'execution_command': executed,
        'command': command, 'input_snapshots': [snapshot], 'output_snapshots': [after]}
    outcome = {'facts': {'command': command, 'requested_job': {**deepcopy(command),
        'requested_job_sha256': digest(assignment['requested_job']), 'resource_kind': 'local',
        'status': 'completed' if returncode == 0 else 'failed', 'output_paths': [str(path)],
        'handoff': {'execution_id': execution_id, 'monitor_operation': 'exec_command', 'results_operation': 'exec_command'}}},
        'native_outcome': {'execution_command': executed, 'scientific_command_proof': proof,
            'input_snapshots': [snapshot], 'output_snapshots': [after]},
        'controlled_test_port': 'saved_native_outcome_descriptor_only_no_producer_execution'}
    assert terminal.terminal_local_job_matches(assignment, outcome)
    state = launch_binding.state(context)
    state.begin(operation_key, 'exec_command', arguments)
    journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': 'exec_command', 'arguments': arguments}), 'result': None, 'credit': None})
    validations = practical.assess_validations(assignment, outcome, state.context(), tool_name='exec_command')
    receipt = state.finish(operation_key, outcome, validations)
    information = information_class(store, run_id)
    reference = information.publish(context, receipt)
    returned = {'status': 'completed', 'record_refs': [reference], 'changed_record_refs': [reference], 'result': receipt}
    journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': 'exec_command', 'arguments': arguments}),
        'result': canonical(returned), 'credit': state.credit_view()['credit']})
    assert information.read(reference, scope)['receipt'] == receipt
    target = contracts.validate_target({'version': 'execution_target_v1', 'handle': reference,
        'run_id': run_id, 'resource_id': 'local', 'resource_kind': 'local', 'execution_id': execution_id,
        'request_sha256': digest(assignment['requested_job']), 'origin_episode_id': context.episode_id,
        'assignment': assignment, 'scope': scope})
    assert seed == original_seed
    return SimpleNamespace(store=store, journal=journal, run_id=run_id, context=context, parent=parent,
        scope=scope, target=target, proof=proof, receipt=receipt, information=information, state=state,
        launch_binding=launch_binding, result_binding=result_binding, options=options, family=family,
        plan=plan, arguments=arguments, source_case=case, reference=reference, resources=resources)
