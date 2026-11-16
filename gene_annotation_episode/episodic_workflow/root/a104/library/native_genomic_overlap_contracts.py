"""Pure records for the selected native all-pairs genomic overlap operation.

Fixed G2 definitions implement packet425 DATA_CONTRACT.json, SHA-256
4b8f38595549bd32484121129132474bc6fd3f5e9f7be1130433a6b3a208c00e.
G1 owns scientific records; these checks validate supplied execution facts and
associations, never observe files, grant source authority or execute work.
"""
from __future__ import annotations
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}
