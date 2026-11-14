"""Each private task selects its own scientific renderer at an optional transport port."""
import asyncio
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

AXIS = __package__.rsplit('.tests', 1)[0]
ROOT = Path(__file__).resolve().parents[1]
HOMES = tuple(sorted(str(path.parent.relative_to(ROOT)).replace('/', '.')
    for path in ROOT.rglob('episode.py') if 'class LiteratureEpisode(' in path.read_text()))


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('declared_transport', [False, True])
def test_private_task_keeps_original_transport_operands(home, declared_transport):
    Binding = import_module(AXIS + '.' + home + '.episode').LiteratureEpisode
    Task = Binding.decision_source_type
    module = (AXIS + '.' + home + '.prompts.literature_experimental_prompt'
        if (ROOT / home.replace('.', '/') / 'prompts/literature_experimental_prompt.py').is_file()
        else AXIS + '.library.literature_experimental_prompt')
    renderer = import_module(module).render_literature_experimental_prompt
    calls = []
    outcome = {'fixture': 'original transport response'}
    async def legacy(episode, role, instructions, context, schema):
        calls.append((episode, role, instructions, context, schema, None))
        return outcome
    async def declared(episode, role, instructions, context, schema, *, prompt_renderer):
        calls.append((episode, role, instructions, context, schema, prompt_renderer))
        return outcome
    provider = SimpleNamespace(complete=legacy)
    if declared_transport:
        provider.complete_with_presentation = declared
    task = object.__new__(Task)
    task.episode_id = 'actual-private-call'
    task.workflow = SimpleNamespace(provider=provider, specialist=lambda source: Binding)
    context = {'version': 'decision_context_v1', 'kind': 'decision_bootstrap', 'fields': {'original': True}}
    schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    returned = asyncio.run(task.decision_completion()(task.episode_id, 'REASONING', 'Original caller instructions', context, schema))
    assert returned is outcome
    assert calls == [('actual-private-call', 'REASONING', 'Original caller instructions', context, schema,
        None)]
    assert Binding.decision_prompt_renderer is renderer
