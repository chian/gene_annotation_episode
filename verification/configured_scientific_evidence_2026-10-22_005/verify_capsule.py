"""Read-only checks of all additive members and referenced 004 source bytes."""
import hashlib
import json
from pathlib import Path
import stat

OUT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
manifest=json.loads((OUT/"MANIFEST.json").read_text())
listed={x["path"] for x in manifest["files"]}
actual={str(x.relative_to(OUT)) for x in OUT.rglob("*") if x.is_file() and x.name!="MANIFEST.json"}
assert listed==actual
for x in manifest["files"]:
    p=OUT/x["path"];data=p.read_bytes()
    assert len(data)==x["bytes"] and sha(data)==x["sha256"],p
    assert stat.S_IMODE(p.stat().st_mode)==0o444,p
assert stat.S_IMODE((OUT/"MANIFEST.json").stat().st_mode)==0o444
references=json.loads((OUT/"prior_references.json").read_text())
prior=OUT.parents[1]/references["prior_directory"]
assert sha((prior/"MANIFEST.json").read_bytes())==references["prior_manifest_sha256"]
prior_manifest={x["path"]:x for x in json.loads((prior/"MANIFEST.json").read_text())["files"]}
referenced_files={x["prior_file"] for x in references["references"].values()}
for name in referenced_files:
    p=prior/name;data=p.read_bytes();entry=prior_manifest[name]
    assert len(data)==entry["bytes"] and sha(data)==entry["sha256"],p
for name in ["verification/provider_context_matches.json","verification/source_anchor_matches.json"]:
    for entry in json.loads((OUT/name).read_text()):
        if "quote_matches_exact_utf8_byte_slice" in entry:assert entry["quote_matches_exact_utf8_byte_slice"]
        else:assert entry["request_context_matches_original_workspace_request"] and entry["response_matches_original_workspace_response"]
report=OUT.parents[1]/"docs/CONFIGURED_SCIENTIFIC_EVIDENCE_2026-10-22_005.md"
assert stat.S_IMODE(report.stat().st_mode)==0o444
print(json.dumps({"verified_members":len(listed),"member_bytes":sum(x["bytes"] for x in manifest["files"]),"referenced_004_files_verified":len(referenced_files),"manifest_sha256":sha((OUT/"MANIFEST.json").read_bytes()),"report_sha256":sha(report.read_bytes()),"report_bytes":report.stat().st_size,"all_published_files_read_only":True},indent=2))
