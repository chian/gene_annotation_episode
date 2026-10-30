from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as E,re
from fractions import Fraction
from datetime import datetime,timezone
base=Path(__file__).parent; orig=base/'originals'; derived=base/'derived';derived.mkdir(exist_ok=True)
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,obj): (base/n).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
urls={'elife65773.html':'https://elifesciences.org/articles/65773','elife65773.pdf':'https://elifesciences.org/articles/65773.pdf','elife65773_fig5.xlsx':'https://cdn.elifesciences.org/articles/65773/elife-65773-fig5-data1-v2.xlsx','elife65773_fig6.xlsx':'https://cdn.elifesciences.org/articles/65773/elife-65773-fig6-data1-v2.xlsx'}
manifest=[]
for name,url in urls.items():
 p=orig/name;b=p.read_bytes();manifest.append({'path':str(p),'url':url,'bytes':len(b),'sha256':sha(b),'kind':'original_public_bytes','received_file_mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),'http_result':'200 in acquisition output'})
save('SOURCE_MANIFEST_001.json',manifest)
selectors=[]; inventories=[]
for fn in ['elife65773_fig5.xlsx','elife65773_fig6.xlsx']:
 with zipfile.ZipFile(orig/fn) as z:
  strings=[''.join(t.itertext()) for t in E.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
  wb=E.fromstring(z.read('xl/workbook.xml'))
  relroot=E.fromstring(z.read('xl/_rels/workbook.xml.rels'))
  rels={e.get('Id'):e.get('Target') for e in relroot}
  for sheet in wb.find('m:sheets',ns):
   rid=sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id');target=rels[rid];member=target.lstrip('/') if target.startswith('/') else 'xl/'+target
   data=z.read(member);root=E.fromstring(data);cells={}
   for c in root.findall('.//m:c',ns):
    v=c.find('m:v',ns)
    if v is not None:cells[c.get('r')]={'value':strings[int(v.text)] if c.get('t')=='s' else v.text,'type':c.get('t'),'formula':c.findtext('m:f',namespaces=ns)}
   inventories.append({'workbook':fn,'sheet_name':sheet.get('name'),'member':member,'nonempty_cells':len(cells),'dimension':root.find('m:dimension',ns).get('ref') if root.find('m:dimension',ns) is not None else None})
   # Preserve complete exact XML members, plus readable coordinate inventory for small numeric tables.
   if member!='xl/worksheets/sheet1.xml':
    out=derived/(fn.replace('.xlsx','')+'_'+sheet.get('name')+'.xml');out.write_bytes(data)
    (out.with_suffix('.cells.json')).write_text(json.dumps(cells,indent=2,ensure_ascii=False)+'\n')
   if fn=='elife65773_fig6.xlsx' and sheet.get('name')=='Fig6C':
    for coord in cells:
     m=re.search(rb'<c\b[^>]*\br="'+coord.encode()+rb'"[^>]*>.*?</c>',data)
     assert m
     selectors.append({'original_path':str(orig/fn),'original_sha256':sha((orig/fn).read_bytes()),'zip_member':member,'member_sha256':sha(data),'sheet_name':sheet.get('name'),'cell':coord,'member_byte_start':m.start(),'member_byte_end':m.end(),'exact_xml':m.group().decode(),'resolved_value':cells[coord]})
   if fn=='elife65773_fig5.xlsx' and member in ['xl/worksheets/sheet3.xml','xl/worksheets/sheet5.xml']:
    # The coordinate inventory preserves source facts, without inferring column-level experiment pairing.
    pass
save('WORKBOOK_INVENTORY_001.json',inventories);save('FIG6C_EXACT_SELECTORS_001.json',selectors)
# Byte-exact bounded HTML source locations, preserving markup instead of invented clean-text offsets.
h=(orig/'elife65773.html').read_bytes();loc=[]
for phrase in [b'All assays are linear',b'The appearance of nicotinamide',b'PARP1 (100 nM) was pre-incubated',b'The area under the curve',b'Reaction volumes were increased',b'Wild-type PARP1 was expressed',b'neither wild-type HPF1']:
 pos=h.find(phrase)
 if pos<0:loc.append({'phrase':phrase.decode(),'status':'literal_not_found'});continue
 a=h.rfind(b'<p',0,pos);b=h.find(b'</p>',pos)+4
 assert a>=0 and b>pos
 loc.append({'source_path':str(orig/'elife65773.html'),'sha256':sha(h),'needle':phrase.decode(),'start':a,'end':b,'quote_html':h[a:b].decode()})
save('METHODS_HTML_SELECTORS_001.json',loc)
# Arithmetic from the explicitly reviewed native Fig6C cells, not an implemented sheet population.
t0=Fraction('1');t=Fraction('50');nad0=Fraction('200');nad=Fraction('100');nam0=Fraction('6.5');nam=Fraction('101');adpr0=Fraction('2.8');adpr=Fraction('13.2')
L=nad0-nad;R=nam-nam0;D=L-R
results={'status':'research arithmetic only; not current sheet execution','native_measurements':{'time_s':[1,50],'NAD_uM':[200,100],'nicotinamide_uM':[6.5,101],'free_ADPR_uM':[2.8,13.2]},'proposed_common_quantity':'amount concentration of NAD glycosidic-bond cleavage from 1 to 50 s, conditional on one NAM per NAD and no other NAD loss/NAM source','calculated_descriptive_cells':{},'uncertainty':{'joint_estimator_covariance':None,'reason':'single released paired timecourse, not same-time replicate pairs; no reported fit-estimator covariance or adequate repeated-experiment sampling model','common_unbiased_model_supported':False,'GLS_weights':None,'combined_estimate':None,'combined_variance':None},'synthetic_values_used':False}
for key,value in [('NAD_loss_uM',L),('NAM_gain_uM',R),('difference_uM',D),('NAD_loss_to_NAM_gain_ratio',L/R),('average_NAD_loss_rate_uM_per_s',L/(t-t0)),('average_NAM_gain_rate_uM_per_s',R/(t-t0)),('free_ADPR_gain_uM',adpr-adpr0),('free_ADPR_gain_per_NAM_gain',(adpr-adpr0)/R)]:
 results['calculated_descriptive_cells'][key]={'fraction':{'numerator':str(value.numerator),'denominator':str(value.denominator)},'value':float(value)}
save('DESCRIPTIVE_ARITHMETIC_001.json',results)
print(json.dumps({'originals':len(manifest),'exact_fig6c_cell_selectors':len(selectors),'arithmetic':results['calculated_descriptive_cells'],'output_directory':str(base)},indent=2))
