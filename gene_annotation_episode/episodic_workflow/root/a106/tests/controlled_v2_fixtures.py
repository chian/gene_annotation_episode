"""Exact original engineered source/pixel fixture; no model/native science claim."""
from copy import deepcopy as cp
import hashlib
import json
from pathlib import Path
import re
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_controlled_response_owner_calculations as owner
DESIGN = Path(__file__).parent / 'fixtures/retained_scientific_sources/controlled'
ROLES = shared.PRIMITIVE_ORDER
CASES = json.loads((DESIGN / 'CONSTRUCTED_SOURCE_CASES_001.json').read_text())

class Fixture:
    def __init__(self,index=0):
        self.case=CASES[index]
        self.args=cp(self.case['selection'])
        self.data={s['source_ref']:(s['content_utf8'].encode() if s['content_utf8'] is not None else
            (DESIGN/s['encoded_image_file']).read_bytes()) for s in json.loads((DESIGN/'CONSTRUCTED_SOURCE_ROSTER_001.json').read_text())}
        self.cov_ref=self.args['covariance']['source_ref']
        self.main_ref=self.args['source_ref']
        self.data[self.cov_ref]=self.case['source_covariance_text'].encode()
        self.doc=json.loads(self.case['source_covariance_text'])
        self.calls=[]

    def source(self,reference,representation):
        self.calls.append((reference,representation))
        raw=self.data[reference]
        return {'artifact_ref':'artifact_'+hashlib.sha256(raw).hexdigest(),'content':raw}

    def read(self):
        return reader.read_controlled_response_v2_inputs(self.args,read_source=self.source)

    def witness(self,quote,ref=None,tagged=True,start=0):
        ref=ref or self.main_ref
        at=self.data[ref].index(quote.encode(),start)
        w=dict(source_ref=ref,representation='original',start=at,end=at+len(quote.encode()),quote=quote)
        return dict(kind='text',**w) if tagged else w

    def interp(self,value,quote=None):
        return dict(value=value,witnesses=[] if quote is None else [self.witness(quote)])

    def number(self,quote,token):
        at=quote.index(token)
        return dict(witness=self.witness(quote,tagged=False),number_start=at,number_end=at+len(token))

    def append(self,text):
        self.data[self.main_ref]+=('<p>'+text+'</p>\n').encode()

    def covariance(self,mapping=None):
        self.data[self.cov_ref]=(json.dumps(self.doc,indent=2)+'\n').encode()
        labels=list(re.finditer(rb'"label":\s*("(?:[^"\\]|\\.)*")',self.data[self.cov_ref]))
        for role in ROLES:
            b=self.args['covariance']['bindings'][role]
            if mapping is not None:
                index=mapping[ROLES.index(role)]
                if index is None:
                    self.args['covariance']['bindings'][role]=None
                    continue
                if b is None:
                    b=dict(variable_index=index,label_witness=None,
                        owner_witness=cp(self.args['arms'][role]['physical_observation']['canonical_witness']),correspondence=None)
                    self.args['covariance']['bindings'][role]=b
                b['variable_index']=index
            if b is None:continue
            at,end=labels[b['variable_index']].span(1)
            b['label_witness']=dict(source_ref=self.cov_ref,representation='original',start=at,end=end,
                quote=self.data[self.cov_ref][at:end].decode())
            b['correspondence']=dict(value='same',witnesses=[dict(kind='text',**b['label_witness'])])
        for name in ('variance_status','model_kind'):
            self.args[name]=dict(value=self.doc[name],witnesses=[self.witness(json.dumps(self.doc[name]),self.cov_ref)])

    def text_measurement(self,role,text,token,unit='nmol/min'):
        self.append(text)
        self.args['arms'][role]['measurement']=dict(kind='source_literal',literal=dict(status='exact',
            candidates=[self.number(text,token)],fragments=[]),unit=self.witness(unit,tagged=False,start=self.data[self.main_ref].index(text.encode())) if unit else None)

    def roundtrip(self):
        before=cp(self.args)
        extraction=self.read()
        assert self.args==before
        Draft202012Validator(reader._extraction_schema()).validate(extraction)
        assert reader.validate_controlled_response_v2_extraction(self.args,extraction)==extraction
        return extraction,owner.populate_controlled_response_owner(extraction['calculation_inputs'])
