"""The extraction of ONE proteoliposome tracer transport experiment (type 'transport_proteoliposome_tracer') from one chunk of text, derived from the grader's input form
(``literature_transport_proteoliposome_tracer_record.py``). DRAFT built 2026-11-22 on the shape of literature_spectro_direct_extraction.py, owner to correct.

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand. The three things
this module offers are all derived from the form's own declarations (its quantities, units, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered 'unavailable' with a reason (a
                        field the passage does not state is never guessed and never 0). A field that is stated carries its value and the quote that states it. The model
                        gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that occurs more than once must be made
                        longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_transport_proteoliposome_tracer_record``), with the operand constructors of that
                        form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model and validated here;
an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller and
the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_transport_proteoliposome_tracer_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'km': 'The Michaelis constant Km (or K0.5, the apparent affinity, half-saturation concentration) of the transported substrate, as the passage reports it for the reconstituted protein in the liposomes, in a concentration unit.',
    'km_spread': 'The reported uncertainty of the Km (the number after a plus-minus sign, or a standard error or deviation), in the unit of the Km.',
    'turnover': 'The turnover number of the transporter (substrate molecules moved per transporter molecule per second or minute), as the passage reports it, in s^-1 or min^-1. It is a rate per transporter molecule, not a rate per mass of protein.',
    'turnover_spread': 'The reported uncertainty of the turnover number, in the unit of the turnover number.',
    'normalized_rate': 'The transport rate (initial rate of uptake or efflux) of the proteoliposomes per mass of protein, as the passage reports it, in pmol/min/mg, nmol/min/mg or umol/min/mg (also written as a rate per mg of reconstituted protein or per mg of protein).',
    'normalized_rate_spread': 'The reported uncertainty of that rate per mass of protein, in the unit of that rate.',
    'fold_over_control': 'How many times larger the transport (the rate or the amount taken up) of the proteoliposomes is than that of the paper\'s own protein-free (empty) liposomes treated the same way, when the passage gives it as a ratio or as a fold.',
    'fold_over_control_spread': 'The reported uncertainty of that fold over the empty liposomes, as a fold.',
    'uptake_percent_of_equilibrium': 'The percent of the plateau (equilibrium or steady-state) uptake that had been reached at the time or times from which the rate was taken, when the passage says it (for example "less than 20% of the equilibrium value").',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    SERIES: 'The substrate concentrations of the saturation (Michaelis-Menten) series over which the transport rate of the proteoliposomes was measured, as a list of numbers in one unit.',
    'spread_kind': 'What the reported spreads (the uncertainties of the transport quantities) are.',
    'driving_force': 'The driving force the passage imposes on the proteoliposomes for the transport: a proton gradient (a pH difference), a membrane potential (for example with valinomycin and a potassium gradient), a sodium gradient, another ion gradient, ATP, or the gradient of the substrate itself.',
    'flux_direction': 'The direction of the substrate movement that was measured: uptake into the proteoliposomes, efflux out of them, or exchange (counter-transport of substrate against substrate).',
    'empty_liposome_control_done': 'Whether the passage says liposomes without the protein (empty or protein-free liposomes) were put through the same transport assay.',
    'inactive_protein_control_done': 'Whether the passage says a reconstituted inactive protein (heat-denatured, or a catalytically dead or binding-deficient mutant) was put through the same transport assay.',
    'no_gradient_control_done': 'Whether the passage says the transport was also measured without the imposed driving force (no gradient, or the gradient dissipated with an ionophore or an uncoupler such as nigericin, CCCP or valinomycin with equal potassium on both sides).',
    'gradient_verified': 'Whether the passage says the imposed gradient or potential was itself verified by a probe or a measurement (for example a fluorescent pH or potential probe such as ACMA, pyranine or oxonol).',
    'leak_checked': 'Whether the passage says the integrity or tightness of the vesicles was checked (for example that the vesicles hold the label or the gradient, or that the leak is the same in empty liposomes).',
    'competitor_control_done': 'Whether the passage says the transport of the labelled substrate was tested against an unlabelled competitor, a structural analogue, a different substrate or an inhibitor (or a substituted ion).',
    'substrate_identity_shown': 'Whether the passage says the label taken up was shown to be the substrate itself (for example by chromatography of the vesicle content) and not a breakdown product.',
    'protein_quantified_after_reconstitution': 'Whether the passage says the amount of protein actually incorporated into the proteoliposomes was measured (as opposed to the protein put into the reconstitution mixture).',
    'active_fraction_determined': 'Whether the passage says the fraction of the reconstituted protein that is active or correctly oriented was determined (for example by an inhibitor, a protease or a labelling accessibility assay).',
    'linear_interval_shown': 'Whether the passage says the rate was taken from the linear (initial) part of the uptake time course, for example that uptake was linear with time over the interval used.',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (independent reconstitutions or protein preparations, or different days) rather than repeated samples of one proteoliposome batch.',
    'native_substrate': 'Whether the passage says the substrate transported is the native (natural, physiological) substrate of the protein, as opposed to an analogue or a surrogate.',
    'purified_protein': 'Whether the passage says the protein reconstituted into the liposomes was purified (as opposed to a membrane extract or a crude preparation).',
    'transport_detected_above_control': 'Whether the passage says the proteoliposomes transported the substrate above the paper\'s own control: yes when it states transport was detected above the empty liposomes (or the detection limit), no only when it states that no transport above the empty liposomes (or the detection limit) was detected.',
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
    """The record of ``literature_transport_proteoliposome_tracer_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'transport_proteoliposome_tracer', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
