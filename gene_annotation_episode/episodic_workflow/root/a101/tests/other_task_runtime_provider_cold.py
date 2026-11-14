"""One isolated other39 import order; no constructor or workflow is run.

CLI TREE SELECTION SHA FIRST OUTPUT DEPENDENCY_ROOT...
"""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import traceback

PACKAGE='gene_annotation_episode.episodic_workflow.root.a101'
FIRST=('runtime','published_evidence_assessment.task','execution_job_submission.task','execution_progress_assessment.task')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 assert len(sys.argv)>=6 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and not sys.flags.optimize
 tree=Path(sys.argv[1]).resolve(strict=True);selection_path=Path(sys.argv[2]).resolve(strict=True)
 pin,first=sys.argv[3:5];output=Path(sys.argv[5]).resolve()
 assert first in FIRST and not output.exists() and output.parent.is_dir() and output.is_relative_to(tree.parent)
 raw=selection_path.read_bytes();assert sha(raw)==pin
 selection=json.loads(raw);rows={r['target']:r for r in selection['rows']};assert len(rows)==len(selection['rows'])
 deps=[Path(p).resolve(strict=True) for p in sys.argv[6:]]
 assert all(p.is_dir() and not (p/'gene_annotation_episode').exists() and not (p/'method_loop').exists() for p in deps)
 sys.path[:0]=[str(tree),*map(str,deps)]
 record={'first':first,'source_selection':{'path':str(selection_path),'sha256':pin},'tree':str(tree),'passed':False,'workflow_or_science_executed':False,'constructors_executed':0}
 status=1
 try:
  importlib.import_module(PACKAGE+'.'+first)
  checks=importlib.import_module(PACKAGE+'.tests.other_task_runtime_provider_checks')
  homes={h:r for h,r in checks.bundle()['homes'].items() if r['family']!='scientific'}
  assert len(homes)==39 and sum(r['definition_count'] for r in homes.values())==762
  checked=[]
  for home,info in sorted(homes.items()):
   checks.assert_private_owners(home)
   checked.extend(PACKAGE+'.'+home.replace('/','.')+'.'+module+'::'+r['class']+'.'+name for module,r in info['modules'].items() for name in r['methods'])
  assert len(checked)==len(set(checked))==762
  origins={}
  for name,module in tuple(sys.modules.items()):
   if name not in ('gene_annotation_episode','method_loop') and not name.startswith(('gene_annotation_episode.','method_loop.')):continue
   path=vars(module).get('__file__')
   if path is None:
    assert all(Path(p).resolve().is_relative_to(tree) for p in vars(module)['__path__']);continue
   path=Path(path).resolve(strict=True);assert path.is_relative_to(tree)
   target=str(path.relative_to(tree));assert target in rows
   assert sha(path.read_bytes())==rows[target]['sha256'] and path.stat().st_mode&0o7777==rows[target]['mode']
   origins[name]=str(path)
  record.update(passed=True,checked_definitions=checked,origins=origins);status=0
 except BaseException as error:
  record['failure']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
 with output.open('x') as stream:json.dump(record,stream,indent=2,sort_keys=True);stream.write('\n')
 raise SystemExit(status)
if __name__=='__main__':main()
