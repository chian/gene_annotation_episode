"""Actual overlap tool information, separate from child commissioning schemas."""
from .native_genomic_overlap_contracts import (
    genomic_overlap_execution_schema, validate_genomic_overlap_bindings,
)

_NAME = "analyze_genomic_region_overlap"
_DESCRIPTION = (
    "Compare every unordered pair of explicitly supplied genomic interval sets using unstranded outer spans; "
    "retain original occurrences and complete bedtools overlap tables for separate numerical calculations."
)
_INSTRUCTIONS = (
    "Supply at least two retained interval artifacts in the selected order, their distinct set keys, exact original "
    "file identities and authorized absolute input paths. Select bed_outer_span_v1 or coordinate_rows_v1 for each "
    "artifact explicitly. BED intervals and coordinate rows use zero-based, half-open [start,end) coordinates. "
    "Declare reference identities and contig metadata when supplied; unknown or conflicting references remain "
    "qualifications and do not cause reference acquisition. No publicly searchable name or candidate annotation "
    "is required. Freeze every unordered i<j comparison in request order with its own comparison key and ordinal. "
    "The mode is unstranded_outer_span: BED block fields and strand are retained as source data, while geometry "
    "uses the outer interval. Duplicate input rows remain distinct occurrences. "
    "Bind the explicit Python interpreter, implementation module root and byte pins, and the exact bedtools "
    "executable, byte identity and version. The requested_job contains the compiled argument list, explicit "
    "environment with LC_ALL=C, and native_genomic_overlap. Its nominal command is the selected Python executable "
    "followed by -B -m gene_annotation_episode.native_genomic_overlap_driver genomic-overlap-plan.json. "
    "Commission launch and its bound launch_local child with the original allocation: 20 GiB RAM, 4 GiB scratch, "
    "zero swap and no wall-time budget. Preparation only reserves the selected attempt; the owning child selects "
    "practical.job.start. The driver retains exact original bytes and G1 occurrence maps, writes canonical BED4, "
    "and invokes the selected bedtools intersect -a A -b B -wo -sorted once for each eligible nonempty pair. "
    "It applies no fraction, strand or block filter. A complete empty set gives an analytic empty comparison "
    "without a native invocation; malformed or unavailable inputs remain distinct, and independent valid pairs "
    "are preserved. A successful invoked zero-byte table is a present result, not an absent file. "
    "Outputs have fixed paths: stdout.log and stderr.log, version logs under the selected output_prefix/software, "
    "original.data, rejected-source.data when applicable, parsed-set.json and canonical.bed under output_prefix/sets/sN, "
    "manifest.json, overlap.wo.tsv and stderr.txt under output_prefix/pairs/pN, and the final bundle.json. "
    "The sealed genomic_overlap_native_batch_v1 bundle retains original identity, native outcomes, complete "
    "file declarations and located failures. Monitoring reads that original job's actual logs, file availability "
    "and lifecycle facts. Per-pair subprocess times, driver times and service-wall times retain their meanings. "
    "An interrupted attempt can retain earlier pair seals without a final batch; recovery never repeats native "
    "calls. A retry requires a separate episode-selected failed-attempt action. "
    "Results acquisition captures complete declared bytes and uses the separate G1 parsers, numerical sheet and "
    "calculators. Native pair counts and summed overlap widths retain duplicate occurrences; unique intersection "
    "and union lengths measure covered bases. Jaccard is intersection-union bases divided by combined-union bases, "
    "with an undefined ratio for a zero denominator. Explicit post hoc minimum-overlap and fraction parameters "
    "can be recalculated from the saved sheet without repeating bedtools. Preserve complete, partial, unavailable "
    "and measured-zero distinctions. These geometric quantities are not function-confidence probabilities. "
    "Request only the typed numerical fields and qualifications needed by the receiving episode; retain the full "
    "native files and sheet separately. Source equality establishes no authority to use another episode's data. "
    "Native success, capture completeness and delivery of the requested result remain separate facts. This entry "
    "describes the bound local operation; it supplies no API/HPC deployment or direct scientific-root execution."
)


def genomic_overlap_tool_contracts(bindings: list[dict], *, resource_kind: str,
                                   resource_id: str) -> list[dict]:
    if resource_kind != "local" or type(resource_id) is not str or not resource_id or "\x00" in resource_id:
        raise ValueError("genomic_overlap_binding_mismatch")
    bindings = validate_genomic_overlap_bindings(bindings)
    if not bindings:
        return []
    return [{"name": _NAME, "description": _DESCRIPTION, "resources": "local", "instructions": _INSTRUCTIONS,
        "input_schema": genomic_overlap_execution_schema("RequestedJob", bindings=bindings),
        "invocation_route": {"kind": "commission", "routes": [
            {"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_local"}]}}]


def genomic_overlap_tool_information(bindings: list[dict], *, resource_kind: str,
                                     resource_id: str) -> list[dict]:
    return [{key: row[key] for key in ("name", "description", "resources", "instructions")}
        for row in genomic_overlap_tool_contracts(bindings, resource_kind=resource_kind, resource_id=resource_id)]


__all__ = ["genomic_overlap_tool_contracts", "genomic_overlap_tool_information"]
