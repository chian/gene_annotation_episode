"""Controlled source nominations and current pure ion-discrimination application.

No episode binding/model call/graph digitization/GHK inversion is performed.
All original-source uncertainty, normalization and attribution gaps remain.
"""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_literature_ion_discrimination_components_194 import original_source,original_common,source_quantity,calculate,w,SOURCE,setup,covariance


def applications():
    text,raw=original_source();cases={}
    args=original_common(text);args['source_kind']='primary_source'
    discussion=text.index('Anion-efflux assays measure');F=text.index('30,000',discussion);Cl=text.index('30 ions/s',discussion)
    preferred=source_quantity(text,'30,000','s<sup>−1</sup>',approx=True,scope='paper_summary_unresolved',at=F)
    alternative=source_quantity(text,'30','ions/s',scope='paper_summary_unresolved',at=Cl)
    alternative['derivation']={'value':'unknown','witnesses':[]}
    result_start=text.index('<p>Purified Fluc proteins are functional');result_end=text.index('channel.<fig',result_start)+len('channel.')
    results_witness=w(text,text[result_start:result_end])
    preferred['qualification']={'value':'source_qualified_approximate','witnesses':[results_witness]}
    preferred['derivation']={'value':'author_inferred_dead_time_and_geometry','witnesses':[results_witness]}
    args.update(route='reported_threshold_pair',thresholds={'preferred':preferred,'alternative':alternative})
    cases['efflux_summary_thresholds']=(args,*calculate(args,[],{SOURCE:raw}))
    for name,token,meaning,derivation,scope in [('Ec2_biionic_reported_permeability','100','reported_permeability_ratio','author_inferred_electrical_model','specific_construct'),
        ('Fluc_author_summary','10<sup>4</sup>','reported_cross_assay_summary_ratio','author_summary_inference','paper_summary_unresolved')]:
        args=original_common(text);args['source_kind']='primary_source'
        at=text.index('lower limit of ∼100')+len('lower limit of ∼') if token=='100' else text.index(token,discussion)
        q=source_quantity(text,token,None,meaning=meaning,approx=token=='100',at=at,scope=scope)
        q['derivation']['value']=derivation
        args.update(route='reported_ratio',reported_ratio=q)
        cases[name]=(args,*calculate(args,[],{SOURCE:raw}))
    return cases


def main():
    output=HERE/'original_application_001';output.mkdir(exist_ok=False)
    cases=applications();summary={}
    for name,(selection,extraction,sheet) in cases.items():
        with (output/(name+'.json')).open('x') as f:json.dump({'selection':selection,'extraction':extraction,'sheet':sheet},f,indent=2);f.write('\n')
        selected=['preferred_activity','alternative_activity','nominal_threshold_ratio'] if name=='efflux_summary_thresholds' else ['reported_selectivity']
        summary[name]={key:{field:sheet['cells'][key][field] for field in ('value','threshold','unit','relation','origin','derivation','quantity_kind','approximation','source_qualifications','nominal_domain','reported_domain','physical_domain','zero_denominator_case','unavailable_reasons')} for key in selected}
    args,rows,sources=setup();args,sources,_=covariance(args,rows,sources,[[.0081,.000675],[.000675,.000225]])
    _,synthetic=calculate(args,rows,sources)
    with (output/'synthetic_point_covariance.json').open('x') as f:json.dump(synthetic,f,indent=2);f.write('\n')
    summary['synthetic_point_example']={key:synthetic['cells'][key]['value'] for key in ('activity_ratio','log_activity_ratio','activity_ratio_variance','activity_ratio_standard_uncertainty','log_activity_ratio_standard_uncertainty')}
    summary['scope']='Controlled original-source nominations/pure functions and separately synthetic statistics; no actual model/selected episode/storage/reconstruction or A105 adequacy proof.'
    with (HERE/'ORIGINAL_APPLICATION_SUMMARY_001.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
    print(json.dumps({'original_source_cases':list(cases),'summary_path':str(HERE/'ORIGINAL_APPLICATION_SUMMARY_001.json'),'source_scientific_unknowns_preserved':True}))


if __name__=='__main__':main()
