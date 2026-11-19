"""The A107 result acquisition binding run through the generic runner over the run's shared Store.

Real pieces only: the binding with its own A107 ``ToolRegistry`` over a ``Store``, a real ``RunJournal``, the
standard ``ModelProvider`` (never invoked: each model decision is a recorded fixture in the journal, read back
as on resume) and a native result receipt in the exact ``source`` form the HPC job route publishes, with the
captured output file it names; for a local handoff, the local job binding's own return after it published its
recorded command receipt to the Store. No model, network, HPC or command is run.
"""
import asyncio
import hashlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from yield_control import CompletionYieldController

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import A107ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.partner_presence_evidence.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_result_acquisition.\
    acquisition_source import (RECEIPT_PROVIDER, ROUTES, SNAPSHOT_PROVIDER, ResultAcquisitionSource, child_finding)
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_job_submission.local_job_execution.tests.\
    test_local_job_runtime import PATHS as LOCAL_PATHS, linked as linked_local_job, practical_assignment
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import assess_validations
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_result_acquisition.\
    episode import ExecutionEpisode

PATH = 'partner_presence_evidence/execution_result_acquisition'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
CONTINUATION = {PATH: {'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.05}}}
OUTPUT = 'job1/results.tsv'


def _entry(scope, handoffs):
    """The entry input: the scope and the handoffs in this binding's assignment form."""
    return {'objective': 'Acquire the native results of the handoffs', 'scope': scope,
            'assignment': {'handoffs': handoffs}}

def _receipt(store, tmp_path, scope, content):
    """A native result receipt as ``hpc_job_execution`` publishes it, naming one captured output snapshot."""
    captured = tmp_path / 'captured' / 'outputs'
    captured.mkdir(parents=True)
    saved = captured / hashlib.sha256(OUTPUT.encode()).hexdigest()
    saved.write_bytes(content)
    row = {'path': OUTPUT, 'phase': 'outputs', 'available': True, 'captured_path': str(saved),
           'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content),
           'source_stable_during_read': True}
    receipt = {'operation_key': 'run:episode:1', 'tool_name': 'exec_command', 'finished_at': '2026-11-18T00:00:00+00:00',
               'outcome': {'facts': {}, 'native_outcome': {'output_snapshots': [row], 'input_snapshots': []}}}
    body = {'version': 'practical_receipt_information_v1', 'run_id': 'submission_run', 'episode_id': 'episode',
            'assignment_sha256': 'a' * 64, 'scope': scope, 'receipt': receipt}
    artifact = store.artifact(canonical(body), 'application/json')
    request = store.artifact(canonical({'version': 'practical_receipt_assignment_v1'}), 'application/json')
    return store.put('source', {'provider': RECEIPT_PROVIDER, 'accession': 'practical_receipt_1', 'uri': None,
                                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
                                'version': 'practical_receipt_information_v1',
                                'retrieved_at': receipt['finished_at']}, origin='tool')['id'], saved


def _setup(tmp_path, store, slot='launch_hpc', content=b'hit\t1e-30\n'):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    scope = store.validate_scope({'subject_refs': [target]})
    receipt_ref, saved = _receipt(store, tmp_path, scope, content)
    handoff = {'request_id': 'r1', 'slot': slot, 'child_return': {'credit': 2.5, 'finding': {
        'receipt_refs': [receipt_ref], 'known_record_refs': [receipt_ref]}}}
    return (*_link(tmp_path, store, scope, handoff), receipt_ref, saved)


def _registry_settings(tmp_path):
    """Every required A107ToolRegistry setting, declared explicitly (no executables configured)."""
    return {'a107_work_directory': tmp_path / 'work', 'a107_detection_bindings': [], 'clients': PublicClients(),
            'cmsearch_executable': None, 'minimap2_executable': None, 'minimap2_cache_dir': tmp_path / 'minimap2-cache',
            'pdfinfo_executable': None, 'pdftotext_executable': None, 'pdftoppm_executable': None}


def _link(tmp_path, store, scope, handoff):
    """This binding linked over the run's Store with one assigned handoff."""
    binding = ExecutionEpisode(tool_registry=A107ToolRegistry(store, **_registry_settings(tmp_path)), api_resources={})
    collaborators = {'store': store, 'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model', tmp_path),
                     'continuation': CONTINUATION}
    journal = RunJournal(tmp_path / 'journal.sqlite')
    run = link(BindingRegistry([binding]), PATH, _entry(scope, [handoff]), run_id='acquire',
               journal=journal, collaborators=collaborators)
    return binding, run, journal


def _decide(journal, run, name, selection):
    journal.record_decision('acquire', run.episode.source._bound.path, name, {'selection': selection})


def test_output_snapshot_is_verified_and_retained_and_completes_the_handoff(tmp_path):
    with Store(tmp_path / 'state') as store:
        binding, run, journal, receipt_ref, _ = _setup(tmp_path, store)
        assert type(run.episode.source) is ResultAcquisitionSource
        controller = binding.build_controller(run.episode.source._bound, {'continuation': CONTINUATION})
        assert type(controller) is CompletionYieldController and controller.target == 1
        # An invalid first response (a path no receipt names) creates no unit; the recorded retry is admitted.
        _decide(journal, run, 'decision.0.0', {'action': 'output_snapshot', 'request_id': 'r1',
                                               'receipt_ref': receipt_ref, 'path': 'elsewhere'})
        _decide(journal, run, 'decision.0.1', {'action': 'output_snapshot', 'request_id': 'r1',
                                               'receipt_ref': receipt_ref, 'path': OUTPUT})
        result = asyncio.run(run.run())
        assert result['record'].ended_by is not None
        record = result['result'].as_record()
        assert record['credit'] == 1
        finding = record['finding']
        assert finding['acquired_request_ids'] == ['r1'] and finding['units'] == 1
        outcome, = finding['outcomes']
        assert outcome['status'] == 'completed'
        source = store.get(outcome['record_refs'][0])
        assert source['provider'] == SNAPSHOT_PROVIDER
        assert store.get_artifact(source['artifact_ref']) == b'hit\t1e-30\n'
        assert json.loads(store.get_artifact(source['request_ref']))['receipt_ref'] == receipt_ref


def test_a_changed_captured_output_is_a_failed_unit_in_the_iterator(tmp_path):
    with Store(tmp_path / 'state') as store:
        _, run, _, receipt_ref, saved = _setup(tmp_path, store)
        saved.write_bytes(b'changed after capture')
        selection = {'action': 'output_snapshot', 'request_id': 'r1', 'receipt_ref': receipt_ref, 'path': OUTPUT}
        source = run.episode.source
        _, prepared = source.admit({'selection': selection}, source.action_schema())
        outcome = asyncio.run(source._execute(0, selection, prepared))
        assert outcome['status'] == 'failed' and outcome['feedback']['code'] == 'captured_output_not_verified'
        assert source.credit == 0 and outcome['record_refs'] == []
        assert source._bound.recorder.recall('outcome.0') == outcome


def _local_job_return(tmp_path, store, scope, content):
    """The local job binding's actual return after one exec_command unit.

    The command's receipt (one captured output snapshot) is the recorded fixture: it was finished in the
    Episode's practical state before its outcome was journaled, so the unit recovers it instead of running a
    command, publishes it to the Store and returns the handoff naming it. No command or model is run.
    """
    job = tmp_path / 'resource' / 'job'
    job.mkdir(parents=True)
    output = str(job / 'results.tsv')
    assignment = practical_assignment(tmp_path, progress_requirements=[
        {'key': 'directory', 'credit': 1.0,
         'predicate': {'kind': 'path_exists', 'path': str(job), 'object_type': 'directory'}},
        {'key': 'outputs', 'credit': 0.0, 'predicate': {'kind': 'requested_job_outputs', 'output_paths': [output]}}],
        completion_keys=['directory', 'outputs'])
    _, run, _ = linked_local_job(tmp_path, store, LOCAL_PATHS[0], assignment, 'local_job', scope)
    source = run.episode.source
    captured = tmp_path / 'local_captured'
    captured.mkdir()
    saved = captured / hashlib.sha256(output.encode()).hexdigest()
    saved.write_bytes(content)
    row = {'path': output, 'phase': 'outputs', 'available': True, 'captured_path': str(saved),
           'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content),
           'source_stable_during_read': True}
    outcome = {'facts': {'paths': [{'path': str(job), 'exists': True, 'object_type': 'directory', 'sha256': None}]},
               'native_outcome': {'output_snapshots': [row], 'input_snapshots': []}}
    arguments = {'cmd': 'sh run.sh', 'workdir': str(job), 'target': 'resource', 'env': {}}
    key = run.run_id + ':' + source._bound.episode_id + ':0'
    context = source.state.context()
    source.state.begin(key, 'exec_command', arguments)
    source.state.finish(key, outcome, assess_validations(source.assignment, outcome, context, tool_name='exec_command'),
                        context_after=context)
    run.journal.record_decision(run.run_id, source._bound.path, 'decision.0.0', {'selection': {
        'tool': 'exec_command', 'cmd': 'sh run.sh', 'workdir': str(job), 'target': 'resource', 'env': []}})
    return asyncio.run(run.run())['result'].as_record(), output


def test_a_local_handoff_is_acquired_from_the_receipts_its_local_job_published(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
        scope = store.validate_scope({'subject_refs': [target]})
        local_return, output = _local_job_return(tmp_path, store, scope, b'hit\t1e-30\n')
        handoff_finding = child_finding(local_return)
        receipt_ref, = handoff_finding['receipt_refs']
        assert handoff_finding['known_record_refs'] == [receipt_ref]
        receipt = store.get(receipt_ref)
        assert receipt['provider'] == RECEIPT_PROVIDER
        assert json.loads(store.get_artifact(receipt['artifact_ref']))['scope'] == scope
        local_slot, = [slot for slot, kind in ROUTES.items() if kind == 'local']
        _, run, journal = _link(tmp_path, store, scope, {'request_id': 'r1', 'slot': local_slot,
                                                         'child_return': local_return})
        _decide(journal, run, 'decision.0.0', {'action': 'output_snapshot', 'request_id': 'r1',
                                               'receipt_ref': receipt_ref, 'path': output})
        result = asyncio.run(run.run())
        record = result['result'].as_record()
        assert record['credit'] == 1
        finding = child_finding(record)
        assert finding['acquired_request_ids'] == ['r1'] and finding['units'] == 1
        outcome, = finding['outcomes']
        assert outcome['status'] == 'completed'
        source = store.get(outcome['record_refs'][0])
        assert source['provider'] == SNAPSHOT_PROVIDER
        assert store.get_artifact(source['artifact_ref']) == b'hit\t1e-30\n'
        assert json.loads(store.get_artifact(source['request_ref']))['receipt_ref'] == receipt_ref


def test_result_acquisition_requires_its_registry_over_the_run_store(tmp_path):
    with Store(tmp_path / 'state') as store, Store(tmp_path / 'other') as other:
        binding = ExecutionEpisode(tool_registry=A107ToolRegistry(other, **_registry_settings(tmp_path)), api_resources={})
        target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
        with pytest.raises(ContractError, match='tool_registry_is_not_over_the_run_store'):
            link(BindingRegistry([binding]), PATH, _entry({'subject_refs': [target]}, [
                {'request_id': 'r1', 'slot': 'launch_hpc', 'child_return': {'credit': 1, 'finding': {}}}]),
                 run_id='acquire', journal=RunJournal(tmp_path / 'journal.sqlite'),
                 collaborators={'store': store, 'continuation': CONTINUATION,
                                'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model', tmp_path)})
