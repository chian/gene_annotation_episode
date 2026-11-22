"""The extraction of ONE counterflow (exchange, trans-stimulation) experiment (type 'transport_counterflow') from one chunk of text, derived from the
grader's input form (``literature_transport_counterflow_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_counterflow_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the spread
kind); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_counterflow_record import (
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
COUNTS = ('replicate_count',)

MEANING = {
    'fold_over_control': 'How many times faster (or larger) the uptake of the label is in the vesicles or cells that were preloaded with the unlabelled substrate than in the same vesicles or cells without the preload (the trans-stimulation, for example "uptake was 8-fold higher in preloaded proteoliposomes"), when the passage gives it as a ratio or as a fold. It is not the ratio over protein-free vesicles or over an empty-vector strain, and it is not the overshoot.',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the non-preloaded baseline, as a fold.',
    'overshoot_ratio': 'How many times more label the preloaded vesicles or cells hold at the highest point of the time course (the overshoot, the transient accumulation above the equilibrium level) than at the equilibrium level that the label reaches later, when the passage gives it as a ratio or as a fold.',
    'overshoot_ratio_spread': 'The reported uncertainty of that overshoot ratio, as a fold.',
    'normalized_rate': 'The rate at which the preloaded vesicles or cells take up the label (the exchange rate), per mass of the preparation, as the passage reports it: in pmol/min/mg, nmol/min/mg or umol/min/mg. It is the rate of the preloaded preparation, not that of the non-preloaded one. An amount reached at one time (for example "5 nmol/mg at 30 s") is not a rate, and a rate per cell, per vesicle or per mg of lipid is not in the unit list.',
    'normalized_rate_spread': 'The reported uncertainty of that exchange rate, in the unit of the rate.',
    'km': 'The Km (or the half-saturation constant K0.5, or the apparent affinity) of the external substrate for the exchange or counterflow, from a series of external concentrations, as the passage reports it, in a concentration unit.',
    'km_spread': 'The reported uncertainty of the Km (the number after a plus-minus sign, or a standard error or deviation), in the unit of the Km.',
    'preload_concentration': 'The concentration of the unlabelled substrate with which the vesicles or cells were loaded (the loading concentration, for example "loaded with 50 mM substrate"), in uM, mM or M.',
    'label_concentration': 'The concentration of the substrate in the medium outside at the start of the uptake (the labelled substrate, with any unlabelled substrate added together with it; not the loading concentration), in nM, uM or mM.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The external substrate concentrations of the series over which the exchange rate was measured to give the Km, as a list of numbers in one unit.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the fold, the overshoot ratio, the rate and the Km) are.',
    'non_preloaded_baseline_done': 'Whether the passage says the same vesicles or cells without the preload (loaded with buffer only, or not loaded) were measured in the same experiment as the baseline of the trans-effect.',
    'protein_free_control_done': 'Whether the passage says a control without the protein (protein-free liposomes, an empty-vector strain, the parent strain or a deletion strain) was taken through the same preload and uptake.',
    'non_substrate_preload_control_done': 'Whether the passage says a preload with a molecule that is not a substrate (a molecule the transporter is not expected to recognize, for example a stereoisomer or an unrelated compound) was tested and did not stimulate the uptake of the label.',
    'label_identity_shown': 'Whether the passage says the label kept inside the vesicles or cells was shown to be the unchanged substrate and not a metabolite of it (for example by chromatography of an extract).',
    'preload_verified': 'Whether the passage says the loading of the vesicles or cells was verified (the substrate inside was measured, or the loading was shown to have reached its aim, for example by equilibration or by counting a labelled preload).',
    'preload_retained': 'Whether the passage says the preloaded substrate stayed inside the vesicles or cells during the uptake (a leak or retention control, or a statement that the vesicles were tight), as opposed to leaking out.',
    'equilibrium_reached': 'Whether the passage says the label inside reached a plateau (the equilibrium level) at later times in the same time course, so that the peak is judged against it.',
    'linear_interval_shown': 'Whether the passage says the uptake rates that are compared (preloaded and non-preloaded) were taken from the linear part of the time course (initial rates).',
    'native_substrate': 'Whether the passage says the molecules used (the labelled one and the preloaded one) are the natural substrate of the transporter, as opposed to analogues or surrogates of it.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, vesicle or proteoliposome batches, or cultures) rather than repeated samples of one batch.',
    'transport_detected_above_control': 'Whether the passage says counterflow, exchange or trans-stimulation was detected: yes when it states the preloaded vesicles or cells took up the label faster than the non-preloaded baseline or held it above the equilibrium level (an overshoot); no only when it states that no trans-stimulation and no overshoot was detected.',
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
    """The record of ``literature_transport_counterflow_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_counterflow', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            SPREAD_KIND: choice(SPREAD_KIND),
            'choice_support': {SPREAD_KIND: answer[SPREAD_KIND]['support']},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
