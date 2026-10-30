from pathlib import Path
import json
from gene_annotation_episode.tool_knowledge import ToolKnowledge
root=Path.cwd().parents[2]
library=ToolKnowledge.freeze(Path('snapshot'))
rows=[]
for name,tool in [('alignment-reference-sites','sequence.sites'),('blast-hsp-columns','result.blast.hsp')]:
 entry=library.entry(name)['entry']
 assert name in library.entries_for_tool(tool)
 query=dict(entry_id=name,section_id='operation-results',offset=0,limit=17)
 pages=[]
 while query is not None:
  result=library.execute('knowledge.read',query)
  assert result['status']=='completed'
  assert result['record_refs']==result['changed_record_refs']==[]
  pages.append(result['result']['text']);query=result['result']['next_query']
 content=''.join(pages)
 expected=(root/'gene_annotation_episode/knowledge'/(name+'.md')).read_text()
 assert content==expected
 if name=='blast-hsp-columns':
  assert 'native paired BLAST' in entry['summary']
  assert 'gene_annotation_episode/native_blast_hsp_views.py' in entry['provenance']
 rows.append({'entry':entry,'pages':len(pages),'bytes':len(content.encode()),'complete_text_recovered':True})
Path('result.json').write_text(json.dumps({'entries':rows,'new_scientific_records':0,'native_execution':False},indent=2)+'\n')
print(json.dumps({'entries':len(rows),'all_complete':True}))
