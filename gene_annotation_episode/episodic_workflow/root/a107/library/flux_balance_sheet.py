"""A107 original retained result worker dependency: flux_balance_sheet.
Scientific bodies, invalid outcomes and original byte qualifications are retained.
"""


from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_flux_balance_contracts import validate_flux_balance_record

def populate_flux_balance_sheet(*, bundle: dict) -> dict:
    """Detach parsed evidence without resolving conflicts or changing numbers."""
    parsed = validate_flux_balance_record('ParsedFBABundle', bundle)
    return validate_flux_balance_sheet({'version': 'flux_balance_sheet_v1', 'operation': 'perform_flux_balance_analysis', 'mode': 'steady_state_linear_fba', **parsed})

def validate_flux_balance_sheet(sheet: dict) -> dict:
    """Return a detached validated sheet; native precision and order survive."""
    return validate_flux_balance_record('FluxBalanceSheet', sheet)
