"""Actual root/A105 setup integration; no scientific units or fabricated rows."""
from dataclasses import replace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import actual_root
from gene_annotation_episode.episodic_workflow.root.tests.private_setup_support import actual_private_root, actual_rows
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_provenance import ScientificProcessProvenance
from gene_annotation_episode.episodic_workflow.root.a105.scientific_tool_retrieval import ScientificToolRetriever


def test_real_root_without_private_binding_omits_optional_setup(tmp_path):
    with actual_root(tmp_path) as root:
        assert root.workflow.scientific_process_binding is None
        assert root.workflow.scientific_provenance is None
        assert root.workflow.scientific_tool_retriever is None
        assert root.provider.requests == root.tools.execution_calls == []


def test_selected_provenance_keeps_real_owner_ports_and_no_acquisition(tmp_path):
    with actual_private_root(tmp_path) as root:
        provenance = root.workflow.scientific_provenance
        assert type(provenance) is ScientificProcessProvenance
        assert root.head is root.workflow.scientific_process_binding
        assert root.head.services is root.workflow.services
        assert provenance.store is root.store and provenance.journal is root.workflow.journal
        assert provenance.journal.db is root.store.db
        assert provenance.library is root.head.library and provenance.tool_library is root.head.tool_library
        assert root.head.tool_retrieval is None and root.workflow.scientific_tool_retriever is None
        assert root.workflow.services.scientific_received_results(root.context) == []
        assert root.workflow.services.scientific_frozen_results(root.context) is None
        assert actual_rows(root) == {'runtime_actions': [], 'runtime_observations': [], 'runtime_model_calls': []}


def test_selected_semantic_retriever_constructs_real_owner_without_calling_provider(tmp_path):
    # Explicit constructor-only configuration: this identifier is never sent
    # to a provider and makes no model availability or scientific claim.
    retrieval = {'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
                 'model': {'model': 'engineering-uninvoked-model', 'reasoning_effort': 'low'}}
    with actual_private_root(tmp_path, retrieval=retrieval) as root:
        retriever = root.workflow.scientific_tool_retriever
        assert type(retriever) is ScientificToolRetriever
        assert retriever.store is root.store and retriever.provider is root.provider
        assert retriever.run_id == root.workflow.run_id and retriever.library is root.head.tool_library
        assert retriever.configuration == root.head.tool_retrieval == retrieval
        assert root.store.db.execute('SELECT count(*) FROM runtime_tool_retrievals').fetchone()[0] == 0
        assert actual_rows(root) == {'runtime_actions': [], 'runtime_observations': [], 'runtime_model_calls': []}


@pytest.mark.parametrize('owner,error', [
    ('self', 'scientific_preparation_reference_invalid'),
    ('parent', 'scientific_preparation_saved_parent_required'),
    ('invalid', 'scientific_preparation_owner_invalid'),
])
def test_genuine_root_preparation_negatives_preserve_credit_and_rows(tmp_path, owner, error):
    with actual_private_root(tmp_path) as root:
        context = root.context
        credit = root.workflow.source_credit_view(root.episode.source)
        rows, changes = actual_rows(root), root.store.db.total_changes
        with pytest.raises(ValueError, match='^' + error + '$') as caught:
            if owner == 'parent':
                root.workflow.services.scientific_parent_preparation(context, 'not-an-operation')
            else:
                root.workflow.services.scientific_preparation(context, 'not-an-operation', owner=owner)
        assert type(caught.value) is ValueError
        assert root.workflow.source_credit_view(root.episode.source) == credit
        assert actual_rows(root) == rows and root.store.db.total_changes == changes
        with pytest.raises(TypeError):
            context.request['goal'] = {}


@pytest.mark.parametrize('port', ['scientific_preparation', 'scientific_parent_preparation'])
def test_original_service_receiver_rejects_foreign_run_before_private_reader(tmp_path, port):
    with actual_private_root(tmp_path) as root:
        # This is an explicitly invalid derivative of the real immutable
        # context, never a fabricated accepted request or private assignment.
        foreign = replace(root.context, run_id='different-engineering-run')
        rows, changes = actual_rows(root), root.store.db.total_changes
        with pytest.raises(ValueError, match='^scientific_provenance_receiver_identity_mismatch$') as caught:
            getattr(root.workflow.services, port)(foreign, 'not-an-operation')
        assert type(caught.value) is ValueError
        assert actual_rows(root) == rows and root.store.db.total_changes == changes


def test_same_current_implementation_reopens_original_root_request(tmp_path):
    with actual_private_root(tmp_path) as root:
        request = root.episode.source.request.as_record()
        record = root.head.as_record()
        credit = root.workflow.source_credit_view(root.episode.source)
        rows = actual_rows(root)
    with actual_private_root(tmp_path, initialize=False) as reopened:
        assert reopened.episode.source.request.as_record() == request
        assert reopened.head.as_record() == record
        assert reopened.workflow.source_credit_view(reopened.episode.source) == credit
        assert actual_rows(reopened) == rows
        assert reopened.workflow.scientific_provenance.journal is reopened.workflow.journal
        assert reopened.workflow.scientific_provenance.store is reopened.store
