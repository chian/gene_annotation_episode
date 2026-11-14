"""Original decision outcome presentation for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_presentation import render_rna_comparison_lookup
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import render_rna_structure_lookup
from .decision_prompt_text import _pick
from .decision_record_fields import _record
from .decision_prompt_text import _scalar
from .decision_prompt_text import _section
from .molecular_result_recognition import _selected_molecular_packet
from .decision_prompt_text import _table
from .molecular_value_presentation import _values


def _band(band):
    if not isinstance(band, Mapping):
        return "unavailable", "unavailable"
    code = band.get("status_code")
    if code not in (None, 0):
        status = {-1: "insufficient completed actions", -2: "unidentifiable"}.get(code,
            "unavailable (status " + str(code) + ")")
        return "unavailable", status
    if "value" not in band:
        return "unavailable", "unavailable"
    uncertainty = "lower=" + _scalar(band.get("lower")) + "; upper=" + _scalar(band.get("upper"))
    if "uncertainty_code" in band:
        uncertainty += "; " + {0: "exact", 1: "Chebyshev bound", 2: "approximate Laplace model band"}.get(
            band["uncertainty_code"], "unavailable uncertainty")
    if "alpha" in band:
        uncertainty += "; alpha=" + _scalar(band["alpha"])
    return _scalar(band["value"]), uncertainty


def _references(value):
    if isinstance(value, Mapping):
        for key, child in value.items():
            if (key in {"id", "ref"} or key.endswith("_ref")) and isinstance(child, str):
                yield child
            elif (key == "dependencies" or key.endswith("_refs")) and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _received_records(state):
    """Only current interpretations and records explicitly linked to this turn.

    Do not turn a scoped source inventory into received source content. No Store
    reads are performed; unresolved references remain operands for a later read.
    """
    working = state.get("working_state", {})
    # A Source is a storage/provenance envelope, not the acquired source's
    # scientific content. Do not expand received references into metadata here.
    # Explicit source operands remain in supplied material and action outcomes.
    fields = ("features", "products", "terms", "references", "contexts", "observations",
        "hypotheses", "assessments", "annotations", "interpretation_accounts")
    records = {row["id"]: row for field in fields for row in working.get(field, ())
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)}
    revision_status = {row["record_ref"]: row["is_current_revision"]
        for row in working.get("received_revision_status", ())}
    current = [row["id"] for field in ("annotations", "interpretation_accounts")
        for row in working.get(field, ()) if revision_status.get(row["id"], True)]
    selected = list(dict.fromkeys([*current,
        *state.get("scientific_process", {}).get("assignment", {}).get("evidence_refs", ()),
        *state.get("current_report_basis_refs", ()),
        *_references(state.get("current_report_update", {})),
        *_references(state.get("last_local_outcome", {})),
        *_references(state.get("child_reports", []))]))
    found = {}
    for reference in selected:
        if reference in found or reference not in records:
            continue
        row = records[reference]
        found[reference] = _record(row)
        selected.extend(ref for ref in _references(row) if ref not in found)
    return list(found.values())


def _feedback(value):
    """Keep actionable feedback without its private host diagnostic address."""
    if not isinstance(value, Mapping):
        return value
    return {key: child for key, child in value.items() if key != "diagnostic_ref"}


def _outcome(value):
    if not isinstance(value, Mapping):
        return value
    # Native result and feedback values are exact; operation receipts and full
    # estimator/tracking envelopes are not presentation. Revision preparation
    # is the exception: its origin is an operand required to commission it.
    shown = _pick(value, ("status", "record_refs", "changed_record_refs", "result", "feedback",
        "error_code", "errors", "conflicts", "notices", "aliases",
        "revision_origin", "automatic_preview", "visual_inputs", "child_completion"))
    if "feedback" in shown:
        shown["feedback"] = _feedback(shown["feedback"])
    proposal = shown.get("result")
    if isinstance(proposal, Mapping) and proposal.get("version") == "scientific_process_child_selection_v1":
        from ..scientific_process_records import (
            SELECTION_VERSION, selector_selection, validate_child_selection, validate_revision_origin)
        from gene_annotation_episode.tool_information import parent_view
        try:
            prepared = validate_child_selection(proposal)
            validate_revision_origin(shown.get("revision_origin"))
        except (ValueError, TypeError):
            return shown
        selected = prepared["selection"]
        if selected["version"] == SELECTION_VERSION:
            # The existing child-assignment interface accepts exact selectors
            # and restores/authenticates the original pinned tool information.
            # Full child instructions remain in the saved preparation, rather
            # than being copied into this parent's latest-outcome table.
            shown["result"] = {**prepared, "selection": selector_selection(selected)}
            shown["prepared_child_tools"] = parent_view(selected["child_tool_info"])
            shown["preparation_use"] = (
                "Commission a separate scientific_process child with result.selection and revision_origin. "
                "The host restores the complete pinned tool descriptions and instructions and authenticates "
                "them against the original preparation. This preparation does not change the current episode.")
    return shown


def _lookup(result):
    """Render only the explicit reply, never the recorded exchange transcript."""
    comparison = render_rna_comparison_lookup(result)
    if comparison is not None:
        return comparison
    original_rna = render_rna_structure_lookup(result)
    if original_rna is not None:
        return original_rna
    if not isinstance(result, Mapping):
        return _values(result)
    if result.get("view") == "own_attempts":
        parts = [_table(("Attempt operand", "Category", "Status", "Completed gain"),
            ((row["decision_index"], row.get("category"), row["status"], row.get("completed_gain"))
                for row in result.get("records", ())))]
        for row in result.get("records", ()):
            data = {"inputs": _bounded_inputs(row.get("inputs", {}))}
            publications = row.get("published_references", {})
            data["published_references"] = _pick(publications, ("values", "total", "included", "complete"))
            if not row.get("input_fields", {}).get("complete", True):
                data["more_input_query"] = row["input_fields"].get("detail_query")
            _section(parts, "Attempt " + str(row["decision_index"]), _values(data))
        _section(parts, "Lookup page", _values(_pick(result,
            ("total", "offset", "returned_count", "next_query", "unavailable_reasons"))))
        return "\n".join(parts)
    if result.get("view") == "own_attempt_detail":
        return _values(_bounded_inputs(_pick(result, ("decision_index", "pointer", "slice_unit",
            "offset", "total", "included", "values", "has_more", "next_query"))))
    content = result.get("result", result)
    if isinstance(content, Mapping) and content.get('information_kind') in (
            'operation_contract_information_v1', 'return_contract_information_v1'):
        parts = [_scalar(content.get('meaning', ''))]
        if content.get('information_kind') == 'return_contract_information_v1':
            parts.append('Child role: '+_scalar(content['role'])+'; fact source: '+_scalar(content['source']))
            parts.append('Explicit form reference: episode-fact:'+_scalar(content['source']))
        parts.append(_scalar(content['text']))
        return '\n\n'.join(parts)
    if isinstance(content, Mapping) and "text" in content:
        parts = [_scalar(content["text"])]
        page = _pick(content, ("entry_id", "section_id", "coordinate_unit", "offset", "returned_lines",
            "total_lines", "next_query"))
        if page:
            _section(parts, "Selected instruction window", _values(page))
        return "\n".join(parts)
    # Composition lookups have an ordinary outcome envelope. Library-specific
    # projections remove the instruction provenance while retaining selectable
    # option operands; no evidence records are fetched to decorate this reply.
    return _values(_information(_outcome(result) if "status" in result else result))


def _bounded_inputs(value):
    if isinstance(value, Mapping):
        if value.get("representation") == "bounded_selected_input_v1":
            return {"value_type": value["value_type"], **_pick(value,
                ("total", "included", "complete", "detail_query")),
                **({"values": _bounded_inputs(value["values"])} if "values" in value else {})}
        return {key: _bounded_inputs(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_bounded_inputs(child) for child in value]
    return value


def _molecular_source_metadata_view(value):
    """Show callable Source operands without private artifact addresses."""
    if (value.get("record_type") != "source" or value.get("origin") != "tool"
            or (value.get("provider"), value.get("version")) not in {
                ("analyze_protease_kinetics", "ordinary_protease_kinetics_result_v1"),
                ("analyze_arsenic_speciation_hplc_icpms", "ordinary_arsenic_speciation_result_v1"),
                ("predict_protein_disorder_regions", "ordinary_protein_disorder_result_v1"),
                ("generate_gene_embeddings_with_ESM_models", "esm_gene_embedding_result_v1"),
                ("analyze_protein_phylogeny", "ordinary_protein_phylogeny_result_v1"),
                ("detect_and_annotate_somatic_mutations", "ordinary_somatic_variant_result_v1"),
                ("analyze_protein_conservation", "ordinary_protein_conservation_result_v1")}):
        return None
    from gene_annotation_episode.episodic_workflow.root.communication import plain
    from gene_annotation_episode.domain import RECORD_SCHEMAS, identity, validate_schema
    try:
        source = plain(value)
        expected_fields = {"id", "record_type", "origin", "provider", "version", "accession", "uri",
            "artifact_ref", "text_ref", "request_ref", "retrieved_at", "parent_source_refs", "auxiliary_artifact_refs"}
        if set(source) != expected_fields:
            return None
        body = {key: child for key, child in source.items() if key not in {"id", "record_type", "origin"}}
        validate_schema(body, RECORD_SCHEMAS["source"])
        if source["id"] != identity("source", {"origin": source["origin"], "record": body}):
            return None
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return None
    if source["provider"] in {"analyze_protein_conservation", "analyze_protein_phylogeny", "generate_gene_embeddings_with_ESM_models", "detect_and_annotate_somatic_mutations"}:
        return {"source_ref": source["id"], "operation": source["provider"], "origin": source["origin"],
            "recorded_file_associations": {
                "selected_values": "recorded" if source["artifact_ref"] is not None else None,
                "verification_control": "recorded" if source["request_ref"] is not None else None,
                "text": "recorded" if source["text_ref"] is not None else None,
                "parent_sources": ["retained provenance" for _ in source["parent_source_refs"]],
                "auxiliary": ["recorded" for _ in source["auxiliary_artifact_refs"]]}}
    return {"source_ref": source["id"], "operation": source["provider"], "origin": source["origin"],
        "accession": source["accession"], "uri": source["uri"],
        "parent_source_refs": deepcopy(source["parent_source_refs"]),
        "recorded_file_associations": {
            "selected_values": "recorded" if source["artifact_ref"] is not None else None,
            "verification_control": "recorded" if source["request_ref"] is not None else None,
            "text": "recorded" if source["text_ref"] is not None else None,
            "auxiliary": ["recorded" for _ in source["auxiliary_artifact_refs"]]}}


def _information(value):
    if isinstance(value, Mapping):
        if value.get("version") in {"ordinary_protease_kinetics_values_v1", "ordinary_arsenic_speciation_values_v1",
                "ordinary_protein_disorder_values_v1", "ordinary_primer_placement_values_v1",
                "ordinary_protein_conservation_values_v1", "esm_gene_embedding_values_v1"}:
            packet = _selected_molecular_packet(value)
            if packet is not None:
                return packet
        source_metadata = _molecular_source_metadata_view(value)
        if source_metadata is not None:
            return source_metadata
        # P entries retain their source rows in the immutable library. They are
        # instruction provenance, not target evidence in a lookup continuation.
        if value.get("slot") == "thought_pattern":
            return {key: _information(child) for key, child in value.items() if key != "evidence"}
        if "option_ref" in value and "entry" in value:
            return {"option_ref": value["option_ref"], "entry": _information(value["entry"])}
        if "entries" in value and "library" in value:
            return {key: _information(child) for key, child in value.items() if key != "library"}
        if value.get("content_role") in {"tool_and_resource_instructions_not_scientific_evidence",
                "launch_instructions_not_inventory_or_scientific_evidence"}:
            return {key: _information(child) for key, child in value.items() if key not in
                {"version", "library_id", "entry_count", "content_role", "section_sha256"}}
        return {key: _information(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_information(child) for child in value]
    return value


def _progress(row):
    """Current already-received progress, retaining measured facts and read operands."""
    result = _pick(row, ("target_handle", "observed_at", "result_available", "committed_record_refs"))
    status = row.get("execution_status", {})
    result["execution_status"] = _pick(status, ("handle", "observed_at", "lifecycle_state", "liveness",
        "result_available", "return_available", "failure", "resource_kind"))
    if isinstance(status.get("native"), Mapping):
        result["native_status"] = _pick(status["native"], ("state", "outcome", "returncode", "failure_code",
            "elapsed_seconds", "duration_measure", "measurements", "outputs"))
    result["measurements"] = row.get("measurements", [])
    result["log_windows"] = [_pick(window, ("source_ref", "artifact_ref", "start_byte", "end_byte",
        "observed_at")) for window in row.get("log_windows", ())]
    result["dependencies"] = [_pick(child, ("handle", "kind", "observed_at", "state"))
        for child in row.get("dependencies", ())]
    return result


