"""The extracted record of ONE isotope-label flow experiment (type 'coupling_isotope_label', class reaction_coupling).

A type of the reaction_coupling class (drafted 2026-11-22 by the SOP, steps 1 to 3 and 5; DRAFT for the owner to correct). The experiment: one enzyme is given a
substrate (or a cofactor, or the medium) that carries a heavy or radioactive label, and the product is read for the label. The labelled source is molecular
oxygen (18O2), water (H2 18O), a substrate carbon or nitrogen (13C, 15N), or a double radiolabel (14C in the substrate and 3H in the cofactor). The product is read by
mass spectrometry (the mass of the product ion moves up by the mass difference of the label), by scintillation counting, or by NMR. The link it shows is the origin of
an atom: how much of the claimed product carries the label of the claimed source. A labelled product from 18O2 and not from H2 18O says the reaction is an oxygenase
and not a hydrolase; 13C or 15N carried from the substrate shows the atom transfer the claimed reaction needs; a 3H of the cofactor that arrives in a 14C product shows
a hydride transfer. This is the most indirect type of the class: the label shows where an atom came from, not how much of the consumed partner ended in the product.
Past work: none found in the places searched; the oxygenase classics (18O2 incorporation into catechol and phenol products, Hayaishi and Mason, 1955) are from memory.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason;
it is never 0 and never omitted.

Only the experiment in which the product is read for the label of a named source is this type. A passage that only says the substrate was labelled, or that gives the
mass of a product without a labelled run beside an unlabelled one, gives no label share; the matching fields stay unavailable.

Record fields
-------------
version, experiment_type ('coupling_isotope_label'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as decided
               2026-11-22 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; the labelled and the unlabelled run come from one preparation,
               so they are one dependence unit; nothing is immobilized and nothing is on a surface, so immobilized_preparation_ref and surface_ref stay None. No
               passage states a preparation reference, so the extraction leaves all four None.
quantities     The share of the product that carries the label of the claimed source, two ways, each with the spread the passage gives for it:
                 label_incorporation (and _spread)   fraction or percent   the share of the product molecules (or of the labelled position) that carry the label
                                                                           of the claimed source, as the passage states it (percent incorporation, percent
                                                                           enrichment of the product)
                 label_retention (and _spread)       fraction or percent   for a double label, the ratio of the two labels in the product as a share of their
                                                                           ratio in the starting mixture (a transferred 3H over the 14C of the same product,
                                                                           relative to the starting mixture); 100 percent is full transfer
               the atoms:
                 label_atoms_per_product             atoms_per_molecule    the number of label atoms in a LABELLED product molecule, as the passage states it
                                                                           (the mass shift in label atoms: one 18O, two 18O), not averaged over the unlabelled
                                                                           molecules
                 label_atoms_expected                atoms_per_molecule    the number of label atoms the passage's own reaction account puts in the product
               what decides how far the label can be trusted:
                 label_purity                        percent or fraction   the isotopic purity (atom percent enrichment) of the labelled source
                 label_in_control                    fraction or percent   the share of the product that carries the label in the control without the enzyme or
                                                                           with an inactive enzyme
               and
                 replicate_count                     count                 the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
label_source   'oxygen_gas', 'water', 'carbon_13', 'nitrogen_15', 'radiolabel' or None: which source carries the label. Recorded for the reviewer; no criterion reads it.
readout        'mass_spectrometry', 'scintillation_counting', 'nmr' or None: how the label was read. Recorded for the reviewer; no criterion reads it.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, label_source, readout), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

The record holds no criterion that rests on a choice: the choices are for the converter's variance (spread_kind) and for the reviewer; everything a criterion reads is a
quantity or a fact with its own quote.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well its
quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the
topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader
does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go through
the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_coupling_isotope_label_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'coupling_isotope_label'
QUANTITIES = ('label_incorporation', 'label_incorporation_spread', 'label_retention', 'label_retention_spread', 'label_atoms_per_product', 'label_atoms_expected',
              'label_purity', 'label_in_control', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
LABEL_SOURCES = ('oxygen_gas', 'water', 'carbon_13', 'nitrogen_15', 'radiolabel')
READOUTS = ('mass_spectrometry', 'scintillation_counting', 'nmr')
# The plain choice fields: name -> its fixed vocabulary. Each is named in the record's choice_support.
CHOICES = {'spread_kind': SPREAD_KINDS, 'label_source': LABEL_SOURCES, 'readout': READOUTS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'unlabelled_control': YES_NO, 'back_exchange_control': YES_NO, 'label_position_determined': YES_NO, 'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO,
         'product_identified_by_mass_shift': YES_NO, 'natural_abundance_corrected': YES_NO, 'same_preparation': YES_NO, 'same_window': YES_NO, 'native_substrate': YES_NO,
         'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'label_detected_in_product': YES_NO}

SHARE_UNITS = ('fraction', 'percent')
ATOM_UNITS = ('atoms_per_molecule',)
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'label_incorporation': SHARE_UNITS, 'label_incorporation_spread': SHARE_UNITS, 'label_retention': SHARE_UNITS, 'label_retention_spread': SHARE_UNITS,
         'label_atoms_per_product': ATOM_UNITS, 'label_atoms_expected': ATOM_UNITS, 'label_purity': ('percent', 'fraction'), 'label_in_control': SHARE_UNITS,
         'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
