"""The extraction of ONE BRET / NanoBRET experiment (bioluminescence resonance energy transfer in cells: a luciferase donor fused to one protein, a fluorescent acceptor or tracer on the other; a saturation titration over the acceptor-to-donor ratio gives BRETmax and BRET50, a tracer titration or displacement gives an apparent KD or Ki) from one
chunk of text, derived from the grader's input form (``literature_bret_record.py``).

Same design as the earlier extractions (SPR to AUC) and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a BRET experiment in cells is mostly qualitative or semi-quantitative, so the KD, the Ki and their spreads are fields that are mostly
unavailable. The reported numbers are the BRET50 of the pair and of the negative control (acceptor-to-donor ratio), BRETmax, the BRET ratio of the pair and of the negative control, the
lowest and the highest acceptor-to-donor ratio and the number of points, the tracer concentration, the R squared of the fit and the number of independent experiments; the format, the donor, the acceptor, the expression and the spread kind are choices;
and the facts are the controls and the results of this method (an interaction, saturation, a negative control pair and whether it gave no specific signal, donor only, acceptor only, expression levels measured, a subtracted background, swapped fusions, a displaced tracer,
independent experiments, one estimate method). Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the two components and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bret_record import (
    ACCEPTORS, BRET_FORMATS, DONORS, EXPERIMENT_TYPE, EXPRESSIONS, FACTS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
BRET_FORMAT = 'bret_format'
DONOR = 'donor'
ACCEPTOR = 'acceptor'
EXPRESSION = 'expression'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('titration_point_count', 'replicate_count')
CHOICES = {BRET_FORMAT: BRET_FORMATS, DONOR: DONORS, ACCEPTOR: ACCEPTORS, EXPRESSION: EXPRESSIONS, SPREAD_KIND: SPREAD_KINDS}

MEANING = {
    'kd': 'The apparent equilibrium dissociation constant that the passage reports under the name KD or Kd (apparent KD) from the BRET or NanoBRET experiment described in the passage (a titration of a tracer on the donor-fused target, or of the acceptor-fused protein, fitted as a saturation binding curve), in a concentration unit. A KD that the passage cites as known or previously reported, or one from another method (for example SPR, ITC or a radioligand assay), is not stated: leave it unavailable. A BRET50 is a ratio of acceptor to donor, not a KD: it is not this field, even when the passage calls it an apparent affinity. An IC50 is not a KD. When the passage gives KD values for several pairs or conditions without saying which one is the result, leave it unavailable. A passage that reports a saturation titration (BRET50, BRETmax) and also a tracer titration with its apparent KD states the KD: other quantities in the passage, such as BRET50 values of several pairs, do not make the KD ambiguous.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty of any other value is not this field.',
    'ki': 'The inhibition constant (Ki) of an unlabelled competitor that the passage reports from the displacement of a tracer in the BRET or NanoBRET experiment described in the passage, in a concentration unit. An IC50 is not a Ki unless the passage itself calls the number a Ki. A Ki cited from earlier work or from another method is not stated.',
    'ki_spread': 'The reported uncertainty of the Ki given in the ki field (standard error, standard deviation or confidence interval half-width), in a concentration unit, as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable.',
    'bret50': 'The BRET50 that the passage reports for the interacting pair of the experiment (the acceptor-to-donor expression ratio at which the BRET ratio is half of BRETmax, as one number; some papers call it the fluorescence/luminescence value at half-maximal BRET). The BRET50 of a negative control pair is not this field. A BRET50 given for several pairs is stated only for the pair that the passage describes as the interaction under test.',
    'bret50_negative_control': 'The BRET50 that the passage reports for the negative control pair of the experiment (a pair of proteins that the passage uses as a non-interacting or irrelevant control, run in the same saturation experiment), as one number. The BRET50 of the pair under test is not this field. A control the passage names but gives no BRET50 for does not state it.',
    'bret_max': 'The BRETmax that the passage reports (the maximal BRET ratio, the plateau of the saturation curve of the pair under test), as one number in a ratio or in milli BRET units (mBU). A BRET ratio read at one condition, and a BRETmax of a negative control, are not this field.',
    'bret_ratio_pair': 'The BRET ratio (net or raw, as the passage gives it) that the passage reports for the interacting pair of the experiment at one condition, as one number in a ratio or in milli BRET units (mBU). The plateau of a saturation curve is the bret_max field. A BRET ratio of the negative control or of the donor alone is not this field.',
    'bret_ratio_negative_control': 'The BRET ratio that the passage reports for the negative control (the donor alone, or a non-interacting pair) measured in the same experiment as the pair under test, as one number in a ratio or in milli BRET units (mBU). The BRET ratio of the pair under test is not this field.',
    'ratio_lowest': 'The lowest acceptor-to-donor expression ratio of the titration, as the passage gives it as one number (a ratio). A DNA amount (ng) or a concentration is not offered: leave it unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only a plot or one ratio does not state a lowest one.',
    'ratio_highest': 'The highest acceptor-to-donor expression ratio of the titration, as the passage gives it as one number (a ratio). A DNA amount (ng) or a concentration is not offered: leave it unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only a plot or one ratio does not state a highest one.',
    'titration_point_count': 'The number of different acceptor-to-donor ratios (or tracer concentrations) at which the titration was run, as the passage gives it as a whole number. The number of replicates, of wells, of cells and of time points is not this field.',
    'tracer_concentration': 'The concentration of the fluorescent tracer used in a NanoBRET target engagement experiment, as the passage gives it, in a concentration unit (a tracer at a fixed concentration in a displacement, or the highest one of a tracer titration is stated only when the passage says so). A concentration of a competitor or of a drug is not this field.',
    'fit_r_squared': 'The coefficient of determination (R squared, R2) of the fit of the saturation or displacement curve, as the passage gives it as one number. A p-value, an rmsd and a correlation of two replicates are not this field.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days, transfections or cell passages, reported as replicates or as n), as a whole number. Wells, technical replicates and points of one curve are not this field.',
    'bret50_spread': 'The reported uncertainty of the BRET50 given in the bret50 field (the BRET50 of the pair under test): its standard error, standard deviation or confidence interval half-width, as one number in the same ratio unit as the BRET50. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. The uncertainty of the BRET50 of the negative control, of a BRET ratio or of a KD is not this field.',
    'bret50_negative_control_spread': 'The reported uncertainty of the BRET50 of the negative control pair given in the bret50_negative_control field: its standard error, standard deviation or confidence interval half-width, as one number in the same ratio unit. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. The uncertainty of the BRET50 of the pair under test is not this field.',
    'bret_ratio_pair_spread': 'The reported uncertainty of the BRET ratio of the pair under test given in the bret_ratio_pair field: its standard error, standard deviation or confidence interval half-width, as one number in a ratio or in milli BRET units (mBU), in the same unit as that BRET ratio. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. The uncertainty of the BRET ratio of the negative control, of BRETmax or of a BRET50 is not this field.',
    'bret_ratio_negative_control_spread': 'The reported uncertainty of the BRET ratio of the negative control given in the bret_ratio_negative_control field: its standard error, standard deviation or confidence interval half-width, as one number in a ratio or in milli BRET units (mBU). A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. The uncertainty of the BRET ratio of the pair under test is not this field.',
    'bret_ratio_donor_only': 'The BRET ratio that the passage reports for the donor expressed alone, with no acceptor (the background BRET, the donor emission seen in the acceptor channel), as one number in a ratio or in milli BRET units (mBU). The BRET ratio of a non-interacting negative control pair, and a ratio of the pair under test, are not this field.',
    'tracer_kd': 'The apparent dissociation constant (KD) of the fluorescent tracer for the donor-fused target that the passage states as the affinity of the tracer (the tracer KD, whether measured in the experiment described or given as the tracer characterisation), in a concentration unit. The KD of any other pair, a BRET50 and an IC50 are not this field. A passage that gives a tracer concentration but not the affinity of the tracer does not state it.',
    BRET_FORMAT: 'The kind of BRET experiment the passage describes: a saturation titration (increasing acceptor over a constant donor, plotted against the acceptor-to-donor ratio, or a tracer titration), a competition or displacement (a tracer displaced by an unlabelled compound), both for the same experiment, or a ligand-induced change (the BRET ratio before and after the addition of a ligand). A passage that reports one BRET ratio of a pair against a control, with none of these, does not state it.',
    DONOR: 'The luciferase donor that the passage says was fused to the donor protein: Rluc (Renilla luciferase, including Rluc8 and RLuc) is rluc, NanoLuc (Nluc, NanoBRET) is nanoluc, another luciferase is other. A passage that does not name the donor does not state it.',
    ACCEPTOR: 'The acceptor that the passage says was used: a fluorescent protein fused to the partner (YFP, Venus, GFP2, mNeonGreen) is fluorescent_protein, a HaloTag with a fluorescent ligand is halotag_ligand, a cell-permeable fluorescent tracer that binds the donor-fused target is fluorescent_tracer, another is other. A passage that does not name the acceptor does not state it.',
    EXPRESSION: 'How the passage says the fusions were expressed in the cells: a transient transfection, a stable cell line, or a fusion made at the endogenous locus (CRISPR knock-in). A passage that names only the cell line does not state it.',
    SPREAD_KIND: 'What the uncertainty given in the kd_spread, ki_spread, bret50_spread, bret50_negative_control_spread, bret_ratio_pair_spread or bret_ratio_negative_control_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    'interaction_detected': 'Whether the passage says that the BRET signal showed the two proteins (or the tracer and the target) in proximity: a BRET signal above that of the control, a saturation, an increase of the BRET ratio when the acceptor partner was co-expressed (yes), or says that no BRET signal above the control was seen (no). A signal that the passage ascribes to random collision of over-expressed proteins, and an interaction that the passage shows only with another method, are not this fact.',
    'saturation_shown': 'Whether the passage says that the BRET ratio of the pair under test increased with the acceptor-to-donor ratio as a saturation curve (a hyperbola that reaches a plateau, BRETmax) (yes), or says that it rose linearly or did not saturate (no). A BRET ratio at one ratio does not state it.',
    'negative_control_pair_used': 'Whether the passage says that a non-interacting or irrelevant pair of proteins (for example a receptor or a membrane protein that is not expected to interact) was run as a negative control in the same way as the pair under test (yes), or says that no such control was run (no). The donor alone and the acceptor alone are not this fact.',
    'negative_control_no_specific_signal': 'Whether the passage says that the negative control pair gave no specific interaction (no BRET above background, a linear relationship, or a clearly higher BRET50 than the pair under test) (yes), or says that the negative control pair also gave a saturation curve or a signal like the pair under test (no). A passage that names a negative control but does not say what it gave does not state it.',
    'donor_only_control_done': 'Whether the passage says that the donor was expressed alone, with no acceptor, and its signal in the acceptor channel measured as a control (yes), or says that it was not (no).',
    'acceptor_only_control_done': 'Whether the passage says that the acceptor was expressed alone, with no donor, as a control (yes), or says that it was not (no).',
    'expression_levels_measured': 'Whether the passage says that the expression of the donor (luminescence) and of the acceptor (fluorescence) were measured in the same cells to give the acceptor-to-donor ratio or to match the levels (yes), or says that they were not (no).',
    'background_subtracted': 'Whether the passage says that the background BRET (the donor-only signal in the acceptor channel, or a no-acceptor control) was subtracted from the BRET ratios (yes), or says that it was not (no).',
    'fusion_orientation_swapped': 'Whether the passage says that both fusion orientations or tag positions (donor on either protein, N-terminal and C-terminal tags) were tested (yes), or says that only one was (no).',
    'tracer_displaced_by_competitor': 'Whether the passage says that an unlabelled competitor lowered the BRET signal of the tracer in a concentration-dependent way, as a displacement (yes), or says that it did not (no).',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate transfections, days or cell passages) rather than wells of one plate (yes), or says that they were not (no).',
    'hyperbola_preferred_over_linear': 'Whether the passage says that the saturation (hyperbolic) model fitted the data of the pair under test significantly better than a straight line, by a stated comparison of the two fits (an F-test, an extra sum-of-squares test, AIC or similar) (yes), or says that the hyperbola was not better than a straight line (no). A statement that a curve saturated, or that a fit had a high R squared, is not this fact (see saturation_shown and fit_r_squared).',
    'bret_constant_across_expression': 'Whether the passage says that, at a fixed acceptor-to-donor ratio, the BRET ratio of the pair stayed constant when the total expression of donor and acceptor was changed (a specific interaction) (yes), or says that the BRET ratio rose or fell with the total expression at a fixed ratio (random collision of over-expressed proteins) (no). A BRET ratio read at one expression level does not state it.',
    'single_estimate_method': 'Whether the passage says that the interaction or the affinity of these two proteins was determined by BRET only (yes), or says that it was also determined by another method (no). Another method that the passage mentions for a different purpose (for example confocal microscopy for localisation) is not this fact, and a passage that says nothing about other methods does not state it. A sentence that only describes the method that was used does not say that no other method was used: yes needs the passage to say that this method alone was used.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (format, donor, acceptor, expression, spread kind), the facts."""
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
        if name in QUANTITIES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_bret_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
