"""Synthetic two-point analytic oracle, independent of the profile solver."""
from pathlib import Path
from fractions import Fraction
import hashlib
import io
import json
import math
import sys
import zipfile
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
PIN = HERE / 'pin_001'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PIN))
from gene_annotation_episode.literature_rate_observation_inputs import read_reported_rate_grid
from gene_annotation_episode.literature_rate_observation_calculations import populate_reported_curve_precision

label = lambda cell, text: dict(cell=cell, expected_text=text)
xlabel = lambda cell, text: dict(kind='xlsx_label', **label(cell, text))
cells = dict(A1='Synthetic analytic panel', A2='Synthetic molecule', D1='reporter µmol/min',
    D2='substrate concentration mM', D3='Stipulated IID reporting curves; no physical replication claim',
    B3='curve A', C3='curve B', A4=1, A5=3, B4=4, B5=6, C4=6, C5=9)
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w') as z:
    z.writestr('_rels/.rels', '<Relationships><Relationship Id="root" Type="x/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    z.writestr('xl/workbook.xml', '<workbook xmlns:r="urn:r"><sheets><sheet name="Sheet1" sheetId="1" r:id="s1"/></sheets></workbook>')
    z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="s1" Type="x/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
    rows = []
    for row in range(1, 6):
        entries = []
        for address, value in cells.items():
            if int(address[1:]) != row: continue
            entries.append('<c r="' + address + '"><v>' + str(value) + '</v></c>' if type(value) is int
                else '<c r="' + address + '" t="inlineStr"><is><t>' + escape(value) + '</t></is></c>')
        rows.append('<row r="' + str(row) + '">' + ''.join(entries) + '</row>')
    z.writestr('xl/worksheets/sheet1.xml', '<worksheet><sheetData>' + ''.join(rows) + '</sheetData></worksheet>')
raw = buffer.getvalue()
args = dict(version='a105_reported_rate_grid_v1', source_ref='source_'+'1'*24,
    source_kind='synthetic_fixture', worksheet='Sheet1', panel=label('A1', cells['A1']),
    subject=label('A2', cells['A2']), native_rate_label=label('D1', cells['D1']),
    curves=[dict(header=label(c+'3', cells[c+'3'])) for c in 'BC'],
    points=[dict(concentration_cell='A'+str(i), rate_cells=[c+str(i) for c in 'BC']) for i in (4,5)],
    rate_unit=dict(code='umol/min', witness=xlabel('D1', cells['D1'])),
    concentration_unit=dict(code='mM', witness=xlabel('D2', cells['D2'])),
    endpoint_relationship=dict(status='reported_convention_only', witnesses=[]),
    curve_sampling=dict(status='stipulated_sensitivity', assumption='iid_reported_curve_vectors',
        source_claim='not_established', witnesses=[xlabel('D3', cells['D3'])]))
data = read_reported_rate_grid(raw, args, artifact_ref='artifact_'+hashlib.sha256(raw).hexdigest())
selectors = [dict(scope='curve', curve_header_cell=c+'3', component=p) for c in 'BC' for p in ('Vmax','Km')]
for kind in ('mean_of_reported_curve_fits','fit_of_point_means'):
    selectors.extend(dict(scope='estimator', estimator=kind, component=p)
                     for p in ('Vmax','Km','log_efficiency_variance'))
selectors.append(dict(scope='reported_curve_covariance', left_concentration_cell='A4',
                     right_concentration_cell='A5', component='sample_covariance'))
sheet = populate_reported_curve_precision(data, dict(version='a105_reported_curve_precision_request_v1',
    fit_model='unweighted_positive_km_mm', requested_components=selectors))
observed = [r['conditional_value'] if r['status']=='conditional_scenario' else r['value'] for r in sheet['cells']]
# For two distinct positive points: K=(y2-y1)/(y1/x1-y2/x2), V=y1*(K+x1)/x1.
oracle = []
for y1,y2 in [(Fraction(4),Fraction(6)),(Fraction(6),Fraction(9))]:
    k=(y2-y1)/(y1/Fraction(1)-y2/Fraction(3)); v=y1*(k+1)
    oracle.extend([v,k])
# V=[8,12], K=[1,1]; C(Vbar)=sample_variance(V)/2=4; gV=1/10.
oracle.extend([Fraction(10),Fraction(1),Fraction(1,25)]*2)
# Two observed vectors [4,6],[6,9] have exact cross-coordinate sample covariance3.
oracle.append(Fraction(3))
assert len(observed)==len(oracle)
assert all(a is not None and math.isclose(a,float(b),rel_tol=1e-9,abs_tol=1e-12) for a,b in zip(observed,oracle))
assert sheet['cells'][6]['value'] is None and sheet['cells'][9]['value'] is None
assert sheet['calculation_metadata']['physical_preparation_count'] is None
assert sheet['calculation_metadata']['published_estimate_covariance'] is None
assert all(r['input_origins']==['synthetic'] for r in sheet['cells'])
result = dict(passed=True, source_kind='synthetic_fixture', observed=observed,
    independent_exact_oracles=[dict(numerator=str(q.numerator),denominator=str(q.denominator)) for q in oracle],
    conditional_covariance_scope='Stipulated IID reporting curves at fixed reported concentrations; no physical replication or total uncertainty.',
    scientific_claim='Synthetic arithmetic/provenance verification only; not experimental evidence or A105 adequacy.')
with (HERE / 'ROOT_ANALYTIC_CURVE_PROBE_001.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(result, indent=2))
