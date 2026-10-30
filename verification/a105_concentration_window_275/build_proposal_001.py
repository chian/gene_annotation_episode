"""Build review artifacts only; this is not the proposed production reader.

The source fixture and independent arithmetic oracle below do not implement
source reading, population, persistence, selected execution or typed delivery.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = ROOT / 'research/experimental_scoring_review_2026-10-23/a105_matched_estimator_source_260'
ROLES = ('substrate_start', 'substrate_end', 'total_product_start', 'total_product_end',
         'fate_product_start', 'fate_product_end', 'coordinate_start', 'coordinate_end')
RELATIONS = ('same_series', 'same_window', 'same_aliquot_window', 'concentration_basis',
             'calibration_linkage', 'endpoint_assignment')


def obj(**p):
    return dict(type='object', properties=p, required=list(p), additionalProperties=False)


def arr(s, unique=False):
    return dict(type='array', items=s, **({'uniqueItems': True} if unique else {}))


def enum(*v): return {'enum': list(v)}
def ref(k): return {'$ref': '#/$defs/' + k}
def nullable(s): return {'anyOf': [s, {'type': 'null'}]}
def exact(q):
    q = Fraction(q)
    return dict(numerator=str(q.numerator), denominator=str(q.denominator))
def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


TEXT = {'type': 'string', 'minLength': 1}
INT = {'type': 'integer', 'minimum': 0}
POSITION = {'type': 'integer', 'minimum': 1}
HEX = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
NUMBER_NULL = {'type': ['number', 'null']}
REASONS = {
    'source': ('number_unavailable', 'unit_unavailable', 'native_nondetection',
               'joint_covariance_unknown', 'joint_covariance_incomplete', 'timing_meaning_unknown'),
    'selection': ('operand_not_selected', 'coefficient_not_selected', 'covariance_not_selected', 'timing_scenario_not_selected'),
    'relationship': ('same_series_unknown', 'same_series_conflicting', 'same_series_incompatible',
        'same_window_unknown', 'same_window_conflicting', 'same_window_incompatible',
        'same_aliquot_window_unknown', 'same_aliquot_window_conflicting', 'same_aliquot_window_incompatible',
        'concentration_basis_unknown', 'concentration_basis_conflicting', 'concentration_basis_incompatible',
        'calibration_linkage_unknown', 'calibration_linkage_conflicting', 'calibration_linkage_incompatible',
        'endpoint_assignment_unknown', 'endpoint_assignment_conflicting', 'endpoint_assignment_incompatible',
        'timing_meaning_conflicting', 'timing_meaning_not_elapsed', 'normalization_mapping_unresolved',
        'coefficient_meaning_unresolved', 'reused_physical_operand'),
    'implementation': ('bounded_arithmetic_unimplemented', 'approximate_arithmetic_unimplemented',
        'formula_cache_point_unimplemented', 'source_unit_unsupported', 'covariance_estimation_from_table_unimplemented',
        'scenario_uncertainty_unimplemented'),
    'domain': ('zero_denominator', 'positive_time_span_required', 'positive_coefficient_required',
               'positive_variance_required', 'numerical_model_range'),
}

D = {}
D['exact'] = obj(numerator={'type': 'string', 'pattern': '^-?[0-9]+$'},
                 denominator={'type': 'string', 'pattern': '^[1-9][0-9]*$'})
D['text_field'] = obj(kind={'const': 'text'}, source_ref=TEXT,
    representation=enum('original', 'text'), start=INT, end=POSITION, quote=TEXT)
D['xlsx_field'] = obj(kind={'const': 'xlsx_cell_slice'}, source_ref=TEXT,
    representation={'const': 'original'}, sheet_key=TEXT, sheet_name=TEXT, worksheet_part=TEXT,
    cell={'type': 'string', 'pattern': '^[A-Z]+[1-9][0-9]*$'}, decoded_start=INT, decoded_end=POSITION, quote=TEXT)
D['field'] = {'oneOf': [ref('text_field'), ref('xlsx_field')]}
D['number_selector'] = obj(field=ref('field'), number_start=INT, number_end=POSITION)


def meaning(*values):
    return obj(value=enum(*values), witnesses=arr(ref('field')))


D['relationship'] = meaning('supported', 'incompatible', 'unknown', 'conflicting')
D['reasons'] = obj(**{k: arr(enum(*v), True) for k, v in REASONS.items()})
D['quantity'] = obj(number=nullable(ref('number_selector')), unit=nullable(ref('field')),
    record=nullable(ref('text_field')), analyte=nullable(ref('field')),
    coordinate=nullable(ref('field')), measurement_identity=nullable(ref('field')),
    unit_association=meaning('same_record', 'source_header', 'source_shared_header', 'source_method', 'unknown', 'conflicting'),
    reading_meaning=meaning('reported_point', 'source_qualified_approximate', 'reported_nondetection', 'unknown', 'conflicting'),
    concentration_basis=meaning('native_reaction_concentration', 'quenched_sample_concentration',
                                'other_normalized_concentration', 'coordinate', 'unknown', 'conflicting'),
    uncertainty=arr(ref('field')))
D['coefficient'] = obj(kind=enum('implicit_unit_coefficient', 'explicit_source_token'),
    number=nullable(ref('number_selector')), reaction=ref('field'),
    relationship=ref('relationship'))
D['grid'] = obj(source_ref=TEXT, sheet_key=TEXT, sheet_name=TEXT, worksheet_part=TEXT,
    header_row=POSITION, start_row=POSITION, end_row=POSITION,
    coordinate_column={'type': 'string', 'pattern': '^[A-Z]+$'},
    columns=obj(**{k: {'type': 'string', 'pattern': '^[A-Z]+$'}
                   for k in ('substrate', 'total_product', 'fate_product')}))
D['assay'] = obj(**{k: nullable(ref('field')) for k in
    ('organism', 'genotype', 'molecule', 'accession', 'construct', 'preparation', 'expression_host',
     'experimental_system', 'conditions', 'intended_change', 'endpoint', 'calibration',
     'blank', 'normalization', 'independent_replication')},
    arrangement=meaning('single_preparation', 'coexistence', 'replacement', 'unknown', 'conflicting'),
    participants=arr(obj(identity=ref('field'), role=enum('assayed_molecule', 'partner', 'activator',
        'substrate', 'product', 'control', 'unknown'), presence=enum('present', 'absent', 'unknown', 'conflicting'))))
D['timing'] = obj(source_meaning=meaning('actual_sampling_time', 'plot_coordinate_only', 'unknown', 'conflicting'),
    scenario=nullable(obj(kind={'const': 'coordinates_are_elapsed_sampling_times'},
                          status={'const': 'stipulated_sensitivity'})))

DEFINITIONS = {}


def component(name, formula, unit, meaning_text, operands, *, scope='source', covariance=False):
    DEFINITIONS[name] = dict(formula=formula, unit=unit, meaning=meaning_text,
        operands=list(operands), population=scope, covariance_required=covariance)


for role in ROLES:
    component(role, 'selected_native_token*unit_multiplier', 's' if role.startswith('coordinate') else 'uM',
              'Native source operand; not an experimental reliability score.', [role])
for name, roles in (
        ('substrate_loss', ('substrate_start', 'substrate_end')),
        ('total_product_gain', ('total_product_start', 'total_product_end')),
        ('fate_product_gain', ('fate_product_start', 'fate_product_end'))):
    component(name, 'S0-S1' if name == 'substrate_loss' else 'T1-T0' if name == 'total_product_gain' else 'F1-F0',
              'uM', 'Signed observed change over the selected common window.', roles)
component('coordinate_span', 't1-t0', 's', 'Released coordinate separation, not automatically elapsed time.', ROLES[-2:])
component('chemical_discrepancy', '(S0-S1)/nuS-(T1-T0)/nuT', 'uM_reaction_equivalents',
          'Signed disagreement between matched chemical readouts under declared stoichiometry.', ROLES[:4])
component('chemical_ratio', '((S0-S1)/nuS)/((T1-T0)/nuT)', 'dimensionless',
          'Relative agreement of matched substrate loss and total-product gain.', ROLES[:4])
component('chemical_relative_discrepancy', 'chemical_ratio-1', 'dimensionless',
          'Signed relative mismatch of the same chemical readouts.', ROLES[:4])
component('fate_fraction', '((F1-F0)/nuF)/((T1-T0)/nuT)', 'dimensionless',
          'Specific measured product fate relative to total measured cleavage; not enzyme attribution.', ROLES[2:6])
component('substrate_depletion_fraction', '(S0-S1)/S0', 'fraction',
          'Fractional depletion, which can limit an initial-regime interpretation.', ROLES[:2])
for role, base in (('substrate', 'substrate_loss'), ('total_product', 'total_product_gain'), ('fate_product', 'fate_product_gain')):
    for prefix in ('source', 'scenario'):
        component(prefix + '_interval_average_' + role, '60*' + base + '/coordinate_span', 'uM/min',
                  'Interval-average concentration change; never initial rate, Vmax or kcat.',
                  (*DEFINITIONS[base]['operands'], *ROLES[-2:]), scope=prefix)
VAR_BASES = ('substrate_loss', 'total_product_gain', 'fate_product_gain', 'coordinate_span',
             'chemical_discrepancy', 'chemical_ratio', 'fate_fraction',
             'source_interval_average_substrate', 'source_interval_average_total_product', 'source_interval_average_fate_product')
for base in VAR_BASES:
    component(base + '_variance', 'gradient(' + base + ')^T*C*gradient(' + base + ')',
              '(' + DEFINITIONS[base]['unit'] + ')^2',
              'Selected-estimate uncertainty; exact linear propagation or explicitly first-order nonlinear propagation.',
              DEFINITIONS[base]['operands'], covariance=True)
component('chemical_standardized_discrepancy', 'chemical_discrepancy/sqrt(chemical_discrepancy_variance)',
          'dimensionless', 'Discrepancy relative to justified joint-estimate uncertainty; no p-value or probability.',
          ROLES[:4], covariance=True)
COMPONENTS = list(DEFINITIONS)

D['selection'] = obj(version={'const': 'a105_concentration_window_selection_v1'},
    source_ref=TEXT, source_kind=enum('primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture'),
    assay=ref('assay'), grid=nullable(ref('grid')),
    quantities=obj(**{r: nullable(ref('quantity')) for r in ROLES}),
    relationships=obj(**{r: ref('relationship') for r in RELATIONS}),
    stoichiometry=obj(**{r: nullable(ref('coefficient')) for r in ('substrate', 'total_product', 'fate_product')}),
    timing=ref('timing'), covariance_source_ref=nullable(TEXT),
    covariance_material=enum('closed_joint_estimator_covariance_document', 'unsupported_observation_table', 'not_selected'),
    evidence=arr(obj(role=enum('chemical_relation', 'product_identity', 'normalization', 'calibration',
        'blank', 'replication', 'uncertainty', 'alternative_contribution', 'preparation_change', 'timing'), witness=ref('field'))),
    requested_cells=arr(enum(*COMPONENTS), True))
D['artifact'] = obj(source_ref=TEXT, representation=enum('original', 'text'), artifact_ref=TEXT, sha256=HEX)
D['location'] = {'oneOf': [
    obj(kind={'const': 'text'}, source_ref=TEXT, artifact_ref=TEXT, representation=enum('original', 'text'), start=INT, end=POSITION),
    obj(kind={'const': 'xlsx_cell'}, source_ref=TEXT, artifact_ref=TEXT, representation={'const': 'original'},
        worksheet_part=TEXT, member_sha256=HEX, sheet_key=TEXT, sheet_name=TEXT, cell=TEXT,
        xml_start=INT, xml_end=POSITION, decoded_start=INT, decoded_end=POSITION,
        shared_string_location=nullable(obj(member=TEXT, member_sha256=HEX, start=INT, end=POSITION))) ]}
D['reading'] = obj(role=enum(*ROLES), value=NUMBER_NULL, exact_value=nullable(ref('exact')),
    unit=enum('uM', 's', None), raw_number=nullable(TEXT), raw_unit=nullable(TEXT),
    unit_multiplier=nullable(ref('exact')), relation=enum('eq', 'lt', 'le', 'gt', 'ge', 'none'),
    status=enum('point', 'bounded', 'nondetection', 'unavailable'), approximate={'type': 'boolean'},
    origin=enum('reported', 'graph_derived', 'calculated', 'synthetic'), owner_key=TEXT,
    physical_owner_key=nullable(TEXT), dependency_keys=arr(TEXT, True), locations=arr(ref('location')),
    reported_uncertainty=arr(ref('field')), reasons=ref('reasons'))
D['coefficient_reading'] = obj(value=NUMBER_NULL, exact_value=nullable(ref('exact')),
    origin=enum('implicit_chemical_notation', 'reported', 'synthetic', 'unavailable'),
    dependency_keys=arr(TEXT, True), reasons=ref('reasons'))
D['covariance_document'] = obj(version={'const': 'a105_concentration_window_covariance_v1'},
    roles=arr(enum(*ROLES), True), owner_keys=arr(TEXT), units=arr(enum('uM', 's')),
    dependency_keys=arr(arr(TEXT, True)), covariance=nullable(arr(arr({'type': 'number'}))),
    basis={'const': 'joint_covariance_of_selected_estimates'},
    variance_status=enum('known', 'estimated', 'unknown'), origin=enum('reported', 'derived', 'synthetic'),
    derivation=enum('reported_estimator_covariance', 'exact_linear_transform', 'estimated_from_observations', 'synthetic_model'),
    systematic_coverage=enum('included_as_declared', 'not_established', 'identified_unresolved'))
D['covariance_reading'] = obj(document=ref('covariance_document'), source_ref=TEXT, artifact_ref=TEXT, sha256=HEX,
    matrix_exact=nullable(arr(arr(ref('exact')))))
D['extraction'] = obj(version={'const': 'a105_concentration_window_extraction_v1'}, selection=ref('selection'),
    quantities=obj(**{r: nullable(ref('reading')) for r in ROLES}),
    coefficients=obj(**{r: ref('coefficient_reading') for r in ('substrate', 'total_product', 'fate_product')}),
    covariance=nullable(ref('covariance_reading')), source_artifacts=arr(ref('artifact')))
D['calculation_inputs'] = obj(version={'const': 'a105_concentration_window_calculation_inputs_v1'},
    extraction_digest=HEX, source_kind=enum('primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture'),
    context=ref('assay'), quantities=obj(**{r: nullable(ref('reading')) for r in ROLES}),
    coefficients=obj(**{r: ref('coefficient_reading') for r in ('substrate', 'total_product', 'fate_product')}),
    relationships=obj(**{r: ref('relationship') for r in RELATIONS}), timing=ref('timing'),
    covariance=nullable(ref('covariance_reading')), covariance_material=enum('closed_joint_estimator_covariance_document',
        'unsupported_observation_table', 'not_selected'), requested_cells=arr(enum(*COMPONENTS), True),
    source_artifacts=arr(ref('artifact')))
D['cell'] = obj(component=enum(*COMPONENTS), value=NUMBER_NULL, exact_value=nullable(ref('exact')),
    conditional_value=NUMBER_NULL, conditional_exact_value=nullable(ref('exact')),
    status=enum('populated', 'conditional_scenario', 'unavailable'),
    unit=enum(*dict.fromkeys(x['unit'] for x in DEFINITIONS.values())),
    formula=enum(*dict.fromkeys(x['formula'] for x in DEFINITIONS.values())),
    meaning=enum(*dict.fromkeys(x['meaning'] for x in DEFINITIONS.values())),
    origin=enum('reported', 'graph_derived', 'calculated', 'synthetic'),
    operand_roles=arr(enum(*ROLES), True), dependency_keys=arr(TEXT, True), contribution_key=TEXT,
    approximate={'type': 'boolean'}, bound=enum('none', 'lt', 'le', 'gt', 'ge'), threshold=NUMBER_NULL,
    outside_physical_fraction_range={'type': 'boolean'}, negative_observed_change={'type': 'boolean'},
    timing_stipulation=enum('coordinates_are_elapsed_sampling_times', None),
    uncertainty_method=enum('not_applicable', 'exact_linear_covariance', 'first_order_covariance', 'not_available'),
    reasons=ref('reasons'))
D['sheet'] = obj(version={'const': 'a105_concentration_window_sheet_v1'}, axis={'const': 'A105'},
    section={'const': 'observed_concentration_window'}, cells=arr(ref('cell')),
    assertion_resolution=enum('total_chemical_extent_and_selected_product_fate'),
    relationship_meanings=obj(**{r: enum('supported', 'incompatible', 'unknown', 'conflicting') for r in RELATIONS}),
    source_timing_meaning=enum('actual_sampling_time', 'plot_coordinate_only', 'unknown', 'conflicting'),
    source_artifacts=arr(ref('artifact')),
    estimate_bindings=arr(obj(role=enum(*ROLES), owner_key=TEXT, physical_owner_key=nullable(TEXT), dependency_keys=arr(TEXT, True))),
    derived_covariance=nullable(obj(components=arr(enum(*VAR_BASES), True), matrix=arr(arr({'type': 'number'})),
        method={'const': 'G*C*G_transpose'}, covariance_source_ref=TEXT)),
    limits=arr(enum('observed_source_scale_not_blank_corrected', 'no_unique_molecular_attribution',
        'unknown_calibration_systematics', 'no_independent_replication_inferred', 'shared_derived_contribution',
        'interval_average_not_initial_or_turnover_rate', 'no_cumulative_amount_from_initial_volume',
        'selected_integration_unimplemented', 'general_reliability_compilation_unfinished', 'no_target_transfer_or_W05'), True),
    annotation_credit={'type': 'null'})


def resource(name):
    # Include exactly the transitive referenced definitions, preserving closures.
    needed = set()
    def visit(v):
        if isinstance(v, dict):
            key = v.get('$ref', '').removeprefix('#/$defs/')
            if key and key not in needed:
                needed.add(key); visit(D[key])
            for child in v.values(): visit(child)
        elif isinstance(v, list):
            for child in v: visit(child)
    body = deepcopy(D[name]); visit(body)
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'urn:a105:concentration-window:275:proposal001:' + name,
            **body, '$defs': {k: deepcopy(D[k]) for k in sorted(needed)}}


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


if __name__ == '__main__':
    schemas = {name.upper(): resource(name) for name in
               ('selection', 'extraction', 'calculation_inputs', 'sheet', 'covariance_document')}
    for schema in schemas.values(): Draft202012Validator.check_schema(schema)
    write('SCHEMAS_001.json', schemas)
    write('COMPONENT_DEFINITIONS_001.json', DEFINITIONS)
    print(json.dumps({'closed_schema_resources': len(schemas), 'components': len(COMPONENTS),
                      'status': 'review_artifacts_not_production'}))
