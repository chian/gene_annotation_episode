"""Bind A106 table numbers to their printed row, column headers and unit.

The existing scalar reader owns numerical semantics and physical identity.
This adapter only replaces adjacency with the existing XML geometry checks;
it does not calculate predictions or establish their scientific applicability.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_assay_inputs import _witness_schema

def table_number_schema(literal):
    schema = deepcopy(literal)
    schema['properties'].update(kind={'const': 'source_table_number'}, row_label=_witness_schema(), column_labels={'type': 'array', 'minItems': 1, 'items': _witness_schema()})
    schema['required'] = list(schema['properties'])
    schema['description'] = 'Read a printed number from an HTML/JATS table using its exact row label, column headers and unit witness. Include grouped quantity and model headers when needed to identify one column. number_start and number_end are zero-based character offsets within number.witness.quote; witness start/end are absolute UTF-8 byte offsets in the source. Values are read from retained bytes. Reading a published model prediction does not establish its independence or biological applicability.'
    return schema
