"""The extracted record of ONE in-gel activity staining experiment (type 'zymogram', class activity_rate).

An experiment type of the activity_rate class (drafted 2026-11-22 by the SOP, steps 1 to 3 and 5; owner to correct). It copies the shape of the first type of the
class, spectro_direct. The experiment: a protein sample (a purified enzyme, a cell or culture extract, a secreted fraction) is run on a polyacrylamide gel and the
ENZYME ACTIVITY is made visible in the gel itself. Two usual forms. In zymography proper (gelatin, casein or other protein zymography, also starch or other polymer
gels) the substrate is polymerised into the gel, the gel is run with SDS, the SDS is washed out with a non-ionic detergent so that the enzyme folds back, the gel is
incubated in a reaction buffer and then stained for the protein: the enzyme shows as a CLEARED band in the dark gel. In activity staining after a native gel
(dehydrogenases with a tetrazolium dye such as NBT and an electron carrier such as PMS, esterases with a naphthyl ester and a diazonium salt, phosphatases and others)
the gel is soaked in the substrate and the cofactor and a coloured product forms where the enzyme is: the enzyme shows as a COLOURED band. The result is QUALITATIVE: an
activity band is seen (or not seen) at a stated position of the gel, and sometimes its apparent mass is read against marker proteins. It gives no rate, no kcat and no
Km; a band intensity is never a rate. A fluorescent or colorimetric solution assay (spectro_direct, fluorogenic, stopped_colorimetric), an assay of a gel slice, and a gel
that only shows a protein stain are not this method.

What a leaf extraction holds for one such experiment: whether an activity band is seen at the position of the enzyme, the control lanes (the gel or the lane developed
without the substrate or the cofactor, a heat-treated or catalytically dead sample, the sample of a strain that lacks the gene, a known active enzyme as a positive
control, an inhibitor), the assignment of the band to the protein, the apparent mass of the band and the mass expected from the sequence, whether the enzyme is purified
and whether the substrate is the enzyme's own, and the number of independent experiments.

One experiment, or replicate experiments reported as one result, in the operand shape of the other records (value, unit, status, reason, measurement_keys,
source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and
never omitted.

What a zymogram shows and what can go wrong is what the form keeps. A band of activity shows that SOMETHING in the sample, at that position, acts on the substrate under
the conditions of the gel. The controls decide how much it means: a lane or gel developed without the substrate (or without the cofactor) must show no band (a
dehydrogenase stain can colour a band from a "nothing dehydrogenase" or from a non-enzymatic reducing agent), a heat-treated or catalytically dead sample must show no
band, and a known active enzyme must show a band on the same gel (without it an absent band says only that the stain did not work). In an extract, a band is assigned to
the protein by a second route (the band is missing in the sample of a strain that lacks the gene, or it is found at the mass of the protein and identified, for example by
mass spectrometry of the excised band or by an antibody on a duplicate gel); a band at the right apparent mass is weak support, because a gel gives a mass only to
about ten or twenty percent and other enzymes of that mass exist. A specific inhibitor that removes the band shows what kind of catalysis it is.

Record fields
-------------
version, experiment_type ('zymogram'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as decided
               2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized enzyme and no electrode (the gel
               holds the enzyme but it is not a surface reference), so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation
               reference, so the extraction leaves all four None.
quantities     band_mass          kDa     the apparent mass of the activity band, read against marker proteins
               expected_mass      kDa     the mass of the protein expected from its sequence (a subunit), as the passage gives it
               replicate_count    count   the number of replicate experiments (independent gels)
gel_kind       choice 'denaturing_renatured' (an SDS gel from which the SDS is washed out so that the enzyme folds back) or 'native' (no SDS); kept for the reviewer. No
               criterion rests on a choice (a choice holds no span in the merged record).
detection_kind choice 'cleared_band_in_substrate_gel', 'formazan_band_tetrazolium', 'azo_dye_band', 'fluorescent_band' or 'other_stain': how the activity is made visible;
               kept for the reviewer, no criterion rests on it.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only. Facts about a CONTROL
               are answered by the OUTCOME the passage states: yes is the standard met (the control lane is free of the band, the positive control shows its band),
               no is the passage stating the standard not met (a band in the control lane).
choice_support name -> support of each plain choice field (gel_kind, detection_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well its
quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the
topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader
does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go through
the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_zymogram_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'zymogram'
QUANTITIES = ('band_mass', 'expected_mass', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
GEL_KINDS = ('denaturing_renatured', 'native')
DETECTION_KINDS = ('cleared_band_in_substrate_gel', 'formazan_band_tetrazolium', 'azo_dye_band', 'fluorescent_band', 'other_stain')
CHOICES = {'gel_kind': GEL_KINDS, 'detection_kind': DETECTION_KINDS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'activity_band_detected': YES_NO, 'no_substrate_control_clean': YES_NO, 'inactive_sample_clean': YES_NO, 'positive_control_band_shown': YES_NO,
         'deletion_sample_lacks_band': YES_NO, 'band_assigned_to_target': YES_NO, 'inhibitor_abolishes_band': YES_NO, 'native_substrate': YES_NO,
         'purified_enzyme': YES_NO, 'independent_replicates': YES_NO}

# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'band_mass': ('kDa',), 'expected_mass': ('kDa',), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
