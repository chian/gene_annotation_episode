"""Copy requested saved fluorescence cells without scientific recalculation."""

from copy import deepcopy

from .fluorescence_event_contracts import (
    VIEW_SCHEMA,
    canonical,
    validate_components,
    validate_selection,
)


def project_fluorescence_result(sheet: dict, components: dict, *, selection: dict) -> dict:
    """Validate identities, then copy only selected saved cells in request order.

    This validates represented contracts, not the authenticity of standalone
    component bytes. Artifact custody belongs to the actual result binding.
    """
    validate_components(components, sheet=sheet)
    validate_selection(selection, components=components)
    lookup = {canonical(cell["request"]): cell for cell in components["cells"]}
    selected = [lookup[canonical(request)] for request in selection["requests"]]
    problems, seen = [], set()
    for cell in selected:
        for problem in cell["issues"]:
            identity = canonical(problem)
            if identity not in seen:
                seen.add(identity)
                problems.append(deepcopy(problem))
    if selected and not any(cell["state"] != "unavailable" for cell in selected):
        status = "unavailable"
    elif problems or any(cell["state"] != "present" for cell in selected):
        status = "partial"
    else:
        status = "calculated"
    start = selection["offset"]
    stop = start + selection["limit"]
    rows = deepcopy(selected[start:stop])
    return dict(schema=VIEW_SCHEMA, selection=deepcopy(selection), rows=rows,
                total_selected_rows=len(selected), returned_row_count=len(rows),
                has_more=stop < len(selected), status=status, issues=problems)
