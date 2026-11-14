"""Legacy homology private-interface preservation, without claiming full composition."""
import asyncio
import importlib
from types import SimpleNamespace

import pytest

HOMES=['homology_job_submission','homology_job_monitoring','homology_result_acquisition']


@pytest.fixture(params=HOMES)
def binding(request):
    cls=importlib.import_module('gene_annotation_episode.episodic_workflow.root.a101.'+request.param+'.episode').HomologyEpisode
    value=object.__new__(cls)
    value.statistics=None
    value.native_event_provider=None
    value.monitoring_projector=lambda *args,**kwargs:0.5
    value._job_credit_calculator=lambda *args,**kwargs:0.75
    return value


def test_original_role_information_and_credit_units(binding):
    role,=binding.roles
    expected=0.5 if role=='job_monitor' else 0.75
    assert binding.initial_credit(object(),role,{'original':True},'child','run')==expected
    assert binding.credit_kind(role)==('monitoring' if role=='job_monitor' else 'operational')
    assert binding.instructions(role)


def test_original_assignment_and_state_are_read_without_native_poll(binding):
    role,=binding.roles
    assignment={'job_ref':'original','cpu':1}
    source=SimpleNamespace(path=((role,'child'),),request=SimpleNamespace(message=SimpleNamespace(as_record=lambda:{'job_assignment':assignment})))
    assert binding.assignment(source)==assignment
    assert binding.working_state(source)=={'role':role,'assignment':assignment}


def test_selected_job_failure_retains_original_job_and_operation(binding):
    role,=binding.roles
    binding.catalog=lambda source:[{'name':'homology.environment'}]
    binding.jobs=SimpleNamespace(_row=lambda ref:{'cpu':2,'search_mode':'native_defaults'})
    source=SimpleNamespace(path=((role,'child'),),request=SimpleNamespace(message=SimpleNamespace(as_record=lambda:{'job_assignment':{'job_ref':'original','cpu':1}})))
    result=asyncio.run(binding.execute(source,'homology.environment',{},operation_key='original-key'))
    assert result['status']=='failed' and result['record_refs']==[]
    assert result['feedback']['code']=='job_assignment_cpu_mismatch'
    assert result['feedback']['job_ref']=='original'
    assert result['feedback']['operation']=='homology.environment'
