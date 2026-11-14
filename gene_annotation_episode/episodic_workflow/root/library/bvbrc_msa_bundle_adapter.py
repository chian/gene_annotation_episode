"""Pinned pure MSA adapter facade for the existing AppService results owner."""
from __future__ import annotations

import hashlib
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_alignment_bundle_contracts as contracts
from gene_annotation_episode.episodic_workflow.root.library import bvbrc_alignment_bundle_resolution as resolution

ADAPTER_ID = 'bvbrc_msa'
ADAPTER_VERSION = '1'
_DEPENDENCIES = (
    '__init__.py',
    'episodic_workflow/root/library/bvbrc_alignment_bundle_contracts.py',
    'episodic_workflow/root/library/bvbrc_alignment_bundle_projection.py',
    'episodic_workflow/root/library/bvbrc_alignment_values.py',
    'bvbrc_appservice_contracts.py',
    'bvbrc_appservice_schemas.json',
    'episodic_workflow/__init__.py',
    'episodic_workflow/root/__init__.py',
    'episodic_workflow/root/library/__init__.py',
    'episodic_workflow/root/library/bvbrc_alignment_associations.py',
    'episodic_workflow/root/library/bvbrc_alignment_bundle_resolution.py',
    'episodic_workflow/root/library/bvbrc_alignment_provider_contracts.py',
    'episodic_workflow/root/library/bvbrc_contingency_math.py',
    'episodic_workflow/root/library/bvbrc_metacats_adequacy.py',
    'episodic_workflow/root/library/bvbrc_metacats_association_contracts.py',
    'episodic_workflow/root/library/bvbrc_metacats_associations.py',
    'episodic_workflow/root/library/bvbrc_metacats_biological_calculators.py',
    'episodic_workflow/root/library/bvbrc_metacats_biological_contracts.py',
    'episodic_workflow/root/library/bvbrc_metacats_bundle_adapter.py',
    'episodic_workflow/root/library/bvbrc_metacats_calculation_contracts.py',
    'episodic_workflow/root/library/bvbrc_metacats_calculators.py',
    'episodic_workflow/root/library/bvbrc_metacats_format_contracts.py',
    'episodic_workflow/root/library/bvbrc_metacats_formats.py',
    'episodic_workflow/root/library/bvbrc_metacats_grader.py',
    'episodic_workflow/root/library/bvbrc_metacats_input_formats.py',
    'episodic_workflow/root/library/bvbrc_metacats_inputs.py',
    'episodic_workflow/root/library/bvbrc_metacats_provider_contracts.py',
    'episodic_workflow/root/library/bvbrc_msa_bundle_adapter.py',
    'episodic_workflow/root/library/bvbrc_msa_calculation_contracts.py',
    'episodic_workflow/root/library/bvbrc_msa_calculators.py',
    'episodic_workflow/root/library/bvbrc_msa_format_contracts.py',
    'episodic_workflow/root/library/bvbrc_msa_formats.py',
    'episodic_workflow/root/library/bvbrc_msa_grader.py',
    'episodic_workflow/root/library/bvbrc_msa_inputs.py',
    'episodic_workflow/root/library/bvbrc_msa_provider_contracts.py',
    'episodic_workflow/root/library/bvbrc_msa_xmfa_inputs.py',
    'episodic_workflow/root/library/xmfa_calculators.py',
    'episodic_workflow/root/library/xmfa_coordinates.py',
    'episodic_workflow/root/library/xmfa_formats.py',
    'episodic_workflow/root/library/xmfa_sources.py',
    'episodic_workflow/root/library/phylogeny_calculation_contracts.py',
    'episodic_workflow/root/library/phylogeny_calculators.py',
    'episodic_workflow/root/library/phylogeny_format_contracts.py',
    'episodic_workflow/root/library/phylogeny_formats.py',
    'episodic_workflow/root/library/xmfa_calculation_contracts.py',
    'episodic_workflow/root/library/xmfa_format_contracts.py',
    'episodic_workflow/root/library/xmfa_source_contracts.py',
)


def validate_parameters(parameters: dict) -> dict:
    return contracts.validate_parameters(parameters, provider='msa')


def parameters_schema() -> dict:
    return contracts.parameters_schema(provider='msa')


def requested_form_schema(fields: dict) -> dict:
    return contracts.requested_form_schema(fields, provider='msa')


def validate_requested_form(requested_form: dict) -> dict:
    return contracts.validate_requested_form(requested_form, provider='msa')


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict], requested_form: dict, parameters: dict) -> dict:
    return resolution.consume_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values,
        requested_form=requested_form, parameters=parameters, provider='msa')


def implementation_sha256() -> str:
    """Configuration-only digest; grading and saved reads do not read files."""
    result = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        content = (Path(__file__).resolve().parents[3] / name).read_bytes()
        result.update(name.encode() + b'\0' + str(len(content)).encode() + b'\0' + content)
    return result.hexdigest()


__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'validate_parameters', 'parameters_schema',
    'requested_form_schema', 'validate_requested_form', 'consume_bundle', 'implementation_sha256']
