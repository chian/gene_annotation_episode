"""A101 retained pairwise source correspondence validation; no alignment execution."""
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_alignment.alignment_correspondence import BASE_COUNT_NAMES, populate_correspondence_sheet

_COUNT_FIELDS = (
    "alignment_columns", "paired_positions", "identical_positions",
    "substituted_positions", "query_gap_columns", "reference_gap_columns",
    "query_aligned_positions", "reference_aligned_positions",
)

def _common_sheet(*, counts, lengths, geometry, correspondence, alignment_state, molecule):
    """Adapt measured cells; never manufacture another producer's traceback."""
    if alignment_state == "no_alignment":
        measurement = {"kind": "explicit_no_alignment"}
    elif counts is None or all(value is None for value in counts.values()):
        measurement = {"kind": "unavailable"}
    else:
        measurement = {"kind": "validated_saved_counts", "basis": "traceback",
            "counts": {name: counts[name] for name in BASE_COUNT_NAMES}}
    available = geometry["available"]
    pairs = [{"query_start": row["query_position"], "query_end": row["query_position"] + 1,
        "reference_start": row["reference_position"], "reference_end": row["reference_position"] + 1,
        "identical": row["relationship"] == "identical"}
        for row in correspondence if row["query_position"] is not None and row["reference_position"] is not None]
    unit = "aa" if molecule == "protein" else "nt"
    return populate_correspondence_sheet(
        operands={"query": {"length": lengths["query"], "unit": unit},
            "reference": {"length": lengths["reference"], "unit": unit}, "alignment_unit": unit},
        rows=[{"source_key": "", "measurement_input": measurement,
            "paired_lengths": dict(lengths),
            "span_inputs": {axis: {"interval": deepcopy(geometry[axis + "_interval"]) if available else None,
                "length": lengths[axis]} for axis in ("query", "reference")},
            "geometry_available": available, "pairs": pairs,
            "symbol_widths": {"query": 1, "reference": 1},
            "reported_alignment_identity_fallback": None}],
        population={"original_rows_complete": True, "execution_state": "unknown",
            "producer_state": "unknown", "explicit_zero_result": alignment_state == "no_alignment"},
        selected_intervals={"query": None, "reference": None})

def _definitions(molecule):
    unit = "amino_acid_positions" if molecule == "protein" else "nucleotide_positions"
    formulas = {
        "alignment_columns": "len(traceback.query)",
        "paired_positions": "count(columns where query and reference are both nongap)",
        "identical_positions": "count(paired columns with literal equal uppercase symbols)",
        "substituted_positions": "paired_positions - identical_positions",
        "query_gap_columns": "count(traceback.query symbols equal to '-')",
        "reference_gap_columns": "count(traceback.reference symbols equal to '-')",
        "query_aligned_positions": "alignment_columns - query_gap_columns",
        "reference_aligned_positions": "alignment_columns - reference_gap_columns",
        "paired_identity": "identical_positions / paired_positions",
        "alignment_identity": "identical_positions / alignment_columns",
        "query_paired_coverage": "paired_positions / lengths.query, with validated geometry",
        "reference_paired_coverage": "paired_positions / lengths.reference, with validated geometry",
        "query_aligned_coverage": "query_aligned_positions / lengths.query, with validated geometry",
        "reference_aligned_coverage": "reference_aligned_positions / lengths.reference, with validated geometry",
        "native_score": "native_result.native_score, unchanged",
    }
    ratio_inputs = {
        "paired_identity": ("measured_column_counts.identical_positions", "measured_column_counts.paired_positions"),
        "alignment_identity": ("measured_column_counts.identical_positions", "measured_column_counts.alignment_columns"),
        "query_paired_coverage": ("measured_column_counts.paired_positions", "lengths.query"),
        "reference_paired_coverage": ("measured_column_counts.paired_positions", "lengths.reference"),
        "query_aligned_coverage": ("measured_column_counts.query_aligned_positions", "lengths.query"),
        "reference_aligned_coverage": ("measured_column_counts.reference_aligned_positions", "lengths.reference"),
    }
    definitions = {}
    for name, formula in formulas.items():
        fraction = name.endswith(("identity", "coverage"))
        inputs = (["native_score"] if name == "native_score" else
                  list(ratio_inputs[name]) if fraction else ["measured_column_counts." + name])
        if name.endswith("coverage"):
            inputs += ["geometry.available", "alignment_state"]
        definitions[name] = {
            "formula": formula,
            "inputs": inputs,
            "measurement_source": ("native_result.native_score" if name == "native_score"
                                   else ["native_result.aligned_query", "native_result.aligned_reference"]),
            "denominator": "denominators." + name if fraction else None,
            "units": "fraction" if fraction else "native_alignment_score" if name == "native_score"
                     else "alignment_columns" if name.endswith("columns") else unit,
            "population": ("full_query_operand" if name.startswith("query_") and name.endswith("coverage") else
                           "full_reference_operand" if name.startswith("reference_") and name.endswith("coverage") else
                           "paired_alignment_columns" if name == "paired_identity" else "supplied_native_alignment"),
            "kind": "native_algorithm_score" if name == "native_score" else "derived_from_native_alignment",
            "missing": ("null_when_native_score_missing_or_invalid" if name == "native_score" else
                        "null_when_geometry_invalid_or_length_missing_or_zero; explicit_no_alignment_uses_zero_positions"
                        if name.endswith("coverage") else
                        "null_when_count_missing_or_denominator_zero" if fraction else
                        "null_when_traceback_unavailable_or_invalid; zero_for_explicit_no_alignment"),
            "coordinate_system": "zero_based_half_open" if name.endswith("coverage") else None,
            "uncertainty": None,
        }
    return definitions

def project_biopython_scores(sheet, common):
    """Select the legacy score cells from stored common calculated cells."""
    counts = {name: common["counts"][name] for name in _COUNT_FIELDS}
    lengths = common["paired_lengths"]
    denominators = {"paired_identity": counts["paired_positions"],
        "alignment_identity": counts["alignment_columns"],
        "query_paired_coverage": lengths["query"], "reference_paired_coverage": lengths["reference"],
        "query_aligned_coverage": lengths["query"], "reference_aligned_coverage": lengths["reference"]}
    return {"schema": "biopython_pairwise_scores_v1", "status": sheet["status"], **counts,
        **{field: common["fractions"][field] for field in denominators},
        "native_score": sheet["native_score"], "denominators": denominators,
        "definitions": _definitions(sheet["molecule"]), "issues": deepcopy(sheet["issues"])}

def validate_biopython_correspondence(grading, instance):
    """Compare retained facts/projections without regrading a frozen source."""
    from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_alignment.alignment_correspondence import _same
    sheet = grading["sheet"]
    expected = _common_sheet(counts=sheet["measured_column_counts"], lengths=sheet["lengths"],
        geometry=sheet["geometry"], correspondence=sheet["residue_correspondence"],
        alignment_state=sheet["alignment_state"], molecule=sheet["molecule"])
    if (instance["legacy_pointer"] != "" or instance["axis_basis"] != "direct"
            or not _same(expected, instance["sheet"])
            or not _same(project_biopython_scores(grading["sheet"], instance["components"]["rows"][0]), grading["scores"])):
        raise ValueError("biopython_saved_correspondence_conflict")
