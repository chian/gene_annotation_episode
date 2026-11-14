"""Exact descriptive balances for Figure 2D soluble CcCdP products."""
from __future__ import annotations

from decimal import Decimal, localcontext

from .domain import ContractError, identity

REPORTED = ('g2_initial', 'g2', 'g3', 'g4', 'g5', 'g6', 'pi',
            'g2_sd', 'g3_sd', 'g4_sd', 'g5_sd', 'g6_sd', 'pi_sd')
DERIVED = ('g2_loss', 'soluble_product_molecules', 'acceptor_accounting_ratio',
           'acceptor_balance_remainder', 'soluble_added_glucosyl_equivalents',
           'soluble_glucosyl_accounting_ratio', 'glucosyl_balance_remainder',
           'nominal_donor_to_soluble_yield')
COMPONENTS = REPORTED + DERIVED
DEPENDENCIES = {
    'g2_loss': ('g2_initial', 'g2'),
    'soluble_product_molecules': ('g3', 'g4', 'g5', 'g6'),
    'acceptor_accounting_ratio': ('g2_initial', 'g2', 'g3', 'g4', 'g5', 'g6'),
    'acceptor_balance_remainder': ('g2_initial', 'g2', 'g3', 'g4', 'g5', 'g6'),
    'soluble_added_glucosyl_equivalents': ('g3', 'g4', 'g5', 'g6'),
    'soluble_glucosyl_accounting_ratio': ('g3', 'g4', 'g5', 'g6', 'pi'),
    'glucosyl_balance_remainder': ('g3', 'g4', 'g5', 'g6', 'pi'),
    'nominal_donor_to_soluble_yield': ('g3', 'g4', 'g5', 'g6', 'donor_nominal'),
}
FORMULAS = {
    'g2_loss': 'G2_0 - G2_t',
    'soluble_product_molecules': 'G3 + G4 + G5 + G6',
    'acceptor_accounting_ratio': '(G3 + G4 + G5 + G6) / (G2_0 - G2_t)',
    'acceptor_balance_remainder': '(G2_0 - G2_t) - (G3 + G4 + G5 + G6)',
    'soluble_added_glucosyl_equivalents': 'G3 + 2*G4 + 3*G5 + 4*G6',
    'soluble_glucosyl_accounting_ratio': '(G3 + 2*G4 + 3*G5 + 4*G6) / Pi',
    'glucosyl_balance_remainder': 'Pi - (G3 + 2*G4 + 3*G5 + 4*G6)',
    'nominal_donor_to_soluble_yield': '(G3 + 2*G4 + 3*G5 + 4*G6) / nominal donor',
}
MEANINGS = {
    'g2_loss': 'G2 loss conditional on source time-zero value matching nominal charge',
    'soluble_product_molecules': 'selected soluble G3–G6 concentration sum; source time-zero entries print zero without detection limits',
    'acceptor_accounting_ratio': 'descriptive soluble-product molecules per G2 loss conditional on source time-zero nominal-matching value and printed-zero product baseline',
    'acceptor_balance_remainder': 'inferred acceptor-account remainder; no solid product measured',
    'soluble_added_glucosyl_equivalents': 'selected soluble-product added-glucosyl equivalents relative to G2; printed-zero product baseline is conditional',
    'soluble_glucosyl_accounting_ratio': 'descriptive soluble-product accounting relative to measured Pi under one-Pi-per-transfer model',
    'glucosyl_balance_remainder': 'inferred Pi-minus-soluble-equivalent remainder; no insoluble product measured',
    'nominal_donor_to_soluble_yield': 'soluble added-glucosyl equivalents per nominal donor charge; not catalyst-specific yield',
}


def populate_stoichiometric_balance_components(extraction):
    source = extraction['values']
    def d(role): return Decimal(source[role]['exact_decimal'])
    donor = Decimal(extraction['conditions']['aGlc1-P']['value']['exact_decimal'])
    if donor <= 0:
        raise ContractError('stoichiometric_balance_positive_nominal_donor_required')
    with localcontext() as ctx:
        ctx.prec = 50
        loss = d('g2_initial') - d('g2')
        m = sum((d(k) for k in ('g3', 'g4', 'g5', 'g6')), Decimal(0))
        w = d('g3') + 2*d('g4') + 3*d('g5') + 4*d('g6')
        pi = d('pi')
        if loss <= 0 or pi <= 0:
            raise ContractError('stoichiometric_balance_positive_denominators_required')
        derived = {'g2_loss': loss, 'soluble_product_molecules': m,
                   'acceptor_accounting_ratio': m/loss,
                   'acceptor_balance_remainder': loss-m,
                   'soluble_added_glucosyl_equivalents': w,
                   'soluble_glucosyl_accounting_ratio': w/pi,
                   'glucosyl_balance_remainder': pi-w,
                   'nominal_donor_to_soluble_yield': w/donor}
    def key(address):
        metadata_cell = address.startswith('Metadata!')
        return identity('xlsx_stoichiometric_balance_measurement', {
            'source_ref': extraction['source_ref'],
            'workbook_sha256': extraction['workbook_sha256'],
            'sheet_key': extraction['metadata_sheet_key'] if metadata_cell else extraction['sheet_key'],
            'address': address.removeprefix('Metadata!')})
    cells = {}
    for role in REPORTED:
        v = d(role); address = source[role]['address']
        origin = ('source_time_zero_nominal_matching' if role == 'g2_initial' else
                  'reported_sd' if role.endswith('_sd') else 'reported_mean')
        meaning = ('source time-zero G2 value matching nominal charge; distinct measured mean not established'
                   if role == 'g2_initial' else 'source-reported SD of duplicate reactions'
                   if role.endswith('_sd') else 'source-reported concentration mean')
        cells[role] = {'value': float(v), 'exact_decimal': str(v), 'unit': 'mM',
            'status': 'point', 'origin': origin, 'meaning': meaning,
            'formula': 'source cell', 'source_cell_addresses': [address],
            'input_measurement_keys': [key(address)]}
    for role in DERIVED:
        v = derived[role]; deps = DEPENDENCIES[role]
        addresses = [source[k]['address'] if k != 'donor_nominal' else
                     'Metadata!' + extraction['conditions']['aGlc1-P']['value']['address'] for k in deps]
        cells[role] = {'value': float(v), 'exact_decimal': str(v),
            'unit': 'fraction' if role.endswith('_ratio') or role.endswith('_yield') else 'mM',
            'status': 'point', 'origin': 'calculated', 'meaning': MEANINGS[role],
            'formula': FORMULAS[role], 'source_cell_addresses': addresses,
            'input_measurement_keys': [key(a) for a in addresses]}
    return {'version': 'a105_stoichiometric_balance_sheet_v1', 'axis': 'A105',
        'evaluation_scope': 'source_soluble_product_stoichiometric_balance',
        'cells': cells, 'one_pi_per_transfer_premise': extraction['model_premise'],
        'ratio_sd': None, 'ratio_se': None, 'ratio_confidence_interval': None,
        'joint_covariance': None, 'matched_no_enzyme_arm': None,
        'independent_preparation_count': None, 'molecule_specific_attribution': None,
        'assay_validity_multiplier': None, 'annotation_credit': None}


__all__ = ['REPORTED', 'DERIVED', 'COMPONENTS', 'DEPENDENCIES', 'FORMULAS',
           'populate_stoichiometric_balance_components']
