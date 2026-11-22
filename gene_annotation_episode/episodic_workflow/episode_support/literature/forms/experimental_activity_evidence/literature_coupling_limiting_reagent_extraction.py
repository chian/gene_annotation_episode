"""The extraction of ONE limiting-reagent endpoint experiment (type 'coupling_limiting_reagent', class reaction_coupling: the reaction is run to completion with one
reagent limiting, and the product formed is set against the limiting reagent used up) from one chunk of text, derived from the grader's input form
(``literature_coupling_limiting_reagent_record.py``). DRAFT 2026-11-22, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand. The three
things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered 'unavailable' with a
                        reason (a field the passage does not state is never guessed and never 0). A field that is stated carries its value and the quote that states
                        it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that occurs more than once must be
                        made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_limiting_reagent_record``), with the operand constructors of that
                        form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model and
validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the choices); the converter judges it.

Differences from the other types that come from the form: the numbers are the stated productive fraction and yield (with their spreads), the equivalents of limiting
reagent per product and the paper's own coefficient, the share of the limiting reagent left at the end (0 to 100, and 0 is allowed), the fold of excess of the other
reagent, the number of titration points and the number of independent experiments. Nothing is worked out here: the equivalents per product, the yield and the coefficient are
the paper's numbers, and the converter does any arithmetic on them.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the
caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_limiting_reagent_record import (
    EXPERIMENT_TYPE, FACTS, LIMITING_REAGENT_KINDS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
LIMITING_REAGENT_KIND = 'limiting_reagent_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('titration_points', 'replicate_count')
RANGES = {'limiting_reagent_remaining': (0, 100)}   # the closed range of a quantity that has one; every other number must be above 0
CHOICES = {SPREAD_KIND: SPREAD_KINDS, LIMITING_REAGENT_KIND: LIMITING_REAGENT_KINDS}

MEANING = {
    'productive_fraction': 'The share of the limiting reagent that ended in the claimed product, with the reaction\'s own coefficient already applied (so that full use of the limiting reagent is 1 or 100 percent), as the passage gives it: a productive fraction, a coupling efficiency, or a yield against the most the limiting reagent allows (for example the product over the smaller of the substrate and the limiting reagent divided by its coefficient). Give it as a fraction or as a percent, as written. A yield that has no coefficient applied is not this field (it is yield_over_limiting_reagent).',
    'productive_fraction_spread': 'The reported uncertainty of the productive fraction (the number after a plus-minus sign, or a standard error or deviation), in the unit of the productive fraction.',
    'yield_over_limiting_reagent': 'The product formed as a share of the amount of limiting reagent that was added, as the passage gives it (for example 95 percent of the NADPH was converted to product, or the product was formed in 0.48 mol per mol of NADPH), with no coefficient applied. Give it as a fraction or as a percent, as written. A conversion of the substrate is not this field unless the substrate is the limiting reagent.',
    'yield_over_limiting_reagent_spread': 'The reported uncertainty of that yield, in the unit of the yield.',
    'limiting_reagent_per_product': 'The measured equivalents of the limiting reagent used up per product formed at the end of the reaction or from the slope of the titration, as the passage gives it in moles per mole (for example 2.1 equivalents of NADPH per preQ1). A coefficient that the passage only expects from the reaction equation, without measuring it, is not this field (it is stoichiometric_coefficient). An amount of limiting reagent added is not this field.',
    'limiting_reagent_per_product_spread': 'The reported uncertainty of the measured equivalents of the limiting reagent per product, in moles per mole.',
    'stoichiometric_coefficient': 'The equivalents of the limiting reagent per product that the passage\'s own account of the reaction expects (the reaction equation or the stated stoichiometry, for example 2 NADPH per product, 1 O2 per product), in moles per mole. A measured value is not this field (it is limiting_reagent_per_product).',
    'limiting_reagent_remaining': 'The percent of the limiting reagent that was still there at the end of the reaction (for example less than 5 percent of the NADPH remained, or 3 percent of the starting absorbance was left), as the passage gives it (0 when the passage says that none remained). A percent of the product or of the substrate is not this field.',
    'excess_over_limiting': 'How many times the other reagent (the substrate, or the cofactor that is not limiting) exceeds the limiting reagent in the reaction, as a fold or a ratio that the passage writes itself (for example a 10-fold excess of substrate over NADPH gives 10). A concentration alone is not this field, and a ratio of enzyme to substrate is not this field.',
    'titration_points': 'The number of additions or points of the stepwise titration of the limiting reagent (for example seven additions of NADPH), as a whole number. A single dose is not a titration. The number of replicates is not this field.',
    'replicate_count': 'The number of replicate experiments the passage reports for this endpoint experiment (a whole number). The number of titration points is not this field.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the productive fraction, the yield and the equivalents per product) are.',
    LIMITING_REAGENT_KIND: 'What the limiting reagent is: cofactor (NADH, NADPH, FAD, ATP used as a cofactor), co_substrate (a second substrate such as oxygen, a donor or an acceptor), substrate (the substrate itself is limiting) or other. A passage that does not say which reagent is limiting does not state it.',
    'completion_shown': 'Whether the passage says the reaction was run to completion: no further product (or no further change) was seen with more enzyme or more time (yes), or says that the reaction did not go to completion (no).',
    'limiting_reagent_consumed_fully': 'Whether the passage says the limiting reagent was used up, measured as gone (for example the NADPH absorbance fell to zero, or no residual cofactor was found) (yes), or says that some of it was left (no). The expected consumption by the reaction equation is not this fact.',
    'other_reagents_in_excess': 'Whether the passage says the other reagents (the substrate, the other cofactor, the enzyme\'s other needs) were in excess over the limiting reagent (yes), or says that they were not (no).',
    'no_regeneration': 'Whether the passage says the limiting reagent was not regenerated during the reaction, so that no regeneration system (for example glucose dehydrogenase for NADPH) was present (yes), or says that it was regenerated (no).',
    'limiting_amount_verified': 'Whether the passage says the amount or concentration of the limiting reagent that was added was checked by a measurement (for example the NADPH concentration was determined from its absorbance with its extinction coefficient) (yes), or says that it was only taken from the weighed amount (no).',
    'product_identified': 'Whether the passage says the product was identified chemically (against an authentic standard by co-elution, or by mass spectrometry or NMR) and not only inferred from the loss of the substrate or of the cofactor (yes), or says that it was not identified (no).',
    'product_calibrated': 'Whether the passage says the product was measured against a standard of known amounts (a standard curve or a standard series of the authentic product) (yes), or says that it was not (no).',
    'same_mixture': 'Whether the passage says the product and the limiting reagent were measured in the same reaction mixture (yes), or says that they were measured in separate reactions (no).',
    'same_endpoint': 'Whether the passage says the product and the limiting reagent were measured at the same end of the reaction, at the same time point (yes), or says that they were measured at different times (no).',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme (a reaction with the limiting reagent and the substrate but no enzyme) was measured, to show the limiting reagent is not lost and the product does not form without the enzyme (yes), or says that it was not done (no).',
    'no_substrate_control': 'Whether the passage says a control with the enzyme and the limiting reagent but without the substrate was measured, to show that the enzyme does not use up the limiting reagent by itself (for example NADPH oxidase activity) (yes), or says that it was not done (no).',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured (yes), or says that it was not done (no).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated measurements of one mixture (yes), or says that they were not (no).',
    'native_substrate': 'Whether the passage says the substrate and the cofactor are the native (natural, physiological) ones of the enzyme, as opposed to a surrogate or an analogue (yes), or says that they are not (no).',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract) (yes), or says that it was not (no).',
    'coupled_product_detected': 'Whether the passage says the claimed product was formed from the limiting reagent above the paper\'s own control or detection limit (yes), or says that no such product was detected (no). A passage that gives only the loss of the limiting reagent says nothing about the product.',
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
    occurs exactly once in ``chunk``; the share of the limiting reagent remaining is from 0 to 100 and any other number is above 0, and a stated value carries its unit
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
        if name in RANGES and not RANGES[name][0] <= item['value'] <= RANGES[name][1]:
            _refuse(name, 'number_must_be_in_its_range', RANGES[name])
        if name in QUANTITIES and name not in RANGES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_coupling_limiting_reagent_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
