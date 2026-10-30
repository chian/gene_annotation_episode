"""Engineering examples from the already independently reviewed frozen paper.

No scientific acquisition, model, selected operation, Store or credit is run.
The four numerical oracle inputs below are hand-transcribed Table 3 numbers,
separate from the selectors and production Fraction arithmetic.
"""
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('coupling212_examples',ROOT/'tests/test_literature_product_coupling_212.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def write(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def witnesses(node):
    if isinstance(node,dict):
        if set(node)=={'source_ref','representation','start','end','quote','artifact_ref'}:
            yield node
        else:
            for child in node.values():yield from witnesses(child)
    elif isinstance(node,list):
        for child in node:yield from witnesses(child)


oracles=[];proofs=[]
for index,(label,p,h,reported) in enumerate((('WT',206,289,71),('T252N',92,216,42),
        ('T252N_V253T',132,343,38),('T252A',0,427,0))):
    source,args,_=fixture.original(index);data,sheet=fixture.run(source,args)
    write('SOURCE_POPULATED_'+label+'_001.json',{'population_input':args,'sheet':sheet})
    checked=list(witnesses(data))
    assert all(source.content[w['start']:w['end']]==w['quote'].encode() for w in checked)
    unique={(w['artifact_ref'],w['start'],w['end']) for w in checked}
    proofs.append({'arm':label,'witness_occurrences':len(checked),'distinct_physical_spans':len(unique),
        'all_exact_source_bytes_match':True,'source_sha256':hashlib.sha256(source.content).hexdigest()})
    with localcontext() as context:
        context.prec=65
        rho=Decimal(p)/Decimal(h)
        discrepancy=Decimal(100)*rho-Decimal(reported)
    actual=sheet['cells']['product_per_cofactor']['value']
    assert actual is None if index==3 else abs(Decimal(str(actual))-rho)<Decimal('1e-15')
    oracles.append({'arm':label,'hand_transcribed_product':p,'hand_transcribed_nadh':h,
        'hand_transcribed_reported_percent':reported,
        'decimal_ratio_oracle':None if index==3 else str(rho),
        'decimal_display_difference_pp_oracle':None if index==3 else str(discrepancy),
        'native_zero_not_physical_point':index==3,
        'eta_interpretation':'unavailable_nondetection' if index==3 else 'conditional_on_matching_and_interpreted_nu1',
        'source_Table3_covariance':'not_supplied',
        'reconstruction_contribution_aliases_product':sheet['cells']['reconstructed_product_activity']['contribution_key']==
            sheet['cells']['reported_product_activity']['contribution_key']})

with localcontext() as context:
    context.prec=65
    product=Decimal(92)/Decimal(206)
    nadh=Decimal(216)/Decimal(289)
    relative_rho=(Decimal(92)/Decimal(216))/(Decimal(206)/Decimal(289))
    assert abs(product-nadh*relative_rho)<Decimal('1e-63')
write('SOURCE_NUMERICAL_ORACLES_001.json',{'scope':'Pure reader/calculator source-populated examples; no model/integration/credit run.',
    'arms':oracles,'mutant_WT_decomposition':{'product_ratio':str(product),'NADH_ratio':str(nadh),
        'relative_product_per_cofactor':str(relative_rho),'meaning':'Same operands; no independent evidence bonus.'},
    'nu_origin':'Interpreted reaction-account convention from source chemistry and the explicit Table 3 footnote NADH-minus-peroxide-minus-product balance; not a printed measured scalar and not fitted to coupling percent.',
    'figure_qualification':{'path':'../a105_identified_product_scoring_case_207/Fig4.jpg',
        'sha256':'1f6c3e7f8e5c0f63e10495aa0ab9fd5c9df0bc30e1598881c67fc98acde7d9bc',
        'previously_actually_viewed':True,'image_label':'T252N/V253N','text_table_label':'T252N/V253T',
        'no_silent_panel_assignment':True,'no_digitization':True,
        'reader_limit':'This text/XML/HTML component does not extract image-internal text.'}})
write('SOURCE_WITNESS_PROOF_001.json',{'source_packet_sha256':'7ca8c54df69f5591d410869e658ff47e31d34028088fec99a9a04829a979d8fb',
    'arms':proofs,'all_verified':True})
print(json.dumps({'examples':4,'source_witness_occurrences':sum(p['witness_occurrences'] for p in proofs),
    'source_witness_proof':True,'independent_decimal_oracles':True}))
