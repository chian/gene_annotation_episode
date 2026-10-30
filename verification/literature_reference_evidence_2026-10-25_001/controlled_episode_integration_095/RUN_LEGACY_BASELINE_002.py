"""Exact47 failed legacy form cases with only pre095 communication restored."""
from pathlib import Path
import hashlib,json,sys
import pytest
from literature_controlled_response_worker_fixture_095 import module_imports
BASE=Path(__file__).resolve().parent;CLONE=BASE/'baseline_code_002';COPY=BASE/'legacy_form_copies_001'
manifest=json.loads((BASE/'BASELINE_CLONE_MANIFEST_002.json').read_text())
args=['-q','--rootdir='+str(COPY),'-c',str(BASE/'pytest095.ini'),
      '--basetemp='+str(BASE/'legacy_baseline_tests_002'),
      '-o','cache_dir='+str(BASE/'legacy_baseline_tests_002/pytest_cache'),
      '--junitxml='+str(BASE/'LEGACY_BASELINE_JUNIT_002.xml'),*manifest['exact_failed_node_ids']]
(BASE/'LEGACY_BASELINE_COMMAND_002.json').write_text(json.dumps({'cwd':str(COPY),'python':sys.executable,
    'pytest_arguments':args,'production_import_root':str(CLONE)},indent=2)+'\n')
assert all(hashlib.sha256((CLONE/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items())
code=int(pytest.main(args));imports=module_imports()
assert all(Path(r['path']).is_relative_to(CLONE) for n,r in imports['modules'].items()
           if n.startswith(('gene_annotation_episode','method_loop')))
assert all(hashlib.sha256((CLONE/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items())
(BASE/'LEGACY_BASELINE_IMPORTS_002.json').write_text(json.dumps(imports,indent=2)+'\n')
(BASE/'LEGACY_BASELINE_RESULT_002.json').write_text(json.dumps({'exit_code':code,'clone_files_unchanged':True,
    'actual_repository_imports':len(imports['modules']),
    'runtime_implementation_sha256':imports['runtime_implementation_sha256']},indent=2)+'\n')
raise SystemExit(code)
