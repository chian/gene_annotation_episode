"""The commission of one launch child: the request of the chosen resource as the child's assignment, every record
this episode names for the child, and the return fields it selects.

The old ``to_child_<role>_job_execution.prepare_commission`` (three copies that differ only in the role and the
binding-path check; the HPC copy also required ``execution_handoff_refs`` in the return form under an ``hpc``
ancestor) built the old runner's envelope (scope, expanded return form, initial report, the child's
``prepare_assignment`` of the selected request). The episode's own content was that the child's assignment is the
selected request of the launch assignment (with the launch instructions materialised). A wrong commission fails:
nothing here checks the request against the child. The local launch child is given the request of the resource and
nothing else (it launches that request's job unchanged and returns at handoff).

Slots keep the old role names: ``launch_api`` (the API service child), ``launch_local`` and ``launch_hpc`` (the
practical execution children). Each child declares ``execution_handoff_refs`` and ``execution_completed`` as
selectable fields; every commission selects both (the old ``required_return_sources`` asked for
``execution_handoff_refs`` of a launch whose parent is the A101 head; both are what this episode reads back).

What the API child's own form needs is built from the request of the chosen resource: the resource and its service
(as the capabilities lookup read it from the job service), the request's sequence subject as the query in custody
(``query_subject_refs``) with the other records this episode holds for the job (``input_refs``: the subject's
sequence artifact), the parameters of the service's request the request fixes (``fixed_request``; the child builds
the rest) and ``completion_target`` (the credit one established handoff earns: ``handoff_unit``). The three API
request forms give them as ``_api_job`` says. The HPC child declares no ``record_refs`` field: the records the job
inputs name cannot be passed to it.

The launch instructions of a request are the sections the commissioner pinned and, added to them, the sections this
episode's lookups read (``pinned_launch_instructions`` of the summary: pinned by code when they were read). The
library's own rule (``retain_inherited_selection``: a child may add instructions and cannot replace the parent's pins)
admits the result."""
from episode_runtime import ChildMessage

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    retain_inherited_selection)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_return_contracts import (
    BLAST_GRADED_REQUEST_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    API_SERVICE_ASSIGNMENT_VERSION)

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


def _api_job(request):
    """The query subject of an API request and the parameters of the service's request it fixes, by its form:
    the BLAST database grader request names the query and, when it constrains one, the database; a service
    assignment carries the service's own request (its ``subject_ref`` is the query, every other member is fixed);
    an execution assignment names the query, the algorithm (the service's ``program``) and the database."""
    if request['version'] == BLAST_GRADED_REQUEST_VERSION:
        return request['query_subject_ref'], {name: request[name] for name in ('database',) if name in request}
    if request['version'] == API_SERVICE_ASSIGNMENT_VERSION:
        fixed = dict(request['request'])
        return fixed.pop('subject_ref'), fixed
    return request['subject_ref'], {'program': request['algorithm'], 'database': request['database']}


def msg_to_child(slot, arguments, summary):
    resource_id = arguments['resource_id']
    request = _request(summary, arguments)
    if slot == 'launch_api':
        resource, = (value for value in summary['capabilities']['execution_resource_capabilities']
                     if value['resource_id'] == resource_id)
        query, fixed = _api_job(request)
        assignment = {'resource_id': resource_id, 'service': resource['service'], 'query_subject_refs': [query],
                      'input_refs': [ref for ref in summary['record_refs'] if ref != query],
                      'fixed_request': fixed, 'completion_target': summary['handoff_unit']}
        if 'launch_instructions' in request:
            assignment['launch_instructions'] = request['launch_instructions']
        return ChildMessage(
            objective='Establish the requested usable handoff of the job on the API resource ' + resource_id,
            message={'resource_id': resource_id}, assignment=assignment, selection=SELECTION)
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
