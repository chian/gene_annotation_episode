"""The task: acquire the requested result files of the handed-off job, one action per decision.

The model chooses one action of a fixed set and code runs it. The job, its resource and the requested file names
come from the assignment and the held job ledger rows, never from the model's answer.

| Action | What code does | Call |
|---|---|---|
| ``check_job`` | one status request for the job through the receiving interface of its resource; the check row is written in custody | ``await resources.check_handoff(ctx, handoff)`` |
| ``fetch_results`` | fetch the requested result files, write each as an artifact and write the closure row | ``await resources.execute(ctx, handoff, 'job.fetch', {'handoff_ref', 'names'})`` |
| ``wait`` (``seconds``: a number in the range of the settings ``wait_seconds``) | the wait runner: waits, then reads the job's state through ``job_access.check``. It earns nothing | ``await wait_for_job(ctx, handoff_ref, seconds=)`` (``episode_support/jobs/job_wait.py``) |

``resources`` is the run's ``ResourceAdapters`` service; it selects the adapter with
``handoff['resource_selection']['resource_id']``, so each job tool is handed the record ``{'resource_selection':
{'resource_id': <the resource of the held handoff row>}, 'handoff_ref': <that row>}``. A request the resource
refuses (the job has not ended, a requested name is not among its results) is the returned outcome ``failed`` of
the unit. The episode performs an execution act (check, fetch); it reads no source and weighs no evidence, so it
has no reasoning commit: the scientific parent interprets what is fetched. The task always offers its actions and
never ends the Episode: its yield controller does.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (the yield controller) and ``wait_seconds`` (``{'minimum',
'maximum'}``: the range of the ``wait`` action's ``seconds``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_wait import wait_for_job
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)

CHILD_SLOTS = {}
SERVICES = ('resources', 'job_access')

INSTRUCTIONS = (
    'You decide the next action of one episode of a gene annotation workflow: the acquisition of the results of '
    'one job.\n'
    'PURPOSE. A job was launched earlier on a compute resource and handed off. Acquire the result files the '
    'parent requested from that job. The parent interprets them.\n'
    'ASSIGNED WORK. context.job is the handed-off job (this episode holds its handoff record) with the state of '
    'its latest status reading. context.requested_result_files names the files to acquire; '
    'context.acquired_result_files names those already held.\n'
    'ACTIONS. Answer with exactly one action. Code executes it and you are asked again; what each earlier action '
    'came to is in context.actions_so_far.\n'
    '- check_job: one status request for the job. It records the state of the job and whether its results are '
    'available.\n'
    '- fetch_results: fetch the requested result files of the job into the record store and close the job. It '
    'fails, and changes nothing, when the job has not ended or a requested file is not among its results.\n'
    '- wait: wait the given number of seconds, then read the state of the job.\n'
    'CREDIT. One credit for each requested result file this episode holds after a fetch. Nothing else earns '
    'credit: not a check or a wait. You do not end the episode: it is stopped when every requested file is held, '
    'or when further actions are not expected to earn more.')


def _branch(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def _one(value):
    return {'type': 'string', 'enum': [value]}


def answer_schema(wait_seconds):
    """The action format: the three actions, each with its arguments."""
    return _branch({'selection': {'anyOf': [
        _branch({'action': _one('check_job')}),
        _branch({'action': _one('fetch_results')}),
        _branch({'action': _one('wait'), 'seconds': {'type': 'number', 'minimum': wait_seconds['minimum'],
                                                     'maximum': wait_seconds['maximum']}})]}})


def _handoff(summary):
    """The record the ``resources`` service selects the adapter with, and the adapter reads the job from."""
    return {'resource_selection': {'resource_id': summary['job']['resource_id']},
            'handoff_ref': summary['job']['handoff_ref']}


def decide(summary, feedback, ctx):
    job = summary['job']
    capability = ctx.services['resources'].read('adapter_capabilities')[job['resource_id']]
    context = {'job': {'handoff_ref': job['handoff_ref'], 'resource_id': job['resource_id'],
                       'resource_kind': job['kind'], 'resource_availability': capability['availability'],
                       'submitted_at': job['submitted_at'], 'state': summary['job_state'],
                       'result_available': summary['result_available']},
               'requested_result_files': summary['requested_names'],
               'acquired_result_files': [item['name'] for item in summary['acquired']],
               'actions_so_far': summary['actions'],
               'credit': {'earned': len(summary['acquired']), 'target': len(summary['requested_names'])}}
    if feedback is not None:
        context['rejected_answer'] = feedback
    return ModelRequest('REASONING', INSTRUCTIONS, context, answer_schema(ctx.settings['wait_seconds']))


def selected_action(response, summary, wait_seconds):
    """The one tool call the answer selects, or a rejection (for a wait: seconds inside the range)."""
    try:
        Draft202012Validator(answer_schema(wait_seconds)).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selection = response['selection']
    if selection['action'] == 'check_job':
        return ToolCall('check_job', _handoff(summary))
    if selection['action'] == 'wait':
        return ToolCall('wait', {'handoff_ref': summary['job']['handoff_ref'], 'seconds': selection['seconds']})
    return ToolCall('fetch_results', {**_handoff(summary), 'names': summary['requested_names']})


def action(response, summary, records, ctx):
    return selected_action(response, summary, ctx.settings['wait_seconds'])


async def check_job(arguments, ctx):
    """One status request for the job through the receiving interface of its resource."""
    return await ctx.services['resources'].check_handoff(ctx, arguments)


async def fetch_results(arguments, ctx):
    """Fetch the requested result files of the job and close it."""
    return await ctx.services['resources'].execute(
        ctx, arguments, 'job.fetch', {'handoff_ref': arguments['handoff_ref'], 'names': arguments['names']})


async def wait(arguments, ctx):
    """The wait action: the wait runner waits and returns the job's state read through a check."""
    return await wait_for_job(ctx, arguments['handoff_ref'], seconds=arguments['seconds'])


TOOLS = {'check_job': check_job, 'fetch_results': fetch_results, 'wait': wait}
