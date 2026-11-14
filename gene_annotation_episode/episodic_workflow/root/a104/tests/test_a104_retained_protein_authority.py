"""Actual typed protein reader authority using immutable original336 inputs."""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.tests.execution_input_version_probe import PARENTS, CHILDREN
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_native_disposable_store import unpack_protein as unpack
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
HOMES = tuple('/'.join(part for part in (parent, child) if part) for parent in PARENTS for child in CHILDREN)


@pytest.fixture(scope='module')
def retained(tmp_path_factory):
    case = unpack(tmp_path_factory.mktemp('original336-protein'))
    yield case
    case.verify_unchanged()


def actual_owner(store, directory, home, case):
    cls = import_module(PREFIX + home.replace('/', '.') + '.episode').ExecutionEpisode
    owner = cls(SimpleNamespace(annotation_task_required=lambda: False), store=store,
        run_id=case.manifest['original_run_id'], directory=directory, resources=resources(),
        initial_information={}, tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))
    owner.directory = case.logical_root / 'run'
    case.seal_store(store)
    return owner


def authenticate_saved_case(store, owner, case):
    saved = json.loads((case.directory / 'CASE.json').read_bytes())
    results, returns = owner.native_protein_structure_results, owner.native_protein_structure_returns
    rows = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL "
        "AND json_extract(result,'$.result.version')='native_protein_structure_acquired_result_v1' ORDER BY rowid",
        (owner.run_id,)).fetchall()
    receipts = [json.loads(row['result'])['result'] for row in rows]
    assert len(receipts) == 3
    for receipt in receipts:
        intent = receipt['body']['intent']
        assert results.receipts.read_completed(episode_id=intent['episode_id'],
            operation_key=intent['operation_key'], scope=intent['scope']) == receipt
        assert receipt['publication']['delivery_complete'] is True
        assert results.read_result_authority(receipt['publication']['custody'],
            scope=intent['scope'])['custody'] == receipt['publication']['custody']
        context = returns.context(intent['episode_id'])
        assert results.own_fact_groups(context, verify_artifacts=False) == receipt['publication']['facts']
    contexts = [returns.context(row['episode_id']) for row in store.db.execute(
        'SELECT episode_id FROM runtime_episodes WHERE run_id=?', (owner.run_id,))]
    science = {plain(context.assignment)['context']['fixture_phase']: context
        for context in contexts if context.role == 'scientific_process'}
    assert set(science) == {'earlier', 'coordinate', 'align_compare'}
    for context in science.values():
        selection = plain(context.assignment)['selection']
        assert selection['evidence_axis']['option_id'] == 'A101'
        assert selection['thought_pattern']['option_id'] == 'P01'
    return saved, receipts, science


@pytest.mark.parametrize('home', HOMES)
def test_real_protein_receipts_preserve_typed_grants_earlier_denials_and_reopen(
        tmp_path, monkeypatch, retained, home):
    case = retained
    error_type = import_module(PREFIX + 'library.protein_structure_authority').ProteinStructureOperandError
    with case.control_transport(monkeypatch), case.open_store() as store:
        owner = actual_owner(store, tmp_path / 'constructor', home, case)
        saved, baseline, science = authenticate_saved_case(store, owner, case)
        returns = owner.native_protein_structure_returns
        assert type(returns) is import_module(PREFIX + 'library.native_protein_structure_returns').NativeProteinStructureReturns
        aligner, early = science['align_compare'], science['earlier']
        assert aligner.episode_id == case.workflow_proof['alignment_events'][0]['episode_id']
        for row in saved['returned'][:2]:
            descriptor, = row['sequences']
            for use in ('sequence_align', 'structure_correspondence'):
                authority = returns.authenticate_received_sequence(aligner, descriptor, required_use=use)
                assert authority['custody'] == descriptor['custody']
            assert store.get_artifact(descriptor['sequence_file']['artifact_ref']) == b'AGST'
            for reference, namespace in ((descriptor['reference_ref'], 'reference'),
                    (descriptor['sequence_file']['artifact_ref'], 'artifact')):
                assert owner._protein_reference_access(aligner, reference, namespace) is True
                assert owner.resolve_received_reference(aligner, reference, namespace) is True
                assert owner.resolve(aligner, reference, namespace) is True
                assert owner._versions([{'reference': reference, 'version': None,
                    'content_sha256': descriptor['sequence_file']['sha256']}], plain(aligner.scope), context=aligner) is None
                assert owner._protein_reference_access(early, reference, namespace) is False
                assert owner.resolve_received_reference(early, reference, namespace) is False
                assert owner.resolve(early, reference, namespace) is False
                with pytest.raises(error_type, match='original_commission_mismatch'):
                    owner._versions([{'reference': reference, 'version': None, 'content_sha256': None}],
                        plain(early.scope), context=early)
            with pytest.raises(error_type) as denied:
                returns.authenticate_received_sequence(early, descriptor, required_use='sequence_align')
            assert denied.value.issue['code'] == 'sequence_not_received'
            wrong = deepcopy(descriptor)
            wrong['custody']['result_operation_key'] += '9'
            with pytest.raises(error_type):
                returns.authenticate_received_sequence(aligner, wrong, required_use='sequence_align')
        descriptor, = saved['returned'][2]['saved']
        for use in ('recalculate', 'select_projection', 'use_transform'):
            authority = returns.authenticate_received_saved_sheet(aligner, descriptor, required_use=use)
            assert authority['custody'] == descriptor['custody']
        for file in (descriptor['sheet_file'], descriptor['original_components_file']):
            reference = file['artifact_ref']
            assert owner._protein_reference_access(aligner, reference, 'artifact') is True
            assert owner.resolve_received_reference(aligner, reference, 'artifact') is True
            assert owner.resolve(aligner, reference, 'artifact') is True
            assert owner._versions([{'reference': reference, 'version': None,
                'content_sha256': file['sha256']}], plain(aligner.scope), context=aligner) is None
            assert owner._protein_reference_access(early, reference, 'artifact') is False
        assert owner._protein_reference_access(aligner, descriptor['custody']['result_receipt_key'], None) is False
        assert owner._protein_reference_access(aligner, descriptor['sheet_file']['artifact_ref'], 'protein_structure_sheet') is False
        with pytest.raises(error_type) as denied:
            returns.authenticate_received_saved_sheet(early, descriptor, required_use='recalculate')
        assert denied.value.issue['code'] == 'saved_sheet_not_received'

    with case.control_transport(monkeypatch), case.open_store() as reopened:
        owner = actual_owner(reopened, tmp_path / 'reopened-constructor', home, case)
        again, receipts, science = authenticate_saved_case(reopened, owner, case)
        assert again == saved and receipts == baseline
        descriptor = again['returned'][0]['sequences'][0]
        assert owner.native_protein_structure_returns.authenticate_received_sequence(
            science['align_compare'], descriptor, required_use='sequence_align')['custody'] == descriptor['custody']
        with pytest.raises(error_type):
            owner.native_protein_structure_returns.authenticate_received_sequence(
                science['earlier'], descriptor, required_use='sequence_align')
    assert case.transported_reads
