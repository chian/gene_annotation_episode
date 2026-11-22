"""The IDENTITY block of an A105 extraction answer: the features that say WHICH experiment a chunk describes, asked of the model
beside the answer of every experiment type, with the TARGET MOLECULE required.

The block is derived from the row contract's own field list (``literature_row_contract.IDENTITY_FIELDS``): nothing here is a second
schema kept in step by hand. The fields the leaf asks the model for (``ASKED``) are the contract's identity fields without the ones
code supplies (``NOT_ASKED``: the experiment type is known to the leaf, ``source_ref`` is stamped by code, the four preparation refs
are not stated by a passage, the chunk's absolute byte span is stamped from the chunk offset, and the unavailable reasons are
derived). Experiment identity is feature based: the model returns identity features and CODE assigns identity.

Every asked field is either stated (``status`` 'stated': ``value``, ``unit`` where the field has one, ``quote``, ``support``) or
unavailable (``status`` 'unavailable': a ``reason`` and nothing else), with the same conventions as the type forms. The model never
counts and never gives an offset: a program finds the byte span of every quote, and a quote must occur in the chunk exactly once.

What the model gives and what code derives:

* the NAME fields (``target_id``, ``partner_id``): the model gives the molecule's name exactly as the passage writes it (``value``) and
  the quote, a short exact span that contains the name and occurs once in the chunk (the name itself usually occurs many times, so
  the quote is the unique span that shows the passage names it in its role). CODE checks that the name is inside the quote and
  derives the identity value with ``normalize_identity_ref``; the model's own typing is never the stored value.
* the SEQUENCE IDENTITY fields (``subject_database_id``, ``subject_organism``, ``subject_residue_range``, ``subject_mutations`` and the
  same four with the prefix ``partner_``) are written like the name fields: exactly as the passage writes them, inside a unique quote,
  normalized by code; ``subject_database`` and ``partner_database`` are vocabulary fields. They say which sequence the molecule is, so
  code can resolve it to a database record and its sequence; a name alone is not a database id.
* the vocabulary fields (subject_database, partner_database, partner_role, construct_tag_class, species_class, immobilization_side, buffer_class, ionic_strength_class,
  reference_kind, panel_letter, section_class): a value of the contract's vocabulary and a quote.
* the numeric fields: ``temperature_c`` is given as a number and a unit ('C' or 'K') and CODE converts it to degrees Celsius with
  ``canonical_value`` and stores the canonical number; ``ph`` is a number; ``label_number`` (the figure, table or section number) is a
  whole number. A number must be written in its quote.
* the locator: ``reference_kind`` ('figure', 'table', 'section', 'supplement', 'text'), ``label_number`` and ``panel_letter``, each with
  the quote of the reference as the passage writes it ('Figure 3B', 'Table 2', 'Supplementary Fig. S4').

``identity_record_keys`` gives the top-level keys of the leaf record exactly as the contract places them
(``LEAF_RECORD_IDENTITY_PLACEMENT``: beside ``source_ref`` and ``experiment_type``; a None key is NOT STATED) and checks them with
the contract's ``validate_identity``. ``with_identity`` adds them, the spans of the stated fields and their support to a type
form's record without changing the form's own record."""
import re

from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CODE_STAMPED_IDENTITY, IDENTITY_FIELDS, IDENTITY_NORMALIZED_REF_FIELDS, IDENTITY_QUANTITY_OF_FIELD, IDENTITY_UNAVAILABLE_REASONS,
    IDENTITY_UNIT_CANONICAL, LEAF_RECORD_IDENTITY, LEAF_RECORD_REF_KEY, NAME_MAX_CHARS, NAME_MAX_WORDS, UNAVAILABLE_NOT_STATED, canonical_value, is_name,
    comparable_identity_name, normalize_identity_ref, validate_identity)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS

KEY = 'identity'   # the one key under which the identity block sits in the answer the model fills
# The contract's identity fields the model is NOT asked for: the type (known to the leaf), the four preparation refs (references to
# records, which no passage states), the chunk's absolute span (stamped by code from the chunk offset) and the derived reasons.
NOT_ASKED = ('experiment_type', 'analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref',
             'span_start', 'span_end', 'unavailable_reasons')
ASKED = tuple(name for name in IDENTITY_FIELDS if name not in CODE_STAMPED_IDENTITY and name not in NOT_ASKED)
NAME_FIELDS = IDENTITY_NORMALIZED_REF_FIELDS      # target_id, partner_id
LOCATOR_NUMBER = 'label_number'
PANEL = 'panel_letter'
# Why an asked field is unavailable: the contract's own list (a unit outside the vocabulary has no place in the identity).
REASONS = IDENTITY_UNAVAILABLE_REASONS

MEANING = {
    'target_id': 'The TARGET MOLECULE: the molecule the assay is about, the protein being assayed in this experiment. value is its name exactly as the passage writes it (a gene or protein symbol or name on one line, at most 12 words, the name only and never a sentence); the quote is the exact span that contains the name and shows the passage names it as the molecule the assay is about. Stated only when the passage names the molecule the assay is about. Not a reagent, antibody, tag, buffer component, instrument, control protein, or a molecule only cited from other work. A molecule that appears only as what an antibody is raised against, or inside a reagent name such as anti-X, is a reagent and is not the target. Give the name with its tag or fusion prefix exactly as the passage writes it (His-X stays His-X). When the passage names no target, answer unavailable.',
    'partner_id': 'The PARTNER: the other molecule the target is tested against in this experiment (the ligand or the binding partner). value is its name exactly as the passage writes it; the quote is the exact span that contains the name and shows it is the target\'s partner. Stated only when the passage names it, and never the same molecule as the target. Not a reagent, antibody, tag, buffer component, instrument or control protein.',
    'partner_role': 'The role of the partner in the assay: analyte (in solution, flowed or added), immobilized (held on a surface, bead or plate), ligand (a small molecule or ligand), protein (a partner protein), other. Only when the partner is stated.',
    'subject_database_id': 'The database identifier of the TARGET molecule, exactly as the passage writes it: an accession, a locus tag or a gene identifier (for example CC_1319, P0A7Z4, 1ABC). Stated only when the passage writes such an identifier for the target. A name or symbol alone (PopZ, HSP90, RecA) is NOT a database id: leave this unavailable when the passage gives only the name. An identifier of the partner, of a reagent or of a molecule cited from other work is not the target\'s.',
    'subject_database': 'The database the target\'s identifier belongs to, only when subject_database_id is stated and the passage says or shows which: uniprot, genbank, refseq, pdb, bvbrc, locus_tag (a genome locus tag), other. gene_name_only when the passage gives the target by name with no identifier. The quote is the span that shows the database or the identifier.',
    'subject_organism': 'The organism and strain of the TARGET molecule exactly as the passage writes it (at most 12 words, for example Caulobacter crescentus NA1000). Stated only when the passage says which organism the target protein comes from in THIS experiment. An organism named in the legend or text of another experiment, of a cited study, or of the host used to express the protein is not stated here.',
    'subject_residue_range': 'The residue range of the target construct exactly as the passage writes it (for example 1-177). Stated only when the passage gives the residues of the target used in this experiment.',
    'subject_mutations': 'The mutations or variants of the target as the passage writes them (for example K45A or R78E), on one line. Stated only when the passage says the target carries them in this experiment; the wild type is not a mutation.',
    'partner_database_id': 'The database identifier of the PARTNER molecule, exactly as the passage writes it (an accession, a locus tag or a gene identifier). Only when the partner is stated. A name alone is NOT a database id: leave this unavailable when the passage gives only the partner\'s name.',
    'partner_database': 'The database the partner\'s identifier belongs to, only when partner_database_id is stated and the passage says or shows which: uniprot, genbank, refseq, pdb, bvbrc, locus_tag, other. gene_name_only when the passage gives the partner by name with no identifier.',
    'partner_organism': 'The organism and strain of the PARTNER molecule exactly as the passage writes it (at most 12 words). Only when the passage says which organism the partner comes from in THIS experiment; an organism of another experiment is not stated here.',
    'partner_residue_range': 'The residue range of the partner construct exactly as the passage writes it. Only when the passage gives the residues of the partner used in this experiment.',
    'partner_mutations': 'The mutations or variants of the partner as the passage writes them, on one line. Only when the passage says the partner carries them in this experiment.',
    'construct_tag_class': 'The tag on the target protein as used in the assay: untagged, his_tag, gst_tag, biotin_tag, fusion_protein (fused to another protein or domain), other_tag. Stated only when the passage says how the target was tagged or fused.',
    'species_class': 'The species the target protein comes from (the passage names the species or organism).',
    'immobilization_side': 'Which molecule is held on a surface, bead or plate: target (the target is immobilized, coated or captured), partner (the partner is), none (the passage says that neither is, both free in solution). Stated only when the passage says it.',
    'buffer_class': 'The buffering agent of the assay buffer the passage names: phosphate, tris, hepes, acetate, carbonate, other.',
    'temperature_c': 'The temperature of the experiment as the passage states it, with its unit C (degrees Celsius) or K (kelvin). A temperature in another unit, or no number, is unavailable.',
    'ph': 'The pH of the assay buffer the passage states, as a number from 0 to 14.',
    'ionic_strength_class': 'The ionic strength of the assay buffer: low, physiological (about 100 to 200 mM monovalent salt), high. The quote is the salt or ionic strength statement.',
    'reference_kind': 'What kind of place in the document the chunk states the experiment\'s result in: figure, table, section, supplement (a supplementary figure or table), text (the running text without a figure or table reference). The quote is the reference as the passage writes it (for example Figure 3B, Table 2, Supplementary Fig. S4).',
    'label_number': 'The number of the figure, table or section reference, as a whole number (3 for Figure 3B). The quote is the reference as the passage writes it.',
    'panel_letter': 'The panel letter of the figure reference, in lower case (b for Figure 3B). Only with a label number. The quote is the reference as the passage writes it.',
    'section_class': 'Which part of the paper the chunk is, when the chunk itself shows it (a heading or a legend): abstract, introduction, methods, results, discussion, figure_legend, table, supplement, other. Otherwise unavailable.',
}


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _units(name):
    quantity = IDENTITY_QUANTITY_OF_FIELD.get(name)
    return tuple(IDENTITY_UNIT_CANONICAL[quantity]['factors']) if quantity else ()


def _value_schema(name):
    spec = IDENTITY_FIELDS[name]
    if name in NAME_FIELDS:
        return {'type': 'string', 'minLength': 1}
    if spec['kind'] == 'vocab':
        return {'enum': list(spec['vocab'])}
    if spec['kind'] == 'count':
        return {'type': 'integer', 'minimum': 0, **({'maximum': spec['hi']} if spec['hi'] is not None else {})}
    return {'type': 'number'}


def _field_schema(name):
    properties = {'status': {'enum': ['stated', 'unavailable']}, 'value': _nullable(_value_schema(name))}
    if _units(name):
        properties['unit'] = _nullable({'enum': list(_units(name))})
    properties.update({'quote': _nullable({'type': 'string', 'minLength': 1}), 'support': _nullable({'enum': list(SUPPORTS)}),
                       'reason': _nullable({'enum': list(REASONS)})})
    return {'type': 'object', 'additionalProperties': False, 'description': MEANING[name], 'required': list(properties),
            'properties': properties}


def identity_answer_schema():
    """The JSON schema of the identity block: one object per asked identity field, named as in the row contract."""
    schema = {name: _field_schema(name) for name in ASKED}
    return {'type': 'object', 'additionalProperties': False, 'required': list(schema), 'properties': schema,
            'description': 'The identity features of the experiment this chunk reports: which molecule it is about (the target), what it is tested against, how it was prepared and run, and where in the document it is reported.'}


def answer_schema_with_identity(type_schema):
    """The schema the model fills: the type form's answer schema plus the identity block under ``KEY``."""
    schema = {name: type_schema['properties'][name] for name in type_schema['required']}
    return {'type': 'object', 'additionalProperties': False, 'required': [*schema, KEY],
            'properties': {**schema, KEY: identity_answer_schema()}}


def split_answer(answer):
    """``(type answer, identity block)`` of an answer filled under ``answer_schema_with_identity``. The block is None when absent."""
    return {name: item for name, item in answer.items() if name != KEY}, answer.get(KEY)


class IdentityRefused(ValueError):
    """The identity block does not satisfy its schema or a rule of the identity features."""


def _refuse(name, code, detail=None):
    raise IdentityRefused(KEY + '.' + name + ':' + code + ('' if detail is None else ':' + str(detail)))


def quote_span(chunk, quote):
    """The (start, end) byte span of ``quote`` in ``chunk``, counted in UTF-8 bytes from the first byte of the chunk
    (end is the byte after the last). None unless the quote occurs exactly once."""
    at = chunk.find(quote)
    if not quote or at < 0 or chunk.find(quote, at + 1) >= 0:
        return None
    start = len(chunk[:at].encode('utf-8'))
    return start, start + len(quote.encode('utf-8'))


def _written(number):
    """The ways a number is written: 7.4 and 7.40, 25 and 25.0."""
    return {format(number, 'g'), repr(number), str(int(number)) if float(number).is_integer() else repr(number)}


def _stated_value(name, item):
    """The value code stores for a stated field: a name normalized, a temperature in degrees Celsius, any other value as given."""
    if name in NAME_FIELDS:
        return normalize_identity_ref(item['value'])
    if name in IDENTITY_QUANTITY_OF_FIELD:
        return canonical_value(IDENTITY_QUANTITY_OF_FIELD[name], item['value'], item['unit'])
    return item['value']


def validate_identity_answer(answer, chunk):
    """Raise ``IdentityRefused`` unless the identity block ``answer`` satisfies ``identity_answer_schema()``, every stated field's quote
    occurs exactly once in ``chunk``, a name is inside its quote and is a reference (``REF_PATTERN`` after normalization), a number
    is written in its quote and converts to its canonical unit inside the contract's range, a partner differs from the target, a
    partner role needs a partner and a panel letter needs a label number. Returns ``answer``."""
    if not isinstance(answer, dict):
        _refuse('answer', 'schema', 'the identity block is missing')
    errors = sorted(Draft202012Validator(identity_answer_schema()).iter_errors(answer), key=lambda error: list(error.path))
    if errors:
        _refuse('.'.join(str(part) for part in errors[0].path) or 'answer', 'schema', errors[0].message[:200])
    for name in ASKED:
        item = answer[name]
        carried = ('value', 'quote', 'support') + (('unit',) if _units(name) else ())
        if item['status'] == 'unavailable':
            if item['reason'] is None or any(item[key] is not None for key in carried):
                _refuse(name, 'unavailable_has_a_reason_and_nothing_else')
            continue
        if item['reason'] is not None or any(item[key] is None for key in carried):
            _refuse(name, 'stated_has_value_unit_quote_span_and_no_reason')
        quote = item['quote']
        if quote not in chunk:
            _refuse(name, 'quote_is_not_in_the_chunk')
        if quote_span(chunk, quote) is None:
            _refuse(name, 'quote_occurs_more_than_once', 'make_the_quote_longer_so_it_occurs_once')
        if name in NAME_FIELDS:
            if item['value'] not in quote:
                _refuse(name, 'name_is_not_inside_its_quote', 'value_is_the_name_exactly_as_the_passage_writes_it')
            if not is_name(item['value']):
                _refuse(name, 'value_is_not_a_molecule_name', f'one_line_at_most_{NAME_MAX_CHARS}_characters_and_{NAME_MAX_WORDS}_words_the_name_only_not_a_sentence')
        if IDENTITY_FIELDS[name]['kind'] in ('number', 'count') and not any(text in quote for text in _written(item['value'])):
            _refuse(name, 'number_is_not_written_in_its_quote')
        if name == PANEL and not re.search(r'\d[\s(.,\-]{0,3}' + item['value'] + r'(?![a-z])', quote.lower()):
            _refuse(name, 'panel_letter_is_not_written_in_its_quote')
        try:
            stored = _stated_value(name, item)
        except ValueError as error:
            _refuse(name, 'canonical_conversion_refused', error)
        spec = IDENTITY_FIELDS[name]
        if spec['kind'] == 'number' and not spec['lo'] <= stored <= spec['hi']:
            _refuse(name, 'number_outside_its_range', f"{spec['lo']}_to_{spec['hi']}")
    stated = {name for name in ASKED if answer[name]['status'] == 'stated'}
    if 'partner_id' in stated and 'target_id' in stated and (comparable_identity_name(answer['partner_id']['value']) ==
                                                               comparable_identity_name(answer['target_id']['value'])):
        _refuse('partner_id', 'partner_is_the_target', 'the_partner_is_the_other_molecule')
    if 'partner_role' in stated and 'partner_id' not in stated:
        _refuse('partner_role', 'partner_role_without_partner_id')
    if PANEL in stated and LOCATOR_NUMBER not in stated:
        _refuse(PANEL, 'panel_letter_without_label_number')
    return answer


def identity_record_keys(answer, chunk, chunk_offset, *, experiment_type, source_ref):
    """The top-level keys a leaf record carries for a VALID identity block (``LEAF_RECORD_IDENTITY``, beside ``source_ref`` and
    ``experiment_type``): a stated field holds its canonical value (a name normalized, the temperature in degrees Celsius), any other
    field is None (NOT STATED) with its reason in ``unavailable_reasons``; the preparation refs are not stated by a passage (None,
    ``not_stated_in_passage``); ``span_start`` and ``span_end`` are the chunk's absolute byte span. Checked with ``validate_identity``."""
    keys, reasons = {}, {}
    for name in ASKED:
        item = answer[name]
        keys[name] = _stated_value(name, item) if item['status'] == 'stated' else None
        if keys[name] is None:
            reasons[name] = item['reason']
    for name in NOT_ASKED:
        if name in ('experiment_type', 'span_start', 'span_end', 'unavailable_reasons'):
            continue
        keys[name] = None
        reasons[name] = UNAVAILABLE_NOT_STATED
    keys['experiment_type'] = experiment_type
    keys['span_start'] = chunk_offset
    keys['span_end'] = chunk_offset + len(chunk.encode('utf-8'))
    keys['unavailable_reasons'] = reasons
    validate_identity({**keys, 'source_ref': source_ref})
    return {name: keys[name] for name in LEAF_RECORD_IDENTITY}


def identity_spans(answer, chunk, chunk_offset):
    """The spans of the stated identity fields, keyed ``span_identity_<field>`` as the type forms key theirs: the quote and its byte
    span in the source (the chunk's offset plus the quote's offset in the chunk)."""
    spans = {}
    for name in ASKED:
        if answer[name]['status'] == 'stated':
            start, end = quote_span(chunk, answer[name]['quote'])
            spans['span_identity_' + name] = {'locator': 'bytes ' + str(chunk_offset + start) + '-' + str(chunk_offset + end) + ' of the source',
                                              'quote': answer[name]['quote']}
    return spans


def with_identity(record, answer, chunk, chunk_offset):
    """The leaf record: the type form's ``record`` plus the identity keys at top level, the spans of the stated identity fields in
    ``spans`` and ``identity_provenance`` (field -> its span key and its support). The form's own record is not changed."""
    keys = identity_record_keys(answer, chunk, chunk_offset, experiment_type=record['experiment_type'], source_ref=record['source_ref'])
    spans = identity_spans(answer, chunk, chunk_offset)
    provenance = {name: {'span_ref': 'span_identity_' + name, 'support': answer[name]['support']} for name in ASKED if answer[name]['status'] == 'stated'}
    return {**record, **keys, 'spans': {**record['spans'], **spans}, 'identity_provenance': provenance}


# The fields of a leaf record: what its form asked and what it states (the leaf field-counting rule,
# literature_leaf_extraction.field_counts).
_RESERVED = ('quantities', 'facts', 'spans', 'preparations', 'choice_support', 'identity_provenance', 'unavailable_reasons')
_OPERAND_KEYS = ('status', 'value', 'unit', 'source_refs')


def _operand_names(record):
    names = ['quantities.' + name for name in record.get('quantities') or {}]
    names += ['operands.' + key for key, item in record.items() if key not in _RESERVED and isinstance(item, dict) and all(k in item for k in _OPERAND_KEYS)]
    return names


def _read_operand(record, name):
    kind, key = name.split('.', 1)
    return record['quantities'][key] if kind == 'quantities' else record[key]


def asked_fields(record):
    """The names of the fields the leaf record's form asked (those the record carries, the asked identity keys included)."""
    return (_operand_names(record) + ['choices.' + name for name in record.get('choice_support') or {}]
            + ['facts.' + name for name in record.get('facts') or {}] + ['identity.' + name for name in ASKED])


def stated_fields(record):
    """The names, among ``asked_fields(record)``, that the leaf record states: a quantity or operand with status 'point', a fact
    whose answer is neither 'unknown' nor 'not_applicable', a choice that is not None, an asked identity key that is not None."""
    stated = [name for name in _operand_names(record) if _read_operand(record, name)['status'] == 'point']
    stated += ['choices.' + name for name in record.get('choice_support') or {} if record.get(name) is not None]
    stated += ['facts.' + name for name, item in (record.get('facts') or {}).items() if item['answer'] not in ('unknown', 'not_applicable')]
    stated += ['identity.' + name for name in ASKED if record.get(name) is not None]
    return stated


def one_record_per_experiment(held):
    """The leaf records that stand, one per experiment ref (``LEAF_RECORD_REF_KEY``, 'experiment_ref': kind, source and window):
    ``held`` is the (record ref, leaf record) pairs in arrival order. A re-extraction of the same experiment supersedes, it is not
    merged: the record that stands is the one stating the most fields (``stated_fields``), ties broken by the latest. Returns the
    record refs that stand, in the arrival order of their experiment refs' first records. A record ref held twice is one record."""
    standing, order = {}, []
    for ref, record in held:
        key = record[LEAF_RECORD_REF_KEY]
        if key not in standing:
            order.append(key)
        elif standing[key][0] == ref:
            continue
        count = len(stated_fields(record))
        if key not in standing or count >= standing[key][1]:
            standing[key] = (ref, count)
    return [standing[key][0] for key in order]
