"""Freeze current application source and synthetic test inputs without histories."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PIN=HERE/'pin_001'

def main():
    if PIN.exists():raise RuntimeError('Never overwrite a retained snapshot')
    files={}
    for directory in ('gene_annotation_episode','method_loop','tests'):
        for p in sorted((ROOT/directory).rglob('*')):
            if not p.is_file() or any(part in ('__pycache__','.pytest_cache','.git') for part in p.parts):continue
            relative=p.relative_to(ROOT);raw=p.read_bytes();out=PIN/relative
            out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
            files[str(relative)]=hashlib.sha256(raw).hexdigest()
    for name in ('pyproject.toml',):
        raw=(ROOT/name).read_bytes();(PIN/name).write_bytes(raw);files[name]=hashlib.sha256(raw).hexdigest()
    owned=json.loads((ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_raw_replicate_binding_163/final_manifest_002.json').read_text())
    for section in ('changed_owned_files','approved_inspected_unchanged_files'):
        for name,digest in owned[section].items():assert files[name]==digest,(name,'agent-final bytes differ')
    changed=[name for name,digest in files.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
    result={'scope':'Current full package, shared loop and tests frozen for focused raw-table verification; no runtime/model histories copied. Concurrent unrelated package bytes retained, with no correctness claim for their paths.','files':files,'live_changed_during_freeze':changed,'owned_final_manifest_verified':True}
    with (HERE/'PIN_001.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    assert not changed,changed
    print(json.dumps({'snapshot':str(PIN),'file_count':len(files),'live_changes_during_freeze':changed,'owned_final_bytes_verified':True}))
if __name__=='__main__':main()
