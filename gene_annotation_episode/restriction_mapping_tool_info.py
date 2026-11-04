"""One ordinary restriction support tool using the existing native and saved owners."""
from copy import deepcopy

from .restriction_mapping_contracts import restriction_schema


TOOL = "find_restriction_sites"


def restriction_tool_contract():
    """Describe explicit current selections without changing retained arguments."""
    reference = {"type": "string", "minLength": 1, "format": "reference"}
    native = {
        "mode": {"type": "string", "const": "native"},
        "sequence_ref": deepcopy(reference),
        "enzyme_selection": restriction_schema("EnzymeSelection"),
        "topology": {"type": "string", "enum": ["linear", "circular"]},
    }
    saved = {
        "mode": {"type": "string", "const": "saved"},
        "result_source_ref": {**reference, "x-reference-namespace": "source"},
    }
    return {
        "name": TOOL,
        "resources": "local",
        "invocation_route": {"kind": "direct"},
        "description": (
            "Predict restriction-enzyme cut and recognition positions in one explicitly received DNA sequence, "
            "preserving the selected enzyme population and linear or circular topology."
        ),
        "input_schema": {"anyOf": [
            {"type": "object", "properties": fields, "required": list(fields),
                "additionalProperties": False}
            for fields in (native, saved)
        ]},
        "instructions": (
            "Use this ordinary tool within the current episode for the assigned restriction-mapping question. "
            "In native mode, select an actual received sequence_ref, explicit topology and enzyme_selection. "
            "An explicit selection uses exact enzyme names in the supplied order, including an explicitly empty list. "
            "commercial_native_batch with names=null selects the commercial population of the pinned native catalog; "
            "the actual resolved members are retained. No enzyme aliases or alternative population are substituted. "
            "Saved mode selects result_source_ref and reads its retained native observations and catalog through "
            "the same result reader without another native enzyme search. Preserve the original sequence binding.\n\n"
            "Keep each row's position_meaning: first_base_after_cut_1based for native cut positions, "
            "recognition_start_1based for no-cut enzyme recognition positions, or unknown when unavailable. "
            "Derived Watson/Crick boundaries use zero-based nucleotide boundaries; recognition spans use "
            "zero-based half-open intervals and retain original orientation and circular-origin segments. "
            "A recognition event is not assigned to an individual cut when the retained association is not_recorded. "
            "Returned position counts and observed recognition-match counts are distinct.\n\n"
            "Preserve selected, attempted and returned enzyme counts, complete empty enzyme searches, "
            "recognition-match populations, partial results and unavailable values. A complete empty position list "
            "differs from a search that did not return; unknown counts remain null. These conditional sequence "
            "predictions are supporting data, not measured digestion, reagent design or gene-function confidence. "
            "Return only the parent's requested fields using the existing typed restriction result contract."
        ),
    }


__all__ = ["TOOL", "restriction_tool_contract"]
