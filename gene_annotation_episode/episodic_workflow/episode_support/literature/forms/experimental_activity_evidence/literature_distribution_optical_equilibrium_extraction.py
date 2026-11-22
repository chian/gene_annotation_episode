"""The extraction of ONE optical equilibrium measurement of a reaction mixture (type 'distribution_optical_equilibrium') from one chunk of text, derived
from the grader's input form (``literature_distribution_optical_equilibrium_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand.
The things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_optical_equilibrium_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the
model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the
converter judges it.

One rule of this form beyond the template: a share (equilibrium_fraction) is a part of a whole, so it is refused when it is above 1 (unit fraction) or
above 100 (unit percent). The model is asked again; no downstream step has to guard against it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``)
are given by the caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_optical_equilibrium_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
# A share is a part of a whole: the largest value of each unit it may be stated in.
SHARES = ('equilibrium_fraction',)
WHOLE = {'fraction': 1.0, 'percent': 100.0}

MEANING = {
    'equilibrium_fraction': 'The share of ONE species (the species named as the partner of the identity block) in the mixture the passage describes as at equilibrium (the equilibrium composition read from the plateau of the absorbance or fluorescence), as a fraction of the total of the species of the reaction (substrate side and product side together), in fraction or percent. It is not how much of the substrate was converted at a time before equilibrium.',
    'equilibrium_fraction_spread': 'The reported uncertainty of the equilibrium share (the number after a plus-minus sign, or a standard error or deviation), in the unit of the equilibrium share.',
    'equilibrium_ratio': 'The ratio of the species named as the partner of the identity block (the claimed side) to the other side at equilibrium, as one number with the partner side on top (the equilibrium constant of an isomerisation or an interconversion between two species, which has no unit, or the ratio of the concentrations at equilibrium); dimensionless. A constant the passage gives with a unit, or with the species the other way round, is unavailable with the reason unit_not_in_vocabulary or ambiguous_or_conflicting_in_passage.',
    'equilibrium_ratio_spread': 'The reported uncertainty of that equilibrium ratio, as a number in the same dimensionless unit.',
    'wavelength': 'The wavelength at which the absorbance or fluorescence of the mixture was read, in nm.',
    'extinction_coefficient': 'The extinction (molar absorption) coefficient the passage uses to turn the absorbance at the plateau into a concentration, in M^-1 cm^-1 or mM^-1 cm^-1. If the passage gives one for each of several species, it is unavailable with the reason ambiguous_or_conflicting_in_passage.',
    'absorbance_max': 'The highest absorbance reached in the measurement, or the absorbance range the passage says was kept below (for example "absorbance below 1.5"), in absorbance units (AU). It is for an absorbance reading; a fluorescence intensity is not an absorbance.',
    'plateau_change_percent': 'How much the signal (absorbance or fluorescence) still changed, in percent of the signal, over the plateau window the passage states (for example "the absorbance changed by less than 1% over 30 minutes"). Give the greatest change the passage states. A passage that only says the signal was constant, without a number, is unavailable here (the fact plateau_stable carries it).',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the equilibrium shares and ratios) are.',
    'readout': 'What was read to follow the mixture: absorbance or fluorescence.',
    'pure_species_spectra_measured': 'Whether the passage says the spectrum (or the extinction coefficient or fluorescence) of each pure species was measured under the conditions of the assay (the same buffer and pH), so that the signal can be assigned to the species.',
    'all_absorbing_species_accounted': 'Whether the passage says every species that absorbs (or fluoresces) at the wavelength read, substrates, products and cofactors, was accounted for in turning the plateau signal into a composition.',
    'constant_refers_to_one_step': 'Whether the passage says the composition or the constant it gives is that of the single reaction step the experiment tests (or is corrected for the coupled equilibria such as hydration, pH or metal binding): yes when it says so, no only when it says the value is an apparent or composite constant of several coupled steps.',
    'no_enzyme_control_done': 'Whether the passage says a mixture without the enzyme (a no-enzyme blank or a buffer-only sample) was followed in the same way, to see whether the signal changes without the enzyme.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was followed in the same way.',
    'plateau_stable': 'Whether the passage says the signal reached a stable plateau (no further change, or no drift over the time stated): yes when it says so, no only when it says the signal was still changing or drifting.',
    'approached_from_both_sides': 'Whether the passage says the same equilibrium was reached starting from the substrate and starting from the product (the reverse reaction).',
    'same_value_at_several_initial_concentrations': 'Whether the passage says the same equilibrium value was found at several different initial concentrations of the reactants.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (separate mixtures, days or preparations) rather than repeated reads of one mixture.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'claimed_product_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the absorbance or fluorescence change showed the product the experiment tests for (the species named as the partner) formed in the mixture; no only when it says that product was not formed or no change of signal was seen. A passage that only describes how the measurement was done, or names the product without saying it was seen, is unavailable.',
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
    occurs exactly once in ``chunk``; a number is above 0 and a stated value carries its unit where the field has one; a share is not above its whole
    (1 as a fraction, 100 as a percent); a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
        if name in SHARES and item['value'] > WHOLE[item['unit']]:
            _refuse(name, 'share_is_above_the_whole')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_distribution_optical_equilibrium_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'distribution_optical_equilibrium', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
