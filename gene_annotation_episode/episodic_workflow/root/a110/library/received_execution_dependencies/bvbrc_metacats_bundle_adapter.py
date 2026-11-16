from __future__ import annotations
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_alignment_bundle_contracts as contracts
ADAPTER_ID = 'bvbrc_metacats'
ADAPTER_VERSION = '1'

def validate_parameters(parameters: dict) -> dict:
    return contracts.validate_parameters(parameters, provider='metacats')

def validate_requested_form(requested_form: dict) -> dict:
    return contracts.validate_requested_form(requested_form, provider='metacats')
