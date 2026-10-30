"""Actual source-function output from explicitly synthetic supplied events.

The original CSV branch executes unchanged. This verifies its report format;
it does not establish an upstream FCS deployment or a new biological finding.
"""
import ast
import hashlib
import json
import os
from pathlib import Path

from gene_annotation_episode.fluorescence_execution_common import identity
from test_native_fluorescence_contracts import event_input, job


SOURCE_PATH = Path('reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/cell_biology.py')
FUNCTION_SHA256 = 'c400891a22aa723c1fb8d42cce9f2c7b9a8241f9a8c16467780c7c2b6e138fb7'


def test_original_facs_csv_function_numbers_reach_report_parser(tmp_path):
    from gene_annotation_episode.fluorescence_native_report_contracts import make_fluorescence_report_binding
    from gene_annotation_episode.fluorescence_native_reports import parse_fluorescence_native_reports

    attempt = Path(os.environ['HMMER529_ATTEMPT']).resolve(strict=True)
    snapshot = attempt / 'source_snapshot'
    assert Path(__file__).resolve().is_relative_to(snapshot)
    source = (snapshot / SOURCE_PATH).read_text()
    node, = [n for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef) and n.name == 'perform_facs_cell_sorting']
    original_function = ast.get_source_segment(source, node) + '\n'
    assert hashlib.sha256(original_function.encode()).hexdigest() == FUNCTION_SHA256
    # Execute the complete original function, not its module's unrelated imports.
    # The AST/function body is unchanged and the original source is frozen above.
    namespace = {'__name__': 'retained_native_facs_source'}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(snapshot / SOURCE_PATH), 'exec'), namespace)
    event_bytes = b'signal\n10\n50\n110\n200\n'
    supplied = event_input(tmp_path, event_bytes)
    selected = job(tmp_path, inputs=[supplied])
    selected_csv = tmp_path / 'sorted_cells.csv'
    log = namespace['perform_facs_cell_sorting'](supplied['path'], 'signal',
        threshold_min=50, threshold_max=110, output_file=str(selected_csv))
    raw = log.encode('utf-8')
    assert '## Error' not in log
    assert selected_csv.read_bytes() == b'signal\n50\n110\n'
    report_file = identity(raw, format='text/plain')
    report_path = tmp_path / 'original_facs_report.txt'
    report_path.write_bytes(raw)
    expected = {'original_count': 4, 'selected_count': 2, 'selected_percent': 50.0,
        'selected_mean': 80.0, 'selected_median': 80.0,
        'lower_remaining_count': 3, 'upper_remaining_count': 2}
    report_input = {'file': report_file, 'path': str(report_path), 'source_key': 'original-report',
        'profile': 'biomni_facs_log_548_v1', 'association_file': None,
        'fields': [{'key': metric, 'locator': {'kind': 'facs_metric',
            'metric': metric, 'occurrence': 0}, 'component_request': None} for metric in expected]}
    binding = make_fluorescence_report_binding(report_input,
        definitions=selected['definitions'], event_inputs=selected['inputs'], preparations=[])
    result = parse_fluorescence_native_reports(raw, binding=binding, association_raw=None)
    rows = {row['key']: row for row in result['reports']}
    assert {key: row['value'] for key, row in rows.items()} == expected
    assert all(row['file'] == report_file and row['component_request'] is None for row in rows.values())
    for row in rows.values():
        where = row['location']
        assert row['raw'].encode() in raw[where['byte_start']:where['byte_end']]
    assert rows['selected_percent']['unit'] == 'percent'
    assert rows['selected_percent']['decimal_places'] == 2
    assert result['provenance']['producer_execution'] == 'unverified'
    # The pure parser cannot infer execution provenance from the log. This test's
    # separate receipt records actual execution without upgrading that claim.
    (tmp_path / 'execution_receipt.json').write_text(json.dumps({
        'kind': 'actual_original_function_with_synthetic_event_input',
        'function_sha256': FUNCTION_SHA256,
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'event_file': supplied['source']['file'], 'report_file': report_file,
        'threshold_min': 50, 'threshold_max': 110, 'parsed_values': expected,
        'biological_observation_claimed': False}, indent=2) + '\n')
