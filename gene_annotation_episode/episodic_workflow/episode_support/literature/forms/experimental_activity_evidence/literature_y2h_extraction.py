"""The extraction of ONE yeast two-hybrid (Y2H) experiment (a pairwise interaction test in yeast: a bait fused to a DNA-binding domain and a prey fused to an activation domain activate a reporter, read as growth on selective medium or as lacZ / beta-galactosidase activity, only if the two proteins interact; qualitative or semi-quantitative, no binding constant; the yeast one-hybrid and three-hybrid belong to it only where a passage reports a pairwise interaction test) from one
chunk of text, derived from the grader's input form (``literature_y2h_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a Y2H reports no binding constant, so there is no KD field. The reported numbers are the 3-AT concentration of the scoring and of the bait-alone test, the beta-galactosidase activities
(of the pair tested, of the negative control and of the positive control, in Miller units) with the SD and the SEM that the passage gives for the pair and for the negative control, the most dilute dilution with growth of the pair and of the negative control (a growth read-out), the incubation temperature and time and the number of independent experiments; the hybrid system, the fusion domains of the bait and the prey, the yeast strain and the selective medium
are choices; and the facts are the result and the controls of this method (an interaction, a bait alone inactive, a prey alone inactive, an unrelated or non-binding control negative, a positive control, the reciprocal orientation, growth on non-selective medium,
the expression of the fusions, more than one reporter activated, independent experiments). Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the bait, the prey and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_y2h_record import (
    BAIT_FUSION_DOMAINS, EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, PREY_FUSION_DOMAINS, QUANTITIES, SELECTIVE_MEDIA, SUPPORTS, SYSTEM_KINDS, UNITS, VERSION, YEAST_STRAINS,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
SYSTEM_KIND = 'system_kind'
BAIT_FUSION_DOMAIN = 'bait_fusion_domain'
PREY_FUSION_DOMAIN = 'prey_fusion_domain'
YEAST_STRAIN = 'yeast_strain'
SELECTIVE_MEDIUM = 'selective_medium_scored'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
CHOICES = {SYSTEM_KIND: SYSTEM_KINDS, BAIT_FUSION_DOMAIN: BAIT_FUSION_DOMAINS, PREY_FUSION_DOMAIN: PREY_FUSION_DOMAINS, YEAST_STRAIN: YEAST_STRAINS, SELECTIVE_MEDIUM: SELECTIVE_MEDIA}

MEANING = {
    'three_at_concentration': 'The concentration of 3-amino-1,2,4-triazole (3-AT, an inhibitor of the HIS3 gene product that raises the stringency of the histidine selection) in the selective medium on which the interaction of the pair was scored, as the passage gives it as one number in millimolar (mM). A concentration in another unit is not offered: leave it unavailable with the reason unit_not_in_vocabulary. When several 3-AT concentrations were used (a titration of the bait against autoactivation) and the passage does not say which one the result was scored on, leave it unavailable.',
    'beta_galactosidase_interaction': 'The lacZ / beta-galactosidase activity, in Miller units, that the passage reports for the pair of bait and prey whose interaction is being tested (the pair of the proteins the passage is about), as one number (a value given with a plus-minus is the number before it). The activity of a control pair (empty vector, unrelated protein, positive control) and a value in another unit (for example relative light units or percent) are not this field.',
    'beta_galactosidase_negative_control': 'The lacZ / beta-galactosidase activity, in Miller units, that the passage reports for the negative control (the bait with an empty prey vector, the prey with an empty bait vector, or the bait with an unrelated prey), as one number. When several negative controls with different values are given and the passage does not name one as the control of the result, leave it unavailable. The activity of the pair tested and of the positive control are not this field.',
    'bait_alone_three_at_concentration': 'The concentration of 3-AT, in millimolar (mM), of the selective medium on which the passage says the bait alone (with the empty prey vector) was tested for autoactivation, as one number. It is not the 3-AT concentration on which the pair was scored (that is three_at_concentration), unless the passage gives the autoactivation test its own concentration. When several concentrations were used for the bait alone (a titration) and the passage does not say which one is the test of the result, leave it unavailable.',
    'beta_galactosidase_interaction_sd': 'The standard deviation (SD) that the passage gives for the beta-galactosidase activity of the pair tested, in Miller units, as one number. Say it only when the passage says the spread is a standard deviation (for example "SD" or "plus-minus s.d."); a standard error is the field beta_galactosidase_interaction_sem, and a spread that the passage does not name is not stated. The spread of a control is not this field.',
    'beta_galactosidase_interaction_sem': 'The standard error of the mean (SEM, s.e.m. or "standard error") that the passage gives for the beta-galactosidase activity of the pair tested, in Miller units, as one number. A standard deviation is the field beta_galactosidase_interaction_sd, and a spread that the passage does not name is not stated. The spread of a control is not this field.',
    'beta_galactosidase_negative_control_sd': 'The standard deviation (SD) that the passage gives for the beta-galactosidase activity of the negative control, in Miller units, as one number. Say it only when the passage says the spread is a standard deviation; a standard error is the field beta_galactosidase_negative_control_sem. The spread of the pair tested is not this field.',
    'beta_galactosidase_negative_control_sem': 'The standard error of the mean (SEM, s.e.m. or "standard error") that the passage gives for the beta-galactosidase activity of the negative control, in Miller units, as one number. A standard deviation is the field beta_galactosidase_negative_control_sd. The spread of the pair tested is not this field.',
    'beta_galactosidase_positive_control': 'The lacZ / beta-galactosidase activity, in Miller units, that the passage reports for the positive control (a pair of proteins known to interact, such as the p53 and SV40 large T antigen pair supplied with the system), as one number. The activity of the pair tested and of the negative control are not this field.',
    'growth_dilution_interaction': 'For a growth read-out on a dilution series or spot assay: the dilution factor of the most dilute spot (or serial dilution) of the pair tested that still shows growth on the scored selective medium, as one number (undiluted is 1, a 10-fold dilution is 10, 10^-3 or 1:1000 is 1000). Say it only when the passage names the most dilute dilution at which the pair grew; a passage that only says the pair grew, or that shows growth in a figure, does not state it. The dilution of a control is not this field.',
    'growth_dilution_negative_control': 'For a growth read-out on a dilution series or spot assay: the dilution factor of the most dilute spot of the negative control (empty vector or unrelated protein) that still shows growth on the scored selective medium, as one number (undiluted is 1, 10^-3 or 1:1000 is 1000). Say it only when the passage gives a dilution at which the negative control grew; a negative control that did not grow at all has no such dilution, so leave it unavailable. The dilution of the pair tested is not this field.',
    'incubation_temperature': 'The temperature at which the yeast was incubated before the reporter was scored (the plates or the cultures), as a number. A passage that says only room temperature does not state it, and the temperature of a storage or of another step is not this field.',
    'incubation_time': 'The time for which the plates or the cultures were incubated before the reporter was scored (growth read, or beta-galactosidase assayed), as a number in hours (h) or days. The time of another step (for example the transformation or a lacZ reaction of minutes) is not this field. When several incubation times are given without saying which one was used for the result, leave it unavailable.',
    'replicate_count': 'The number of independent experiments the passage reports for the interaction test (separate transformations, experiments on separate days, or independent clones reported as replicates), as a whole number. Spots of one plate, colonies of one transformation and the number of pairs tested are not this field.',
    SYSTEM_KIND: 'Which hybrid system the passage reports for the pairwise interaction test: a yeast two-hybrid (a protein bait and a protein prey; y2h), a yeast one-hybrid (a DNA bait and a prey that is a protein fused to an activation domain; y1h) or a yeast three-hybrid (an RNA or a small molecule bridges the two fusions; y3h). A passage that does not name the system does not state it.',
    BAIT_FUSION_DOMAIN: 'The DNA-binding domain that the passage says the bait was fused to: the GAL4 DNA-binding domain (gal4_dbd; pGBKT7, pGBT9), the LexA DNA-binding domain (lexa_dbd; pBTM116, pEG202) or another domain. A vector name alone (for example pGBKT7) does not state it unless the passage also names the domain.',
    PREY_FUSION_DOMAIN: 'The activation domain that the passage says the prey was fused to: the GAL4 activation domain (gal4_ad; pGADT7, pACT2), the B42 activation domain (b42_ad; pJG4-5), the VP16 activation domain (vp16_ad) or another domain. A vector name alone does not state it unless the passage also names the domain.',
    YEAST_STRAIN: 'The reporter strain of Saccharomyces cerevisiae that the passage names for the test: AH109, Y2HGold, PJ69-4A, L40, EGY48, or another strain. A strain that the passage names only for another purpose (for example a prey library strain used for mating) is not this field.',
    SELECTIVE_MEDIUM: 'The selective medium on which the passage says the interaction was scored by growth: a medium lacking histidine (minus_histidine), lacking adenine (minus_adenine) or lacking both (minus_histidine_and_adenine), or another medium. A medium lacking only leucine and tryptophan is the non-selective plasmid-selection medium, not this field. When several selective media were used and the passage names none as the result, leave it unavailable.',
    'interaction_detected': 'Whether the passage says that the bait and the prey of the pair tested interacted, as growth on selective medium or activation of a reporter (yes), or says that they did not (no growth, no activation) (no). The interaction of a control pair and an interaction shown only with another method are not this fact.',
    'bait_alone_inactive': 'Whether the passage says that the bait together with the empty prey vector did not activate the reporter, so the bait does not autoactivate (yes), or says that the bait alone activated the reporter (no). A passage that says only that controls were done does not state it.',
    'prey_alone_inactive': 'Whether the passage says that the prey together with the empty bait vector did not activate the reporter (yes), or says that the prey alone activated the reporter (no).',
    'non_interacting_control_done': 'Whether the passage says that an unrelated protein, or a non-binding mutant, in place of the prey or of the bait did not activate the reporter (yes), or says that it did (no). The empty vector is not this fact (it is the bait alone and the prey alone).',
    'positive_control_done': 'Whether the passage says that a known interacting pair was included and activated the reporter, so the system worked (yes), or says that the known pair was tested and did NOT activate the reporter (no). A positive control that is only named, or said not to have been done, has no stated result: leave it unavailable, not no.',
    'reciprocal_orientation_tested': 'Whether the passage says that the interaction was also tested with the bait and the prey swapped (each protein as bait and as prey) and was seen in both orientations (yes), or says that the swapped orientation was tested and the interaction was NOT seen in it, so it was seen in only one orientation (no). A passage that gives one orientation only, or says the swapped orientation was not tested, says nothing about the result: leave it unavailable, not no.',
    'nonselective_growth_shown': 'Whether the passage says that the yeast carrying the pair grew on non-selective medium (for example without leucine and tryptophan, which selects the two plasmids), so both plasmids were present and the cells were alive (yes), or says that they did not (no).',
    'fusion_expression_verified': 'Whether the passage says that the expression of the bait fusion and of the prey fusion in yeast was shown (for example by immunoblot) (yes), or says that a fusion was tested and was not expressed (no). Expression in another host is not this fact; an expression test that is not mentioned or was not done is unavailable, not no.',
    'more_than_one_reporter_activated': 'Whether the passage says that the pair activated more than one reporter, for example growth on selective medium and beta-galactosidase activity, or HIS3 and ADE2 (yes), or says that it activated one reporter and not another that was tested (no). A passage that reports one reporter, or a second reporter that was not tested, does not state it.',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate transformations, days or clones) rather than spots or colonies of one plate (yes), or says that they were not (no).',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (system kind, bait fusion domain, prey fusion domain, yeast strain, selective medium), the facts."""
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
    """The record of ``literature_y2h_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
