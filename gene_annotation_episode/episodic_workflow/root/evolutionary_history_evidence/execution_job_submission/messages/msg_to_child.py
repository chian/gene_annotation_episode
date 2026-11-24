"""The commission of one launch child: the request of the chosen resource as the child's assignment, every record this
episode names for the child, and the return fields it selects.

The old ``to_child_<role>_job_execution.assemble_request`` (three copies that differ only in the role) built the old
runner's envelope (goal, scope, initial report, knowledge inheritance, the child's ``prepare_assignment`` of the
selected request). The episode's own content was that the child's assignment is the selected request of the launch
assignment (with the launch instructions materialised), that the scientific parent task reached the child, and that
the initial report was empty. A wrong commission fails: nothing here checks the request against the child.

Slots keep the old role names: ``launch_api`` (the API service child), ``launch_local`` and ``launch_hpc`` (the
practical execution children). The old ``required_return_sources`` asked for ``execution_handoff_refs`` of a launch
whose parent is the A104 head. The local and HPC children declare ``execution_handoff_refs`` and
``execution_completed`` selectable, and the commission selects both; the API child declares both as required fields
(always returned), so its commission selects nothing (a selection naming a required field is refused by the form).

What each child's own form needs is passed as it asks. The API child takes the request's parts as separate fields,
``input_refs`` (the records the job inputs name), ``handoff_unit`` (also its completion target) and
``acquired_record_unit``, and reads the scientific question and the selected tool information from the commission
message. The local launch child is given the request of the resource and nothing else. The HPC child
declares no ``record_refs`` field: the records the job inputs name cannot be passed to it.

The launch instructions of a request are the sections the commissioner pinned and, added to them, the sections this
episode's lookups read (``pinned_launch_instructions`` of the summary: pinned by code when they were read). The
library's own rule (``retain_inherited_selection``: a child may add instructions and cannot replace the parent's pins)
admits the result."""
from episode_runtime import ChildMessage

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    retain_inherited_selection)

SELECTION = ('execution_handoff_refs', 'execution_completed')


def _request(summary, arguments):
    request = dict(summary['assignment']['requests'][arguments['resource_id']])
    if 'launch_instructions' in summary['assignment'] and 'launch_instructions' not in request:
        request['launch_instructions'] = summary['assignment']['launch_instructions']
    read = summary['pinned_launch_instructions']
    if read is not None:
        given = request.get('launch_instructions')
        kept = [] if given is None else given['sections']
        request['launch_instructions'] = retain_inherited_selection(given, {**read, 'sections': kept + [
            section for section in read['sections'] if section not in kept]})
    return request


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = _request(summary, arguments)
    if slot == 'launch_api':
        task = summary['scientific_task']
        assignment = {**request, 'input_refs': list(summary['record_refs']),
                      'handoff_unit': summary['handoff_unit'],
                      'acquired_record_unit': summary['acquired_record_unit']}
        return ChildMessage(
            objective='Establish the requested usable handoff of the job on the API resource ' + resource_id,
            message={'scientific_question': task['scientific_question'],
                     'selected_tool_info': task['selected_tool_info']},
            assignment=assignment, selection=())
    if slot == 'launch_local':
        # The local launch child is given the request of the resource and nothing else: it launches that request's
        # job as it is and returns at handoff.
        return ChildMessage(
            objective='Launch the assigned job on the local resource ' + resource_id + ' and return its handoff',
            message={'resource_id': resource_id}, assignment=request, selection=SELECTION)
    if slot == 'launch_hpc':
        return ChildMessage(
            objective='Execute the assigned job on the HPC resource ' + resource_id
                      + ' until its requested handoff exists',
            message={'resource_id': resource_id}, assignment=request, selection=SELECTION)
    raise ValueError('execution_launch_slot_unknown:' + slot)
