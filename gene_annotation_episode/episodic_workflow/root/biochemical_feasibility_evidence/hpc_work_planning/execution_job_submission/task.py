"""The task: choose which permitted concrete execution request to commission on an explicit resource_id.

One unit is one route child commission (the child owns the iterative execution) or the one lookup this launch
offers. The task always offers a unit and never ends the Episode: the old ``redeliver_report``, ``wait`` and
``reason`` actions are not carried (an hpc launch permitted only ``tool`` and ``child``), and only the yield
controller stops the Episode.

Submitting is the route child's: this episode calls no job service itself (``SERVICES = ()``); the services the
route children need are theirs."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting

from .goal import GOAL

CHILD_SLOTS = {
    'hpc_job_execution': 'biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution',
    'local_job_execution': 'biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission/local_job_execution',
}
SLOT_OF_KIND = {'hpc': 'hpc_job_execution', 'local': 'local_job_execution'}
SERVICES = ()

# The old goal.LaunchGoal.instructions (replaces the default instructions: replaces_default_instructions).
INSTRUCTIONS = (
    'Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
    'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
    'constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive '
    'its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes '
    'this launch endpoint with exact zero future credit.')
ANSWER_INSTRUCTIONS = (
    '\nAnswer with one selection: kind child with the resource_id of a permitted request (permitted_resource_ids) '
    'to commission its route child, or kind tool to read the execution capabilities. The route child for a '
    'request is the one of its resource kind (hpc or local).')

TOOL_DESCRIPTIONS = [
    {'name': 'execution_capabilities',
     'description': 'Read the actual caller-bound resource configuration and already recorded inventory; no '
                    'discovery or selection.',
     'input_schema': {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}}]
CHILD_OPTIONS = {
    'hpc_job_execution': 'Commission the hpc route child for an hpc request: it executes the job on the PBS '
                         'resource with shell commands and returns the handoff to the actual job.',
    'local_job_execution': 'Commission the local route child for a local request: it executes the job locally '
                           'and returns the handoff to the actual job.'}
TRANSPORT = {'open_records_as_text': True,
             'argument_transport_error': 'execution_job_submission_argument_transport_unsupported'}


def action_schema(eligible):
    """The one selection the model answers: a permitted request to commission, or the capabilities lookup."""
    options = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool'],
                'properties': {'kind': {'const': 'tool'}, 'tool': {'enum': [item['name'] for item in TOOL_DESCRIPTIONS]}}}]
    if eligible:
        options.insert(0, {'type': 'object', 'additionalProperties': False, 'required': ['kind', 'resource_id'],
                           'properties': {'kind': {'const': 'child'},
                                          'resource_id': {'type': 'string', 'enum': list(eligible)}}})
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': options}}}


def _launch_instruction_context(settings, summary):
    """The run-frozen launch instruction library, when one is configured: its identity and the sections the
    commissioner selected."""
    directory = settings.get('launch_instructions_directory')
    if directory is None:
        return {}
    library = LaunchInstructions(directory)
    context = {'launch_instruction_library': library.context()}
    selected = library.materialize(summary.get('launch_instructions'))
    if selected is not None:
        context['selected_launch_instructions'] = selected
    return context


def decide(summary, feedback, ctx):
    context = {'goal': GOAL,
               'execution_assignment': {name: summary[name] for name in
                                        ('requests', 'immutable_input_versions', 'constraints')},
               'permitted_resource_ids': summary['eligible'],
               'execution_progress': {'handed_off_resource_ids': summary['handed_off_resource_ids'],
                                      'handoff_refs': summary['handoff_refs'],
                                      'commissioned': summary['commissioned']},
               'current_credit': summary['controller']['current_credit'],
               'completed_action_reports': [*summary['commissioned'], *summary['lookups']],
               'child_options': CHILD_OPTIONS,
               'tools': TOOL_DESCRIPTIONS,
               'feedback': feedback,
               'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               **_launch_instruction_context(ctx.settings, summary)}
    for name in ('hpc_execution_job', 'selected_execution_task'):
        if name in summary:
            context[name] = summary[name]
    if 'launch_instructions' in summary:
        context['launch_instructions'] = summary['launch_instructions']
    return ModelRequest('REASONING', INSTRUCTIONS + ANSWER_INSTRUCTIONS, context,
                        strict_output_schema(action_schema(summary['eligible']), **TRANSPORT))


def action(response, summary, records, ctx):
    """The model's answer is one selection; an answer that is not one is rejected."""
    schema = action_schema(summary['eligible'])
    try:
        decoded = decode_strict_output(response, schema, **TRANSPORT)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='invalid_action'))
    selection = decoded['selection']
    if selection['kind'] == 'tool':
        return ToolCall(selection['tool'], {})
    resource_id = selection['resource_id']
    return ChildCall(SLOT_OF_KIND[summary['requests'][resource_id]['resource_kind']], {'resource_id': resource_id})


def execution_capabilities(arguments, ctx):
    """The old ``LaunchWorkOperations.execute`` of ``execution.capabilities``.

    The reader ``execution_capability_information(self, context)`` (old ``library.execution_resource_information``)
    is in the old shared root and has no home in ``episode_support``: the use raises."""
    raise NotImplementedError('library_not_placed:library.execution_resource_information.'
                              'execution_capability_information')


TOOLS = {'execution_capabilities': execution_capabilities}
