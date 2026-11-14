"""Real retained reader owner with controlled workflow metadata, no execution.

The owner and its native result/return readers are actual application classes.
The workflow port carries actual Store/run identity; no authority is mocked.
"""
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]

@pytest.fixture
def retained(tmp_path):
    module=lambda name:import_module(PACKAGE+'.'+name)
    owner_module=module('library.retained_input_authority.retained_protein_owner')
    with module('state').Store(tmp_path/'state') as store:
        store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT)')
        store.db.execute('INSERT INTO runtime_episodes VALUES(?)',('actual-retained-run',))
        before=store.db.total_changes
        reader=owner_module.RetainedProteinReader.retained_protein_structure_reader(
            store,run_id='actual-retained-run',directory=tmp_path/'original-logical-run')
        assert store.db.total_changes==before
        yield owner_module,store,reader,SimpleNamespace(store=store,run_id='actual-retained-run')


def test_original_factory_owns_exact_native_readers_without_execution_state(retained):
    owner_module,store,reader,workflow=retained
    owner=reader.owner
    assert type(owner) is owner_module.RetainedProteinReader
    assert reader is owner.native_protein_structure_returns
    assert reader.results is owner.native_protein_structure_results
    assert set(vars(owner))=={'store','run_id','directory','native_protein_structure_results','native_protein_structure_returns'}
    before=store.db.total_changes
    transferred=owner_module.reader_from_bound_owner(workflow,owner)
    assert type(transferred.owner) is owner_module.RetainedProteinReader
    assert transferred.owner.store is store and transferred.run_id==workflow.run_id
    assert transferred.owner.directory==owner.directory
    assert store.db.total_changes==before


@pytest.mark.parametrize('change',['missing','wrong_store','wrong_run','relative_directory','unrecorded_run'])
def test_metadata_transfer_rejects_missing_or_wrong_actual_owner(retained,change):
    owner_module,store,reader,workflow=retained
    owner=reader.owner
    if change=='missing':owner=None
    elif change=='wrong_store':workflow.store=object()
    elif change=='wrong_run':workflow.run_id='different-run'
    elif change=='relative_directory':owner.directory=Path('relative-run')
    else:
        owner.run_id=reader.run_id=workflow.run_id='never-recorded-run'
    before=store.db.total_changes
    with pytest.raises(ValueError,match='protein_structure_retained_reader_'):
        owner_module.reader_from_bound_owner(workflow,owner)
    assert store.db.total_changes==before


@pytest.mark.parametrize('changed_arguments',[False,True])
def test_selected_action_reader_preserves_original_action_identity(retained,changed_arguments):
    _,store,reader,workflow=retained
    store.db.execute('CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT)')
    action={'kind':'tool','tool':'original.read','arguments':{'actual':'selection'}}
    store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)',
        (workflow.run_id,'original-episode',3,json.dumps(action),None))
    before=store.db.total_changes
    supplied={'actual':'changed'} if changed_arguments else action['arguments']
    if changed_arguments:
        with pytest.raises(ValueError,match='execution_result_selected_action_conflict'):
            reader.owner._selected_result_action('original-episode',workflow.run_id+':original-episode:3','original.read',supplied)
    else:
        row=reader.owner._selected_result_action('original-episode',workflow.run_id+':original-episode:3','original.read',supplied)
        assert json.loads(row['action'])==action and row['result'] is None
    assert store.db.total_changes==before
