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


# Versioned reported-curve grid section; legacy complete v1 prefix is unchanged.
GRID_SHEET_VERSION = 'a105_reported_curve_precision_v1'
GRID_SOLVER_VERSION = 'dimensionless_profile_stationarity_log2_32_v1'
GRID_REASONS = ('incomplete_selected_roster', 'no_point_observations', 'insufficient_entry_count',
    'nonpositive_mean', 'numerical_model_range', 'model_not_selected', 'concentration_unit_unknown',
    'positive_concentrations_required', 'insufficient_distinct_concentrations',
    'fit_nonpositive_response', 'fit_domain_exhausted', 'fit_solution_unresolved',
    'fit_nonidentifiable', 'fit_solver_failed', 'sampling_model_unknown', 'sampling_model_conflicting',
    'not_applicable_to_estimator', 'zero_covariance_variance', 'source_measurement_unavailable',
    'nondetection_without_point', 'censored_measurement', 'formula_measurement_unsupported',
    'numeric_cell_type_required', 'source_cell_error', 'source_error_cell', 'invalid_numeric_lexeme')
_GRID_POINT_COMPONENTS = ('mean', 'sample_variance', 'sample_sd', 'cv', 'available_point_mean',
    'available_point_variance', 'available_point_sd', 'available_point_cv', 'selected_entry_count', 'available_point_count')
_GRID_ESTIMATORS = ('mean_of_reported_curve_fits', 'fit_of_point_means')


def reported_curve_precision_selector_schema():
    from .domain import obj
    from .literature_rate_observation_inputs import CELL
    def choices(values): return {'enum': list(values)}
    fields = [
        obj({'scope': {'const': 'point'}, 'concentration_cell': CELL, 'component': choices(_GRID_POINT_COMPONENTS)}),
        obj({'scope': {'const': 'curve'}, 'curve_header_cell': CELL, 'component': choices(
            ('Vmax', 'Km', 'SSE', 'stationarity_error', 'selected_point_count', 'available_point_count'))}),
        obj({'scope': {'const': 'estimator'}, 'estimator': choices(_GRID_ESTIMATORS), 'component': choices(
            ('Vmax', 'Km', 'native_efficiency', 'SSE', 'log_efficiency_variance',
             'log_efficiency_standard_uncertainty', 'diagonal_only_log_efficiency_variance'))}),
        obj({'scope': {'const': 'reported_curve_covariance'}, 'left_concentration_cell': CELL,
            'right_concentration_cell': CELL, 'component': choices(('sample_covariance', 'conditional_mean_curve_covariance'))}),
        obj({'scope': {'const': 'parameter_covariance'}, 'estimator': choices(('reported_curve_fit_distribution', *_GRID_ESTIMATORS)),
            'left_parameter': choices(('Vmax', 'Km')), 'right_parameter': choices(('Vmax', 'Km')),
            'component': choices(('covariance', 'correlation'))}),
        obj({'scope': {'const': 'sensitivity'}, 'estimator': {'const': 'fit_of_point_means'},
            'parameter': choices(('Vmax', 'Km')), 'concentration_cell': CELL,
            'component': {'const': 'd_parameter_d_point_mean'}}),
        obj({'scope': {'const': 'variance_term'}, 'estimator': choices(_GRID_ESTIMATORS),
            'left_parameter': choices(('Vmax', 'Km')), 'right_parameter': choices(('Vmax', 'Km')),
            'component': {'const': 'signed_log_efficiency_variance_term'}}),
        obj({'scope': {'const': 'grid'}, 'component': choices(('all_reported_residual_SS',
            'within_concentration_reported_entry_SS', 'mean_curve_fit_residual_SS_times_curve_count',
            'reported_curve_count', 'complete_curve_count'))})]
    return {'anyOf': fields}


def reported_curve_precision_request_schema():
    from .domain import obj
    return obj({'version': {'const': 'a105_reported_curve_precision_request_v1'},
        'fit_model': {'enum': ['none', 'unweighted_positive_km_mm']},
        'requested_components': {'type': 'array', 'uniqueItems': True,
                                 'items': reported_curve_precision_selector_schema()}})


def _grid_formula(selector):
    scope, component = selector['scope'], selector['component']
    formulas = {
        'mean': 'sum(selected_distinct_points)/n', 'sample_variance': 'sum((y-mean)^2)/(n-1)',
        'sample_sd': 'sqrt(sample_variance)', 'cv': 'sample_sd/positive_mean',
        'available_point_mean': 'sum(available_distinct_points)/n_available',
        'available_point_variance': 'sum((available_y-available_mean)^2)/(n_available-1)',
        'available_point_sd': 'sqrt(available_point_variance)', 'available_point_cv': 'available_point_sd/positive_available_mean',
        'selected_entry_count': 'count(distinct_selected_source_cells)', 'available_point_count': 'count(observed_distinct_source_cells)',
        'selected_point_count': 'count(selected_concentration_rows)', 'reported_curve_count': 'count(distinct_reporting_headers)',
        'complete_curve_count': 'count(complete_selected_reporting_columns)',
        'sample_covariance': 'sum((curve_i-mean_i)*(curve_j-mean_j))/(n_curves-1)',
        'conditional_mean_curve_covariance': 'sample_curve_covariance/n_curves',
        'native_efficiency': 'selected_estimator_Vmax/selected_estimator_Km',
        'log_efficiency_variance': 'sum_ab(g_a*C_ab*g_b)',
        'log_efficiency_standard_uncertainty': 'sqrt(sum_ab(g_a*C_ab*g_b))',
        'diagonal_only_log_efficiency_variance': 'sum_a(g_a*C_aa*g_a)',
        'signed_log_efficiency_variance_term': 'g_left*C_left_right*g_right',
        'd_parameter_d_point_mean': '(JtJ-sum(residual*model_Hessian))^-1*Jt',
        'all_reported_residual_SS': 'sum_all_reported_cells((y-fitted_mean_curve)^2)',
        'within_concentration_reported_entry_SS': 'sum_all_reported_cells((y-point_mean)^2)',
        'mean_curve_fit_residual_SS_times_curve_count': 'n_curves*point_mean_fit_SSE',
        'stationarity_error': 'dimensionless_profile_stationarity_absolute_residual',
        'correlation': 'C_left_right/sqrt(C_left_left*C_right_right)'}
    if component in ('Vmax', 'Km', 'SSE'):
        return ('mean_of_complete_reporting_curve_parameter_vectors' if selector.get('estimator') == 'mean_of_reported_curve_fits'
                else 'unweighted_positive_Km_profile_MM_least_squares') + ':' + component
    if component == 'covariance':
        return {'reported_curve_fit_distribution': 'sum((theta_j-theta_mean)*(theta_j-theta_mean)t)/(n-1)',
                'mean_of_reported_curve_fits': 'sample_covariance_of_fitted_vectors/n',
                'fit_of_point_means': 'A*(full_sample_curve_covariance/n)*At'}[selector['estimator']]
    return formulas[component]


def reported_curve_precision_sheet_schema():
    from .domain import obj
    from .literature_rate_observation_inputs import (_grid_array, _grid_nullable,
        _grid_exact_schema, reported_rate_grid_extraction_schema, TEXT)
    array = _grid_array; nullable = _grid_nullable
    cell = obj({'selector': reported_curve_precision_selector_schema(), 'cell_key': TEXT,
        'value': {'type': ['number', 'null']}, 'exact_value': nullable(_grid_exact_schema()),
        'conditional_value': {'type': ['number', 'null']}, 'conditional_exact_value': nullable(_grid_exact_schema()),
        'unit': TEXT, 'formula_id': TEXT, 'meaning_id': TEXT,
        'numeric_basis': {'enum':['source_decimal_arithmetic','canonical_numeric_fit_operands_not_exact_fits']},
        'status': {'enum': ['populated', 'conditional_scenario', 'unavailable']},
        **{name: array({'enum': list(GRID_REASONS)}) for name in
            ('source_missing_reasons', 'relationship_reasons', 'implementation_reasons')},
        'input_measurement_keys': array(TEXT), 'input_origins': array({'enum': ['reported', 'synthetic']}),
        'estimator_key': nullable(TEXT), 'model_keys': array(TEXT), 'contribution_key': TEXT,
        'variance_status': {'enum': ['not_applicable', 'estimated', 'unknown']},
        'count_basis': {'const': 'distinct_reported_cells_and_columns_not_physical_preparations'},
        'scope': {'enum': ['full_selected_roster', 'available_points', 'not_applicable']}})
    diagnostics = obj({'label': TEXT, 'reason': {'enum': [*GRID_REASONS, None]},
        'log2_Km_domain': {'const': [-32, 32]}, 'stationarity_error': {'type': ['number', 'null']},
        'curvature_determinant': {'type': ['number', 'null']}})
    return obj({'version': {'const': GRID_SHEET_VERSION}, 'axis': {'const': 'A105'},
        'evaluation_scope': {'const': 'reported_curve_precision'},
        'extraction': reported_rate_grid_extraction_schema(), 'request': reported_curve_precision_request_schema(),
        'cells': array(cell), 'calculation_metadata': obj({'solver_version': {'const': GRID_SOLVER_VERSION},
            'solver_scope': {'const': 'finite_numerical_domain_not_global_certification'},
            'diagnostics': array(diagnostics), 'sampling': deepcopy(reported_rate_grid_extraction_schema()['properties']['original_arguments']['properties']['curve_sampling']),
            'physical_preparation_count': {'type': 'null'}, 'published_estimate_covariance': {'type': 'null'}}),
        'remaining_implementation_limits': {'const': ['selected_typed_binding_unimplemented',
            'general_quality_compilation_unfinished', 'same_estimand_contradiction_compilation_unfinished',
            'no_target_correspondence_or_final_credit']}})


def _grid_fit(xs, ys):
    """Finite dimensionless profile fit; no biological bounds or global claim."""
    diag = {'log2_Km_domain': [-32, 32], 'stationarity_error': None, 'curvature_determinant': None}
    def failure(reason): return {'reason': reason, 'diagnostic': diag}
    if any(x <= 0 for x in xs): return failure('positive_concentrations_required')
    if len(xs) < 2 or len(set(xs)) < 2: return failure('insufficient_distinct_concentrations')
    if max(ys) <= 0: return failure('fit_nonpositive_response')
    xscale = sorted(xs)[len(xs)//2]; yscale = max(abs(y) for y in ys)
    try:
        x = [float(v/xscale) for v in xs]; y = [float(v/yscale) for v in ys]
        if any(not math.isfinite(v) or v == 0 for v in x) or any(not math.isfinite(v) for v in y):
            return failure('numerical_model_range')
        def profile(k):
            terms = [s/(k+s) for s in x]; d = math.fsum(t*t for t in terms)
            v = math.fsum(t*z for t,z in zip(terms,y))/d
            residual = [z-v*t for z,t in zip(y,terms)]
            return v, math.fsum(r*r for r in residual), math.fsum(r*s/(k+s)**2 for r,s in zip(residual,x))
        domain = [2.0**(-32+i/4) for i in range(257)]
        values = [profile(k) for k in domain]; candidates = []
        for i in range(len(domain)-1):
            if values[i][2] <= 0 <= values[i+1][2]:
                lo, hi = domain[i:i+2]
                for _ in range(80):
                    mid = (lo+hi)/2
                    if mid == lo or mid == hi: break
                    if profile(mid)[2] < 0: lo = mid
                    else: hi = mid
                k = (lo+hi)/2; v, sse, derivative = profile(k)
                if v > 0 and not any(abs(k-old[1]) <= 1e-10*k for old in candidates):
                    candidates.append((v,k,sse,derivative))
        if not candidates: return failure('fit_domain_exhausted')
        candidates.sort(key=lambda item: item[2]); v,k,sse,derivative = candidates[0]
        if min(values[0][1],values[-1][1]) <= sse + 1e-12*max(1,sse): return failure('fit_domain_exhausted')
        if len(candidates)>1 and abs(candidates[1][2]-sse)<=1e-11*max(1,sse): return failure('fit_solution_unresolved')
        residual = [z-v*s/(k+s) for z,s in zip(y,x)]
        jac = [[s/(k+s),-v*s/(k+s)**2] for s in x]
        h00 = math.fsum(j[0]*j[0] for j in jac)
        h01 = math.fsum(j[0]*j[1]+r*s/(k+s)**2 for j,r,s in zip(jac,residual,x))
        h11 = math.fsum(j[1]*j[1]-r*2*v*s/(k+s)**3 for j,r,s in zip(jac,residual,x))
        det = h00*h11-h01*h01
        diag.update(stationarity_error=abs(derivative),curvature_determinant=det)
        if det<=1e-14*max(abs(h00*h11),abs(h01*h01)) or h00<=0 or h11<=0:
            return failure('fit_nonidentifiable')
        if abs(derivative)>1e-9: return failure('fit_solver_failed')
        inv = [[h11/det,-h01/det],[-h01/det,h00/det]]
        # Transform d(normalized theta)/d(normalized y) back to native operands.
        scales = [float(yscale),float(xscale)]; yfloat=float(yscale)
        sensitivity = [[math.fsum(inv[a][b]*j[b] for b in range(2))*scales[a]/yfloat for j in jac] for a in range(2)]
        theta = [v*scales[0],k*scales[1]]
        result_sse_q=Fraction(str(sse))*Fraction(str(scales[0]))**2
        result_sse=float(result_sse_q)
        if result_sse==0 and result_sse_q!=0:return failure('numerical_model_range')
        if any(not math.isfinite(z) for z in [*theta,result_sse,*[q for row in sensitivity for q in row]]) or any(z<=0 for z in theta):
            return failure('numerical_model_range')
        return {'reason': None, 'theta': theta, 'SSE': result_sse, 'sensitivity': sensitivity, 'diagnostic': diag}
    except (ArithmeticError,ValueError): return failure('numerical_model_range')


def _grid_covariance(vectors):
    n=len(vectors)
    if n<2:return None
    means=[sum(values,Fraction())/n for values in zip(*vectors)]
    return [[sum(((row[i]-means[i])*(row[j]-means[j]) for row in vectors),Fraction())/(n-1)
             for j in range(len(means))] for i in range(len(means))]


def populate_reported_curve_precision(extraction, request):
    """Populate finite scalar precision components; no source IO or credit policy."""
    from .domain import validate_schema, identity
    from .literature_experimental_contracts import ExperimentalContractError
    from .literature_rate_observation_inputs import validate_reported_rate_grid_extraction, _grid_exact
    data=validate_reported_rate_grid_extraction(extraction); args=data['original_arguments']
    validate_schema(request,reported_curve_precision_request_schema()); request=deepcopy(request)
    points=data['points']; curves=data['curves']; n=len(curves)
    point_indices={p['concentration']['witness']['cell']:i for i,p in enumerate(points)}
    curve_indices={c['header']['cell']:i for i,c in enumerate(curves)}
    for selector in request['requested_components']:
        for field in ('concentration_cell','left_concentration_cell','right_concentration_cell'):
            if field in selector and selector[field] not in point_indices:
                raise ExperimentalContractError('grid_selected_point_required',field)
        if 'curve_header_cell' in selector and selector['curve_header_cell'] not in curve_indices:
            raise ExperimentalContractError('grid_selected_curve_required','curve_header_cell')
    def quantity(q):return _q(q['exact_value']) if q['status']=='observed' else None
    xs=[quantity(p['concentration']) for p in points]
    rows=[[quantity(e['quantity']) for e in p['entries']] for p in points]
    columns=list(map(list,zip(*rows))); complete=all(v is not None for row in rows for v in row)
    means=[sum(row,Fraction())/n if all(v is not None for v in row) else None for row in rows]
    source_cov=_grid_covariance(columns) if complete else None
    fit_reason=('model_not_selected' if request['fit_model']=='none' else
        'concentration_unit_unknown' if args['concentration_unit']['code']=='unknown' else
        'incomplete_selected_roster' if any(x is None for x in xs) else None)
    def fit(values):
        reason=fit_reason or ('incomplete_selected_roster' if any(v is None for v in values) else None)
        if reason:return {'reason':reason,'diagnostic':{'log2_Km_domain':[-32,32],'stationarity_error':None,'curvature_determinant':None}}
        return _grid_fit(xs,values)
    fits=[fit(col) for col in columns]; pooled=fit(means)
    parameter_reason=next((f['reason'] for f in fits if f['reason']),None)
    vectors=[f['theta'] for f in fits] if parameter_reason is None else None
    theta_mean=[sum((Fraction(str(v[i])) for v in vectors),Fraction())/n for i in range(2)] if vectors else None
    fitted_cov=_grid_covariance([[Fraction(str(v)) for v in row] for row in vectors]) if vectors else None
    sampling=args['curve_sampling']
    sampling_reason=('sampling_model_unknown' if sampling['status']=='unknown' else
        'sampling_model_conflicting' if sampling['status']=='conflicting' else None)
    model_key=identity('reported_grid_sampling_model',sampling)
    basis={'measurements':[p['concentration']['measurement_key'] for p in points]+[e['quantity']['measurement_key'] for p in points for e in p['entries']],
        'rate_unit':args['rate_unit']['code'],'concentration_unit':args['concentration_unit']['code'],
        'curves':[c['curve_key'] for c in curves],'solver':GRID_SOLVER_VERSION}
    def estimator_key(kind):return identity('reported_grid_estimator',{'basis':basis,'kind':kind})
    parameter_cov={}; sensitivities=None
    if fitted_cov is not None:parameter_cov['reported_curve_fit_distribution']=fitted_cov
    if fitted_cov is not None and sampling_reason is None:
        parameter_cov['mean_of_reported_curve_fits']=[[v/n for v in row] for row in fitted_cov]
    if pooled['reason'] is None:
        sensitivities=pooled['sensitivity']
        if source_cov is not None and sampling_reason is None:
            # Gram of centered observed-curve modes handles rank-deficient C_y.
            # Rational arithmetic on canonical floating sensitivity operands
            # avoids cross-stage overflow/underflow; A remains a numeric derivative,
            # not an exact algebraic estimator. Preserve that implementation basis.
            modes=[[sum((Fraction(str(sensitivities[a][i]))*(col[i]-means[i]) for i in range(len(points))),Fraction())
                    for a in range(2)] for col in columns] if n>=2 else []
            if modes:parameter_cov['fit_of_point_means']=[[sum((mode[a]*mode[b] for mode in modes),Fraction())/(n*(n-1)) for b in range(2)] for a in range(2)]
    unit=args['rate_unit']['code']; xunit=args['concentration_unit']['code']; cells=[]
    all_quantities=[p['concentration'] for p in points]+[e['quantity'] for p in points for e in p['entries']]
    def emit(selector,value,output_unit,reason=None,*,conditional=False,variance=False,quantities=None,estimator=None):
        exact=_grid_exact(value) if isinstance(value,Fraction) else None
        number=None
        if value is not None:
            try:
                number=float(value)
                if not math.isfinite(number) or number==0 and value!=0:raise ValueError()
            except (ArithmeticError,ValueError):number,reason=None,'numerical_model_range'
        why=[] if number is not None else [reason or 'numerical_model_range']
        qlist=all_quantities if quantities is None else quantities
        owners=list(dict.fromkeys(q['measurement_key'] for q in qlist))
        ek=None if estimator is None else estimator_key(estimator)
        mk=[model_key] if conditional else []
        dependency={'measurement_keys':owners,'estimator':ek,'models':mk}
        source_reasons=[r for r in why if r in ('no_point_observations','insufficient_entry_count','insufficient_distinct_concentrations')]
        relation_reasons=[r for r in why if r in ('nonpositive_mean','model_not_selected','concentration_unit_unknown',
            'positive_concentrations_required','fit_nonpositive_response','fit_nonidentifiable',
            'sampling_model_unknown','sampling_model_conflicting','not_applicable_to_estimator','zero_covariance_variance')]
        implementation=[r for r in why if r not in source_reasons+relation_reasons and r!='incomplete_selected_roster']
        if 'incomplete_selected_roster' in why:
            for q in qlist:
                code=q['unavailable_reason']
                if code is None:continue
                target=implementation if code in ('formula_measurement_unsupported','numeric_cell_type_required','invalid_numeric_lexeme') else source_reasons
                if code not in target:target.append(code)
            if not source_reasons and not implementation:source_reasons.append('incomplete_selected_roster')
        cells.append({'selector':deepcopy(selector),'cell_key':identity('reported_grid_cell',{'selector':selector,'unit':output_unit,**dependency}),
            'value':number if not conditional else None,'exact_value':exact if number is not None and not conditional else None,
            'conditional_value':number if conditional else None,'conditional_exact_value':exact if number is not None and conditional else None,
            'unit':output_unit,'formula_id':_grid_formula(selector),'meaning_id':selector['scope']+':'+selector['component'],
            'numeric_basis':'canonical_numeric_fit_operands_not_exact_fits' if estimator is not None or selector['component'] in ('all_reported_residual_SS','mean_curve_fit_residual_SS_times_curve_count') else 'source_decimal_arithmetic',
            'status':'unavailable' if number is None else 'conditional_scenario' if conditional else 'populated',
            'source_missing_reasons':source_reasons,'relationship_reasons':relation_reasons,
            'implementation_reasons':implementation,
            'input_measurement_keys':owners,'input_origins':list(dict.fromkeys(q['origin'] for q in qlist)),
            'estimator_key':ek,'model_keys':mk,'contribution_key':identity('reported_grid_contribution',dependency),
            'variance_status':'estimated' if variance and number is not None else 'unknown' if variance else 'not_applicable',
            'count_basis':'distinct_reported_cells_and_columns_not_physical_preparations',
            'scope':'available_points' if selector['component'].startswith('available_point') else 'full_selected_roster'})
    def estimate(kind):
        return (theta_mean,parameter_reason) if kind=='mean_of_reported_curve_fits' else (pooled.get('theta'),pooled['reason'])
    for selected in request['requested_components']:
        scope=selected['scope']; component=selected['component']; value=None; reason=None; output_unit=unit
        conditional=False; variance=False; quantities=None; estimator=selected.get('estimator')
        if scope=='point':
            i=point_indices[selected['concentration_cell']]; row=rows[i]; available=[v for v in row if v is not None]
            if component in ('cv','available_point_cv'):output_unit='dimensionless'
            if component in ('sample_variance','available_point_variance'):output_unit=unit+'^2';variance=True
            quantities=[e['quantity'] for e in points[i]['entries']]
            if component.endswith('count'):value=len(available) if component=='available_point_count' else len(row);output_unit='count'
            else:
                partial=component.startswith('available_point'); key=component.replace('available_point_','')
                key='sample_variance' if key=='variance' else 'sample_sd' if key=='sd' else key
                reason='incomplete_selected_roster' if not partial and len(available)!=len(row) else None
                if not available:reason=reason or 'no_point_observations'
                if not reason:
                    mean=sum(available,Fraction())/len(available)
                    if key=='mean':value=mean
                    elif len(available)<2:reason='insufficient_entry_count'
                    else:
                        var=sum(((v-mean)**2 for v in available),Fraction())/(len(available)-1)
                        if key=='sample_variance':value=var;output_unit=unit+'^2';variance=True
                        elif key=='sample_sd':
                            with localcontext() as ctx:
                                ctx.prec=60;value=(Decimal(var.numerator)/Decimal(var.denominator)).sqrt()
                        elif mean<=0:reason='nonpositive_mean';output_unit='dimensionless'
                        else:
                            with localcontext() as ctx:
                                ctx.prec=60;value=(Decimal(var.numerator)/Decimal(var.denominator)).sqrt()/(Decimal(mean.numerator)/Decimal(mean.denominator))
                            output_unit='dimensionless'
        elif scope=='curve':
            j=curve_indices[selected['curve_header_cell']]; f=fits[j]; estimator='reported_curve:'+curves[j]['curve_key']
            quantities=[p['concentration'] for p in points]+[p['entries'][j]['quantity'] for p in points]
            if component.endswith('count'):value=len(points) if component=='selected_point_count' else sum(v is not None for v in columns[j]);output_unit='count'
            else:
                reason=f['reason'];value=None if reason else f['theta'][0 if component=='Vmax' else 1] if component in ('Vmax','Km') else f['SSE'] if component=='SSE' else f['diagnostic']['stationarity_error']
                output_unit=xunit if component=='Km' else unit+'^2' if component=='SSE' else 'dimensionless' if component=='stationarity_error' else unit
        elif scope=='reported_curve_covariance':
            i=point_indices[selected['left_concentration_cell']]; j=point_indices[selected['right_concentration_cell']]
            quantities=[points[k]['entries'][c]['quantity'] for k in dict.fromkeys((i,j)) for c in range(n)]
            pair_vectors=[[row[i],row[j]] for row in columns]
            covariance=_grid_covariance(pair_vectors) if all(v is not None for row in pair_vectors for v in row) else None
            reason='incomplete_selected_roster' if any(v is None for row in pair_vectors for v in row) else 'insufficient_entry_count' if covariance is None else None
            value=None if covariance is None else covariance[0][1];output_unit=unit+'^2';variance=True
            conditional=component=='conditional_mean_curve_covariance'
            if conditional:reason=reason or sampling_reason;value=None if reason else value/n
        elif scope in ('parameter_covariance','variance_term'):
            kind=estimator; theta,fit_why=estimate('mean_of_reported_curve_fits' if kind=='reported_curve_fit_distribution' else kind)
            matrix=parameter_cov.get(kind);reason=fit_why
            conditional=kind!='reported_curve_fit_distribution';variance=True
            if conditional:reason=reason or sampling_reason
            reason=reason or ('insufficient_entry_count' if n<2 else None)
            a=('Vmax','Km').index(selected['left_parameter']);b=('Vmax','Km').index(selected['right_parameter'])
            if matrix is not None and reason is None:
                value=matrix[a][b]
                if scope=='variance_term':value=value*[1/Fraction(str(theta[0])),-1/Fraction(str(theta[1]))][a]*[1/Fraction(str(theta[0])),-1/Fraction(str(theta[1]))][b]
                elif component=='correlation':
                    with localcontext() as ctx:
                        ctx.prec=60
                        def dec(q):
                            q=Fraction(q);return Decimal(q.numerator)/Decimal(q.denominator)
                        denominator=(dec(matrix[a][a])*dec(matrix[b][b])).sqrt()
                        value=dec(value)/denominator if denominator>0 else None
                    if value is None:reason='zero_covariance_variance'
            if matrix is None and reason is None:reason='fit_solver_failed'
            output_unit='dimensionless' if component=='correlation' or scope=='variance_term' else (unit if a==0 else xunit)+'*'+(unit if b==0 else xunit)
        elif scope=='sensitivity':
            reason=pooled['reason'];i=point_indices[selected['concentration_cell']];a=('Vmax','Km').index(selected['parameter'])
            value=None if reason else sensitivities[a][i];output_unit=(unit if a==0 else xunit)+'/'+unit
        elif scope=='estimator':
            theta,reason=estimate(estimator)
            if component in ('Vmax','Km','native_efficiency'):
                value=None if reason else theta[0] if component=='Vmax' else theta[1] if component=='Km' else Fraction(str(theta[0]))/Fraction(str(theta[1]))
                output_unit=xunit if component=='Km' else unit+'/'+xunit if component=='native_efficiency' else unit
            elif component=='SSE':
                reason=reason or ('not_applicable_to_estimator' if estimator=='mean_of_reported_curve_fits' else None)
                value=None if reason else pooled['SSE'];output_unit=unit+'^2'
            else:
                conditional=True;variance=True;reason=reason or sampling_reason or ('insufficient_entry_count' if n<2 else None)
                matrix=parameter_cov.get(estimator);output_unit='dimensionless'
                if reason is None and matrix is not None:
                    g=[1/Fraction(str(theta[0])),-1/Fraction(str(theta[1]))]
                    terms=[[g[a]*matrix[a][b]*g[b] for b in range(2)] for a in range(2)]
                    value=sum((terms[a][a] for a in range(2)),Fraction()) if component=='diagonal_only_log_efficiency_variance' else sum((v for row in terms for v in row),Fraction())
                    if value<0:value=None;reason='numerical_model_range'
                    elif component=='log_efficiency_standard_uncertainty':
                        with localcontext() as ctx:
                            ctx.prec=60;value=(Decimal(value.numerator)/Decimal(value.denominator)).sqrt()
                elif reason is None:reason='fit_solver_failed'
        else:
            if component in ('reported_curve_count','complete_curve_count'):
                value=n if component=='reported_curve_count' else sum(all(v is not None for v in col) for col in columns);output_unit='count'
            else:
                reason=None if complete else 'incomplete_selected_roster';output_unit=unit+'^2'
                within=sum(((y-means[i])**2 for i,row in enumerate(rows) for y in row),Fraction()) if complete else None
                if component=='within_concentration_reported_entry_SS':value=within
                else:
                    reason=reason or pooled['reason']
                    value=None if reason else n*Fraction(str(pooled['SSE']))+(within if component=='all_reported_residual_SS' else 0)
        emit(selected,value,output_unit,reason,conditional=conditional,variance=variance,quantities=quantities,estimator=estimator)
    result={'version':GRID_SHEET_VERSION,'axis':'A105','evaluation_scope':'reported_curve_precision',
        'extraction':data,'request':request,'cells':cells,'calculation_metadata':{
            'solver_version':GRID_SOLVER_VERSION,'solver_scope':'finite_numerical_domain_not_global_certification',
            'diagnostics':[{'label':c['header']['cell'],'reason':f['reason'],**f['diagnostic']} for c,f in zip(curves,fits)]+
                [{'label':'fit_of_point_means','reason':pooled['reason'],**pooled['diagnostic']}],
            'sampling':deepcopy(sampling),'physical_preparation_count':None,'published_estimate_covariance':None},
        'remaining_implementation_limits':['selected_typed_binding_unimplemented','general_quality_compilation_unfinished',
            'same_estimand_contradiction_compilation_unfinished','no_target_correspondence_or_final_credit']}
    validate_schema(result,reported_curve_precision_sheet_schema());return result
