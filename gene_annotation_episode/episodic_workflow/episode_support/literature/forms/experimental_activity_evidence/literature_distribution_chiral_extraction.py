"""The extraction of ONE chiral product-distribution experiment (type 'distribution_chiral') from one chunk of text, derived from the grader's input form
(``literature_distribution_chiral_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in step by hand. The three things
this module offers are all derived from the form's own declarations (its quantities, units, choices, facts and vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered 'unavailable' with a reason
                        (a field the passage does not state is never guessed and never 0). A field that is stated carries its value and the quote that states it. The model
                        gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that occurs more than once must be made
                        longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_distribution_chiral_record``), with the operand constructors of that form. The
                        quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by the model and validated here;
an unavailable field carries None. The record keeps it per stated value (``choice_support`` for the plain choices); the converter judges it.

Two ranges are checked here because the value would be impossible otherwise: an excess or a detection limit cannot exceed 100 percent (1 as a fraction), and a ratio of the
major isomer over the minor one is at least 1.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller
and the four preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_distribution_chiral_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
# FIXED_BY_DEFINITION: the largest value a share can have in each of its units (the whole is 100 percent, or 1 as a fraction).
SHARE_MAXIMUM = {'percent': 100.0, 'fraction': 1.0}
SHARE_QUANTITIES = ('enantiomeric_excess', 'minor_isomer_detection_limit')
# FIXED_BY_DEFINITION: a ratio of the major isomer over the minor one is at least 1 (the same amounts give exactly 1).
RATIO_MINIMUM = 1.0
RATIO_QUANTITIES = ('enantiomer_ratio', 'diastereomer_ratio')

MEANING = {
    'enantiomeric_excess': 'The enantiomeric excess (ee) of the product as the passage states it, a positive number: the excess of the MAJOR enantiomer, in percent (98 for "98% ee") or as a fraction (0.98). A lower bound such as ">99% ee" is given as its number (99); a value given as "up to", as an upper bound or as a range of several values is not one value, so answer unavailable.',
    'enantiomeric_excess_spread': 'The reported uncertainty of the enantiomeric excess (the number after a plus-minus sign, or a standard error or deviation), in the unit of the enantiomeric excess.',
    'enantiomer_ratio': 'The enantiomer ratio (er) of the product as the passage states it: the amount of the major enantiomer divided by the amount of the minor one, a number of at least 1 (a ratio written 95:5 is 19, 98:2 is 49, 99:1 is 99; a ratio written with the minor first is read with the larger number on top). It is the same measurement as the enantiomeric excess written another way.',
    'enantiomer_ratio_spread': 'The reported uncertainty of the enantiomer ratio, as a number (dimensionless).',
    'diastereomer_ratio': 'The diastereomer ratio (dr) of the product as the passage states it for two diastereomers (cis and trans, syn and anti, E and Z): the amount of the major diastereomer divided by the amount of the minor one, a number of at least 1 (a ratio written 10:1 is 10). A ratio of three or more diastereomers (10:1:1) is not one number, so answer unavailable.',
    'diastereomer_ratio_spread': 'The reported uncertainty of the diastereomer ratio, as a number (dimensionless).',
    'peak_resolution': 'The resolution Rs between the peaks of the two isomers on the chiral column (or the column that separates the diastereomers), as the passage reports it as a number (for example "Rs = 2.1").',
    'minor_isomer_detection_limit': 'The smallest amount of the minor isomer, as a share of the total of both isomers, that the method detects or quantifies (a limit of detection or of quantification), in percent or as a fraction, when the passage states it.',
    'replicate_count': 'The number of replicate experiments the passage reports for the stereochemical result (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the excess or the ratios) are.',
    'configuration': 'The configuration of the major isomer that the passage names for the product (R, S, E, Z, cis, trans, syn or anti), when it names one.',
    'technique': 'The method that separated the isomers: chiral-phase HPLC (chiral_hplc), chiral gas chromatography (chiral_gc), supercritical-fluid chromatography on a chiral column (chiral_sfc), capillary electrophoresis with a chiral selector (chiral_ce), or an ordinary column used because the isomers are diastereomers (diastereomers_on_achiral_column).',
    'product_detected': 'Whether the passage says the stereo-isomeric product (the product the stereochemical analysis is about) was formed and detected in the reaction of the enzyme: yes when it states the product was formed or detected, no only when it states that the product was not detected or not formed.',
    'racemic_standard_run': 'Whether the passage says a racemic standard of the product (or a mixture of its diastereomers) was prepared and run on the same column, so that both isomers are shown to be separated.',
    'configuration_assigned_by_standard': 'Whether the passage says the configuration of the major isomer was assigned by comparison with an authentic standard of known configuration (or the elution order of a known standard).',
    'isomer_peaks_baseline_resolved': 'Whether the passage says the two isomer peaks were baseline resolved (fully separated): yes when it says so, no only when it says the peaks overlapped or were only partly resolved.',
    'response_factors_calibrated': 'Whether the passage says the detector responses of the two isomers were checked or calibrated against each other (for diastereomers, whose responses can differ), for example by a calibration with the pure isomers.',
    'no_enzyme_control_done': 'Whether the passage says a control reaction without the enzyme (a buffer-only or substrate-only reaction) was run and analysed on the same column.',
    'inactive_enzyme_control_done': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run and analysed on the same column.',
    'product_configurationally_stable': 'Whether the passage says the product does not racemize or epimerize under the assay conditions and the work-up (its configuration was shown to be stable, for example by re-analysing the pure isomer after the same treatment).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated injections of one reaction mixture.',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a synthetic or surrogate substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate, an extract or whole cells).',
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
    where the field has one; a share is at most 100 percent (1 as a fraction) and a ratio of the major isomer over the minor one is at least 1;
    a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
        if name in SHARE_QUANTITIES and item['value'] > SHARE_MAXIMUM[item['unit']]:
            _refuse(name, 'share_is_above_the_whole')
        if name in RATIO_QUANTITIES and item['value'] < RATIO_MINIMUM:
            _refuse(name, 'ratio_of_major_over_minor_is_at_least_one')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_distribution_chiral_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'distribution_chiral', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
