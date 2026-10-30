"""Execute twelve constructed source callbacks. No actual native receipt/science."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from test_literature_ratio_source_inputs import callbacks
from gene_annotation_episode.literature_ratio_source_inputs import read_relative_signal_source_inputs
from gene_annotation_episode.literature_ratio_source_calculations import populate_relative_signal_v2
from gene_annotation_episode.literature_ratio_source_validation import validate_relative_signal_saved

HERE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_reader_070'
rows = json.loads((HERE / 'normative/EXAMPLES_004.json').read_text())
outputs = []
for row in rows:
    read_source, read_view, calls = callbacks()
    extraction = read_relative_signal_source_inputs(row['selection'], read_source=read_source,
        read_view=read_view, evidence_origin='synthetic_fixture')
    sheet = populate_relative_signal_v2(extraction)
    # Detached dictionary for pure saved checks; these identifiers deliberately
    # DO NOT claim that Store publication or a native operation happened.
    ref = 'source_' + '1' * 24
    outcome = {'status': 'completed', 'operation_ref': 'operation_' + '2' * 24,
        'record_refs': [ref], 'changed_record_refs': [ref], 'feedback': None,
        'result': {'sheet_ref': ref, 'cells': deepcopy(sheet['cells']),
            **{k: sheet[k] for k in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict')}}}
    validate_relative_signal_saved(row['selection'], extraction, sheet, outcome)
    expected = row['expected_sheet']
    actual = sheet['cells']['reported_ratio']
    for field in ('value', 'value_candidates', 'unavailable_reason'):
        assert actual[field] == expected['cells']['reported_ratio'][field], (row['name'], field)
    for field in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict'):
        assert sheet[field] == expected[field], (row['name'], field)
    outputs.append({'name': row['name'], 'origin': 'synthetic_fixture',
        'custody_claim': 'constructed callbacks/pixels/metadata only; no actual native Store/view receipt',
        'callback_calls': calls, 'extraction': extraction, 'sheet': sheet,
        'detached_saved_check_passed': True})
(HERE / 'ACTUAL_CONSTRUCTED_OUTPUTS_014.json').write_text(json.dumps(outputs, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
print(json.dumps({'executed_constructed_cases': len(outputs), 'actual_native_views': 0,
    'model_calls': 0, 'episode_actions': 0, 'artifact': str(HERE / 'ACTUAL_CONSTRUCTED_OUTPUTS_014.json')}))
