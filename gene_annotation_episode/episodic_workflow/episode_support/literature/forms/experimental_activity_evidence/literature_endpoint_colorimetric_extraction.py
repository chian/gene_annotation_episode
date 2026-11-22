"""The extraction of ONE stopped colorimetric end-point experiment (type 'endpoint_colorimetric': the reaction is stopped after a set time, a colour reagent
turns a product class into a colour, and the share of the substrate converted or the amount of product is read from a standard curve) from one chunk of
text, derived from the grader's input form (``literature_endpoint_colorimetric_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand.
The things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_colorimetric_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model
and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread kind and the reagent class);
the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are
given by the caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_colorimetric_record import (
    EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, QUANTITIES, REAGENT_CLASSES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
REAGENT_CLASS = 'reagent_class'
CHOICES = {SPREAD_KIND: SPREAD_KINDS, REAGENT_CLASS: REAGENT_CLASSES}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's question, never a
# statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('standard_curve_points', 'replicate_count')

MEANING = {
    'conversion': 'The share of the substrate that was converted at the end point of the test reaction, as the passage gives it: a percent (62 percent gives 62 with the unit percent) or a proportion between 0 and 1 (0.62 with the unit fraction), not corrected for any control. The share converted in a control, a no-enzyme reaction, an inactive-enzyme reaction or a mutant is not this field. A share that the passage gives already after the control was taken away is not this field (it is net_conversion). A yield of another product, a percent of an activity and a percent of protein are not this field.',
    'conversion_spread': 'The reported uncertainty of the conversion (the number after a plus-minus sign, a standard error or a standard deviation), in the unit of the conversion.',
    'control_conversion': 'The share of the substrate that was converted, or the apparent conversion that the colour reagent showed, in the paper\'s own control reaction (the reaction without the enzyme, with an inactive or heat-treated enzyme, or stopped at time zero), as the passage gives it, in percent or as a proportion. The conversion of the test reaction is not this field.',
    'net_conversion': 'The share of the substrate converted that the passage itself gives after the value of its control was taken away (also called the net, the corrected or the above-control conversion), in percent or as a proportion. Do not subtract one number from another yourself: when the passage gives only the test value and the control value this field is unavailable.',
    'net_conversion_spread': 'The reported uncertainty of the net conversion, in the unit of the net conversion.',
    'product_concentration': 'The concentration of the product (or of the product class that the colour reagent measures, for example released phosphate, reducing ends, a thiol or ammonia) in the reaction mixture at the end point of the test reaction, as the passage gives it, in nM, uM or mM. An amount per well or per tube is not a concentration (it is product_amount). The product amount that the standard curve gave inside the colour mixture is not this field unless the passage says it is the concentration in the reaction. The concentration of a standard is not this field.',
    'product_concentration_spread': 'The reported uncertainty of the product concentration, in the unit of the product concentration.',
    'product_amount': 'The amount of the product (or of the product class that the colour reagent measures) formed in the test reaction at the end point, as the passage gives it, in pmol, nmol or umol (an amount per reaction, per tube or per well). A concentration is not an amount (it is product_concentration). Do not work out an amount from a concentration and a volume yourself.',
    'reaction_volume': 'The volume of the reaction mixture in which the product amount was formed, as the passage gives it, in uL or mL. The volume of the colour reagent, of the stop solution or of the final colour mixture is not this field.',
    'substrate_initial': 'The concentration of the substrate at the start of the test reaction (the amount that the share converted refers to), as the passage gives it, in nM, uM or mM. The Km of the substrate and a concentration of a standard are not this field.',
    'endpoint_time': 'The time that the test reaction ran before it was stopped or read (the incubation time of the end point), as the passage gives it, in s, min or h. The time allowed for the colour to develop after the colour reagent was added, a pre-incubation time and the time points of a time course are not this field.',
    'product_read_on_curve': 'The largest amount or concentration of the product (or product class) that the standard curve gave for a test sample, only when the passage says it, in the same terms and unit as the standard curve is stated (a concentration in nM, uM or mM, or an amount in pmol, nmol or umol per tube or well). It is the value read from the curve, not the concentration in the reaction mixture when the sample was diluted into the colour reagent.',
    'standard_curve_low': 'The lowest standard (lowest non-zero amount or concentration) of the product standard curve (the standards used to turn the colour into an amount of product, for example a phosphate, glucose or ammonium standard series), as the passage gives it, in a concentration unit (nM, uM, mM) or an amount unit (pmol, nmol, umol). A blank of zero is not a standard of this field.',
    'standard_curve_high': 'The highest standard of the product standard curve (the standards used to turn the colour into an amount of product), as the passage gives it, in a concentration unit (nM, uM, mM) or an amount unit (pmol, nmol, umol).',
    'standard_curve_points': 'The number of standards (different amounts or concentrations) of the product standard curve, as the passage gives it as a whole number, counting a zero blank only when the passage counts it.',
    'replicate_count': 'The number of replicate experiments the passage reports for the end point (a whole number). Wells or tubes read from one reaction mixture are not this field.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the conversion and of the product concentration) are: standard_error, standard_deviation or confidence_interval. A passage that gives a plus-minus sign without naming what it is does not state it.',
    REAGENT_CLASS: 'The class of the colour-forming reagent or method that turned the product into a measured colour: malachite_green_phosphate (malachite green or molybdate for phosphate), reducing_sugar (DNS or a similar reducing-sugar reagent), thiol (DTNB or a similar thiol reagent), hydroxamate (a ferric hydroxamate reagent), ammonia (Nessler or Berthelot reagent), chromogenic_product (a coloured product read after the reaction was stopped) or other_colorimetric (any other colour reagent).',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme was measured (a reaction mixture of substrate and buffer incubated without enzyme and taken through the colour reagent, or a substrate-only blank) (yes), or says it was not (no). A control with an inactive enzyme is not this fact (it is the inactive_enzyme_control fact).',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured (yes), or says it was not (no). A control without any enzyme is not this fact (it is the no_enzyme_control fact).',
    'no_substrate_control': 'Whether the passage says a control with the enzyme and without the substrate was measured (so that colour from the enzyme preparation or its buffer, for example phosphate carried over with the protein, would show) (yes), or says it was not (no).',
    'zero_time_sample': 'Whether the passage says a zero-time sample was measured: a reaction in which the stop or the colour reagent was added before the incubation (yes), or says it was not (no).',
    'standard_curve_in_buffer': 'Whether the passage says the product standard curve was made in the reaction buffer (the same buffer and components as the reactions), or says the standards were taken through the same steps as the samples (yes), or says it was made in water or another solvent (no).',
    'reagent_interference_checked': 'Whether the passage says it was checked that a component of the reaction (the buffer, a salt, a reducing agent, a detergent, the substrate, the enzyme preparation) does not itself give colour with the reagent or change the colour of the product (yes), or says that such a component interferes and was not accounted for (no). A passage that only names the buffer does not state it.',
    'product_rises_with_enzyme': 'Whether the passage says the product (or the share converted) was shown to rise with the amount of enzyme, or with the incubation time (yes), or says it did not (no). A single enzyme amount at a single time does not state it.',
    'product_identified_independently': 'Whether the passage says the product was identified by another measurement than the colour reagent (for example chromatography, mass spectrometry, NMR or a second, specific enzyme assay) (yes), or says the product was not identified and only the colour was measured (no). The name of the reagent alone does not state it.',
    'reaction_stopped': 'Whether the passage says the reaction was stopped at a stated moment before the colour was read (by the colour reagent itself, an acid, heat, a chelator or another quench) (yes), or says that it was not stopped and ran on while the colour developed (no).',
    'same_time_for_compared_arms': 'Whether the passage says the test reaction and the reactions it is compared with (the controls, the other enzymes or the other conditions) were incubated and read for the same time (yes), or says they were not (no).',
    'initial_substrate_determined': 'Whether the passage says the amount or concentration of the substrate at the start was measured (assayed, titrated or checked), rather than only weighed out or pipetted from a nominal stock (yes), or says that it is only nominal (no).',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate substrate (yes), or says it is a surrogate (no).',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (yes), or says it was a cell lysate, an extract or whole cells (no).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture (yes), or says that they were not (no).',
    'conversion_detected_above_control': 'Whether the passage says that conversion of the substrate (formation of the product) was detected above the paper\'s own control, blank or detection limit (yes), or says that no conversion above the control, blank or detection limit was detected (no). A passage that only reports a measured number and says nothing in words does not state it.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices (spread kind, reagent class), the facts."""
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
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
    """The record of ``literature_endpoint_colorimetric_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
