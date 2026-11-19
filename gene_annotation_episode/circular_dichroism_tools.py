"""The CD tool contract and its Store-free worker calculation.

The worker reads only its copied File and uses the existing CD numerical
authority. It chooses no other method and creates no episode.
"""
import hashlib
import os
from pathlib import Path
import stat

from . import circular_dichroism_contracts as contracts
from . import circular_dichroism_measurements as core
from .molecular_sequence_input_contracts import decode_molecular_sequence_input


CD_TOOL = contracts.CD_TOOL


def circular_dichroism_tool_contract():
    return dict(resources="local", description=(
        "Calculate source-defined signed spectral point counts and relative thermal-signal summaries from an "
        "explicitly received versioned CD JSON File. Retain ordered measurements, units, original point identities, "
        "partial results and the source-labelled heuristic qualifications. Thermal summaries use min-max relative "
        "signal, the first sampled point nearest one half, and the source's N-point transition width. "
        "These are descriptive source heuristics, with no calibrated structure fractions, fitted melting parameters "
        "or function-confidence probabilities. Alternatively read literal stored values or recalculate the retained "
        "sheet with the same numerical authority. Explicit selected-row views preserve original ordinals and the "
        "full original populations; neither saved mode acquires data or republishes the original Source."),
        input_schema=contracts.circular_dichroism_tool_argument_schema())


def _regular(path):
    try:
        return stat.S_ISREG(Path(path).lstat().st_mode)
    except OSError:
        return False


def run_circular_dichroism_tool_request(request, *, input_path, output_directory):
    """Verify copied bytes, decode once, then use the existing CD calculation.

    One direct population and one numerical calculation occur here. The
    calculator's existing internal sheet revalidation/population is unchanged.
    This is not execution of the original Biomni function; its provenance flag
    remains false. Only the enclosing selected worker writes the result file.
    """
    request = contracts.validate_circular_dichroism_tool_request(request)
    try:
        directory = Path(output_directory).resolve(strict=True)
        path = Path(input_path)
        if not directory.is_dir() or not _regular(path):
            raise ValueError("circular_dichroism_input_unavailable")
        if path.resolve(strict=True).parent != directory:
            raise ValueError("circular_dichroism_owned_input_conflict")
        selected = request["input_file"]
        with path.open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != selected["size_bytes"]:
                raise ValueError("circular_dichroism_input_identity_conflict")
            raw = stream.read()
    except OSError as error:
        raise ValueError("circular_dichroism_input_unavailable") from error
    if len(raw) != selected["size_bytes"] or hashlib.sha256(raw).hexdigest() != selected["sha256"]:
        raise ValueError("circular_dichroism_input_identity_conflict")
    decoded = decode_molecular_sequence_input(raw, tag_key="schema")
    if decoded["failure"] is not None:
        raise ValueError("circular_dichroism_input_" + decoded["failure"]["code"])
    sheet = core.populate_circular_dichroism_sheet(measurements=decoded["value"])
    components = core.calculate_circular_dichroism_components(sheet)
    return dict(version=contracts.RESULT_VERSION, request=request, sheet=sheet, components=components)


__all__ = ["CD_TOOL", "circular_dichroism_tool_contract", "run_circular_dichroism_tool_request"]
