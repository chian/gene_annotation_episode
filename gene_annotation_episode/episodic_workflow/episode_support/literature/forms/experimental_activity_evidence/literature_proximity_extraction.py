"""The extraction of ONE proximity-labeling experiment (a bait is fused to a biotin ligase such as BioID or TurboID, or to the peroxidase APEX2, or the enzyme is used as split halves; the enzyme biotinylates proteins within about 10 to 20 nm in living cells; the biotinylated proteins are captured on streptavidin and identified by western blot or mass spectrometry, and a candidate partner is called proximal when it is enriched over a control: a free enzyme, an unrelated bait, or no biotin or no peroxide; qualitative or semi-quantitative, no binding constant, and proximity is not direct binding) from one
chunk of text, derived from the grader's input form (``literature_proximity_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused.

Differences from the other types that come from the form: a proximity-labeling experiment reports no binding constant, so there is no KD field; the result is the enrichment of the candidate over the control (a fold change and a false discovery rate), and the
enrichment itself is a fact (``candidate_enriched``). The reported numbers are the enrichment, its false discovery rate, the expression of the fusion relative to the endogenous bait, the labelling time, the biotin (or biotin-phenol) and the hydrogen peroxide concentration and the number of independent experiments; the enzyme, the fusion site, the cell system, the readout and the quantification are
choices; and the facts are the controls and checks of this method (a free-enzyme control, an unlabelled control, an unrelated or differently localised bait, biotinylation confirmed, capture on streptavidin, the expression level and the localisation of the fusion checked, an orthogonal validation, a statistical test, independent experiments). Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the bait, the candidate and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_proximity_record import (
    CELL_SYSTEMS, EXPERIMENT_TYPE, FACTS, FUSION_SITES, LIGASES, PREPARATION_KEYS, QUANTIFICATIONS, QUANTITIES, READOUTS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
LIGASE = 'ligase'
FUSION_SITE = 'fusion_site'
CELL_SYSTEM = 'cell_system'
READOUT = 'readout'
QUANTIFICATION = 'quantification'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)
CHOICES = {LIGASE: LIGASES, FUSION_SITE: FUSION_SITES, CELL_SYSTEM: CELL_SYSTEMS, READOUT: READOUTS, QUANTIFICATION: QUANTIFICATIONS}

MEANING = {
    'enrichment_fold': 'The enrichment of the candidate partner (the protein whose proximity to the bait is tested) in the proximity-labeling sample over the control, as the passage gives it for that candidate as one number: a fold change or a ratio of abundance or of spectral counts (unit ratio), or its base-2 logarithm (unit log2_ratio). A value for several candidates, for the bait itself or for a different comparison, a threshold or cut-off that the passage only applies (for example fold change above 2 as a criterion), a range, and a percent are not this field. Without a statement of which candidate the number is for, leave it unavailable.',
    'enrichment_fdr': 'The false discovery rate, q-value or adjusted p-value that the passage reports for the enrichment of the candidate, as one number (unit percent, or fraction when given as a fraction such as 0.01). A threshold that the passage only applies (for example FDR below 10 percent as a criterion), an unadjusted p-value, a SAINT probability and a score of another protein are not this field.',
    'bait_expression_ratio': 'The expression level of the enzyme-bait fusion relative to the endogenous bait protein, as one ratio the passage states (for example the fusion at about twice the endogenous level, ratio 2). A statement that the expression was similar, comparable or lower without a number does not state it, and neither does the expression of the fusion relative to the free enzyme.',
    'labeling_time': 'How long the labelling reaction lasted, as the passage gives it for the experiment, in minutes or hours: for a ligase the time the cells were incubated with biotin, for a peroxidase the time the labelling lasted after the hydrogen peroxide was added (the pulse), not the earlier incubation with biotin-phenol. When several times are given without saying which one is the result, leave it unavailable. A time of lysis, of washing, of capture or of any other step is not this field.',
    'biotin_concentration': 'The concentration of biotin (for a ligase) or of biotin-phenol (for a peroxidase) added to the cells for the labelling, in micromolar or millimolar. A concentration of streptavidin, of any other reagent and a mass per volume are not this field (a unit not offered: unavailable with the reason unit_not_in_vocabulary).',
    'peroxide_concentration': 'The concentration of hydrogen peroxide used for the labelling pulse of a peroxidase (APEX or APEX2), in micromolar or millimolar. Not this field: a concentration of any other reagent, a quencher, and a percent (unit not offered: unavailable with the reason unit_not_in_vocabulary).',
    'replicate_count': 'The number of independent experiments (biological replicates, separate cultures or separate days) the passage reports for the labelling experiment, as a whole number. Lanes, technical injections and the number of proteins are not this field.',
    LIGASE: 'The labelling enzyme the passage says was fused to the bait: BioID (the BirA* mutant), BioID2, TurboID, miniTurbo, APEX, APEX2, or a split version of one of them (split-BioID, split-TurboID, split-APEX2; the enzyme as two halves each fused to one partner). Another enzyme: other. A passage that does not name the enzyme does not state it.',
    FUSION_SITE: 'Where the passage says the enzyme is fused to the bait: at the N terminus of the bait, at its C terminus, or inside it. A passage that does not say does not state it.',
    CELL_SYSTEM: 'The kind of living system in which the labelling was done as the passage states it: mammalian cells, yeast, bacteria, plant, parasite, a whole animal or tissue, or another. A passage that does not name it does not state it.',
    READOUT: 'How the biotinylated proteins were identified: by western blot (a named protein probed), by mass spectrometry, or by both. A streptavidin blot or imaging that only shows that biotinylation took place, without identifying proteins, is not this field.',
    QUANTIFICATION: 'How the enrichment was quantified, as the passage states it: spectral counts, label-free intensity (LFQ), SILAC, TMT or another isobaric label, densitometry of a blot, or another. A program name alone (for example SAINT or MaxQuant) does not state it unless the passage also names the kind of quantity.',
    'candidate_enriched': 'Whether the passage says that the candidate partner was enriched (significantly or clearly) in the proximity-labeling sample over the control, that is, found in proximity to the bait (yes), or says that it was not enriched or not found proximal (no). A candidate that was only detected, or only known from earlier work or from another method, and a protein that the passage lists as an expected hit without saying that it was enriched here, are not this fact.',
    'ligase_only_control': 'Whether the passage says that the enzyme without the bait (the free ligase or peroxidase, or the enzyme with only a tag or a signal sequence) was run in parallel as a control (yes), or says that no such control was run (no).',
    'unlabeled_control': 'Whether the passage says that a control without labelling was run: cells with the bait fusion but without biotin, or without biotin-phenol or without hydrogen peroxide (yes), or says that none was run (no). A negative control that is the free enzyme with biotin is not this fact.',
    'unrelated_bait_control': 'Whether the passage says that the enzyme fused to an unrelated protein, or to a protein or signal that sends it to a different compartment, was run as a control (yes), or says that no such control was run (no). The free enzyme alone is not this fact.',
    'biotinylation_confirmed': 'Whether the passage says that biotinylation was shown to depend on the fusion and on the labelling (for example a streptavidin blot or streptavidin fluorescence that shows biotinylated proteins only with biotin, or only with biotin and peroxide) (yes), or says that it did not (no).',
    'streptavidin_capture': 'Whether the passage says that the biotinylated proteins were captured or purified on streptavidin or neutravidin beads before identification (yes), or says that they were not (no).',
    'bait_expression_checked': 'Whether the passage says that the expression level of the fusion was checked against the endogenous bait or against the control constructs (for example by an immunoblot) (yes), or says that it was not (no).',
    'bait_localization_checked': 'Whether the passage says that the fusion was shown to localise like the endogenous bait or in the expected compartment (for example by immunofluorescence) (yes), or says that it did not (no).',
    'orthogonal_validation': 'Whether the passage says that the proximity of the candidate to the bait was confirmed by an independent method (co-immunoprecipitation, colocalisation, a binding assay) (yes), or says that the independent method did not confirm it (no). A confirmation of the biotinylation itself is not this fact.',
    'statistical_test_used': 'Whether the passage says that the enrichment was assessed with a statistical test or model (SAINT, a t-test, a moderated test, a false discovery rate) (yes), or says that no statistical test was applied (no).',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate cultures, days or preparations) rather than injections or lanes of one sample (yes), or says that they were not (no).',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (enzyme, fusion site, cell system, readout, quantification), the facts."""
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
    """The record of ``literature_proximity_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
