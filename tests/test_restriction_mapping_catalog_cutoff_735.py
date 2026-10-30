"""Frozen catalog custody checks; engineering authority seams, no science.

The reused729 fixture supplies a tiny explicitly synthetic catalog and stubs
only725/726 authority. Its source labels are not native biological data. These
tests never open the retained original scientific Store or install a ToolInfo.
"""
from copy import deepcopy
from dataclasses import replace
import os

import pytest

from gene_annotation_episode.restriction_mapping_action_records import RestrictionMappingActionRecords
from test_restriction_mapping_action_records_729 import (
    ALIAS, RUN, engineering_case, engineering_action, initial, page, saved_context,
)


pytestmark=pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ,reason='requires bounded529')
PREFIX='restriction_mapping_return_'


def source_receipt(case,context,outcome,*,index=3,**changes):
    """A labelled synthetic namespace receipt, not a fabricated Store source."""
    values={'run_id':RUN,'episode_id':context.episode_id,
        'record_ref':outcome['result']['source_ref'],'receipt_kind':'own_action','source_index':index}
    values.update(changes)
    columns=list(values)
    cursor=case.store.db.execute('INSERT INTO runtime_record_receipts ('+','.join(columns)+') '
        'VALUES ('+','.join('?' for _ in columns)+')',[values[k] for k in columns])
    return cursor.lastrowid


def own(case,context,reference='EcoRI',*,before=4,through=1000):
    return case.service.own_enzyme_reference(context,reference,
        before_decision_index=before,through_receipt_index=through)


@pytest.mark.parametrize('tool',[ALIAS,'find_restriction_enzymes'])
@pytest.mark.parametrize('mode',['native','saved'])
def test_bounded_catalog_reuses_original_native_or_saved_alias_authority(engineering_case,tool,mode):
    case=engineering_case
    context=saved_context(case)
    initial(case,context,saved=mode=='saved')
    outcome=engineering_action(case,context,tool=tool,mode=mode)
    receipt=source_receipt(case,context,outcome)
    assert own(case,context,through=receipt) is True
    assert case.sources[outcome['result']['source_ref']]['mapping'] is None


@pytest.mark.parametrize('before,expected',[(0,False),(2,False),(3,False),(4,True)])
def test_commission_decision_cutoff_is_strict(engineering_case,before,expected):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context))
    assert own(case,context,before=before,through=receipt) is expected


def test_receipt_boundary_is_inclusive_and_zero_is_not_unbounded(engineering_case):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context))
    assert own(case,context,through=0) is False
    assert own(case,context,through=receipt-1) is False
    assert own(case,context,through=receipt) is True


@pytest.mark.parametrize('before,through',[
    (None,0),(0,None),(True,0),(0,False),(-1,0),(0,-1),(1.0,0),(0,1.0),
    ('4',0),(0,'4'),([],0),(0,[]),({},0),(0,{}),(float('nan'),0),(0,float('inf')),
])
def test_cutoffs_must_be_an_explicit_pair_of_nonnegative_integers(engineering_case,before,through):
    case=engineering_case
    context=saved_context(case)
    with pytest.raises(ValueError,match=PREFIX+'explicit_catalog_cutoff_required'):
        own(case,context,before=before,through=through)


@pytest.mark.parametrize('kind',['initial','decision_input','child_form','report_redelivery'])
def test_other_delivery_kinds_do_not_establish_own_catalog_delivery(engineering_case,kind):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context),receipt_kind=kind)
    assert own(case,context,through=receipt) is False


@pytest.mark.parametrize('change',[
    {'run_id':'foreign'}, {'episode_id':'sibling'}, {'record_ref':'other_source'},
    {'source_index':2}, {'source_index':None},
],ids=['run','episode','source','decision','missing_decision'])
def test_receipt_must_join_the_same_original_own_source_and_action(engineering_case,change):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context),**change)
    assert own(case,context,through=receipt) is False


def test_delayed_completion_of_an_earlier_decision_stays_outside_original_prefix(engineering_case,monkeypatch):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    cutoff=case.store.db.execute('SELECT MAX(receipt_index) FROM runtime_record_receipts').fetchone()[0]
    outcome=engineering_action(case,context,index=1)
    receipt=source_receipt(case,context,outcome,index=1)
    assert receipt>cutoff
    original=case.service._authenticated
    seen=[]
    def observed(ctx,row):
        seen.append(row['decision_index'])
        return original(ctx,row)
    monkeypatch.setattr(case.service,'_authenticated',observed)
    assert own(case,context,before=2,through=cutoff) is False
    assert seen==[]
    assert own(case,context,before=2,through=receipt) is True
    assert seen==[1]


def test_later_and_unreceived_broken_actions_are_filtered_before_authentication(engineering_case,monkeypatch):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    late=engineering_action(case,context,index=5)
    receipt=source_receipt(case,context,late,index=5)
    engineering_action(case,context,index=1)  # Earlier, but never received.
    case.store.db.execute('DELETE FROM tool_operations')
    def forbidden(*args):raise AssertionError('An ineligible action was authenticated')
    monkeypatch.setattr(case.service,'_authenticated',forbidden)
    assert own(case,context,before=5,through=receipt) is False


@pytest.mark.parametrize('loss',['row','table'])
def test_missing_authority_for_eligible_completed_action_keeps_specific_failure(engineering_case,loss):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context))
    case.store.db.execute('DELETE FROM tool_operations' if loss=='row' else 'DROP TABLE tool_operations')
    with pytest.raises(ValueError,match=PREFIX+'completed_operation_missing'):
        own(case,context,through=receipt)


def test_bounded_lookup_requires_receipt_history_instead_of_current_state_guess(engineering_case):
    case=engineering_case
    context=saved_context(case)
    case.store.db.execute('DROP TABLE runtime_record_receipts')
    with pytest.raises(ValueError,match=PREFIX+'receipt_history_unbound'):
        own(case,context)


@pytest.mark.parametrize('catalog',['separate','native','missing'])
def test_only_the_authenticated_catalog_or_native_catalog_can_supply_name(engineering_case,catalog):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    outcome=engineering_action(case,context)
    receipt=source_receipt(case,context,outcome)
    source=case.sources[outcome['result']['source_ref']]
    if catalog=='separate':
        source['catalog']=deepcopy(source['native']['catalog'])
        source['native']['catalog']={'enzymes':[]}
    elif catalog=='missing':
        source['native']['catalog']={'enzymes':[]}
        # Arguments still contain EcoRI. They do not replace a catalog.
        assert source['body']['arguments']['enzyme_names']==['EcoRI']
    assert own(case,context,through=receipt) is (catalog!='missing')


@pytest.mark.parametrize('reference',['ecori','EcoRII','BcgI','',None,True,1])
def test_bounded_names_are_exact_case_sensitive_identifiers(engineering_case,reference):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context))
    assert own(case,context,reference,through=receipt) is False


def test_sibling_own_action_and_receipt_grant_nothing(engineering_case):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    sibling=saved_context(case,name='sibling');initial(case,sibling)
    receipt=source_receipt(case,sibling,engineering_action(case,sibling))
    assert own(case,context,through=receipt) is False
    assert own(case,sibling,through=receipt) is True


def test_original_context_authentication_still_precedes_bounded_catalog(engineering_case):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context))
    with pytest.raises(ValueError,match=PREFIX+'context_conflict'):
        own(case,replace(context,run_id='foreign'),through=receipt)


def test_successful_lookup_has_no_cached_authority_and_writes_no_observations(engineering_case):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    outcome=engineering_action(case,context)
    receipt=source_receipt(case,context,outcome)
    before=case.store.db.total_changes
    assert own(case,context,through=receipt) is True
    assert case.store.db.total_changes==before
    case.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?',
        (outcome['result']['source_ref'],))
    assert own(case,context,through=receipt) is False
    for table in ('runtime_observations','runtime_model_calls','runtime_report_attempts'):
        assert case.store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_unbounded_lookup_and_requested_pagination_keep_their_existing_meaning(engineering_case):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    engineering_action(case,context,index=1)
    engineering_action(case,context,index=3)
    # Existing own authority does not need its result-source receipt. A child
    # cutoff does; the two calls deliberately answer different questions.
    assert case.service.own_enzyme_reference(context,'EcoRI') is True
    assert case.service.own_enzyme_reference(context,'EcoRI',before_decision_index=None,
        through_receipt_index=None) is True
    assert own(case,context,before=4,through=1000) is False
    first=page(case,context,limit=1)
    second=page(case,context,limit=1,after=first['next_after_decision_index'])
    assert [row['decision_index'] for row in first['records']]==[1]
    assert [row['decision_index'] for row in second['records']]==[3]
    assert second['next_after_decision_index'] is None


@pytest.mark.parametrize('status',['failed','invalid','unavailable'])
def test_noncompleted_actions_do_not_gain_catalog_authority_from_a_receipt(engineering_case,status):
    case=engineering_case
    context=saved_context(case);initial(case,context)
    receipt=source_receipt(case,context,engineering_action(case,context,status=status))
    assert own(case,context,through=receipt) is False
