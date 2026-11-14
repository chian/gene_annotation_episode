"""Original explicit raw API context reader for service clients and cross-context reads."""
from ..communication import plain

def standalone_api_context(api, context, *, verify_artifacts=True, _completed_appservice_download=False):
    if context.run_id != api.run_id:
        raise ValueError('api_execution_run_conflict')
    if context.role == 'launch_api':
        assignment = api.validate_assignment(context.assignment, scope=context.scope)
        return (assignment, api.services[assignment['resource_id']], None)
    if context.role != 'results':
        raise ValueError('api_execution_role_required')
    raw = plain(context.assignment)
    if set(raw) != {'version', 'handoff_ref', 'selector'} or raw['version'] != 'execution_results_assignment_v1':
        raise ValueError('invalid_api_results_assignment')
    target = api.read_target(raw['handoff_ref'], context.scope, verify_artifacts=verify_artifacts, **{'_completed_appservice_download': True} if _completed_appservice_download else {})
    api.validate_result_selector(target, raw['selector'])
    return (target['assignment'], api.services[target['resource_id']], target)
