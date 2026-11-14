"""Exact selected call-expression controls; not whole Workflow/model validation.

Original is the retained own runtime expression. Candidate is extracted from the
actual imported private owner, so no hand-written candidate expression substitutes
for it. Full-module source inverses separately preserve journals/saved branches.
"""
import ast
import asyncio
from copy import deepcopy
import importlib
import inspect
import textwrap
from types import MethodType, SimpleNamespace
import pytest

BASE = 'gene_annotation_episode.episodic_workflow.root.a104'
HOMES = (
    ('execution_job_submission.task_decision', 'LaunchTaskDecision'),
    ('execution_progress_assessment.task_decision', 'MonitorTaskDecision'),
    ('homology_job_submission.task_decision', 'HomologySubmissionTaskDecision'),
)
DESCRIPTORS = ('raising_property', 'recording_property', 'instance_raw_original',
    'instance_bound_original', 'custom_dict_property', 'class_original_alias',
    'dict_subclass', 'non_string_collision_key', 'custom_metaclass')

@pytest.mark.parametrize('home,class_name', HOMES)
@pytest.mark.parametrize('case', DESCRIPTORS)
def test_original_complete_does_not_probe_presentation_descriptor(home, class_name, case):
    providers = importlib.import_module(BASE + '.providers')
    owner = getattr(importlib.import_module(BASE + '.' + home), class_name)
    events = []; token = object(); renderer = object()
    original_hook = providers.ModelConnection.complete_with_presentation

    class Raising(providers.ModelConnection):
        @property
        def complete_with_presentation(self):
            events.append('forbidden_presentation_getter')
            raise RuntimeError('original complete never read this property')

    class Recording(providers.ModelConnection):
        @property
        def complete_with_presentation(self):
            events.append('forbidden_presentation_getter')
            return MethodType(original_hook, self)

    class DictProperty(providers.ModelConnection):
        @property
        def __dict__(self):
            events.append('forbidden_dict_getter')
            raise RuntimeError('use the original instance-dict getset')

    class Alias(providers.ModelConnection):
        complete_with_presentation = original_hook

    class Metadata(type):
        def __getattribute__(self, name):
            if name == '__dict__': raise AssertionError('do not inspect custom metaclass dictionary')
            return type.__getattribute__(self, name)

    class WithMetadata(providers.ModelConnection, metaclass=Metadata):
        pass

    kind = {'raising_property': Raising, 'recording_property': Recording,
        'custom_dict_property': DictProperty, 'class_original_alias': Alias,
        'custom_metaclass': WithMetadata}.get(case, providers.ModelConnection)
    provider = object.__new__(kind); provider.worker_lock = asyncio.Lock()
    async def serial(self, *args, **kwargs):
        events.append(('serial', args, kwargs)); return token
    provider._complete_serial = MethodType(serial, provider)
    if case == 'dict_subclass':
        class Dictionary(dict):
            def __contains__(self, key): raise AssertionError('no custom contains')
            def items(self): raise AssertionError('no custom items')
            def get(self, *args): raise AssertionError('no custom get')
        provider.__dict__ = Dictionary(provider.__dict__)
    if case == 'non_string_collision_key':
        collision_armed = False
        class Key:
            def __hash__(self): return hash('complete_with_presentation')
            def __eq__(self, other):
                if collision_armed: raise AssertionError('no arbitrary key equality')
                return False
        provider.__dict__[Key()] = object()
        collision_armed = True
    if case == 'instance_raw_original': provider.complete_with_presentation = original_hook
    if case == 'instance_bound_original': provider.complete_with_presentation = MethodType(original_hook, provider)
    use_private = case in ('custom_dict_property', 'class_original_alias', 'dict_subclass')

    class Workflow:
        def __init__(self): self.provider = provider
        def specialist(self, source):
            assert use_private, 'fallback must not resolve renderer'
            events.append('renderer'); return SimpleNamespace(decision_prompt_renderer=renderer)
        @property
        def job_episodes(self):
            assert use_private, 'fallback must not resolve Homology renderer'
            events.append('renderer'); return SimpleNamespace(decision_prompt_renderer=renderer)

    source = SimpleNamespace(workflow=Workflow(), path=(('job_launch', 'control'),), episode_id='episode:descriptor-control')
    operands = ('episode:descriptor-control', 'REASONING', object(), {}, {})
    pending = (owner.decision_completion(source)(*operands) if hasattr(owner, 'decision_completion')
        else owner.complete_decision(source, *operands[2:]))
    assert asyncio.run(pending) is token
    assert events == (['renderer'] if use_private else []) + [
        ('serial', operands, {'prompt_renderer': renderer} if use_private else {})]

ORDER_CASES = ('ordinary', 'complete_getter_error', 'episode_error', 'operand_error',
    'operand_replaces_complete', 'operand_replaces_provider')

def selected_expression(owner, name, direct):
    module = ast.parse(textwrap.dedent(inspect.getsource(owner)))
    method = next(n for n in module.body[0].body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
    accepted = {'self.workflow.provider.complete'} if direct else {'self.complete_decision', 'self.decision_completion()'}
    found = [n for n in ast.walk(method) if isinstance(n, ast.Call) and ast.unparse(n.func) in accepted]
    assert len(found) == 1
    return deepcopy(found[0])

def invoke_expression(expression, site, schema_callback):
    wrapper = ast.parse('async def invoke(self, instructions, context, schema, request):\n    pass\n')
    body = []
    if site == 'call': body = ast.parse('instructions = self.instructions(context)').body
    body.append(ast.Return(value=ast.Await(value=expression)))
    wrapper.body[0].body = body
    namespace = {'_action_generation_schema': schema_callback}
    exec(compile(ast.fix_missing_locations(wrapper), '<actual-private-provider-expression>', 'exec'), namespace)
    return namespace['invoke']

