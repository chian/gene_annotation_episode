"""The task of the feature calling head: one request the model fills, one check, and the commission of the child that
does it.

Every decision the model chooses one database search of one sequence it holds, by the child ``bvbrc_blast`` (one BLAST
search at the BV-BRC service, followed from its launch to its graded result; a search takes minutes, so it is a child and
can be left running and come back to). The model chooses the sequence to search, the program, the database, the service
and whether to wait for the result now. What a hit says about the features of the sequence is not the model's to judge:
the child's extract step grades the result and keeps the claims in the same unit, and this head's credit reads them.

Code checks the commission before any child is made (the search library's one check): which program takes which letters,
which database holds what the program searches, and that a search already running is continued and not sent again. A
commission with something to fix is rejected with the things to fix and no unit is made.

The model is the router: it chooses what to ask next from what is held so far (the feature calls, the claims that wait
for one, what each search found and what each costs). It never ends the episode: the forecast yield controller does, when
no search left is worth its cost. A search left running is finished before the episode ends (``resume_action``).

Words: the QUERY is the sequence the root was given, and nothing else is called that. What a search is run on is the
SEARCHED sequence (``searched_ref``); the search library's own argument for it is named ``query_ref``."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected

from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_blast_search as bvbrc)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    seconds_between)

from .goal import GOAL

HEAD = 'feature_calling'
SEARCH = 'bvbrc_blast'
CHILD_SLOTS = {SEARCH: 'feature_calling/bvbrc_blast'}
SERVICES = ('job_access',)
TOOLS = {}
# Every program of the service is offered: which takes which letters and which database is the search library's check.
PROGRAMS = tuple(sorted(PROGRAM_UNITS))
# The databases this head searches at the BV-BRC service, by the name a commission gives: the protein databases of its
# two genome sets (named by the set) and the nucleotide databases of the same sets (named ``<set>.<type>``: ``ffn`` the
# genes as DNA, ``fna`` the genome sequences). The set is this head's own: it is what the model is
# offered and what the search library's check is given (``check_search``).
DATABASES = {**bvbrc.PRECOMPUTED_DATABASES, **bvbrc.NUCLEOTIDE_DATABASES}
SEARCH_FIELDS = ('searched_ref', 'program', 'database', 'resource_id', 'until')

INSTRUCTIONS = """You are finding out which features a sequence holds: what type of thing lies where on it, and on which strand. Nothing about the sequence is known beforehand.

Each step you choose one database search, as `selection`: the child `bvbrc_blast` with a `searched_ref` (a sequence you hold), a `program`, a `database`, a `resource_id` (a BV-BRC service of `bound_resources`) and `until`.

What a search gives. A search compares the sequence with known sequences and returns the ones it resembles. A hit says that a stretch of your sequence lies inside a feature of the hit's type, on which strand and, for a search against proteins, in which reading frame. It finds a part of a feature: it says where the feature starts or ends only when the alignment reaches the first or the last position of the known sequence. Code turns the hits into such claims when the result is fetched; you do not grade them.

What you are shown:
- `held_sequences`: the sequences you can search, with their length and letters.
- `programs` and `databases`: each program with the letters it takes and the letters it searches, each database with the letters it holds and its type: `faa` the proteins of its genomes, `ffn` their genes as DNA, `fna` the genome sequences themselves. A program must take the letters of the searched sequence and the database must hold what the program searches.
- `searches`: the searches already sent, each with its state. A search that is still running is continued by commissioning it again with the same program, database and service and `until` `extracted`; it is not sent a second time. A search already extracted is not repeated.
- `until`: `extracted` follows the search to its graded result. `launched` sends the search and returns at once; the service runs one search of a sequence at a time, so while it runs no other search of that sequence can be sent, and the only thing left to do with it is to continue it.
- `feature_calls`: the candidate feature calls found so far for each sequence, the highest score first: type, positions, strand, score, and the calls that compete with it for the same letters. `waiting_claims`: the claims that no feature call includes yet: type, strand, positions, which end they claim, and their support. A waiting claim is real evidence that has no feature call to sit in yet.
- `action_yields`: what each offered action is forecast to earn against its cost in time. You do not set these numbers and you do not end the episode; it ends when nothing left is worth its cost.

Choose the search that will tell you most for its cost given what is held: a database not yet searched, a program that reads the sequence another way, a search that could tell two competing calls apart. Answer with the selection only."""


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind (read through the service's read handle, so the read
    is recorded with the decision)."""
    return {resource['resource_id']: resource['kind'] for resource in ctx.services['job_access'].read('resources')}


def search_fields(summary, resources):
    """The commission of ``bvbrc_blast`` as ``(properties, required)``: the sequence to search among the held sequences,
    the program, the database and the BV-BRC service, each from a fixed set. ``None`` while this episode holds no sequence
    or no BV-BRC service is bound: the search is then not offered."""
    services = [name for name, kind in resources.items() if kind == bvbrc.ROUTE_KIND]
    # the sequences a program of the service can take (the search library's own table of letters)
    searchable = [ref for ref, letters in summary['held_sequences'].items() if letters in bvbrc.MOLECULE_UNITS]
    if not searchable or not services:
        return None
    properties = {'searched_ref': {'enum': searchable}, 'program': {'enum': list(PROGRAMS)},
                  'database': {'enum': list(DATABASES)}, 'resource_id': {'enum': services},
                  'until': {'enum': list(bvbrc.UNTIL)}}
    return properties, list(properties)


def selection_schema(summary, resources):
    """What the model answers with: one commission of the search child."""
    properties, required = search_fields(summary, resources)
    return obj({'selection': obj({'kind': {'const': 'episode_child'}, 'slot': {'const': SEARCH}, **properties},
                                 required=['kind', 'slot', *required])})


def offered_actions(summary, ctx):
    """The action types this decision offers, by the names a unit is recorded under: the search child while its
    commission can be stated."""
    return [] if search_fields(summary, bound_resources(ctx)) is None else [SEARCH]


def library_request(commission):
    """A commission in the search library's own argument names (its ``query_ref`` is the searched sequence)."""
    return {'query_ref': commission['searched_ref'],
            **{name: commission[name] for name in ('program', 'database', 'resource_id', 'until')}}


def check_search(commission, summary, resources):
    """The things to fix in a commission of the search child (``bvbrc_blast_search.check_commission``): the program takes
    the letters of the searched sequence, the database (one of ``DATABASES``) holds what the program searches, the
    service is a bound BV-BRC service, a search still running is continued and a search already extracted or already
    sent is not sent again. Any sequence this episode holds may be searched."""
    return bvbrc.check_commission(
        library_request(commission), programs=PROGRAMS, databases=DATABASES, sequences=summary['held_sequences'],
        scope_subjects=list(summary['held_sequences']), resources=resources, searches=summary['searches'],
        commissioned=[(row['arguments']['searched_ref'], row['arguments']['program'], row['arguments']['database'])
                      for row in summary['units'] if row['kind'] == 'child'])


def searches_view(searches, now):
    """The searches this episode holds as the model sees them at ``now`` (the decision's recorded time): each with its
    state, whether it is still running, and for a running one the seconds since its launch and the seconds still expected
    (the estimate recorded with its launch minus those seconds, not below zero). Facts, never a deadline."""
    shown = []
    for search in searches:
        row = {'searched_ref': search['query_ref'],
               **{key: search[key] for key in ('handoff_ref', 'program', 'database', 'resource_id', 'latest_state',
                                               'outstanding', 'closed', 'estimated_seconds')}}
        if search['outstanding']:
            elapsed = seconds_between(search['launched_at'], now)
            row.update(seconds_since_launch=elapsed,
                       expected_remaining_seconds=max(search['estimated_seconds'] - elapsed, 0.0))
        shown.append(row)
    return shown


def resume_commission(search):
    """The commission that continues a search left running: its own commission again with ``until`` ``extracted`` (it
    sends nothing)."""
    return {'searched_ref': search['query_ref'], 'program': search['program'], 'database': search['database'],
            'resource_id': search['resource_id'], 'until': 'extracted'}


def resume_action(summary, records, ctx):
    """The resume this episode owes: ``None`` while no search is left running, else the continuation of one as
    ``{'action_type', 'arguments', 'due'}``. ``due`` is True once the search's expected remaining seconds have passed (the
    estimate recorded with its launch minus the seconds from the launch to this decision's recorded time). The search
    chosen: the earliest launched among the due ones, else the earliest launched. While a search is left running the
    episode does not stop; once it is due its continuation is the only action offered. The commission passes this head's
    own check, else this raises: a continuation the check refuses is a fault of the episode."""
    running = [search for search in summary['searches'] if search['outstanding']]
    if not running:
        return None
    remaining = lambda search: search['estimated_seconds'] - seconds_between(search['launched_at'], ctx.clock.now)
    due = [search for search in running if remaining(search) <= 0]
    arguments = resume_commission(min(due or running, key=lambda search: search['launched_at']))
    problems = check_search(arguments, summary, bound_resources(ctx))
    if problems:
        raise ContractError('feature_calling_resume_commission_refused_by_its_check:' + repr(problems))
    return {'action_type': SEARCH, 'arguments': arguments, 'due': bool(due)}


def decide(summary, feedback, ctx):
    """Ask the model for the next search, shown the sequences it holds, the programs and databases, the searches sent,
    the feature calls and the waiting claims, its own outcomes, the measured time and the yield table."""
    resources = bound_resources(ctx)
    context = {
        'goal': GOAL, 'scope': summary['scope'],
        'held_sequences': [{'record_ref': ref, 'letters': letters, 'length': summary['sequence_lengths'][ref]}
                           for ref, letters in summary['held_sequences'].items()],
        'programs': [{'program': program, 'takes': PROGRAM_UNITS[program][0], 'searches': PROGRAM_UNITS[program][1]}
                     for program in PROGRAMS],
        'databases': [{'database': name, 'holds': entry['unit'], 'type': entry['db_type']}
                      for name, entry in DATABASES.items()],
        'bound_resources': resources,
        'searches': searches_view(summary['searches'], ctx.clock.now),
        'given_features': summary['given_features'],
        'feature_calls': [{'target_ref': finding['target_ref'], 'features': finding['features'],
                           'rival_rank': finding.get('rival_rank')} for finding in summary['target_findings']],
        'waiting_claims': [{'target_ref': finding['target_ref'], 'claims': finding['waiting_claims']}
                           for finding in summary['target_findings']],
        'tests': summary['tests'], 'differentials': summary['differentials'],
        'credit_binding': summary['credit_binding'],
        'own_outcomes': summary['units'], 'last_local_outcome': summary['last_local_outcome'],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', INSTRUCTIONS, context, generation_schema(selection_schema(summary, resources)))


def action(response, summary, records, ctx):
    """Turn the model's answer into the commission of the search child, or reject it (no unit): an answer that does not
    fit the schema, or a commission the check finds something to fix in (rejected with the things to fix)."""
    resources = bound_resources(ctx)
    schema = selection_schema(summary, resources)
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('feature_calling_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    commission = {name: selection[name] for name in SEARCH_FIELDS}
    problems = check_search(commission, summary, resources)
    if problems:
        raise Rejected({'status': 'invalid', 'category': SEARCH + '_commission',
                        'detail': {'commission': commission, 'fix': problems}})
    return ChildCall(SEARCH, commission)
