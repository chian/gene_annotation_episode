"""Original native_blast_result_worker scientific values and explicit received-record contracts."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.blast_pairwise_result_views import NATIVE_BLAST_METRICS
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import PROGRAM_UNITS
from Bio.Seq import Seq
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_pairwise_grader import _axis_geometry
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import _options
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_alignment.alignment_correspondence import _same
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import identity
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_pairwise_grader import validate_blast_correspondence_instance
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_alignment.alignment_correspondence import validate_correspondence_artifacts

def record_key(bundle, search_key, family, hit_ordinal=None, hsp_ordinal=None):
    return identity("native_blast_pairwise_row", {"bundle_identity": bundle["identity"],
        "search_key": search_key, "family": family,
        "hit_ordinal": hit_ordinal, "hsp_ordinal": hsp_ordinal})

def metric_definitions():
    """Document concrete inputs/denominators without a second scoring language."""
    return {
        "native_score_bits": "Exact native HSP bit_score in bits; no HSP summation.",
        "native_raw_score": "Exact native HSP score in the selected program's score units.",
        "native_evalue": "Exact native HSP evalue, expected count; retained and unused as paired relevance.",
        "alignment_columns": "Shared HSP counts.alignment_columns, all reported/traceback alignment columns.",
        "paired_positions": "Shared HSP counts.paired_columns, columns with both residues present.",
        "identical_positions": "Shared HSP counts.identical_pairs, equal paired symbols.",
        "substituted_positions": "paired_columns - identical_pairs when both are established.",
        "query_gap_columns": "Shared HSP counts.query_gap_columns from the actual traceback.",
        "reference_gap_columns": "Shared HSP counts.reference_gap_columns from the actual traceback.",
        "query_aligned_positions": "Shared HSP counts.paired_query_positions in original query units; translated residues span three nt; excludes gaps.",
        "reference_aligned_positions": "Shared HSP counts.paired_reference_positions in original reference units; translated residues span three nt; excludes gaps.",
        "query_length": "Length of the complete captured query FASTA sequence in its original units.",
        "reference_length": "Length of the complete captured reference FASTA sequence in its original units.",
        "paired_identity": "HSP identical_pairs / paired_columns; union identical distinct pairs / distinct pairs, unavailable when mappings conflict or denominator is zero.",
        "alignment_identity": "HSP identical_pairs / alignment_columns; reported percentages stay distinguished in complete components when traceback is absent.",
        "query_paired_coverage": "HSP paired query positions / actual full query length; union of observed paired query positions / actual full query length.",
        "reference_paired_coverage": "HSP paired reference positions / actual full reference length; union of observed paired reference positions / actual full reference length.",
        "observed_distinct_residue_pairs": "Shared union counts.distinct_residue_pairs from usable retained HSP geometry, not an inferred complete global alignment.",
        "observed_identical_residue_pairs": "Shared union counts.identical_residue_pairs; unavailable for conflicted identity or no defined pairs.",
        "observed_paired_query_positions": "Shared union counts.paired_query_positions, merging overlapping original query intervals.",
        "observed_paired_reference_positions": "Shared union counts.paired_reference_positions, merging overlapping original reference intervals.",
        "hsps_with_geometry": "Shared union counts.hsps_with_geometry, number of retained HSPs with validated geometry.",
        "hsps_without_geometry": "Shared union counts.hsps_without_geometry, number of retained HSPs lacking validated geometry.",
        "query_selected_length": "selected_operand_coverage.query.denominator: explicit query_loc width, otherwise full query length.",
        "reference_selected_length": "selected_operand_coverage.reference.denominator: explicit subject_loc width, otherwise full reference length.",
        "query_selected_paired_positions": "selected_operand_coverage.query.numerator; unavailable if the retained reported geometry is incomplete, except established complete zero-hit output gives zero.",
        "reference_selected_paired_positions": "selected_operand_coverage.reference.numerator with the same completeness qualification.",
        "query_selected_paired_coverage": "selected_operand_coverage.query.value = its numerator / its explicit selected denominator.",
        "reference_selected_paired_coverage": "selected_operand_coverage.reference.value = its numerator / its explicit selected denominator.",
        "conflicting_mapping_count": "Length of the shared union.conflicts list; diagnostic mappings, not independent evidence or confidence.",
        "identical_mapping_group_count": "Length of shared union.identical_mapping_hsp_groups; repeated representations, not independent evidence.",
        "missingness": "No uncertainty estimate is inferred. Missing inputs, incompatible inputs, invalid rows and unmeasured quantities retain separate closed reasons. Complete source quantities, original lexemes, geometry and diagnostics remain in the sheet/components.",
    }

def _invocation(bundle, records):
    options = _options(bundle["requested_job"]["native_blast"])
    operands, bindings = [], {}
    for axis, row in records.items():
        binding = row["binding"] or {}
        ref = binding.get("subject_ref") if axis == "query" else binding.get("reference_ref")
        descriptor = {"subject_ref": ref, **{key: row[key] for key in
            ("length", "molecule", "artifact_key", "native_id", "selected_interval")}}
        bindings[axis] = descriptor
        operands.append({"role": "query" if axis == "query" else "subject", **descriptor,
            "record_ordinal": 0, "native_title": row["native_title"],
            "identity": {"namespace": "sequence_sha256", "value": row["sequence_sha256"], "version": None}})
    return {"execution_program": bundle["program"], "scientific_mode": "pairwise", "resource_kind": "local",
        "query_kind": "sequence", "reference_kind": "sequence", "request": bundle["requested_job"],
        "effective_options": {**options,
            "requested_hit_limit": int(options["-max_target_seqs"]) if "-max_target_seqs" in options else None,
            "requested_hsp_limit": int(options["-max_hsps"]) if "-max_hsps" in options else None},
        "operands": operands, "completion": {"native_returncode": bundle["returncode"],
            "producer_complete": bundle["returncode"] == 0 and not bundle["failures"]}}, bindings

def _hsp_values(component, common=None, *, archived_values=None):
    if component is None:
        return {}
    if common is None:
        if archived_values is None:
            raise ValueError("native_blast_common_hsp_components_required")
        # Explicit v1 read only: the archived result is already a frozen fact.
        # Legacy component envelopes did not contain this calculated cell.
        counts, scores = component["counts"], component["native_scores"]
        values = {name: scores[source] for name, source in (("native_score_bits", "bit_score"),
            ("native_raw_score", "score"), ("native_evalue", "evalue"))}
        values.update({name: counts.get(source) for name, source in (
            ("alignment_columns", "alignment_columns"), ("paired_positions", "paired_columns"),
            ("identical_positions", "identical_pairs"), ("query_gap_columns", "query_gap_columns"),
            ("reference_gap_columns", "reference_gap_columns"), ("query_aligned_positions", "paired_query_positions"),
            ("reference_aligned_positions", "paired_reference_positions"))})
        values["substituted_positions"] = archived_values["substituted_positions"]
        values.update({name: component["denominators"][name] for name in ("query_length", "reference_length")})
        values.update(component["fractions"])
        return values
    counts, scores = common["counts"], component["native_scores"]
    values = {name: scores[source] for name, source in (("native_score_bits", "bit_score"),
              ("native_raw_score", "score"), ("native_evalue", "evalue"))}
    values.update({name: counts.get(source) for name, source in (
        ("alignment_columns", "alignment_columns"), ("paired_positions", "paired_positions"),
        ("identical_positions", "identical_positions"), ("substituted_positions", "substituted_positions"),
        ("query_gap_columns", "query_gap_columns"), ("reference_gap_columns", "reference_gap_columns"))})
    values.update({axis + "_aligned_positions": common["paired_units"][axis] for axis in ("query", "reference")})
    values.update({name: component["denominators"][name] for name in ("query_length", "reference_length")})
    values.update(component["fractions"])
    return values

def _union_values(components, records, common=None):
    values = {axis + "_length": row["length"] for axis, row in records.items()}
    if components is None:
        return values
    union = components["union"]
    # An unreadable/absent report has no successful observed zero counts.
    if components["status"] != "alignment_report_unavailable":
        values.update({"observed_" + name: union["counts"][name] for name in (
            "distinct_residue_pairs", "identical_residue_pairs", "paired_query_positions", "paired_reference_positions")})
        values.update({name: union["counts"][name] for name in ("hsps_with_geometry", "hsps_without_geometry")})
        values.update({name: common["union"]["counts"][name] for name in
            ("conflicting_mapping_count", "identical_mapping_group_count")})
    values.update(union["fractions"])
    for axis, row in components["selected_operand_coverage"].items():
        values.update({axis + "_selected_" + target: row[source] for target, source in (
            ("length", "denominator"), ("paired_positions", "numerator"), ("paired_coverage", "value"))})
    return values

def _traceback_intervals(native, component, records, program, format_name, options):
    if component is None or not component["geometry_available"]:
        raise ValueError("native_blast_hsp_geometry_unavailable")
    units = PROGRAM_UNITS[program]
    intervals = {}
    for axis, prefix, unit, gencode in (("query", "query", units[0], "-query_gencode"),
                                       ("reference", "hit", units[1], "-db_gencode")):
        row = records[axis]
        geometry = _axis_geometry(native, prefix=prefix, length=row["length"], coordinate_unit=unit,
            alignment_unit=units[2], issues=[], symbols=native["qseq" if axis == "query" else "hseq"],
            coordinate_convention="blast_json2" if format_name == "json2" else "directional")
        if geometry is None:
            raise ValueError("native_blast_hsp_geometry_unavailable")
        start, end, width, direction = geometry
        interval = [min(start, end) - 1, max(start, end)]
        selected = row["selected_interval"] or [0, row["length"]]
        if not selected[0] <= interval[0] < interval[1] <= selected[1]:
            raise ValueError("native_blast_hsp_outside_selected_interval")
        sequence = row["sequence"][interval[0]:interval[1]]
        if direction < 0:
            sequence = str(Seq(sequence).reverse_complement())
        if width == 3:
            sequence = str(Seq(sequence).translate(table=int(options.get(gencode, 1))))
        displayed = native["qseq" if axis == "query" else "hseq"].replace("-", "").upper()
        if unit == "nt" and width == 1:
            sequence, displayed = sequence.replace("U", "T"), displayed.replace("U", "T")
        if sequence != displayed:
            raise ValueError("native_blast_traceback_sequence_mismatch:" + axis)
        intervals[axis] = interval
    return intervals

def _row(bundle, search, family, records, values, *, hit=None, hsp=None,
         native_status="alignment_report_unavailable", invalid=False, intervals=None):
    units = PROGRAM_UNITS[bundle["program"]]
    key = record_key(bundle, search["search_key"], family, hit, hsp)
    missing = {}
    for name in NATIVE_BLAST_METRICS[family]:
        if values.get(name) is None:
            missing[name] = ("invalid_native_row" if invalid else "missing_input"
                if (name.startswith("query_") and "query" not in records or
                    name.startswith("reference_") and "reference" not in records)
                else "incompatible_input" if native_status == "partial" else "not_measured")
    return {"version": "native_blast_complete_row_v1", "family": family,
        "record_key": key, "search_key": search["search_key"], "hit_ordinal": hit, "hsp_ordinal": hsp,
        "program": bundle["program"], "coordinate_units": dict(zip(("query", "reference", "alignment"), units)),
        "native_status": native_status, "invalid": invalid,
        "values": values, "unavailable": missing,
        "operands": {axis: {k: deepcopy(v) for k, v in operand.items() if k != "sequence"}
                     for axis, operand in records.items()}, "intervals": intervals}

def validate_native_blast_correspondence_collections(sheet, scores, *, admission=False):
    """Authenticate the explicit new collection companion without frozen regrading."""
    if (set(sheet) != {"schema", "collection", "searches", "publication_inputs", "correspondence"}
            or sheet["schema"] != "native_blast_sheet_collection_v2"
            or set(scores) != {"schema", "searches", "rows", "metric_definitions", "correspondence", "fallback_hsp_components"}
            or scores["schema"] != "native_blast_scores_collection_v2"
            or not _same(sheet["correspondence"], scores["correspondence"])):
        raise ValueError("native_blast_correspondence_collections_required")
    companion = validate_correspondence_artifacts(scores["correspondence"], admission=admission)
    expected = {}
    for index, entry in enumerate(scores["searches"]):
        if entry["scores"] is not None:
            expected["/searches/" + str(index) + "/scores/components"] = entry["scores"]["components"]
    for index, entry in enumerate(scores["fallback_hsp_components"]):
        expected["/fallback_hsp_components/" + str(index) + "/component"] = entry["component"]
    if {instance["legacy_pointer"] for instance in companion["instances"]} != set(expected):
        raise ValueError("native_blast_correspondence_instances_conflict")
    for instance in companion["instances"]:
        if instance["axis_basis"] != "qualified":
            raise ValueError("native_blast_correspondence_axis_conflict")
        validate_blast_correspondence_instance(expected[instance["legacy_pointer"]], instance)
