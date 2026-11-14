"""Original primer received context for supplied decision information."""
from __future__ import annotations
from .molecular_provenance_display import _molecular_literal
from .decision_prompt_text import _rows
from .decision_prompt_text import _table


def _primer_placement_context_text(packet):
    """Show retained operand and population metadata without projecting new hits."""
    context = packet["context"]

    def sequence(value):
        if isinstance(value, str) and len(value) > 120:
            return str(len(value)) + " symbols retained in the result context"
        return _molecular_literal(value)

    inputs, operand_rows = context["input"], []
    if inputs is not None:
        operand_rows.append(("target_sequence", sequence(inputs["target_sequence"])))
        primers = inputs["primers"]
        operand_rows.append(("primer input form", "ordered list" if isinstance(primers, list) else "scalar"))
        if isinstance(primers, list):
            operand_rows.extend(("primers[" + str(index) + "]", sequence(value)) for index, value in enumerate(primers))
            if not primers:
                operand_rows.append(("primers", "[]"))
        else:
            operand_rows.append(("primers", sequence(primers)))
        operand_rows.extend((name, _molecular_literal(inputs[name])) for name in
            ("target_ref", "primer_refs", "target_mapping", "primer_mappings"))
    metadata = [(name, _molecular_literal(context[name])) for name in
        ("sheet_state", "components_state", "native_outcome", "component_status", "source_assumptions")]
    for name in ("population", "group_populations", "definitions", "issues"):
        metadata.extend(_rows(context[name], name))
    return "\n\n".join(["Retained primer-placement operands and populations",
        _table(("Original operand property", "Supplied value"), operand_rows) if inputs is not None else "Original operands unavailable.",
        _table(("Retained property", "Supplied value"), metadata)])


