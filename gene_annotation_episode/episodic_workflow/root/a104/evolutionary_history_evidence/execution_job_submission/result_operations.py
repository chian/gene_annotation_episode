"""Private A104 Launch result operations."""
from __future__ import annotations
from .schema_fields import FILE_LIMIT
from .schema_fields import OFFSET
from .schema_fields import TEXT
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj

def native_result_operation_catalog():
    """Actual local/PBS acquisition operators; execution still requires a target."""
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Observe the original attempt and acquire bounded first windows of the requested paths.', 'input_schema': obj({})}, {'name': 'execution.results.read', 'description': 'Acquire one selected bounded byte window within the original requested paths and interval.', 'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]
