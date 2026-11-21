"""The record of ONE finalized grader: the member leaf records of one grouping (literature_identity.group_leaf_records) merged
into one record in the shape the type's grade function reads. Pure: records in, a record out; no Store, no custody, no I/O;
the member records are never changed (LEAF_RECORDS_IMMUTABLE).

merged_record(experiment_type, member_records, grader_ref) -> one record.
(The third argument is not in the brief's signature: the grader's ref cannot be derived from the members here, so the caller,
the page, passes grader['grader_ref'].)

THE SHAPE IS DERIVED FROM THE MEMBERS, never from one type's module. All 25 leaf records of the experimental types share one
generic structure, and the fields are found by structure:
  quantities           {name: operand}; an operand is {value, unit, status ('point' | 'unavailable'), reason, measurement_keys,
                       source_refs, origin, native_component, support}
  top-level operands   any other top-level mapping that has the operand keys status, value, unit and source_refs (the
                       concentration series of the types that have one), same rules as quantities
  choices              the plain top-level values named by the keys of 'choice_support'; choice_support[name] is the support
  facts                {name: {answer, source_refs, support}}
  spans                {span ref: {locator 'bytes a-b of the source', quote}}
  preparations         the type's own preparation refs {key: ref or None}
  identity keys        the top-level LEAF_RECORD_IDENTITY keys (target_id, partner_id, partner_role, the descriptors, the four
                       preparation refs, temperature_c, ph, locator fields, span_start, span_end, unavailable_reasons) and
                       'identity_provenance' {field: {span_ref, support}}

HOW A VALUE IS CHOSEN (per field, over the members that STATE it; members are taken in the order of their experiment_ref, so
the result never depends on arrival):
  * a stated value is an operand with status 'point', a fact whose answer is not 'unknown' ('not_applicable' counts as a
    stated answer, a judgement call: it keeps the criterion not_applicable), a choice that is not None.
  * the same value (and the same unit) from several members counts ONCE; its source_refs are the distinct ABSOLUTE byte spans
    of all the stating members, one reference per span (ref 'span_<start>-<end>', deduplicated on the byte span, every
    distinct span kept), each with its locator and quote in 'spans'.
  * its support is the WEAKEST support class (SUPPORT_WEAKEST_ORDER) among the members that state the chosen value.
  * BASE OPERAND: the operand shell (unit, origin, measurement_keys, native_component) is copied from the FIRST member, in
    experiment_ref order, that states the chosen value; for an unavailable field from the first member. Only status, value,
    source_refs, reason and support are then set from the merge.
  * different stated values (or a member that found the field ambiguous and no member states it): the field is UNAVAILABLE
    with the exact reason 'ambiguous_or_conflicting_in_passage' (an operand: status 'unavailable', value None, reason, no
    refs, support None; a fact: answer 'unknown'; a choice: None). Nothing is picked among the values.
  * a field no member states: unavailable with 'not_stated_in_passage'.
  The reason of every unavailable field (operand, fact and choice alike) is also kept in the added top-level map
  'unavailable_field_reasons' {'quantities.<n>' | 'operands.<n>' | 'facts.<n>' | 'choices.<n>': reason}, because a fact and a
  choice have no place for a reason in the record shape (the identity key 'unavailable_reasons' is the identity fields' own map).
  * preparations: a key stated by exactly one distinct value takes it; different values, or none, give None (unknown, so
    dependent).
  * identity keys: the same normalized value (target_id and partner_id after normalize_identity_ref) is one value; the two
    number fields temperature_c and ph agree when their stated values are closer than IDENTITY_NUMBER_TOLERANCE (the first
    member's value is kept); a conflict or no statement gives None with its reason in 'unavailable_reasons'; span_start and
    span_end are the hull of the members' chunk spans.

experiment_ref is set to the grader_ref, source_ref to the document, experiment_type to the type; assertion_ref is also the
grader_ref (the grader serves every candidate; the grade functions and the old sheet inside the converters need a non-empty
reference there; it is never read as a candidate by the page).
"""
import copy
import re

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    IDENTITY_NORMALIZED_REF_FIELDS,
    IDENTITY_NUMBER_TOLERANCE,
    LEAF_RECORD_IDENTITY,
    SUPPORT_WEAKEST_ORDER,
    UNAVAILABLE_CONFLICTING,
    UNAVAILABLE_NOT_STATED,
    normalize_identity_ref,
)

_LOCATOR = re.compile(r'^bytes (\d+)-(\d+) of the source$')
_OPERAND_KEYS = ('status', 'value', 'unit', 'source_refs')
_RESERVED = ('quantities', 'facts', 'spans', 'preparations', 'choice_support', 'identity_provenance', 'unavailable_reasons')
_IDENTITY_NAMES = tuple(name for name in LEAF_RECORD_IDENTITY if name not in ('experiment_type', 'unavailable_reasons', 'span_start', 'span_end'))


def _weakest(supports):
    held = [support for support in supports if support is not None]
    return min(held, key=SUPPORT_WEAKEST_ORDER.index) if held else None


def _locate(member, ref, spans):
    """The merged reference of the member's span `ref`: 'span_<start>-<end>' of its absolute byte span; the span is registered
    once with its locator and quote (the same bytes are the same quote)."""
    held = (member.get('spans') or {}).get(ref)
    if held is None:
        raise ValueError(f"record {member['experiment_ref']!r} cites span {ref!r} that its spans do not hold")
    match = _LOCATOR.match(held['locator'])
    if not match:
        raise ValueError(f"span {ref!r} of record {member['experiment_ref']!r} has a locator that is not 'bytes a-b of the source': {held['locator']!r}")
    merged = f'span_{match.group(1)}-{match.group(2)}'
    spans.setdefault(merged, {'locator': held['locator'], 'quote': held['quote']})
    return merged


def _span_order(merged_ref):
    start, end = merged_ref[len('span_'):].split('-')
    return int(start), int(end)


def _entry(member, stated, value=None, unit=None, support=None, refs=(), reason=None, item=None):
    return {'member': member, 'stated': stated, 'value': value, 'unit': unit, 'support': support, 'refs': list(refs), 'reason': reason, 'item': item}


def _resolve(entries):
    """(chosen entries or None, reason or None): the entries that state the single chosen value, or the reason the field is
    unavailable. Members are already in experiment_ref order."""
    groups = []
    for entry in entries:
        if not entry['stated']:
            continue
        for group in groups:
            if group[0]['value'] == entry['value'] and group[0]['unit'] == entry['unit']:
                group.append(entry)
                break
        else:
            groups.append([entry])
    if len(groups) == 1:
        return groups[0], None
    if len(groups) > 1 or any(entry['reason'] == UNAVAILABLE_CONFLICTING for entry in entries):
        return None, UNAVAILABLE_CONFLICTING
    return None, UNAVAILABLE_NOT_STATED


def _merged_refs(chosen, spans):
    refs = {_locate(entry['member'], ref, spans) for entry in chosen for ref in entry['refs']}
    return sorted(refs, key=_span_order)


def _operand_entries(members, read):
    entries = []
    for member in members:
        item = read(member)
        if item is None:
            continue
        if item['status'] == 'point':
            entries.append(_entry(member, True, item['value'], item['unit'], item.get('support'), item['source_refs'], item=item))
        else:
            entries.append(_entry(member, False, reason=item.get('reason'), item=item))
    return entries


def _merge_operand(entries, spans, reasons, path):
    chosen, reason = _resolve(entries)
    if chosen is None:
        item = copy.deepcopy(entries[0]['item'])
        item.update({'value': None, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'support': None})
        reasons[path] = reason
        return item
    item = copy.deepcopy(chosen[0]['item'])
    item['source_refs'] = _merged_refs(chosen, spans)
    item['support'] = _weakest(entry['support'] for entry in chosen)
    return item


def _merge_fact(entries, spans, reasons, path):
    chosen, reason = _resolve(entries)
    if chosen is None:
        reasons[path] = reason
        return {'answer': 'unknown', 'source_refs': [], 'support': None}
    return {'answer': chosen[0]['value'], 'source_refs': _merged_refs(chosen, spans), 'support': _weakest(entry['support'] for entry in chosen)}


def _merge_choice(entries, spans, reasons, path):
    """(value, support)."""
    chosen, reason = _resolve(entries)
    if chosen is None:
        reasons[path] = reason
        return None, None
    _merged_refs(chosen, spans)   # the choice's spans are kept in 'spans' (a choice has no source_refs in the record shape)
    return chosen[0]['value'], _weakest(entry['support'] for entry in chosen)


def _names(members, read):
    """The field names in first-seen order over the members (members are in experiment_ref order)."""
    names = []
    for member in members:
        for name in read(member):
            if name not in names:
                names.append(name)
    return names


def _identity_value(name, entries):
    """(value or None, reason or None, chosen entries) of one identity key over the members that carry the key."""
    stated = [entry for entry in entries if entry['stated']]
    if name in IDENTITY_NUMBER_TOLERANCE:
        values = [entry['value'] for entry in stated]
        if values and max(values) - min(values) < IDENTITY_NUMBER_TOLERANCE[name]:
            return stated[0]['value'], None, stated
        if values:
            return None, UNAVAILABLE_CONFLICTING, []
    else:
        chosen, reason = _resolve(entries)
        if chosen is not None:
            return chosen[0]['value'], None, chosen
        return None, reason, []
    return None, (UNAVAILABLE_CONFLICTING if any(entry['reason'] == UNAVAILABLE_CONFLICTING for entry in entries) else UNAVAILABLE_NOT_STATED), []


def _identity(members, spans):
    """(identity keys, 'unavailable_reasons', 'identity_provenance') of the merged record; empty when no member carries one."""
    keys, reasons, provenance = {}, {}, {}
    for name in _IDENTITY_NAMES:
        if not any(name in member for member in members):
            continue
        entries = []
        for member in members:
            if name not in member:
                continue
            value = member[name]
            if value is None:
                entries.append(_entry(member, False, reason=(member.get('unavailable_reasons') or {}).get(name)))
            else:
                entries.append(_entry(member, True, normalize_identity_ref(value) if name in IDENTITY_NORMALIZED_REF_FIELDS else value))
        value, reason, chosen = _identity_value(name, entries)
        keys[name] = value
        if value is None:
            reasons[name] = reason
            continue
        held = [(entry['member'], (entry['member'].get('identity_provenance') or {}).get(name)) for entry in chosen]
        held = [(member, source) for member, source in held if source is not None]
        if held:
            refs = sorted({_locate(member, source['span_ref'], spans) for member, source in held}, key=_span_order)
            provenance[name] = {'span_ref': refs[0], 'span_refs': refs, 'support': _weakest(source['support'] for _, source in held)}
    if any('span_start' in member for member in members):
        starts = [member['span_start'] for member in members if member.get('span_start') is not None and member.get('span_end') is not None]
        ends = [member['span_end'] for member in members if member.get('span_start') is not None and member.get('span_end') is not None]
        keys['span_start'], keys['span_end'] = (min(starts), max(ends)) if starts else (None, None)
        if not starts:
            reasons['span_start'] = reasons['span_end'] = UNAVAILABLE_NOT_STATED
    return keys, reasons, provenance


def merged_record(experiment_type, member_records, grader_ref):
    """The record of one grader (see the module docstring for the rules): the member leaf records of ONE grader merged into
    one record in the type's record shape. A member of another type or document, a repeated member ref or members of
    different record versions raise ValueError (a wrong grouping is not repaired)."""
    members = sorted(member_records, key=lambda record: record['experiment_ref'])
    if not members:
        raise ValueError('a grader needs at least one member record')
    refs = [member['experiment_ref'] for member in members]
    if len(set(refs)) != len(refs):
        raise ValueError('member records must have distinct record refs (experiment_ref)')
    for name in ('experiment_type', 'source_ref', 'version'):
        if len({member[name] for member in members}) != 1:
            raise ValueError(f'the member records of one grader must share {name}')
    if members[0]['experiment_type'] != experiment_type:
        raise ValueError(f"the member records are of type {members[0]['experiment_type']!r}, not {experiment_type!r}")
    spans, reasons = {}, {}

    quantities = {}
    for name in _names(members, lambda member: member.get('quantities') or {}):
        quantities[name] = _merge_operand(_operand_entries(members, lambda member, name=name: (member.get('quantities') or {}).get(name)), spans, reasons, 'quantities.' + name)

    operands = {}
    for name in _names(members, lambda member: [key for key, item in member.items() if key not in _RESERVED and isinstance(item, dict) and all(k in item for k in _OPERAND_KEYS)]):
        operands[name] = _merge_operand(_operand_entries(members, lambda member, name=name: member.get(name)), spans, reasons, 'operands.' + name)

    choices, choice_support = {}, {}
    for name in _names(members, lambda member: member.get('choice_support') or {}):
        entries = []
        for member in members:
            if name not in (member.get('choice_support') or {}):
                continue
            value = member.get(name)
            refs_of = ['span_' + name] if value is not None and 'span_' + name in (member.get('spans') or {}) else []
            entries.append(_entry(member, value is not None, value, None, member['choice_support'][name], refs_of))
        choices[name], choice_support[name] = _merge_choice(entries, spans, reasons, 'choices.' + name)

    facts = {}
    for name in _names(members, lambda member: member.get('facts') or {}):
        entries = []
        for member in members:
            item = (member.get('facts') or {}).get(name)
            if item is not None:
                entries.append(_entry(member, item['answer'] != 'unknown', item['answer'], None, item.get('support'), item['source_refs']))
        facts[name] = _merge_fact(entries, spans, reasons, 'facts.' + name)

    preparations = {}
    for key in _names(members, lambda member: member.get('preparations') or {}):
        values = []
        for member in members:
            value = (member.get('preparations') or {}).get(key)
            if value is not None and value not in values:
                values.append(value)
        preparations[key] = values[0] if len(values) == 1 else None

    identity, identity_reasons, provenance = _identity(members, spans)

    record = {'version': members[0]['version'], 'experiment_type': experiment_type, 'experiment_ref': grader_ref,
              'source_ref': members[0]['source_ref'], 'assertion_ref': grader_ref, 'preparations': preparations}
    record.update(identity)
    record['quantities'] = quantities
    record.update(operands)
    record.update(choices)
    record['choice_support'] = choice_support
    record['facts'] = facts
    record['spans'] = {ref: spans[ref] for ref in sorted(spans, key=_span_order)}
    if identity:
        record['unavailable_reasons'] = identity_reasons
        record['identity_provenance'] = provenance
    record['unavailable_field_reasons'] = reasons
    return record
