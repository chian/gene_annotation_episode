"""One corrected counterfactual fixture against original immutable095 runtime."""
from pathlib import Path
import hashlib,json,sys
import pytest
from literature_controlled_response_worker_fixture_095 import module_imports

BASE=Path(__file__).resolve().parent;PIN=BASE/'coherent_code_001';COPY=BASE/'revised_tests_002'
node='test_controlled_response_consumer_095_revised.py::test_actual_runtime_digest_and_complete_alternate_wrapper_cannot_replace_selected_output'
args=['-q','--rootdir='+str(COPY),'-c',str(BASE/'pytest095.ini'),
      '--basetemp='+str(BASE/'runtime_tamper_tests_002'),
      '-o','cache_dir='+str(BASE/'runtime_tamper_tests_002/pytest_cache'),
      '--junitxml='+str(BASE/'RUNTIME_TAMPER_JUNIT_002.xml'),node]
manifest=json.loads((BASE/'COHERENT_CODE_MANIFEST_001.json').read_text())
copy=json.loads((BASE/'REVISED_TEST_COPY_002.json').read_text())
def unchanged():
    assert all(hashlib.sha256((PIN/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items())
    assert hashlib.sha256(Path(copy['path']).read_bytes()).hexdigest()==copy['sha256']
unchanged()
(BASE/'RUNTIME_TAMPER_COMMAND_002.json').write_text(json.dumps({'cwd':str(COPY),'python':sys.executable,
    'pytest_arguments':args,'production_import_root':str(PIN)},indent=2)+'\n')
code=int(pytest.main(args));imports=module_imports()
assert imports['runtime_implementation_sha256']==manifest['runtime_implementation_sha256']
assert all(Path(r['path']).is_relative_to(PIN) for n,r in imports['modules'].items()
           if n.startswith(('gene_annotation_episode','method_loop')))
(BASE/'RUNTIME_TAMPER_IMPORTS_002.json').write_text(json.dumps(imports,indent=2)+'\n')
unchanged()
(BASE/'RUNTIME_TAMPER_RESULT_002.json').write_text(json.dumps({'exit_code':code,'pin_and_test_copy_unchanged':True,
    'runtime_implementation_sha256':imports['runtime_implementation_sha256'],
    'actual_repository_imports':len(imports['modules'])},indent=2)+'\n')
raise SystemExit(code)
