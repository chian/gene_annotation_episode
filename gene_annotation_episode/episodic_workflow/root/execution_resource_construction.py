"""Construct the actual selected fixed transport owner for each original resource."""
from .execution_job_submission.local_job_execution.resource import LocalResourceExecution
from .execution_job_submission.hpc_job_execution.resource import HPCResourceExecution

def resource_execution(services, *, resource_kind, directory, resources, store, initial_information):
    if resource_kind=='local':
        return LocalResourceExecution(services,directory=directory,resources=resources,store=store,initial_information=initial_information)
    if resource_kind=='hpc':
        return HPCResourceExecution(services,directory=directory,resources=resources,store=store,initial_information=initial_information)
    raise ValueError('execution_resource_kind_invalid')
