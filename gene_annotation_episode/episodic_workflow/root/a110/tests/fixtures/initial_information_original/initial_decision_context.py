"""Exact captured original callback; test-only comparison asset."""
def initial_decision_context(self, context):
    if self.local_file_sources.applies(context):
        target = self._target(context)
        return {'execution_resource_capabilities': [{'resource_id': target['resource_id'],
            'resource_kind': 'local'}], 'execution_initial_information': {}}
    return {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources],
        'execution_initial_information': deepcopy(self.initial_information)}
