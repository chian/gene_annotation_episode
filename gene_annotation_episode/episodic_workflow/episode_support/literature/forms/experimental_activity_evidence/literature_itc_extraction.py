"""The extraction of ONE isothermal titration calorimetry (ITC) experiment from one chunk of text, derived from the ITC
grader's input form (``literature_itc_record.py``).

Same design as the SPR extraction (``literature_spr_extraction``) and private to ITC: the grader's input form IS the
extraction's answer form; nothing here is a second schema kept in step by hand. ``answer_schema()``,
``validate_answer()``, ``quote_span()`` and ``record_from_answer()`` are all derived from the form's own declarations
(its quantities, units, facts and vocabularies). The model gives only the quote of each stated field; code finds the
UTF-8 byte span, and a quote that does not occur in the chunk exactly once is refused.

Differences from SPR that come from the form: the ITC form has no concentration series; enthalpy and entropy are
signed (a stated negative value is valid), and a temperature may be in K or C. Every other number must be above 0.
Fields not extracted (``NOT_EXTRACTED``): the identity references (``experiment_ref``, ``source_ref``,
``assertion_ref``) are given by the caller and the three preparation references (``preparations``) are references to
records, which no passage states; they stay unknown (None).
"""
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_record import (
    EXPERIMENT_TYPE, FACTS, FIT_MODELS, PREPARATION_KEYS, QUANTITIES, SPREAD_KINDS, SUPPORTS, TITRATION_MODES, UNITS, VERSION, fact, point, unavailable)

KELVIN_OFFSET = 273.15   # 0 C in kelvin (a definition)
NOT_EXTRACTED = ('preparations',)
SPREAD_KIND = 'spread_kind'
FIT_MODEL = 'fit_model'
TITRATION_MODE = 'titration_mode'
CHOICES = {SPREAD_KIND: SPREAD_KINDS, FIT_MODEL: FIT_MODELS, TITRATION_MODE: TITRATION_MODES}
# Why a field is unavailable: a fixed vocabulary.
REASONS = ('not_stated_in_passage', 'unit_not_in_vocabulary', 'ambiguous_or_conflicting_in_passage')
# A fact answer the passage can state. 'unknown' is the unavailable status itself and 'not_applicable' is a
# judgement of the grader's question, never a statement of a passage.
STATABLE = {name: tuple(answer for answer in answers if answer not in ('unknown', 'not_applicable'))
            for name, answers in FACTS.items()}
COUNTS = ('injection_count', 'replicate_count')
# Signed quantities: a stated enthalpy or entropy may be negative (or any sign); a temperature in C may be below 1.
SIGNED = ('enthalpy', 'entropy', 'temperature')

MEANING = {
    'kd': 'The equilibrium dissociation constant KD of the interaction as the passage reports it from the titration, in a concentration unit.',
    'kd_spread': 'The reported uncertainty of the KD (its standard error, standard deviation or confidence interval half-width), in a concentration unit.',
    'stoichiometry': 'The fitted binding stoichiometry n of the titration (ligand molecules per molecule in the cell).',
    'expected_stoichiometry': 'The stoichiometry the passage says the complex is expected to have (for example from a structure), not the fitted n. Stated only when the passage says the stoichiometry is expected, predicted or known beforehand; a sentence that describes what the measured n shows (for example a dimer bound by one ligand) is the measured result, so answer unavailable.',
    'enthalpy': 'The binding enthalpy change, with its sign as the passage gives it (negative for heat released).',
    'entropy': 'The binding entropy change dS itself (not T dS), with its sign as the passage gives it.',
    'temperature': 'The temperature at which the titration was done.',
    'cell_concentration': 'The concentration of the partner placed in the calorimeter cell.',
    'syringe_concentration': 'The concentration of the ligand (titrant) placed in the syringe.',
    'injection_count': 'The number of injections of the titration (a whole number).',
    'replicate_count': 'The number of replicate titrations the passage reports (a whole number).',
    'final_molar_ratio': 'The molar ratio of ligand (syringe) to partner (cell) reached at the END of the titration, as the passage states it (for example "titrated to a final molar ratio of 3" or "up to a 2.5-fold molar excess of ligand"). Not the fitted stoichiometry n, and not the ratio of the two starting concentrations unless the passage says that is the final ratio.',
    SPREAD_KIND: 'What the reported KD uncertainty is.',
    FIT_MODEL: 'The binding model the passage says the isotherm was fitted with.',
    TITRATION_MODE: 'How the titrant was added, as the passage states it: incremental (a series of separate injections), single_injection (one long injection of the whole titrant) or continuous (continuous injection or a slow ramp). Answer incremental only when the passage says the titration was done by separate injections; a bare injection count does not state the mode.',
    'dilution_control_performed': 'Whether the passage says the heat of diluting the ligand into buffer was measured (a control titration).',
    'dilution_control_subtracted': 'Whether the passage says the heat of dilution was subtracted from the binding heats.',
    'baseline_corrected': 'Whether the passage says the baseline was corrected or the raw thermogram was baseline-treated before integration.',
    'concentrations_determined': 'Whether the passage says the protein and ligand concentrations were determined accurately (for example by absorbance or amino acid analysis).',
    'active_fraction_determined': 'Whether the passage says the active fraction of the protein was determined or accounted for.',
    'binding_sites_heterogeneous': 'Whether the passage says the binding sites are heterogeneous or interacting (several kinds of site).',
    'residuals_reported': 'Whether the passage says the residuals of the fit are shown or reported.',
    'n_fitted_freely': 'Whether the passage says the stoichiometry n was a free fitting parameter (yes) or was fixed (no).',
    'buffer_matching': 'Whether the passage says how the buffers of the cell and syringe samples were matched (dialysed together, matched by a stated procedure, or not matched).',
    'temperature_controlled': 'Whether the passage says the temperature was controlled (held constant by the instrument).',
    'independent_titrations': 'Whether the passage says the replicate titrations were independent (separate samples or preparations).',
    'enthalpy_buffer_ionization_corrected': 'Whether the passage says the reported binding enthalpy was corrected for the heat of buffer protonation or ionization (an intrinsic, buffer-independent enthalpy): yes if it was corrected, no if the passage says the reported enthalpy is the observed one, not corrected.',
    'binding_detected': 'The yes/no result of this experiment as the passage states it: yes when it says the experiment showed that the two partners bind (heats of binding, a binding isotherm, a reported binding constant, or the plain statement that one binds the other as measured by ITC); no when it says the experiment showed no binding (no heat beyond dilution, "did not bind", "no detectable binding"). A passage that only describes how the experiment was done, or names the method without its result, does not state this.',
}


def field_names():
    """Every field the extraction answers, in the form's own order: the quantities, the spread kind,
    the fit model, the titration mode, the facts."""
    return (*QUANTITIES, SPREAD_KIND, FIT_MODEL, TITRATION_MODE, *FACTS)


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
    occurs exactly once in ``chunk``; a number is above 0 (enthalpy and entropy: any sign; temperature: above absolute zero) and a stated value carries its unit
    where the field has one; a stated field carries a support (direct, implied or about_something_else) and an unavailable one carries none. Returns ``answer``."""
    errors = sorted(Draft202012Validator(answer_schema()).iter_errors(answer), key=lambda error: list(error.path))
    if errors:
        _refuse('.'.join(str(part) for part in errors[0].path) or 'answer', 'schema', errors[0].message[:200])
    for name in field_names():
        item = answer[name]
        carried = ('value', 'quote', 'support') +(('unit',) if name in UNITS else ())
        if item['status'] == 'unavailable':
            if item['reason'] is None or any(item[key] is not None for key in carried):
                _refuse(name, 'unavailable_has_a_reason_and_nothing_else')
            continue
        if item['reason'] is not None or any(item[key] is None for key in carried):
            _refuse(name, 'stated_has_value_unit_quote_span_and_no_reason')
        if name == 'temperature':
            if item['value'] <= (-KELVIN_OFFSET if item['unit'] == 'C' else 0):
                _refuse(name, 'temperature_must_be_above_absolute_zero')
        elif name in QUANTITIES and name not in SIGNED and item['value'] <= 0:
            _refuse(name, 'number_must_be_above_zero')
        _quote(name, item, chunk)
    return answer


def _span(chunk, offset, item):
    start, end = quote_span(chunk, item['quote'])
    return {'locator': 'bytes ' + str(offset + start) + '-' + str(offset + end) + ' of the source', 'quote': item['quote']}


def record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref):
    """The ITC record of ``literature_itc_record`` for a VALID answer. ``chunk`` is the chunk's text and ``chunk_offset`` its byte offset
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
