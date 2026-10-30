"""Classify unchanged legacy failures and test all actual registered BLAST forms."""
from pathlib import Path
import hashlib,json,sys,types
from copy import deepcopy

BASE=Path(__file__).resolve().parent;PIN=BASE/'coherent_code_001'
from gene_annotation_episode import communication as current
from gene_annotation_episode.runtime import TypedReportContract,_compile_form
from gene_annotation_episode.rna_structure_comparison_views import rna_comparison_fact_sources,PROJECTION_SOURCE
from literature_controlled_response_worker_fixture_095 import module_imports
sys.path.insert(0,str(BASE/'legacy_form_copies_001/tests'))
import test_native_blast_fact_forms as old

baseline=types.ModuleType('_original_communication095');baseline.__package__='gene_annotation_episode'
before=BASE/'communication.py.before'
exec(compile(before.read_bytes(),str(before),'exec'),baseline.__dict__)
form=old.object_form({'requested':rna_comparison_fact_sources()[PROJECTION_SOURCE]['report_schema']})
results={}
for name,module in [('original_before095',baseline),('frozen095',current)]:
    try:module.validate_closed_schema(form)
    except module.ReportBoundaryError as e:results[name]={'diagnostic':e.diagnostic,'message':str(e)}
    else:raise AssertionError('unexpected RNA comparison registration')
assert results['original_before095']==results['frozen095']
forms=[]
for source,node in old.SOURCES.items():
    schema=old.fact_form(source);expected=node['report_schema'];original=deepcopy(schema)
    value={key:False for key in expected['properties']} if expected['type']=='object' else []
    payload={'facts':value}
    assert baseline.validate_closed_schema(schema)==current.validate_closed_schema(schema)==original
    assert _compile_form(json.dumps(schema),old.SOURCES)==original
    assert TypedReportContract('retain_requested_native_facts',schema,old.resolver()).admit(payload,audit_identifiers=()).as_record()==payload
    assert schema==original
    forms.append(source)
imports=module_imports();manifest=json.loads((BASE/'COHERENT_CODE_MANIFEST_001.json').read_text())
assert imports['runtime_implementation_sha256']==manifest['runtime_implementation_sha256']
assert all(Path(r['path']).is_relative_to(PIN) for n,r in imports['modules'].items()
           if n.startswith(('gene_annotation_episode','method_loop')))
assert all(hashlib.sha256((PIN/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items())
(BASE/'LEGACY_BASELINE_IMPORTS_001.json').write_text(json.dumps(imports,indent=2)+'\n')
(BASE/'LEGACY_BASELINE_RESULT_001.json').write_text(json.dumps({'status':'passed',
    'original_compiler_sha256':hashlib.sha256(before.read_bytes()).hexdigest(),
    'rna_comparison_registration_unchanged':results,'current_blast_form_count':len(forms),
    'original_stale_test_expected_count':30,'actual_form_compile_and_admission_passed':forms,
    'pin_files_unchanged':True,'runtime_implementation_sha256':imports['runtime_implementation_sha256']},indent=2)+'\n')
print('Original/current RNA comparison rejection identical; all36 registered BLAST forms compile and admit unchanged.')
