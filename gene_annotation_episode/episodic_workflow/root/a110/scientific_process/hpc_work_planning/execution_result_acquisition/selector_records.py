"""Private A110 Results selector_records"""
from __future__ import annotations
from .schema_fields import LIMIT
from .schema_fields import OFFSET
from .schema_fields import TEXT
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import obj
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])
