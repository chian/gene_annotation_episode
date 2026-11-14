"""Reporting-level numerical cells, without preparation or sampling inference."""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

VERSION='a105_reported_rate_contrast_v1'
GROUP_COMPONENTS=('rate','sample_sd','cv','observed_point_mean','observed_point_sd')
COMPONENTS=('reference_rate','test_rate','rate_difference','retained_fraction','fractional_decrease',
    'reference_sample_sd','test_sample_sd','reference_cv','test_cv',
    'reference_observed_point_mean','test_observed_point_mean','reference_observed_point_sd','test_observed_point_sd')
REASONS=('numerical_model_range','insufficient_entry_count','no_point_observations','nonpositive_mean',
    'conflicting_reported_entry','source_entry_association_unresolved','incomplete_selected_roster','missing_reference_group','missing_test_group','zero_reference_rate')
FORMULAS={'rate':'sum(all_selected_distinct_entries)/selected_entry_count',
    'sample_sd':'sqrt(sum((entry-full_set_mean)^2)/(selected_entry_count-1))',
    'cv':'descriptive_sample_sd/full_set_mean',
    'observed_point_mean':'sum(available_distinct_point_entries)/point_entry_count',
    'observed_point_sd':'sqrt(sum((point-observed_point_mean)^2)/(point_entry_count-1))',
    'rate_difference':'reference_rate-test_rate','retained_fraction':'test_rate/reference_rate',
    'fractional_decrease':'1-test_rate/reference_rate'}
QUALIFICATIONS=('reported_convention_only','preparation_grouping_unknown','pairing_unknown',
    'physical_unit_conversion_unknown','method_binding_unknown','blank_binding_unknown',
    'calibration_binding_unknown','product_attribution_unknown','experimental_comparability_not_established')


def _q(exact):
    return Fraction(int(exact['numerator']),int(exact['denominator']))


def _cell(value,unit,formula,*,reason=None):
    exact=None
    if isinstance(value,Fraction):exact={'numerator':str(value.numerator),'denominator':str(value.denominator)}
    if value is not None:
        try:
            number=float(value)
            if not math.isfinite(number) or number==0 and value!=0:raise ValueError()
        except (ArithmeticError,ValueError):number,reason=None,'numerical_model_range'
    else:number=None
    return {'value':number,'unit':unit,'formula':formula,'origin':'derived',
        'status':'populated' if number is not None else 'unavailable',
        'unavailable_reason':reason,'source_exact_value':exact if number is not None else None}


def _statistics(values):
    if not values:return None,None,'no_point_observations','no_point_observations'
    mean=sum(values,Fraction())/len(values)
    if len(values)<2:return mean,None,None,'insufficient_entry_count'
    variance=sum(((v-mean)**2 for v in values),Fraction())/(len(values)-1)
    with localcontext() as ctx:
        ctx.prec=60
        sd=(Decimal(variance.numerator)/Decimal(variance.denominator)).sqrt()
    return mean,sd,None,None


def populate_rate_observation_contrast(extraction,*,reference_group,test_group):
    """Flat distinct reported-entry descriptors; no IID, SE or corrected rate.

    Incomplete rosters retain available-point descriptions but never silently
    substitute those points for the entire selected group. Identity conflicts
    exclude all conflicting representations from available-point summaries.
    """
    data=deepcopy(extraction)
    unit=data['meanings']['native_unit']['value']
    by_identity={}
    for entry in data['entries']:by_identity.setdefault(entry['record_identity'],[]).append(entry)
    conflicts=set()
    for key,entries in by_identity.items():
        signatures={(e['group'],e['status'],e['bound'],None if e['exact_value'] is None else _q(e['exact_value']),
            e['origin'],e['value_source']['value'] if e['status']!='observed' else None) for e in entries}
        if len(signatures)>1:conflicts.add(key)
    grouped={}
    for entry in data['entries']:grouped.setdefault(entry['group'],[]).append(entry)
    groups=[]
    for name,entries in grouped.items():
        unique={}
        for entry in entries:unique.setdefault(entry['record_identity'],entry)
        labels={}
        for key,e in unique.items():labels.setdefault(e['label'],set()).add(key)
        unresolved={key for keys in labels.values() if len(keys)>1 for key in keys}
        points=[_q(e['exact_value']) for key,e in unique.items() if key not in conflicts and key not in unresolved and e['status']=='observed']
        mean,sd,mr,sr=_statistics(points)
        complete=all(key not in conflicts and key not in unresolved and e['status']=='observed' for key,e in unique.items())
        reason=None if complete else 'conflicting_reported_entry' if any(key in conflicts for key in unique) else 'source_entry_association_unresolved' if unresolved else 'incomplete_selected_roster'
        cells={'observed_point_mean':_cell(mean,unit,FORMULAS['observed_point_mean'],reason=mr),
            'observed_point_sd':_cell(sd,unit,FORMULAS['observed_point_sd'],reason=sr),
            'rate':_cell(mean if complete else None,unit,FORMULAS['rate'],reason=reason or mr),
            'sample_sd':_cell(sd if complete else None,unit,FORMULAS['sample_sd'],reason=reason or sr)}
        cv_reason=reason or mr or sr or ('nonpositive_mean' if mean is not None and mean<=0 else None)
        with localcontext() as ctx:
            ctx.prec=60
            cv=sd/(Decimal(mean.numerator)/Decimal(mean.denominator)) if cv_reason is None else None
        cells['cv']=_cell(cv,'fraction',FORMULAS['cv'],reason=cv_reason)
        groups.append({'label':name,'entry_count':None if unresolved else len(unique),
            'selected_row_count':len(unique),'known_entry_count':len(set(unique)-unresolved),
            'association_unresolved':bool(unresolved),'representation_count':len(entries),
            'point_entry_count':len(points),'complete':complete,
            'observation_labels':[{'record_identity':key,'label':e['label'],'status':e['status'],
                'conflicting':key in conflicts,'association_unresolved':key in unresolved,'unavailable_reason':e['unavailable_reason'],
                'label_source':deepcopy(e['label_source']),'group_source':deepcopy(e['group_source'])} for key,e in unique.items()],
            'limitations':list(dict.fromkeys([*([reason] if reason else []),
                *(e['unavailable_reason'] for e in entries if e['unavailable_reason'] is not None)])),
            'cells':cells})
    selected={role:next((g for g in groups if g['label']==label),None)
        for role,label in (('reference',reference_group),('test',test_group))}
    a,b=selected.values()
    reason=('missing_reference_group' if a is None else 'missing_test_group' if b is None else
        a['cells']['rate']['unavailable_reason'] or b['cells']['rate']['unavailable_reason'])
    av=_q(a['cells']['rate']['source_exact_value']) if a and a['cells']['rate']['source_exact_value'] else None
    bv=_q(b['cells']['rate']['source_exact_value']) if b and b['cells']['rate']['source_exact_value'] else None
    cells={}
    for role,g in selected.items():
        for name in GROUP_COMPONENTS:
            cells[role+'_'+name]=deepcopy(g['cells'][name]) if g else _cell(None,
                'fraction' if name=='cv' else unit,FORMULAS[name],reason='missing_'+role+'_group')
    cells['rate_difference']=_cell(av-bv if reason is None else None,unit,FORMULAS['rate_difference'],reason=reason)
    ratio_reason=reason or ('zero_reference_rate' if av==0 else None)
    ratio=bv/av if ratio_reason is None else None
    cells['retained_fraction']=_cell(ratio,'fraction',FORMULAS['retained_fraction'],reason=ratio_reason)
    cells['fractional_decrease']=_cell(1-ratio if ratio is not None else None,'fraction',FORMULAS['fractional_decrease'],reason=ratio_reason)
    return {'version':VERSION,'axis':'A105','scope':'source_reported_entry_endpoint',
        'extraction':data,'groups':groups,'reference_group':reference_group,'test_group':test_group,
        'cells':cells,'qualifications':list(QUALIFICATIONS),'preparation_count':None,
        'between_preparation_sd':None,'mean_se':None,'difference_se':None,'corrected_activity':None,
        'annotation_credit':None,'assay_error_rate':None}
