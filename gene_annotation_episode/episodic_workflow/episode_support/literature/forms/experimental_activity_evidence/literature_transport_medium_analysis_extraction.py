"""The extraction of ONE medium-analysis transport experiment (type 'transport_medium_analysis') from one chunk of text, derived from the
grader's input form (``literature_transport_medium_analysis_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_medium_analysis_record``), with the
                        operand constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's
                        ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain
choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_medium_analysis_record import (
    ANALYTICAL_METHODS, FACTS, PREPARATION_KEYS, QUANTITIES, RATE_BASES, SERIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
RATE_BASIS = 'rate_basis'
ANALYTICAL_METHOD = 'analytical_method'
# The plain choice fields and their vocabularies (recorded only; no criterion rests on a choice).
CHOICES = {SPREAD_KIND: SPREAD_KINDS, RATE_BASIS: RATE_BASES, ANALYTICAL_METHOD: ANALYTICAL_METHODS}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'normalized_rate': 'The rate at which the substrate was taken up or released by the cells, as the passage reports it, per mass of cells (per mg of cell protein or of cell dry weight, or per g of dry weight), taken from the change of the substrate amount in the medium (or in the cells) over time: in pmol/min/mg, nmol/min/mg, umol/min/mg or umol/min/g. A rate per cell, per 10^9 cells, per volume of culture or a change of concentration per minute is not this field.',
    'normalized_rate_spread': 'The reported uncertainty of that rate per mass of cells (the number after a plus-minus sign, or a standard error or deviation), in the unit of the rate.',
    'fold_over_control': 'How many times larger the rate or the amount taken up or released by the cells that carry the transporter is than that of the paper\'s own control cells (an empty-vector strain, the parent strain, a deletion strain or uninduced cells), when the passage gives it as a ratio or as a fold. A value below 1 given as a fraction of the wild type is not a fold over the control.',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the control, as a fold.',
    'substrate_moved_percent': 'The percent of the starting amount of the substrate that was taken up from the medium (for an uptake) or released from the cells (for an export) over the interval from which the rate was taken, when the passage says it (for example "less than 10% of the pyruvate was consumed").',
    'interval': 'The length of the incubation from the start of the transport to the last sample from which the rate or amount was determined (for example "10 min at room temperature"), in s, min or h.',
    'separation_delay': 'The time between taking a sample and the cells being separated from the medium or the reaction being stopped (for example "centrifuged for 5 min"), in s, min or h. A separation described only as immediate, rapid or through silicone oil, without a time, is not this field.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The times after the start of the transport at which samples were taken for the analysis, as a list of numbers in one unit (s, min or h), all above 0. The time zero is not in the list.',
    SPREAD_KIND: 'What the reported spreads (the uncertainties of the rate quantities) are.',
    RATE_BASIS: 'What the reported rate per mass of cells is per: cell_protein (per mg of cell protein) or dry_weight (per mg or g of cell dry weight).',
    ANALYTICAL_METHOD: 'How the amount of the substrate was measured: hplc (liquid chromatography with an optical or other non-mass detector, with or without derivatization), lc_ms (liquid chromatography with mass spectrometry), enzymatic_analyzer (an enzymatic or biochemical analyzer or kit) or ion_analysis (ion chromatography, ICP-MS, atomic absorption or an ion-selective electrode on samples).',
    'cell_free_control_done': 'Whether the passage says a control of the same medium and substrate without cells (a cell-free blank) was measured through the same handling, to show the substrate is not lost or gained by itself or by sticking to the tube.',
    'zero_time_sample_taken': 'Whether the passage says the substrate was measured in a sample taken at the start (time zero, before or at the addition of the substrate or the cells).',
    'empty_vector_control_done': 'Whether the passage says cells without the transporter (an empty-vector strain, the parent strain, a deletion strain or uninduced cells) were measured the same way beside the cells that carry it.',
    'expression_confirmed': 'Whether the passage says the expression or the membrane insertion of the transporter in the cells was confirmed (for example by immunoblot, a tag, or a fluorescent fusion).',
    'calibration_in_medium': 'Whether the passage says the analysis was calibrated with standards of the substrate prepared in the same medium or buffer as the samples (a standard curve in the sample matrix).',
    'internal_standard_used': 'Whether the passage says an internal standard (for example an isotope-labelled copy of the substrate) was added to the samples for the analysis.',
    'linear_time_course': 'Whether the passage says the rate was taken from the linear part of the time course (an initial rate), or that the amount changed linearly with time over the interval.',
    'immediate_separation': 'Whether the passage says the cells were separated from the medium, or the reaction stopped, at once at the time of sampling (for example by silicone oil, rapid filtration or an immediate quench).',
    'substrate_identity_confirmed': 'Whether the passage says the substance that was measured was identified as the substrate itself (against an authentic standard of the substrate, by retention time and mass, or by a substrate-specific enzyme).',
    'substrate_metabolism_excluded': 'Whether the passage says the substrate is not metabolized (consumed or converted) by the cells during the experiment, or that its metabolism was measured or blocked.',
    'reuptake_excluded': 'Whether the passage says re-uptake of the released substrate by the cells was excluded or accounted for (for example by an uptake-deficient strain or a measured uptake of the same substrate).',
    'lysis_excluded': 'Whether the passage says leakage or lysis of the cells was excluded (for example the cells were shown to be intact or viable, or no intracellular marker appeared in the medium).',
    'energy_source_provided': 'Whether the passage says the cells were given an energy source or the driving gradient for the transport (for example glucose, a carbon source, an ion gradient or a membrane potential), or says the measurement was made in the conditions in which the transport is driven.',
    'native_substrate': 'Whether the passage says the measured substrate is the native (natural, physiological) substrate of the transporter, as opposed to an analogue.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, cultures or biological replicates) rather than repeated measurements of one sample.',
    'transport_detected_above_control': 'Whether the passage says the protein showed transport (uptake or release of the substrate) above the paper\'s own control: yes when it states transport was detected above the control or detection limit, no only when it states that no transport above the control or detection limit was detected.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the plain choices, the facts."""
    return (*QUANTITIES, SERIES, *CHOICES, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
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
    """The record of ``literature_transport_medium_analysis_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its
    byte offset in its source: each quote's span is found in the chunk and recorded at its offset in the source. A value not stated is an
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

    return {'version': VERSION, 'experiment_type': 'transport_medium_analysis', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
