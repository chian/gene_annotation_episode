"""Original Launch-parent schemas are independent of a child's public role."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

AXIS=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]
HOMES=sorted(str(path.parent.relative_to(ROOT)) for path in ROOT.rglob('episode.py')
    if 'tests' not in path.parts and 'class ExecutionEpisode(' in path.read_text())


@pytest.fixture(params=HOMES)
def parent_form(request):
    cls=import_module(AXIS+'.'+request.param.replace('/','.')+'.episode').ExecutionEpisode
    binding=object.__new__(cls)
    binding.resources={'original-api':{'kind':'api','service':'bvbrc_appservice'}}
    schema={'type':'object','properties':{'version':{'const':'original_test_request'}},
        'required':['version'],'additionalProperties':False}
    binding._request_schema=lambda *args,**kwargs:deepcopy(schema)
    checked=[]
    def validate(value,**kwargs):
        checked.append((deepcopy(value),kwargs))
        return value
    binding._validate_request=validate
    binding.api_execution=SimpleNamespace(validate_assignment=validate)
    form={'version':'execution_launch_assignment_v1',
        'requests':{'original-api':{'version':'original_test_request'}},
        'immutable_input_versions':[],'constraints':{}}
    return binding,form,checked


def test_original_parent_form_retains_request_identity_and_scope_validation(parent_form):
    binding,form,checked=parent_form
    original=deepcopy(form)
    assert binding._launch(form,scope={'original':'scope'})==original
    assert form==original
    assert checked==[({'version':'original_test_request'},{'resource_id':'original-api'}),
        ({'version':'original_test_request'},{'scope':{'original':'scope'}})]
    if binding.roles!=('launch',):
        with pytest.raises(ValueError,match='unknown_execution_episode_role'):
            binding.assignment_schema('launch')


def test_unknown_parent_resource_fails_before_request_execution(parent_form):
    binding,form,checked=parent_form
    form['requests']['unbound-api']=form['requests'].pop('original-api')
    with pytest.raises(ValueError,match='invalid_execution_launch_assignment'):
        binding._launch(form)
    assert checked==[]


def test_parent_constraints_keep_original_validator(parent_form):
    binding,form,checked=parent_form
    form['constraints']['allowed_resource_ids']='original-api'
    with pytest.raises(ValueError,match='invalid_execution_resource_constraints'):
        binding._launch(form)
    assert checked==[({'version':'original_test_request'},{'resource_id':'original-api'})]
