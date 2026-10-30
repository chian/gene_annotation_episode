"""New decoded formats through actual selected native work and both return boundaries.

These engineering cases use the existing scripted Workflow fixture. Each selects
one tiny local conversion; native bytes, calculation, publication and typed
communication are production paths. They do not establish biological annotation,
configured-model choices, external services or historical format coverage.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.native_hmmer_preparation_worker import recalculate_hmmer_preparation
from test_native_hmmer_preparation_nested_workflow import (
    PREFIX, assert_accounting, assert_return_replay, nested_case,
)
from test_native_hmmer_preparation_workflow import assert_projected_values, forbid_work


@pytest.mark.parametrize('mode,encoding', [
    ('binary', 'hmmer3_binary_probability'),
    ('legacy_hmmer2', 'hmmer2_ascii_millibit_log_odds'),
])
def test_decoded_format_reaches_both_parents_and_saved_only_recalculation(
        tmp_path, monkeypatch, mode, encoding):
    case = nested_case(tmp_path, 'hmmconvert', mode)
    try:
        assert_accounting(case)
        body = case.outcome['result']
        assert body['complete'] and case.returned['completed'], body['failures']
        prepared = body['prepared']
        sheet_bytes = case.store.get_artifact(prepared['sheet_artifact_ref'])
        component_bytes = case.store.get_artifact(prepared['calculations_artifact_ref'])
        sheet, components = json.loads(sheet_bytes), json.loads(component_bytes)
        grading = json.loads(case.store.get_artifact(prepared['grading_artifact_ref']))
        assert grading['sheet'] == sheet and grading['calculations'] == components
        extraction, = [value for value in sheet['model_extractions']
            if value['occurrence']['direction'] == 'output']
        assert extraction['population'] == {
            'decoded_count': 1, 'complete': True, 'state': 'decoded'}
        record, = extraction['records']
        assert record['length'] == 12 and record['sequence_count'] == 3
        assert len(record['positions']) == 12
        assert record['representation']['encoding'] == encoding
        assert record['locator']['record_ordinal'] == 0
        assert record['record_key'] == extraction['occurrence']['occurrence_id'] + '#model/0'
        original = case.store.get_artifact(extraction['occurrence']['artifact_ref'])
        assert hashlib.sha256(original).hexdigest() == extraction['occurrence']['sha256']
        assert len(original) == extraction['occurrence']['size_bytes']
        if mode == 'binary':
            assert original[:4] == bytes.fromhex('baedede8')
            cell = record['positions'][0]['match']['cells'][0]
            source = cell['source']
            assert bytes.fromhex(source['raw_hex']) == original[source['byte_start']:source['byte_end']]
            assert record['representation']['legacy'] is None
        else:
            assert original.startswith(b'HMMER2.0')
            null = record['representation']['legacy']['null_emissions']['cells'][0]
            cell = record['positions'][0]['match']['cells'][0]
            assert null['source']['score'] == 656
            assert cell['source']['score'] == 3666
            assert cell['source']['nominal_probability'] > 1
            assert cell['probability'] is None
            assert cell['state'] == 'quantized_out_of_range'
            assert record['effective_sequence_count'] is None
        output, = [row for row in components['rows']
            if row['kind'] == 'population' and row['direction'] == 'output']
        assert output['decoded_model_count']['value'] == 1
        assert output['decoded_model_count']['state'] == 'present'
        comparison, = [row for row in components['rows'] if row['kind'] == 'model_comparison']
        assert comparison['source_length']['value'] == comparison['output_length']['value'] == 12
        assert comparison['output_record_key'] == record['record_key']
        assert comparison['compared_cell_count']['value'] > 0
        if mode == 'binary':
            assert comparison['compared_cell_count']['value'] == 611
        else:
            assert any(check['code'] == 'model_probability_equivalence'
                and check['state'] != 'pass' for check in components['checks'])

        assert_projected_values(case.returned, case.selector, components)
        assert case.forwarded == {name: case.returned[name] for name in ('rows', 'population')}
        received = case.owner.native_hmmer_preparation_returns.received_facts(
            case.root_context, case.science_form)
        assert received == {PREFIX + name: case.forwarded[name] for name in ('rows', 'population')}
        assert set(case.forwarded) == {'rows', 'population'}
        for row in case.forwarded['rows']:
            assert [cell['path'] for cell in row['quantities']] == case.selector['projection']['quantities']

        saved = deepcopy(sheet)
        with monkeypatch.context() as isolated:
            forbidden = forbid_work(isolated)
            isolated.setattr('builtins.open', forbidden)
            isolated.setattr(Path, 'open', forbidden)
            assert recalculate_hmmer_preparation(sheet, parameters=case.job['grading_parameters']) == components
            changed = recalculate_hmmer_preparation(sheet, parameters={'probability_tolerance': 1e-3})
            assert changed['parameters']['probability_tolerance'] == 1e-3
            assert changed['rows'][0]['decoded_model_count']['value'] == 1
        assert sheet == saved
        assert case.store.get_artifact(prepared['sheet_artifact_ref']) == sheet_bytes
        assert case.store.get_artifact(prepared['calculations_artifact_ref']) == component_bytes
        assert_return_replay(case, monkeypatch)
        (tmp_path / 'FORMAT_DELIVERY.json').write_text(json.dumps({
            'mode': mode, 'scope': 'scripted choices; actual local native and Workflow paths',
            'source_sha256': extraction['occurrence']['sha256'],
            'decoded_count': output['decoded_model_count'],
            'comparison': comparison, 'returned': case.returned, 'forwarded': case.forwarded,
            'saved_recalculation_equal': True, 'replay_preserves_observations': True,
        }, indent=2, allow_nan=False) + '\n')
    finally:
        case.store.close()
