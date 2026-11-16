"""Ordinary-tool methods: tool_resource_configuration."""
from __future__ import annotations
import json
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical

class ToolResourceConfiguration:
    def configure_protein_structure_resources(self, resources, environments):
        """Bind explicit ordinary operations without probing or executing them."""
        from .library.protein_structure_tools import normalize_protein_structure_configuration
        selected = normalize_protein_structure_configuration(
            resources, environments, policy=self.local_job_policy)
        if selected is None:
            return
        selected = json.loads(canonical(selected))
        if (self._protein_structure_configuration is not None
                and canonical(self._protein_structure_configuration) != canonical(selected)):
            raise ContractError('protein_structure_configuration_changed')
        self._protein_structure_configuration = selected

    def configure_flux_balance_resources(self, resources, environments):
        """Bind the explicitly selected ordinary FBA software and environment."""
        from .library.flux_balance_tools import OrdinaryFluxBalanceTools, normalize_flux_balance_configuration
        selected = normalize_flux_balance_configuration(resources, environments, self.local_job_policy)
        if selected is None:
            return
        selected = json.loads(canonical(selected))
        if self._flux_balance_configuration is not None and canonical(self._flux_balance_configuration) != canonical(selected):
            raise ContractError('flux_balance_configuration_changed')
        self._flux_balance_configuration = selected
        if self.ordinary_flux_balance_backend is None:
            self.ordinary_flux_balance_backend = OrdinaryFluxBalanceTools(self)

    def configure_molecular_sequence_resources(self, resources, environments, *, saved_modes=False):
        """Bind the caller's explicit ordinary sequence operation selection."""
        from .library.molecular_sequence_tools import OrdinaryMolecularSequenceTools, normalize_molecular_sequence_configuration
        if type(saved_modes) is not bool:
            raise ContractError('explicit_molecular_sequence_saved_modes_boolean_required')
        selected = normalize_molecular_sequence_configuration(resources, environments, self.local_job_policy)
        if (self._molecular_sequence_saved_modes is not None
                and self._molecular_sequence_saved_modes != saved_modes):
            raise ContractError('molecular_sequence_saved_modes_changed')
        if selected is None and not saved_modes:
            return
        selected = json.loads(canonical(selected))
        if (self.ordinary_molecular_sequence_backend is not None
                and canonical(self._molecular_sequence_configuration) != canonical(selected)):
            raise ContractError('molecular_sequence_configuration_changed')
        self._molecular_sequence_configuration = selected
        self._molecular_sequence_saved_modes = saved_modes
        if self.ordinary_molecular_sequence_backend is None:
            self.ordinary_molecular_sequence_backend = OrdinaryMolecularSequenceTools(
                self, configuration=selected, saved_modes=saved_modes)

    def configure_homer_resources(self, resources, environments, *, saved_modes=False):
        """Freeze the caller's explicit ordinary HOMER resource selection."""
        if type(saved_modes) is not bool:
            raise ContractError('explicit_homer_saved_modes_boolean_required')
        if self._homer_configuration is None and not environments and not saved_modes:
            return
        from gene_annotation_episode.episodic_workflow.root.library.homer_motif_tools import normalize_homer_configuration
        selected = normalize_homer_configuration(resources, environments,
            policy=self.local_job_policy.to_dict())
        selected = json.loads(canonical(selected))
        selected['saved_modes'] = saved_modes
        if (self._homer_configuration is not None
                and canonical(self._homer_configuration) != canonical(selected)):
            raise ContractError('homer_configuration_changed')
        self._homer_configuration = selected

    def configure_tf_binding_resources(self, resources, environments, *, saved_modes=False):
        """Freeze the caller's explicit ordinary TF worker resource selection."""
        if type(saved_modes) is not bool:
            raise ContractError('explicit_tf_binding_saved_modes_boolean_required')
        if self._tf_binding_configuration is None and not environments and not saved_modes:
            return
        from gene_annotation_episode.episodic_workflow.root.library.tf_binding_tools import normalize_tf_binding_configuration
        selected = normalize_tf_binding_configuration(resources, environments,
            policy=self.local_job_policy.to_dict())
        selected = json.loads(canonical(selected))
        selected['saved_modes'] = saved_modes
        if (self._tf_binding_configuration is not None
                and canonical(self._tf_binding_configuration) != canonical(selected)):
            raise ContractError('tf_binding_configuration_changed')
        self._tf_binding_configuration = selected

    def configure_protease_kinetics_resources(self, resources, environments, *, saved_modes=False):
        """Freeze the caller's explicit protease deployment and saved modes."""
        if type(saved_modes) is not bool:
            raise ContractError('explicit_protease_kinetics_saved_modes_boolean_required')
        if self._protease_kinetics_configuration is None and not environments and not saved_modes:
            return
        from gene_annotation_episode.episodic_workflow.root.library.protease_kinetics_tools import normalize_protease_kinetics_configuration
        selected = normalize_protease_kinetics_configuration(resources, environments,
            policy=self.local_job_policy.to_dict())
        selected = json.loads(canonical(selected))
        selected['saved_modes'] = saved_modes
        if (self._protease_kinetics_configuration is not None
                and canonical(self._protease_kinetics_configuration) != canonical(selected)):
            raise ContractError('protease_kinetics_configuration_changed')
        self._protease_kinetics_configuration = selected

    def configure_protein_conservation_resources(self, resources, environments, *, saved_modes=False):
        """Freeze an explicit MUSCLE profile and independent saved-data modes."""
        if type(saved_modes) is not bool:
            raise ContractError('explicit_protein_conservation_saved_modes_boolean_required')
        if self._protein_conservation_configuration is None and not environments and not saved_modes:
            return
        from .library.protein_conservation_tools import normalize_protein_conservation_configuration
        selected = normalize_protein_conservation_configuration(resources, environments,
            policy=self.local_job_policy.to_dict())
        selected = json.loads(canonical(selected))
        selected['saved_modes'] = saved_modes
        if (self._protein_conservation_configuration is not None
                and canonical(self._protein_conservation_configuration) != canonical(selected)):
            raise ContractError('protein_conservation_configuration_changed')
        self._protein_conservation_configuration = selected

    def configure_protein_phylogeny_resources(self, resources, environments, *, saved_modes=False):
        """Freeze an explicit MUSCLE/IQ-TREE profile and independent saved-data modes."""
        if type(saved_modes) is not bool:
            raise ContractError('explicit_protein_phylogeny_saved_modes_boolean_required')
        if self._protein_phylogeny_configuration is None and not environments and not saved_modes:
            return
        from .library.protein_phylogeny_tools import normalize_protein_phylogeny_configuration
        selected = normalize_protein_phylogeny_configuration(resources, environments,
            policy=self.local_job_policy.to_dict())
        selected = json.loads(canonical(selected))
        selected['saved_modes'] = saved_modes
        if (self._protein_phylogeny_configuration is not None
                and canonical(self._protein_phylogeny_configuration) != canonical(selected)):
            raise ContractError('protein_phylogeny_configuration_changed')
        self._protein_phylogeny_configuration = selected

    def configure_somatic_variant_resources(self, resources, environments, *, saved_modes=False):
        """Freeze explicit matched-input native software and independent saved modes."""
        if type(saved_modes) is not bool:
            raise ContractError('explicit_somatic_variant_saved_modes_boolean_required')
        if self._somatic_variant_configuration is None and not environments and not saved_modes:
            return
        from gene_annotation_episode.episodic_workflow.root.library.somatic_variant_tools import normalize_somatic_variant_configuration
        selected = normalize_somatic_variant_configuration(resources, environments,
            policy=self.local_job_policy.to_dict())
        selected = json.loads(canonical(selected))
        selected['saved_modes'] = saved_modes
        if (self._somatic_variant_configuration is not None
                and canonical(self._somatic_variant_configuration) != canonical(selected)):
            raise ContractError('somatic_variant_configuration_changed')
        self._somatic_variant_configuration = selected

    def configure_esm_gene_embedding_resources(self, resources, environments, *, stored_reads=False):
        """Freeze one explicitly selected offline ESM profile and stored reads."""
        if type(stored_reads) is not bool:
            raise ContractError('explicit_esm_gene_embedding_stored_reads_boolean_required')
        if self._esm_gene_embedding_configuration is None and not environments and not stored_reads:
            return
        from gene_annotation_episode.episodic_workflow.root.library.esm_gene_embedding_tools import normalize_esm_gene_embedding_configuration
        selected = normalize_esm_gene_embedding_configuration(resources, environments,
            policy=self.local_job_policy.to_dict())
        selected = json.loads(canonical(selected))
        selected['stored_reads'] = stored_reads
        if (self._esm_gene_embedding_configuration is not None
                and canonical(self._esm_gene_embedding_configuration) != canonical(selected)):
            raise ContractError('esm_gene_embedding_configuration_changed')
        self._esm_gene_embedding_configuration = selected

