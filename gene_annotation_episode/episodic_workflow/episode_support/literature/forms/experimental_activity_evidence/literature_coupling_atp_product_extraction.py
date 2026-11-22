"""The extraction of ONE nucleotide-hydrolysis-to-product coupling experiment (type 'coupling_atp_product') from one chunk of text, derived from the
grader's input form (``literature_coupling_atp_product_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts, choices and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_atp_product_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices);
the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_atp_product_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'productive_fraction': 'The share of the hydrolysed nucleotide (ATP or GTP) that ends in the product, as the passage states it (a coupling efficiency, a productive fraction, a percent coupling), as a fraction or a percent. Not a cost per product and not a ratio of moles.',
    'productive_fraction_spread': 'The reported uncertainty of that productive fraction (the number after a plus-minus sign, or a standard error or deviation), in the unit of the productive fraction.',
    'stoichiometric_ratio': 'The moles of product formed per mole of nucleotide hydrolysed, as the passage states it (product per ATP, product per GTP), in mol per mol or as a fraction. Not the reverse: the nucleotides per product go in their own field.',
    'stoichiometric_ratio_spread': 'The reported uncertainty of that product per nucleotide, in the unit of the product per nucleotide.',
    'nucleotides_per_product': 'The moles of nucleotide hydrolysed per mole of product formed, as the passage states it (for example 4.5 ATP hydrolysed per product, the ATP cost or ATP/product ratio), in mol per mol. It is a cost and is normally above 1.',
    'nucleotides_per_product_spread': 'The reported uncertainty of the nucleotides per product, in mol per mol.',
    'stoichiometric_coefficient': 'The moles of nucleotide that one product needs according to the passage\'s own account of the reaction (for example "one ATP is used for each phosphate transferred", "two ATP per electron pair" is 2, "the reaction needs 4 ATP per product"), as a number in mol per mol. Only a number the passage states as what the reaction needs, not a measured cost.',
    'nucleotide_rate': 'The rate of nucleotide hydrolysis (phosphate released, NADH lost in the pyruvate kinase and lactate dehydrogenase coupled assay, or ADP formed) of the reaction that makes the product, with the substrate or partner present, as the passage states it before any basal rate is taken off, in a rate unit the field offers.',
    'basal_rate': 'The rate of nucleotide hydrolysis of the same enzyme without the substrate or partner that drives the product (the basal or uncoupled ATPase rate), as the passage states it, in a rate unit the field offers.',
    'nucleotide_consumed_percent': 'The percent of the starting nucleotide that was hydrolysed in the window over which the measurement was taken, when the passage says it (for example "less than 10% of the ATP was hydrolysed").',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the productive fraction, the product per nucleotide and the nucleotides per product) are.',
    'nucleotide': 'Which nucleotide is hydrolysed in the reaction that makes the product: ATP, GTP or another.',
    'hydrolysis_readout': 'How the nucleotide hydrolysis was measured: a phosphate dye (malachite green and similar), the NADH loss of the pyruvate kinase and lactate dehydrogenase coupled assay, radiolabelled phosphate released from [gamma-32P] nucleotide, chromatography of the ADP or GDP formed, or another readout.',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme (a no-enzyme blank, or a buffer-only reaction with the nucleotide) was measured, so that the non-enzymatic hydrolysis is known.',
    'reagent_blank_done': 'Whether the passage says the free phosphate (or ADP) already present in the nucleotide stock or the reagents was measured in a blank and set aside.',
    'basal_rate_subtracted': 'Whether the passage says the basal nucleotide hydrolysis rate (the rate without the substrate or partner) was measured and taken off, or that the link is stated over the substrate-stimulated hydrolysis only. Answer no only when the passage says the basal rate was not taken off.',
    'coupling_enzymes_in_excess': 'Whether the passage says the coupling enzymes of the hydrolysis assay (pyruvate kinase and lactate dehydrogenase, or another coupled system) were in excess or were shown not to limit the rate.',
    'signal_in_linear_range': 'Whether the passage says the phosphate or NADH signal stayed within the linear range of its standard curve.',
    'nucleotide_regenerated': 'Whether the passage says an ATP- or GTP-regenerating system (for example phosphoenolpyruvate with pyruvate kinase, or creatine phosphate with creatine kinase) kept the nucleotide up and the ADP or GDP down during the measurement.',
    'product_requires_hydrolysis': 'Whether the passage says no product formed (or the product was lost) without the nucleotide, with a non-hydrolysable analogue (AMP-PNP, ATP-gamma-S) or with a hydrolysis-dead mutant, so that the product is driven by the hydrolysis.',
    'product_identified': 'Whether the passage says the product was identified by another measurement (for example chromatography against an authentic standard, mass spectrometry or NMR).',
    'product_calibrated': 'Whether the passage says the amount of product was calibrated with a standard (a standard curve or a standard of known amount).',
    'nucleotide_side_calibrated': 'Whether the passage says the nucleotide hydrolysis side was calibrated (a phosphate standard curve, the extinction coefficient of NADH, the specific radioactivity of the 32P nucleotide, or an ADP standard).',
    'same_mixture': 'Whether the passage says the nucleotide hydrolysis and the product were measured in the same reaction mixture (not in separate reactions).',
    'same_window': 'Whether the passage says the nucleotide hydrolysis and the product were measured over the same time window.',
    'native_substrate': 'Whether the passage says the substrate (and nucleotide) is the native (natural, physiological) one of the enzyme, as opposed to a surrogate or an analogue.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'coupled_product_detected': 'Whether the passage says the product was formed by the nucleotide-driven reaction above the paper\'s own control: yes when it states the product was detected above the control or detection limit, no only when it states that no product above the control or detection limit was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the plain choices, the facts."""
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
    """The record of ``literature_coupling_atp_product_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
    in its source: each quote's span is found in the chunk and recorded at its offset in the source. A value not stated is an
    'unavailable' operand with its reason, never 0; a fact not stated is 'unknown'; a choice not stated is None."""
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

    return {'version': VERSION, 'experiment_type': 'coupling_atp_product', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
