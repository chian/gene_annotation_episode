"""The extraction of ONE continuous vesicle flux experiment read by a probe (type 'transport_vesicle_probe_flux') from one chunk of text, derived from the
grader's input form (``literature_transport_vesicle_probe_flux_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The things this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_vesicle_probe_flux_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the two plain
choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_vesicle_probe_flux_record import (
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
    'turnover': 'The number of ions or molecules that ONE transporter or channel moves per second (or per minute), as the passage reports it (for example "more than 30,000 ions per second per channel"), in s^-1 or min^-1. It is a rate per transporter, not the rate constant of the whole vesicle population and not a rate per mass of protein.',
    'turnover_spread': 'The reported uncertainty of that turnover per transporter, in the unit of the turnover.',
    'normalized_rate': 'The flux of the vesicles per mass of the protein, as the passage reports it: in pmol/min/mg, nmol/min/mg or umol/min/mg. It is a rate (an amount moved per minute) per mg of protein; a fraction released, a rate constant and a half-time are different fields.',
    'normalized_rate_spread': 'The reported uncertainty of that rate per mg of protein, in the unit of the rate.',
    'fold_over_control': 'How many times larger the flux of the vesicles with the protein is than the flux of the paper\'s own protein-free vesicles (empty liposomes or vesicles without the protein), when the passage gives it as a ratio or as a fold (for example "20-fold faster than protein-free vesicles").',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'release_fraction': 'The share of the whole pool (the content that a detergent released at the end, taken as 100 percent) that had left the vesicles with the protein at the stated time, in percent. A fraction given as a number between 0 and 1 is converted to percent only when the conversion is exact. If the passage says that nothing was released, leave this field unavailable.',
    'control_release_fraction': 'The same share of the whole pool that had left the protein-free vesicles (the control) at the same time, in percent. If the passage says that nothing was released from the control, leave this field unavailable.',
    'release_time': 'The time after the start of the transport at which the release fractions were read, in s or min.',
    'rate_constant': 'The first-order rate constant of the release of the pool from the vesicles, as the passage reports it (for example "k = 0.5 s^-1"), in s^-1 or min^-1. It is the rate of the whole vesicle population, not a rate per transporter (that is the turnover).',
    'half_time': 'The half-time of the release of the pool from the vesicles (the time to release half of it), as the passage reports it, in s or min.',
    'dead_time': 'The response time or the dead time of the apparatus that the passage gives (the time the electrode or the dye needs to register a change, or the time lost in mixing), in ms or s.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the turnover, the rate and the fold) are.',
    'probe_kind': 'How the flux was followed in real time: with an ion-selective electrode in the bath (ion_selective_electrode), or with a dye or probe trapped inside the vesicles (entrapped_dye).',
    'protein_free_vesicle_control_done': 'Whether the passage says vesicles without the protein (protein-free or empty liposomes, or vesicles from cells without it) were run through the same protocol as the background of the flux.',
    'second_ion_control_done': 'Whether the passage says a second ion or substrate was tested in the same kind of vesicles (for example chloride beside fluoride, another cation, or a substituted counter-ion) to show which species the protein moves.',
    'probe_selective_for_ion': 'Whether the passage says the electrode or the entrapped dye responds to the ion or species that is followed and not to the other species present (for example its response to the counter-ion, the buffer or the second ion was tested).',
    'ionophore_control_done': 'Whether the passage says an ionophore or a pore (for example valinomycin, CCCP, FCCP, nigericin or gramicidin) was used to set or test the driving force or to supply the counter-ion, for example to show that the flux was not limited by the counter-ion.',
    'gradient_defined': 'Whether the passage states the concentrations (or activities) of the ion or substrate inside and outside the vesicles at the start, which is the gradient that drives the flux.',
    'detergent_reference_done': 'Whether the passage says that the content left in the vesicles was released at the end with a detergent or a pore former, and that this release was taken as the whole (100 percent) pool.',
    'probe_calibrated': 'Whether the passage says the electrode or the dye was calibrated with known amounts of the ion (or known pH values) in the same buffer, so that the signal is read as an amount.',
    'vesicle_integrity_checked': 'Whether the passage says the vesicles were shown to hold their content, for example a slow background release of the protein-free vesicles, or retention of the ion or dye before the flux was started.',
    'protein_quantified_in_vesicles': 'Whether the passage says the amount of protein that is in the vesicles was measured (for example a protein-to-lipid ratio of the vesicles, the amount recovered after reconstitution, or the number of channels per vesicle), not only the amount put into the reconstitution.',
    'flux_faster_than_apparatus_response': 'Whether the passage says the release was faster than the apparatus could follow (complete within its response time or dead time), so that the rate is only a lower limit: yes when it says so, no only when it says the release was slower than the response time and was resolved.',
    'native_substrate': 'Whether the passage says the ion or substrate whose flux was followed is the natural substrate of the protein, as opposed to a surrogate or an analogue.',
    'purified_protein': 'Whether the passage says the protein was purified and reconstituted into the vesicles (as opposed to native membrane vesicles or vesicles made from cells).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different vesicle preparations or reconstitutions, or different days) rather than repeated traces of one batch of vesicles.',
    'transport_detected_above_control': 'Whether the passage says the vesicles with the protein released (or took up) the ion or substrate above the paper\'s own protein-free vesicles: yes when it states that transport was detected above the control, no only when it states that no transport above the control or the detection limit was detected.',
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
    """The record of ``literature_transport_vesicle_probe_flux_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_vesicle_probe_flux', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
