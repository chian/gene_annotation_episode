"""The extraction of ONE isotope-label flow experiment (type 'coupling_isotope_label') from one chunk of text, derived from the grader's input form
(``literature_coupling_isotope_label_record.py``).

The extraction and the grader are linked: the grader's input form IS the extraction's answer form. Nothing here is a second schema kept in
step by hand. The three things this module offers are all derived from the form's own declarations (its quantities, units, facts and
vocabularies):

``answer_schema()``     the JSON schema the extractor's model answers with. One entry per field the form names. Every field may be answered
                        'unavailable' with a reason (a field the passage does not state is never guessed and never 0). A field that is stated
                        carries its value and the quote that states it. The model gives only the quote; code finds where it sits.
``validate_answer()``   checks an answer against that schema and checks that every quote occurs in the chunk exactly once (a quote that
                        occurs more than once must be made longer so it points to one place).
``quote_span()``        the byte span (UTF-8 bytes from the start of the chunk) of a quote that occurs once.
``record_from_answer()``turns a valid answer into the record the grader takes (``literature_coupling_isotope_label_record``), with the operand
                        constructors of that form. The quoted spans become the record's ``spans`` and are cited by each value's ``source_refs``.

Support: every stated field also carries ``support`` ('direct', 'implied' or 'about_something_else': how well its quote supports it), chosen by
the model and validated here; an unavailable field carries None. The record keeps it per stated value (``choice_support`` for each plain choice
field); the converter judges it.

Fields of the form the extraction does not answer (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the four preparation references (``preparations``) are references to records, which no passage
states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_coupling_isotope_label_record import (
    CHOICES, FACTS, PREPARATION_KEYS, QUANTITIES, SUPPORTS, UNITS, VERSION, fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a judgement of the grader's
# question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('replicate_count',)

MEANING = {
    'label_incorporation': 'The share of the product molecules (or of the labelled position of the product) that carry the label of the claimed source, as the passage states it: the percent incorporation, the percent enrichment of the product, or the labelled fraction of the product ion in the mass spectrum. In a percent or a fraction.',
    'label_incorporation_spread': 'The reported uncertainty of the label incorporation (the number after a plus-minus sign, or a standard error or deviation), in the unit of the label incorporation.',
    'label_retention': 'For an experiment with two labels (for example a 14C label in the substrate and a 3H label in the cofactor), the ratio of the two labels in the product as a share of their ratio in the starting mixture, as the passage states it (100 percent is full transfer of the second label). In a percent or a fraction.',
    'label_retention_spread': 'The reported uncertainty of the label retention, in the unit of the label retention.',
    'label_atoms_per_product': 'The number of label atoms in a labelled product molecule, as the passage states it (the mass shift of the product ion read in label atoms: one 18O atom, two 18O atoms). It is the count in a labelled molecule, not an average over labelled and unlabelled molecules.',
    'label_atoms_expected': 'The number of label atoms the passage\'s own reaction account says the claimed reaction puts into the product (for example one 18O atom for a monooxygenase, two for a dioxygenase).',
    'label_purity': 'The isotopic purity (atom percent enrichment) of the labelled source that was fed to the enzyme (for example 98 atom percent 18O2), in a percent or a fraction.',
    'label_in_control': 'The share of the product that carries the label in the control reaction without the enzyme or with an inactive enzyme, as the passage states it, in a percent or a fraction.',
    'replicate_count': 'The number of replicate experiments the passage reports (a whole number).',
    'spread_kind': 'What the reported spreads (the uncertainties of the label shares) are.',
    'label_source': 'Which source carried the label: oxygen_gas (18O2), water (H2 18O), carbon_13, nitrogen_15, or radiolabel (a radioactive label such as 14C or 3H).',
    'readout': 'How the label in the product was read: mass_spectrometry, scintillation_counting or nmr.',
    'unlabelled_control': 'Whether the passage says the reaction was also run with the unlabelled source (an unlabelled medium or substrate) and its product read the same way.',
    'back_exchange_control': 'Whether the passage says a control was done for exchange of the label that does not go through the claimed reaction (for example the product or the substrate incubated in the labelled water or gas without the reaction, or the product re-incubated after the reaction, so that label exchange into a carbonyl or hydroxyl is seen).',
    'label_position_determined': 'Whether the passage says the position of the label in the product was determined (for example by a fragment ion of tandem mass spectrometry or by NMR), so that the label is shown to sit where the claimed reaction puts it.',
    'no_enzyme_control': 'Whether the passage says a control without the enzyme was run with the labelled source and its product read for the label.',
    'inactive_enzyme_control': 'Whether the passage says a control with an inactive enzyme (heat-denatured, boiled or a catalytically dead mutant) was run with the labelled source and its product read for the label.',
    'product_identified_by_mass_shift': 'Whether the passage says the product was identified by its mass and the mass shift of the label, against an unlabelled product or standard (for example the expected shift of 2 Da for one 18O).',
    'natural_abundance_corrected': 'Whether the passage says the label share was corrected for the natural abundance of the heavy isotope (and for the impurity of the label).',
    'same_preparation': 'Whether the passage says the labelled and the unlabelled run used the same enzyme preparation.',
    'same_window': 'Whether the passage says the labelled and the unlabelled run were incubated and sampled over the same time (the same incubation time and the same stop and work-up).',
    'native_substrate': 'Whether the passage says the substrate is the native (natural, physiological) substrate of the enzyme, as opposed to a surrogate substrate.',
    'purified_enzyme': 'Whether the passage says the enzyme was purified (as opposed to a cell lysate or extract).',
    'independent_replicates': 'Whether the passage says the replicates were independent experiments (different days, preparations or reaction mixtures) rather than repeated reads of one mixture.',
    'label_detected_in_product': 'Whether the passage says the product carried the label of the claimed source above the paper\'s own control: yes when it states the label was found in the product, no only when it states that no label was found in the product above the control or detection limit.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the plain choices, the facts."""
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
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': _nullable({'enum': list(SUPPORTS)}), 'reason': _nullable({'enum': list(REASONS)})})
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
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
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
    """The record of ``literature_coupling_isotope_label_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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

    return {'version': VERSION, 'experiment_type': 'coupling_isotope_label', 'experiment_ref': experiment_ref, 'source_ref': source_ref,
            'assertion_ref': assertion_ref, 'preparations': dict.fromkeys(PREPARATION_KEYS),
            'quantities': {name: operand(name) for name in QUANTITIES},
            **{name: choice(name) for name in CHOICES},
            'choice_support': {name: answer[name]['support'] for name in CHOICES},
            'facts': {name: fact(answer[name]['value'], [refs[name]], answer[name]['support']) if answer[name]['status'] == 'stated' else fact('unknown')
                      for name in FACTS},
            'spans': spans}
