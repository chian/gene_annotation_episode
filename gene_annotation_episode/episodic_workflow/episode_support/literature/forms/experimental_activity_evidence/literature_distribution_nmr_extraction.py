"""The extraction of ONE quantitative NMR measurement of a product mixture (type 'distribution_nmr') from one chunk of text, derived from the grader's
input form (``literature_distribution_nmr_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand.
The things this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_nmr_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the
model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the
converter judges it.

One rule of this form beyond the template: a share (product_fraction, equilibrium_fraction) is a part of a whole, so it is refused when it is above 1
(unit fraction) or above 100 (unit percent). The model is asked again; no downstream step has to guard against it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``)
are given by the caller and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_nmr_record import (
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
SHARES = ('product_fraction', 'equilibrium_fraction')
WHOLE = {'fraction': 1.0, 'percent': 100.0}

MEANING = {
    'product_fraction': 'The share of ONE species among the species the reaction gave (the species whose share the passage states, the product the experiment tests for; it is also the species named as the partner of the identity block), as a fraction of the total of the integrals of the species in the NMR spectrum, in fraction or percent. It is not the share at equilibrium (that is the equilibrium fraction) and not how much of the substrate was converted.',
    'product_fraction_spread': 'The reported uncertainty of that product share (the number after a plus-minus sign, or a standard error or deviation), in the unit of the product share.',
    'product_fraction_ratio': 'The ratio of the species whose share the passage states (the species named as the partner of the identity block) to one other species of the reaction, as one number, with the first species on top, for example a ratio written 3:1 is 3; dimensionless. If the passage writes the ratio the other way round, it is unavailable. It is not a ratio at equilibrium (that is the equilibrium ratio).',
    'product_fraction_ratio_spread': 'The reported uncertainty of that product ratio, as a number in the same dimensionless unit.',
    'equilibrium_fraction': 'The share of ONE species (the species named as the partner of the identity block) in the mixture the passage describes as at equilibrium (the equilibrium composition), as a fraction of the total of the integrals of the species, in fraction or percent.',
    'equilibrium_fraction_spread': 'The reported uncertainty of the equilibrium share, in the unit of the equilibrium share.',
    'equilibrium_ratio': 'The ratio of the species named as the partner of the identity block to the other side at equilibrium, as one number, with the partner species on top (the equilibrium constant of an isomerisation or an interconversion between two species, which has no unit); dimensionless. A constant the passage gives with a unit, or with the species the other way round, is unavailable.',
    'equilibrium_ratio_spread': 'The reported uncertainty of that equilibrium ratio, as a number in the same dimensionless unit.',
    'total_recovery': 'The sum of the quantified species over the amount the reaction started with, as the passage states it (for example against an internal concentration standard or the starting concentration), in fraction or percent. A set of shares that were only normalised to 100 percent is not a recovery.',
    'relaxation_delay': 'The delay between scans of the NMR acquisition as the passage states it (the relaxation delay, recycle delay or repetition time), in s or ms.',
    'longest_t1': 'The longest spin-lattice relaxation time T1 of the integrated nuclei that the passage states (measured or quoted for this experiment), in s or ms.',
    'signal_to_noise_minor': 'The signal-to-noise ratio the passage states for the smallest integrated signal (the minor species), as one number.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the shares and ratios) are.',
    'nucleus': 'The nucleus whose signals were integrated for the shares: 1H, 13C, 31P, 19F or 15N.',
    'no_enzyme_control_done': 'Whether the passage says a mixture without the enzyme (a no-enzyme blank or a buffer-only sample) was measured by NMR, to see the species that appear or interconvert without the enzyme.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was measured by NMR.',
    'integrals_from_resolved_signals': 'Whether the passage says each species was quantified from its own resolved signal, which does not overlap with a signal of another species (or says the overlapping signals were separated by fitting).',
    'species_assigned_with_standards': 'Whether the passage says the species were assigned by authentic standards, reference spectra or spiking with the pure compound, and not only by an expected chemical shift.',
    'relaxation_delay_adequate': 'Whether the passage says the delay between scans was long enough for full relaxation of every integrated nucleus (for example at least five times the longest T1, or checked by an inversion-recovery measurement or a longer delay giving the same shares): yes when it says so, no only when it says the delay was too short for full relaxation.',
    'fractions_share_one_denominator': 'Whether the passage says the shares were taken over one common total (the sum of the integrals of all the species), so that they add up to the whole.',
    'all_products_identified': 'Whether the passage says every signal of the spectrum belongs to an identified species, with no unassigned signal left out of the total.',
    'distribution_stable_over_time': 'Whether the passage says the composition of the mixture no longer changed over time (the same shares at two or more times, or a stable plateau): yes when it says so, no only when it says the composition was still changing.',
    'approached_from_both_sides': 'Whether the passage says the same composition was reached starting from the substrate and starting from the product (equilibrium approached from both sides).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (separate reactions, tubes or preparations) rather than repeated spectra of one sample.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'claimed_product_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the NMR spectrum showed the product the experiment tests for (the species named as the partner) among the species formed; no only when it says that product was not detected or not seen in the spectrum. A passage that only describes how the measurement was done, or names the product without saying it was seen, is unavailable.',
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
    """The record of ``literature_distribution_nmr_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'distribution_nmr', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
