"""Native root factory ownership/receipt boundaries; no scientific acquisition."""
from contextlib import contextmanager
import json
from pathlib import Path

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.evidence_root import (
    NativeEvidenceRootCredit, create_evidence_root_workflow)
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.numerical import YieldController
from gene_annotation_episode.episodic_workflow.root.a102.a102_credit import A102StructuralCredit
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import (
    ConstructorTools, InputOnlyProvider)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 'engineering-native-factory-ownership'


def controller_factory(path, initial_credit):
    # Original score-based controller, with no observations or estimated actions.
    # Zero continuation cost is an explicit engineering operand, not a work cap.
    return YieldController(json.dumps(path), initial_credit, 0)


def options():
    # Explicit isolated topology; this is not the public constructor's default.
    return {'episode_binding_factories': (), 'annotation_child_roles': ()}


@contextmanager
def operands(directory, *, initialize=True):
    tools, provider = ConstructorTools(), InputOnlyProvider()
    with Store(directory / 'store') as store:
        if initialize:
            store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQ', molecule='protein')
        scope = store.validate_scope()
        try:
            yield store, scope, tools, provider
        finally:
            assert tools.execution_calls == []
            assert provider.requests == []


def create(directory, store, scope, tools, provider, **extra):
    return create_evidence_root_workflow(store, tools, provider,
        directory / 'workflow', RUN_ID, controller_factory,
        axes=('A102',), initial_known_record_refs=list(scope['subject_refs']),
        **(options() | extra))


def rows(store):
    return {table: [dict(row) for row in store.db.execute(
        'SELECT * FROM ' + table + ' WHERE run_id=?', (RUN_ID,))]
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls')}


def build(flow, scope):
    return flow.build('annotation', 'root', 'Engineering native factory ownership', scope)


@pytest.mark.parametrize('field', ['project_credit', 'credit_binding'])
def test_native_factory_rejects_caller_numeric_override(tmp_path, field):
    with operands(tmp_path) as (store, scope, tools, provider):
        with pytest.raises(ValueError) as caught:
            create(tmp_path, store, scope, tools, provider, **{field: None})
        assert type(caught.value) is ValueError
        assert str(caught.value) == 'evidence_root_numeric_binding_is_host_owned'


@pytest.mark.parametrize('receipt_option', [False, None, 0], ids=['false', 'none', 'integer'])
def test_native_factory_rejects_disabled_or_nonboolean_receipts(tmp_path, receipt_option):
    with operands(tmp_path) as (store, scope, tools, provider):
        with pytest.raises(ValueError) as caught:
            create(tmp_path, store, scope, tools, provider,
                episode_record_receipts=receipt_option)
        assert type(caught.value) is ValueError
        assert str(caught.value) == 'evidence_root_requires_explicit_receipts'


def test_native_factory_requires_explicit_initial_receipt_sequence(tmp_path):
    with operands(tmp_path) as (store, scope, tools, provider):
        with pytest.raises(ValueError) as caught:
            create_evidence_root_workflow(store, tools, provider,
                tmp_path / 'workflow', RUN_ID, controller_factory,
                axes=('A102',), initial_known_record_refs=None, **options())
        assert type(caught.value) is ValueError
        assert str(caught.value) == 'receipt_binding_requires_explicit_initial_known_record_refs'


def test_native_factory_uses_own_root_ports_and_real_axis_receipts(tmp_path):
    with operands(tmp_path) as (store, scope, tools, provider):
        flow = create(tmp_path, store, scope, tools, provider)
        assert type(flow) is Workflow
        assert type(flow.project_credit) is NativeEvidenceRootCredit
        assert flow.project_credit.axes == ('A102',)
        assert flow.store is store and flow.tools is tools and flow.provider is provider
        assert flow.controller_factory is controller_factory
        assert type(flow.journal) is Journal and flow.journal.store is store
        assert type(flow.receipts) is EpisodeReceipts and flow.receipts.store is store
        assert flow.episode_record_receipts is True
        assert flow.initial_known_record_refs == tuple(scope['subject_refs'])
        descriptor = flow.project_credit.as_record()
        assert flow.credit_binding == descriptor
        assert descriptor['axis_graders'] == {'A102': A102StructuralCredit().as_record()}
        assert descriptor['kind'] == 'native_evidence_root'
        assert descriptor['formula'] == 'product(1 + received_axis_credit) - 1'
        episode = build(flow, scope)
        context = flow.binding_context(episode.source)
        assert type(context) is BindingContext
        known = list(flow.receipts.known(episode.source.episode_id))
        # Original receipt traversal also retains actual input provenance refs.
        assert set(scope['subject_refs']) <= set(known)
        assert set(context.received_record_refs) == set(known)
        arguments = flow.projector_receipt_arguments(flow.project_credit, episode.source.episode_id)
        assert set(arguments) == {'known_record_refs'}
        assert list(arguments['known_record_refs']) == known
        original_rows, changes = rows(store), store.db.total_changes
        details = flow.project_credit.read_details(store, scope, known_record_refs=known,
            details_limit=0, details_offset=0)
        axis = A102StructuralCredit().read_details(store, scope,
            known_record_refs=known, details_limit=0, details_offset=0)
        assert axis['credit'] == 0 and axis['source_contribution_count'] == 0
        assert details['credit'] == axis['credit']
        assert details['axis_components'] == {'A102': axis['credit']}
        assert details['source_contribution_count'] == 0
        for target in scope['subject_refs']:
            assert details['target_sheets'][target]['axis_status'] == {
                'A102': 'no_received_native_measurement'}
        assert flow.source_credit_view(episode.source)['credit'] == details['credit']
        assert flow.source_credit_binding(episode.source) == descriptor
        controller = flow.controller(episode.source.path)
        assert type(controller.controller) is YieldController
        assert controller.controller.initial_credit == details['credit']
        assert rows(store) == original_rows == {key: [] for key in original_rows}
        assert store.db.total_changes == changes
        import sys
        owners = {
            Workflow: 'runtime.py', NativeEvidenceRootCredit: 'evidence_root.py',
            Journal: 'episode_journal.py', EpisodeReceipts: 'episode_receipts.py',
            BindingContext: 'receiving_context.py', YieldController: 'numerical.py',
            A102StructuralCredit: 'a102/a102_credit.py'}
        for owner, relative in owners.items():
            module = sys.modules[owner.__module__]
            expected_name = 'gene_annotation_episode.episodic_workflow.root.' + relative[:-3].replace('/', '.')
            assert owner.__module__ == expected_name
            assert getattr(module, owner.__name__) is owner
            assert Path(module.__file__).resolve() == ROOT / relative


def test_native_factory_reopens_same_native_descriptor_and_receipts(tmp_path):
    with operands(tmp_path) as (store, scope, tools, provider):
        flow = create(tmp_path, store, scope, tools, provider)
        episode = build(flow, scope)
        saved = {'request': episode.request.as_record(),
            'descriptor': flow.credit_binding,
            'known': list(flow.receipts.known(episode.source.episode_id)),
            'credit': flow.source_credit_view(episode.source), 'rows': rows(store)}
    with operands(tmp_path, initialize=False) as (store, scope, tools, provider):
        flow = create(tmp_path, store, scope, tools, provider)
        episode = build(flow, scope)
        assert episode.request.as_record() == saved['request']
        assert flow.credit_binding == saved['descriptor']
        assert list(flow.receipts.known(episode.source.episode_id)) == saved['known']
        assert flow.source_credit_view(episode.source) == saved['credit']
        assert rows(store) == saved['rows']
