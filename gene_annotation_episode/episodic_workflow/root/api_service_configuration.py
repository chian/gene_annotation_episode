"""Original API provider construction and existing lazy reader ports.

Construction order, eager providers, validation and original callbacks remain.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .api_execution import HMMERAPIExecution
from gene_annotation_episode.execution_contracts import canonical, digest


class APIServiceConfiguration:
    def __init__(self, store, *, run_id, directory, configuration, tool_registry,
                 handoff_unit, acquired_record_unit, received_input_reader=None):
        from gene_annotation_episode.api_services import build_service
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_execution_run_required')
        for unit in (handoff_unit, acquired_record_unit):
            if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        self.store, self.run_id = store, run_id
        if received_input_reader is not None and not callable(received_input_reader):
            raise ValueError('api_received_input_reader_must_be_callable')
        self.received_input_reader = received_input_reader
        self.directory = Path(directory)/'api-service-execution'/digest(run_id)
        self.configuration = json.loads(canonical(configuration))
        self.tools, self.clients = tool_registry, tool_registry.clients
        self.handoff_unit, self.acquired_record_unit = handoff_unit, acquired_record_unit
        from gene_annotation_episode.api_selected_effects import SelectedAPIEffects
        self.selected_effects = SelectedAPIEffects(directory, run_id=run_id)
        if not self.configuration or tool_registry.store is not store:
            raise ValueError('actual_api_services_and_tool_registry_required')
        self.services = {}
        legacy = {}
        for resource_id, config in self.configuration.items():
            if config.get('kind') == 'hmmer_api':
                legacy[resource_id] = config
            elif config.get('kind') == 'api':
                self.services[resource_id] = build_service(config.get('service'), config, tool_registry)
            else:
                raise ValueError('unsupported_api_resource_configuration')
        self.legacy = None if not legacy else HMMERAPIExecution(store, run_id=run_id,
            directory=directory, configuration=legacy, tool_registry=tool_registry,
            handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit)
        from .bvbrc_data_host import BVBRCDataHost
        self.bvbrc_data = BVBRCDataHost(self)
        from .bvbrc_minhash_host import BVBRCMinhashHost
        self.minhash = BVBRCMinhashHost(self)
        from .bvbrc_appservice_host import BVBRCAppServiceHost
        self.appservice = BVBRCAppServiceHost(self)
        from .bvbrc_homology_returns import BVBRCHomologyReturns
        self.homology_returns = BVBRCHomologyReturns(self)
        from .bvbrc_phylogeny_returns import BVBRCPhylogenyReturns
        self.phylogeny_returns = BVBRCPhylogenyReturns(self)
        from .bvbrc_alignment_returns import BVBRCAlignmentReturns
        self.alignment_returns = BVBRCAlignmentReturns(self)
        from .bvbrc_genome_alignment_returns import BVBRCGenomeAlignmentReturns
        self.genome_alignment_returns = BVBRCGenomeAlignmentReturns(self)
        from .bvbrc_proteome_returns import BVBRCProteomeReturns
        self.proteome_returns = BVBRCProteomeReturns(self)
        from .bvbrc_comparative_systems_returns import BVBRCComparativeSystemsReturns
        self.comparative_systems_returns = BVBRCComparativeSystemsReturns(self)
        from .bvbrc_fastqutils_returns import BVBRCFastqUtilsReturns
        self.fastqutils_returns = BVBRCFastqUtilsReturns(self)
        from .bvbrc_application_returns import BVBRCApplicationReturns
        self.application_returns = BVBRCApplicationReturns(self)

    @property
    def rfam_returns(self):
        from .rfam_batch_returns import RfamBatchReturns
        if '_rfam_returns' not in self.__dict__:
            self._rfam_returns = RfamBatchReturns(self)
        return self._rfam_returns

    @property
    def uniprot_returns(self):
        from .uniprot_returns import UniProtReturns
        if '_uniprot_returns' not in self.__dict__:
            self._uniprot_returns = UniProtReturns(self)
        return self._uniprot_returns

    @property
    def enrichr_protocol(self):
        from gene_annotation_episode.api_enrichr_host import EnrichrProtocolHost
        if '_enrichr_protocol' not in self.__dict__:
            self._enrichr_protocol = EnrichrProtocolHost(self)
        return self._enrichr_protocol

    @property
    def enrichr_returns(self):
        from gene_annotation_episode.enrichr_returns import EnrichrReturns
        if '_enrichr_returns' not in self.__dict__:
            self._enrichr_returns = EnrichrReturns(self)
        return self._enrichr_returns

    @property
    def addgene_returns(self):
        from gene_annotation_episode.addgene_sequence_returns import AddgeneSequenceReturns
        if '_addgene_returns' not in self.__dict__:
            self._addgene_returns = AddgeneSequenceReturns(self)
        return self._addgene_returns

    def __getattr__(self, name):
        # Preserve existing inspection ports for the unchanged legacy binding.
        legacy = self.__dict__.get('legacy')
        if legacy is not None:
            return getattr(legacy, name)
        raise AttributeError(name)

    def _legacy_binding(self):
        if self.legacy is None:
            raise ValueError('legacy_api_resource_not_bound')
        return self.legacy

