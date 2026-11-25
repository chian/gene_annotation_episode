"""The task of the organism identification head: one request the model fills, one check, one library function that runs
and grades.

Every decision the model chooses one classification: a DNA sequence of the scope, an index and a local resource
(``kraken2_classify``, the program Kraken 2). Code checks the request before anything runs
(``check_kraken2_request``): a request with something to fix is rejected with the things to fix and no unit is made. A
request that passed runs as one unit by the library's one function (``kraken2_classification``): run, grade, keep. Grading
is not a choice of anyone.

The model is the router: it chooses which index to ask next from what the classifications held so far show (the
candidate taxa, their scores, what each index holds). It never ends the episode: the forecast yield controller does, when
no classification left is worth its cost. The service ``job_access`` is read for the bound resources a tool may name.

Settings: ``kraken2_indexes`` (index name to the path of its manifest: name, version, directory, what it contains, the top
taxa it holds, and its files) and ``kraken2_executable_directory`` (the directory that holds the ``kraken2`` program)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.tools.taxonomic_classification.kraken2_classification import (
    QUERY_MOLECULES, check_kraken2_request, kraken2_classification)

from .credit import KRAKEN2_TOOL, index_manifests, made
from .goal import GOAL

HEAD = 'organism_identification'
CHILD_SLOTS = {}
SERVICES = ('job_access',)

INSTRUCTIONS = """You are finding out which organism a piece of DNA is from. Nothing about the DNA is known beforehand: it can be from a virus, a bacterium, an archaeon or something else.

Each step you choose one classification, as `selection`: the tool `kraken2_classify` with a `query_ref` (a DNA sequence of your scope), an `index` and a `resource_id` (a local resource of `bound_resources`).

What you are shown:
- `indexes`: the indexes you can ask, each with what it contains. An index says what it holds and nothing of what it does not hold: an index of viruses only cannot tell you the DNA is bacterial, and a few k-mers shared with something it holds are not an identification.
- `held_classifications`: the classifications already made. The same sequence against the same index is refused as a repeat.
- `candidates`: the candidate taxa found so far for each sequence, the leading one first, each with its score. A candidate's score is the support on its own lineage, so a call at a vaguer level (a family) supports every finer candidate inside it. A taxon and its ancestor are not rivals; rivals are calls that are not nested. `leader_taxon_id`, `rival_taxon_id` and `agreed_taxon_id` (the deepest taxon the leader and its rival share) say how far the placement is settled.
- `action_yields`: what each offered action is forecast to earn against its cost. You do not set these numbers and you do not end the episode; it ends when nothing left is worth its cost.

Choose the classification that will tell you most given what is known. Answer with the selection only."""

DESCRIPTIONS = {
    KRAKEN2_TOOL: ('Classify one DNA sequence of your scope against one Kraken 2 index on a local resource. Kraken 2 looks '
                   'up every k-mer of the sequence in the index and reads the taxon the index holds for it (the lowest '
                   'common ancestor of the genomes that contain that k-mer). What comes back, graded in the same unit: for '
                   'each taxon with k-mers of its own, the share of the sequence\'s k-mers it holds; each such taxon is a '
                   'candidate. A sequence with no k-mer in the index comes back with no taxon: the index was asked and '
                   'holds nothing like it. Fill the three fields: query_ref, index, resource_id. Code checks the request '
                   'before it runs; if something is wrong it comes back in feedback with the things to fix and nothing was '
                   'run.'),
}


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind, which a tool may name (read through the service's read
    handle, so the read is recorded with the decision)."""
    access = ctx.services['job_access']
    return {resource['resource_id']: resource['kind'] for resource in access.read('resources')}


def kraken2_options(summary, resources, indexes):
    """The request of the ``kraken2_classify`` tool, as the model fills it out: each field from a fixed set (the held DNA
    sequences of the scope, the configured indexes, the bound resources). Whether the filled request can run is decided by
    ``check_kraken2_request`` in ``action``. Not offered while no index is configured, the scope holds no DNA sequence or
    no resource is bound."""
    held = [ref for ref in summary['scope']['subject_refs'] if summary['held_sequences'].get(ref) in QUERY_MOLECULES]
    if not indexes or not held or not resources:
        return []
    return [obj({'kind': {'const': 'tool'}, 'tool': {'const': KRAKEN2_TOOL},
                 'arguments': obj({'query_ref': {'enum': held}, 'index': {'enum': list(indexes)},
                                   'resource_id': {'enum': list(resources)}})})]


def selection_schema(summary, resources, indexes):
    """What the model answers with: one classification."""
    return obj({'selection': {'anyOf': kraken2_options(summary, resources, indexes)}})


def offered_actions(summary, ctx):
    """The action types this decision offers, by the names a unit is recorded under (``ToolCall.name``):
    ``kraken2_classify`` while its option is offered."""
    return [KRAKEN2_TOOL] if kraken2_options(summary, bound_resources(ctx), index_manifests(ctx)) else []


def index_view(manifests):
    """What the model is shown of each index: its name, version, what it contains and the top taxa it holds."""
    return [{'index': name, 'version': manifest['version'], 'contains': manifest['contains'],
             'covers_taxon_ids': manifest['covers_taxon_ids']} for name, manifest in manifests.items()]


def decide(summary, feedback, ctx):
    """Ask the model for the next classification, shown the scope's sequences, the indexes, the classifications held,
    the candidate taxa, its own outcomes, the measured time and the yield table."""
    resources, manifests = bound_resources(ctx), index_manifests(ctx)
    context = {
        'goal': GOAL, 'scope': summary['scope'],
        'held_sequences': [{'record_ref': ref, 'molecule': molecule, 'length': summary['sequence_lengths'][ref]}
                           for ref, molecule in summary['held_sequences'].items()],
        'indexes': index_view(manifests), 'bound_resources': resources,
        'held_classifications': summary['held_classifications'],
        'candidates': summary['target_findings'], 'tests': summary['tests'], 'differentials': summary['differentials'],
        'credit_binding': summary['credit_binding'],
        'own_outcomes': summary['units'], 'last_local_outcome': summary['last_local_outcome'],
        'tools': [{'name': KRAKEN2_TOOL, 'description': DESCRIPTIONS[KRAKEN2_TOOL]}],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', INSTRUCTIONS, context,
                        generation_schema(selection_schema(summary, resources, manifests)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit): an answer that does not fit the schema, or a
    classification request the check finds something to fix in (rejected with the things to fix)."""
    resources = bound_resources(ctx)
    schema = selection_schema(summary, resources, index_manifests(ctx))
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('organism_identification_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        problems = check_kraken2_request(
            selection['arguments'], sequences=summary['held_sequences'],
            scope_subjects=summary['scope']['subject_refs'], resources=resources, made=made(summary))
        if problems:
            raise Rejected({'status': 'invalid', 'category': 'kraken2_classify_request',
                            'detail': {'request': selection['arguments'], 'fix': problems}})
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    return ToolCall(KRAKEN2_TOOL, dict(selection['arguments']))


async def kraken2_classify(arguments, ctx):
    """One classification as one unit: run and grade, by the library's one function. The arguments are the model's three
    controlled choices; the index's manifest and the program's directory are settings."""
    return await kraken2_classification(
        ctx, query_ref=arguments['query_ref'], index=arguments['index'], resource_id=arguments['resource_id'],
        executable_directory=ctx.settings['kraken2_executable_directory'],
        manifest_path=ctx.settings['kraken2_indexes'][arguments['index']])


TOOLS = {KRAKEN2_TOOL: kraken2_classify}
