"""Explicitly selected v2 facade for retained GenomeComparison measurements."""
import hashlib
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_bundle_v2_contracts import (
    parameters_schema_v2 as parameters_schema, validate_parameters_v2 as validate_parameters,
    validate_result_selector_v2 as validate_result_selector,
)
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_bundle_v2_resolution import _construct_bundle
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_directional_fact_contracts import (
    requested_form_schema_v2 as requested_form_schema, validate_requested_form_v2 as validate_requested_form,
)
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_directional_projection import project_requested_facts_v2
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_bundle_adapter import _DEPENDENCIES as _LEGACY_DEPENDENCIES

ADAPTER_ID = 'bvbrc_proteome'
ADAPTER_VERSION = '2'
_DEPENDENCIES = tuple(sorted(set(_LEGACY_DEPENDENCIES) | {
    '__init__.py',
    'episodic_workflow/root/library/alignment_correspondence.py',
    'episodic_workflow/root/library/blast_search.py',
    'bvbrc_appservice_contracts.py',
    'bvbrc_appservice_schemas.json',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_projection.py',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_schemas.json',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_v2_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_v2_schemas.json',
    'episodic_workflow/root/library/bvbrc_proteome_data_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_data_schemas.json',
    'episodic_workflow/root/library/bvbrc_proteome_directional_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_fact_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_geometry.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_numerical_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_numerical_schemas.json',
    'episodic_workflow/root/library/bvbrc_proteome_directional_projection.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_saved_validation.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_schemas.json',
    'episodic_workflow/root/library/bvbrc_proteome_fact_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_native_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_native_schemas.json',
    'episodic_workflow/root/library/bvbrc_proteome_sheet_contracts.py',
    'episodic_workflow/root/library/bvbrc_proteome_sheet_schemas.json',
    'episodic_workflow/__init__.py',
    'episodic_workflow/root/__init__.py',
    'episodic_workflow/root/library/__init__.py',
    'episodic_workflow/root/library/blast_pairwise_grader.py',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_adapter.py',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_adapter_v2.py',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_resolution.py',
    'episodic_workflow/root/library/bvbrc_proteome_bundle_v2_resolution.py',
    'episodic_workflow/root/library/bvbrc_proteome_calculators.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_calculators.py',
    'episodic_workflow/root/library/bvbrc_proteome_directional_sheet.py',
    'episodic_workflow/root/library/bvbrc_proteome_inputs.py',
    'episodic_workflow/root/library/bvbrc_proteome_joins.py',
    'episodic_workflow/root/library/bvbrc_proteome_native.py',
    'episodic_workflow/root/library/bvbrc_proteome_numerical_sheet.py',
    'episodic_workflow/root/library/bvbrc_proteome_sheet.py',
}))


def implementation_sha256():
    result = hashlib.sha256()
    for name in _DEPENDENCIES:
        raw = (Path(__file__).resolve().parents[3] / name).read_bytes()
        result.update(name.encode() + b'\0' + str(len(raw)).encode() + b'\0' + raw)
    return result.hexdigest()


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    built = _construct_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values,
                              requested_form=requested_form, parameters=parameters)
    projected = project_requested_facts_v2(**built, requested_form=requested_form, parameters=parameters)
    return dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION, **projected,
                sheet=built['sheet'], components=built['components'])


__all__ = ['ADAPTER_ID','ADAPTER_VERSION','parameters_schema','validate_parameters','validate_result_selector',
           'requested_form_schema','validate_requested_form','implementation_sha256','consume_bundle']
