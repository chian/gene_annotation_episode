"""Chunks of text for the SPA (scintillation proximity assay) extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree and micro signs) so byte
offsets differ from character offsets.

``REAL`` is real: the Methods paragraph on the pharmacological SPA experiments of 'Exploring the K+ binding site and its coupling to
transport in the neurotransmitter:sodium symporter LeuT' (eLife 2024, doi 10.7554/eLife.87985, PMC10945697, PMID 38271216, open access,
CC0 public domain dedication), as the publisher's XML gives the paragraph's own text with the markup (superscripts, italics,
subscripts) removed: the paragraph is whole (one paragraph in the XML, nothing removed), 2519 characters. It says how purified LeuT
variants were studied by SPA: leucine affinities by saturation binding of [3H]leucine (25 Ci/mmol) with non-specific binding corrected
for by 100 uM unlabelled leucine, alanine and leucine affinities by competitive displacement of a fixed concentration of [3H]leucine,
YSi-Cu His-tag SPA beads (PerkinElmer) at 1.25 or 1.6 mg/ml with 0.3, 1.5 or 3 ug/ml protein, [3H]leucine at 120, 1200 or 200 nM of
25, 4 or 20 Ci/mmol, ligand depletion avoided by a 20-fold molar excess of [3H]leucine over LeuT, about 16 hours at 4 degrees C and
counting on a 2450 MicroBeta2 counter in SPA mode. It gives no measured KD, Bmax, IC50 or Ki value, no affinity of the unlabelled leucine, no Hill slope, no fit model, no
bead-only control, no association half-time, no equilibrium time course, no settling time and no replicate count.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_extraction import (
    ASSAY_FORMAT, BEAD_TYPE, CAPTURE, COUNTER, FIT_MODEL, ISOTOPE, PREPARATION_TYPE, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_record import UNITS

PAPER_ID = 'PMC10945697'
REAL = (
    'Pharmacological studies were conducted on purified LeuT variants by virtue of the SPA. Leucine affinities for WT LeuT and mutants displaying WT substrate affinities (A22V, A22S) were determined by saturation binding of [3H]leucine (25 Ci/mmol) (PerkinElmer), with unspecific binding corrected for by the addition of 100 µM unlabeled leucine. '
    'Alanine and leucine affinities for the remaining LeuT variants were determined by the ability of increasing concentrations of unlabeled alanine or leucine, respectively, to competitively displace a fixed concentration of [3H]leucine. '
    'Assayed in a 96-well plate (Corning), LeuT was mixed with Yttrium Silicate Copper (YSi-Cu) His-tag SPA beads (PerkinElmer) and [3H]leucine in binding buffer (200 mM NaCl, 20 mM Tris [pH 8], 20% [vol/vol] glycerol, 0.05% [wt/vol] DDM, and 100 µM TCEP). '
    'The following conditions were applied for the mutants tested: WT, K398C, A22V, A22S: 0.3 µg/ml protein, 1.25 mg/ml YSi-Cu His-tag SPA beads, 120 nM [3H]leucine (25 Ci/mmol); N27Q, N286Q: 3 µg/ml protein, 1.6 mg/ml YSi-Cu His-tag SPA beads, 1200 nM [3H]leucine (4 Ci/mmol); E290Q: 1.5 µg/ml protein, 1.6 mg/ml YSi-Cu His-tag SPA beads, 200 nM [3H]leucine (20 Ci/mmol). '
    'The Na+ dependency on [3H]leucine binding was determined by mixing LeuT, YSi-Cu His-tag SPA beads (in equivalent concentrations as above) and a fixed concentration of [3H]leucine (10× Kd, as determined in 200 mM NaCl) in binding buffer supplemented with increasing concentrations of Na+. '
    'The specific activity of [3H]leucine was kept approximately inversely proportional to the concentration of [3H]leucine and protein used. '
    'This experiment was repeated in the presence of 200 and 800 mM K+. '
    'The K+-dependent inhibition of Na+-mediated [3H]leucine binding was assayed by subjecting LeuT mutants (double the concentration as above) to increasing concentrations of K+ (0–1600 mM) in the presence of Na+ equivalent to the EC50 determined with 10× Kd of [3H]leucine. '
    'The unspecific binding of [3H]leucine was determined upon addition of 100 (WT, A22V, A22S) or 300 µM (N27Q, N286Q) of unlabeled leucine. '
    'Ionic strengths were preserved by substituting Na+ and K+ for Ch+. '
    'For competition binding and ion-dependent [3H]leucine binding experiments, ligand depletion was avoided by maintaining ≥20-fold molar excess of [3H]leucine relative to LeuT. '
    'Sealed plates were incubated for ~16 hr at 4°C with gentle agitation and counts per minute (c.p.m.) were recorded on a 2450 MicroBeta2 microplate counter (PerkinElmer) in ‘SPA’ mode.')

SYNTHETIC = (
    'Binding of [3H]DX-17 to the His-tagged DX receptor was measured by scintillation proximity assay in a purified protein preparation at 25 °C. '
    'The assay was about the DX receptor and its ligand DX-17. '
    '[3H]DX-17 had a specific activity of 85 Ci/mmol. Each well held 2 mg of yttrium silicate (YSi) beads at 20 mg/mL, which captured the receptor through a '
    'nickel chelate binding its His tag, and 0.5 µg of receptor protein. The main experiment was a saturation experiment, in which the receptor was incubated with [3H]DX-17 at 10 '
    'concentrations of 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6 and 51.2 nM for 120 min. The series ran from 0.1 nM to 51.2 nM. '
    'Non-specific binding was determined with 1000 nM unlabelled DX-17, a 500-fold excess over the Kd, and was subtracted from the total binding to give the '
    'specific binding; at the highest concentration it was 25% of the total binding. The unlabelled ligand was the unlabelled form of [3H]DX-17 itself, '
    'with a Kd for the receptor of 2.2 nM. A control without the captured receptor (beads and [3H]DX-17 only) was '
    'measured and gave 8% of the total signal. The non-proximity signal of the free radioligand was checked and was small. '
    'No separation or wash step was done: the plates were counted with the free radioligand still in the wells. Counting was on a MicroBeta counter with a '
    'counting efficiency of 32%, after the beads had settled for 30 min. The settling time was fixed for all plates, so the settling of the beads was controlled. '
    'The quench of the counts was corrected using a quench curve of the beads. The radiochemical purity of [3H]DX-17 was checked by HPLC before each '
    'experiment. The binding was at equilibrium because an association time course reached a plateau within 120 min, with a half-time of 4 min. Only 6% of the added radioligand was '
    'bound, so depletion of the free radioligand was avoided. The saturation data were fitted by non-linear regression with a one-site binding model, which '
    'gave a KD = 2.0 nM (standard error 0.2 nM), a Bmax of 1200 fmol/mg protein and a Hill slope of 1.0. In a competition experiment 1 nM [3H]DX-17 was '
    'displaced by an unlabelled ligand, which gave an IC50 of 7.5 nM; the Ki = 5.0 nM (standard error 0.3 nM) was calculated with the Cheng-Prusoff equation '
    'using the KD of [3H]DX-17 on the same receptor. Each condition was measured in 3 wells, and 3 independent experiments were done on separate days with '
    'fresh receptor. The affinity was also measured by surface plasmon resonance.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (2.0, 'nM', 'a KD = 2.0 nM'),
    'bmax': (1200, 'fmol/mg', 'a Bmax of 1200 fmol/mg protein'),
    'ki': (5.0, 'nM', 'the Ki = 5.0 nM'),
    'ic50': (7.5, 'nM', 'an IC50 of 7.5 nM'),
    'hill_slope': (1.0, 'ratio', 'a Hill slope of 1.0'),
    'kd_spread': (0.2, 'nM', 'standard error 0.2 nM'),
    'ki_spread': (0.3, 'nM', 'standard error 0.3 nM'),
    'specific_activity': (85, 'Ci/mmol', 'a specific activity of 85 Ci/mmol'),
    'radioligand_concentration': (1, 'nM', '1 nM [3H]DX-17 was displaced'),
    'radioligand_range_lowest': (0.1, 'nM', 'ran from 0.1 nM'),
    'radioligand_range_highest': (51.2, 'nM', 'to 51.2 nM'),
    'bead_amount': (2, 'mg', 'Each well held 2 mg of yttrium silicate (YSi) beads'),
    'bead_concentration': (20, 'mg/mL', 'at 20 mg/mL'),
    'receptor_amount': (0.5, 'ug', '0.5 µg of receptor protein'),
    'percent_bound': (6, 'percent', 'Only 6% of the added radioligand was bound'),
    'nonspecific_fraction': (25, 'percent', 'it was 25% of the total binding'),
    'nonspecific_ligand_concentration': (1000, 'nM', '1000 nM unlabelled DX-17'),
    'nonspecific_ligand_affinity': (2.2, 'nM', 'a Kd for the receptor of 2.2 nM'),
    'nonspecific_excess': (500, 'ratio', 'a 500-fold excess over the Kd'),
    'bead_only_fraction': (8, 'percent', 'gave 8% of the total signal'),
    'counting_efficiency': (32, 'percent', 'a counting efficiency of 32%'),
    'incubation_time': (120, 'min', 'for 120 min'),
    'association_half_time': (4, 'min', 'with a half-time of 4 min'),
    'settling_time': (30, 'min', 'settled for 30 min'),
    'temperature': (25, 'C', 'at 25 °C'),
    'titration_point_count': (10, 'count', 'at 10 concentrations'),
    'technical_replicate_count': (3, 'count', 'measured in 3 wells'),
    'replicate_count': (3, 'count', '3 independent experiments'),
    SERIES: ([0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2], 'nM', '0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6 and 51.2 nM'),
    ASSAY_FORMAT: ('saturation', None, 'The main experiment was a saturation experiment'),
    ISOTOPE: ('tritium', None, 'Binding of [3H]DX-17 to the His-tagged DX receptor'),
    BEAD_TYPE: ('ysi', None, 'yttrium silicate (YSi) beads'),
    CAPTURE: ('metal_chelate', None, 'captured the receptor through a nickel chelate binding its His tag'),
    PREPARATION_TYPE: ('purified_protein', None, 'in a purified protein preparation'),
    COUNTER: ('microbeta', None, 'on a MicroBeta counter'),
    SPREAD_KIND: ('standard_error', None, 'standard error 0.2 nM'),
    FIT_MODEL: ('one_site', None, 'with a one-site binding model'),
    'homogeneous_no_wash_format': ('yes', None, 'No separation or wash step was done'),
    'nonspecific_binding_determined': ('yes', None, 'Non-specific binding was determined with 1000 nM unlabelled DX-17'),
    'nonspecific_ligand_is_radioligand': ('yes', None, 'the unlabelled form of [3H]DX-17 itself'),
    'nonproximity_signal_checked': ('yes', None, 'The non-proximity signal of the free radioligand was checked and was small'),
    'bead_only_control_done': ('yes', None, 'A control without the captured receptor (beads and [3H]DX-17 only) was measured'),
    'equilibrium_reached': ('yes', None, 'The binding was at equilibrium because an association time course reached a plateau within 120 min'),
    'ligand_depletion_checked': ('yes', None, 'so depletion of the free radioligand was avoided'),
    'quench_interference_checked': ('yes', None, 'The quench of the counts was corrected using a quench curve'),
    'bead_settling_controlled': ('yes', None, 'so the settling of the beads was controlled'),
    'radioligand_purity_checked': ('yes', None, 'The radiochemical purity of [3H]DX-17 was checked by HPLC'),
    'nonlinear_fit_used': ('yes', None, 'fitted by non-linear regression'),
    'cheng_prusoff_applied_with_own_kd': ('yes', None, 'calculated with the Cheng-Prusoff equation using the KD of [3H]DX-17 on the same receptor'),
    'independent_experiments': ('yes', None, '3 independent experiments were done on separate days'),
    'single_estimate_method': ('no', None, 'also measured by surface plasmon resonance'),
}

# field -> (value, unit, quote) for the real passage: what a careful reader may state from it about the experiments it describes, with the
# quote that says it. The real paragraph gives several values for some fields (one per LeuT variant); the value given here is the one of the
# wild-type saturation experiment or the first condition listed.
REAL_STATED = {
    ISOTOPE: ('tritium', None, 'saturation binding of [3H]leucine'),
    'specific_activity': (25, 'Ci/mmol', 'saturation binding of [3H]leucine (25 Ci/mmol)'),
    BEAD_TYPE: ('ysi', None, 'Yttrium Silicate Copper (YSi-Cu) His-tag SPA beads'),
    CAPTURE: ('metal_chelate', None, 'Yttrium Silicate Copper (YSi-Cu) His-tag SPA beads'),
    PREPARATION_TYPE: ('purified_protein', None, 'Pharmacological studies were conducted on purified LeuT variants'),
    COUNTER: ('microbeta', None, 'on a 2450 MicroBeta2 microplate counter'),
    'bead_concentration': (1.25, 'mg/mL', '1.25 mg/ml YSi-Cu His-tag SPA beads'),
    'nonspecific_ligand_concentration': (100, 'uM', 'addition of 100 µM unlabeled leucine'),
    'incubation_time': (16, 'h', 'incubated for ~16 hr'),
    'temperature': (4, 'C', 'at 4°C with gentle agitation'),
    'ligand_depletion_checked': ('yes', None, 'ligand depletion was avoided by maintaining ≥20-fold molar excess of [3H]leucine relative to LeuT'),
    'nonspecific_ligand_is_radioligand': ('yes', None, 'The unspecific binding of [3H]leucine was determined upon addition of 100 (WT, A22V, A22S) or 300 µM (N27Q, N286Q) of unlabeled leucine'),
    'nonspecific_binding_determined': ('yes', None, 'with unspecific binding corrected for by the addition of 100 µM unlabeled leucine'),
}
# The allowed set of the real model run: field -> every (value, unit) the paragraph clearly states for it. Some fields hold more than one,
# because the paragraph gives one value per LeuT variant (specific activity 25, 4 and 20 Ci/mmol; beads 1.25 and 1.6 mg/ml; the excess unlabelled
# leucine 100 and 300 uM) or the time in other units (about 16 hr is 960 min). Not allowed, because the paragraph does not state them by the
# field's general meaning: the single competition radioligand concentration (120, 1200 and 200 nM are given per variant and the paragraph does
# not say which of them is the fixed competition concentration), the assay format (saturation and competition are both described), the amount
# of protein or beads per well (only concentrations in ug/ml and mg/ml are given), a no-wash format (SPA is named, no wash is not said), the
# KD (a '10x Kd' is a multiple, not a value), equilibrium (an incubation of 16 hr is not a statement that equilibrium was reached), and the
# fit model, Hill slope, replicates, settling, quench and bead-only control (not mentioned).
REAL_ALLOWED = {
    ISOTOPE: {('tritium', None)},
    'specific_activity': {(25, 'Ci/mmol'), (4, 'Ci/mmol'), (20, 'Ci/mmol')},
    ASSAY_FORMAT: {('saturation', None)},      # "determined by saturation binding of [3H]leucine": stated by the paragraph (the model's quote), added after the real run
    BEAD_TYPE: {('ysi', None)},
    CAPTURE: {('metal_chelate', None)},
    PREPARATION_TYPE: {('purified_protein', None)},
    COUNTER: {('microbeta', None)},
    'bead_concentration': {(1.25, 'mg/mL'), (1.6, 'mg/mL')},
    'nonspecific_ligand_concentration': {(100, 'uM'), (300, 'uM')},
    'incubation_time': {(16, 'h'), (960, 'min')},
    'temperature': {(4, 'C')},
    'ligand_depletion_checked': {('yes', None)},
    'nonspecific_binding_determined': {('yes', None)},
    'nonspecific_ligand_is_radioligand': {('yes', None)},      # "The unspecific binding of [3H]leucine was determined upon addition of ... unlabeled leucine": the unlabelled form of the radioligand itself
}

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'dx receptor'
SYNTHETIC_PARTNER = 'dx-17'
# LeuT is the protein assayed. The partner is left None: the paragraph names several (leucine as radioligand, alanine as competitor,
# Na+ and K+ ions), so no single partner is clear.
REAL_EXPECTED_TARGET = 'leut'
REAL_EXPECTED_PARTNER = None


def answer_from(chunk, stated, support=None):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable. A stated field
    carries support 'direct' unless ``support`` (field -> support) says otherwise; an unavailable one carries none."""
    answer = {}
    for name in field_names():
        carries_unit = name in UNITS
        if name in stated:
            value, unit, quote = stated[name]
            answer[name] = {'status': 'stated', 'value': value, 'quote': quote, 'support': (support or {}).get(name, 'direct'), 'reason': None,
                            **({'unit': unit} if carries_unit else {})}
        else:
            answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None,
                            'reason': 'not_stated_in_passage', **({'unit': None} if carries_unit else {})}
    return answer


def synthetic_answer():
    return answer_from(SYNTHETIC, SYNTHETIC_STATED)


REAL_KD = (10, 'nM', '10× Kd, as determined in 200 mM NaCl')       # a multiple of the Kd, not a KD: used only to test quote refusals ('10× Kd' alone occurs twice)


# The capture method is only implied by the quote: it names His-tag SPA beads and does not say what holds the tag (a metal chelate).
REAL_SUPPORT = {CAPTURE: 'implied'}


def real_answer():
    return answer_from(REAL, REAL_STATED, REAL_SUPPORT)
