"""The task: submit the assigned database search once through the job service and end at the handoff. Nothing here is
a decision of a model: ``decide`` builds the request from the commission and returns the one unit, so the model is never
asked (``action`` exists because the system requires the member; it is never reached).

The request is exactly the commission: the program, the hosted database and the hit-list size are the parent's
controlled choices, the query is the held sequence record the parent named, and the ``submit`` unit stages it (no
sequence and no parameter is written by a model). A request that is not of the service's request form, or whose program
does not take a query of the assigned molecule, fails the run with its error: a wrong commission is not an outcome of
a unit. The job is also checked against the declared kind: the job of the public service must derive to a database
search before anything is sent.

A submission that failed is the outcome of its unit, with its code, whether the request was sent and, when the service
asks to be left alone, for how long (the route keeps the provider's spacing and refuses a too-early request without
sending it). The next decision then submits again after that time. A reply that was lost (``sent`` unknown) is not
resubmitted by the route: it answers the same error and sends nothing, and the controller ends the episode when
further units stop being expected to earn.

The job continues at the service after the submission returns: this episode does not wait for it, ask its status or
fetch its results.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``)."""
import asyncio

from jsonschema import Draft202012Validator

from episode_runtime import ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    DATABASE_SEARCH, checked_analysis_kind)

CHILD_SLOTS = {}
SERVICES = ('job_access',)
QUERY_FILE = 'query.fasta'
# The unit a program's query is counted in, for each molecule a held sequence subject can have.
MOLECULE_UNITS = {'protein': 'aa', 'dna': 'nt', 'rna': 'nt'}
SPACING_MARGIN_SECONDS = 0.5


async def submit(arguments, ctx):
    """One submission of the built request on the assigned resource, through the ``job_access`` service: the query is
    staged from the held sequence record, the job's handle comes from this unit's operation key (a unit that runs
    again does not submit again) and the handoff row is written through ``ctx.store`` with the service's reply as an
    artifact. A request that failed is the returned outcome, with whether it was sent."""
    if arguments['wait_seconds'] > 0:
        await asyncio.sleep(arguments['wait_seconds'])
    job = {**arguments['request'], 'query_file': QUERY_FILE}
    checked_analysis_kind(DATABASE_SEARCH, job)                 # the declared kind and the job's own agree
    launched = ctx.services['job_access'].launch(ctx, arguments['resource_id'], job,
                                                 inputs={QUERY_FILE: arguments['query_sequence_ref']})
    if launched['status'] != 'completed':
        failure = launched['failure']
        return {'status': 'failed', 'job': launched['job'], 'handoff_refs': [], 'failure_code': failure['code'],
                'sent': failure['detail']['sent'],
                'retry_after_seconds': failure['detail'].get('retry_after_seconds'), 'failure': failure}
    return {'status': 'completed', 'job': launched['job'], 'handoff_refs': [launched['handoff_ref']],
            'failure_code': None, 'sent': True, 'retry_after_seconds': None, 'failure': None,
            'submitted_at': launched['submitted_at'], 'reply_ref': launched['reply_ref'],
            'adopted': launched['adopted'], 'replayed': launched['replayed']}


TOOLS = {'submit': submit}


def decide(summary, feedback, ctx):
    """The one unit: submit the request the commission is. The commission is checked against the service's own request
    form and the molecule the program takes; a violation raises and ends the run."""
    description = ctx.services['job_access'].read('describe', summary['resource_id'])
    if description['service'] != summary['service']:
        raise ValueError('database_blast_launch_service_conflict:' + description['service'] + ':'
                         + summary['service'])
    request = {'program': summary['program'], 'database': summary['database'],
               'hitlist_size': summary['hitlist_size']}
    Draft202012Validator(description['request_schema']).validate(request)
    unit = MOLECULE_UNITS[summary['query']['molecule']]
    if description['query_unit_by_program'][request['program']] != unit:
        raise ValueError('program_does_not_take_the_assigned_query:' + request['program'] + ':query_is:'
                         + summary['query']['molecule'])
    last = summary['submissions'][-1] if summary['submissions'] else None
    retry = None if last is None else last['retry_after_seconds']
    return ToolCall('submit', {'resource_id': summary['resource_id'], 'request': request,
                               'query_sequence_ref': summary['query']['sequence_ref'],
                               'wait_seconds': 0.0 if retry is None else retry + SPACING_MARGIN_SECONDS})


def action(response, summary, records, ctx):
    raise TypeError('database_blast_launch_api_asks_no_model_so_no_response_is_ever_acted_on')
