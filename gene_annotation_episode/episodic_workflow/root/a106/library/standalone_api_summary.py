"""Original raw API decision-summary protocol; no role-based owner selection."""

def standalone_api_summary(api, context, current_view=None):
    api.initialize(context)
    assignment, service, target = api._context(context)
    latest = {}
    for row in api._events(context.episode_id):
        latest[row['name']] = {'state': row['event']['state'], 'kind': row['event']['kind'], 'facts': row['event']['facts'], 'failure_code': row['event']['failure_code']}
    return {'api_service': service.service, 'api_request': assignment['request'], 'api_received_progress': latest, 'api_execution_completed': api._completion(context) is not None}
