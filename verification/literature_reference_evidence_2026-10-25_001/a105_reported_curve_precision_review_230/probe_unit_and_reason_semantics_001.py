"""Explicit synthetic current-code diagnostic, not final228 acceptance."""
from pathlib import Path
from copy import deepcopy
import hashlib
import io
import json
import sys
import zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_rate_observation_inputs import read_reported_rate_grid
from gene_annotation_episode.literature_rate_observation_calculations import populate_reported_curve_precision

HERE = Path(__file__).resolve().parent
paths = [ROOT / 'gene_annotation_episode' / ('literature_rate_observation_' + name + '.py')
         for name in ('inputs', 'calculations')]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
before = {str(p.relative_to(ROOT)): sha(p) for p in paths}
label = lambda cell, text: dict(cell=cell, expected_text=text)
xlabel = lambda cell, text: dict(kind='xlsx_label', **label(cell, text))

def workbook(nondetection=False):
    cells = dict(A1='Synthetic panel', A2='Synthetic molecule', D1='NADH consumption µmol/min',
                 D2='substrate concentration mM', B3='curve1', C3='curve2',
                 A4=1, A5=2, A6=3, B4='ND' if nondetection else 1, B5=2, B6=3, C4=2, C5=3, C6=4)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('_rels/.rels', '<Relationships><Relationship Id="root" Type="x/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', '<workbook xmlns:r="urn:r"><sheets><sheet name="Sheet1" sheetId="1" r:id="s1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="s1" Type="x/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        rows = []
        for row in range(1, 7):
            parts = []
            for address, value in cells.items():
                if int(address[1:]) != row: continue
                parts.append('<c r="' + address + '">' + ('<v>' + str(value) + '</v>' if type(value) is int
                    else '<is><t>' + escape(value) + '</t></is>') + '</c>')
                if type(value) is str: parts[-1] = parts[-1].replace('<c r=', '<c t="inlineStr" r=')
            rows.append('<row r="' + str(row) + '">' + ''.join(parts) + '</row>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet><sheetData>' + ''.join(rows) + '</sheetData></worksheet>')
    return out.getvalue()

args = dict(version='a105_reported_rate_grid_v1', source_ref='source_' + '1'*24,
    source_kind='synthetic_fixture', worksheet='Sheet1', panel=label('A1', 'Synthetic panel'),
    subject=label('A2', 'Synthetic molecule'), native_rate_label=label('D1', 'NADH consumption µmol/min'),
    curves=[dict(header=label('B3', 'curve1')), dict(header=label('C3', 'curve2'))],
    points=[dict(concentration_cell='A'+str(i), rate_cells=[c+str(i) for c in 'BC']) for i in (4,5,6)],
    rate_unit=dict(code='umol/min', witness=xlabel('D1', 'NADH consumption µmol/min')),
    concentration_unit=dict(code='mM', witness=xlabel('D2', 'substrate concentration mM')),
    endpoint_relationship=dict(status='reported_convention_only', witnesses=[]),
    curve_sampling=dict(status='unknown', assumption='none', source_claim='unknown', witnesses=[]))

def read(raw, selected):
    return read_reported_rate_grid(raw, selected, artifact_ref='artifact_' + hashlib.sha256(raw).hexdigest())

wrong = deepcopy(args); wrong['rate_unit']['code'] = 'nmol/min'
try:
    data = read(workbook(), wrong)
    unit_probe = dict(rejected=False, selected_rate_unit=data['original_arguments']['rate_unit']['code'],
                      original_label=data['meanings']['native_rate_label']['value'])
except Exception as error:
    unit_probe = dict(rejected=True, error_type=type(error).__name__, reason=str(error))
data = read(workbook(True), args)
request = dict(version='a105_reported_curve_precision_request_v1', fit_model='none', requested_components=[
    dict(scope='point', component='mean', concentration_cell='A4'),
    dict(scope='point', component='available_point_mean', concentration_cell='A4')])
sheet = populate_reported_curve_precision(data, request)
after = {str(p.relative_to(ROOT)): sha(p) for p in paths}
result = dict(scope='Explicit synthetic unit-mismatch/nondetection diagnostic of live WIP code; not final acceptance.',
    code_hashes_before=before, code_hashes_after=after, stable_during_probe=before == after,
    unit_mismatch=unit_probe, nondetection_cells=sheet['cells'], source_kind='synthetic_fixture')
with (HERE / 'ROOT_UNIT_AND_REASON_PROBE_001.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(dict(stable_during_probe=result['stable_during_probe'], unit_mismatch=unit_probe,
    nondetection_reason_fields=[{k: r[k] for k in ('status','value','source_missing_reasons','relationship_reasons','implementation_reasons')}
                               for r in sheet['cells']]), indent=2))
