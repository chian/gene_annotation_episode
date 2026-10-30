"""Independent full affected-reader execution on pure248's final pin."""
from copy import deepcopy
import contextlib
from fractions import Fraction
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = HERE.parent / 'a105_summary_precision_components_248'
PLAN = HERE.parent / 'a105_summary_precision_binding_251'
PIN = OWNER / 'pin_006'
manifest = json.loads((OWNER / 'IMPLEMENTATION_MANIFEST_006.json').read_text())
pin = json.loads((OWNER / 'PIN_MANIFEST_006.json').read_text())
hashes = {row['path']: row['sha256'] for row in pin['files']}
for row in manifest['files']:
    assert sha256((OWNER / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
def verify_pin():
    for row in pin['files']:
        assert sha256((OWNER / row['pin_path']).read_bytes()).hexdigest() == row['sha256'], row['path']
verify_pin()
os.chdir(PIN)
sys.path[:0] = [str(PIN), str(PIN/'tests')]
import pytest
from jsonschema import Draft202012Validator
started = time.monotonic()
with (HERE/'ROOT_PURE_PIN_002.log').open('x') as output:
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = pytest.main(['-q', '--tb=short', '-c', '/dev/null', '-p', 'no:cacheprovider',
                            '--junitxml='+str(HERE/'ROOT_PURE_PIN_002.xml'),
                            'tests/test_literature_kinetic_summary_precision_components_248.py',
                            'tests/test_literature_kinetic_inputs.py',
                            'tests/test_literature_kinetic_count_inputs.py',
                            'tests/test_literature_kinetic_calculations.py',
                            'tests/test_literature_rate_native_inputs.py',
                            'tests/test_literature_rate_replicates.py'])
assert int(code) == 0
from test_literature_kinetic_summary_precision_components_248 import actual, synth_extraction
from gene_annotation_episode.literature_kinetic_summary_precision_calculations import populate_kinetic_summary_precision
data = actual()
sheet = populate_kinetic_summary_precision(data['calculation_inputs'])
saved = json.loads((OWNER/'ACTUAL_SHEET_006.json').read_text())
assert sheet == saved
source = sheet['source_cells']; scenario = sheet['scenario_cells']
parameter = Fraction(31,10)*Fraction(60,10**6)
sd = Fraction(1,10)*Fraction(60,10**6)
variance = sd*sd/2
se = math.sqrt(float(variance))
t1 = 1/math.tan(math.pi/40)
assert source['reported_parameter']['value'] == float(parameter)
assert source['reported_sd']['value'] == float(sd)
assert source['independent_preparation_count']['value'] == 2
assert source['statistical_estimator_count']['value'] is None
assert source['mean_standard_error']['value'] is None
assert scenario['mean_variance']['source_exact_value'] == {'numerator':str(variance.numerator),'denominator':str(variance.denominator)}
assert math.isclose(scenario['mean_standard_error']['value'], se, rel_tol=1e-14)
assert math.isclose(scenario['mean_interval_t_multiplier']['value'], t1, rel_tol=1e-12)
for name, sign in [('mean_interval_lower',-1),('mean_interval_upper',1)]:
    assert math.isclose(scenario[name]['value'], float(parameter)+sign*t1*se, rel_tol=1e-12)
partial = populate_kinetic_summary_precision(synth_extraction('missing_central_value')['calculation_inputs'])['source_cells']
assert partial['reported_parameter']['value'] is None
assert [partial[name]['value'] for name in ('reported_sd','mean_variance','mean_standard_error')] == [12,36,6]

# Proposed integration rows: shape conformance only, not selected/authenticated
# episode results. Use the original pure output for every exact named cell.
rows_schema = json.loads((PLAN/'RETURN_ROWS_SCHEMA_001.json').read_text())
validator = Draft202012Validator(rows_schema)
base = json.loads((PLAN/'PROPOSED_SCHEMA_EXAMPLES_001.json').read_text())['proposed_output_rows'][0]
shape_cases = 0
negative_cases = 0
for population, prefix in [('source_cells','source'),('scenario_cells','scenario')]:
    cells = sheet[population]
    for name, cell in cells.items():
        row = deepcopy(base)
        row.update(component=prefix+'_'+name, population=population, cell_name=name, cell=deepcopy(cell))
        validator.validate([row]);shape_cases += 1
        for field, wrong in [('formula_code','invented_formula'),('unit','per_min' if cell['unit'] in ('count','dimensionless') else 'count')]:
            bad=deepcopy(row);bad['cell'][field]=wrong
            assert not validator.is_valid([bad]), (population,name,field)
            negative_cases += 1
        bad=deepcopy(row);bad['population']='scenario_cells' if population=='source_cells' else 'source_cells'
        assert not validator.is_valid([bad]);negative_cases += 1
assert shape_cases == 30 and negative_cases == 90
imports = {}
for module in list(sys.modules.values()):
    filename = getattr(module,'__file__',None)
    if not filename: continue
    path = Path(filename).resolve()
    if path.is_relative_to(PIN) and path.is_file():
        relative = str(path.relative_to(PIN)); digest=sha256(path.read_bytes()).hexdigest()
        assert hashes.get(relative)==digest, relative
        imports[relative]=digest
    elif getattr(module,'__name__',None)!='__main__' and path.is_relative_to(ROOT) and not path.is_relative_to(Path(sys.prefix)) and path.suffix=='.py':
        raise AssertionError('Project import escaped pure pin: '+str(path))
verify_pin()
cases = ET.parse(HERE/'ROOT_PURE_PIN_002.xml').getroot().findall('.//testcase')
assert len(cases)==566 and all(c.find('failure') is None and c.find('error') is None for c in cases)
result={'status':'pass','elapsed_seconds':time.monotonic()-started,
        'owner_manifest_entries_rehashed':len(manifest['files']), 'input_pin_files_rehashed':len(pin['files']),
        'manifest_sha256':sha256((OWNER/'IMPLEMENTATION_MANIFEST_006.json').read_bytes()).hexdigest(),
        'pin_manifest_sha256':sha256((OWNER/'PIN_MANIFEST_006.json').read_bytes()).hexdigest(),
        'tests_passed':566,'actual_source_sheet_matches_original_saved_pure_output':True,
        'independent_oracle':{'parameter':float(parameter),'sd':float(sd),'estimated_variance':float(variance),'conditional_SE':se,'df1_t95':t1},
        'valid_integration_row_shapes':shape_cases,'invalid_formula_unit_population_shapes_rejected':negative_cases,
        'shape_validation_is_not_authenticated_selected_output':True,
        'actual_local_imports':imports,'selected_integration_tested':False,'actual_model_execution':False,
        'private_provider_data_read':False,'A105_complete':False,'goal_changed':False}
with (HERE/'ROOT_PURE_PIN_REVIEW_002.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
print(json.dumps({key:value for key,value in result.items() if key!='actual_local_imports'},indent=2))
