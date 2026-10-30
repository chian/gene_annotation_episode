"""A selected A105 V2 kinetic dependency reaches the receiving parent as text."""
from copy import deepcopy
import re

from gene_annotation_episode.literature_a105_worksheet import VERSION, VERSION_V2
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
import test_literature_a105_native_dependency_307 as original_case


def _parent(form):
    return {
        'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
        'goal': {'objective': 'Assess the returned Pa0142 substrate comparisons.'},
        'literature_assignment': {},
        'child_reports': [form],
        'action_yields': {'rows': []},
        'controller': {},
        'working_state': {},
    }


def test_selected_pa0142_v2_return_and_cold_read_reach_parent_steering(tmp_path, monkeypatch):
    # Reuse the original selected two-contrast and cold reconstruction test;
    # observe only its already validated typed form, never a private sheet.
    admitted = []
    validate = original_case.validate_a105_worksheet_links

    def record_admitted(form, schema, assignment, *, read_public_record):
        result = validate(form, schema, assignment, read_public_record=read_public_record)
        if form['assessment_context']['version'] == VERSION_V2 and form['assessment_context']['quantity_links']:
            admitted.append(deepcopy(form))
        return result

    monkeypatch.setattr(original_case, 'validate_a105_worksheet_links', record_admitted)
    original_case.test_pa0142_reused_numerator_links_in_selected_return_and_cold_read(tmp_path, monkeypatch)
    assert admitted
    form = admitted[0]
    task_text = 'Assess what the returned Pa0142 substrate comparisons establish and retain their uncertainty.'
    before = render_literature_experimental_prompt({**_parent(form), 'child_reports': []}, task_text)
    after = render_literature_experimental_prompt(_parent(form), task_text)
    task_before, _ = before.split('\n\nSTEERING\n', 1)
    task_after, steering = after.split('\n\nSTEERING\n', 1)
    assert task_after == task_before
    assert task_text in task_after
    assert steering.count('A105 experimental evidence worksheet') == 1
    assert steering.count('one shared original physical measurement; dependent contrasts, not independent experimental evidence') == 1
    assert 'parameter_ratio' in steering
    assert all(str(row['value']) in steering for row in form['kinetics']
        if row['component'] == 'parameter_ratio')
    assert 'numeric_tokens' not in steering and 'measurement_ref' not in steering
    assert VERSION_V2 not in steering
    assert not re.search(r'\b(?:source|artifact|operation)_[0-9a-f]{24,64}\b', steering)

    # The V1 presentation still takes the original path and cannot display a
    # relationship that its schema does not admit.
    prior = deepcopy(form)
    prior['assessment_context'] = {'version': VERSION, 'assertion_refs': [],
        'quantity_links': [], 'assertion_links': []}
    v1_task, v1_steering = render_literature_experimental_prompt(_parent(prior), task_text).split('\n\nSTEERING\n', 1)
    assert v1_task == task_after
    assert v1_steering.count('A105 experimental evidence worksheet') == 1
    assert 'one shared original physical measurement' not in v1_steering
