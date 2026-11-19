"""Pure, versioned A102 geometry and functional-contrast subscoring sheets.

The user-approved RMSD profile is an index of measured correspondence. It is
independent of a function hypothesis and is never a biochemical probability.
These functions perform arithmetic on supplied cells; they execute no tool,
select no investigation, read no source and update no Episode credit.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math


VERSION = 'a102_rmsd_2A_features_1A_v1'
NATIVE_SCHEMA = 'a102_native_alignment_v1'
GRADE_SCHEMA = 'a102_comparison_grade_v1'


class A102ScoringUnavailable(ValueError):
    def __init__(self, code, **detail):
        self.code, self.detail = code, detail
        super().__init__(code)


def require(condition, code, **detail):
    if not condition:
        raise A102ScoringUnavailable(code, **detail)


def number(value, name, *, low=0, high=None):
    require(type(value) in (int, float) and math.isfinite(value) and value >= low
        and (high is None or value <= high), 'a102_invalid_number', field=name)
    return value


def positive_int(value, name):
    require(type(value) is int and value > 0, 'a102_positive_integer_required', field=name)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()).hexdigest()


def geometry(distances, target_length, reference_length):
    """Apply symmetric extent exactly once to RMSD for these actual CA pairs."""
    positive_int(target_length, 'target_length')
    positive_int(reference_length, 'reference_length')
    require(isinstance(distances, list), 'a102_paired_distances_required')
    for value in distances:
        number(value, 'paired_distance_A')
    n = len(distances)
    require(n <= min(target_length, reference_length), 'a102_pair_count_exceeds_scope')
    rmsd = math.sqrt(math.fsum(value*value for value in distances)/n) if n else None
    coverage = 2*n/(target_length+reference_length)
    kernel = 1/(1+(rmsd/2)**2) if rmsd is not None else None
    return {'profile': VERSION, 'n_pairs': n, 'target_length': target_length,
        'reference_length': reference_length, 'target_coverage': n/target_length,
        'reference_coverage': n/reference_length, 'symmetric_coverage': coverage,
        'rmsd_A': rmsd, 'rmsd_kernel': kernel, 'global_scale_A': 2.0,
        'B': coverage*kernel if kernel is not None else 0.0,
        'status': 'measured' if n else 'no_paired_coordinates'}


def grade_comparison(native):
    require(isinstance(native, dict) and native.get('schema') == NATIVE_SCHEMA,
        'a102_native_alignment_schema_required')
    result = deepcopy(native)
    length = positive_int(native['supplied_length'], 'supplied_length')
    scope = native['target_scope']
    require(isinstance(scope, list) and len(scope)==2 and all(type(x) is int for x in scope)
        and 0<=scope[0]<scope[1]<=length, 'a102_invalid_target_scope')
    ref_length = positive_int(native['reference_length'], 'reference_length')
    q, r, distances = (native[key] for key in ('target_positions','reference_positions','distances_A'))
    require(all(isinstance(row, list) for row in (q,r,distances))
        and len(q)==len(r)==len(distances), 'a102_correspondence_population_conflict')
    require(all(type(x) is int and scope[0]<=x<scope[1] for x in q)
        and all(type(x) is int and 0<=x<ref_length for x in r)
        and len(set(q))==len(q) and len(set(r))==len(r), 'a102_noninjective_or_unmapped_correspondence')
    for name in ('target_ref','reference_ref','comparison_group','variant_ref'):
        require(type(native.get(name)) is str and bool(native[name]),
            'a102_comparison_identity_required', field=name)
    require(type(native.get('primary')) is bool, 'a102_explicit_primary_variant_required')
    require(native.get('atom_selection') == 'CA', 'a102_rmsd_atom_profile_unbound')
    require(native.get('target_model', {}).get('origin') in {'experimental','predicted','supplied_unknown'}
        and native.get('reference_model', {}).get('origin') in {'experimental','predicted','supplied_unknown'},
        'a102_model_origin_required')
    components = geometry(distances, scope[1]-scope[0], ref_length)
    if native.get('distance_rounding_bounds_A') is not None:
        bounds=native['distance_rounding_bounds_A']
        require(isinstance(bounds,list) and len(bounds)==len(distances),'a102_distance_rounding_bounds_conflict')
        for value in bounds:number(value,'distance_rounding_bound_A')
        low=geometry([max(0,d-e) for d,e in zip(distances,bounds,strict=True)],scope[1]-scope[0],ref_length)
        high=geometry([d+e for d,e in zip(distances,bounds,strict=True)],scope[1]-scope[0],ref_length)
        components.update(rmsd_rounding_interval_A=[low['rmsd_A'],high['rmsd_A']],
            B_rounding_interval=[high['B'],low['B']],
            precision_status='conditional_native_print_rounding_bound_only_not_model_uncertainty')
    same_file = (native.get('target_structure_sha256') == native.get('reference_structure_sha256')
        if native.get('target_structure_sha256') is not None else False)
    same_copy = same_file and native.get('target_selection') == native.get('reference_selection')
    same_coordinates = native.get('target_coordinate_sha256') is not None and native.get(
        'target_coordinate_sha256') == native.get('reference_coordinate_sha256')
    excluded = same_copy or same_coordinates
    result.update(schema=GRADE_SCHEMA, version=VERSION, components=components,
        eligible=not excluded, exclusion='self_structure_copy' if same_copy else 'self_coordinate_copy' if same_coordinates else None,
        interpretation='native_structural_correspondence_not_function_probability',
        function_specific={'status':'not_assessed','F':None,'E':None,
            'reason':'source_grounded_required_features_not_supplied'})
    result['native_input_sha256'] = digest(native)
    return result


def feature_sheet(grade, definition):
    """Consume grounded feature measurements; absence and unknown stay distinct."""
    require(grade.get('schema') == GRADE_SCHEMA, 'a102_comparison_grade_required')
    require(definition.get('comparison_ref') == grade['variant_ref'],
        'a102_feature_comparison_conflict')
    require(type(definition.get('function_ref')) is str and definition['function_ref'],
        'a102_function_identity_required')
    require(bool(definition.get('definition_source_refs')), 'a102_feature_definition_sources_required')
    features = definition['features']
    require(isinstance(features,list) and bool(features), 'a102_required_feature_set_missing')
    keys = [row['physical_feature_key'] for row in features]
    require(len(set(keys))==len(keys), 'a102_duplicate_physical_feature')
    cells, low, high = [], [], []
    for row in features:
        state = row['state']
        require(state in {'measured','established_absent','established_incompatible','unresolved'},
            'a102_invalid_feature_state')
        if state == 'unresolved':
            value, bound = None, [0.0,1.0]
            require(bool(row.get('missing_reason')), 'a102_feature_missing_reason_required')
        elif state in {'established_absent','established_incompatible'}:
            require(bool(row.get('witness_refs')), 'a102_absence_requires_witness')
            value, bound = 0.0, [0.0,0.0]
        else:
            require(bool(row.get('witness_refs')), 'a102_feature_measurement_requires_witness')
            require(row.get('transform_sha256') == grade.get('transform_sha256')
                and row.get('transform_sha256') is not None, 'a102_feature_scaffold_transform_conflict')
            distance = number(row['distance_A'], 'feature_distance_A')
            value = 1/(1+distance*distance)
            uncertainty = row.get('coordinate_bound_A')
            if uncertainty is None:
                bound = [value,value]
            else:
                uncertainty = number(uncertainty, 'coordinate_bound_A')
                require(bool(row.get('bound_witness_refs')), 'a102_coordinate_bound_requires_witness')
                bound = [1/(1+(distance+uncertainty)**2),
                    1/(1+max(0,distance-uncertainty)**2)]
        cells.append({**deepcopy(row),'kernel':value,'bounds':bound})
        low.append(bound[0]); high.append(bound[1])
    count = len(cells)
    nominal = math.fsum(row['kernel'] for row in cells)/count if all(row['kernel'] is not None for row in cells) else None
    bounds = [math.fsum(low)/count,math.fsum(high)/count]
    base = grade['components']['B']
    eligible=grade['eligible']
    return {'schema':'a102_feature_sheet_v1','version':VERSION,
        'function_ref':definition['function_ref'],'comparison_ref':grade['variant_ref'],
        'comparison_group':grade['comparison_group'],'primary':grade['primary'],'eligible':eligible,
        'definition_source_refs':deepcopy(definition['definition_source_refs']),
        'K':count,'features':cells,'feature_scale_A':1.0,'F':nominal,
        'E':None if nominal is None or not eligible else base*nominal,'F_bounds':bounds,
        'E_bounds':[base*x for x in bounds] if eligible else [0.0,1.0],
        'n_unresolved':sum(row['state']=='unresolved' for row in cells),
        'uncertainty_status':'conditional_on_supplied_bounds' if any(row.get('coordinate_bound_A') is not None for row in cells) else 'unreported'}


def contrast_panel(rows, *, function_ref, supporting_refs, opposing_refs,
                   contrast_witness_refs, scope_ref, profile=VERSION):
    require(profile == VERSION, 'a102_mixed_metric_profiles')
    by_ref = {row['comparison_ref']:row for row in rows}
    require(len(by_ref)==len(rows), 'a102_duplicate_panel_comparison')
    require(not (set(supporting_refs or []) & set(opposing_refs or [])),
        'a102_reference_support_and_opposition_conflict')
    selected_refs=set(supporting_refs or [])|set(opposing_refs or [])
    primary_groups={}
    for ref in selected_refs:
        require(ref in by_ref,'a102_panel_row_unavailable',comparison_ref=ref)
        row=by_ref[ref]
        require(row.get('eligible',True) and row.get('primary',True),'a102_panel_ineligible_or_nonprimary_comparison')
        group=row.get('comparison_group',ref)
        require(group not in primary_groups or primary_groups[group]==ref,
            'a102_panel_primary_variant_unresolved',comparison_group=group)
        primary_groups[group]=ref
    def pool(refs):
        if not refs:return None,[0.0,1.0]
        selected=[]
        for ref in set(refs):
            require(ref in by_ref,'a102_panel_row_unavailable',comparison_ref=ref)
            selected.append(by_ref[ref])
        value = max(row['E'] for row in selected) if all(row['E'] is not None for row in selected) else None
        return value,[max(row['E_bounds'][0] for row in selected),max(row['E_bounds'][1] for row in selected)]
    support,sb = pool(supporting_refs)
    opposition,ob = pool(opposing_refs)
    contrasted = bool(contrast_witness_refs) and bool(opposing_refs)
    value = max(0,support-opposition) if contrasted and support is not None and opposition is not None else None
    bounds = [max(0,sb[0]-ob[1]),max(0,sb[1]-ob[0])]
    return {'schema':'a102_contrast_sheet_v1','version':VERSION,'function_ref':function_ref,
        'scope_ref':scope_ref,'profile':profile,'supporting_refs':list(supporting_refs or []),
        'opposing_refs':list(opposing_refs or []),'contrast_witness_refs':list(contrast_witness_refs),
        'S':support,'O':opposition,'A102_f':value,'bounds':bounds,
        'status':'derived' if value is not None else 'support_only_or_unresolved_contrast'}


def compile_native_sheet(grades, *, target_ref, supplied_length, regions=None, evidence_regions=None):
    positive_int(supplied_length, 'supplied_length')
    regions = deepcopy(regions if regions is not None else [[0,supplied_length]])
    require(bool(regions), 'a102_required_scope_empty')
    for a,b in regions:
        require(type(a) is int and type(b) is int and 0<=a<b<=supplied_length,
            'a102_invalid_required_region')
    require(all(regions[i][1]<=regions[i+1][0] for i in range(len(regions)-1)),
        'a102_required_regions_overlap_or_unordered')
    groups, excluded = {}, []
    for grade in grades:
        require(grade.get('schema')==GRADE_SCHEMA and grade.get('version')==VERSION,
            'a102_expected_grader_unavailable')
        require(grade['target_ref']==target_ref and grade['supplied_length']==supplied_length,
            'a102_original_target_conflict')
        if not grade['eligible']:
            excluded.append({'comparison_ref':grade['variant_ref'],'reason':grade['exclusion']})
            continue
        group=groups.setdefault(grade['comparison_group'],{})
        old=group.get(grade['variant_ref'])
        require(old is None or old==grade,'a102_variant_identity_conflict')
        group[grade['variant_ref']]=grade
    selected=[]
    for group,variants in groups.items():
        primary=[row for row in variants.values() if row['primary']]
        require(len(primary)==1,'a102_primary_variant_unresolved',comparison_group=group,
            primary_count=len(primary))
        selected.extend(primary)
    values=[]
    for a,b in regions:
        comparisons=[]
        for row in selected:
            distances=[d for position,d in zip(row['target_positions'],row['distances_A'],strict=True)
                if a<=position<b and (evidence_regions is None or any(x <= position < y
                    for x,y in evidence_regions.get(row['variant_ref'], ())))]
            calculated=geometry(distances,b-a,row['reference_length'])
            comparisons.append({'comparison_ref':row['variant_ref'],**calculated})
        values.append({'start':a,'end':b,'value':max((row['B'] for row in comparisons),default=0.0),
            'comparisons':comparisons})
    components=[row['value'] for row in values]
    value=math.exp(math.fsum(math.log(x) for x in components)/len(components)) if all(components) else 0.0
    return {'schema':'a102_native_sheet_v1','version':VERSION,'axis':'A102','value':value,
        'profile':VERSION,'scope':regions,'regions':values,'excluded':excluded,
        'comparison_count':len(selected),'status':'derived' if selected else 'not_observed',
        'interpretation':'native_structural_correspondence_not_function_probability',
        'function_specific_index':{'value':None,'status':'not_assessed'},
        'full_target_index':{'value':None,'status':'not_assessed',
            'reason':'supplied_scope_does_not_establish_biological_completeness'}}
