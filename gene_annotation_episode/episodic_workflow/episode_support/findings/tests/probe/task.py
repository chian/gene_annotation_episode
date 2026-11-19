"""The task: one plan step per unit, each a call of a tool that runs findings library functions through the
Episode's custody-scoped store, as an episode's tool does."""
from datetime import datetime, timezone
import importlib
from pathlib import Path

from episode_runtime import ToolCall
from gene_annotation_episode.domain import canonical

PACKAGE = 'gene_annotation_episode.episodic_workflow.episode_support.findings.'


def idle(arguments, ctx):
    return {'idle': True}


def library(axis, name):
    return importlib.import_module(PACKAGE + axis + '.' + name)


def image_view(arguments, ctx):
    """The image.view flow of an axis's tool: select a frame, keep the source and the view, read the view back and
    resolve it to a file inside a scratch directory."""
    images, store = library(arguments['axis'], 'image_evidence'), ctx.store
    body = images.prepare_image(store, arguments['source_ref'], colour_conversion=arguments['colour_conversion'])
    with store.transaction():
        source = store.put('source', {
            'provider': 'image.view', 'accession': None, 'uri': None, 'artifact_ref': body['image_artifact_ref'],
            'text_ref': None, 'parent_source_refs': [body['input_source_ref']],
            'request_ref': store.artifact(canonical(body), 'application/json'), 'version': body['software_version'],
            'retrieved_at': datetime.now(timezone.utc).isoformat()}, origin='tool')
        view = store.put('image_view', {'source_ref': source['id'], **body}, origin='tool')
    metadata = images.view_metadata(store, view['id'])
    with store.scratch('image-input') as scratch:
        shown = images.resolve_image_input(store, scratch, store.get(view['id']))
        copied = Path(shown['path']).read_bytes()
        inside = Path(shown['path']).parent == scratch.path
    return {'body': body, 'view': view['id'], 'metadata_is_view': metadata == store.get(view['id']),
            'shown_type': shown['type'], 'copy_is_display': copied == store.get_artifact(body['image_artifact_ref']),
            'copy_inside_scratch': inside, 'display': body['image_artifact_ref']}


def image_view_refused(arguments, ctx):
    """A frame the source does not have is refused by the library's own error."""
    images = library(arguments['axis'], 'image_evidence')
    try:
        images.prepare_image(ctx.store, arguments['source_ref'], frame=arguments['frame'])
    except Exception as error:
        return {'raised': type(error).__name__ + ': ' + str(error)}
    return {'raised': None}


def finding(status, claim, reason='not_withdrawn', replaces=(), same=None):
    return {'source_claim': claim, 'qualification': {'kind': 'none', 'context_refs': [], 'assumption_refs': []},
            'status': status, 'withdrawal_reason': reason, 'same_source_claim_as_ref': same,
            'replaces_refs': list(replaces)}


def findings(arguments, ctx):
    """An assessment carrying a typed finding, its correction withdrawing it, and the finding library over them:
    the roots and write extent of the assessments, the replacement scope, which findings are eligible and valid,
    and the finding-unit progress with the reason a superseded known finding is inactive."""
    axis, store, target = arguments['axis'], ctx.store, arguments['target']
    scope = {'subject_refs': [target]}
    scientific, validity = library(axis, 'scientific_findings'), library(axis, 'finding_validity')
    value = {'type': 'enum', 'value': 'intact'}
    claim = {'subject_refs': [target], 'predicate': 'sequence_integrity', 'value': value, 'context_refs': []}
    with store.transaction():
        hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                              'value': value, 'context_refs': []}, origin='reasoning')['id']
        observation = store.put('observation', {
            'subject_refs': [target], 'source_subject_refs': [], 'kind': 'source_content',
            'source_ref': arguments['source'], 'measurements': [], 'dependencies': [], 'anchor': None},
            origin='external')['id']
        base = {'hypothesis_ref': hypothesis, 'observation_ref': observation, 'relation': 'strengthens',
                'applicability': 'direct', 'extent_basis': 'observed_extent', 'condition_refs': [],
                'assumption_refs': []}
        first = store.put('assessment', {**base, 'expected_revision': 0,
                                         'investigation_finding': finding('retained', claim)},
                          origin='reasoning', scope=scope)['id']
    out = {'first': first, 'roots': sorted(scientific.finding_target_roots(store, store.get(first))),
           'extent': validity.target_eligible(store, store.get(first), scope),
           'correction': validity.correction_eligible(store, store.get(first), scope)}
    withdrawn = None
    if arguments['withdraw']:
        with store.transaction():
            withdrawn = store.put('assessment', {
                **base, 'expected_revision': 1,
                'investigation_finding': finding('withdrawn', claim, 'superseded_evidence', replaces=[first] if arguments['replaces'] else [])},
                origin='reasoning', scope=scope)['id']
        if arguments['replaces']:
            scientific.validate_replacement_scope(store, store.get(withdrawn), scope)
    out['second'] = withdrawn
    if 'investigation_progress' in arguments:
        progress = library(axis, 'investigation_progress')
        policy = progress.FindingProgressPolicy(finding_unit=arguments['investigation_progress'])
        known = progress.project_finding_progress(store, scope, policy, known_assessment_refs=[first],
                                                  details_limit=10)
        out['progress'] = known
    return out


TOOLS = {'idle': idle, 'image_view': image_view, 'image_view_refused': image_view_refused, 'findings': findings}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    return ToolCall(item['tool'], item['arguments'])


def action(response, summary, records, ctx):
    raise ValueError('findings_probe_asks_no_model')
