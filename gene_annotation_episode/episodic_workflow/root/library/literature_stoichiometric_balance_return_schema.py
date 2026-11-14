"""Original numerical return contract; no reader, calculator or repository activation."""
from gene_annotation_episode.domain import obj

REPORTED = ('g2_initial', 'g2', 'g3', 'g4', 'g5', 'g6', 'pi',
            'g2_sd', 'g3_sd', 'g4_sd', 'g5_sd', 'g6_sd', 'pi_sd')
DERIVED = ('g2_loss', 'soluble_product_molecules', 'acceptor_accounting_ratio',
           'acceptor_balance_remainder', 'soluble_added_glucosyl_equivalents',
           'soluble_glucosyl_accounting_ratio', 'glucosyl_balance_remainder',
           'nominal_donor_to_soluble_yield')
COMPONENTS = REPORTED + DERIVED
NAMESPACE = 'literature_stoichiometric_balance_cells'
def stoichiometric_balance_cells_schema():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    artifact = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'artifact'}
    text = {'type': 'string'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj({
        'sheet_ref': ref, 'evidence_source_ref': ref, 'workbook_artifact_ref': artifact,
        'component': {'type': 'string', 'enum': list(COMPONENTS)},
        'evaluation_scope': {'const': 'source_soluble_product_stoichiometric_balance'},
        'value': {'type': 'number'}, 'exact_decimal': text,
        'unit': {'type': 'string', 'enum': ['mM', 'fraction']},
        'status': {'const': 'point'},
        'origin': {'enum': ['source_time_zero_nominal_matching', 'reported_mean', 'reported_sd', 'calculated']},
        'meaning': text, 'formula': text,
        'source_cell_addresses': {'type': 'array', 'minItems': 1, 'items': text},
        'input_measurement_keys': {'type': 'array', 'minItems': 1, 'items': text},
        'panel': {'const': 'D'}, 'sheet_name': {'const': 'Data'},
        'assayed_molecule': {'const': 'Cellodextrin phosphorylase from Clostridium cellulosi'},
        'construct_status': {'const': 'not_reported_in_workbook'},
        'expression_host': {'type': 'null'},
        'row_number': {'type': 'integer', 'minimum': 53},
        'time_minutes': {'type': 'number', 'minimum': 0},
        'reaction_conditions': obj({
            'nominal_donor_mM': {'type': 'number'},
            'nominal_acceptor_mM': {'type': 'number'},
            'enzyme_U_per_mL': {'type': 'number'},
            'MES_mM': {'type': 'number'},
            'pH': {'type': 'number'},
            'temperature_C': {'type': 'number'}}),
        'calibration_source_cell': {'const': 'Metadata!A22'},
        'one_pi_per_transfer_source_cell': {'const': 'Metadata!A29'},
        'one_pi_per_transfer_premise': text,
        'pi_method_source_cell': {'const': 'Metadata!A23'},
        'reported_sd_basis': {'const': 'duplicate_reactions'},
        'initial_baseline_status': {'const': 'source_printed_zero_measurement_and_detection_limit_unestablished'},
        'ratio_sd': {'type': 'null'}, 'ratio_se': {'type': 'null'},
        'ratio_confidence_interval': {'type': 'null'}, 'joint_covariance': {'type': 'null'},
        'matched_no_enzyme_arm': {'type': 'null'},
        'independent_preparation_count': {'type': 'null'},
        'molecule_specific_attribution': {'type': 'null'},
        'assay_validity_multiplier': {'type': 'null'},
        'annotation_credit': {'type': 'null'}})}


