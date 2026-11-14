"""Original A101 scientific values; custody remains at the host call boundary."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError


PRESETS = ["map-ont", "map-pb", "map-hifi", "lr:hq", "map-iclr", "sr"]


PARAMETERS = {"kmer": "-k", "window": "-w", "max_secondary": "-N", "seed": "--seed"}


NATIVE_INT_MAX = 2147483647


PARAMETER_RANGES = {"kmer": (1,28), "window": (1,255),
    "max_secondary": (0,NATIVE_INT_MAX), "seed": (0,NATIVE_INT_MAX)}


_COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVNacgtryswkmbdhvn", "TGCAYRSWMKVHDBNtgcayrswmkvhdbn")


def native_integer(value, *, field_path, minimum, maximum):
    detail = {"field_path": list(field_path), "minimum": minimum, "maximum": maximum,
        "native_representation": "minimap2_2_31_supported_integer_interface"}
    if type(value) is not int:
        raise ContractError("native_mapping_integer_required", detail={**detail, "actual_type": type(value).__name__})
    if not minimum <= value <= maximum:
        raise ContractError("native_mapping_integer_out_of_range", detail={**detail, "value": value})
    return value


def parameter_schema(name):
    low, high = PARAMETER_RANGES[name]
    field = {"type":"integer", "minimum":low, "maximum":high}
    if name == "max_secondary":
        field["description"] = ("Native -N0 is a supported alias: it disables secondary output and retains "
            "the prior preset's internal best_n, even with secondary=true. Selected flags are preserved.")
    return field


def parameter_schema_failure(error, *, path_prefix=()):
    """Project an existing field validation failure; do not validate again.

    The caller selects the actual reads.map schema branch. Other fields and
    schema failures keep their normal feedback rather than being guessed here.
    """
    path = list(getattr(error, "absolute_path", ()))
    prefix = list(path_prefix)
    relative = path[len(prefix):] if path[:len(prefix)] == prefix else []
    if (len(relative) != 2 or relative[0] != "parameters"
            or relative[1] not in PARAMETER_RANGES
            or error.validator not in ("minimum", "maximum", "type")
            or error.schema.get("type") != "integer"):
        return None
    detail = {"field_path": relative, "minimum": error.schema["minimum"],
        "maximum": error.schema["maximum"], "schema_keyword": error.validator,
        "native_representation": "minimap2_2_31_supported_integer_interface"}
    if error.validator == "type":
        detail["actual_type"] = type(error.instance).__name__
        code = "native_mapping_integer_required"
    else:
        detail["value"] = error.instance
        code = "native_mapping_integer_out_of_range"
    return {"code": code, "detail": detail}


def settings(preset, parameters=None):
    if preset not in PRESETS:
        raise ContractError("unsupported_genomic_mapping_preset")
    given = dict(parameters or {})
    if set(given) - (set(PARAMETERS) | {"secondary", "homopolymer_compression"}):
        raise ContractError("unknown_mapping_parameter")
    for key,(low,high) in PARAMETER_RANGES.items():
        if key in given:
            native_integer(given[key], field_path=["parameters",key], minimum=low, maximum=high)
    for key in ("secondary", "homopolymer_compression"):
        if key in given and type(given[key]) is not bool:
            raise ContractError("invalid_native_mapping_parameter", detail={"field_path": ["parameters", key]})
    # -H is enable-only. A false override must not silently leave a preset's
    # enabled HPC unchanged; the initial interface exposes an explicit true.
    if given.get("homopolymer_compression") is False:
        raise ContractError("native_homopolymer_flag_is_enable_only",
            detail={"field_path": ["parameters", "homopolymer_compression"], "allowed_value": True})
    effects = ([{"option":"max_secondary", "requested":0,
        "native_effect":"secondary_output_disabled_prior_preset_internal_best_n_retained",
        "secondary_yes_does_not_override_zero_alias":True}]
        if given.get("max_secondary") == 0 else [])
    return {"preset": preset, "overrides": given, "native_option_effects":effects,
        "base_alignment": "PAF_cg_and_cs_long",
        "fragment_mode": "unpaired", "quality_used_for_mapping": False,
        "native_unset_options": "installed_version_preset_defaults_not_host_overrides"}


def _paf_error(error):
    code = str(error)
    # Preserve the established representation-failure category for ordinary
    # callers, with the new parser's precise tag diagnostic retained in detail.
    if code.startswith("native_paf_duplicate_tag:") or code in {
            "invalid_native_paf_tag", "invalid_native_paf_tag_value"}:
        return ContractError("invalid_native_paf_row", detail={"native_parser_code": code})
    return ContractError(code)


def cigar_operations(cigar):
    from gene_annotation_episode.episodic_workflow.root.a101.library.minimap2_grading_inputs import cigar_operations as parse_cigar
    try:
        return [(row["operation"], row["length"]) for row in parse_cigar(cigar)]
    except ValueError as error:
        raise _paf_error(error) from error


def cs_operations(cs):
    from gene_annotation_episode.episodic_workflow.root.a101.library.minimap2_grading_inputs import cs_operations as parse_cs
    try:
        return [(row["operation"], row["length"], row["value"]) for row in parse_cs(cs)]
    except ValueError as error:
        raise _paf_error(error) from error


def parse_paf_line(line):
    """Shared native parser for publication, admission and later site use.

    Raw lines remain in the original PAF artifact. Do not add a full raw row to
    the ordinary placement preview: it includes long alignment strings.
    """
    from gene_annotation_episode.episodic_workflow.root.a101.library.minimap2_grading_inputs import parse_minimap2_paf_row
    try:
        row = parse_minimap2_paf_row(line)
    except ValueError as error:
        raise _paf_error(error) from error
    return {key: value for key, value in row.items() if key not in {"native_line", "issues"}}


def compare_paf_sites(row, reference_positions, *, query, reference, quality=None, quality_encoding="unspecified"):
    """Observe actual operand bases along a native CIGAR, never call variants.

    Query positions/quality indices always use its original strand. Returned
    query_residue is oriented to the reference; original symbols remain explicit.
    Insertions use a reference boundary, not a fabricated reference residue.
    """
    if len(query) != row["query_length"] or len(reference) != row["reference_length"]:
        raise ContractError("native_alignment_operand_length_changed")
    if not row.get("cigar"):
        raise ContractError("native_base_alignment_unavailable")
    if any(type(p) is not int or not 0 <= p < len(reference) for p in reference_positions):
        raise ContractError("invalid_reference_site")
    if quality is not None and len(quality) != len(query):
        raise ContractError("native_query_quality_length_mismatch")
    if quality_encoding not in {"unspecified", "phred33", "phred64", "solexa64"}:
        raise ContractError("unknown_quality_encoding")
    wanted, found, insertions = set(reference_positions), {}, []
    plus = row["strand"] == "+"
    q = row["query_interval"][0] if plus else row["query_interval"][1]-1
    r = row["reference_interval"][0]
    direction = 1 if plus else -1

    def query_data(position):
        original = query[position]
        char = quality[position] if quality is not None else None
        numeric = (ord(char) - (33 if quality_encoding == "phred33" else 64)
            if char is not None and quality_encoding != "unspecified" else None)
        return {"query_position": position, "query_original_residue": original,
            "query_residue": original if plus else original.translate(_COMPLEMENT),
            "query_quality_character": char, "query_quality_score": numeric,
            "quality_encoding": quality_encoding}

    for kind, size in cigar_operations(row["cigar"]):
        if kind in "M=X":
            for position in wanted:
                if r <= position < r+size:
                    data = query_data(q + direction*(position-r))
                    found[position] = {"reference_position": position, "reference_residue": reference[position],
                        **data, "relationship": "identical" if data["query_residue"].upper() == reference[position].upper() else "substituted",
                        "native_operation": kind, "query_strand": row["strand"]}
            q += direction*size; r += size
        elif kind in "DN":
            for position in wanted:
                if r <= position < r+size:
                    found[position] = {"reference_position": position, "reference_residue": reference[position],
                        "query_position": None, "query_original_residue": None, "query_residue": None,
                        "query_quality_character": None, "query_quality_score": None, "quality_encoding": quality_encoding,
                        "relationship": "gap" if kind == "D" else "reference_skip", "native_operation": kind,
                        "query_strand": row["strand"]}
            r += size
        else:  # I: query bases between reference positions, not a reference base.
            if r in wanted or r-1 in wanted:
                indices = range(q, q + direction*size, direction)
                original_positions = [min(q, q+direction*(size-1)), max(q, q+direction*(size-1))+1]
                insertions.append({"reference_boundary": r, "query_interval": original_positions,
                    "query_strand": row["strand"], "query_sequence": "".join(query_data(p)["query_residue"] for p in indices),
                    "query_quality_characters": ("".join(quality[p] for p in indices) if quality is not None else None),
                    "quality_encoding": quality_encoding, "native_operation": "I"})
            q += direction*size
    return {"sites": [found.get(p, {"reference_position": p, "reference_residue": None,
        "query_position": None, "query_residue": None, "relationship": "outside_alignment",
        "query_strand": row["strand"]}) for p in reference_positions], "insertions": insertions,
        "quality_encoding": quality_encoding, "mapping_quality": row["mapping_quality"],
        "mapping_quality_available": row["mapping_quality_available"],
        "native_alignment_type": row["native_alignment_type"]}
