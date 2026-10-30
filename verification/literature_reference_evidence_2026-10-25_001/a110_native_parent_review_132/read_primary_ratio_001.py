"""Root source-token verification for one reported CsiD product ratio.

No raw spectrum integration, modeled precision, new scientific record or
annotation credit. Scientist nominates the reported expression and meanings;
existing deterministic reader/calculator perform token parsing and arithmetic.
"""
from pathlib import Path
import hashlib,json
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_reaction_native_inputs import read_native_reaction_selection,VERSION
from gene_annotation_episode.literature_reaction_calculations import populate_reaction_constraints
BASE=Path(__file__).resolve().parent
raw=(BASE/'ROOT_SUPPLEMENT_TEXT_001.txt').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='330a23b72195341a36493a68b238b246a0b491f5a6d90c382f89eb5a09e692a1'
quote='succinic acid : L-2-hydroxyglutarate = 1:1'
i=raw.index(quote.encode())
w=dict(source_ref='source_csid_supplement_text',representation='original',start=i,end=i+len(quote.encode()),quote=quote)
start=quote.index('1:1')
selector=lambda offset:dict(witness=w,number_start=start+offset,number_end=start+offset+1)
model=dict(definition=w,reaction=None,function_relation=None,prediction_evidence=w,prediction_basis='source_supported_inference')
recipe={'version':VERSION,'ratio':{'mode':'source_summary','ratio_kind':'product_pair','unit':'mol_per_mol',
 'measurement_basis':'source_supported_molar_ratio','basis_witnesses':[w],'observations':[],
 'summary':{'value':{'kind':'reported_pair','numerator':selector(0),'denominator':selector(2)},
  'uncertainty':{'kind':'unreported','number':None,'basis_witnesses':[]},
  'count':{'number':None,'basis':'unknown','basis_witnesses':[]}},
 'claim':{'kind':'declared','value':1,'basis':'source_supported_inference','evidence':[w]},'alternatives':[]},
 'budget':None,'meanings':{'ratio':{'claim':model,'alternatives':[]},'budget':None}}
sources=_Sources(lambda ref,representation: {'artifact_ref':'artifact_'+hashlib.sha256(raw).hexdigest(),'content':raw})
normalized,trace=read_native_reaction_selection(recipe,sources=sources)
sheet=populate_reaction_constraints({k:normalized[k] for k in ['ratio','budget']})
assert sheet['cells']['ratio_mean']['value']==1
assert sheet['cells']['claim_nominal_squared_error']['value']==0
assert sheet['cells']['claim_mean_squared_error']['value'] is None
assert sheet['cells']['reaction_comparison']['value'] is None
assert sheet['cells']['reaction_comparison_lower']['value']==-1
assert sheet['cells']['reaction_comparison_upper']['value']==1
for name,value in [('PRIMARY_RATIO_RECIPE_001.json',recipe),('PRIMARY_RATIO_TRACE_001.json',trace),('PRIMARY_RATIO_SHEET_001.json',sheet)]:
 (BASE/name).write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'source':'Original supplementPDF independently text-extracted; exact reported ratio-token selection','ratio_mean':1,'claim_nominal_squared_error':0,'full_mean_squared_error':None,'alternative_comparison':None,'comparison_logical_bounds':[-1,1],'model_prediction_basis':'source-supported interpretation, not independent measurement','limits':'No rawNMRintegration/calibration, ratioSD/n, productiveoxygen coupling or targetcredit inferred.'},indent=2))
