"""Original somatic variant received values for supplied decision information."""
from __future__ import annotations
from .decision_prompt_text import _rows
from .decision_prompt_text import _table
from .vcf_received_values import _vcf_result_text


def _somatic_variant_text(packet, number):
    """Copy selected native fields and qualifications; omit declared custody slots."""
    context = packet["context"]
    shown = {
        "inputs": [{"role": row["role"],
            "file_metadata": {key: row["file"][key] for key in ("format", "size_bytes")},
            "source_association": "retained supplied-input provenance" if row["source_ref"] is not None else None}
            for row in context["inputs"]],
        "sample_ids": context["sample_ids"], "reference_id": context["reference_id"],
        "software": {key: context["software"][key] for key in ("reported_versions", "loaded_dependencies_verified")},
        "annotation_database": {key: context["annotation_database"][key] for key in ("id", "reference_association")},
        "parameters": context["parameters"], "stages": context["stages"],
        "outputs": [{key: row[key] for key in ("role", "size_bytes")} for row in context["outputs"]],
        "issues": context["issues"], "definitions": context["definitions"],
    }
    return "\n\n".join([
        _vcf_result_text({"source_ref": packet["source_ref"], "value": packet["value"]}, number),
        "Recorded somatic native context; process completion is separate from biological truth",
        _table(("Selected native stage", "Retained value"), [("Stage", packet["selection"]["stage"])]),
        _table(("Context field", "Literal value"), _rows(shown))])


