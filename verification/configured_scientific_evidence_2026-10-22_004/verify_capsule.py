"""Verify published members without opening a database or importing the app."""
import hashlib
import json
from pathlib import Path
import stat

OUT=Path(__file__).resolve().parent
manifest=json.loads((OUT/"MANIFEST.json").read_text())
listed={x["path"] for x in manifest["files"]}
actual={str(x.relative_to(OUT)) for x in OUT.rglob("*") if x.is_file() and x.name!="MANIFEST.json"}
assert listed==actual, (listed-actual,actual-listed)
for x in manifest["files"]:
    p=OUT/x["path"]
    data=p.read_bytes()
    assert len(data)==x["bytes"],p
    assert hashlib.sha256(data).hexdigest()==x["sha256"],p
    assert stat.S_IMODE(p.stat().st_mode)==0o444,p
assert stat.S_IMODE((OUT/"MANIFEST.json").stat().st_mode)==0o444
for name in ["verification/provider_context_matches.json","verification/source_anchor_matches.json"]:
    values=json.loads((OUT/name).read_text())
    for x in values:
        if "quote_matches_exact_utf8_byte_slice" in x:
            assert x["quote_matches_exact_utf8_byte_slice"]
        else:
            assert x["request_context_matches_original_workspace_request"]
            assert x["response_matches_original_workspace_response"]
report=OUT.parents[1]/"docs/CONFIGURED_SCIENTIFIC_EVIDENCE_2026-10-22_004.md"
assert stat.S_IMODE(report.stat().st_mode)==0o444
print(json.dumps({"verified_members":len(listed),"member_bytes":sum(x["bytes"] for x in manifest["files"]),"manifest_sha256":hashlib.sha256((OUT/"MANIFEST.json").read_bytes()).hexdigest(),"report_sha256":hashlib.sha256(report.read_bytes()).hexdigest(),"report_bytes":report.stat().st_size,"all_published_files_read_only":True},indent=2))
