"""The extraction of ONE electrophoretic mobility shift assay (EMSA, gel shift) experiment (a labelled nucleic acid probe incubated with a protein and run on a native gel; the complex migrates more slowly; qualitative, or a titration giving an apparent KD) from one
chunk of text, derived from the grader's input form (``literature_emsa_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA and pull-down extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: an EMSA is often qualitative (a shifted band is seen), so the apparent KD and its spread are fields that
are mostly unavailable, and the shift itself is a fact. The reported numbers are the apparent KD, the fraction of the probe shifted at the highest protein concentration, the
lowest and highest protein concentration, the probe concentration and length, the binding buffer (salt, magnesium, glycerol), the amount of non-specific competitor and the
fold excess of the specific competitor, the incubation, the gel and the run, the number of titration points, the number of shifted species and the number of independent experiments;
the probe type, the label, the gel type, the competitor type, the spread kind and the fit model are choices; and the facts are the controls and the results of this method
(the shift, competition by the specific and the non-specific competitor, the mutant probe, the probe-alone lane, the non-specific protein control, quantification of the free
probe, the probe at or below the KD, equilibrium, the supershift, purity of the protein, survival of the complex in the gel run, the protein range bracketing the KD,
independent experiments, one estimate method). Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the probe and the protein and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import (
    COMPETITOR_TYPES, EXPERIMENT_TYPE, FACTS, FIT_MODELS, GEL_TYPES, PREPARATION_KEYS, PROBE_LABELS, PROBE_TYPES, QUANTITIES, SPREAD_KINDS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
PROBE_TYPE = 'probe_type'
PROBE_LABEL = 'probe_label'
GEL_TYPE = 'gel_type'
COMPETITOR_TYPE = 'nonspecific_competitor_type'
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
COUNTS = ('titration_point_count', 'shifted_species_count', 'replicate_count')
CHOICES = {PROBE_TYPE: PROBE_TYPES, PROBE_LABEL: PROBE_LABELS, GEL_TYPE: GEL_TYPES, COMPETITOR_TYPE: COMPETITOR_TYPES, SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS}

MEANING = {
    'kd': 'The apparent equilibrium dissociation constant of the protein for the labelled probe, as the passage reports it under the name KD or Kd (apparent Kd, dissociation constant, or the protein concentration at which half of the probe is shifted) from a titration of the protein described in the passage. A KD that the passage cites as a known or previously reported property of the protein, rather than one measured in the experiment described, is not stated: leave it unavailable. A concentration that merely gave a shift, a concentration used in one lane, and an IC50 or EC50 of a competitor are not this field. When the passage gives KD values for several proteins, probes or conditions without saying which one is the result, leave it unavailable.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value is not this field.',
    'fraction_shifted_highest': 'The percent of the probe that was in the shifted band (bound by the protein) at the highest protein concentration of the titration, when the passage gives it as a percent. A percent of binding at another concentration, a percent of competition, and a percent you would have to calculate are not this field.',
    'plateau_shifted_fraction': 'The plateau of the fitted binding curve: the maximum percent of the probe that the fit says can be shifted (a fitted maximum, an upper asymptote, or the stated active fraction of the probe), when the passage gives it as a percent. The percent shifted at the highest protein concentration is the fraction_shifted_highest field, not this one, and a plateau you would have to read off a figure or calculate is not this field.',
    'competition_protein_concentration': 'The concentration of the protein in the reactions of the competition (the lanes where the unlabelled specific probe was added), as the passage gives it as a concentration. The concentration of the protein in the titration lanes (the lowest and the highest) is not this field unless the passage says that the competition used it; the concentration of the competitor itself is not this field.',
    'protein_concentration_lowest': 'The lowest protein concentration of the titration (the first lane with protein), when the passage gives the series as a range with a first and a last concentration or names its lowest concentration. A single concentration that gave a shift is not this field.',
    'protein_concentration_highest': 'The highest protein concentration of the titration, when the passage gives the series as a range with a first and a last concentration or names its highest concentration. A single concentration that gave a shift is not this field.',
    'probe_concentration': 'The concentration of the labelled probe in the binding reaction, as the passage gives it as a concentration. An amount of probe (for example a number of counts or femtomoles) and the concentration of an unlabelled competitor are not offered here: do not convert them.',
    'probe_length': 'The length of the probe, as the passage gives it in base pairs (bp, for a double-stranded probe) or nucleotides (nt, for a single-stranded probe or an RNA). A length in kilobases or any other unit is not offered: answer unavailable with the reason unit_not_in_vocabulary.',
    'salt_concentration': 'The concentration of salt (for example NaCl or KCl) in the binding buffer of the reaction, as the passage gives it in millimolar or molar. A salt concentration of the gel buffer, of the running buffer or of a protein storage buffer is not this field.',
    'magnesium_concentration': 'The concentration of magnesium (for example MgCl2) in the binding buffer of the reaction, as the passage gives it in millimolar or molar. A magnesium concentration of the gel or running buffer is not this field.',
    'glycerol_percent': 'The concentration of glycerol in the binding buffer of the reaction, as a percent, when the passage gives it as a percent. A glycerol percent of the gel, the loading buffer or the storage buffer is not this field.',
    'nonspecific_competitor_amount': 'The amount of non-specific competitor nucleic acid (for example poly(dI-dC), salmon sperm DNA or tRNA) in the binding reaction, as the passage gives it in nanograms or micrograms. A concentration (for example per microlitre) and the amount of the unlabelled specific probe are not this field.',
    'specific_competitor_excess': 'The fold excess of the unlabelled specific probe (the same sequence as the labelled probe, the cold competitor) over the labelled probe that was used in the competition, as a number, when the passage gives it as a fold excess. When the passage gives several different excesses without saying which one is the result, leave it unavailable. An excess of a non-specific or mutant competitor is not this field.',
    'incubation_time': 'How long the protein was incubated with the probe in the binding reaction before the mixture was loaded on the gel. A time of the gel run, of a pre-run, of the labelling of the probe and of a pre-incubation of the protein with the competitor or an antibody alone is not this field, and neither is a time that is only a range of times tried.',
    'incubation_temperature': 'The temperature at which the protein was incubated with the probe in the binding reaction, as a number. A passage that says only room temperature, or on ice, does not state it, and the temperature of the gel run is not this field.',
    'gel_percent': 'The concentration of the native gel (the percent of polyacrylamide, or of agarose) on which the reactions were run, as a percent. A percent of a denaturing gel, of the stacking gel only or of the glycerol is not this field.',
    'run_time': 'How long the native gel was run, as the passage gives it as a time. A time of the pre-run of the gel, of the incubation and of the exposure or detection is not this field.',
    'run_voltage': 'The voltage at which the native gel was run, as the passage gives it in volts (V) or in volts per centimetre (V/cm). A current or a power is not offered here.',
    'run_temperature': 'The temperature at which the native gel was run (for example in the cold room), as a number. A passage that says only cold room, or on ice, does not state it, and the temperature of the binding reaction is not this field.',
    'titration_point_count': 'The number of protein concentrations of the titration (the lanes with increasing protein), as a whole number, when the passage gives it as a number.',
    'shifted_species_count': 'The number of different shifted bands (distinct protein-probe complexes) that the passage says were seen, as a whole number, when the passage gives it as a number or as a number word (for example two shifted complexes). A passage that says only that a shifted band was seen does not state a number.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days or preparations), as a whole number. Lanes of one gel are not this field.',
    PROBE_TYPE: 'What the probe is, as the passage states it: double-stranded DNA, single-stranded DNA, RNA, or another nucleic acid. The words must say that the probe is double-stranded, single-stranded or RNA: a name such as fragment, PCR product, oligonucleotide or promoter region does not state it, and the passage is not to be read with knowledge of what such a thing usually is. A passage that describes several kinds of probe without saying which one the reported result comes from does not state it: leave it unavailable.',
    PROBE_LABEL: 'How the probe was labelled, as the passage states it: with phosphorus-32 (32P, radioactive), with a fluorophore, with biotin and detected by chemiluminescence, with an infrared dye, or another way. A label of the protein or of an antibody is not the label of the probe.',
    GEL_TYPE: 'The kind of native gel on which the reactions were run, as the passage states it: a native polyacrylamide gel, an agarose gel, or another gel. A denaturing (SDS) gel is not a native gel.',
    COMPETITOR_TYPE: 'The carrier nucleic acid that is added to the binding reaction to absorb non-specific binding, as the passage names it: poly(dI-dC), salmon sperm DNA, tRNA, or another one. An unrelated unlabelled fragment used as a competitor in a competition control (to test whether the shift is specific) is not this carrier, and neither is the unlabelled specific probe.',
    SPREAD_KIND: 'What the uncertainty given in the kd_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    FIT_MODEL: 'The model the shifted fraction against the protein concentration was fitted with, as the passage names it: a one-site binding model (hyperbola), a Hill model (a free Hill slope), a quadratic model for tight binding, a two-site model, or another one. A passage that does not name the model does not state it.',
    'shift_detected': 'Whether the passage says that a shifted band (a complex that migrates more slowly than the free probe) was seen with the protein and the probe (yes), or says that no shift was seen (no). A shift seen only with another protein or another probe is not this fact.',
    'shift_abolished_by_specific_competitor': 'Whether the passage says that an excess of the unlabelled specific probe (the cold competitor of the same sequence) abolished or reduced the shifted band (yes), or says that it did not (no).',
    'shift_not_abolished_by_nonspecific_competitor': 'Whether the passage says that an excess of a non-specific or unrelated unlabelled nucleic acid (a competitor of another sequence) did not abolish the shifted band (yes), or says that it did abolish or reduce it (no).',
    'mutant_probe_does_not_shift': 'Whether the passage says that a probe whose binding site is mutated (or a scrambled probe) did not give the shift (yes), or says that it did shift (no).',
    'probe_alone_lane_shown': 'Whether the passage says that a lane with the labelled probe alone (without protein) was run beside the reactions (yes), or says that none was (no).',
    'nonspecific_protein_control_done': 'Whether the passage says that a control with a non-specific protein (for example bovine serum albumin, or the tag alone) did not shift the probe (yes), or says that it did (no).',
    'free_probe_quantified': 'Whether the passage says that the free and the shifted probe were quantified (for example by densitometry or by phosphorimager) to give the fraction of the probe shifted (yes), or says that they were not (no).',
    'probe_at_or_below_kd': 'Whether the passage says that the probe concentration was at or below the KD (so that the titration is not stoichiometric) (yes), or says that it was above the KD (no). A probe concentration with no statement about the KD is not this fact.',
    'equilibrium_reached': 'Whether the passage says that the binding had reached equilibrium before the gel was loaded (for example shown by a time course) (yes), or says that it had not (no).',
    'supershift_confirms_protein_identity': 'Whether the passage says that an antibody against the protein gave a supershift (a further retarded band) or removed the shifted band, so that the protein in the complex is confirmed (yes), or says that the antibody did not (no).',
    'protein_purified': 'Whether the passage says that the protein used was purified (for example recombinant protein purified from bacteria or insect cells) (yes), or says that it was in a crude extract, a lysate or an in vitro translation mixture (no).',
    'complex_survives_gel_run': 'Whether the passage says that the complex was stable during the gel run, with no smear between the shifted band and the free probe (yes), or says that it dissociated during the run or gave a smear (no).',
    'protein_range_brackets_kd': 'Whether the passage says that the protein concentrations of the titration spanned the KD, from well below it to a saturating concentration (yes), or says that they did not (no).',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days or preparations), rather than lanes of one gel (yes), or says that they were not (no).',
    'single_estimate_method': 'Whether the passage says that the KD was determined by this gel shift method only (yes), or says that it was also determined by another method (no).',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (probe type, label, gel type, competitor type, spread kind, fit model), the facts."""
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
    """The record of ``literature_emsa_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
