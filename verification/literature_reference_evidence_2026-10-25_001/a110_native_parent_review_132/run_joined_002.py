"""Root independent joined-current-native-reader verification; no model calls."""
from pathlib import Path
import hashlib,json,sys
import pytest
import gene_annotation_episode.literature_episodes as binding
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_002'
assert Path.cwd().resolve()==PIN and Path(binding.__file__).resolve().is_relative_to(PIN)
selection=['tests/test_literature_reaction_native_primary_129.py', 'tests/test_literature_reaction_native_contract_information_129.py', 'tests/test_literature_context_native_integration.py', 'tests/test_literature_reaction_meanings_integration.py', 'tests/test_literature_perturbation_covariance_meanings.py::test_ordinary_child_parent_and_first_read_only_reconstruction_keep_actual_covariance_meaning', 'tests/test_literature_parent_population_information.py::test_all_child_population_entries_schemas_and_order_equal_prechange_catalog[literature]']
args=['-q','-x','--junitxml='+str(BASE/'TESTS_002.xml'),*selection]
(BASE/'COMMAND_002.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'args':args,'limits':'ConstructedscientificchoiceswithonepreviouslyreviewedretainedCsiDprimarycase; no configured-model or newsourceacquisition.'},indent=2)+'\n')
result=pytest.main(args)
imports={}
for name,module in tuple(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file or not name.startswith(('gene_annotation_episode','method_loop','test_literature','test_joined_native')):continue
 p=Path(file).resolve()
 if p.suffix!='.py':continue
 assert p.is_relative_to(PIN),(name,str(p));imports[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(BASE/'IMPORTS_002.json').write_text(json.dumps(imports,indent=2)+'\n')
manifest=json.loads((BASE/'PIN_MANIFEST_002.json').read_text())['files']
changed=[name for name,digest in manifest.items() if hashlib.sha256((PIN/name).read_bytes()).hexdigest()!=digest]
(BASE/'RESULT_002.json').write_text(json.dumps({'exit_code':int(result),'checked_snapshot_files':len(manifest),'changed_files':changed,'checked_imports':len(imports),'limits':'Originalclosedtypedforms, actualsubsetreceipts, source-freequery-onlyreconstruction andscriptedproviderdecisions; no newlive-modelscientificclaim.'},indent=2)+'\n');assert not changed,changed
raise SystemExit(int(result))
