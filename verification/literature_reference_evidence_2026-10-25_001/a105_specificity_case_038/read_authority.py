raise SystemExit("Historical agent-note reader retired.")

from pathlib import Path
import argparse, hashlib, json
from datetime import datetime,timezone
ROOT=Path('/home/chia/repos/gene_annotation_episode');OUT=Path(__file__).resolve().parent
ACTIVE=Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001'
NAMES=['AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md','docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md','docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md','research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md','research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md','docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md','verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md','research/experimental_scoring_review_2026-10-23/AGENTS.md','research/experimental_scoring_review_2026-10-23/SOURCE_CORRECTIONS.md','research/experimental_scoring_review_2026-10-23/a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md','gene_annotation_episode/literature_assay_inputs.py','gene_annotation_episode/literature_activity_calculations.py','gene_annotation_episode/literature_experimental_contracts.py','gene_annotation_episode/literature_rate_calculations.py','gene_annotation_episode/literature_ratio_calculations.py','gene_annotation_episode/literature_ratio_reader.py','gene_annotation_episode/literature_rate_reader.py']
FILES=[ACTIVE]+[ROOT/x for x in NAMES]+[BASE/'ASSAY_GRAPH_INTERFACES_001.md',BASE/'ASSAY_GRAPH_INTERFACES_002.md',BASE/'NATIVE_RATE_SOURCE_INTERFACES_024.md',BASE/'LATEST_HUMAN_DIRECTION_PARENT_028.txt',ACTIVE]
chunks=[];docs=[]
for path in FILES:
 b=path.read_bytes();ls=b.decode().splitlines(keepends=True);docs.append({'path':str(path),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'lines':len(ls)})
 buf='';start=1
 for i,line in enumerate(ls,1):
  if len((buf+line).encode())>26000 and buf:
   chunks.append({'path':str(path),'start_line':start,'end_line':i-1,'text':buf});buf='';start=i
  buf+=line
 if buf:chunks.append({'path':str(path),'start_line':start,'end_line':len(ls),'text':buf})
p=argparse.ArgumentParser();p.add_argument('--read',type=int);p.add_argument('--ack',type=int,action='append');a=p.parse_args()
f=OUT/'READ_RECEIPT.json'
d=json.loads(f.read_text()) if f.exists() else {'created_utc':datetime.now(timezone.utc).isoformat(),'documents':docs,'chunks_total':len(chunks),'acknowledged_chunks':[],'complete':False,'source_read_before_reset':'PMC2711008 BioC passages 0-75: complete main article Methods and Results/Discussion, table and captions; references not claimed; supplement not accessed'}
assert d['documents']==docs
for n in a.ack or []:
 assert n==len(d['acknowledged_chunks']);d['acknowledged_chunks'].append({k:v for k,v in chunks[n].items() if k!='text'})
d['complete']=len(d['acknowledged_chunks'])==len(chunks);f.write_text(json.dumps(d,indent=2)+'\n')
if a.read is not None:
 assert a.read==len(d['acknowledged_chunks']);print(json.dumps({'chunk':a.read,'total':len(chunks),**{k:v for k,v in chunks[a.read].items() if k!='text'}}));print(chunks[a.read]['text'],end='')
else:print(json.dumps({'read':len(d['acknowledged_chunks']),'total':len(chunks),'complete':d['complete']}))
