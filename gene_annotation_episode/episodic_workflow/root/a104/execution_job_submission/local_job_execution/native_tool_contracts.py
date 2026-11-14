"""Private original A104 LocalExecution service native_tool_contracts."""
from __future__ import annotations

def operation_catalog(kind):
    """General execution capability, identical for every resource."""
    if kind not in {'local', 'hpc'}:
        raise ValueError('execution_resource_kind_invalid')
    return [{'name': 'exec_command', 'description': 'Execute the shell command you write on the assigned resource. Use normal shell/file tools to inspect files, author scripts, prepare an environment, run software, or submit/observe the actual job as needed. Returns its actual output and saved action receipt. workdir and env apply to this command; select them explicitly on each action.', 'input_schema': {'type': 'object', 'properties': {'cmd': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]}, 'workdir': {'type': 'string', 'minLength': 1}, 'target': {'type': 'string', 'enum': ['resource', 'coordinator'], 'description': 'Assigned resource (default), or local coordinator run directory for input-file work.'}, 'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}}, 'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}}]
