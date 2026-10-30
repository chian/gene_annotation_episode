"""Actual local ATAC operation information, separate from episode prompts."""
from .native_atac_differential_contracts import atac_execution_schema, validate_atac_bindings


_DESCRIPTION = (
    "Compare two supplied ATAC BAM conditions with MACS2 2.2.9.1, retaining native peak, pileup and "
    "background measurements and separate depth-normalized differential likelihood components and regions."
)
_INSTRUCTIONS = (
    "Supply two authorized retained BAM inputs in declared condition order, their sample and reference "
    "relationships, and explicit calculation parameters. No candidate function or public gene identifier is "
    "required. This binding uses MACS2 2.2.9.1 single-end BAM interpretation, narrow peaks, --nomodel, "
    "--shift -100, --extsize 200, --keep-dup 1 and raw bedGraph tracks. The second BAM is a second treatment "
    "condition, even if an upstream wrapper named it control_bam. There is no matched control; each "
    "condition's background is MACS2's model background. BAMPE, matched-control, broad-peak and other "
    "MACS2-version modes are not bound here. Supply the effective genome-size argument and peak q-value "
    "cutoff explicitly. The genome-size argument is not a chromosome dictionary. Preserve actual BAM "
    "header sequence names, lengths and any checksums separately from caller reference metadata. "
    "Different filenames or sample labels do not establish independent replicates, and this calculator "
    "does not estimate replicate uncertainty. "
    "Commission launch and the configured launch_local child. The local episode owns preparation, "
    "practical.job.start, monitoring and any later repair choice through the ordinary episode loop. "
    "Select a prepared, pinned native installation and exact input bindings; the compiler supplies "
    "commands and output paths. Execution uses 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time "
    "budget. The finite producer runs callpeak for each condition and bdgdiff with those actual output "
    "paths and observed post-filter tag depths. It never substitutes equal depth factors or treats the "
    "second condition as callpeak's control input. Native logs, XLS, narrowPeak, summits, pileup and "
    "background tracks, differential BEDs and actual BAM header text remain available as retained "
    "artifacts. Missing outputs remain missing; valid outputs from a failed attempt remain usable as "
    "qualified partial data. "
    "Monitoring uses the generic local resource instructions and observed process, log, output and "
    "command-completion facts. Liveness alone is not productive progress. Use execution.results.status "
    "or execution.results.collect under the existing results episode with the ATAC selector. Collection "
    "captures the original closed output, builds a numerical sheet and runs deterministic calculations; "
    "it does not rerun MACS2. Raw native pileup values, observed post-filter tag counts, derived depth "
    "factors and likelihood components retain their separate units and definitions. Calculation uses "
    "the explicitly selected population and actual supplied track coverage. Unobserved tails and "
    "missing operands are not zero; a complete empty output remains distinguishable from an absent "
    "file. MACS2 2.2.9.1 bdgdiff can report displaced interval coordinates. Preserve its original BED "
    "coordinates and qualification; correct derived regions come separately from the actual four-track "
    "boundaries, never a guessed offset. "
    "Request only the measurements, region population and qualifications needed by the receiving "
    "episode. A requested saved bundle contains the numerical sheet and all its raw track tables. "
    "Changed calculation parameters use that explicitly received bundle without rereading BAMs, "
    "reacquiring data or rerunning the analysis. Native execution success, retained-data extent, "
    "calculation availability and completion of the requested typed delivery are separate facts. "
    "Likelihood components are not calibrated probabilities of gene function or annotation credit."
)


def atac_tool_contracts(bindings: list[dict], *, resource_kind: str, resource_id: str) -> list[dict]:
    if resource_kind != "local" or type(resource_id) is not str or not resource_id or "\0" in resource_id:
        raise ValueError("original_attempt_mismatch")
    bindings = validate_atac_bindings(bindings)
    if not bindings:
        return []
    return [{"name": "analyze_atac_seq_differential_accessibility", "description": _DESCRIPTION,
        "resources": "local", "instructions": _INSTRUCTIONS,
        "input_schema": atac_execution_schema("RequestedJob", bindings=bindings),
        "invocation_route": {"kind": "commission", "routes": [
            {"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_local"}]}}]


def atac_tool_information(bindings: list[dict], *, resource_kind: str, resource_id: str) -> list[dict]:
    return [{key: row[key] for key in ("name", "description", "resources", "instructions")}
        for row in atac_tool_contracts(bindings, resource_kind=resource_kind, resource_id=resource_id)]
