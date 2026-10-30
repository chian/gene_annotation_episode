raise SystemExit("Historical agent-note reader retired.")

from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
ACTIVE=Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
BASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001'
paths=['AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md','docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md','docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md','research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md','research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md','docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md','verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md','research/experimental_scoring_review_2026-10-23/AGENTS.md','research/experimental_scoring_review_2026-10-23/SOURCE_CORRECTIONS.md','research/experimental_scoring_review_2026-10-23/a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md','gene_annotation_episode/literature_binding_reader.py','gene_annotation_episode/literature_binding_calculations.py','gene_annotation_episode/literature_binding_model_inputs.py','gene_annotation_episode/literature_binding_models.py','gene_annotation_episode/literature_binding_prompt.py','gene_annotation_episode/literature_binding_storage.py','gene_annotation_episode/literature_binding_model_storage.py','gene_annotation_episode/literature_experimental_contracts.py']
files=[ACTIVE]+[ROOT/p for p in paths]+[BASE/'LATEST_HUMAN_DIRECTION_PARENT_039.txt',BASE/'LITERATURE_GRADER_SELECTION_TARGET_040.md',ACTIVE]
chunks=[];entries=[]
for p in files:
 raw=p.read_bytes();lines=raw.decode().splitlines(keepends=True);entries.append({'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lines':len(lines)});buf='';start=1
 for i,line in enumerate(lines,1):
  if len((buf+line).encode())>17000 and buf:chunks.append({'path':str(p),'start_line':start,'end_line':i-1,'text':buf});buf='';start=i
  buf+=line
 if buf:chunks.append({'path':str(p),'start_line':start,'end_line':len(lines),'text':buf})
a=argparse.ArgumentParser();a.add_argument('--read',type=int);a.add_argument('--count',type=int,default=1);a.add_argument('--ack',type=int,action='append');v=a.parse_args();rp=OUT/'READ_RECEIPT.json'
d=json.loads(rp.read_text()) if rp.exists() else {'created_utc':datetime.now(timezone.utc).isoformat(),'documents':entries,'chunks_total':len(chunks),'acknowledged_chunks':[],'complete':False,'paper_read':'primary_text.txt all409 lines sequential observed; table3.jpg visual inspected; supplement inaccessible; no companion papers or retained paper packet read'}
assert d['documents']==entries
for n in v.ack or []:
 assert n==len(d['acknowledged_chunks']);d['acknowledged_chunks'].append({k:x for k,x in chunks[n].items() if k!='text'})
d['complete']=len(d['acknowledged_chunks'])==len(chunks);rp.write_text(json.dumps(d,indent=2)+'\n')
if v.read is not None:
 assert v.read==len(d['acknowledged_chunks'])
 for i in range(v.read,min(v.read+v.count,len(chunks))):
  c=chunks[i];print(json.dumps({'chunk':i,'total':len(chunks),**{k:x for k,x in c.items() if k!='text'}}));print(c['text'],end='')
else:print(json.dumps({'acknowledged':len(d['acknowledged_chunks']),'total':len(chunks),'complete':d['complete']}))
