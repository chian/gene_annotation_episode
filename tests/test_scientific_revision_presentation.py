"""Retained process-revision failure and the existing child-selector interface."""
from copy import deepcopy
from functools import cache
import gzip
import json
from pathlib import Path

import pytest

from gene_annotation_episode.component_axis_literature_prompt import with_fact_contract_instructions
from gene_annotation_episode.scientific_process_prompt import (
    _information, _outcome, _values, render_scientific_process_prompt)
from gene_annotation_episode.tool_information import selectors
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


FIXTURE = Path(__file__).parent / 'fixtures/work_reports/a107-genomic02-revised-selection.json.gz'


@pytest.fixture
def actual(tmp_path):
    with Store(tmp_path / 'state') as store:
        tools = ToolRegistry(store)
        library = ScientificToolLibrary.freeze(tmp_path / 'tool-information',
            catalog=tools.catalog(), tool_info=True)
        yield store, tools, library, None


@cache
def retained_failure():
    return json.loads(gzip.decompress(FIXTURE.read_bytes()))


def test_actual_revised_selection_fits_the_observed_provider_interface():
    trace = retained_failure()
    state = deepcopy(trace['state'])
    before = deepcopy(state)
    original = trace['sent_text']
    assert trace['original_input_matches_sent']
    assert len(original) == trace['transport_failure']['input_chars']
    assert len(original) > trace['transport_failure']['provider_max_chars']
    rendered = with_fact_contract_instructions(
        render_scientific_process_prompt(state, trace['instructions']), state)
    projected = _outcome(state['last_local_outcome'])
    # Context JSON sorts stored keys; the original presentation has an explicit
    # field order. Preserve that order while restoring the recorded old values.
    old_view = {key: trace['old_outcome_view'][key] for key in projected
        if key in trace['old_outcome_view']}
    old_section = _values(_information(old_view))
    new_section = _values(_information(projected))
    assert original.count(old_section) == 1
    # The actual task, scientific values, uncertainty, receipts and controller
    # text are byte-identical; only the prepared-selection view changes.
    assert rendered == original.replace(old_section, new_section, 1)
    assert state == before
    # This is a retained provider-interface rejection, not a runtime budget.
    assert len(rendered) <= trace['transport_failure']['provider_max_chars']


def test_prepared_selectors_restore_complete_registered_child_information(actual):
    _, tools, library, _ = actual
    outcome = deepcopy(retained_failure()['state']['last_local_outcome'])
    chosen = selectors(outcome['result']['selection']['child_tool_info'])
    canonical = library.resolve_tool_info(chosen, tools.catalog())
    outcome['result']['selection']['child_tool_info'] = canonical
    before = deepcopy(outcome)
    shown = _outcome(outcome)
    assert shown['revision_origin'] == before['revision_origin']
    assert shown['result']['parent_selection_sha256'] == before['result']['parent_selection_sha256']
    assert shown['result']['version'] == before['result']['version']
    assert shown['result']['selection']['evidence_axis'] == before['result']['selection']['evidence_axis']
    assert shown['result']['selection']['thought_pattern'] == before['result']['selection']['thought_pattern']
    compact = shown['result']['selection']['child_tool_info']
    assert compact == chosen
    assert library.resolve_tool_info(compact, tools.catalog()) == canonical
    assert shown['prepared_child_tools'] == [
        {key: row[key] for key in ('name', 'description', 'resources')} for row in canonical]
    assert outcome == before


@pytest.mark.parametrize('result', [
    {'version': 'a107_genomic_detection_v1', 'present': None,
     'native_hits': [], 'uncertain_cds': [{'translation': None}]},
    {'version': 'scientific_process_child_selection_v1',
     'parent_selection_sha256': 'unknown', 'selection': {'unresolved': None}},
])
def test_other_results_and_invalid_preparations_retain_their_original_values(result):
    outcome = {'status': 'partial', 'result': result,
        'revision_origin': {'version': 'unknown'}, 'errors': [{'code': 'original_failure'}]}
    before = deepcopy(outcome)
    assert _outcome(outcome) == before
    assert outcome == before
