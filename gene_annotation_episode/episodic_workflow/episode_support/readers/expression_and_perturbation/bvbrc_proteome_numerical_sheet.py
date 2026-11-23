"""Compose separately measured native and directional sheets without a join."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_bundle_contracts import validate_shape, _require
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_directional_numerical_contracts import validate_directional_numerical

def build_proteome_numerical_sheet(*, native_sheet, directional_sheet):
    _require(native_sheet is not None or directional_sheet is not None, path='/numerical_sheet')
    if native_sheet is not None:
        validate_proteome_sheet_data('NativeSheet', native_sheet)
    if directional_sheet is not None:
        validate_directional_numerical('DirectionalSheet', directional_sheet)
    return validate_shape('ProteomeNumericalSheet', {'version': 'bvbrc_proteome_numerical_sheet', 'native_sheet': deepcopy(native_sheet), 'directional_sheet': deepcopy(directional_sheet), 'directional_operand_binding': 'unbound'})
__all__ = ['build_proteome_numerical_sheet']
