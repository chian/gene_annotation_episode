"""Resource wiring with authentic saved bytes and explicitly controlled dispatch.

No native scientific executable runs here. The four saved615 outputs are copied
by a controlled subprocess fixture into newly owned attempts. Root's separate
Workflow verification owns fresh native/whole requested-return evidence.
"""
import base64
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_blast_masking_driver as driver
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_progress import ExecutionProgressProvider
from gene_annotation_episode.native_blast_masking_contracts import (
    requested_job_from_native_blast_masking, validate_original_bundle)
from gene_annotation_episode.native_blast_masking_local import PLAN_NAME, local_blast_masking_plan
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import assess_validations, validate_assignment
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.state import Store


FIXTURES = Path(__file__).resolve().parents[1] / 'verification' / 'tool_graders_blast_masking_resource_wiring_2026-10-28_618' / 'fixtures'
MODES = [('dustmasker', 'mask'), ('segmasker', 'mask'),
         ('windowmasker', 'mask'), ('windowmasker', 'create_counts')]
POLICY = {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3, 'wall_seconds': None}


def selector():
    return {'version': 'native_blast_masking_result_selector_v1', 'mode': 'native_result',
        'records': {'mode': 'all'}, 'quantities': [], 'statistics_fields': [],
        'statistics_unit_codes': [], 'include_checks': True, 'artifacts': [],
        'saved_data': [], 'saved_sheet_ref': None}


@contextmanager
def environment(tmp_path, monkeypatch, program='dustmasker', mode='mask', returncode=0):
    saved = FIXTURES / (program + '_' + mode)
    evidence = json.loads((saved / 'native_evidence.json').read_text())
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    executable = tmp_path / 'controlled-executable'
    executable.write_bytes(b'controlled fixture; never executed\n')
    executable.chmod(0o700)
    job = deepcopy(evidence['plan']['requested_job']['native_blast_masking'])
    job['software'] = {'executable': str(executable),
        'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'engine_version': 'controlled_resource_fixture_618'}
    job['operation']['engine_version'] = job['software']['engine_version']
    for operand, original in zip(job['operands'], evidence['bundle']['inputs']):
        path = workspace / ('supplied-' + operand['role'])
        path.write_bytes((saved / original['relative_path']).read_bytes())
        operand['path'] = str(path)
    request = requested_job_from_native_blast_masking(job)
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'selected618',
        'resource_kind': 'local', 'resource_id': 'local618', 'workspace': str(workspace),
        'endpoint': 'completed_job_outputs', 'requested_job': request,
        'progress_requirements': [{'key': 'outputs', 'credit': 1, 'predicate': {
            'kind': 'requested_job_outputs', 'output_paths': [str(workspace / 'later-requested-output')]}}],
        'completion_keys': ['outputs'], 'initial_context': {'revision': 0,
            'cwd': str(workspace), 'environment': {}}, 'inventory_snapshot': {},
        'constraints': {'allocation': deepcopy(POLICY)}}
    configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_blast_masking': [{'program': program, 'mode': mode, 'software': job['software'],
            'output_formats': [job['operation']['output_format']],
            'masking_styles': [job['operation']['masking_style']]}]}
    operations = LocalPracticalOperations(configuration)
    operations.validate_assignment(validate_assignment(assignment))
    calls, views, bundles = [], {}, {}

    def controlled_command(argv, **kwargs):
        # Copy original measured bytes; this is a dispatch fixture, not a new
        # native measurement. The actual615 bundle remains untouched.
        path = Path(kwargs['cwd'])
        primary = next(row for row in job['outputs'] if row['role'] not in {'stdout', 'stderr'})
        (path / primary['relative_path']).write_bytes((saved / primary['relative_path']).read_bytes())
        kwargs['stdout'].write(b'controlled fixture stdout\x00\xff\n')
        kwargs['stderr'].write(b'controlled fixture stderr\n')
        return SimpleNamespace(returncode=returncode)

    def start(handle):
        calls.append(str(handle.path))
        body = handle.read()
        body['stage'] = 'released'
        handle.path.write_text(json.dumps(body))
        plan = json.loads((handle.path.parent / PLAN_NAME).read_text())
        bundle = driver.run_native_blast_masking(plan)
        bundles[str(handle.path)] = bundle
        views[str(handle.path)] = {'state': 'returned', 'terminal': True, 'quiescent': True,
            'metadata': {'policy': deepcopy(POLICY), 'native_returncode': 1 if bundle['failures'] else 0,
                'elapsed_seconds': 0.25, 'duration_measure': 'systemd_service_wall_seconds',
                'service_exit': {'EXIT_CODE': 'exited'}}}

    monkeypatch.setattr(driver.subprocess, 'run', controlled_command)
    monkeypatch.setattr(native, 'start_prepared', start)
    monkeypatch.setattr(native, 'resume_start', lambda *a: pytest.fail('no automatic resume in this fixture'))
    monkeypatch.setattr(native, 'status', lambda handle: deepcopy(views[str(handle.path)]))
    with Store(tmp_path / 'store') as store:
        fasta = tmp_path / 'scope.fa'
        fasta.write_text('>first\nACGTACGT\n>second\nAACCGGTT\n')
        store.create_problem(fasta, molecule='dna')
        scope = store.validate_scope({'subject_refs': [store.targets()[0]['id']]})
        journal = Journal(store, 'run618')
        receipts = PracticalReceiptInformation(store, 'run618')

        def owner(episode_id, selected_assignment=None, selected_scope=None):
            selected_assignment = selected_assignment or assignment
            selected_scope = selected_scope or scope
            request_message = {'message': {'scope': selected_scope, 'episode_assignment': selected_assignment}}
            context = BindingContext('run618', episode_id, 'launch_local',
                (('annotation', 'root'), ('launch_local', episode_id)), selected_scope,
                selected_assignment, request_message)
            with store.transaction():
                journal.save('runtime_episodes', {'episode_id': episode_id,
                    'path': canonical(plain(context.path)), 'request': canonical(request_message),
                    'initial_credit': 0, 'state': 'running'})
            state = PracticalState(tmp_path / ('practical-' + episode_id), 'run618',
                episode_id, selected_assignment)
            return context, state

        context, state = owner('local-child618')

        def publish(outcome, *, index=0, tool='practical.job.start', arguments=None,
                    selected_context=None, selected_state=None):
            selected_context, selected_state = selected_context or context, selected_state or state
            arguments = arguments or {}
            key = f'run618:{selected_context.episode_id}:{index}'
            with store.transaction():
                journal.save('runtime_actions', {'episode_id': selected_context.episode_id,
                    'decision_index': index, 'action': canonical({'kind': 'tool',
                        'tool': tool, 'arguments': arguments}), 'result': None, 'credit': None})
            selected_state.begin(key, tool, arguments)
            receipt = selected_state.finish(key, outcome, assess_validations(
                selected_state.assignment, outcome, selected_state.context(), tool_name=tool))
            ref = receipts.publish(selected_context, receipt)
            result = {'status': 'completed', 'record_refs': [ref],
                'changed_record_refs': [], 'result': receipt}
            with store.transaction():
                store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                    (canonical(result), 'run618', selected_context.episode_id, index))
            return ref, result

        def execute(*, index=0, tool='practical.job.start', arguments=None):
            arguments = arguments or {}
            key = f'run618:{context.episode_id}:{index}'
            outcome, changed = operations._execute(state, tool, arguments, key)
            assert changed is None
            ref, result = publish(outcome, index=index, tool=tool, arguments=arguments)
            return outcome, ref, result

        progress = ExecutionProgressProvider(store, run_id='run618', directory=tmp_path / 'progress',
            resources={'local618': configuration}, api_execution=None,
            log_window_bytes=9, log_roles=('stdout', 'stderr'))
        yield SimpleNamespace(store=store, scope=scope, assignment=assignment,
            configuration=configuration, operations=operations, state=state, context=context,
            calls=calls, views=views, bundles=bundles, execute=execute, publish=publish,
            owner=owner, progress=progress, targets=progress.targets, saved=saved, evidence=evidence)


@pytest.mark.parametrize('program,mode', MODES)
def test_selected_dispatch_target_selector_and_exact_read(tmp_path, monkeypatch, program, mode):
    with environment(tmp_path, monkeypatch, program, mode) as e:
        outcome, ref, result = e.execute()
        execution_id = outcome['facts']['requested_job']['execution_id']
        assert e.calls == [execution_id]
        plan = local_blast_masking_plan(e.assignment, execution_id)
        assert outcome['native_outcome']['native_blast_masking_plan'] == plan
        assert plan['identity']['episode_id'] == e.context.episode_id
        target = e.targets.read_target(ref, e.scope)
        assert target['origin_episode_id'] == e.context.episode_id
        description = e.targets.describe_target(ref, e.scope, selector=selector())
        assert description['service_or_program'] == program
        assert description['mode'] == mode
        assert description['output_format'] == 'native_blast_masking_bundle_v1'
        assert description['selected_outputs'] == e.assignment['requested_job']['native_blast_masking']['outputs']
        assert description['result_selection'] == selector()
        extractor = description['extractors'][1]
        assert 'saved_data' in extractor['return_fields']
        assert ('execution.masking_saved_data' in extractor['return_fact_sources'])
        assert bool(extractor['calculators']) == (mode == 'mask')
        observed = e.targets.observe_target(target, operation_key='observe618')
        assert observed['state'] == 'completed' and observed['result_available']
        assert observed['measurements'] == [{'measure': 'systemd_service_wall_seconds', 'seconds': 0.25}]
        assert {r['role'] for r in observed['outputs']} == {'stdout', 'stderr', 'native_blast_masking_bundle', 'statistics' if mode == 'create_counts' else 'mask'}
        path = str(Path(plan['attempt_directory']) / 'selected.out')
        read = e.targets.read_file(target, path=path, offset=3, limit=17)
        assert base64.b64decode(read['bytes_base64']) == (e.saved / 'selected.out').read_bytes()[3:20]
        assert e.state.begin('run618:local-child618:0', 'practical.job.start', {})['receipt'] == result['result']
        e.execute(index=1, tool='practical.job.collect')
        e.execute(index=2)
        assert e.calls == [execution_id]


@pytest.mark.parametrize('bad', ['resource_kind', 'resource_id', 'unbound', 'software',
    'format', 'style', 'workspace', 'allocation', 'memory', 'scratch', 'wall'])
def test_binding_allocation_and_workspace_fail_before_dispatch(tmp_path, monkeypatch, bad):
    with environment(tmp_path, monkeypatch) as e:
        assignment, config = deepcopy(e.assignment), deepcopy(e.configuration)
        if bad == 'resource_kind': assignment['resource_kind'] = 'hpc'
        elif bad == 'resource_id': assignment.pop('resource_id')
        elif bad == 'unbound': config.pop('native_blast_masking')
        elif bad == 'software': config['native_blast_masking'][0]['software']['sha256'] = '0' * 64
        elif bad in {'format', 'style'}:
            config['native_blast_masking'][0].update(output_formats=['fasta'], masking_styles=['soft'])
        elif bad == 'workspace': assignment['workspace'] = str(tmp_path / 'outside')
        elif bad == 'allocation': assignment['constraints']['allocation']['memory_bytes'] //= 2
        elif bad == 'memory': config['policy']['memory_bytes'] += 1
        elif bad == 'scratch': config['policy']['scratch_bytes'] += 1
        elif bad == 'wall': config['policy']['wall_seconds'] = 1
        with pytest.raises(ValueError):
            LocalPracticalOperations(config).validate_assignment(validate_assignment(assignment))
        assert not e.calls


def test_failed_partial_handoff_retry_and_original_ownership(tmp_path, monkeypatch):
    with environment(tmp_path, monkeypatch, returncode=3) as e:
        first, ref, _ = e.execute()
        old = first['facts']['requested_job']['execution_id']
        target = e.targets.read_target(ref, e.scope)
        assert first['facts']['requested_job']['status'] == 'failed'
        assert not e.targets.usable_handoff(target)
        assert e.targets.returnable_handoff(target)
        partial = e.targets.observe_target(target, operation_key='partial')
        assert partial['state'] == 'failed' and partial['result_available']
        assert e.bundles[old]['returncode'] == 3
        assert e.bundles[old]['failures']
        for key, wrong in [('run_id', 'other'), ('origin_episode_id', 'observer'),
                           ('resource_id', 'other'), ('attempt_id', '0' * 64),
                           ('original_operation_key', 'other'), ('requested_job_sha256', '0' * 64)]:
            with pytest.raises(ValueError, match='original_attempt_mismatch'):
                e.operations.observe_execution(e.assignment, old, **{key: wrong})
        e.execute(index=1)
        assert e.calls == [old]
        new, _, _ = e.execute(index=2, arguments={'retry_failed_execution_id': old})
        assert new['facts']['requested_job']['execution_id'] != old
        assert len(e.calls) == 2
        assert e.targets.read_target(ref, e.scope) == target


@pytest.mark.parametrize('condition', ['wrong_id', 'running', 'unknown_rc', 'killed', 'unsealed'])
def test_uncertain_or_unselected_retry_never_dispatches(tmp_path, monkeypatch, condition):
    with environment(tmp_path, monkeypatch, returncode=3) as e:
        first, _, _ = e.execute()
        old = first['facts']['requested_job']['execution_id']
        retry_id = old
        if condition == 'wrong_id': retry_id += '-wrong'
        elif condition == 'running': e.views[old].update(state='running', terminal=False)
        elif condition == 'unknown_rc': e.views[old]['metadata']['native_returncode'] = None
        elif condition == 'killed': e.views[old]['metadata']['service_exit']['EXIT_CODE'] = 'killed'
        elif condition == 'unsealed':
            (Path(first['native_outcome']['native_blast_masking_plan']['attempt_directory']) / 'bundle.json').unlink()
        outcome, _, _ = e.execute(index=1, arguments={'retry_failed_execution_id': retry_id})
        assert outcome['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
        assert e.calls == [old]


def test_saved_receipt_replay_after_native_paths_removed(tmp_path, monkeypatch):
    with environment(tmp_path, monkeypatch, returncode=3) as e:
        outcome, ref, _ = e.execute()
        target = e.targets.read_target(ref, e.scope)
        job = e.assignment['requested_job']['native_blast_masking']
        shutil.rmtree(Path(outcome['facts']['requested_job']['execution_id']).parent)
        Path(job['software']['executable']).unlink()
        for operand in job['operands']: Path(operand['path']).unlink()
        def forbid(*args, **kwargs): pytest.fail('historical target must not inspect current native state')
        monkeypatch.setattr(e.targets.operations['local618'], 'validate_assignment', forbid)
        monkeypatch.setattr(native, 'status', forbid)
        assert e.targets.read_target(ref, e.scope) == target
        assert e.targets.returnable_handoff(target)
        assert len(e.calls) == 1


def test_receiver_receipt_ancestry_preserves_native_owner(tmp_path, monkeypatch):
    with environment(tmp_path, monkeypatch) as e:
        _, original_ref, _ = e.execute()
        original = e.targets.read_target(original_ref, e.scope)
        collected, _ = e.operations._execute(e.state, 'practical.job.collect', {}, 'receiver-observation')
        assignment = deepcopy(e.assignment)
        assignment['assignment_id'] = 'received618'
        receiver, receiver_state = e.owner('observer618', assignment)
        reference, _ = e.publish(collected, tool='practical.job.collect',
            arguments={'receipt_ref': original_ref}, selected_context=receiver, selected_state=receiver_state)
        target = e.targets.read_target(reference, e.scope)
        assert target['origin_episode_id'] == original['origin_episode_id'] == 'local-child618'
        assert target['assignment'] == original['assignment']
        assert e.targets.observe_target(target, operation_key='observer-again')['state'] == 'completed'
        with pytest.raises(ValueError, match='ancestry_cycle'):
            e.targets._native(reference, e.scope, _seen=(reference,))
        bad_context, bad_state = e.owner('unlinked618', assignment)
        bad_ref, _ = e.publish(collected, tool='practical.job.collect',
            selected_context=bad_context, selected_state=bad_state)
        with pytest.raises(ContractError, match='outside_scope'):
            e.targets.read_target(bad_ref, e.scope)
        assert len(e.calls) == 1


def test_receiver_ancestry_requires_its_own_scope_and_exact_attempt(tmp_path, monkeypatch):
    with environment(tmp_path, monkeypatch, returncode=3) as e:
        outcome, original_ref, _ = e.execute()
        original_id = outcome['facts']['requested_job']['execution_id']
        collected, _ = e.operations._execute(e.state, 'practical.job.collect', {}, 'observation-only')
        other_scope = {'subject_refs': [e.store.targets()[1]['id']]}
        broad_scope = {'subject_refs': [row['id'] for row in e.store.targets()]}
        receiver, state = e.owner('wrong-scope618', selected_scope=other_scope)
        wrong_scope_ref, _ = e.publish(collected, tool='practical.job.collect',
            arguments={'receipt_ref': original_ref}, selected_context=receiver, selected_state=state)
        with pytest.raises(ContractError, match='outside_scope'):
            e.targets.read_target(wrong_scope_ref, broad_scope)
        retry, _, _ = e.execute(index=1, arguments={'retry_failed_execution_id': original_id})
        receiver, state = e.owner('wrong-attempt618')
        wrong_attempt_ref, _ = e.publish(retry, tool='practical.job.collect',
            arguments={'receipt_ref': original_ref}, selected_context=receiver, selected_state=state)
        with pytest.raises(ContractError, match='outside_scope'):
            e.targets.read_target(wrong_attempt_ref, broad_scope)
        assert len(e.calls) == 2


@pytest.mark.parametrize('damage', ['input', 'outside', 'changed', 'symlink'])
def test_file_reads_confined_to_selected_original_bundle(tmp_path, monkeypatch, damage):
    with environment(tmp_path, monkeypatch) as e:
        outcome, ref, _ = e.execute()
        target = e.targets.read_target(ref, e.scope)
        plan = outcome['native_outcome']['native_blast_masking_plan']
        path = Path(plan['attempt_directory']) / 'selected.out'
        if damage == 'input': path = Path(e.assignment['requested_job']['native_blast_masking']['operands'][0]['path'])
        elif damage == 'outside': path = tmp_path / 'outside-output'
        elif damage == 'changed': path.write_bytes(b'changed')
        elif damage == 'symlink':
            path.unlink()
            path.symlink_to(e.saved / 'selected.out')
        with pytest.raises((ValueError, OSError)):
            e.targets.read_file(target, path=str(path), offset=0, limit=20)
        assert len(e.calls) == 1


@pytest.mark.parametrize('program,mode', MODES[:3])
def test_saved_actual_native_bundles_keep_original_owner_and_measurements(program, mode):
    # Pure validation of saved actual615 bundles. Counts068 uses the historical
    # pre070 generated-binding identity; it is preserved, not rewritten here.
    directory = FIXTURES / (program + '_' + mode)
    evidence = json.loads((directory / 'native_evidence.json').read_text())
    assert validate_original_bundle(evidence['bundle'], evidence['plan']) == evidence['bundle']
    for row in evidence['bundle']['artifacts']:
        raw = (directory / row['relative_path']).read_bytes()
        assert len(raw) == row['size_bytes']
        assert hashlib.sha256(raw).hexdigest() == row['sha256']


def test_progress_replay_preserves_one_observation(tmp_path, monkeypatch):
    with environment(tmp_path, monkeypatch) as e:
        _, ref, _ = e.execute()
        fields = ['execution_status', 'measurements', 'log_windows', 'result_available']
        first = e.progress.observe(ref, fields, e.scope, operation_key='monitor618:0')
        def forbid(*args, **kwargs): pytest.fail('saved monitoring replay must not poll')
        monkeypatch.setattr(e.targets, 'read_target', forbid)
        monkeypatch.setattr(e.targets, 'observe_target', forbid)
        assert e.progress.observe(ref, fields, e.scope, operation_key='monitor618:0') == first
        assert len(e.calls) == 1
