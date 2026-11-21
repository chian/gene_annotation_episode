"""Credit: the leaf's own progress in lessening uncertainty, the share of the fields the form asked that this Episode's
records newly state. A field is stated when a held record states it (a quantity or operand with status 'point', a fact whose
answer is neither 'unknown' nor 'not_applicable', a choice that is not None, an asked identity key that is not None); it is newly
stated by the first held record that states it, and a record held twice (the same ref) is one record. Never bounded, clamped or
rescaled. The judgement of the stated fields belongs to the page, never to this leaf.

The page's row resolution change stays the authoritative credit; this share is only the leaf's own progress."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_identity_extraction as identity

_RESERVED = ('quantities', 'facts', 'spans', 'preparations', 'choice_support', 'identity_provenance', 'unavailable_reasons')
_OPERAND_KEYS = ('status', 'value', 'unit', 'source_refs')


def _operand_names(record):
    names = ['quantities.' + name for name in record.get('quantities') or {}]
    names += ['operands.' + key for key, item in record.items() if key not in _RESERVED and isinstance(item, dict) and all(k in item for k in _OPERAND_KEYS)]
    return names


def asked_fields(record):
    """The names of the fields the record's form asked (those the record carries, the asked identity keys included)."""
    return (_operand_names(record) + ['choices.' + name for name in record.get('choice_support') or {}]
            + ['facts.' + name for name in record.get('facts') or {}] + ['identity.' + name for name in identity.ASKED])


def stated_fields(record):
    """The names, among ``asked_fields(record)``, that the record states."""
    stated = [name for name in _operand_names(record) if _read_operand(record, name)['status'] == 'point']
    stated += ['choices.' + name for name in record.get('choice_support') or {} if record.get(name) is not None]
    stated += ['facts.' + name for name, item in (record.get('facts') or {}).items() if item['answer'] not in ('unknown', 'not_applicable')]
    stated += ['identity.' + name for name in identity.ASKED if record.get(name) is not None]
    return stated


def _read_operand(record, name):
    kind, key = name.split('.', 1)
    return record['quantities'][key] if kind == 'quantities' else record[key]


def field_counts(records, record_refs):
    """{'stated', 'newly_stated', 'asked'} over the held leaf records ``record_refs`` (in the order given): ``stated`` adds up what
    each record states, ``newly_stated`` counts each field once, at the first record that states it, ``asked`` is the number of
    fields the form asked (the same for every record of one experiment type)."""
    seen, stated, asked = set(), 0, 0
    for ref in record_refs:
        record = json.loads(records.get_artifact(ref))
        now = stated_fields(record)
        stated += len(now)
        seen.update(now)
        asked = max(asked, len(asked_fields(record)))
    return {'stated': stated, 'newly_stated': len(seen), 'asked': asked}


def credit(summary, records):
    counts = summary['counts']
    return counts['newly_stated'] / counts['asked'] if counts['asked'] else 0.0


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` with ``arguments`` is taken as the next unit.

    The episode has one action, ``extract``, whatever its arguments: it holds one record of the commissioned experiment type,
    and the credit is newly_stated / asked, the share of the asked fields that the held records state. That share is a
    fraction of the fields the form asked, so it never exceeds 1 (a field is counted once however many records state it, and
    the asked count of a record is at least the fields it states). A new record can therefore raise it only up to 1, so the
    most it can add is what is not yet earned, 1 - credit(summary, records), and no less than 0 once every asked field is
    stated. The bound is the same for every arguments (the answer is the model's, so no argument narrows it). Any other
    action type is not one this episode offers and cannot earn: 0."""
    if action_type != 'extract':
        return 0.0
    return max(0.0, 1.0 - credit(summary, records))
