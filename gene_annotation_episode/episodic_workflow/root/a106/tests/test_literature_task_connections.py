"""Literature tasks retain executed outcomes, original progress and saved replay."""
import asyncio
from contextlib import nullcontext
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
ROOT = Path(__file__).resolve().parents[1]
HOMES = sorted(str(p.parent.relative_to(ROOT)) for p in ROOT.rglob('episode.py')
    if 'published_evidence_assessment' in p.parts and 'tests' not in p.parts and 'class LiteratureEpisode(' in p.read_text())
runtime = importlib.import_module(PACKAGE + '.runtime')


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
def test_original_literature_action_status_credit_and_saved_replay(home, status):
    Binding = importlib.import_module(PACKAGE + '.' + home.replace('/', '.') + '.episode').LiteratureEpisode
    Task = getattr(Binding, 'decision_source_type', runtime.DecisionSource)
    saved, events = {}, []
    async def execute(source, name, arguments, **kwargs):
        events.append(('operation', name, kwargs['operation_key']))
        return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None}
    async def score(source, index, result):
        events.append(('grading', index))
        return result
    task = object.__new__(Task)
    task.episode_id, task.path, task.scope = 'literature-test', ((Binding.roles[0], 'child'),), {}
    task.checkpoint = lambda: None
    task.workflow = SimpleNamespace(run_id='run', execution_binding=None, pending_work=lambda source: [],
        
        journal=SimpleNamespace(row=lambda table, episode, index: saved.get(index),
            save=lambda table, row: saved.__setitem__(row['decision_index'], row), measure=lambda *args: nullcontext()),
        execute=execute, receive_native_outcome=lambda *args: None,
        receive_outcome=lambda source, selection, result, index: events.append(('receive', index)),
        automatic_score_updates=score,
        source_credit_view=lambda source: events.append(('credit', 0.75)) or {'credit': 0.75},
        controller_value=lambda source, index, credit: {'original_index': index, 'credit': credit})
    selection = {'kind': 'tool', 'tool': 'source.read', 'arguments': {'source_ref': 'actual-original'}}
    result = asyncio.run(task.execute(selection, 7))
    assert asyncio.run(task.execute(selection, 7)) == result == {'original_index': 7, 'credit': 0.75}
    assert events == [('operation', 'source.read', 'run:literature-test:7'), ('receive', 7), ('grading', 7), ('credit', 0.75)]
    assert json.loads(saved[7]['action']) == selection
    assert json.loads(saved[7]['result'])['status'] == status
