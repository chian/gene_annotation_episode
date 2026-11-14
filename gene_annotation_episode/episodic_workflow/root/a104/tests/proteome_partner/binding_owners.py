"""Explicit original placements; actual configured owners perform each role."""
from importlib import import_module

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
PLACEMENTS = ('', 'scientific_process/', 'hpc_work_planning/',
    'hpc_work_planning/hpc_allocation_execution/', 'scientific_process/hpc_work_planning/',
    'scientific_process/hpc_work_planning/hpc_allocation_execution/')


def binding_types(placement):
    assert placement in PLACEMENTS
    selected = []
    for suffix, role in (('execution_result_acquisition', 'results'),
            ('execution_job_submission/api_job_execution', 'launch_api'),
            ('execution_job_submission', 'launch')):
        path = placement + suffix
        actual = import_module(PREFIX + path.replace('/', '.') + '.episode').ExecutionEpisode
        assert actual.binding_path == path and actual.roles == (role,)
        selected.append(actual)
    return tuple(selected)
