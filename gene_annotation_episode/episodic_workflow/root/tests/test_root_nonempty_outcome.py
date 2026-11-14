"""Connect a genuine root unit/replay to its next outcome presentation."""
import asyncio
import inspect
import json
from pathlib import Path
import sys
import traceback

from gene_annotation_episode import ensembl_acquisition
from gene_annotation_episode.episodic_workflow.root.tests.nonempty_outcome_support import diagnose, save


def test_real_root_nonempty_outcome_replays_and_reaches_next_inputs(tmp_path):
    presenter = ensembl_acquisition.ensembl_outcome_view
    assert presenter.__module__ == 'gene_annotation_episode.ensembl_acquisition'
    assert Path(inspect.getsourcefile(presenter)).resolve() == Path(__file__).resolve().parents[3] / 'ensembl_acquisition.py'
    events = []

    def observe(frame, event, argument):
        if frame.f_code is presenter.__code__ and event in ('call', 'return'):
            events.append({'event': event, 'value': json.loads(json.dumps(
                frame.f_locals['outcome'] if event == 'call' else argument))})

    result = {'version': 'root_nonempty_outcome_test_v1', 'status': 'blocked',
        'scripted_engineering_caller': True, 'scientific_or_autonomous_validation_claim': False,
        'estimated_timestamp_schedules_no_wait_or_timer': True, 'new_stopping_gate': False,
        'replayed_original_without_provider_call': False, 'next_decision_inputs_completed': False}
    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        asyncio.run(diagnose(tmp_path, result))
        assert result['replayed_original_without_provider_call'] is True
        assert result['next_decision_inputs_completed'] is True
        original, replay = result['original'], result['replay']
        assert original['unit'] == replay['unit']
        assert original['last_outcome'] == replay['last_outcome']
        assert original['rows_at_exit'] == replay['rows_at_exit']
        presented = json.loads((tmp_path / 'next_decision_inputs.json').read_bytes())
        assert presented['context']['last_local_outcome'] == replay['last_outcome']
        assert presented['context']['controller'] == {key: replay['next_view']['controller_state'][key]
            for key in ('arms', 'annotation_credits', 'root_score', 'decision')}
        assert presented['context']['current_credit']['root_score'] == replay['credit_after_unit']['root_score']
        assert events == [{'event': 'call', 'value': replay['last_outcome']}, {'event': 'return', 'value': None}]
        result['status'] = 'passed'
    except Exception as error:
        result['failure'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
        raise
    finally:
        sys.setprofile(previous)
        result['real_presenter_events'] = events
        save(tmp_path / 'diagnostic.json', result)
