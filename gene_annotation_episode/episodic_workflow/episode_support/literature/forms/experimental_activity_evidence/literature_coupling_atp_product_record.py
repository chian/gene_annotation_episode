"""The extracted record of ONE nucleotide-hydrolysis-to-product coupling experiment (type 'coupling_atp_product', class reaction_coupling).

A type of the reaction_coupling class (DRAFT 2026-11-22, owner to correct; the structure is copied from the spectro_direct record). The experiment:
one enzyme (or enzyme complex) hydrolyses ATP or GTP while it makes a product, and the paper measures BOTH sides in the same reaction: the
nucleotide hydrolysed (free phosphate by a dye such as malachite green, the loss of NADH in the pyruvate kinase / lactate dehydrogenase coupled
assay, [gamma-32P] phosphate released, or ADP by chromatography) and the product it drives (a phosphorylated or ligated product, ammonia, a
reduced or fixed product, and so on). The link between the two is reported as the nucleotides hydrolysed per product formed (a COST, normally above
1: it is not a fraction), as the product per nucleotide, or as the share of the hydrolysis that ends in product once the reaction's own coefficient
is applied. The rate of ATP hydrolysis with no substrate or partner (the basal ATPase rate) is the uncoupled hydrolysis; it must be taken off or
reported, and it is the main way this link goes wrong.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status
'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('coupling_atp_product'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided 2026-11-22 (owner to confirm): the enzyme preparation, from which BOTH sides of the coupling come, is the
               analyte_preparation_ref; nothing is immobilized and there is no surface, so immobilized_preparation_ref and surface_ref stay None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     the link, as the passage states it (one quantity may be stated, several may be; each with the spread the passage gives for it):
                 productive_fraction and productive_fraction_spread          fraction or percent: the share of the hydrolysed nucleotide that ends in product
                 stoichiometric_ratio and stoichiometric_ratio_spread        mol_per_mol or fraction: moles of product per mole of nucleotide hydrolysed
                 nucleotides_per_product and nucleotides_per_product_spread  mol_per_mol: moles of nucleotide hydrolysed per mole of product (the cost)
               the paper's own reaction account and the conditions that decide how far the link can be trusted:
                 stoichiometric_coefficient  mol_per_mol   the moles of nucleotide the paper's own reaction account says one product needs
                 nucleotide_rate             rate units    the nucleotide hydrolysis rate of the reaction that makes the product, before the basal rate is taken off
                 basal_rate                  rate units    the nucleotide hydrolysis rate with no substrate or partner (the uncoupled, basal ATPase rate)
                 nucleotide_consumed_percent percent       the share of the nucleotide hydrolysed in the window the measurement was taken over
                 replicate_count             count         the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the three spreads are.
nucleotide     'atp', 'gtp', 'other_nucleotide' or None: which nucleotide is hydrolysed. For the reviewer; no criterion rests on it.
hydrolysis_readout
               'phosphate_dye', 'coupled_nadh_loss', 'radiolabelled_phosphate', 'chromatography', 'other_readout' or None: how the hydrolysis was
               measured. For the reviewer; no criterion rests on it.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, nucleotide, hydrolysis_readout), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

The link is NEVER worked out here from the amounts or the rates of the two sides: only a link the passage itself states is a quantity of the record.
No criterion rests on a choice (a choice holds no span after the merge of the leaf records): what a criterion needs is a yes/no fact with its quote or
a quantity.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and
default it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_atp_product_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_atp_product'
QUANTITIES = ('productive_fraction', 'productive_fraction_spread', 'stoichiometric_ratio', 'stoichiometric_ratio_spread', 'nucleotides_per_product',
              'nucleotides_per_product_spread', 'stoichiometric_coefficient', 'nucleotide_rate', 'basal_rate', 'nucleotide_consumed_percent', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
NUCLEOTIDES = ('atp', 'gtp', 'other_nucleotide')
HYDROLYSIS_READOUTS = ('phosphate_dye', 'coupled_nadh_loss', 'radiolabelled_phosphate', 'chromatography', 'other_readout')
# The plain choice fields: name -> its vocabulary. Each is a top-level value named in 'choice_support' (the merge reads choices only so).
CHOICES = {'spread_kind': SPREAD_KINDS, 'nucleotide': NUCLEOTIDES, 'hydrolysis_readout': HYDROLYSIS_READOUTS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'reagent_blank_done': YES_NO, 'basal_rate_subtracted': YES_NO, 'coupling_enzymes_in_excess': YES_NO,
         'signal_in_linear_range': YES_NO, 'nucleotide_regenerated': YES_NO, 'product_requires_hydrolysis': YES_NO, 'product_identified': YES_NO,
         'product_calibrated': YES_NO, 'nucleotide_side_calibrated': YES_NO, 'same_mixture': YES_NO, 'same_window': YES_NO, 'native_substrate': YES_NO,
         'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'coupled_product_detected': YES_NO}

RATE_UNITS = ('umol/min', 'nmol/min', 'pmol/min', 'nmol/s', 'umol/min/mg', 'nmol/min/mg', 'pmol/min/mg', 'uM/min', 'uM/s', 's^-1', 'min^-1')
FRACTION_UNITS = ('fraction', 'percent')
RATIO_UNITS = ('mol_per_mol', 'fraction')
# The unit vocabulary of each quantity: the units a record may carry. A spread has the units of its quantity.
UNITS = {'productive_fraction': FRACTION_UNITS, 'productive_fraction_spread': FRACTION_UNITS, 'stoichiometric_ratio': RATIO_UNITS, 'stoichiometric_ratio_spread': RATIO_UNITS,
         'nucleotides_per_product': ('mol_per_mol',), 'nucleotides_per_product_spread': ('mol_per_mol',), 'stoichiometric_coefficient': ('mol_per_mol',),
         'nucleotide_rate': RATE_UNITS, 'basal_rate': RATE_UNITS, 'nucleotide_consumed_percent': ('percent',), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
