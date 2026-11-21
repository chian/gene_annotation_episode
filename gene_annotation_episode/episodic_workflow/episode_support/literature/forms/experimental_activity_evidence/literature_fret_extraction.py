"""The extraction of ONE FRET / TR-FRET binding experiment (in solution) from one chunk of text, derived from the
FRET grader's input form (``literature_fret_record.py``).

Same design as the SPR, ITC, BLI, GCI and FP extractions and private to FRET: the grader's input form IS the
extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``,
``validate_answer()``, ``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations
(its quantities, units, facts and vocabularies). The model gives only the quote of each stated field; code finds the
UTF-8 byte span, and a quote that does not occur in the chunk exactly once is refused.

Differences from the other types that come from the form: the emission ratio ends are unit-less ratios, the form has
the donor and the acceptor concentration, the delay and the integration window of a time-resolved read, an assay volume,
an incubation time and a temperature, a Ki and the half-maximal concentrations EC50 and IC50 beside the KD, an assay
format (direct titration or competition), the donor-acceptor pair, a plate type and the FRET fit models. Every number
must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the three preparation references (``preparations``) are references to
records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_record import (
    ASSAY_FORMATS, CHOICES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PAIRS, PLATE_TYPES, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
ASSAY_FORMAT = 'assay_format'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
PLATE_TYPE = 'plate_type'
PAIR = 'donor_acceptor_pair'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the binding partners, as the passage reports it from a direct (saturation) titration (a half-maximal binding concentration is this field only if the passage reports it as the KD).',
    'ki': 'The inhibition constant Ki of an unlabelled ligand that displaces a labelled partner, as the passage reports it from a competition (displacement) experiment. An IC50 is not this field.',
    'ec50': 'The half-maximal effective concentration EC50 of a titration, as the passage reports it under that name.',
    'ic50': 'The half-maximal inhibitory concentration IC50 of a competition (displacement) experiment, as the passage reports it under that name.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable unless the passage gives the uncertainty as one number. An uncertainty reported for any other value is not this field.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (its standard error, standard deviation or confidence interval half-width), in a concentration unit. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable unless the passage gives the uncertainty as one number. An uncertainty reported for any other value is not this field.',
    'donor_concentration': 'The concentration of the donor-labelled binding partner held fixed in the assay.',
    'acceptor_concentration': 'The concentration of the acceptor-labelled binding partner when it is held fixed in the assay (not the titrated series).',
    'ratio_minimum': 'The lowest value of the acceptor over donor emission ratio of the titration (the background end of the curve), as the passage gives it.',
    'ratio_maximum': 'The highest value of the acceptor over donor emission ratio of the titration (the plateau end of the curve), as the passage gives it.',
    'delay_time': 'The delay between the excitation flash and the start of the read in a time-resolved measurement.',
    'integration_time': 'The length of the integration window of the read in a time-resolved measurement.',
    'assay_volume': 'The volume of one assay sample as read, in uL or mL.',
    'incubation_time': 'How long the samples were incubated before the read.',
    'temperature': 'The temperature at which the samples were incubated or read.',
    'replicate_count': 'The number of replicate titrations the passage reports (a whole number).',
    SERIES: 'The titrant concentrations that were used, as a list of numbers in one unit (in a competition experiment, the competitor concentrations). A number of points with a top concentration is not a list.',
    ASSAY_FORMAT: 'Whether the experiment titrated a labelled partner with its partner (direct titration, a saturation experiment) or displaced a labelled partner with an unlabelled competitor (competition).',
    SPREAD_KIND: 'What the reported KD or Ki uncertainty is.',
    FIT_MODEL: 'The model the passage says the binding curve was fitted with: a one-site hyperbolic 1:1 model, a Hill model, a quadratic (tight-binding) model, a competitive-binding model, or another one.',
    PLATE_TYPE: 'The kind of plate or cell the read was made in.',
    PAIR: 'The kind of donor and acceptor pair, when the passage says what the donor and the acceptor are: a lanthanide (terbium or europium) chelate or cryptate donor with an organic dye, d2 or allophycocyanin acceptor; two fluorescent proteins; two organic dyes; or another pair. A dye or product name alone, without the passage saying what kind of fluorophore it is, does not say this.',
    'time_resolved_read': 'Whether the passage says the read was time-resolved (time-resolved FRET, TR-FRET, HTRF, a delay before the read), or says it was a steady-state (not time-resolved) read.',
    'ratiometric_readout_used': 'Whether the passage says the signal was the ratio of the acceptor emission to the donor emission, computed for each sample (yes), or says that only one channel was used (no).',
    'donor_only_control_measured': 'Whether the passage says a sample with the donor alone (without the acceptor) was measured as a control.',
    'acceptor_only_control_measured': 'Whether the passage says a sample with the acceptor alone (without the donor) was measured as a control, for example for direct excitation of the acceptor.',
    'crosstalk_corrected': 'Whether the passage says the spectral crosstalk (bleed-through of the donor emission into the acceptor channel, or direct excitation of the acceptor) was corrected for or subtracted (yes), or says it was not (no).',
    'labelled_partner_at_or_below_kd': 'Whether the passage says the concentration of the labelled partner held fixed was at or below the KD (yes), or above the KD (no).',
    'tight_binding_considered': 'Whether the passage says depletion of the titrant by tight binding was considered or accounted for, for example by a quadratic fit (yes), or says it was not (no).',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when read, for example because the signal was stable over time (yes), or says it was not (no). An incubation time alone does not say this, and neither does a measured equilibration time or half-life unless the passage says the samples were read after it.',
    'indirect_labelling_used': 'Whether the passage says a partner was labelled indirectly, through a labelled antibody against a tag or through streptavidin (yes), or says the labelling was direct, by attaching the dye to the protein itself (no).',
    'labelling_does_not_alter_binding': 'Whether the passage says the labelling (dye, tag or antibody) was tested and did not change the binding (yes), or says it did (no).',
    'compound_interference_checked': 'Whether the passage says interference of the titrant or of a test compound with the signal (absorbance, inner filter effect, own fluorescence, quenching) was checked.',
    'nonspecific_binding_checked': 'Whether the passage says non-specific signal was checked, for example with a non-binding mutant, an unrelated protein, or a sample without one partner.',
    'unlabelled_competitor_displaces': 'Whether the passage says an excess of unlabelled partner or ligand displaced the labelled partner (reduced the signal) (yes), or did not (no).',
    'independent_titrations': 'Whether the passage says the replicates were independent titrations (separate dilution series or preparations).',
    'single_estimate_method': 'Whether the passage itself says that only one method (direct titration or competition) was used to estimate the affinity (yes), or says that both were used (no). A passage that merely reports one constant does not say this: leave it unavailable.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the assay format,
    the spread kind, the fit model, the plate type, the pair, the facts."""
    return (*QUANTITIES, SERIES, ASSAY_FORMAT, SPREAD_KIND, FIT_MODEL, PLATE_TYPE, PAIR, *FACTS)


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _field_schema(name):
    value = ({'type': 'array', 'items': {'type': 'number'}} if name == SERIES else
             {'type': 'integer'} if name in COUNTS else
             {'type': 'number'} if name in QUANTITIES else
             {'enum': list(ASSAY_FORMATS)} if name == ASSAY_FORMAT else
             {'enum': list(SPREAD_KINDS)} if name == SPREAD_KIND else
             {'enum': list(FIT_MODELS)} if name == FIT_MODEL else
             {'enum': list(PLATE_TYPES)} if name == PLATE_TYPE else
             {'enum': list(PAIRS)} if name == PAIR else
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
    where the field has one. Returns ``answer``."""
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
    """The FRET record of ``literature_fret_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES}, SERIES: operand(SERIES),
            ASSAY_FORMAT: choice(ASSAY_FORMAT), SPREAD_KIND: choice(SPREAD_KIND), FIT_MODEL: choice(FIT_MODEL), PLATE_TYPE: choice(PLATE_TYPE), PAIR: choice(PAIR),
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
