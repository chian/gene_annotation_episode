"""The extraction of ONE ELISA-style binding experiment (plate-based solid-phase binding, direct, indirect, sandwich or competition) from one
chunk of text, derived from the grader's input form (``literature_elisa_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp and FCS extractions and private to this method: the grader's input form IS the
extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused. Each stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well
its quote supports it): required when stated, None when unavailable; the record keeps it and the converter turns it into a degree.

Differences from the other types that come from the form: the signal is what stays on the plate after the washes, read with an
enzyme-linked reagent, so the reported number is an apparent KD (or an EC50 or an IC50, which are separate fields and are not
dissociation constants), the coating, the blocking, the washing, the binding step and the detection are fields or choices, the
absorbance of the plateau and of the background are fields, the technical wells and the independent experiments are two
different counts, and the facts are the controls of this method (blank subtraction, a non-binding control, a plateau, the linear
range of the detector, dissociation during the washes, equilibrium, avidity, the activity of the coated protein and the
interference of the detection reagent). Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity
references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller and the three preparation references
(``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_record import (
    ASSAY_FORMATS, BLOCKING_AGENTS, DETECTION_FORMATS, ENZYME_CONJUGATES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, READOUT_SIGNALS,
    SPREAD_KINDS, UNITS, VERSION, CHOICE_FIELDS, fact, point, unavailable)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
ASSAY_FORMAT = 'assay_format'
DETECTION_FORMAT = 'detection_format'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
READOUT_SIGNAL = 'readout_signal'
ENZYME_CONJUGATE = 'enzyme_conjugate'
BLOCKING_AGENT = 'blocking_agent'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'titration_point_count', 'technical_replicate_count', 'wash_count')
CHOICES = {ASSAY_FORMAT: ASSAY_FORMATS, DETECTION_FORMAT: DETECTION_FORMATS, SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS,
           READOUT_SIGNAL: READOUT_SIGNALS, ENZYME_CONJUGATE: ENZYME_CONJUGATES, BLOCKING_AGENT: BLOCKING_AGENTS}

MEANING = {
    'kd': 'The dissociation constant of the binding partners, as the passage reports it under the name KD (or dissociation constant, or apparent KD) from the binding curve. A half-maximal concentration reported under the name EC50 or IC50 is not this field, and a value the passage does not call a dissociation constant is not this field.',
    'ki': 'The inhibition constant Ki of an unlabelled competitor, as the passage reports it under that name from a competition experiment on the same partners as the binding experiment (a competition ELISA beside a saturation titration is part of this experiment, not another one). An IC50 is not this field, and a value is not a Ki unless the passage calls it one.',
    'ec50': 'The half-maximal effective concentration EC50 of the binding curve (the titrant concentration at half of the maximal signal), as the passage reports it under the name EC50 or half-maximal effective concentration. A value the passage calls a KD is not this field.',
    'ic50': 'The half-maximal inhibitory concentration IC50 of a competition (the concentration of the competitor that lowers the signal to half), as the passage reports it under the name IC50 or half-maximal inhibitory concentration, from a competition experiment on the same partners as the binding experiment (a competition ELISA beside a saturation titration is part of this experiment, not another one). A value the passage calls a Ki or a KD is not this field.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. It belongs to the Ki, not to the KD. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'coating_concentration': 'The concentration of the solution in which the plate was coated with the coated partner, as the passage gives it in a mass per volume. A concentration of the titrated partner, or an amount per well, is not this field.',
    'signal_maximum': 'The absorbance (optical density, OD) of the plateau of the binding curve, the highest signal, as the passage gives it as a number. A wavelength is not this field, and a readout that is not an absorbance is not this field.',
    'signal_background': 'The absorbance (optical density, OD) of the background, the wells without the coated partner or without the ligand (blank wells), as the passage gives it as a number. A wavelength is not this field, and a readout that is not an absorbance is not this field.',
    'wash_count': 'The number of washes of the plate after the binding step of the ligand (a whole number), when the passage gives it as a number. Washes at other steps of the protocol are not this field.',
    'titration_point_count': 'The number of concentrations of the series of the titrated partner or of the competitor (the number of dilutions), as a whole number, when the passage gives it as a number.',
    'technical_replicate_count': 'The number of wells of the same sample on one plate (technical replicates, for example duplicates or triplicate wells), as a whole number, when the passage gives it as a number. The number of independent experiments is not this field.',
    'incubation_time': 'How long the titrated partner (the ligand or the competitor) was left to bind on the plate before the washing. The time of another step (coating, blocking, detection or the colour reaction) is not this field.',
    'temperature': 'The temperature at which the binding step was done, as a number.',
    'replicate_count': 'The number of independent experiments the passage reports (separate plates, dilution series or days), as a whole number. Wells of one plate are not this field.',
    'detector_linear_limit': 'The highest absorbance (optical density, OD) that the passage says the plate reader reads linearly (its linear range, or the absorbance above which the reader is not linear), as a number. The absorbance of the plateau is not this field, and a wavelength is not this field.',
    'koff': 'The dissociation rate constant of the complex of the two partners, as the passage gives it under the name koff (or off-rate, or dissociation rate constant), per second. A dissociation constant KD is not this field, and a rate the passage gives for another complex is not this field.',
    'wash_duration': 'The total time of the washes of the plate after the binding step of the ligand (the time the complex spends in buffer without free ligand before detection), as the passage gives it as one duration, for example washes of 5 minutes in total. The number of washes alone is not this duration, and the time of another step (blocking, antibody or substrate incubation) is not this field.',
    'tracer_concentration': 'In a competition, the constant concentration of the ligand that the competitor displaces (the labelled or tagged ligand, the tracer), as the passage gives it. A concentration of the competitor, a point of the series or the concentration of a coating is not this field.',
    'tracer_kd': 'The dissociation constant KD that the passage gives for the ligand that the competitor displaces (the tracer ligand of the competition), when it states it as the KD of that ligand. A KD the passage reports for the partners in the binding curve of the experiment is the kd field, not this one, unless the passage says it is the KD of the displaced ligand.',
    SERIES: 'The concentrations of the titrated partner (or of the competitor) that were used, as a list of numbers in one unit. A range with a first and a last concentration, or a number of points with a top concentration, is not a list.',
    ASSAY_FORMAT: 'Whether the experiment titrated the coated partner with its ligand (saturation titration) or displaced a ligand with an unlabelled competitor (competition). A passage that describes both formats without saying which one the reported constant comes from does not state it: leave it unavailable.',
    DETECTION_FORMAT: 'How the bound ligand was detected: with the enzyme on the ligand itself (direct), on a secondary antibody or a reagent that binds the ligand or its tag (indirect), or on a second reagent that binds the ligand held by a capture antibody (sandwich), as the passage states it.',
    SPREAD_KIND: 'What the reported KD or Ki uncertainty is.',
    FIT_MODEL: 'The model the passage names in words as the one the binding curve was fitted with: a one-site 1:1 model, a Hill model, a four-parameter logistic model, a competitive binding model, or another named one. A model the passage only calls simple, or an equation that is only written out, is not this field: do not work out the model from the form of an equation.',
    READOUT_SIGNAL: 'What the plate was read as, according to the passage: an absorbance (colorimetric substrate), chemiluminescence, or a fluorescence of a fluorogenic substrate.',
    ENZYME_CONJUGATE: 'The enzyme of the detection reagent, as the passage names it: horseradish peroxidase, alkaline phosphatase or another enzyme.',
    BLOCKING_AGENT: 'The protein or solution the plate was blocked with, as the passage names it: bovine serum albumin, milk, casein, serum or another one.',
    'blank_subtracted': 'Whether the passage says the signal of blank wells (without the coated partner, or without the ligand) was subtracted or corrected for (yes), or says it was not (no).',
    'nonspecific_binding_checked': 'Whether the passage says non-specific binding was checked with a control, for example an irrelevant protein, an uncoated well or a non-binding mutant, that gave no or little signal (yes), or says it was not (no). A control that is only used to estimate or subtract a background, with no stated result, is not such a statement.',
    'saturation_reached': 'Whether the passage says the binding curve reached a plateau (saturation) within the concentrations used (yes), or says it did not (no).',
    'signal_in_linear_range': 'Whether the passage says the absorbance (or other signal) was within the linear range of the reader, or did not saturate the detector (yes), or says it was not (no).',
    'wash_dissociation_considered': 'Whether the passage says that dissociation of the bound ligand during the washes was considered, limited or shown to be negligible, for example with a quick wash, or a comparison with an assay without washing (yes), or says it was not considered (no). Stating the number or the buffer of the washes is not such a statement.',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when the plate was washed, for example because a longer binding step gave the same signal (yes), or says it was not (no). An incubation time alone does not say this, and a statement of what an incubation was meant to achieve (for example to allow or to ensure equilibrium) is not a statement that equilibrium was reached.',
    'avidity_excluded': 'Whether the passage says multivalent binding (avidity) was excluded or controlled, for example with a monovalent ligand, a low coating density or a monomeric partner (yes), or says that multivalent binding contributed (no). A passage that only names the partners does not say this.',
    'coated_protein_active': 'Whether the passage says the coated protein was shown to be active or correctly oriented on the plate, for example because it was captured through a tag or an antibody, or because its known ligand bound it (yes), or says it was not (no).',
    'detection_does_not_interfere': 'Whether the passage says the detection reagent (the antibody or the conjugate) does not interfere with the binding, or does not bind the coated partner or the plate on its own (yes), or says it does (no).',
    'independent_experiments': 'Whether the passage says the replicates were independent experiments (separate plates, dilution series or days).',
    'single_estimate_method': 'Whether the passage itself says that the affinity was estimated only by this plate assay (yes), or says that another method was also used for it (no). A passage that merely reports one constant does not say this: leave it unavailable.',
    'binding_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the experiment showed that the two partners bind (a signal above the blank or control wells that rises with the titrated partner, a reported binding constant, or the plain statement that one binds the other as measured by ELISA); no when it says the experiment showed no binding (no signal above the blank or control wells, "did not bind", "no detectable binding"). A passage that only describes how the experiment was done, or names the method without its result, does not state this.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices
    (assay format, detection format, spread kind, fit model, readout, enzyme, blocking agent), the facts."""
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
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': _nullable({'enum': list(SUPPORTS)}),
                       'reason': _nullable({'enum': list(REASONS)})})
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
            _refuse(name, 'stated_has_value_unit_quote_support_and_no_reason')
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
    """The record of ``literature_elisa_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] if answer[name]['status'] == 'stated' else None for name in CHOICE_FIELDS},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
