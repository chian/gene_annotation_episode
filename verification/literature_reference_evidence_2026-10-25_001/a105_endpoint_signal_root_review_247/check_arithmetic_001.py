"""Independent exact arithmetic; source238 conversion was already reviewed240."""
from fractions import Fraction as Q
from itertools import product
from pathlib import Path
import json
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_components_241/implementation_004'
sys.path.insert(0, str(PIN))
helpers = runpy.run_path(str(PIN / 'tests/test_literature_endpoint_signal_components_241.py'))

def exact(cell, field):
    x = cell[field]
    return Q(int(x['numerator']), int(x['denominator'])) if x else None

args, blobs = helpers['_paper']()
sheet = helpers['populate_endpoint_signal'](helpers['_read'](args, blobs))
cells = {c['component']: c for c in sheet['cells']}
a, b, t = map(Q, (39, 170, 181))
D, C, G, F, H = t-a, b-a, t-b, (a-b)/(a-t), (b-t)/(a-t)
assert D == C+G and C == F*D and F+H == 1
for name, wanted in zip(('total_amplitude', 'corrected_amplitude', 'additional_amplitude', 'retained_fraction', 'additional_fraction'), (D,C,G,F,H)):
    field = 'exact_value' if name == 'total_amplitude' else 'conditional_exact_value'
    assert exact(cells[name], field) == wanted, name
corners = [(Q(aa-bb, aa-tt), Q(bb-tt, aa-tt))
    for aa,bb,tt in product((38,40), (168,172), (180,183))]
assert (min(x[0] for x in corners), max(x[0] for x in corners)) == (Q(128,143), Q(67,71))
assert exact(cells['retained_fraction'], 'exact_lower') == min(x[0] for x in corners)
assert exact(cells['retained_fraction'], 'exact_upper') == max(x[0] for x in corners)
assert all(cells[n]['value'] is None and cells[n]['conditional_value'] is None for n in helpers['COMPONENTS'][5:])
# Entirely synthetic covariance, not an experimental estimate or inferred data.
a,b,t = map(Q, (10,4,2))
sigma = [[Q(x) for x in row] for row in ((4,1,0),(1,9,2),(0,2,16))]
j = ((b-t)/(a-t)**2, -1/(a-t), (a-b)/(a-t)**2)
variance = sum(j[i]*sigma[i][k]*j[k] for i in range(3) for k in range(3))
assert variance == Q(59,256)
jd,jc = (1,0,-1), (1,-1,0)
cov_cd = sum(jc[i]*sigma[i][k]*jd[k] for i in range(3) for k in range(3))
assert cov_cd == 5
false_independence = Q(11,64) + Q(36*20,4096)
assert false_independence == Q(89,256) and false_independence != variance
receipt = {'status':'passed', 'source_case':'already converted238/root240',
    'source_endpoint_values': {'D':str(D),'C':str(C),'G':str(G),'F':str(F),'H':str(H)},
    'ratio_reading_enclosure':[str(min(x[0] for x in corners)),str(max(x[0] for x in corners))],
    'physical_variance_source_case':'unreported; all variance cells null',
    'synthetic_shared_covariance':{'var_F':str(variance),'cov_C_D':str(cov_cd),
        'incorrect_independence_result':str(false_independence)},
    'scope':'pure arithmetic; no selected execution, model run, source reacquisition or credit'}
(HERE/'ROOT_ARITHMETIC_001.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
