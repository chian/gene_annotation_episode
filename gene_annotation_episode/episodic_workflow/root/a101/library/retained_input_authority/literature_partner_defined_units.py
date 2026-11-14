"""Source-defined activity units, with exact endpoint-bound source custody.

There is deliberately no universal U conversion. A selected source definition
supplies the positive amount, molecular entity and per-time meaning. This finite
reader verifies that relationship's bytes and lexical structure; the association
with an experiment remains an explicit scientific interpretation.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import REF, obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_assay_inputs import _witness_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_partner_source_fields import number_selector_schema
_DEFINITION_KEYS = ('bridge', 'clause', 'amount', 'amount_unit', 'time_unit', 'endpoint', 'endpoint_entity', 'definition_entity')

def _enriched_schema():
    return obj({**deepcopy(_witness_schema()['properties']), 'artifact_ref': deepcopy(REF)})

def _parsed_number_schema():
    return obj({'selector': obj({'witness': _enriched_schema(), 'number_start': {'type': 'integer', 'minimum': 0}, 'number_end': {'type': 'integer', 'minimum': 1}}), 'raw_number': {'type': 'string', 'minLength': 1}, 'value': {'type': 'number'}, 'relation': {'enum': ['point', 'lt', 'le']}})

def defined_rate_unit_schema():
    """Closed source selectors; no supplied scientific coefficient or scale."""
    fields = {name: deepcopy(_witness_schema()) for name in _DEFINITION_KEYS if name != "amount"}
    fields["amount"] = number_selector_schema()
    return obj({"kind": {"const": "source_defined_rate_unit"},
        "witness": _witness_schema(), "definition": obj(fields)})


def parsed_defined_rate_unit_schema():
    fields = {name: _enriched_schema() for name in _DEFINITION_KEYS if name != 'amount'}
    fields['amount'] = _parsed_number_schema()
    return obj({'witness': _enriched_schema(), 'raw_unit': {'type': 'string', 'minLength': 1}, 'canonical_unit': {'const': 'pmol/min/mg'}, 'multiplier': {'type': 'number', 'exclusiveMinimum': 0}, 'definition': obj(fields)})
