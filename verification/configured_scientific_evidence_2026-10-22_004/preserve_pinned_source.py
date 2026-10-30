"""Copy the earlier run-pin source capsule; never read mutable live sources."""
import hashlib
import json
import datetime as dt
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = ROOT / "verification/episode_assignment_transport_2026-10-21_001"
manifest_bytes = (SOURCE / "MANIFEST.json").read_bytes()
assert hashlib.sha256(manifest_bytes).hexdigest() == "803a3f649a7b4c52cf41f8750d364b54207adda9ee5d16cbd3fed0039dd16248"
manifest = json.loads(manifest_bytes)
provenance_path = OUT / "file_provenance.json"
provenance = json.loads(provenance_path.read_text())
members=[]
for entry in manifest["files"]:
    if not entry["path"].startswith("implementation/"):
        continue
    src=SOURCE/entry["path"]
    data=src.read_bytes()
    assert len(data)==entry["bytes"]
    assert hashlib.sha256(data).hexdigest()==entry["sha256"]
    dest=OUT/entry["path"]
    if dest.exists():
        assert dest.read_bytes()==data
    else:
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(data)
        provenance["original_files"].append({"source_path":str(src.relative_to(ROOT)),"publication_path":entry["path"],"kind":"unchanged_prior_preserved_pinned_source","sha256":entry["sha256"],"bytes":entry["bytes"]})
    members.append(entry)
pin_manifest=OUT/"binding/prior_source_manifest.json"
assert not pin_manifest.exists()
pin_manifest.write_bytes(manifest_bytes)
provenance["original_files"].append({"source_path":str((SOURCE/"MANIFEST.json").relative_to(ROOT)),"publication_path":"binding/prior_source_manifest.json","kind":"earlier_pinned_source_manifest","sha256":hashlib.sha256(manifest_bytes).hexdigest(),"bytes":len(manifest_bytes)})
provenance["source_pin_comparison"]={"prior_manifest":str((SOURCE/"MANIFEST.json").relative_to(ROOT)),"prior_manifest_sha256":hashlib.sha256(manifest_bytes).hexdigest(),"implementation_members_preserved_and_verified":len(members),"existing_003_source_copies_match":True,"mutable_live_source_files_used":False}
provenance["copy_finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
provenance_path.write_text(json.dumps(provenance,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
print(json.dumps(provenance["source_pin_comparison"],indent=2))
