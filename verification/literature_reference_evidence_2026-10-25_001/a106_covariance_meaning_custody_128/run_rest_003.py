from pathlib import Path
import hashlib,json,sys
import pytest
BASE=Path(__file__).resolve().parent;PIN=BASE/'pin_003';assert Path.cwd().resolve()==PIN
nodes=json.loads((BASE/'COLLECTED_NODEIDS_002.json').read_text())
failed='tests/test_literature_parent_population_information.py::test_all_child_population_entries_schemas_and_order_equal_prechange_catalog[literature]'
remaining=nodes[nodes.index(failed)+1:]
args=['-q','--junitxml='+str(BASE/'REST_TESTS_003.xml'),*remaining]
(BASE/'REST_COMMAND_003.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'pytest_arguments':args,'selected_remaining_count':len(remaining)},indent=2)+'\n')
result=pytest.main(args)
imports={}
for name,module in tuple(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file or not name.startswith(('gene_annotation_episode','method_loop','test_')):continue
 path=Path(file).resolve()
 if path.suffix!='.py':continue
 assert path.is_relative_to(PIN),(name,str(path));imports[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(BASE/'REST_ACTUAL_IMPORTS_003.json').write_text(json.dumps(imports,indent=2)+'\n')
manifest=json.loads((BASE/'PIN_MANIFEST_003.json').read_text());changed=[n for n,h in manifest['files'].items() if hashlib.sha256((PIN/n).read_bytes()).hexdigest()!=h]
(BASE/'REST_RESULT_003.json').write_text(json.dumps({'pytest_exit':int(result),'snapshot_files_checked':len(manifest['files']),'changed_snapshot_files':changed,'actual_imports_checked':len(imports),'selected_remaining_count':len(remaining)},indent=2)+'\n')
assert not changed,changed
raise SystemExit(int(result))
