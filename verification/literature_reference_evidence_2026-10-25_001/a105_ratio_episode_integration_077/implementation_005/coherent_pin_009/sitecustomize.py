import atexit,hashlib,json,os,sys
from pathlib import Path
pin=Path(__file__).resolve().parent
def record():
 rows=[];bad=[]
 for name,module in tuple(sys.modules.items()):
  if not (name.startswith(('gene_annotation_episode','method_loop')) or name.startswith('test_literature_ratio_source') or name=='literature_ratio_source_worker_fixture_077'):continue
  source=getattr(module,'__file__',None)
  if not source:continue
  path=Path(source).resolve()
  if not path.is_relative_to(pin):bad.append(str(path))
  rows.append({'module':name,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 target=Path(os.environ['SOURCE077_IMPORT_AUDIT']);target.mkdir(parents=True,exist_ok=True)
 (target/(str(os.getpid())+'.json')).write_text(json.dumps({'pid':os.getpid(),'argv':sys.argv,'pin':str(pin),'outside_pin':bad,'imports':rows},indent=2))
atexit.register(record)
