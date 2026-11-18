"""Private A104 LocalExecution resource operations."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj

def launch_operation_catalog():
    """Declared launch operations, without a target/resource observation."""
    return [{'name': 'execution.capabilities', 'description': 'Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection.', 'input_schema': obj({})}]
