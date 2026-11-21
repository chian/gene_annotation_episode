"""The extraction of ONE cellular thermal shift assay (CETSA: the melt curve with its shift of the melting temperature, and the isothermal dose-response format ITDR-CETSA with its EC50; thermal proteome profiling only where a paragraph reports the target engagement of one target) experiment (a compound is added to intact cells, a lysate or a tissue, the sample is heated, and the target protein that stays soluble is read by western blot, AlphaScreen or mass spectrometry; a ligand that binds the target stabilises it, so the melt curve shifts to a higher temperature, or at one temperature the soluble fraction rises with the compound concentration; mostly a qualitative statement of target engagement, occasionally an EC50 read as an apparent affinity) from one
chunk of text, derived from the grader's input form (``literature_cetsa_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a CETSA is mostly qualitative, so the EC50 and its spread are fields that are mostly
unavailable, and the engagement itself is a fact. The reported numbers are the melting temperatures without and with the compound and their shift (in degrees Celsius), the one temperature of an ITDR, the heating time,
the standard deviation of the melting temperature, the ends of the temperature range and the number of temperatures, the ends of the compound concentration series and their number, the time of the compound incubation and the number of independent experiments; the sample, the format, the readout and the spread kind are choices; and the facts are the controls and the results of
this method (a target engagement, a vehicle control, a loading control, a melt curve, an isothermal temperature in the transition, a dose dependence, a negative compound, a specificity control, a viability check, a control of the total target, independent experiments, whether the scatter of the Tm is between independent experiments). Every number must be above 0 (the shift of the melting temperature is the
stabilisation: a passage that reports no shift or a lowering of the melting temperature states the fact target_engagement_shown as no, or leaves the shift unavailable). Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the ligand, the target and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_cetsa_record import (
    EXPERIMENT_FORMATS, EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, QUANTITIES, READOUTS, SAMPLE_FORMATS, SPREAD_KINDS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SAMPLE_FORMAT = 'sample_format'
EXPERIMENT_FORMAT = 'experiment_format'
READOUT = 'readout'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('temperature_count', 'concentration_count', 'replicate_count')
CHOICES = {SAMPLE_FORMAT: SAMPLE_FORMATS, EXPERIMENT_FORMAT: EXPERIMENT_FORMATS, READOUT: READOUTS, SPREAD_KIND: SPREAD_KINDS}

MEANING = {
    'engagement_ec50': 'The concentration of the compound that gives half of the maximal thermal stabilisation of the target in the isothermal dose-response CETSA (ITDR-CETSA, ITDRF-CETSA: the compound concentration is varied at one heating temperature), as the passage reports it under the name EC50 (or as an apparent affinity or apparent KD that it derives from that dose-response), for the one compound and the one target that the passage reports, as one number. An IC50 of the loss of an agonist-induced stabilisation, an EC50 or IC50 of a functional or reporter assay or of another method, a KD that the passage cites as known from earlier work, and a concentration at which a shift was seen are not this field. When the passage gives EC50 values for several compounds, or for several conditions, without saying which one is the result for the target and the compound the passage is about, leave it unavailable.',
    'engagement_ec50_spread': 'The reported uncertainty of the EC50 given in the engagement_ec50 field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value (for example the plus-minus of a melting temperature) is not this field.',
    'tm_vehicle': 'The melting temperature Tm (the temperature at which half of the target is denatured and lost from the soluble fraction), in degrees Celsius, of the target in the control sample without the compound (the vehicle, DMSO or the untreated sample), as the passage gives it as one number. A melting temperature with the compound, a temperature of an isothermal experiment, and values for several samples or conditions without saying which one is the control of the result are not this field.',
    'tm_ligand': 'The melting temperature Tm, in degrees Celsius, of the target in the sample with the compound, as the passage gives it as one number. The melting temperature of the control without the compound, the shift of the melting temperature, and values for several compounds or conditions without saying which one is the result are not this field.',
    'tm_shift': 'The shift of the melting temperature of the target by the compound (the thermal stabilisation, delta Tm or delta Tagg), in degrees Celsius, as the passage gives it as one number above 0 (a value given with a plus-minus is the number before it). A shift to a lower temperature or no shift is not stated here: leave it unavailable. A shift that the passage gives for several compounds or conditions without saying which one is the result, and a difference between two melting temperatures that you would have to calculate yourself, are not this field.',
    'tm_spread': 'The reported scatter of the melting temperature Tm over replicates, as a standard deviation, in degrees Celsius, as the passage gives it as one number (for example the plus-minus after a Tm that the passage says is a standard deviation). A standard error, a range and a confidence interval are not this field, and a plus-minus whose kind the passage does not state is not this field either. The uncertainty of the EC50 is the engagement_ec50_spread field, not this one.',
    'isothermal_temperature': 'The one temperature, in degrees Celsius, at which the samples of the isothermal dose-response CETSA were heated (the heat shock of the ITDR), as the passage gives it as one number. A single temperature of an ordinary melt curve, the temperature of the incubation with the compound (for example 37 degrees), and several different temperatures are not this field.',
    'heating_time': 'How long the samples were heated at each temperature (the heat shock), as the passage gives it in seconds or minutes. The time of the incubation with the compound, of the cooling and of the centrifugation are not this field.',
    'temperature_lowest': 'The lowest temperature, in degrees Celsius, of the temperature range of the melt curve (the temperatures at which the samples were heated), as the passage gives it as a number. A passage that gives only one heating temperature, or the temperature of the incubation with the compound, does not state it.',
    'temperature_highest': 'The highest temperature, in degrees Celsius, of the temperature range of the melt curve (the temperatures at which the samples were heated), as the passage gives it as a number. A passage that gives only one heating temperature does not state it.',
    'temperature_count': 'The number of different temperatures at which the melt curve was measured, as the passage gives it as a whole number. The number of concentrations, of compounds, of replicates and of cell lines is not this field.',
    'compound_concentration_lowest': 'The lowest concentration of the compound of the series that was tested (the compound with the target the passage is about), as the passage gives it as a molar concentration (the smallest one when several are given). A concentration in mass per volume (for example ug/mL) is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one compound concentration does not state a lowest one.',
    'compound_concentration_highest': 'The highest concentration of the compound of the series that was tested (the compound with the target the passage is about), as the passage gives it as a molar concentration (the largest one when several are given). A concentration in mass per volume (for example ug/mL) is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one compound concentration does not state a highest one.',
    'concentration_count': 'The number of different compound concentrations at which the dose-response was measured, as the passage gives it as a whole number (for example an eleven-point dilution series). The number of temperatures, of compounds, of cell lines and of replicates is not this field.',
    'compound_incubation_time': 'How long the cells, the lysate or the tissue were incubated with the compound before the heating, as the passage gives it in minutes or hours, as one number. The time of the heating, and the time points of a separate time-course experiment, are not this field.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days, passages of cells or preparations, or independent runs reported as replicates), as a whole number. Technical replicates in one plate and the number of concentrations or temperatures are not this field.',
    SAMPLE_FORMAT: 'What was heated, as the passage states it: intact cells (living cells treated with the compound and then heated, in-cell or intracellular engagement), a cell lysate (the compound added to the lysate and the lysate heated), or a tissue or an animal (tissue samples, organs, or cells from treated animals). A passage that does not name it does not state it.',
    EXPERIMENT_FORMAT: 'The format of the CETSA result the passage reports: a melt curve (the sample heated at a series of temperatures, a shift of the melting temperature), an isothermal dose-response (ITDR-CETSA: one temperature, a series of compound concentrations), or both. A passage that does not say which format gave the result does not state it.',
    READOUT: 'How the passage says the soluble target protein was read after the heating: a western blot, AlphaScreen (AlphaLISA), mass spectrometry (CETSA-MS, thermal proteome profiling), or another readout (for example ELISA, a split luciferase or an enzyme fragment complementation reporter). A passage that does not name the readout does not state it.',
    SPREAD_KIND: 'What the uncertainty given in the engagement_ec50_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    'target_engagement_shown': 'Whether the passage says that the compound stabilised the target against heat (a shift of the melt curve to higher temperatures, or more soluble target at the heating temperature with the compound), that is, a thermal stabilisation that shows target engagement of the compound with the protein the passage is about (yes), or says that the compound caused no stabilisation of the target (no). A binding that the passage shows only with another method, a stabilisation of a different protein, and a statement of the aim of the experiment are not this fact.',
    'vehicle_control_done': 'Whether the passage says that a control sample with the solvent of the compound (vehicle, DMSO) or without the compound was heated and read in the same way, as the comparison of the result (yes), or says that there was none (no). A passage needs to name such a control sample (vehicle, DMSO, untreated or no-compound control) to state it; a description of how the unbound protein behaves, or a phrase such as in the absence of the compound or of the agonist, without naming a control sample that was run, does not state it.',
    'loading_control_used': 'Whether the passage says that a loading control was used (a protein that does not change with the compound or the heating, an unheated sample, or the total protein, to show that the same amount of sample was loaded or read) (yes), or says that none was used (no).',
    'melt_curve_measured': 'Whether the passage says that the target was measured at several heating temperatures, as a melt curve or a temperature series, with the compound and without it (yes), or says that only one temperature was used (no). An isothermal dose-response at one temperature alone is not this fact.',
    'isothermal_temperature_in_window': 'Whether the passage says that the one temperature of the isothermal dose-response was chosen in the transition of the unbound target, where a part of the target is denatured without the compound and a part is stabilised with it (a temperature that gives a window between the unbound and the bound target) (yes), or says that it was not (no). A passage that gives the temperature and says nothing about why it was chosen does not state it.',
    'dose_dependent_shown': 'Whether the passage says that the stabilisation of the target changed with the concentration of the compound (a dose-response, a concentration-dependent stabilisation, an EC50) (yes), or says that it did not (no). A stabilisation seen at one concentration does not state it.',
    'negative_control_done': 'Whether the passage says that a negative compound (an inactive analogue, an inactive metabolite, or a compound that does not bind the target) did not stabilise the target (yes), or says that it did (no). A vehicle control is not this fact.',
    'specificity_control_done': 'Whether the passage says that a control showed that the stabilisation depends on the binding of the compound to the target (a mutant of the binding site that is not stabilised, a competition with a known ligand that removes the stabilisation, or a knockdown or knockout of the target) (yes), or says that the stabilisation did not depend on it (no). A competition of one ligand by another that is only the subject of the passage, without a statement that it is a control of the stabilisation, is not this fact.',
    'cell_integrity_checked': 'Whether the passage says that the viability, the integrity or the lysis of the cells, or the uptake or the accumulation of the compound in the cells, was checked, or that the compound did not change them (yes), or says that it was not checked or that it did change them (no).',
    'total_target_level_controlled': 'Whether the passage says that the total amount of the target protein (in an unheated sample or in the whole lysate) was measured and was not changed by the compound, so that the stabilisation is not a change of the expression of the target (yes), or says that it was changed (no).',
    'tm_spread_over_independent_experiments': 'Whether the passage says that the scatter of the Tm given in the tm_spread field is the scatter between independent experiments (separate experiments, days, cell passages or preparations) (yes), or says that it is only the scatter between technical replicates, wells, tubes or repeated blots of one sample (no). A scatter whose basis the passage does not say does not state it.',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days, cell passages or preparations) rather than wells or tubes of one sample (yes), or says that they were not (no).',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (sample format, experiment format, readout, spread kind), the facts."""
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
    """The record of ``literature_cetsa_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
