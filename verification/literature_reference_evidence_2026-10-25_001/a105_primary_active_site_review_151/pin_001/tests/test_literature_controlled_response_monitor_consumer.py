"""Scientific native fields confer no C8 progress; mixed real progress survives."""
from copy import deepcopy

import pytest
from method_loop.durable import DurableExecutionStore

from gene_annotation_episode.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_monitoring import FIELDS, ProgressProvider
from gene_annotation_episode.literature_controlled_response_storage import controlled_response_cells_schema
from gene_annotation_episode.local_return_history import _progress_refs
from gene_annotation_episode.state import Store
from test_recursive_monitoring import durable_target


def test_exact_native_field_keeps_original_delivery_digest_and_real_progress(tmp_path):
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MKWAA',molecule='protein')
        executions=DurableExecutionStore(tmp_path/'executions')
        target=durable_target(tmp_path,store,executions)
        provider=ProgressProvider(store,executions,run_id=target['run_id']);scope=target['child']['scope']
        observed=provider.observe(target['handle'],list(FIELDS),scope)
        native=controlled_response_cells_schema()
        schema=obj({'numbers':native,'progress':{'type':'string','format':'reference','x-reference-namespace':'episode_progress'},
            'flag':{'type':'string','enum':['unknown','supported']}})
        form={'numbers':[],'progress':observed['progress_ref'],'flag':'unknown'}
        validate_form(form,schema,lambda *_:True)
        assert _progress_refs(form,{'measurements':{'schema':schema}})==[observed['progress_ref']]
        before=store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0]
        assert provider.receive_form('parent',form,schema,scope,'actual-mixed')==[observed['progress_ref']]
        assert provider.received_progress_refs('parent',scope)==[observed['progress_ref']]
        assert provider.receive_form('parent',deepcopy(form),deepcopy(schema),scope,'actual-mixed')==[observed['progress_ref']]
        assert store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0]==before
        assert provider.receive_form('science',{'numbers':[]},obj({'numbers':native}),scope,'scientific-only')==[]
        assert _progress_refs({'numbers':[]},{'measurements':{'schema':obj({'numbers':native})}})==[]
        assert provider.received_progress_refs('science',scope)==[]
        with pytest.raises(ContractError,match='identity_conflict'):
            provider.receive_form('parent',{**form,'flag':'supported'},schema,scope,'actual-mixed')


def test_native_collector_rejects_altered_nested_external_contracts(tmp_path):
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MKWAA',molecule='protein')
        executions=DurableExecutionStore(tmp_path/'executions')
        target=durable_target(tmp_path,store,executions)
        provider=ProgressProvider(store,executions,run_id=target['run_id']);scope=target['child']['scope']
        native=controlled_response_cells_schema()
        altered=deepcopy(native);altered['description']='changed registered contract'
        external=deepcopy(native);external['items']={'$ref':'https://invalid.example/schema'}
        for wrong in (altered,external):
            with pytest.raises(ReportBoundaryError):
                provider.receive_form('parent',{'numbers':[]},obj({'numbers':wrong}),scope,'invalid')
        with pytest.raises(ReportBoundaryError):
            provider.receive_form('parent',{'nested':{'numbers':[]}},obj({'nested':obj({'numbers':native})}),scope,'invalid-nested')
        # Arbitrary reference nodes have no new skip path.
        with pytest.raises(ReportBoundaryError):
            provider.receive_form('parent',{'arbitrary':{'unbound':'value'}},obj({'arbitrary':{'$ref':'#/$defs/Anything'}}),scope,'arbitrary')
        assert provider.received_progress_refs('parent',scope)==[]
