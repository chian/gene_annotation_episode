"""Emit complete sequential authority chunks; acknowledge only observed full output."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
ACTIVE=Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001'
FILES=[ACTIVE,ROOT/'AGENTS.md',ROOT/'GOAL.md',ROOT/'docs/EPISODE_STRUCTURE.md',ROOT/'docs/TIME_AWARE_ESTIMATION.md',ROOT/'docs/TOOL_KNOWLEDGE.md',ROOT/'docs/TASK_AND_STEERING.md',ROOT/'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md',ROOT/'docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',ROOT/'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',ROOT/'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',ROOT/'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',ROOT/'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md',ROOT/'research/experimental_scoring_review_2026-10-23/AGENTS.md',ROOT/'research/experimental_scoring_review_2026-10-23/SOURCE_CORRECTIONS.md',ROOT/'research/experimental_scoring_review_2026-10-23/a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md',ROOT/'gene_annotation_episode/literature_assay_prompt.py',ROOT/'gene_annotation_episode/literature_assay_inputs.py',ROOT/'gene_annotation_episode/literature_activity_calculations.py',ROOT/'gene_annotation_episode/literature_experimental_contracts.py',ROOT/'gene_annotation_episode/literature_rate_calculations.py',BASE/'ASSAY_GRAPH_INTERFACES_001.md',BASE/'ASSAY_GRAPH_INTERFACES_002.md',BASE/'NATIVE_RATE_SOURCE_INTERFACES_024.md',BASE/'LATEST_HUMAN_DIRECTION_PARENT_028.txt']
sha=lambda b:hashlib.sha256(b).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--read',type=int);p.add_argument('--ack',type=int);a=p.parse_args()
chunks=[];entries=[]
for path in FILES:
 raw=path.read_bytes();lines=raw.decode().splitlines(keepends=True)
 entries.append({'path':str(path),'bytes':len(raw),'sha256':sha(raw),'lines':len(lines)})
 buf='';start=1
 for index,line in enumerate(lines,1):
  if len((buf+line).encode())>19000 and buf:
   chunks.append({'path':str(path),'start_line':start,'end_line':index-1,'text':buf});buf='';start=index
  buf+=line
 if buf:chunks.append({'path':str(path),'start_line':start,'end_line':len(lines),'text':buf})
receipt=OUT/'READ_RECEIPT.json'
if receipt.exists():
 d=json.loads(receipt.read_bytes());assert d['documents']==entries
else:d={'created_utc':datetime.now(timezone.utc).isoformat(),'documents':entries,'chunks_total':len(chunks),'acknowledged_chunks':[],'complete':False,'paper_packet':'complete FINDINGS.md reread after initial truncated combined display; PROVENANCE.md body displayed untruncated in that initial output','scientific_interpretation_started':False}
if a.ack is not None:
 assert a.ack==len(d['acknowledged_chunks']) and a.ack<len(chunks)
 d['acknowledged_chunks'].append({k:v for k,v in chunks[a.ack].items() if k!='text'})
 d['complete']=len(d['acknowledged_chunks'])==len(chunks)
 receipt.write_text(json.dumps(d,indent=2)+'\n')
if a.read is not None:
 assert a.read==len(d['acknowledged_chunks'])
 c=chunks[a.read]
 print(json.dumps({'chunk':a.read,'total':len(chunks),**{k:v for k,v in c.items() if k!='text'}}))
 print(c['text'],end='')
else:print(json.dumps({'acknowledged':len(d['acknowledged_chunks']),'total':len(chunks),'complete':d['complete']}))
