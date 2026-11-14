"""Pure population of the one shared FBA sheet from already parsed records."""
from .flux_balance_contracts import validate_flux_balance_record

__all__ = ["populate_flux_balance_sheet", "validate_flux_balance_sheet"]


def populate_flux_balance_sheet(*, bundle: dict) -> dict:
    """Detach parsed evidence without resolving conflicts or changing numbers."""
    parsed = validate_flux_balance_record("ParsedFBABundle", bundle)
    return validate_flux_balance_sheet({
        "version": "flux_balance_sheet_v1", "operation": "perform_flux_balance_analysis",
        "mode": "steady_state_linear_fba", **parsed})


def validate_flux_balance_sheet(sheet: dict) -> dict:
    """Return a detached validated sheet; native precision and order survive."""
    return validate_flux_balance_record("FluxBalanceSheet", sheet)
