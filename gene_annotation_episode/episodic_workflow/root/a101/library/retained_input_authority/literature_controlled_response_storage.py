"""Native custody and exact-key projection for selected controlled responses.

This repository owns no scientific choices, model calls, controller observations
or episode loop. Source meanings and numerical results remain separate payloads.
"""
from __future__ import annotations
from copy import deepcopy as cp
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority import literature_controlled_response_v3_inputs as source

def controlled_response_cells_schema():
    return cp(source._schemas()['NATIVE_RETURN_SCHEMA_V3_007'])
