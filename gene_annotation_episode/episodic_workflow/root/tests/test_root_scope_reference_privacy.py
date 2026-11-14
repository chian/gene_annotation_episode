"""Real root scope resolution through existing negative-only privacy owners.

Fresh/raw Store fixtures have no selected publication or tool-operation table.
These tests establish original scope/namespace behavior, not publication or
context-aware File authority. No classifier, resolver or constructor is patched.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys

import pytest
from gene_annotation_episode import enrichr_reference_privacy, molecular_reference_privacy
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
from gene_annotation_episode.episodic_workflow.root.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.root_assembly import create_signed_evidence_root_workflow
from gene_annotation_episode.episodic_workflow.root.tests import fresh_decision_support
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import (
    actual_root, ConstructorTools, InputOnlyProvider)


@contextmanager
def observe_privacy_calls(store, reference, namespace):
    """Observe actual calls without replacing either function or its result."""
    functions = {
        enrichr_reference_privacy.enrichr_reference_restriction.__code__: 'enrichr',
        molecular_reference_privacy.molecular_reference_restriction.__code__: 'molecular',
    }
    calls = []
    previous = sys.getprofile()

    def profile(frame, event, argument):
        if event == 'call' and frame.f_code in functions:
            values = frame.f_locals
            calls.append((functions[frame.f_code], values['store'] is store,
                values['context'], values['reference'], values['namespace'], values['private_only']))

    sys.setprofile(profile)
    try:
        yield calls
    finally:
        sys.setprofile(previous)


def assert_scope_ports(calls, reference, namespace):
    assert calls == [(owner, True, None, reference, namespace, True) for owner in ('enrichr', 'molecular')]


def assert_no_execution(workflow, tools, provider):
    for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
        assert workflow.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
    assert tools.execution_calls == [] and provider.requests == []


def resolve(root, reference, namespace, expected):
    services = root.workflow.services
    assert type(services) is WorkflowServices and services.workflow is root.workflow
    before = root.store.db.total_changes
    tables = tuple(row[0] for row in root.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
    assert 'tool_operations' not in tables
    with observe_privacy_calls(root.store, reference, namespace) as calls:
        assert services.reference_in_scope(reference, root.scope, namespace) is expected
    assert_scope_ports(calls, reference, namespace)
    assert root.store.db.total_changes == before
    assert tuple(row[0] for row in root.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")) == tables
    assert_no_execution(root.workflow, root.tools, root.provider)


def test_existing_global_owners_defer_real_fresh_input_without_publication(tmp_path):
    """Control passes before service import relocation; it never calls Services."""
    with actual_root(tmp_path) as root:
        reference = root.scope['subject_refs'][0]
        before = root.store.db.total_changes
        with observe_privacy_calls(root.store, reference, 'subject') as calls:
            assert enrichr_reference_privacy.enrichr_reference_restriction(
                root.store, None, reference, 'subject', private_only=True) is None
            assert molecular_reference_privacy.molecular_reference_restriction(
                root.store, None, reference, 'subject', private_only=True) is None
        assert_scope_ports(calls, reference, 'subject')
        assert root.store.db.total_changes == before
        assert_no_execution(root.workflow, root.tools, root.provider)


@pytest.mark.parametrize('namespace', ['input', 'subject', None, ''], ids=['input', 'subject', 'none', 'empty'])
def test_real_raw_input_scope_accepts_original_namespace_aliases(tmp_path, namespace):
    with actual_root(tmp_path) as root:
        reference = root.scope['subject_refs'][0]
        assert root.store.get(reference)['record_type'] == 'input'
        assert root.store.reference_subset([reference], root.scope) == [reference]
        resolve(root, reference, namespace, True)


@pytest.mark.parametrize('namespace', ['source', 'artifact'])
def test_real_raw_input_scope_rejects_wrong_record_namespace(tmp_path, namespace):
    with actual_root(tmp_path) as root:
        resolve(root, root.scope['subject_refs'][0], namespace, False)


def test_original_raw_sequence_artifact_requires_its_actual_namespace(tmp_path):
    with actual_root(tmp_path) as root:
        target = root.store.get_input(root.scope['subject_refs'][0])
        reference = target['sequence_ref']
        assert root.store.get_artifact(reference) == b'ATGAAATAG'
        assert root.store.reference_subset([reference], root.scope) == [reference]
        resolve(root, reference, 'artifact', True)
        resolve(root, reference, 'subject', False)


def test_unattached_real_file_is_not_made_visible_by_store_membership(tmp_path):
    with actual_root(tmp_path) as root:
        reference = root.store.artifact(b'unattached engineering bytes', 'text/plain')
        assert root.store.get(reference)['record_type'] == 'artifact'
        assert root.store.reference_subset([reference], root.scope) == []
        resolve(root, reference, 'artifact', False)


@pytest.mark.parametrize('reference', [None, 17, 'artifact_' + '0' * 64], ids=['none', 'integer', 'unknown-artifact'])
def test_unknown_or_nonstring_reference_does_not_gain_scope(tmp_path, reference):
    with actual_root(tmp_path) as root:
        assert root.store.reference_subset([reference], root.scope) == []
        resolve(root, reference, 'artifact', False)


@pytest.mark.parametrize('namespace', ['execution', 'execution_handle'])
def test_actual_absence_of_progress_owner_does_not_grant_execution_namespace(tmp_path, namespace):
    with actual_root(tmp_path) as root:
        assert root.workflow.progress_provider is None
        resolve(root, root.scope['subject_refs'][0], namespace, False)


def test_original_scope_validator_still_rejects_empty_scope_after_privacy_deferral(tmp_path):
    with actual_root(tmp_path) as root:
        reference = root.scope['subject_refs'][0]
        before = root.store.db.total_changes
        with observe_privacy_calls(root.store, reference, 'subject') as calls:
            with pytest.raises(ContractError, match='unknown_or_empty_scope'):
                root.workflow.services.reference_in_scope(reference, {'subject_refs': []}, 'subject')
        assert_scope_ports(calls, reference, 'subject')
        assert root.store.db.total_changes == before
        assert_no_execution(root.workflow, root.tools, root.provider)


def test_real_reopen_retains_input_scope_resolution_without_new_receipts(tmp_path):
    with actual_root(tmp_path) as root:
        reference = root.scope['subject_refs'][0]
        known = tuple(root.workflow.receipts.known(root.source.episode_id))
        request = root.episode.request.as_record()
        resolve(root, reference, 'subject', True)
    with actual_root(tmp_path, initialize=False) as root:
        assert root.episode.request.as_record() == request
        assert tuple(root.workflow.receipts.known(root.source.episode_id)) == known
        resolve(root, reference, 'subject', True)
        assert tuple(root.workflow.receipts.known(root.source.episode_id)) == known


def test_context_aware_port_absence_keeps_original_deferral(tmp_path):
    """The injected Tools port is unchanged; no replacement authority is supplied."""
    with actual_root(tmp_path) as root:
        context = root.workflow.binding_context(root.source)
        assert not hasattr(root.tools, 'retained_molecular_reference_access')
        before = root.store.db.total_changes
        with observe_privacy_calls(root.store, root.scope['subject_refs'][0], 'subject') as calls:
            assert root.workflow.services._molecular_reference_access(context, root.scope['subject_refs'][0], 'subject') is None
        assert calls == [] and root.store.db.total_changes == before
        assert_no_execution(root.workflow, root.tools, root.provider)


def test_genuine_constructor_only_store_preserves_missing_problem_failure(tmp_path):
    """No empty problem or scope is substituted for authentic missing intake."""
    raw = (Path(fresh_decision_support.__file__).parent / 'fixtures/fresh_decision_binding.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '14abad6673f40e74f2494ed9dec06125d4883720d903a30596b47fcfe662b437'
    binding = SignedRootEpisodeBinding.from_record(json.loads(raw))
    tools, provider = ConstructorTools(), InputOnlyProvider()
    with Store(tmp_path / 'store') as store:
        workflow = create_signed_evidence_root_workflow(store, tools, provider, tmp_path / 'workflow',
            'engineering-scope-constructor-only', binding.yield_controller,
            initial_known_record_refs=binding.initial_known_record_refs, project_credit=binding.task_credit,
            credit_binding=binding.task_credit.as_record(), controller_binding=binding.controller_record(),
            episode_binding_factories=(), annotation_child_roles=())
        assert type(workflow.services) is WorkflowServices
        reference = store.artifact(b'unattached constructor-only File')
        before = store.db.total_changes
        with observe_privacy_calls(store, reference, 'artifact') as calls:
            with pytest.raises(ContractError, match='problem_not_initialized'):
                workflow.services.reference_in_scope(reference, None, 'artifact')
        assert_scope_ports(calls, reference, 'artifact')
        assert store.db.total_changes == before
        assert_no_execution(workflow, tools, provider)
