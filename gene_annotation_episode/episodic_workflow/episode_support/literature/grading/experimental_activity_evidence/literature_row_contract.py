"""The A105 row contract: every vocabulary, field list, version, constant and function signature of the A105 scoring
paradigm, in one place. Constants and schemas only; the only code is small validators of a record against a schema.
Every later builder (resolution, bearing, direction, row merger, main-sheet merger, axis output, sheet features,
per-class rows, wiring) imports from here and never redefines anything.

CONTRACT (the owner's paradigm, 2026-11-20; it wins over what the code did before):

* Two separate outputs, produced at BOTH levels (every subscoring sheet, and the main scoring sheet fed by merger 2),
  passed upward separately and never mixed:
    - the PER-ANNOTATION SCORES (one per candidate annotation): support, opposition, net, and at the axis the scalar
      tanh(net / 2). They answer "how much does the evidence speak for or against this candidate". They use the weight
      (degree and quote support, unknown = 0, conflicting = 0) and never read credit.
    - the CREDIT: progress in lessening uncertainty. Resolution R is the mean resolution of the open questions
      (conflicting counts as resolved, unknown as 0); credit is the change of R (sheet level) or of 1 - mean R over
      the commissioned classes (main level). Credit never reads the sign or the magnitude of a score.
* A row is (class = sheet, candidate = assertion_ref). The main sheet has one row per class for each candidate.
* Everything passed upward is a number, a count, a vocabulary value or a record reference. No prose field anywhere.
* The grader holds facts only; the converter and the sheet side judge and own every threshold.
* Unknown is never zero and never opposition. A measured zero stays scored (status measured_zero, neutral).
* Only a result with bearing 'direct' gives support or opposition. The degree and the quote-support factor are applied
  once (converter, via literature_quote_support) and are never reapplied by a merger or the main sheet.

OWNER RULINGS OF 2026-11-20 ON WHERE THE WORK RUNS AND WHAT AN EXPERIMENT IS (A-G; they replace the earlier proposal
that literature/head run merger (1) and merger (2), and change the 'where' of OWNER_DECISIONS 6, 10 and 11):

* (A) OWNER_DECISION 10. The PAGE (one page = one document: a web page or a pdf) finalizes each experiment's grader and
  uses it to UPDATE the subscoring sheet. Merger (1) runs at the page as an update of a PERSISTENT subscoring sheet: the
  sheet is the accumulator, and the merge compares the new experiment with what the sheet already holds, including its
  preparation, dataset and source refs, so cross-document dependence is handled inside the sheet update. Updating the
  subscoring sheet updates the main scoring sheet (merger (2)), the credit and the per-annotation scores in the SAME
  step. The levels above the page (literature, head and up) only RECEIVE the controlled results (credit and scores as
  controlled numbers) and compute nothing. The chunk and table leaves stay extractors: they neither convert nor merge.
* (B) OWNER_DECISION 14. One experiment = one grader: one version of one experiment in one document. The same experiment
  repeated in another paper is another grader. An experiment never spans documents. The facts of one experiment may be
  spread over many chunks and tables, so several leaves contribute to ONE grader.
* (C) OWNER_DECISION 14. Leaf records are IMMUTABLE once written. A grader is a GROUPING of leaf records by identity,
  derived by code from what has arrived and re-derivable until the page finalizes, so a later split or merge is lossless
  (each field keeps its own quote and byte span). A leaf returns identity features; code, not the model, assigns identity.
* (D) OWNER_DECISION 13. Identity rule ('best effort, mostly right'). Records belong to the same experiment grader when
  (1) they come from the same document (source_ref, a must-have) and (2) have the same experiment_type. DEFAULT = MERGE:
  same document and same type merge, no name is needed (many papers have exactly one experiment of a type and never name
  it). SPLIT only on a positive identity-feature CONFLICT: both sides state a feature of IDENTITY_FEATURES and the values
  differ (the target or partner identity, an identity-bearing condition, the figure/table/section label). A mere
  difference of a measured value (for example two KD values) is NOT a split: the field is held CONFLICTING inside one
  grader (reason ambiguous_or_conflicting_in_passage) and the sheet judges it. Only features both sides state are
  compared; per feature the result is agree, conflict or missing, and missing is skipped, never a conflict. A positive
  tie (an agreeing name or label, an agreeing target or partner identity) is not required but is recorded. KNOWN RISK: two same-type
  experiments of one document with no differing stated feature merge until something differing arrives; this
  undercounts evidence and does not overcount it.
* (E) The identity features a leaf returns are small controlled fields beside the answer (IDENTITY_FIELDS,
  LEAF_RECORD_IDENTITY); each may be unavailable with a vocabulary reason; none is prose.
* (F) Finalizing. The page finalizes a grader when no unread chunk or table in its neighbourhood remains or its routing
  has no further candidate. It converts EVERY grader, including incomplete ones, into a subscoring-sheet update; the only
  grader skipped is a source-grounded 'no applicable experiment' finding. Fields no leaf states stay unavailable (reason
  not_stated_in_passage). The same value from overlapping chunks is ONE stated support (deduplicated on absolute byte
  spans); different values keep both with their spans and mark the field conflicting. Credit follows: a repeat of an
  already-held fact earns nothing, a newly filled field or newly resolved criterion earns the change in resolution.
* (G) The experiment_ref the caller supplies today is NOT an identity. The page assigns the grader's ref (grader_ref)
  from its grouping (GRADER_REF_FIELDS).

REVISION OF 2026-11-20 (gaps the builders reported; OWNER_DECISIONS 15, 16, 17 added, 3, 4, 6 and 8 completed):

* A converted result carries what the row merger reads (RESULT_FIELDS: interpretations, measured effect, variance, unit,
  the preparation refs, dataset_ref, source_ref, direction_field_support, the qualitative statement and its refs).
* A row is built in TWO steps. merge_row returns a PARTIAL row (ROW_FIELDS without ROW_CALLER_FIELDS: weight, resolution,
  credit); complete_row(row, weight, resolution, credit) fills those three and validates the complete row. The weight comes
  from literature_resolution.row_weight, the resolution from row_resolution (which reads the stored boolean
  independence_known), the credit from credit_change(before, after): the two outputs (scores, credit) stay separate.
* The persistent subscoring sheet holds a STATE (SHEET_STATE_FIELDS): the row, the member results it was built from, and a
  version. merge_row_state returns it; a repeat result (same result_ref) changes nothing and earns no credit.
* The direction is computed directly from the effect (QUANTITATIVE_STRENGTH); the criteria never gate it.

OWNER RULING OF 2026-11-20 ON THE TARGET MOLECULE (OWNER_DECISION 18; replaces partner_a_*/partner_b_*):

* Every experimental grader has a TARGET MOLECULE: the molecule the assay is about. The identity fields are target_id
  (the target: an annotation ID or normalized name), partner_id (OPTIONAL: the other molecule the target is tested
  against, for example the ligand or the binding partner) and partner_role (optional, ROLE vocabulary). Nothing in the
  contract is symmetrical any more: the target is the subject of the experiment, the partner is the counterpart.
* BEARING requires the target (it is the one identity field bearing requires): a grader no member record of which states
  target_id bears on no candidate (bearing none, reason target_not_stated), earns no score, and still counts in the
  credit as the credit resolution says. An open question 'target known' is NOT added to CREDIT_QUESTIONS_EXTRA; a target
  left unknown leaves the direction unknown (the direction_known question already carries that).
* Identity: target_id and partner_id are identity-bearing (a stated conflict splits graders); both compare by equality
  after IDENTITY_REF_NORMALIZATION (casefold and whitespace collapse); either side missing is skipped, never a conflict;
  agreeing counts as a positive tie.
* The target applies at EVERY level: each converted result, each subscoring row (target_id = the claim's subject_id = the
  target of its direct results), each main row (= its source row's; a placeholder carries the commissioned candidate's
  target), the axis score channel and the investigation_finding features carry target_id. The scoring sheet IS the
  annotation score (one per candidate annotation, per target); the credit is a different quantity produced at the same
  levels and kept apart: SCORE group (target_id, support, opposition, net, scalar, status) and CREDIT group (resolution,
  credit) are separate named groups (ROW_SCORE_FIELDS, ROW_CREDIT_FIELDS, AXIS_SCORE_CHANNEL, AXIS_CREDIT_CHANNEL).
* Units: the identity number fields carry no unit key. Every identity number is stated by the leaf form in the field's
  canonical unit (temperature_c in degrees Celsius), so the code never guesses a unit; the leaf form converts to it.
"""
import math
import re

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import (
    SUPPORT_DEGREE,
    SUPPORTS,
)

ROW_VERSION = 'a105_row_contract_v1'
RESULT_VERSION = 'a105_converted_result_v1'
ROW_SHEET_VERSION = 'a105_subscoring_row_v1'
MAIN_SHEET_VERSION = 'a105_main_scoring_row_v1'
AXIS_VERSION = 'a105_axis_output_v1'
FEATURES_VERSION = 'a105_investigation_features_v1'

# ---------------------------------------------------------------------------------------------------------------
# (2) Classes (sheet names) and the experiment types
# ---------------------------------------------------------------------------------------------------------------
CLASSES = ('activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling', 'ligand_binding', 'transport_response', 'protein_signal', 'protein_amount')

EXPERIMENT_TYPES = ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis', 'auc', 'dsf', 'cetsa', 'bret', 'y2h', 'split_reporter', 'pla', 'proximity')

# The 25 experiment types all belong to the ligand_binding class. Types of the other seven classes are added with
# those classes (their converters do not exist yet).
CLASS_OF_EXPERIMENT_TYPE = {experiment_type: 'ligand_binding' for experiment_type in EXPERIMENT_TYPES}

# ---------------------------------------------------------------------------------------------------------------
# (3) Vocabularies
# ---------------------------------------------------------------------------------------------------------------
BEARING = ('direct', 'different_subject', 'transfer', 'none')   # only 'direct' gives support or opposition
DIRECTION = ('supports', 'opposes', 'neutral', 'unknown')
ROW_STATUS = ('measured', 'measured_zero', 'unknown')
CRITERION_STATUS = ('supported', 'conflicting', 'unknown', 'not_applicable')
QUALITATIVE_STATEMENT = ('interaction_detected', 'interaction_not_detected', 'interaction_not_stated')

# Candidate claim predicates. OWNER_DECISION 1: a candidate carries predicate + subject_id + partner_id (annotation
# IDs or names from a looked-up list). A claim names molecules only: it never carries a physical prediction or threshold
# (owner ruling of 2026-11-21); the sheet grades the measurement itself (QUANTITATIVE_STRENGTH).
# EXTENSION POINT: the predicates of the other seven classes (for example catalyses, transports, changes_amount) are
# to be added here WITH THEIR CLASS, by the builder who adds that class; a predicate not listed for a class is refused.
CLAIM_PREDICATES_BY_CLASS = {
    'ligand_binding': ('binds',),
}
# A symmetric predicate holds both ways: 'A binds B' is 'B binds A'. A result whose target is the claim's partner and whose
# partner is the claim's subject is then direct for the claim (bearing, reason partner_route).
SYMMETRIC_PREDICATES = ('binds',)
CLAIM_PREDICATES = tuple(p for predicates in CLAIM_PREDICATES_BY_CLASS.values() for p in predicates)
CLAIM_FIELDS = {   # OWNER_DECISION 1
    'predicate': 'vocab CLAIM_PREDICATES',
    'subject_id': 'molecule name (is_name; compared after normalize_identity_ref): the target the annotation is about',
    'partner_id': 'molecule name or null (is_name; compared after normalize_identity_ref)',
}

# Support classes and factors: not redefined here; imported from literature_quote_support (SUPPORTS, SUPPORT_DEGREE).
SUPPORT_CLASSES = SUPPORTS
SUPPORT_FACTORS = SUPPORT_DEGREE

# ---------------------------------------------------------------------------------------------------------------
# Constants that implement owner decisions (each marked OWNER_DECISION n; judging constants are EXPERT_REVIEW)
# ---------------------------------------------------------------------------------------------------------------
# Weight rule, OWNER_DECISION 4: w = sum r_c / N_applicable; supported -> degree (1.0 if none); conflicting 0; unknown 0;
# not_applicable dropped. Unknown lowers magnitude and never flips the sign.
WEIGHT_NO_DEGREE = 1.0           # EXPERT_REVIEW: OWNER_DECISION 4: a supported criterion without a degree is fully supported.
WEIGHT_CONFLICTING = 0.0         # EXPERT_REVIEW: OWNER_DECISION 4: a conflicting criterion gives the measurement no reliability for the weight.
WEIGHT_UNKNOWN = 0.9             # OWNER_DECISION 4 (owner, 2026-11-21: 0.9; real paragraphs decide about 1 criterion in 7, so an unknown criterion barely lowers the weight): it is never treated as opposition.
# The weight an UNKNOWN criterion still counts, PER EXPERIMENT TYPE (owner, 2026-11-21: 0.9 was reasoned for KD, whose
# reference range is trusted even when the paper states little; other assays differ). Decided per type by asking: is the
# readout absolute or relative; is there a reference range we would trust without the paper; what does an unstated control
# or calibration do to the number's meaning; how badly does a wrong assumption mislead; is it consistent with KD.
# The full question-and-answer chain per assay is docs/axis_restructure_20261117/A105_ASSAY_CALIBRATION_DETAILS.md. The
# weight is the expected reliability of an unstated detail, anchored so SPR gives the owner's 0.9: in KD-type assays a
# failed unstated detail mostly distorts the KD's size and 'binds' survives; in relative or qualitative assays a failed
# unstated control can turn background into a false 'binds', so they weigh less.
WEIGHT_UNKNOWN_BY_TYPE = {
    'spr': 0.90, 'itc': 0.90, 'bli': 0.85, 'gci': 0.85, 'fp': 0.80, 'fret': 0.75, 'mst': 0.75, 'trp_quenching': 0.70,
    'fcs': 0.80, 'elisa': 0.70, 'alphascreen': 0.65, 'radioligand': 0.85, 'spa': 0.80, 'pulldown': 0.70, 'emsa': 0.75,
    'sec': 0.75, 'dialysis': 0.85, 'auc': 0.85, 'dsf': 0.70, 'cetsa': 0.65, 'bret': 0.70, 'y2h': 0.60,
    'split_reporter': 0.65, 'pla': 0.55, 'proximity': 0.60,
}
# Per sheet criterion overrides where the answers differ within an assay (same document).
WEIGHT_UNKNOWN_BY_CRITERION = {
    'itc': {'binding_regime': 0.85},
    'bli': {'binding_controls': 0.80},
    'fp': {'binding_controls': 0.75, 'binding_regime': 0.75},
    'fret': {'binding_controls': 0.70, 'binding_parameter_definition': 0.70, 'calibration_applicability': 0.85},
    'mst': {'binding_controls': 0.70},
    'trp_quenching': {'binding_controls': 0.60},
    'fcs': {'calibration_applicability': 0.75},
    'elisa': {'binding_controls': 0.65, 'binding_regime': 0.65},
    'alphascreen': {'binding_controls': 0.60, 'binding_regime': 0.60},
    'radioligand': {'binding_controls': 0.90, 'binding_regime': 0.80, 'calibration_applicability': 0.80},
    'spa': {'calibration_applicability': 0.75},
    'pulldown': {'binding_controls': 0.55, 'binding_species': 0.60, 'sampling_basis': 0.80},
    'emsa': {'binding_controls': 0.60},
    'sec': {'binding_regime': 0.60, 'calibration_applicability': 0.90},
    'dialysis': {'calibration_applicability': 0.80},
    'auc': {'binding_regime': 0.75},
    'dsf': {'binding_controls': 0.80, 'binding_regime': 0.65},
    'cetsa': {'binding_controls': 0.55},
    'bret': {'binding_controls': 0.60, 'binding_regime': 0.60},
    'y2h': {'binding_controls': 0.50, 'binding_species': 0.80, 'sampling_basis': 0.80},
    'split_reporter': {'binding_controls': 0.55, 'binding_regime': 0.60},
    'pla': {'binding_controls': 0.50, 'calibration_applicability': 0.50, 'binding_regime': 0.70, 'sampling_basis': 0.80},
    'proximity': {'binding_parameter_definition': 0.55, 'calibration_applicability': 0.85, 'sampling_basis': 0.80},
}
if set(WEIGHT_UNKNOWN_BY_TYPE) != set(EXPERIMENT_TYPES) or not set(WEIGHT_UNKNOWN_BY_CRITERION) <= set(EXPERIMENT_TYPES):
    raise ValueError('WEIGHT_UNKNOWN_BY_TYPE must name exactly the EXPERIMENT_TYPES (and the overrides only those)')


def weight_unknown(experiment_type, criterion):
    """The weight an unknown sheet criterion of this experiment type counts: its override, else the type's weight."""
    return WEIGHT_UNKNOWN_BY_CRITERION.get(experiment_type, {}).get(criterion, WEIGHT_UNKNOWN_BY_TYPE[experiment_type])
# OWNER_DECISION 4 sub-rules (defaults; each EXPERT_REVIEW):
#  (4a) a POOLED supported criterion of a row carries the MINIMUM degree over the experiments that gave one (the weakest
#       experiment limits it; matches the pooled status rule 'supported only if all are supported').
#  (4b) a result with NO applicable criterion (every criterion not_applicable, or none given) has the weight of an unvetted
#       measurement, WEIGHT_UNKNOWN; 1.0 is never invented.
#  (4c) the row weight is the MEAN of the per-result weights (each w = sum r_c / N_applicable).
#  (4d) a group mean (support_g, opposition_g) divides by ALL members of the group: a member whose direction is unknown
#       contributes 0 and dilutes its group.
#  (4e) a group counts as KNOWN when ANY member's direction is known; the row is 'unknown' only when no group is known.
WEIGHT_POOLED_DEGREE = 'minimum_over_experiments'            # OWNER_DECISION 4a
WEIGHT_NO_APPLICABLE_CRITERIA = WEIGHT_UNKNOWN               # OWNER_DECISION 4b: unvetted, not unreliable
ROW_WEIGHT_RULE = 'mean_of_per_result_weights'               # OWNER_DECISION 4c
GROUP_MEAN_DIVIDES_BY = 'all_members'                        # OWNER_DECISION 4d
GROUP_KNOWN_WHEN = 'any_member_direction_known'              # OWNER_DECISION 4e

# Credit rule, OWNER_DECISION 5: R = mean resolution of the open questions; a definite negative is a resolved answer.
RESOLVED_NO_DEGREE = 1.0         # EXPERT_REVIEW: OWNER_DECISION 5: a supported criterion without a degree is fully resolved.
RESOLVED_CONFLICTING = 1.0       # EXPERT_REVIEW: OWNER_DECISION 5: conflicting is a definite answer, so it lessens uncertainty (unlike in the weight).
RESOLVED_UNKNOWN = 0.0           # EXPERT_REVIEW: OWNER_DECISION 5: unknown is the uncertainty itself.
CREDIT_QUESTIONS_EXTRA = ('direction_known', 'independence_known')   # OWNER_DECISION 5: the two row-level questions beside the criteria.
# OWNER_DECISION 18: no 'target known' question is added; a grader with no stated target bears on no candidate, earns no score
# and still counts in the credit as this resolution says; a target left unknown leaves the direction unknown (direction_known).
# direction_known: r = 1 if row_status is measured or measured_zero, else 0.
# independence_known: r = 1 if no dependence group rests on an unknown preparation, else 0.
MAIN_CREDIT_CLASSES = 'classes the parent commissioned for the candidate (N_k)'   # OWNER_DECISION 5

# Direction of a quantitative result, OWNER_DECISIONS 3 and 15 (owner ruling of 2026-11-21: graded, sheet-side, from the
# measurement itself; a claim supplies no prediction or threshold). The effect e (with its variance v when stated) gets a
# STRENGTH s in [0, 1] on its experiment type's own scale (QUANTITATIVE_STRENGTH_ANCHORS, section 5b). s > 0 supports, s == 0
# is neutral; log_ratio = QUALITATIVE_LOG_RATIO[type] * s. A quantitative result never opposes: opposition comes only from a
# stated non-detection (the qualitative path). The criteria NEVER gate the direction: they only lower the weight.
NEUTRAL_LOG_RATIO = 0.0                                        # OWNER_DECISION 3: strength 0 (at the type's noise end).
QUANTITATIVE_STRENGTH = {   # OWNER_DECISION 15 (completes 3)
    'position': 'p = (log10 e - log10 noise_end) / (log10 strong_end - log10 noise_end), clipped to [0, 1] (a smaller constant is stronger)',
    'strength': 's = (3 p^2 - 2 p^3) / (1 + r^2), r = sqrt(v) / e the relative uncertainty; r = 0 when no variance is stated',
    'direction': {'s > 0': 'supports', 's == 0': 'neutral'},
    'log_ratio': 'QUALITATIVE_LOG_RATIO[experiment_type] * s',
    'opposition': 'never from a quantitative effect; only a stated non-detection (qualitative path) opposes',
    'criteria_gate_direction': False,   # criteria statuses and degrees lower the WEIGHT only, never remove a direction
    'unit_conversion': False,           # the effect is in the anchors' unit and the variance in that unit squared; anything else is a converter error
}

# Effect support, OWNER_DECISIONS 8 and 17: the quote-support factor of the field that fixes the direction multiplies the
# magnitude. The converted result carries it as direction_field_support (a support class); the factor is
# SUPPORT_FACTORS[direction_field_support].
EFFECT_SUPPORT_FROM = 'quote_support_factor_of_direction_field'   # OWNER_DECISION 8
# OWNER_DECISION 17: copied from the support class of the field that fixes the direction: the KD operand for a
# quantitative result; the field(s) the statement derives from for a qualitative one (the weakest if several).
EFFECT_SUPPORT_FIELD = {'quantitative': 'the KD operand (effect)', 'qualitative': 'the field(s) the statement derives from', 'several_fields': 'weakest'}   # OWNER_DECISION 17
SUPPORT_WEAKEST_ORDER = ('about_something_else', 'implied', 'direct')   # OWNER_DECISION 17: weakest first (matches SUPPORT_FACTORS 0.3 < 0.7 < 1.0)

# Cross-class dependence at merger 2, OWNER_DECISIONS 6 and 16 (it runs at the page, in the same step as the sheet update, OWNER_DECISION 10): rows resting on the same dataset (first), then the same source, collapse to one unit.
CROSS_CLASS_DEPENDENCE_KEYS = ('dataset_ref', 'source_ref')   # OWNER_DECISION 6
# OWNER_DECISION 16 (default): main rows sharing a dataset (checked first) or else a source collapse to ONE unit; the unit's
# support and opposition are the MEAN over the unit's rows whose status is known; a row with neither key is independent (its
# own unit); an unknown row never enters the mean. The axis then sums over units.
CROSS_CLASS_COLLAPSE_RULE = {   # OWNER_DECISION 16
    'key_order': CROSS_CLASS_DEPENDENCE_KEYS,
    'unit_support': 'mean over the unit rows with known status',
    'unit_opposition': 'mean over the unit rows with known status',
    'row_with_neither_key': 'independent (its own unit)',
    'axis_sum': 'sum over units',
}
# The main-row optional INPUT keys (not stored fields of a main row): the page stamps them on each subscoring row it hands
# to merge_main; merge_main reads them to set dependence_unit_ref and strips them before validate_row / validate_main_row.
MAIN_ROW_INPUT_KEYS = CROSS_CLASS_DEPENDENCE_KEYS   # OWNER_DECISION 16
# The placeholder main row of a commissioned class that has no subscoring row yet: source_row_ref 'no_row', status unknown,
# null scores, weight 0.0, resolution 0.0, credit 0.0, experiments 0, independent_groups 0 (the class counts R = 0 in N_k).
# validate_main_row enforces it. A main row of a class or candidate that was not commissioned is a wrong commission: ValueError.
NO_ROW_REF = 'no_row'
# Within a row: the existing rule of the old binding merger (union-find over these keys; an unknown preparation counts as dependent).
ROW_DEPENDENCE_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')   # OWNER_DECISION 9 (they must be captured by extraction)

# Axis, OWNER_DECISION 7: one scalar tanh(net / 2) in [-1, 1], plus support and opposition returned so conflict stays visible.
AXIS_SCALAR_DIVISOR = 2.0        # EXPERT_REVIEW: OWNER_DECISION 7: scalar = tanh(net / 2), the existing A105 convention of docs/ALL_AXES_ROOT_SCALARS.md.
AXIS_SCALAR_RANGE = (-1.0, 1.0)

# Where it runs, OWNER_DECISION 10 (owner ruling A, 2026-11-20): the PAGE finalizes each grader and updates the persistent
# subscoring sheet (merger 1); that update updates the main scoring sheet (merger 2), the credit and the per-annotation
# scores in the same step. Converted results, rows and sheets are saved through the scoped store; credit is read only from
# saved rows. The levels above the page receive controlled numbers and compute nothing. Chunk and table leaves are
# extractors only.
WHERE_IT_RUNS = 'page'                                  # OWNER_DECISION 10
MERGER_1_RUNS_AT = 'page_update_of_persistent_subscoring_sheet'   # OWNER_DECISION 10: the sheet is the accumulator
MERGER_2_RUNS_AT = 'page_same_step_as_sheet_update'     # OWNER_DECISION 10
LEAVES_CONVERT_OR_MERGE = False                         # OWNER_DECISION 10: chunk and table leaves are extractors
LEVELS_ABOVE_PAGE_COMPUTE = False                       # OWNER_DECISION 10: they only receive
LEVELS_ABOVE_PAGE_RECEIVE = ('credit', 'scores')        # OWNER_DECISION 10: controlled numbers
CREDIT_READ_FROM = 'saved_rows'  # OWNER_DECISION 10
# Root combination, OWNER_DECISION 11 (computed at the page, received unchanged above it): the per-candidate credit vector goes up unchanged; the root's form is the owner's.
CREDIT_UPWARD = 'per_candidate_vector_unchanged'   # OWNER_DECISION 11
# Old path, OWNER_DECISION 12: deleted per AGENTS 'Removing unwanted code' (old per-assertion aggregate, reason/required_grading, criteria_counts as credit).
OLD_PATH_DELETED = ('per_assertion_aggregate', 'reason_required_grading_for_a105', 'criteria_counts_as_credit')   # OWNER_DECISION 12

# ---------------------------------------------------------------------------------------------------------------
# (5) QUALITATIVE_LOG_RATIO: PROPOSALS, not facts. Natural-log-ratio units, the unit of grade_assay's
# source_log_evidence_ratio and of tanh(overall / 2). Used for 'interaction_detected' (supports) and
# 'interaction_not_detected' (opposes) alike (OWNER_DECISION 2), and the per-type maximum of a quantitative result
# (log_ratio = QUALITATIVE_LOG_RATIO[type] * strength, QUANTITATIVE_STRENGTH). Rule: a weaker assay carries less evidence.
# Each value is an EXPERT_REVIEW constant for the owner or an expert to correct.
# ---------------------------------------------------------------------------------------------------------------
QUALITATIVE_LOG_RATIO = {   # OWNER_DECISION 2
    'spr': 1.5,             # EXPERT_REVIEW: label-free real-time response of a defined pair; a stated binding response is strong even without a fitted KD.
    'itc': 1.5,             # EXPERT_REVIEW: heat of binding in solution is label-free and self-identifying; a stated heat signal is strong.
    'bli': 1.4,             # EXPERT_REVIEW: label-free surface response like SPR, slightly more prone to nonspecific shifts.
    'gci': 1.4,             # EXPERT_REVIEW: label-free surface response like SPR, less often controlled in the literature.
    'mst': 1.2,             # EXPERT_REVIEW: solution thermophoresis shift; sensitive to aggregation and label artefacts.
    'fp': 1.2,              # EXPERT_REVIEW: polarisation change of a tracer; competition and quenching artefacts are possible.
    'fret': 1.0,            # EXPERT_REVIEW: proximity-dependent signal; distance and orientation effects make a bare 'detected' weaker than binding itself.
    'trp_quenching': 1.0,   # EXPERT_REVIEW: intrinsic fluorescence change can come from conformational change or inner-filter effects, not only binding.
    'fcs': 1.0,             # EXPERT_REVIEW: diffusion-time shift of a labelled partner; labelling and aggregation can mimic it.
    'radioligand': 1.4,     # EXPERT_REVIEW: direct counting of bound ligand with competition controls; strong.
    'spa': 1.2,             # EXPERT_REVIEW: proximity of a radioligand to a bead; strong when competed, weaker for a bare signal.
    'dialysis': 1.2,        # EXPERT_REVIEW: equilibrium partition of ligand is direct but coarse.
    'auc': 1.2,             # EXPERT_REVIEW: sedimentation shift of a complex is direct evidence of complex formation, with lower precision on affinity.
    'elisa': 0.8,           # EXPERT_REVIEW: surface-adsorbed, washed endpoint; avidity and nonspecific adsorption inflate positives.
    'alphascreen': 0.8,     # EXPERT_REVIEW: bead-proximity signal with known interference and a hook effect.
    'sec': 0.8,             # EXPERT_REVIEW: co-elution depends on affinity and dilution; a positive is moderate, a negative is weak.
    'pulldown': 0.7,        # EXPERT_REVIEW: washed, often overexpressed and tagged; positives frequently reflect nonspecific carry-over.
    'emsa': 0.7,            # EXPERT_REVIEW: gel shift of a nucleic-acid or protein complex; stabilised by the gel, and by competitor controls only when stated.
    'dsf': 0.6,             # EXPERT_REVIEW: thermal stabilisation is indirect: it shows an effect on stability, not that binding is at a site.
    'cetsa': 0.6,           # EXPERT_REVIEW: in-cell thermal stabilisation is indirect and can be secondary to other targets.
    'bret': 0.5,            # EXPERT_REVIEW: cellular proximity (about 10 nm), not direct binding; overexpression artefacts.
    'proximity': 0.5,       # EXPERT_REVIEW: cellular proximity labelling shows nearness, not binding.
    'pla': 0.5,             # EXPERT_REVIEW: in-situ proximity ligation shows nearness within about 40 nm, not binding.
    'y2h': 0.4,             # EXPERT_REVIEW: heterologous nuclear reporter; high false-positive and false-negative rates.
    'split_reporter': 0.4,  # EXPERT_REVIEW: reporter reconstitution can occur through proximity or forced association; weakest direct-binding evidence.
}

# ---------------------------------------------------------------------------------------------------------------
# (5b) QUANTITATIVE_STRENGTH_ANCHORS: the two ENDS of each type's gray scale for its measured effect (QUANTITATIVE_STRENGTH),
# in the effect's own unit. Every converter that fills an effect reports a binding or engagement constant in nM (variance in
# nM_squared), so each scale runs on log10 of the constant. noise_end: a constant this weak is indistinguishable from the
# type's nonspecific background or detection floor (strength 0); strong_end: a constant this tight is the strongest signal
# the type resolves (strength 1). They are never thresholds: every value between them gets a smoothly graded strength.
# Types whose converters fill no effect (pulldown, y2h, pla, proximity: qualitative only) have no anchors.
# Each pair is an EXPERT_REVIEW proposal for the owner or an expert to correct.
# ---------------------------------------------------------------------------------------------------------------
QUANTITATIVE_STRENGTH_ANCHORS = {   # OWNER_DECISION 15
    'spr': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e6, 'strong_end': 1.0},                # EXPERT_REVIEW: label-free; resolves fragments near 1 mM up to sub-nM kinetics.
    'itc': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 10.0},               # EXPERT_REVIEW: the c-window: weak heats are lost near 100 uM, tighter than about 10 nM is not resolved by direct titration.
    'bli': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 1.0},                # EXPERT_REVIEW: label-free like SPR, less sensitive for weak or small analytes.
    'gci': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e6, 'strong_end': 1.0},                # EXPERT_REVIEW: label-free like SPR.
    'fp': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 1.0},           # EXPERT_REVIEW: limited by the tracer concentration at the tight end.
    'fret': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 1.0},         # EXPERT_REVIEW: labelled titration; weak end limited by label concentration and inner-filter effects.
    'mst': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e6, 'strong_end': 1.0},          # EXPERT_REVIEW: solution titration resolves mM binders; tight end limited by the labelled partner.
    'trp_quenching': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 10.0},     # EXPERT_REVIEW: micromolar protein limits the tight end; inner-filter effects the weak end.
    'fcs': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 1.0},                # EXPERT_REVIEW: single-molecule concentrations resolve tight binding.
    'elisa': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e4, 'strong_end': 1.0},        # EXPERT_REVIEW: washed endpoint loses weak binders; avidity inflates the tight end.
    'alphascreen': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e4, 'strong_end': 1.0},  # EXPERT_REVIEW: bead-proximity signal; weak complexes fall below the background.
    'radioligand': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e4, 'strong_end': 0.1},  # EXPERT_REVIEW: picomolar radioligands; filtration loses fast-dissociating weak binders.
    'spa': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 0.1},          # EXPERT_REVIEW: radioligand without a wash keeps weaker binders than filtration.
    'emsa': {'quantity': 'apparent KD', 'unit': 'nM', 'noise_end': 1e4, 'strong_end': 1.0},      # EXPERT_REVIEW: weak complexes dissociate in the gel.
    'sec': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e4, 'strong_end': 10.0},              # EXPERT_REVIEW: column dilution dissociates weak complexes.
    'dialysis': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 10.0},    # EXPERT_REVIEW: equilibrium partition is direct but coarse at both ends.
    'auc': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 10.0},              # EXPERT_REVIEW: sedimentation resolves micromolar to tens of nM.
    'dsf': {'quantity': 'apparent KD', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 10.0},      # EXPERT_REVIEW: an apparent constant from a thermal dose response; indirect.
    'cetsa': {'quantity': 'apparent engagement EC50', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 10.0},   # EXPERT_REVIEW: in-cell isothermal dose response; depends on heating temperature and time.
    'bret': {'quantity': 'KD or Ki', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 1.0},         # EXPERT_REVIEW: cellular tracer engagement.
    'split_reporter': {'quantity': 'KD', 'unit': 'nM', 'noise_end': 1e5, 'strong_end': 10.0},    # EXPERT_REVIEW: reporter reconstitution titration; coarse.
}

# ---------------------------------------------------------------------------------------------------------------
# (4) Field lists. Each field: kind, plus lo/hi for numbers, vocab for vocabularies, nullable.
#   kinds: 'vocab', 'number' (finite float or int, not bool), 'count' (int >= 0), 'ref' (a record reference: no
#   whitespace, <= 200 chars; never prose), 'map' (a controlled mapping, checked by its own rule), 'bool' (true or
#   false), 'refs' (a list of distinct record references; lo = the least length, default 1).
# ---------------------------------------------------------------------------------------------------------------
REF_PATTERN = re.compile(r'^[A-Za-z0-9_.:/#@+\-]{1,200}$')

# A MOLECULE NAME (target_id, partner_id, claim subject_id and partner_id): the molecule's name as the passage writes it,
# normalized (casefold, whitespace collapsed: normalize_identity_ref). It is NOT a record reference: names contain spaces,
# parentheses, Greek letters and the like ('heat shock protein 90', 'HSP90α', 'Hfq (E. coli)'), which REF_PATTERN refuses.
# It is still a controlled field, not prose: one line, at most NAME_MAX_CHARS characters, at most NAME_MAX_WORDS words, no
# control characters (OWNER_DECISION 18).
NAME_MAX_CHARS = 120   # EXPERT_REVIEW: longest molecule name accepted; a longer string is a sentence, not a name
NAME_MAX_WORDS = 12    # EXPERT_REVIEW: most words in a molecule name accepted


def is_name(value):
    return (isinstance(value, str) and 1 <= len(value) <= NAME_MAX_CHARS and len(value.split()) <= NAME_MAX_WORDS
            and all(character.isprintable() for character in value) and value == ' '.join(value.split()))


def _f(kind, *, lo=None, hi=None, vocab=None, nullable=False, required=True):
    return {'kind': kind, 'lo': lo, 'hi': hi, 'vocab': vocab, 'nullable': nullable, 'required': required}


# The converted RESULT (one experiment result, one candidate).
RESULT_FIELDS = {
    'result_ref': _f('ref'),
    'experiment_ref': _f('ref'),
    'assertion_ref': _f('ref'),
    'target_id': _f('name', nullable=True),   # OWNER_DECISION 18: the experiment's target (normalized); null only when the experiment states none (bearing none); required non-null when bearing is direct
    'experiment_type': _f('vocab', vocab=EXPERIMENT_TYPES),
    'sheet': _f('vocab', vocab=CLASSES),
    'bearing': _f('vocab', vocab=BEARING),
    'direction': _f('vocab', vocab=DIRECTION),
    'log_ratio': _f('number', lo=0.0, nullable=True),            # >= 0 or null; null exactly when direction is unknown
    'weight': _f('number', lo=0.0, hi=1.0),
    'effect_support': _f('number', lo=0.0, hi=1.0, nullable=True),   # null exactly when direction is unknown
    'source_ref': _f('ref', nullable=True),
    'dataset_ref': _f('ref', nullable=True),                     # null = unknown dataset = dependent
    # What the row merger reads from a converted result (revision of 2026-11-20). All optional (absent = null = not given):
    # a result that carries no criteria has no applicable criterion (weight 0.0, OWNER_DECISION 4b); a null preparation
    # ref means UNKNOWN, hence dependent (OWNER_DECISION 9). No prose anywhere.
    'interpretations': _f('map', required=False),                # {criterion: {'status': CRITERION_STATUS, 'degree': 0..1 or null}}
    'measured_effect': _f('number', nullable=True, required=False),     # native scale of the class; null = none
    'effect_variance': _f('number', lo=0.0, nullable=True, required=False),   # variance of the effect, in the square of effect_unit
    'effect_unit': _f('ref', nullable=True, required=False),     # unit of measured_effect (required when it is given)
    'analyte_preparation_ref': _f('ref', nullable=True, required=False),      # ROW_DEPENDENCE_KEYS; null = unknown = dependent
    'immobilized_preparation_ref': _f('ref', nullable=True, required=False),
    'surface_ref': _f('ref', nullable=True, required=False),
    'direction_field_support': _f('vocab', vocab=SUPPORT_CLASSES, nullable=True, required=False),   # OWNER_DECISION 17; required when direction is known
    'statement': _f('vocab', vocab=QUALITATIVE_STATEMENT, nullable=True, required=False),   # the qualitative statement of the experiment
    'statement_support_refs': _f('refs', nullable=True, required=False),   # refs of the stated support of the statement; null when no statement
}

# The ROW of one subscoring sheet: (sheet, assertion_ref).
#
# HOW weight, resolution AND credit ARE FILLED (revision of 2026-11-20): merge_row returns the row WITHOUT these three
# (ROW_CALLER_FIELDS), a PARTIAL row (validate_partial_row). The caller then calls complete_row(row, weight, resolution,
# credit), which adds them and validates the complete row (validate_row):
#   weight     = literature_resolution.row_weight(results)           (scores side; OWNER_DECISION 4)
#   resolution = literature_resolution.row_resolution(row)           (credit side; reads criteria, row_status and independence_known)
#   credit     = literature_resolution.credit_change(before, after)  (change of R; 0.0 for a repeat result)
# The score fields (support, opposition, net) never read resolution or credit; resolution and credit never read them.
#
# OWNER_DECISION 18: the scoring sheet IS the annotation score (one per candidate annotation, per target). target_id is
# the (normalized) target the score is about: it equals the claim's subject_id and the target_id of every direct result of
# the row. TWO SEPARATE NAMED GROUPS, never mixed: the SCORE group (ROW_SCORE_FIELDS) and the CREDIT group (ROW_CREDIT_FIELDS).
# THE ROW REF IS CONTENT-ADDRESSED. row_ref = 'row:<sheet>:<assertion_ref>:<hash>' where <hash> is the first ROW_REF_HASH_CHARS hex
# characters of the sha256 of the sorted member result refs and ROW_SHEET_VERSION (literature_row.row_ref_of). A row with new
# members has a new ref; an unchanged row keeps its ref; so merge_main's test 'prior source_row_ref == row_ref' means 'unchanged
# content'. The ref of the main row is 'main:' + row_ref, and a main row_ref is also a REF_PATTERN ref of at most 200
# characters, so the subscoring row_ref is at most ROW_REF_MAX_LENGTH = 195 characters: when the assertion_ref is too long for
# that, its readable prefix is cut and the hash stays last.
ROW_REF_HASH_CHARS = 16
ROW_REF_MAX_LENGTH = 195
ROW_SCORE_FIELDS = ('target_id', 'support', 'opposition', 'net')   # + row_status; read by the weight, never by credit
ROW_CREDIT_FIELDS = ('resolution', 'credit')                       # read by credit only, never by the score
ROW_FIELDS = {
    'sheet': _f('vocab', vocab=CLASSES),
    'assertion_ref': _f('ref'),
    'target_id': _f('name'),                                     # OWNER_DECISION 18: the target the score is about; never null on a row
    'row_ref': _f('ref'),                                        # content-addressed: 'row:<sheet>:<assertion_ref>:<hash of the sorted member result refs and the row version>' (ROW_REF_HASH_CHARS, ROW_REF_MAX_LENGTH)
    'row_status': _f('vocab', vocab=ROW_STATUS),
    'support': _f('number', lo=0.0, nullable=True),              # null when unknown
    'opposition': _f('number', lo=0.0, nullable=True),           # null when unknown
    'net': _f('number', nullable=True),                          # null when unknown
    'weight': _f('number', lo=0.0, hi=1.0),
    'resolution': _f('number', lo=0.0, hi=1.0),                  # R, for credit; never read by the score
    'credit': _f('number'),                                      # change of R for the committed work; unbounded, may be 0
    'experiments': _f('count'),
    'independent_groups': _f('count'),
    'measured_effects': _f('count'),
    'criteria_supported': _f('count'),
    'criteria_conflicting': _f('count'),
    'criteria_unknown': _f('count'),
    'criteria_not_applicable': _f('count'),
    'min_degree': _f('number', lo=0.0, hi=1.0, nullable=True),
    'mean_degree': _f('number', lo=0.0, hi=1.0, nullable=True),
    'relative_deviation': _f('number', lo=0.0, nullable=True),   # pooled sd / |effect|, or null
    'criteria': _f('map', required=False),                       # criterion id -> CRITERION_STATUS (pooled: conflicting if any, supported if all, else unknown)
    'interpretation_degrees': _f('map', required=False),         # {criterion: {experiment_ref: degree 0..1}}, never combined
    'pooled_effect': _f('number', nullable=True, required=False),     # native scale of the class
    'pooled_variance': _f('number', lo=0.0, nullable=True, required=False),
    'pooled_precision': _f('number', lo=0.0, nullable=True, required=False),
    # Stored by the row merger (revision of 2026-11-20):
    'independence_known': _f('bool'),                            # true when no dependence group rests on an unknown preparation; read by row_resolution (CREDIT_QUESTIONS_EXTRA)
    'qualitative_statements': _f('map'),                         # counts only: {QUALITATIVE_STATEMENT: number of experiments stating it}; all three keys present
    'qualitative_support_refs': _f('refs', nullable=True),       # distinct refs of the qualitative statements' support, null when none
}
ROW_CALLER_FIELDS = ('weight', 'resolution', 'credit')           # filled by complete_row, never by merge_row
PARTIAL_ROW_FIELDS = {name: spec for name, spec in ROW_FIELDS.items() if name not in ROW_CALLER_FIELDS}

# The persistent subscoring sheet STATE of one (sheet, assertion_ref): what merge_row_state returns and takes back as its
# optional last argument. 'row' is the PARTIAL row of merge_row_state (the caller may store the completed row instead:
# both are accepted); 'member_results' are the converted results (bearing direct) the row was built from, ordered by
# result_ref, with distinct result_refs; 'version' is ROW_SHEET_VERSION. A result whose result_ref is already held changes
# nothing and earns no credit (CREDIT_FOR_REPEATED_FACT).
SHEET_STATE_FIELDS = {
    'row': _f('record'),
    'member_results': _f('records'),
    'version': _f('vocab', vocab=(ROW_SHEET_VERSION,)),
}

# The MAIN SHEET row: one row per class for each candidate, fed by merger 2 from the subscoring rows.
MAIN_ROW_FIELDS = {
    'sheet': _f('vocab', vocab=CLASSES),
    'assertion_ref': _f('ref'),
    'target_id': _f('name'),                                     # OWNER_DECISION 18: equals its source row's target_id; a placeholder carries the commissioned candidate's target
    'row_ref': _f('ref'),
    'source_row_ref': _f('ref'),                                 # the subscoring row (its content-addressed row_ref) this main row stands for; equal to the row's current row_ref exactly when its content is unchanged
    'row_status': _f('vocab', vocab=ROW_STATUS),
    'support': _f('number', lo=0.0, nullable=True),
    'opposition': _f('number', lo=0.0, nullable=True),
    'net': _f('number', nullable=True),
    'weight': _f('number', lo=0.0, hi=1.0),
    'resolution': _f('number', lo=0.0, hi=1.0),
    'credit': _f('number'),
    'experiments': _f('count'),
    'independent_groups': _f('count'),
    'dependence_unit_ref': _f('ref', nullable=True),             # rows collapsed on a shared dataset_ref / source_ref share one
}

# The AXIS output per candidate. Score channel and credit channel, never mixed.
AXIS_FIELDS = {
    'assertion_ref': _f('ref'),
    'target_id': _f('name'),                                     # OWNER_DECISION 18: the subject the score is for
    'support': _f('number', lo=0.0, nullable=True),
    'opposition': _f('number', lo=0.0, nullable=True),
    'net': _f('number', nullable=True),
    'scalar': _f('number', lo=-1.0, hi=1.0, nullable=True),      # tanh(net / 2); null when status is unknown
    'status': _f('vocab', vocab=ROW_STATUS),
    'resolution_main': _f('number', lo=0.0, hi=1.0),
    'credit': _f('number'),
}
AXIS_SCORE_CHANNEL = ('assertion_ref', 'target_id', 'support', 'opposition', 'net', 'scalar', 'status')
AXIS_CREDIT_CHANNEL = ('assertion_ref', 'resolution_main', 'credit')

# investigation_finding FEATURES: read by code from a row (never typed by a model, never prose).
FEATURE_SOURCES = {
    'sheet_ref': 'row_ref',
    'evidence_type': 'sheet',
    'assertion_ref': 'assertion_ref',
    'target_id': 'target_id',   # OWNER_DECISION 18: the investigation_finding says what target the evidence is about
    'number_of_assays': ('experiments', 'independent_groups'),
    'deviation': 'relative_deviation',
    'signal': ('net', 'support', 'opposition'),
    'status': 'row_status',
}
FEATURE_FIELDS = {
    'sheet_ref': _f('ref'),
    'evidence_type': _f('vocab', vocab=CLASSES),
    'assertion_ref': _f('ref'),
    'target_id': _f('name'),
    'experiments': _f('count'),
    'independent_groups': _f('count'),
    'relative_deviation': _f('number', lo=0.0, nullable=True),
    'net': _f('number', nullable=True),
    'support': _f('number', lo=0.0, nullable=True),
    'opposition': _f('number', lo=0.0, nullable=True),
    'status': _f('vocab', vocab=ROW_STATUS),
}

# ---------------------------------------------------------------------------------------------------------------
# (4b) Identity features, the grader grouping and the grader ref (OWNER_DECISIONS 13 and 14; owner rulings B-G).
# New field kinds: 'bool' (a true/false), 'refs' (a non-empty list of distinct record references).
# ---------------------------------------------------------------------------------------------------------------
ROLE = ('analyte', 'immobilized', 'ligand', 'protein', 'other')   # OWNER_DECISIONS 13, 18: the role of the partner in the assay (partner_role)

# Locator vocabularies (OWNER_DECISION 13): where in the document a chunk states a fact; all controlled, never prose.
REFERENCE_KINDS = ('figure', 'table', 'section', 'supplement', 'text')
PANEL_LETTERS = tuple('abcdefghijklmnopqrstuvwxyz')
SECTION_CLASSES = ('abstract', 'introduction', 'methods', 'results', 'discussion', 'figure_legend', 'table', 'supplement', 'other')
LABEL_NUMBER_MAX = 999            # EXPERT_REVIEW: OWNER_DECISION 13: the largest figure/table/section number accepted

# Preparation and reagent descriptor vocabularies (OWNER_DECISION 13); recorded, never identity-bearing.
CONSTRUCT_TAG_CLASSES = ('untagged', 'his_tag', 'gst_tag', 'biotin_tag', 'fusion_protein', 'other_tag')
SPECIES_CLASSES = ('human', 'mouse', 'rat', 'yeast', 'bacterial', 'insect', 'plant', 'viral', 'other')
IMMOBILIZATION_SIDES = ('target', 'partner', 'none')   # OWNER_DECISION 18: which molecule is immobilized (was partner_a / partner_b)
BUFFER_CLASSES = ('phosphate', 'tris', 'hepes', 'acetate', 'carbonate', 'other')
IONIC_STRENGTH_CLASSES = ('low', 'physiological', 'high')

# Why an identity field is unavailable (OWNER_DECISION 13/14): the two reasons the page uses for a field.
UNAVAILABLE_NOT_STATED = 'not_stated_in_passage'
UNAVAILABLE_CONFLICTING = 'ambiguous_or_conflicting_in_passage'
IDENTITY_UNAVAILABLE_REASONS = (UNAVAILABLE_NOT_STATED, UNAVAILABLE_CONFLICTING)

TEMPERATURE_C_RANGE = (-50.0, 150.0)    # EXPERT_REVIEW: OWNER_DECISION 13
PH_RANGE = (0.0, 14.0)

# The identity fields (OWNER_DECISION 13). source_ref is stamped by code from the page, never by the model; every other
# field is returned by the leaf beside its answer and is null (with a reason in unavailable_reasons) when not stated.
# experiment_type is a vocabulary and never null (a leaf that cannot name a type has no experiment to group).
# OWNER_DECISION 18: the identity number fields (temperature_c, ph) have no unit key. Every identity number is stated by the
# leaf form in the field's canonical unit (temperature_c in degrees Celsius), so the code never has to guess a unit; the
# leaf form converts to it.
IDENTITY_FIELDS = {
    'source_ref': _f('ref'),                                                      # the document; stamped by code
    'experiment_type': _f('vocab', vocab=EXPERIMENT_TYPES),
    'target_id': _f('name', nullable=True),                                       # OWNER_DECISION 18: the molecule the assay is about (annotation ID or normalized name); the one identity field bearing requires
    'partner_id': _f('name', nullable=True),                                      # OPTIONAL: the other molecule the target is tested against (ligand, binding partner)
    'partner_role': _f('vocab', vocab=ROLE, nullable=True),                       # optional: the role of the partner
    'construct_tag_class': _f('vocab', vocab=CONSTRUCT_TAG_CLASSES, nullable=True),
    'species_class': _f('vocab', vocab=SPECIES_CLASSES, nullable=True),
    'immobilization_side': _f('vocab', vocab=IMMOBILIZATION_SIDES, nullable=True),
    'buffer_class': _f('vocab', vocab=BUFFER_CLASSES, nullable=True),
    'analyte_preparation_ref': _f('ref', nullable=True),                          # the four existing preparation refs
    'immobilized_preparation_ref': _f('ref', nullable=True),                      # (ROW_DEPENDENCE_KEYS), when known to the page
    'surface_ref': _f('ref', nullable=True),
    'dataset_ref': _f('ref', nullable=True),
    'temperature_c': _f('number', lo=TEMPERATURE_C_RANGE[0], hi=TEMPERATURE_C_RANGE[1], nullable=True),
    'ph': _f('number', lo=PH_RANGE[0], hi=PH_RANGE[1], nullable=True),
    'ionic_strength_class': _f('vocab', vocab=IONIC_STRENGTH_CLASSES, nullable=True),
    'reference_kind': _f('vocab', vocab=REFERENCE_KINDS, nullable=True),
    'label_number': _f('count', hi=LABEL_NUMBER_MAX, nullable=True),
    'panel_letter': _f('vocab', vocab=PANEL_LETTERS, nullable=True),
    'section_class': _f('vocab', vocab=SECTION_CLASSES, nullable=True),
    'span_start': _f('count', nullable=True),                                     # the chunk's absolute document byte span
    'span_end': _f('count', nullable=True),
    'unavailable_reasons': _f('map'),                                             # field name -> IDENTITY_UNAVAILABLE_REASONS; exactly the null fields
}
CODE_STAMPED_IDENTITY = ('source_ref',)
# OWNER_DECISION 13 (owner ruling E): the identity fields that EVERY extraction answer carries beside its answer.
LEAF_RECORD_IDENTITY = tuple(name for name in IDENTITY_FIELDS if name not in CODE_STAMPED_IDENTITY)

# Per-feature comparison result and the pair result (OWNER_DECISION 13). Missing is skipped, never a conflict.
IDENTITY_COMPARISON = ('agree', 'conflict', 'missing')
IDENTITY_PAIR_RESULT = ('same', 'different')
IDENTITY_COMPARE_FIELDS = {   # the result of identity_compare
    'features': _f('map'),                       # feature -> IDENTITY_COMPARISON, for every key of IDENTITY_FEATURES
    'result': _f('vocab', vocab=IDENTITY_PAIR_RESULT),
    'positive_tie': _f('bool'),                  # an agreeing identity-bearing name, label, target or partner; recorded, never required
}

# OWNER_DECISION 13: the same document and the same experiment_type are required; DEFAULT = MERGE; split only on a conflict.
IDENTITY_MUST_MATCH = ('source_ref', 'experiment_type')
IDENTITY_DEFAULT = 'merge'
IDENTITY_SPLIT_ONLY_ON = 'conflict_of_an_identity_bearing_feature_both_sides_state'
IDENTITY_NUMBER_TOLERANCE = {'temperature_c': 1.0, 'ph': 0.2}   # EXPERT_REVIEW: OWNER_DECISION 13: two stated numbers closer than this agree
# IDENTITY_FEATURES: feature -> fields it reads, how it is compared, and whether it is identity-bearing (can split).
# compare modes: 'equal'; 'equal_normalized' (equality after IDENTITY_REF_NORMALIZATION: casefold and whitespace collapse;
# a side that does not state the field is skipped, never a conflict); 'equal_within_tolerance' (IDENTITY_NUMBER_TOLERANCE);
# 'span_overlap' (agree when the byte spans overlap).
# Identity-bearing (EXPERT_REVIEW: the owner may narrow the condition list): the target identity and the partner identity
# (OWNER_DECISION 18; two experiments with different targets, or different partners, in one document are different
# experiments), the figure/table/section label (kind + number), and the conditions temperature, pH and ionic strength
# class. Everything else is only recorded: its comparison result is kept in the grader's identity summary and never splits.
IDENTITY_FEATURES = {   # OWNER_DECISIONS 13, 18
    'target_id': {'fields': ('target_id',), 'compare': 'equal_normalized', 'bearing': True},
    'partner_id': {'fields': ('partner_id',), 'compare': 'equal_normalized', 'bearing': True},
    'locator_label': {'fields': ('reference_kind', 'label_number'), 'compare': 'equal', 'bearing': True},
    'temperature_c': {'fields': ('temperature_c',), 'compare': 'equal_within_tolerance', 'bearing': True},
    'ph': {'fields': ('ph',), 'compare': 'equal_within_tolerance', 'bearing': True},
    'ionic_strength_class': {'fields': ('ionic_strength_class',), 'compare': 'equal', 'bearing': True},
    'partner_role': {'fields': ('partner_role',), 'compare': 'equal', 'bearing': False},
    'construct_tag_class': {'fields': ('construct_tag_class',), 'compare': 'equal', 'bearing': False},
    'species_class': {'fields': ('species_class',), 'compare': 'equal', 'bearing': False},
    'immobilization_side': {'fields': ('immobilization_side',), 'compare': 'equal', 'bearing': False},
    'buffer_class': {'fields': ('buffer_class',), 'compare': 'equal', 'bearing': False},
    'preparation_refs': {'fields': ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref'), 'compare': 'equal', 'bearing': False},
    'panel_letter': {'fields': ('panel_letter',), 'compare': 'equal', 'bearing': False},
    'section_class': {'fields': ('section_class',), 'compare': 'equal', 'bearing': False},
    'byte_span': {'fields': ('span_start', 'span_end'), 'compare': 'span_overlap', 'bearing': False},
}
IDENTITY_BEARING = tuple(name for name, spec in IDENTITY_FEATURES.items() if spec['bearing'])   # OWNER_DECISION 13

# OWNER_DECISION 18: how two target or partner identities are made comparable: casefold, then collapse every run of
# whitespace to one space (and strip). identity_compare, the grader's field statements and bearing all use normalize_identity_ref.
IDENTITY_REF_NORMALIZATION = ('casefold', 'collapse_whitespace', 'unicode_dashes_to_hyphen')
# The dash characters papers use inside a molecule name (hyphen U+2010, non-breaking hyphen, figure dash, en dash, em dash,
# horizontal bar, minus sign); all compare as the ASCII hyphen so 'PPARγ‐DL' and 'PPARγ-DL' are one molecule.
_UNICODE_DASHES = dict.fromkeys(map(ord, '‐‑‒–—―−'), '-')
IDENTITY_NORMALIZED_REF_FIELDS = ('target_id', 'partner_id')   # the identity fields compared after IDENTITY_REF_NORMALIZATION


def normalize_identity_ref(value):
    """A target or partner identity in its comparable form: casefolded, whitespace collapsed (IDENTITY_REF_NORMALIZATION)."""
    if not isinstance(value, str):
        raise ValueError(f'an identity reference must be a string: {value!r}')
    return ' '.join(value.translate(_UNICODE_DASHES).split()).casefold()

# Finalizing and stating a field (OWNER_DECISIONS 13 and 14; owner ruling F).
FINALIZE_WHEN = ('no_unread_chunk_or_table_in_neighbourhood', 'routing_has_no_further_candidate')   # OWNER_DECISION 14
SKIPPED_GRADER = 'source_grounded_no_applicable_experiment'   # OWNER_DECISION 14: the only grader not converted into a sheet update
STATE_DEDUPE_KEY = 'absolute_byte_span'                       # OWNER_DECISION 14: the same value from overlapping chunks is one stated support
LEAF_RECORDS_IMMUTABLE = True                                 # OWNER_DECISION 14: a grader is a derived, re-derivable grouping of them
GRADER_DERIVED_BY = 'code'                                    # OWNER_DECISION 14: the model returns identity features, never identity
CREDIT_FOR_REPEATED_FACT = 0.0                                # OWNER_DECISION 14: a repeat of an already-held fact earns nothing

# The grader ref record (OWNER_DECISION 14; owner ruling G): assigned by the page from its grouping. The experiment_ref a
# caller supplied before is not an identity.
GRADER_REF_FIELDS = {
    'grader_ref': _f('ref'),
    'source_ref': _f('ref'),
    'experiment_type': _f('vocab', vocab=EXPERIMENT_TYPES),
    'member_record_refs': _f('refs', lo=1),                   # the leaf records grouped into this grader (at least one)
    'finalized': _f('bool'),
    'identity_summary': _f('map'),                            # feature (IDENTITY_FEATURES) -> IDENTITY_COMPARISON across the members
    'conflicting_field_names': _f('refs', lo=0),              # fields held CONFLICTING; may be an empty list; COMPUTED by group_leaf_records (from state_grader_fields of the members), never given by a caller
}

# Where the identity features sit on a LEAF RECORD (OWNER_DECISION 13; the leaf record is the extraction record of one
# chunk or table): the features of LEAF_RECORD_IDENTITY are TOP-LEVEL keys of the leaf record, beside source_ref and
# experiment_type. A missing key or a None value means NOT STATED (never a number, never a guess). The member record ref
# of a grader (GRADER_REF_FIELDS.member_record_refs) is the leaf record's 'experiment_ref' key; it is a reference only and
# never an identity (owner ruling G).
LEAF_RECORD_IDENTITY_PLACEMENT = 'top_level_keys_beside_source_ref_and_experiment_type'   # OWNER_DECISION 13
LEAF_RECORD_MISSING_MEANS = 'not_stated'                                                  # OWNER_DECISION 13
LEAF_RECORD_REF_KEY = 'experiment_ref'                                                    # OWNER_DECISION 14

# Extra keys the identity block of a leaf record writes (literature_identity_extraction.with_identity), beside the form's own
# record and the LEAF_RECORD_IDENTITY keys. Both are read by literature_grader_record.merged_record.
#   identity_provenance  {identity field: {'span_ref': 'span_identity_<field>', 'support': a quote-support class}} for every
#                        identity field the answer states (an unstated field has no entry)
#   spans['span_identity_<field>']  {'locator': 'bytes a-b of the source' (absolute), 'quote': the quote}: the span
#                        identity_provenance[<field>]['span_ref'] names; it sits in the record's ordinary 'spans' map
LEAF_RECORD_EXTRA_KEYS = {
    'identity_provenance': {'key': 'identity field name', 'value': {'span_ref': 'span_identity_<field>', 'support': 'quote-support class'}},
    'spans.span_identity_<field>': {'locator': 'bytes a-b of the source', 'quote': 'the quote'},
}

# IDENTITY VALUE NORMALIZATION (OWNER_DECISION 13): before two stated values are compared (identity_compare) or deduplicated
# (state_grader_fields), BOTH are normalized to the canonical unit of their quantity, so 1 uM equals 1000 nM. A value is
# canonical_value = value * factor[unit] + offset.get(unit, 0.0). The factors are the existing converters' unit tables
# (NM_PER_UNIT of the *_criteria modules, for example literature_dialysis_criteria: pM 0.001, nM 1, uM 1000, mM 1e6;
# NM_PER_M 1e9 of literature_spr_criteria for M; S_PER_UNIT of literature_fcs_criteria and literature_mst_criteria: s 1,
# min 60, ms 0.001; h 3600 follows from MIN_PER_UNIT of the other criteria modules, h = 60 min; KELVIN_OFFSET 273.15 of
# literature_itc_criteria). The temperature identity field is
# temperature_c, so its canonical unit is C (K converts with offset -273.15). A value whose unit is not in the table of its
# quantity cannot be normalized: canonical_value raises ValueError; identity_compare then treats that side as NOT STATED
# (missing, never a conflict). EXPERT_REVIEW: this last default is the contract's, the owner may change it.
IDENTITY_UNIT_CANONICAL = {   # OWNER_DECISION 13
    'concentration': {'canonical': 'nM', 'factors': {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0, 'M': 1000000000.0}, 'offsets': {}},
    'time': {'canonical': 's', 'factors': {'ms': 0.001, 's': 1.0, 'min': 60.0, 'h': 3600.0}, 'offsets': {}},
    'temperature': {'canonical': 'C', 'factors': {'C': 1.0, 'K': 1.0}, 'offsets': {'K': -273.15}},
}
IDENTITY_QUANTITY_OF_FIELD = {'temperature_c': 'temperature'}   # identity field -> quantity kind; fields not listed here carry no unit


def canonical_value(quantity, value, unit):
    """The value in the canonical unit of its quantity (IDENTITY_UNIT_CANONICAL): value * factor[unit] + offset[unit].
    Raises ValueError for an unknown quantity, a unit outside its table, or a value that is not a finite number."""
    if quantity not in IDENTITY_UNIT_CANONICAL:
        raise ValueError(f'unknown quantity kind {quantity!r}')
    table = IDENTITY_UNIT_CANONICAL[quantity]
    if unit not in table['factors']:
        raise ValueError(f'unit {unit!r} is not in the {quantity} table')
    if not _is_number(value):
        raise ValueError(f'value must be a finite number: {value!r}')
    return value * table['factors'][unit] + table['offsets'].get(unit, 0.0)


# The features whose agreement is a POSITIVE TIE (recorded, never required); identity_compare reads this.
POSITIVE_TIE_FEATURES = ('target_id', 'partner_id', 'locator_label')   # EXPERT_REVIEW: OWNER_DECISIONS 13, 18

# The result of state_grader_fields(member_records): {field name: entry}. Field names are generic record paths
# ('quantities.<name>', 'operands.<name>', 'facts.<name>', 'choices.<name>'), never prose. Entry rules in validate_state_grader_fields.
STATE_FIELD_STATUS = ('stated', 'unavailable')
STATE_FIELD_FIELDS = {
    'status': _f('vocab', vocab=STATE_FIELD_STATUS),
    'values': _f('records'),        # each {'value': scalar or a list of numbers (a series, for example a concentration series, with its unit), 'unit': ref or null, 'spans': [[start, end], ...]}; empty when unavailable
    'conflicting': _f('bool'),      # true when different values were stated, or the field was ambiguous in a passage
    'reason': _f('vocab', vocab=IDENTITY_UNAVAILABLE_REASONS, nullable=True),
}

# ---------------------------------------------------------------------------------------------------------------
# (6) SIGNATURES: documentation constants for the functions the later steps write (not implementations).
# ---------------------------------------------------------------------------------------------------------------
SIGNATURES = {
    'bearing': {
        'module': 'literature_bearing',
        'args': ('record', 'claim'),
        'returns': {'bearing': 'BEARING', 'reasons': 'list of controlled reason codes (not prose)'},
        'target_note': 'OWNER_DECISION 18: a converted result carries the experiment target_id (non-null when direct); a row, main row, axis output and feature record carry the target_id of the score (equal to the claim subject_id)',
        'note': 'code, not the model; only direct gives support or opposition. OWNER_DECISION 18: record carries experiment_type, target_id and partner_id; direct iff the class bears the predicate and the normalized target_id equals the normalized claim subject_id and, when both sides state a partner, partner_id equals the claim partner_id; different_subject when a target is stated and differs from the subject (or both partners are stated and differ); none when the target is not stated (reason target_not_stated) or the predicate is not borne; transfer is not produced',
    },
    'direction_and_ratio': {
        'module': 'literature_direction',
        'args': ('converted',),
        'returns': {'direction': 'DIRECTION', 'log_ratio': 'number >= 0 or null', 'effect_support': 'number 0..1 or null'},
        'note': 'OWNER_DECISION 15: quantitative: a graded strength s in [0, 1] from the effect and its variance on the type scale (QUANTITATIVE_STRENGTH, QUANTITATIVE_STRENGTH_ANCHORS), supports when s > 0, neutral at 0, log_ratio = QUALITATIVE_LOG_RATIO[type] * s (criteria never gate it); qualitative: QUALITATIVE_LOG_RATIO[type]; unstated: unknown with null; called only for a direct result (the claim is not read); effect_support from converted direction_field_support (OWNER_DECISION 17), required when the direction is known',
    },
    'criterion_resolution': {
        'module': 'literature_resolution',
        'args': ('status', 'degree'),
        'returns': 'float r_c for the WEIGHT (conflicting 0, unknown 0); not_applicable is dropped by the caller',
    },
    'criterion_resolved': {
        'module': 'literature_resolution',
        'args': ('status', 'degree'),
        'returns': 'float r_c for the CREDIT (conflicting 1, unknown 0)',
    },
    'row_weight': {
        'module': 'literature_resolution',
        'args': ('results',),
        'returns': 'float w in [0, 1] = sum r_c / N_applicable',
    },
    'row_resolution': {
        'module': 'literature_resolution',
        'args': ('row',),
        'returns': 'float R in [0, 1] = mean over the criteria and CREDIT_QUESTIONS_EXTRA',
        'note': 'reads the stored ROW_FIELDS boolean independence_known (no separate key is passed); the pooled supported criterion carries the minimum degree (OWNER_DECISION 4a)',
    },
    'credit_change': {
        'module': 'literature_resolution',
        'args': ('before', 'after'),
        'returns': 'float R(after) - R(before); unbounded',
    },
    'group_by_candidate': {
        'module': 'literature_row',
        'args': ('results',),
        'returns': '{(sheet, assertion_ref): [results with bearing direct]}',
    },
    'merge_row_state': {
        'module': 'literature_row',
        'args': ('sheet', 'assertion_ref', 'results', 'prior_row=None'),
        'returns': 'the updated sheet STATE (SHEET_STATE_FIELDS): {row: a PARTIAL row, member_results: ordered by result_ref, version}',
        'note': 'OWNER_DECISION 18: the row target_id is the (normalized) target_id of its direct results; results of one (sheet, assertion_ref) with different targets are refused by validate_sheet_state; prior_row is the prior STATE (a dict with row and member_results), or None for the first fill; a repeat result (same result_ref) changes nothing and earns no credit; the output does not depend on arrival order; validate with validate_sheet_state',
    },
    'merge_row': {
        'module': 'literature_row',
        'args': ('sheet', 'assertion_ref', 'results', 'prior_row=None'),
        'returns': 'the PARTIAL row (PARTIAL_ROW_FIELDS: ROW_FIELDS without ROW_CALLER_FIELDS weight, resolution, credit) of merge_row_state',
        'note': 'prior_row is the prior STATE (as returned by merge_row_state), not a row; complete_row then fills weight, resolution and credit',
    },
    'complete_row': {
        'module': 'literature_row',
        'args': ('row', 'weight', 'resolution', 'credit'),
        'returns': 'a complete ROW (ROW_FIELDS), validated with validate_row',
        'note': 'weight from row_weight, resolution from row_resolution(row), credit from credit_change(before, after); the partial row is not changed; a row that already holds one of the three is refused',
    },
    'merge_main': {
        'module': 'literature_main_sheet',
        'args': ('rows', 'classes_needed', 'prior_main=None', 'targets=None'),
        'returns': 'a list of MAIN ROWS (MAIN_ROW_FIELDS) with cross-class dependence recorded (dependence_unit_ref)',
        'targets': '{assertion_ref: target_id} (optional last argument): the commissioned target of each commissioned candidate; a placeholder row needs its candidate target from here; when given, every row target must equal it; a key that is not a commissioned candidate raises ValueError',
        'note': 'a main row whose source_row_ref equals the subscoring row row_ref is unchanged (the row_ref is content-addressed: it changes when the member results change) and is carried with credit 0.0. OWNER_DECISION 18: every main row, placeholder included, carries target_id = its source row target_id (a placeholder: the commissioned candidate target); rows are complete subscoring rows (ROW_FIELDS) that may carry the optional input keys MAIN_ROW_INPUT_KEYS (dataset_ref, source_ref), stamped by the page and stripped before validate_row / validate_main_row; classes_needed = {assertion_ref: classes commissioned (N_k)}; a commissioned class with no row gets a placeholder (source_row_ref NO_ROW_REF); a row of an uncommissioned class or candidate raises ValueError, no repair; OWNER_DECISION 16',
    },
    'axis_output': {
        'module': 'literature_axis_output',
        'args': ('main_sheet',),
        'returns': {'score': AXIS_SCORE_CHANNEL, 'credit': AXIS_CREDIT_CHANNEL},
        'note': 'OWNER_DECISION 18: the score channel names the subject (target_id) the score is for; the credit channel does not carry it beside resolution_main and credit apart from assertion_ref; the signature stays: the commissioned classes (N_k) and the before state reach it THROUGH the main sheet, not as arguments: placeholder rows (source_row_ref NO_ROW_REF: status unknown, null scores, weight 0.0, resolution 0.0, credit 0.0) stand for commissioned classes without a row, and each main row carries its own credit (R(after) - R(before)); a row of an uncommissioned class or candidate was already refused by merge_main (ValueError, wrong commissions fail, nothing repairs them). OWNER_DECISION 16 collapse: rows sharing a dependence_unit_ref (dataset first, then source) are one unit with the MEAN support and opposition over the unit rows of known status; a row with no unit key is independent; the axis sums over units, scalar = tanh(net / AXIS_SCALAR_DIVISOR); credit = mean of the row credits over N_k',
    },
    'row_features': {
        'module': 'literature_sheet_features',
        'args': ('row',),
        'returns': 'FEATURE_FIELDS read by code from the row',
    },
    'identity_compare': {
        'module': 'literature_identity',
        'args': ('record_a', 'record_b'),
        'returns': {'features': 'feature -> IDENTITY_COMPARISON (agree | conflict | missing) for every IDENTITY_FEATURES key', 'result': 'same | different', 'positive_tie': 'bool'},
        'note': 'OWNER_DECISIONS 13, 18: code, not the model; different only for a different source_ref or experiment_type, or a conflict on an IDENTITY_BEARING feature (target_id, partner_id, locator_label, temperature_c, ph, ionic_strength_class) that both sides state; target_id and partner_id compare equal after IDENTITY_REF_NORMALIZATION; missing is skipped',
    },
    'group_leaf_records': {
        'module': 'literature_identity',
        'args': ('leaf_records',),
        'returns': 'list of graders (GRADER_REF_FIELDS, finalized false), each a grouping of immutable leaf records',
        'note': 'OWNER_DECISION 14: derived by code from what has arrived, re-derivable until the page finalizes; merge by default; the leaf records are never changed; group_leaf_records COMPUTES conflicting_field_names (the fields state_grader_fields finds conflicting over the members); identity features are read as top-level leaf record keys (LEAF_RECORD_IDENTITY_PLACEMENT), the member ref is the leaf record experiment_ref (LEAF_RECORD_REF_KEY)',
    },
    'state_grader_fields': {
        'module': 'literature_identity',
        'args': ('member_records',),
        'returns': '{field name: STATE_FIELD_FIELDS entry}: status stated | unavailable, values [{value, unit, spans}], conflicting, reason (None | not_stated_in_passage | ambiguous_or_conflicting_in_passage); checked by validate_state_grader_fields',
        'note': 'OWNER_DECISION 14: STATE_DEDUPE_KEY absolute byte span: the same value (after IDENTITY_UNIT_CANONICAL normalization) from overlapping chunks is one stated value; different values keep both and mark the field conflicting; the member records are not changed. OWNER_DECISION 18: the identity fields target_id and partner_id are stated as fields identity.target_id and identity.partner_id (values deduplicated after IDENTITY_REF_NORMALIZATION); identity.target_id unavailable means no member states a target',
    },
    'merged_record': {
        'module': 'literature_grader_record',
        'args': ('experiment_type', 'member_records', 'grader_ref'),
        'returns': 'the record of one finalized grader in the shape the type grade function reads (experiment_ref and assertion_ref are the grader_ref)',
        'note': 'the grader_ref is the third argument because it cannot be derived from the members here; the page passes grader[grader_ref]; member records of another type, repeated refs or different versions raise ValueError',
    },
    'finalize_grader': {
        'module': 'literature_identity',
        'args': ('grader',),
        'returns': 'a grader record (GRADER_REF_FIELDS, finalized true) with its fields stated, dedupe on absolute byte spans, unstated fields unavailable (not_stated_in_passage), differing values kept conflicting',
        'note': 'OWNER_DECISION 14: every grader is finalized and converted, incomplete ones included; only SKIPPED_GRADER is not',
    },
    'page_update': {
        'module': 'literature_page_update',
        'args': ('sheet_state', 'graders', 'claims'),
        'graders': "list of {'grader': a FINALIZED grader record (GRADER_REF_FIELDS), 'member_records': [the leaf records of its member_record_refs]} with an optional 'finding' key; an item whose 'finding' is SKIPPED_GRADER is skipped",
        'claims': 'a dict keyed by assertion_ref; each value is a claim with exactly CLAIM_FIELDS (a claim carries no assertion_ref, so the key is the candidate ref)',
        'returns': {'sheet_state': 'the updated persistent subscoring sheet', 'rows': 'list of ROW_FIELDS rows', 'main_sheet': 'list of MAIN_ROW_FIELDS rows', 'axis': 'list of AXIS_FIELDS outputs', 'credit': 'per-candidate credit (number)', 'scores': 'per-annotation scores (controlled numbers)', 'features': 'list of FEATURE_FIELDS records (investigation_finding features), one per row, read by code from the row (row_features)'},
        'note': 'OWNER_DECISION 10: runs at the page; merger 1 as an update of the sheet (compared with what it holds, cross-document dependence included), merger 2, credit and scores in the same step; the levels above only receive credit and scores. sheet_state = {(sheet, assertion_ref): SHEET_STATE}; the page stamps dataset_ref and source_ref (MAIN_ROW_INPUT_KEYS) on each subscoring row it hands to merge_main (they are stripped before validate_main_row); credit and scores stay two separate outputs at both levels',
    },
}

# ---------------------------------------------------------------------------------------------------------------
# (8) OWNER_DECISIONS: the default applied for each of the 12 decisions of section 4 of the design report, and decisions
# 13 and 14 (owner rulings of 2026-11-20). Decision 10 is rewritten by owner ruling A; it changes the 'where' of 6 and 11.
# ---------------------------------------------------------------------------------------------------------------
OWNER_DECISIONS = {
    1: ('candidate claim shape', 'predicate vocabulary + subject_id + partner_id; a claim names molecules only and never carries a physical prediction or threshold (owner ruling of 2026-11-21) (CLAIM_FIELDS, CLAIM_PREDICATES_BY_CLASS)'),
    2: ('evidence magnitude constants', 'expert-review QUALITATIVE_LOG_RATIO per experiment type in this file, also the per-type maximum of a quantitative result; proposals'),
    3: ('direction of a quantitative result', 'graded, sheet-side, from the measurement itself (owner ruling of 2026-11-21): a strength s in [0, 1] on the type scale (QUANTITATIVE_STRENGTH, decision 15); s > 0 supports, s == 0 neutral (NEUTRAL_LOG_RATIO); a quantitative result never opposes'),
    4: ('weight rule', 'w = sum r_c / N_applicable; unknown counts 0.9 (WEIGHT_UNKNOWN, owner 2026-11-21), conflicting 0 (WEIGHT_*). Sub-rules (defaults): 4a a pooled supported criterion carries the MINIMUM degree over the experiments (WEIGHT_POOLED_DEGREE); 4b a result with no applicable criterion has the unvetted weight WEIGHT_UNKNOWN (WEIGHT_NO_APPLICABLE_CRITERIA); 4c the row weight is the mean of the per-result weights (ROW_WEIGHT_RULE); 4d group means divide by ALL members, so an unknown-direction member dilutes its group (GROUP_MEAN_DIVIDES_BY); 4e a group counts as known when any member direction is known (GROUP_KNOWN_WHEN)'),
    5: ('credit definition and N_k', 'R = mean open-question resolution, conflicting resolved; N_k = classes the parent commissioned (RESOLVED_*, CREDIT_QUESTIONS_EXTRA)'),
    6: ('cross-class dependence at merger 2', 'collapse rows on a shared dataset_ref, then source_ref (CROSS_CLASS_DEPENDENCE_KEYS); runs at the page in the sheet-update step (decision 10); the collapse statistic is decision 16'),
    7: ('net or split at the axis-to-root boundary', 'one scalar tanh(net / 2), with support and opposition also returned (AXIS_SCALAR_DIVISOR, AXIS_FIELDS)'),
    8: ('quote support on the direction field', 'yes: effect_support multiplies the magnitude (EFFECT_SUPPORT_FROM); where it comes from is decision 17'),
    9: ('preparation identity capture', 'controlled annotation fields in each extraction plus a vocabulary answer for same-preparation; unknown stays dependent (ROW_DEPENDENCE_KEYS)'),
    10: ('where converters and mergers run, sheet requirement (OWNER RULING A, 2026-11-20; replaces the earlier proposal that literature/head run mergers 1 and 2)', 'the PAGE finalizes each grader and updates a persistent subscoring sheet (merger 1, the sheet is the accumulator, compared with what it already holds); that update updates the main scoring sheet (merger 2), the credit and the per-annotation scores in the same step; levels above the page only receive credit and scores as controlled numbers and compute nothing; chunk and table leaves are extractors only; saved through the scoped store, credit read only from saved rows (WHERE_IT_RUNS, MERGER_1_RUNS_AT, MERGER_2_RUNS_AT, LEAVES_CONVERT_OR_MERGE, LEVELS_ABOVE_PAGE_*, CREDIT_READ_FROM)'),
    11: ('credit combination at the root', "the per-candidate credit vector, computed at the page (decision 10), goes up unchanged; the owner states the root's form (CREDIT_UPWARD)"),
    12: ('delete the old path', 'delete the old per-assertion aggregate, reason/required_grading for A105, criteria_counts as credit (OLD_PATH_DELETED)'),
    13: ('identity rule (OWNER RULING D, 2026-11-20)', 'same source_ref and same experiment_type merge by default; split only on a conflict of an identity-bearing feature both sides state; per feature agree/conflict/missing, missing skipped; a measured-value difference is held conflicting inside one grader, never a split; a positive tie is recorded, not required (IDENTITY_MUST_MATCH, IDENTITY_DEFAULT, IDENTITY_FEATURES, IDENTITY_BEARING, IDENTITY_FIELDS, IDENTITY_COMPARISON, LEAF_RECORD_IDENTITY)'),
    14: ('immutable leaf records, derived grader grouping (OWNER RULINGS B, C, F, G, 2026-11-20)', 'one experiment = one grader (one version, one document, never spanning documents); leaf records are immutable; a grader is a code-derived, re-derivable grouping of them until the page finalizes; every grader is finalized and converted, incomplete ones included, except a source-grounded no-applicable-experiment finding; dedupe on absolute byte spans; a repeat earns no credit; the page assigns grader_ref (GRADER_REF_FIELDS, FINALIZE_WHEN, SKIPPED_GRADER, STATE_DEDUPE_KEY, LEAF_RECORDS_IMMUTABLE, GRADER_DERIVED_BY, CREDIT_FOR_REPEATED_FACT)'),
    15: ('graded strength of a quantitative result; criteria never gate it (owner ruling of 2026-11-21)', 'the strength s = smoothstep(p) / (1 + r^2), p the position of log10 of the constant between the type noise end (0) and strong end (1), r = sqrt(v) / e the relative uncertainty (0 when not stated); the anchors are the ends of a gray scale, never thresholds; log_ratio = QUALITATIVE_LOG_RATIO[type] * s; criteria statuses and degrees lower the weight only and never remove a direction (QUANTITATIVE_STRENGTH, QUANTITATIVE_STRENGTH_ANCHORS)'),
    16: ('cross-class collapse rule (revision of 2026-11-20; default)', 'main rows sharing a dataset_ref (first) or else a source_ref collapse to one unit using the MEAN support and opposition over the unit rows of known status; a row with neither key is independent; the axis sums over units (CROSS_CLASS_COLLAPSE_RULE, MAIN_ROW_INPUT_KEYS, CROSS_CLASS_DEPENDENCE_KEYS)'),
    18: ('target molecule (OWNER RULING, 2026-11-20)', "every experimental grader has a target molecule: target_id (the molecule the assay is about), optional partner_id and partner_role replace partner_a_*/partner_b_*; bearing requires the target: no stated target gives bearing none (target_not_stated), no score, credit as the resolution says, and no 'target known' question is added; direct iff the class bears the predicate and the normalized target_id equals the claim subject_id and, when both sides state a partner, the partner_ids are equal; different_subject when the stated target differs from the subject or both partners are stated and differ; a result of a SYMMETRIC predicate (SYMMETRIC_PREDICATES, binds) whose target is the claim's partner and whose partner is the claim's subject IS direct (reason partner_route); the row and score still belong to the claim's subject; transfer stays unused; the target applies at every level: a converted result, every subscoring row, every main row (placeholders too), the axis score channel and the investigation_finding features carry the target_id the score is about (the scoring sheet IS the annotation score, one per candidate per target; credit stays a separate quantity); target_id and partner_id are identity-bearing, compared by equality after casefold and whitespace collapse, missing skipped, agreeing is a positive tie; every identity number is stated by the leaf form in the field's canonical unit (IDENTITY_FIELDS, IDENTITY_FEATURES, POSITIVE_TIE_FEATURES, IDENTITY_REF_NORMALIZATION)"),
    17: ('effect support (revision of 2026-11-20; default)', 'a converted result carries direction_field_support, copied from the support class of the field that fixes the direction: the KD operand for a quantitative result, the field(s) the statement derives from for a qualitative one, the weakest if several; effect_support = SUPPORT_FACTORS[direction_field_support] (EFFECT_SUPPORT_FIELD, SUPPORT_WEAKEST_ORDER, RESULT_FIELDS.direction_field_support)'),
}


# ---------------------------------------------------------------------------------------------------------------
# (7) Validators: small and strict. They raise ValueError on the first violation; they repair nothing.
# ---------------------------------------------------------------------------------------------------------------
def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_field(owner, name, spec, value):
    if value is None:
        if not spec['nullable']:
            raise ValueError(f'{owner}.{name} must not be null')
        return
    kind = spec['kind']
    if kind == 'vocab':
        if value not in spec['vocab']:
            raise ValueError(f'{owner}.{name} is outside its vocabulary: {value!r}')
    elif kind == 'number':
        if not _is_number(value):
            raise ValueError(f'{owner}.{name} must be a finite number: {value!r}')
        if spec['lo'] is not None and value < spec['lo']:
            raise ValueError(f'{owner}.{name} is below {spec["lo"]}: {value!r}')
        if spec['hi'] is not None and value > spec['hi']:
            raise ValueError(f'{owner}.{name} is above {spec["hi"]}: {value!r}')
    elif kind == 'count':
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f'{owner}.{name} must be a count (int >= 0): {value!r}')
        if spec['hi'] is not None and value > spec['hi']:
            raise ValueError(f'{owner}.{name} is above {spec["hi"]}: {value!r}')
    elif kind == 'bool':
        if not isinstance(value, bool):
            raise ValueError(f'{owner}.{name} must be true or false: {value!r}')
    elif kind == 'record':
        if not isinstance(value, dict):
            raise ValueError(f'{owner}.{name} must be a mapping')
    elif kind == 'records':
        if not isinstance(value, (list, tuple)) or not all(isinstance(item, dict) for item in value):
            raise ValueError(f'{owner}.{name} must be a list of mappings')
    elif kind == 'refs':
        if not isinstance(value, (list, tuple)):
            raise ValueError(f'{owner}.{name} must be a list of record references')
        least = 1 if spec['lo'] is None else spec['lo']
        if len(value) < least:
            raise ValueError(f'{owner}.{name} must hold at least {least} reference(s)')
        for item in value:
            if not isinstance(item, str) or not REF_PATTERN.match(item):
                raise ValueError(f'{owner}.{name} has an item that is not a record reference, not prose: {item!r}')
        if len(set(value)) != len(value):
            raise ValueError(f'{owner}.{name} has a repeated reference')
    elif kind == 'ref':
        if not isinstance(value, str) or not REF_PATTERN.match(value):
            raise ValueError(f'{owner}.{name} must be a record reference, not prose: {value!r}')
    elif kind == 'name':
        if not is_name(value):
            raise ValueError(f'{owner}.{name} must be a molecule name (a short exact name, not prose): {value!r}')
    elif kind == 'map':
        _check_map(owner, name, value)
    else:
        raise ValueError(f'{owner}.{name} has an unknown field kind {kind!r}')


def _check_map(owner, name, value):
    if not isinstance(value, dict):
        raise ValueError(f'{owner}.{name} must be a mapping')
    for key, item in value.items():
        if not isinstance(key, str) or not REF_PATTERN.match(key):
            raise ValueError(f'{owner}.{name} has a key that is not a reference: {key!r}')
        if name == 'criteria':
            if item not in CRITERION_STATUS:
                raise ValueError(f'{owner}.{name}[{key}] is outside CRITERION_STATUS: {item!r}')
        elif name == 'interpretation_degrees':
            if not isinstance(item, dict):
                raise ValueError(f'{owner}.{name}[{key}] must map experiment refs to degrees')
            for experiment_ref, degree in item.items():
                if not isinstance(experiment_ref, str) or not REF_PATTERN.match(experiment_ref):
                    raise ValueError(f'{owner}.{name}[{key}] has a key that is not a reference: {experiment_ref!r}')
                if not _is_number(degree) or not 0.0 <= degree <= 1.0:
                    raise ValueError(f'{owner}.{name}[{key}][{experiment_ref}] must be a number in 0..1: {degree!r}')
        elif name == 'interpretations':
            if not isinstance(item, dict) or not set(item) <= {'status', 'degree'} or 'status' not in item:
                raise ValueError(f"{owner}.{name}[{key}] must be {{'status', 'degree'}} with a status (degree optional)")
            if item['status'] not in CRITERION_STATUS:
                raise ValueError(f'{owner}.{name}[{key}].status is outside CRITERION_STATUS: {item["status"]!r}')
            degree = item.get('degree')
            if degree is not None and (not _is_number(degree) or not 0.0 <= degree <= 1.0):
                raise ValueError(f'{owner}.{name}[{key}].degree must be a number in 0..1 or null: {degree!r}')
        elif name == 'qualitative_statements':
            if key not in QUALITATIVE_STATEMENT:
                raise ValueError(f'{owner}.{name} has a key outside QUALITATIVE_STATEMENT: {key!r}')
            if not isinstance(item, int) or isinstance(item, bool) or item < 0:
                raise ValueError(f'{owner}.{name}[{key}] must be a count (int >= 0): {item!r}')
        elif name == 'unavailable_reasons':
            if key not in IDENTITY_FIELDS or key in CODE_STAMPED_IDENTITY or key == 'unavailable_reasons':
                raise ValueError(f'{owner}.{name} names a field that cannot be unavailable: {key!r}')
            if item not in IDENTITY_UNAVAILABLE_REASONS:
                raise ValueError(f'{owner}.{name}[{key}] is outside IDENTITY_UNAVAILABLE_REASONS: {item!r}')
        elif name == 'identity_summary':
            if key not in IDENTITY_FEATURES:
                raise ValueError(f'{owner}.{name} names a feature outside IDENTITY_FEATURES: {key!r}')
            if item not in IDENTITY_COMPARISON:
                raise ValueError(f'{owner}.{name}[{key}] is outside IDENTITY_COMPARISON: {item!r}')
        elif name == 'features':
            if key not in IDENTITY_FEATURES:
                raise ValueError(f'{owner}.{name} names a feature outside IDENTITY_FEATURES: {key!r}')
            if item not in IDENTITY_COMPARISON:
                raise ValueError(f'{owner}.{name}[{key}] is outside IDENTITY_COMPARISON: {item!r}')
        else:
            raise ValueError(f'{owner}.{name} is not a declared mapping field')


def _validate(owner, record, fields):
    if not isinstance(record, dict):
        raise ValueError(f'{owner} must be a mapping')
    extra = sorted(set(record) - set(fields))
    if extra:
        raise ValueError(f'{owner} has fields outside its schema (no open fields): {extra}')
    for name, spec in fields.items():
        if name not in record:
            if spec['required']:
                raise ValueError(f'{owner}.{name} is required')
            continue
        _check_field(owner, name, spec, record[name])


def _require_null(owner, record, names, because):
    for name in names:
        if record[name] is not None:
            raise ValueError(f'{owner}.{name} must be null ({because}); unknown is never a number')


def validate_result(result):
    """Refuse a converted result that misses a field, leaves its vocabulary or range, carries prose or an extra field,
    or breaks the direction rules: unknown (and any bearing other than direct) means null log_ratio and effect_support;
    neutral means log_ratio exactly 0.0. Cross-field rules of the revision of 2026-11-20: an effect variance needs an
    effect, an effect needs its unit; a statement refs list needs a statement; a qualitative result (no measured_effect,
    bearing direct, a statement given) has the direction its statement states (detected supports, not detected opposes,
    not stated unknown); direction_field_support is required when the direction is known and null (or absent) when it is
    unknown (OWNER_DECISION 17); log_ratio never depends on the criteria (OWNER_DECISION 15)."""
    _validate('result', result, RESULT_FIELDS)
    if CLASS_OF_EXPERIMENT_TYPE.get(result['experiment_type']) != result['sheet']:
        raise ValueError('result.sheet is not the class of result.experiment_type')
    if result['bearing'] != 'direct' and result['direction'] != 'unknown':
        raise ValueError("result.direction must be 'unknown' unless bearing is 'direct'")
    if result['bearing'] == 'direct' and result['target_id'] is None:
        raise ValueError("result.target_id is required when bearing is 'direct' (OWNER_DECISION 18)")
    if result.get('effect_variance') is not None and result.get('measured_effect') is None:
        raise ValueError('result.effect_variance is given without result.measured_effect')
    if result.get('measured_effect') is not None and result.get('effect_unit') is None:
        raise ValueError('result.effect_unit is required when result.measured_effect is given')
    if result.get('statement') is None and result.get('statement_support_refs') is not None:
        raise ValueError('result.statement_support_refs is given without result.statement')
    statement = result.get('statement')
    if statement is not None and result['bearing'] == 'direct' and result.get('measured_effect') is None:
        stated_direction = {'interaction_detected': 'supports', 'interaction_not_detected': 'opposes', 'interaction_not_stated': 'unknown'}[statement]
        if result['direction'] != stated_direction:
            raise ValueError(f'result.direction must be {stated_direction!r} for the qualitative statement {statement!r}')
    if result['direction'] == 'unknown':
        _require_null('result', result, ('log_ratio', 'effect_support'), 'direction is unknown')
        _require_null('result', {'direction_field_support': result.get('direction_field_support')}, ('direction_field_support',), 'direction is unknown')
        return result
    if result['log_ratio'] is None or result['effect_support'] is None:
        raise ValueError('result.log_ratio and result.effect_support are required when direction is known')
    if result.get('direction_field_support') is None:
        raise ValueError('result.direction_field_support is required when direction is known (OWNER_DECISION 17)')
    if abs(result['effect_support'] - SUPPORT_FACTORS[result['direction_field_support']]) > 1e-9:
        raise ValueError('result.effect_support must be SUPPORT_FACTORS[result.direction_field_support] (OWNER_DECISION 17)')
    if result['direction'] == 'neutral' and result['log_ratio'] != NEUTRAL_LOG_RATIO:
        raise ValueError('result.log_ratio must be exactly 0.0 for a neutral (measured zero) result')
    return result


def _validate_score_triplet(owner, record, status):
    if status == 'unknown':
        _require_null(owner, record, ('support', 'opposition', 'net'), 'status is unknown')
        return
    for name in ('support', 'opposition', 'net'):
        if record[name] is None:
            raise ValueError(f'{owner}.{name} is required when status is {status}')
    if status == 'measured_zero' and (record['support'] != 0.0 or record['opposition'] != 0.0 or record['net'] != 0.0):
        raise ValueError(f'{owner}: a measured zero has support, opposition and net exactly 0.0')
    if abs(record['net'] - (record['support'] - record['opposition'])) > 1e-9 * max(1.0, abs(record['support']), abs(record['opposition'])):
        raise ValueError(f'{owner}.net must equal support - opposition')


def _validate_row_body(row, fields):
    _validate('row', row, fields)
    _validate_score_triplet('row', row, row['row_status'])
    if row['independent_groups'] > row['experiments']:
        raise ValueError('row.independent_groups exceeds row.experiments')
    if row['row_status'] == 'unknown' and row['measured_effects'] != 0:
        raise ValueError("row.measured_effects must be 0 when row_status is 'unknown'")
    statements = row['qualitative_statements']
    if set(statements) != set(QUALITATIVE_STATEMENT):
        raise ValueError(f'row.qualitative_statements must hold exactly the keys {QUALITATIVE_STATEMENT}')
    if sum(statements.values()) > row['experiments']:
        raise ValueError('row.qualitative_statements counts more experiments than row.experiments')
    if row['qualitative_support_refs'] is not None and statements['interaction_detected'] + statements['interaction_not_detected'] == 0:
        raise ValueError('row.qualitative_support_refs is given without a detected or not-detected statement')
    return row


def validate_partial_row(row):
    """Refuse a PARTIAL row (what merge_row returns: ROW_FIELDS without weight, resolution and credit) under the same
    rules as validate_row; the three ROW_CALLER_FIELDS must be absent."""
    return _validate_row_body(row, PARTIAL_ROW_FIELDS)


def validate_row(row):
    """Refuse a COMPLETE subscoring row that misses a field, leaves its vocabulary or range, carries prose, has a number
    where null is required for status unknown, or whose counts are inconsistent (independent_groups <= experiments;
    the qualitative statement counts hold all three keys and sum to at most experiments)."""
    return _validate_row_body(row, ROW_FIELDS)


def validate_sheet_state(state):
    """Refuse a subscoring sheet STATE (SHEET_STATE_FIELDS) whose row is neither a valid partial nor a valid complete
    row, whose member results are not valid converted results of bearing direct for the row's (sheet, assertion_ref),
    repeat a result_ref or are not ordered by result_ref, or whose version is not ROW_SHEET_VERSION."""
    _validate('state', state, SHEET_STATE_FIELDS)
    row = state['row']
    held = [name for name in ROW_CALLER_FIELDS if name in row]
    if held and len(held) != len(ROW_CALLER_FIELDS):
        raise ValueError('state.row holds some but not all of weight, resolution and credit')
    (validate_row if held else validate_partial_row)(row)
    refs = []
    for result in state['member_results']:
        validate_result(result)
        if result['bearing'] != 'direct':
            raise ValueError('state.member_results holds a result whose bearing is not direct')
        if result['sheet'] != row['sheet'] or result['assertion_ref'] != row['assertion_ref']:
            raise ValueError('state.member_results holds a result of another sheet or candidate')
        if normalize_identity_ref(result['target_id']) != normalize_identity_ref(row['target_id']):
            raise ValueError("state.member_results holds a result whose target_id differs from the row's target_id (OWNER_DECISION 18)")
        refs.append(result['result_ref'])
    if len(set(refs)) != len(refs):
        raise ValueError('state.member_results repeats a result_ref')
    if refs != sorted(refs):
        raise ValueError('state.member_results must be ordered by result_ref')
    return state


def validate_main_row(main_row):
    """Refuse a main-sheet row that misses a field, leaves its vocabulary or range, or carries prose or a number where
    null is required for status unknown. target_id is required (OWNER_DECISION 18); that it equals the source row's
    target_id is checked where the source row is at hand (merge_main), not here."""
    _validate('main_row', main_row, MAIN_ROW_FIELDS)
    _validate_score_triplet('main_row', main_row, main_row['row_status'])
    if main_row['independent_groups'] > main_row['experiments']:
        raise ValueError('main_row.independent_groups exceeds main_row.experiments')
    if main_row['source_row_ref'] == NO_ROW_REF:   # the placeholder of a commissioned class without a row (OWNER_DECISION 16)
        if main_row['row_status'] != 'unknown' or main_row['weight'] != 0.0 or main_row['resolution'] != 0.0 or main_row['credit'] != 0.0 \
                or main_row['experiments'] != 0 or main_row['independent_groups'] != 0 or main_row['dependence_unit_ref'] is not None:
            raise ValueError("main_row with source_row_ref 'no_row' is a placeholder: status unknown, weight, resolution and credit 0.0, no experiments, no dependence unit")
    return main_row


def validate_axis(axis):
    """Refuse an axis output that misses a field, leaves its vocabulary or range, carries prose, has a number where
    null is required for status unknown, or whose scalar is not tanh(net / 2)."""
    _validate('axis', axis, AXIS_FIELDS)
    _validate_score_triplet('axis', axis, axis['status'])
    if axis['status'] == 'unknown':
        _require_null('axis', axis, ('scalar',), 'status is unknown')
    else:
        if axis['scalar'] is None:
            raise ValueError('axis.scalar is required when status is measured or measured_zero')
        if abs(axis['scalar'] - math.tanh(axis['net'] / AXIS_SCALAR_DIVISOR)) > 1e-9:
            raise ValueError('axis.scalar must equal tanh(net / AXIS_SCALAR_DIVISOR)')
    return axis


def validate_identity(identity_features):
    """Refuse the identity features of a leaf record that miss a field, leave a vocabulary or range, carry prose or an
    extra field, leave a null field without a reason (or give a reason for a field that is stated), name a partner_role
    without a partner_id, or give a half or reversed byte span. Unavailable is never a number or a guess."""
    _validate('identity', identity_features, IDENTITY_FIELDS)
    reasons = identity_features['unavailable_reasons']
    for name, spec in IDENTITY_FIELDS.items():
        if name == 'unavailable_reasons':
            continue
        if identity_features[name] is None and name not in reasons:
            raise ValueError(f'identity.{name} is null and needs a reason in unavailable_reasons')
        if identity_features[name] is not None and name in reasons:
            raise ValueError(f'identity.unavailable_reasons names {name}, which is stated')
    if identity_features['partner_role'] is not None and identity_features['partner_id'] is None:
        raise ValueError('identity.partner_role is given without partner_id')
    if (identity_features['span_start'] is None) != (identity_features['span_end'] is None):
        raise ValueError('identity.span_start and identity.span_end are both given or both unavailable')
    if identity_features['span_start'] is not None and identity_features['span_end'] < identity_features['span_start']:
        raise ValueError('identity.span_end is before identity.span_start')
    if identity_features['panel_letter'] is not None and identity_features['label_number'] is None:
        raise ValueError('identity.panel_letter is given without label_number')
    return identity_features


def validate_grader_ref(record):
    """Refuse a grader record that misses a field, leaves its vocabulary, carries prose or an extra field, names a
    feature outside IDENTITY_FEATURES, repeats a member, or holds a CONFLICT on an identity-bearing feature (such records
    belong to different graders and would have been split)."""
    _validate('grader', record, GRADER_REF_FIELDS)
    for feature in IDENTITY_BEARING:
        if record['identity_summary'].get(feature) == 'conflict':
            raise ValueError(f'grader.identity_summary[{feature}] is a conflict of an identity-bearing feature: the members are different experiments')
    return record


def validate_features(record):
    """Refuse an investigation-finding feature record (FEATURE_FIELDS) that misses a field, leaves its vocabulary or
    range, carries prose or an extra field, has a number in net, support or opposition when status is unknown (or null
    when it is not), a measured zero that is not exactly 0.0, or independent_groups above experiments."""
    _validate('features', record, FEATURE_FIELDS)
    _validate_score_triplet('features', record, record['status'])
    if record['independent_groups'] > record['experiments']:
        raise ValueError('features.independent_groups exceeds features.experiments')
    return record


def validate_identity_compare(result):
    """Refuse the result of identity_compare (IDENTITY_COMPARE_FIELDS) that misses a field, leaves its vocabulary, does
    not name exactly the features of IDENTITY_FEATURES, says 'same' although an identity-bearing feature conflicts, or
    whose positive_tie is not 'a POSITIVE_TIE_FEATURES feature agrees'."""
    _validate('identity_compare', result, IDENTITY_COMPARE_FIELDS)
    if set(result['features']) != set(IDENTITY_FEATURES):
        raise ValueError('identity_compare.features must name every key of IDENTITY_FEATURES and nothing else')
    if result['result'] == 'same' and any(result['features'][feature] == 'conflict' for feature in IDENTITY_BEARING):
        raise ValueError("identity_compare.result is 'same' although an identity-bearing feature conflicts")
    if result['positive_tie'] != any(result['features'][feature] == 'agree' for feature in POSITIVE_TIE_FEATURES):
        raise ValueError('identity_compare.positive_tie must be true exactly when a POSITIVE_TIE_FEATURES feature agrees')
    return result


def validate_state_grader_fields(states):
    """Refuse the result of state_grader_fields: a mapping of field name (a reference, not prose) to an entry
    (STATE_FIELD_FIELDS); a stated value may also be a non-empty list of numbers (a series with its unit). A 'stated' entry holds at least one value and has reason null and conflicting false, or holds
    several different values and is conflicting with reason ambiguous_or_conflicting_in_passage. An 'unavailable' entry
    holds no value; its reason is not_stated_in_passage (conflicting false) or ambiguous_or_conflicting_in_passage
    (conflicting true). Each value is {value: a number, string or boolean, unit: a reference or null, spans: [[start,
    end], ...] of absolute byte spans with end >= start}; no two values of a field are equal."""
    if not isinstance(states, dict):
        raise ValueError('states must be a mapping')
    for name, entry in states.items():
        if not isinstance(name, str) or not REF_PATTERN.match(name):
            raise ValueError(f'states has a field name that is not a reference: {name!r}')
        owner = f'states[{name}]'
        _validate(owner, entry, STATE_FIELD_FIELDS)
        if entry['conflicting'] != (entry['reason'] == UNAVAILABLE_CONFLICTING):
            raise ValueError(f'{owner}.conflicting must be true exactly when reason is {UNAVAILABLE_CONFLICTING}')
        seen = []
        for value in entry['values']:
            if set(value) != {'value', 'unit', 'spans'}:
                raise ValueError(f"{owner}.values item must have exactly value, unit and spans")
            if isinstance(value['value'], (list, tuple)):
                if not value['value'] or not all(_is_number(item) for item in value['value']):
                    raise ValueError(f'{owner}.values item value, when a series, must be a non-empty list of finite numbers')
            elif isinstance(value['value'], dict) or value['value'] is None:
                raise ValueError(f'{owner}.values item value must be a number, string, boolean or a list of numbers')
            if isinstance(value['value'], str) and (not value['value'] or len(value['value']) > 200 or '\n' in value['value']):
                raise ValueError(f'{owner}.values item value is a string that is empty, longer than 200 characters or multi-line, so not a controlled value: {value["value"]!r}')
            if isinstance(value['value'], float) and not math.isfinite(value['value']):
                raise ValueError(f'{owner}.values item value must be finite')
            if value['unit'] is not None and (not isinstance(value['unit'], str) or not REF_PATTERN.match(value['unit'])):
                raise ValueError(f'{owner}.values item unit must be a reference or null')
            if not isinstance(value['spans'], list):
                raise ValueError(f'{owner}.values item spans must be a list')
            for span in value['spans']:
                if not isinstance(span, (list, tuple)) or len(span) != 2 or not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in span) or span[1] < span[0]:
                    raise ValueError(f'{owner}.values item has a span that is not [start, end] with 0 <= start <= end: {span!r}')
            key = (type(value['value']).__name__, tuple(value['value']) if isinstance(value['value'], (list, tuple)) else value['value'], value['unit'])
            if key in seen:
                raise ValueError(f'{owner}.values repeats a value')
            seen.append(key)
        if entry['status'] == 'stated':
            if not entry['values']:
                raise ValueError(f'{owner} is stated but holds no value')
            if entry['conflicting'] != (len(entry['values']) > 1):
                raise ValueError(f'{owner} is conflicting exactly when it holds more than one value')
            if not entry['conflicting'] and entry['reason'] is not None:
                raise ValueError(f'{owner} is stated without conflict, so its reason must be null')
        else:
            if entry['values']:
                raise ValueError(f'{owner} is unavailable but holds values')
            if entry['reason'] is None:
                raise ValueError(f'{owner} is unavailable and needs a reason')
    return states
