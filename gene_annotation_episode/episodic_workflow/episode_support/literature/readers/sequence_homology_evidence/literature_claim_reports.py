"""The controlled report of an A101 literature episode and the counts code reads from it.

A101 has no literature grader or subscoring sheet (``INVESTIGATION_FINDING_FEATURES_a101.md`` section 0.1). What a
literature episode writes with its ``report`` tool is therefore a set of controlled entries chosen by the model from
fixed vocabularies (section 9): the source the entry rests on (a record the episode holds), the kind of claim the
source makes, how the source's subject relates to the target, whether the source reports a measurement, and
optionally the annotation (a function name or ID as written in the source, taken as given and never looked up).
No paragraph, interpretation or qualification passes: the counts below and the chosen source references are what a
parent receives. Each episode calls these functions with its own entry location fields."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    REF, obj)

CLAIM_KINDS = ('reported_sequence_identity', 'reported_domain_assignment', 'reported_family_assignment',
               'reported_homolog_function', 'reported_non_transferability', 'no_applicable_claim')
SUBJECT_RELATIONS = ('target_itself', 'aligned_homolog', 'family_member', 'unresolved')
NO_CLAIM = 'no_applicable_claim'
UNRESOLVED = 'unresolved'
ANNOTATION = {'type': 'string', 'minLength': 1, 'maxLength': 200,
              'description': 'The function name or ID the claim concerns, as written in the source'}
INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
# Entry locations by episode kind (integers only).
PASSAGE_LOCATION = {'offset': INTEGER, 'limit': POSITIVE}
TABLE_LOCATION = {'row_start': INTEGER, 'row_end': INTEGER, 'column_start': INTEGER, 'column_end': INTEGER}

CLAIM_MEANING = ('The kind of claim the source makes: a reported sequence identity, a domain assignment, a family '
                 'assignment, the function of a homolog, a report that function does not transfer, or no '
                 'applicable claim')
RELATION_MEANING = ('How the subject of the claim relates to the target: the target itself, an aligned homolog, a '
                    'family member, or unresolved correspondence')


def entry_schema(location=None):
    """The JSON schema of one report entry; ``location`` adds the episode's integer location fields."""
    properties = {'source_ref': REF, 'claim_kind': {'enum': list(CLAIM_KINDS), 'description': CLAIM_MEANING},
                  'subject_relation': {'enum': list(SUBJECT_RELATIONS), 'description': RELATION_MEANING},
                  'measured': {'type': 'boolean',
                               'description': 'Whether the source reports a measurement (not a prediction or an '
                                              'annotation)'},
                  'function': ANNOTATION, **(location or {})}
    return obj(properties, [name for name in properties if name != 'function'])


def report_schema(location=None):
    """The ``report`` tool's input: the entries, one per claim the report rests on."""
    return obj({'entries': {'type': 'array', 'items': entry_schema(location)}})


def entry_form(location=()):
    """The return form of one entry: controlled fields and the source as a record reference."""
    fields = {'source_refs': Field('record_refs', 'The source the entry rests on (one reference)'),
              'claim_kind': ChoiceField('text', CLAIM_MEANING, CLAIM_KINDS),
              'subject_relation': ChoiceField('text', RELATION_MEANING, SUBJECT_RELATIONS),
              'measured': Field('boolean', 'Whether the source reports a measurement'),
              'function': Field('text', 'The annotation the claim concerns, as written in the source (taken as '
                                'given)', required=False)}
    fields.update({name: Field('integer', 'Entry location: ' + name.replace('_', ' ')) for name in location})
    return RecordForm(fields)


def returned_entries(report, location=()):
    """The entries as returned: each source as a one-reference list, the controlled fields and the location."""
    if report is None:
        return []
    rows = []
    for entry in report['entries']:
        row = {'source_refs': [entry['source_ref']], 'claim_kind': entry['claim_kind'],
               'subject_relation': entry['subject_relation'], 'measured': entry['measured'],
               **{name: entry[name] for name in location}}
        if 'function' in entry:
            row['function'] = entry['function']
        rows.append(row)
    return rows


COUNT_FIELDS = {'written': Field('boolean', 'Whether the model wrote a report before the episode ended'),
                'entry_count': Field('integer', 'Entries in the report'),
                'unresolved_correspondence_count': Field('integer', 'Entries whose subject correspondence to the '
                                                         'target is unresolved'),
                **{'claim_count_' + kind: Field('integer', 'Entries of claim kind ' + kind) for kind in CLAIM_KINDS}}


def report_counts(report):
    """The counts code reads from the latest report (all zero when none was written)."""
    entries = [] if report is None else report['entries']
    counts = {'written': report is not None, 'entry_count': len(entries),
              'unresolved_correspondence_count': sum(entry['subject_relation'] == UNRESOLVED for entry in entries)}
    counts.update({'claim_count_' + kind: sum(entry['claim_kind'] == kind for entry in entries)
                   for kind in CLAIM_KINDS})
    return counts


def chosen_source_refs(report):
    """The sources of entries with an applicable claim, in first-seen order."""
    if report is None:
        return []
    return list(dict.fromkeys(entry['source_ref'] for entry in report['entries']
                              if entry['claim_kind'] != NO_CLAIM))


def report_source_refs(report):
    """Every source a report names (each must be held for the report to be accepted)."""
    return [] if report is None else list(dict.fromkeys(entry['source_ref'] for entry in report['entries']))
