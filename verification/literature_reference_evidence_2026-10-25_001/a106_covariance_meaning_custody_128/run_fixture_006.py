from pathlib import Path
import hashlib,json,sys
import pytest
BASE=Path(__file__).resolve().parent;PIN=BASE/'pin_006';assert Path.cwd().resolve()==PIN
nodes=json.loads((BASE/'COLLECTED_NODEIDS_002.json').read_text())
failed='tests/test_literature_parent_population_information.py::test_all_child_population_entries_schemas_and_order_equal_prechange_catalog[literature]'
remaining=['tests/test_literature_controlled_response_communication.py::test_actual_registered_sheet_reference_and_native_number_validation','tests/test_literature_controlled_response_communication.py::test_actual_joint_scope_witness_reference_behind_native_definition']
args=['-q','--junitxml='+str(BASE/'FIXTURE_TESTS_006.xml'),*remaining]
(BASE/'FIXTURE_COMMAND_006.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'pytest_arguments':args,'selected_remaining_count':len(remaining)},indent=2)+'\n')
result=pytest.main(args)
imports={}
for name,module in tuple(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file or not name.startswith(('gene_annotation_episode','method_loop','test_')):continue
 path=Path(file).resolve()
 if path.suffix!='.py':continue
 assert path.is_relative_to(PIN),(name,str(path));imports[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(BASE/'FIXTURE_ACTUAL_IMPORTS_006.json').write_text(json.dumps(imports,indent=2)+'\n')
manifest=json.loads((BASE/'PIN_MANIFEST_006.json').read_text());changed=[n for n,h in manifest['files'].items() if hashlib.sha256((PIN/n).read_bytes()).hexdigest()!=h]
(BASE/'FIXTURE_RESULT_006.json').write_text(json.dumps({'pytest_exit':int(result),'snapshot_files_checked':len(manifest['files']),'changed_snapshot_files':changed,'actual_imports_checked':len(imports),'selected_remaining_count':len(remaining)},indent=2)+'\n')
assert not changed,changed
raise SystemExit(int(result))
