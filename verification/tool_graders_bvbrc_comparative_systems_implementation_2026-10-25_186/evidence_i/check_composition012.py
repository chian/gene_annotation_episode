from pathlib import Path
import hashlib,json
receipt=json.loads(Path('../PROTEOME_COMPOSITION_RECEIPT_001.json').read_text())
allowed={'gene_annotation_episode/bvbrc_appservice_adapters.py','gene_annotation_episode/bvbrc_appservice_publication.py','gene_annotation_episode/execution_episodes.py','pyproject.toml'}
rows=[]
for row in receipt['files']:
 path=Path(row['path'])
 actual=hashlib.sha256(path.read_bytes()).hexdigest()
 rows.append({'path':str(path),'composition_sha256':row['after_sha256'],'current_sha256':actual,'unchanged':actual==row['after_sha256'],'allowed_shared_or_root_packaging_delta':str(path) in allowed})
assert all(row['unchanged'] or row['allowed_shared_or_root_packaging_delta'] for row in rows)
Path('../evidence_i/PROTEOME_PRESERVATION_001.json').write_text(json.dumps({'unexpected_changes':[],'files':rows},indent=2)+'\n')
print({'unchanged_files':sum(x['unchanged'] for x in rows),'changed_allowed_files':[x['path'] for x in rows if not x['unchanged']]})
