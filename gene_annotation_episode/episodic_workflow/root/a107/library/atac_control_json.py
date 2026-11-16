"""A107 atac control json."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.a107.library.atac_execution_contracts import require

def decode_json(raw):

    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'invalid_native_control_json')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('invalid_native_control_json')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('invalid_native_control_json') from error
