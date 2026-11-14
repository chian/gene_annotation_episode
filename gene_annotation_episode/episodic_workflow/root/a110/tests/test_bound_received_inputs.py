"""Actual FBA input custody with explicitly synthetic software metadata.

The model is an opaque provided artifact; no parser, solver, native operation or
scientific producer is involved. This tests the real received-input boundary.
"""
from copy import deepcopy
import hashlib
from pathlib import PurePosixPath
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from ..state import Store
from ..episode_journal import Journal
from ..episode_receipts import EpisodeReceipts
from ..episode_bindings import BindingContext, EpisodeBindingRegistry
from ..method_loop.identities import EpisodeRef
from ..method_loop.episode import EpisodeGoal, EpisodeRequest
from ..runtime import Record
from ..execution_contracts import canonical
from ..flux_balance_execution_inputs import FluxBalanceExecutionInputs
from ..native_flux_balance_contracts import (STACK, DRIVER_MODULE, RUN_PLAN_FILENAME,
    SOURCE_FUNCTION_SHA256, flux_balance_environment)
from ..hpc_work_planning.execution_result_acquisition.episode import ExecutionEpisode


def synthetic_software():
    root = PurePosixPath('/unexecuted-synthetic-fba-callback-fixture')
    def pin(path): return {'path': str(path), 'sha256': '0' * 64, 'size_bytes': 1}
    module_root, python_home, dependencies = root / 'source', root / 'python', root / 'dependencies'
    private = module_root / 'gene_annotation_episode/episodic_workflow/root/a110'
    return {'version': 'fba_software_v1', 'python': pin(python_home / 'bin/python'),
        'python_version': 'synthetic metadata only', 'python_home': str(python_home),
        'module_root': str(module_root), 'dependency_roots': [str(dependencies)],
        'implementation_files': [pin(module_root / 'gene_annotation_episode/__init__.py'),
            *[pin(private / name) for name in ('execution_contracts.py', 'flux_balance_contracts.py',
                'native_flux_balance_contracts.py', 'native_flux_balance_storage.py',
                'native_flux_balance_cobra_glpk.py', 'native_flux_balance_driver.py')]],
        'runtime_files': [pin(python_home / 'lib/synthetic.py'), pin(dependencies / 'synthetic.py')],
        'solver_runtime_files': [pin(root / 'solver/synthetic.so')],
        'distributions': [{'name': name, 'version': version} for name, version in STACK.items()],
        'solver_interface': 'optlang.glpk_interface'}


@pytest.fixture
def selected(tmp_path, monkeypatch):
    from .. import native_lifecycle
    def forbidden(*args, **kwargs): raise AssertionError('received input test attempted native execution')
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'collect', 'wait_job'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope, run_id = store.validate_scope(), 'bound-fba-input-callback'
        journal, receipts = Journal(store, run_id), EpisodeReceipts(store, run_id)
        path = (('annotation', 'root'),)
        episode_id = EpisodeRef(run_id, path).episode_id
        inheritance = receipts.bind(episode_id, None)
        goal = EpisodeGoal.root(objective='Authenticate opaque supplied model metadata', result_contract={'role': 'annotation'})
        request = EpisodeRequest(goal, Record({'scope': scope, 'episode_assignment': {},
            'initial_report': {}, 'knowledge_inheritance': inheritance}), None).as_record()
        context = BindingContext(run_id, episode_id, 'annotation', path, scope, {}, request)
        journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'active'})
        raw = b'opaque supplied model; no scientific parser is called'
        artifact = store.artifact(raw)
        source = store.put('source', {'provider': 'synthetic-bound-input-fixture', 'accession': None,
            'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='caller', scope=scope)['id']
        receipts.receive(episode_id, [source], kind='initial')
        digest = hashlib.sha256(raw).hexdigest()
        software = synthetic_software()
        lifecycle = str(tmp_path / 'unexecuted')
        job = {'version': 'native_flux_balance_job_v1', 'operation': 'perform_flux_balance_analysis',
            'mode': 'steady_state_linear_fba', 'source_alias': 'biomni.tool.systems_biology.perform_flux_balance_analysis',
            'source_function_sha256': SOURCE_FUNCTION_SHA256,
            'model_input': {'file': {'path': str(store.path / 'artifacts' / digest[:2] / digest),
                'sha256': digest, 'size_bytes': len(raw)}, 'artifact_ref': artifact, 'format': 'cobra_json',
                'original_loader_selection': 'json_file', 'repository_identifier': None, 'acquisition_receipt_file': None},
            'constraints': None, 'objective': {'kind': 'model_default', 'reaction_id': None},
            'solver_options': {'feasibility_tolerance': None, 'optimality_tolerance': None, 'integrality_tolerance': None},
            'software': software, 'output_prefix': 'outputs', 'flux_output_name': 'flux.csv'}
        assignment = {'requested_job': {'argv': [software['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME],
            'environment': flux_balance_environment(software, attempt_directory=lifecycle + '/flux-balance-attempt', lifecycle_directory=lifecycle),
            'native_flux_balance': job}}
        versions = [{'reference': source, 'version': None, 'content_sha256': digest}]
        services = SimpleNamespace(annotation_task_required=lambda: False)
        owner = ExecutionEpisode(services, store=store, run_id=run_id, directory=tmp_path / 'workflow',
            resources=resources(), initial_information={}, tool_registry=None,
            handoff_unit=3., acquired_record_unit=2., log_window_bytes=1024, log_roles=('stdout',))
        yield SimpleNamespace(store=store, owner=owner, context=context, assignment=assignment,
            versions=versions, source=source, artifact=artifact, services=services)


def test_original_custom_callback_protocol_receives_nonempty_model(selected, monkeypatch):
    case = selected
    visited = []
    def supplied(context, reference, namespace):
        visited.append((context, reference, namespace))
        return None
    custom = SimpleNamespace(store=case.store, run_id=case.context.run_id, resolve_received_reference=supplied)
    inputs = FluxBalanceExecutionInputs(custom)
    before = list(case.store.db.iterdump())
    monkeypatch.setattr(case.store, 'get_artifact', lambda *_: pytest.fail('input admission read scientific bytes'))
    binding = inputs.validate_selected(case.context, case.assignment, input_versions=case.versions)
    assert binding['model']['witnesses'][0]['reference'] == case.source
    assert visited and all(context is case.context for context, _, _ in visited)
    custom.resolve_received_reference = lambda *_: False
    with pytest.raises(ValueError, match='protected_reference_denied'):
        inputs.validate_selected(case.context, case.assignment, input_versions=case.versions)
    assert list(case.store.db.iterdump()) == before


def test_nonempty_private_owner_input_admission_uses_its_original_callback(selected, monkeypatch):
    case = selected
    before = list(case.store.db.iterdump())
    monkeypatch.setattr(case.store, 'get_artifact', lambda *_: pytest.fail('input admission read scientific bytes'))
    value = case.owner.flux_balance_inputs.validate_selected(case.context, case.assignment, input_versions=case.versions)
    assert value['model']['witnesses'][0]['reference'] == case.source
    assert value['model']['file']['artifact_ref'] == case.artifact
    assert list(case.store.db.iterdump()) == before


def test_connected_explicit_adapter_callback_has_precedence(selected):
    case = selected
    visited = []
    custom = SimpleNamespace(store=case.store, run_id=case.context.run_id,
        resolve_received_reference=lambda *_: pytest.fail('explicit port lost precedence'))
    def supplied(context, reference, namespace): visited.append(reference)
    inputs = FluxBalanceExecutionInputs(custom, reference_access=supplied)
    value = inputs.validate_selected(case.context, case.assignment, input_versions=case.versions)
    assert value['model']['witnesses'][0]['reference'] == case.source and visited


