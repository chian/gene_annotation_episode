"""Original parent Launch form, independently admitted by this private child."""
from .execution_contracts import INPUT_VERSION_SCHEMA, LAUNCH_VERSION, SELECTION_SCHEMA, deepcopy, launch_request_schema, obj

class LaunchParentAssignment:

    def _parent_launch_assignment_schema(self, *, internal=False):
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: launch_request_schema(self._request_schema(key, selected=False, internal=internal, compact=False), key, self.resources[key].get('service')) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        return schema
