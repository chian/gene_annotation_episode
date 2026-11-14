"""Original raw selected service catalogue invocation."""
from ..communication import plain

def standalone_api_catalog(api, context):
    assignment, service, target = api._context(context)
    return service.launch_catalog(assignment['request']) if target is None else service.result_catalog(assignment['request'], plain(context.assignment)['selector'])
