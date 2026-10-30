"""Existing form regressions only, production imports from immutable095 pin."""
from pathlib import Path
import hashlib
import json
import sys
import pytest
from literature_controlled_response_worker_fixture_095 import module_imports

BASE=Path(__file__).resolve().parent
PIN=BASE/'coherent_code_001'
COPY=BASE/'legacy_form_copies_001'
nodes=['tests/test_rna_comparison_report_boundary.py','tests/test_rna_structure_report_boundary.py',
       'tests/test_native_blast_fact_forms.py']
args=['-q','--rootdir='+str(COPY),'-c',str(BASE/'pytest095.ini'),
      '--basetemp='+str(BASE/'legacy_form_tests_001'),
      '-o','cache_dir='+str(BASE/'legacy_form_tests_001/pytest_cache'),
      '--junitxml='+str(BASE/'LEGACY_FORMS_JUNIT_001.xml'),*nodes]
copy_manifest=json.loads((BASE/'LEGACY_FORM_COPIES_001.json').read_text())['files']
pin_manifest=json.loads((BASE/'COHERENT_CODE_MANIFEST_001.json').read_text())
def unchanged():
    assert all(hashlib.sha256((COPY/p).read_bytes()).hexdigest()==h for p,h in copy_manifest.items())
    assert all(hashlib.sha256((PIN/p).read_bytes()).hexdigest()==h for p,h in pin_manifest['files'].items())
unchanged()
(BASE/'LEGACY_FORMS_COMMAND_001.json').write_text(json.dumps({'cwd':str(COPY),
    'python':sys.executable,'pytest_arguments':args,'production_import_root':str(PIN)},indent=2)+'\n')
code=int(pytest.main(args))
imports=module_imports()
assert imports['runtime_implementation_sha256']==pin_manifest['runtime_implementation_sha256']
assert all(Path(r['path']).is_relative_to(PIN) for n,r in imports['modules'].items()
           if n.startswith(('gene_annotation_episode','method_loop')))
(BASE/'LEGACY_FORMS_IMPORTS_001.json').write_text(json.dumps(imports,indent=2)+'\n')
unchanged()
(BASE/'LEGACY_FORMS_RESULT_001.json').write_text(json.dumps({'exit_code':code,
    'pin_and_test_copies_unchanged':True,'actual_repository_imports':len(imports['modules']),
    'runtime_implementation_sha256':imports['runtime_implementation_sha256']},indent=2)+'\n')
raise SystemExit(code)
