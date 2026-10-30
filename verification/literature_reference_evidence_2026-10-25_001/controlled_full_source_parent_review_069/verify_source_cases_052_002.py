"""Root actual full-source cases from the final073 pin; engineering inputs only."""
from copy import deepcopy
from pathlib import Path
from fractions import Fraction
import hashlib
import json
import runpy
import sys

HERE = Path(__file__).resolve().parent
PIN = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PIN))
Fixture = runpy.run_path(str(PIN / 'tests/test_literature_controlled_response_v2_inputs.py'))['Fixture']
from gene_annotation_episode import literature_controlled_response_inputs as shared
from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode import literature_controlled_response_figure_inputs as graph
from gene_annotation_episode import literature_controlled_response_owner_calculations as calculator

results = []
for name, index in [('missing_canceled_readings', 1), ('invalid_unused_covariance', 1),
                    ('unknown_active_owner', 4), ('active_graph_spread', 6)]:
    f = Fixture(index)
    if name != 'active_graph_spread':
        f.text_measurement('protein_condition1', 'Root A response: 13.5 nmol/min.', '13.5')
        f.text_measurement('protein_condition0', 'Root C response: 0.00925 umol/min.', '0.00925', unit='umol/min')
        f.doc['covariance'][2][2] = .36
        f.doc['covariance'][1][1] = .49
        f.doc['covariance'][1][2] = f.doc['covariance'][2][1] = .12
        if name == 'invalid_unused_covariance':
            f.doc['covariance'][0][0] = -1
        f.covariance()
    before = deepcopy(f.args)
    extraction = f.read()
    sheet = calculator.populate_controlled_response_owner(extraction['calculation_inputs'])
    assert f.args == before and f.calls == shared._reference_closure(f.args)
    effect = sheet['cells']['controlled_response_difference']
    variance = sheet['cells']['contrast_variance']
    if name != 'active_graph_spread':
        if name == 'unknown_active_owner':
            # B0 has unknown owner and actual graph4.05[3.95,4.15]nmol/min.
            # It cannot cancel B1=4:13.5-4-9.25+4.05=4.30nmol/min.
            assert effect['value'] == .0043
            assert (effect['lower'],effect['upper']) == (.0042,.0044)
        else:
            assert effect['value'] == .00425
        if name == 'missing_canceled_readings':
            assert variance['value'] == float(Fraction(61, 100000000))
            assert sheet['cells']['condition1_controlled_response']['value'] is None
            assert sheet['cells']['condition0_controlled_response']['value'] is None
        elif name == 'invalid_unused_covariance':
            assert extraction['covariance']['source_validation'] == 'invalid'
            assert variance['value'] is None
        else:
            assert variance['value'] is None
            assert sheet['contrast_dependencies']['covariance_state'] == 'incomplete_active_coverage'
    else:
        arm = extraction['arms']['protein_condition1']
        assert arm['reported_uncertainty']['canonical']['magnitude'] == .0012
        assert arm['calculation_operand']['origin'] == 'synthetic'
        assert arm['graph_details']['operand_projection']['origin'] == 'graph_derived'
        assert arm['calculation_operand']['digitization_interval']
        assert sheet['cells']['source_profile_log_ratio']['value'] is None
        assert 'unresolved_reading_model' in sheet['cells']['source_profile_log_ratio']['unavailable_reason']
    results.append({'case': name, 'arguments': before, 'extraction': extraction,
                    'sheet': sheet, 'actual_source_callbacks': f.calls})

def forbidden(*args, **kwargs):
    raise AssertionError('Detached validation reacquired or reinterpreted scientific inputs')
for module, names in [(shared, ('_Context', '_Sources', '_Inputs', '_native_number', '_native_unit')),
                      (graph, ('read_controlled_response_rate_figure', '_strict_decode', '_count_bar_runs')),
                      (calculator, ('populate_controlled_response_owner',))]:
    for name in names:
        setattr(module, name, forbidden)
for row in results:
    arguments = json.loads(json.dumps(row['arguments'], sort_keys=True))
    extraction = json.loads(json.dumps(row['extraction'], sort_keys=True))
    assert reader.validate_controlled_response_v2_extraction(arguments, extraction) == extraction
imports = {}
for name, module in sorted(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(PIN), (name, str(path))
        imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
out = {'scope': 'Four constructed root full-source cases, no primary/native/model/episode evidence',
       'pin': str(PIN), 'results': results, 'actual_imports': imports,
       'canonical_saved_validation_under_forbidden_entrypoints': len(results)}
with (HERE / 'ACTUAL_SOURCE_ROOT_CASES_052_002.json').open('x') as stream:
    json.dump(out, stream, indent=2); stream.write('\n')
print(json.dumps({'actual_source_cases': len(results), 'canonical_detached_passes': len(results),
    'imports_inside_final_pin': len(imports), 'values': [{
        'case': row['case'], 'effect': row['sheet']['cells']['controlled_response_difference']['value'],
        'variance': row['sheet']['cells']['contrast_variance']['value']} for row in results]}))
