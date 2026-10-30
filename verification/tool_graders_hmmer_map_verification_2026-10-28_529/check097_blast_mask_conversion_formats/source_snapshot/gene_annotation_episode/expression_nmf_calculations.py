"""Independent numerical calculations from saved NMF operands.

X_hat=W@H; R=X_fit-X_hat; SSE=sum(R**2); RMSE=sqrt(SSE/(G*S));
MAE=sum(abs(R))/(G*S); relative residual=norm(R)/norm(X_fit).
L[k]=sum_g W[g,k]; normalized W=W/L; C[k,s]=L[k]*H[k,s];
fraction=C[k,s]/sum_j C[j,s]. Stable equivalent arithmetic preserves finite
ratios/norms even when a squared sum or unscaled loading sum overflows.
All quantities retain their own denominator and failure state. Units of SSE
are squared input units; R/norm/RMSE/MAE/C use fitted input units. Normalized
loadings and contribution fractions are dimensionless, with no probability or
uncertainty interpretation. Original W/H have fitted arbitrary scale.
"""
from copy import deepcopy
import math

from .expression_nmf_common import CALCULATION_SCHEMA, digest, finite, issue


def _safe(function, qualifications, field, **locator):
    try:
        value = function()
        if finite(value):
            return value
    except (OverflowError, ValueError, ZeroDivisionError):
        pass
    qualifications.append(issue('derived_numeric_overflow', 'calculation', field=field, **locator))
    return None


def _scaled_norm(values):
    scale = max((abs(v) for v in values), default=0.0)
    return scale, math.hypot(*(v / scale for v in values)) if scale else 0.0


def reconstruct_nmf(W, H, *, qualifications=None):
    q = [] if qualifications is None else qualifications
    return [[_safe(lambda: math.fsum(w * H[k][s] for k, w in enumerate(row)), q, 'reconstructed',
        gene_position=g, sample_position=s) for s in range(len(H[0]))] for g, row in enumerate(W)]


def residual_measurements(X, reconstructed, *, qualifications=None):
    q = [] if qualifications is None else qualifications
    G, S = len(X), len(X[0])
    R = [[X[g][s] - reconstructed[g][s] if reconstructed[g][s] is not None else None for s in range(S)] for g in range(G)]
    gene_sse = [_safe(lambda: math.fsum(v*v for v in row), q, 'gene_sse', gene_position=g)
        if all(v is not None for v in row) else None for g, row in enumerate(R)]
    sample_sse = [_safe(lambda: math.fsum(R[g][s]**2 for g in range(G)), q, 'sample_sse', sample_position=s)
        if all(R[g][s] is not None for g in range(G)) else None for s in range(S)]
    values = [v for row in R for v in row]
    original = [v for row in X for v in row]
    denominator_scale, denominator_norm = _scaled_norm(original)
    denominator = _safe(lambda: denominator_scale * denominator_norm, q, 'relative_frobenius_denominator')
    result = {'residuals': R, 'gene_sse': gene_sse, 'gene_observation_counts': [S] * G,
        'sample_sse': sample_sse, 'sample_observation_counts': [G] * S, 'sse': None, 'cell_count': G*S,
        'frobenius_residual': None, 'rmse': None, 'mae': None, 'relative_frobenius_residual': None,
        'relative_frobenius_denominator': denominator,
        'input_norm_scaled_representation': {'scale': denominator_scale, 'scaled_norm': denominator_norm}}
    if any(v is None for v in values):
        q.append(issue('residual_population_incomplete', 'calculation'))
        return result
    scale, norm = _scaled_norm(values)
    result.update(sse=_safe(lambda: math.fsum(v*v for v in values), q, 'sse'),
        frobenius_residual=_safe(lambda: scale * norm, q, 'frobenius_residual'),
        rmse=_safe(lambda: scale * (norm / math.sqrt(G*S)), q, 'rmse'),
        mae=_safe(lambda: math.fsum(abs(v)/(G*S) for v in values), q, 'mae'))
    if denominator_scale == 0:
        q.append(issue('zero_input_frobenius_denominator', 'calculation'))
    else:
        common = max(scale, denominator_scale)
        result['relative_frobenius_residual'] = _safe(
            lambda: ((scale/common)*norm) / ((denominator_scale/common)*denominator_norm), q, 'relative_frobenius_residual')
    return result


def component_measurements(W, H, *, qualifications=None):
    q = [] if qualifications is None else qualifications
    G, K, S = len(W), len(H), len(H[0])
    sums, scales, normalized_columns = [], [], []
    for k in range(K):
        values = [W[g][k] for g in range(G)]
        scale = max(values)
        scaled_sum = math.fsum(v/scale for v in values) if scale else 0.0
        sums.append(_safe(lambda: scale*scaled_sum, q, 'component_loading_sums', component_position=k))
        scales.append({'scale': scale, 'scaled_sum': scaled_sum})
        normalized_columns.append([(v/scale)/scaled_sum if scale else None for v in values])
        if scale == 0:
            q.append(issue('zero_component_loading_sum', 'calculation', component_position=k))
    contributions = [[_safe(lambda: math.fsum(W[g][k]*H[k][s] for g in range(G)), q,
        'sample_component_contributions', component_position=k, sample_position=s) for s in range(S)] for k in range(K)]
    denominators, fractions = [], [[None] * S for _ in range(K)]
    for s in range(S):
        values = [contributions[k][s] for k in range(K)]
        if any(v is None for v in values):
            denominators.append(None)
            continue
        denominators.append(_safe(lambda: math.fsum(values), q, 'sample_contribution_denominators', sample_position=s))
        scale = max(values)
        scaled_sum = math.fsum(v/scale for v in values) if scale else 0.0
        for k in range(K):
            fractions[k][s] = (values[k]/scale)/scaled_sum if scale else None
        if not scale:
            q.append(issue('zero_reconstructed_sample_denominator', 'calculation', sample_position=s))
    return {'component_loading_sums': sums, 'loading_sum_scaled_representations': scales,
        'normalized_gene_loadings': [[normalized_columns[k][g] for k in range(K)] for g in range(G)],
        'sample_component_contributions': contributions, 'sample_contribution_denominators': denominators,
        'sample_component_fractions': fractions}


def calculate_nmf_sheet(sheet: dict) -> dict:
    from .expression_nmf_sheet import validate_nmf_sheet
    validate_nmf_sheet(sheet)
    result = {'schema': CALCULATION_SCHEMA, 'sheet_sha256': digest(sheet), 'status': 'unavailable',
        'qualifications': deepcopy(sheet['preparation_qualifications']), 'failures': deepcopy(sheet['failures']),
        'units': {'input': sheet['fit_units'], 'squared_error': None if sheet['fit_units'] is None else sheet['fit_units'] + '^2',
            'normalized_loadings': 'dimensionless', 'component_fraction': 'dimensionless'},
        'population': {'gene_count': sheet['shape'][0], 'sample_count': sheet['shape'][1], 'component_count': len(sheet['components']),
            'coordinate_convention': 'zero_based_input_occurrence_positions'},
        'native_reconstruction_error': sheet['native_diagnostics'].get('reconstruction_err_'),
        'native_minus_calculated_frobenius': None}
    fields = ('reconstructed', 'residuals', 'gene_sse', 'gene_observation_counts', 'sample_sse', 'sample_observation_counts',
        'sse', 'cell_count', 'frobenius_residual', 'rmse', 'mae', 'relative_frobenius_denominator', 'relative_frobenius_residual',
        'input_norm_scaled_representation', 'component_loading_sums', 'loading_sum_scaled_representations',
        'normalized_gene_loadings', 'sample_component_contributions', 'sample_contribution_denominators', 'sample_component_fractions')
    result.update({field: None for field in fields})
    if not sheet['calculation_eligible']:
        return result
    q = result['qualifications']
    result['reconstructed'] = reconstruct_nmf(sheet['W'], sheet['H'], qualifications=q)
    result.update(residual_measurements(sheet['fit_matrix'], result['reconstructed'], qualifications=q))
    result.update(component_measurements(sheet['W'], sheet['H'], qualifications=q))
    native, computed = result['native_reconstruction_error'], result['frobenius_residual']
    if native is not None and computed is not None:
        result['native_minus_calculated_frobenius'] = _safe(lambda: native-computed, q, 'native_minus_calculated_frobenius')
    result['status'] = 'calculated'
    return result
