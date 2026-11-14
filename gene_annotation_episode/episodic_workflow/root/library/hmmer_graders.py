"""Pure dispatch for supplied HMMER outputs and numerical scoring sheets.

Resource selection and acquisition remain with the owning episode. These
functions select actual native formats, populate sheets and calculate their
components. They perform no I/O, reference lookup, submission or observation.
"""
from __future__ import annotations

import json


def grade_hmmer_api_result(content, *, algorithm, artifact_ref, inputs,
                          parameters=None):
    from .hmmer_search_inputs import parse_hmmer_api_result, build_hmmer_search_sheet
    from .hmmer_search_grader import calculate_hmmer_search_scores

    try:
        payload = json.loads(content) if isinstance(content, (bytes, str)) else content
    except (ValueError, UnicodeError) as error:
        raise ValueError("hmmer_api_payload_invalid_json") from error
    native = parse_hmmer_api_result(payload, algorithm=algorithm, artifact_ref=artifact_ref)
    sheet = build_hmmer_search_sheet(native, inputs=inputs)
    return {"sheet": sheet, "scores": calculate_hmmer_search_scores(sheet, parameters=parameters)}


def grade_hmmer_native_artifacts(*, program, artifacts, artifact_refs,
                                engine_version, inputs, parameters=None,
                                checkpoints=()):
    """Grade explicitly supplied complete or partial native text artifacts.

    Searches take stdout/tblout/domtblout as applicable. hmmalign takes the
    actual Stockholm under the ``stockholm`` role; a log or HTML page is not
    an alignment. Large callers can instead use the family streaming parsers
    and the same sheet builders/calculators on their explicitly associated rows.
    """
    if program in {"phmmer", "hmmscan", "hmmsearch", "jackhmmer"}:
        from .hmmer_search_inputs import parse_hmmer_search_artifacts, build_hmmer_search_sheet
        from .hmmer_search_grader import calculate_hmmer_search_scores
        native = parse_hmmer_search_artifacts(program=program, artifacts=artifacts,
            artifact_refs=artifact_refs, engine_version=engine_version, checkpoints=checkpoints)
        sheet = build_hmmer_search_sheet(native, inputs=inputs)
        scores = calculate_hmmer_search_scores(sheet, parameters=parameters)
    elif program in {"nhmmer", "nhmmscan"}:
        if checkpoints:
            raise ValueError("hmmer_checkpoints_not_applicable_to_nucleotide_search")
        from .nhmmer_inputs import parse_nhmmer_artifacts, build_nhmmer_sheet
        from .nhmmer_grader import calculate_nhmmer_scores
        native = parse_nhmmer_artifacts(program=program, artifacts=artifacts,
            artifact_refs=artifact_refs, engine_version=engine_version)
        sheet = build_nhmmer_sheet(native, inputs=inputs)
        scores = calculate_nhmmer_scores(sheet, parameters=parameters)
    elif program == "hmmalign":
        if checkpoints:
            raise ValueError("hmmer_checkpoints_not_applicable_to_profile_alignment")
        if (not isinstance(artifacts, dict) or set(artifacts) != {"stockholm"}
                or not isinstance(artifact_refs, dict) or "stockholm" not in artifact_refs):
            raise ValueError("hmmalign_stockholm_artifact_required")
        from .hmmalign_inputs import parse_hmmalign_stockholm, build_hmmalign_sheet
        from .hmmalign_grader import calculate_hmmalign_scores
        native = parse_hmmalign_stockholm(artifacts["stockholm"],
            artifact_ref=artifact_refs["stockholm"], engine_version=engine_version)
        sheet = build_hmmalign_sheet(native, inputs=inputs)
        scores = calculate_hmmalign_scores(sheet, parameters=parameters)
    else:
        raise ValueError("hmmer_grading_program_unsupported")
    return {"sheet": sheet, "scores": scores}


HMMER_DOMAIN_METRICS = (
    "model_length", "sequence_length", "model_span_positions",
    "sequence_span_residues", "sequence_envelope_residues", "model_span_coverage",
    "sequence_span_coverage", "sequence_envelope_coverage", "paired_positions",
    "insert_positions", "delete_positions", "alignment_columns", "paired_model_coverage",
    "paired_sequence_coverage", "sequence_identity_fraction", "consensus_identity_fraction",
    "alignment_identity_fraction", "api_identity_fraction", "native_domain_score_bits",
    "native_domain_bias_bits", "native_conditional_evalue", "native_independent_evalue",
    "native_accuracy", "posterior_lower_mean", "posterior_upper_mean",
)


def api_domain_scores(grading, *, hit_array_index, domain_array_index, artifact_ref=None):
    """Match one original array position, never a filtered or native ordinal.

    The explicit index join is a publication boundary. An ambiguous grading
    result rejects rather than assigning numbers to an arbitrary sibling.
    """
    if (grading.get("failure") or type(hit_array_index) is not int
            or type(domain_array_index) is not int):
        return {}
    scores = grading.get("scores") or {}
    rows = [row for row in scores.get("domains", ())
        if row.get("locator", {}).get("hit_array_index") == hit_array_index
        and row.get("locator", {}).get("domain_array_index") == domain_array_index]
    if len(rows) > 1:
        raise ValueError("hmmer_grading_domain_locator_ambiguous")
    if rows and artifact_ref is not None and rows[0]["locator"].get("artifact_ref") != artifact_ref:
        raise ValueError("hmmer_grading_domain_artifact_mismatch")
    return rows[0] if rows else {}
