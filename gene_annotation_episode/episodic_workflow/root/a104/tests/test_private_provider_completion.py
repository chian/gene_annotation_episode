"""Real private/provider method controls; controlled serial transport, no model/native run.

Run unchanged against the explicitly copied current and corrected epochs. Current
failures are retained regression evidence; they must not be converted to xfails.
The 60-site source inverse separately proves the three dispatcher representations.
"""
import asyncio
import importlib
from types import MethodType, SimpleNamespace
import pytest

BASE = 'gene_annotation_episode.episodic_workflow.root.a104'
HOMES = (
    ('execution_job_submission.task_decision', 'LaunchTaskDecision'),
    ('execution_progress_assessment.task_decision', 'MonitorTaskDecision'),
    ('homology_job_submission.task_decision', 'HomologySubmissionTaskDecision'),
)
CASES = ('default', 'subclass_return', 'subclass_exception', 'instance_return',
    'instance_exception', 'baseclass_replacement', 'property_once',
    'callable_instance', 'no_presentation_probe', 'custom_presentation')

@pytest.mark.parametrize('home,class_name', HOMES)
@pytest.mark.parametrize('case', CASES)
def test_original_complete_authority_and_private_base_renderer(home, class_name, case, monkeypatch):
    providers = importlib.import_module(BASE + '.providers')
    owner = getattr(importlib.import_module(BASE + '.' + home), class_name)
    events = []; answer = object(); marker = object(); error = RuntimeError('same controlled callback error')
    instructions = object(); context = {}; schema = {}
    operands = ('episode:provider-control', 'REASONING', instructions, context, schema)

    async def custom(*args):
        events.append(('complete', args))
        if case.endswith('exception'): raise error
        return answer

    async def custom_method(self, *args): return await custom(*args)

    class Subclass(providers.ModelConnection):
        async def complete(self, *args): return await custom(*args)

    class PropertyOwner(providers.ModelConnection):
        @property
        def complete(self):
            events.append(('complete_lookup',))
            return custom

    class NoPresentationProbe(Subclass):
        @property
        def complete_with_presentation(self):
            raise AssertionError('custom complete must not probe presentation')

    class CustomPresentation(providers.ModelConnection):
        async def complete_with_presentation(self, *args, **kwargs):
            raise AssertionError('original complete did not select custom presentation')

    kind = (Subclass if case.startswith('subclass_') else PropertyOwner if case == 'property_once'
        else NoPresentationProbe if case == 'no_presentation_probe'
        else CustomPresentation if case == 'custom_presentation' else providers.ModelConnection)
    provider = object.__new__(kind)
    provider.worker_lock = asyncio.Lock()

    async def serial(self, *args, **kwargs):
        events.append(('serial', args, kwargs))
        return answer
    provider._complete_serial = MethodType(serial, provider)
    if case.startswith('instance_'): provider.complete = custom
    if case == 'baseclass_replacement': monkeypatch.setattr(providers.ModelConnection, 'complete', custom_method)
    if case == 'callable_instance':
        class Callable:
            def __getattribute__(self, name):
                if name in ('__func__', '__self__'): raise AssertionError('no callable identity probing')
                return object.__getattribute__(self, name)
            async def __call__(self, *args): return await custom(*args)
        provider.complete = Callable()

    class Workflow:
        def __init__(self): self.provider = provider
        def specialist(self, task):
            assert case == 'default', 'custom complete must not resolve a renderer'
            events.append(('specialist', task))
            return SimpleNamespace(decision_prompt_renderer=marker)
        @property
        def job_episodes(self):
            assert case == 'default', 'custom complete must not resolve a Homology renderer'
            events.append(('job_episodes',))
            return SimpleNamespace(decision_prompt_renderer=marker)

    source = SimpleNamespace(workflow=Workflow(), episode_id=operands[0], path=(('job_launch', 'control'),))
    try:
        pending = (owner.decision_completion(source)(source.episode_id, 'REASONING', instructions, context, schema)
            if hasattr(owner, 'decision_completion') else owner.complete_decision(source, instructions, context, schema))
        result = asyncio.run(pending)
    except BaseException as caught:
        assert case.endswith('exception') and caught is error
    else:
        assert not case.endswith('exception') and result is answer
    deliveries = [row for row in events if row[0] in ('complete', 'serial')]
    assert len(deliveries) == 1
    assert len(deliveries[0][1]) == len(operands)
    assert deliveries[0][1][:2] == operands[:2]
    assert all(a is b for a, b in zip(deliveries[0][1][2:], operands[2:]))
    if case == 'default':
        assert deliveries[0][0] == 'serial' and deliveries[0][2] == {'prompt_renderer': marker}
        assert len(events) == 2
    elif case == 'custom_presentation':
        assert events == [('serial', operands, {})]
    else:
        assert deliveries[0][0] == 'complete'
        assert events == ([('complete_lookup',)] if case == 'property_once' else []) + [('complete', operands)]
