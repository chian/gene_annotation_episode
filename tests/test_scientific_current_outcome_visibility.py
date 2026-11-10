"""Current authorized data and actual credit explanations reach the model."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.scientific_process_prompt import render_episode_steering


@pytest.mark.parametrize('result,marker', [
    ({'source_ref': 'source_' + '1' * 24, 'artifact_ref': 'artifact_' + '2' * 64,
      'representation': 'original', 'start': 37, 'end': 107,
      'text': '{"dataset_id":"actual_chemical_panel_contents_9f2e","cofactor":null}'},
     'actual_chemical_panel_contents_9f2e'),
    ({'source_ref': 'source_' + '1' * 24, 'artifact_ref': 'artifact_' + '2' * 64,
      'matches': [{'witness': {'source_ref': 'source_' + '1' * 24,
          'start': 37, 'end': 71, 'quote': 'actual_source_witness_contents_8c7d'}}]},
     'actual_source_witness_contents_8c7d'),
    ({'outcome': {'native_outcome': {'returncode': 1,
          'stdout': 'actual_command_output_7b6c', 'stderr': 'original command diagnostic'}}},
     'actual_command_output_7b6c'),
])
def test_completed_work_summary_keeps_latest_authorized_tool_return(result, marker):
    state = {'completed_action_reports': [],
        'last_local_outcome': {'status': 'completed', 'result': result},
        'working_state': {}}
    rendered = render_episode_steering(state)
    assert 'Last own action outcome' in rendered
    assert marker in rendered


def test_original_finding_exclusion_and_progress_policy_reach_rendered_input():
    state = json.loads((Path(__file__).parent / 'fixtures/progress/'
        'a11030-missing-finding-feedback.json').read_text())
    before = deepcopy(state)
    rendered = render_episode_steering(state)
    assert 'typed_finding_not_recorded' in rendered
    assert 'assessment_382f2c9dad5b7bd617d38f05' in rendered
    documents = [json.loads(line) for line in rendered.splitlines()
        if line.startswith('{')]
    assert {'credit_binding': state['credit_binding'],
        'investigation_progress': state['investigation_progress']} in documents
    assert state == before
