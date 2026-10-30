"""Root-owned synthetic invariance/oracle checks on the frozen pure component."""
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
sys.path = [str(PIN), str(PIN/'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT/'tests')]]
os.chdir(PIN)
from test_literature_product_coupling_212 import Source, run, exact

results = {}
# Independent error-mode construction: columns (2,1), (1,-3) yield this C.
# Differentiate P/H along each mode, avoiding the production matrix expression.
s = Source(product='3', cofactor='7')
a = s.args()
s.covariance(a, ((5,-1),(-1,10)))
data, sheet = run(s,a)
step = Fraction(1,10**12)
oracle = Fraction(0)
for dp,dh in ((2,1),(1,-3)):
    derivative = ((3+step*dp)/(7+step*dh)-(3-step*dp)/(7-step*dh))/(2*step)
    oracle += derivative**2
observed = exact(sheet['cells']['product_per_cofactor_variance'])
assert observed == Fraction(377,2401)
assert abs(observed-oracle) < Fraction(1,10**22)
results['signed_covariance_independent_error_mode_oracle'] = True
# Changing the common rate scale changes C quadratically, preserving fraction variance.
scaled = Source(product='30',cofactor='70')
sa = scaled.args()
scaled.covariance(sa, ((500,-100),(-100,1000)))
_, second = run(scaled,sa)
assert exact(second['cells']['product_per_cofactor']) == Fraction(3,7)
assert exact(second['cells']['product_per_cofactor_variance']) == observed
results['common_scale_and_covariance_scale_invariance'] = True
# A productive fraction concerns the selected system's chemistry. It does not
# itself assert attribution to the studied molecule or supply an attribution score.
assert data['relationships']['molecular_attribution']['value'] == 'unknown'
assert sheet['cells']['productive_fraction']['value'] is not None
assert 'product_identity_does_not_quantify_molecule_specific_attribution' in sheet['qualifications']
results['physical_coupling_keeps_molecular_attribution_unknown'] = True
# Unknown stoichiometry must preserve the descriptive ratio without a default.
unknown = deepcopy(a)
unknown['nu_cofactor_per_product'].update(status='unknown',exact_value=None,witnesses=[])
_, partial = run(s,unknown)
assert exact(partial['cells']['product_per_cofactor']) == Fraction(3,7)
assert partial['cells']['productive_fraction']['value'] is None
assert partial['cells']['productive_fraction']['conditional_value'] is None
results['unknown_stoichiometry_retains_only_supported_partial'] = True
# Exact byte aliases cannot manufacture model contributions by duplication/order.
alias = deepcopy(a)
w = alias['nu_cofactor_per_product']['witnesses'][0]
alias['nu_cofactor_per_product']['witnesses'] = [dict(w,representation='text'),w]
def read_alias(ref,representation):
    return s.read(ref,'original')
from gene_annotation_episode.literature_product_coupling_inputs import read_product_coupling_inputs
aliased = read_product_coupling_inputs(alias, read_source=read_alias)
assert aliased['nu_cofactor_per_product']['model_key'] == data['nu_cofactor_per_product']['model_key']
results['same_artifact_representation_aliases_preserve_model_identity'] = True
# Native observations and dependent reconstruction retain the original owner.
assert sheet['cells']['reported_product_activity']['contribution_key'] == sheet['cells']['reconstructed_product_activity']['contribution_key']
assert sheet['cells']['productive_fraction_variance']['contribution_key'] == sheet['cells']['productive_fraction_standard_uncertainty']['contribution_key']
results['dependent_views_retain_shared_contributions'] = True
hashes = json.loads((BASE/'PIN_001.json').read_text())['hashes']
changed = [p for p,h in hashes.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
imports = {n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside = {n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
assert not changed and not outside
result = {'scope':'Independent explicitly synthetic pure-component checks; no integration/model/adequacy claim.',
    'properties':results,'oracle_variance_exact':{'numerator':str(observed.numerator),'denominator':str(observed.denominator)},
    'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed}
(BASE/'ROOT_INDEPENDENT_PROBES_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='imports'},indent=2))
