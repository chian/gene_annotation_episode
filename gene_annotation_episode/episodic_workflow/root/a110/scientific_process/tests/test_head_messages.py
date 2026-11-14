"""Scientific-head endpoint ordering with controlled receipt/progress ports."""
from importlib import import_module
from types import SimpleNamespace
import pytest

AXIS='a110'
def own(name):return import_module('gene_annotation_episode.episodic_workflow.root.'+AXIS+'.'+name)

@pytest.mark.parametrize('role,child',[('scientific_process','scientific_process'),('hpc','hpc_work_planning'),('literature','published_evidence_assessment')])
def test_distinct_receiver_selection_uses_only_known_role(role,child):
    cls=own('scientific_process.child_commissioning').ScientificChildCommissioning
    owner=object.__new__(cls)
    assert owner.execution_child_report_receiver(role) is own('scientific_process.from_child_'+child).receive_report
    assert owner.execution_child_report_receiver('unrelated') is None
    assert not hasattr(owner,'child_report_receiver')

@pytest.mark.parametrize('child',['scientific_process','hpc_work_planning','published_evidence_assessment'])
def test_cached_original_admission_returns_before_progress_or_counterpart_reads(monkeypatch,child):
    events=[];records=own('episode_return_records')
    class Cached:
        def __init__(self,*args,**kwargs):events.append('original_receipt_reader')
        def recorded_admission_references(self,*args):events.append('cached_admission');return ['source_original']
    monkeypatch.setattr(records,'EpisodeReturnRecords',Cached)
    def forbidden(*args,**kwargs):pytest.fail('The cached return must precede this operation')
    source=SimpleNamespace(episode_id='parent',scope={'subject_refs':[]})
    workflow=SimpleNamespace(receipts=object(),is_job_source=lambda source:False,store=object(),run_id='original-run',
        binding_context=lambda source:SimpleNamespace(),progress_provider=SimpleNamespace(receive_form=forbidden),
        specialist=forbidden)
    receive=own('scientific_process.from_child_'+child).receive_report
    assert receive(workflow,source,{}, {'type':'object','properties':{}},7)==['source_original']
    assert events==['original_receipt_reader','cached_admission']

@pytest.mark.parametrize('child',['scientific_process','hpc_work_planning','published_evidence_assessment'])
def test_uncached_typed_progress_then_receipt_then_attribution_order(monkeypatch,child):
    events=[];records=own('episode_return_records')
    class Uncached:
        def __init__(self,*args,**kwargs):pass
        def recorded_admission_references(self,*args):events.append('cached_admission');return None
    monkeypatch.setattr(records,'EpisodeReturnRecords',Uncached)
    source=SimpleNamespace(episode_id='parent',scope={'subject_refs':[]})
    workflow=SimpleNamespace(run_id='original-run',is_job_source=lambda source:False,
        receipts=SimpleNamespace(receive=lambda *args,**kwargs:events.append('receipt')),
        store=SimpleNamespace(get=lambda ref:None,reference_subset=lambda refs,scope:refs),binding_context=lambda source:SimpleNamespace(),
        progress_provider=SimpleNamespace(receive_form=lambda *args:events.append('progress')),
        specialist=lambda source:SimpleNamespace(),native_timing_information=None,job_episodes=None,
        episode_bindings=SimpleNamespace(received_form_references=lambda *args:events.append('form_references') or ['source_child']),
        receive_tool_attributions=lambda *args,**kwargs:events.append('attribution') or ['source_derived'])
    receive=own('scientific_process.from_child_'+child).receive_report
    result=receive(workflow,source,{}, {'type':'object','properties':{}},7)
    assert result==['source_child','source_derived']
    assert events==['cached_admission','progress','form_references','receipt','attribution']
