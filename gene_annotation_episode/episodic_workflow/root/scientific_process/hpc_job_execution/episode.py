"""Original fixed hpc execution episode responsibilities; source candidate."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.communication import plain
from ...practical_execution_records import ASSIGNMENT_SCHEMA

from .execution_state import HPCExecutionState
from .instructions import HPCInstructions
from .operations import HPCCommandActions
from .to_parent import HPCToParent
from .from_parent import HPCFromParent
from .goal import HPCGoal
from .internal_summary import HPCSummary
from .credit import HPCCredit
from importlib import import_module
HPCYield = import_module('.yield', __package__).HPCYield
from .task import HPCTask

VERSION = 'root_scientific_process_hpc_terminal_execution_v1'


class HPCEpisodeBinding(HPCFromParent, HPCGoal, HPCSummary, HPCExecutionState, HPCInstructions, HPCCommandActions, HPCToParent, HPCCredit, HPCYield):
    binding_path = 'scientific_process/hpc_job_execution'
    decision_source_type = HPCTask
    commissioning_parent = 'scientific_process'
    resource_kind = 'hpc'

    def __init__(self, services, *, directory, resources, store=None,
                 initial_information=None, flux_balance_input_reader=None):
        self.services,self.directory,self.store=services,Path(directory),store
        self.resources=json.loads(json.dumps(plain(resources),allow_nan=False))
        if not self.resources or not set(self.resources)<={'local','hpc'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information=plain(initial_information or {})
        if not set(self.initial_information)<=set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        # Inventory is historical resource context. It does not define a menu of
        # allowed job stages and is not an observation of current usability.
        if 'hpc' not in self.resources:
            raise ValueError('root_hpc_terminal_resource_required')
        self.roles=('launch_hpc',)
        self.entry_roles=()
        self._states={}

    def as_record(self):
        return {'binding_id':'root_scientific_process_hpc_terminal_execution','version':VERSION,
            'configuration':{'resources':deepcopy(self.resources),
                'initial_information':deepcopy(self.initial_information)}}

    def child_roles(self,role):return ()

    def credit_kind(self,role):return 'operational'

    def permitted_common_actions(self,context):return ('tool',)

    def allowed_children(self,parent,caller_capabilities):return ()

