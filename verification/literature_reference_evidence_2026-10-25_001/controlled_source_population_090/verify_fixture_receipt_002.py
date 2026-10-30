"""Execute retained fixture bytes solely through the final imported source pin."""
from pathlib import Path
import base64
import hashlib
from importlib.metadata import version
import json
import sys

OUT = Path(__file__).resolve().parent/'final_002'
PIN = OUT/'pin'
sys.path.insert(0, str(PIN))
from gene_annotation_episode import literature_controlled_response_v3_inputs as source
from gene_annotation_episode import literature_controlled_response_v3_population as population
from gene_annotation_episode import literature_controlled_response_local_calculations as local


def exact(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


cases = json.loads((OUT/'CONSTRUCTED_CASES.json').read_text())
manifest = json.loads((OUT/'PINNED_IMPORTS.json').read_text())
results = []
for case in cases:
    records = {(r['source_ref'],r['representation']): r for r in case['sources']}
    calls = []
    def read_source(reference, representation):
        calls.append((reference,representation))
        row = records[(reference,representation)]
        return {'artifact_ref':row['artifact_ref'],'content':base64.b64decode(row['content_base64'],validate=True)}
    extraction = source.read_controlled_response_v3_inputs(case['selection'], read_source=read_source)
    assert calls == sorted(records)
    assert exact(extraction, case['extraction'])
    assert exact(source.validate_controlled_response_v3_extraction(case['selection'],extraction), extraction)
    sheet = population.populate_controlled_response_v3(extraction)
    assert exact(sheet, case['population'])
    assert exact(population.validate_controlled_response_v3_population(extraction,sheet),sheet)
    assert exact(local.validate_controlled_response_local_sheet(extraction['component_local_inputs'],sheet['local_sheet']),sheet['local_sheet'])
    pair = sheet['local_sheet']['pairs'][0]
    results.append({'name':case['name'],'source_calls':len(calls),'projection_status':sheet['projection_status'],
        'alternatives':len(sheet['alternatives']), 'local_difference':pair['difference'], 'local_variance':pair['variance'],
        'local_standard_uncertainty':pair['standard_uncertainty']})
actual_imports = {}
for name,module in sorted(sys.modules.copy().items()):
    if not name.startswith('gene_annotation_episode') or not getattr(module,'__file__',None): continue
    path = Path(module.__file__).resolve()
    assert path.is_relative_to(PIN), (name,str(path))
    assert name in manifest
    expected = manifest[name]
    assert str(path.relative_to(PIN)) == expected['relative_path']
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == expected['sha256']
    actual_imports[name] = {'path':str(path), 'sha256':digest}
result = {'status':'passed','evidence_scope':'synthetic_fixture_bytes_actual_readers_and_numerical_calculators',
    'cases':results, 'actual_imported_project_modules':actual_imports,
    'external_versions':{'python':sys.version,'Pillow':version('Pillow'),'jsonschema':version('jsonschema')},
    'primary_paper_execution':False,'model_execution':False,'native_episode_execution':False}
(OUT/'EXECUTION_RECEIPT.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
print(json.dumps({'status':'passed','cases':len(results),'actual_imports_from_pin':len(actual_imports),
    'local_difference':results[0]['local_difference']['value'],'local_variance':results[0]['local_variance']['value']}))
