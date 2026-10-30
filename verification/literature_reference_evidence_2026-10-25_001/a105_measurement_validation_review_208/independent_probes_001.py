"""Synthetic population oracle and metamorphic checks, independent of formulas."""
from pathlib import Path
from fractions import Fraction
from copy import deepcopy
import hashlib
import json
import os
import sys

BASE = Path(__file__).resolve().parent
PIN = BASE / 'pin_001'
ROOT = Path('/home/chia/repos/gene_annotation_episode')
sys.dont_write_bytecode = True
sys.path = [str(PIN), str(PIN / 'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT / 'tests')]]
from test_literature_measurement_validation_205 import Source, run, exact
from gene_annotation_episode.literature_measurement_validation_calculations import populate_measurement_validation

checks = []
for nominal, measured, cv in [('10','12','25'), ('25','20','0'), ('.5','.4','12.5'),
                             ('8','8','50'), ('4','5','100'), ('40','1','2.5')]:
    source = Source(nominal=nominal, measured=measured, within=cv)
    data, sheet = run(source, source.args(supported=True), source.recovery_rows())
    n, m, c = Fraction(nominal), Fraction(measured), Fraction(cv)/100
    # A two-point synthetic population whose mean is m and population CV is c.
    # Directly average squared errors of the observations; do not call the
    # implementation's recovery/bias/loss formulas to construct the oracle.
    observations = (m*(1-c), m*(1+c))
    direct = sum(((x-n)/n)**2 for x in observations)/2
    cells = sheet['precision'][0]['cells']
    assert exact(cells['relative_squared_deviation_plugin']) == direct
    assert cells['relative_squared_deviation_plugin']['conditional_value'] is None
    assert cells['relative_squared_deviation_plugin']['contribution_key'] == cells['relative_rms_percent']['contribution_key']
    assert cells['relative_squared_deviation_plugin']['input_measurement_keys'] == cells['relative_rms_percent']['input_measurement_keys']
    previous, calls = deepcopy(data), list(source.calls)
    assert populate_measurement_validation(data) == sheet
    assert data == previous and source.calls == calls
    # Change only supported population interpretation: arithmetic must remain
    # explicit but interpreted measurement-error estimates must disappear.
    unknown_args = source.args(supported=True)
    unknown_args['precision'][0]['cv_denominator'] = source.interpretation('unknown')
    _, conditional = run(source, unknown_args, source.recovery_rows())
    loss = conditional['precision'][0]['cells']['relative_squared_deviation_plugin']
    assert loss['value'] is None and exact(loss, 'conditional_exact_value') == direct
    assert loss['status'] == 'conditional' and 'cv_denominator_unknown' in loss['unavailable_reasons']
    # Uniform amount-unit rescaling must leave normalized error unchanged.
    scaled = Source(nominal=str(n*100), measured=str(m*100), within=cv)
    _, scaled_sheet = run(scaled, scaled.args(supported=True), scaled.recovery_rows())
    assert exact(scaled_sheet['precision'][0]['cells']['relative_squared_deviation_plugin']) == direct
    checks.append({'synthetic_nominal':nominal, 'synthetic_mean':measured, 'synthetic_CV_percent':cv,
        'direct_population_mean_squared_relative_deviation':str(direct),
        'population_oracle':True, 'conditional_interpretation_separated':True,
        'amount_scale_invariance':True, 'repeat_has_no_IO_or_mutation':True})

for value in ('-3', '-.25', '0', '.5', '1'):
    source = Source(zprime=value)
    _, sheet = run(source)
    z = sheet['zprime'][0]['cells']
    band = exact(z['control_band_ratio'])
    # Reconstruct source Z from the returned nonnegative band width, rather
    # than comparing two calls to the implementation's forward expression.
    assert band >= 0 and 1-3*band == Fraction(value)
    assert z['reported_zprime']['contribution_key'] == z['control_band_ratio']['contribution_key']
    checks.append({'synthetic_Zprime':value, 'nonnegative_control_band_roundtrip':True,
                   'same_contribution_preserved':True})

manifest = json.loads((BASE/'PIN_001.json').read_text())
changed = [p for p,h in manifest['hashes'].items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest() != h]
assert not changed
imports = {name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
           if getattr(module,'__file__',None) and name.startswith(('gene_annotation_episode','method_loop','test_'))}
outside = {name:path for name,path in imports.items() if not Path(path).is_relative_to(PIN)}
assert not outside
result = {'scope':'Synthetic mathematical verification only; no new paper, acquired measurements or scientific independence claim.',
    'checks':checks, 'all_pass':True, 'imports':imports, 'imports_outside_pin':outside,
    'changed_pinned_files':changed}
(BASE/'ROOT_INDEPENDENT_PROBES_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'synthetic_population_cases':6,'Zprime_roundtrips':5,'all_pass':True,
    'imports_outside_pin':outside,'changed_pinned_files':changed}))
