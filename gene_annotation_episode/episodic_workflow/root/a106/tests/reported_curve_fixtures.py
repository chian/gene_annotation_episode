"""Original workbook/source setup and actual Store fixture, exact scientific operands."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
from ..state import Store
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_observation_inputs import GRID_INPUT_VERSION
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_observation_storage import GRID_REQUESTED, GRID_POPULATION
CASE = Path(__file__).parent / 'fixtures/retained_scientific_sources/reported_curve' 

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def artifact(raw):return 'artifact_'+hashlib.sha256(raw).hexdigest()

def label(address,text):return {'cell':address,'expected_text':text}

def xlabel(address,text):return {'kind':'xlsx_label',**label(address,text)}

def source_setup():
    # Retained source witnesses supply locations/meanings only, never numeric
    # arguments to the reader. Every operand is reread from the original XLSX.
    packet=json.loads((CASE/'SOURCE_PACKET_001.json').read_text())
    raw=(CASE/'originals/S1Data.xlsx').read_bytes()
    context=(CASE/'originals/article_text.txt').read_bytes(); ar=artifact(context)
    def span(name):
        w=packet['article_witnesses'][name]
        return {'kind':'context_span','source_ref':'source_'+'2'*24,'artifact_ref':ar,
                'start':w['start'],'end':w['end'],'quote':w['quote']}
    caption=span('S17_caption'); methods=span('main_mutant_kinetic_method')
    args={'version':GRID_INPUT_VERSION,'source_ref':'source_'+'1'*24,
        'source_kind':'primary_source','worksheet':'Sheet1',
        'panel':label('A189',packet['selected_headers']['A189']['value']),
        'subject':label('Q191','PK_WT-DHA'),
        'native_rate_label':label('B190','NADH consumption rate µmol min-1'),
        'curves':[{'header':label(c+'192','data-'+str(j+1))} for j,c in enumerate('RST')],
        'points':[{'concentration_cell':'Q'+str(i),'rate_cells':[c+str(i) for c in 'RST']} for i in range(193,206)],
        'rate_unit':{'code':'umol/min','witness':xlabel('B190','NADH consumption rate µmol min-1')},
        'concentration_unit':{'code':'mM','witness':caption},
        'endpoint_relationship':{'status':'conflicting','witnesses':[xlabel('B190','NADH consumption rate µmol min-1'),methods]},
        'curve_sampling':{'status':'stipulated_sensitivity','assumption':'iid_reported_curve_vectors',
            'source_claim':'not_established','witnesses':[caption]}}
    docs=[{'source_ref':'source_'+'2'*24,'artifact_ref':ar,'content':context}]
    return raw,args,docs,packet

def select(scope,component,**kw):return {'scope':scope,'component':component,**kw}

def edit_workbook(mutator):
    raw,_,_,_=source_setup(); out=io.BytesIO()
    with ZipFile(io.BytesIO(raw)) as original,ZipFile(out,'w',ZIP_DEFLATED) as target:
        for name in original.namelist():
            content=original.read(name)
            if name=='xl/worksheets/sheet1.xml':
                sheet=ET.fromstring(content); cells={c.get('r'):c for c in sheet.findall('m:sheetData/m:row/m:c',NS)}
                mutator(sheet,cells); content=ET.tostring(sheet,encoding='utf-8')
            target.writestr(name,content)
    return out.getvalue()

SELECTORS=[select('point','cv',concentration_cell='Q196'),
    select('estimator','Km',estimator='fit_of_point_means'),
    select('estimator','log_efficiency_variance',estimator='fit_of_point_means')]

def setup(path,*,selectors=SELECTORS,nondetection=False):
    raw,grid,docs,_=source_setup()
    if nondetection:
        from xml.etree import ElementTree as ET
        def mutate(_,cells):
            c=cells['R196'];c.set('t','inlineStr')
            for child in list(c):c.remove(child)
            ET.SubElement(ET.SubElement(c,'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is'),
                '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t').text='ND'
        raw=edit_workbook(mutate);grid['source_kind']='synthetic_fixture'
    store=Store(path);manifest=path/'empty-manifest.json';manifest.write_text(json.dumps({'schema_version':1,'entries':[]}));store.create_problem(manifest_path=manifest)
    def put(content,provider,parents=None):
        artifact=store.artifact(content)
        return store.put('source',{'provider':provider,'accession':None,'uri':None,'artifact_ref':artifact,
            'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None,
            **({'parent_source_refs':parents} if parents else {})},origin='caller')['id']
    article=put(docs[0]['content'],'retained_original_225_article')
    source=put(raw,'synthetic_grid231' if nondetection else 'retained_original_225_xlsx',[article])
    original_source=grid['source_ref'];original_context=docs[0]['source_ref']
    def replace_refs(v):
        if isinstance(v,dict):return {k:replace_refs(c) for k,c in v.items()}
        if isinstance(v,list):return [replace_refs(c) for c in v]
        return source if v==original_source else article if v==original_context else v
    grid=replace_refs(grid)
    assignment={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':[source,article],GRID_REQUESTED:deepcopy(selectors)}
    ctx=BindingContext('curve231','child231','literature',(('literature','child231'),),store.validate_scope(),assignment,{},(source,article))
    args={'version':GRID_POPULATION,'grid':grid,'calculation':{'version':'a105_reported_curve_precision_request_v1',
        'fit_model':'unweighted_positive_km_mm','requested_components':deepcopy(selectors)}}
    return store,ctx,args,source,article
