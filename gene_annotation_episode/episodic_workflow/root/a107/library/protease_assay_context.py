"""A107 protease assay context declarations."""
from __future__ import annotations
from copy import deepcopy
import math
QUALIFICATIONS = ['first_window_signal_slope_is_not_proof_of_an_initial_chemical_regime', 'native_fit_is_unweighted_over_original_substrate_rows', 'repeated_concentrations_are_not_inferred_replicates', 'native_unit_labels_do_not_establish_supplied_units', 'native_efficiency_uncertainty_omits_parameter_covariance', 'fit_only_uncertainty_holds_calibration_and_enzyme_values_fixed', 'no_total_uncertainty_or_function_probability']

class ProteaseKineticsContractError(ValueError):

    def __init__(self, code, field):
        self.code, self.field = (code, field)
        super().__init__(code + ':' + field)

def _fail(code, field):
    raise ProteaseKineticsContractError(code, field)

def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) and (type(value) is not int or result == value) else None

def _context(raw):
    result = {'sample_key': None, 'substrate_identity': None, 'enzyme_identity': None, 'conditions': None, 'replicate_ids': None, 'units': {'time': None, 'signal': None, 'substrate': None, 'enzyme': None}, 'calibration': None, 'enzyme_basis': 'unknown', 'product_per_cleavage': None}
    if raw is None:
        return result
    if type(raw) is not dict or set(raw) != set(result):
        _fail('closed_assay_context_required', '/assay_context')
    for name in ('sample_key', 'substrate_identity', 'enzyme_identity'):
        if raw[name] is not None and (type(raw[name]) is not str or not raw[name].strip()):
            _fail('identity_or_null_required', '/assay_context/' + name)
    if raw['replicate_ids'] is not None and (type(raw['replicate_ids']) is not list or any((item is not None and (type(item) is not str or not item.strip()) for item in raw['replicate_ids']))):
        _fail('replicate_ids_or_null_required', '/assay_context/replicate_ids')
    units = raw['units']
    if type(units) is not dict or set(units) != set(result['units']):
        _fail('closed_declared_units_required', '/assay_context/units')
    for name, value in units.items():
        if value is not None and (type(value) is not str or not value.strip()):
            _fail('declared_unit_or_null_required', '/assay_context/units/' + name)
    if raw['enzyme_basis'] not in {'unknown', 'total_enzyme_concentration', 'active_site_concentration'}:
        _fail('enzyme_basis_required', '/assay_context/enzyme_basis')
    stoichiometry = raw['product_per_cleavage']
    if stoichiometry is not None and (_number(stoichiometry) is None or stoichiometry <= 0):
        _fail('positive_product_stoichiometry_required', '/assay_context/product_per_cleavage')
    calibration = raw['calibration']
    if calibration is not None:
        fields = {'schema', 'response_per_product_concentration', 'signal_unit', 'product_concentration_unit', 'curve_ordinals', 'applicability', 'source_ref'}
        if type(calibration) is not dict or set(calibration) != fields or calibration['schema'] != 'protease_signal_calibration_v1':
            _fail('closed_calibration_required', '/assay_context/calibration')
        factor = calibration['response_per_product_concentration']
        if _number(factor) is None or factor <= 0:
            _fail('positive_calibration_response_required', '/assay_context/calibration/response_per_product_concentration')
        if calibration['applicability'] not in {'supported', 'unknown', 'conflicting', 'unsupported'}:
            _fail('calibration_applicability_required', '/assay_context/calibration/applicability')
        if type(calibration['curve_ordinals']) is not list or any((type(i) is not int or i < 0 for i in calibration['curve_ordinals'])):
            _fail('original_curve_ordinals_required', '/assay_context/calibration/curve_ordinals')
        for name in ('signal_unit', 'product_concentration_unit', 'source_ref'):
            if type(calibration[name]) is not str or not calibration[name].strip():
                _fail('calibration_source_and_units_required', '/assay_context/calibration/' + name)
    return deepcopy(raw)
