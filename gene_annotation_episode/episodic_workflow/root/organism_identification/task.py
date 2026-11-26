"""The task of the organism identification head: one request the model fills, one check, one library function that runs
and grades.

Every decision the model chooses one run on one DNA sequence of the scope, on a local resource:

* ``kraken2_classify`` (the program Kraken 2): the sequence's k-mers against one index.
* ``genomad_classify`` (the program geNomad): what kind of DNA the sequence is, and a virus taxonomy from its genes.
* ``vitap_assign`` (the program VITAP): the virus lineage the sequence's proteins support.

Code checks the request before anything runs (the library's check of that tool): a request with something to fix is
rejected with the things to fix and no unit is made. A request that passed runs as one unit by the library's one function
of that tool: run, grade, keep. Grading is not a choice of anyone.

The model is the router: it chooses what to ask next from what the runs held so far show (the candidate taxa, their scores,
the taxon claims passed in that wait for a candidate, what each tool and database can speak of, what each costs). It never
ends the episode: the forecast yield controller does, when no run left is worth its cost. The service ``job_access`` is read for the bound resources a tool may name.

Settings: ``kraken2_indexes`` (index name to the path of its manifest) and ``kraken2_executable_directory``;
``genomad_database`` (the path of its database's manifest), ``genomad_environment_directory`` and ``genomad_splits``;
``vitap_database`` and ``vitap_environment_directory``; ``taxonomy`` (the path of the prepared NCBI taxonomy's manifest,
which turns the names geNomad and VITAP report into taxon ids). A tool whose settings are absent is not offered."""
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
from gene_annotation_episode.episodic_workflow.episode_support.tools.taxonomic_classification.genomad_classification import (
    check_genomad_request, genomad_classification)
from gene_annotation_episode.episodic_workflow.episode_support.tools.taxonomic_classification.kraken2_classification import (
    check_kraken2_request, kraken2_classification)
from gene_annotation_episode.episodic_workflow.episode_support.tools.taxonomic_classification.vitap_assignment import (
    check_vitap_request, vitap_assignment)

from .credit import (GENOMAD_TOOL, KRAKEN2_TOOL, ONCE_TOOLS, VITAP_TOOL, database_manifest, dna_subjects, index_manifests,
                     made)
from .goal import GOAL

HEAD = 'organism_identification'
CHILD_SLOTS = {}
SERVICES = ('job_access',)
CHECKS = {KRAKEN2_TOOL: check_kraken2_request, GENOMAD_TOOL: check_genomad_request, VITAP_TOOL: check_vitap_request}

INSTRUCTIONS = """You are finding out which organism a piece of DNA is from. Nothing about the DNA is known beforehand: it can be from a virus, a bacterium, an archaeon or something else, and it can be close to a known genome or far from every one.

Each step you choose one run, as `selection`: one of the `tools`, with a `query_ref` (a DNA sequence of your scope), a `resource_id` (a local resource of `bound_resources`) and, for `kraken2_classify`, an `index`.

What you are shown:
- `tools`: what each tool measures, what it can speak of, and about how long it takes. No tool works at every distance. Exact k-mers name the species of a sequence that has a close relative in the index and say nothing of a distant one. The tools that work from the sequence's genes reach distant viruses but stop at family or above, and take minutes.
- `indexes` and `databases`: what each holds. A tool says what its database holds and nothing of what it does not hold: an index of viruses only cannot tell you the DNA is bacterial, and a virus classifier gives a virus lineage with a low score to a piece of a cell that carries a few virus-like genes.
- `held_runs`: the runs already made. The same run again is refused as a repeat.
- `candidates`: the candidate taxa found so far for each sequence, the leading one first, each with its score. A candidate's score is the support on its own lineage, so a call at a vaguer level (a family, or just "virus") supports every finer candidate inside it. A taxon and its ancestor are not rivals; rivals are calls that are not nested. `leader_taxon_id`, `rival_taxon_id` and `agreed_taxon_id` (the deepest taxon the leader and its rival share) say how far the placement is settled.
- `waiting_claims` (in each sequence's `candidates` row): taxa named by the hits of a database search you were given, which no candidate is or lies inside. A claim never makes a candidate; it adds to the score of the candidates it includes. `finer_than_its_candidate`: it agrees with the listed candidate `consistent_taxon_id` and is finer, so a run that can name taxa at that depth may confirm it. `no_candidate_on_its_lineage`: it disagrees with what is listed, or nothing is listed yet. `taxon_not_in_taxonomy`: its taxon is outside the prepared taxonomy and cannot be placed.
- `action_yields`: what each offered action is forecast to earn against its cost in time. You do not set these numbers and you do not end the episode; it ends when nothing left is worth its cost.

Choose the run that will tell you most for its cost given what is known: when the quick runs have found nothing, the slower ones are what can still place the DNA; when they have found a close relative, a slower run is worth it only for what it adds. Answer with the selection only."""

DESCRIPTIONS = {
    KRAKEN2_TOOL: ('Kraken 2: classify the sequence against one index of k-mers. It looks up every k-mer of the sequence in '
                   'the index and reads the taxon the index holds for it (the lowest common ancestor of the genomes that '
                   'contain that k-mer). Each taxon with k-mers of its own is a candidate, with the share of the sequence\'s '
                   'k-mers it holds. It names the species of a sequence that has a close relative in the index, from a few '
                   'hundred letters; a sequence with no close relative comes back with no taxon. Seconds to half a minute. '
                   'Fields: query_ref, index, resource_id.'),
    GENOMAD_TOOL: ('geNomad: what kind of DNA the sequence is (three scores that sum to 1: chromosome, plasmid, virus; a '
                   'chromosome or plasmid is of a cell), and, from the genes that match its marker database, a virus '
                   'taxonomy down to family at most. It reaches viruses that share no k-mers with a known genome. It never '
                   'names a genus or species and has no taxonomy of cells. Several minutes: its search first builds a table '
                   'of its whole database. Fields: query_ref, resource_id.'),
    VITAP_TOOL: ('VITAP: the virus lineage the sequence\'s proteins support, from an alignment of them to the proteins of '
                 'the viruses of its database, with a score for the lineage it settles on and for each other lineage it '
                 'considered. It reaches distant viruses, usually to family or class. It is a classifier of viruses only: it '
                 'gives a virus lineage, with a low score, to a piece of a cell that carries a few virus-like genes. A few '
                 'minutes. Fields: query_ref, resource_id.'),
}


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind, which a tool may name (read through the service's read
    handle, so the read is recorded with the decision)."""
    access = ctx.services['job_access']
    return {resource['resource_id']: resource['kind'] for resource in access.read('resources')}


def configured(ctx):
    """What the run's settings offer: the Kraken 2 index manifests by name, and the database manifest of each tool that
    runs once for a sequence (absent when its settings are)."""
    return {'indexes': index_manifests(ctx),
            'databases': {tool: manifest for tool in ONCE_TOOLS
                          if (manifest := database_manifest(ctx, tool)) is not None and 'taxonomy' in ctx.settings}}


def options(summary, resources, offered):
    """The requests the model can fill, one per offered tool: each field from a fixed set (the DNA sequences of the scope,
    the configured indexes, the bound resources). Whether a filled request can run is decided by the tool's check in
    ``action``. A tool is not offered while the scope holds no DNA sequence, no resource is bound or its settings are
    absent."""
    held = dna_subjects(summary)
    if not held or not resources:
        return []
    found = []
    if offered['indexes']:
        found.append(obj({'kind': {'const': 'tool'}, 'tool': {'const': KRAKEN2_TOOL},
                          'arguments': obj({'query_ref': {'enum': held}, 'index': {'enum': list(offered['indexes'])},
                                            'resource_id': {'enum': list(resources)}})}))
    found.extend(obj({'kind': {'const': 'tool'}, 'tool': {'const': tool},
                      'arguments': obj({'query_ref': {'enum': held}, 'resource_id': {'enum': list(resources)}})})
                 for tool in offered['databases'])
    return found


def selection_schema(summary, resources, offered):
    """What the model answers with: one run of one tool."""
    return obj({'selection': {'anyOf': options(summary, resources, offered)}})


def offered_actions(summary, ctx):
    """The action types this decision offers, by the names a unit is recorded under (``ToolCall.name``): each tool whose
    option is offered."""
    return [option['properties']['tool']['const'] for option in options(summary, bound_resources(ctx), configured(ctx))]


def decide(summary, feedback, ctx):
    """Ask the model for the next run, shown the scope's sequences, the tools with their indexes and databases, the runs
    held, the candidate taxa with the waiting taxon claims of each sequence, its own outcomes, the measured time and the
    yield table."""
    resources, offered = bound_resources(ctx), configured(ctx)
    names = [option['properties']['tool']['const'] for option in options(summary, resources, offered)]
    context = {
        'goal': GOAL, 'scope': summary['scope'],
        'held_sequences': [{'record_ref': ref, 'molecule': molecule, 'length': summary['sequence_lengths'][ref]}
                           for ref, molecule in summary['held_sequences'].items()],
        'indexes': [{'index': name, 'version': manifest['version'], 'contains': manifest['contains'],
                     'covers_taxon_ids': manifest['covers_taxon_ids']} for name, manifest in offered['indexes'].items()],
        'databases': [{'tool': tool, 'database': manifest['name'], 'version': manifest['version'],
                       'contains': manifest['contains']} for tool, manifest in offered['databases'].items()],
        'bound_resources': resources, 'held_runs': summary['held_runs'],
        'candidates': summary['target_findings'], 'tests': summary['tests'], 'differentials': summary['differentials'],
        'credit_binding': summary['credit_binding'],
        'own_outcomes': summary['units'], 'last_local_outcome': summary['last_local_outcome'],
        'tools': [{'name': name, 'description': DESCRIPTIONS[name]} for name in names],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', INSTRUCTIONS, context,
                        generation_schema(selection_schema(summary, resources, offered)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit): an answer that does not fit the schema, or a
    request the tool's check finds something to fix in (rejected with the things to fix)."""
    resources = bound_resources(ctx)
    schema = selection_schema(summary, resources, configured(ctx))
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('organism_identification_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        tool = selection['tool']
        problems = CHECKS[tool](selection['arguments'], sequences=summary['held_sequences'],
                                scope_subjects=summary['scope']['subject_refs'], resources=resources,
                                made=made(summary, tool))
        if problems:
            raise Rejected({'status': 'invalid', 'category': tool + '_request',
                            'detail': {'request': selection['arguments'], 'fix': problems}})
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    return ToolCall(tool, dict(selection['arguments']))


async def kraken2_classify(arguments, ctx):
    """One Kraken 2 classification as one unit: run and grade, by the library's one function. The arguments are the
    model's three controlled choices; the index's manifest and the program's directory are settings."""
    return await kraken2_classification(
        ctx, query_ref=arguments['query_ref'], index=arguments['index'], resource_id=arguments['resource_id'],
        executable_directory=ctx.settings['kraken2_executable_directory'],
        manifest_path=ctx.settings['kraken2_indexes'][arguments['index']])


async def genomad_classify(arguments, ctx):
    """One geNomad run as one unit: run and grade, by the library's one function."""
    return await genomad_classification(
        ctx, query_ref=arguments['query_ref'], resource_id=arguments['resource_id'],
        environment_directory=ctx.settings['genomad_environment_directory'],
        database_manifest_path=ctx.settings['genomad_database'], taxonomy_manifest_path=ctx.settings['taxonomy'],
        splits=ctx.settings['genomad_splits'])


async def vitap_assign(arguments, ctx):
    """One VITAP assignment as one unit: run and grade, by the library's one function."""
    return await vitap_assignment(
        ctx, query_ref=arguments['query_ref'], resource_id=arguments['resource_id'],
        environment_directory=ctx.settings['vitap_environment_directory'],
        database_manifest_path=ctx.settings['vitap_database'], taxonomy_manifest_path=ctx.settings['taxonomy'])


TOOLS = {KRAKEN2_TOOL: kraken2_classify, GENOMAD_TOOL: genomad_classify, VITAP_TOOL: vitap_assign}
