"""Private A104 retained source-representation selection."""
from .domain import ContractError

def source_window_selection(source, representation):
    """Select the existing representation using metadata, without opening bytes."""
    if representation not in {"text", "original", "stdout", "stderr"}:
        raise ContractError("invalid_source_representation")
    available = ["original"] + [name for name in ("text", "stdout", "stderr") if source.get(name + "_ref")]
    if representation in {"stdout", "stderr"}:
        if representation not in available:
            raise ContractError("source_representation_unavailable", detail={
                "representation": representation, "available_representations": available})
        selected_ref = source[representation + "_ref"]
    else:
        representation = "text" if representation == "text" and source.get("text_ref") else "original"
        selected_ref = source["text_ref"] if representation == "text" else source["artifact_ref"]
    return selected_ref, representation, available


