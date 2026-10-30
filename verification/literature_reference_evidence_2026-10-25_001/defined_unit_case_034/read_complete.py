from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys
out=Path(__file__).resolve().parent
plan=json.loads((out/'read_plan.json').read_text())
phase=sys.argv[1]
if phase=='code':plan=json.loads((out/'code_plan.json').read_text())
if phase=='paper':plan=['verification/literature_reference_evidence_2026-10-25_001/literature_model_run_024/pin_001/inputs/PRIMARY_ARTICLE_TEXT_001.txt']
chunks=[]
for name in plan:
 p=Path(name).resolve();raw=p.read_bytes();txt=raw.decode();lines=txt.splitlines(keepends=True);start=1;buf=''
 for i,line in enumerate(lines,1):
  if len(buf)+len(line)>16000 and buf:
   chunks.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),start_line=start,end_line=i-1,text=buf));start=i;buf=''
  buf+=line
 if buf:chunks.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),start_line=start,end_line=len(lines),text=buf))
index=int(sys.argv[2]);c=chunks[index]
print(json.dumps(dict(phase=phase,index=index,total=len(chunks),**{k:v for k,v in c.items() if k!='text'})))
print(c['text'],end='')
log=out/'read_receipts.jsonl'
with log.open('a') as s:s.write(json.dumps(dict(phase=phase,index=index,total=len(chunks),utc=datetime.now(timezone.utc).isoformat(),**{k:v for k,v in c.items() if k!='text'}))+'\n')
