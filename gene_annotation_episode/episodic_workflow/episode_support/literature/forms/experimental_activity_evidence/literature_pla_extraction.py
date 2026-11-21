"""The extraction of ONE proximity ligation assay (PLA: in situ PLA, Duolink) experiment (two proteins are probed in fixed cells or tissue with two primary antibodies from different species and oligonucleotide-linked secondary antibodies; where the two proteins are within about 40 nm the oligonucleotides are ligated, amplified by rolling-circle amplification and detected as one fluorescent punctum; the puncta are counted per cell; qualitative proximity evidence, no binding constant) from one
chunk of text, derived from the grader's input form (``literature_pla_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a PLA reports no binding constant, so there is no KD field; its numbers are the mean puncta per cell of the test, of the negative control (a single primary antibody or no primary antibody) and after a knockdown, a knockout or a competition of one protein (a count of puncta may be 0), the number of cells counted, the amplification time and the number of independent experiments; the cell system, the fixation and the image analysis software are choices; and the facts are the controls and the results of this method (a proximity signal, primary antibodies from different species, validated antibodies, negative single-antibody and no-primary controls, a specificity control that lowers the signal, a positive control pair, puncta in the compartment expected for both proteins, a blind quantification, a statistical test, independent experiments). A number of puncta is 0 or more, every other number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the two proteins and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pla_record import (
    CELL_SYSTEMS, EXPERIMENT_TYPE, FACTS, FIXATIONS, PREPARATION_KEYS, QUANTITIES, SOFTWARES, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
CELL_SYSTEM = 'cell_system'
FIXATION = 'fixation'
QUANTIFICATION_SOFTWARE = 'quantification_software'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('cells_counted', 'replicate_count')
PUNCTA = ('puncta_per_cell_target', 'puncta_per_cell_control', 'puncta_per_cell_knockdown')   # a count of puncta may be 0
CHOICES = {CELL_SYSTEM: CELL_SYSTEMS, FIXATION: FIXATIONS, QUANTIFICATION_SOFTWARE: SOFTWARES}

MEANING = {
    'puncta_per_cell_target': 'The mean number of PLA puncta (fluorescent dots) per cell in the test condition of the PLA experiment described in the passage (both primary antibodies against the two proteins, cells or tissue that carry both), as the passage gives it as one number of puncta per cell (an average, a mean or a median). A number of puncta per field, per nucleus area, per image or per 100 cells is not this field (leave it unavailable with the reason unit_not_in_vocabulary and do not convert it). A percent of cells with a signal, a fold increase and an intensity are not this field. A mean in a control, in a knockdown or in a mutant condition is not this field.',
    'puncta_per_cell_control': 'The mean number of PLA puncta per cell in the negative control that the passage describes (one single primary antibody, or no primary antibody, with the PLA probes), as the passage gives it as one number of puncta per cell; 0 when the passage states a number of 0 puncta per cell. A statement that the control showed no signal or few puncta, without a number, is not a number: leave it unavailable. The puncta per cell of a knockdown, a knockout, a competition or a cell without one protein are not this field. When the passage gives several different controls with different numbers without saying which one is the negative control of the test, leave it unavailable.',
    'puncta_per_cell_knockdown': 'The mean number of PLA puncta per cell with both primary antibodies after the knockdown, the knockout or the competing peptide that removes or blocks one of the two proteins (a specificity control of the same PLA), as the passage gives it as one number of puncta per cell. The puncta per cell of a single-antibody or a no-primary control are not this field.',
    'cells_counted': 'The number of cells in which the PLA puncta of the test condition were counted, as the passage gives it as a whole number (the number of cells analysed, quantified or scored, in total or per condition). The number of images, fields, experiments, patients, animals and wells is not this field.',
    'amplification_time': 'The time of the rolling-circle amplification of the PLA, as the passage gives it in minutes (for example 100 min); a time in hours is not offered: leave it unavailable with the reason unit_not_in_vocabulary. The time of the ligation, of the antibody incubation and of any other step is not this field.',
    'replicate_count': 'The number of independent experiments the passage reports for the PLA (separate experiments on separate days or with separate cultures, or independent biological replicates), as a whole number. Cells, fields and images of one experiment are not this field.',
    CELL_SYSTEM: 'What the PLA was done on, as the passage states it: cultured cells (a cell line or a culture on coverslips), primary cells isolated from an animal or a person, or a tissue section. A passage that does not name the cells or the tissue does not state it.',
    FIXATION: 'How the cells or the tissue were fixed for the PLA, as the passage states it: paraformaldehyde (or formaldehyde), methanol (or ice-cold methanol), or formalin fixation with paraffin embedding. Another fixative is not offered: leave it unavailable. A passage that does not say how the sample was fixed does not state it.',
    QUANTIFICATION_SOFTWARE: 'The software that the passage says was used to count the PLA puncta or to analyse their images: ImageJ (or Fiji), CellProfiler, BlobFinder, or another named program. A microscope control program that only acquired the images is not this field.',
    'proximity_signal_detected': 'Whether the passage says that the PLA gave a signal for the two proteins together, that is, puncta that show the two proteins within about 40 nm of each other (yes), or says that no such signal was found (no). A signal that the passage reports only for another method (for example co-immunoprecipitation or immunofluorescence co-localisation), and a signal only in a control, are not this fact.',
    'primary_antibodies_different_species': 'Whether the passage says that the two primary antibodies of the PLA were raised in different species (for example one mouse and one rabbit antibody), as it names the species (yes), or says that they were from the same species (no). Naming only one antibody does not state it.',
    'antibodies_validated': 'Whether the passage says that the primary antibodies were validated for the use in the PLA or in immunofluorescence (for example by knockout or knockdown cells, by a peptide block, or by a published validation) (yes), or says that they were not (no). The name of an antibody and the catalogue number of a vendor do not state it.',
    'single_antibody_controls_negative': 'Whether the passage says that the PLA with only one of the two primary antibodies gave no or few puncta (yes), or says that it gave a signal (no). A control with no primary antibody at all is not this fact (it is the no_primary_control_negative fact).',
    'no_primary_control_negative': 'Whether the passage says that the PLA with no primary antibody (only the PLA probes) gave no or few puncta (yes), or says that it gave a signal (no). A control with one primary antibody is not this fact.',
    'specificity_control_reduces_signal': 'Whether the passage says that the PLA signal fell when one of the two proteins was knocked down, knocked out or competed away (siRNA, shRNA, CRISPR knockout cells, a blocking peptide) (yes), or says that it did not fall (no). A control that does not remove a protein is not this fact.',
    'positive_control_pair_done': 'Whether the passage says that a pair of proteins known to interact (a positive control pair) was run in the same PLA and gave a signal (yes), or says that it did not (no).',
    'puncta_in_expected_compartment': 'Whether the passage says that the puncta lay in the cell compartment where both proteins are present or expected to meet (for example the nucleus, the plasma membrane, the cytoplasm, a named organelle) (yes), or says that the puncta lay where the proteins are not expected to meet (no). A passage that gives a localisation of the puncta with no statement of what is expected does not state it.',
    'quantification_blinded': 'Whether the passage says that the PLA puncta were counted blind to the condition, or by a fully automatic image analysis that did not depend on the person (yes), or says that they were counted unblinded (no). A passage that only names a counting program does not state it.',
    'statistical_test_done': 'Whether the passage says that the PLA puncta of the test and of the control were compared by a named statistical test (for example a t-test, a Mann-Whitney test, an ANOVA) (yes), or says that no test was done (no). A p-value or a star in a figure without a named test, and a mean with an error bar, do not state it.',
    'independent_experiments': 'Whether the passage says the repeats of the PLA were independent experiments (separate experiments, days or cultures) rather than cells or images of one sample (yes), or says that they were not (no).',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (cell system, fixation, quantification software), the facts."""
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
    occurs exactly once in ``chunk``; a number of puncta is 0 or more and any other number is above 0, and a stated value carries its unit
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
        if name in PUNCTA and item['value'] < 0:
            _refuse(name, 'number_must_not_be_negative')
        if name in QUANTITIES and name not in PUNCTA and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_pla_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
    in its source: each quote's span is found in the chunk and recorded at its offset in the source. A value not stated is an
    'unavailable' operand with its reason, never invented; a fact not stated is 'unknown'."""
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
