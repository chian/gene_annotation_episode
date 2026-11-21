"""The extracted record of ONE FRET / TR-FRET binding experiment, in solution.

What a leaf extraction holds for one Forster resonance energy transfer (FRET) binding experiment, including the
time-resolved variants (TR-FRET, HTRF, LanthaScreen): one binding partner carries a donor fluorophore and the other an
acceptor, and binding is read from the energy transfer between them, as a titration (the titrant is added in a series
to a labelled partner held fixed; KD) or as a competition (an unlabelled ligand displaces one labelled partner; Ki or
IC50). One experiment, or replicate titrations reported as one result, in the same operand shape as the SPR, ITC, BLI,
GCI and FP records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys,
source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value
None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR
record module's; they are shared because they only build operands.

FRET differs from the other methods in what is measured and what can go wrong: the read is a ratio of the acceptor
emission to the donor emission (for example 665 nm over 620 nm), which corrects for volume, lamp and quenching only when
a ratio is really used; the donor's light leaks into the acceptor channel and the acceptor is excited directly, so the
donor-only and acceptor-only signals must be measured and subtracted; in the time-resolved format the read waits a delay
after the flash so that short-lived background has decayed, which only works with a long-lived donor (a lanthanide
chelate or cryptate; a fluorescent-protein or organic-dye donor lives nanoseconds); the labelling may be direct (a dye
on the protein) or indirect (a labelled antibody against a tag, or streptavidin), which adds equilibria and can produce
higher-order complexes; and test compounds can absorb or fluoresce and so disturb the ratio. The form keeps exactly those
things.

Record fields
-------------
version, experiment_type ('fret'), experiment_ref, source_ref, assertion_ref
preparations   titrant_preparation_ref (the partner added in a series, or in competition the unlabelled competitor),
               fixed_partner_preparation_ref (the labelled partner held at a fixed concentration), dataset_ref: each a
               string or None (unknown). The converter hands them to the merger as its dependence keys (titrant as the
               analyte key, the fixed partner as the other partner; a FRET experiment in solution has no surface).
quantities     kd, ki, ec50, ic50, kd_spread, ki_spread, donor_concentration, acceptor_concentration, ratio_minimum,
               ratio_maximum, delay_time, integration_time, assay_volume, incubation_time, temperature, replicate_count:
               one operand each.
               Units: kd/ki/ec50/ic50/kd_spread/ki_spread/donor_concentration/acceptor_concentration pM, nM, uM or mM;
               ratio_minimum and ratio_maximum 'ratio' (the acceptor over donor emission ratio as the passage gives it, on
               whatever scale it uses; only their quotient is judged); delay_time and integration_time us or ms;
               assay_volume uL or mL; incubation_time s, min or h; temperature C or K; replicate_count count.
concentration_series
               operand whose 'value' is a list of titrant concentrations (unit pM, nM, uM or mM), or None when not given.
               In the competition format it is the competitor series.
assay_format   'direct_titration' (a labelled partner is titrated with its partner; KD) or 'competition' (an unlabelled
               ligand displaces a labelled partner; Ki or IC50) or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
fit_model      '1:1', 'hill', 'quadratic', 'competitive_binding', 'other' or None.
plate_type     'white', 'black', 'cuvette', 'other' or None. The plate or cell the reads were made in, kept in the record
               for the reviewer; no criterion judges it.
donor_acceptor_pair
               'lanthanide_with_organic_acceptor' (a terbium or europium chelate or cryptate donor with an organic dye or
               d2 or allophycocyanin acceptor), 'fluorescent_protein_pair' (for example CFP and YFP), 'organic_dye_pair'
               (for example Cy3 and Cy5, or fluorescein and rhodamine), 'other' or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
choice_support name -> support of each plain choice field (assay_format, spread_kind, fit_model, plate_type, donor_acceptor_pair),
               None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries
'support', the extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or
fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the topic but is really
about another measurement or condition). An unavailable operand, an 'unknown' fact and an unstated choice carry None. The
grader does not judge it; the converter does. Rule for the constructors: they take ``support`` and default it to
'direct', and the default is only for forms built by tests that do not go through the extraction (the extraction always
passes the model's answer).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record

SUPPORTS = ('direct', 'implied', 'about_something_else')


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': support}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    return {**literature_spr_record.fact(answer, refs), 'support': None if answer == 'unknown' else support}

VERSION = 'a105_fret_record_v1'
EXPERIMENT_TYPE = 'fret'
QUANTITIES = ('kd', 'ki', 'ec50', 'ic50', 'kd_spread', 'ki_spread', 'donor_concentration', 'acceptor_concentration', 'ratio_minimum', 'ratio_maximum', 'delay_time', 'integration_time', 'assay_volume', 'incubation_time', 'temperature', 'replicate_count')
PREPARATION_KEYS = ('titrant_preparation_ref', 'fixed_partner_preparation_ref', 'dataset_ref')
ASSAY_FORMATS = ('direct_titration', 'competition')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', 'hill', 'quadratic', 'competitive_binding', 'other')
PLATE_TYPES = ('white', 'black', 'cuvette', 'other')
CHOICES = ('assay_format', 'spread_kind', 'fit_model', 'plate_type', 'donor_acceptor_pair')
PAIRS = ('lanthanide_with_organic_acceptor', 'fluorescent_protein_pair', 'organic_dye_pair', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'time_resolved_read': YES_NO, 'ratiometric_readout_used': YES_NO, 'donor_only_control_measured': YES_NO, 'acceptor_only_control_measured': YES_NO, 'crosstalk_corrected': YES_NO, 'labelled_partner_at_or_below_kd': YES_NO, 'tight_binding_considered': YES_NO, 'equilibrium_reached': YES_NO, 'indirect_labelling_used': YES_NO, 'labelling_does_not_alter_binding': YES_NO, 'compound_interference_checked': YES_NO, 'nonspecific_binding_checked': YES_NO, 'unlabelled_competitor_displaces': YES_NO, 'independent_titrations': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'ki': CONCENTRATION_UNITS, 'ec50': CONCENTRATION_UNITS, 'ic50': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'donor_concentration': CONCENTRATION_UNITS, 'acceptor_concentration': CONCENTRATION_UNITS, 'ratio_minimum': ('ratio',), 'ratio_maximum': ('ratio',), 'delay_time': ('us', 'ms'), 'integration_time': ('us', 'ms'), 'assay_volume': ('uL', 'mL'), 'incubation_time': ('s', 'min', 'h'), 'temperature': ('C', 'K'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
