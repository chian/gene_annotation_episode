"""The extraction of ONE size-exclusion chromatography (SEC, gel filtration), with or without multi-angle light scattering (SEC-MALS), complex experiment (two proteins are mixed and run on a size-exclusion column; the complex elutes earlier than either component alone, in a co-elution peak that shows both partners on SDS-PAGE; SEC-MALS gives the molar mass of the complex; mostly qualitative or semi-quantitative, occasionally an apparent KD from peak areas) from one
chunk of text, derived from the grader's input form (``literature_sec_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down and EMSA extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: an SEC is mostly qualitative or semi-quantitative, so the apparent KD and its spread are fields that are mostly
unavailable, and the complex peak itself is a fact. The reported numbers are the elution volumes (of the complex, of the component that elutes earlier alone and of the one that
elutes later alone) and the shift between them, the molar masses by MALS (of the complex and of the larger and the smaller component alone) and the mass the complex should have, the
stoichiometry, the polydispersity, the flow rate and the temperature, the injected concentration and volume, the salt of the running buffer, the incubation before the injection and the
number of independent experiments; the column type, the detector and the spread kind are choices; and the facts are the controls and the results of this method (the complex peak,
each component run alone, SDS-PAGE of the complex peak, the free peak shrinking with the titration, the MALS mass matching the complex, calibration of the column, a buffer that rules
out resin interaction, a complex stable on the column, no aggregation, a single-component control, independent experiments, one estimate method). Every number must be above 0. Fields not
extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller, and the two components and the dataset
(``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import (
    COLUMN_TYPES, DETECTIONS, EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
COLUMN_TYPE = 'column_type'
DETECTION = 'detection'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
CHOICES = {COLUMN_TYPE: COLUMN_TYPES, DETECTION: DETECTIONS, SPREAD_KIND: SPREAD_KINDS}

MEANING = {
    'kd': 'The apparent equilibrium dissociation constant of the two proteins, as the passage reports it under the name KD or Kd (apparent Kd, dissociation constant) from a titration of the mixture in which the areas or heights of the complex peak and of the free-component peak were read, for the experiment described in the passage. A KD that the passage cites as a known or previously reported property of the proteins, or one that comes from another method (for example fluorescence, MST or NMR titrations, which a passage on size-exclusion chromatography may also mention), rather than from the size-exclusion experiment described, is not stated: leave it unavailable. A concentration at which a complex was seen is not this field. When the passage gives KD values for several pairs or conditions without saying which one is the result, leave it unavailable.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'complex_elution_volume': 'The elution volume at the peak of the complex (the mixture of the two proteins), in millilitres, as the passage gives it as a volume. An elution time (retention time in minutes), a mass read from the peak and the elution volume of a component alone are not this field: a time is not offered, so leave it unavailable with the reason unit_not_in_vocabulary. A passage that says only that the mixture eluted earlier does not state a volume.',
    'component_elution_volume_earlier': 'The elution volume at the peak, in millilitres, of the component that elutes earlier (the larger one) when it is run alone on the column, as the passage gives it as a volume for that component. The elution volume of the mixture is not this field, and a passage that says only that the components eluted later than the mixture does not state a volume.',
    'component_elution_volume_later': 'The elution volume at the peak, in millilitres, of the component that elutes later (the smaller one) when it is run alone on the column, as the passage gives it as a volume for that component. The elution volume of the mixture is not this field.',
    'elution_volume_shift': 'The shift of the elution volume, in millilitres, as the passage gives it as one number: how much earlier the complex peak elutes than the component that elutes earlier alone. A shift you would have to calculate from two elution volumes, a shift in minutes, and a statement that the mixture eluted earlier without a number are not this field.',
    'complex_mass_measured': 'The molar mass of the complex peak measured by multi-angle light scattering (MALS), in kilodaltons, as the passage gives it for the mixture of the two proteins. A mass of a component alone, a mass read from the elution volume against standards, and a mass the complex is expected to have are not this field. When the passage gives several masses of the mixture under different conditions (for example with added ions) without saying which one is the result, leave it unavailable.',
    'complex_mass_theoretical': 'The molar mass, in kilodaltons, that the complex should have (the theoretical or calculated mass of the complex, or the sum of the sequence masses of its components), as the passage gives it as one number for the complex. The theoretical mass of one component, and the masses of the components of a complex that you would have to add up, are not this field.',
    'component_mass_measured_larger': 'The molar mass measured by MALS, in kilodaltons, of the component that is the larger of the two proteins (larger by its mass, as the passage states it or makes plain) when it is run alone, as the passage gives it as one number. A theoretical mass, a mass of the mixture, and masses given for the same component at several concentrations or conditions without saying which one is the result are not this field.',
    'component_mass_measured_smaller': 'The molar mass measured by MALS, in kilodaltons, of the component that is the smaller of the two proteins (smaller by its mass, as the passage states it or makes plain) when it is run alone, as the passage gives it as one number. A theoretical mass, a mass of the mixture, and masses given for the same component at several concentrations or conditions without saying which one is the result are not this field.',
    'stoichiometry_ratio': 'The molar ratio of the two components in the complex, as the passage states it for the complex (first named component over second named: a 1:1 complex or a heterodimer made of one of each is 1, a 2:1 complex is 2, a 1:2 complex is 0.5), as a number. The ratio in which the proteins were mixed is not the stoichiometry of the complex, and neither is an oligomeric state of one protein alone (a homodimer). A passage that gives no ratio and names no composition does not state it.',
    'polydispersity': 'The polydispersity of the peak, the ratio of the weight-average to the number-average molar mass (Mw/Mn), as the passage gives it as a number. A molar mass, a percent of aggregate and the width of a peak are not this field.',
    'flow_rate': 'The flow rate of the column, as the passage gives it in millilitres per minute. A rate in another unit is not offered here: leave it unavailable with the reason unit_not_in_vocabulary.',
    'run_temperature': 'The temperature at which the column was run, as a number. A passage that says only room temperature or the cold room does not state it, and the temperature of a centrifugation or of a pre-incubation of the proteins is not this field.',
    'loaded_concentration': 'The concentration of the mixture that was injected onto the column, as the passage gives it as a molar concentration (the concentration of each protein, or of the protein that is held at a constant concentration in a titration; the highest one when it is titrated). A concentration in mass per volume (for example mg/mL) is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A concentration in the peak after dilution on the column, the concentration of a component run alone, and injected concentrations that the passage gives for several runs without saying which one is the result are not this field.',
    'loaded_volume': 'The volume of the sample that was injected onto the column (the loop volume), as the passage gives it in microlitres or millilitres. The volume of the column and the volume of a fraction are not this field.',
    'salt_concentration': 'The concentration of monovalent salt (for example NaCl or KCl) in the running buffer of the column, as the passage gives it in millimolar or molar. A divalent cation (for example CaCl2 or MgCl2) added to test its effect on the interaction, the concentration of a buffer substance such as Tris, and the salt of a protein storage buffer are not this field.',
    'incubation_time': 'How long the two proteins were incubated together before the injection, as the passage gives it as a time. A time of a column run, of the elution and of a centrifugation of the sample is not this field, and neither is a time that is only a range of times tried.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days or preparations, or independent injections reported as replicates), as a whole number. Fractions of one run and injections at different concentrations are not this field.',
    COLUMN_TYPE: 'The kind of size-exclusion column, as the passage names its resin: a Superdex column (for example Superdex 200 Increase 10/300 GL), a Superose column, an SRT SEC column, or another one. A column of another kind of chromatography (ion exchange, affinity) is not a size-exclusion column.',
    DETECTION: 'The detector on which the passage says the elution or the result was read: absorbance at 280 nm, absorbance at 260 nm, refractive index, light scattering (MALS), or fluorescence, or another detector. When the passage names several, give the one on which it says the result of this field of the experiment was read; a passage that does not name a detector does not state it. The quote must be the words that name the detector or the technique, copied exactly from the passage; the name of a detector or technique usually occurs several times in a passage, so take a quote that includes the distinctive words of the one sentence that names it, and check that it occurs once.',
    SPREAD_KIND: 'What the uncertainty given in the kd_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    'complex_peak_detected': 'Whether the passage says that a complex peak was seen: the mixture of the two proteins eluted earlier than each of the components run alone, as a co-eluting peak (yes), or says that no such peak was seen and the mixture eluted as the separate components (no). A peak that eluted earlier but that the passage ascribes to aggregation, and an interaction that the passage shows only with another method, are not this fact.',
    'components_run_alone': 'Whether the passage says that each of the two components was also run alone on the same column, so that the elution of the mixture is compared with the elution of each component (yes), or says that they were not (no). A component that is run alone on another column is not this fact.',
    'complex_peak_analysed_by_sds_page': 'Whether the passage says that the fractions of the complex peak were analysed by SDS-PAGE (or by another gel or mass spectrometry) and that both proteins were found in them (yes), or says that only one protein was found or that the peak was not analysed (no).',
    'free_peak_decreases_with_titration': 'Whether the passage says that, when one component was increased, the peak of the free (excess-free) component got smaller and the complex peak larger, as a stoichiometric or progressive binding (yes), or says that the peaks did not change (no).',
    'mals_mass_matches_complex': 'Whether the passage says that the molar mass of the complex peak by MALS agrees with the mass expected for the complex (a heterodimer, a 1:1 complex), as consistent, in agreement or matching the calculated mass (yes), or says that it does not agree (no). A mass given with no statement of what it is compared with does not state it.',
    'column_calibrated_with_standards': 'Whether the passage says that the column was calibrated with protein standards of known size (a calibration curve of elution volume), or that standards were run (yes), or says that it was not (no).',
    'buffer_rules_out_resin_interaction': 'Whether the passage says that the running buffer had enough ionic strength to prevent interaction of the proteins with the resin, or that no interaction with the matrix was seen (yes), or says that the proteins interacted with the resin (no). A salt concentration with no statement about the resin is not this fact.',
    'complex_stable_on_column': 'Whether the passage says that the complex stayed assembled during the column run despite the dilution (the concentrations were above the KD, or the complex was stable on the column, or it co-eluted as one peak with no dissociation) (yes), or says that it dissociated on the column or that the concentrations were below the KD (no). A complex that is only said to form, with no statement of its stability on the column, is not this fact.',
    'aggregation_absent': 'Whether the passage says that no aggregates or higher-order species were present in the peaks (monodisperse, no aggregation, a polydispersity close to 1) (yes), or says that aggregates were present (no). A single peak, with no statement of aggregation or of a polydispersity, is not this fact.',
    'single_component_control_done': 'Whether the passage says that a control in which one partner was replaced by a non-binding mutant or by an unrelated protein did not co-elute or shift (yes), or says that it did (no). Running each component alone is not this fact.',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days or preparations) rather than injections of one sample (yes), or says that they were not (no).',
    'single_estimate_method': 'Whether the passage says that the KD, or the binding of the two proteins, was determined by size-exclusion chromatography only (yes), or says that the KD or the binding of these two proteins was also determined by another method (no). Another method that the passage mentions for a different purpose (for example an observation of the oligomerization of one protein) is not this fact, and a passage that reports no KD and says nothing about other methods for the binding does not state it. A sentence that only describes the method that was used (for example that SEC-MALS was used to assess an interaction) does not say that no other method was used: yes needs the passage to say that this method alone was used.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (column type, detector, spread kind), the facts."""
    return (*QUANTITIES, *CHOICES, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(CHOICES[name])} if name in CHOICES else
             {'enum': list(STATABLE[name])})
    properties = {'status': {'enum': ['stated', 'unavailable']}, 'value': _nullable(value)}
    if name in UNITS:
        properties['unit'] = _nullable({'enum': list(UNITS[name])})
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': {**_nullable({'enum': list(SUPPORTS)}), 'description': SUPPORT_MEANING}, 'reason': _nullable({'enum': list(REASONS)})})
    return {'type': 'object', 'additionalProperties': False, 'description': MEANING[name],
            'required': list(properties), 'properties': properties}


def answer_schema():
    """The JSON schema of an extraction answer: one object per field, named as in the form."""
    schema = {name: _field_schema(name) for name in field_names()}
    return {'type': 'object', 'additionalProperties': False, 'required': list(schema), 'properties': schema}


class ExtractionRefused(ValueError):
    """The answer does not satisfy the answer schema or a quote is not at its span."""


def _refuse(name, code, detail=None):
    raise ExtractionRefused(name + ':' + code + ('' if detail is None else ':' + str(detail)))


def quote_span(chunk, quote):
    """The (start, end) byte span of ``quote`` in ``chunk``, counted in UTF-8 bytes from the first byte of the chunk
    (end is the byte after the last). None unless the quote occurs exactly once."""
    at = chunk.find(quote)
    if not quote or at < 0 or chunk.find(quote, at + 1) >= 0:
        return None
    start = len(chunk[:at].encode('utf-8'))
    return start, start + len(quote.encode('utf-8'))


def _quote(name, item, chunk):
    if not item['quote'] or item['quote'] not in chunk:
        _refuse(name, 'quote_is_not_in_the_chunk')
    if quote_span(chunk, item['quote']) is None:
        _refuse(name, 'quote_occurs_more_than_once', 'make_the_quote_longer_so_it_occurs_once')


def validate_answer(answer, chunk):
    """Raise ``ExtractionRefused`` unless ``answer`` satisfies ``answer_schema()`` and every stated field's quote
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one
    carries none. Returns ``answer``."""
    errors = sorted(Draft202012Validator(answer_schema()).iter_errors(answer), key=lambda error: list(error.path))
    if errors:
        _refuse('.'.join(str(part) for part in errors[0].path) or 'answer', 'schema', errors[0].message[:200])
    for name in field_names():
        item = answer[name]
        carried = ('value', 'quote', 'support') + (('unit',) if name in UNITS else ())
        if item['status'] == 'unavailable':
            if item['reason'] is None or any(item[key] is not None for key in carried):
                _refuse(name, 'unavailable_has_a_reason_and_nothing_else')
            continue
        if item['reason'] is not None or any(item[key] is None for key in carried):
            _refuse(name, 'stated_has_value_unit_quote_span_and_no_reason')
        if name in QUANTITIES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_sec_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
    in its source: each quote's span is found in the chunk and recorded at its offset in the source. A value not stated is an
    'unavailable' operand with its reason, never 0; a fact not stated is 'unknown'."""
    spans, refs = {}, {}
    for name in field_names():
        if answer[name]['status'] == 'stated':
            refs[name] = 'span_' + name
            spans[refs[name]] = _span(chunk, chunk_offset, answer[name])

    def operand(name):
        item = answer[name]
        if item['status'] == 'unavailable':
            return unavailable(UNITS[name][0], name, item['reason'])
        return point(item['value'], item['unit'], name, [refs[name]], support=item['support'])

    def choice(name):
        return answer[name]['value'] if answer[name]['status'] == 'stated' else None

    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
