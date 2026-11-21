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

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_grader import (
    grade_cetsa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_converter import (
    _criterion as judge_cetsa)

GRADERS = {'spr': grade_spr, 'itc': grade_itc, 'bli': grade_bli, 'gci': grade_gci, 'fp': grade_fp, 'fret': grade_fret, 'mst': grade_mst, 'trp_quenching': grade_trp, 'fcs': grade_fcs, 'elisa': grade_elisa, 'alphascreen': grade_alpha, 'radioligand': grade_radioligand, 'spa': grade_spa, 'pulldown': grade_pulldown, 'emsa': grade_emsa, 'sec': grade_sec, 'dialysis': grade_dialysis, 'auc': grade_auc, 'proximity': grade_proximity,'cetsa': grade_cetsa, 'split_reporter': grade_split_reporter, 'y2h': grade_y2h,'dsf': grade_dsf, 'pla': grade_pla, 'bret': grade_bret}   # the grader of each experiment type: code picks it by the record's own type
JUDGES = {'spr': judge_spr, 'itc': judge_itc, 'bli': judge_bli, 'gci': judge_gci, 'fp': judge_fp, 'fret': judge_fret, 'mst': judge_mst, 'trp_quenching': judge_trp, 'fcs': judge_fcs, 'elisa': judge_elisa, 'alphascreen': judge_alpha, 'radioligand': judge_radioligand, 'spa': judge_spa, 'pulldown': judge_pulldown, 'emsa': judge_emsa, 'sec': judge_sec, 'dialysis': judge_dialysis, 'auc': judge_auc, 'proximity': judge_proximity,'cetsa': judge_cetsa, 'split_reporter': judge_split_reporter, 'y2h': judge_y2h,'dsf': judge_dsf, 'pla': judge_pla, 'bret': judge_bret}   # the sheet-side judgement of each type's criterion (its converter owns the thresholds)
