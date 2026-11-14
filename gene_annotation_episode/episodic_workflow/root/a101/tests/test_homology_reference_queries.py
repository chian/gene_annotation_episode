"""Reference evidence subjects keep their identity and explicit receipt guard."""
import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library.homology_query import protein_query
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.a103.tests.a103_test_support import source,protein


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
