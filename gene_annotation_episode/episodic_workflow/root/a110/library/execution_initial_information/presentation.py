"""Own-axis recorded resource and received-value presentation; selects no work."""
from ..execution_resource_information import resource_information_for_id, execution_capabilities
from copy import deepcopy
import json
KINDS = {'local': 'local', 'pbs_ssh': 'hpc'}

class RecordedExecutionInformation:
    def __init__(self, readers):
        self.readers = readers
        self.resources = deepcopy(readers.factory_record["resources"])
        self.initial_information = deepcopy(readers.factory_record["initial_information"])
        self.store, self.run_id = readers.store, readers.run_id

    _resource_information = resource_information_for_id

    capabilities = execution_capabilities

def resource_information(readers):
    value = RecordedExecutionInformation(readers)
    return {'execution_resource_capabilities': [value._resource_information(key) for key in value.resources],
        'execution_initial_information': deepcopy(value.initial_information)}
