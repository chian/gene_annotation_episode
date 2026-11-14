"""Original source perturbation point return contracts and metadata projection."""
from gene_annotation_episode.domain import obj
from .literature_perturbation_calculations import COMPONENTS, CONDITIONAL_CODES, REASONS

PROVIDER = 'literature.experimental.perturbation'
FORMULA_CODES = {name: 'perturbation_' + name + '_v1' for name in COMPONENTS}
BINDINGS = {'assayed_subject_ref': ('molecule', 'reference'),
    'recipient_ref': ('recipient', 'reference'), 'donor_ref': ('donor', 'reference'),
    'experiment_ref': ('experiment', 'reference'), 'reference_arm_ref': ('reference_arm', 'reference'),
    'perturbed_arm_ref': ('perturbed_arm', 'reference'), 'restored_arm_ref': ('restored_arm', 'reference'),
    'partner_ref': ('partner', 'reference'), 'endpoint_ref': ('endpoint', 'term'),
    'normalization_ref': ('normalization', 'term'), 'condition_ref': ('condition', 'context'),
    'intended_change_ref': ('intended_change', 'term')}


def _metadata(extraction):
    return {**{name: extraction[name] for name in ('design', 'measurement_status',
        'same_endpoint_scope', 'amount_role', 'orientation', 'data_origin', 'endpoint_unit', 'exposure_unit')},
        'operand_source_kind': extraction['source_kind'],
        'uncertainty_basis': extraction['uncertainty_basis'],
        'index_kind': 'proposed_source_restoration_index',
        'evaluated_scope': 'interpreted_reference_perturbation'}


def perturbation_cells_schema():
    source = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    properties = {'sheet_ref': dict(source), 'evidence_source_ref': dict(source),
        'data_source_ref': {**source, 'type': ['string', 'null']},
        **{field: {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': kind}
           for field, (_, kind) in BINDINGS.items()},
        'component': {'type': 'string', 'enum': list(COMPONENTS), 'description':
            'Native reference/perturbed/restored outcomes and separate effect, restoration, nuisance amount and isolation components. The reference index combines their declared orientation and proposed conventions; it is not target correspondence or probability. Joint uncertainty remains unreported.'},
        'value': {'type': ['number', 'null']},
        'unit': {'type': 'string', 'enum': ['unreported', 'events_per_100000_cells', 'fraction',
            'CFU_per_mL', 'CFU_per_initial_OD_per_mL', 'minutes', 'per_min', 'per_h', 'dimensionless']},
        'status': {'type': 'string', 'enum': ['populated', 'unavailable']},
        'formula_code': {'type': 'string', 'enum': list(FORMULA_CODES.values())},
        'origin': {'type': 'string', 'enum': ['reported', 'derived', 'graph_derived', 'synthetic', 'proposed']},
        'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *REASONS]},
        'conditional_on': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': list(CONDITIONAL_CODES)}},
        'design': {'type': 'string', 'enum': ['native_deletion_restoration', 'selective_perturbation_restoration',
            'cas_free_reconstitution', 'variant_replacement', 'other_explicit', 'unknown', 'conflicting']},
        'measurement_status': {'type': 'string', 'enum': ['validated_ratio_scale', 'qualitative_only', 'unknown', 'conflicting']},
        'same_endpoint_scope': {'type': 'string', 'enum': ['yes', 'no', 'unknown', 'conflicting']},
        'amount_role': {'type': 'string', 'enum': ['nuisance', 'intended_change', 'unknown']},
        'orientation': {'type': ['integer', 'null'], 'enum': [None, -1, 1]},
        'data_origin': {'type': ['string', 'null'], 'enum': [None, 'reported', 'graph_derived', 'synthetic']},
        'operand_source_kind': {'type': 'string', 'enum': ['primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture']},
        'uncertainty_basis': {'type': 'string', 'enum': ['unreported']},
        'endpoint_unit': {'type': 'string', 'enum': ['unreported', 'events_per_100000_cells',
            'fraction', 'CFU_per_mL', 'CFU_per_initial_OD_per_mL', 'minutes', 'per_min', 'per_h']},
        'exposure_unit': {'type': 'string', 'enum': ['unreported', 'molecules_per_cell',
            'normalized_signal', 'fraction', 'mg_per_mL']},
        'index_kind': {'type': 'string', 'enum': ['proposed_source_restoration_index']},
        'evaluated_scope': {'type': 'string', 'enum': ['interpreted_reference_perturbation']}}
    return {'type': 'array', 'items': obj(properties), 'x-source': 'literature_perturbation_cells'}


