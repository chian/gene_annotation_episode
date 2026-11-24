"""The task of the parts-discovery head: one unit per decision, three tools and no child yet.

THE FIRST PASS is OWED, in this order, without asking the model (``resume_action``, due at once; the system takes it as the unit, and
the forecast gate never refuses it): ``describe_piece``, then ``find_genes`` with the default genetic code (11), then
``find_rna_genes``. A unit counts as done once it was tried, whatever its outcome (a failed scan is reported once, not owed again).
``offered_actions`` lists the owed action while it is owed.

AFTER THE FIRST PASS the model is offered ``find_genes`` with a special code (4 or 25) not yet read, and only when the piece has at
least 20000 nt (a shorter piece is read by the pre-trained finder, which ignores the code). Each tool is a fixed workflow with ONE
deterministic check run in ``action`` before anything runs (SOP Step 3); a request that passes simply works, a repeat of a held
(tool, arguments) is refused with its fix list. With no code left to read ``find_genes`` is still the one offered action, with the
ceiling 0, which is how the yield controller ends the episode (``credit.ceiling``). The head never ends its episode: only the yield
controller does. No ``reason`` action.

Settings of the head: ``infernal_executable_directory`` (the directory of ``cmscan``), ``covariance_database_manifest`` (the path of
the Rfam manifest) and ``yield_bindings`` (``yield_estimator.py``). The service ``job_access`` is read for the resources
``find_rna_genes`` runs on (the first local one)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.gene_finding_sheet import (
    DEFAULT_CODE, SELF_TRAINED_MINIMUM)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import rejection_feedback
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.parts_discovery.describe_piece import (
    TOOL_NAME as DESCRIBE_TOOL, check_describe_piece_request, describe_piece)
from gene_annotation_episode.episodic_workflow.episode_support.tools.parts_discovery.find_genes import (
    TOOL_NAME as FIND_GENES_TOOL, check_find_genes_request, find_genes)
from gene_annotation_episode.episodic_workflow.episode_support.tools.parts_discovery.find_rna_genes import (
    TOOL_NAME as RNA_TOOL, check_find_rna_genes_request, find_rna_genes)

from .credit import held_codes, offered_codes, rna_scanned
from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access',)


def describe_piece_tool(arguments, ctx):
    """One description of the piece as one unit, by the library's one function."""
    return describe_piece(ctx, piece_ref=arguments['piece_ref'])


def find_genes_tool(arguments, ctx):
    """One gene finding under one genetic code as one unit, by the library's one function."""
    return find_genes(ctx, piece_ref=arguments['piece_ref'], code=arguments['code'])


async def find_rna_genes_tool(arguments, ctx):
    """One scan of the piece for RNA genes as one unit, by the library's one function (an async unit: its local job goes through the
    job service)."""
    return await find_rna_genes(ctx, piece_ref=arguments['piece_ref'], resource_id=arguments['resource_id'])


TOOLS = {DESCRIBE_TOOL: describe_piece_tool, FIND_GENES_TOOL: find_genes_tool, RNA_TOOL: find_rna_genes_tool}

INSTRUCTIONS = (
    GOAL + '\n\n'
    'You are the head of this investigation. At each decision you choose exactly one action, from the actions offered '
    '(tool_options), by answering with the controlled fields of its request; the configured yield controller owns continuation: '
    'you cannot end the episode. The first pass (a description of the piece, a gene finding under the default genetic code 11 and a '
    'scan for RNA genes) is done by code before your first decision. Recorded facts come from actual records and are shown to you as '
    'they are: the piece with its length, GC fraction and GC skew, the readings held (one per genetic code read: the finder\'s mode, '
    'the code, whether the code was applied, the gene count, the median gene length, the coding share, which is the nucleotides in '
    'the called genes over the length of the piece, and the score, which is the sum of the finder\'s own scores of the genes), the RNA '
    'scan, the leading parts, your earlier units and the yield table.')

CREDIT_TEXT = ('Your credit counts the score of the reading: the highest score of the readings of the protein genes held, plus the '
               'bit scores of the RNA genes held, each weighed by its commission\'s part unit. A second reading earns only the amount '
               'by which its score beats the best reading held; a repeat earns nothing.')
FIND_GENES_DESCRIPTION = (
    'Find the protein genes of the piece again under one other genetic code, by the gene finder pyrodigal (Prodigal). The finder is '
    'trained on the piece itself, which it can do only for a piece of at least ' + str(SELF_TRAINED_MINIMUM) + ' nt; a shorter '
    'piece is read by its pre-trained mode, which ignores the code, so this action is offered only for a piece that long. The one '
    'field of its request is code: the genetic code (translation table) of the reading, one of the codes offered. Code 11 is the '
    'bacterial, archaeal and plant plastid code (the default, read first). Code 4 is the Mycoplasma and Spiroplasma code, in which '
    'TGA is not a stop but tryptophan; code 25 is the Candidate Division SR1 and Gracilibacteria code, in which TGA is glycine; '
    'codes 4 and 25 give the same gene calls. A reading under a code that does not fit the piece has a lower score (the sum of '
    'the finder\'s scores of its genes) than the reading under the code that does; it can also call more and shorter genes and have '
    'a lower coding share. The sheet of a reading keeps every gene with its positions, strand, start codon, whether an end is cut off by the end of '
    'the piece, ribosome-binding site, score, confidence and translation. ' + CREDIT_TEXT + ' Code checks the request before '
    'anything runs; if something is wrong it comes back in feedback with the things to fix and nothing ran. A request that passes '
    'runs as one unit with no second call; a reading under a code already held is not made again.')


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind (read through the service's read handle, so the read is recorded
    with the decision)."""
    return {resource['resource_id']: resource['kind'] for resource in ctx.services['job_access'].read('resources')}


def local_resource(ctx):
    """The first local resource of the job service: where the RNA scan runs (a fixed rule, not a choice)."""
    return [name for name, kind in bound_resources(ctx).items() if kind == 'local'][0]


def tried(summary, tool, **arguments):
    """Whether a unit of ``tool`` with these ``arguments`` was tried, whatever its outcome."""
    return any(row['tool'] == tool and all(row['arguments'][name] == value for name, value in arguments.items())
               for row in summary['units'])


def owed_action(summary, ctx):
    """The first unit of the first pass not yet tried, as ``{'action_type', 'arguments'}``, or ``None`` once the first pass is
    done. The arguments are those the tool's check accepts."""
    piece = summary['piece']['ref']
    if not tried(summary, DESCRIBE_TOOL):
        return {'action_type': DESCRIBE_TOOL, 'arguments': {'piece_ref': piece}}
    if not tried(summary, FIND_GENES_TOOL, code=DEFAULT_CODE):
        return {'action_type': FIND_GENES_TOOL, 'arguments': {'piece_ref': piece, 'code': DEFAULT_CODE}}
    if not tried(summary, RNA_TOOL):
        return {'action_type': RNA_TOOL, 'arguments': {'piece_ref': piece, 'resource_id': local_resource(ctx)}}
    return None


def check_request(tool, request, summary, ctx):
    """The things to fix in a request of ``tool``: the library's one check of that tool over what the head holds."""
    piece = summary['piece']
    if tool == DESCRIBE_TOOL:
        return check_describe_piece_request(request, piece_ref=piece['ref'],
                                            described={piece['ref']} if summary['description'] is not None else set())
    if tool == FIND_GENES_TOOL:
        return check_find_genes_request(request, piece_ref=piece['ref'], length=piece['length'], held_codes=held_codes(summary))
    return check_find_rna_genes_request(
        request, piece_ref=piece['ref'], resources=bound_resources(ctx), scanned={piece['ref']} if rna_scanned(summary) else set(),
        manifest_path=ctx.settings['covariance_database_manifest'],
        executable_directory=ctx.settings['infernal_executable_directory'])


def resume_action(summary, records, ctx):
    """The unit this episode owes (``method_loop.episode_type``, step 3): the next unit of the first pass, due at once, else
    ``None``. Its request passes the tool's own check, else this raises: an owed unit the check refuses is a fault of the episode."""
    owed = owed_action(summary, ctx)
    if owed is None:
        return None
    problems = check_request(owed['action_type'], owed['arguments'], summary, ctx)
    if problems:
        raise ContractError('parts_owed_unit_refused_by_its_check:' + owed['action_type'] + ':' + repr(problems))
    return {**owed, 'due': True}


def find_genes_options(summary):
    """The request of the ``find_genes`` tool as the model fills it out: the codes still offered (``credit.offered_codes``). Empty
    when none is."""
    codes = offered_codes(summary)
    return [{'type': 'object', 'additionalProperties': False, 'required': ['name', 'code'],
             'properties': {'name': {'type': 'string', 'enum': [FIND_GENES_TOOL]}, 'code': {'type': 'integer', 'enum': codes}}}] \
        if codes else []


def selection_schema(summary):
    """What the model answers with: one request of ``find_genes``."""
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': find_genes_options(summary)}}}


def offered_actions(summary, ctx):
    """The action types this decision offers, by the names a unit is recorded under (``ToolCall.name``): the owed unit while the
    first pass is not done, else ``find_genes`` (with the ceiling 0 once no code is left to read)."""
    owed = owed_action(summary, ctx)
    return [FIND_GENES_TOOL] if owed is None else [owed['action_type']]


def outcome_row(row):
    """One earlier unit as the model sees it: its tool, request, status and the numbers of its result."""
    return {'position': row['position'], 'tool': row['tool'], 'arguments': row['arguments'], 'status': row['status'],
            **row['result']}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the piece, what the sheets held show, its own outcomes, the tool it may use and the
    yield table."""
    context = {
        'goal': GOAL, 'piece': summary['piece'], 'description': summary['description'], 'readings': summary['readings'],
        'rna_scans': summary['rna_scans'] or None, 'leading_parts': summary['leading_parts'],
        'own_outcomes': [outcome_row(row) for row in summary['units']],
        'tool_options': [{'name': FIND_GENES_TOOL, 'description': FIND_GENES_DESCRIPTION}],
        'yield_table': summary['yield_table'], 'time_accounting': time_accounting(ctx.clock.progress_time),
        'feedback': feedback}
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items() if value is not None},
                        selection_schema(summary))


def action(response, summary, records, ctx):
    """Turn the model's answer into one request of ``find_genes``, or reject it (no unit): an answer that does not fit the schema, or
    a request the check finds something to fix in (rejected with the things to fix)."""
    try:
        Draft202012Validator(selection_schema(summary)).validate(response)
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    request = {'piece_ref': summary['piece']['ref'], 'code': response['action']['code']}
    problems = check_request(FIND_GENES_TOOL, request, summary, ctx)
    if problems:
        raise Rejected({'status': 'invalid', 'category': FIND_GENES_TOOL + '_request',
                        'detail': {'request': request, 'fix': problems}})
    return ToolCall(FIND_GENES_TOOL, request)
