"""Actual private controllers retain configured units and every observed outcome."""
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]
HOMES=sorted(str(path.parent.relative_to(ROOT)) for path in ROOT.rglob('episode.py')
    if 'tests' not in path.parts and 'class ExecutionEpisode(' in path.read_text())

@pytest.fixture(params=HOMES)
def configured(request):
    cls=import_module(AXIS+'.'+request.param.replace('/','.')+'.episode').ExecutionEpisode
    binding=object.__new__(cls);role=binding.roles[0]
    binding.private_yield_binding=True
    binding.handoff_unit=3.;binding.acquired_record_unit=4.
    binding._request_yield_class=lambda request:'original_selected_task'
    binding._validate_request=lambda assignment:assignment
    binding.verify_completion=lambda *args:False
    if role=='launch':
        assignment={'version':'execution_launch_assignment_v1',
            'requests':{'original-resource':{'version':'original-request'}},
            'immutable_input_versions':[],'constraints':{}}
        key='launch:original_selected_task'
        binding._launch=lambda assignment,**kwargs:assignment
        binding._permitted=lambda *args:True
        binding._received=lambda context:({'known_record_refs':[],'initial_known_record_refs':[]},{},{})
        binding.job_progress_provider=SimpleNamespace(targets=SimpleNamespace(usable_handoff=lambda target:True))
    elif role=='results':
        assignment={'version':'execution_results_assignment_v1','handoff_ref':'original-handoff',
            'selector':{'version':'original_selector'}}
        binding._target=lambda context:{'resource_kind':'api','service':'original_api'}
        binding._selector=lambda assignment,target:assignment['selector']
        key='results:api_original_api_original_selector'
    else:
        assignment={'version':'original-request','resource_id':'original-resource'}
        key=role+':original_selected_task'
    binding.task_yield_profiles={key:{'cutoff':.125,'parameters':{'uncertainty_alpha':.2}}}
    context=SimpleNamespace(role=role,assignment=assignment,scope={},path=((role,'original'),))
    return binding,context,key


def test_actual_selected_controller_keeps_original_units_settings_and_zero_outcome(configured):
    binding,context,_=configured
    controller=binding.yield_controller(context,0.,'original-epoch')
    assert controller.epoch=='original-epoch' and controller.initial_credit==0
    assert controller.cost==.125 and controller.settings.uncertainty_alpha==.2
    if context.role=='launch':assert controller.maximum_credit==3.
    observation=controller.observe('original-returned-unavailable',{'credit':0.})
    assert observation.unit_label=='original-returned-unavailable'
    assert observation.credit==observation.marginal_credit==0.
    assert controller.state().history==(0.,)


def test_missing_original_profile_is_not_replaced_by_a_default_controller(configured):
    binding,context,key=configured
    binding.task_yield_profiles.clear()
    with pytest.raises(ValueError,match='execution_original_task_yield_profile_required:'):
        binding.yield_controller(context,0.,'original-epoch')
