"""Actual selected-unit accounting without closing a scientific investigation.

Uses the existing experimental run_unit_async boundary, private task execution,
actual receipts/finding projection and the original numerical controller. It has
no test stopping controller and creates no scientific finding or provider clock.
"""
import asyncio
from dataclasses import replace
from types import MethodType, SimpleNamespace

from ..communication import plain
from ..episode_journal import Journal
from ..episode_receipts import EpisodeReceipts
from ..execution_timing import capture_progress_time
from ..investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from ..method_loop import Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain
from ..method_loop.identities import EpisodeRef
from ..numerical import YieldController
from ..runtime import ActionLeaf, DecisionSource, Record, Workflow, _effective_configuration


def run_selected_literature_unit(store, context, binding, selection, *, decision_index=0):
    """Acquire the identified primitive once; preserve the controller's decision."""
    assert len(context.path)==1, 'This primitive fixture makes no child-commission claim'
    episode_id=EpisodeRef(context.run_id,context.path).episode_id
    context=replace(context,episode_id=episode_id)
    journal=Journal(store,context.run_id)
    receipts=EpisodeReceipts(store,context.run_id)
    receipts.bind(episode_id)
    receipts.receive(episode_id,context.received_record_refs,kind='initial')
    host=(SimpleNamespace(store=store,run_id=context.run_id) if binding is None
          else binding.services.workflow)
    provider_calls=[]
    async def unselected(*args,**kwargs):
        provider_calls.append((args,kwargs))
        raise AssertionError('No provider is selected by this source-operation boundary')
    host.store,host.run_id,host.journal=store,context.run_id,journal
    host.execution_binding=host.inprocess_replay=None
    host.pending_work=lambda source: []
    host.progress_provider=host.native_timing_information=None
    host.receipts=receipts
    host.provider=SimpleNamespace(complete=unselected)
    host.specialist=lambda source:binding
    host.is_job_source=lambda source:False
    host.binding_context=lambda source:replace(context,
        received_record_refs=tuple(receipts.known(episode_id)))
    async def execute(source,name,arguments,**kwargs):
        if binding is None:
            raise AssertionError('The parent primitive fixture selects only its original reasoning commit')
        return await binding.execute(host.binding_context(source),name,arguments,kwargs['operation_key'])
    host.execute=execute
    for name in ('receive_outcome','receive_native_outcome','automatic_score_updates'):
        setattr(host,name,MethodType(getattr(Workflow,name),host))
    scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    host.source_credit_view=lambda source:scorer(store,plain(context.scope),
        known_assessment_refs=tuple(receipts.known(episode_id,record_type='assessment')))
    # No provider decision ran. Preserve actual clock unavailability rather than
    # fabricate a model-call origin to make the numerical estimate available.
    host.controller_value=lambda source,index,credit:Record({'credit':credit,
        'estimation_context':{'progress_time':capture_progress_time(journal,episode_id,
            original_decision_index=index)}})
    task=object.__new__(DecisionSource if binding is None else binding.decision_source_type)
    task.workflow,task.path,task.scope,task.episode_id=host,context.path,store.validate_scope(plain(context.scope)),episode_id
    task.last_outcome=task.last_outcome_index=task.feedback=None
    initial=host.source_credit_view(task)['credit']
    _,settings=_effective_configuration()
    controller=YieldController('selected-original-unit',initial,settings['cost'],
        {name:value for name,value in settings.items() if name!='cost'})
    grain=Grain(context.role,'Selected original source operation','Original finding credit',lambda _:controller)
    execution_context=Context(tree=EpisodeTree(grain),run_id=context.run_id)
    label=selection['kind']+':'+str(decision_index)
    leaf=ActionLeaf(selection,extract=lambda selected:task.execute(selected,decision_index),
        result=lambda selected,value:value,label=label,decision_index=decision_index)
    hooks=[]
    def forbidden_close(*args):
        raise AssertionError('Single-unit verification must not close or force-yield the investigation')
    episode=Episode(grain,context.path[-1][1],SimpleNamespace(next=lambda view:leaf),
        EpisodeRequest(EpisodeGoal.root(objective='Verify the selected source operation boundary',
            result_contract={}),Record({'assignment':plain(context.assignment)})),forbidden_close,
        on_unit=lambda item,contribution,view:hooks.append((item,contribution,view)),on_close=forbidden_close)
    unit=asyncio.run(episode.run_unit_async(execution_context,expected_label=label,
        starting_unit_index=decision_index))
    assert not provider_calls
    return SimpleNamespace(unit=unit,task=task,context=context,controller=controller,
        receipts=receipts,hooks=hooks,outcome=task.last_outcome)
