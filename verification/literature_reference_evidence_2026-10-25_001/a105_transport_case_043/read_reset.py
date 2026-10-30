raise SystemExit("Historical agent-note reader retired.")

from pathlib import Path
import json,hashlib,sys,datetime
R=Path.cwd();O=R/'verification/literature_reference_evidence_2026-10-25_001/a105_transport_case_043';B=R/'verification/literature_reference_evidence_2026-10-25_001';A=Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
paths=[A]+[R/p for p in ['AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md','docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md','docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md','research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md','research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md','docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md','verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md','research/experimental_scoring_review_2026-10-23/AGENTS.md','research/experimental_scoring_review_2026-10-23/SOURCE_CORRECTIONS.md','research/experimental_scoring_review_2026-10-23/a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md','gene_annotation_episode/literature_transport_calculations.py','gene_annotation_episode/literature_transport_inputs.py','gene_annotation_episode/literature_transport_storage.py','gene_annotation_episode/literature_quantity_storage.py','gene_annotation_episode/literature_prose_reader.py','gene_annotation_episode/literature_html_quantity_reader.py','gene_annotation_episode/literature_assay_inputs.py','gene_annotation_episode/literature_experimental_contracts.py']]+[B/'LATEST_HUMAN_DIRECTION_PARENT_039.txt',B/'LITERATURE_GRADER_SELECTION_TARGET_040.md',A]
chunks=[];docs=[]
for p in paths:
 raw=p.read_bytes();lines=raw.decode().splitlines(True);docs.append(dict(path=str(p),bytes=len(raw),lines=len(lines),sha256=hashlib.sha256(raw).hexdigest()));buf='';start=1
 for i,l in enumerate(lines,1):
  if len((buf+l).encode())>16000 and buf:chunks.append(dict(path=str(p),start=start,end=i-1,text=buf));buf='';start=i
  buf+=l
 if buf:chunks.append(dict(path=str(p),start=start,end=len(lines),text=buf))
phase,action=sys.argv[1:3];f=O/(phase+'_receipt.json');d=json.loads(f.read_text()) if f.exists() else dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),documents=docs,chunks=len(chunks),acknowledged=[],complete=False)
assert d['documents']==docs
if action=='ack':
 for n in map(int,sys.argv[3:]):
  assert n==len(d['acknowledged']);d['acknowledged'].append({k:v for k,v in chunks[n].items() if k!='text'})
 d['complete']=len(d['acknowledged'])==len(chunks);f.write_text(json.dumps(d,indent=2)+'\n');print('ack',len(d['acknowledged']),'/',len(chunks))
else:
 n=int(action);assert n==len(d['acknowledged']);
 for j in range(n,min(len(chunks),n+(int(sys.argv[3]) if len(sys.argv)>3 else 1))):
  print(json.dumps(dict(chunk=j,total=len(chunks),**{k:v for k,v in chunks[j].items() if k!='text'})));print(chunks[j]['text'],end='')
