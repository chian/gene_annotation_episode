"""The extraction of ONE surface plasmon resonance (SPR) experiment from one chunk of text, derived from the SPR
grader's input form (``literature_spr_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here
is a second schema kept in step by hand. The three things this module offers are all derived from the form's own
declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every
                        field may be answered 'unavailable' with a reason (a field the passage does not state is
                        never guessed and never 0). A field that is stated carries its value and the quote that
                        states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly
                        once (a quote that occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the SPR record the grader takes (``literature_spr_record``), with
                        the operand constructors of that form. The quoted spans become the record's ``spans`` and
                        are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote
supports it), chosen by the model and validated here; an unavailable field carries None. The record keeps it per
stated value (``choice_support`` for the spread kind and the fit model); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``,
``source_ref``, ``assertion_ref``) are given by the caller and the four preparation references
(``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import (
    FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the interaction as the passage reports it (the kinetic fit, or the one KD the passage reports if it does not say how it was obtained).',
    'kd_steady_state': 'A KD the passage says came from a steady-state (equilibrium response) fit, when the passage also reports a kinetic one.',
    'kon': 'The association rate constant kon, in M^-1 s^-1.',
    'koff': 'The dissociation rate constant koff, in s^-1.',
    'rmax': 'The maximum response Rmax, in response units (RU).',
    'kd_spread': 'The reported uncertainty of the KD (its standard error, standard deviation or confidence interval half-width), in a concentration unit.',
    'chi_squared': 'The chi-squared of the fit, in RU^2.',
    'baseline_noise': 'The noise level of the baseline or of the instrument that the passage states, in RU (for example "the baseline noise was 0.5 RU"). It is not the chi-squared and not the residual of one fit unless the passage calls it the noise.',
    'immobilization_level': 'The amount of immobilized partner on the surface, in RU.',
    'analyte_mass': 'The molecular mass of the analyte (the protein in solution), in kDa.',
    'ligand_mass': 'The molecular mass of the immobilized partner, in kDa.',
    'stoichiometry': 'The binding stoichiometry the passage uses (analyte molecules per immobilized molecule).',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The analyte concentrations of the titration series that was injected, as a list of numbers in one unit.',
    SPREAD_KIND: 'What the reported KD uncertainty is.',
    FIT_MODEL: 'The model the passage says the sensorgrams were fitted with.',
    'reference_surface': 'Whether the passage says a reference surface (reference flow cell) was used to correct the signal.',
    'double_referencing': 'Whether the passage says double referencing (reference surface and blank injections) was used.',
    'mass_transport': 'Whether the passage says mass-transport limitation was checked, and if so whether it was found limiting.',
    'baseline_drift': 'Whether the passage says the baseline was stable (no significant drift).',
    'regeneration': 'Whether the passage says the surface was regenerated cleanly between cycles.',
    'independent_surfaces': 'Whether the passage says the replicates were run on independent surfaces or chips.',
    'immobilized_activity': 'Whether the passage says the immobilized partner was shown to be active on the surface.',
    'analyte_bivalent_or_oligomeric': 'Whether the passage says the analyte is bivalent or oligomeric.',
    'residuals_reported': 'Whether the passage says the residuals of the fit are reported.',
    'single_estimate_method': 'Whether the passage says only one method (kinetic or steady-state) was used to estimate the KD.',
    'kd_analysis': 'How the passage says the reported KD was obtained: kinetic_fit when it says the KD came from fitting the association and dissociation phases of the sensorgrams (the rate constants), steady_state_fit when it says it came from the equilibrium (steady-state) response plotted against concentration. The words "equilibrium dissociation constant" only name the constant and do not state the method; a passage that does not say how the KD was obtained does not state this.',
    'binding_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the experiment showed that the two partners bind (a binding response, binding seen in the sensorgrams, a reported binding constant, or the plain statement that one binds the other as measured by SPR); no when it says the experiment showed no binding (no response above the reference, "did not bind", "no detectable binding"). A passage that only describes how the experiment was done, or names the method without its result, does not state this.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the spread kind,
    the fit model, the facts."""
    return (*QUANTITIES, SERIES, SPREAD_KIND, FIT_MODEL, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(SPREAD_KINDS)} if name == SPREAD_KIND else
             {'enum': list(FIT_MODELS)} if name == FIT_MODEL else
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
        carried = ('value', 'quote', 'support') +(('unit',) if name in UNITS else ())
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
    """The SPR record of ``literature_spr_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'spr', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            SPREAD_KIND: choice(SPREAD_KIND), FIT_MODEL: choice(FIT_MODEL),
            'choice_support': {name: answer[name]['support'] for name in (SPREAD_KIND, FIT_MODEL)},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
