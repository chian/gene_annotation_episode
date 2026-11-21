"""The declared criteria are the single source: the declaration, the grader, and the expert-facing index must agree.

Checks (for SPR, ITC, BLI and GCI; the index document check for SPR and ITC): every criterion has the declared fields; every
threshold constant is defined once, carries a review marker, and is used by a
criterion; the grader evaluates exactly the declared criteria, in order; every
(status, reason) a grader returns on real records is a declared case; the
grader holds no inline number besides structural 0, 1 and 2; and the index
document lists every criterion id and every constant with its current value.
"""
import ast
import inspect
import re
from pathlib import Path
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_alpha_criteria, literature_alpha_grader, literature_radioligand_criteria, literature_radioligand_grader, literature_spa_criteria, literature_spa_grader, literature_bli_criteria, literature_bli_grader, literature_elisa_criteria, literature_elisa_grader, literature_fcs_criteria, literature_fcs_grader, literature_fp_criteria, literature_fp_grader, literature_fret_criteria, literature_fret_grader, literature_gci_criteria, literature_gci_grader, literature_itc_criteria, literature_itc_grader, literature_mst_criteria, literature_mst_grader, literature_spr_criteria, literature_spr_grader, literature_trp_criteria, literature_trp_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_grader import grade_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import grade_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_grader import grade_spa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_pulldown_criteria, literature_pulldown_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import grade_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import pulldown_cases
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_emsa_criteria, literature_emsa_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import grade_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import emsa_cases
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_sec_criteria, literature_sec_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_grader import grade_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import sec_cases
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_dialysis_criteria, literature_dialysis_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import grade_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_dialysis_grader import variants as dialysis_variants
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_grader import grade_elisa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import grade_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_grader import grade_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_grader import grade_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_grader import grade_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import grade_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_grader import grade_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import grade_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests import alpha_cases, radioligand_cases, spa_cases, bli_cases, elisa_cases, fcs_cases, fp_cases, fret_cases, gci_cases, itc_cases, mst_cases, spr_cases, trp_cases

INDEX = Path(__file__).resolve().parents[7] / 'docs' / 'axis_restructure_20261117' / 'A105_GRADER_CRITERIA_INDEX.md'
FIELDS = {'id', 'question', 'reads', 'rule', 'thresholds', 'returns'}
STATUSES = {'supported', 'unknown', 'conflicting', 'not_applicable'}
GRADERS = {'spr': (literature_spr_criteria, literature_spr_grader, literature_spr_criteria.SPR_CRITERIA, {0, 1}), 'itc': (literature_itc_criteria, literature_itc_grader, literature_itc_criteria.ITC_CRITERIA, {0, 1}),
           'bli': (literature_bli_criteria, literature_bli_grader, literature_bli_criteria.BLI_CRITERIA, {0, 1}),
           'gci': (literature_gci_criteria, literature_gci_grader, literature_gci_criteria.GCI_CRITERIA, {0, 1}),
           'fp': (literature_fp_criteria, literature_fp_grader, literature_fp_criteria.FP_CRITERIA, {0, 1}),
           'fret': (literature_fret_criteria, literature_fret_grader, literature_fret_criteria.FRET_CRITERIA, {0, 1}),
           'mst': (literature_mst_criteria, literature_mst_grader, literature_mst_criteria.MST_CRITERIA, {0, 1}),
           'trp': (literature_trp_criteria, literature_trp_grader, literature_trp_criteria.TRP_CRITERIA, {0, 1}),
           'fcs': (literature_fcs_criteria, literature_fcs_grader, literature_fcs_criteria.FCS_CRITERIA, {0, 1}),
           'elisa': (literature_elisa_criteria, literature_elisa_grader, literature_elisa_criteria.ELISA_CRITERIA, {0, 1}),
           'alphascreen': (literature_alpha_criteria, literature_alpha_grader, literature_alpha_criteria.ALPHA_CRITERIA, {0, 1}),
           'radioligand': (literature_radioligand_criteria, literature_radioligand_grader, literature_radioligand_criteria.RADIOLIGAND_CRITERIA, {0, 1}),
           'spa': (literature_spa_criteria, literature_spa_grader, literature_spa_criteria.SPA_CRITERIA, {0, 1}),
           'pulldown': (literature_pulldown_criteria, literature_pulldown_grader, literature_pulldown_criteria.PULLDOWN_CRITERIA, {0, 1}),
           'emsa': (literature_emsa_criteria, literature_emsa_grader, literature_emsa_criteria.EMSA_CRITERIA, {0, 1}),
           'sec': (literature_sec_criteria, literature_sec_grader, literature_sec_criteria.SEC_CRITERIA, {0, 1}),
           'dialysis': (literature_dialysis_criteria, literature_dialysis_grader, literature_dialysis_criteria.DIALYSIS_CRITERIA, {0, 1})}


def constants(criteria_module):
    return {name: value for name, value in vars(criteria_module).items() if name.isupper() and name != 'VERSION' and not name.endswith('_CRITERIA')}


def bli_mutated():
    mutated = bli_cases.synthetic_record()
    mutated['facts']['nonspecific_binding_checked'] = bli_cases.fact('no')
    mutated['facts']['analyte_bivalent_or_oligomeric'] = bli_cases.fact('yes')
    mutated['facts']['single_estimate_method'] = bli_cases.fact('yes')
    mutated['quantities']['loading_level'] = bli_cases.point(3.0, 'nm', 'l', ['s'])
    mutated['quantities']['dissociation_time'] = bli_cases.point(5.0, 's', 't', ['s'])
    mutated['quantities']['kd_steady_state'] = {**mutated['quantities']['kd_steady_state'], 'status': 'unavailable', 'value': None}
    mutated['quantities']['kon'] = bli_cases.point(1.0e4, 'M^-1 s^-1', 'k', ['s'])
    mutated['concentration_series']['value'] = [1.0, 2.0]
    mutated['quantities']['replicate_count'] = bli_cases.point(2, 'count', 'n', ['s'])
    return mutated


def gci_mutated():
    mutated = gci_cases.synthetic_record()
    mutated['facts']['nonspecific_binding_checked'] = gci_cases.fact('no')
    mutated['facts']['analyte_bivalent_or_oligomeric'] = gci_cases.fact('yes')
    mutated['facts']['single_estimate_method'] = gci_cases.fact('yes')
    mutated['quantities']['immobilization_level'] = gci_cases.point(3000.0, 'pg/mm2', 'l', ['s'])
    mutated['quantities']['response_max'] = gci_cases.point(0.5, 'pg/mm2', 'r', ['s'])
    mutated['quantities']['kd_steady_state'] = {**mutated['quantities']['kd_steady_state'], 'status': 'unavailable', 'value': None}
    mutated['quantities']['kon'] = gci_cases.point(1.0e4, 'M^-1 s^-1', 'k', ['s'])
    mutated['concentration_series']['value'] = [1.0, 2.0]
    mutated['quantities']['replicate_count'] = gci_cases.point(2, 'count', 'n', ['s'])
    return mutated


def gci_pulsed(pulse_high):
    pulsed = gci_cases.synthetic_record()
    pulsed['facts']['repeated_pulse_kinetics_used'] = gci_cases.fact('yes', ['s'])
    pulsed['concentration_series']['value'] = [200.0 if pulse_high else 90.0]
    return pulsed


def fp_mutated():
    mutated = fp_cases.synthetic_record()
    mutated['facts']['nonspecific_binding_checked'] = fp_cases.fact('no')
    mutated['facts']['unlabelled_competitor_displaces'] = fp_cases.fact('no')
    mutated['facts']['tight_binding_considered'] = fp_cases.fact('no')
    mutated['facts']['single_estimate_method'] = fp_cases.fact('yes')
    mutated['quantities']['tracer_concentration'] = fp_cases.point(200.0, 'nM', 't', ['s'])
    mutated['quantities']['signal_maximum'] = fp_cases.point(80.0, 'mP', 'm', ['s'])
    mutated['quantities']['total_intensity_change'] = fp_cases.point(60.0, 'percent', 'c', ['s'])
    mutated['quantities']['ki'] = {**mutated['quantities']['ki'], 'status': 'unavailable', 'value': None}
    mutated['quantities']['replicate_count'] = fp_cases.point(2, 'count', 'n', ['s'])
    mutated['concentration_series']['value'] = [1.0, 2.0]
    mutated['fit_model'] = 'competitive_binding'
    return mutated


def fp_variants():
    out = []
    for answer, minutes, change in (('unknown', 3.0, 5.0), ('unknown', 30.0, 5.0), ('no', 30.0, 5.0)):
        variant = fp_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = fp_cases.fact(answer)
        variant['facts']['intensity_change_checked'] = fp_cases.fact(answer)
        variant['quantities']['incubation_time'] = fp_cases.point(minutes, 'min', 'i', ['s'])
        variant['quantities']['total_intensity_change'] = fp_cases.point(change * 10, 'percent', 'c', ['s'])
        out.append(variant)
    direct = fp_cases.synthetic_record()
    direct['fit_model'], direct['assay_format'] = 'hill', 'competition'
    direct['quantities']['signal_minimum'] = fp_cases.point(0.2, 'r', 'a', ['s'])
    direct['quantities']['signal_maximum'] = fp_cases.point(0.1, 'r', 'b', ['s'])
    out.append(direct)
    return out


def fret_mutated():
    mutated = fret_cases.synthetic_record()
    mutated['facts']['crosstalk_corrected'] = fret_cases.fact('no')
    mutated['facts']['nonspecific_binding_checked'] = fret_cases.fact('no')
    mutated['facts']['unlabelled_competitor_displaces'] = fret_cases.fact('no')
    mutated['facts']['tight_binding_considered'] = fret_cases.fact('no')
    mutated['facts']['labelling_does_not_alter_binding'] = fret_cases.fact('no')
    mutated['facts']['single_estimate_method'] = fret_cases.fact('yes')
    mutated['donor_acceptor_pair'] = 'fluorescent_protein_pair'
    mutated['quantities']['donor_concentration'] = fret_cases.point(200.0, 'nM', 'd', ['s'])
    mutated['quantities']['acceptor_concentration'] = fret_cases.point(300.0, 'nM', 'a', ['s'])
    mutated['quantities']['ratio_maximum'] = fret_cases.point(0.5, 'ratio', 'm', ['s'])
    mutated['quantities']['ki'] = {**mutated['quantities']['ki'], 'status': 'unavailable', 'value': None}
    mutated['quantities']['replicate_count'] = fret_cases.point(2, 'count', 'n', ['s'])
    mutated['concentration_series']['value'] = [1.0, 2.0]
    mutated['fit_model'] = 'competitive_binding'
    return mutated


def fret_variants():
    out = []
    for answer, minutes in (('unknown', 3.0), ('unknown', 30.0), ('no', 30.0)):
        variant = fret_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = fret_cases.fact(answer)
        variant['facts']['indirect_labelling_used'] = fret_cases.fact('yes' if answer == 'unknown' else 'unknown')
        variant['facts']['labelling_does_not_alter_binding'] = fret_cases.fact(answer)
        variant['facts']['crosstalk_corrected'] = fret_cases.fact(answer)
        variant['quantities']['incubation_time'] = fret_cases.point(minutes, 'min', 'i', ['s'])
        out.append(variant)
    for delay, window in ((10.0, 400.0), (100.0, 50.0)):
        gated = fret_cases.synthetic_record()
        gated['quantities']['delay_time'] = fret_cases.point(delay, 'us', 'd', ['s'])
        gated['quantities']['integration_time'] = fret_cases.point(window, 'us', 'w', ['s'])
        out.append(gated)
    steady = fret_cases.synthetic_record()
    steady['facts']['time_resolved_read'] = fret_cases.fact('no')
    out.append(steady)
    ungated = fret_cases.synthetic_record()
    ungated['quantities']['delay_time'] = {**ungated['quantities']['delay_time'], 'status': 'unavailable', 'value': None}
    out.append(ungated)
    unstated = fret_cases.synthetic_record()
    unstated['facts']['time_resolved_read'] = fret_cases.fact('unknown')
    unstated['facts']['indirect_labelling_used'] = fret_cases.fact('unknown')
    unstated['facts']['labelling_does_not_alter_binding'] = fret_cases.fact('unknown')
    unstated['quantities']['delay_time'] = {**unstated['quantities']['delay_time'], 'status': 'unavailable', 'value': None}
    unstated['facts']['donor_only_control_measured'] = fret_cases.fact('not_applicable')
    unstated['facts']['acceptor_only_control_measured'] = fret_cases.fact('not_applicable')
    unstated['facts']['crosstalk_corrected'] = fret_cases.fact('not_applicable')
    out.append(unstated)
    direct = fret_cases.synthetic_record()
    direct['fit_model'], direct['assay_format'] = 'hill', 'competition'
    direct['quantities']['ratio_minimum'] = fret_cases.point(2.0, 'ratio', 'a', ['s'])
    direct['quantities']['ratio_maximum'] = fret_cases.point(1.0, 'ratio', 'b', ['s'])
    out.append(direct)
    return out


def mst_mutated():
    mutated = mst_cases.synthetic_record()
    mutated['facts']['initial_fluorescence_consistent'] = mst_cases.fact('no', ['s'])
    mutated['facts']['fluorescence_intensity_in_range'] = mst_cases.fact('no', ['s'])
    mutated['facts']['aggregation_or_adsorption_checked'] = mst_cases.fact('no', ['s'])
    mutated['facts']['nonspecific_binding_checked'] = mst_cases.fact('no', ['s'])
    mutated['facts']['tight_binding_considered'] = mst_cases.fact('no', ['s'])
    mutated['facts']['labelling_does_not_alter_binding'] = mst_cases.fact('no', ['s'])
    mutated['facts']['single_estimate_method'] = mst_cases.fact('yes', ['s'])
    mutated['quantities']['labelled_concentration'] = mst_cases.point(200.0, 'nM', 'l', ['s'])
    mutated['quantities']['signal_to_noise'] = mst_cases.point(2.0, 'ratio', 'n', ['s'])
    mutated['quantities']['fhot_time'] = mst_cases.point(0.5, 's', 'f', ['s'])
    mutated['quantities']['ki'] = {**mutated['quantities']['ki'], 'status': 'unavailable', 'value': None}
    mutated['quantities']['replicate_count'] = mst_cases.point(2, 'count', 'n', ['s'])
    mutated['concentration_series']['value'] = [1.0, 2.0]
    mutated['fit_model'] = 'competitive_binding'
    return mutated


def mst_variants():
    out = []
    for answer, minutes in (('unknown', 3.0), ('unknown', 30.0), ('no', 30.0)):
        variant = mst_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = mst_cases.fact(answer, ['s'])
        variant['facts']['labelling_does_not_alter_binding'] = mst_cases.fact(answer, ['s'])
        variant['facts']['initial_fluorescence_consistent'] = mst_cases.fact(answer, ['s'])
        variant['facts']['initial_fluorescence_checked'] = mst_cases.fact(answer, ['s'])
        variant['quantities']['incubation_time'] = mst_cases.point(minutes, 'min', 'i', ['s'])
        variant['quantities']['fnorm_amplitude'] = mst_cases.point(minutes / 10, 'permille', 'a', ['s'])
        out.append(variant)
    for readout in ('t_jump', 'initial_fluorescence', None):
        read = mst_cases.synthetic_record()
        read['readout_signal'] = readout
        out.append(read)
    ungated = mst_cases.synthetic_record()
    ungated['quantities']['fhot_time'] = {**ungated['quantities']['fhot_time'], 'status': 'unavailable', 'value': None}
    ungated['quantities']['titration_point_count'] = mst_cases.point(8, 'count', 'n', ['s'])
    ungated['concentration_series'] = {**ungated['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(ungated)
    label_free = mst_cases.synthetic_record()
    label_free['label_type'] = 'label_free_intrinsic_fluorescence'
    label_free['facts']['labelling_does_not_alter_binding'] = mst_cases.fact('unknown')
    out.append(label_free)
    unlabelled = mst_cases.synthetic_record()
    unlabelled['label_type'] = None
    unlabelled['facts']['labelling_does_not_alter_binding'] = mst_cases.fact('unknown')
    out.append(unlabelled)
    not_applicable = mst_cases.synthetic_record()
    not_applicable['label_type'] = None
    not_applicable['facts']['labelling_does_not_alter_binding'] = mst_cases.fact('not_applicable')
    not_applicable['facts']['initial_fluorescence_consistent'] = mst_cases.fact('not_applicable')
    not_applicable['facts']['initial_fluorescence_checked'] = mst_cases.fact('not_applicable')
    out.append(not_applicable)
    unchecked = mst_cases.synthetic_record()
    unchecked['facts']['initial_fluorescence_consistent'] = mst_cases.fact('unknown')
    unchecked['facts']['initial_fluorescence_checked'] = mst_cases.fact('no', ['s'])
    out.append(unchecked)
    direct = mst_cases.synthetic_record()
    direct['fit_model'], direct['assay_format'] = 'hill', 'competition'
    direct['quantities']['fnorm_amplitude'] = mst_cases.point(2.0, 'permille', 'b', ['s'])
    out.append(direct)
    return out


def trp_mutated():
    mutated = trp_cases.synthetic_record()
    mutated['facts']['inner_filter_corrected'] = trp_cases.fact('no')
    mutated['facts']['ligand_absorbance_negligible'] = trp_cases.fact('no')
    mutated['facts']['dilution_corrected'] = trp_cases.fact('no')
    mutated['facts']['buffer_blank_subtracted'] = trp_cases.fact('no')
    mutated['facts']['ligand_only_control_measured'] = trp_cases.fact('no')
    mutated['facts']['nonbinding_control_done'] = trp_cases.fact('no')
    mutated['facts']['trp_analogue_control_done'] = trp_cases.fact('no')
    mutated['facts']['signal_localised_to_binding_site'] = trp_cases.fact('no')
    mutated['facts']['signal_saturates'] = trp_cases.fact('no')
    mutated['facts']['quenching_is_static'] = trp_cases.fact('no')
    mutated['facts']['photobleaching_checked'] = trp_cases.fact('no')
    mutated['facts']['tight_binding_considered'] = trp_cases.fact('no')
    mutated['quantities']['protein_concentration'] = trp_cases.point(200.0, 'nM', 'p', ['s'])
    mutated['quantities']['fluorescence_change'] = trp_cases.point(2.0, 'percent', 'c', ['s'])
    mutated['quantities']['ligand_absorbance'] = trp_cases.point(0.2, 'AU', 'a', ['s'])
    mutated['quantities']['added_volume_fraction'] = trp_cases.point(15.0, 'percent', 'v', ['s'])
    mutated['quantities']['replicate_count'] = trp_cases.point(2, 'count', 'n', ['s'])
    mutated['concentration_series']['value'] = [1.0, 2.0]
    mutated['fit_model'] = 'stern_volmer'
    return mutated


def trp_variants():
    out = []
    for answer, minutes in (('unknown', 1.0), ('unknown', 30.0), ('no', 30.0)):
        variant = trp_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = trp_cases.fact(answer)
        variant['facts']['inner_filter_corrected'] = trp_cases.fact(answer)
        variant['facts']['ligand_absorbance_negligible'] = trp_cases.fact(answer)
        variant['facts']['dilution_corrected'] = trp_cases.fact(answer)
        variant['quantities']['incubation_time'] = trp_cases.point(minutes, 'min', 'i', ['s'])
        variant['quantities']['ligand_absorbance'] = {**variant['quantities']['ligand_absorbance'], 'status': 'unavailable', 'value': None}
        variant['quantities']['added_volume_fraction'] = {**variant['quantities']['added_volume_fraction'], 'status': 'unavailable', 'value': None}
        out.append(variant)
    for wavelength in (280.0, None):
        excited = trp_cases.synthetic_record()
        if wavelength is None:
            excited['quantities']['excitation_wavelength'] = {**excited['quantities']['excitation_wavelength'], 'status': 'unavailable', 'value': None}
        else:
            excited['quantities']['excitation_wavelength'] = trp_cases.point(wavelength, 'nm', 'e', ['s'])
        out.append(excited)
    uncorrected = trp_cases.synthetic_record()
    uncorrected['facts']['inner_filter_corrected'] = trp_cases.fact('no')
    uncorrected['facts']['dilution_corrected'] = trp_cases.fact('no')
    out.append(uncorrected)
    ungated = trp_cases.synthetic_record()
    ungated['quantities']['titration_point_count'] = trp_cases.point(6, 'count', 'n', ['s'])
    ungated['concentration_series'] = {**ungated['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(ungated)
    not_applicable = trp_cases.synthetic_record()
    for name in ('inner_filter_corrected', 'ligand_absorbance_negligible', 'dilution_corrected', 'nonbinding_control_done', 'trp_analogue_control_done', 'signal_localised_to_binding_site'):
        not_applicable['facts'][name] = trp_cases.fact('not_applicable')
    not_applicable['quantities']['ligand_absorbance'] = {**not_applicable['quantities']['ligand_absorbance'], 'status': 'unavailable', 'value': None}
    not_applicable['quantities']['added_volume_fraction'] = {**not_applicable['quantities']['added_volume_fraction'], 'status': 'unavailable', 'value': None}
    out.append(not_applicable)
    unstated = trp_cases.synthetic_record()
    unstated['fit_model'] = None
    for name in ('nonbinding_control_done', 'trp_analogue_control_done', 'signal_localised_to_binding_site'):
        unstated['facts'][name] = trp_cases.fact('unknown')
    out.append(unstated)
    return out


def fcs_mutated():
    mutated = fcs_cases.synthetic_record()
    for name in ('confocal_volume_calibrated', 'triplet_state_modelled', 'free_diffusion_time_fixed', 'brightness_change_accounted', 'crosstalk_corrected', 'background_corrected', 'aggregates_checked', 'photobleaching_or_saturation_checked', 'surface_adsorption_prevented', 'labelling_does_not_alter_binding', 'nonbinding_control_done', 'tight_binding_considered', 'equilibrium_reached', 'independent_titrations'):
        mutated['facts'][name] = fcs_cases.fact('no', ['s'])
    mutated['quantities']['labelled_concentration'] = fcs_cases.point(200.0, 'nM', 'l', ['s'])
    mutated['quantities']['particle_number'] = fcs_cases.point(40.0, 'molecules', 'n', ['s'])
    mutated['quantities']['bound_diffusion_time'] = fcs_cases.point(66.0, 'us', 'b', ['s'])
    mutated['quantities']['fraction_bound_maximum'] = fcs_cases.point(50.0, 'percent', 'f', ['s'])
    mutated['quantities']['measurement_time'] = fcs_cases.point(10.0, 's', 't', ['s'])
    mutated['quantities']['measurement_repeat_count'] = fcs_cases.point(2, 'count', 'r', ['s'])
    mutated['quantities']['replicate_count'] = fcs_cases.point(2, 'count', 'n', ['s'])
    mutated['concentration_series']['value'] = [1.0, 2.0]
    return mutated


def fcs_variants():
    out = []
    for answer, minutes in (('unknown', 2.0), ('unknown', 30.0), ('no', 30.0)):
        variant = fcs_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = fcs_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['facts']['free_diffusion_time_fixed'] = fcs_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['facts']['crosstalk_corrected'] = fcs_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['quantities']['incubation_time'] = fcs_cases.point(minutes, 'min', 'i', ['s'])
        out.append(variant)
    for readout in ('cross_correlation', 'brightness', None):
        read = fcs_cases.synthetic_record()
        read['readout_signal'] = readout
        read['facts']['crosstalk_corrected'] = fcs_cases.fact('unknown')
        out.append(read)
    for model in ('one_component', 'anomalous', None):
        modelled = fcs_cases.synthetic_record()
        modelled['diffusion_model'] = model
        out.append(modelled)
    not_diffusion = fcs_cases.synthetic_record()
    not_diffusion['readout_signal'] = 'cross_correlation'
    not_diffusion['diffusion_model'] = None
    for name in ('free_diffusion_time', 'bound_diffusion_time', 'free_diffusion_coefficient', 'bound_diffusion_coefficient', 'mass_ratio'):
        not_diffusion['quantities'][name] = {**not_diffusion['quantities'][name], 'status': 'unavailable', 'value': None}
    out.append(not_diffusion)
    no_pair = fcs_cases.synthetic_record()
    for name in ('bound_diffusion_time', 'free_diffusion_coefficient'):
        no_pair['quantities'][name] = {**no_pair['quantities'][name], 'status': 'unavailable', 'value': None}
    no_pair['diffusion_model'] = 'one_component'
    out.append(no_pair)
    ungated = fcs_cases.synthetic_record()
    ungated['quantities']['titration_point_count'] = fcs_cases.point(6, 'count', 'n', ['s'])
    ungated['concentration_series'] = {**ungated['concentration_series'], 'status': 'unavailable', 'value': None}
    ungated['quantities']['measurement_repeat_count'] = {**ungated['quantities']['measurement_repeat_count'], 'status': 'unavailable', 'value': None}
    ungated['quantities']['measurement_time'] = fcs_cases.point(10.0, 's', 't', ['s'])
    out.append(ungated)
    untimed = fcs_cases.synthetic_record()
    untimed['quantities']['measurement_time'] = {**untimed['quantities']['measurement_time'], 'status': 'unavailable', 'value': None}
    untimed['quantities']['fraction_bound_maximum'] = {**untimed['quantities']['fraction_bound_maximum'], 'status': 'unavailable', 'value': None}
    untimed['quantities']['particle_number'] = {**untimed['quantities']['particle_number'], 'status': 'unavailable', 'value': None}
    untimed['quantities']['labelled_concentration'] = {**untimed['quantities']['labelled_concentration'], 'status': 'unavailable', 'value': None}
    untimed['facts']['labelled_partner_at_or_below_kd'] = fcs_cases.fact('unknown')
    out.append(untimed)
    mismatched = fcs_cases.synthetic_record()
    mismatched['quantities']['mass_ratio'] = fcs_cases.point(1.5, 'ratio', 'm', ['s'])
    mismatched['quantities']['labelled_concentration'] = fcs_cases.point(0.1, 'nM', 'l', ['s'])
    mismatched['quantities']['particle_number'] = {**mismatched['quantities']['particle_number'], 'status': 'unavailable', 'value': None}
    mismatched['fit_model'] = None
    out.append(mismatched)
    return out


def elisa_mutated():
    mutated = elisa_cases.synthetic_record()
    for name in ('blank_subtracted', 'nonspecific_binding_checked', 'saturation_reached', 'signal_in_linear_range', 'wash_dissociation_considered', 'equilibrium_reached', 'avidity_excluded', 'coated_protein_active', 'detection_does_not_interfere', 'independent_experiments'):
        mutated['facts'][name] = elisa_cases.fact('no', ['s'])
    mutated['quantities']['signal_maximum'] = elisa_cases.point(0.2, 'OD', 'm', ['s'])
    mutated['quantities']['replicate_count'] = elisa_cases.point(2, 'count', 'n', ['s'])
    mutated['quantities']['ki'] = elisa_cases.point(200.0, 'nM', 'k', ['s'])
    mutated['assay_format'] = 'competition'
    mutated['fit_model'] = 'hill'
    mutated['concentration_series']['value'] = [1.0, 2.0]
    return mutated


def elisa_variants():
    out = []
    for answer, minutes in (('unknown', 2.0), ('unknown', 60.0), ('no', 60.0)):
        variant = elisa_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = elisa_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['facts']['signal_in_linear_range'] = elisa_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['quantities']['incubation_time'] = elisa_cases.point(minutes, 'min', 'i', ['s'])
        out.append(variant)
    for maximum in (3.0, None):
        read = elisa_cases.synthetic_record()
        read['facts']['signal_in_linear_range'] = elisa_cases.fact('unknown')
        if maximum is None:
            read['quantities']['signal_maximum'] = {**read['quantities']['signal_maximum'], 'status': 'unavailable', 'value': None}
        else:
            read['quantities']['signal_maximum'] = elisa_cases.point(maximum, 'OD', 'm', ['s'])
        out.append(read)
    for model, form in (('competitive_binding', 'saturation_titration'), ('competitive_binding', 'competition'), ('hill', 'competition'), (None, None)):
        modelled = elisa_cases.synthetic_record()
        modelled['fit_model'], modelled['assay_format'] = model, form
        out.append(modelled)
    ungated = elisa_cases.synthetic_record()
    ungated['quantities']['titration_point_count'] = elisa_cases.point(6, 'count', 'n', ['s'])
    ungated['concentration_series'] = {**ungated['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(ungated)
    missing_series = elisa_cases.synthetic_record()
    missing_series['concentration_series'] = {**missing_series['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(missing_series)
    for kind, name in (('half_maximal', 'kd'), ('none', 'ki')):
        single = elisa_cases.synthetic_record()
        single['quantities'][name] = {**single['quantities'][name], 'status': 'unavailable', 'value': None}
        single['facts']['single_estimate_method'] = elisa_cases.fact('yes' if kind == 'half_maximal' else 'unknown')
        out.append(single)
    only_half = elisa_cases.synthetic_record()
    for name in ('kd', 'ki', 'ec50'):
        only_half['quantities'][name] = {**only_half['quantities'][name], 'status': 'unavailable', 'value': None}
    out.append(only_half)
    unreplicated = elisa_cases.synthetic_record()
    unreplicated['facts']['independent_experiments'] = elisa_cases.fact('unknown')
    out.append(unreplicated)
    return out


def alpha_mutated():
    mutated = alpha_cases.synthetic_record()
    for name in ('counter_screen_done', 'hook_effect_handled', 'partner_concentration_below_kd', 'signal_in_linear_range', 'equilibrium_reached', 'nonspecific_binding_checked', 'capture_does_not_alter_binding', 'light_protected', 'avidity_excluded', 'independent_experiments'):
        mutated['facts'][name] = alpha_cases.fact('no', ['s'])
    mutated['quantities']['signal_to_background'] = alpha_cases.point(4.0, 'ratio', 'm', ['s'])
    mutated['quantities']['z_prime'] = alpha_cases.point(0.3, 'ratio', 'z', ['s'])
    mutated['quantities']['replicate_count'] = alpha_cases.point(2, 'count', 'n', ['s'])
    mutated['quantities']['ki'] = alpha_cases.point(200.0, 'nM', 'k', ['s'])
    mutated['assay_format'] = 'competition'
    mutated['fit_model'] = 'one_site'
    mutated['concentration_series']['value'] = [1.0, 2.0]
    return mutated


def alpha_variants():
    out = []
    for answer, minutes in (('unknown', 2.0), ('unknown', 60.0), ('no', 60.0)):
        variant = alpha_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = alpha_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['quantities']['incubation_time'] = alpha_cases.point(minutes, 'min', 'i', ['s'])
        out.append(variant)
    for model, form in (('competitive_binding', 'saturation_titration'), ('competitive_binding', 'competition'), ('bell_shaped_hook', 'competition'), ('quadratic', 'saturation_titration'), (None, None)):
        modelled = alpha_cases.synthetic_record()
        modelled['fit_model'], modelled['assay_format'] = model, form
        out.append(modelled)
    ungated = alpha_cases.synthetic_record()
    ungated['quantities']['titration_point_count'] = alpha_cases.point(6, 'count', 'n', ['s'])
    ungated['concentration_series'] = {**ungated['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(ungated)
    missing_series = alpha_cases.synthetic_record()
    missing_series['concentration_series'] = {**missing_series['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(missing_series)
    for kind, name in (('half_maximal', 'kd'), ('none', 'ki')):
        single = alpha_cases.synthetic_record()
        single['quantities'][name] = {**single['quantities'][name], 'status': 'unavailable', 'value': None}
        single['facts']['single_estimate_method'] = alpha_cases.fact('yes' if kind == 'half_maximal' else 'unknown', ['s'] if kind == 'half_maximal' else [])
        out.append(single)
    windowed = alpha_cases.synthetic_record()
    windowed['quantities']['signal_to_background'] = {**windowed['quantities']['signal_to_background'], 'status': 'unavailable', 'value': None}
    windowed['quantities']['signal_maximum'] = alpha_cases.point(5000.0, 'cps', 'm', ['s'])
    out.append(windowed)
    no_window = alpha_cases.synthetic_record()
    for name in ('signal_to_background', 'signal_maximum', 'z_prime'):
        no_window['quantities'][name] = {**no_window['quantities'][name], 'status': 'unavailable', 'value': None}
    out.append(no_window)
    unreplicated = alpha_cases.synthetic_record()
    unreplicated['facts']['independent_experiments'] = alpha_cases.fact('unknown')
    out.append(unreplicated)
    return out


def radioligand_mutated():
    mutated = radioligand_cases.synthetic_record()
    for name in ('ligand_depletion_checked', 'nonspecific_binding_determined', 'equilibrium_reached', 'radioligand_purity_checked', 'filter_binding_checked', 'wash_dissociation_considered', 'nonlinear_fit_used', 'cheng_prusoff_applied_with_own_kd', 'independent_experiments'):
        mutated['facts'][name] = radioligand_cases.fact('no', ['s'])
    mutated['quantities']['percent_bound'] = radioligand_cases.point(40.0, 'percent', 'p', ['s'])
    mutated['quantities']['nonspecific_fraction'] = radioligand_cases.point(70.0, 'percent', 'f', ['s'])
    mutated['quantities']['nonspecific_excess'] = radioligand_cases.point(20.0, 'ratio', 'e', ['s'])
    mutated['quantities']['radioligand_concentration'] = radioligand_cases.point(20.0, 'nM', 'l', ['s'])
    mutated['quantities']['hill_slope'] = radioligand_cases.point(0.5, 'ratio', 'h', ['s'])
    mutated['quantities']['replicate_count'] = radioligand_cases.point(2, 'count', 'n', ['s'])
    mutated['assay_format'] = 'saturation'
    mutated['fit_model'] = 'competitive_binding'
    mutated['concentration_series']['value'] = [1.0, 2.0]
    return mutated


def radioligand_variants():
    out = []
    for answer, minutes in (('unknown', 2.0), ('unknown', 60.0), ('no', 60.0)):
        variant = radioligand_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = radioligand_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['quantities']['incubation_time'] = radioligand_cases.point(minutes, 'min', 'i', ['s'])
        out.append(variant)
    for method in ('scintillation_proximity', 'centrifugation', None):
        variant = radioligand_cases.synthetic_record()
        variant['separation_method'] = method
        variant['facts']['filter_binding_checked'] = radioligand_cases.fact('unknown')
        variant['facts']['wash_dissociation_considered'] = radioligand_cases.fact('unknown')
        out.append(variant)
    for model, form in (('competitive_binding', 'saturation'), ('competitive_binding', 'competition'), ('two_site', 'competition'), (None, None)):
        modelled = radioligand_cases.synthetic_record()
        modelled['fit_model'], modelled['assay_format'] = model, form
        out.append(modelled)
    ungated = radioligand_cases.synthetic_record()
    ungated['quantities']['titration_point_count'] = radioligand_cases.point(6, 'count', 'n', ['s'])
    ungated['concentration_series'] = {**ungated['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(ungated)
    missing_series = radioligand_cases.synthetic_record()
    missing_series['concentration_series'] = {**missing_series['concentration_series'], 'status': 'unavailable', 'value': None}
    for name in ('radioligand_range_lowest', 'radioligand_range_highest'):
        missing_series['quantities'][name] = {**missing_series['quantities'][name], 'status': 'unavailable', 'value': None}
    out.append(missing_series)
    unmeasured = radioligand_cases.synthetic_record()
    for name in ('percent_bound', 'nonspecific_fraction', 'nonspecific_excess', 'nonspecific_ligand_concentration', 'hill_slope', 'radioligand_concentration', 'ic50'):
        unmeasured['quantities'][name] = {**unmeasured['quantities'][name], 'status': 'unavailable', 'value': None}
    unmeasured['facts']['ligand_depletion_checked'] = radioligand_cases.fact('unknown')
    unmeasured['facts']['cheng_prusoff_applied_with_own_kd'] = radioligand_cases.fact('unknown')
    out.append(unmeasured)
    saturation_only = radioligand_cases.synthetic_record()
    for name in ('ki', 'ic50'):
        saturation_only['quantities'][name] = {**saturation_only['quantities'][name], 'status': 'unavailable', 'value': None}
    saturation_only['facts']['cheng_prusoff_applied_with_own_kd'] = radioligand_cases.fact('unknown')
    out.append(saturation_only)
    disagreeing = radioligand_cases.synthetic_record()
    disagreeing['quantities']['ki'] = radioligand_cases.point(20.0, 'nM', 'k', ['s'])
    out.append(disagreeing)
    unreplicated = radioligand_cases.synthetic_record()
    unreplicated['facts']['independent_experiments'] = radioligand_cases.fact('unknown')
    out.append(unreplicated)
    return out


def spa_mutated():
    mutated = spa_cases.synthetic_record()
    for name in ('homogeneous_no_wash_format', 'nonspecific_binding_determined', 'nonproximity_signal_checked', 'bead_only_control_done', 'equilibrium_reached', 'ligand_depletion_checked', 'quench_interference_checked', 'bead_settling_controlled', 'radioligand_purity_checked', 'nonlinear_fit_used', 'cheng_prusoff_applied_with_own_kd', 'independent_experiments'):
        mutated['facts'][name] = spa_cases.fact('no', ['s'])
    mutated['quantities']['percent_bound'] = spa_cases.point(40.0, 'percent', 'p', ['s'])
    mutated['quantities']['nonspecific_fraction'] = spa_cases.point(70.0, 'percent', 'f', ['s'])
    mutated['quantities']['nonspecific_excess'] = spa_cases.point(20.0, 'ratio', 'e', ['s'])
    mutated['quantities']['bead_only_fraction'] = spa_cases.point(60.0, 'percent', 'b', ['s'])
    mutated['quantities']['radioligand_concentration'] = spa_cases.point(20.0, 'nM', 'l', ['s'])
    mutated['quantities']['hill_slope'] = spa_cases.point(0.5, 'ratio', 'h', ['s'])
    mutated['quantities']['replicate_count'] = spa_cases.point(2, 'count', 'n', ['s'])
    mutated['assay_format'] = 'saturation'
    mutated['fit_model'] = 'competitive_binding'
    mutated['concentration_series']['value'] = [1.0, 2.0]
    return mutated


def spa_variants():
    out = []
    for answer, minutes in (('unknown', 2.0), ('unknown', 120.0), ('no', 120.0)):
        variant = spa_cases.synthetic_record()
        variant['facts']['equilibrium_reached'] = spa_cases.fact(answer, ['s'] if answer == 'no' else [])
        variant['quantities']['incubation_time'] = spa_cases.point(minutes, 'min', 'i', ['s'])
        out.append(variant)
    for model, form in (('competitive_binding', 'saturation'), ('competitive_binding', 'competition'), ('two_site', 'competition'), (None, None)):
        modelled = spa_cases.synthetic_record()
        modelled['fit_model'], modelled['assay_format'] = model, form
        out.append(modelled)
    ungated = spa_cases.synthetic_record()
    ungated['quantities']['titration_point_count'] = spa_cases.point(6, 'count', 'n', ['s'])
    ungated['concentration_series'] = {**ungated['concentration_series'], 'status': 'unavailable', 'value': None}
    out.append(ungated)
    missing_series = spa_cases.synthetic_record()
    missing_series['concentration_series'] = {**missing_series['concentration_series'], 'status': 'unavailable', 'value': None}
    for name in ('radioligand_range_lowest', 'radioligand_range_highest'):
        missing_series['quantities'][name] = {**missing_series['quantities'][name], 'status': 'unavailable', 'value': None}
    out.append(missing_series)
    unmeasured = spa_cases.synthetic_record()
    for name in ('percent_bound', 'nonspecific_fraction', 'nonspecific_excess', 'nonspecific_ligand_concentration', 'bead_only_fraction', 'hill_slope', 'radioligand_concentration', 'ic50'):
        unmeasured['quantities'][name] = {**unmeasured['quantities'][name], 'status': 'unavailable', 'value': None}
    unmeasured['facts']['ligand_depletion_checked'] = spa_cases.fact('unknown')
    unmeasured['facts']['bead_only_control_done'] = spa_cases.fact('unknown')
    unmeasured['facts']['cheng_prusoff_applied_with_own_kd'] = spa_cases.fact('unknown')
    out.append(unmeasured)
    saturation_only = spa_cases.synthetic_record()
    for name in ('ki', 'ic50'):
        saturation_only['quantities'][name] = {**saturation_only['quantities'][name], 'status': 'unavailable', 'value': None}
    saturation_only['facts']['cheng_prusoff_applied_with_own_kd'] = spa_cases.fact('unknown')
    out.append(saturation_only)
    disagreeing = spa_cases.synthetic_record()
    disagreeing['quantities']['ki'] = spa_cases.point(20.0, 'nM', 'k', ['s'])
    out.append(disagreeing)
    unreplicated = spa_cases.synthetic_record()
    unreplicated['facts']['independent_experiments'] = spa_cases.fact('unknown')
    out.append(unreplicated)
    return out


def pulldown_mutated():
    mutated = pulldown_cases.synthetic_record()
    for name in ('prey_detected_in_eluate', 'prey_absent_in_negative_control', 'bait_minus_control_done', 'input_lane_shown', 'reciprocal_done', 'competition_disrupts_interaction', 'interaction_survives_nuclease', 'endogenous_expression_levels', 'quantification_with_normalization', 'specificity_validated', 'independent_experiments'):
        mutated['facts'][name] = pulldown_cases.fact('no', ['s'])
    mutated['quantities']['nacl_wash'] = pulldown_cases.point(100.0, 'mM', 'n', ['s'])
    mutated['quantities']['wash_count'] = pulldown_cases.point(1, 'count', 'w', ['s'])
    mutated['quantities']['incubation_time'] = pulldown_cases.point(10.0, 'min', 'i', ['s'])
    mutated['quantities']['fold_enrichment'] = pulldown_cases.point(1.5, 'ratio', 'e', ['s'])
    mutated['quantities']['replicate_count'] = pulldown_cases.point(2, 'count', 'r', ['s'])
    return mutated


def pulldown_variants():
    out = []
    detergent = pulldown_cases.synthetic_record()
    detergent['quantities']['detergent_wash'] = pulldown_cases.point(0.01, 'percent', 'd', ['s'])
    out.append(detergent)
    unwashed = pulldown_cases.synthetic_record()
    for name in ('nacl_wash', 'detergent_wash', 'wash_count', 'incubation_time', 'fold_enrichment', 'replicate_count'):
        unwashed['quantities'][name] = {**unwashed['quantities'][name], 'status': 'unavailable', 'value': None}
    out.append(unwashed)
    for done, absent in (('no', 'unknown'), ('yes', 'unknown'), ('not_applicable', 'not_applicable')):
        control = pulldown_cases.synthetic_record()
        control['facts']['negative_control_done'] = pulldown_cases.fact(done, ['s'] if done == 'no' else [])
        control['facts']['prey_absent_in_negative_control'] = pulldown_cases.fact(absent)
        out.append(control)
    for answer in ('no', 'unknown', 'not_applicable'):
        direct = pulldown_cases.synthetic_record()
        direct['facts']['direct_interaction_shown'] = pulldown_cases.fact(answer, ['s'] if answer == 'no' else [])
        out.append(direct)
    return out


def emsa_mutated():
    mutated = emsa_cases.synthetic_record()
    for name in ('shift_detected', 'shift_abolished_by_specific_competitor', 'shift_not_abolished_by_nonspecific_competitor', 'mutant_probe_does_not_shift', 'nonspecific_protein_control_done', 'free_probe_quantified', 'equilibrium_reached', 'complex_survives_gel_run', 'independent_experiments'):
        mutated['facts'][name] = emsa_cases.fact('no', ['s'])
    for name in ('supershift_confirms_protein_identity', 'protein_purified'):
        mutated['facts'][name] = emsa_cases.fact('no', ['s'])
    mutated['quantities']['probe_concentration'] = emsa_cases.point(50.0, 'nM', 'p', ['s'])
    mutated['quantities']['protein_concentration_highest'] = emsa_cases.point(30.0, 'nM', 'h', ['s'])
    mutated['quantities']['titration_point_count'] = emsa_cases.point(3, 'count', 't', ['s'])
    mutated['quantities']['fraction_shifted_highest'] = emsa_cases.point(40.0, 'percent', 'f', ['s'])
    mutated['quantities']['shifted_species_count'] = emsa_cases.point(2, 'count', 's', ['s'])
    mutated['quantities']['replicate_count'] = emsa_cases.point(2, 'count', 'r', ['s'])
    return mutated


def emsa_variants():
    out = [emsa_cases.multiple_species_record()]
    for answer in ('no', 'unknown', 'not_applicable'):
        record = emsa_cases.synthetic_record()
        record['facts']['probe_at_or_below_kd'] = emsa_cases.fact(answer, ['s'] if answer == 'no' else [])
        record['facts']['protein_range_brackets_kd'] = emsa_cases.fact(answer, ['s'] if answer == 'no' else [])
        record['quantities']['probe_concentration'] = {**record['quantities']['probe_concentration'], 'status': 'unavailable', 'value': None}
        record['quantities']['protein_concentration_lowest'] = {**record['quantities']['protein_concentration_lowest'], 'status': 'unavailable', 'value': None}
        out.append(record)
    for answer in ('no', 'unknown'):
        competitor = emsa_cases.synthetic_record()
        competitor['facts']['shift_abolished_by_specific_competitor'] = emsa_cases.fact(answer, ['s'] if answer == 'no' else [])
        competitor['quantities']['specific_competitor_excess'] = emsa_cases.point(10.0, 'ratio', 'x', ['s'])
        out.append(competitor)
    for supershift, purified in (('unknown', 'unknown'), ('not_applicable', 'not_applicable'), ('yes', 'no')):
        identity = emsa_cases.synthetic_record()
        identity['facts']['supershift_confirms_protein_identity'] = emsa_cases.fact(supershift, ['s'] if supershift == 'yes' else [])
        identity['facts']['protein_purified'] = emsa_cases.fact(purified, ['s'] if purified == 'no' else [])
        out.append(identity)
    unstated = emsa_cases.synthetic_record()
    for name in ('kd', 'kd_spread', 'fraction_shifted_highest', 'titration_point_count', 'shifted_species_count', 'incubation_time', 'replicate_count'):
        unstated['quantities'][name] = {**unstated['quantities'][name], 'status': 'unavailable', 'value': None}
    unstated['fit_model'] = None
    unstated['facts']['equilibrium_reached'] = emsa_cases.fact('unknown')
    out.append(unstated)
    return out


def sec_mutated():
    mutated = sec_cases.synthetic_record()
    for name in ('complex_peak_detected', 'components_run_alone', 'complex_peak_analysed_by_sds_page', 'free_peak_decreases_with_titration', 'column_calibrated_with_standards', 'single_component_control_done', 'independent_experiments'):
        mutated['facts'][name] = sec_cases.fact('no', ['s'])
    mutated['quantities']['elution_volume_shift'] = sec_cases.point(0.1, 'mL', 'sh', ['s'])
    mutated['quantities']['complex_mass_measured'] = sec_cases.point(20.0, 'kDa', 'm', ['s'])
    mutated['quantities']['stoichiometry_ratio'] = sec_cases.point(2.0, 'ratio', 'r', ['s'])
    mutated['quantities']['loaded_concentration'] = sec_cases.point(1000.0, 'nM', 'l', ['s'])
    mutated['quantities']['polydispersity'] = sec_cases.point(1.3, 'ratio', 'p', ['s'])
    mutated['quantities']['replicate_count'] = sec_cases.point(2, 'count', 'r', ['s'])
    mutated['facts']['buffer_rules_out_resin_interaction'] = sec_cases.fact('no', ['s'])
    return mutated


def sec_variants():
    out = []
    for answer in ('no', 'unknown', 'not_applicable'):
        record = sec_cases.synthetic_record()
        for name in ('mals_mass_matches_complex', 'buffer_rules_out_resin_interaction', 'complex_stable_on_column', 'aggregation_absent'):
            record['facts'][name] = sec_cases.fact(answer, ['s'] if answer == 'no' else [])
        for name in ('complex_mass_measured', 'salt_concentration', 'loaded_concentration', 'polydispersity', 'elution_volume_shift'):
            record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}
        out.append(record)
    unstated = sec_cases.synthetic_record()
    for name in ('kd', 'kd_spread', 'complex_elution_volume', 'stoichiometry_ratio', 'replicate_count', 'salt_concentration'):
        unstated['quantities'][name] = {**unstated['quantities'][name], 'status': 'unavailable', 'value': None}
    unstated['quantities']['elution_volume_shift'] = {**unstated['quantities']['elution_volume_shift'], 'status': 'unavailable', 'value': None}
    unstated['facts']['buffer_rules_out_resin_interaction'] = sec_cases.fact('unknown')
    out.append(unstated)
    low_salt = sec_cases.synthetic_record()
    low_salt['facts']['buffer_rules_out_resin_interaction'] = sec_cases.fact('unknown')
    low_salt['quantities']['salt_concentration'] = sec_cases.point(50.0, 'mM', 's', ['s'])
    out.append(low_salt)
    return out


def records(kind):
    if kind == 'dialysis':
        return [grade_dialysis(r) for r in dialysis_variants()]
    if kind == 'sec':
        return [grade_sec(r) for r in (sec_cases.synthetic_record(), sec_cases.qualitative_record(), sec_cases.sparse_record(), sec_cases.real_record(), sec_cases.weak_complex_record(), sec_mutated(), *sec_variants())]
    if kind == 'emsa':
        return [grade_emsa(r) for r in (emsa_cases.synthetic_record(), emsa_cases.qualitative_record(), emsa_cases.sparse_record(), emsa_cases.real_record(), emsa_mutated(), *emsa_variants())]
    if kind == 'pulldown':
        return [grade_pulldown(r) for r in (pulldown_cases.synthetic_record(), pulldown_cases.sparse_record(), pulldown_cases.real_record(), pulldown_mutated(), *pulldown_variants())]
    if kind == 'spa':
        return [grade_spa(r) for r in (spa_cases.synthetic_record(), spa_cases.sparse_record(), spa_cases.real_record(), spa_mutated(), *spa_variants())]
    if kind == 'radioligand':
        return [grade_radioligand(r) for r in (radioligand_cases.synthetic_record(), radioligand_cases.sparse_record(), radioligand_cases.real_record(), radioligand_mutated(), *radioligand_variants())]
    if kind == 'alphascreen':
        return [grade_alpha(r) for r in (alpha_cases.synthetic_record(), alpha_cases.sparse_record(), alpha_cases.real_record(), alpha_mutated(), *alpha_variants())]
    if kind == 'elisa':
        return [grade_elisa(r) for r in (elisa_cases.synthetic_record(), elisa_cases.sparse_record(), elisa_cases.real_record(), elisa_mutated(), *elisa_variants())]
    if kind == 'fcs':
        return [grade_fcs(r) for r in (fcs_cases.synthetic_record(), fcs_cases.sparse_record(), fcs_cases.real_record(), fcs_mutated(), *fcs_variants())]
    if kind == 'trp':
        return [grade_trp(r) for r in (trp_cases.synthetic_record(), trp_cases.sparse_record(), trp_cases.real_record(), trp_mutated(), *trp_variants())]
    if kind == 'mst':
        return [grade_mst(r) for r in (mst_cases.synthetic_record(), mst_cases.sparse_record(), mst_cases.real_record(), mst_mutated(), *mst_variants())]
    if kind == 'fret':
        return [grade_fret(r) for r in (fret_cases.synthetic_record(), fret_cases.sparse_record(), fret_cases.real_record(), fret_mutated(), *fret_variants())]
    if kind == 'fp':
        return [grade_fp(r) for r in (fp_cases.synthetic_record(), fp_cases.sparse_record(), fp_cases.real_record(), fp_mutated(), *fp_variants())]
    if kind == 'spr':
        return [grade_spr(spr_cases.synthetic_record()), grade_spr(spr_cases.popz_record())]
    if kind == 'bli':
        return [grade_bli(bli_cases.synthetic_record()), grade_bli(bli_cases.sparse_record()), grade_bli(bli_cases.real_record()), grade_bli(bli_mutated())]
    if kind == 'gci':
        return [grade_gci(gci_cases.synthetic_record()), grade_gci(gci_cases.sparse_record()), grade_gci(gci_cases.real_record()), grade_gci(gci_mutated()), grade_gci(gci_pulsed(True)), grade_gci(gci_pulsed(False))]
    mutated = itc_cases.synthetic_record()
    mutated['facts']['buffer_matching'] = itc_cases.fact('not_matched')
    mutated['quantities']['injection_count'] = itc_cases.point(5, 'count', 'i', ['s'])
    mutated['quantities']['cell_concentration'] = itc_cases.point(1.0, 'nM', 'c', ['s'])
    mutated['quantities']['entropy'] = itc_cases.point(80.0, 'J/mol/K', 's', ['s'])
    return [grade_itc(itc_cases.synthetic_record()), grade_itc(itc_cases.sparse_record()), grade_itc(mutated)]


@pytest.mark.parametrize('kind', ['spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis'])
def test_declaration_is_complete_and_constants_are_defined_once_with_a_marker(kind):
    criteria_module, grader_module, declared, _ = GRADERS[kind]
    assert len({c['id'] for c in declared}) == len(declared)
    names = constants(criteria_module)
    source = inspect.getsource(criteria_module).splitlines()
    for criterion in declared:
        assert set(criterion) == FIELDS
        assert criterion['question'].endswith('?') and criterion['rule'] and criterion['reads']
        assert {status for status, _, _ in criterion['returns']} <= STATUSES | {'not_applicable'}
        assert set(criterion['thresholds']) <= set(names)
    for name in names:
        lines = [line for line in source if re.match(name + r' = ', line)]
        assert len(lines) == 1, name
        assert 'EXPERT_REVIEW' in lines[0] or 'FIXED_BY_DEFINITION' in lines[0], name
        assert any(name in c['thresholds'] for c in declared), name


@pytest.mark.parametrize('kind', ['spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis'])
def test_grader_evaluates_exactly_the_declared_criteria_in_order(kind):
    criteria_module, grader_module, declared, _ = GRADERS[kind]
    assert grader_module.CRITERIA == tuple(c['id'] for c in declared)
    assert tuple(grader_module.EVALUATORS) == grader_module.CRITERIA


@pytest.mark.parametrize('kind', ['spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis'])
def test_every_returned_status_and_reason_is_a_declared_case(kind):
    declared = {c['id']: {(status, reason) for status, reason, _ in c['returns']} for c in GRADERS[kind][2]}
    seen = 0
    for graded in records(kind):
        for name, outcome in graded['criteria'].items():
            assert (outcome['status'], graded['reasons'][name]) in declared[name], (name, outcome['status'], graded['reasons'][name])
            seen += 1
    assert seen >= 2 * len(declared)


@pytest.mark.parametrize('kind', ['spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis'])
def test_no_inline_threshold_number_in_the_grader(kind):
    _, grader_module, _, allowed = GRADERS[kind]
    numbers = {node.value for node in ast.walk(ast.parse(inspect.getsource(grader_module))) if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)}
    assert numbers - {float(a) for a in allowed} == set()


# The index document (docs/, outside the library) has SPR and ITC sections only; a BLI and a GCI section are the owner's to add.
@pytest.mark.parametrize('kind', ['spr', 'itc'])
def test_index_lists_every_criterion_and_constant_with_its_current_value(kind):
    criteria_module, _, declared, _ = GRADERS[kind]
    text = INDEX.read_text()
    rows = [line for line in text.splitlines() if line.startswith('|')]
    for criterion in declared:
        assert any('`' + criterion['id'] + '`' in row for row in rows), criterion['id']
    for name, value in constants(criteria_module).items():
        assert any('`' + name + '`' in row and re.search(r'(?<![\w.])' + re.escape(str(value)) + r'(?![\w.])', row) for row in rows), name
