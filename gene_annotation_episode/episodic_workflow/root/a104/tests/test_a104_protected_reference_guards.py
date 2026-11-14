"""Actual owners and saved grants; no native work or synthetic successful result.

The positive protein path is the original independently explicit reference
grant. It does not impersonate a completed protein result. Fluorescence coverage
here establishes reader installation and invalid-receipt denial only; its
positive saved-sheet chain has separate required coverage.
"""
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a104.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a104.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a104.state import Store
from gene_annotation_episode.episodic_workflow.root.a104.tests.execution_input_version_probe import PARENTS, CHILDREN
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources

HOMES = tuple('/'.join(part for part in (parent, child) if part) for parent in PARENTS for child in CHILDREN)
PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'


def owner(store, directory, home):
    cls = import_module(PREFIX + home.replace('/', '.') + '.episode').ExecutionEpisode
    return cls(SimpleNamespace(annotation_task_required=lambda: False), store=store,
        run_id='a104-protected-reference-controls', directory=directory, resources=resources(),
        initial_information={}, tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))


def root_context(store, run_id, scope):
    journal = Journal(store, run_id)
    receipts = EpisodeReceipts(store, run_id)
    path = (('annotation', 'root'),)
    episode_id = EpisodeRef(run_id, path).episode_id
    manifest = receipts.bind(episode_id, None)
    request = {'goal': {'goal_id': 'a104-protected-fixture', 'objective': 'Check original saved read authority'},
        'message': {'scope': scope, 'episode_assignment': {}, 'knowledge_inheritance': manifest, 'initial_report': {}},
        'report_contract': None}
    context = BindingContext(run_id, episode_id, 'annotation', path, scope, {}, request)
    journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
        'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    receipts.receive(episode_id, scope['subject_refs'], kind='initial')
    return context, journal, receipts


def protein_records(store, artifact):
    source = store.put('source', {'provider': 'episode.execution_result', 'accession': 'negative-provenance-fixture',
        'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
        'version': 'native_protein_structure_bundle_v1', 'retrieved_at': None,
        'auxiliary_artifact_refs': []}, origin='tool')['id']
    reference = store.put('reference', {'reference_type': 'protein', 'source_ref': source,
        'accession': 'original-protected-sequence', 'label': 'Synthetic protected ancestry',
        'sequence_ref': artifact, 'molecule': 'protein', 'length': 8, 'term_refs': [], 'context_refs': []}, origin='tool')['id']
    feature = store.put('feature', {'subject_ref': reference, 'kind': 'sequence_region',
        'segments': [{'start': 0, 'end': 3}], 'strand': '+', 'context_refs': []}, origin='reasoning')['id']
    product = store.put('product', {'parent_refs': [feature], 'molecule': 'protein',
        'sequence_ref': store.artifact(b'MAC', 'text/plain'), 'derivation': 'extraction',
        'context_refs': [], 'footprint': []}, origin='tool')['id']
    return source, reference, feature, product


@pytest.mark.parametrize('home', HOMES)
def test_actual_owner_nonempty_validation_and_original_independent_grant(tmp_path, home):
    path = tmp_path / 'store'
    directory = tmp_path / 'workflow'
    with Store(path) as store:
        manifest_path = tmp_path / 'two-protein-targets.json'
        manifest_path.write_text(canonical({'schema_version': 1, 'entries': [
            {'sequence': 'MACDEFGH', 'format': 'raw', 'molecule': 'protein', 'use': 'target', 'name': 'input'},
            {'sequence': 'WACDEFGH', 'format': 'raw', 'molecule': 'protein', 'use': 'target', 'name': 'outside-assigned-scope'},
        ]}) + '\n')
        problem = store.create_problem(manifest_path=manifest_path)
        subject, other = problem['subject_refs']
        scope = {'subject_refs': [subject]}
        assert subject != other and other not in scope['subject_refs']
        assert store.get(subject)['record_type'] == store.get(other)['record_type'] == 'input'
        binding = owner(store, directory, home)
        context, journal, receipts = root_context(store, binding.run_id, scope)
        subject, = scope['subject_refs']
        record = store.get(subject)
        artifact = record['sequence_ref']
        version = {'reference': subject, 'version': None,
            'content_sha256': hashlib.sha256(store.get_artifact(artifact)).hexdigest()}
        assert binding._versions([version], scope, context=context) is None
        for field, value in (('version', 'different-original-version'), ('content_sha256', '0' * 64)):
            with pytest.raises(ValueError, match='execution_input_version_conflict'):
                binding._versions([{**version, field: value}], scope, context=context)
        other_parse = store.get(problem['initial_parse_refs'][1])
        assert other_parse['status'] == 'completed'
        with pytest.raises(ValueError, match='execution_input_outside_assigned_scope'):
            binding._versions([{'reference': other, 'version': None, 'content_sha256': None}], scope, context=context)
        for name in ('native_expression_nmf_results', 'native_expression_nmf_returns', 'atac_results',
                'atac_returns', 'native_chromatin_interaction_results', 'native_chromatin_interaction_returns'):
            assert getattr(binding, name) is None
        for attribute, module, class_name in (
            ('native_protein_structure_results', 'native_protein_structure_results', 'NativeProteinStructureResults'),
            ('native_protein_structure_returns', 'native_protein_structure_returns', 'NativeProteinStructureReturns'),
            ('native_fluorescence_results', 'native_fluorescence_results', 'NativeFluorescenceResults'),
            ('native_fluorescence_returns', 'fluorescence_returns', 'FluorescenceReturns')):
            assert type(getattr(binding, attribute)) is getattr(import_module(PREFIX + 'library.' + module), class_name)
        error = import_module(PREFIX + 'library.protein_structure_authority').ProteinStructureOperandError
        source, reference, feature, product = protein_records(store, artifact)
        for protected in (source, reference, artifact, feature, product):
            assert binding._protein_reference_access(context, protected, None) is False
            assert binding.resolve_received_reference(context, protected, None) is False
            assert binding.resolve(context, protected, None) is False
            with pytest.raises(error, match='original_commission_mismatch'):
                binding._versions([{'reference': protected, 'version': None, 'content_sha256': None}], scope, context=context)
        assert binding._protein_reference_access(context, 'protein_structure_result_receipt:ungranted', None) is False
        assert binding._protein_reference_access(context, subject, 'protein_structure_sequence') is False
        assert binding._protein_reference_access(context, artifact, 'execution_handle') is None
        # An independent original tool result explicitly grants this exact
        # artifact. Merely retaining the source or its auxiliaries did not.
        action = {'kind': 'tool', 'tool': 'fixture.independently_supplied', 'arguments': {}}
        outcome = {'status': 'completed', 'record_refs': [artifact]}
        journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': canonical(outcome), 'credit': 0})
        receipts.receive(context.episode_id, [artifact], kind='own_action', source_index=0)
        before = list(store.db.iterdump())
        assert binding._protein_reference_access(context, artifact, 'artifact') is True
        assert binding.resolve_received_reference(context, artifact, 'artifact') is True
        assert binding.resolve(context, artifact, 'artifact') is True
        assert binding._versions([{'reference': artifact, 'version': None,
            'content_sha256': version['content_sha256']}], scope, context=context) is None
        assert binding._protein_reference_access(context, source, 'source') is False
        assert list(store.db.iterdump()) == before
        saved_context = plain(context.as_record())
    # Reopening uses the same original context, runtime action and receipt.
    with Store(path) as store:
        binding = owner(store, directory, home)
        reopened = binding.native_protein_structure_returns.context(saved_context['episode_id'])
        assert plain(reopened.as_record()) == saved_context
        assert binding.resolve_received_reference(reopened, artifact, 'artifact') is True
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical({'status': 'completed', 'record_refs': []}), binding.run_id, reopened.episode_id))
        assert binding._protein_reference_access(reopened, artifact, 'artifact') is False
        assert binding.resolve_received_reference(reopened, artifact, 'artifact') is False
        assert binding.resolve(reopened, artifact, 'artifact') is False


@pytest.mark.parametrize('home', HOMES)
def test_fluorescence_invalid_saved_control_cannot_fall_through(tmp_path, home):
    with Store(tmp_path / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        binding = owner(store, tmp_path / 'workflow', home)
        context, journal, _ = root_context(store, binding.run_id, scope)
        artifact = store.artifact(b'synthetic-invalid-fluorescence-control', 'application/octet-stream')
        # Deliberately invalid saved result: its original context is annotation,
        # not a commissioned Results owner. The real reader must reject it.
        fabricated = {'version': 'native_fluorescence_acquired_result_v1',
            'worker_capture': {'outputs': [{'observed': {'artifact_ref': artifact}}]},
            'capture': None, 'intent': {'operation_key': binding.run_id + ':' + context.episode_id + ':0'}}
        journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}),
            'result': canonical({'status': 'completed', 'result': fabricated}), 'credit': 0})
        with pytest.raises(ValueError, match='fluorescence_results_context_required'):
            binding._fluorescence_reference_access(context, artifact, 'artifact')
        with pytest.raises(ValueError, match='fluorescence_results_context_required'):
            binding.resolve_received_reference(context, artifact, 'artifact')
        assert binding.resolve(context, artifact, 'artifact') is False
