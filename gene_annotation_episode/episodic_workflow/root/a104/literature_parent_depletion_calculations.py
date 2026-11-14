"""Exact within-row arithmetic for finite parent-compound removal fractions.

These are endpoint contrasts, not rates, catalytic yields or credit weights.
The two contrasts reuse one active observation and are dependent descriptions.
"""
from decimal import Decimal

from .domain import ContractError, identity

COMPONENTS=('active_parent_removal','inactive_parent_removal','abiotic_parent_removal',
    'active_reported_sd','inactive_reported_sd','abiotic_reported_sd',
    'active_minus_inactive','active_minus_abiotic')
SOURCES={'active_parent_removal':'active','inactive_parent_removal':'inactive',
    'abiotic_parent_removal':'abiotic','active_reported_sd':'active_sd',
    'inactive_reported_sd':'inactive_sd','abiotic_reported_sd':'abiotic_sd'}
DEPENDENCIES={'active_minus_inactive':('active','inactive'),
    'active_minus_abiotic':('active','abiotic')}
FORMULAS={'active_parent_removal':'reported Bio','inactive_parent_removal':'reported inactive_enzyme',
    'abiotic_parent_removal':'reported Ab','active_reported_sd':'reported Stdev1',
    'inactive_reported_sd':'reported Stdev3','abiotic_reported_sd':'reported Stdev2',
    'active_minus_inactive':'Bio - inactive_enzyme',
    'active_minus_abiotic':'Bio - Ab'}
CHECK_TOLERANCE=Decimal('0.000000000001')


def populate_parent_depletion_components(extraction):
    values=extraction['values']
    def dec(role): return Decimal(values[role]['exact_decimal'])
    active,inactive,abiotic=dec('active'),dec('inactive'),dec('abiotic')
    calculated={'active_minus_inactive':active-inactive,'active_minus_abiotic':active-abiotic}
    for component,reported in (('active_minus_inactive','reported_active_minus_inactive'),
            ('active_minus_abiotic','reported_active_minus_abiotic')):
        if abs(calculated[component]-dec(reported))>CHECK_TOLERANCE:
            raise ContractError('parent_depletion_reported_difference_mismatch')
    cells={}
    for component in COMPONENTS:
        roles=(SOURCES[component],) if component in SOURCES else DEPENDENCIES[component]
        value=dec(roles[0]) if component in SOURCES else calculated[component]
        cells[component]={'value':float(value),'exact_decimal':str(value),'unit':'fraction',
            'status':'point','origin':'reported' if component in SOURCES else 'calculated',
            'formula':FORMULAS[component],
            'input_measurement_keys':[identity('xlsx_parent_removal_measurement',{
                'source_ref':extraction['source_ref'],'workbook_sha256':extraction['workbook_sha256'],
                'sheet_key':extraction['sheet_key'],'address':values[role]['address']}) for role in roles],
            'source_cell_addresses':[values[role]['address'] for role in roles],
            'reported_sd_of_difference':None,'standard_error_of_difference':None,
            'difference_uncertainty_status':'joint_replication_and_covariance_unknown'}
    return {'version':'a105_parent_depletion_sheet_v1','axis':'A105',
        'evaluation_scope':'finite_parent_compound_removal','cells':cells,
        'reported_difference_check_tolerance':str(CHECK_TOLERANCE),
        'active_minus_inactive_reported_discrepancy':str(calculated['active_minus_inactive']-dec('reported_active_minus_inactive')),
        'active_minus_abiotic_reported_discrepancy':str(calculated['active_minus_abiotic']-dec('reported_active_minus_abiotic')),
        'shared_active_observation_key':cells['active_parent_removal']['input_measurement_keys'][0],
        'product_coupling_factor':None,'annotation_credit':None}


__all__=['COMPONENTS','CHECK_TOLERANCE','populate_parent_depletion_components']
