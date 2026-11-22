"""The extraction of ONE radiometric end-point conversion experiment (type 'endpoint_radiometric') from one chunk of text, derived from the
grader's input form (``literature_endpoint_radiometric_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_endpoint_radiometric_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the three plain
choices); the converter judges it.

Differences from the other types that come from the form: the three ways the class states an end point (a share converted, the share in the
paper's own control, the control-corrected share) and the product amount each have a spread field; a share converted can not exceed 100 percent
(or 1 as a fraction), so a larger number is refused and the model answers unavailable; every other number must be above 0.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_endpoint_radiometric_record import (
    EXPERIMENT_TYPE, FACTS, LABEL_ISOTOPES, PREPARATION_KEYS, QUANTITIES, SEPARATION_METHODS, SPREAD_KINDS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
LABEL_ISOTOPE = 'label_isotope'
SEPARATION_METHOD = 'separation_method'
CHOICES = {SPREAD_KIND: SPREAD_KINDS, LABEL_ISOTOPE: LABEL_ISOTOPES, SEPARATION_METHOD: SEPARATION_METHODS}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
# A share converted can not be larger than the whole: the largest value of each unit of these quantities (FIXED_BY_DEFINITION).
SHARES = ('conversion', 'control_conversion', 'net_conversion')
LARGEST_SHARE = {'percent': 100.0, 'fraction': 1.0}

MEANING = {
    'conversion': 'The share of the labelled substrate that was converted to the labelled product at the stated end time, as the passage gives it for the test reaction (the percent of the total radioactivity that was in the product, the percent of the substrate converted, or the same as a proportion of 1). It is a share of the whole and can not be above 100 percent. It is not a rate.',
    'conversion_spread': 'The reported uncertainty of that share converted (the number after a plus-minus sign, or a standard error or deviation), in the unit of the share converted.',
    'control_conversion': 'The same share converted that the passage gives for the paper\'s own control read at the same time (the reaction without the enzyme, with boiled or inactive enzyme, or the sample taken at time zero), in percent or as a proportion of 1.',
    'control_conversion_spread': 'The reported uncertainty of the share converted in that control, in the unit of the control\'s share.',
    'net_conversion': 'The share converted that the passage itself gives after the control has been subtracted (the corrected, net or enzyme-dependent share converted), in percent or as a proportion of 1. State it only when the passage gives that corrected number; never work it out from the share converted and the control.',
    'net_conversion_spread': 'The reported uncertainty of that control-corrected share converted, in the unit of the net share.',
    'product_amount': 'The amount or the concentration of labelled product that the passage says was formed in the reaction at the stated end time (for example 120 pmol, or 5 uM), in an amount unit (nmol, pmol, umol) or a concentration unit (nM, uM, mM). Radioactivity in cpm or dpm is not an amount.',
    'product_amount_spread': 'The reported uncertainty of the product amount, in the unit of the product amount.',
    'reaction_volume': 'The volume of the reaction mixture in which the labelled product was formed (the volume of the incubation, not the volume spotted or counted), in uL or mL.',
    'endpoint_time': 'The time at which the reaction was stopped and read (the incubation time of the end point), in s, min or h. If the passage gives several incubation times, the one of the stated result.',
    'counts_test': 'The radioactivity counted for the test reaction (the product fraction), as the passage gives it, in cpm, dpm or arbitrary units (a phosphorimager signal).',
    'counts_background': 'The radioactivity counted for the paper\'s own blank (the reaction without the enzyme, the substrate taken through the separation, or the empty region of the plate), in the same counting unit as the test counts.',
    'signal_over_background': 'How many times larger the counts of the test reaction are than the counts of the blank, when the passage gives that ratio itself (for example "20-fold above background"), as a fold.',
    'specific_radioactivity': 'The specific radioactivity of the labelled substrate as used in the reaction (radioactivity per amount of substrate, for example 55 mCi/mmol), in Ci/mmol, mCi/mmol, uCi/umol, cpm/pmol or dpm/pmol. The total radioactivity added (for example 0.1 uCi) is not a specific radioactivity.',
    'replicate_count': 'The number of replicate experiments the passage reports for this end point (a whole number).',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the shares converted and of the amount) are.',
    LABEL_ISOTOPE: 'The radioactive label of the substrate that the passage names (14C, 3H, 32P, 33P, 35S or 125I; other for another).',
    SEPARATION_METHOD: 'How the passage says the labelled product was separated from the labelled substrate before counting: thin-layer or paper chromatography, filter binding, ion exchange, precipitation, a trapped gas (for example 14CO2 in alkali), HPLC with a radioactivity detector, or a gel read by a phosphorimager; other for another way.',
    'no_enzyme_control_done': 'Whether the passage says a control reaction without the enzyme (a no-enzyme blank, a buffer-only incubation) was run and read at the same time.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (boiled or heat-denatured enzyme, or a catalytically dead mutant) was run.',
    'zero_time_sample_done': 'Whether the passage says a sample taken at time zero (the reaction stopped at once, or the substrate mixed with the enzyme and the stop solution together) was run through the separation.',
    'separation_control_done': 'Whether the passage says the labelled substrate alone (without the enzyme and without incubation) was taken through the separation and counted, to show how much label is carried over into the product fraction.',
    'reaction_stopped_before_analysis': 'Whether the passage says the reaction was stopped (quenched, with acid, base, heat, an inhibitor, EDTA or an organic solvent, or by freezing) before the product was separated, so that the stated time is the real end of the reaction.',
    'same_time_for_compared_arms': 'Whether the passage says the test and the control reactions (or the compared enzymes or conditions) were incubated for the same time.',
    'fraction_over_total_label': 'Whether the passage says the share converted was calculated over the total radioactivity of the same sample (substrate plus product), as opposed to counts of the product alone or a share over an amount that was not measured.',
    'conversion_depends_on_enzyme': 'Whether the passage says the conversion depends on the enzyme: it rises with the amount of enzyme or with the time, or it is absent or lower with the inactive enzyme, the mutant or an inhibitor (yes), or says that it does not (no).',
    'product_identified_by_standard': 'Whether the passage says the counted product was identified by an authentic standard (it runs or elutes with the standard) or by an independent identification such as mass spectrometry or NMR.',
    'label_in_product_position': 'Whether the passage says the radioactive label is on the part of the substrate that ends up in the counted product (for example the labelled carbon is in the product and not in the released group), or says that it is not.',
    'counting_efficiency_corrected': 'Whether the passage says the counts were corrected for counting efficiency or quenching (an internal or external standard, a quench curve, or a counting efficiency that is stated).',
    'native_substrate': 'Whether the passage says the labelled substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate or an analogue.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated counts of one reaction.',
    'conversion_detected_above_control': 'Whether the passage says conversion was detected above the paper\'s own control: yes when it states that the substrate was converted (product was formed) above the control or the detection limit, no only when it states that no conversion above the control or the detection limit was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices, the facts."""
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
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': _nullable({'enum': list(SUPPORTS)}), 'reason': _nullable({'enum': list(REASONS)})})
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
    occurs exactly once in ``chunk``; a number is above 0 (a share converted also not above its whole: 100 percent or 1) and a stated value carries its unit
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
        if name in SHARES and item['value'] > LARGEST_SHARE[item['unit']]:
            _refuse(name, 'a_share_converted_is_not_above_its_whole', LARGEST_SHARE[item['unit']])
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_endpoint_radiometric_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
