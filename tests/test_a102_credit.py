"""Native grading happens at publication; observation and receipts govern credit."""
from copy import deepcopy

import pytest

from gene_annotation_episode.a102_credit import A102StructuralCredit
from gene_annotation_episode.a102_publication import PROVIDER, publish_comparison, received_grade
from gene_annotation_episode.a102_scoring import A102ScoringUnavailable
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.state import Store
from test_a102_scoring import native


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence='M'+'A'*99,molecule='protein')['subject_refs']
        row=native();row.update(target_ref=target,producer='synthetic_geometry_fixture')
        yield store,target,row,A102StructuralCredit()


def test_publication_attaches_grader_before_credit_read_and_parent_recomputes(case):
    store,target,row,scorer=case;scope={'subject_refs':[target]}
    published=publish_comparison(store,row);ref=published['source_ref']
    assert received_grade(store,ref)['grade']['components']['B']==pytest.approx(.72)
    assert scorer(store,scope,known_record_refs=[target])['credit']==0
    owner=scorer(store,scope,known_record_refs=[target,ref])
    parent=scorer(store,scope,known_record_refs=[target,ref])
    assert owner['credit']==parent['credit']==pytest.approx(.72)
    assert owner['target_sheets'][target]['function_specific_index']['value'] is None
    assert scorer(store,scope,known_record_refs=[target,published['grading_artifact_ref']])['credit']==0
    assert store.count('assessment')==0


def test_auxiliary_grader_without_native_publication_grant_cannot_mint_credit(case):
    store,target,row,scorer=case
    published=publish_comparison(store,row)
    source=store.get(published['source_ref'])
    body={k:v for k,v in source.items() if k not in {'id','origin','record_type'}}
    body['accession']='forged-copy'
    forged=store.put('source',body,origin='tool')['id']
    with pytest.raises(A102ScoringUnavailable,match='scoring_grant_unavailable'):
        scorer(store,{'subject_refs':[target]},known_record_refs=[forged])


def test_parent_denominator_is_not_replaced_by_child_fragment(case):
    store,target,row,scorer=case
    row.update(target_scope=[0,20],target_positions=list(range(20)),reference_positions=list(range(20)),
        distances_A=[0.0]*20,reference_length=100)
    published=publish_comparison(store,row)
    child_scope={'subject_refs':[target],'segments':[{'target_ref':target,'start':0,'end':20,'unit':'aa'}]}
    assert scorer(store,child_scope,known_record_refs=[published['source_ref']])['credit']==pytest.approx(1/3)
    assert scorer(store,{'subject_refs':[target]},known_record_refs=[published['source_ref']])['credit']==pytest.approx(.2)
