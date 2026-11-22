"""The extraction of ONE AlphaScreen / AlphaLISA binding experiment (bead-based amplified luminescent proximity binding assay: direct titration, cross-titration or competition) from one
chunk of text, derived from the grader's input form (``literature_alpha_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS and ELISA extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused. Each stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well
its quote supports it): required when stated, None when unavailable; the record keeps it and the converter turns it into a degree.

Differences from the other types that come from the form: the signal is a count rate (cps) of acceptor-bead emission, so the signal at
the top of the curve, the background, the signal-to-background ratio and the Z' factor are fields; the reported number is an apparent
KD (or an EC50 or an IC50, which are separate fields and are not dissociation constants) of bead-presented complexes; the bead
coatings, the bead concentration, the concentrations of the two captured partners, the plate format, the binding step and the bead
step are fields or choices; a cross-titration and the hook effect are of this method; and the facts are the controls of this method
(a counter-screen for signal interference, the handling of the hook effect, a partner concentration at or below the KD, the linear
range of the reader, equilibrium, a non-binding control, the effect of the tag or the capture on the binding, protection of the
beads from light and avidity). Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references
(``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller and the three preparation references
(``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_record import (
    ASSAY_FORMATS, BEAD_COATINGS, CHOICE_FIELDS, EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, TITRATION_DESIGNS, UNITS, VERSION, fact,
    point, unavailable)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
ASSAY_FORMAT = 'assay_format'
TITRATION_DESIGN = 'titration_design'
DONOR_BEAD = 'donor_bead'
ACCEPTOR_BEAD = 'acceptor_bead'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'titration_point_count', 'technical_replicate_count', 'plate_well_count')
CHOICES = {ASSAY_FORMAT: ASSAY_FORMATS, TITRATION_DESIGN: TITRATION_DESIGNS, DONOR_BEAD: BEAD_COATINGS, ACCEPTOR_BEAD: BEAD_COATINGS, SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS}

MEANING = {
    'kd': 'The dissociation constant of the binding partners, as the passage reports it under the name KD (or dissociation constant, or apparent KD) from the binding curve. A half-maximal concentration reported under the name EC50 or IC50 is not this field, and a value the passage does not call a dissociation constant is not this field.',
    'ki': 'The inhibition constant Ki of an unlabelled competitor, as the passage reports it under that name from a competition experiment on the same partners as the binding experiment (a competition beside a titration is part of this experiment, not another one). An IC50 is not this field, and a value is not a Ki unless the passage calls it one.',
    'ec50': 'The half-maximal effective concentration EC50 of the binding curve (the concentration of the titrated partner at half of the maximal signal), as the passage reports it under the name EC50 or half-maximal effective concentration. A value the passage calls a KD is not this field.',
    'ic50': 'The half-maximal inhibitory concentration IC50 of a competition (the concentration of the competitor that lowers the signal to half), as the passage reports it under the name IC50 or half-maximal inhibitory concentration, from a competition experiment on the same partners as the binding experiment (a competition beside a titration is part of this experiment, not another one). A value the passage calls a Ki or a KD is not this field. When the passage gives several IC50 values for different conditions without saying which one is the result, leave it unavailable.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. It belongs to the Ki, not to the KD. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'signal_maximum': 'The signal at the top of the binding curve (the highest signal, or the positive control), as the passage gives it as a number of counts per second (cps). A signal in other units, a ratio or a percentage is not this field.',
    'signal_background': 'The signal of the background (wells without one of the partners, or the blank or negative control), as the passage gives it as a number of counts per second (cps). A signal in other units, a ratio or a percentage is not this field.',
    'signal_to_background': 'The signal-to-background ratio (S/B) of the assay as a number, when the passage reports it as a ratio. A ratio you would have to calculate from a signal and a background is not this field.',
    'z_prime': 'The Z-prime factor (Z\') of the assay as a number, when the passage reports it. Any other statistic is not this field.',
    'bead_concentration': 'The final concentration of the donor and acceptor beads in the well, as the passage gives it in a mass per volume (when the passage gives one concentration for both bead kinds, that one). A dilution factor of a stock is not this field, and neither is the concentration of a partner.',
    'labelled_partner_concentration': 'The concentration of the labelled (for example biotinylated) partner that is captured by the donor beads, as the passage gives it as a concentration held constant in the well at which the experiment was done (it is later compared with the KD, to see whether this partner depletes the other). A concentration of the tagged partner or of a competitor is not this field, and neither is a concentration the passage only chooses or recommends for later experiments, or one point of a series.',
    'tagged_partner_concentration': 'The concentration of the tagged (for example His-, GST- or Fc-tagged) partner that is captured by the acceptor beads, as the passage gives it as a concentration held constant in the well at which the experiment was done (it is later compared with the KD, to see whether this partner depletes the other). A concentration of the labelled partner or of a competitor is not this field, and neither is a concentration the passage only chooses or recommends for later experiments, or one point of a series.',
    'plate_well_count': 'The number of wells of the microplate format (for example 96, 384 or 1536), as a whole number, when the passage names the format.',
    'titration_point_count': 'The number of concentrations of the series of the titrated partner or of the competitor (the number of dilutions), as a whole number, when the passage gives it as a number.',
    'technical_replicate_count': 'The number of wells of the same sample on one plate (technical replicates, for example duplicates or triplicate wells), as a whole number, when the passage gives it as a number. The number of independent experiments is not this field.',
    'incubation_time': 'How long the partners (and the competitor, if any) were left to bind before the beads were added. The time of the step after the beads were added is not this field, and neither is a time that is only a range of times tried.',
    'bead_incubation_time': 'How long the plate was incubated after the beads were added, before it was read. The time of the binding step of the partners before the beads is not this field.',
    'temperature': 'The temperature at which the incubation was done, as a number. A passage that says only room temperature does not state it.',
    'replicate_count': 'The number of independent experiments the passage reports (separate plates, dilution series or days), as a whole number. Wells of one plate are not this field.',
    SERIES: 'The concentrations of the titrated partner (or of the competitor) that were used, as a list of numbers in one unit. A range with a first and a last concentration, or a number of points with a top concentration, is not a list.',
    ASSAY_FORMAT: 'Whether the experiment titrated a partner against the other (saturation titration) or lowered the signal of a pair with an unlabelled competitor (competition). A passage that describes both formats without saying which one the reported constant comes from does not state it: leave it unavailable. A titration or cross-titration done only to choose assay conditions (partner or bead concentrations, the hook point) does not state the format unless the passage says the curve gives a binding constant or a half-maximal concentration.',
    TITRATION_DESIGN: 'Whether both partners were titrated against each other in a matrix (cross-titration) or one partner was held at a constant concentration while the other was titrated (fixed-partner titration), as the passage states it.',
    DONOR_BEAD: 'The coating of the donor beads, as the passage names it: streptavidin, nickel chelate, an anti-tag antibody, protein A, glutathione or another one. A bead coating is often named in several places: quote enough neighbouring words that the quote occurs once.',
    ACCEPTOR_BEAD: 'The coating of the acceptor beads, as the passage names it: streptavidin, nickel chelate, an anti-tag antibody, protein A, glutathione or another one. A bead coating is often named in several places: quote enough neighbouring words that the quote occurs once.',
    SPREAD_KIND: 'What the reported KD or Ki uncertainty is.',
    FIT_MODEL: 'The model the passage names in words as the one the curve was fitted with: a one-site binding model, a quadratic binding model, a four-parameter logistic (sigmoidal dose-response) model, a bell-shaped model of a curve that falls at a high concentration, a competitive binding model, or another named one. A model the passage only calls simple, or an equation that is only written out, is not this field: do not work out the model from the form of an equation.',
    'counter_screen_done': 'Whether the passage says that signal interference was tested with a counter-screen, for example a control linker that brings donor and acceptor beads together without the partners (a biotinylated His-tagged peptide), a TruHits control, or a test of colour or singlet oxygen quenching, biotin mimetics or metal chelators (yes), or says it was not (no).',
    'hook_effect_handled': 'Whether the passage says that the fall of the signal at a high concentration of a partner (the hook effect, a bell-shaped curve) was looked for and dealt with, for example by choosing concentrations below the hook point, by fitting only the rising part of the curve or by a bell-shaped model (yes), or says it was observed and not dealt with (no). A passage that does not mention a hook effect does not state this.',
    'partner_concentration_below_kd': 'Whether the passage says that the partner that was held at a constant concentration was used at or below the KD, or at a concentration low enough not to deplete the titrated partner (yes), or says it was above the KD (no). Giving the concentration alone does not state this.',
    'signal_in_linear_range': 'Whether the passage says the signal was within the linear range of the reader, or did not saturate the detector (yes), or says it was not (no).',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when the beads were added or the plate was read, for example because a longer incubation gave the same result (yes), or says it was not (no). An incubation time alone does not say this, and a statement of what an incubation was meant to achieve (for example to allow or to ensure equilibrium) is not a statement that equilibrium was reached.',
    'nonspecific_binding_checked': 'Whether the passage says non-specific binding was checked with a control, for example an irrelevant protein, a non-binding mutant or an untagged partner, that gave no or little signal (yes), or says it was not (no). A control that is only used to estimate or subtract a background, with no stated result, is not such a statement.',
    'capture_does_not_alter_binding': 'Whether the passage says that the tag, the label or the capture on the beads does not alter the binding of the partners, for example because the result agrees with a measurement with untagged partners or with another capture format (yes), or says it does (no).',
    'light_protected': 'Whether the passage says the beads were protected from light, for example handled under subdued or green light or kept in the dark (yes), or says they were not (no).',
    'avidity_excluded': 'Whether the passage says multivalent binding (avidity) of the bead-presented partners was excluded or controlled, for example by a low capture density or by agreement with a solution method (yes), or says that multivalent binding contributed (no). A passage that only names the partners or the beads does not say this.',
    'independent_experiments': 'Whether the passage says the replicates were independent experiments (separate plates, dilution series or days).',
    'single_estimate_method': 'Whether the passage itself says that the affinity was estimated only by this bead assay (yes), or says that another method was also used for it (no). A passage that merely reports one constant does not say this: leave it unavailable.',
    'binding_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the experiment showed that the two partners bind (a bead-proximity signal above background for the pair, a reported binding constant, or the plain statement that one binds the other as measured by AlphaScreen); no when it says the experiment showed no binding (no bead-proximity signal above background, "did not bind", "no detectable binding"). A passage that only describes how the experiment was done, or names the method without its result, does not state this.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices
    (assay format, titration design, the two bead coatings, spread kind, fit model), the facts."""
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
    """The record of ``literature_alpha_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
