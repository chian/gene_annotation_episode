from pathlib import Path
import shutil,json,hashlib
root=Path('/home/chia/repos/gene_annotation_episode'); base=Path(__file__).parent
candidate=base/'candidate_001'; candidate.mkdir(exist_ok=False)
for name in ('gene_annotation_episode','method_loop','tests'):
 shutil.copytree(root/name,candidate/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'))
for p in (base/'draft/gene_annotation_episode').glob('*.py'):
 shutil.copy2(p,candidate/'gene_annotation_episode'/p.name)
manifest={str(p.relative_to(candidate)):hashlib.sha256(p.read_bytes()).hexdigest()
 for directory in ('gene_annotation_episode','method_loop') for p in sorted((candidate/directory).rglob('*')) if p.is_file()}
(base/'CANDIDATE_RUNTIME_HASHES_001.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'candidate':str(candidate),'runtime_files':len(manifest)}))
