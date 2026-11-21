"""The extraction of ONE split-reporter (protein-fragment complementation: split luciferase such as NanoBiT, split GFP or BiFC, split beta-lactamase, split TEV) experiment (two fragments of a reporter are fused to the two candidate partners; when the partners come together the reporter is reconstituted and its signal reports proximity or interaction in cells, in a lysate or with purified proteins; a titration or a kinetic time course of a reversible reporter such as NanoBiT can give an apparent KD) from one
chunk of text, derived from the grader's input form (``literature_split_reporter_record.py``).

Same design as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis and AUC extractions and private to this method: the grader's input form IS
the extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``, ``validate_answer()``,
``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations (its quantities, units, facts and
vocabularies). The model gives only the quote of each stated field; code finds the UTF-8 byte span, and a quote that does not
occur in the chunk exactly once is refused. A stated field carries a support (direct, implied, about_something_else); an unavailable one carries none; the choice fields are the plain choices of the record and carry a support as well (``choice_support``).

Differences from the other types that come from the form: a split reporter is mostly qualitative (a signal above the controls), so the apparent KD and its spread are fields that are mostly
unavailable. The reported numbers are the signal over the background and over the negative control, the number of fusion orientations tested, the lowest and the highest concentration of the titrated partner and their number, and the number of independent
experiments; the reporter system, the assay system, the readout mode and the spread kind are choices; and the facts are the result and the controls of this method (a reconstituted signal, each fragment alone at background, a
non-interacting pair and a non-binding mutant at background, a positive control, a signal in several orientations, expression of the fusions shown, a saturable titration, a reversible complementation, background subtracted, independent experiments, one estimate method).
Every number must be above 0. Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller, and the two components and the dataset (``preparations``) are references to records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_split_reporter_record import (
    ASSAY_SYSTEMS, EXPERIMENT_TYPE, FACTS, PREPARATION_KEYS, QUANTITIES, READOUT_MODES, REPORTER_SYSTEMS, SPREAD_KINDS, SUPPORTS, UNITS, VERSION,
    fact, point, unavailable)

NOT_EXTRACTED = ('preparations',)
REPORTER_SYSTEM = 'reporter_system'
ASSAY_SYSTEM = 'assay_system'
READOUT_MODE = 'readout_mode'
SPREAD_KIND = 'spread_kind'
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# How well the quote supports a stated field: a fixed vocabulary (SUPPORTS). Null when the field is unavailable.
SUPPORT_MEANING = "Required when the status is 'stated', null when it is 'unavailable'. direct: the quote itself states the value or fact. implied: the quote states it only by implication. about_something_else: the quote is on the topic but is really about another measurement or condition."
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('orientation_pairs_tested', 'concentration_count', 'replicate_count')
CHOICES = {REPORTER_SYSTEM: REPORTER_SYSTEMS, ASSAY_SYSTEM: ASSAY_SYSTEMS, READOUT_MODE: READOUT_MODES, SPREAD_KIND: SPREAD_KINDS}

MEANING = {
    'kd': 'The apparent equilibrium dissociation constant of the two fusion proteins, as the passage reports it under the name KD or Kd (apparent dissociation constant) from the split-reporter experiment described in the passage (a titration of one partner, or the kinetics of association and dissociation, of a reversible split reporter such as NanoBiT). A KD that the passage cites as a known or previously reported property of the proteins, or one that comes from another method (for example SPR, ITC, fluorescence polarization or a pull-down, which a passage on a split reporter may also mention), or a KD the passage says was determined elsewhere or earlier, rather than from the split-reporter experiment described, is not stated: leave it unavailable. The affinity of the two reporter fragments for each other (for example the KD of LgBiT and SmBiT), a half-maximal effective concentration (EC50) of a ligand and a concentration at which a signal was seen are not this field. When the passage gives KD values for several pairs or conditions without saying which one is the result, leave it unavailable.',
    'kd_spread': 'The reported uncertainty of the KD given in the kd field (its standard error, standard deviation or confidence interval half-width), in a concentration unit, when the passage gives it as one number. A confidence interval given as a lower and an upper limit is not a half-width: leave this unavailable. An uncertainty reported for any other value (for example the plus-minus of a signal ratio) is not this field.',
    'signal_to_background': 'The signal of the tested pair of fusion proteins divided by the background signal (untransfected cells, cells with the empty vectors, buffer or substrate alone), as the passage gives it as one number: a signal-to-background ratio, or a fold of the signal over the background. A fold over the negative control pair, over a fragment alone, over a positive control, over a vehicle or over the time zero, and a fold change of a signal in response to a ligand or a drug, are not this field.',
    'signal_over_negative_control': 'The signal of the tested pair of fusion proteins divided by the signal of the negative control pair (a pair with a non-interacting protein, a non-binding mutant, or one fragment fusion with the free partner fragment), as the passage gives it as one number: a fold of the signal over the negative control. A fold over the background, over a positive control, over a vehicle and over a ligand-free state are not this field.',
    'orientation_pairs_tested': 'The number of different fusion orientation combinations of the two partners that the passage says were built and tested (which end of each partner carries which reporter fragment; with the two partners and two fragments, a full set is four or eight), as a whole number. The number of constructs in general, of cell lines, of mutants and of replicates is not this field. A passage that says only that several orientations were tested, with no number, does not state it.',
    'loaded_concentration_lowest': 'The lowest concentration of the titrated partner (the purified protein or the fusion protein added in a series, or the dilution series of a lysate in molar units) of the titration, as the passage gives it as a molar concentration (the smallest one when several are given). A concentration in mass per volume (for example ng/mL), an amount of DNA or a dilution factor is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one concentration does not state a lowest one.',
    'loaded_concentration_highest': 'The highest concentration of the titrated partner (the purified protein or the fusion protein added in a series) of the titration, as the passage gives it as a molar concentration (the largest one when several are given). A concentration in mass per volume (for example ng/mL), an amount of DNA or a dilution factor is not offered: answer unavailable with the reason unit_not_in_vocabulary, and do not convert it. A passage that gives only one concentration does not state a highest one.',
    'concentration_count': 'The number of different concentrations of the titrated partner at which the signal was read, as the passage gives it as a whole number (for example a dilution series of twelve concentrations). The number of time points, of wells and of replicates is not this field.',
    'replicate_count': 'The number of independent experiments the passage reports (separate experiments on separate days, transfections or preparations, or independent runs reported as replicates), as a whole number. Technical replicate wells and the concentrations of one series are not this field.',
    REPORTER_SYSTEM: 'The reporter whose two fragments are fused to the partners, as the passage names it: split NanoLuc (NanoBiT, LgBiT and SmBiT), another split luciferase (for example split firefly or split Renilla luciferase), a split fluorescent protein (split GFP, bimolecular fluorescence complementation BiFC, split Venus or YFP), split beta-lactamase, split TEV protease, or another reporter. A passage that does not name the reporter does not state it.',
    ASSAY_SYSTEM: 'Where the passage says the complementation was measured: in living cells, in a cell lysate, with purified proteins, or elsewhere. A passage that does not say it does not state it.',
    READOUT_MODE: 'How the passage says the signal was read for the result: an endpoint reading at one time or concentration, a titration (a series of concentrations of a partner), or a kinetic time course (the signal followed in time, for example the association and the dissociation). A passage that does not say it does not state it.',
    SPREAD_KIND: 'What the uncertainty given in the kd_spread field is, as the passage states it: a standard error, a standard deviation or a confidence interval.',
    'interaction_detected': 'Whether the passage says that the signal of the reconstituted reporter was seen for the tested pair of fusion proteins, above the background and the controls, so that the two proteins are reported to interact or to be in proximity (yes), or says that no such signal was seen and the pair was not different from the controls (no). A signal that the passage ascribes to the fragments alone, and an interaction that the passage shows only with another method, are not this fact.',
    'fragment_alone_control_negative': 'Whether the passage says that each fragment fusion alone, or each fusion with the free (unfused) partner fragment, gave only background signal, so that the fragments do not reconstitute by themselves (yes), or says that they gave a signal (no). A control that is only run, with no statement of its result, does not state it.',
    'unrelated_pair_control_negative': 'Whether the passage says that a pair of non-interacting or unrelated proteins fused to the same fragments gave only background signal (yes), or says that it gave a signal (no). The fragment fusion alone and a non-binding mutant are not this fact.',
    'binding_mutant_control_negative': 'Whether the passage says that a non-binding mutant of one partner (a point mutant or a deletion of the interface) in place of the partner gave only background signal, or a much lower signal, than the wild-type pair (yes), or says that it gave the same signal (no). An unrelated protein is not this fact.',
    'positive_control_done': 'Whether the passage says that a known interacting pair of proteins fused to the same fragments (for example a leucine zipper pair, or FKBP and FRB with rapamycin) gave a signal in the same assay, so that the assay works (yes), or says that it did not (no).',
    'signal_in_several_orientations': 'Whether the passage says that the signal of the tested pair was seen in more than one fusion orientation (which end of each partner carries which fragment) (yes), or says that it was seen in only one orientation and not in the others (no). A passage that tests orientations and does not say which gave a signal does not state it.',
    'expression_verified': 'Whether the passage says that the expression of the fusion proteins was shown (an immunoblot, a fluorescence or a luminescence tag, or comparable expression levels of the constructs) (yes), or says that the expression was not shown or was not comparable (no).',
    'saturable_titration_shown': 'Whether the passage says that the signal rose with the concentration of the titrated partner and reached a plateau, a saturable dose-response of a specific interaction (yes), or says that it rose linearly without saturation or did not depend on the concentration (no). A signal at one concentration does not state it.',
    'complementation_reversible': 'Whether the passage says that the reconstitution of the reporter is reversible, so that the signal follows the equilibrium of the partners (for example a low-affinity fragment pair such as NanoBiT, or a dissociation that was measured) (yes), or says that the reconstitution is irreversible, so that the complex is trapped and the signal accumulates (for example BiFC or split GFP) (no). A passage that names a reporter and does not say whether it is reversible does not state it.',
    'background_subtracted': 'Whether the passage says that the background signal (untransfected cells, empty vectors, buffer or substrate alone) was measured and subtracted or used to normalise the signal (yes), or says that it was not (no).',
    'independent_experiments': 'Whether the passage says the repeats were independent experiments (separate experiments, days, transfections or preparations) rather than wells of one plate or one sample (yes), or says that they were not (no).',
    'single_estimate_method': 'Whether the passage says that the interaction or the apparent KD of the two proteins was determined by the split reporter only (yes), or says that the interaction or the KD of these two proteins was also determined by another method (no). Another method that the passage mentions for a different purpose (for example to show the expression or to locate the interface) is not this fact, and a passage that reports no KD and says nothing about other methods for the binding does not state it. A sentence that only describes the method that was used does not say that no other method was used: yes needs the passage to say that this method alone was used.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the choices
    (reporter system, assay system, readout mode, spread kind), the facts."""
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
    """The record of ``literature_split_reporter_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
