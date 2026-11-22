"""The graders of the experiment types (``GRADERS``) and the sheet-side judgement of each type's criterion (``JUDGES``), each
picked by the record's own experiment type. Tables only: no model call, no store access, nothing held."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_grader import (
    grade_alpha)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_auc_grader import (
    grade_auc)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_grader import (
    grade_bret)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_converter import (
    _criterion as judge_bret)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_proximity_grader import (
    grade_proximity)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_grader import (
    grade_split_reporter)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import (
    grade_bli)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import (
    grade_dialysis)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_grader import (
    grade_dsf)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_grader import (
    grade_elisa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import (
    grade_emsa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import (
    grade_fcs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_grader import (
    grade_fp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_grader import (
    grade_fret)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_grader import (
    grade_gci)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import (
    grade_itc)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_grader import (
    grade_mst)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import (
    grade_pulldown)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import (
    grade_radioligand)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_grader import (
    grade_sec)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_grader import (
    grade_spa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import (
    grade_spr)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import (
    grade_trp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_y2h_grader import (
    grade_y2h)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import (
    _criterion as judge_alpha)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_auc_converter import (
    _criterion as judge_auc)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_proximity_converter import (
    _criterion as judge_proximity)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_converter import (
    _criterion as judge_split_reporter)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import (
    _criterion as judge_bli)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import (
    _criterion as judge_dialysis)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_converter import (
    _criterion as judge_dsf)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_converter import (
    _criterion as judge_elisa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import (
    _criterion as judge_emsa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import (
    _criterion as judge_fcs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import (
    _criterion as judge_fp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import (
    _criterion as judge_fret)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import (
    _criterion as judge_gci)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import (
    _criterion as judge_itc)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import (
    _criterion as judge_mst)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import (
    _criterion as judge_pulldown)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import (
    _criterion as judge_radioligand)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import (
    _criterion as judge_sec)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import (
    _criterion as judge_spa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import (
    _criterion as judge_spr)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import (
    _criterion as judge_trp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_y2h_converter import (
    _criterion as judge_y2h)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pla_grader import (
    grade_pla)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pla_converter import (
    _criterion as judge_pla)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_colocalization_grader import (
    grade_colocalization)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_colocalization_converter import (
    _criterion as judge_colocalization)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_grader import (
    grade_cetsa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_converter import (
    _criterion as judge_cetsa)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_grader import (
    grade_spectro_direct)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_converter import (
    _criterion as judge_spectro_direct)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupled_enzyme_grader import (
    grade_coupled_enzyme)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupled_enzyme_converter import (
    _criterion as judge_coupled_enzyme)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_redox_mediator_grader import (
    grade_redox_mediator)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_redox_mediator_converter import (
    _criterion as judge_redox_mediator)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fluorogenic_grader import (
    grade_fluorogenic)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fluorogenic_converter import (
    _criterion as judge_fluorogenic)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_luminescent_grader import (
    grade_luminescent)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_luminescent_converter import (
    _criterion as judge_luminescent)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_stopped_flow_grader import (
    grade_stopped_flow)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_stopped_flow_converter import (
    _criterion as judge_stopped_flow)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_quench_flow_grader import (
    grade_quench_flow)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_quench_flow_converter import (
    _criterion as judge_quench_flow)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_chromatographic_grader import (
    grade_chromatographic)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_chromatographic_converter import (
    _criterion as judge_chromatographic)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_stopped_colorimetric_grader import (
    grade_stopped_colorimetric)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_stopped_colorimetric_converter import (
    _criterion as judge_stopped_colorimetric)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radiometric_grader import (
    grade_radiometric)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radiometric_converter import (
    _criterion as judge_radiometric)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_separation_band_grader import (
    grade_separation_band)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_separation_band_converter import (
    _criterion as judge_separation_band)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_oxygen_electrode_grader import (
    grade_oxygen_electrode)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_oxygen_electrode_converter import (
    _criterion as judge_oxygen_electrode)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_ph_stat_grader import (
    grade_ph_stat)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_ph_stat_converter import (
    _criterion as judge_ph_stat)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_protein_film_electrochem_grader import (
    grade_protein_film_electrochem)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_protein_film_electrochem_converter import (
    _criterion as judge_protein_film_electrochem)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_kinetics_grader import (
    grade_itc_kinetics)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_kinetics_converter import (
    _criterion as judge_itc_kinetics)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_continuous_ms_grader import (
    grade_continuous_ms)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_continuous_ms_converter import (
    _criterion as judge_continuous_ms)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_nmr_timecourse_grader import (
    grade_nmr_timecourse)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_nmr_timecourse_converter import (
    _criterion as judge_nmr_timecourse)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_immunodetection_grader import (
    grade_product_immunodetection)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_immunodetection_converter import (
    _criterion as judge_product_immunodetection)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_zymogram_grader import (
    grade_zymogram)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_zymogram_converter import (
    _criterion as judge_zymogram)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_cell_tracer_uptake_grader import (
    grade_transport_cell_tracer_uptake)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_cell_tracer_uptake_converter import (
    _criterion as judge_transport_cell_tracer_uptake)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_counterflow_grader import (
    grade_transport_counterflow)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_counterflow_converter import (
    _criterion as judge_transport_counterflow)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_fluorescent_reporter_grader import (
    grade_transport_fluorescent_reporter)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_fluorescent_reporter_converter import (
    _criterion as judge_transport_fluorescent_reporter)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_medium_analysis_grader import (
    grade_transport_medium_analysis)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_medium_analysis_converter import (
    _criterion as judge_transport_medium_analysis)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_oocyte_two_electrode_grader import (
    grade_transport_oocyte_two_electrode)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_oocyte_two_electrode_converter import (
    _criterion as judge_transport_oocyte_two_electrode)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_patch_clamp_grader import (
    grade_transport_patch_clamp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_patch_clamp_converter import (
    _criterion as judge_transport_patch_clamp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_planar_bilayer_grader import (
    grade_transport_planar_bilayer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_planar_bilayer_converter import (
    _criterion as judge_transport_planar_bilayer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_proteoliposome_tracer_grader import (
    grade_transport_proteoliposome_tracer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_proteoliposome_tracer_converter import (
    _criterion as judge_transport_proteoliposome_tracer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_ssm_electrophysiology_grader import (
    grade_transport_ssm_electrophysiology)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_ssm_electrophysiology_converter import (
    _criterion as judge_transport_ssm_electrophysiology)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_vesicle_probe_flux_grader import (
    grade_transport_vesicle_probe_flux)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_vesicle_probe_flux_converter import (
    _criterion as judge_transport_vesicle_probe_flux)

GRADERS = {'spr': grade_spr, 'itc': grade_itc, 'bli': grade_bli, 'gci': grade_gci, 'fp': grade_fp, 'fret': grade_fret, 'mst': grade_mst, 'trp_quenching': grade_trp, 'fcs': grade_fcs, 'elisa': grade_elisa, 'alphascreen': grade_alpha, 'radioligand': grade_radioligand, 'spa': grade_spa, 'pulldown': grade_pulldown, 'emsa': grade_emsa, 'sec': grade_sec, 'dialysis': grade_dialysis, 'auc': grade_auc, 'proximity': grade_proximity,'cetsa': grade_cetsa, 'split_reporter': grade_split_reporter, 'y2h': grade_y2h,'dsf': grade_dsf, 'pla': grade_pla, 'bret': grade_bret, 'colocalization': grade_colocalization, 'spectro_direct': grade_spectro_direct, 'coupled_enzyme': grade_coupled_enzyme, 'redox_mediator': grade_redox_mediator, 'fluorogenic': grade_fluorogenic, 'luminescent': grade_luminescent, 'stopped_flow': grade_stopped_flow, 'quench_flow': grade_quench_flow, 'chromatographic': grade_chromatographic, 'stopped_colorimetric': grade_stopped_colorimetric, 'radiometric': grade_radiometric, 'separation_band': grade_separation_band, 'oxygen_electrode': grade_oxygen_electrode, 'ph_stat': grade_ph_stat, 'protein_film_electrochem': grade_protein_film_electrochem, 'itc_kinetics': grade_itc_kinetics, 'continuous_ms': grade_continuous_ms, 'nmr_timecourse': grade_nmr_timecourse, 'product_immunodetection': grade_product_immunodetection, 'zymogram': grade_zymogram, 'transport_cell_tracer_uptake': grade_transport_cell_tracer_uptake, 'transport_counterflow': grade_transport_counterflow, 'transport_fluorescent_reporter': grade_transport_fluorescent_reporter, 'transport_medium_analysis': grade_transport_medium_analysis, 'transport_oocyte_two_electrode': grade_transport_oocyte_two_electrode, 'transport_patch_clamp': grade_transport_patch_clamp, 'transport_planar_bilayer': grade_transport_planar_bilayer, 'transport_proteoliposome_tracer': grade_transport_proteoliposome_tracer, 'transport_ssm_electrophysiology': grade_transport_ssm_electrophysiology, 'transport_vesicle_probe_flux': grade_transport_vesicle_probe_flux}   # the grader of each experiment type: code picks it by the record's own type
JUDGES = {'spr': judge_spr, 'itc': judge_itc, 'bli': judge_bli, 'gci': judge_gci, 'fp': judge_fp, 'fret': judge_fret, 'mst': judge_mst, 'trp_quenching': judge_trp, 'fcs': judge_fcs, 'elisa': judge_elisa, 'alphascreen': judge_alpha, 'radioligand': judge_radioligand, 'spa': judge_spa, 'pulldown': judge_pulldown, 'emsa': judge_emsa, 'sec': judge_sec, 'dialysis': judge_dialysis, 'auc': judge_auc, 'proximity': judge_proximity,'cetsa': judge_cetsa, 'split_reporter': judge_split_reporter, 'y2h': judge_y2h,'dsf': judge_dsf, 'pla': judge_pla, 'bret': judge_bret, 'colocalization': judge_colocalization, 'spectro_direct': judge_spectro_direct, 'coupled_enzyme': judge_coupled_enzyme, 'redox_mediator': judge_redox_mediator, 'fluorogenic': judge_fluorogenic, 'luminescent': judge_luminescent, 'stopped_flow': judge_stopped_flow, 'quench_flow': judge_quench_flow, 'chromatographic': judge_chromatographic, 'stopped_colorimetric': judge_stopped_colorimetric, 'radiometric': judge_radiometric, 'separation_band': judge_separation_band, 'oxygen_electrode': judge_oxygen_electrode, 'ph_stat': judge_ph_stat, 'protein_film_electrochem': judge_protein_film_electrochem, 'itc_kinetics': judge_itc_kinetics, 'continuous_ms': judge_continuous_ms, 'nmr_timecourse': judge_nmr_timecourse, 'product_immunodetection': judge_product_immunodetection, 'zymogram': judge_zymogram, 'transport_cell_tracer_uptake': judge_transport_cell_tracer_uptake, 'transport_counterflow': judge_transport_counterflow, 'transport_fluorescent_reporter': judge_transport_fluorescent_reporter, 'transport_medium_analysis': judge_transport_medium_analysis, 'transport_oocyte_two_electrode': judge_transport_oocyte_two_electrode, 'transport_patch_clamp': judge_transport_patch_clamp, 'transport_planar_bilayer': judge_transport_planar_bilayer, 'transport_proteoliposome_tracer': judge_transport_proteoliposome_tracer, 'transport_ssm_electrophysiology': judge_transport_ssm_electrophysiology, 'transport_vesicle_probe_flux': judge_transport_vesicle_probe_flux}   # the sheet-side judgement of each type's criterion (its converter owns the thresholds)
