"""The original selected local command and receipt owner; no episode dispatcher."""
from pathlib import Path
import json
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .resource_execution_state import LocalExecutionState
from .resource_instructions import LocalInstructions
from .resource_operations import LocalCommandActions
from .resource_to_parent import LocalToParent
from .resource_progress import LocalProgress

class LocalResourceExecution(LocalExecutionState, LocalInstructions, LocalCommandActions, LocalToParent, LocalProgress):
    def __init__(self, services, *, directory, resources, store=None, initial_information=None):
        self.services,self.directory,self.store=services,Path(directory),store
        self.resources=json.loads(json.dumps(plain(resources),allow_nan=False))
        if not self.resources or set(self.resources)!={'local'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information=plain(initial_information or {})
        if not set(self.initial_information)<=set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        self._states={}
