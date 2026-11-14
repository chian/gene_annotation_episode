"""Receiver presentation of already-computed native numerical decision context.

Stored observations and numerical sheets remain complete. Requested typed child
returns already carry the admitted measurements and qualifications; automatically
hydrated native observations must not expand those returns for the receiver.
"""

from collections.abc import Mapping
from copy import deepcopy


def infernal_receiver_context(context: Mapping) -> dict:
    """Detach a full, unframed context and omit native automatic observations.

    Only rows in the top-level ``working_state.observations`` list with the exact
    Infernal or native BLAST host marker are omitted. Explicit child returns,
    action outcomes, lookup results and all other context remain unchanged.
    This function neither retrieves records nor parses or recalculates results.
    """
    if not isinstance(context, Mapping):
        raise TypeError("context must be a mapping")

    projected = deepcopy(dict(context))
    working_state = projected.get("working_state")
    if not isinstance(working_state, Mapping):
        return projected
    observations = working_state.get("observations")
    if not isinstance(observations, list):
        return projected

    projected["working_state"] = dict(working_state)
    projected["working_state"]["observations"] = [
        row
        for row in observations
        if not (
            isinstance(row, Mapping)
            and any(isinstance(row.get(marker), Mapping)
                and row[marker].get("version") == version
                for marker, version in (
                    ("native_infernal", "native_infernal_observation_v1"),
                    ("native_blast_database", "native_blast_database_observation_v1"),
                    ("native_blast_standard_database", "native_blast_standard_database_observation_v1"),
                    ("native_blast_pairwise", "native_blast_pairwise_observation_v1")))
        )
    ]
    return projected


__all__ = ["infernal_receiver_context"]
