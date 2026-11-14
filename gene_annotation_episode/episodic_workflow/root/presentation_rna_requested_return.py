"""Original presentation of a supplied parent form and exact recorded RNA facts."""
from __future__ import annotations
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_views import PROJECTION_SOURCE
from .library.decision_prompt_text import _pick, _scalar, _section, _table
from .library.decision_schema_display import _schema
from .library.molecular_value_presentation import _values


def _text(value):
    return _values(value) if isinstance(value, (Mapping, list, tuple)) else _scalar(value)


def render_rna_comparison_requested_return(state: Mapping) -> str:
    """Explain the actual parent's form; recorded RNA rows need no model entry.

Only the top-level, exact comparison fact source receives compact treatment.
The authoritative schema and every interpretation constraint remain untouched.
Other fact sources retain their declared field/schema and source meanings.
"""
    parts = []
    purpose = state.get("requested_report_purpose")
    if purpose is not None:
        _section(parts, "Information requested by the parent", _text(purpose))
    form = state.get("requested_form")
    if form is None:
        _section(parts, "Parent return form", "Absent: no parent return form was supplied.")
    else:
        from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import rna_structure_return_schema_view
        shown = rna_structure_return_schema_view(plain(form))
        for name, node in shown.get("properties", {}).items():
            if node.get("x-source") == PROJECTION_SOURCE:
                # The complete eight-family source contract is host-validated.
                # It is not an interpretation form for the model to populate.
                shallow = _pick(node, ("type", "description", "x-source",
                    "minItems", "maxItems", "uniqueItems"))
                shallow["description"] = (node.get("description", "") +
                    ("; " if node.get("description") else "") +
                    "Automatically supplied requested RNA comparison facts and their required qualifications.")
                shown["properties"][name] = shallow
        _section(parts, "Parent return form", _schema(shown, "return"))
        sources = state.get("available_report_facts", {})
        requested = {node.get("x-source") for node in form.get("properties", {}).values()}
        meanings = [(name, sources[name].get("meaning", "")) for name in sources if name in requested]
        if meanings:
            _section(parts, "Meaning of requested recorded facts", _table(("Source", "Meaning"), meanings))
    lifecycle = state.get("report_lifecycle")
    if lifecycle is not None:
        _section(parts, "Return interpretation timing", _text(lifecycle))
    return "\n".join(parts).lstrip("\n")


