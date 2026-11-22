"""The extraction of ONE protein-film electrochemistry experiment (type 'protein_film_electrochem') from one chunk of text, derived from the
grader's input form (``literature_protein_film_electrochem_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_protein_film_electrochem_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_protein_film_electrochem_record import (
    FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'electrons_per_turnover')

MEANING = {
    'catalytic_efficiency': 'The catalytic efficiency kcat/Km (also written kcat/KM or the specificity constant) of the enzyme film for the substrate, as the passage reports it, in M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1.',
    'catalytic_efficiency_spread': 'The reported uncertainty of the catalytic efficiency (the number after a plus-minus sign, or a standard error or deviation), in the unit of the catalytic efficiency.',
    'turnover': 'The turnover frequency or turnover number kcat of the enzyme on the electrode, as the passage reports it, in s^-1 or min^-1. It is a rate per enzyme that exchanges electrons with the electrode, not a current.',
    'turnover_spread': 'The reported uncertainty of the turnover frequency kcat, in the unit of the turnover frequency.',
    'rate_over_control': 'How many times larger the catalytic current of the enzyme film is than the current of the paper\'s own control (the same film without the substrate, or the bare electrode without enzyme with the substrate), when the passage gives it as a ratio or as a fold.',
    'rate_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'catalytic_current_density': 'The catalytic current per area of the electrode that the passage reports for the enzyme film with its substrate (a current density, not a total current), in nA/cm^2, uA/cm^2 or mA/cm^2.',
    'electroactive_coverage': 'The electroactive coverage of the film as the passage reports it: the amount of enzyme per area of the electrode that exchanges electrons with the electrode (for example from the area of the non-turnover redox signal), in pmol/cm^2 or nmol/cm^2.',
    'electrons_per_turnover': 'The number of electrons transferred per turnover of the reaction, as the passage states it for the catalysed reaction (a whole number).',
    'km': 'The (apparent) Michaelis constant Km (KM) of the enzyme film for the substrate, as the passage reports it, in a concentration unit.',
    'film_loss_percent': 'The percent of the signal (the catalytic current, or the non-turnover signal) that was lost during the measurement from which the reported value was taken, by loss or inactivation of the enzyme film (for example "the current decayed by 15% over the scan").',
    'replicate_count': 'The number of independent films or electrodes (separately prepared enzyme films) the passage reports (a whole number).',
    SERIES: 'The substrate concentrations of the current-against-substrate (saturation) curve over which the catalytic current was measured, as a list of numbers in one unit.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the rate quantities) are.',
    'bare_electrode_control': 'Whether the passage says a control with the bare electrode (no enzyme film, or the electrode with the film medium but no enzyme) was measured with the substrate, to show the current the substrate gives at the electrode itself.',
    'no_substrate_control': 'Whether the passage says the enzyme film was also measured without the substrate (a baseline, or the non-turnover response), so that the catalytic current is the part that needs the substrate.',
    'substrate_dependent_current': 'Whether the passage says the catalytic current was shown to depend on the substrate: it rises when the substrate is added or its concentration is raised, and falls when it is removed.',
    'product_identified': 'Whether the passage says the product of the reaction behind the catalytic current was identified by another measurement (for example chromatography, mass spectrometry or a product assay).',
    'potential_referenced': 'Whether the passage states the electrode potential of the measurement against a named reference (for example SHE, Ag/AgCl or SCE).',
    'electrode_area_stated': 'Whether the passage states the area of the electrode (geometric or electroactive) by which the current is divided or against which the current is reported.',
    'mass_transport_excluded': 'Whether the passage says mass transport of the substrate to the film was removed or shown not to limit the current (for example a rotating electrode, or a current that does not change with the rotation rate or the stirring).',
    'steady_state_wave': 'Whether the passage says the catalytic current is a steady-state wave: a sigmoidal wave or a current plateau that does not depend on the scan rate or the time of the measurement.',
    'electroactive_coverage_determined': 'Whether the passage says the electroactive coverage was measured on the film itself (for example from the area of the non-turnover redox peak), as opposed to taking the amount of protein applied to the electrode as the amount that is active.',
    'film_loss_corrected': 'Whether the passage says the loss of the enzyme film during the measurement (film desorption or decay of the current) was corrected for or removed from the reported value.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate substrate or mediator reaction.',
    'purified_enzyme': 'Whether the passage says the enzyme in the film was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent films or electrodes (separately prepared films) rather than repeated scans of one film.',
    'activity_detected_above_control': 'Whether the passage says the enzyme film showed catalytic current above the paper\'s own control: yes when it states a catalytic current was detected above the control or the baseline, no only when it states that no catalytic current above the control or the baseline was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the spread kind, the facts."""
    return (*QUANTITIES, SERIES, SPREAD_KIND, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(SPREAD_KINDS)} if name == SPREAD_KIND else
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
        numbers = item['value'] if name == SERIES else [item['value']] if name in QUANTITIES else []
        if name == SERIES and not numbers:
            _refuse(name, 'series_is_empty')
        if any(number <= 0 for number in numbers):
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_protein_film_electrochem_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'protein_film_electrochem', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
