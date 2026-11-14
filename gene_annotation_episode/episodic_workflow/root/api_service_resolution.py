"""Original API reference namespaces and authenticated provider evidence ports."""
from __future__ import annotations

from gene_annotation_episode.domain import ContractError


class APIServiceResolution:
    def resolve(self, context, reference, namespace):
        if context.run_id == self.run_id:
            if any(service.service == 'enrichr' for service in self.services.values()):
                resolved = (self.enrichr_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.enrichr_returns.resolve_received(context, reference, namespace))
                if resolved is not None:
                    return resolved
            if any(service.service == 'uniprot' for service in self.services.values()):
                resolved = (self.uniprot_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.uniprot_returns.resolve_received(context, reference, namespace))
                if resolved is not None:
                    return resolved
            if any(service.service == 'sequence_support' for service in self.services.values()):
                resolved = (self.addgene_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.addgene_returns.resolve_received(context, reference, namespace))
                if resolved is not None:
                    return resolved
            if namespace in {'rfam_record', 'rfam_query', 'rfam_family', 'rfam_model'}:
                return (self.rfam_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.rfam_returns.resolve_received(context, reference, namespace))
            from .bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return (self.homology_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.homology_returns.resolve_received(context, reference, namespace))
            from .bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                return (self.phylogeny_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.phylogeny_returns.resolve_received(context, reference, namespace))
            from .bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
            if namespace in ALIGNMENT_NAMESPACES:
                return (self.alignment_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.alignment_returns.resolve_received(context, reference, namespace))
            from .bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
            if namespace in GENOME_ALIGNMENT_NAMESPACES:
                return (self.genome_alignment_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.genome_alignment_returns.resolve_received(context, reference, namespace))
            from .bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                return (self.proteome_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.proteome_returns.resolve_received(context, reference, namespace))
            from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                return (self.comparative_systems_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.comparative_systems_returns.resolve_received(context, reference, namespace))
            from .bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
            if namespace in FASTQUTILS_NAMESPACES:
                return (self.fastqutils_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.fastqutils_returns.resolve_received(context, reference, namespace))
            from .bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
            if namespace in APPLICATION_NAMESPACES:
                return (self.application_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.application_returns.resolve_received(context, reference, namespace))
            resolved = self.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if context.run_id != self.run_id or namespace not in {None, 'source', 'execution_handoff', 'execution_result'}:
            return False
        try:
            if namespace != 'execution_result':
                self.read_target(reference, context.scope)
                return True
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            pass
        try:
            self.read_result(reference, context.scope)
            return namespace != 'execution_handoff' and (namespace != 'source' or
                self.store.get(reference)['record_type'] == 'source')
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            return False

    def read_bvbrc_result(self, reference, *, context, admission_operation_key=None):
        return self.bvbrc_data.read(reference, context=context,
            admission_operation_key=admission_operation_key)

    def record_bvbrc_admission(self, context, form, schema, operation_key):
        return self.bvbrc_data.record_admission(context, form, schema, operation_key)

    def received_bvbrc_context(self, context):
        return self.bvbrc_data.received_context(context)


