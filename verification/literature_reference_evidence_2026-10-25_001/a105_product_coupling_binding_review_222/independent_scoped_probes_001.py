"""Root synthetic coordinate-vs-value and scientific-name projection checks."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import os
import sys

BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_003'
ROOT=Path('/home/chia/repos/gene_annotation_episode')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
from test_literature_product_coupling_binding_218 import Source, setup, populated
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt

text='Reaction coefficient 37 cofactor per product. Separate temperature 37 C. Product 5-exo-hydroxycamphor; SEM3uM.'
fixture=Source(content=Source().content+('<p>'+text+'</p>').encode())
store,ctx,args=setup(BASE/'independent_store_001',source_fixture=fixture,
    requested=['reported_cofactor_activity'])
with store:
    def witness(token):
        start=fixture.content.index(token.encode())
        return {'source_ref':args['source_ref'],'representation':'original','start':start,
            'end':start+len(token.encode()),'quote':token}
    model=witness('Reaction coefficient 37 cofactor per product')
    args['nu_cofactor_per_product'].update(exact_value={'numerator':'37','denominator':'1'},witnesses=[model])
    args['context']['experiment']=model
    args['context']['cofactor_conditions']=witness('37 C')
    args['context']['product']=witness('5-exo-hydroxycamphor')
    args['context']['product_identity_method']=witness('Product 5-exo-hydroxycamphor; SEM3uM')
    repo,out,current=populated(store,ctx,args)
    row,=out['result']['cells']; means=row['source_meanings']
    assert row['reaction_account'] is None
    assert '37' not in means['experiment']['display_text']
    assert means['cofactor_conditions']['display_text']=='37 C'
    assert means['cofactor_conditions']['status']=='selected'
    assert means['product']['display_text']=='5-exo-hydroxycamphor'
    assert '5-exo-hydroxycamphor' in means['product_identity_method']['display_text']
    assert '3uM' not in means['product_identity_method']['display_text']
    assert means['product_identity_method']['status']=='numerical_scope_unresolved'
    assert row['source_value']==4 and row['value']==4
    saved=repo.read(out['result']['sheet_ref'])
    assert saved['extraction']['context']['product_identity_method']['value']=='Product 5-exo-hydroxycamphor; SEM3uM'
    assert repo.fact_cells(current,out['record_refs'],components=['reported_cofactor_activity'])==[row]
    task,steering=render_literature_experimental_prompt({'literature_experimental_work':{'version':'literature_experimental_task_v1'},
        'child_reports':[{'numbers':[row]}]},'Evaluate the requested cofactor report.').split('\n\nSTEERING\n',1)
    assert '5-exo-hydroxycamphor' in steering and '37 C' in steering and 'SEM3uM' not in steering
    assert 'Reaction coefficient 37' not in steering and 'product_coupling_projection_v2' not in task+steering
    result={'scope':'Explicitly synthetic selected storage/fact/text checks; no actual paper, model or episode execution.',
        'same_number_different_coordinates_keeps_true_condition':True,
        'unrequested_model_coefficient_withheld':True,
        'chemical_locant_retained_with_attached_statistic_withheld':True,
        'source_native_requested_value_and_full_original_source_retained':True,
        'text_and_exact_fact_projection_agree':True}
hashes=json.loads((BASE/'PIN_003.json').read_text())['hashes']
changed=[p for p,h in hashes.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
outside={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))
    and not Path(m.__file__).resolve().is_relative_to(PIN)}
assert not changed and not outside
result.update(imports_outside_pin=outside,changed_pinned_files=changed)
with (BASE/'ROOT_SCOPED_PROBES_001.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
