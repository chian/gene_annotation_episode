"""Import-compatible Rfam report delegate to the common Infernal calculator."""
from __future__ import annotations

from . import infernal_search_grader
from .rfam_batch_contracts import validate_rfam_parameters
from .rfam_batch_infernal import select_rfam_common_sheet


def calculate_rfam_batch_report_components(sheet, *, parameters) -> dict:
    """Use the common numerical authority for all newly requested report work."""
    validate_rfam_parameters(parameters)
    sheet = select_rfam_common_sheet(sheet, representation="out")
    return infernal_search_grader.calculate_infernal_search_scores(sheet, parameters={"hit_scope": "reported"})


__all__ = ["calculate_rfam_batch_report_components"]
