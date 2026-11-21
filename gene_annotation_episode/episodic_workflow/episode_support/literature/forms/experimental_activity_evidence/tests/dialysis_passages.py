"""Chunks of text for the equilibrium dialysis / ultrafiltration extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (micro and degree signs) so byte
offsets differ from character offsets.

``REAL`` is real: two consecutive Methods paragraphs of 'Perfluoroalkyl Acid Binding with Peroxisome Proliferator-Activated Receptors alpha, gamma, and delta, and Fatty Acid Binding Proteins by
Equilibrium Dialysis with a Comparison of Methods' (Toxics 2021, 9(3), 45, PMC7996760, PMID 33652875, open access under the Creative Commons Attribution 4.0 licence (CC BY 4.0), Licensee MDPI, Basel, Switzerland),
the paragraph that begins 'EqD experiments were performed at room temperature' and the paragraph that follows it ('Blanks were prepared using a protein solution with no PFAS'), as the publisher's XML gives their own text,
joined by one space. Nothing is removed from either paragraph. They describe the equilibrium dialysis (EqD) set-up: 1.2 mL of phosphate buffered saline (pH 7.4) with the perfluoroalkyl acid in a tube, a Slide-a-Lyzer
mini dialysis cup with a 10 kDa cutoff membrane that is impermeable to the proteins, protein at 1 uM (0.48 uM for two proteins) in a final volume of 100 uL, blanks and non-binding controls (prepared; no result is given),
36 h on a rocker to reach equilibrium at room temperature, in duplicate. They give no KD, no percent bound, no detection method and no result (the LC-MS/MS and the results are in other paragraphs), so the real
record built from them is a qualitative one with no statement of binding.

``REAL_RESULT`` is real: the Results paragraph of the same paper that begins 'Strong binding for PFHxA (Figure 4A)', whole (PMC7996760, CC BY 4.0). It reports the KD of PFHxA with PPAR-alpha from the EqD experiments (0.097 uM) and
states that binding was seen for PFHxA and PFNA and not for PFBA and PFHpA.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_extraction import (
    DETECTION, DEVICE, FIT_MODEL, SEPARATION, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import UNITS

PAPER_ID = 'PMC7996760'
REAL = (
    'EqD experiments were performed at room temperature by first adding 1.2 mL of the 18.1 mS/cm phosphate buffered saline (pH 7.4) spiked with PFAS to a 1.5 mL polypropylene microcentrifuge tube (Supplemental Figure S1). '
    'A Slide-a-Lyzer mini dialysis cup containing a semi-permeable membrane (molecular weight cutoff: 10kDa) was then inserted into the tube, through which PFAS could freely pass but which was impermeable to the proteins used '
    '(MW range 15.1–54.1 kDa). A known volume of protein in buffer (20 to 50 μL) was added to reach a 1 μM concentration for L-FABP, I-FABP, and PPAR-γ, and 0.48 μM for PPAR-δ and PPAR-α. The lower concentration of PPAR-δ and '
    'PPAR-α was necessary due to the larger size of these proteins. Finally, the total volume in the dialysis cup was brought to 100 μL by adding the buffer spiked with PFAS. '
    'Blanks were prepared using a protein solution with no PFAS. Non-binding controls (containing PFAS but no protein) were prepared with the buffer spiked with different concentrations of PFAS. Finally, samples were placed on a rocker '
    '(Open-Air Rocker, Fisher Scientific, Waltham, MA, USA) for 36 h to reach equilibrium at room temperature. All dialysis tests were performed in duplicate.')

REAL_RESULT = (
    'Strong binding for PFHxA (Figure 4A) and PFNA (Figure 4B) were observed via EqD experiments, whereas no binding occurred for PFBA (Supplemental Figure S2A) and PFHpA (Supplemental Figure S2B). The lack of chain length '
    'dependence suggested by this is in agreement with the MD predictions. However, MD simulations suggested only PFBA would have strong binding for PPAR-α, which was not borne out by dialysis. The relatively strong binding '
    'suggested by the KD of 0.097 μM for PFHxA could have implications for short-chain PFAS safety.')

# The expected identity of the model runs (normalized: casefold, whitespace collapsed). Synthetic: the assayed protein PZ-2 is the target, the compound QX-7 the
# partner. Real METHODS paragraphs (REAL): several proteins (L-FABP, I-FABP, PPAR-gamma, -delta, -alpha) are named, so no single target. Real RESULT paragraph
# (REAL_RESULT): the PPAR-alpha protein (the chunk writes 'PPAR-α') with the compound PFHxA. The real constants are suffixed by the variant of the run id.
SYNTHETIC_TARGET = 'pz-2'
SYNTHETIC_PARTNER = 'qx-7'
REAL_EXPECTED_TARGET_METHODS = None
REAL_EXPECTED_PARTNER_METHODS = None
REAL_EXPECTED_TARGET_RESULT = 'ppar-α'
REAL_EXPECTED_PARTNER_RESULT = 'pfhxa'

SYNTHETIC = (
    'The binding of the compound QX-7 to the protein PZ-2 was measured by rapid equilibrium dialysis in a RED device with a membrane cutoff of 10 kDa. '
    'The protein chamber held 100 µL of PZ-2 at 1 µM and the buffer chamber 300 µL of buffer, 20 mM HEPES pH 7.4 with 150 mM NaCl, and the device was shaken at 37 °C for 6 h. '
    'Equilibrium was shown by a time course, in which the concentrations in the two chambers stopped changing after 4 h. '
    'QX-7 was measured in both chambers by LC-MS/MS. The free concentration of QX-7 was measured directly in the buffer chamber. '
    'A control with buffer only, without protein, showed equal concentrations of QX-7 in both chambers. '
    'No PZ-2 was found in the buffer chamber, so the protein was retained by the membrane. '
    'QX-7 was stable over the incubation, with no breakdown. '
    'The recovery of QX-7 from both chambers was 95%, as a mass balance, and the adsorption of QX-7 to the membrane and the device was 5%, which was checked with protein-free cells and corrected. '
    'The volume shift of the protein chamber was 3%, and it was corrected. '
    'At a total QX-7 concentration of 500 nM, the free concentration was 200 nM and the bound concentration was 300 nM. '
    'Thus 60% of QX-7 was bound, with a fraction bound of 0.6, and 40% was unbound, with a fraction unbound of 0.4, which shows that QX-7 bound to PZ-2. '
    'In a saturation series of six total concentrations of QX-7 (50, 100, 200, 400, 800 and 1600 nM), from 50 nM to 1600 nM, the bound against the free QX-7 was fitted with a one-site binding model, '
    'which gave a KD of 200 nM with a standard error of 20 nM and a Bmax of 1.0 mol of QX-7 per mol of PZ-2. '
    'The protein concentration of 1 µM was above the KD. '
    'In a competition with the unlabelled QX-9, a Ki of 500 nM with a standard error of 50 nM was found. '
    'Two cells were run per concentration, and three independent experiments were done on separate days. The KD was determined by this dialysis only.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (200, 'nM', 'a KD of 200 nM'),
    'kd_spread': (20, 'nM', 'a standard error of 20 nM'),
    'bmax': (1.0, 'ratio', 'a Bmax of 1.0 mol of QX-7 per mol of PZ-2'),
    'ki': (500, 'nM', 'a Ki of 500 nM'),
    'ki_spread': (50, 'nM', 'a standard error of 50 nM'),
    'percent_bound': (60, 'percent', '60% of QX-7 was bound'),
    'percent_unbound': (40, 'percent', '40% was unbound'),
    'fraction_bound': (0.6, 'ratio', 'a fraction bound of 0.6'),
    'fraction_unbound': (0.4, 'ratio', 'a fraction unbound of 0.4'),
    'ligand_total_concentration': (500, 'nM', 'a total QX-7 concentration of 500 nM'),
    'free_ligand_concentration': (200, 'nM', 'the free concentration was 200 nM'),
    'bound_ligand_concentration': (300, 'nM', 'the bound concentration was 300 nM'),
    'protein_concentration': (1, 'uM', 'PZ-2 at 1 µM'),
    'ligand_range_lowest': (50, 'nM', 'from 50 nM'),
    'ligand_range_highest': (1600, 'nM', 'to 1600 nM'),
    'titration_point_count': (6, 'count', 'six total concentrations'),
    'membrane_cutoff': (10, 'kDa', 'a membrane cutoff of 10 kDa'),
    'equilibration_time': (6, 'h', 'for 6 h'),
    'run_temperature': (37, 'C', 'at 37 °C'),
    'buffer_ph': (7.4, 'pH', 'HEPES pH 7.4'),
    'salt_concentration': (150, 'mM', '150 mM NaCl'),
    'protein_chamber_volume': (100, 'uL', 'The protein chamber held 100 µL'),
    'buffer_chamber_volume': (300, 'uL', 'the buffer chamber 300 µL'),
    'recovery': (95, 'percent', 'The recovery of QX-7 from both chambers was 95%'),
    'membrane_adsorption': (5, 'percent', 'the adsorption of QX-7 to the membrane and the device was 5%'),
    'volume_shift': (3, 'percent', 'The volume shift of the protein chamber was 3%'),
    'technical_replicate_count': (2, 'count', 'Two cells were run per concentration'),
    'replicate_count': (3, 'count', 'three independent experiments'),
    'concentration_series': ([50, 100, 200, 400, 800, 1600], 'nM', '(50, 100, 200, 400, 800 and 1600 nM)'),
    SEPARATION: ('rapid_equilibrium_dialysis', None, 'rapid equilibrium dialysis in a RED device'),
    DEVICE: ('red_device', None, 'a RED device'),
    DETECTION: ('lc_msms', None, 'QX-7 was measured in both chambers by LC-MS/MS'),
    SPREAD_KIND: ('standard_error', None, 'a standard error of 20 nM'),
    FIT_MODEL: ('one_site', None, 'a one-site binding model'),
    'binding_detected': ('yes', None, 'which shows that QX-7 bound to PZ-2'),
    'equilibrium_time_course_shown': ('yes', None, 'Equilibrium was shown by a time course'),
    'recovery_checked': ('yes', None, 'as a mass balance'),
    'adsorption_checked_and_corrected': ('yes', None, 'which was checked with protein-free cells and corrected'),
    'volume_shift_corrected': ('yes', None, 'and it was corrected'),
    'ligand_stable': ('yes', None, 'QX-7 was stable over the incubation, with no breakdown'),
    'free_ligand_measured_directly': ('yes', None, 'The free concentration of QX-7 was measured directly in the buffer chamber'),
    'protein_retained': ('yes', None, 'so the protein was retained by the membrane'),
    'buffer_only_control_equal': ('yes', None, 'showed equal concentrations of QX-7 in both chambers'),
    'protein_at_or_above_kd': ('yes', None, 'The protein concentration of 1 µM was above the KD'),
    'independent_experiments': ('yes', None, 'three independent experiments were done on separate days'),
    'single_estimate_method': ('yes', None, 'The KD was determined by this dialysis only'),
}

# field -> (value, unit, quote) for the real passage: what a careful reader may state from it about the experiment it describes, with the
# quote that says it.
REAL_STATED = {
    'membrane_cutoff': (10, 'kDa', 'molecular weight cutoff: 10kDa'),
    'buffer_ph': (7.4, 'pH', 'phosphate buffered saline (pH 7.4)'),
    'buffer_chamber_volume': (1.2, 'mL', 'first adding 1.2 mL of the 18.1 mS/cm phosphate buffered saline'),
    'protein_chamber_volume': (100, 'uL', 'the total volume in the dialysis cup was brought to 100 μL'),
    'equilibration_time': (36, 'h', 'for 36 h to reach equilibrium'),
    'technical_replicate_count': (2, 'count', 'All dialysis tests were performed in duplicate'),
    SEPARATION: ('equilibrium_dialysis', None, 'A Slide-a-Lyzer mini dialysis cup containing a semi-permeable membrane'),
    DEVICE: ('dialysis_cup', None, 'A Slide-a-Lyzer mini dialysis cup'),
    'protein_retained': ('yes', None, 'impermeable to the proteins used'),
}
# The allowed set of the real model run: field -> every (value, unit) the paragraphs clearly state for it. Not allowed, because they do not state them:
# a protein concentration (1 uM for three proteins and 0.48 uM for two, none given as the result), the salt (a conductivity and a phosphate buffered saline are not a salt concentration), the temperature
# (room temperature is not a number), the ratio of ligand to protein and the stock concentration, any KD, percent or fraction bound, recovery or adsorption (the recovery range of 75-235 percent is in another paragraph),
# the detection (in another paragraph), a statement of binding, an equilibrium time course (the 36 h are what was meant to reach equilibrium), the buffer-only control (prepared; no result), independent experiments (the
# duplicate is of dialysis tests, which a reader takes as two cells; the paragraph does not say they were independent experiments, so the replicate count is not allowed), a fit model, and a single method.
REAL_ALLOWED = {name: {(value, unit)} for name, (value, unit, _) in REAL_STATED.items()}

REAL_RESULT_STATED = {
    'kd': (0.097, 'uM', 'the KD of 0.097 μM for PFHxA'),
    'binding_detected': ('yes', None, 'Strong binding for PFHxA (Figure 4A) and PFNA (Figure 4B) were observed via EqD experiments'),
    SEPARATION: ('equilibrium_dialysis', None, 'which was not borne out by dialysis'),
}
# The KD may also be given in nanomolar (0.097 uM is exactly 97 nM, a conversion the instructions allow).
REAL_RESULT_ALLOWED = {'kd': {(0.097, 'uM'), (97, 'nM')}, 'binding_detected': {('yes', None)}, SEPARATION: {('equilibrium_dialysis', None)}}


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


REAL_COUNT = (2, 'count', 'PFAS')       # not a replicate count: used only to test quote refusals ('PFAS' occurs many times)


def real_answer():
    return answer_from(REAL, REAL_STATED)


# The separation method is only implied by the quote: it says what the binding was not borne out by, not that the experiment was an equilibrium dialysis.
REAL_RESULT_SUPPORT = {SEPARATION: 'implied'}


def real_result_answer():
    return answer_from(REAL_RESULT, REAL_RESULT_STATED, REAL_RESULT_SUPPORT)
