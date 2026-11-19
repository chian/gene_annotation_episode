"""Original synthetic operands retained locally for A106 scientific contracts.

The fixture functions below are retained from the original assay tests; their
values describe engineering controls, never acquired biological evidence.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.perturbation_evidence.literature_assay_grading import ROLES, INPUT_VERSION, CRITERIA_BY_TYPE, COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_assay_grading_storage import REQUESTED

def operand(value, unit, key):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None,
        'measurement_keys': [key], 'source_refs': ['source_synthetic_' + key],
        'origin': 'synthetic', 'native_component': key}


def fixture(assay_type='activity_rate', quantity_kind=None):
    kind, unit, effect, variance, predicted, alternative = {
        'activity_rate': ('rate', 'per_min', .68, .11124225, 1., 0.),
        'endpoint_conversion': ('conversion_difference', 'fraction', .6, .04, .8, 0.),
        'product_distribution': ('equilibrium_fraction', 'fraction', .6, .01, .6, .2),
        'reaction_coupling': ('productive_fraction', 'fraction', .8, .01, 1., .2),
        'ligand_binding': ('binding_parameter', 'nM', 25., 4., 20., 40.),
        'transport_response': ('electrical_conductance', 'pS', 12., 1., 14., 5.),
        'protein_signal': ('signal_ratio', 'dimensionless', .8, .01, 1., .2),
        'protein_amount': ('protein_amount_ratio', 'dimensionless', .8, .01, 1., .2),
    }[assay_type]
    quantities = dict.fromkeys(ROLES)
    quantities.update(effect=operand(effect, unit, 'observed_effect'),
        effect_variance=operand(variance, unit + '_squared', 'estimate_variance'),
        assertion_prediction=operand(predicted, unit, 'fixed_assertion_prediction'),
        alternative_prediction=operand(alternative, unit, 'fixed_alternative_prediction'),
        recovery=operand(.95, 'fraction', 'matrix_recovery'),
        attributed_signal=operand(.85, 'uM/min', 'assigned_rate'),
        total_signal=operand(1., 'uM/min', 'net_preparation_rate'),
        condition_test=operand(2., 'uM/min', 'nuisance_test'),
        condition_reference=operand(1.6, 'uM/min', 'nuisance_reference'))
    return {'version': INPUT_VERSION, 'assay_type': assay_type,
        'assertion_ref': 'hypothesis_synthetic_selected_reference_function',
        'quantity_kind': quantity_kind or kind, 'quantities': quantities,
        'interpretations': {criterion: {'status': 'supported',
            'support_refs': ['source_synthetic_design_' + criterion]}
            for criterion in CRITERIA_BY_TYPE[assay_type]},
        'prediction_model': {'kind': 'fixed_predictions_known_normal',
            'variance_interpretation': 'known', 'support_refs': ['source_synthetic_known_normal_model']}}


def grading_fixture(store, assay_type='endpoint_conversion'):
    quantity_kind = dict(activity_rate='rate_ratio', endpoint_conversion='conversion_fraction',
        product_distribution='product_fraction', reaction_coupling='productive_fraction')[assay_type]
    unit = 'dimensionless' if assay_type == 'activity_rate' else 'fraction'
    lines = [
        'Experiment A: synthetic assay for one reference molecule. Scientific applicability and a known normal fixed-prediction model are explicitly stipulated for this synthetic fixture.',
        f'effect 0.8 {unit}; variance 0.04 {unit}_squared;',
        'recovery 0.9 fraction; attributed 0.6 fraction; total 0.8 fraction;',
        'condition test 0.8 fraction; condition reference 1 fraction;',
        f'assertion prediction 1 {unit}; alternative prediction 0 {unit}.',
        f'Experiment B: effect 0.2 {unit}; variance 0.09 {unit}_squared.',
    ]
    text = '\n'.join(lines)
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_assay_grading_322', 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': None, 'retrieved_at': None}, origin='caller')['id']
    quote = lines[0]
    support = store.put('reference', {'reference_type': 'assay', 'source_ref': source,
        'accession': 'synthetic_assay_322', 'label': 'Experiment A', 'sequence_ref': None,
        'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [],
        'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0,
            'end': len(quote), 'quote': quote}}, origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'reaction322',
        'label': 'Synthetic reaction', 'term_type': 'reaction', 'source_ref': source,
        'anchor': None}, origin='caller')['id']
    assertion = store.put('hypothesis', {'subject_refs': [support], 'predicate': 'catalyzes',
        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []}, origin='reasoning')['id']
    def witness(quote, start=0):
        offset = text.index(quote, start)
        return {'source_ref': source, 'representation': 'original', 'start': offset,
            'end': offset + len(quote), 'quote': quote}
    def number(label, token, native_unit):
        fragment = label + ' ' + token + ' ' + native_unit
        start = text.index(fragment)
        return {'kind': 'source_number', 'number': {'witness': witness(fragment),
            'number_start': len(label) + 1, 'number_end': len(label) + 1 + len(token)},
            'unit': witness(native_unit, start + len(label) + 1 + len(token) + 1), 'origin': 'synthetic'}
    args = {'source_ref': source, 'source_kind': 'synthetic_fixture', 'assay_type': assay_type,
        'assertion_ref': assertion, 'experiment_ref': support, 'quantity_kind': quantity_kind,
        'interpretations': {name: {'status': 'supported', 'support_refs': [support]}
            for name in CRITERIA_BY_TYPE[assay_type]},
        'prediction_model': {'kind': 'fixed_predictions_known_normal', 'variance_interpretation': 'known',
            'support_refs': [support]},
        'quantities': {
            'effect': number('effect', '0.8', unit),
            'effect_variance': number('variance', '0.04', unit + '_squared'),
            'recovery': number('recovery', '0.9', 'fraction'),
            'attributed_signal': number('attributed', '0.6', 'fraction'),
            'total_signal': number('total', '0.8', 'fraction'),
            'condition_test': number('condition test', '0.8', 'fraction'),
            'condition_reference': number('condition reference', '1', 'fraction'),
            'assertion_prediction': number('assertion prediction', '1', unit),
            'alternative_prediction': number('alternative prediction', '0', unit),
        }}
    refs = [source, support, assertion]
    context = LiteratureContext('grading322', 'child', 'literature', (('literature', 'child'),),
        store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'version': 'literature_assignment_v1', 'question_context_refs': [support, assertion],
            'source_refs': [source], REQUESTED: list(COMPONENTS)}, {}, refs)
    return context, args, artifact
DESEQ = (b"Gene_Name\tbaseMean\tlog2FoldChange\tlfcSE\tstat\tpvalue\tpadj\n"
    b"geneA\t20\t-2\t0.5\t-4\t0.0001\t0.001\n"
    b"geneB\t0\tNA\tNA\tNA\tNA\tNA\n")
