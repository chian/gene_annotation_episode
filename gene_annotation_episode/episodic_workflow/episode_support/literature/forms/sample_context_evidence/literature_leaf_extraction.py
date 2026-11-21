"""The A108 leaf extraction: the one extraction action over one item (a window of a source's text) that the leaf
episodes ``passage_evidence_extraction`` (chunk), ``table_evidence_extraction`` (table) and ``source_coverage_improvement``
(report: its windows in order) each call from their own ``task.py``, ``credit.py`` and ``messages/internal_summary.py``
with their own pieces (what the text is called, their goal text, their credit definition).

The leaf receives its item and shows the model the item as segments with their exact UTF-8 byte offsets in the artifact of
the source's representation (code cuts the segments; the model has no tool to read, locate or look around), and asks it once
per item for the axis's own extraction form: the typed commit (source subjects, contexts, observations and assessments, each
with its exact source anchor) together with its ``evidence_processing`` (the purpose-specific grading whose subscoring sheet
is saved in the same unit, or the source-grounded ``no_applicable_evidence`` declaration) and the source lead of the
verified-source-leads commission. ``AGENTS.md`` ("Required literature evidence processing"): an interpretation with
scientific rows is never held without its saved sheet. The one action is ``extract``: there is no reasoning commit that
assesses anything on its own, no population tool and no access tool. An item that has been extracted is done (nano-graphrag's
processed chunk), whatever the unit's outcome was: it is never offered again.

``extraction_call`` checks the answer against the form (an answer that is not in the form is rejected before any unit exists
and ``decide`` asks again with the reason); ``extract`` is the unit: the library's required-grading ``execute`` on the
custody-scoped store and, with the source lead, the validated lead in the same transaction. A returned invalid or failed
outcome is the unit's outcome like any other."""
import re
from dataclasses import dataclass

from jsonschema import ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.forms.sample_context_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.sample_context_evidence import (
    literature_required_grading as required_grading)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_grading_inputs import (
    grading_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.sample_context_evidence.literature_assay_inputs import (
    _Sources, _witness_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    _GRADER_TABLE)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sample_context_evidence.literature_investigation_prompt import (
    REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    LiteratureA108GradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import (
    time_accounting, yield_table)
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    REF, identity, obj, source_location_inputs, validate_schema)

ARTIFACT_FIELD = {'original': 'artifact_ref', 'text': 'text_ref', 'stdout': 'stdout_ref', 'stderr': 'stderr_ref'}
FACT_KINDS = ('reference', 'term', 'context', 'observation', 'hypothesis', 'assessment')
ACTION = 'extract'

READING = ('You are shown one {text} of one source, cut into segments, each with its exact half-open UTF-8 byte interval '
           '[start, end) in the source representation named in {text}. The {text} is the one item you extract; nothing '
           'else of the source is read, and nothing outside it is offered. Report what the {text} reports for the assigned '
           'question: the actual biological subject, organism, strain, sample and conditions, the scope of the finding and '
           'its qualifications; separate a reported observation from an author inference, a prediction and a repeated '
           'annotation. A source anchor or a witness selects the source (and its artifact or representation) and the '
           'interval taken from the segments shown; the host reads and stores the exact quotation. You select the '
           'segments and their contextual meaning; you give no quotation. Every anchor lies in the {text}.\n'
           'You answer once for this {text} with one extract action: the typed commit of what the {text} reports and, '
           'with it, its evidence_processing (the grading of each relevant observation, saved in this same action, or the '
           'source-grounded no_applicable_evidence declaration when the {text} contains no applicable contextual '
           'observation). Missing quantities, controls or organism/strain/sample links are unresolved inputs to the '
           'grader, never a reason to skip it or to invent a value. Do not manufacture target support.')
GRADER_GUIDANCE = '\nGraders (the grader_type of a grading):\n'
LEAD_GUIDANCE = ('\nThe verified_source_leads commission: the extract action also carries source_lead, the inspected '
                 'source, its anchored reference subject, whether it is a useful lead for the original question and the '
                 'exact witnessed byte interval. A title alone verifies nothing.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the counts code reads from the A108 sheets you saved, '
                   'with their references; nothing you write in prose is returned. The {text} is done once you have '
                   'answered for it.')


@dataclass(frozen=True)
class LibraryCallContext:
    """The values the A108 grading repository and the required-grading ``execute`` read from their ``context`` argument
    (``scope``, ``run_id``, ``episode_id``, ``role``, ``received_record_refs``, ``assignment``), named as they are read there:
    the assignment is the leaf's reading assignment (its ``page`` bounds the sources the repository reads; the requested
    components it carries are the cells saved with the sheet). A plain value: no behaviour and no recording."""
    scope: dict
    run_id: str
    episode_id: str
    role: str
    received_record_refs: tuple
    assignment: dict


def extraction_instructions(*, text, goal):
    """The instruction text: the leaf's goal, how the {text} is shown, the reasoning-commit requirement, the grading
    instructions of the axis with the grader table, the lead and the return."""
    return (goal + '\n\n' + READING.format(text=text) + '\n' + REASONING_COMMIT_REQUIREMENT + GRADING_INSTRUCTIONS
            + GRADER_GUIDANCE + _GRADER_TABLE + LEAD_GUIDANCE + RETURN_GUIDANCE.format(text=text))


def lead_schema():
    """The source lead the extraction also carries (the commission is the verified source leads)."""
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'},
                'source_ref': {**REF, 'x-reference-namespace': 'source'},
                'subject_ref': {**REF, 'x-reference-namespace': 'reference'},
                'disposition': {'enum': ['relevant', 'not_relevant'],
                                'description': 'Whether the inspected source is a useful lead for this commissioned '
                                               'question. This is not evidence supporting or opposing the proposed '
                                               'annotation.'},
                'relevance_rationale': {'type': 'string', 'minLength': 1,
                                        'description': 'Explain the specific connection between the witnessed source '
                                                       'subject/result and the original question; a search hit or '
                                                       'matching title alone is not verification.'},
                'witness': _witness_schema()})


def extract_schema(commit_schema):
    """The extraction form: the required-grading action (the typed commit with its ``evidence_processing``) and the
    source lead, every input projected through ``source_location_inputs``."""
    schema = required_grading.action_schema(commit_schema, source_location_inputs(grading_population_schema()))
    schema['properties']['source_lead'] = lead_schema()
    return source_location_inputs(schema)


def selection_schema(commit_schema):
    """What the model answers with: the one extract action and its arguments."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': ACTION},
                                             'arguments': extract_schema(commit_schema)})]}})


def representation_content(records, source_ref, representation):
    """The bytes of the artifact of ``representation`` of the source, read through the custody reader."""
    artifact = records.get(source_ref).get(ARTIFACT_FIELD[representation])
    if artifact is None:
        raise LookupError('literature_source_representation_unavailable:' + representation)
    return records.get_artifact(artifact)


def window_segments(content, start, end):
    """The segments of ``content[start:end]``, each ``{'start', 'end', 'text'}`` with its absolute byte interval: cut at a
    line end or after a sentence-ending mark, blank space trimmed. Pure code; the model chooses among them."""
    window = content[start:end]
    segments, cursor = [], 0
    cuts = [match.end() for match in re.finditer(rb'[.!?]["\')\]]*(?:\s+|$)|\n+', window)]
    for cut in [*cuts, len(window)]:
        piece = window[cursor:cut]
        stripped = piece.strip()
        if stripped:
            first = start + cursor + len(piece) - len(piece.lstrip())
            segments.append({'start': first, 'end': first + len(stripped),
                             'text': stripped.decode('utf-8', 'replace')})
        cursor = cut
    return segments


def completed(outcome):
    return isinstance(outcome, dict) and outcome.get('status') in ('completed', 'partial')


def received_fact_display(records):
    """The held records of the display kinds (the claim, the target context, the references: what the model refers to)."""
    shown = {}
    for reference in records.refs():
        kind = next((kind for kind in FACT_KINDS if reference.startswith(kind + '_')), None)
        if kind is None:
            continue
        record = records.get(reference)
        if record.get('id') != reference or record.get('record_type') != kind:
            raise ValueError('literature_received_fact_display_record_mismatch')
        shown[reference] = record
    return {'records': shown, 'received_refs': sorted(records.refs())}


def graded_assessments(records, reasons):
    """The current retained assessments the extractions committed (each with its grading sheet), by reference; their typed
    ``investigation_finding`` stays in the record."""
    found = []
    for outcome in reasons:
        for ref in outcome['record_refs']:
            record = records.get(ref)
            if (record['record_type'] == 'assessment' and record['investigation_finding']['status'] == 'retained'
                    and records.is_current(ref)):
                found.append(ref)
    return list(dict.fromkeys(found))


def extraction_state(view, spans):
    """Where the extraction stands, from the loop's view: the commissioned windows ``spans`` in order, each consumed by one
    extract unit (whatever its outcome), the next one shown as segments, the credit definition inputs, the held records and
    the extractions' outcomes. The leaf's own ``internal_summary`` adds what is its own (credit definition, leads, cells)."""
    parent = view.parent_input
    page, records = parent['page'], view.records
    extracted = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == ACTION]
    reasons = [outcome['outcome'] for outcome in extracted if completed(outcome['outcome'])]
    consumed, remaining = spans[:len(extracted)], spans[len(extracted):]
    item = None
    if remaining:
        window = remaining[0]
        content = representation_content(records, page['source_ref'], page['representation'])
        start, end = window['offset'], window['offset'] + window['limit']
        item = {'source_ref': page['source_ref'], 'representation': page['representation'],
                'artifact_ref': page['artifact_ref'], 'start': start, 'end': end,
                'segments': window_segments(content, start, end)}
    last = extracted[-1] if extracted else None
    return {
        'page': page, 'item': item, 'task': parent['task'], 'task_key': parent['task_key'],
        'literature_assignment': {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': spans},
                                  'literature_task': parent['task'],
                                  'proposed_annotation_ref': parent['proposed_annotation_ref']},
        'input_list': [[window['offset'], window['offset'] + window['limit']] for window in remaining],
        'consumed_inputs': [[window['offset'], window['offset'] + window['limit']] for window in consumed],
        'proposed_annotation_ref': parent['proposed_annotation_ref'], 'scope': parent['scope'],
        'received_record_refs': parent['received_record_refs'],
        'literature_received_fact_display': received_fact_display(records),
        'reasoning_schema': records.reasoning_schema(),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons if 'literature_source_lead' in outcome],
        'graded_assessments': graded_assessments(records, reasons),
    }


def extraction_request(summary, feedback, ctx, *, goal, text):
    """The model request: the one item (as segments), the claim and the records it may refer to, the credit definition, the
    findings so far, the measured time and the yield table. An empty input list is asked for no decision."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + text)
    context = {'goal': goal, 'scope': summary['scope'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
               'page': summary['page'], text: summary['item'], 'input_list': summary['input_list'],
               'consumed_inputs': summary['consumed_inputs'],
               'literature_received_fact_display': summary['literature_received_fact_display'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'current_findings': summary['finding'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    schema = selection_schema(summary['reasoning_schema'])
    return ModelRequest('REASONING', extraction_instructions(text=text, goal=goal), context, generation_schema(schema))


def empty_commit(commit, commit_schema):
    """Every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def extraction_call(response, summary):
    """Turn the model's answer into the one extract call, or reject it (no unit): an answer that is not in the form, or an
    empty commit that has neither the no-applicable-evidence declaration nor a source lead. The call carries the leaf's
    reading assignment (``literature_assignment``: the page, and the grading components the parent requested)."""
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(commit_schema)
    try:
        selection = decode_response(response, schema)
        validate_schema(selection, schema)
        arguments = selection['selection']['arguments']
        if (empty_commit(arguments['commit'], commit_schema)
                and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'
                and 'source_lead' not in arguments):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(ACTION, {'arguments': arguments, 'scope': summary['scope'],
                             'page_source_ref': summary['page']['source_ref'],
                             'proposed_annotation_ref': summary['proposed_annotation_ref'],
                             'assignment': summary['literature_assignment']})


def within_source(store, reference, root, scope):
    """Whether ``reference`` is ``root`` or a source derived from it through ``parent_source_refs`` (each source on the way
    is read in scope)."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(read_record_in_scope(store, current, scope, 'source').get('parent_source_refs', ()))
    return False


def resolve_aliases(value, aliases, reference_position=False):
    """The same-action aliases in the reference positions of a source lead."""
    if reference_position and isinstance(value, str) and value.startswith('@'):
        if value[1:] not in aliases:
            raise ContractError('required_grading_unresolved_alias', detail={'reference': value})
        return aliases[value[1:]]
    if isinstance(value, dict):
        return {key: resolve_aliases(child, aliases, key in ('ref', 'dependencies') or key.endswith('_ref')
                                     or key.endswith('_refs')) for key, child in value.items()}
    if isinstance(value, list):
        return [resolve_aliases(child, aliases, reference_position) for child in value]
    return value


def validate_source_lead(store, lead, outcome, proposed):
    """The lead's identity and exact source witness against the records the episode holds. A violation is a
    ``ContractError``."""
    value = plain(resolve_aliases(plain(lead), outcome.get('aliases', {})))
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    known = {*store.refs(), *outcome.get('record_refs', [])}
    if not {value['source_ref'], value['subject_ref'], proposed} <= known:
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
    if (anchor['artifact_ref'] != witness['artifact_ref']
            or not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']):
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}


def extract(arguments, ctx):
    """The unit: the typed commit and its grading in one action (``required_grading.execute``, which saves the subscoring
    sheet before any credit projection). With a source lead the commit, its grading and the validated lead are one
    transaction: a lead that does not hold returns an ``invalid`` outcome and nothing is committed. A source outside the
    page's source is a contract error and an ``invalid`` outcome."""
    envelope = arguments
    selection, scope, root = plain(envelope['arguments']), envelope['scope'], envelope['page_source_ref']
    store = ctx.store
    context = LibraryCallContext(scope=scope, run_id=ctx.run_id, episode_id=ctx.episode_id, role='literature_leaf',
                                 received_record_refs=tuple(store.refs()), assignment=plain(envelope['assignment']))
    repository = LiteratureA108GradingRepository(store)

    def authorize(ref, representation):
        if not within_source(store, ref, root, scope):
            raise ContractError('literature_reading_outside_assigned_source')
        repository.authorize_source_access(context, ref, representation, 'source.read')
    try:
        if 'source_lead' not in selection:
            return required_grading.execute(context, selection, ctx.operation_key, repository,
                                            authorize_source_access=authorize)
        witness = selection['source_lead']['witness']
        authorize(witness['source_ref'], witness['representation'])
        with store.transaction():
            native = {key: value for key, value in selection.items() if key != 'source_lead'}
            result = required_grading.execute(context, native, ctx.operation_key, repository,
                                              authorize_source_access=authorize)
            if result['status'] not in ('completed', 'partial'):
                return result
            lead = validate_source_lead(store, selection['source_lead'], result, envelope['proposed_annotation_ref'])
            return {**result, 'literature_source_lead': lead}
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        return {'status': 'invalid', 'operation_ref': identity('operation', {
            'key': ctx.operation_key, 'name': ACTION, 'arguments': selection}), 'record_refs': [],
            'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': getattr(error, 'code', str(error))}}
