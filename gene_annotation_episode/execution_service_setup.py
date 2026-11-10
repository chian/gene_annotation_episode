"""Explicit, reconstructible caller operands for the wired execution family."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import json
import math
from types import MappingProxyType

from .communication import plain
from .episode_application_services import EpisodeApplicationServices
from .episode_monitoring import MonitorEpisodes, read_progress
from .episode_progress_credit import ProgressInformationCredit


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class _ProgressReader:
    store: object
    run_id: str

    def read_progress(self, reference, scope):
        return read_progress(self.store, self.run_id, reference, scope)


@dataclass(frozen=True)
class ExecutionServiceFactory:
    resources: dict
    initial_information: dict
    handoff_unit: float
    acquired_record_unit: float
    monitoring_information_unit: float
    log_window_bytes: int = 8192
    log_roles: tuple = ('stdout', 'stderr')
    monitor_outcome_page_size: int = 20
    protein_structure_environments: tuple = ()
    flux_balance_environments: tuple = ()
    molecular_sequence_environments: tuple = ()
    molecular_sequence_saved_modes: bool = False
    homer_environments: tuple = ()
    homer_saved_modes: bool = False
    tf_binding_environments: tuple = ()
    tf_binding_saved_modes: bool = False
    protease_kinetics_environments: tuple = ()
    protease_kinetics_saved_modes: bool = False
    protein_conservation_environments: tuple = ()
    protein_conservation_saved_modes: bool = False
    protein_phylogeny_environments: tuple = ()
    protein_phylogeny_saved_modes: bool = False
    somatic_variant_environments: tuple = ()
    somatic_variant_saved_modes: bool = False
    esm_gene_embedding_environments: tuple = ()
    esm_gene_embedding_stored_reads: bool = False
    hpc_commissions: dict | None = None
    shared_execution_memory: dict | None = None

    def __post_init__(self):
        if self.shared_execution_memory is not None:
            from .execution_memory import ExecutionMemory
            object.__setattr__(self, 'shared_execution_memory', _freeze(
                ExecutionMemory(**plain(self.shared_execution_memory)).as_record()))
        if self.hpc_commissions is not None:
            from .hpc_campaign import validate_commission
            commissions = plain(self.hpc_commissions)
            # An explicit empty catalog enables authenticated received work.
            # None still leaves the HPC service unconfigured.
            if not isinstance(commissions, dict):
                raise ValueError('explicit_hpc_commissions_required')
            object.__setattr__(self, 'hpc_commissions', _freeze({key: validate_commission(value, plain(self.resources))
                for key, value in commissions.items()}))
        if type(self.molecular_sequence_saved_modes) is not bool:
            raise ValueError('explicit_molecular_sequence_saved_modes_boolean_required')
        if type(self.homer_saved_modes) is not bool:
            raise ValueError('explicit_homer_saved_modes_boolean_required')
        if type(self.tf_binding_saved_modes) is not bool:
            raise ValueError('explicit_tf_binding_saved_modes_boolean_required')
        if type(self.protease_kinetics_saved_modes) is not bool:
            raise ValueError('explicit_protease_kinetics_saved_modes_boolean_required')
        if type(self.protein_conservation_saved_modes) is not bool:
            raise ValueError('explicit_protein_conservation_saved_modes_boolean_required')
        if type(self.protein_phylogeny_saved_modes) is not bool:
            raise ValueError('explicit_protein_phylogeny_saved_modes_boolean_required')
        if type(self.somatic_variant_saved_modes) is not bool:
            raise ValueError('explicit_somatic_variant_saved_modes_boolean_required')
        if type(self.esm_gene_embedding_stored_reads) is not bool:
            raise ValueError('explicit_esm_gene_embedding_stored_reads_boolean_required')
        for name in ('resources', 'initial_information'):
            value = json.loads(json.dumps(plain(getattr(self, name)), allow_nan=False))
            if not isinstance(value, dict) or name == 'resources' and not value:
                raise ValueError('explicit_execution_resources_required')
            object.__setattr__(self, name, _freeze(value))
        for name in ('handoff_unit', 'acquired_record_unit', 'monitoring_information_unit'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('explicit_positive_execution_information_units_required')
        for name in ('log_window_bytes', 'monitor_outcome_page_size'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError('explicit_positive_execution_window_required')
        roles = tuple(self.log_roles)
        if (not roles or any(not isinstance(role, str) or not role for role in roles)
                or len(set(roles)) != len(roles)):
            raise ValueError('explicit_execution_log_roles_required')
        object.__setattr__(self, 'log_roles', roles)
        for family in ('protein_structure', 'flux_balance', 'molecular_sequence', 'homer', 'tf_binding', 'protease_kinetics', 'protein_conservation', 'protein_phylogeny', 'somatic_variant', 'esm_gene_embedding'):
            name = family + '_environments'
            environments = json.loads(json.dumps(plain(getattr(self, name)), allow_nan=False))
            if not isinstance(environments, list):
                raise ValueError('explicit_' + family + '_environment_table_required')
            object.__setattr__(self, name, _freeze(environments))

    def as_record(self):
        return {'version': 'execution_service_factory_v1',
            **{name: plain(getattr(self, name)) for name in (
                'resources', 'initial_information', 'handoff_unit', 'acquired_record_unit',
                'monitoring_information_unit', 'log_window_bytes', 'log_roles',
                'monitor_outcome_page_size')},
            **({'protein_structure_environments': plain(self.protein_structure_environments)}
               if self.protein_structure_environments else {}),
            **({'flux_balance_environments': plain(self.flux_balance_environments)}
               if self.flux_balance_environments else {}),
            **({'molecular_sequence_environments': plain(self.molecular_sequence_environments)}
               if self.molecular_sequence_environments else {}),
            **({'molecular_sequence_saved_modes': True}
               if self.molecular_sequence_saved_modes else {}),
            **({'homer_environments': plain(self.homer_environments)}
               if self.homer_environments else {}),
            **({'homer_saved_modes': True} if self.homer_saved_modes else {}),
            **({'tf_binding_environments': plain(self.tf_binding_environments)}
               if self.tf_binding_environments else {}),
            **({'tf_binding_saved_modes': True} if self.tf_binding_saved_modes else {}),
            **({'protease_kinetics_environments': plain(self.protease_kinetics_environments)}
               if self.protease_kinetics_environments else {}),
            **({'protease_kinetics_saved_modes': True} if self.protease_kinetics_saved_modes else {}),
            **({'protein_conservation_environments': plain(self.protein_conservation_environments)}
               if self.protein_conservation_environments else {}),
            **({'protein_conservation_saved_modes': True} if self.protein_conservation_saved_modes else {}),
            **({'protein_phylogeny_environments': plain(self.protein_phylogeny_environments)}
               if self.protein_phylogeny_environments else {}),
            **({'protein_phylogeny_saved_modes': True} if self.protein_phylogeny_saved_modes else {}),
            **({'somatic_variant_environments': plain(self.somatic_variant_environments)}
               if self.somatic_variant_environments else {}),
            **({'somatic_variant_saved_modes': True} if self.somatic_variant_saved_modes else {}),
            **({'esm_gene_embedding_environments': plain(self.esm_gene_embedding_environments)}
               if self.esm_gene_embedding_environments else {}),
            **({'esm_gene_embedding_stored_reads': True} if self.esm_gene_embedding_stored_reads else {}),
            **({'hpc_commissions': plain(self.hpc_commissions)} if self.hpc_commissions is not None else {}),
            **({'shared_execution_memory': plain(self.shared_execution_memory)}
               if self.shared_execution_memory is not None else {})}

    @classmethod
    def from_record(cls, value):
        value = plain(value)
        if not isinstance(value, dict) or value.get('version') != 'execution_service_factory_v1':
            raise ValueError('invalid_execution_service_factory')
        return cls(**{key: item for key, item in value.items() if key != 'version'})

    def configure_tool_registry(self, tool_registry):
        """Configure actual ordinary tools before freezing their callable catalog."""
        if self.shared_execution_memory is not None and tool_registry is not None:
            from .execution_memory import ExecutionMemory
            tool_registry.execution_memory = ExecutionMemory(**plain(self.shared_execution_memory))
        for family in ('protein_structure', 'flux_balance', 'molecular_sequence', 'homer', 'tf_binding', 'protease_kinetics', 'protein_conservation', 'protein_phylogeny', 'somatic_variant'):
            environments = getattr(self, family + '_environments')
            saved_modes = (getattr(self, family + '_saved_modes')
                           if family in ('molecular_sequence', 'homer', 'tf_binding', 'protease_kinetics', 'protein_conservation', 'protein_phylogeny', 'somatic_variant') else False)
            configure = getattr(tool_registry, 'configure_' + family + '_resources', None)
            if not callable(configure):
                if environments or saved_modes:
                    raise ValueError('actual_' + family + '_tool_registry_required')
                continue
            if saved_modes:
                configure(plain(self.resources), plain(environments), saved_modes=True)
            else:
                configure(plain(self.resources), plain(environments))
        configure_esm = getattr(tool_registry, 'configure_esm_gene_embedding_resources', None)
        if not callable(configure_esm):
            if self.esm_gene_embedding_environments or self.esm_gene_embedding_stored_reads:
                raise ValueError('actual_esm_gene_embedding_tool_registry_required')
        else:
            configure_esm(plain(self.resources), plain(self.esm_gene_embedding_environments),
                stored_reads=self.esm_gene_embedding_stored_reads)

    def __call__(self, store, *, run_id, directory, job_episodes=None,
                 resource_estimator=None, tool_registry=None, tool_catalog=None):
        from .execution_episodes import ExecutionEpisodes
        self.configure_tool_registry(tool_registry)
        binding = ExecutionEpisodes(None, store=store, run_id=run_id, directory=directory,
            resources=plain(self.resources), initial_information=plain(self.initial_information),
            tool_registry=tool_registry, handoff_unit=self.handoff_unit,
            acquired_record_unit=self.acquired_record_unit,
            log_window_bytes=self.log_window_bytes, log_roles=self.log_roles)
        monitor = MonitorEpisodes(None, outcome_page_size=self.monitor_outcome_page_size)
        information = ProgressInformationCredit(_ProgressReader(store, run_id),
            information_unit=self.monitoring_information_unit)
        definition = {'version': 'execution_received_information_credit_v1',
            'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit,
            'practical_units': 'original_assignment_progress_requirements',
            'baseline': 'original_received_information', 'repeated_gain': 0}
        resource_catalogs = {}
        for row in binding.resource_tool_contracts():
            resource_catalogs.setdefault(row['resources'], []).append(row)
        descriptors = [binding.as_record(), monitor.as_record()]
        hpc_credit = {}
        if self.hpc_commissions is not None:
            from .hpc_episodes import HPCEpisodes
            hpc = HPCEpisodes(None, store=store, run_id=run_id, directory=directory,
                resources=plain(self.resources), commissions=plain(self.hpc_commissions),
                shared_execution_memory=plain(self.shared_execution_memory))
            descriptors.append(hpc.as_record())
            hpc_credit = {role: {'definition': {'version': 'hpc_credit_v1',
                'operands': 'original_commission', 'polling_credit': 0}, 'project': hpc.credit_view}
                for role in hpc.roles}
        return EpisodeApplicationServices(tuple(descriptors), {
            **{role: {'definition': deepcopy(definition), 'project': binding.project_credit}
               for role in binding.roles},
            'monitor': {'definition': information.as_record(), 'project': information}, **hpc_credit},
            binding.job_progress_provider, resource_tool_catalogs=resource_catalogs)


__all__ = ['ExecutionServiceFactory']
