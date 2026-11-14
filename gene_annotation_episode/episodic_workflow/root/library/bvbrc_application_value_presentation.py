"""Original supplied BV-BRC application-value display; no return authentication."""
from collections.abc import Mapping
from urllib.parse import unquote
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.bvbrc_application_value_identity import (
    ANNOTATION_VALUE_VERSION as VALUE_VERSION, ASSEMBLY_VALUE_VERSION,
    VARIATION_VALUE_VERSION, INFLUENZA_HA_VALUE_VERSION,
    SUBSPECIES_VALUE_VERSION, INTERVENTION_VALUE_VERSION, IDENTIFIER_NAMESPACE,
)

def select_application_execution_values(value):
    """Present declared selected values without interpreting native JSON keys.

    Only the adapter's context fields imply custody. Native identifiers and
    member names remain literal, including strings resembling Source handles.
    """
    if not isinstance(value, Mapping):
        return None
    if set(value) == {"source_ref", "field", "value"} and isinstance(value.get("value"), Mapping):
        selected = select_application_execution_values(value["value"])
        field = value.get("field")
        if selected is not None and isinstance(field, str) and field.startswith(IDENTIFIER_NAMESPACE + ":"):
            return {"field": unquote(field.rsplit("/", 1)[-1]), "value": selected}
        return None
    if value.get("version") == VARIATION_VALUE_VERSION:
        if set(value) != {"version", "selection", "state", "value", "context", "issues"}:
            return None
        result = plain(value)
        context = result.get("context")
        if isinstance(context, dict):
            for name in ("original_task", "content", "vcf_sheet_sha256"):
                context.pop(name, None)
        # Exact VCF metadata shapes only. Biological tokens, INFO keys and
        # strings resembling reference handles remain untouched literal data.
        def visible(node):
            if isinstance(node, dict):
                if set(node) == {"input_id", "retained_file", "original_file", "source_ref", "capture"}:
                    return {"capture": visible(node["capture"])}
                if set(node) == {"input_id", "artifact_ref", "sha256", "byte_start_0based",
                        "byte_end_0based_exclusive", "line_start_1based", "line_end_1based_inclusive"}:
                    return {key: child for key, child in node.items() if key not in {"input_id", "artifact_ref", "sha256"}}
                return {key: visible(child) for key, child in node.items()}
            if isinstance(node, list):
                return [visible(child) for child in node]
            return node
        result["value"] = visible(result["value"])
        return result
    if (value.get("version") not in (VALUE_VERSION, ASSEMBLY_VALUE_VERSION,
            INFLUENZA_HA_VALUE_VERSION, SUBSPECIES_VALUE_VERSION, INTERVENTION_VALUE_VERSION) or set(value) != {
            "version", "selection", "records", "record_accounting", "context", "issues"}
            or not isinstance(value.get("selection"), Mapping)
            or not isinstance(value.get("records"), (list, tuple))):
        return None
    result = plain(value)
    context = result.get("context")
    if isinstance(context, dict):
        context.pop("original_task", None)
        context.pop("content", None)
        identity = context.get("native_task_identity")
        if isinstance(identity, dict):
            identity.pop("observed_task_id", None)
    if result["selection"].get("kind") == "components":
        for row in result["records"]:
            if isinstance(row.get("value"), dict):
                row["value"].pop("document_sha256", None)
    if (result["version"] == ASSEMBLY_VALUE_VERSION and isinstance(context, dict)
            and context.get("representation") == "assembly_fasta"):
        for row in result["records"]:
            selected = row.get("value")
            if not isinstance(selected, dict):
                continue
            if result["selection"]["kind"] == "native_document":
                selected.pop("artifact", None)
                native_rows = selected.get("rows", [])
            elif result["selection"]["kind"] == "records":
                native_rows = [selected]
            else:
                native_rows = []
            for native_row in native_rows:
                if isinstance(native_row, dict) and isinstance(native_row.get("source_location"), dict):
                    native_row["source_location"].pop("artifact", None)
    return result


