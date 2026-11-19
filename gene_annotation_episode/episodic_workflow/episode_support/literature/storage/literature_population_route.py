"""The A106 population route of a literature episode: the population operations of the old catalogue
(``literature.*.populate`` and ``literature.a106.finalize``, by tool name the library name with the dots replaced),
the automatic A106 score judgment and the grader instructions, as library functions an episode calls with its own
pieces (its role, its goal, its unit context and the envelope its ``action`` built).

Carried from the old bindings' ``source_operations.py`` (``_population_catalog``, the population branch of
``execute`` and ``_tool_arguments``), ``grading/intervention_assessment.py`` and ``scoring/intervention_main_sheet.py``
of each A106 literature episode at ``97308b94c``. The repositories run over the custody-scoped store of the running
unit (``ctx.store``); what the old Store called "received" is what the Episode holds (``ctx.store.refs()``). The old
access guards against another episode's private receipts (``authorize_source_access``, ``authorize_record_access``)
are custody's: a record the Episode does not hold cannot be read.

The envelope (what ``action`` makes of a selection) carries ``arguments``, ``scope``, ``page_source_ref`` (``None``
for an episode that reads no assigned page: its readings are not confined to one source),
``assignment`` (with the ``page`` and the ``literature_task``) and ``proposed_annotation_ref``.

Which optional populations are offered is the episode's explicit setting ``literature_populations`` (a list of
``OPTIONAL_POPULATIONS`` names) with ``literature_evidence_origins`` (the evidence origin of each of ``ratio_source``,
``controlled_response`` and ``gel`` when offered); both are required settings.
"""
from dataclasses import replace

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_intervention_grading import (
    CRITERION_QUESTIONS, QUANTITY_KINDS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence.literature_assay_inputs import (
    materialize_text_witness_inputs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_intervention_storage import (
    OPERATION_DESCRIPTION as INTERVENTION_DESCRIPTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import (
    LiteratureContext, LiteratureRepositories, POPULATION_OWNERS, population_catalog, validate_populations)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_subscore_storage import (
    LiteratureA106SubscoreRepository)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope

# The population operations of the old catalogue by tool name.
POPULATION_NAMES = {name.replace('.', '_'): name for name in POPULATION_OWNERS}
OPEN = 'open_population'
JUDGMENT = 'literature_a106_score_judgment'

# The A106 graders (owner's texts): G1, the intervention grading sheet (``literature.a106.intervention_grading``, one
# sheet per experiment: the native intervention effect on one of the quantity kinds, its variance and the signed log
# evidence ratio of the assertion over a named alternative; diagnostics stay separate cells), its criteria and their
# questions; G2, the A106 final subscore (``literature.a106.finalize``: the subscore reader's TASK, which the goal
# carries); the automatic source-bound judgment that also writes G2; and the perturbation filling instructions
# (``PERTURBATION_TASK``, in the goal).
JUDGMENT_DESCRIPTION = (
    'Make the automatic A106 score judgment: for each question (proposed annotation and explicit alternative) of '
    'your current intervention grading sheets, the library prepares one source-bound judgment request from the '
    'current assessments and the model answers it as a calculation, not a decision about next actions; the '
    'answer is saved as the A106 final subscore, or stays unresolved with its reasons. Takes no arguments.')
GRADER_SECTION = (
    '\nA106 grading. Intervention grading sheet (tool literature_intervention_grading_populate, one sheet per '
    'original experiment): ' + INTERVENTION_DESCRIPTION + ' Quantity kinds: ' + ', '.join(QUANTITY_KINDS) + '. '
    'Criteria, each kept as its own interpretation with status supported, unknown or conflicting and anchored '
    'support_refs: ' + ' '.join(name + ': ' + question for name, question in CRITERION_QUESTIONS.items())
    + '\nA106 final subscore (tool literature_a106_finalize): combines the current intervention grading sheet of each '
    'original experiment of one question, as the goal states. ' + JUDGMENT_DESCRIPTION
    + '\nA population operation is used in two steps: open_population names it, and from then on it is offered with '
    'its full input schema until another one is opened.\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the A106 sheets '
                   'you saved and your investigations returned: for each current intervention grading sheet (G1) and '
                   'each current A106 final subscore (G2) its numbers, statuses, counts and record references; no '
                   'prose of yours is returned. Selecting a tool does not end your work: only the numerical '
                   'controller does.')

POPULATION_SOURCE_KEYS = {'source_ref', 'covariance_source_ref', 'activity_covariance_source_ref', 'model_source_ref',
                          'km_sheet_ref', 'data_source_ref', 'coordinate_source_ref', 'validation_source_ref'}
SHEET_REF_TOOLS = {'literature.intervention_grading.populate', 'literature.a106.finalize',
                   'literature.measurement_validation.populate', 'literature.assay.components.populate',
                   'literature.ion_discrimination.populate'}


def populations(settings):
    """The optional populations the episode offers and the evidence origin each origin-bearing one declares."""
    return validate_populations(settings['literature_populations'], settings['literature_evidence_origins'])


def population_entries(settings):
    """The population operations offered, by tool name (the old ``_population_catalog``, in its order)."""
    chosen, _ = populations(settings)
    return {entry['name'].replace('.', '_'): entry for entry in population_catalog(chosen)}


def opened_population(outcomes):
    """The population operation the latest completed ``open_population`` unit opened, or ``None``.

    The input schemas of all population operations together exceed what one model request may carry (about 1.1
    million characters against the provider's 1,048,576), so ``open_population`` names one and the decisions from
    then on offer it with its full input schema."""
    opened = [outcome['outcome']['opened_population'] for outcome in outcomes
              if outcome['kind'] == 'tool' and outcome['tool'] == OPEN]
    return opened[-1] if opened else None


def offered_population_tools(opened):
    """The population tools of a decision: ``open_population``, the opened operation, the score judgment."""
    return [OPEN] + ([opened] if opened is not None else []) + [JUDGMENT]


def population_tool_entry(name, settings):
    """The catalog entry of one population tool (``open_population``, the judgment, or a population operation)."""
    entries = population_entries(settings)
    if name == OPEN:
        return {'name': name,
                'description': ('Open one population operation: from the next decision on it is offered with its '
                                'full input schema. The operations: ' + ' '.join(
                                    key + ': ' + entry['description'] for key, entry in entries.items())),
                'input_schema': obj({'population': {'enum': list(entries)}})}
    if name == JUDGMENT:
        return {'name': name, 'description': JUDGMENT_DESCRIPTION, 'input_schema': obj({})}
    return {'name': name, 'description': entries[name]['description'],
            'input_schema': source_location_inputs(entries[name]['input_schema'])}


def open_population(envelope):
    """Open one population operation (see ``opened_population``). It reads and writes nothing."""
    return {'status': 'completed', 'opened_population': envelope['arguments']['population']}


def within_source(store, reference, root, scope):
    """Whether ``reference`` is ``root`` or a source derived from it through ``parent_source_refs`` (the old
    ``_within_source``; each source on the way is read in scope)."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        source = read_record_in_scope(store, current, scope, 'source')
        pending.extend(source.get('parent_source_refs', ()))
    return False


def population_sources(name, arguments):
    """The sources a population operation's arguments name (the old ``sources`` of ``_tool_arguments``): each must be
    inside the assigned page's source."""
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == 'metadata_source_ref' and isinstance(child, str):
                    yield child
                    continue
                if (key == 'sheet_ref' and name in SHEET_REF_TOOLS
                        or key == 'original_source_ref' and name == 'literature.binding.interaction.populate'
                        or key in POPULATION_SOURCE_KEYS) and isinstance(child, str):
                    yield child
                elif key == 'covariance_source_refs' and name == 'literature.measurement_comparison.populate':
                    yield from child
                else:
                    yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
        elif isinstance(value, str) and (value in arguments.get('visual_source_refs', ())
                                         or value in arguments.get('covariance_source_refs', ())):
            yield value
    return set(walk(arguments))


def admit_population(store, name, arguments, scope, root, settings):
    """The population branch of the old ``_tool_arguments``: the arguments against the offered schema, and every
    source they name inside the assigned page's source when there is one. A violation is a ``ContractError``."""
    validate_schema(arguments, source_location_inputs(population_entries(settings)[name.replace('.', '_')]
                                                      ['input_schema']))
    if root is not None and any(not within_source(store, ref, root, scope)
                                for ref in population_sources(name, arguments)):
        raise ContractError('literature_reading_outside_assigned_source')


def literature_context(ctx, envelope, role, goal):
    """The context the library repositories read: the Episode's identity (the system's), its role and path, the
    commission and the records it holds now."""
    return LiteratureContext(
        run_id=ctx.run_id, episode_id=ctx.episode_id, role=role, path=tuple(ctx.binding_path.split('/')),
        scope=envelope['scope'], assignment=envelope['assignment'], request={'goal': goal, 'scope': envelope['scope']},
        received_record_refs=tuple(ctx.store.refs()))


def repositories(ctx):
    """The A106 sheet repositories over the custody store, for the populations the episode offers."""
    chosen, origins = populations(ctx.settings)
    return LiteratureRepositories(ctx.store, ctx.run_id, chosen, origins)


def invalid_outcome(ctx, name, arguments, error):
    """The old invalid outcome of ``execute``: a contract error is returned as ``arguments_or_reference`` feedback;
    the detail is kept for the contract errors the old code kept it for."""
    detail = getattr(error, 'detail', None)
    keep = detail is not None and (
        isinstance(error, ExperimentalContractError) and error.code == 'source_quote_mismatch'
        or isinstance(error, ContractError) and str(error) in {
            'representation_error', 'a106_revision_question_mismatch',
            'a106_existing_assessment_requires_null_missing_reason'}
        or isinstance(error, ContractError) and name == 'literature.intervention_grading.populate'
        and (str(error) == 'assay_grading_anchored_support_required'
             or str(error) == 'intervention_latest_revision_required' and bool(detail)))
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': getattr(error, 'code', str(error)),
                         'field': getattr(error, 'field', None), **({'detail': detail} if keep else {})}}


def populate(name, envelope, ctx, role, goal):
    """The old population branch of ``execute`` for the population tool ``name`` (library name): the arguments
    admitted, their text witnesses materialized from the actual source bytes, then the repository that owns the
    operation populates and saves its sheet. A contract error is an ``invalid`` outcome that enters the iterator."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    store = ctx.store
    context = literature_context(ctx, envelope, role, goal)
    owned = repositories(ctx)
    try:
        admit_population(store, name, arguments, scope, root, ctx.settings)
        owner = owned.owner(name, arguments)

        def read_source(ref, representation):
            source = owner._native_source(context, ref)
            if root is not None and not within_source(store, ref, root, scope):
                raise ContractError('literature_reading_outside_assigned_source')
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
        materialized = materialize_text_witness_inputs(arguments, read_source=read_source)
        return owned.populate(context, name, materialized, ctx.operation_key)
    except (ContractError, ExperimentalContractError) as error:
        return invalid_outcome(ctx, name, arguments, error)


async def score_judgment(envelope, ctx, role, goal):
    """The automatic A106 score judgment (old ``scoring/intervention_main_sheet.py``: ``automatic_score_judgments``
    and ``complete_score_judgment``): the subscore repository prepares one source-bound judgment request per question
    of the current intervention assessments; the model answers each through ``ctx.model`` (recorded and replayed
    under the unit) and the repository validates and saves the answer as the A106 final subscore, or keeps it
    unresolved with its reasons. A judgment is a calculation, not a decision about next actions; a request already
    completed keeps its outcome. The outcome lists one outcome per judgment."""
    # The judgment is made for the commissioned A106 question: the repository reads the axis and the proposed
    # annotation of the commission (the old head commission held them as ``selection.evidence_axis.option_id`` and
    # ``proposed_annotation_ref``).
    context = literature_context(ctx, envelope, role, goal)
    task = envelope['assignment']['literature_task']
    context = replace(context, assignment={**context.assignment,
                                           'selection': {'evidence_axis': {'option_id': task['evidence_axis']}},
                                           'proposed_annotation_ref': envelope['proposed_annotation_ref']})
    repository = LiteratureA106SubscoreRepository(ctx.store, ctx.run_id)
    outcomes = []
    for request in repository.prepare_judgments(context):
        if 'completed_outcome' in request:
            outcomes.append(request['completed_outcome'])
            continue
        schema = request['output_schema']
        response = await ctx.model.complete('REASONING', request['instructions'], request['context'],
                                            generation_schema(schema))
        outcomes.append(repository.complete_judgment(context, request['judgment_ref'],
                                                     decode_response(response, schema),
                                                     provenance={'model_role': 'REASONING',
                                                                 'operation_key': ctx.operation_key}))
    return {'status': 'completed' if outcomes else 'unavailable', 'judgments': outcomes,
            'record_refs': [ref for outcome in outcomes for ref in outcome['record_refs']]}
