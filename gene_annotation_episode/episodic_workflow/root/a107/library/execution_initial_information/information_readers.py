"""Candidate: narrow, factory-declared read ports for A107 initial information.

Reader construction stays explicit at the original factory setup site. This
object owns no episode registration, task, action selector, native observation,
receipt admission, or yield operation. Recipient functions select its read ports.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import hashlib
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.a107.state import Store
from gene_annotation_episode.episodic_workflow.root.a107.execution_progress import ExecutionProgressProvider
from gene_annotation_episode.episodic_workflow.root.a107.method_loop.identities import EpisodeRef


def _copy(value):
    return json.loads(json.dumps(plain(value), sort_keys=True, allow_nan=False))


def _identity(value):
    cls = type(value)
    return cls.__module__ + '.' + cls.__qualname__


@dataclass(frozen=True)
class FactoryInformationReaders:
    factory: ExecutionServiceFactory
    store: Store
    run_id: str
    directory: Path
    job_progress_provider: ExecutionProgressProvider
    api_execution: object | None
    native_rna_structure_returns: object | None
    rna_structure_comparison_returns: object | None
    # The setup declaration names the literal source constructor and the full
    # original factory record. It is not inferred from any callback result.
    construction_record: dict
    implementation_record: dict

    def validate_original_setup(self, factory_record):
        if type(self.factory) is not ExecutionServiceFactory or type(self.store) is not Store:
            raise TypeError('initial_information_actual_axis_setup_required')
        if (not isinstance(self.run_id, str) or not self.run_id
                or not isinstance(self.directory, Path) or not self.directory.is_absolute()):
            raise ValueError('initial_information_run_directory_required')
        definition = _copy(self.factory.as_record())
        if definition != _copy(factory_record):
            raise ValueError('initial_information_factory_record_changed')
        if (not isinstance(self.construction_record, dict)
                or set(self.construction_record) != {'version', 'constructor', 'factory_definition'}
                or self.construction_record['version'] != 'factory_information_reader_construction_v1'
                or self.construction_record['constructor'] !=
                    'gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup.ExecutionServiceFactory'
                or self.construction_record['factory_definition'] != definition):
            raise ValueError('initial_information_factory_construction_provenance_required')
        # A full source inventory is supplied by the audited original setup.
        # Missing source custody fails; an arbitrary empty fingerprint is not
        # treated as a compatibility declaration.
        if (not isinstance(self.implementation_record, dict)
                or set(self.implementation_record) != {'version', 'sources'}
                or self.implementation_record['version'] != 'initial_information_reader_sources_v1'
                or not isinstance(self.implementation_record['sources'], list)
                or not self.implementation_record['sources']):
            raise ValueError('initial_information_reader_source_custody_required')
        seen = set()
        for row in self.implementation_record['sources']:
            if (not isinstance(row, dict) or set(row) != {'path', 'sha256'}
                    or not isinstance(row['path'], str)
                    or not (row['path'].startswith('gene_annotation_episode/episodic_workflow/root/a107/') or row['path'] == 'gene_annotation_episode/workflow_budget.py')
                    or row['path'] in seen or not isinstance(row['sha256'], str)
                    or len(row['sha256']) != 64
                    or any(c not in '0123456789abcdef' for c in row['sha256'])):
                raise ValueError('initial_information_reader_source_custody_required')
            seen.add(row['path'])
            if '..' in Path(row['path']).parts:
                raise ValueError('initial_information_reader_source_custody_required')
            roots = [parent for parent in Path(__file__).resolve().parents
                if (parent / 'gene_annotation_episode').is_dir()]
            if not roots or hashlib.sha256((roots[0] / row['path']).read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('initial_information_reader_implementation_changed')
        self._validate_axis_ports(definition)

    @property
    def factory_record(self):
        return _copy(self.factory.as_record())

    def _validate_axis_ports(self, definition):
        progress = self.job_progress_provider
        if (type(progress) is not ExecutionProgressProvider or progress.store is not self.store
                or progress.run_id != self.run_id or progress.directory != self.directory
                or _copy(progress.resources) != definition['resources']
                or progress.log_window_bytes != definition['log_window_bytes']
                or list(progress.log_roles) != definition['log_roles']):
            raise ValueError('initial_information_original_progress_reader_required')
        from gene_annotation_episode.episodic_workflow.root.a107.api_service_execution import APIServiceExecution
        from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_returns import NativeRNAStructureReturns
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_returns import RNAStructureComparisonReturns
        configured_api = {key: row for key, row in definition['resources'].items()
            if row['kind'] in {'api', 'hmmer_api'}}
        if bool(configured_api) != (self.api_execution is not None):
            raise ValueError('initial_information_original_api_reader_required')
        if self.api_execution is not None:
            api = self.api_execution
            if (type(api) is not APIServiceExecution or api.store is not self.store
                    or api.run_id != self.run_id or _copy(api.configuration) != configured_api
                    or api.tools.store is not self.store
                    or api.handoff_unit != definition['handoff_unit']
                    or api.acquired_record_unit != definition['acquired_record_unit']
                    or progress.targets.api_execution is not api):
                raise ValueError('initial_information_original_api_reader_required')
        configured_rna = any(row.get('native_rna_structure') for row in definition['resources'].values())
        if configured_rna != (self.native_rna_structure_returns is not None):
            raise ValueError('initial_information_original_rna_reader_required')
        if configured_rna != (self.rna_structure_comparison_returns is not None):
            raise ValueError('initial_information_original_rna_comparison_reader_required')
        if configured_rna:
            original, comparison = self.native_rna_structure_returns, self.rna_structure_comparison_returns
            if (type(original) is not NativeRNAStructureReturns
                    or type(comparison) is not RNAStructureComparisonReturns
                    or original.store is not self.store or original.run_id != self.run_id
                    or comparison.store is not self.store or comparison.run_id != self.run_id
                    or comparison.original is not original
                    or original.owner is not comparison.owner
                    or original.owner.job_progress_provider is not progress
                    or original.owner.directory != self.directory
                    or _copy(original.owner.resources) != definition['resources']):
                raise ValueError('initial_information_original_rna_reader_required')

    def authenticate_context_identity(self, context):
        if (context.run_id != self.run_id or context.role != context.path[-1][0]
                or EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('initial_information_receiver_identity_conflict')
        # Scientific record custody is still authenticated by the original
        # return/API reader. Identity validation does not grant received facts.

    def as_record(self):
        self.validate_original_setup(_copy(self.factory.as_record()))
        return {'version': 'factory_information_readers_v1', 'axis': 'A107',
            'run_id': self.run_id, 'directory': str(self.directory),
            'construction': deepcopy(self.construction_record),
            'implementation': deepcopy(self.implementation_record),
            'progress_binding': _copy(self.job_progress_provider.as_record()),
            'ports': {name: None if getattr(self, name) is None else _identity(getattr(self, name))
                for name in ('api_execution', 'native_rna_structure_returns', 'rna_structure_comparison_returns')}}
