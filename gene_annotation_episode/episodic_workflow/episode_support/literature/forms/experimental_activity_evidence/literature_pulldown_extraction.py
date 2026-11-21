"""The extraction of ONE pull-down or co-immunoprecipitation (co-IP) experiment (a tagged or antibody-captured bait on beads, wash, elution, detection of the prey by western blot or mass spectrometry; qualitative to semi-quantitative) from one
chunk of text, derived from the grader's input form (``literature_pulldown_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand and SPA extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a pull-down reports no binding constant, so there is no KD, Ki or IC50 field. The reported numbers are
semi-quantitative (the fold enrichment over the control, the percent of the input recovered, the input fraction), the wash (sodium chloride, detergent, number of
washes), the incubation and the number of independent experiments; the detection method, the way the bait is captured, the source of the prey, the nuclease
treatment and the crosslinker are choices; and the facts are the controls and the results of this method (the prey in the eluate, the bead-only or tag-only control
and the prey absent from it, the control without the bait, the input lane, the reciprocal pull-down, competition, survival of a nuclease treatment, a direct
interaction of purified proteins, endogenous expression levels, quantification with normalization, validation of the antibody or tag, independent experiments).
Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``, ``assertion_ref``) are given by
the caller, and the bait and the prey and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import (
    CAPTURE_FORMATS, CROSSLINKERS, DETECTION_METHODS, EXPERIMENT_TYPE, FACTS, NUCLEASE_TREATMENTS, PREPARATION_KEYS, PROTEIN_SOURCES, QUANTITIES, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
DETECTION = 'detection_method'
CAPTURE = 'capture_format'
SOURCE = 'protein_source'
NUCLEASE = 'nuclease_treatment'
CROSSLINKER = 'crosslinker'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('wash_count', 'replicate_count')
CHOICES = {DETECTION: DETECTION_METHODS, CAPTURE: CAPTURE_FORMATS, SOURCE: PROTEIN_SOURCES, NUCLEASE: NUCLEASE_TREATMENTS, CROSSLINKER: CROSSLINKERS}

MEANING = {
    'fold_enrichment': 'How many times stronger the prey signal (band intensity) was in the specific capture than in the control capture (for example the bead-only, tag-only or isotype antibody control), as a number, when the passage gives it as a fold, a ratio or a relative intensity against that control. A percent of the input, an intensity with no control to compare with, and a number you would have to calculate are not this field.',
    'percent_input_recovered': 'The prey in the eluate as a percent of the input (the starting material), when the passage gives it as a percent of the input. A fold enrichment, a percent of the bait and a percent you would have to calculate are not this field.',
    'input_fraction': 'The part of the starting material (lysate or protein applied to the beads) that was loaded as the input lane, as a percent, when the passage gives it as a percent or a fraction of the material applied. A percent of the input that was recovered is not this field.',
    'nacl_wash': 'The concentration of sodium chloride in the wash buffer of the beads, as the passage gives it in millimolar or molar. A salt concentration of the lysis buffer, of the binding buffer or of the elution buffer is not this field unless the passage says the beads were washed with it.',
    'detergent_wash': 'The concentration of detergent (for example Triton X-100, NP-40, Tween-20, DDM or SDS) in the wash buffer of the beads, as a percent, when the passage gives it as a percent. A detergent of the lysis buffer alone, of the elution buffer or of the sample buffer is not this field unless the passage says the beads were washed with it. When the passage gives several different detergent percents for different washes without saying which one is the result, leave it unavailable.',
    'wash_count': 'The number of times the beads were washed after the capture, as a whole number, when the passage gives it as a number or as a number word. A wash that the passage calls only extensive or thorough does not state a number.',
    'incubation_time': 'How long the bait was incubated with the prey (the lysate or the protein solution) before the beads were washed. A time of the lysis, of the bead coupling or capture of the bait alone, of the elution or of the detection, and a time that is only a range of times tried, are not this field.',
    'incubation_temperature': 'The temperature at which the bait was incubated with the prey, as a number. A passage that says only room temperature, or on ice, does not state it.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days, preparations or cell cultures), as a whole number. Lanes or wells of one experiment are not this field.',
    DETECTION: 'How the prey was detected in the eluate, as the passage states it: by western blot (immunoblot), by mass spectrometry, by fluorescence, by autoradiography or another way. How the bait was captured or how the protein was stained for loading (for example Coomassie) is not the detection of the prey.',
    CAPTURE: 'How the bait was held on the beads, as the passage states it: through a GST, His, Strep, FLAG, HA or Myc tag, by an antibody against the bait (a co-immunoprecipitation, usually on protein A or protein G beads), through biotin on streptavidin beads, or another way. A passage that names several different capture formats without saying which one the reported result comes from does not state it: leave it unavailable.',
    SOURCE: 'What the prey (the protein looked for in the eluate) came from, as the passage states it: purified recombinant protein, a cell lysate (or a nuclear or cell extract), a tissue lysate, or another source.',
    NUCLEASE: 'The nuclease the lysate or the binding reaction was treated with, as the passage names it: benzonase, RNase, DNase, both RNase and DNase, or another one. A treatment the passage describes only as removal of nucleic acid without naming the enzyme does not state it. Ethidium bromide is not a nuclease.',
    CROSSLINKER: 'The crosslinker used on the cells or the proteins before the capture, as the passage names it: formaldehyde, DSP (dithiobis(succinimidyl propionate)) or another one; answer none only when the passage says that no crosslinking was used.',
    'prey_detected_in_eluate': 'Whether the passage says that the prey was detected in the eluate of the specific capture (the bait was pulled down together with the prey, or the antibody against the bait co-precipitated the prey) (yes), or says that it was not detected there (no). A statement that the prey was detected only in the input, in the flow-through or in a control is not this fact.',
    'negative_control_done': 'Whether the passage says that a negative-control capture was done with beads and a control that has no bait (beads alone, a tag alone such as GST alone, an empty vector, or a non-specific isotype or normal IgG antibody) (yes), or says that it was not (no).',
    'prey_absent_in_negative_control': 'Whether the passage says that the prey was absent from, or not pulled down by, the negative-control capture (bead-only, tag-only or isotype IgG) (yes), or says that the prey was also found there (no).',
    'bait_minus_control_done': 'Whether the passage says that the prey was incubated with the beads without the bait to show that the prey does not bind the beads alone, and that it did not (yes), or says that the prey bound the beads without the bait (no). A control capture with an irrelevant tag or antibody is not this control.',
    'input_lane_shown': 'Whether the passage says that an input lane (a sample of the starting material) was shown beside the eluate (yes), or says that none was (no).',
    'reciprocal_done': 'Whether the passage says that the pull-down or co-immunoprecipitation was also done the other way round, with the former prey as the bait, and that it found the interaction (yes), or says that the reciprocal experiment did not find it (no).',
    'competition_disrupts_interaction': 'Whether the passage says that competition with untagged protein, or a mutant, a deletion or a peptide that disrupts the interaction, abolished or reduced the capture of the prey (yes), or says that it did not (no).',
    'interaction_survives_nuclease': 'Whether the passage says that the interaction was still seen after a nuclease treatment (benzonase, RNase or DNase) or in the presence of ethidium bromide, so that it is not bridged by nucleic acid (yes), or says that the interaction was lost after that treatment (no).',
    'direct_interaction_shown': 'Whether the passage says that the interaction was shown with purified proteins only (for example purified recombinant bait and prey), so that it is direct (yes), or says that the interaction is not direct or needs another factor (no). A pull-down from a lysate or extract, or a co-immunoprecipitation, does not state this: leave it unavailable.',
    'endogenous_expression_levels': 'Whether the passage says that the interacting proteins were at their endogenous levels (not overexpressed, not tagged and expressed from a plasmid) (yes), or says that one or both were overexpressed or ectopically expressed (no).',
    'quantification_with_normalization': 'Whether the passage says that the band intensities were quantified and normalized (for example to the input, to the bait or to a loading control) (yes), or says that they were not (no).',
    'specificity_validated': 'Whether the passage says that the specificity of the antibody or tag used to capture or detect was validated, for example with a knockout or knockdown control or with a blocking peptide (yes), or says that it was not (no).',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days, preparations or cell cultures), including repeated blots, rather than lanes or wells of one experiment.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (detection method, capture format, protein source, nuclease treatment, crosslinker), the facts."""
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
    """The record of ``literature_pulldown_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
