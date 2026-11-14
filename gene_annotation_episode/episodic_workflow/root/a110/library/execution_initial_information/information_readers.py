"""Candidate: narrow, factory-declared read ports for A110 initial information.

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

from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.a110.state import Store
from gene_annotation_episode.episodic_workflow.root.a110.execution_progress import ExecutionProgressProvider
from gene_annotation_episode.episodic_workflow.root.a110.method_loop.identities import EpisodeRef


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
                    'gene_annotation_episode.episodic_workflow.root.a110.execution_service_setup.ExecutionServiceFactory'
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
                    or not (row['path'].startswith('gene_annotation_episode/episodic_workflow/root/a110/') or row['path'] == 'gene_annotation_episode/workflow_budget.py')
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

    def authenticate_context_identity(self, context):
        if (context.run_id != self.run_id or context.role != context.path[-1][0]
                or EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('initial_information_receiver_identity_conflict')
        # Scientific record custody is still authenticated by the original
        # return/API reader. Identity validation does not grant received facts.

    def as_record(self):
        self.validate_original_setup(_copy(self.factory.as_record()))
        return {'version': 'factory_information_readers_v1', 'axis': 'A110',
            'run_id': self.run_id, 'directory': str(self.directory),
            'construction': deepcopy(self.construction_record),
            'implementation': deepcopy(self.implementation_record),
            'progress_binding': _copy(self.job_progress_provider.as_record()),
            'ports': {name: None if getattr(self, name) is None else _identity(getattr(self, name))
                for name in ()}}
