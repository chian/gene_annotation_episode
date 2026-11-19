"""The parent asks the real model which field to extract; the runner records the call and resume replays it.

The commissioner leaves the field unchosen, so ``fact_collection``'s task asks the model (``ModelRequest``)
through the standard ``ModelProvider`` over the packaged ``[models]`` configuration. Nothing in the episode
files records the call: the runner journals its request and response, keyed by unit and call index, and a
resumed run returns the recorded response without starting another model process.

Selected only with ``-m model_run`` (see ``pyproject.toml``); it needs the owner's Codex sign-in.
"""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from .fact_collection.episode import FactCollection
from .fact_collection.fact_extraction.episode import FactExtraction
from .probe_world import again, probe_path, run, world  # noqa: F401 - ``world`` is the fixture
from .test_system_recording import CONTINUATION, PARENT, parent_path

RUN_ID = 'fact_collection_model_run'


@pytest.mark.model_run
def test_the_model_chooses_the_field_and_resume_replays_its_recorded_answer(tmp_path):
    store = Store(tmp_path / 'store')
    subject = store.artifact(json.dumps({'name': 'GeneX', 'function': 'kinase'}), 'application/json')
    calls = tmp_path / 'model_calls'
    provider = ModelProvider(load_config(), calls, tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    collaborators = {'store': store, 'model_provider': provider, 'continuation': CONTINUATION, 'services': {}}
    registry = BindingRegistry([FactCollection(), FactExtraction()])
    entry = {'selection': [], 'assignment': {'subject_refs': [subject]}, 'message': {'fields': ['name', 'function']}}

    first = asyncio.run(link(registry, PARENT, entry, run_id=RUN_ID, journal=journal,
                             collaborators=collaborators).run())['result'].as_record()
    recorded = journal.model_calls(RUN_ID, parent_path(RUN_ID))
    assert recorded and all(call['position'] == 0 for call in recorded)
    assert len(list(calls.glob('call-*'))) == len(recorded)
    chosen = recorded[-1]['response']['field']
    assert chosen in ('name', 'function')
    assert first['finding']['facts'] == [{'name': 'GeneX', 'function': 'kinase'}[chosen]]
    assert first['credit'] == 2.0 and journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    child = journal.units(RUN_ID, parent_path(RUN_ID))[0]
    assert child[2]['kind'] == 'child' and child[2]['slot'] == 'extraction'
    assert child[2]['report'] == {'fact': first['finding']['facts'][0]}

    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators).run())['result'].as_record()
    assert resumed == first
    assert len(list(calls.glob('call-*'))) == len(recorded)
    assert journal.model_calls(RUN_ID, parent_path(RUN_ID)) == recorded
    store.close()


def named(world):
    return [{'ref': world['unrelated'], 'name': 'GeneY'}, {'ref': world['subject'], 'name': 'GeneX'}]


@pytest.mark.model_run
def test_a_model_named_record_that_is_not_held_is_rejected_and_the_recorded_calls_replay(world):
    """The model is asked for the record named GeneY, which the Episode does not hold: ``action`` rejects the
    answer as an invalid answer (the record is an argument of the episode's own tool, not a commission), the
    feedback goes into the next request, and the model then names the held record. The unit the answer chose is
    interrupted; the resumed run is given the recorded answers and asks the model nothing. The request carries a
    value ``decide`` read from a service: the service's value changes before the resume, and the rebuilt request
    still equals its record, because the read was recorded with the decision."""
    journal, path = world['journal'], probe_path('named')
    log = world['tmp'] / 'side_effects.log'
    plan = [{'model': {'records': named(world), 'wanted': 'GeneY'}, 'count_in_context': True, 'then': 'effect',
             'arguments': {'log': str(log)}}]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='interrupted after the side effect'):
        run(world, 'named', plan)
    calls = journal.model_calls('named', path)
    assert len(calls) >= 2 and all(call['position'] == 0 for call in calls)
    assert [call['call_index'] for call in calls] == list(range(len(calls)))
    assert calls[0]['response'] == {'ref': world['unrelated']} and calls[0]['request']['context']['feedback'] is None
    for before, after in zip(calls, calls[1:]):
        assert before['response'] == {'ref': world['unrelated']}        # every earlier answer was rejected
        assert after['request']['context']['feedback'] == {'not_held': world['unrelated']}
    assert calls[-1]['response'] == {'ref': world['subject']}
    assert journal.units('named', path) == []                           # a rejection created no unit
    asked = len(list(world['calls'].glob('call-*')))
    assert asked == len(calls)
    assert all(call['request']['context']['count'] == 0 for call in calls)
    assert journal.service_reads('named', path) == [{
        'position': 0, 'request': {'service': 'counter', 'member': 'count', 'arguments': []}, 'value': 0}]
    # The service's value changes. The decision is rebuilt from the recorded read, so every request equals its
    # record and the recorded answers replay.
    world['switch'].fail = False
    world['counter'].count = 5
    result = again(world, 'named')
    assert len(journal.service_reads('named', path)) == 1
    assert result['record'].units_consumed == 1
    outcome = journal.units('named', path)[0][2]
    assert outcome['tool'] == 'effect' and outcome['arguments']['ref'] == world['subject']
    assert outcome['outcome']['resumed'] is True
    assert journal.model_calls('named', path) == calls and len(list(world['calls'].glob('call-*'))) == asked


@pytest.mark.model_run
def test_a_tool_asks_the_model_through_its_context_and_a_rerun_is_given_the_recorded_answer(world):
    """One unit: ``decide`` asks the model which record to use (call 0), then the tool it chose asks the model a
    question through ``ctx.model`` (call 1) and is interrupted. The rerun gets both recorded answers."""
    journal, path = world['journal'], probe_path('asks')
    plan = [{'model': {'records': named(world), 'wanted': 'GeneX'}, 'then': 'ask',
             'arguments': {'instructions': 'Answer the question with one word.',
                           'question': 'Which of the two words is the opposite of cold: hot or wet?'}}]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='cut after the model answered'):
        run(world, 'asks', plan)
    calls = journal.model_calls('asks', path)
    assert [(call['position'], call['call_index']) for call in calls] == [(0, 0), (0, 1)]
    assert calls[0]['response'] == {'ref': world['subject']}
    assert calls[1]['request']['context'] == {'question': plan[0]['arguments']['question']}
    answer = calls[1]['response']['answer']
    assert 'hot' in answer.lower()
    asked = len(list(world['calls'].glob('call-*')))
    assert asked == 2 and journal.units('asks', path) == []
    world['switch'].fail = False
    result = again(world, 'asks')
    assert result['record'].units_consumed == 1
    assert journal.units('asks', path)[0][2]['outcome'] == {'answer': answer, 'resumed': True}
    assert journal.model_calls('asks', path) == calls and len(list(world['calls'].glob('call-*'))) == asked
