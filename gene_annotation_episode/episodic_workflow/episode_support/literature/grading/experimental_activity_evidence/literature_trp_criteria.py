"""Trp criteria: the ONE place where the intrinsic tryptophan (and tyrosine) fluorescence quenching grader's criteria and thresholds are declared.

DRAFT FOR EXPERT REVIEW. This file is the single source for what the Trp grader asks.
The grader reports FACTS and holds NO threshold that judges goodness: where a criterion
needs a number to be compared with a limit (the fluorescence change, the excitation
wavelength, the ligand absorbance, the added volume, the concentration series, the protein
over the KD, the incubation, the replicate count), the grader records the number with its
support refs and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the
judgement and its EXPERT_REVIEW constants are on the sheet side, in
literature_trp_converter.py. The logic that answers each question is in
literature_trp_grader.py (one short function per criterion, same order). The only
constants left here are unit conversions (FIXED_BY_DEFINITION).

How to read an entry in TRP_CRITERIA
------------------------------------
id          the criterion's name (also the key in the grader's result)
question    the plain question the criterion answers
reads       the record fields it reads (forms/.../literature_trp_record.py)
rule        the rule in words, one or two sentences an expert can check
thresholds  the names of the constants below that the rule uses
returns     every case the criterion can return, as
            (status, reason_code, when). Statuses are the existing A105
            vocabulary: supported / unknown / conflicting / not_applicable.
            'conflicting' means the record shows the standard is NOT met
            (the vocabulary has no 'failed'). 'unknown' means the record does
            not say; missing information is never read as met and never as
            unmet. A status listed as 'never' cannot occur for this criterion.

Constants: each is defined once, below. FIXED_BY_DEFINITION marks a physical
constant or unit conversion, not a judgment; no judgment value is declared here.

Terms. The reported constant of a series: the KD (the native value 'constant_name'
says which; only a KD is a binding constant, a Stern-Volmer constant Ksv is a
quenching efficiency and is never taken for one). Protein: the partner whose
intrinsic fluorescence is read, held at a constant concentration. Titrant: the
ligand added in a series. Signal: the fractional change of the protein's
fluorescence (fluorescence_change, percent) between the free protein and the
saturated complex. Inner-filter effect: absorption of the excitation or the
emission light by the ligand lowers the measured fluorescence without any
binding; it is corrected with an absorbance-based formula or with a titration of
free tryptophan or N-acetyl-tryptophanamide (NATA), or avoided because the ligand
does not absorb there. Dilution: the added ligand dilutes the protein and lowers
the fluorescence without any binding. Static quenching: a complex is formed (what
a KD describes); dynamic (collisional) quenching is described by Ksv and is not a
binding. Tight binding: the protein is not well below the KD, so binding depletes
the free ligand and the 1:1 hyperbola no longer gives the KD; a quadratic fit (or
an explicit consideration of the depletion) is needed.

What this method does not ask (items of the other binding experiments left out
because a fluorescence titration in solution has no such thing): a surface and its
regeneration, mass transport, a sensorgram baseline, the kinetic rate constants,
a labelling scheme (the protein's own fluorescence is read, nothing is attached),
a competition format, the donor and the acceptor of FRET and the polarization
ends of FP. The emission wavelength and shift, their direction and the direction
of the change are kept in the record for the reviewer; no criterion judges them.
"""

VERSION = 'a105_trp_criteria_v1'

# ---- Threshold constants -------------------------------------------------
NM_PER_UNIT = {'pM': 0.001, 'nM': 1.0, 'uM': 1000.0, 'mM': 1000000.0}  # FIXED_BY_DEFINITION: nanomolar per concentration unit.
MIN_PER_UNIT = {'s': 1 / 60, 'min': 1.0, 'h': 60.0}  # FIXED_BY_DEFINITION: minutes per time unit.

# ---- The criteria --------------------------------------------------------
TRP_CRITERIA = (
    {
        'id': 'signal_amplitude',
        'question': 'Is the change of the intrinsic fluorescence large enough to fit a KD?',
        'reads': ('quantities.fluorescence_change',),
        'rule': 'The grader records the change of the fluorescence between the free protein and the saturated complex (fluorescence_change_percent) and its refs (change_refs) and leaves the judgement to the sheet. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'fluorescence_change_recorded_for_the_sheet', 'the change is given: it is recorded and the sheet judges it'),
            ('unknown', 'fluorescence_change_not_given', 'the change is not given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'excitation_selectivity',
        'question': 'Was the excitation wavelength one that reads tryptophan alone?',
        'reads': ('quantities.excitation_wavelength',),
        'rule': 'The grader records the excitation wavelength (excitation_nm) and its refs (excitation_refs) and leaves the judgement to the sheet. Not given is unknown.',
        'thresholds': (),
        'returns': (
            ('unknown', 'excitation_recorded_for_the_sheet', 'the excitation wavelength is given: it is recorded and the sheet judges it'),
            ('unknown', 'excitation_wavelength_not_stated', 'the excitation wavelength is not given'),
            ('conflicting', 'never', 'never returned'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'inner_filter',
        'question': 'Was the inner-filter effect of the ligand corrected, or shown to be negligible?',
        'reads': ('facts.inner_filter_corrected', 'facts.ligand_absorbance_negligible', 'quantities.ligand_absorbance'),
        'rule': 'A stated correction is supported. Otherwise a given ligand absorbance is recorded (ligand_absorbance, in AU, and absorbance_refs) and the judgement is left to the sheet. Otherwise a stated negligible absorbance is supported, and a statement that it was not corrected, or that the ligand absorbs, fails. Nothing stated is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'inner_filter_corrected', 'the correction is yes'),
            ('unknown', 'ligand_absorbance_recorded_for_the_sheet', 'not corrected and an absorbance is given: it is recorded and the sheet judges it'),
            ('supported', 'ligand_absorbance_negligible', 'no absorbance number and the negligible-absorbance fact is yes'),
            ('conflicting', 'inner_filter_not_corrected', 'no absorbance number and the correction or the negligible-absorbance fact is no'),
            ('unknown', 'inner_filter_not_addressed', 'nothing stated'),
            ('not_applicable', 'fact_not_applicable', 'both facts are not_applicable and no absorbance is given'),
        ),
    },
    {
        'id': 'dilution',
        'question': 'Was the dilution of the protein by the added ligand corrected, or small?',
        'reads': ('facts.dilution_corrected', 'quantities.added_volume_fraction'),
        'rule': 'A stated correction is supported. Otherwise a given added volume is recorded (added_volume_percent and added_volume_refs) and the judgement is left to the sheet. Otherwise a statement that it was not corrected fails. Nothing stated is unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'dilution_corrected', 'the correction is yes'),
            ('unknown', 'added_volume_recorded_for_the_sheet', 'not corrected and an added volume is given: it is recorded and the sheet judges it'),
            ('conflicting', 'dilution_not_corrected', 'no added volume and the correction is no'),
            ('unknown', 'dilution_not_addressed', 'nothing stated'),
            ('not_applicable', 'fact_not_applicable', 'the fact is not_applicable and no added volume is given'),
        ),
    },
    {
        'id': 'buffer_blank',
        'question': 'Was the fluorescence of the buffer subtracted?',
        'reads': ('facts.buffer_blank_subtracted',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'ligand_fluorescence',
        'question': 'Was the fluorescence of the ligand alone measured?',
        'reads': ('facts.ligand_only_control_measured',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'specificity_control',
        'question': 'Was the specificity of the signal shown by a control (a non-binding protein, a free tryptophan or NATA control, or a signal traced to a tryptophan at the binding site)?',
        'reads': ('facts.nonbinding_control_done', 'facts.trp_analogue_control_done', 'facts.signal_localised_to_binding_site'),
        'rule': 'One control done is enough: any of the three facts yes is supported (a control reported as not done beside it does not outweigh it). Otherwise any no fails, otherwise all not_applicable is not applicable, otherwise unknown.',
        'thresholds': (),
        'returns': (
            ('supported', 'a_specificity_control_done', 'any of the three facts is yes'),
            ('conflicting', 'fact_answered_no', 'none is yes and any is no'),
            ('unknown', 'fact_unknown', 'none is yes or no and any is unknown'),
            ('not_applicable', 'fact_not_applicable', 'all three are not_applicable'),
        ),
    },
    {
        'id': 'photobleaching',
        'question': 'Was photobleaching of the protein checked or avoided?',
        'reads': ('facts.photobleaching_checked',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'saturation',
        'question': 'Did the fluorescence change saturate with the ligand concentration?',
        'reads': ('facts.signal_saturates',),
        'rule': 'The one fact decides: yes supported, no fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'concentration_series',
        'question': 'Did the ligand concentrations bracket the KD well enough to define the binding curve?',
        'reads': ('quantities.kd', 'quantities.titration_point_count', 'concentration_series'),
        'rule': 'The grader records the number of concentrations (concentration_count: the listed series, or else the stated number of points) with its refs (count_refs) and, when the list and the KD are both given, the lowest and the highest over the KD (concentration_low_over_constant, concentration_high_over_constant) with their refs (series_refs), and leaves the judgement to the sheet; the span can only be judged from the list. Neither a list nor a count is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'series_recorded_for_the_sheet', 'a list or a count is given: the count (and the span, when it can be formed) is recorded and the sheet judges it'),
            ('unknown', 'kd_or_series_missing', 'neither a list nor a count is given'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'protein_concentration',
        'question': 'Was the protein at or below the KD, or was depletion handled by a tight-binding analysis?',
        'reads': ('quantities.protein_concentration', 'quantities.kd', 'fit_model', 'facts.protein_at_or_below_kd', 'facts.tight_binding_considered'),
        'rule': 'With the protein concentration and the KD both given, the grader records their quotient (protein_over_kd), the refs (protein_refs) and whether the analysis handles tight binding (tight_binding_handled: a quadratic fit, or tight binding stated as considered) and leaves the judgement to the sheet. With either number missing, the fact that the protein is at or below the KD decides: yes supported; no is supported when tight binding was handled and fails otherwise; not stated is unknown.',
        'thresholds': ('NM_PER_UNIT',),
        'returns': (
            ('unknown', 'protein_over_kd_recorded_for_the_sheet', 'both numbers are given: the quotient is recorded and the sheet judges it'),
            ('supported', 'protein_at_or_below_kd', 'no quotient and the fact is yes'),
            ('supported', 'protein_above_kd_with_tight_binding_analysis', 'no quotient, the fact is no and the fit is quadratic or tight binding is stated considered'),
            ('conflicting', 'protein_above_kd_without_tight_binding_analysis', 'no quotient, the fact is no and neither'),
            ('unknown', 'protein_or_kd_missing', 'no quotient and the fact is not stated'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'equilibrium',
        'question': 'Was the binding at equilibrium when read?',
        'reads': ('facts.equilibrium_reached', 'quantities.incubation_time'),
        'rule': 'The fact decides: yes supported, no fails. When it is not stated and an incubation time is given, the grader records it (incubation_min, in minutes, and incubation_refs) and leaves the judgement to the sheet; otherwise it is unknown.',
        'thresholds': ('MIN_PER_UNIT',),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'incubation_recorded_for_the_sheet', 'not stated and an incubation time is given: it is recorded and the sheet judges it'),
            ('unknown', 'fact_unknown', 'not stated and no incubation time'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'quenching_mechanism',
        'question': 'Is the quenching static (a complex), not dynamic (collisional)?',
        'reads': ('facts.quenching_is_static',),
        'rule': 'The one fact decides: yes supported, no (dynamic or collisional quenching) fails, unknown unknown, not_applicable not applicable.',
        'thresholds': (),
        'returns': (
            ('supported', 'facts_answered_yes', 'answer yes'),
            ('conflicting', 'fact_answered_no', 'answer no'),
            ('unknown', 'fact_unknown', 'answer unknown'),
            ('not_applicable', 'fact_not_applicable', 'answer not_applicable'),
        ),
    },
    {
        'id': 'fit_model',
        'question': 'Is the fitting model stated and one that gives a dissociation constant?',
        'reads': ('fit_model',),
        'rule': 'The model must be stated. A Stern-Volmer fit gives the quenching constant Ksv, not a KD, and fails.',
        'thresholds': (),
        'returns': (
            ('supported', 'model_stated', 'a binding model stated (1:1, hill, quadratic or other)'),
            ('conflicting', 'stern_volmer_fit_gives_ksv_not_kd', 'the model is the Stern-Volmer equation'),
            ('unknown', 'fit_model_not_stated', 'no fit model'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
    {
        'id': 'replicates',
        'question': 'Were there enough independent titrations?',
        'reads': ('quantities.replicate_count', 'facts.independent_titrations'),
        'rule': 'Independence stated as no fails (a fact). A stated count with independence not stated as no is recorded (replicate_count, replicate_independent, replicate_refs) and the judgement is left to the sheet.',
        'thresholds': (),
        'returns': (
            ('conflicting', 'replicates_not_independent', 'independence is stated as no'),
            ('unknown', 'replicate_count_recorded_for_the_sheet', 'a count is stated and independence is not no: they are recorded and the sheet judges them'),
            ('unknown', 'replicate_count_or_independence_unknown', 'no count is stated and independence is not no'),
            ('not_applicable', 'never', 'never returned'),
        ),
    },
)
