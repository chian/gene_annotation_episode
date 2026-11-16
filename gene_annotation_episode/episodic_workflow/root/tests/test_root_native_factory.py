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
