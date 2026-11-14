"""Original esm embedding received values for supplied decision information."""
from __future__ import annotations
from copy import deepcopy
from .decision_prompt_text import _rows
from .decision_prompt_text import _table


def _esm_gene_embedding_text(packet, number):
    """Display literal selected representations without private custody slots."""
    context = deepcopy(packet["context"])
    # These are declared provenance slots, not fields in opaque scientific
    # headers, symbols or caller-supplied protein/isoform/gene identifiers.
    context.pop("selected_checkpoint_sha256")
    context.pop("selected_regression_checkpoint_sha256")
    original_file = context.pop("input_file")
    context["input_file_metadata"] = {key: original_file[key] for key in ("format", "size_bytes")}
    context["input_source_ref"] = ("Retained supplied-input provenance"
        if context["input_source_ref"] is not None else None)
    return "\n\n".join(["Selected molecular result " + str(number),
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Operation", "generate_gene_embeddings_with_ESM_models"),
            ("Meaning", "Literal model representations; no function-probability interpretation")]),
        _table(("Retained field/member", "Literal value"), _rows({
            "selection": packet["selection"], "context": context,
            **{name: packet[name] for name in ("residues", "proteins", "isoforms", "genes")}}))])


