"""Original arsenic received values for supplied decision information."""
from __future__ import annotations
from copy import deepcopy
from .molecular_provenance_display import _molecular_failure_view
from .decision_prompt_text import _rows
from .decision_prompt_text import _table


def _arsenic_speciation_text(packet, number):
    """Present every retained selected field without recalculating quantities."""
    shown = {key: deepcopy(value) for key, value in packet.items()
        if key not in {"source_ref", "version"}}
    shown["failures"] = [_molecular_failure_view(issue, packet) for issue in packet["failures"]]
    return "\n\n".join(["Selected molecular result " + str(number),
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Operation", "analyze_arsenic_speciation_hplc_icpms")]),
        _table(("Retained field/member", "Literal value"), _rows(shown))])


