"""Private root annotation yield parameters."""
from __future__ import annotations
from collections.abc import Mapping

def _category_yield_parameters(controller_binding):
    """Read explicit yield operands from the supported controller layouts.

    This binds the separate category table's fit only. Caller identity wrappers
    add one declared definition layer; arbitrary custom definitions are not
    searched for numbers or interpreted as the existing yield controller.
    """
    if not isinstance(controller_binding, Mapping):
        return None
    definition = controller_binding.get('definition')
    if not isinstance(definition, Mapping):
        return None
    keys = ('window_size', 'subsample_size', 'uncertainty_alpha')
    if 'version' not in definition and 'uncertainty_alpha' in definition:
        parameters = definition
    else:
        versions = ('existing_yield_controller_explicit_parameters_v1', 'existing_yield_controller_explicit_role_costs_v2', 'existing_yield_controller_explicit_role_costs_v3')
        if definition.get('version') not in versions:
            definition = definition.get('definition')
        if not isinstance(definition, Mapping) or definition.get('version') not in versions:
            return None
        parameters = definition.get('parameters')
    if not isinstance(parameters, Mapping) or 'uncertainty_alpha' not in parameters:
        return None
    return {key: parameters[key] for key in keys if key in parameters}
