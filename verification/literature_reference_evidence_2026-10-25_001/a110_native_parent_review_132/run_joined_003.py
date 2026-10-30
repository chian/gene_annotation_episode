"""Root independent joined-current-native-reader verification; no model calls."""
from pathlib import Path
import hashlib,json,sys
import pytest
import gene_annotation_episode.literature_episodes as binding
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_003'
assert Path.cwd().resolve()==PIN and Path(binding.__file__).resolve().is_relative_to(PIN)
selection=['tests/test_literature_reaction_graph_origin_129.py']
args=['-q','-x','--junitxml='+str(BASE/'TESTS_003.xml'),*selection]
(BASE/'COMMAND_003.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'args':args,'limits':'ConstructedscientificchoiceswithonepreviouslyreviewedretainedCsiDprimarycase; no configured-model or newsourceacquisition.'},indent=2)+'\n')
from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import obj
legacy=json.loads((BASE/'CURRENT_FACT_CONTRACTS_001.json').read_text())['literature_reaction_native_observations']['report_schema']
validate_closed_schema(obj({'legacy_native_rows':legacy}))
result=pytest.main(args)
imports={}
for name,module in tuple(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file or not name.startswith(('gene_annotation_episode','method_loop','test_literature','test_joined_native')):continue
 p=Path(file).resolve()
 if p.suffix!='.py':continue
 assert p.is_relative_to(PIN),(name,str(p));imports[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(BASE/'IMPORTS_003.json').write_text(json.dumps(imports,indent=2)+'\n')
manifest=json.loads((BASE/'PIN_MANIFEST_003.json').read_text())['files']
changed=[name for name,digest in manifest.items() if hashlib.sha256((PIN/name).read_bytes()).hexdigest()!=digest]
(BASE/'RESULT_003.json').write_text(json.dumps({'exit_code':int(result),'checked_snapshot_files':len(manifest),'changed_files':changed,'checked_imports':len(imports),'limits':'Originalclosedtypedforms, actualsubsetreceipts, source-freequery-onlyreconstruction andscriptedproviderdecisions; no newlive-modelscientificclaim.'},indent=2)+'\n');assert not changed,changed
raise SystemExit(int(result))
