"""The extraction of ONE scintillation proximity assay (SPA) binding experiment (a radioligand binding to a target captured on scintillant-containing beads, no separation or wash; saturation binding for KD and Bmax, competition binding for IC50 and Ki by the Cheng-Prusoff equation) from one
chunk of text, derived from the grader's input form (``literature_spa_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen and radioligand extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: the reported numbers are the KD of the radioligand and the number of sites
Bmax from a saturation experiment and the IC50 and the Ki from a competition (separate fields), the Hill slope, the radioligand's
specific activity, its single concentration in a competition and the lowest and highest concentration of a saturation series, the amount
of beads and the amount of the captured target, the percent of the radioligand that was bound, the non-specific binding (its fraction of the
total binding, the excess of the unlabelled ligand that defines it and that ligand's own affinity), the signal of the control without captured target, the counting
efficiency and the settling time; the isotope, the kind of bead, the way the target is captured, the kind of target, the counter and the
fit model are choices; and the facts are the controls of this method (no-wash homogeneous format, determination of non-specific binding,
the non-proximity signal, the control without captured target, equilibrium, ligand depletion, colour quench, bead settling, purity of the
radioligand, a non-linear fit, the Cheng-Prusoff equation with the KD of the radioligand itself). Every number must be above 0. Fields not
extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by the caller and
the three preparation references (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_record import (
    ASSAY_FORMATS, BEAD_TYPES, CAPTURE_METHODS, COUNTERS, EXPERIMENT_TYPE, FACTS, FIT_MODELS, ISOTOPES, PREPARATION_KEYS, PREPARATION_TYPES, QUANTITIES,
    SPREAD_KINDS, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SERIES = 'concentration_series'
ASSAY_FORMAT = 'assay_format'
ISOTOPE = 'radioligand_isotope'
BEAD_TYPE = 'bead_type'
CAPTURE = 'capture_method'
PREPARATION_TYPE = 'preparation_type'
COUNTER = 'counter'
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count', 'titration_point_count', 'technical_replicate_count')
CHOICES = {ASSAY_FORMAT: ASSAY_FORMATS, ISOTOPE: ISOTOPES, BEAD_TYPE: BEAD_TYPES, CAPTURE: CAPTURE_METHODS, PREPARATION_TYPE: PREPARATION_TYPES, COUNTER: COUNTERS, SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS}

MEANING = {
    'kd': 'The equilibrium dissociation constant of the radioligand for its captured target, as the passage reports it under the name KD or Kd (or dissociation constant) from a saturation binding experiment described in the passage. A KD that the passage cites as a known or previously reported property of the ligand, rather than one measured in the experiment described, is not stated: leave it unavailable. An IC50 or a Ki is not this field, and a constant the passage does not call a dissociation constant is not this field. When the passage gives KD values for several targets, preparations or conditions without saying which one is the result, leave it unavailable.',
    'bmax': 'The maximal number of binding sites, as the passage reports it under the name Bmax (or maximal binding capacity or receptor density), in one of the units the field offers: per mg of protein, per cell, or as a concentration. A value that is not the number of sites (for example a specific activity, an amount of protein or beads, a count rate or a percent of binding) is not this field.',
    'ki': 'The inhibition constant Ki of an unlabelled ligand, as the passage reports it under that name from a competition (displacement) experiment. An IC50 is not this field, a KD is not this field, and a value is not a Ki unless the passage calls it one. When the passage gives several Ki values for different ligands or conditions without saying which one is the result, leave it unavailable.',
    'ic50': 'The half-maximal inhibitory concentration IC50 of an unlabelled ligand in a competition (displacement) experiment (the concentration that lowers the specific binding of the radioligand to half), as the passage reports it under the name IC50 or half-maximal inhibitory concentration. A value the passage calls a Ki or a KD is not this field. When the passage gives several IC50 values for different ligands or conditions without saying which one is the result, leave it unavailable.',
    'hill_slope': 'The Hill slope (Hill coefficient, nH, or slope factor) of the binding or competition curve as a number, when the passage reports it. Any other slope is not this field.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. It belongs to the Ki, not to the KD. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'specific_activity': 'The specific activity of the radioligand, as the passage gives it in curies per millimole (Ci/mmol). A specific activity in another unit (for example becquerel or Ci per gram) is not offered: answer unavailable with the reason unit_not_in_vocabulary. A radioactivity per volume or per well is not this field.',
    'radioligand_concentration': 'The single concentration of the radioligand that was used in a competition (displacement) experiment, as the passage gives it as a concentration. A concentration of the unlabelled competitor, a concentration used in a saturation series, or a series of concentrations is not this field.',
    'radioligand_range_lowest': 'The lowest concentration of the radioligand of a saturation series, when the passage gives the series as a range with a first and a last concentration or names its lowest concentration. The concentration of a competition is not this field.',
    'radioligand_range_highest': 'The highest concentration of the radioligand of a saturation series, when the passage gives the series as a range with a first and a last concentration or names its highest concentration. The concentration of a competition is not this field.',
    'bead_amount': 'The amount of scintillation proximity beads per assay well, as the passage gives it in micrograms or milligrams of beads per well. A concentration of beads (for example mg/mL) is not offered here: do not convert it.',
    'bead_concentration': 'The concentration of the scintillation proximity beads in the assay, as the passage gives it in milligrams per millilitre. An amount of beads per well is not this field: do not convert it.',
    'receptor_amount': 'The amount of the captured target (protein) per assay well, as the passage gives it in micrograms or milligrams of protein. A protein concentration of a stock or of the assay, a number of cells, or a volume is not offered: do not convert it.',
    'percent_bound': 'The percent of the total added radioligand that was bound (the bound fraction), when the passage gives it as a percent. A percent of specific binding, of non-specific binding or of inhibition is not this field, and a percent you would have to calculate is not this field.',
    'nonspecific_fraction': 'The non-specific binding as a percent of the total binding (usually at the highest radioligand concentration), when the passage gives it as a percent of the total binding. A percent of the specific binding, or a percent you would have to calculate, is not this field.',
    'nonspecific_ligand_concentration': 'The concentration of the unlabelled ligand that was used to define non-specific binding (the excess of unlabelled ligand), as the passage gives it as a concentration. The concentration of the competitor of a competition curve, or of the radioligand, is not this field. When the passage gives several different concentrations for different conditions without saying which one is the result, leave it unavailable.',
    'nonspecific_ligand_affinity': 'The KD or Ki of the unlabelled ligand that was used to define non-specific binding, as the passage gives it for that ligand and the captured target, in a concentration unit. The KD of the radioligand is not this field unless the passage says the unlabelled ligand is the same compound; the affinity of the competitor of a competition curve is not this field.',
    'nonspecific_excess': 'The fold excess of the unlabelled ligand over its Kd that the passage says defined non-specific binding (for example 100-fold or 1000 times the Kd), as a number. A concentration of the unlabelled ligand is not this field.',
    'bead_only_fraction': 'The signal of the control without the captured target (beads and radioligand only, or an uncaptured or untagged target) as a percent of the total signal, when the passage gives it as a percent of the total signal. A percent of the specific signal, non-specific binding defined with an excess of unlabelled ligand, or a percent you would have to calculate, is not this field.',
    'counting_efficiency': 'The counting efficiency of the scintillation counting, as a percent, when the passage gives it as a percent. A count rate or a number of counts is not this field.',
    'association_half_time': 'The time to half of the plateau binding (the half-time of association) in an association time course the passage reports, as a time. An incubation time, a dissociation half-time or the time to reach a plateau is not this field.',
    'incubation_time': 'How long the radioligand was incubated with the captured target and the beads before the plate was counted. A time of settling of the beads, of a pre-incubation of beads with the target or of counting is not this field, and neither is a time that is only a range of times tried.',
    'settling_time': 'How long the plate stood for the beads to settle before it was counted, when the passage gives it as a time. An incubation time or a counting time is not this field.',
    'temperature': 'The temperature at which the incubation was done, as a number. A passage that says only room temperature does not state it.',
    'titration_point_count': 'The number of radioligand concentrations of a saturation series (or of competitor concentrations of a competition curve), as a whole number, when the passage gives it as a number.',
    'technical_replicate_count': 'The number of wells of the same condition within one experiment (for example duplicates or triplicates), as a whole number, when the passage gives it as a number. The number of independent experiments is not this field.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days or preparations), as a whole number. Wells of one experiment are not this field.',
    SERIES: 'The concentrations of the radioligand of a saturation series that were used, as a list of numbers in one unit. A range with a first and a last concentration, or a number of points with a top concentration, is not a list.',
    ASSAY_FORMAT: 'Whether the experiment is a saturation experiment (increasing concentrations of the radioligand, giving a KD and a Bmax), a competition (displacement) experiment (an unlabelled ligand lowering the binding of one concentration of the radioligand, giving an IC50 or a Ki), or a kinetic experiment (association and dissociation time courses), as the passage states it. A passage that describes several of these without saying which one the reported constant comes from does not state it: leave it unavailable. A passage that only says how data were analysed (for example which kinds of data a program or a model was applied to) describes the analysis, not the experiment: leave it unavailable unless the passage says the experiment itself was of that kind.',
    ISOTOPE: 'The radioactive isotope of the radioligand, as the passage names it: tritium (3H), iodine-125 (125I), sulfur-35 (35S) or another one.',
    BEAD_TYPE: 'The kind of scintillant bead, as the passage names it: yttrium silicate (YSi) beads, polyvinyltoluene (PVT) beads or another kind. The molecule that captures the target on the bead (WGA, streptavidin, a metal chelate, an antibody) is not the kind of bead.',
    CAPTURE: 'How the target was captured on the bead, as the passage states it: by wheat-germ agglutinin (WGA), by streptavidin binding a biotinylated target, by a metal chelate (nickel, copper or cobalt) binding a His-tagged target, by an antibody, or another way. The kind of scintillant in the bead is not this field.',
    PREPARATION_TYPE: 'What the captured target was in the assay, as the passage states it: a membrane preparation, a purified protein, whole cells, or another one.',
    COUNTER: 'The plate counter on which the counts were read, as the passage names it: a MicroBeta counter, a TopCount counter or another one.',
    SPREAD_KIND: 'What the reported KD or Ki uncertainty is.',
    FIT_MODEL: 'The model the passage names in words as the one the curve was fitted with: a one-site binding model, a two-site binding model, a model with a free Hill slope, a one-site competition (competitive binding) model, or another named one. A model the passage only calls simple, or an equation that is only written out, is not this field: do not work out the model from the form of an equation. A name that joins two model names (for example a one-site and a two-site model together) names more than one model: leave it unavailable.',
    'homogeneous_no_wash_format': 'Whether the passage says that the bound radioligand was measured without a separation or a wash step, so that the radioligand that is not bound stays in the well during counting (yes), or says that a separation or wash step was done before counting (no). Naming the assay or the beads without saying that no separation or wash was done does not state this.',
    'nonspecific_binding_determined': 'Whether the passage says that non-specific binding was determined with an excess of an unlabelled ligand and subtracted from the total binding to give the specific binding (yes), or says that it was not (no). Naming the excess ligand without saying that non-specific binding was determined does not state this.',
    'nonspecific_ligand_is_radioligand': 'Whether the passage says that the unlabelled ligand used to define non-specific binding is the unlabelled form of the radioligand itself (the same compound without the radioactive label) (yes), or says that it is a different compound (no). Naming an unlabelled ligand with a name that is only similar to the radioligand\'s name does not state this unless the passage says it is the same compound or that the radioligand was displaced by its own unlabelled form.',
    'nonproximity_signal_checked': 'Whether the passage says that the signal of radioligand that is not bound to the captured target (a non-proximity signal of the free radioligand in solution, for example the counts of the radioligand with beads at the highest concentration, or a test that the free radioligand gives only a small signal) was measured or shown to be small (yes), or says it was not (no).',
    'bead_only_control_done': 'Whether the passage says that a control without the captured target was measured, because the radioligand can bind to the bead itself (beads and radioligand only, an uncaptured or untagged target, or beads without receptor) (yes), or says it was not (no). Non-specific binding defined with an excess of unlabelled ligand is not this control.',
    'equilibrium_reached': 'Whether the passage says the binding was at equilibrium when the plate was counted, for example because an association time course reached a plateau by the incubation time (yes), or says it was not (no). An incubation time alone does not say this, and a statement of what an incubation was meant to achieve (for example to allow or to ensure equilibrium) is not a statement that equilibrium was reached.',
    'ligand_depletion_checked': 'Whether the passage says that the depletion of the free radioligand by binding was checked or avoided, for example because less than 10 percent of the added radioligand was bound, a large molar excess of radioligand over the target was kept, or the free concentration was measured (yes), or says that it was not (no). A passage that does not mention depletion does not state this.',
    'quench_interference_checked': 'Whether the passage says that the lowering of the counts by coloured or quenching compounds or by the buffer (colour quench) was checked or corrected for, for example with a quench curve, a counting-efficiency correction or a test of the compounds in the assay (yes), or says that it was not (no).',
    'bead_settling_controlled': 'Whether the passage says that the settling of the beads was controlled, for example by a fixed settling time before the plate was counted or by a check that the signal is stable (yes), or says it was not (no). A passage that only states how long the plate was incubated does not state this.',
    'radioligand_purity_checked': 'Whether the passage says the radiochemical purity of the radioligand, or its freedom from degradation, was checked (yes), or says it was not (no). A purity given by the supplier without saying that it was checked in this experiment still states it only if the passage says it was checked.',
    'nonlinear_fit_used': 'Whether the passage says the constants were obtained by a non-linear fit of the binding curve (yes), or says they were obtained from a linearised plot such as a Scatchard plot (no).',
    'cheng_prusoff_applied_with_own_kd': 'Whether the passage says the Ki was calculated from the IC50 with the Cheng-Prusoff equation using the KD of the same radioligand on the same target (yes), or says it was not, for example that the IC50 is reported without correction as the Ki or that the KD of another radioligand or target was used (no). A passage that only names the equation does not say which KD was used: leave it unavailable.',
    'independent_experiments': 'Whether the passage says the replicates were independent experiments (separate experiments, days or preparations).',
    'single_estimate_method': 'Whether the passage itself says that the affinity was estimated only by this scintillation proximity experiment (yes), or says that another method was also used for it (no). A passage that merely reports one constant does not say this: leave it unavailable.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the series, the choices
    (assay format, isotope, bead type, capture method, preparation type, counter, spread kind, fit model), the facts."""
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
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': {**_nullable({'enum': list(SUPPORTS)}), 'description': SUPPORT_MEANING}, 'reason': _nullable({'enum': list(REASONS)})})
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
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one
    carries none. Returns ``answer``."""
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
    """The record of ``literature_spa_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
