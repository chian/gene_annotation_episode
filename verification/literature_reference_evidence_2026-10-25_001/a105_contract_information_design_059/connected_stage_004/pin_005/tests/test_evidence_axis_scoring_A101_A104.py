"""Execute the proposed real entry rubrics, using explicit native-number fixtures.

HemK values come from the preserved analysis; other stated numbers are arithmetic
fixtures, not claimed new measurements. No model, provider or external job runs.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.evidence_axis_scoring import score_axis


PUBLICATION=Path(__file__).resolve().parents[1]/'research/slotted_process_library/publications/2026-10-23-002'


def entry(axis_id):
    return json.loads((PUBLICATION/'entries'/f'{axis_id}.json').read_text())


def unit(axis, numbers, *, criteria=None, grades=None):
    """Explicit test evidence under the shared literature/dataset input schema."""
    criteria, grades = criteria or {}, grades or {}
    witness='fixture:received_evidence'
    definitions={row['metric_id']:row for row in axis['native_measurements']}
    measurements=[]
    for metric_id, number in numbers.items():
        definition=definitions[metric_id]
        atom={'type':'number','value':number,'unit_ref':None}
        measurements.append({'measurement_id':'fixture:comparison', 'fact':{
            'metric_id':metric_id,'observation':witness,'measurement_index':len(measurements),
            'native_field':definition['native_field'] or metric_id,'native_value':atom,
            'declared_native_unit':definition['units'][0],'direction':definition['direction'],
            'source':'fixture:source','source_subjects':['fixture:comparator'],
            'subjects':['fixture:target'],'dependencies':[],
            'method':{'provider':'explicit_numeric_fixture','recorded_source_version':'fixture_only',
                      'request_record':None}}})
    criterion_rows=[]
    for row in axis['judgment_criteria']:
        outcome=criteria.get(row['criterion_id'],'met')
        criterion_rows.append({'criterion_id':row['criterion_id'],'outcome':outcome,
            'witnesses':[] if outcome=='unknown' else [witness],
            'missing_inputs':[row['required_evidence'][0]] if outcome=='unknown' else []})
    return {'experiment_id':'fixture:original_comparison','representation_id':'fixture:representation',
        'origin':'dataset','measurements':measurements,'witnesses':[witness],
        'judgment':{'criteria':criterion_rows,
            'qualitative_grades':[{'criterion_id':row['criterion_id'],
                'grade':grades.get(row['criterion_id'],'unknown'),
                'witnesses':[witness] if grades.get(row['criterion_id'],'unknown')!='unknown' else []}
                for row in axis['qualitative_grading']],
            'evidence_chain':{key:[witness] for key in axis['transfer_chain']}}}


def routes(axis_id,numbers,**kwargs):
    axis=entry(axis_id)
    result=score_axis(axis,[unit(axis,numbers,**kwargs)],resolve_witness=lambda reference: reference.startswith('fixture:'))
    assert result['annotation_aggregate'] is None
    assert result['witness_validation']=='resolved'
    return {row['route_id']:row for row in result['experiments'][0]['routes']}


def test_preserved_hemk_native_score_and_identity_remain_distinct_numbers():
    result=routes('A101',{'alignment_score':254,'identity_fraction':63/192})
    assert result['sequence_raw']['score']==254
    assert result['sequence_raw']['score_unit']=='native_alignment_score'
    assert result['sequence_identity']['score']==pytest.approx(0.328125)
    assert result['sequence_identity']['polarity']=='non_discriminating'
    assert result['sequence_bits']['status']=='unavailable'
    assert result['sequence_bits']['score'] is None


def test_sequence_expectation_uses_native_log_not_a_probability_or_bit_score_sum():
    result=routes('A101',{'bitscore':72.4,'evalue':1e-20})
    assert result['sequence_bits']['score']==72.4
    assert result['sequence_log_expect']['score']==20
    assert result['sequence_log_expect']['score_unit']=='negative_log10_expected_random_matches'


def test_exact_function_transfer_cannot_use_native_score_when_specificity_is_contradicted():
    result=routes('A101',{'alignment_score':254},criteria={'specificity_not_overtransferred':'not_met'})
    assert result['sequence_raw']['status']=='ineligible'
    assert result['sequence_raw']['score'] is None
    assert result['sequence_raw']['reason']=='eligibility_not_met'


def test_missing_comparator_characterization_is_unknown_not_zero_support():
    result=routes('A101',{'bitscore':72.4},criteria={'comparator_property_characterized':'unknown'})
    assert result['sequence_bits']['status']=='unavailable'
    assert result['sequence_bits']['score'] is None
    assert result['sequence_bits']['reason']=='eligibility_unknown'


def test_structural_methods_retain_native_units_and_opposite_geometric_directions():
    result=routes('A102',{'tm_score':0.72,'dali_z_score':11.4,'aligned_structure_rmsd':1.8})
    assert result['structure_tm']['score']==0.72
    assert result['structure_tm']['score_unit']=='TM_score'
    assert result['structure_dali']['score']==11.4
    assert result['structure_dali']['score_unit']=='DALI_Z'
    assert result['structure_rmsd']['score']==1.8
    assert result['structure_rmsd']['direction']=='lower'
    assert result['structure_rmsd']['score_unit']=='angstrom'


def test_global_fold_without_corresponding_functional_geometry_does_not_score_exact_function():
    result=routes('A102',{'tm_score':0.99},criteria={'functional_geometry_corresponds':'unknown'})
    assert result['structure_tm']['score'] is None
    assert result['structure_tm']['reason']=='eligibility_unknown'


def test_context_native_association_significance_and_actual_counts_are_not_neighbor_homology():
    result=routes('A103',{'string_neighborhood_score':0.83,
        'gene_context_association_pvalue':0.001,
        'conserved_context_genomes':8,'evaluable_context_genomes':10,
        'neighbor_identification_bitscore':150})
    assert result['context_string_neighborhood']['score']==0.83
    assert result['context_log_significance']['score']==3
    assert result['context_conservation_fraction']['score']==0.8
    assert result['context_native']['score'] is None
    assert all(row['score']!=150 for row in result.values())


def test_context_ratio_does_not_invent_a_denominator_for_approximately_one_third():
    result=routes('A103',{'conserved_context_genomes':3})
    assert result['context_conservation_fraction']['score'] is None
    assert result['context_conservation_fraction']['reason']=='native_measurement_missing'


def test_phylogeny_native_branch_statistics_are_scored_separately_without_rescaling():
    result=routes('A104',{'bootstrap_clade_support_percent':92,
        'supported_clade_replicates':920,'evaluable_clade_replicates':1000,
        'posterior_clade_probability':0.97})
    assert result['phylogeny_bootstrap_percent']['score']==92
    assert result['phylogeny_bootstrap_percent']['score_unit']=='percent'
    assert result['phylogeny_bootstrap_fraction']['score']==0.92
    assert result['phylogeny_posterior_clade']['score']==0.97


@pytest.mark.parametrize(('grade','score'),[('contradicted',0),('plausible_only',1),('corroborated',2)])
def test_hgt_grade_scores_every_permitted_level_without_changing_native_tree_score(grade,score):
    result=routes('A104',{'bootstrap_clade_support_percent':92},
        criteria={'hgt_outlier_explanation':'not_met' if grade=='contradicted' else 'unknown'},
        grades={'hgt_outlier_explanation':grade})
    assert result['hgt_explanation_grade']['score']==score
    assert result['hgt_explanation_grade']['score_unit']=='ordinal_evidence_level'
    assert result['phylogeny_bootstrap_percent']['score']==92


def test_environmental_plausibility_cannot_create_a_phylogenetic_score_without_a_tree():
    result=routes('A104',{},criteria={'phylogeny_actually_reconstructed':'unknown'},
        grades={'hgt_outlier_explanation':'plausible_only'})
    assert result['hgt_explanation_grade']['score'] is None
    assert result['hgt_explanation_grade']['reason']=='eligibility_unknown'
    assert result['phylogeny_bootstrap_percent']['score'] is None


def test_native_structural_definitions_are_not_claimed_as_bound_extractors():
    axis=entry('A102')
    for metric in axis['native_measurements']:
        assert metric['binding']['kind']=='unbound'
        assert metric['binding']['measurement_name'] is None
        assert metric['binding']['json_pointer'] is None


@pytest.mark.parametrize(('axis_id','numbers','route_id'),[
    ('A101',{'identity_fraction':1.2},'sequence_identity'),
    ('A102',{'tm_score':1.2},'structure_tm'),
    ('A103',{'gene_context_association_pvalue':1.2},'context_log_significance'),
    ('A103',{'string_neighborhood_score':830},'context_string_neighborhood'),
    ('A104',{'bootstrap_clade_support_percent':120},'phylogeny_bootstrap_percent'),
    ('A104',{'posterior_clade_probability':1.2},'phylogeny_posterior_clade'),
])
def test_native_domain_violations_are_not_clipped_into_valid_support(axis_id,numbers,route_id):
    result=routes(axis_id,numbers)[route_id]
    assert result['score'] is None
    assert result['reason']=='native_value_outside_declared_range'


def test_expect_values_above_one_remain_valid_native_values_unlike_p_values():
    result=routes('A101',{'evalue':2})['sequence_log_expect']
    assert result['score']==pytest.approx(-0.3010299956639812)
    assert result['status']=='scored'


def test_supporting_context_count_cannot_exceed_the_actual_evaluable_genomes():
    result=routes('A103',{'conserved_context_genomes':12,'evaluable_context_genomes':10})
    assert result['context_conservation_fraction']['score'] is None
    assert result['context_conservation_fraction']['reason']=='ratio_numerator_exceeds_denominator'


def test_unassigned_hgt_grade_retains_possible_levels_without_fabricating_zero():
    result=routes('A104',{})['hgt_explanation_grade']
    assert result['score'] is None
    assert result['status']=='partial'
    assert result['score_bounds']['lower']==0
    assert result['score_bounds']['upper']==2
