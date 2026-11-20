"""The task: establish a usable prepared-data record of the assigned set on a bound local resource.

The model is the router. It answers with one defined action as JSON: ``launch_local`` (the resource and the kind) or
``hold`` (a reason from a fixed vocabulary). Code checks the JSON with ONE deterministic function before anything
runs (``preparation_problems``: against the commission, the records held and the bound resources). If it names
problems, ``action`` raises ``Rejected`` with them (each a code and the field it concerns): no unit is made and the
model answers again. If it passes, the tool ``launch_local`` runs the whole preparation as one unit
(``prepare_locally``) and, with a passed check, a fault of the job is the environment's: reported once as failed,
never retryable. ``hold`` is always a valid answer. The task never ends the Episode; the yield controller does.

Settings (``ctx.settings``): ``blast_executable_directory`` (the directory with the BLAST programs),
``python_executable`` (the absolute interpreter the job runs the driver with), ``cost`` and ``parameters``
(``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    KINDS)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence.blast_preparation_run import (
    PROBLEM_CODES, prepare_locally, preparation_problems)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)

CHILD_SLOTS = {}
SERVICES = ('job_access',)
HOLD_REASONS = ('usable_record_held', 'failure_not_retryable', 'input_above_local_bound', 'no_local_resource')

INSTRUCTIONS = (
    'You are the preparation agent for one assigned sequence set. This episode exists to establish a usable '
    'prepared-data record from that set (a BLAST database build or a masking run, as the commission says) on a '
    'bound local resource, and to return it to the parent.\n'
    '\n'
    'You do not write a command. You answer with one action as JSON; code checks your JSON before anything runs and '
    'runs the job.\n'
    '- launch_local, with resource_id (one of the bound local resources listed in local_resources) and kind (the '
    'commission\'s kind, assignment.kind). Code first checks the call against the commission, the records held and '
    'the resource: the resource is bound and local, the kind is the commission\'s, the input parses and is within '
    'that resource\'s size bound (scratch_bytes), the programs exist, the job compiles. If something is wrong you '
    'are told each problem as a code with the field it concerns (feedback.problems) and nothing has run; fix those '
    'fields and answer again. If the check passes, one unit builds the job, runs it to its end, reads its receipt '
    'and keeps the prepared-data record. A correct call works on the first try.\n'
    '- hold, with reason: do nothing now. The reasons are usable_record_held (a usable record of this set is '
    'already held), failure_not_retryable (the last launch failed and cannot be retried), input_above_local_bound '
    '(the input is larger than every local resource\'s bound) and no_local_resource (none is bound).\n'
    '\n'
    'What you are shown. units: each earlier action with its status (usable, failed, incomplete, held), its '
    'failure_code (a fixed vocabulary) and retryable. A failure after a passed check is a fault of the job or the '
    'environment: retryable is false, the same call gives the same result, so do not launch again; hold with '
    'failure_not_retryable. A usable status means the record is held and the work is done. prepared: the '
    'prepared-data records you hold with their controlled features, and whether the parent passed them.\n'
    '\n'
    'Credit is the measure of this episode: prepared_unit is earned once when a usable prepared-data record is newly '
    'established (not one the parent already passed). A failed or incomplete record, a hold and a repeat earn '
    'nothing. The yield table shows what each unit earned and the forecast. You cannot end the episode; the yield '
    'controller does.')


def local_resources(ctx):
    """The bound local resources with the size bound each gives (read through the service's read handle, so the
    read is recorded with the decision)."""
    access = ctx.services['job_access']
    return [{'resource_id': resource['resource_id'],
             'scratch_bytes': access.read('describe', resource['resource_id'])['policy']['scratch_bytes']}
            for resource in access.read('resources') if resource['kind'] == 'local']


def output_schema():
    """The answer: one defined action with its controlled fields."""
    def one(name, **fields):
        return {'type': 'object', 'additionalProperties': False, 'required': ['name', *fields],
                'properties': {'name': {'type': 'string', 'enum': [name]}, **fields}}
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': [
                one('launch_local', resource_id={'type': 'string'}, kind={'type': 'string', 'enum': list(KINDS)}),
                one('hold', reason={'type': 'string', 'enum': list(HOLD_REASONS)})]}}}


def decide(summary, feedback, ctx):
    context = {'assignment': summary['fields'], 'credit': {'prepared_unit': summary['prepared_unit']},
               'input_set': summary['input'], 'local_resources': local_resources(ctx),
               'units': summary['units'], 'prepared': summary['prepared'], 'yield_table': summary['yield_table'],
               'feedback': feedback, 'problem_codes': list(PROBLEM_CODES)}
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items()
                                                     if value is not None}, output_schema())


def action(response, summary, records, ctx):
    """The model's JSON to a unit. The one check runs here, before anything runs; a call with problems is rejected
    with the list of them (no unit, no observation)."""
    try:
        Draft202012Validator(output_schema()).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    if chosen['name'] == 'hold':
        return ToolCall('hold', {'reason': chosen['reason']})
    access = ctx.services['job_access']
    resources = {item['resource_id']: access.read('describe', item['resource_id']) for item in access.read('resources')}
    problems = preparation_problems(chosen, fields=summary['fields'], records=records, resources=resources,
                                    executable_directory=ctx.settings['blast_executable_directory'],
                                    python=ctx.settings['python_executable'])
    if problems:
        raise Rejected({'status': 'invalid', 'category': 'launch_local_check', 'problems': problems})
    return ToolCall('launch_local', {'resource_id': chosen['resource_id'], 'fields': summary['fields']})


async def launch_local(arguments, ctx):
    """The whole local preparation as one unit, by the library's one function."""
    return await prepare_locally(ctx, arguments['resource_id'], arguments['fields'],
                                 executable_directory=ctx.settings['blast_executable_directory'],
                                 python=ctx.settings['python_executable'])


def hold(arguments, ctx):
    """Nothing is run: the unit's outcome is the reason."""
    return {'status': 'held', 'reason': arguments['reason']}


TOOLS = {'launch_local': launch_local, 'hold': hold}
