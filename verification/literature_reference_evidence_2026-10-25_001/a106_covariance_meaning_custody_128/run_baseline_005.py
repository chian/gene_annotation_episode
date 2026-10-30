from pathlib import Path
import hashlib,json,sys
import pytest
BASE=Path(__file__).resolve().parent;PIN=BASE/'baseline_pre128_005';assert Path.cwd().resolve()==PIN
args=['-q','-x','--junitxml='+str(BASE/'BASELINE_TESTS_005.xml'),'tests/test_literature_parent_population_information.py::test_all_child_population_entries_schemas_and_order_equal_prechange_catalog[literature]']
(BASE/'BASELINE_COMMAND_005.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'pytest_arguments':args},indent=2)+'\n')
result=pytest.main(args)
imports={}
for name,module in tuple(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file or not name.startswith(('gene_annotation_episode','method_loop','test_')):continue
 path=Path(file).resolve()
 if path.suffix!='.py':continue
 assert path.is_relative_to(PIN),(name,str(path));imports[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(BASE/'BASELINE_ACTUAL_IMPORTS_005.json').write_text(json.dumps(imports,indent=2)+'\n')
m=json.loads((BASE/'BASELINE_MANIFEST_005.json').read_text());changed=[n for n,h in m['files'].items() if hashlib.sha256((PIN/n).read_bytes()).hexdigest()!=h]
(BASE/'BASELINE_RESULT_005.json').write_text(json.dumps({'pytest_exit':int(result),'snapshot_files_checked':len(m['files']),'changed_snapshot_files':changed,'actual_imports_checked':len(imports)},indent=2)+'\n');assert not changed
raise SystemExit(int(result))
