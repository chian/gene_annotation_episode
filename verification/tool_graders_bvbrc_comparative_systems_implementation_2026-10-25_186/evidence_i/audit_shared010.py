from pathlib import Path
import difflib,hashlib,json
root=Path('/home/chia/repos/gene_annotation_episode')
composition=json.loads(Path('../PROTEOME_COMPOSITION_RECEIPT_001.json').read_text())
files=['api_service_execution.py','bvbrc_appservice_adapters.py','bvbrc_appservice_host.py','bvbrc_appservice_publication.py','execution_episodes.py']
outputs=[]
for name in files:
 rel='gene_annotation_episode/'+name
 path=Path(rel)
 candidates=[root/'verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182/candidate'/rel, root/rel]
 expected=next((x['after_sha256'] for x in composition['files'] if x['path']==rel),None)
 baseline=next((p for p in candidates if p.is_file() and (expected is None or hashlib.sha256(p.read_bytes()).hexdigest()==expected)),None)
 if baseline is None:
  outputs.append({'file':rel,'baseline':'unavailable','expected':expected});continue
 diff=''.join(difflib.unified_diff(baseline.read_text().splitlines(True),path.read_text().splitlines(True),fromfile=str(baseline),tofile=str(path)))
 Path('../evidence_i/'+name+'.diff').write_text(diff)
 outputs.append({'file':rel,'baseline':str(baseline),'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'added':sum(1 for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')),'removed':sum(1 for line in diff.splitlines() if line.startswith('-') and not line.startswith('---'))})
Path('../evidence_i/SHARED_DELTA_AUDIT_001.json').write_text(json.dumps(outputs,indent=2)+'\n')
print(json.dumps(outputs,indent=2))
