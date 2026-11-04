"""Reference evidence subjects keep their identity and explicit receipt guard."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.homology_query import protein_query
from gene_annotation_episode.resource_information import ResourceInformation
from gene_annotation_episode.state import Store
from a103_test_support import source,protein
from test_resource_episode_branches import resources,context
from gene_annotation_episode.communication import plain as dict_plain


def test_reference_query_does_not_create_a_target_and_other_target_remains_outside_scope(tmp_path):
    file=tmp_path/'two.faa';file.write_text('>one\nMDEAKG\n>two\nMKQQ\n')
    with Store(tmp_path/'state') as store:
        one,two=store.create_problem(file,molecule='protein')['subject_refs']
        scope={'subject_refs':[one]}
        origin=source(store,'engineering.protein_input',{'purpose':'reference operand validation'})
        ref=protein(store,'MEEAKG',origin,'received-reference')
        assert protein_query(store,scope,ref,error_code='bad')['id']==ref
        with pytest.raises(ValueError,match='bad'):
            protein_query(store,scope,two,error_code='bad')
        assert {r['id'] for r in store.targets()}=={one,two}


def test_external_reference_order_requires_received_operand_and_preserves_original_scope(resources):
    r=resources
    origin=source(r.store,'engineering.reference_query',{'purpose':'received external protein query'})
    ref=protein(r.store,'MDEAKG',origin,'external-query')
    assignment=dict_plain(r.launch)
    assignment.update(job_request={'query_ref':ref,'cpu':2,'search_mode':'maximum_sensitivity'},
        immutable_input_versions=[],resource_selection=r.adapter._selection(2))
    receiver=context(r,'launch',assignment,key='external-query-parent')
    with pytest.raises(ValueError,match='reference_query_requires_explicit_received_operand'):
        r.adapter.prepare_assignment(receiver,'launch_local',assignment,r.scope,'explicit-reference-order')
    r.adapter.bind_record_selection(lambda c:{'run_id':c.run_id,'episode_id':c.episode_id,'known_record_refs':[ref]})
    prepared=r.adapter.prepare_assignment(receiver,'launch_local',assignment,r.scope,'explicit-reference-order')
    assert prepared['adapter_assignment']['query_ref']==ref
    assert len(list(r.store.targets()))==1
    assert ResourceInformation(r.store,run_id=receiver.run_id,jobs=r.jobs)._query(ref,r.scope)['id']==ref


def test_unrelated_received_handoff_is_authenticated_then_filtered(resources,monkeypatch):
    r=resources
    receiver=context(r,'launch',dict_plain(r.launch),key='handoff-filter')
    ref=source(r.store,'episode.resource_handoff',{'meaning':'explicit unit-control body; custody reader is instrumented'})
    body={'registry_ref':r.jobs.config['registry_ref'],'execution_handoff':{'submitted_input_versions':[]},
        'job':{'query_ref':'another-query','cpu':2,'search_mode':'maximum_sensitivity','job_ref':'another-job'}}
    r.adapter.bind_record_selection(lambda c:{'run_id':c.run_id,'episode_id':c.episode_id,'known_record_refs':[ref]})
    seen=[]
    monkeypatch.setattr(r.adapter.information,'_body',lambda _:deepcopy(body))
    def authenticate(reference,*,scope):seen.append(reference);return deepcopy(body)
    monkeypatch.setattr(r.adapter.information,'read_handoff_source',authenticate)
    assert r.adapter.execution_handoffs(receiver)==[] and seen==[ref]
    def reject(*a,**k):raise ValueError('custody_conflict')
    monkeypatch.setattr(r.adapter.information,'read_handoff_source',reject)
    with pytest.raises(ValueError,match='custody_conflict'):
        r.adapter.execution_handoffs(receiver)
