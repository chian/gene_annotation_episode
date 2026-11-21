"""The task: launch the assigned work on the selected local resource and see its handoff checked, one action per
decision.

The model chooses one action of a fixed set and code runs it. It writes no command, no script, no path and no
environment: the work is the record the assignment names, and the launch hands it to the library's one execution
point for local resources.

| Action | Offered | What code does |
|---|---|---|
| ``inspect_resource`` | always | reads what the job services say of the selected resource (``job_access.describe``) |
| ``launch_work`` | until this Episode holds a handoff row | reads the work record through custody and calls ``execute_on_local_resource(..., wait=False)``: the work starts as a detached job, its handoff row is written in custody, and the unit returns at handoff |
| ``check_handoff`` (``handoff_ref``: a held row) | once a handoff row is held | one status request for the launched job (``job_access.check``): the receiving check, written as a check row in custody |
| ``wait`` (``seconds``: a number in the range of the settings ``wait_seconds``) | once a handoff row is held | the wait runner ``wait_for_job`` (``episode_support/jobs/job_wait.py``): waits, then reads the job's state through ``job_access.check``. It earns nothing |

The episode performs an execution act (launch, check); it reads no source and weighs no evidence, so it has no
reasoning commit. A request the resource refuses is the returned outcome ``failed`` of its unit. The task always
offers a unit and never ends the Episode: its yield controller does, at the commission's target or when nothing
more is forecast.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (the yield controller) and ``wait_seconds`` (``{'minimum',
'maximum'}``: the range of the ``wait`` action's ``seconds``)."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_wait import wait_for_job
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

INSTRUCTIONS = (
    'You decide the next action of one episode of a gene annotation workflow: the launch of one piece of work on a '
    'local compute resource.\n'
    'PURPOSE. The parent defined a piece of work as a record. Launch it on the selected local resource and see '
    'its handoff checked. The job runs on after this episode: its results are acquired elsewhere.\n'
    'ASSIGNED WORK. context.work_ref is the record that defines the work and context.resource is the selected '
    'resource. Code reads the record and starts the work; you never write a command. context.launched_jobs lists '
    'each job this episode launched, by its handoff record, with the state its latest status reading saw.\n'
    'ACTIONS. Answer with exactly one of the actions offered by the answer schema. Code executes it and you are '
    'asked again; what each earlier action came to is in context.actions_so_far.\n'
    '- inspect_resource: read what the job services say of the resource (its workspace and limits).\n'
    '- launch_work: start the assigned work as a detached job on the resource and return at handoff. Offered '
    'until a job is handed off: the work is launched once. A launch the resource refuses is a failed action.\n'
    '- check_handoff: one status request for a launched job, named by its handoff_ref: the receiving check of the '
    'handoff.\n'
    '- wait: wait the given number of seconds, then read the state of the launched job. Offered once a job is '
    'handed off.\n'
    'CREDIT. context.credit lists what earns credit and whether it is earned: holding the handoff record of the '
    'launched work, and holding a receiving check (check_handoff) that found the job in a known state. Nothing '
    'else earns credit: not a reading or a wait. You do not end the episode: it is stopped when both are earned, '
    'or when further actions are not expected to earn more.')


def _branch(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def _one(value):
    return {'type': 'string', 'enum': [value]}


def answer_schema(summary, wait_seconds):
    """The action format: the actions offered where the Episode stands, each with its arguments."""
    branches = [_branch({'action': _one('inspect_resource')})]
    held = [job['handoff_ref'] for job in summary['jobs']]
    if held:
        branches.append(_branch({'action': _one('check_handoff'), 'handoff_ref': {'type': 'string', 'enum': held}}))
        branches.append(_branch({'action': _one('wait'),
                                 'seconds': {'type': 'number', 'minimum': wait_seconds['minimum'],
                                             'maximum': wait_seconds['maximum']}}))
    else:
        branches.append(_branch({'action': _one('launch_work')}))
    return _branch({'selection': {'anyOf': branches}})


def decide(summary, feedback, ctx):
    units = summary['credit_units']
    kinds = {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}
    context = {'work_ref': summary['work_ref'],
               'resource': {'resource_id': summary['resource_id'], 'kind': kinds[summary['resource_id']],
                            'description': summary['resource_description']},
               'launched_jobs': [{name: job[name] for name in ('handoff_ref', 'submitted_at', 'state',
                                                              'result_available')} for job in summary['jobs']],
               'actions_so_far': summary['actions'],
               'credit': [{'for': 'the handoff record of the launched work', 'credit': units['handoff'],
                           'earned': summary['handoff_held']},
                          {'for': 'a receiving check that found the job in a known state',
                           'credit': units['usable_check'], 'earned': summary['usable_check_held']}]}
    if feedback is not None:
        context['rejected_answer'] = feedback
    return ModelRequest('REASONING', INSTRUCTIONS, context, answer_schema(summary, ctx.settings['wait_seconds']))


def selected_action(response, summary, wait_seconds):
    """The one tool call the answer selects, or a rejection: it names an offered action with arguments that fit
    its format (for a wait: seconds inside the range). A selection that fails here creates no unit; the model
    decides again with the feedback."""
    try:
        Draft202012Validator(answer_schema(summary, wait_seconds)).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selection = response['selection']
    if selection['action'] == 'launch_work':
        return ToolCall('launch_work', {'resource_id': summary['resource_id'], 'work_ref': summary['work_ref']})
    if selection['action'] == 'check_handoff':
        return ToolCall('check_handoff', {'handoff_ref': selection['handoff_ref']})
    if selection['action'] == 'wait':
        return ToolCall('wait', {'handoff_ref': summary['jobs'][-1]['handoff_ref'], 'seconds': selection['seconds']})
    return ToolCall('inspect_resource', {'resource_id': summary['resource_id']})


def action(response, summary, records, ctx):
    return selected_action(response, summary, ctx.settings['wait_seconds'])


def inspect_resource(arguments, ctx):
    """What the job services say of the selected resource."""
    return {'status': 'completed', 'resource': ctx.services['job_access'].describe(arguments['resource_id'])}


async def launch_work(arguments, ctx):
    """Start the assigned work and return at handoff. The work record is read through custody; its command,
    environment and input files go, as the record gives them, to the library's execution point for local
    resources, which writes the handoff row in custody."""
    work = json.loads(ctx.store.get_artifact(arguments['work_ref']))
    return await execute_on_local_resource(ctx, arguments['resource_id'], work['command'], work['environment'],
                                           wait=False, inputs=work['inputs'], name='work')


def check_handoff(arguments, ctx):
    """The receiving check of the handoff: one status request for the launched job, written as a check row."""
    return ctx.services['job_access'].check(ctx, arguments['handoff_ref'])


async def wait(arguments, ctx):
    """The wait action: the wait runner waits and returns the launched job's state read through a check."""
    return await wait_for_job(ctx, arguments['handoff_ref'], seconds=arguments['seconds'])


TOOLS = {'inspect_resource': inspect_resource, 'launch_work': launch_work, 'check_handoff': check_handoff,
         'wait': wait}
