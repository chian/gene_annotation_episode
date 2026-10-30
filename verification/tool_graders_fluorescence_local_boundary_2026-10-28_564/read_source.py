raise SystemExit("Historical agent-note reader retired.")

from pathlib import Path
import ast, hashlib, json, sys
base=Path(__file__).resolve().parent
records=[]
for arg in sys.argv[1:]:
    name,sep,selection=arg.partition('#')
    p=Path(name)
    if p.name == 'GOAL.md': raise SystemExit('prohibited source')
    raw=p.read_bytes(); text=raw.decode(); lines=text.splitlines(keepends=True)
    scopes=[]
    if not sep:
        print('\n=== '+name+' (complete) ===\n'+text)
        scopes=[{'kind':'complete_file','start_line':1,'end_line':len(lines)}]
    else:
        tree=ast.parse(text)
        for requested in selection.split(','):
            found=None
            for node in tree.body:
                if getattr(node,'name',None)==requested: found=node
                if isinstance(node,ast.ClassDef):
                    for child in node.body:
                        if node.name+'.'+getattr(child,'name','')==requested: found=child
            if found is None: raise SystemExit('missing '+requested)
            first=min([found.lineno]+[d.lineno for d in getattr(found,'decorator_list',[])])
            print('\n=== '+name+' '+requested+' lines '+str(first)+'-'+str(found.end_lineno)+' ===\n'+''.join(lines[first-1:found.end_lineno]))
            scopes.append({'kind':'complete_symbol','symbol':requested,'start_line':first,'end_line':found.end_lineno})
    records.append({'path':str(p.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw),'scopes':scopes})
manifest=base/'SOURCE_READS.jsonl'
with manifest.open('a') as stream:
    for record in records: stream.write(json.dumps(record,sort_keys=True)+'\n')
g=Path('/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt').read_text()
print('\n'+g.split('\n\n',1)[0]+'\n\n'+g[g.index('OPERATING PRINCIPLES —'):g.index('ACCOUNTING AND COMPLETION')])
