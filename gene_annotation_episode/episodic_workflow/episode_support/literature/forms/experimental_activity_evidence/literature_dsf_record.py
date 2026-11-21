"""The extracted record of ONE thermal shift experiment (differential scanning fluorimetry, DSF, with an extrinsic dye such as SYPRO Orange, or nanoDSF, which follows the intrinsic tryptophan and tyrosine fluorescence of the protein without a dye and may also follow the scattering for the aggregation temperature Tagg): a protein is heated at a constant rate while its unfolding is followed, and the melting temperature Tm (the midpoint of the unfolding transition) is read from the curve, by a fit of a Boltzmann (two-state) sigmoid or from the maximum of the first derivative. The protein is measured alone and with a ligand (the other protein or the small molecule whose binding is tested). A ligand that binds the folded protein more tightly than the unfolded one stabilises it and raises the Tm: the thermal shift (delta Tm = Tm with ligand minus Tm without, signed). The result is mostly QUALITATIVE (a shift of the Tm at one or a few ligand concentrations); some papers fit a series of ligand concentrations (the Tm or the shift against the ligand concentration) to an apparent dissociation constant (KD, or an apparent Kd or EC50 of the shift).

What a leaf extraction holds for one thermal shift experiment: the protein at a concentration in a buffer (with the vehicle of the ligand, for example DMSO, matched in the reference), the ligand at one or more concentrations, the dye or the label-free readout, the heating rate (degrees Celsius per minute), the Tm of the protein alone, the Tm with the ligand and their difference, the spread of the Tm over replicates, the Tagg of nanoDSF and the number of independent experiments. Three facts that the shift and its scatter need are also kept: the ligand concentration at which the stated shift (or the Tm with the ligand) was read (shift_ligand_concentration: the shift grows as ln(1 + [L]/KD), so the same shift means different things at different occupancies), whether the stated scatter of the Tm is over independent experiments or only over wells of one plate (tm_spread_over_independent_experiments), and, from the protein concentration beside the KD, whether the KD is titration-limited. The controls of the experiment are the protein alone in the same buffer and vehicle, the ligand with the dye and without the protein (to show that the ligand does not fluoresce, quench or bind the dye on its own), a melt curve with one clean sigmoidal transition, and a series of ligand concentrations in which the shift grows with the concentration.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What a thermal shift shows and what can go wrong is what the form keeps. The shift shows binding only INDIRECTLY: a ligand can raise the Tm without binding in the site of interest, and a ligand that binds equally to the folded and the unfolded protein shifts nothing. A shift is read against the protein alone in the same buffer and vehicle (a solvent such as DMSO alone moves the Tm), and against its spread over replicates (a shift is only meaningful when it is larger than the scatter of the Tm). A ligand can also fluoresce, quench or bind the dye, so the ligand with the dye and no protein must show no signal of its own. The melt curve must be one clean sigmoid: a high initial fluorescence, several transitions or an aggregation signal make the Tm unreliable. Tm depends on the heating rate (the unfolding is not at equilibrium at a fast scan). Binding is shown by the dependence of the shift on the ligand concentration; a KD from the shifts is apparent (it comes from the shift of the Tm, not from the equilibrium of the folded protein at one temperature) and needs ligand concentrations on both sides of it.

Record fields
-------------
version, experiment_type ('dsf'), experiment_ref, source_ref, assertion_ref
preparations   protein_preparation_ref, ligand_preparation_ref, dataset_ref: each a string or None (unknown). They are references to records, which the caller supplies; no passage
               states them. The converter hands them to the merger as its dependence keys (the protein as the analyte key, the ligand as the other partner; there is no surface).
quantities     kd, kd_spread, tm_apo, tm_ligand, delta_tm, tm_spread, tagg_apo, tagg_ligand, protein_concentration, ligand_concentration_lowest, ligand_concentration_highest,
               ligand_concentration_count, heating_rate, replicate_count: one operand each.
               Units: kd and kd_spread pM, nM, uM or mM (the apparent dissociation constant from the ligand series and its spread); tm_apo, tm_ligand 'C' (the Tm of the protein alone and with the ligand);
               delta_tm 'C' (SIGNED: positive is stabilisation by the ligand; it is the one quantity that may be zero or negative); tm_spread 'C' (the standard deviation of the Tm over replicates);
               tagg_apo, tagg_ligand 'C' (the aggregation onset temperature of nanoDSF, alone and with the ligand); protein_concentration, ligand_concentration_lowest and
               ligand_concentration_highest pM, nM, uM or mM; ligand_concentration_count 'count'; heating_rate 'C_per_min' (degrees Celsius, or the same number in kelvin, per minute);
               replicate_count 'count'.
readout        'dye_sypro_orange', 'label_free_intrinsic_fluorescence' (nanoDSF) or 'other_dye' or None: how the unfolding was followed. Kept in the record for the reviewer.
tm_method      'boltzmann_fit', 'first_derivative' or 'other' or None: how the Tm was read from the curve. Kept in the record for the reviewer.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (readout, tm_method, spread_kind), None when the choice is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's
fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (the quote states it only by
implication), 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand and
an 'unknown' fact carry support None. The grader keeps it and does not judge it; the converter does. Rule for the constructors: they take
``support`` and default it to 'direct' only so that forms built by tests, which do not go through the extraction, are direct; the extraction always
passes the model's own value.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record

SUPPORTS = ('direct', 'implied', 'about_something_else')


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': support}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    return {**literature_spr_record.fact(answer, refs), 'support': None if answer == 'unknown' else support}


VERSION = 'a105_dsf_record_v1'
EXPERIMENT_TYPE = 'dsf'
QUANTITIES = ('kd', 'kd_spread', 'tm_apo', 'tm_ligand', 'delta_tm', 'tm_spread', 'tagg_apo', 'tagg_ligand', 'protein_concentration', 'ligand_concentration_lowest', 'ligand_concentration_highest', 'ligand_concentration_count', 'shift_ligand_concentration', 'heating_rate', 'replicate_count')
SIGNED_QUANTITIES = ('delta_tm',)     # the only quantity that may be zero or negative: every other stated number is above 0
PREPARATION_KEYS = ('protein_preparation_ref', 'ligand_preparation_ref', 'dataset_ref')
READOUTS = ('dye_sypro_orange', 'label_free_intrinsic_fluorescence', 'other_dye')
TM_METHODS = ('boltzmann_fit', 'first_derivative', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'thermal_shift_observed': YES_NO, 'protein_alone_control_done': YES_NO, 'ligand_alone_control_done': YES_NO, 'melt_curve_sigmoidal': YES_NO, 'ligand_titration_measured': YES_NO, 'shift_dose_dependent': YES_NO, 'independent_experiments': YES_NO, 'tm_spread_over_independent_experiments': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'tm_apo': ('C',), 'tm_ligand': ('C',), 'delta_tm': ('C',), 'tm_spread': ('C',), 'tagg_apo': ('C',), 'tagg_ligand': ('C',), 'protein_concentration': CONCENTRATION_UNITS, 'ligand_concentration_lowest': CONCENTRATION_UNITS, 'ligand_concentration_highest': CONCENTRATION_UNITS, 'ligand_concentration_count': ('count',), 'shift_ligand_concentration': CONCENTRATION_UNITS, 'heating_rate': ('C_per_min',), 'replicate_count': ('count',)}
