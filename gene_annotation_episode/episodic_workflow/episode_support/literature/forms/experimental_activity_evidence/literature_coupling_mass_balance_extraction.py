"""The extraction of ONE mass-balance (closure) experiment (type 'coupling_mass_balance') from one chunk of text, derived from the
grader's input form (``literature_coupling_mass_balance_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_mass_balance_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the choices);
the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_mass_balance_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'closure': 'The closure (also called the recovery, the mass balance, the carbon balance, the nitrogen balance or the molar balance) that the passage states for the reaction: the share of the substrate that disappeared which is accounted for by the identified products, as a percent or a fraction (for example "the products accounted for 96% of the substrate consumed" gives 96 percent). A share that the passage states as the part NOT accounted for is not this field. A value above 100 percent is stated as the passage gives it.',
    'closure_spread': 'The reported uncertainty of the closure (the number after a plus-minus sign, or a standard error or deviation), in the unit of the closure (percent or fraction).',
    'substrate_consumed': 'The net amount of the substrate that was consumed (disappeared) in the reaction, as the passage gives it, as a concentration (nM, uM or mM) or an amount (pmol, nmol or umol). It is the loss of the substrate, not the amount that was added.',
    'products_total': 'The total amount of all the identified products together (their sum), as the passage gives it as one number, as a concentration (nM, uM or mM) or an amount (pmol, nmol or umol). Only a total that the passage itself states; the amounts of the single products are not this field.',
    'balance_residual': 'The amount that was not accounted for (the unaccounted or missing substrate, the residual of the balance), as the passage gives it as an amount, as a concentration (nM, uM or mM) or an amount (pmol, nmol or umol).',
    'zero_time_closure': 'The recovery that the passage gives for a sample with no reaction (a sample taken at time zero, or a sample without the enzyme) analysed in the same way: the share of the added substrate (or of the total of substrate and products) that the method found again, as a percent or a fraction. It is the closure of the method itself.',
    'detection_limit': 'The detection limit (or limit of quantification) of the method for the products, as an amount or concentration (nM, uM, mM, pmol, nmol or umol). When the passage gives several, the one of the least sensitive product.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spread of the closure is.',
    'balance_basis': 'What the closure counts: molar (moles of substrate and products), carbon (carbon atoms), nitrogen (nitrogen atoms) or mass (grams or mass units).',
    'analysis_method': 'How the substrate and the products were quantified: hplc (liquid chromatography with an optical or similar detector), gc (gas chromatography with a flame ionisation or similar detector), lc_ms (liquid chromatography with mass spectrometry), gc_ms (gas chromatography with mass spectrometry), nmr (nuclear magnetic resonance) or other.',
    'product_identified': 'Whether the passage says each product was identified (against an authentic standard by retention time, by its mass spectrum, or by NMR), as opposed to being inferred.',
    'each_species_calibrated': 'Whether the passage says the substrate and every quantified product were calibrated with their own standards (a standard series of each species, or NMR with a known reference), rather than quantified with the response of another compound.',
    'internal_standard': 'Whether the passage says an internal standard was added to the samples for the quantification.',
    'zero_time_sample': 'Whether the passage says a sample taken at time zero (before the reaction) was analysed in the same way.',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme (incubated and analysed like the reaction) was measured.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured.',
    'all_products_quantified': 'Whether the passage says that all the products expected from the reaction were quantified (yes), or says that some product or part of the substrate could not be identified or quantified (no).',
    'volatile_loss_excluded': 'Whether the passage says that loss of a volatile or insoluble species was excluded or checked (for example a closed vessel, analysis of the headspace, or a check of a precipitate).',
    'reaction_equation_stated': 'Whether the passage states the balanced reaction (the equation or the stoichiometric coefficients, or the atom counts) that the closure is calculated on.',
    'same_mixture': 'Whether the passage says the substrate and the products were measured in the same reaction mixture (the same aliquots), not in separate reactions.',
    'same_window': 'Whether the passage says the substrate and the products were measured at the same time points of the reaction.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated injections of one mixture.',
    'product_formation_detected': 'Whether the passage says that the substrate was converted to the product or products (product formation was detected, or the products accounted for the substrate consumed): yes; or says that no product was formed above the paper\'s own control or detection limit: no. The statement itself, not a number.',
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
    """The record of ``literature_coupling_mass_balance_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'coupling_mass_balance', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
