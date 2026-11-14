"""Monitoring calculator preservation; saved observations supplied by a controlled reader."""
from copy import deepcopy
import importlib
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.tests.monitor_credit_behavior import progress, received_fixture
AXES=('a101','a102','a103','a104','a106','a107','a110')

@pytest.fixture(params=AXES)
def axis(request):return 'gene_annotation_episode.episodic_workflow.root.'+request.param

def calculator(axis):return importlib.import_module(axis+'.library.progress_information_credit').ProgressInformationCredit


def test_received_semantic_baseline_is_not_representation_or_poll_count(axis):
    context,selection,reader,reads=received_fixture(axis)
    project=calculator(axis)(reader,information_unit=.375)
    assert project(context,selection)['credit']==1.125
    assert project(context,{**selection,'known_progress_refs':['baseline','repeat']})['credit']==0


def test_original_receiver_identity_and_context_type_are_required(axis):
    context,selection,reader,_=received_fixture(axis)
    project=calculator(axis)(reader,information_unit=1)
    with pytest.raises(ValueError,match='progress_credit_receiver_identity_mismatch'):
        project(context,{**selection,'episode_id':'other'})
    with pytest.raises(TypeError,match='progress_credit_binding_context_required'):
        project(SimpleNamespace(**dict(run_id='run',episode_id='monitor')),selection)
    with pytest.raises(ValueError,match='progress_credit_reference_identity_mismatch'):
        project.__class__(SimpleNamespace(read_progress=lambda *args:progress('different')),information_unit=1)(context,selection)


def test_resource_output_growth_is_not_credit_and_closed_intervals_remain_measured(axis):
    context,selection,_,_=received_fixture(axis)
    records=importlib.import_module(axis+'.progress_records')
    target={'handle':'resource','resource_id':'local','resource_kind':'local','execution_id':'original',
        'request_sha256':'a'*64}
    def snapshot(ref,*,size=10,measurements=()):
        status=records.resource_status(target,{'observed_at':'2026-11-11T00:00:00Z','state':'running',
            'returncode':None,'failure_code':None,'result_available':False,'measurements':list(measurements),
            'outputs':[{'role':'text','available':True,'bytes':size,'writer_closed':False}],
            'logs':[],'provenance_refs':[],'native':{'unfinished_elapsed_seconds':size}})
        row=progress(ref,target='resource');row['execution_status']=status;row['result_available']=False;return row
    values={'baseline':snapshot('baseline'),'growth':snapshot('growth',size=100),
        'measured':snapshot('measured',size=100,measurements=[{'measure':'queue_wait_seconds','seconds':8}])}
    project=calculator(axis)(SimpleNamespace(read_progress=lambda ref,scope:deepcopy(values[ref])),information_unit=.25)
    result=project(context,{**selection,'known_progress_refs':['baseline','growth','measured'],'initial_progress_refs':['baseline']})
    assert result['credit']==.25
    assert [r['progress_ref'] for r in result['monitoring_information_contributions']]==['measured']


@pytest.mark.parametrize('axis_name',['a101','a103','a104'])
def test_supported_job_elapsed_growth_is_not_credit_and_closed_duration_remains_measured(axis_name):
    axis='gene_annotation_episode.episodic_workflow.root.'+axis_name
    context,selection,_,_=received_fixture(axis)
    records=importlib.import_module(axis+'.progress_records')
    def snapshot(ref,*,state='running',outcome='pending',elapsed=1,size=10):
        status=records.job_status('job',{'job_ref':'job','registry_ref':'registry','state':state,'outcome':outcome,
            'elapsed_seconds':elapsed,'duration_measure':'systemd_service_wall_seconds','native_returncode':None,
            'failure_code':None,'resource':None,'progress_kind':'native_execution_state_and_output_bytes_not_search_fraction',
            'outputs':[{'role':'native_text','available':True,'bytes':size,'writer_closed':False}]},
            observed_at='2026-11-11T00:00:00Z')
        row=progress(ref,target='job');row['execution_status']=status;row['result_available']=status['result_available'];return row
    values={'baseline':snapshot('baseline'),'growth':snapshot('growth',elapsed=8,size=100),
        'closed':snapshot('closed',state='returned',outcome='succeeded',elapsed=8)}
    reader=SimpleNamespace(read_progress=lambda ref,scope:deepcopy(values[ref]))
    project=calculator(axis)(reader,information_unit=.25)
    selection={**selection,'known_progress_refs':['baseline','growth','closed'],'initial_progress_refs':['baseline']}
    result=project(context,selection)
    assert result['credit']==.25
    assert [r['progress_ref'] for r in result['monitoring_information_contributions']]==['closed']
