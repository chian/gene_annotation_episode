"""Actual local chromatin operation information, distinct from scientific data."""
from .native_chromatin_interaction_contracts import chromatin_interaction_execution_schema, validate_chromatin_bindings


_DESCRIPTION = (
    "Quantify supplied cis chromatin contacts between explicitly assigned regulatory-element anchors and/or compute "
    "a cross-window insulation heuristic, retaining complete selected populations and numerical denominators."
)
_FORMAT_INSTRUCTIONS = {
    "cooler_hdf5_v3": (
        "For Cooler HDF5 schema 3, supply an explicit HDF5 group and fixed resolution (or null for variable bins). "
        "Select raw contacts or a named precomputed weight column with its actual multiplicative/divisive convention. "
    ),
    "hic_binary_v9": (
        "For HIC binary version 9, supply a null group_path, an existing BP resolution, and exact biological "
        "chromosome names. Select raw contacts or an existing named divisive normalization vector. "
        "The All pseudochromosome, FRAG units and other HIC versions are not supported by this binding. "
        "A missing matrix, unread block or absent normalization remains unavailable; it is not an empty matrix. "
        "Native expected-value vectors are retained as source metadata and are not used as the requested "
        "same-population distance expectation. "
    ),
}
_INSTRUCTIONS = (
    "Supply an authorized retained contact container, its complete file identity and actual format, and exact "
    "cis population intervals in selected order. Select "
    "cis_anchor_contact_enrichment, cross_window_insulation_heuristic, or both. For contacts, supply retained BED "
    "occurrences with explicit enhancer/promoter/other assignments, interval-start or supplied in-interval anchors, "
    "and actual reference/sample/condition/replicate/dependence information when available. Names never determine "
    "element class or gene associations. No candidate annotation or public gene name is required. Bind exact "
    "input keys/identities/paths, selected Python interpreter and dependency/source byte pins. The binding compiler "
    "supplies the driver command and exact output paths under output_prefix. Commission launch and its configured "
    "launch_local child with 20 GiB RAM, 4 GiB scratch, zero swap, and no wall-time budget. The local child owns "
    "preparation, practical.job.start, observation and any later repair choices through the ordinary episode. "
    "The finite producer validates immutable supplied bytes and uses the selected format's parser for each population, "
    "closes its exact canonical tables and population seal, then advances in selected order. It retains the full "
    "container, BED, supplied metadata, sparse rows/source locators, bins, selected weights and exceptional cells; "
    "absent roles and failed reads remain explicit. It performs no mapping or balancing. No raw fallback, smaller "
    "region, first-chromosome choice, fabricated zero matrix, resource substitution or retry is performed. "
    "Monitoring uses the existing local resource instructions and actual lifecycle/log/population-seal facts; "
    "liveness establishes no productive progress. Earlier closed population seals survive a later interruption. "
    "Results captures complete files and separately builds the numerical sheet and calculations from retained "
    "tables. Same-distance expectation uses the exact selected region, not an inferred whole chromosome. Fold "
    "is undefined when its denominator is zero; count zero remains distinct from missing data. Duplicate element "
    "occurrences remain separate, dependent comparisons. Insulation includes every full cross-window, retains "
    "its cell denominator and standardized sum, and uses explicit strict-neighbor/threshold rules. Folds and "
    "boundaries are descriptive heuristics, not probabilities or significance tests. Request the specific typed "
    "projection needed by the parent, retaining complete components and sheet/table bundle separately. Changed "
    "calculation parameters use the saved bundle only; missing saved attachments never trigger native rereading "
    "or acquisition. Capture extent, native execution outcome, numerical qualification, requested delivery and "
    "credit/completion remain distinct."
)


def chromatin_interaction_tool_contracts(bindings: list[dict], *, resource_kind: str, resource_id: str) -> list[dict]:
    if resource_kind != "local" or type(resource_id) is not str or not resource_id or "\0" in resource_id:
        raise ValueError("original_attempt_mismatch")
    bindings = validate_chromatin_bindings(bindings)
    if not bindings:
        return []
    formats = {format for row in bindings for format in row["supported_formats"]}
    instructions = "".join(text for format, text in _FORMAT_INSTRUCTIONS.items() if format in formats) + _INSTRUCTIONS
    return [{"name": "analyze_chromatin_interactions", "description": _DESCRIPTION, "resources": "local",
        "instructions": instructions, "input_schema": chromatin_interaction_execution_schema("RequestedJob", bindings=bindings),
        "invocation_route": {"kind": "commission", "routes": [
            {"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_local"}]}}]


def chromatin_interaction_tool_information(bindings: list[dict], *, resource_kind: str, resource_id: str) -> list[dict]:
    return [{key: row[key] for key in ("name", "description", "resources", "instructions")}
        for row in chromatin_interaction_tool_contracts(bindings, resource_kind=resource_kind, resource_id=resource_id)]
