"""Exercise the original selector cases on installed Native tasks without provider transport."""
import asyncio
import importlib
from types import SimpleNamespace

import pytest

AXIS = 'a110'
HOMES = (
    'execution_job_submission.local_job_execution',
    'execution_job_submission.hpc_job_execution',
    'scientific_process.execution_job_submission.local_job_execution',
    'scientific_process.execution_job_submission.hpc_job_execution',
    'hpc_work_planning.execution_job_submission.local_job_execution',
    'hpc_work_planning.execution_job_submission.hpc_job_execution',
    'hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution',
    'hpc_work_planning.hpc_allocation_execution.execution_job_submission.hpc_job_execution',
    'scientific_process.hpc_work_planning.execution_job_submission.local_job_execution',
    'scientific_process.hpc_work_planning.execution_job_submission.hpc_job_execution',
    'scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution',
    'scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.hpc_job_execution',
)


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('variant', ('absent_binding', 'falsey_binding', 'custom_complete'))
def test_private_completion_preserves_original_callable_and_binding(home, variant):
    prefix = 'gene_annotation_episode.episodic_workflow.root.' + AXIS + '.'
    owner = importlib.import_module(prefix + home + '.episode').ExecutionEpisode
    provider_type = importlib.import_module(prefix + 'providers').ModelConnection
    provider = object.__new__(provider_type)
    provider.worker_lock = asyncio.Lock()
    calls, lookups = [], []
    result = object()

    async def complete(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    provider._complete_serial = complete
    renderer = object()

    class FalseyBinding:
        decision_prompt_renderer = renderer

        def __bool__(self):
            return False

    def specialist(source):
        lookups.append(source)
        return None if variant == 'absent_binding' else FalseyBinding()

    if variant == 'custom_complete':
        provider.complete = complete
    task = object.__new__(owner.decision_source_type)
    task.workflow = SimpleNamespace(provider=provider, specialist=specialist)
    arguments = ('original-episode', 'REASONING', 'original-instructions',
                 {'context': object()}, {'schema': object()})
    captured = task.decision_completion()
    if variant == 'custom_complete':
        # The original callable was acquired before call argument evaluation.
        provider.complete = None
    assert asyncio.run(captured(*arguments)) is result
    expected = {'prompt_renderer': renderer} if variant == 'falsey_binding' else {}
    assert calls == [(arguments, expected)]
    assert all(left is right for left, right in zip(calls[0][0], arguments))
    assert lookups == ([] if variant == 'custom_complete' else [task])
