"""Original results assignment custody over explicit synthetic saved SQL rows.

The Store, immutable BindingContexts and original base reader are real. These
rows represent a controlled ordinary child return, not executed native science.
"""
from importlib import import_module
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]

def module(name):
    return import_module(PACKAGE+'.'+name)


@pytest.mark.parametrize('changed_assignment',[False,True])
def test_original_result_assignment_checked_before_frozen_form_acceptance(tmp_path,changed_assignment):
    canonical=module('domain').canonical
    BindingContext=module('episode_bindings').BindingContext
    EpisodeRef=module('method_loop.identities').EpisodeRef
    with module('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope=store.validate_scope()
        store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT)')
        store.db.execute('CREATE TABLE runtime_report_attempts(run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,child_episode_id TEXT,contract TEXT,form TEXT,failure TEXT,delivery_ref TEXT)')
        store.db.execute('CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT)')
        store.db.execute('CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT)')
        run='synthetic-original-result-assignment'
        contract={'decision':'return exact original selection','measurements':{'schema':{'type':'object','properties':{},'additionalProperties':False}}}
        selected={'selected_original_operand':'first'}
        actual={'selected_original_operand':'changed'} if changed_assignment else selected
        def context(path,assignment):
            request={'message':{'scope':scope,'episode_assignment':assignment},'report_contract':contract}
            result=BindingContext(run,EpisodeRef(run,path).episode_id,path[-1][0],path,scope,assignment,request)
            store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
                (run,result.episode_id,canonical(path),canonical(request)))
            return result
        parent=context((('perturbation_evidence','parent'),),{})
        child=context((*parent.path,('results','child_0')),actual)
        action={'kind':'episode_child','role':'results','assignment':selected}
        store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)',
            (run,parent.episode_id,0,canonical(action),None))
        store.db.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)',
            (run,parent.episode_id,0,child.episode_id,canonical(contract),'{}',None,'synthetic-original-delivery'))
        store.db.execute('INSERT INTO runtime_forms VALUES(?,?,?)',(run,child.episode_id,'{}'))
        reader=module('episode_return_records').EpisodeReturnRecords(store,run,failure_prefix='original_return_')
        before=store.db.total_changes
        if changed_assignment:
            with pytest.raises(ValueError,match='commission_assignment_conflict'):
                reader._attempt(parent,0)
        else:
            returned,form,schema=reader._attempt(parent,0)
            assert returned==child and form=={} and schema==contract['measurements']['schema']
        assert store.db.total_changes==before
