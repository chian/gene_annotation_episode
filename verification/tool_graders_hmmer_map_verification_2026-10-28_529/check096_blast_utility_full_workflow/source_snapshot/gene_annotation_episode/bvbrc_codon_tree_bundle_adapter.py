"""Pure C4 entry point for the selected CodonTree codon/protein service mode."""
from .bvbrc_phylogeny_bundle_contracts import requested_form_schema, validate_requested_form
from .bvbrc_phylogeny_bundle_contracts import validate_parameters as _parameters
from .bvbrc_phylogeny_bundle_projection import consume_bundle as _consume, implementation_sha256

ADAPTER_ID = "bvbrc_codon_tree"
ADAPTER_VERSION = "1"


def validate_parameters(parameters):
    return _parameters(parameters, provider="codon_tree")


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict],
                   requested_form: dict, parameters: dict) -> dict:
    return _consume(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values,
                    requested_form=requested_form, parameters=parameters, provider="codon_tree")


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "implementation_sha256", "validate_parameters",
           "requested_form_schema", "validate_requested_form", "consume_bundle"]
