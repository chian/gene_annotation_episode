"""The original selected hpc command and receipt owner; no episode dispatcher."""
from pathlib import Path
import json
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .resource_execution_state import HPCExecutionState
from .resource_instructions import HPCInstructions
from .resource_operations import HPCCommandActions
from .resource_to_parent import HPCToParent
from .resource_progress import HPCProgress

class HPCResourceExecution(HPCExecutionState, HPCInstructions, HPCCommandActions, HPCToParent, HPCProgress):
    def __init__(self, services, *, directory, resources, store=None, initial_information=None):
        self.services,self.directory,self.store=services,Path(directory),store
        self.resources=json.loads(json.dumps(plain(resources),allow_nan=False))
        if not self.resources or set(self.resources)!={'hpc'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information=plain(initial_information or {})
        if not set(self.initial_information)<=set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        self._states={}
