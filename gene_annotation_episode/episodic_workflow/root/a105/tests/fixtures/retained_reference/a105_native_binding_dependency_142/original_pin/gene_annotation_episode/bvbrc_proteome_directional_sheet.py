"""Copy complete retained directional reports into the numerical input sheet.

This function indexes observations only: it does not calculate correspondence,
infer source/execution bindings, parse raw bytes, or acquire anything.
"""
from copy import deepcopy

from .bvbrc_proteome_directional_contracts import (
    ProteomeDirectionalError, validate_directional_report,
)
from .bvbrc_proteome_directional_numerical_contracts import (
    DirectionalNumericalContractError, _issue, _observations, _sheet_diagnostics,
    validate_directional_numerical,
)


def build_directional_sheet(directional_results: list[dict]) -> dict:
    """Return every valid reader occurrence, or a located structural failure.

    A conforming native partial/failure report remains an input occurrence.
    Structural corruption rejects this construction without mutating caller
    data; independent documents can be constructed separately by the caller.
    """
    try:
        if type(directional_results) is not list:
            raise DirectionalNumericalContractError('invalid_input_contract', '/directional_results')
        results = []
        for index, result in enumerate(directional_results):
            try: results.append(validate_directional_report(result))
            except ProteomeDirectionalError as error:
                raise DirectionalNumericalContractError('invalid_input_contract',
                    f'/directional_results/{index}' + error.path) from None
        diagnostics = _sheet_diagnostics(results)
        sheet = {'version': 'bvbrc_proteome_directional_sheet_v1',
                 'reader_results': results, 'reports': _observations(results),
                 'diagnostics': diagnostics}
        answer = {'state': 'partial' if diagnostics else 'available', 'sheet': sheet,
                  'diagnostics': deepcopy(diagnostics)}
        return validate_directional_numerical('DirectionalSheetResult', answer)
    except DirectionalNumericalContractError as error:
        return {'state': 'failure', 'sheet': None, 'diagnostics': [
            _issue(error.code, argument_pointer=error.pointer)]}


__all__ = ['build_directional_sheet']
