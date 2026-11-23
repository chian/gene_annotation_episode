"""The A105 row contract: every vocabulary, field list, version, constant and function signature of the A105 scoring
paradigm, in one place. Constants and schemas only; the only code is small validators of a record against a schema.
Every later builder (resolution, target, relevance, direction, row merger, main-sheet merger, axis output, sheet features,
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
* Only a result on the row (target match 'same' or 'related', relevance 'relevant' or 'unresolved'; on_row) gives support or
  opposition, each by its identified_closeness (literature_target; 2026-11-21: closeness of the assayed protein's sequence to the target's). The degree and the quote-support factor are applied
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
* The target match requires the target (it is the one identity field it requires): a grader no member record of which states
  target_id matches no candidate (target_match not_stated, reason target_not_stated), earns no score, and still counts in the
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

ROW_VERSION = 'a105_row_contract'
RESULT_VERSION = 'a105_converted_result'
ROW_SHEET_VERSION = 'a105_subscoring_row'
MAIN_SHEET_VERSION = 'a105_main_scoring_row'
AXIS_VERSION = 'a105_axis_output'
FEATURES_VERSION = 'a105_investigation_features'

# ---------------------------------------------------------------------------------------------------------------
# (2) Classes (sheet names) and the experiment types
# ---------------------------------------------------------------------------------------------------------------
# protein_signal and protein_amount were removed on 2026-11-22 (owner: they answer to no claim; a band that is a reaction product is an
# activity_rate method, a band in a pull-down is the pulldown method, the active fraction is a fact of an activity method, and the
# presence of a protein is context, not activity).
CLASSES = ('activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling', 'ligand_binding', 'transport_response')

EXPERIMENT_TYPES = ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis', 'auc', 'dsf', 'cetsa', 'bret', 'y2h', 'split_reporter', 'pla', 'proximity',
                    'colocalization', 'spectro_direct',
                    'coupled_enzyme', 'redox_mediator', 'fluorogenic', 'luminescent', 'stopped_flow', 'quench_flow', 'chromatographic', 'stopped_colorimetric', 'radiometric',
                    'separation_band', 'oxygen_electrode', 'ph_stat', 'protein_film_electrochem', 'itc_kinetics', 'continuous_ms', 'nmr_timecourse', 'product_immunodetection', 'zymogram',
                    'transport_cell_tracer_uptake', 'transport_counterflow', 'transport_fluorescent_reporter', 'transport_medium_analysis', 'transport_oocyte_two_electrode',
                    'transport_patch_clamp', 'transport_planar_bilayer', 'transport_proteoliposome_tracer', 'transport_ssm_electrophysiology', 'transport_vesicle_probe_flux',
                    'endpoint_colorimetric', 'endpoint_enzymatic_assay', 'endpoint_gas_evolution', 'endpoint_gel_band', 'endpoint_hplc_uv', 'endpoint_ms_quant', 'endpoint_nmr',
                    'endpoint_optical_plateau', 'endpoint_radiometric', 'endpoint_time_course_completion',
                    'distribution_chiral', 'distribution_enzymatic_endpoint', 'distribution_gc', 'distribution_gel_bands', 'distribution_hplc',
                    'distribution_lcms', 'distribution_nmr', 'distribution_optical_equilibrium', 'distribution_radio_tlc',
                    'coupling_atp_product', 'coupling_cofactor_product', 'coupling_electron_balance', 'coupling_isotope_label', 'coupling_limiting_reagent',
                    'coupling_mass_balance', 'coupling_oxygen_product', 'coupling_uncoupling_byproduct')

# The class of each experiment type: the first 26 belong to ligand_binding; the activity_rate class has 19 types, spectro_direct
# (2026-11-21) and eighteen more (2026-11-22); the transport_response class has 10 types (2026-11-22); the endpoint_conversion class has 10 types
# (2026-11-22); the product_distribution class has 9 types (2026-11-22); the reaction_coupling class has 8 types (2026-11-22); the types of the other two classes are added with their converters.
CLASS_OF_EXPERIMENT_TYPE = {
    'spr': 'ligand_binding', 'itc': 'ligand_binding', 'bli': 'ligand_binding', 'gci': 'ligand_binding', 'fp': 'ligand_binding', 'fret': 'ligand_binding', 'mst': 'ligand_binding',
    'trp_quenching': 'ligand_binding', 'fcs': 'ligand_binding', 'elisa': 'ligand_binding', 'alphascreen': 'ligand_binding', 'radioligand': 'ligand_binding', 'spa': 'ligand_binding',
    'pulldown': 'ligand_binding', 'emsa': 'ligand_binding', 'sec': 'ligand_binding', 'dialysis': 'ligand_binding', 'auc': 'ligand_binding', 'dsf': 'ligand_binding', 'cetsa': 'ligand_binding',
    'bret': 'ligand_binding', 'y2h': 'ligand_binding', 'split_reporter': 'ligand_binding', 'pla': 'ligand_binding', 'proximity': 'ligand_binding', 'colocalization': 'ligand_binding',
    'spectro_direct': 'activity_rate',
    'coupled_enzyme': 'activity_rate',
    'redox_mediator': 'activity_rate',
    'fluorogenic': 'activity_rate',
    'luminescent': 'activity_rate',
    'stopped_flow': 'activity_rate',
    'quench_flow': 'activity_rate',
    'chromatographic': 'activity_rate',
    'stopped_colorimetric': 'activity_rate',
    'radiometric': 'activity_rate',
    'separation_band': 'activity_rate',
    'oxygen_electrode': 'activity_rate',
    'ph_stat': 'activity_rate',
    'protein_film_electrochem': 'activity_rate',
    'itc_kinetics': 'activity_rate',
    'continuous_ms': 'activity_rate',
    'nmr_timecourse': 'activity_rate',
    'product_immunodetection': 'activity_rate',
    'zymogram': 'activity_rate',
    # The ten transport_response types (2026-11-22): 'P transports S' is the class claim (CLAIM_PREDICATES_BY_CLASS).
    'transport_cell_tracer_uptake': 'transport_response', 'transport_counterflow': 'transport_response', 'transport_fluorescent_reporter': 'transport_response',
    'transport_medium_analysis': 'transport_response', 'transport_oocyte_two_electrode': 'transport_response', 'transport_patch_clamp': 'transport_response',
    'transport_planar_bilayer': 'transport_response', 'transport_proteoliposome_tracer': 'transport_response', 'transport_ssm_electrophysiology': 'transport_response',
    'transport_vesicle_probe_flux': 'transport_response',
    # The ten endpoint_conversion types (2026-11-22): 'E catalyzes S' is the class claim (CLAIM_PREDICATES_BY_CLASS).
    'endpoint_colorimetric': 'endpoint_conversion', 'endpoint_enzymatic_assay': 'endpoint_conversion', 'endpoint_gas_evolution': 'endpoint_conversion',
    'endpoint_gel_band': 'endpoint_conversion', 'endpoint_hplc_uv': 'endpoint_conversion', 'endpoint_ms_quant': 'endpoint_conversion', 'endpoint_nmr': 'endpoint_conversion',
    'endpoint_optical_plateau': 'endpoint_conversion', 'endpoint_radiometric': 'endpoint_conversion', 'endpoint_time_course_completion': 'endpoint_conversion',
    # The nine product_distribution types (2026-11-22): 'E catalyzes P' is the class claim (CLAIM_PREDICATES_BY_CLASS).
    'distribution_chiral': 'product_distribution', 'distribution_enzymatic_endpoint': 'product_distribution', 'distribution_gc': 'product_distribution',
    'distribution_gel_bands': 'product_distribution', 'distribution_hplc': 'product_distribution', 'distribution_lcms': 'product_distribution',
    'distribution_nmr': 'product_distribution', 'distribution_optical_equilibrium': 'product_distribution', 'distribution_radio_tlc': 'product_distribution',
    # The eight reaction_coupling types (2026-11-22): 'E catalyzes R' is the class claim (CLAIM_PREDICATES_BY_CLASS).
    'coupling_atp_product': 'reaction_coupling', 'coupling_cofactor_product': 'reaction_coupling', 'coupling_electron_balance': 'reaction_coupling',
    'coupling_isotope_label': 'reaction_coupling', 'coupling_limiting_reagent': 'reaction_coupling', 'coupling_mass_balance': 'reaction_coupling',
    'coupling_oxygen_product': 'reaction_coupling', 'coupling_uncoupling_byproduct': 'reaction_coupling',
}

# ---------------------------------------------------------------------------------------------------------------
# (3) Vocabularies
# ---------------------------------------------------------------------------------------------------------------
# Two separate checks of a result against a claim (owner, 2026-11-21: "Use target and relevance. It does make sense you need both"):
# TARGET_MATCH asks who was measured (is the experiment's target the claim's protein: 'same' the exact sequence, 'related' a related
# protein, 'different', 'not_stated'); RELEVANCE asks what was asked (did the experiment test the claim's question: 'relevant',
# 'irrelevant', 'unresolved' = it measured an interaction but names no partner). A result is on the row, and gives support or
# opposition by its identified_closeness, exactly when its target match is in TARGET_MATCH_ON_ROW and its relevance in RELEVANCE_ON_ROW.
TARGET_MATCH = ('same', 'related', 'different', 'not_stated')
TARGET_MATCH_ON_ROW = ('same', 'related')
RELEVANCE = ('relevant', 'irrelevant', 'unresolved')
RELEVANCE_ON_ROW = ('relevant', 'unresolved')


def on_row(result):
    """True when the converted result may carry a direction, enter a row and be a member result of a sheet state."""
    return result['target_match'] in TARGET_MATCH_ON_ROW and result['relevance'] in RELEVANCE_ON_ROW
# How the protein a paper assayed was identified against the target's sequence (2026-11-21 owner goal: "find the exact sequence
# associated with the experimental data so we know how close the real evidence is"; "no gate").
SUBJECT_RESOLUTION = ('database_id', 'name_unique', 'name_ambiguous', 'unresolved')
DIRECTION = ('supports', 'opposes', 'neutral', 'unknown')
ROW_STATUS = ('measured', 'measured_zero', 'unknown')
CRITERION_STATUS = ('supported', 'conflicting', 'unknown', 'not_applicable')
QUALITATIVE_STATEMENT = ('interaction_detected', 'interaction_not_detected', 'interaction_not_stated')
# The statements say whether the CLAIMED RELATION was detected. For the ligand_binding class the relation is binding; for the
# activity_rate class (decided 2026-11-21, owner to confirm) 'interaction_detected' reads "activity detected",
# 'interaction_not_detected' reads "activity not detected" (no activity above the paper's own control or detection limit) and
# 'interaction_not_stated' reads "activity not stated". No new values: the vocabulary is unchanged.
# For the transport_response class (DRAFT 2026-11-22, owner to confirm) 'interaction_detected' reads "transport detected" (movement of the claimed
# substrate or ion above the paper's own control), 'interaction_not_detected' reads "transport not detected" (no movement above the paper's own
# control or detection limit) and 'interaction_not_stated' reads "transport not stated".
# For the endpoint_conversion class (DRAFT 2026-11-22, owner to confirm) 'interaction_detected' reads "conversion detected", 'interaction_not_detected'
# reads "conversion not detected" (no conversion above the paper's own control or detection limit) and 'interaction_not_stated' reads "conversion not stated".
# For the product_distribution class (DRAFT 2026-11-22, owner to confirm) 'interaction_detected' reads "product detected" (the claimed product is among the
# products), 'interaction_not_detected' reads "product not detected" and 'interaction_not_stated' reads "product not stated".
# For the reaction_coupling class (DRAFT 2026-11-22, owner to confirm) 'interaction_detected' reads "coupled product formation detected",
# 'interaction_not_detected' reads "no product formed above the paper's own control or detection limit" and 'interaction_not_stated' reads "not stated".

# Candidate claim predicates. OWNER_DECISION 1: a candidate carries predicate + subject_id + partner_id (annotation
# IDs or names from a looked-up list). A claim names molecules only: it never carries a physical prediction or threshold
# (owner ruling of 2026-11-21); the sheet grades the measurement itself (QUANTITATIVE_STRENGTH).
# The predicates of the other classes (catalyzes for the four reaction classes, transports) are
# to be added here WITH THEIR CLASS, by the builder who adds that class; a predicate not listed for a class is refused.
CLAIM_PREDICATES_BY_CLASS = {
    'ligand_binding': ('binds',),
    # decided 2026-11-21, owner to confirm: 'E catalyzes R' (R a reaction term or a substrate molecule). Subject = the enzyme
    # (the record's target_id). NOT symmetric. Spelling 'catalyzes' as the A105 hypotheses and A104 already use.
    'activity_rate': ('catalyzes',),
    # DRAFT 2026-11-22, owner to confirm: 'P transports S' (P the transporter or channel, S a substrate or an ion). Subject = the protein (the
    # record's target_id), partner = the transported molecule or ion (the record's partner_id). NOT symmetric. Do not add to SYMMETRIC_PREDICATES.
    'transport_response': ('transports',),
    # DRAFT 2026-11-22, owner to confirm: 'E catalyzes the conversion of S' (S a substrate molecule; a reaction term gives a null partner). Subject = the
    # enzyme (the record's target_id). NOT symmetric. The word is the activity_rate class's too (owner, 2026-11-22: "One word for all four classes");
    # classes_of_predicate returns both classes.
    'endpoint_conversion': ('catalyzes',),
    # DRAFT 2026-11-22, owner to confirm: 'E catalyzes P' where P is a product of the reaction (a molecule). Subject = the enzyme (the record's
    # target_id); partner = the claimed product. NOT symmetric. The same word as activity_rate and endpoint_conversion (owner, 2026-11-22:
    # "One word for all four classes"); classes_of_predicate returns every class that holds it; a class none of whose types a paper reports holds no row.
    'product_distribution': ('catalyzes',),
    # DRAFT 2026-11-22, owner to confirm: 'E catalyzes R' for the stoichiometric link of a reaction. Subject = the enzyme (the record's target_id);
    # partner = the substrate whose conversion is coupled to the consumption of a cofactor (the record's partner_id, as stated). NOT symmetric.
    # A claim names molecules only and carries no threshold. The same word as activity_rate, endpoint_conversion and product_distribution
    # (owner, 2026-11-22: "One word for all four classes"); classes_of_predicate returns every class that holds it; a class none of whose
    # types a paper reports holds no row.
    'reaction_coupling': ('catalyzes',),
}

# What each experiment type is, in one plain line: the method and what it reports. This is the one place; the page shows these
# lines to its model where it names a leaf's experiment_type (only the types of the claim's class). A test fails when a type of
# CLASS_OF_EXPERIMENT_TYPE has no line.
EXPERIMENT_TYPE_LINES = {
    'spr': 'Surface plasmon resonance: one partner immobilised on a chip, the other flowed over it; reports association and dissociation rates and the KD.',
    'itc': 'Isothermal titration calorimetry: one partner titrated into the other in a calorimeter; reports the KD, the stoichiometry and the binding enthalpy.',
    'bli': 'Biolayer interferometry: one partner on a biosensor tip dipped into the other; reports association and dissociation rates and the KD.',
    'gci': 'Grating-coupled interferometry (waveguide chip, as SPR): one partner on a chip, the other flowed over; reports association and dissociation rates and the KD.',
    'fp': 'Fluorescence polarisation (anisotropy): a fluorescent partner whose polarisation rises when it binds; reports the KD or Ki from a titration or competition.',
    'fret': 'Forster resonance energy transfer in vitro: donor and acceptor fluorophores on the two partners; reports energy transfer on binding and a KD from a titration.',
    'mst': 'Microscale thermophoresis: a fluorescent partner whose movement in a temperature gradient changes on binding; reports the KD.',
    'trp_quenching': 'Intrinsic tryptophan fluorescence quenching: the protein\'s own tryptophan fluorescence drops on binding; reports the KD from a titration.',
    'fcs': 'Fluorescence correlation spectroscopy: diffusion time of a fluorescent partner slows on binding; reports the KD or the bound fraction.',
    'elisa': 'Enzyme-linked immunosorbent assay: one partner coated on a plate, the other detected by an antibody; reports a binding signal or an apparent KD.',
    'alphascreen': 'AlphaScreen / AlphaLISA: donor and acceptor beads on the two partners give a luminescent signal when close; reports the signal, an apparent KD or an IC50.',
    'radioligand': 'Radioligand binding: a radiolabelled ligand bound to its target, free ligand separated; reports the KD, Bmax or a Ki from competition.',
    'spa': 'Scintillation proximity assay: a radiolabelled ligand binds a target on a scintillant bead and only bound ligand gives a signal; reports the KD or a Ki.',
    'pulldown': 'Pull-down or co-immunoprecipitation: a tagged or antibody-captured bait is isolated and the prey is detected by blot or mass spectrometry; reports detected or not detected, often a fold enrichment.',
    'emsa': 'Electrophoretic mobility shift assay (gel shift): a labelled nucleic acid shifts on a gel when bound; reports the shift and the KD from a titration.',
    'sec': 'Size-exclusion chromatography (gel filtration): the elution volume of a mixture compared with the single partners; reports complex formation and its apparent size.',
    'dialysis': 'Equilibrium dialysis or ultrafiltration: ligand concentrations on the two sides of a membrane; reports the bound amount, the KD and the stoichiometry.',
    'auc': 'Analytical ultracentrifugation (sedimentation velocity or equilibrium): sedimentation of the mixture; reports complex species, their mass and a KD.',
    'dsf': 'Differential scanning fluorimetry (thermal shift, thermofluor): melting temperature of the protein with and without partner; reports the change in melting temperature.',
    'cetsa': 'Cellular thermal shift assay: thermal stability of a target protein in cells or lysate with and without a ligand; reports the shift in aggregation temperature or an isothermal dose response.',
    'bret': 'Bioluminescence resonance energy transfer in living cells: luciferase and fluorescent fusions of the two partners; reports an energy transfer ratio and a BRET50 or saturation curve.',
    'y2h': 'Yeast two-hybrid: the two partners fused to the halves of a transcription factor, a reporter or growth in yeast shows interaction; reports growth or reporter activity, detected or not.',
    'split_reporter': 'Split reporter or protein-fragment complementation (split luciferase, split GFP, BiFC): the two partners fused to halves of a reporter that reconstitutes on binding; reports a signal, detected or not.',
    'pla': 'Proximity ligation assay: antibodies against the two partners with ligatable oligonucleotides give a fluorescent spot when the partners are within about 40 nm in fixed cells; reports spots per cell, detected or not.',
    'proximity': 'Proximity labelling in cells (BioID, TurboID, APEX): a labelling enzyme fused to a bait biotinylates nearby proteins, which are identified by mass spectrometry or blot; reports enrichment over a control, detected or not.',
    'colocalization': 'Fluorescence microscopy co-localization or recruitment: one labelled protein is found where the other is (together in cells, recruited to the focus, pole, membrane or condensate the other makes, in a native or heterologous host or as purified proteins in droplets), and not when the other is absent; reports a yes or no, a fraction of cells, foci or droplets, a Pearson coefficient or an enrichment.',
    'spectro_direct': 'Continuous direct spectrophotometric enzyme assay: absorbance of a substrate or product read over time in a cuvette or plate; reports the rate, kcat, Km or specific activity.',
    'coupled_enzyme': 'Continuous coupled-enzyme assay: the product of the enzyme tested has no signal, so helper (coupling) enzymes turn it into a change of a reporter (usually NADH or NADPH at 340 nm) that is read over time; reports the rate, kcat, Km or specific activity, and how far the helper enzymes keep up with the reaction.',
    'redox_mediator': 'Artificial redox-mediator enzyme assay: an artificial electron acceptor or donor (DCPIP, ferricyanide, a viologen, a tetrazolium dye, a quinone) takes the place of the enzyme\'s natural redox partner and its colour change is read over time; reports the rate of dye reduction or oxidation, specific activity or kcat with that dye.',
    'fluorogenic': 'Fluorogenic enzyme assay: the fluorescence of a released or formed fluorophore (an AMC or AFC peptide, a methylumbelliferyl glycoside, resorufin, NADH or NADPH fluorescence, a FRET peptide cut apart) read over time in a cuvette or plate reader; reports a rate in fluorescence units, or after a free-fluorophore standard curve the rate, kcat, Km, kcat/Km or specific activity.',
    'luminescent': 'Luminescent enzyme assay (ADP-Glo, Kinase-Glo, NAD(P)H-Glo, luciferase-coupled ATP or pyrophosphate detection): a luciferase turns the ADP or ATP made or used by the reaction into light read in a plate and a standard series turns it into an amount of product; reports a rate, a specific activity, kcat, Km, kcat/Km or a signal over background, with a Z\' factor when it is a screen.',
    'stopped_flow': 'Stopped-flow rapid-mixing enzyme experiment: enzyme and substrate are mixed in about a millisecond and the absorbance or fluorescence is read from then on, before the steady state; reports the rate constant of one phase (single-turnover or burst chemistry, observed k_obs, its dependence on the substrate), not a steady-state slope.',
    'quench_flow': 'Rapid chemical quench-flow: enzyme and substrate react for milliseconds to seconds, a quench (acid, base, EDTA, denaturant) stops each sample, and the product is separated and counted (radioactivity, HPLC, mass spectrometry); reports the burst amplitude and the rate constant of a single-turnover or burst phase, and the steady-state turnover after it; not an optical trace (that is stopped-flow).',
    'chromatographic': 'Discontinuous chromatographic enzyme assay: the reaction is sampled at chosen times, each sample is stopped, and the product (or the lost substrate) is separated and quantified against an authentic standard by HPLC, LC-MS, GC, GC-MS or ion chromatography; it reports an amount of product per time that becomes a rate, kcat, kcat/Km or specific activity (not a continuous optical or electrode trace, not a radiometric count, not a gel band).',
    'stopped_colorimetric': 'A stopped assay: the enzyme reaction runs for a set time and is stopped, a colour reagent (malachite green for phosphate, DNS for reducing sugar, DTNB for thiol, ferric hydroxamate, Nessler/Berthelot for ammonia) then colours a product CLASS, and the amount is read from a product standard curve to give a rate; unlike spectro_direct it has no live trace and no extinction coefficient, and unlike chromatographic it names no separated product.',
    'radiometric': 'Radiometric enzyme assay: a radiolabelled substrate (14C, 3H, 32P, 35S) is converted, the labelled product is separated from the substrate (TLC, filter binding, ion exchange, trapped gas) and counted; reports the rate, kcat, Km or specific activity in amount of product per time.',
    'separation_band': 'Gel or thin-layer separation assay: the reaction is stopped at several times, substrate and product are separated on a gel or plate and the band intensities give the fraction converted over time (a discontinuous assay with stopped time points, unlike the continuous trace of spectro_direct and the chromatographic column of the HPLC type); it reports a rate, a turnover, a specific activity or a fold over the no-enzyme lane.',
    'oxygen_electrode': 'Oxygen-electrode enzyme assay: the dissolved oxygen of a closed, stirred chamber read with a Clark-type electrode, a respirometer or an optical sensor, the slope being the rate of oxygen uptake or evolution; reports the rate (per mg of protein, or a fold over the control), kcat, Km or a stated yes or no.',
    'ph_stat': 'pH-stat titration enzyme assay: a pH electrode holds the pH of an unbuffered or lightly buffered reaction at a set point and a base is added as fast as the reaction releases protons (esterase, lipase, carbonic anhydrase); reports the base added over time as a rate, kcat, Km or specific activity.',
    'protein_film_electrochem': 'Protein-film electrochemistry (voltammetry or chronoamperometry): the enzyme is adsorbed as a film on an electrode and its catalytic current with the substrate is the rate; reports the catalytic current or current density, a turnover frequency kcat when the electroactive coverage is measured, an apparent Km and the current over the control.',
    'itc_kinetics': 'Isothermal titration calorimetry enzyme kinetics: enzyme or substrate injected into a calorimeter cell and the heat of the reaction read as thermal power, which divided by a separately measured reaction enthalpy gives the rate; reports the rate, kcat, Km or specific activity of any reaction that gives heat, with no label and no product identification (not the binding titration of type itc).',
    'continuous_ms': 'Continuous mass-spectrometry enzyme assay: the reaction is followed live in a mass spectrometer (a membrane-inlet probe for dissolved gases such as CO2, O2 or H2, or online electrospray), the ion current at the mass of the product is calibrated to a concentration with known standards and its initial slope is the rate; reports kcat, Km, kcat/Km, a specific activity or a fold over the no-enzyme baseline. It reads a mass, not an absorbance (no chromophore, product identity by mass or isotope label), and is continuous with no separation step.',
    'nmr_timecourse': 'Real-time NMR progress-curve enzyme assay: a series of 1H, 13C, 31P or 19F spectra recorded while the enzyme converts its substrate in the NMR tube, the integrals of an assigned substrate and product resonance giving the amounts over time; reports the rate, kcat, Km, kcat/Km or a specific activity, with the product told apart by its chemical shift.',
    'product_immunodetection': 'Antibody detection of the modified product of a stopped enzyme reaction (TR-FRET/HTRF, ELISA, AlphaScreen/AlphaLISA or an in vitro blot with an antibody against the phospho-, methyl-, acetyl- or ubiquitin product): the antibody signal is the product, read against a no-enzyme control and, when a product standard series is given, as an amount; reports the signal fold over the control, the specific activity, kcat or Km.',
    'zymogram': 'In-gel activity staining (zymography, activity stain after a native gel): the enzyme is made visible as a cleared or coloured band in a gel that holds or is soaked in its substrate; reports only that an activity band is seen (or not) at a gel position, no rate or constant.',
    'transport_cell_tracer_uptake': 'Whole-cell tracer uptake or efflux: living cells that make the protein, and matched control cells, take up (or release) a labelled substrate (14C, 3H, 86Rb+), the transport is stopped by filtration or an oil spin and the label kept is counted; reports an uptake rate per mg of cells, a Km or the fold over the empty-vector cells.',
    'transport_counterflow': 'Counterflow, exchange and trans-stimulation: vesicles, proteoliposomes or cells preloaded with an unlabelled substrate take up a labelled substrate faster than the same preparation without the preload, or hold it above its equilibrium level (overshoot); reports the fold over the non-preloaded baseline, the overshoot ratio or an exchange rate, and shows that the transporter recognizes the molecule on both sides, not how fast it carries it alone.',
    'transport_fluorescent_reporter': 'Fluorescent reporter of transport in cells: a fluorescent substrate analogue, an indicator dye or a genetically encoded sensor read on a plate reader, microscope or flow cytometer while the substrate or ion moves; reports a fold of the signal over control cells or a Km, usually relative to its own control.',
    'transport_medium_analysis': 'Transport read by chemical analysis of an unlabelled substrate: cells take up or release the substrate and its amount in the medium (or in cells separated from it) is measured at stated times by HPLC, LC-MS, an enzymatic analyzer or ion analysis; reports a rate per mass of cells or a fold over a control strain over an interval, with no tracer and no continuous probe.',
    'transport_oocyte_two_electrode': 'Two-electrode voltage clamp of Xenopus oocytes: oocytes injected with the cRNA of the protein are held at a set voltage and the current the substrate induces is recorded over water-injected control oocytes; reports the substrate-induced current, a fold over the control, an apparent Km from a concentration series and whether the current depends on the ion (a charge flow, not the substrate flow itself).',
    'transport_patch_clamp': 'Patch clamp of cells (whole-cell, inside-out, outside-out or cell-attached): the membrane current of cells that make the protein, set against control cells, under voltage steps or ramps and ion replacement; reports the conductance of one channel, a reversal potential, a charge flow per second or the current as a fold over control cells.',
    'transport_planar_bilayer': 'Planar lipid bilayer recording: a purified channel or transporter in an artificial bilayer between two solutions, current recorded at a held voltage; reports the single-channel current and conductance and, with two ions in the chambers, the reversal potential and the ion selectivity.',
    'transport_proteoliposome_tracer': 'Proteoliposome tracer transport: one purified transporter reconstituted into liposomes with an imposed gradient (pH, membrane potential, sodium or another ion), uptake or efflux of a labelled substrate counted after stopping, against protein-free liposomes; reports the rate per mg of protein, turnover, Km or the fold over empty liposomes.',
    'transport_ssm_electrophysiology': 'Solid-supported membrane electrophysiology: proteoliposomes on a gold sensor, a substrate concentration jump gives a transient current of electrogenic transport (voltage not clamped); reports the apparent Km of the peak current and the fold over an empty-liposome sensor.',
    'transport_vesicle_probe_flux': 'Vesicle flux read continuously: vesicles (liposomes with a reconstituted protein, or native vesicles) release or take up an ion or substrate while an ion-selective electrode in the bath or a dye trapped inside follows it in real time, and a detergent at the end releases the whole pool; reports the fraction of the pool released over time against protein-free vesicles, a rate constant or half-time and, when stated, a rate per transporter, a rate per mg or the fold over protein-free vesicles; it is not a labelled tracer that is stopped and counted, and not a current.',
    'endpoint_colorimetric': 'Stopped end-point colour assay: the reaction runs for a set time and is stopped, a colour reagent (malachite green for phosphate, DNS for reducing sugar, DTNB for a thiol, Nessler or Berthelot for ammonia) colours a product class, and the share of the substrate converted, or the amount of product, is read at that one time from a standard curve made in the reaction buffer; reports an end point, never a rate, and names a product class, not a separated product.',
    'endpoint_enzymatic_assay': 'End-point determination with a second enzyme: after a stated time the first reaction is stopped and the substrate left or the product formed is measured by a second, specific enzyme (formate by formate dehydrogenase, glucose by glucose oxidase, ammonia by glutamate dehydrogenase) against a standard series; reports the share of the substrate converted or the product amount at that time, not a rate.',
    'endpoint_gas_evolution': 'Gas-evolution end point: an enzyme reaction in a closed vessel whose gas product (H2, CO2, CH4, N2O) is read from the headspace by gas chromatography or manometry at a fixed time; reports the gas amount or the percent of the theoretical yield.',
    'endpoint_gel_band': 'Gel or TLC separation of substrate and product, read by densitometry: the share of the substrate converted at one stated time, or whether a product band is present.',
    'endpoint_hplc_uv': 'Fixed-time reaction read by HPLC with an optical or refractive-index detector: the reaction is run for a stated time and stopped, and substrate and product are separated and quantified against an authentic standard; reports the share of the substrate converted (or the product concentration) at that one time, not a rate and not the time to completion.',
    'endpoint_ms_quant': 'Fixed-time enzyme reaction, stopped at a stated time, whose product is quantified by LC-MS, LC-MS/MS or GC-MS against an internal standard and a matrix-matched calibration of an authentic standard; reports the share of the substrate converted, the product amount or the completion time at that one end point, not a rate.',
    'endpoint_nmr': 'NMR end-point conversion: an enzyme reaction read as one NMR spectrum at a stated time or at completion, the integrals of an assigned substrate and product signal (product over substrate plus product, or against an internal standard) giving the share of the substrate converted; reports the percent conversion or the product amount at that time, not a rate.',
    'endpoint_optical_plateau': 'Reaction run to an optical plateau: the absorbance or fluorescence of a chromophoric or fluorogenic substrate or product is read until it stops changing, and the final change is turned into the share of the substrate converted (with an extinction coefficient or a full-conversion reference); reports a conversion fraction, a product amount or the time to the plateau, not a rate.',
    'endpoint_radiometric': 'Radiometric end point: a radiolabelled substrate is incubated with the enzyme for a stated time, the reaction is stopped, the labelled product is separated (TLC, filter binding, ion exchange, trapped 14CO2) and counted; reports the share of the label converted, or the product amount, at that one time (not a rate).',
    'endpoint_time_course_completion': 'Sampled time course to a stated completion or equilibrium (followed by NMR, HPLC, mass spectrometry or an optical signal): the reaction is sampled until a stated state is reached; reports the time to completion, possibly only a bound, and its ratio to a reference arm.',
    'distribution_chiral': 'Chiral-phase chromatography or electrophoresis of stereo-isomeric products (chiral HPLC, GC, SFC or CE, or diastereomers on an ordinary column) with a racemic standard: the enzyme\'s product is separated into its isomers; reports the enantiomeric excess, the enantiomer ratio or the diastereomer ratio of the product.',
    'distribution_enzymatic_endpoint': 'Enzymatic end-point analysis of a product mixture: after the reaction each species is determined by its own specific enzymatic analysis (a dehydrogenase, oxidase or kinase that turns it to a read reporter, for example NADH at 340 nm) against its own standards; reports the share of each species, a product ratio or the equilibrium ratio, from the concentrations.',
    'distribution_gc': 'Gas chromatography (GC-FID or GC-MS) of volatile or derivatized products, as an extract, headspace or fibre sample: peaks named by standards, retention index or library match; reports the share of each product in the product spectrum (terpene spectra, regio-isomers, chain lengths).',
    'distribution_gel_bands': 'gel or capillary electrophoresis of the reaction products by size, read by densitometry or fragment analysis: the share of each product length or cleavage site among the products, or a ratio of two of them',
    'distribution_hplc': 'HPLC peak-area distribution of products: the reaction (or an equilibrium mixture) is stopped and its species are separated by liquid chromatography (UV, diode-array, fluorescence, refractive-index, ELSD or CAD detection); reports the share of one named product among the products, a ratio of two products, or the composition at equilibrium, and is a molar share only with response factors; not a rate, not the total conversion.',
    'distribution_lcms': 'LC-MS or LC-MS/MS product profile: the products of an enzyme reaction separated by liquid chromatography and each read by its mass-spectrometric ion signal (extracted ion chromatogram, selected or multiple reaction monitoring); reports the share of one product among the products, or a ratio of two products, quantitative only when each species is calibrated on its own or against isotope-labelled standards.',
    'distribution_nmr': 'Quantitative NMR of a product mixture: an enzyme reaction (or a mixture left to equilibrium) read by NMR of one nucleus (1H, 13C, 31P, 19F) with no separation, the integrals of each assigned species giving the share of one named product among the products, a ratio of two products or the equilibrium composition; reports shares and ratios, not a rate and not how much substrate was converted.',
    'distribution_optical_equilibrium': 'Optical equilibrium composition: the absorbance or fluorescence of the reaction mixture is followed to a plateau (the species have their own spectra, for example NADH at 340 nm), ideally reached from both the substrate and the product side, and the plateau signal and the pure-species spectra give the equilibrium share or ratio; no separation; reports an equilibrium fraction or ratio.',
    'distribution_radio_tlc': 'Radiolabelled product distribution: a radioactively labelled substrate is incubated with the enzyme, the products are separated on a TLC plate, by radio-HPLC or on a gel and the label of each is counted or imaged; reports the share of the labelled counts in each named product (or the ratio of two), not the total conversion or the rate.',
    'coupling_atp_product': 'ATP or GTP hydrolysis paired with the product it drives: the nucleotide hydrolysed (phosphate dye, pyruvate kinase / lactate dehydrogenase NADH loss, [gamma-32P] release or ADP by chromatography) and the product are measured in the same reaction, with the basal ATPase rate taken off; reports the nucleotides hydrolysed per product (a cost, normally above 1) or the share of the hydrolysis that ends in product.',
    'coupling_cofactor_product': 'Cofactor consumption paired with an identified product: NAD(P)H loss (absorbance at 340 nm, or HPLC) and the product (by chromatography or mass spectrometry against a standard) measured in the same reaction; reports the coupling (coefficient times product over cofactor, as a percent or fraction) or the product per cofactor.',
    'coupling_electron_balance': 'Electron balance of a reaction: the electrons delivered (a reductant titrated in, charge passed at an electrode, a reduced donor oxidised) are counted against the electrons recovered in the product (H2 by gas chromatography, a reduced compound), times the electrons the product needs; reports the share of the delivered electrons found in the product (electron recovery, faradaic efficiency).',
    'coupling_isotope_label': 'Isotope-label flow: the enzyme is given a labelled source (18O2, H2 18O, 13C, 15N, or a double 14C and 3H label) and the product is read by mass spectrometry or counting; reports the share of the product that carries the label of the claimed source (where an atom came from), not an amount of the partner consumed.',
    'coupling_limiting_reagent': 'Limiting-reagent endpoint: one reaction run to completion with a single reagent (a cofactor or co-substrate) limiting, in one dose or by stepwise titration, and the product at the end set against the limiting reagent used up; reports the equivalents of the limiting reagent per product (for example 2 NADPH per product) or the yield over it, as a productive fraction or a product-per-reagent ratio.',
    'coupling_mass_balance': 'Mass balance (closure) of a reaction: the substrate that disappeared is set against the sum of the identified products, each quantified in the same samples by HPLC, GC, mass spectrometry or NMR against standards; reports the closure (the share of the consumed substrate that the products account for, as a molar, carbon, nitrogen or mass balance) and the unaccounted residual, not a conversion alone and not a rate.',
    'coupling_oxygen_product': 'Oxygen uptake paired with an identified product: the oxygen consumed by an enzyme reaction is read with an electrode or optode (Clark, Oroboros, fluorescence) in one vessel and the claimed product is identified and counted by chromatography, mass spectrometry or NMR over the same interval, with the oxygen that went to hydrogen peroxide accounted for; reports the product per oxygen consumed (or a productive fraction), the two amounts or rates, or a stated yes or no.',
    'coupling_uncoupling_byproduct': 'Peroxide or superoxide formed per cofactor consumed (Amplex Red with peroxidase, ferrous oxidation with xylenol orange, catalase oxygen return, cytochrome c with superoxide dismutase): it reports the uncoupled share of the cofactor and, by difference, the productive share when the by-product is stated to be the only loss; it does not identify the product.',
}


def experiment_types_of_class(sheet_class):
    """The experiment types of one sheet class, in registry order."""
    return tuple(name for name in EXPERIMENT_TYPES if CLASS_OF_EXPERIMENT_TYPE[name] == sheet_class)


def classes_of_predicate(predicate):
    """The sheet classes whose claims carry this predicate, in the order of CLASSES. One word may span several classes
    (owner, 2026-11-22: "One word for all four classes": E catalyzes R is supported by its rate, its endpoint conversion, its
    product distribution and its reaction coupling alike, each on its own row). A predicate no class lists raises."""
    classes = tuple(sheet for sheet in CLASSES if predicate in CLAIM_PREDICATES_BY_CLASS.get(sheet, ()))
    if not classes:
        raise ValueError(f'the predicate {predicate!r} belongs to no class')
    return classes


def experiment_types_of_predicate(predicate):
    """The experiment types that can support a claim with this predicate: the types of every class that lists it, in registry
    order. Not every class applies to every paper: a class none of whose types a paper reports holds no row and gives no
    score (an unknown row never enters the score), and a result that did not test the claim stays irrelevant (literature_relevance)."""
    classes = classes_of_predicate(predicate)
    return tuple(name for name in EXPERIMENT_TYPES if CLASS_OF_EXPERIMENT_TYPE[name] in classes)
# A symmetric predicate holds both ways: 'A binds B' is 'B binds A'. A result whose target is the claim's partner and whose
# partner is the claim's subject is then the same target and relevant for the claim (reason partner_route in both).
SYMMETRIC_PREDICATES = ('binds',)
CLAIM_PREDICATES = tuple(dict.fromkeys(p for predicates in CLAIM_PREDICATES_BY_CLASS.values() for p in predicates))   # one word may span several classes: listed once
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
    # colocalization (2026-11-22, EXPERT_REVIEW, confirmed by the owner 2026-11-22): a relative image readout (where fluorescence lies) whose meaning rests on controls (an unrelated protein, the absent partner, a binding-region mutant) and on a tag and an expression level that a paper may not state; a little above PLA, whose antibody artefacts are worse, and level with proximity labelling.
    'colocalization': 0.60,
    # spectro_direct (2026-11-21, owner to confirm; the answer chain is in literature_spectro_direct_converter.py and A105_ASSAY_CALIBRATION_DETAILS.md): an absolute rate with a well-known reference range of kcat and kcat/Km, a little under the KD anchor.
    'spectro_direct': 0.85,
    # The eighteen further activity_rate types (2026-11-22, all EXPERT_REVIEW, owner to confirm; the answer chain of each is in its converter docstring).
    'coupled_enzyme': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute rate with the trusted reference range of spectro_direct, but an indirect readout with more ways to be wrong (coupling limits, contaminating activity, no product identity).
    'redox_mediator': 0.80,  # EXPERT_REVIEW, owner to confirm: absolute in form (extinction coefficient and electron count) but indirect in meaning; a rate with an artificial dye has no trusted reference range.
    'fluorogenic': 0.80,  # EXPERT_REVIEW, owner to confirm: a relative readout in instrument units until a free-fluorophore standard curve calibrates it, and a fluorescence assay has more ways to be wrong (gain, plate, inner filter, autofluorescence).
    'luminescent': 0.80,  # EXPERT_REVIEW, owner to confirm: a relative readout (RLU) made absolute only by a standard series, and indirect (it reads ADP or ATP), so a little under spectro_direct.
    'stopped_flow': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute rate constant with a trusted range, but the rate is that of a phase and its assignment to the chemical step may be unstated.
    'quench_flow': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute rate with a known reference range, with the product identified by separation; level with spectro_direct.
    'chromatographic': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute, calibrated amount of product with a well-known reference range, so an unstated detail changes the size of a rate and not the existence of the activity; level with spectro_direct.
    'stopped_colorimetric': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute amount only if the standard curve is in the same matrix and the product class is the claimed product; reagent background is the classic false positive, so under spectro_direct.
    'radiometric': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute rate (specific radioactivity and counting efficiency turn counts into amount) with the same trusted reference range as spectro_direct.
    'separation_band': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute readout (product over lane total) with the same trusted kcat range, but discontinuous and coarser, so a little under spectro_direct.
    'oxygen_electrode': 0.80,  # EXPERT_REVIEW, owner to confirm: absolute after the two-point calibration but not specific, since oxygen is used by anything oxidizable in the chamber; an unstated blank or coupling can turn background into false catalysis.
    'ph_stat': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute readout with a trusted reference range, but not selective (every proton source counts).
    'protein_film_electrochem': 0.75,  # EXPERT_REVIEW, owner to confirm: the readout is a current per electrode area, a rate per enzyme only when the electroactive coverage is measured; a bare current density has no reference range.
    'itc_kinetics': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute rate with a trusted reference range, but the readout is a non-specific heat and the rate depends on a separately measured enthalpy.
    'continuous_ms': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute rate with a trusted reference range, as spectro_direct; a mass-specific signal is slightly safer and an instrument calibration slightly less standard, and the two cancel.
    'nmr_timecourse': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute, species-specific rate (amounts from integrals against a reference) with the same trusted reference range as spectro_direct, level with it.
    'product_immunodetection': 0.75,  # EXPERT_REVIEW, owner to confirm: the raw readout is relative and becomes an amount only through a product standard series; an unstated antibody specificity can turn another modification into the claimed one; level with fret.
    'zymogram': 0.65,  # EXPERT_REVIEW, owner to confirm: a relative, qualitative readout with no calibration and no reference range; a wrong assumption counts another enzyme's band as the target's activity (the existence is wrong, a worse error than a rate's size).
    # The ten transport_response types (2026-11-22, all EXPERT_REVIEW, owner to confirm); the answer chain of each is in its converter docstring.
    'transport_cell_tracer_uptake': 0.75,  # EXPERT_REVIEW, owner to confirm: absolute in form but its meaning rests on the matched control cells; an unstated empty-vector control is the dominant false positive (host uptake and metabolism of the label); whole cells have more ways to be wrong than a purified-enzyme rate (spectro_direct 0.85) and a KD (SPR 0.90).
    'transport_counterflow': 0.80,  # EXPERT_REVIEW, owner to confirm: a relative readout (a ratio of two counts of one label in one preparation) with no well-established reference range of folds or overshoots, whose label calibration cancels; below the KD anchor (0.90) and spectro_direct (0.85).
    'transport_fluorescent_reporter': 0.65,  # EXPERT_REVIEW, owner to confirm: a relative reading (a fold over the paper's own control), absolute only after calibration; no reference range we would trust; an unstated control cell line or no-substrate control is the dominant false positive; level with AlphaScreen, split reporter and CETSA (0.65).
    'transport_medium_analysis': 0.75,  # EXPERT_REVIEW, owner to confirm: absolute in units (calibration standards) but an interval balance and not a constant of the protein; a rate per mg of cells depends on expression, the substrate level and the normalizer, so no trusted reference range; an unstated metabolism or control-strain check can turn a host contribution into a false 'transports'.
    'transport_oocyte_two_electrode': 0.80,  # EXPERT_REVIEW, owner to confirm: a membrane current of one oocyte, absolute in the clamp but its meaning (the protein's carrier rather than the oocyte's own channels or a leak) rests on controls; the water-injected control is universal practice so unstated is mostly benign; under the KD anchor 0.90 and spectro_direct 0.85 (a purified enzyme has no host background).
    'transport_patch_clamp': 0.80,  # EXPERT_REVIEW, owner to confirm: absolute in form (pS), partly trusted reference range (1 to 100 pS), but its meaning rests on control cells; an unstated host-cell control is the dominant false positive; between spectro_direct 0.85 and transport_cell_tracer_uptake 0.75.
    'transport_planar_bilayer': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute, intensive readout (a conductance in pS needs no protein amount) with a well-known range of channel sizes; a little under the KD anchor because a contaminating channel or pore-forming peptide is a false positive a protein-free bilayer does not show; level with spectro_direct.
    'transport_proteoliposome_tracer': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute rate and Km in a defined system with a trusted reference range of carrier Km and turnover; an unstated control mostly changes magnitude; just under the KD anchor 0.90, as spectro_direct.
    'transport_ssm_electrophysiology': 0.70,  # EXPERT_REVIEW, owner to confirm: a relative readout whose meaning rests on its controls (the solution-exchange artefact is a known false current); no reference range we would trust if the paper said less; level with ELISA and DSF.
    'transport_vesicle_probe_flux': 0.80,  # EXPERT_REVIEW, owner to confirm: a clean defined system whose reference range (transporter and channel turnover) is known, but a rate needs the protein-free control, the response time and the protein amount, and a stated rate without them can be leak or a lag; a little under spectro_direct (0.85).
    # The ten endpoint_conversion types (2026-11-22, all EXPERT_REVIEW, owner to confirm); the answer chain of each is in its converter docstring. An end point is not a constant of the enzyme (it depends on the loading and the time the paper chose) and has no trusted reference range as KD or kcat have, so none reaches the KD anchor 0.90.
    'endpoint_colorimetric': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute amount of a product class only if the standard curve is made in the reaction matrix; the classic false positive is the reagent reacting with substrate, buffer or enzyme preparation; level with stopped_colorimetric.
    'endpoint_enzymatic_assay': 0.80,  # EXPERT_REVIEW, owner to confirm: absolute readout through a standard series with well-known analytical ranges, but two enzymes can go wrong, not one.
    'endpoint_gas_evolution': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute amount of one named gas from a calibrated reading, as trusted as the spectro_direct rate; the real gaps are the controls (gas without the enzyme, a leak).
    'endpoint_gel_band': 0.75,  # EXPERT_REVIEW, owner to confirm: a relative-within-the-lane, semi-quantitative readout whose band is identified by mobility; level with emsa, the other gel readout.
    'endpoint_hplc_uv': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute share or concentration against an authentic standard with substrate and product both visible; level with spectro_direct.
    'endpoint_ms_quant': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute, calibrated amount of a named product identified by its mass, but with no natural reference range of conversions; level with spectro_direct.
    'endpoint_nmr': 0.85,  # EXPERT_REVIEW, owner to confirm: an absolute fraction from integrals (no calibration curve), identified by its shift; an unstated acquisition detail is a real gap; level with spectro_direct.
    'endpoint_optical_plateau': 0.75,  # EXPERT_REVIEW, owner to confirm: a relative readout in instrument units until a calibration makes it a fraction; an unstated baseline is the main false positive; below spectro_direct and fluorogenic.
    'endpoint_radiometric': 0.85,  # EXPERT_REVIEW, owner to confirm: the share converted is a ratio of counts of one sample, sensitive, used for weak activities; equal to the activity class's radiometric type.
    'endpoint_time_course_completion': 0.70,  # EXPERT_REVIEW, owner to confirm: a time to completion is a relative readout (enzyme and substrate amounts, temperature, what the paper calls complete) with no reference range; lower than spectro_direct.
    # The nine product_distribution types (2026-11-22, all EXPERT_REVIEW, owner to confirm); the answer chain of each is in its converter docstring.
    'distribution_chiral': 0.85,  # EXPERT_REVIEW, owner to confirm: a ratio of two peak areas of one compound, needing no calibration for enantiomers; a routine, well-trusted number when a racemic standard is run; an unstated standard or control more often leaves a gap than a lie; just under the KD anchor 0.90 and level with spectro_direct.
    'distribution_enzymatic_endpoint': 0.80,  # EXPERT_REVIEW, owner to confirm: absolute molar shares by each species' own calibration, below the KD anchor 0.90 and just under spectro_direct 0.85, because several determinations must each be right and their errors add in a share; an unstated standard curve, completion or blank is benign typical practice, an unstated specificity, quench or coverage is the method's own classical failure.
    'distribution_gc': 0.80,  # EXPERT_REVIEW, owner to confirm: a composition within one chromatogram, well defined when species are identified; a terpene-synthase spectrum is reproducible and an FID share of isomers is close to the true share even when little is stated; an unstated no-enzyme extract, identification or injector check can leave a solvent, plastic or thermal-rearrangement peak read as a product (a false product, worse than a wrong magnitude); below the KD anchor 0.90, level with the activity types.
    'distribution_gel_bands': 0.75,  # EXPERT_REVIEW, owner to confirm: a share of band signals inside one lane (loading cancels, the signal per molecule is arbitrary) whose meaning needs in-lane controls and an equal response per molecule; level with emsa (0.75, the other gel readout), below spectro_direct (0.85, an absolute rate).
    'distribution_hplc': 0.80,  # EXPERT_REVIEW, owner to confirm: a relative share from peak areas (absolute only with calibration), no trusted reference range as for KD or kcat, and an unstated standard or response correction leaves the identity or the magnitude open; a little under spectro_direct (0.85).
    'distribution_lcms': 0.75,  # EXPERT_REVIEW, owner to confirm: the readout is RELATIVE (a share of the summed ion signal) unless each species is calibrated and there is no reference range for the size of a share; the presence of a product is well established by mass and retention time, so the direction mostly survives an unstated detail while the share can be off by a multiple; well under the KD anchor 0.90 and the activity types 0.85.
    'distribution_nmr': 0.85,  # EXPERT_REVIEW, owner to confirm: the shares are read in one spectrum over one denominator and, with full relaxation, need no response factor, so a share is as absolute as an NMR integral; a species is identified by its chemical shift, a structural identity; an unstated acquisition detail (the delay) biases the size of a share rather than the existence of a species; level with spectro_direct, just under the KD anchor 0.90.
    'distribution_optical_equilibrium': 0.75,  # EXPERT_REVIEW, owner to confirm: the composition is absolute (a state function) but rests on extinction coefficients and is told by spectrum only; what a paper rarely states (what makes the plateau an equilibrium, which species absorb, the controls) can turn a stalled reaction, a second absorbing species or a composite constant into a "composition"; below the NMR (0.85) and spectro_direct (0.85) defaults.
    'distribution_radio_tlc': 0.80,  # EXPERT_REVIEW, owner to confirm: a RELATIVE share within a lane (no absolute calibration needed; absolute as a share of labelled products only when the label per molecule and the detection are equal); an unstated blank is the dominant false product (a radiochemical impurity of the labelled substrate runs where a product runs), an unstated standard leaves the product named only by position; under KD 0.90 and spectro_direct 0.85.
    # The eight reaction_coupling types (2026-11-22, all EXPERT_REVIEW, owner to confirm); the answer chain of each is in its converter docstring. The ratio of two measured amounts is absolute and dimensionless, but each side needs its own calibration and the two sides must be matched.
    'coupling_atp_product': 0.80,  # EXPERT_REVIEW, owner to confirm: a ratio of two absolute amounts, each from its own calibration, only as good as the worse calibration and the match of the sides; a trusted reference range exists only for a few well-studied systems (nitrogenase); under KD (0.90) and spectro_direct (0.85).
    'coupling_cofactor_product': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute dimensionless link, but each side needs its own calibration and the two must be matched; P450 couplings run from a few percent to near 100 percent, which does not help with matching or product identity; under spectro_direct (0.85) and KD (0.90).
    'coupling_electron_balance': 0.75,  # EXPERT_REVIEW, owner to confirm: the share is absolute and dimensionless with a physical bound, but each side needs its own calibration and the controls that separate the enzyme from a bypass are often unstated; below KD (0.90) and spectro_direct (0.85).
    'coupling_isotope_label': 0.75,  # EXPERT_REVIEW, owner to confirm: an absolute fraction read from one ratio of ion intensities (no external calibration) with labels of known purity, but the claim it supports is indirect and rests on controls a paper may not state; below KD (0.90).
    'coupling_limiting_reagent': 0.80,  # EXPERT_REVIEW, owner to confirm: an absolute dimensionless ratio fixed by the reaction's own coefficient, but made of two measurements that must agree; a little under spectro_direct (0.85).
    'coupling_mass_balance': 0.80,  # EXPERT_REVIEW, owner to confirm: a ratio of two quantified amounts, only as good as the calibration of every species, and a low closure is a real result, so no reference range can stand in for an unstated detail; under spectro_direct and endpoint_hplc_uv (0.85).
    'coupling_oxygen_product': 0.80,  # EXPERT_REVIEW, owner to confirm: the product per oxygen is absolute and dimensionless and the oxygenase stoichiometry gives a trusted expectation, but two measurements must be matched and each needs its own calibration; just under spectro_direct (0.85).
    'coupling_uncoupling_byproduct': 0.75,  # EXPERT_REVIEW, owner to confirm: a ratio of two absolute amounts, each needing its own calibration; the uncoupled share of a monooxygenase runs from a few percent to nearly all, so no reference range holds, and peroxide reagents are known for artefacts; level with the fret and mst relative readouts.
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
    # colocalization (EXPERT_REVIEW, confirmed by the owner 2026-11-22): an unstated specificity control (an unrelated protein or tag alone, the absent partner) counts clearly less, as in PLA (a crowded or sticky site recruits any protein); an unstated heterologous or in-vitro system or binding-region mutant leaves a native bridge open but is common practice (0.70); an unstated tag-function or expression check is a real but ordinary gap (0.60); the number of objects and the replicates are benign when unstated (0.80).
    'colocalization': {'binding_controls': 0.50, 'binding_regime': 0.70, 'calibration_applicability': 0.60, 'sampling_basis': 0.80},
    # spectro_direct: the blank is what separates activity from spontaneous chemistry (a real gap); a contaminating activity or a second reaction on the chromophore is the attribution risk; the extinction coefficient of the common chromophores, the mass basis of a specific activity and triplicate practice are benign when unstated.
    'spectro_direct': {'background_alternatives': 0.75, 'attribution_supported': 0.80, 'calibration_applicability': 0.90, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # The eighteen further activity_rate types (2026-11-22, EXPERT_REVIEW, owner to confirm); the reason of each entry is in its converter docstring.
    # coupled_enzyme: the blank separates a primary activity from a contaminating one in an indirect assay; the product is known only through the reporter; coupling excess and lag are often unstated; NAD(P)H with a known coefficient is the textbook case.
    'coupled_enzyme': {'background_alternatives': 0.70, 'attribution_supported': 0.75, 'rate_regime': 0.80, 'calibration_applicability': 0.85, 'matrix_interference': 0.90, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # redox_mediator: dyes are reduced by thiols, ascorbate and light, so the blank separates enzyme from chemistry; a contaminating dye-reducing activity is common; the native-partner (bypass) question is the main risk of the method.
    'redox_mediator': {'background_alternatives': 0.70, 'attribution_supported': 0.75, 'assertion_relevance': 0.65, 'calibration_applicability': 0.85, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # fluorogenic: the no-enzyme blank is the main false positive of fluorescence; a contaminating protease or second reaction can release the fluorophore; an unstated standard curve or inner-filter check leaves the amount instrument-dependent.
    'fluorogenic': {'background_alternatives': 0.70, 'attribution_supported': 0.80, 'calibration_applicability': 0.75, 'matrix_interference': 0.75, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # luminescent: the no-enzyme and no-substrate controls separate the enzyme from carried-over ATP and autophosphorylation; an unchecked luciferase disturbance looks like extra activity; the reagent cannot tell which reaction made the ADP.
    'luminescent': {'background_alternatives': 0.75, 'matrix_interference': 0.75, 'attribution_supported': 0.70, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # stopped_flow: the assignment of the phase to the chemical step and the identity of the product are the central gap; the dead time and enzyme excess are usually evident; first-order rate constants do not scale with the enzyme amount; shots are averaged routinely.
    'stopped_flow': {'attribution_supported': 0.65, 'rate_regime': 0.85, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # quench_flow: the zero-time control and the quench test are the method's safeguards (a leaking quench gives a false burst); the product is separated and identified by the method itself; mass basis and triplicates are benign.
    'quench_flow': {'background_alternatives': 0.80, 'matrix_interference': 0.80, 'attribution_supported': 0.90, 'calibration_applicability': 0.90, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # chromatographic: the blank (no-enzyme, inactive enzyme, zero-time sample) separates activity from spontaneous chemistry; the retention time narrows a second reaction; an unstated quench or single end point turns a rate into an average; the other four are benign when unstated.
    'chromatographic': {'background_alternatives': 0.75, 'attribution_supported': 0.85, 'rate_regime': 0.80, 'calibration_applicability': 0.90, 'matrix_interference': 0.90, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # stopped_colorimetric: the blanks separate activity from reagent chemistry; a product class and a possible contaminating activity; a standard curve out of matrix changes every amount; an unstated number of time points leaves linearity unseen.
    'stopped_colorimetric': {'background_alternatives': 0.70, 'attribution_supported': 0.70, 'calibration_applicability': 0.80, 'rate_regime': 0.80, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # radiometric: the method is used for weak activities where the blank (carry-over, label impurity) is most of the signal; the product is known only through the separation; mass basis and triplicates are benign.
    'radiometric': {'background_alternatives': 0.70, 'attribution_supported': 0.75, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # separation_band: a copurified nuclease or protease and spontaneous breakage are the dominant false positives of a gel assay; an unmarked band may be a degradation product; stain and film response; a stopped-time rate needs its stop, early points and time count.
    'separation_band': {'background_alternatives': 0.70, 'attribution_supported': 0.75, 'calibration_applicability': 0.75, 'rate_regime': 0.75, 'normalization_basis': 0.90, 'sampling_basis': 0.85},
    # oxygen_electrode: autoxidation of reduced cofactors, thiols, catechols and metal ions and sensor drift are the dominant false positive; uncoupled oxygen use and a contaminating oxidase are the attribution risk; calibration, mass basis and triplicates are benign.
    'oxygen_electrode': {'background_alternatives': 0.65, 'attribution_supported': 0.70, 'calibration_applicability': 0.90, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # ph_stat: an unstated no-enzyme blank or CO2 exclusion is the dominant false positive (ester autohydrolysis, dissolved CO2 consumes base); any proton-releasing contaminant gives signal; titrant standardization changes the magnitude, not the existence.
    'ph_stat': {'background_alternatives': 0.70, 'attribution_supported': 0.75, 'calibration_applicability': 0.85, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # protein_film_electrochem: the bare-electrode and no-substrate controls separate catalysis from direct electrolysis; without the electroactive coverage and film loss a current is only relative; unstated mass transport leaves a limited current that reads low but exists.
    'protein_film_electrochem': {'background_alternatives': 0.65, 'attribution_supported': 0.75, 'normalization_basis': 0.60, 'calibration_applicability': 0.85, 'rate_regime': 0.75, 'sampling_basis': 0.85},
    # itc_kinetics: the dilution heat is the commonest false heat in a calorimeter; heat is non-specific and the product is rarely identified; mass basis and triplicate practice are benign when unstated.
    'itc_kinetics': {'background_alternatives': 0.70, 'attribution_supported': 0.75, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # continuous_ms: the blank (leak, drift, the preparation giving off the monitored species) separates activity from baseline; there is no known constant for the calibration of a given probe, so an unstated calibration leaves the absolute scale open (magnitude, not existence).
    'continuous_ms': {'background_alternatives': 0.75, 'calibration_applicability': 0.80, 'matrix_interference': 0.80, 'normalization_basis': 0.90, 'sampling_basis': 0.90},
    # nmr_timecourse: spectra show substrate and product separately, so an unstated blank or product assignment is more often benign; an unstated relaxation delay, internal standard or signal-to-noise is a real way for the integrals to be wrong; the other criteria take the 0.85 type default.
    'nmr_timecourse': {'background_alternatives': 0.80, 'attribution_supported': 0.90, 'calibration_applicability': 0.80, 'normalization_basis': 0.90},
    # product_immunodetection: an unstated no-enzyme or no-cofactor control is the usual false positive of a weak signal; an unstated antibody specificity is the largest gap; an unstated standard curve makes an amount uninterpretable; plate assays are usually run in duplicate or triplicate.
    'product_immunodetection': {'background_alternatives': 0.65, 'attribution_supported': 0.60, 'calibration_applicability': 0.70, 'normalization_basis': 0.90, 'sampling_basis': 0.85},
    # zymogram: the no-substrate and inactive lanes tell an enzyme band from a stain artefact; assigning a band in an extract to the protein is the central gap; the band mass against the expected mass; a representative gel of repeats.
    'zymogram': {'background_alternatives': 0.60, 'attribution_supported': 0.55, 'calibration_applicability': 0.75, 'measurement_identity': 0.70, 'sampling_basis': 0.80},
    # transport_cell_tracer_uptake (2026-11-22, EXPERT_REVIEW, owner to confirm; chain in literature_transport_cell_tracer_uptake_converter.py): the empty-vector or zero-time control and the label identity / competitor guard are the real gaps (host uptake, metabolism or trapping of the label can be the whole signal); the protein is presumed present (expression), intact cells are routine in filtration assays (integrity, energy test), the labelled compound is usually the substrate named (native substrate), triplicates are usual (sampling); the specific activity of a supplier's label is known (calibration) and the Km is stated even when the series is only in a figure (response model); the interval (transport_endpoint) takes the type default.
    'transport_cell_tracer_uptake': {'background_alternatives': 0.65, 'transport_specificity': 0.65, 'attribution_supported': 0.80, 'membrane_system': 0.85, 'transport_driving_force': 0.85, 'assertion_relevance': 0.85, 'sampling_basis': 0.85, 'calibration_applicability': 0.90, 'transport_response_model': 0.90},
    # transport_counterflow: the non-preloaded sample is what the trans-effect is read against (0.75); the protein-free control is what ties the exchange to the protein and not to another carrier or a metabolic trap (0.70); the non-substrate preload is the defining specificity control of a counterflow (0.70, together with label identity); retention of the preload keeps the gradient (0.75); the loading concentrations are in the methods of nearly every paper (0.85) and triplicates are usual for a ratio (0.90), so both are benign when unstated. transport_endpoint, transport_response_model and assertion_relevance take the type default.
    'transport_counterflow': {'background_alternatives': 0.75, 'attribution_supported': 0.70, 'transport_specificity': 0.70, 'membrane_system': 0.75, 'transport_driving_force': 0.85, 'sampling_basis': 0.90},
    # transport_fluorescent_reporter (DRAFT 2026-11-22, EXPERT_REVIEW, owner to confirm): the control cells and the no-substrate control are what separate transport by this protein from the host's own (0.50, as the PLA and yeast two-hybrid controls); autofluorescence, bleaching and dye leakage are real ordinary artefacts of a fluorescence reading (0.55); the fluorescent molecule is often an analogue that other carriers also take up (0.55); a relative signal without calibration leaves the fold but not its size (0.55); competition by the natural substrate or an inhibitor is what shows the analogue goes through this carrier (0.60); a viability check is ordinary but a leaky cell takes up a dye (0.65); expression is usually shown but often not said (0.70); the substrate concentration and the buffer are stated in Methods (0.70); triplicates are usual (0.80); transport_endpoint and transport_response_model take the default.
    'transport_fluorescent_reporter': {'background_alternatives': 0.50, 'matrix_interference': 0.55, 'assertion_relevance': 0.55, 'calibration_applicability': 0.55, 'transport_specificity': 0.60, 'membrane_system': 0.65, 'attribution_supported': 0.70, 'transport_driving_force': 0.70, 'sampling_basis': 0.80},
    # transport_medium_analysis (2026-11-22, EXPERT_REVIEW, owner to confirm; chain in literature_transport_medium_analysis_converter.py): the control strain and the expression check tie the signal to the protein (the YjeH deletion strain still exported most of the amino acid); metabolism and re-uptake unaddressed is the commonest failure of a medium analysis; an unstated regime, number of sampling times and stop usually mean a two-point interval average; lysis, the internal standard and the cell-free blank are less often a problem; standards in the medium and triplicates are routine.
    'transport_medium_analysis': {'background_alternatives': 0.80, 'attribution_supported': 0.60, 'matrix_interference': 0.80, 'calibration_applicability': 0.90, 'transport_endpoint': 0.65, 'transport_specificity': 0.65, 'membrane_system': 0.75, 'transport_driving_force': 0.85, 'sampling_basis': 0.85},
    # transport_oocyte_two_electrode (2026-11-22, EXPERT_REVIEW, owner to confirm; chain in literature_transport_oocyte_two_electrode_converter.py): the water-injected control and the ion or substrate specificity controls are the real gaps (a host current counted as the protein's); a current is charge and not the substrate; inactive-mutant and expression checks are often unsaid; oocyte and batch numbers and the clamp voltage are usually given; the same-oocyte baseline defines the current; the clamp is calibrated by the instrument.
    'transport_oocyte_two_electrode': {'background_alternatives': 0.70, 'transport_specificity': 0.70, 'assertion_relevance': 0.65, 'attribution_supported': 0.75, 'sampling_basis': 0.85,
                                       'transport_driving_force': 0.85, 'transport_endpoint': 0.90, 'calibration_applicability': 0.90},
    # transport_patch_clamp (2026-11-22, EXPERT_REVIEW, owner to confirm; chain in literature_transport_patch_clamp_converter.py): the host-cell control and the substrate-free control (endogenous currents can be the whole current); a mutant or blocker often unstated; charge flow is not ion flow without an ion substitution or a reversal potential; series resistance, seal and leak are benign when unstated; n of cells is usually in the legend.
    'transport_patch_clamp': {'background_alternatives': 0.65, 'attribution_supported': 0.70, 'transport_specificity': 0.60, 'calibration_applicability': 0.90, 'sampling_basis': 0.85},
    # transport_planar_bilayer (2026-11-22, EXPERT_REVIEW, owner to confirm; the answer chain is in literature_transport_planar_bilayer_converter.py): the protein-free bilayer and the attribution to the protein are what separate a channel from a contaminant or a failing bilayer (real gaps when unstated); the ion that carries the current is established only by a bi-ionic reversal potential, and charge flow is not ion flow; the usual recording solutions, the amplifier and filter practice and triplicate bilayers are benign when unstated, and a wrong driving force changes the size and not the existence.
    'transport_planar_bilayer': {'background_alternatives': 0.75, 'attribution_supported': 0.75, 'transport_specificity': 0.80, 'transport_driving_force': 0.90, 'calibration_applicability': 0.90, 'sampling_basis': 0.90},
    # transport_proteoliposome_tracer (2026-11-22, EXPERT_REVIEW, owner to confirm; chain in literature_transport_proteoliposome_tracer_converter.py): the empty-liposome control separates carrier transport from leak and label sticking (the lowest); vesicle tightness is often unstated and the empty-liposome control is part of it; the gradient and its control define the flux but a uniporter needs none; a competitor is evidence of specificity yet its absence does not invalidate a purified system; the active fraction changes the size of a turnover, not its existence; triplicates are usual.
    'transport_proteoliposome_tracer': {'background_alternatives': 0.75, 'membrane_system': 0.80, 'transport_driving_force': 0.80, 'transport_specificity': 0.90, 'calibration_applicability': 0.90, 'sampling_basis': 0.90},
    # transport_ssm_electrophysiology (2026-11-22, EXPERT_REVIEW, owner to confirm; chain in literature_transport_ssm_electrophysiology_converter.py): a jump over an empty sensor also gives a transient, so an unstated empty-liposome or artefact control can leave the current without an owner; charge flow is not identified-ion flow; an inactive-protein control is often left out; a reference jump on the same sensor decides whether Km and fold compare; peak current is the usual readout and triplicate sensors are usual.
    'transport_ssm_electrophysiology': {'background_alternatives': 0.60, 'transport_specificity': 0.60, 'attribution_supported': 0.75, 'calibration_applicability': 0.70, 'transport_endpoint': 0.85, 'sampling_basis': 0.80},
    # transport_vesicle_probe_flux (2026-11-22, EXPERT_REVIEW, owner to confirm; chain in literature_transport_vesicle_probe_flux_converter.py): the protein-free vesicle separates transport from leak; the second ion and the probe's selectivity say which species moved; the detergent total and the response time decide whether a rate is a rate; standard additions and triplicates are usual.
    'transport_vesicle_probe_flux': {'background_alternatives': 0.70, 'transport_specificity': 0.70, 'transport_endpoint': 0.75, 'calibration_applicability': 0.85, 'sampling_basis': 0.90},
    # The ten endpoint_conversion types (2026-11-22, all EXPERT_REVIEW, owner to confirm; the reasons are in registration/endpoint_<type>.md section 5 and the answer chain in each converter docstring). Criteria not listed take the type default.
    'endpoint_colorimetric': {'background_alternatives': 0.70, 'attribution_supported': 0.70, 'matrix_interference': 0.70, 'product_identity': 0.60, 'endpoint_alignment': 0.85, 'sampling_basis': 0.90},   # the blanks separate conversion from reagent chemistry; the colour cannot name the product
    'endpoint_enzymatic_assay': {'background_alternatives': 0.65, 'product_identity': 0.70, 'matrix_interference': 0.75, 'calibration_applicability': 0.85, 'sampling_basis': 0.90},   # the blank without the first enzyme separates conversion from a contaminating analyte; identity rests on the second enzyme's specificity
    'endpoint_gas_evolution': {'background_alternatives': 0.75, 'attribution_supported': 0.80, 'matrix_interference': 0.80, 'endpoint_alignment': 0.90, 'measurement_identity': 0.90, 'sampling_basis': 0.90},   # the no-enzyme vessel and leak check separate enzyme gas from chemistry and contamination
    'endpoint_gel_band': {'background_alternatives': 0.70, 'attribution_supported': 0.70, 'product_identity': 0.70, 'calibration_applicability': 0.80, 'conversion_denominator': 0.85, 'sampling_basis': 0.85},   # an unstated no-enzyme lane leaves spontaneous breakdown open; identity by mobility alone is the weakest
    'endpoint_hplc_uv': {'background_alternatives': 0.75, 'attribution_supported': 0.80, 'matrix_interference': 0.80, 'calibration_applicability': 0.90, 'endpoint_alignment': 0.90, 'sampling_basis': 0.90},   # the no-enzyme control and the time-zero sample separate conversion from spontaneous chemistry; a co-eluting peak adds to the product peak
    'endpoint_ms_quant': {'background_alternatives': 0.75, 'attribution_supported': 0.85, 'matrix_interference': 0.80, 'calibration_applicability': 0.85, 'endpoint_alignment': 0.80, 'product_identity': 0.90, 'sampling_basis': 0.90},   # an unstated blank is the dominant false positive for a weak conversion; ion suppression changes an amount by a factor
    'endpoint_nmr': {'background_alternatives': 0.75, 'attribution_supported': 0.75, 'calibration_applicability': 0.80, 'conversion_denominator': 0.90},   # NMR reactions run for hours at high loading where spontaneous conversion is real; unstated acquisition details put the integrals in doubt
    'endpoint_optical_plateau': {'calibration_applicability': 0.65, 'background_alternatives': 0.65, 'attribution_supported': 0.70, 'product_identity': 0.65, 'matrix_interference': 0.70, 'sampling_basis': 0.85},   # an unstated calibration leaves a signal change that is not a conversion; a plateau is not completion
    'endpoint_radiometric': {'background_alternatives': 0.70, 'attribution_supported': 0.80, 'product_identity': 0.75, 'calibration_applicability': 0.90, 'matrix_interference': 0.90, 'conversion_denominator': 0.90, 'sampling_basis': 0.90},   # an unstated blank or carry-over control is the dominant false positive of a very sensitive method
    'endpoint_time_course_completion': {'measurement_identity': 0.55, 'endpoint_alignment': 0.60, 'background_alternatives': 0.65, 'attribution_supported': 0.60, 'product_identity': 0.75, 'conversion_denominator': 0.85, 'sampling_basis': 0.85},   # no stated end state identifies no estimate; completion times of hours are where slow spontaneous chemistry competes
    # The nine product_distribution types (2026-11-22, EXPERT_REVIEW, owner to confirm); the reason of each entry is in its converter docstring.
    # distribution_chiral: an unstated racemic standard leaves the assignment of both peaks unproved (a real gap); an unstated no-enzyme control or configurational stability leaves a chemical route or racemization open, but both lower the excess instead of faking it (cautious side, 0.80); the inactive-enzyme control is the enzyme-attribution risk, as in spectro_direct (0.80); two isomers over their own sum have a shared denominator by construction, and replicate counts are benign when unstated (0.90).
    'distribution_chiral': {'species_identity': 0.75, 'background_alternatives': 0.80, 'attribution_supported': 0.80, 'common_denominator': 0.90, 'sampling_basis': 0.90},
    # distribution_enzymatic_endpoint: the specificity of the analysis enzymes and the quench of the first enzyme are what the method rests on (an enzyme that also reads the neighbour, a first enzyme that goes on working): unstated counts clearly less; a species with no assay is missing from the denominator (0.75); spontaneous interconversion and loss on standing stay open without a no-enzyme sample and a stability statement (0.75); an equilibrium read from one end point (0.65); the standard curve, completion and blank are routine and benign when unstated (response_factors 0.90, calibration_applicability 0.85), as are triplicates (0.90).
    'distribution_enzymatic_endpoint': {'species_identity': 0.75, 'matrix_interference': 0.70, 'common_denominator': 0.75, 'background_alternatives': 0.75, 'equilibrium_state': 0.65, 'calibration_applicability': 0.85, 'response_factors': 0.90, 'sampling_basis': 0.90},
    # distribution_gc: species_identity 0.75 (an unstated identification leaves a neighbouring isomer a possible reading of the peak); background_alternatives 0.70 (solvent, plastic, bleed and spontaneous rearrangement all give peaks, a minor product can be one of them; the real gap of this method); matrix_interference 0.75 (injector rearrangement and extraction loss decide whether the peak is the product made); response_factors 0.85 and calibration_applicability 0.85 (benign for FID isomers); sampling_basis 0.90 (triplicates are usual, an unstated count changes precision, not existence).
    'distribution_gc': {'species_identity': 0.75, 'background_alternatives': 0.70, 'matrix_interference': 0.75, 'response_factors': 0.85, 'calibration_applicability': 0.85, 'sampling_basis': 0.90},
    # distribution_gel_bands: species_identity 0.85, size markers are on almost every gel, so a silent paper is a reporting gap; response_factors 0.65, an unstated stain without a length correction can distort a share by the ratio of the fragment lengths (an end label does not); common_denominator 0.70, a band or smear left out of the total is unseen and moves every share; calibration_applicability 0.80, the linear range, the detection limit and the recovery are usual practice; background_alternatives 0.65, an unstated no-enzyme or substrate-only lane leaves a spontaneous breakdown (RNA is labile) or a pre-cleaved substrate counted as product, the leading false positive of a gel; attribution_supported 0.70, a contaminating nuclease is the risk and the inactive-enzyme lane is often not reported; sampling_basis 0.85, triplicate practice.
    'distribution_gel_bands': {'species_identity': 0.85, 'response_factors': 0.65, 'common_denominator': 0.70, 'calibration_applicability': 0.80, 'background_alternatives': 0.65, 'attribution_supported': 0.70, 'sampling_basis': 0.85},
    # distribution_hplc: an unstated standard leaves the peak assigned by retention time alone, the main false positive of HPLC (0.70); an unstated no-enzyme injection leaves spontaneous and substrate peaks open (0.75); a composition without equilibrium evidence is a single end point (0.70, counts only for the two equilibrium kinds, where the criterion is required); an unstated calibration range, quench or resolution is ordinary practice (0.85); an unstated replicate count is benign (0.90). The other criteria take the type default 0.80.
    'distribution_hplc': {'species_identity': 0.70, 'background_alternatives': 0.75, 'equilibrium_state': 0.70, 'calibration_applicability': 0.85, 'matrix_interference': 0.85, 'sampling_basis': 0.90},
    # distribution_lcms: response_factors 0.60, an unstated per-species calibration is the dominant gap of an ion-signal share (off by a multiple, not by a few percent); matrix_interference 0.65, ion suppression is common and changes the signal by tens of percent when unstated; background_alternatives 0.70, the method is so sensitive that a spontaneous product or contaminant ion is seen, so an unstated no-enzyme blank matters; calibration_applicability 0.80, an unstated calibration range or limit of quantification changes the precision more than the meaning; sampling_basis 0.90, triplicates are usual. The other criteria take the type default 0.75.
    'distribution_lcms': {'response_factors': 0.60, 'matrix_interference': 0.65, 'background_alternatives': 0.70, 'calibration_applicability': 0.80, 'sampling_basis': 0.90},
    # distribution_nmr: assignment by chemical shift is the usual practice (0.90); the delay between scans is rarely stated and a short one biases a share (0.80); an unassigned signal or a species left out of the total moves every share (0.80); an unstated no-enzyme spectrum is a real gap because a spontaneous isomerisation, hydrolysis or exchange gives its own distribution without the enzyme (0.75); an unstated inactive-enzyme control leaves a contaminating activity open, and an equilibrium composition is the same for any catalyst, so attribution is the main risk of the class (0.70); a composition counted as an equilibrium that was still moving (0.70, only selected for the equilibrium quantities); a single tube is usual for NMR, so the replicate count is benign when unstated (0.90). calibration_applicability, assertion_relevance and condition_scope take the 0.85 default.
    'distribution_nmr': {'species_identity': 0.90, 'response_factors': 0.80, 'common_denominator': 0.80, 'background_alternatives': 0.75, 'attribution_supported': 0.70, 'equilibrium_state': 0.70, 'sampling_basis': 0.90},
    # distribution_optical_equilibrium: species told apart by spectrum only (0.70); the extinction coefficients of the common chromophores are known (0.85); an unaccounted absorbing species or a composite constant moves the share (0.70); the equilibrium is the same without the enzyme, so an unstated no-enzyme sample (0.70) and inactive-enzyme sample (0.65) leave open that the plateau says nothing about THIS enzyme; an unstated plateau or reverse approach can turn a stalled reaction into an "equilibrium" (0.65, the defining evidence of the type); an absorbance below about 1 and triplicates are routine (0.85).
    'distribution_optical_equilibrium': {'species_identity': 0.70, 'response_factors': 0.85, 'common_denominator': 0.70, 'background_alternatives': 0.70, 'attribution_supported': 0.65, 'equilibrium_state': 0.65, 'calibration_applicability': 0.85, 'sampling_basis': 0.85},
    # distribution_radio_tlc: an unstated standard leaves the product named only by its position on the plate (a real gap, the claim itself); an unstated no-enzyme or zero-time lane leaves a radiochemical impurity of the labelled substrate free to be counted as a product (a real gap for a minor product); an unstated equal label per molecule or matched detection is benign for one isotope on one plate; an unstated linear range of the imager and the replicate count are ordinary practice. The other criteria take the type default 0.80.
    'distribution_radio_tlc': {'species_identity': 0.70, 'background_alternatives': 0.70, 'response_factors': 0.85, 'calibration_applicability': 0.85, 'sampling_basis': 0.85},
    # coupling_atp_product (EXPERT_REVIEW, owner to confirm): a ratio of sides that may not be matched, or of a product that may not be the claimed one, is the least interpretable (matched_windows 0.65, product_identity 0.70); an unstated basal rate counts uncoupled hydrolysis as cost (reporter_specificity 0.70); an unstated blank or no-enzyme control leaves spontaneous hydrolysis open (0.75); hydrolysis dependence is often shown but left unsaid (0.75); an unstated coefficient leaves a bare ratio, not a wrong one (0.75); a phosphate standard curve or the NADH extinction coefficient is routine (0.85); triplicates are usual (0.90).
    'coupling_atp_product': {'matched_windows': 0.65, 'product_identity': 0.70, 'reporter_specificity': 0.70, 'background_alternatives': 0.75, 'attribution_supported': 0.75, 'stoichiometry': 0.75, 'calibration_applicability': 0.85, 'sampling_basis': 0.90},
    # coupling_cofactor_product (EXPERT_REVIEW, owner to confirm): a ratio of product to cofactor is uninterpretable when the product is not identified or the two sides are not matched (0.65); the uncoupled cofactor use left unstated (no-substrate control, by-product) leaves the share the method exists to separate open (0.70); an unstated blank (0.75) and an unstated coefficient (a factor of 2 open for reactions that take two cofactors, 0.75) are real gaps; the extinction coefficient of NAD(P)H is well known and a standard series is usual practice (calibration 0.85), and triplicates are usual (0.90).
    'coupling_cofactor_product': {'product_identity': 0.65, 'matched_windows': 0.65, 'reporter_specificity': 0.70, 'background_alternatives': 0.75, 'stoichiometry': 0.75, 'calibration_applicability': 0.85, 'sampling_basis': 0.90},
    # coupling_electron_balance (EXPERT_REVIEW, owner to confirm): an unstated no-enzyme blank leaves chemistry or the electrode as a source of product electrons (background_alternatives 0.65); an unstated mediator bypass or oxygen exclusion is the dominant false positive of the method (reporter_specificity 0.60); a share from electrons and product of different intervals or vessels is uninterpretable (matched_windows 0.65); an unstated inactive-enzyme control leaves another catalyst open (attribution_supported 0.70); H2 by gas chromatography identifies itself (product_identity 0.85); the electrons per common product are textbook (stoichiometry 0.85); calibration, matrix and measurement identity are routine when unstated (0.80); triplicate practice (sampling_basis 0.90).
    'coupling_electron_balance': {'background_alternatives': 0.65, 'reporter_specificity': 0.60, 'matched_windows': 0.65, 'attribution_supported': 0.70, 'product_identity': 0.85, 'stoichiometry': 0.85, 'calibration_applicability': 0.80, 'matrix_interference': 0.80, 'measurement_identity': 0.80, 'sampling_basis': 0.90},
    # coupling_isotope_label (EXPERT_REVIEW, owner to confirm): the unlabelled run, back-exchange control and label position turn a mass shift into a flow through the claimed reaction; an unstated back-exchange control is the dominant false positive of H2 18O work (attribution_supported 0.65); a shifted ion without a standard can be another molecule (product_identity 0.70); no-enzyme control (0.75); no ratio of two measurements depends on the windows, the isotope ratio is read inside one spectrum (matched_windows 0.80); calibration and sampling are benign when unstated (0.85).
    'coupling_isotope_label': {'attribution_supported': 0.65, 'product_identity': 0.70, 'background_alternatives': 0.75, 'matched_windows': 0.80, 'calibration_applicability': 0.85, 'sampling_basis': 0.85},
    # coupling_limiting_reagent (EXPERT_REVIEW, owner to confirm): an unmatched endpoint or an unfinished reaction makes the ratio uninterpretable (matched_windows 0.70); an unidentified product is the case of a cofactor lost without the claimed product (product_identity 0.70); an unstated coefficient, excess or regeneration leaves open that nothing was limiting (stoichiometry 0.75); use of the limiting reagent by something else (an oxidase side activity) is common and usually unstated (reporter_specificity 0.70); sampling_basis 0.90 is benign when unstated.
    'coupling_limiting_reagent': {'matched_windows': 0.70, 'product_identity': 0.70, 'stoichiometry': 0.75, 'reporter_specificity': 0.70, 'sampling_basis': 0.90},
    # coupling_mass_balance (EXPERT_REVIEW, owner to confirm): a sum over peaks that were not identified, or over substrate and products taken from different mixtures or time points, is uninterpretable (product_identity 0.70, matched_windows 0.70); the no-enzyme or time-zero sample separates enzymatic consumption from spontaneous loss of the substrate (background_alternatives 0.75); an unquantified expected product or a missing inactive-enzyme control leaves the balance open (attribution_supported 0.75); triplicates are usual (sampling_basis 0.90).
    'coupling_mass_balance': {'product_identity': 0.70, 'matched_windows': 0.70, 'background_alternatives': 0.75, 'attribution_supported': 0.75, 'sampling_basis': 0.90},
    # coupling_oxygen_product (EXPERT_REVIEW, owner to confirm): an unstated identity is the dominant false positive, the oxygen goes elsewhere and the product is inferred from the uptake (product_identity 0.55); unmatched vessels or intervals make the ratio one of unrelated numbers (matched_windows 0.65); an unstated no-substrate control or peroxide accounting leaves oxygen used by something else (reporter_specificity 0.65); an unstated electrode calibration and product standard are routine (0.85); drift is measured and small, a no-enzyme blank is usual (background_alternatives 0.80); triplicates are usual (0.90).
    'coupling_oxygen_product': {'product_identity': 0.55, 'matched_windows': 0.65, 'reporter_specificity': 0.65, 'calibration_applicability': 0.85, 'background_alternatives': 0.80, 'sampling_basis': 0.90},
    # coupling_uncoupling_byproduct (EXPERT_REVIEW, owner to confirm): an unstated product measurement most likely means none was made, so the ratio does not identify the product (0.55); an unstated accounting of the other loss routes usually means only one route was measured and the difference overstates the coupling (0.60); peroxide reagent artefacts and their checks are real and often unstated (reporter_specificity and matrix_interference 0.65); autoxidation of the cofactor and contaminating iron or heme are real but the blank is ordinary practice (0.70); the cofactor loss and the by-product are often measured separately (matched_windows 0.65); the same enzyme preparation is usual (0.80); a standard curve is usual (0.85); triplicates are usual (0.90).
    'coupling_uncoupling_byproduct': {'product_identity': 0.55, 'stoichiometry': 0.60, 'reporter_specificity': 0.65, 'matrix_interference': 0.65, 'background_alternatives': 0.70, 'attribution_supported': 0.70, 'matched_windows': 0.65, 'measurement_identity': 0.80, 'calibration_applicability': 0.85, 'sampling_basis': 0.90},
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
# 'interaction_not_detected' (opposes) alike (OWNER_DECISION 2; times STATED_ONLY_STRENGTH for a type that can report a
# measured effect, OWNER_DECISION 19), and the per-type maximum of a quantitative result
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
    'colocalization': 0.5,  # EXPERT_REVIEW, confirmed by the owner 2026-11-22: microscopy co-localization or recruitment shows nearness (within about 250 nm with diffraction-limited imaging), not contact, in the same family as bret, proximity and pla; a heterologous or purified system and the controls raise the weight through the criteria, not this value.
    'y2h': 0.4,             # EXPERT_REVIEW: heterologous nuclear reporter; high false-positive and false-negative rates.
    'split_reporter': 0.4,  # EXPERT_REVIEW: reporter reconstitution can occur through proximity or forced association; weakest direct-binding evidence.
    'spectro_direct': 1.2,  # EXPERT_REVIEW, owner to confirm (decided 2026-11-21): a direct continuous absorbance readout of the reaction on purified enzyme is the standard evidence of catalysis, so a stated rate is strong (below SPR 1.5: the chromophore change names a reaction only when the product is identified, and that is a weight criterion, not this magnitude). The same constant is the magnitude of 'activity not detected': an absent signal is limited by the assay's detection limit and the substrate and conditions tried, so it is not stronger than 1.2.
    # The eighteen further activity_rate types (2026-11-22, all EXPERT_REVIEW, owner to confirm). The same constant is the magnitude of 'activity not detected'.
    'coupled_enzyme': 1.0,  # EXPERT_REVIEW, owner to confirm: a continuous, purified-enzyme rate read through a reporter chain; a contaminating activity feeding the same reporter or a coupling-limited slope can look like (or hide) activity, so it counts less than the direct assay (1.2).
    'redox_mediator': 1.0,  # EXPERT_REVIEW, owner to confirm: electron transfer to a surrogate dye is strong evidence of a redox enzyme but not of the claimed reaction with its native partner (below spectro_direct 1.2); an absent dye reduction is weaker still, the one constant is the compromise.
    'fluorogenic': 1.1,  # EXPERT_REVIEW, owner to confirm: a stated rate on enzyme is strong evidence of catalysis, a little under spectro_direct because a fluorescence readout of a mostly synthetic substrate is more open to artefact (autohydrolysis, inner filter, quenching, gain).
    'luminescent': 1.0,  # EXPERT_REVIEW, owner to confirm: the reagent reads ADP, ATP or NAD(P)H, not the reaction itself (a contaminating ATPase, autophosphorylation and carried-over ATP give the same light), so below spectro_direct 1.2 and above the proximity types 0.5.
    'stopped_flow': 1.0,  # EXPERT_REVIEW, owner to confirm: a time-resolved optical readout on purified enzyme is direct, but it reports a phase of a signal that counts as chemistry only when assigned to it (a fast optical change can be binding or a conformational step).
    'quench_flow': 1.3,  # EXPERT_REVIEW, owner to confirm: the product is separated, identified and counted, not read from an optical proxy, and the zero-time and quench controls are standard, so slightly above spectro_direct 1.2 and under SPR/ITC 1.5 (a rate of a chemical step, not of a defined binding pair); an absent product is limited by the substrate, time range and detection limit tried.
    'chromatographic': 1.3,  # EXPERT_REVIEW, owner to confirm: a separated, identified and calibrated product peak is among the most direct evidence of catalysis, a little above spectro_direct 1.2 and below SPR and ITC 1.5.
    'stopped_colorimetric': 1.0,  # EXPERT_REVIEW, owner to confirm: a measured rate on purified enzyme is good evidence, but the colour names a product class, is read only at chosen times and is easily raised by the reagent reacting with substrate or buffer; below spectro_direct 1.2, level with fret and fcs.
    'radiometric': 1.3,  # EXPERT_REVIEW, owner to confirm: the label follows the substrate's own atoms and the count is very sensitive, so slightly above a chromophore proxy (spectro_direct 1.2); below SPR 1.5 because the product is known only through the separation.
    'separation_band': 1.1,  # EXPERT_REVIEW, owner to confirm: the product is seen as a band of the expected size, which names it better than a bare absorbance change, but the conversion is semi-quantitative densitometry from a few stopped points and an absent band is limited by stain or exposure sensitivity.
    'oxygen_electrode': 1.0,  # EXPERT_REVIEW, owner to confirm: a direct continuous oxygen readout is real evidence of an oxygen-using reaction but oxygen use is not specific (autoxidation, sensor drift, a contaminating oxidase, uncoupled oxygen use), so it names the reaction less than a chromophore does.
    'ph_stat': 1.0,  # EXPERT_REVIEW, owner to confirm: the base added is a direct stoichiometric count of protons released, but it counts every proton source (spontaneous hydrolysis, dissolved CO2, acid-producing contaminants); below spectro_direct 1.2, at the level of fret.
    'protein_film_electrochem': 1.0,  # EXPERT_REVIEW, owner to confirm: a substrate-dependent catalytic current of a film, absent without enzyme, is direct label-free evidence of catalysis, but only for an enzyme that exchanges electrons with the electrode in a film of unknown active fraction and orientation; one step under spectro_direct.
    'itc_kinetics': 1.0,  # EXPERT_REVIEW, owner to confirm: a stated rate from a direct heat read on purified enzyme is strong evidence, but the heat is non-specific (any process in the cell adds to it, the product is not identified), so under spectro_direct 1.2.
    'continuous_ms': 1.2,  # EXPERT_REVIEW, owner to confirm: as spectro_direct: a continuous readout of the reaction on purified enzyme is the standard evidence of catalysis; a mass names the product more surely than an absorbance, but the instrument and its calibration are lab-specific, so not above 1.2.
    'nmr_timecourse': 1.2,  # EXPERT_REVIEW, owner to confirm: an assigned product seen by its chemical shift is strong evidence (better than a dye signal), but the method is insensitive, so 'activity not detected' is bounded by a high detection limit; the two pull opposite ways and the value equals spectro_direct.
    'product_immunodetection': 0.9,  # EXPERT_REVIEW, owner to confirm: the signal is an antibody's reading of the product and depends on its specificity and on the controls (which lower the weight, not this value); level with the relative immunoassays (elisa 0.8, alphascreen 0.8) but a little higher because the signal is tied to an enzyme-dependent modification.
    'zymogram': 0.6,  # EXPERT_REVIEW, owner to confirm: a band of activity at a gel position is a direct enzymatic readout (more direct than the nearness types 0.5) but qualitative, on a renatured or partly denatured enzyme, and it names a band, not a protein. See the note on stated_strength in REGISTERED_activity_rate.md.
    # The ten transport_response types (2026-11-22, all EXPERT_REVIEW, owner to confirm). The same constant is the magnitude of 'transport not detected'. Rule: a weaker assay carries less evidence.
    'transport_proteoliposome_tracer': 1.5,  # EXPERT_REVIEW, owner to confirm: only protein, lipid and gradient define the flux, so a stated transport is the cleanest evidence that this protein moves this substrate (level with SPR in the binding class); a non-detection can also come from an inactive or badly oriented reconstitution.
    'transport_planar_bilayer': 1.4,  # EXPERT_REVIEW, owner to confirm: single molecules of the purified protein in a defined bilayer, the ion identified by its reversal potential; the strongest transport evidence after the proteoliposome tracer and stronger than every cell assay.
    'transport_ssm_electrophysiology': 1.3,  # EXPERT_REVIEW, owner to confirm: a defined system (purified protein, lipid, one substrate jump) but the amplitude is relative to the protein on the sensor and only electrogenic steps give a signal; a little under the planar bilayer and the proteoliposome tracer.
    'transport_counterflow': 1.2,  # EXPERT_REVIEW, owner to confirm: preloaded vesicles taking up label above the non-preloaded baseline is direct evidence that the transporter exchanges the two molecules, but it infers the substrate from trans-stimulation and is a relative ratio; below the proteoliposome tracer (1.5), level with vesicle probe flux, patch clamp and oocyte clamp.
    'transport_vesicle_probe_flux': 1.2,  # EXPERT_REVIEW, owner to confirm: a defined vesicle system followed in real time with a protein-free control has no host background (stronger than a cell assay) but the species is only as sure as the probe's selectivity and the second-ion control.
    'transport_patch_clamp': 1.2,  # EXPERT_REVIEW, owner to confirm: a direct electrical readout of charge movement with its own signature (reversal potential, block, ion dependence), but in a cell whose own channels and transporters add a background, and charge flow is not the flow of one ion; as the oocyte clamp, below the bilayer, above whole-cell tracer uptake.
    'transport_oocyte_two_electrode': 1.2,  # EXPERT_REVIEW, owner to confirm: a current of oocytes that make one injected protein, read against water-injected oocytes, is a direct and sensitive readout in a defined host; but the host has its own carriers, the current is charge and not the substrate, and an electroneutral transporter gives no current; under the vesicle and bilayer systems, above whole-cell tracer uptake.
    'transport_cell_tracer_uptake': 1.0,  # EXPERT_REVIEW, owner to confirm: the label kept by living cells can also come from other host transporters, metabolism or trapping of the label and surface binding; weaker than a defined system (proteoliposomes 1.5, bilayer 1.4) and stronger than an interval balance in the medium or a dye (0.9).
    'transport_medium_analysis': 0.9,  # EXPERT_REVIEW, owner to confirm: an interval balance of export, re-uptake, lysis and metabolism on a living host with other transporters, not the movement through one protein; weaker than the tracer assay (where the label follows the substrate).
    'transport_fluorescent_reporter': 0.9,  # EXPERT_REVIEW, owner to confirm: an analogue or a surrogate ion and a relative dye signal are not the substrate and not an amount; the weakest of the class, level with the medium analysis.
    # The ten endpoint_conversion types (2026-11-22, all EXPERT_REVIEW, owner to confirm). The same constant is the magnitude of 'conversion not detected'. Rule: the product named and quantified by the method itself is the strongest; a class of products or a final signal alone is the weakest.
    'endpoint_ms_quant': 1.4,  # EXPERT_REVIEW, owner to confirm: the product is seen by its mass and quantified against an authentic standard with an internal standard; among the most specific end-point evidence.
    'endpoint_hplc_uv': 1.3,  # EXPERT_REVIEW, owner to confirm: the product is separated, identified against an authentic standard and quantified; identity by retention time is weaker than by mass.
    'endpoint_nmr': 1.3,  # EXPERT_REVIEW, owner to confirm: a product assigned by its spectrum and quantified without a response factor; the low sensitivity limits what a non-detection can exclude, not what is seen.
    'endpoint_radiometric': 1.2,  # EXPERT_REVIEW, owner to confirm: the label follows the substrate's own atoms and the count is very sensitive, but the product is known only through the separation; under the activity radiometric type (1.3).
    'endpoint_time_course_completion': 1.1,  # EXPERT_REVIEW, owner to confirm: a time to completion is relative to the loading and to the end state the paper chose; a long one cannot be told from slow background chemistry.
    'endpoint_gas_evolution': 1.1,  # EXPERT_REVIEW, owner to confirm: a gas product named by the detector is specific and direct, but the vessel, the headspace calibration and the dissolved part decide the amount.
    'endpoint_gel_band': 1.0,  # EXPERT_REVIEW, owner to confirm: densitometry of a band shift is semi-quantitative and the band is identified by its mobility only.
    'endpoint_enzymatic_assay': 1.0,  # EXPERT_REVIEW, owner to confirm: a second enzyme reports the amount, so identity rests on that enzyme's specificity and on a blank easy to contaminate.
    'endpoint_colorimetric': 0.9,  # EXPERT_REVIEW, owner to confirm: a reagent reports a product class (phosphate, reducing ends, a thiol), not a named product, and is easily raised by reagent chemistry.
    'endpoint_optical_plateau': 0.9,  # EXPERT_REVIEW, owner to confirm: a final optical change is one number with no trace to check; a plateau does not show completion and names a reaction only when the product is identified.
    # The nine product_distribution types (2026-11-22, all EXPERT_REVIEW, owner to confirm). The same constant is the magnitude of 'product not detected'. Rule: the methods that identify the species by structure (NMR, GC, chiral) carry most, those that need response factors or identify by retention or signal alone carry less, and those that tell species apart by size or spectrum alone least.
    'distribution_chiral': 1.3,  # EXPERT_REVIEW, owner to confirm: chiral chromatography identifies both isomers (racemic standard) and gives a share with no response bias for enantiomers (equal response by symmetry), so it carries as much as NMR and GC for this class; below the label-free binding types (SPR 1.5), above the HPLC area method (1.2), whose response factors are unequal.
    'distribution_enzymatic_endpoint': 1.1,  # EXPERT_REVIEW, owner to confirm: each species is identified by the specificity of its own enzyme and is molar by calibration, so a stated product is good evidence, but identity rests on enzyme specificity and not on structure, and a species with no assay is invisible; below NMR, GC and chiral (1.3), level with LC-MS (1.1), above gel bands (1.0) and optical equilibrium (0.9).
    'distribution_gc': 1.3,  # EXPERT_REVIEW, owner to confirm: GC separates and names the species (retention index plus mass spectrum) and an FID share has little response bias for isomers; strong, below the label-free binding types; the same value as NMR and chiral chromatography, above HPLC (area needs response factors) and LC-MS (ion signal is not molar).
    'distribution_gel_bands': 1.0,  # EXPERT_REVIEW, owner to confirm: a band is identified by its mobility against a ladder only, and a densitometry share rests on an indirect label or stain; below the separation-and-detector methods (HPLC, GC, NMR 1.2 to 1.3).
    'distribution_hplc': 1.2,  # EXPERT_REVIEW, owner to confirm: the species are separated and a stated share rests on peaks assigned against standards, so a stated product is good evidence; below NMR, GC and chiral (1.3) because an HPLC area needs response factors and identity by retention alone is weaker than by spectrum; level with spectro_direct (1.2).
    'distribution_lcms': 1.1,  # EXPERT_REVIEW, owner to confirm: a mass and a retention time identify a species specifically, so a stated product is strong evidence; but an ion signal is not a molar amount (ionisation efficiency differs between species, the matrix suppresses it), so the size of a share is weaker than from NMR or GC (1.3) or HPLC with response factors (1.2).
    'distribution_nmr': 1.3,  # EXPERT_REVIEW, owner to confirm: species identified by their spectrum and quantified by their integrals, with no response curve and no separation step, are strong evidence of which products a reaction gives; the low sensitivity of NMR (about 1 to 5 percent for a minor species, from memory) limits what a non-detection can exclude, which the signal-to-noise criterion carries through the weight, not this magnitude.
    'distribution_optical_equilibrium': 0.9,  # EXPERT_REVIEW, owner to confirm: the weakest method of the class; species are told apart by their spectra only (no separation, no structural identity) and an equilibrium composition is the same for any catalyst, so it shows where the reaction lies more than that this enzyme makes the product; the gel type is 1.0, NMR, GC and chiral 1.3.
    'distribution_radio_tlc': 1.2,  # EXPERT_REVIEW, owner to confirm: direct counting of the label in each separated species is sensitive and has no detector-response bias between species of one isotope, but it names a product only by its position beside a standard and sees only products that keep the label; a notch below the methods that identify the species by themselves (NMR, GC, chiral 1.3) and level with HPLC (1.2).
    # The eight reaction_coupling types (2026-11-22, all EXPERT_REVIEW, owner to confirm). The same constant is the magnitude of 'no product formed above the control'. Rule: a weaker assay carries less evidence.
    'coupling_atp_product': 1.2,  # EXPERT_REVIEW, owner to confirm: both sides of the reaction are measured in one mixture, so a stated product formed with the nucleotide is strong evidence of an ATP-driven reaction; level with spectro_direct (1.2) and below SPR (1.5), because the product is known through a second assay and the match of the two sides is a weight criterion, not this magnitude.
    'coupling_cofactor_product': 1.3,  # EXPERT_REVIEW, owner to confirm: a product identified by chromatography or mass spectrometry and tied to the cofactor use of the same reaction shows the claimed reaction itself and not only a signal; a little above spectro_direct (1.2) and below SPR (1.5); an absent product is limited by the detection limit and the conditions tried.
    'coupling_electron_balance': 1.0,  # EXPERT_REVIEW, owner to confirm: a closed electron count on an identified product is direct evidence that the electrons end in the claimed product, but does not say which catalyst moved them (a mediator dye or the electrode can do it); a little below a direct rate on purified enzyme (spectro_direct 1.2).
    'coupling_isotope_label': 1.0,  # EXPERT_REVIEW, owner to confirm: a label found in the product shows where an atom came from, direct evidence for the claimed route, but not how much of the consumed partner ended in the product, and open to exchange artefacts (a carbonyl oxygen exchanging with H2 18O); the same level as fret and fcs, below spectro_direct (1.2).
    'coupling_limiting_reagent': 1.2,  # EXPERT_REVIEW, owner to confirm: a reaction run to completion on one limiting reagent, with the product identified, is the standard direct evidence of a reaction with its stoichiometry, level with spectro_direct (1.2) and below SPR (1.5): the claim is coupling, which needs two measurements to agree, and a ratio is only as sure as its endpoint.
    'coupling_mass_balance': 1.3,  # EXPERT_REVIEW, owner to confirm: the substrate and every product are separated, identified and quantified in the same samples, so a stated closure or product formation is strong, specific evidence of the claimed reaction; level with endpoint_hplc_uv (1.3), a little under endpoint_ms_quant (1.4) because identity is often by retention time, and under SPR and ITC (1.5).
    'coupling_oxygen_product': 1.2,  # EXPERT_REVIEW, owner to confirm: two independent measurements (an electrode and an identified, calibrated product) agree on one reaction, the standard evidence that the claimed product comes from the oxygen reaction; level with spectro_direct (1.2) and below SPR (1.5): the two sides are linked only by a matched vessel and window (a weight criterion, not this magnitude).
    'coupling_uncoupling_byproduct': 0.6,  # EXPERT_REVIEW, owner to confirm: the by-product shows how much cofactor is NOT used for the product; the productive share is the rest by difference, and the product is not identified by the method itself; indirect like thermal stabilisation (dsf, cetsa 0.6) and below the direct paired-rate and direct-readout types (spectro_direct 1.2).
}

# ---------------------------------------------------------------------------------------------------------------
# (5b) QUANTITATIVE_STRENGTH_ANCHORS: the two ENDS of each type's gray scale for its measured effect (QUANTITATIVE_STRENGTH),
# in the effect's own unit. Every converter that fills an effect reports a binding or engagement constant in nM (variance in
# nM_squared), so each scale runs on log10 of the constant. noise_end: a constant this weak is indistinguishable from the
# type's nonspecific background or detection floor (strength 0); strong_end: a constant this tight is the strongest signal
# the type resolves (strength 1). They are never thresholds: every value between them gets a smoothly graded strength.
# Types whose converters fill no effect (pulldown, y2h, pla, proximity, colocalization: qualitative only) have no anchors.
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
# (5b2) STATED_ONLY_STRENGTH (OWNER_DECISION 19; owner, 2026-11-22: "yes/no statement is weakest evidence than experimental
# measurements"). A type that can report a measured effect (it has anchors in QUANTITATIVE_STRENGTH_ANCHORS, or it is an
# activity_rate, transport_response, endpoint_conversion, product_distribution or reaction_coupling type) may also be stated in words alone ("binds", "no binding was detected", "active"), with no number. Such a
# result says nothing about where on the type's scale the effect sits, so it counts as a fixed low strength on that scale:
# log_ratio = QUALITATIVE_LOG_RATIO[type] * STATED_ONLY_STRENGTH, for a stated detection and a stated non-detection alike.
# 0.25 is chosen so that the bare statement of even the strongest type (SPR or ITC, 1.5 * 0.25 = 0.375) stays under the
# observed result of the weakest type (yeast two-hybrid, 0.4); a measured SPR constant counts more than the sentence whenever
# it is tighter than about 11 uM (strength above 0.25). A type whose own result IS a yes/no observation (pulldown, y2h, pla, colocalization,
# proximity: no anchors) keeps its full QUALITATIVE_LOG_RATIO: there the observed band, growth or signal is the measurement.
# ---------------------------------------------------------------------------------------------------------------
STATED_ONLY_STRENGTH = 0.25   # EXPERT_REVIEW; confirmed by the owner 2026-11-22


# Types of a measuring class whose OWN result is a yes/no observation (a band of activity in the gel): they keep their full value, like pulldown or y2h.
OBSERVATION_RESULT_TYPES = ('zymogram',)


def stated_strength(experiment_type):
    """The strength a result stated in words alone takes on its type's scale (OWNER_DECISION 19)."""
    measures = (experiment_type in QUANTITATIVE_STRENGTH_ANCHORS or CLASS_OF_EXPERIMENT_TYPE[experiment_type] in ('activity_rate', 'transport_response', 'endpoint_conversion', 'product_distribution', 'reaction_coupling')) and experiment_type not in OBSERVATION_RESULT_TYPES
    return STATED_ONLY_STRENGTH if measures else 1.0


# ---------------------------------------------------------------------------------------------------------------
# (5c) ACTIVITY_STRENGTH_ANCHORS: the activity_rate class's gray-scale ends (decided 2026-11-21, owner to confirm; every
# number below is EXPERT_REVIEW and every literature citation is from memory, to be verified). Anchors are per QUANTITY, not per
# experiment type: the physics of kcat, kcat/Km, specific activity and fold over control is the same in every assay. For these
# quantities LARGER is stronger; the position runs on the log10 scale from noise_end (strength 0) to strong_end (strength 1), as
# for the binding anchors. They are the two ends of a gray scale, never thresholds.
# Reference points (from memory, Bar-Even A et al. 2011 Biochemistry 50:4402-4410): natural enzymes have a median kcat near
# 10 s^-1 and a median kcat/Km near 1e5 M^-1 s^-1; the upper quartiles are near 70 s^-1 and 1e6 M^-1 s^-1. Promiscuous
# (side) activities of enzymes are typically 1e2 to 1e4 times less efficient than the main activity, so their kcat/Km sits near
# 1e3 M^-1 s^-1 and their kcat near 1e-2 to 1 s^-1 (from memory, Khersonsky O, Tawfik DS 2010 Annu Rev Biochem 79:471-505).
# noise_end: a rate this low is no better than promiscuous or background chemistry. strong_end: about the upper quartile of
# natural enzymes. A median natural enzyme then sits at p = 0.75 on both scales, so the two scales agree with each other.
ACTIVITY_STRENGTH_ANCHORS = {
    # catalytic efficiency kcat/Km. noise_end: one decade under the typical promiscuous activity (1e3). strong_end: upper quartile of natural enzymes.
    'catalytic_efficiency': {'unit': 'M^-1s^-1', 'noise_end': 1e2, 'strong_end': 1e6},   # EXPERT_REVIEW, owner to confirm
    # turnover kcat. noise_end: the low end of promiscuous turnover (1e-2 s^-1, about one turnover per two minutes). strong_end: the upper quartile (70) rounded to 1e2.
    'turnover': {'unit': 's^-1', 'noise_end': 1e-2, 'strong_end': 1e2},                  # EXPERT_REVIEW, owner to confirm
    # a rate over the paper's own control, as a fold. noise_end: 1 (no better than the control). strong_end: three orders over the control, the practical dynamic range of most activity assays (signal over background); a fold at or under 1 is strength 0, never opposition.
    'rate_over_control': {'unit': 'fold', 'noise_end': 1.0, 'strong_end': 1e3},          # EXPERT_REVIEW, owner to confirm
}
# Specific activity (U/mg, U = umol per minute) has no ends of its own: its ends are the kcat ends at the enzyme's molar mass M
# (g/mol): U/mg = kcat * SECONDS_PER_MINUTE * UMOL_PER_MMOL / M (literature_activity_direction.specific_activity_ends).
SECONDS_PER_MINUTE = 60.0          # FIXED_BY_DEFINITION: U = umol/min, kcat in s^-1.
UMOL_PER_MMOL = 1000.0             # FIXED_BY_DEFINITION: M g/mol is M mg per mmol, so one enzyme molecule's mass in mg per umol is M / 1000.
REFERENCE_ENZYME_MASS_G_PER_MOL = 5.0e4   # EXPERT_REVIEW, owner to confirm: used for the specific-activity ends only when the record does not state the enzyme's mass; 50 kDa, a typical subunit (the median enzyme subunit is about 40 to 50 kDa, from memory).
# Which stated quantity is the effect when a record states several: the best-determined first (decided 2026-11-21, owner to
# confirm). kcat/Km is a ratio of two fitted constants taken at low substrate and does not depend on the active-site amount
# being known or on saturation; kcat needs the active-site concentration and a saturating curve; specific activity needs only
# the mass of protein, which includes inactive protein and depends on the one substrate concentration used; a fold over the
# paper's own control is relative to a control whose own activity differs between papers.
ACTIVITY_EFFECT_ORDER = ('catalytic_efficiency', 'turnover', 'specific_activity', 'rate_over_control')
# The record's quantity kind (QUANTITY_KINDS['activity_rate']) of the effect, and the anchor quantity it is read against.
ACTIVITY_QUANTITY_OF_KIND = {'catalytic_efficiency': 'catalytic_efficiency', 'turnover': 'turnover', 'rate': 'specific_activity', 'rate_ratio': 'rate_over_control'}

# ---------------------------------------------------------------------------------------------------------------
# (5d) TRANSPORT_STRENGTH_ANCHORS: the transport_response class's gray-scale ends (DRAFT 2026-11-22, owner to confirm; every number below is
# EXPERT_REVIEW and every literature figure is from memory, not verified). Anchors are per QUANTITY, not per experiment type: the physics of a
# Km, a turnover or a unitary conductance is the same in every assay. The position runs on the log10 scale from noise_end (strength 0) to
# strong_end (strength 1), as for the binding and activity anchors. They are the two ends of a gray scale, never thresholds.
# Direction: for transport_km a SMALLER value is stronger (noise_end > strong_end, as for a binding constant); for every other quantity a LARGER
# value is stronger.
# ---------------------------------------------------------------------------------------------------------------
TRANSPORT_STRENGTH_ANCHORS = {
    # Apparent Km (or K0.5) of the transported substrate, in uM. noise_end 1e4 uM (10 mM): saturation is hardly reachable in an uptake assay and a
    # Km this large is not told from a linear, non-mediated uptake; strong_end 1 uM: a high-affinity carrier (BioY about 0.25 uM, BtsT about 16 uM,
    # most nutrient carriers 1 to 1000 uM; from memory).
    'transport_km': {'unit': 'uM', 'noise_end': 1e4, 'strong_end': 1.0},                                   # EXPERT_REVIEW, owner to confirm
    # Turnover per transporter molecule or channel, in s^-1 (the same ends as the activity turnover). noise_end 1e-2: about one turnover per
    # two minutes, the slow end of carriers and ATP-driven pumps; strong_end 1e2: the upper range of carriers (typical carriers 1 to 100 s^-1; a
    # channel is far above and caps at 1; from memory).
    'turnover': {'unit': 's^-1', 'noise_end': 1e-2, 'strong_end': 1e2},                                    # EXPERT_REVIEW, owner to confirm
    # Unitary (single-channel) conductance, in pS, already corrected for the driving force (g = I / (V - Vrev)). noise_end 1 pS: about 0.1 pA at
    # 100 mV, the least a single-channel recording resolves above its own noise (about 0.1 pA rms, from memory); strong_end 100 pS: the large
    # end of ordinary ion channels (many are 10 to 100 pS; the fluoride channel Fluc about 7 pS; from memory).
    'unitary_conductance': {'unit': 'pS', 'noise_end': 1.0, 'strong_end': 1e2},                            # EXPERT_REVIEW, owner to confirm
    # Charge-equivalent rate of one channel (elementary charges per second, current / e). The ends are the two conductance ends read at 100 mV
    # (1 pS = 6.2e5 charges/s, 100 pS = 6.2e7 charges/s), rounded: so the two channel scales agree. Used when only a current and not a conductance is stated.
    'charge_rate': {'unit': 'elementary_charge_equivalents_per_s', 'noise_end': 6e5, 'strong_end': 6e7},  # EXPERT_REVIEW, owner to confirm
    # A rate or an accumulated amount over the paper's own matched negative control (empty vector, protein-free liposomes, uninjected oocyte,
    # no substrate), as a dimensionless ratio. noise_end 1: no better than the control; strong_end 30: the control then holds about 3 percent of the
    # signal, so it no longer limits the reading (typical empty-vector backgrounds are 3 to 30 percent of a good uptake signal; from memory).
    # A ratio at or under 1 is strength 0 (neutral), never opposition.
    'fold_over_control': {'unit': 'dimensionless', 'noise_end': 1.0, 'strong_end': 30.0},                  # EXPERT_REVIEW, owner to confirm
    # Rate per mass of the preparation (cells, vesicles or purified protein), in nmol/min/mg. noise_end 1e-3 (1 pmol/min/mg): about 90 counts per
    # minute at 40 mCi/mmol (88.8 dpm per pmol), the floor of a filtration assay over its blank; strong_end 1e1 (10 nmol/min/mg): a well expressed
    # carrier in whole cells (from memory). Weak evidence: it depends on expression level, the substrate and the normalizer (open question).
    'normalized_rate': {'unit': 'nmol/min/mg', 'noise_end': 1e-3, 'strong_end': 1e1},                      # EXPERT_REVIEW, owner to confirm
}
# Which stated quantity is the effect when a record states several: the best-determined first (DRAFT, owner to confirm). Km is an intensive
# property: it needs neither the amount of transporter nor a normalizer, and a fitted saturable curve already shows signal over background.
# Turnover and unitary conductance are intensive per molecule too, but need the active amount or a single-channel record. The charge-equivalent
# rate comes after the conductance, which has the driving force removed. A fold over the paper's own control shows that the protein transports
# at all but depends on the control's own background. A rate per mg depends on expression, substrate concentration and the normalizer, so it is last.
TRANSPORT_EFFECT_ORDER = ('transport_km', 'turnover', 'unitary_conductance', 'charge_rate', 'fold_over_control', 'normalized_rate')   # EXPERT_REVIEW, owner to confirm
# The record's quantity kind (QUANTITY_KINDS['transport_response']) of the effect and the anchor quantity it is read against. The kind
# 'transport_rate' holds two anchor quantities and is told apart by the effect's unit (the converter has converted it exactly).
TRANSPORT_QUANTITY_OF_KIND = {'transport_parameter': 'transport_km', 'electrical_conductance': 'unitary_conductance', 'charge_equivalent_rate': 'charge_rate',
                              'transport_rate_ratio': 'fold_over_control', 'substrate_response_ratio': 'fold_over_control'}   # EXPERT_REVIEW, owner to confirm
TRANSPORT_RATE_QUANTITY_OF_UNIT = {'s^-1': 'turnover', 'nmol/min/mg': 'normalized_rate'}   # EXPERT_REVIEW, owner to confirm
# The reverse, for a converter that selected a quantity with select_transport_effect and must name the record kind (transport_rate for the two rates).
TRANSPORT_KIND_OF_QUANTITY = {'transport_km': 'transport_parameter', 'turnover': 'transport_rate', 'unitary_conductance': 'electrical_conductance',
                              'charge_rate': 'charge_equivalent_rate', 'fold_over_control': 'transport_rate_ratio', 'normalized_rate': 'transport_rate'}   # EXPERT_REVIEW, owner to confirm

# ---------------------------------------------------------------------------------------------------------------
# (5g) COUPLING_STRENGTH_ANCHORS: the reaction_coupling class's gray-scale ends (DRAFT 2026-11-22, owner to confirm; every number
# below is EXPERT_REVIEW and every literature figure is from memory, to be verified). Anchors are per QUANTITY, not per experiment
# type: a coupling fraction means the same in every protocol. For both quantities LARGER is stronger (more of what was consumed
# ends in the claimed product); the position runs on the log10 scale from noise_end (strength 0) to strong_end (strength 1), as
# for the binding and activity anchors. They are the two ends of a gray scale, never thresholds. Both are read in the unit
# 'fraction' (mol of product over mol of the consumed partner, times the stated stoichiometric coefficient for the productive fraction).
# Reference points (from memory): cytochrome P450 monooxygenases with a non-native or poor substrate commonly couple only 1 to 30
# percent of the NAD(P)H consumed to product (the rest leaves as H2O2, superoxide or water; Guengerich 2018 and Denisov et al.
# 2005 Chem Rev 105:2253, from memory); the best-coupled systems, the native substrate of P450cam with camphor, are near 100
# percent; fatty-acid hydroxylation by P450 BM3 is near 60 to 90 percent (from memory).
# ---------------------------------------------------------------------------------------------------------------
COUPLING_STRENGTH_ANCHORS = {
    # productive fraction = stoichiometric coefficient x product per consumed partner, 0 to 1 by definition. noise_end: 1 percent, the
    # floor of nearly fully uncoupled turnover (and of background chemistry that makes a little product without the enzyme's
    # help). strong_end: 90 percent, the 'well coupled' end of the oxygenase literature.
    'productive_fraction': {'unit': 'fraction', 'noise_end': 0.01, 'strong_end': 0.9},    # EXPERT_REVIEW, owner to confirm
    # stoichiometric ratio = mol of product per mol of the consumed partner, with no coefficient applied (the paper does not state
    # the reaction's coefficient). noise_end: 1 percent, as above. strong_end: 1, one product per partner consumed (the usual
    # coefficient; a reaction that takes two partners per product, such as QueF with 2 NADPH, reads 0.5 at full coupling and sits
    # at p = 0.85 on this scale, a small loss, which is why a coefficient-free ratio ranks after the productive fraction).
    'stoichiometric_ratio': {'unit': 'fraction', 'noise_end': 0.01, 'strong_end': 1.0},   # EXPERT_REVIEW, owner to confirm
}
# Which stated quantity is the effect when a record states several: the best-determined first (DRAFT, owner to confirm). The
# productive fraction already carries the reaction's own coefficient, so it answers the claimed reaction; the bare ratio does not
# know the coefficient and is read as one product per partner.
COUPLING_EFFECT_ORDER = ('productive_fraction', 'stoichiometric_ratio')   # EXPERT_REVIEW, owner to confirm
# The record's quantity kind (QUANTITY_KINDS['reaction_coupling']) of the effect, and the anchor quantity it is read against.
# 'balance_residual' (an amount left unaccounted for) has no anchors: amounts have no common scale. A mass or electron balance
# is stated as the productive fraction (accounted for over consumed), and the residual amount goes in the 'attributed_signal' and
# 'total_signal' roles of the extraction.
COUPLING_QUANTITY_OF_KIND = {'productive_fraction': 'productive_fraction', 'stoichiometric_ratio': 'stoichiometric_ratio'}   # EXPERT_REVIEW, owner to confirm

# ---------------------------------------------------------------------------------------------------------------
# (5f) PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS: the product_distribution class's gray-scale ends (DRAFT 2026-11-22, owner to confirm;
# every number below is EXPERT_REVIEW and every literature figure is from memory, to be verified). The effect of a result of this
# class is the share of the CLAIMED product among the products of the reaction (a fraction, or a ratio of two products with the claimed
# product in the numerator), or where the equilibrium lies (the same two forms). For these quantities LARGER is stronger; the position
# runs on the log10 scale from noise_end (strength 0) to strong_end (strength 1), as for the binding and activity anchors. They are
# the two ends of a gray scale, never thresholds.
# noise_end of a fraction, 0.01: about the smallest minor component that area or integral percentages of HPLC, GC and NMR resolve
# and quantify without a dedicated trace method (from memory: the reporting limit of a mixture analysis is about 1 percent; below it
# a "product" is often an impurity, a carry-over or a spontaneous side reaction). strong_end of a fraction, 0.9: a claimed product that
# is nine tenths of what the reaction gives is the reaction's product, whatever the minor components are; beyond 0.9 a further share says
# more about selectivity than about whether the enzyme gives this product, and the claim names only the product.
# The ratio ends are the fraction ends carried through r = f / (1 - f), the ratio of the claimed product to the one other species:
# f = 0.01 -> r = 0.0101 (rounded to 0.01) and f = 0.9 -> r = 9. So the two ends are the same two points on both forms. BETWEEN the ends
# the curves differ (the fraction is read on log f, the ratio on log r = log of f / (1 - f)): a share of 0.5 gives strength about 0.95,
# the equal ratio 1 (the same share) about 0.76. Reported to the owner as an open question.
# The equilibrium quantities keep their own entries (same ends) so the owner can tune them apart: an equilibrium composition does not
# depend on the enzyme, so it shows where the reaction lies, not that this enzyme makes the product (the sheet criterion
# attribution_supported, with a no-enzyme control, carries that; it lowers the weight, not the direction).
PRODUCT_DISTRIBUTION_STRENGTH_ANCHORS = {
    'product_fraction': {'unit': 'fraction', 'noise_end': 0.01, 'strong_end': 0.9},                    # EXPERT_REVIEW, owner to confirm
    'product_fraction_ratio': {'unit': 'dimensionless', 'noise_end': 0.01, 'strong_end': 9.0},         # EXPERT_REVIEW, owner to confirm; claimed product in the numerator; r = f / (1 - f)
    'equilibrium_fraction': {'unit': 'fraction', 'noise_end': 0.01, 'strong_end': 0.9},                # EXPERT_REVIEW, owner to confirm; fraction of the claimed product at equilibrium
    'equilibrium_ratio': {'unit': 'dimensionless', 'noise_end': 0.01, 'strong_end': 9.0},              # EXPERT_REVIEW, owner to confirm; [claimed product] / [other species] at equilibrium (K for an isomerization)
}
# Which stated quantity is the effect when a record states several: the best-determined first (DRAFT, owner to confirm).
# product_fraction: the claimed product's own share with its stated denominator; it needs no choice of numerator or direction.
# product_fraction_ratio: the same measurement as a ratio of two products; the numerator must be the claimed product, so the direction
# of the ratio is one more thing to get right. equilibrium_fraction and equilibrium_ratio last: the composition at equilibrium is the
# same for any catalyst (or none), and the equilibrium criterion (reached from both sides, stable in time) must hold for it to mean anything.
PRODUCT_DISTRIBUTION_EFFECT_ORDER = ('product_fraction', 'product_fraction_ratio', 'equilibrium_fraction', 'equilibrium_ratio')

# ---------------------------------------------------------------------------------------------------------------
# (5e) ENDPOINT_STRENGTH_ANCHORS: the endpoint_conversion class's gray-scale ends (DRAFT 2026-11-22, owner to confirm; every number below is
# EXPERT_REVIEW and every literature statement is from memory, not verified). The class asks how much substrate was converted, or how much
# product there was, at an end point, and how long completion took: one time point or a yield, never a rate (rates are activity_rate's).
# Anchors are per QUANTITY, not per experiment type: a fraction converted, a completion time and an amount mean the same in every assay.
# The position runs on the log10 scale from noise_end (strength 0) to strong_end (strength 1), as for the binding and activity anchors.
# For the conversion quantities and the amount LARGER is stronger; for the completion time SMALLER is stronger (its noise_end is the larger
# number, so the same formula serves). They are the two ends of a gray scale, never thresholds. 'maximum' is a physical limit (a fraction
# cannot exceed 1), not a threshold.
# ---------------------------------------------------------------------------------------------------------------
ENDPOINT_STRENGTH_ANCHORS = {
    # fraction converted MINUS the paper's own control (no-enzyme, inactive-enzyme or zero-time) in the same units. noise_end 0.02: integration, pipetting
    # and control-subtraction noise of HPLC, NMR and gel densitometry is of the order of a few percent (from memory: quantitation limits near 1-5 percent
    # of the substrate). strong_end 0.9: near-complete conversion; beyond it the product is limited by what the method can tell from residual substrate.
    'conversion_difference': {'unit': 'fraction', 'noise_end': 0.02, 'strong_end': 0.9, 'maximum': 1.0},   # EXPERT_REVIEW, owner to confirm
    # fraction converted as stated, not corrected by a control. noise_end 0.05: higher than the net one because it still holds spontaneous conversion and
    # background (from memory: uncatalysed reactions and autohydrolysis commonly give a few percent over hours). strong_end 0.9 as above.
    'conversion_fraction': {'unit': 'fraction', 'noise_end': 0.05, 'strong_end': 0.9, 'maximum': 1.0},     # EXPERT_REVIEW, owner to confirm
    # completion time of the test over the completion time of the paper's own reference (control, earlier preparation, wild type): >1 means the test
    # completes sooner. noise_end 1: no faster than the reference. strong_end 1e3: three orders of speed-up, the practical range of a time comparison
    # (the HFP isomerisation case of the owner's old inventory was a ratio above 108, from the old report, not verified).
    'completion_time_ratio': {'unit': 'dimensionless', 'noise_end': 1.0, 'strong_end': 1e3},               # EXPERT_REVIEW, owner to confirm
    # time to reach the paper's stated completion or equilibrium, in minutes; SMALLER is stronger. noise_end 1440 (24 h): a reaction that needs a day
    # is hard to tell from slow background chemistry and enzyme decay at the usual temperatures. strong_end 1: completion within a minute is the fastest
    # an ordinary sampled assay can resolve (manual quench and sampling; from memory).
    'completion_time': {'unit': 'min', 'noise_end': 1440.0, 'strong_end': 1.0},                            # EXPERT_REVIEW, owner to confirm
    # product amount at the end point as a concentration in micromolar. Weakest scale: it depends on how much substrate and enzyme the paper loaded.
    # noise_end 1 uM: about the quantitation floor of UV-HPLC and colorimetric product assays (from memory). strong_end 1e3 uM (1 mM): a product at
    # millimolar level is a substantial conversion of a usual assay substrate (about 1 to 10 mM).
    'endpoint_amount': {'unit': 'uM', 'noise_end': 1.0, 'strong_end': 1e3},                                # EXPERT_REVIEW, owner to confirm
}
# Which stated quantity is the effect when a record states several: the best-determined first (DRAFT, owner to confirm). A fraction converted net
# of the paper's own control isolates the enzyme's contribution from spontaneous conversion and is dimensionless; the raw fraction is still
# relative to the substrate loaded but holds the background; a time ratio is relative to the paper's own reference but needs the same endpoint
# definition on both sides; a bare completion time depends on the enzyme and substrate loaded; an absolute amount depends on the loading and has no
# natural scale of its own.
ENDPOINT_EFFECT_ORDER = ('conversion_difference', 'conversion_fraction', 'completion_time_ratio', 'completion_time', 'endpoint_amount')   # EXPERT_REVIEW, owner to confirm
# The record's quantity kind (QUANTITY_KINDS['endpoint_conversion']) of the effect, and the anchor quantity it is read against.
ENDPOINT_QUANTITY_OF_KIND = {kind: kind for kind in ENDPOINT_EFFECT_ORDER}   # EXPERT_REVIEW, owner to confirm

# ---------------------------------------------------------------------------------------------------------------
# (4) Field lists. Each field: kind, plus lo/hi for numbers, vocab for vocabularies, nullable.
#   kinds: 'vocab', 'number' (finite float or int, not bool), 'count' (int >= 0), 'ref' (a record reference: no
#   whitespace, <= 200 chars; never prose), 'map' (a controlled mapping, checked by its own rule), 'bool' (true or
#   false), 'refs' (a list of distinct record references; lo = the least length, default 1), 'unit' (a unit spelling,
#   UNIT_PATTERN, defined just below).
# ---------------------------------------------------------------------------------------------------------------
REF_PATTERN = re.compile(r'^[A-Za-z0-9_.:/#@+\-]{1,200}$')
# A UNIT of a stated value: a spelling from a record form's fixed UNITS vocabulary. It is short and never prose, but it
# is not a reference: the forms write powers and products as papers do ('s^-1', 'M^-1 s^-1', 'RU^2'), so a unit may hold
# '^' and '%' and at most three space-separated parts.
UNIT_PATTERN = re.compile(r'^[A-Za-z0-9_.:/#@+\-^%]{1,24}( [A-Za-z0-9_.:/#@+\-^%]{1,24}){0,2}$')

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
    'target_id': _f('name', nullable=True),   # OWNER_DECISION 18: the experiment's target (normalized); null only when the experiment states none (target_match not_stated); required non-null when the result is on the row
    'experiment_type': _f('vocab', vocab=EXPERIMENT_TYPES),
    'sheet': _f('vocab', vocab=CLASSES),
    'target_match': _f('vocab', vocab=TARGET_MATCH),
    'relevance': _f('vocab', vocab=RELEVANCE),
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
    'effect_unit': _f('unit', nullable=True, required=False),     # unit of measured_effect (required when it is given); a unit spelling (UNIT_PATTERN), since an activity_rate unit holds '^' ('s^-1', 'M^-1s^-1')
    'analyte_preparation_ref': _f('ref', nullable=True, required=False),      # ROW_DEPENDENCE_KEYS; null = unknown = dependent
    'immobilized_preparation_ref': _f('ref', nullable=True, required=False),
    'surface_ref': _f('ref', nullable=True, required=False),
    'direction_field_support': _f('vocab', vocab=SUPPORT_CLASSES, nullable=True, required=False),   # OWNER_DECISION 17; required when direction is known
    'statement': _f('vocab', vocab=QUALITATIVE_STATEMENT, nullable=True, required=False),   # the qualitative statement of the experiment
    'statement_support_refs': _f('refs', nullable=True, required=False),   # refs of the stated support of the statement; null when no statement
    # The identification of the assayed protein (2026-11-21): the reference record and sequence the paper's identity resolved to,
    # how it resolved, how many records the name matched and the closeness of its sequence to the target's (pairwise BLAST).
    'subject_record_ref': _f('ref', nullable=True),                 # null when unresolved
    'subject_sequence_ref': _f('ref', nullable=True),               # null when unresolved or the record holds no sequence
    'subject_resolution': _f('vocab', vocab=SUBJECT_RESOLUTION),
    'subject_match_count': _f('count'),                             # records the stated identity matched (0 when unresolved)
    'subject_closeness': _f('number', lo=0.0, hi=1.0, nullable=True),   # null when there is no sequence to compare
    'comparison_ref': _f('ref', nullable=True),                     # the stored graded BLAST result; null exactly when subject_closeness is null
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
    # The identification of the row's BEST identified member result (the greatest identified_closeness; ties by the least result_ref);
    # row_resolution (the credit) scales by identified_closeness, so credit never rises for a protein that cannot be identified.
    'identified_closeness': _f('number', lo=0.0, hi=1.0),
    'subject_record_ref': _f('ref', nullable=True),
    'subject_sequence_ref': _f('ref', nullable=True),
    'subject_resolution': _f('vocab', vocab=SUBJECT_RESOLUTION),
    'subject_match_count': _f('count'),
    'subject_closeness': _f('number', lo=0.0, hi=1.0, nullable=True),
    'comparison_ref': _f('ref', nullable=True),
}
ROW_CALLER_FIELDS = ('weight', 'resolution', 'credit')           # filled by complete_row, never by merge_row
PARTIAL_ROW_FIELDS = {name: spec for name, spec in ROW_FIELDS.items() if name not in ROW_CALLER_FIELDS}

# The persistent subscoring sheet STATE of one (sheet, assertion_ref): what merge_row_state returns and takes back as its
# optional last argument. 'row' is the PARTIAL row of merge_row_state (the caller may store the completed row instead:
# both are accepted); 'member_results' are the converted results (on the row) the row was built from, ordered by
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
# Which database a molecule's identifier belongs to, as the passage says it (the subject_database / partner_database vocabulary;
# owner goal 2026-11-21: find the exact sequence behind the experiment). gene_name_only: the passage gives a name and no identifier;
# locus_tag: a genome locus tag such as CC_1319; other: an identifier of a database not listed.
SUBJECT_DATABASES = ('uniprot', 'genbank', 'refseq', 'pdb', 'bvbrc', 'locus_tag', 'gene_name_only', 'other')
# The five identity fields that say WHICH sequence a molecule is, for the subject (the target) and for the partner; every one is
# stated only with a quote, like the other identity fields.
SUBJECT_TEXT_FIELDS = ('subject_database_id', 'subject_organism', 'subject_residue_range', 'subject_mutations')
PARTNER_TEXT_FIELDS = tuple('partner_' + name[len('subject_'):] for name in SUBJECT_TEXT_FIELDS)
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
    'target_id': _f('name', nullable=True),                                       # OWNER_DECISION 18: the molecule the assay is about (annotation ID or normalized name); the one identity field the target match requires
    'partner_id': _f('name', nullable=True),                                      # OPTIONAL: the other molecule the target is tested against (ligand, binding partner)
    'partner_role': _f('vocab', vocab=ROLE, nullable=True),                       # optional: the role of the partner
    # Which sequence the molecule is (owner goal 2026-11-21): the identifier exactly as the passage writes it, the database it belongs
    # to, the organism and strain as written (at most NAME_MAX_WORDS words), the residue range and the mutations as written.
    # Optional; a name alone is not a database id (that is gene_name_only with no id). Code resolves them to a record and sequence.
    'subject_database_id': _f('name', nullable=True),
    'subject_database': _f('vocab', vocab=SUBJECT_DATABASES, nullable=True),
    'subject_organism': _f('name', nullable=True),
    'subject_residue_range': _f('name', nullable=True),
    'subject_mutations': _f('name', nullable=True),
    'partner_database_id': _f('name', nullable=True),
    'partner_database': _f('vocab', vocab=SUBJECT_DATABASES, nullable=True),
    'partner_organism': _f('name', nullable=True),
    'partner_residue_range': _f('name', nullable=True),
    'partner_mutations': _f('name', nullable=True),
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

# OWNER_DECISION 18: how two target or partner identities are made stored-comparable: casefold, then collapse every run of
# whitespace to one space (and strip): normalize_identity_ref, the form a record stores. A molecule NAME is compared (identity_compare,
# the grader's identity keys, target_match, relevance, the row and main-sheet target tests) and looked up in the protein database in
# its COMPARABLE form, comparable_identity_name: the normalized name without a fused tag or label at its start or end.
IDENTITY_REF_NORMALIZATION = ('casefold', 'collapse_whitespace', 'unicode_dashes_to_hyphen')
IDENTITY_NAME_COMPARISON = IDENTITY_REF_NORMALIZATION + ('fusion_tags_removed_from_start_and_end',)   # the comparable form of a name: comparable_identity_name
# The dash characters papers use inside a molecule name (hyphen U+2010, non-breaking hyphen, figure dash, en dash, em dash,
# horizontal bar, minus sign); all compare as the ASCII hyphen so 'PPARγ‐DL' and 'PPARγ-DL' are one molecule.
_UNICODE_DASHES = dict.fromkeys(map(ord, '‐‑‒–—―−'), '-')
IDENTITY_NORMALIZED_REF_FIELDS = ('target_id', 'partner_id', *SUBJECT_TEXT_FIELDS, *PARTNER_TEXT_FIELDS)   # the identity fields compared after IDENTITY_REF_NORMALIZATION
# The identity fields a grader states per field (state_grader_fields): the normalized ones and the two database vocabularies.
IDENTITY_STATED_FIELDS = (*IDENTITY_NORMALIZED_REF_FIELDS, 'subject_database', 'partner_database')


def normalize_identity_ref(value):
    """A target or partner identity in its comparable form: casefolded, whitespace collapsed (IDENTITY_REF_NORMALIZATION)."""
    if not isinstance(value, str):
        raise ValueError(f'an identity reference must be a string: {value!r}')
    return ' '.join(value.translate(_UNICODE_DASHES).split()).casefold()


# The tokens a protein name carries as a fused tag or label, not as part of the protein's own name (casefolded). Only tokens that are
# not themselves ordinary protein names belong here: fluorescent proteins, self-labelling tags, affinity tags, dye labels, and the
# words 'labeled'/'labelled' after a dye. HA, Myc and V5 are left out: they are proteins too (a name 'HA-X' could be hemagglutinin).
FUSION_TAG_TOKENS = frozenset({   # EXPERT_REVIEW
    'gfp', 'egfp', 'sfgfp', 'yfp', 'eyfp', 'cfp', 'ecfp', 'bfp', 'ebfp', 'rfp', 'mcherry', 'mchy', 'pamcherry', 'mkate2', 'mscarlet',
    'dendra2', 'venus', 'mvenus', 'mneongreen', 'tdtomato', 'meos2', 'meos3.2', 'citrine', 'cerulean', 'mcitrine', 'mcerulean',
    'mturquoise', 'mturquoise2', 'dsred', 'mruby', 'pagfp', 'pamcherry1',
    'halo', 'halotag', 'snap', 'snaptag', 'clip',
    'his', 'his6', '6his', '6xhis', 'his8', 'his10', '10xhis', 'gst', 'mbp', 'sumo', 'strep', 'strepii', 'twinstrep', 'flag', '3xflag',
    'tap', 'avi',
    'af488', 'af555', 'af647', 'alexa488', 'alexa647', 'cy3', 'cy5', 'atto488', 'atto647n', 'fitc', 'tmr', 'labeled', 'labelled'})


def comparable_identity_name(value):
    """A molecule name in its comparable form: normalize_identity_ref, then every FUSION_TAG_TOKENS token removed from the START
    and the END of the name (split on hyphens and whitespace, repeated), together with a pure number left at the end directly
    after a removed tag ('ctra-eyfp-14' -> 'ctra'). Tokens in the middle are never touched ('bcl-2', 'c-myc', 'il-6' are
    unchanged); a name that is nothing but tags, or tags and numbers ('gfp', 'gst', 'snap-25'), is kept whole. What remains is
    joined with the separators the name was written with. A name without a tag comes out exactly as normalize_identity_ref gives it."""
    name = normalize_identity_ref(value)
    pieces = re.split(r'([-\s]+)', name)
    words, separators = pieces[0::2], pieces[1::2]
    start, end = 0, len(words)
    while True:
        if start < end and words[start] in FUSION_TAG_TOKENS:
            start += 1
        elif start < end and words[end - 1] in FUSION_TAG_TOKENS:
            end -= 1
        elif end - 2 > start and words[end - 1].isdigit() and words[end - 2] in FUSION_TAG_TOKENS:
            end -= 2
        else:
            break
    if start >= end or all(word.isdigit() for word in words[start:end]):
        return name
    return ''.join(word + (separators[index] if index < end - 1 else '') for index, word in zip(range(start, end), words[start:end]))

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
    'target_match': {
        'module': 'literature_target',
        'args': ('record', 'claim', 'subject_closeness'),
        'returns': {'target_match': 'TARGET_MATCH', 'reasons': 'list of controlled reason codes (not prose)'},
        'target_note': 'OWNER_DECISION 18: a converted result carries the experiment target_id (non-null when on the row); a row, main row, axis output and feature record carry the target_id of the score (equal to the claim subject_id)',
        'note': 'code, not the model; who was measured. record carries experiment_type, target_id and partner_id; not_stated when no target is stated (reason target_not_stated); when the assayed protein was identified (closeness not null) the sequence decides: same at the exact sequence (EXACT_SEQUENCE_CLOSENESS), related for a related protein; when it was not identified the names decide: same when the normalized target_id equals the claim subject_id (or by the symmetric partner route), else different',
    },
    'relevance': {
        'module': 'literature_relevance',
        'args': ('record', 'claim'),
        'returns': {'relevance': 'RELEVANCE', 'reasons': 'list of controlled reason codes (not prose)'},
        'note': 'code, not the model; what was asked. record carries experiment_type, target_id, partner_id, statement and effect_measured; irrelevant when the type cannot test the predicate, when the partners differ, or when the claim names a partner and the experiment neither names one nor measured an interaction; unresolved when it measured an interaction but names no partner; relevant otherwise. Irrelevant results stay off the row and are never scored',
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
        'returns': '{(sheet, assertion_ref): [results on the row]}',
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
    18: ('target molecule (OWNER RULING, 2026-11-20)', "every experimental grader has a target molecule: target_id (the molecule the assay is about), optional partner_id and partner_role replace partner_a_*/partner_b_*; the target match requires the target: no stated target gives target_match not_stated (target_not_stated), no score, credit as the resolution says, and no 'target known' question is added; the target is the same when the normalized target_id equals the claim subject_id (or the sequence decides, see target_match), different when it differs; the partner is judged by relevance, not by the target match (2026-11-21, owner: 'Use target and relevance. It does make sense you need both': target asks who was measured, relevance asks what was asked; an irrelevant result stays off the row and is never scored, an unresolved one measured an interaction but names no partner and is treated on the row as before); a result of a SYMMETRIC predicate (SYMMETRIC_PREDICATES, binds) whose target is the claim's partner and whose partner is the claim's subject is the same target and relevant (reason partner_route); the row and score still belong to the claim's subject; the target applies at every level: a converted result, every subscoring row, every main row (placeholders too), the axis score channel and the investigation_finding features carry the target_id the score is about (the scoring sheet IS the annotation score, one per candidate per target; credit stays a separate quantity); target_id and partner_id are identity-bearing, compared by equality after casefold and whitespace collapse, missing skipped, agreeing is a positive tie; every identity number is stated by the leaf form in the field's canonical unit (IDENTITY_FIELDS, IDENTITY_FEATURES, POSITIVE_TIE_FEATURES, IDENTITY_REF_NORMALIZATION)"),
    17: ('effect support (revision of 2026-11-20; default)', 'a converted result carries direction_field_support, copied from the support class of the field that fixes the direction: the KD operand for a quantitative result, the field(s) the statement derives from for a qualitative one, the weakest if several; effect_support = SUPPORT_FACTORS[direction_field_support] (EFFECT_SUPPORT_FIELD, SUPPORT_WEAKEST_ORDER, RESULT_FIELDS.direction_field_support)'),
    19: ('a result stated in words alone is weaker than a measured one (owner, 2026-11-22)', 'for a type that can report a measured effect, a stated detection or non-detection without a number counts QUALITATIVE_LOG_RATIO[type] * STATED_ONLY_STRENGTH (stated_strength); a type whose own result is a yes/no observation keeps its full value'),
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
    elif kind == 'unit':
        if not isinstance(value, str) or not UNIT_PATTERN.match(value):
            raise ValueError(f'{owner}.{name} must be a unit spelling (UNIT_PATTERN), not prose: {value!r}')
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
    or breaks the direction rules: unknown (and any result not on the row) means null log_ratio and effect_support;
    neutral means log_ratio exactly 0.0. Cross-field rules of the revision of 2026-11-20: an effect variance needs an
    effect, an effect needs its unit; a statement refs list needs a statement; a qualitative result (no measured_effect,
    on the row, a statement given) has the direction its statement states (detected supports, not detected opposes,
    not stated unknown); direction_field_support is required when the direction is known and null (or absent) when it is
    unknown (OWNER_DECISION 17); log_ratio never depends on the criteria (OWNER_DECISION 15)."""
    _validate('result', result, RESULT_FIELDS)
    if CLASS_OF_EXPERIMENT_TYPE.get(result['experiment_type']) != result['sheet']:
        raise ValueError('result.sheet is not the class of result.experiment_type')
    if not on_row(result) and result['direction'] != 'unknown':
        raise ValueError("result.direction must be 'unknown' unless the result is on the row (target_match same or related, relevance relevant or unresolved)")
    if on_row(result) and result['target_id'] is None:
        raise ValueError('result.target_id is required when the result is on the row (OWNER_DECISION 18)')
    if result['subject_resolution'] == 'unresolved':
        if result['subject_record_ref'] is not None or result['subject_sequence_ref'] is not None or result['subject_closeness'] is not None:
            raise ValueError("an unresolved subject has no record, sequence or closeness")
    elif result['subject_match_count'] < 1 or result['subject_record_ref'] is None:
        raise ValueError('a resolved subject has a record and matched at least one record')
    if (result['subject_closeness'] is None) != (result['comparison_ref'] is None):
        raise ValueError('result.comparison_ref is given exactly when result.subject_closeness is')
    if result['subject_closeness'] is not None and result['subject_sequence_ref'] is None:
        raise ValueError('result.subject_closeness needs result.subject_sequence_ref')
    if result.get('effect_variance') is not None and result.get('measured_effect') is None:
        raise ValueError('result.effect_variance is given without result.measured_effect')
    if result.get('measured_effect') is not None and result.get('effect_unit') is None:
        raise ValueError('result.effect_unit is required when result.measured_effect is given')
    if result.get('statement') is None and result.get('statement_support_refs') is not None:
        raise ValueError('result.statement_support_refs is given without result.statement')
    statement = result.get('statement')
    if statement is not None and on_row(result) and result.get('measured_effect') is None:
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
    row, whose member results are not valid converted results on the row for the row's (sheet, assertion_ref),
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
        if not on_row(result):
            raise ValueError('state.member_results holds a result that is not on the row (target_match same or related, relevance relevant or unresolved)')
        if result['sheet'] != row['sheet'] or result['assertion_ref'] != row['assertion_ref']:
            raise ValueError('state.member_results holds a result of another sheet or candidate')
        if comparable_identity_name(result['target_id']) != comparable_identity_name(row['target_id']):
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
    (conflicting true). Each value is {value: a number, string or boolean, unit: a unit spelling (UNIT_PATTERN) or null, spans: [[start,
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
            if value['unit'] is not None and (not isinstance(value['unit'], str) or not UNIT_PATTERN.match(value['unit'])):
                raise ValueError(f'{owner}.values item unit must be a unit spelling (UNIT_PATTERN) or null: {value["unit"]!r}')
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
