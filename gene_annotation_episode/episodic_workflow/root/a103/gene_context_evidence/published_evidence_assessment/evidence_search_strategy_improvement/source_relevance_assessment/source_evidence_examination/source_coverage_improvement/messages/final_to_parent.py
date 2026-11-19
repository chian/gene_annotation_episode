"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding the
episode reported: the actual source claim, the actual source subject and its qualification (including unresolved
target correspondence), with the separate source windows it rests on. The old episode had no report fact sources of
its own, so there is no other field."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    validate_schema)

WINDOW_FORM = RecordForm({
    'source_ref': Field('text', 'The source the window is from'),
    'representation': Field('text', 'The representation read: text, original, stdout or stderr'),
    'offset': Field('integer', 'The UTF-8 byte offset of the window'),
    'limit': Field('integer', 'The UTF-8 byte length of the window'),
    'quote': Field('text', 'The exact quoted text of this window; separate windows are never concatenated'),
})
FINDING_FORM = RecordForm({
    'source_claim': Field('text', 'What the examined sections actually claim, in the source scope'),
    'source_subject': Field('text', 'The actual locus, genome, construct or entity the claim is about'),
    'qualification': Field('text', 'The conditions, limits and alternative explanations the source attaches, including '
                                   'neighboring-gene identity, order, orientation, spacing, fusion and cooccurrence'),
    'target_correspondence': Field('text', 'Whether the source subject corresponds to the target: established, '
                                           'unresolved or not applicable, and why'),
    'windows': Field('list', 'The source-bound windows, in reading order, the finding rests on',
                     items=WINDOW_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The actual source claim, subject and qualification of the evidence from the newly '
                               'covered sections', form=FINDING_FORM),
})

FINDING_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['source_claim', 'source_subject', 'qualification', 'target_correspondence', 'windows'],
    'properties': {
        'source_claim': {'type': 'string', 'minLength': 1},
        'source_subject': {'type': 'string', 'minLength': 1},
        'qualification': {'type': 'string', 'minLength': 1},
        'target_correspondence': {'type': 'string', 'minLength': 1},
        'windows': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['source_ref', 'representation', 'offset', 'limit', 'quote'],
            'properties': {'source_ref': {'type': 'string', 'minLength': 1},
                           'representation': {'enum': ['text', 'original', 'stdout', 'stderr']},
                           'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1},
                           'quote': {'type': 'string', 'minLength': 1}}}},
    },
}


def validate_report(finding, held):
    """The episode's check of its own report: the finding is valid against its schema and every source it cites
    resolves in this episode's context (``held`` maps each cited reference to whether the Episode holds it)."""
    validate_schema(finding, FINDING_SCHEMA)
    for window in finding['windows']:
        if not held.get(window['source_ref'], False):
            raise ValueError('a103_report_cites_a_source_the_episode_does_not_hold:' + window['source_ref'])


def final_to_parent(summary, completion, selection):
    finding = summary['report']
    if finding is None:
        raise ValueError('a103_source_coverage_finding_not_reported')
    validate_report(finding, summary['report_sources_held'])
    return {'credit': completion['credit'], 'finding': finding}
