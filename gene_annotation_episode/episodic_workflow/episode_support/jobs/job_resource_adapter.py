"""A resource adapter over one resource of the ``job_access`` service.

``JobResourceAdapter`` binds one resource id of the run's ``ResourceAdapters`` service
(``episode_runtime/resource_adapters.py``, which states the adapter protocol) to the same route the run's
``JobAccess`` service holds for it. Its tools are the four operations of a job: ``job.launch``, ``job.check``,
``job.fetch`` and ``job.cancel``. Each is one call of the job-access service with the tool's ``ctx``, so the job's
handoff, check and closure rows are written through ``ctx.store`` and held by the Episode, and a unit that runs
again takes over its abandoned row instead of launching again.

The capability is the caller's declaration of the resource (it is configuration: this adapter reports it and adds
nothing). A handoff is ``{'resource_selection': {'resource_id': ...}, 'handoff_ref': <the held handoff row>}``;
its receiving check is one status request (``job.check``).
"""
from __future__ import annotations

from method_loop.jsonvalue import closed_copy


def _object(properties, required):
    return {'type': 'object', 'additionalProperties': False, 'required': list(required), 'properties': properties}


_REF = {'type': 'string', 'minLength': 1}
CATALOG = (
    {'name': 'job.launch', 'description': 'Submit one job on this resource and return at handoff.',
     'input_schema': _object({'job': {'type': 'object'}, 'inputs': {'type': 'object', 'additionalProperties': _REF},
                              'estimates': {}}, ('job', 'inputs', 'estimates'))},
    {'name': 'job.check', 'description': 'One status request for a job this Episode holds the handoff of.',
     'input_schema': _object({'handoff_ref': _REF}, ('handoff_ref',))},
    {'name': 'job.fetch', 'description': 'Fetch the result files of a job that has ended and close it.',
     'input_schema': _object({'handoff_ref': _REF, 'names': {'type': ['array', 'null'], 'items': _REF}},
                             ('handoff_ref', 'names'))},
    {'name': 'job.cancel', 'description': 'Cancel a job and close it.',
     'input_schema': _object({'handoff_ref': _REF}, ('handoff_ref',))},
)


class JobResourceAdapter:
    """The resource ``capability['resource_id']`` of ``job_access``, as a resource adapter."""

    def __init__(self, job_access, capability):
        self._jobs = job_access
        self._capability = closed_copy(capability, 'resource_capability', TypeError)
        self.resource_id = self._capability['resource_id']
        self._jobs.describe(self.resource_id)       # the resource must be bound in the job-access service

    def capability(self):
        return closed_copy(self._capability, 'resource_capability', TypeError)

    def catalog(self, assignment):
        return [dict(entry) for entry in CATALOG]

    def facts(self, assignment):
        return {'resource': self._jobs.describe(self.resource_id)}

    def decision_context(self, assignment):
        return {'resource': self._jobs.describe(self.resource_id), 'capability': self.capability()}

    def prepare_assignment(self, ctx, assignment):
        """The assignment with the resource it selected described: nothing is reserved or submitted."""
        return {**assignment, 'resource': self._jobs.describe(self.resource_id)}

    def execute(self, ctx, assignment, tool, arguments):
        if tool == 'job.launch':
            return self._jobs.launch(ctx, self.resource_id, arguments['job'], inputs=arguments['inputs'],
                                     estimates=arguments['estimates'])
        if tool == 'job.check':
            return self._jobs.check(ctx, arguments['handoff_ref'])
        if tool == 'job.fetch':
            return self._jobs.fetch(ctx, arguments['handoff_ref'], names=arguments['names'])
        if tool == 'job.cancel':
            return self._jobs.cancel(ctx, arguments['handoff_ref'])
        raise LookupError('job_resource_tool_unknown:' + str(tool))

    def check_handoff(self, ctx, handoff):
        return self._jobs.check(ctx, handoff['handoff_ref'])


__all__ = ['CATALOG', 'JobResourceAdapter']
