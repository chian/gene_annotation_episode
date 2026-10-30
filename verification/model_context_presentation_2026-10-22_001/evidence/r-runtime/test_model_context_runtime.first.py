"""Saved model presentation with original calculation inputs; isolated fixtures.

All work uses scripted providers and synthetic semantic records. No configured
model, public client, native executable or scientific workspace is invoked.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import runtime
from gene_annotation_episode.domain import ContractError
from method_loop.durable import canonical
from test_runtime import (FixtureController, ScriptedProvider, fixture_credit,
    obj, reason, run, setup)


MODE = 'bounded_wait_history_v1'
VERSION = 'runtime_model_call_request_v2'


class CapturingProvider(ScriptedProvider):
    def __init__(self, script, *, has_session=False):
        super().__init__(script)
        self.session = has_session
        self.instructions = []
        self.schemas = []
        self.texts = []

    def has_session(self, *_):
        return self.session

    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.instructions.append(instructions)
        self.schemas.append(deepcopy(output_schema))
        self.texts.append(json.dumps(context, allow_nan=False))
        return await super().complete(episode_id, role, instructions, context, output_schema)


def host(tmp_path, *, mode=True, preview_size=24, provider=None):
    store, tools = setup(tmp_path)
    settings = {'preview_size': preview_size}
    if mode:
        settings['model_presentation'] = MODE
    provider = provider or CapturingProvider([])
    workflow = runtime.Workflow(store, tools, provider, tmp_path/'run', 'presentation-fixture',
        lambda path, initial: FixtureController(str(path), initial, 50), fixture_credit,
        restoration_settings=settings)
    source = workflow.build('annotation', 'root', 'Keep exact original fixture inputs',
        {'subject_refs': ['subject_A']}).source
    return SimpleNamespace(store=store, tools=tools, workflow=workflow, source=source,
        provider=provider)


def saved_call(h, index=0):
    return h.workflow.journal.row('runtime_model_calls', h.source.episode_id, index)


def forbidden(*_, **__):
    raise AssertionError('Saved request replay must not capture current state')


def test_pending_legacy_request_text_is_byte_identical_across_fresh_transport(tmp_path, monkeypatch):
    h = host(tmp_path, mode=False,
        provider=CapturingProvider([KeyboardInterrupt()], has_session=True))
    schema = obj({})
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(h.source.call({'visible_record_refs': [], 'unicode': 'μ', 'z': -0.0}, schema))
    first = saved_call(h)
    original = json.loads(first['request'])
    assert 'restored_episode_history' not in original['context']
    # Valid formatting variations are original captured TEXT, not an excuse to
    # normalize a pending request at the dispatch/response upserts.
    text = json.dumps({'schema': original['schema'], 'context': original['context']},
        ensure_ascii=True, indent=3) + '\n'
    h.store.db.execute('UPDATE runtime_model_calls SET request=?', (text,))
    provider = CapturingProvider([reason(0)], has_session=False)
    h.workflow.provider = provider
    monkeypatch.setattr(h.workflow, 'history_preview', forbidden)
    monkeypatch.setattr(h.workflow, 'waiting_support', forbidden)
    monkeypatch.setattr(h.workflow, 'api_execution_planning_context', forbidden)
    h.source.calls = 0
    response, index, context, actual_schema = asyncio.run(h.source.call({}, obj({'new': {'type': 'string'}})))
    assert saved_call(h)['request'] == text
    assert response == reason(0) and index == 0
    assert context == original['context'] == provider.contexts[0]
    assert actual_schema == schema
    assert provider.schemas == [runtime._action_generation_schema(schema)]
    assert h.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
