"""Identical-source continuation after exact auxiliary fixture restoration."""
from pathlib import Path
import hashlib,json,sys
import pytest
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_003'
assert Path.cwd().resolve()==PIN
selection=json.loads((BASE/'COLLECTION_SELECTION_002.json').read_text())
class Collection:
 def pytest_collection_finish(self,session):
  (BASE/'COLLECTED_NODEIDS_002.json').write_text(json.dumps([item.nodeid for item in session.items],indent=2)+'\n')
collect_args=['-q','--collect-only',*['--deselect='+x for x in selection['deselect']],*selection['selection']]
with (BASE/'COLLECTION_STDOUT_002.txt').open('w') as out:
 original=sys.stdout; sys.stdout=out
 try: collected=pytest.main(collect_args,plugins=[Collection()])
 finally: sys.stdout=original
assert int(collected)==0,collected
nodes=json.loads((BASE/'COLLECTED_NODEIDS_002.json').read_text())
failed='tests/test_form_reference_validation.py::test_public_genome_resolvers_reuse_facts_but_preserve_possession_and_semantics'
tail=nodes[nodes.index(failed):]
args=['-q','-x','--junitxml='+str(BASE/'TAIL_TESTS_002.xml'),*tail]
(BASE/'TAIL_COMMAND_002.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'pytest_arguments':args,'selected_tail_count':len(tail)},indent=2)+'\n')
result=pytest.main(args)
imports={}
for name,module in tuple(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if not file or not name.startswith(('gene_annotation_episode','method_loop','test_')):continue
 path=Path(file).resolve()
 if path.suffix!='.py':continue
 assert path.is_relative_to(PIN),(name,str(path))
 imports[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(BASE/'TAIL_ACTUAL_IMPORTS_002.json').write_text(json.dumps(imports,indent=2)+'\n')
manifest=json.loads((BASE/'PIN_MANIFEST_003.json').read_text())
changed=[n for n,h in manifest['files'].items() if hashlib.sha256((PIN/n).read_bytes()).hexdigest()!=h]
(BASE/'TAIL_RESULT_002.json').write_text(json.dumps({'pytest_exit':int(result),'snapshot_files_checked':len(manifest['files']),'changed_snapshot_files':changed,'actual_imports_checked':len(imports),'collected_total':len(nodes),'selected_tail_count':len(tail)},indent=2)+'\n')
assert not changed,changed
raise SystemExit(int(result))
