"""A105 experiment identity: compare two leaf records, group immutable leaf records into graders, finalize a grader.

Owner rulings D, E, F, G (contract OWNER_DECISIONS 13 and 14). Pure functions on controlled data: arguments in,
controlled records out, no Store, no custody, no I/O. Leaf records are never changed (LEAF_RECORDS_IMMUTABLE); a grader
is a grouping of them derived by code and re-derivable until the page finalizes it.

WHERE THE IDENTITY FEATURES SIT ON A LEAF RECORD (contract: LEAF_RECORD_IDENTITY_PLACEMENT). The features of
LEAF_RECORD_IDENTITY are TOP-LEVEL keys of the leaf record, beside 'source_ref' and 'experiment_type'. A key that is
missing or None is NOT STATED (LEAF_RECORD_MISSING_MEANS). A record that carries no identity feature therefore states
nothing but source_ref and experiment_type and merges by the default rule.

HOW A LEAF RECORD IS REFERENCED. The leaf record's record ref is its LEAF_RECORD_REF_KEY ('experiment_ref'). It is used
only as the member reference, never as an identity (ruling G).

GROUPING RULE (order independent). Records are first split by (source_ref, experiment_type): the must-match keys.
Inside one block the default is MERGE. When no two records of the block conflict on an identity-bearing feature, the block
is ONE grader. When some do, the records are taken in a fixed order (records stating more identity-bearing features
first, then by record ref; this order depends only on the records, never on arrival) and each joins the existing group
in which it conflicts with NO member; among several such groups it joins the one with the most agreeing members
(positive ties), then the earliest; if there is none it opens a new group. A record that states nothing conflicting
(for example one that names no target) therefore never forces two conflicting records together and is never a bridge
that chains conflicting records into one component.

THE TARGET MOLECULE (OWNER_DECISION 18). The leaf record states target_id (the molecule the assay is about), optionally
partner_id and partner_role, as top-level keys. target_id and partner_id are identity-bearing and are compared by
equality after casefold and whitespace collapse (normalize_identity_ref); a side that does not state one is skipped. A
grader whose members state no target_id has no target (state_grader_fields: identity.target_id unavailable,
not_stated_in_passage); literature_bearing then gives it bearing none. The identity number fields carry no unit: the leaf
form states them in the canonical unit (temperature_c in degrees Celsius).

VALUE NORMALIZATION. Before two stated values are compared or deduplicated, both are normalized to the canonical unit
of their quantity with the contract's canonical_value (1 uM equals 1000 nM). A value whose unit is not in the
normalization table cannot be normalized: in identity_compare that side is treated as NOT STATED (missing, never a
conflict); in state_grader_fields the value is kept and only equal to an identical (value, unit) pair.
"""
import hashlib
import json
import re

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    IDENTITY_BEARING,
    IDENTITY_DEFAULT,
    IDENTITY_FEATURES,
    IDENTITY_MUST_MATCH,
    IDENTITY_NORMALIZED_REF_FIELDS,
    IDENTITY_NUMBER_TOLERANCE,
    IDENTITY_QUANTITY_OF_FIELD,
    IDENTITY_SPLIT_ONLY_ON,
    IDENTITY_UNIT_CANONICAL,
    LEAF_RECORD_IDENTITY_PLACEMENT,
    LEAF_RECORD_MISSING_MEANS,
    LEAF_RECORD_REF_KEY,
    LEAF_RECORDS_IMMUTABLE,
    POSITIVE_TIE_FEATURES,
    UNAVAILABLE_CONFLICTING,
    UNAVAILABLE_NOT_STATED,
    canonical_value,
    normalize_identity_ref,
    validate_grader_ref,
    validate_identity_compare,
    validate_state_grader_fields,
)

_SPAN_LOCATOR = re.compile(r'^bytes (\d+)-(\d+) of the source$')
_OPERAND_KEYS = ('status', 'value', 'unit', 'source_refs')
_NOT_STATED_FACTS = ('unknown', 'not_applicable')


# ---------------------------------------------------------------------------------------------------------------
# Value normalization
# ---------------------------------------------------------------------------------------------------------------
def _normalized(quantity, value, unit):
    """The value in the canonical unit of its quantity, or None when it cannot be normalized (a unit outside the
    table, a value that is not a finite number). This is the one place where canonical_value's ValueError is caught;
    the caller treats None as not stated."""
    try:
        return canonical_value(quantity, value, unit)
    except ValueError:
        return None


def _quantity_of_unit(unit):
    """The quantity kind whose table holds this unit, or None. The unit names of the tables do not overlap."""
    for quantity, table in IDENTITY_UNIT_CANONICAL.items():
        if unit in table['factors']:
            return quantity
    return None


# ---------------------------------------------------------------------------------------------------------------
# identity_compare
# ---------------------------------------------------------------------------------------------------------------
def _stated(record, name):
    """The stated value of an identity field; None when the key is missing or None (LEAF_RECORD_MISSING_MEANS)."""
    return record.get(name)


def _compare_equal(fields, a, b):
    compared = []
    for name in fields:
        va, vb = _stated(a, name), _stated(b, name)
        if va is None or vb is None:
            continue
        compared.append(va == vb)
    if not compared:
        return 'missing'
    return 'agree' if all(compared) else 'conflict'


def _compare_tolerance(feature, fields, a, b):
    """Two stated numbers agree when they are CLOSER than IDENTITY_NUMBER_TOLERANCE (strictly less). A field with a
    quantity kind (IDENTITY_QUANTITY_OF_FIELD, for example temperature_c) holds its value in the canonical unit of that
    quantity, so both sides are passed through canonical_value; a side that cannot be normalized counts as not stated."""
    tolerance = IDENTITY_NUMBER_TOLERANCE[feature]
    compared = []
    for name in fields:
        va, vb = _stated(a, name), _stated(b, name)
        if va is None or vb is None:
            continue
        quantity = IDENTITY_QUANTITY_OF_FIELD.get(name)
        if quantity is not None:
            unit = IDENTITY_UNIT_CANONICAL[quantity]['canonical']
            va, vb = _normalized(quantity, va, unit), _normalized(quantity, vb, unit)
            if va is None or vb is None:
                continue
        compared.append(abs(va - vb) < tolerance)
    if not compared:
        return 'missing'
    return 'agree' if all(compared) else 'conflict'


def _compare_equal_normalized(fields, a, b):
    """Target and partner identities (OWNER_DECISION 18): equal after casefold and whitespace collapse. A side that does
    not state the field is skipped (missing, never a conflict)."""
    compared = []
    for name in fields:
        va, vb = _stated(a, name), _stated(b, name)
        if va is None or vb is None:
            continue
        compared.append(normalize_identity_ref(va) == normalize_identity_ref(vb))
    if not compared:
        return 'missing'
    return 'agree' if all(compared) else 'conflict'


def _compare_span_overlap(fields, a, b):
    start_name, end_name = fields
    sa, ea, sb, eb = _stated(a, start_name), _stated(a, end_name), _stated(b, start_name), _stated(b, end_name)
    if sa is None or ea is None or sb is None or eb is None:
        return 'missing'
    # Spans are half open: 'bytes a-b' covers a up to b; spans that only touch do not overlap.
    return 'agree' if max(sa, sb) < min(ea, eb) else 'conflict'


def _compare_feature(feature, spec, a, b):
    mode = spec['compare']
    fields = spec['fields']
    if mode == 'equal':
        return _compare_equal(fields, a, b)
    if mode == 'equal_within_tolerance':
        return _compare_tolerance(feature, fields, a, b)
    if mode == 'equal_normalized':
        return _compare_equal_normalized(fields, a, b)
    if mode == 'span_overlap':
        return _compare_span_overlap(fields, a, b)
    raise ValueError(f'identity feature {feature} has an unknown compare mode {mode!r}')


def identity_compare(record_a, record_b):
    """Compare two leaf records. Per feature of IDENTITY_FEATURES, only fields both sides state are compared: agree,
    conflict or missing (missing is skipped, never a conflict). Numeric identity values are normalized to the canonical
    unit first, and a value that cannot be normalized (unit outside the table) is treated as not stated, so it is
    missing and never a conflict. The pair result is 'different' when source_ref or experiment_type differs
    (IDENTITY_MUST_MATCH) or when an identity-bearing feature conflicts; else 'same'. positive_tie is true when a
    POSITIVE_TIE_FEATURES feature (target_id, partner_id, locator_label) agrees. target_id and partner_id are
    identity-bearing: different stated targets (or partners), compared after casefold and whitespace collapse, make
    two different experiments; either side not stating one is skipped. The result is checked with validate_identity_compare."""
    for owner, record in (('record_a', record_a), ('record_b', record_b)):
        if not isinstance(record, dict):
            raise ValueError(f'{owner} must be a mapping')
        for name in IDENTITY_MUST_MATCH:
            if record.get(name) is None:
                raise ValueError(f'{owner}.{name} is required (it is a must-match of the identity rule)')
    features = {feature: _compare_feature(feature, spec, record_a, record_b) for feature, spec in IDENTITY_FEATURES.items()}
    must_match = all(record_a[name] == record_b[name] for name in IDENTITY_MUST_MATCH)
    bearing_conflict = any(features[feature] == 'conflict' for feature in IDENTITY_BEARING)
    result = {
        'features': features,
        'result': 'same' if must_match and not bearing_conflict else 'different',
        'positive_tie': any(features[feature] == 'agree' for feature in POSITIVE_TIE_FEATURES),
    }
    return validate_identity_compare(result)


# ---------------------------------------------------------------------------------------------------------------
# Field statements of one grader (what its members state, deduplicated on absolute byte spans)
# ---------------------------------------------------------------------------------------------------------------
def _parse_span(record, ref):
    spans = record.get('spans') or {}
    if ref not in spans:
        raise ValueError(f"record {record.get(LEAF_RECORD_REF_KEY)!r} cites span {ref!r} that its spans do not hold")
    match = _SPAN_LOCATOR.match(spans[ref]['locator'])
    if not match:
        raise ValueError(f"span {ref!r} has a locator that is not 'bytes a-b of the source': {spans[ref]['locator']!r}")
    return (int(match.group(1)), int(match.group(2)))


def _value_key(value, unit):
    """The raw representation of a stated value; also orders the representations of one normalized value."""
    return json.dumps([value, unit], sort_keys=True)


def _dedupe_key(value, unit, name=None):
    """The key under which stated values are the same value: the value in the canonical unit of its quantity (rounded
    to 12 significant digits against float noise), so 1 uM and 1000 nM are one value. A value that cannot be normalized
    keeps its raw (value, unit) as key. A target or partner identity (field identity.target_id / identity.partner_id)
    is the same value after casefold and whitespace collapse (OWNER_DECISION 18). A series (a list of numbers, for example a
    concentration series) with a unit in the table is the same series when every element, in order, is the same normalized
    number; a different series (other length, order or numbers) is a different value, so the field is conflicting; a series
    whose unit is not in the table keeps its raw (list, unit) as key."""
    if name is not None and name.startswith('identity.') and name[len('identity.'):] in IDENTITY_NORMALIZED_REF_FIELDS:
        return json.dumps(['identity', normalize_identity_ref(value)])
    quantity = _quantity_of_unit(unit)
    if isinstance(value, (list, tuple)):   # a series of numbers (for example a concentration series) with its unit
        if quantity is not None:
            canonical = [_normalized(quantity, item, unit) for item in value]
            if None not in canonical:
                return json.dumps(['canonical_series', quantity, [float(f'{item:.12g}') for item in canonical]])
        return json.dumps(['raw', _value_key(list(value), unit)])
    if quantity is not None:
        canonical = _normalized(quantity, value, unit)
        if canonical is not None:
            return json.dumps(['canonical', quantity, float(f'{canonical:.12g}')])
    return json.dumps(['raw', _value_key(value, unit)])


def _member_fields(record):
    """name -> ('stated', value, unit, [absolute spans]) or ('unavailable', reason or None), read from the generic record
    structure: quantities and top-level operands, facts, plain choices. Nothing type specific."""
    found = {}

    def operand(name, item):
        if item['status'] == 'point':
            found[name] = ('stated', item['value'], item['unit'], [_parse_span(record, ref) for ref in item['source_refs']])
        else:
            found[name] = ('unavailable', item.get('reason'))

    for name, item in (record.get('quantities') or {}).items():
        operand('quantities.' + name, item)
    for name, item in record.items():
        if name not in ('quantities', 'facts', 'spans', 'preparations', 'choice_support') and isinstance(item, dict) \
                and all(key in item for key in _OPERAND_KEYS):
            operand('operands.' + name, item)
    for name, item in (record.get('facts') or {}).items():
        if item['answer'] in _NOT_STATED_FACTS:
            found['facts.' + name] = ('unavailable', None)
        else:
            found['facts.' + name] = ('stated', item['answer'], None, [_parse_span(record, ref) for ref in item['source_refs']])
    for name in (record.get('choice_support') or {}):
        value = record.get(name)
        if value is None:
            found['choices.' + name] = ('unavailable', None)
        else:
            ref = 'span_' + name
            spans = [_parse_span(record, ref)] if ref in (record.get('spans') or {}) else []
            found['choices.' + name] = ('stated', value, None, spans)
    # OWNER_DECISION 18: the target and the partner identity (top-level keys of the leaf record). Unavailable when not stated;
    # the chunk's byte span (span_start, span_end) is the stated support when the record carries it.
    reasons = record.get('unavailable_reasons') or {}
    for name in IDENTITY_NORMALIZED_REF_FIELDS:
        value = record.get(name)
        if value is None:
            found['identity.' + name] = ('unavailable', UNAVAILABLE_CONFLICTING if reasons.get(name) == UNAVAILABLE_CONFLICTING else None)
        else:
            start, end = record.get('span_start'), record.get('span_end')
            found['identity.' + name] = ('stated', value, None, [(start, end)] if start is not None and end is not None else [])
    return found


def state_grader_fields(member_records):
    """What the members of one grader state, field by field (STATE_DEDUPE_KEY = absolute_byte_span). The same value
    stated by overlapping chunks is ONE stated value, after both are normalized to the canonical unit (1 uM and
    1000 nM are the same value; the representation that sorts first is kept); its spans are kept once each. A value
    whose unit is not in the normalization table is only the same as an identical (value, unit) pair. Different stated
    values keep both with their spans and the field is conflicting (reason ambiguous_or_conflicting_in_passage). A
    field no member states stays unavailable with reason not_stated_in_passage. A field no member states but one
    member found ambiguous in its passage is unavailable and conflicting. The member records are not changed. The
    result is checked with validate_state_grader_fields. The identity fields target_id and partner_id are stated as
    'identity.target_id' and 'identity.partner_id' (deduplicated after casefold and whitespace collapse; always present,
    unavailable with reason not_stated_in_passage when no member states them): identity.target_id unavailable means the
    grader has no target (OWNER_DECISION 18).
    A stated value may be a series (a list of numbers with its unit): the same series and unit count once, a different
    series is a conflict (see _dedupe_key).
    Returns {field name: {'status': 'stated' | 'unavailable', 'values': [{'value', 'unit', 'spans': [[start, end], ...]}],
    'conflicting': bool, 'reason': None | reason}}."""
    names = {}
    for record in member_records:
        for name, entry in _member_fields(record).items():
            names.setdefault(name, []).append(entry)
    fields = {}
    for name in sorted(names):
        by_value = {}
        ambiguous = False
        for entry in names[name]:
            if entry[0] == 'stated':
                slot = by_value.setdefault(_dedupe_key(entry[1], entry[2], name), {'representations': {}, 'spans': set()})
                slot['representations'][_value_key(entry[1], entry[2])] = (entry[1], entry[2])
                slot['spans'].update(entry[3])
            elif entry[1] == UNAVAILABLE_CONFLICTING:
                ambiguous = True
        values = []
        for _, slot in sorted(by_value.items()):
            value, unit = slot['representations'][min(slot['representations'])]
            if isinstance(value, (list, tuple)):
                value = list(value)   # a series is copied, the member record's list is not shared
            values.append({'value': value, 'unit': unit, 'spans': [list(span) for span in sorted(slot['spans'])]})
        if len(values) > 1:
            fields[name] = {'status': 'stated', 'values': values, 'conflicting': True, 'reason': UNAVAILABLE_CONFLICTING}
        elif values:
            fields[name] = {'status': 'stated', 'values': values, 'conflicting': False, 'reason': None}
        elif ambiguous:
            fields[name] = {'status': 'unavailable', 'values': [], 'conflicting': True, 'reason': UNAVAILABLE_CONFLICTING}
        else:
            fields[name] = {'status': 'unavailable', 'values': [], 'conflicting': False, 'reason': UNAVAILABLE_NOT_STATED}
    return validate_state_grader_fields(fields)


# ---------------------------------------------------------------------------------------------------------------
# group_leaf_records
# ---------------------------------------------------------------------------------------------------------------
def _stated_bearing_count(record):
    return sum(1 for feature in IDENTITY_BEARING if any(record.get(name) is not None for name in IDENTITY_FEATURES[feature]['fields']))


def _group_block(records, compares):
    """Groups of one (source_ref, experiment_type) block: default merge, split only on a bearing conflict (see module doc)."""
    ordered = sorted(records, key=lambda record: (-_stated_bearing_count(record), record[LEAF_RECORD_REF_KEY]))
    groups = []
    for record in ordered:
        open_groups = []
        for index, group in enumerate(groups):
            results = [compares(record, member) for member in group]
            if all(result['result'] == 'same' for result in results):
                open_groups.append((-sum(1 for result in results if result['positive_tie']), index))
        if open_groups:
            groups[min(open_groups)[1]].append(record)
        else:
            groups.append([record])
    return groups


def _summary(members, compares):
    summary = {}
    for feature in IDENTITY_FEATURES:
        results = [compares(a, b)['features'][feature] for i, a in enumerate(members) for b in members[i + 1:]]
        if 'conflict' in results:
            summary[feature] = 'conflict'
        elif 'agree' in results:
            summary[feature] = 'agree'
        else:
            summary[feature] = 'missing'
    return summary


def _grader_ref(source_ref, experiment_type, member_refs):
    digest = hashlib.sha256(json.dumps([source_ref, experiment_type, sorted(member_refs)]).encode('utf-8')).hexdigest()
    return 'grader_' + digest[:24]


def group_leaf_records(leaf_records):
    """Group immutable leaf records into graders (one experiment = one grader, one document). Default merge for the same
    source_ref and experiment_type; split only on a conflict of an identity-bearing feature both sides state. The result
    does not depend on the order of leaf_records. Identity features are read as top-level leaf record keys; the member
    ref is the leaf record's LEAF_RECORD_REF_KEY. Returns graders with GRADER_REF_FIELDS, finalized false; grader_ref is
    derived by code from source_ref, experiment_type and the sorted member record refs; conflicting_field_names is
    computed here from state_grader_fields of the members. The leaf records are not changed."""
    assert LEAF_RECORDS_IMMUTABLE and IDENTITY_DEFAULT == 'merge' and IDENTITY_SPLIT_ONLY_ON
    assert LEAF_RECORD_IDENTITY_PLACEMENT and LEAF_RECORD_MISSING_MEANS == 'not_stated'
    leaf_records = list(leaf_records)
    cache = {}

    def compares(a, b):
        key = (id(a), id(b)) if id(a) < id(b) else (id(b), id(a))
        if key not in cache:
            cache[key] = identity_compare(a, b)
        return cache[key]

    refs = [record.get(LEAF_RECORD_REF_KEY) for record in leaf_records]
    if len(set(refs)) != len(refs):
        raise ValueError(f'leaf records must have distinct record refs ({LEAF_RECORD_REF_KEY})')
    blocks = {}
    for record in leaf_records:
        for name in IDENTITY_MUST_MATCH:
            if record.get(name) is None:
                raise ValueError(f"leaf record {record.get(LEAF_RECORD_REF_KEY)!r} has no {name}")
        blocks.setdefault(tuple(record[name] for name in IDENTITY_MUST_MATCH), []).append(record)
    graders = []
    for (source_ref, experiment_type), records in blocks.items():
        for members in _group_block(records, compares):
            member_refs = sorted(member[LEAF_RECORD_REF_KEY] for member in members)
            fields = state_grader_fields(members)
            grader = {
                'grader_ref': _grader_ref(source_ref, experiment_type, member_refs),
                'source_ref': source_ref,
                'experiment_type': experiment_type,
                'member_record_refs': member_refs,
                'finalized': False,
                'identity_summary': _summary(members, compares),
                'conflicting_field_names': [name for name, state in fields.items() if state['conflicting']],
            }
            graders.append(validate_grader_ref(grader))
    graders.sort(key=lambda grader: (grader['source_ref'], grader['experiment_type'], grader['member_record_refs'][0]))
    return graders


# ---------------------------------------------------------------------------------------------------------------
# finalize_grader
# ---------------------------------------------------------------------------------------------------------------
def finalize_grader(grader):
    """Mark a grader finalized (the page decides when FINALIZE_WHEN holds) and validate it. Returns a new grader record;
    the argument is not changed. A grader that is already finalized is refused. Every grader, incomplete ones included,
    is finalized; the only grader the page skips is a SKIPPED_GRADER finding, which never reaches this function. A grader
    with no stated target is finalized like any other (it counts in the credit); it bears on no candidate, which
    literature_bearing decides from the target the members state (OWNER_DECISION 18)."""
    validate_grader_ref(grader)
    if grader['finalized']:
        raise ValueError('grader is already finalized')
    finalized = dict(grader, finalized=True)
    return validate_grader_ref(finalized)
