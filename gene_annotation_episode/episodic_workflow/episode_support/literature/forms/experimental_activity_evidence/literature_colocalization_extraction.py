"""The extraction of ONE microscopy co-localization / recruitment experiment (fluorescence microscopy shows that one labelled protein is found where the other is: two labelled proteins co-localize in cells, one is recruited to the site that the other makes, in a native or a heterologous host or as purified proteins in droplets, on beads or on a membrane, and the localization is lost when the partner is absent or its binding region is removed; qualitative nearness evidence, no binding constant) from one
chunk of text, derived from the grader's input form (``literature_colocalization_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis, AUC and PLA extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a co-localization reports no binding constant, so there is no KD field; its numbers are the number of cells, foci or droplets scored, the percent of them that showed the co-localization (0 to 100, and 0 is allowed), the Pearson coefficient of the two channels (from -1 to 1), the enrichment (above 0) and the number of independent experiments; the imaging mode is a choice and the system is two yes/no facts (a heterologous host, purified proteins); and the facts are the controls and the results of this method (a co-localization or recruitment, an unrelated protein or the tag alone that is not recruited, the loss without the partner, the loss when the binding region is removed, the following of the partner when it is moved, near-native expression, a functional fusion, a quantification over many objects, independent experiments). The percent and the Pearson coefficient have their own ranges, every other number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the two proteins and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_colocalization_record import (
    EXPERIMENT_TYPE, FACTS, IMAGING_MODES, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
IMAGING_MODE = 'imaging_mode'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('objects_counted', 'replicate_count')
RANGES = {'fraction_colocalized': (0, 100), 'pearson_coefficient': (-1, 1)}   # the closed range of a quantity that has one; every other number must be above 0
CHOICES = {IMAGING_MODE: IMAGING_MODES}

MEANING = {
    'objects_counted': 'The number of cells, foci or droplets that were scored for the co-localization or the recruitment of the test condition of the experiment described in the passage (the number analysed, scored, quantified or counted, in total or per condition), as the passage gives it as a whole number. The number of images, fields, experiments, embryos, animals and wells is not this field. A number of cells given only for another experiment of the passage is not this field.',
    'fraction_colocalized': 'The percent of the scored cells, foci or droplets that showed the co-localization or the recruitment of the test condition, as the passage gives it as a percent (for example 85 percent of cells showed polar foci gives 85; 0 when the passage says that none did). A fraction written as a proportion of 1 is not converted: leave it unavailable with the reason unit_not_in_vocabulary. A percent of a control, of a mutant or of a deletion strain is not this field. A percent of protein, of intensity or of area is not this field.',
    'pearson_coefficient': 'The Pearson correlation coefficient (also Pearson r, PCC or Pearson correlation) of the two fluorescence channels that the passage gives for the test condition, as one number from -1 to 1. The Manders coefficients (M1, M2), the overlap coefficient and the intensity correlation quotient are not this field. A coefficient of a control, of a mutant or of a deletion strain is not this field.',
    'enrichment_ratio': 'The enrichment that the passage gives for the test condition: the fluorescence at the site of the partner (the focus, the pole, the condensate or droplet, the bead or the membrane) over the fluorescence elsewhere (the cytoplasm, the dilute phase or the background), also called a partition coefficient or a recruitment ratio, as one number above 0 (a ratio, not a percent). A percent, a difference of intensities and an enrichment of a control or a mutant are not this field.',
    'replicate_count': 'The number of independent experiments the passage reports for the co-localization or the recruitment (separate experiments on separate days, with separate cultures or preparations, or independent biological replicates), as a whole number. Cells, foci, droplets and images of one experiment are not this field.',
    IMAGING_MODE: 'The imaging mode that the passage names for the images that give the result: widefield (epifluorescence), confocal (laser scanning or spinning disk), tirf (total internal reflection fluorescence) or super_resolution (STORM, PALM, STED, SIM or another named super-resolution method). A passage that does not name the mode does not state it.',
    'colocalization_observed': 'Whether the passage says that one labelled protein was found where the other is, that is, that the two co-localized, or that one was recruited to the site (a focus, a pole, a membrane, a condensate, a droplet, a bead) that the other makes (yes), or says that it was not (it stayed diffuse, was not recruited, did not co-localize) (no). A localization of one protein with no statement about the partner, and a signal that the passage reports only for another method (for example a pull-down or a FRET measurement), are not this fact.',
    'unrelated_protein_not_recruited': 'Whether the passage says that a protein that is not expected to bind the partner (or the fluorescent tag alone) was not recruited and did not co-localize under the same conditions (yes), or says that it was (no). A control with the partner absent is not this fact (it is the lost_without_partner fact).',
    'lost_without_partner': 'Whether the passage says that the protein was no longer localized there (it was diffuse or spread) when the partner was absent (a deletion strain, cells that do not express it, droplets or beads that lack it, a depletion) (yes), or says that it stayed localized without the partner (no). A mutant that lacks only a region of the partner is not this fact (it is the lost_with_binding_region_removed fact).',
    'lost_with_binding_region_removed': 'Whether the passage says that a mutant or a truncation of either protein that lacks the proposed binding region no longer co-localized with the partner or was no longer recruited (yes), or says that it still did (no). A deletion of the whole partner is not this fact (it is the lost_without_partner fact).',
    'follows_partner_when_moved': 'Whether the passage says that, when the partner was put somewhere else (it was mislocalized, relocalized or made to form a new focus), the protein followed it to the new place (yes), or says that it did not follow (no). A protein that is only found at its usual place is not this fact.',
    'heterologous_host': 'Whether the passage says that the co-localization or the recruitment was shown in a host that has neither of the two proteins of its own, for example the two proteins expressed together in Escherichia coli or in yeast although they come from another organism (yes), or says that it was shown in the organism or the cell type in which the two proteins naturally occur (no). A passage that does not say in what cells the experiment was done does not state this.',
    'purified_proteins': 'Whether the passage says that the co-localization or the recruitment was shown with purified proteins outside cells: in solution, in droplets or condensates, on beads or on a membrane (yes), or says that it was shown in cells (no). A passage that does not say whether the proteins were purified or in cells does not state this.',
    'expressed_near_native_level': 'Whether the passage says that the labelled proteins were expressed from their native locus or promoter, or at a level shown to be near the native level, rather than overexpressed (yes), or says that they were overexpressed (no). A passage that only names a plasmid or an inducer does not state it. Purified proteins have no expression level: a statement about them is not this fact.',
    'fusion_functional': 'Whether the passage says that the tagged protein was shown to be functional (for example it complements the deletion strain) or that the tag was shown not to change the localization (yes), or says that the tag changed the localization or the function (no). A passage that only names the tag or the fluorophore does not state it.',
    'quantified_over_many_cells': 'Whether the passage says that the result was quantified over a stated population of cells, foci or droplets (a fraction, a mean, a coefficient with the number scored) (yes), or says that it is one representative image without a quantification (no). A passage that only shows or names an image does not state it.',
    'independent_experiments': 'Whether the passage says the repeats of the experiment were independent experiments (separate experiments, days or cultures) rather than cells or images of one sample (yes), or says that they were not (no).',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (imaging mode), the facts."""
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
    occurs exactly once in ``chunk``; a percent is from 0 to 100, a Pearson coefficient from -1 to 1 and any other number is above 0, and a stated value carries its unit
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
        if name in RANGES and not RANGES[name][0] <= item['value'] <= RANGES[name][1]:
            _refuse(name, 'number_must_be_in_its_range', RANGES[name])
        if name in QUANTITIES and name not in RANGES and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The record of ``literature_colocalization_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
