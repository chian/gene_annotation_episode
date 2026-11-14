from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.domain import obj
SELECTION_VERSION = 'calibrated_signal_selection_v1'
TEXT = {'type': 'string', 'minLength': 1}

def array(schema, *, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def calibrated_signal_selection_schema():
    return obj({'version': {'const': SELECTION_VERSION}, **{name: array(TEXT, unique=True) for name in ('sample_ids', 'species_ids', 'calibration_ids')}})
