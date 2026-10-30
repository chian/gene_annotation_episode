"""Seal additive009; prove every original008 payload/manifest/checksum unchanged."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent

def fp(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(n,v):
 with (HERE/n).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
old=json.loads((HERE/'FINAL_MANIFEST_008.json').read_text())
assert old['file_count']==92
assert all(fp(HERE/n)==v for n,v in old['files'].items())
old_sha_lines=(HERE/'SHA256SUMS_008.txt').read_text().splitlines()
for line in old_sha_lines:
 expected,name=line.split('  ',1);assert fp(HERE/name)['sha256']==expected
put('PRESERVATION_009.json',dict(original_manifest008_payloads=92,all_equal=True,original008_checksum_lines=93,
 all_original_checksum_payloads_and_manifest_equal=True,
 original_manifest008=fp(HERE/'FINAL_MANIFEST_008.json'),original_checksum008=fp(HERE/'SHA256SUMS_008.txt'),
 production_or_old_artifact_mutations=False))
put('READ_PROVENANCE_009.json',dict(prior_complete_read_provenance='READ_PROVENANCE_006.json',
 correction_reads={n:fp(HERE/n) for n in ['build_declarations_006.py','verify_design_006.py','DESIGN_VERIFICATION_006.json',
 'TASK_AND_STEERING_004.md','FINAL_MANIFEST_008.json','SHA256SUMS_008.txt']},
 latest_root_direction='Closed authority-selection basis and null absent-local source-kind corrections; original008 payload preservation; no production writes',
 new_paper_or_retained_paper_packet_read=False,post_packet_reset_triggered=False,new_sources_or_models=False))
proof=json.loads((HERE/'DESIGN_VERIFICATION_007.json').read_text());assert proof['schema_count']==7
payload={str(p.relative_to(HERE)):fp(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['FINAL_MANIFEST_009.json','SHA256SUMS_009.txt']}
put('FINAL_MANIFEST_009.json',dict(status='design_only_no_production_release',file_count=len(payload),files=payload,
 final_schema_generation='007',schema_count=7,api_generation='007',latest_contract_correction='009',latest_task_template='009',
 original008_payloads_unchanged=92,new_source_reads=0,new_owner_populations=0,production_writes=False,
 v3_reader_or_new_local_API_implemented=False))
lines=[f"{v['sha256']}  {n}\n" for n,v in payload.items()]
lines.append(f"{fp(HERE/'FINAL_MANIFEST_009.json')['sha256']}  FINAL_MANIFEST_009.json\n")
with (HERE/'SHA256SUMS_009.txt').open('x') as f:f.writelines(lines)
print(json.dumps(dict(final_payloads=len(payload),checksum_lines=len(lines),schemas=7,original008_payloads_preserved=92)))
