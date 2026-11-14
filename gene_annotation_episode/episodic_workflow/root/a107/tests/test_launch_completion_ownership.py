"""Launch completion uses its substantive owner and original global objects."""
from __future__ import annotations
import importlib
import inspect
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a107'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = ['/'.join(filter(None, (prefix, 'execution_job_submission'))) for prefix in PREFIXES]

@pytest.mark.parametrize('home', HOMES)
def test_completion_methods_and_globals_have_exact_private_owners(home):
    name = AXIS + '.' + home.replace('/', '.')
    episode = importlib.import_module(name + '.episode')
    goal = importlib.import_module(name + '.goal')
    completion = importlib.import_module(name + '.completion')
    owner = episode.ExecutionEpisode
    assert owner.roles == ('launch',)
    assert inspect.getattr_static(owner, 'instructions') is goal.LaunchGoal.__dict__['instructions']
    assert {name for name, value in goal.LaunchGoal.__dict__.items() if inspect.isfunction(value)} == {'instructions'}
    for method in ('_proof_for_action', 'completion_for_action', '_closed_completion_verdict', 'verify_completion'):
        function = completion.LaunchCompletion.__dict__[method]
        assert inspect.getattr_static(owner, method) is function
        assert function.__module__ == name + '.completion'
        assert function.__qualname__ == 'LaunchCompletion.' + method
        for global_name in ('ROLE_KINDS', 'canonical', 'digest', 'json', 'plain', 'validate_completion_proof'):
            assert function.__globals__[global_name] is goal.__dict__[global_name]
    assert owner.__mro__.index(completion.LaunchCompletion) < owner.__mro__.index(goal.LaunchGoal)
