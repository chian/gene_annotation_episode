"""Compose separately measured legacy and directional sheets without a join."""
from copy import deepcopy

from .bvbrc_proteome_bundle_v2_contracts import validate_shape_v2, _require
from .bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data
from .bvbrc_proteome_directional_numerical_contracts import validate_directional_numerical


def build_proteome_numerical_sheet(*, legacy_sheet, directional_sheet):
    _require(legacy_sheet is not None or directional_sheet is not None, path='/numerical_sheet')
    if legacy_sheet is not None:
        validate_proteome_sheet_data('NativeSheet', legacy_sheet)
    if directional_sheet is not None:
        validate_directional_numerical('DirectionalSheet', directional_sheet)
    return validate_shape_v2('ProteomeNumericalSheetV2', {
        'version':'bvbrc_proteome_numerical_sheet_v2', 'legacy_sheet':deepcopy(legacy_sheet),
        'directional_sheet':deepcopy(directional_sheet), 'directional_operand_binding':'unbound'})


__all__ = ['build_proteome_numerical_sheet']
