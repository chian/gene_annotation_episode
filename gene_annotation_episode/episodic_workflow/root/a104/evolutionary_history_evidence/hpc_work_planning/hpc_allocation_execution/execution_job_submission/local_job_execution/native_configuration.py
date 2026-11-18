"""Private original A104 LocalExecution service native_configuration."""
from __future__ import annotations
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a104.library.native_terminal_transport import TerminalExecution
from .native_resource_contracts import VERSION
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class LocalExecutionNativeConfiguration:

    def __init__(self, services, *, directory, resources, store=None, initial_information=None):
        self.services, self.directory, self.store = (services, Path(directory), store)
        self.resources = json.loads(json.dumps(plain(resources), allow_nan=False))
        if not self.resources or not set(self.resources) <= {'local', 'hpc'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information = plain(initial_information or {})
        if not set(self.initial_information) <= set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        self._states = {}

    def _operations(self, kind):
        from gene_annotation_episode.episodic_workflow.root.a104.terminal_scientific_evidence import terminal_artifact_paths
        return TerminalExecution(self.resources[kind], coordinator_workspace=self.directory, artifact_selector=terminal_artifact_paths)

    def as_record(self):
        return {'binding_id': 'terminal_execution', 'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information)}}
