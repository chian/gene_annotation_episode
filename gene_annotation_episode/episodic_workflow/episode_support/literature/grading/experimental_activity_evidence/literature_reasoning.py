"""The A105 reasoning unit of a literature episode and what its outcomes answer.

``reason`` is the old ``ExperimentalInterpretation.execute_reasoning`` (every A105 literature episode at
``97308b94c``) on the custody-scoped store: the interpretation and the graders selected for it are committed in one
unit by ``literature_required_grading.execute`` (AGENTS.md, "Required literature evidence processing": an accepted
interpretation is refused unless its subscoring sheet is saved with it), and for a verified-source-leads commission
the validated source lead is part of the same transaction (the old ``credit.validate_lead``).

The other functions read what the episode's units answer for the commissioned literature task, as counts and record
references: the relevant lead sources (own validated leads and the lead sources its children returned, merged in
unit order) and the examined no-applicable-evidence spans with whether they cover the commissioned spans (the old
``lead_dispositions`` and ``screening_answers``)."""
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.scientific_findings import (
    FindingIdentity)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_required_grading import (
    action_schema, execute)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_task_credit import (
    _resolve, lead_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_grading_inputs import (
    assay_grading_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_inputs import (
    _Sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical, obj, source_location_inputs, validate_schema)

REASON_DESCRIPTION = (
    'Commit one typed scientific reasoning over the examined source and the records you hold (extracted terms, source '
    'subjects, contexts, observations, hypotheses and assessments, each with its exact source anchor) together with '
    'its evidence_processing in this one call: the gradings that save the subscoring sheet of each relevant '
    'experiment (alias references allowed), or a source-grounded no_applicable_evidence with the exact examined '
    'spans. An interpretation is not saved without its grading sheet. Every assessment carries its typed '
    'investigation_finding of the common schema; it stays a record of this episode. What returns to your parent is '
    'the features code reads from the saved grading sheets (evidence type, quantity kind, measured effect, variance, '
    'log evidence ratio, prediction model, criterion statuses) and their references, never prose. A commit with every '
    'section empty and no no_applicable_evidence or source lead is rejected.')


def reason_schema(commit_schema, leads):
    """The ``reason`` tool's arguments: the required-grading action (the typed commit and ``evidence_processing``)
    and, for a verified-source-leads commission, a ``source_lead``. The ``kind`` of the old selection is the tool."""
    schema = action_schema(commit_schema, source_location_inputs(assay_grading_population_schema()))
    properties = {name: value for name, value in schema['properties'].items() if name != 'kind'}
    if leads:
        properties['source_lead'] = lead_schema()
    return source_location_inputs(obj(properties, required=[name for name in schema['required'] if name != 'kind']))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def validate_lead(store, lead, outcome, proposed):
    """The old ``credit.validate_lead`` on custody: the lead's identity and exact source witness against the records
    this Episode holds. A violation is a ``ContractError``."""
    value = _resolve(lead, outcome['aliases'])
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    if not all(store.holds(ref) for ref in (value['source_ref'], value['subject_ref'], proposed)):
        raise ContractError('literature_lead_original_inputs_not_received')
    source = store.require(value['source_ref'], {'source'})
    subject = store.require(value['subject_ref'], {'reference'})
    if subject['source_ref'] != value['source_ref'] or not subject.get('anchor'):
        raise ContractError('literature_lead_subject_not_anchored_in_source')
    uri = (source.get('uri') or '').split('?', 1)[0].rstrip('/')
    if uri.endswith(('/search', '/esearch.fcgi')):
        raise ContractError('literature_lead_requires_acquired_source_not_search_page')

    def read_source(ref, representation):
        if ref != value['source_ref']:
            raise ContractError('literature_lead_source_mismatch')
        artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
        if artifact is None:
            raise ContractError('literature_lead_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    witness = _Sources(read_source).witness(value['witness'], 'source_lead.witness')
    anchor = subject['anchor']
    if anchor['artifact_ref'] != witness['artifact_ref'] or not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']:
        raise ContractError('literature_lead_subject_outside_witness')
    return {'source_ref': value['source_ref'], 'disposition': value['disposition'],
            'proposed_annotation_ref': value['proposed_annotation_ref']}


def reason(store, scope, page_source_ref, arguments, operation_key, proposed_annotation_ref, authorize_source_access,
           read_cells=None):
    """One reasoning unit. ``arguments`` is the model's ``reason`` selection (commit, evidence_processing, and a
    source_lead for a verified-source-leads commission); ``authorize_source_access(ref, representation)`` raises a
    ``ContractError`` for a read outside the assigned source. Its outcome is the unit's outcome: an invalid or failed
    commit enters the iterator like any other outcome."""
    repository = LiteratureAssayGradingRepository(store, read_cells)
    selection = {'kind': 'reason', **{name: value for name, value in arguments.items() if name != 'source_lead'}}
    if 'source_lead' not in arguments:
        return execute(scope, page_source_ref, selection, operation_key, repository,
                       authorize_source_access=authorize_source_access)
    try:
        witness = arguments['source_lead']['witness']
        authorize_source_access(witness['source_ref'], witness['representation'])
        with store.transaction():
            result = execute(scope, page_source_ref, selection, operation_key, repository,
                             authorize_source_access=authorize_source_access)
            if result['status'] not in ('completed', 'partial'):
                return result
            return {**result, 'literature_source_lead': validate_lead(store, arguments['source_lead'], result,
                                                                      proposed_annotation_ref)}
    except (ContractError, ExperimentalContractError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}


def no_applicable_spans(outcomes, records):
    """The spans the Episode's own reasoning units declared, source-grounded, to hold no applicable experiment or
    result, with the artifact of the representation read."""
    spans = []
    for outcome in outcomes:
        if outcome['kind'] != 'tool' or outcome['tool'] != 'reason':
            continue
        processing = outcome['outcome'].get('evidence_processing')
        if processing is None or processing['kind'] != 'no_applicable_evidence':
            continue
        for witness in processing['examined']:
            source = records.get(witness['source_ref'])
            spans.append({**{key: witness[key] for key in ('source_ref', 'representation', 'start', 'end')},
                          'artifact_ref': source['artifact_ref' if witness['representation'] == 'original'
                                                 else 'text_ref']})
    return spans


def spans_cover(task, spans):
    """The old ``screening_answers`` test: the declared spans cover every span the screening task commissioned."""
    for requested in task['examined']:
        covered = requested['start']
        intervals = sorted((span['start'], span['end']) for span in spans
                           if (span['source_ref'], span['artifact_ref']) == (requested['source_ref'],
                                                                              requested['artifact_ref']))
        for start, end in intervals:
            if start <= covered:
                covered = max(covered, end)
        if covered < requested['end']:
            return False
    return True


def screening_covered(task, outcomes, spans):
    """Whether the commissioned screening spans are answered: by the Episode's own declarations, or by a child that
    returned them covered."""
    if task.get('answer_kind') != 'screening':
        return False
    if spans_cover(task, spans):
        return True
    return any(outcome['kind'] == 'child' and outcome['report']['screening_covered'] for outcome in outcomes)


def relevant_lead_sources(outcomes, proposed, records):
    """The latest disposition per source identity for the commissioned annotation, merged in unit order over the
    own validated leads and the relevant lead sources the children returned; the sources whose latest disposition is
    relevant."""
    normalizer, current = FindingIdentity(records), {}
    for outcome in outcomes:
        if outcome['kind'] == 'child':
            for ref in outcome['report']['lead_source_refs']:
                current[canonical(normalizer.source(ref))] = (ref, 'relevant')
        elif outcome['tool'] == 'reason' and 'literature_source_lead' in outcome['outcome']:
            lead = outcome['outcome']['literature_source_lead']
            if lead['proposed_annotation_ref'] == proposed:
                current[canonical(normalizer.source(lead['source_ref']))] = (lead['source_ref'], lead['disposition'])
    return [ref for ref, disposition in current.values() if disposition == 'relevant']


__all__ = ['REASON_DESCRIPTION', 'reason_schema', 'empty_commit', 'validate_lead', 'reason', 'no_applicable_spans',
           'spans_cover', 'screening_covered', 'relevant_lead_sources']
