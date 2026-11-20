"""The task: launch the assigned job on the assigned local resource. The Episode ends at handoff.

The model is the router. It answers with one defined action and that action's controlled fields, as JSON; code
carries it out. There are two actions:

- ``launch_job``: start the assignment's requested job on the assignment's resource. The model names the resource
  (the one value the assignment allows); ``action`` takes the job's command and environment from the assignment and
  the tool calls the library's local wrapper (``resource_local.execute_on_local_resource``, the inspection point
  before execution), which starts the detached job through the real ``job_access`` route and writes the job's
  handoff row of ``JOB_LEDGER``. The model writes no command and nothing it writes is run.
- ``hold_launch``: do not launch now, with a reason from a fixed vocabulary. It starts nothing and earns nothing.

A local assignment's constraints name the allocation the job is to run under; they are not a range to choose in, so
``launch_job`` has no override field. The model sees the constraints beside the resource as ``job_access`` describes
it and chooses whether to launch.

The task always offers a unit and never ends the Episode. The yield controller ends it: at the handoff, whose
credit is the commission's target, or when further actions stop earning."""
from episode_runtime import ModelRequest, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource

CHILD_SLOTS = {}
SERVICES = ('job_access',)
HOLD_REASONS = ('constraints_not_met', 'launch_failed')

INSTRUCTIONS = (
    'You are the launch agent for the one job and the one local resource assigned below. This episode exists to '
    'start that job as a detached job on that resource and hand it off: the handoff record goes back to the '
    'parent, and the episode ends there. It does not wait for the job, check it or collect its results; other '
    'episodes do that from the handoff record.\n'
    '\n'
    'The job to run is assignment.requested_job, exactly as it is given. You do not write, change or run a '
    'command: you choose an action and code carries it out. The caller\'s scientific inputs, desired outputs and '
    'acceptance criteria are preserved because the requested job is launched unchanged.\n'
    '\n'
    'Your choice is whether, when and how to launch within the assignment\'s constraints. assignment.constraints '
    'names the allocation the job is to run under (memory_bytes, scratch_bytes, or the allocation as a whole); '
    'resource is the assigned resource as it is configured now, and resource.policy is the allocation it gives '
    'every job. The recorded inventory in the assignment is context, not proof of present usability.\n'
    '\n'
    'Credit is the measure of this episode. A handoff is the only thing that earns credit: it earns '
    'credit.handoff_earns, the credit the assignment\'s requested_job_handoff requirement defines, and the episode '
    'ends when it is earned. Nothing else earns credit. Each action is one recorded unit: its actual result and '
    'the credit it earned count, including a failed launch and zero progress. You cannot end the episode; it ends '
    'at the handoff, or when further actions stop earning credit.\n'
    '\n'
    'Actions. Answer with exactly one, as JSON:\n'
    '- launch_job, with resource_id (the assignment\'s resource_id): start the requested job as a detached job on '
    'the assigned resource. Its result is the handoff, or the failure of the launch request. A failed launch '
    'started no job; launching again is a new attempt.\n'
    '- hold_launch, with reason: do not launch now. reason is constraints_not_met (the resource as configured does '
    'not give the allocation the assignment\'s constraints name) or launch_failed (a launch request failed and '
    'repeating it is not expected to succeed). A hold starts nothing and earns no credit.')


async def launch_job(arguments, ctx):
    """Start the assigned job through the library's local wrapper and return at handoff."""
    return await execute_on_local_resource(ctx, arguments['resource_id'], arguments['command'],
                                           arguments['environment'], wait=False)


def hold_launch(arguments, ctx):
    """Nothing is launched: the unit's outcome is the reason the model gave."""
    return {'status': 'held', 'reason': arguments['reason']}


TOOLS = {'launch_job': launch_job, 'hold_launch': hold_launch}


def output_schema(assignment):
    """The answer: one defined action with its controlled fields, every value from a fixed set."""
    def one(name, field, values):
        return {'type': 'object', 'additionalProperties': False, 'required': ['name', field],
                'properties': {'name': {'type': 'string', 'enum': [name]},
                               field: {'type': 'string', 'enum': list(values)}}}
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': [one('launch_job', 'resource_id', [assignment['resource_id']]),
                                                one('hold_launch', 'reason', HOLD_REASONS)]}}}


def decide(summary, feedback, ctx):
    """One action: the model chooses it from the assignment, the resource, what its actions did and their credit."""
    assignment = summary['assignment']
    context = {'assignment': assignment,
               'resource': ctx.services['job_access'].read('describe', assignment['resource_id']),
               'actions_so_far': {'launches': summary['launches'], 'holds': summary['holds']},
               'credit': {'handoff_earns': summary['handoff_credit'],
                          'earned_by_each_action_so_far': summary['credit_by_action']}}
    return ModelRequest('REASONING', INSTRUCTIONS, context, output_schema(assignment))


def action(response, summary, records, ctx):
    """The unit of the chosen action. The launch runs the assignment's own job: its command and environment are
    taken from the assignment here, never from the answer."""
    chosen = response['action']
    if chosen['name'] == 'hold_launch':
        return ToolCall('hold_launch', {'reason': chosen['reason']})
    job = summary['assignment']['requested_job']
    return ToolCall('launch_job', {'resource_id': chosen['resource_id'], 'command': job['argv'],
                                   'environment': job['environment']})
